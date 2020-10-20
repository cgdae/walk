#! /usr/bin/env python3

'''
Summary:

    Provides a mechanism for running commands which avoids actually running
    commands if we can infer that they would not change any generated files.


Use as a build system:

    walk.py allows a build system to be written simply as a list of commands to
    be run, without specifying detailed dependency information.
    
    By specifying these commands as calls to walk.system(), we ensure that they
    will not be run if the command would not modify the generated files, so we
    end up only running the commands that are necessary to bring things up to
    date.
    
    For example to build a project consisting of two .c files, one could do:
    
        walk.system( 'cc -c -o foo.o foo.c', 'foo.o.walk')
        walk.system( 'cc -c -o bar.o bar.c', 'bar.o.walk')
        walk.system( 'cc -o myapp foo.o bar.o', 'myapp.walk')
    
    Unlike conventional builds systems, we are is in control of the order in
    which commands are run, so for example we could choose to compile newer
    source files first, which often finds compilation errors more quickly.

How it works:

    The first time we run a command, we create a file <walk_file> which
    contains information about the command and what files the command (or its
    child commands) read or wrote.

    On subsequent invocations of the same command, we check the modification
    times of the files listed in <walk_file>. If all input files (e.g. opened
    for reading), are older than all output files (e.g. opened for writing), we
    do not run the command.

    Otherwise we run the command as before and re-create <walk_file>.

    We specially handle cases such as failed input files (e.g. failed to open
    for reading) where the file now exists - in this case we always run the
    command. We also ensure that we are resilient to being interrupted by
    signals or system crashes. For example we write a zero-length <walk_file>
    before re-running a command so that if we are killed before the command
    completes, then the next we are run we will know the command was
    interrupted and can force a re-run.


Concurrency:

    The Concurrent class allows the running of commands (via walk.system())
    on internal threads. One can use the .join() method to wait for a set of
    commands to complete before running further commands.
    
    Example:

        # Create multiple internal worker threads.
        #
        walk_concurrent = walk.Concurrent( num_threads=3)
        
        # Schedule commands to be run concurrently.
        #
        walk_concurrent.system( 'cc -c -o foo.o foo.c', 'foo.o.walk')
        walk_concurrent.system( 'cc -c -o bar.o bar.c', 'bar.o.walk')
        ...
        
        # Wait for all scheduled commands to complete.
        #
        walk_concurrent.join()
        
        # Run more commands.
        #
        walk.system( 'cc -o myapp foo.o bar.o', 'myapp.walk')
        walk_concurrent.end()


Command line usage:

    We are primarily a python module, but can also be used from the command
    line:

        walk.py [<args>] <walk-path> <command> ...

    Args:
        --new <path>
            Treat file <path> as new, like make's -W.
            
        -f 0 | 1
            0 - never run the command.
            1 - always run the command.
        
        --test
            Does some basic tests.

    Examples:

        walk.py cc myapp.exe.walk -Wall -W -o myapp.exe foo.c bar.c


Limitatations:

    As of 2020-06-02 we are very experimental.
    
    Things might go wrong if a command uses the first successful match when
    searching for a file in multiple places, and a file is created where the
    command previously failed to open.

    
Implementation details:

    We use two approaches to finding out what files a command (or its
    sub-command) opened for reading and/or writing - an LD_PRELOAD library
    which intercepts open() etc, or running commands under a syscall tracer
    such as Linux's strace or OpenBSD's ktrace.

    As of 2020-06-01, the LD_PRELOAD approach on Linux doesn't work due to
    ld appearing to open the output file using a function that has proven
    difficult to intercept. On OpenBSD we can use either approach but default
    to LD_PRELOAD.

    It's not yet clear which of LD_PRELOAD or strace/ktrace is the better
    approach overall; maybe LD_PRELOAD could be faster (though this needs
    profilng) but tracing syscalls could be more reliable.


Future:

    Automatic concurrency:
    
        It might be possible to use the information in walk files to do
        automatic command ordering: look at existing build files to find
        dependency information between commands (i.e. find commands whose
        output files are read by other commands) and run commands in the right
        order without the caller specify anything other than an unordered list
        of commands.

        And we could also do automatic concurrency - run multiple commands
        concurrently when they are known to not depend on each otheer.

        Dependency information in walk files is not available the first time
        a build is run, and might be incorrect if a command has changed, so
        we'd always have to re-scan walk files after commands have completed
        and re-run commands if necessary. But most of the time this wouldn't
        necessary.
    
    Automatic selection of source files:
    
        A log of the script for building Flightgear is for selecting the source
        files to compile and link together.

        It might be possible to write code that extracts unresolved and defined
        symbols after each compilation and saves to a separate file next to the
        .walk file. Then one could tell the script to compile the file that
        contains main() and have it automatically look for other files that
        implement the unresolved symbols.

        We would need help to resolve situations where more than one file
        implements the same symbol.


License:

    Copyright 2020 Julian Smith.

    This program is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    This program is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with this program.  If not, see <https://www.gnu.org/licenses/>.

'''

import codecs
import hashlib
import io
import os
import queue
import re
import subprocess
import sys
import textwrap
import threading
import time


_log_prefix = ''

def log_prefix_set( prefix):
    global _log_prefix
    _log_prefix = prefix

class LogPrefixScope:
    def __init__(self, prefix):
        self.prefix = prefix
    def __enter__(self):
        global _log_prefix
        self.prefix_prev = _log_prefix
        _log_prefix += self.prefix
    def __exit__(self, type, value, tb):
        global _log_prefix
        _log_prefix = self.prefix_prev

_log_last_t = 0
def log( text):
    global _log_last_t
    out = sys.stdout
    if text.endswith( '\n'):
        text = text[:-1]
    for line in text.split( '\n'):
        out.write( f'{_log_prefix}{line}\n')
    out.flush()
    _log_last_t = time.time()

def log_ping( text, interval):
    '''
    Outputs <text> with walk.log() if it is more than <interval> seconds since
    walk.log() was last called.
    '''
    t = time.time()
    if t - _log_last_t > interval:
        log( text)

_mtime_new = 3600*24*365*10*1000
_mtime_cache = dict()

def mtime( path, default=None):
    '''
    Returns mtime of file, or <default> if error - e.g. doesn't
    exist. Caches previously-returned information, so it's important to call
    mtime_cache_clear() if a file is updated.
    '''
    t = _mtime_cache.get( path, -1)
    if t == -1:
        # Not in cache.
        try:
            t = os.path.getmtime( path)
        except Exception:
            t = default
        _mtime_cache[ path] = t
    return t


def mtime_cache_clear( path=None):
    global _mtime_cache
    if path:
        _mtime_cache.pop( path, None)
    else:
        _mtime_cache = dict()


def mtime_cache_mark_new( path):
    path = os.path.abspath( path)
    _mtime_cache[ path] = _mtime_new

def mtime_cache_mark_old( path):
    path = os.path.abspath( path)
    _mtime_cache[ path] = 0


def remove( filename):
    '''
    Removes file without error if we fail or it doesn't exist.
    '''
    try:
        os.remove( filename)
    except Exception:
        pass


def ensure_parent_dir( path):
    parent = os.path.dirname( path)
    if parent:
        os.makedirs( parent, exist_ok=True)


def date_time( t=None):
    '''
    Returns <t> in the form YYYY-MM-DD-HH:MM:SS. If <t> is None, we use current
    date and time.
    '''
    if t is None:
        t = time.time()
    return time.strftime( "%F-%T", time.gmtime( t))

def get_verbose( v):
    '''
    Returns <v> or default verbose settings if <v> is None.
    '''
    if v is None:
        return 'de'
    return v

def file_write( text, path, verbose=None, force=None):
    '''
    If file <path> exists and contents are already <text>, does nothing.

    Otherwise writes <text> to file <path>.

    Will raise an exception if something goes wrong.

    <verbose> and <force> are as in walk.system().
    '''
    verbose = get_verbose( verbose)
    try:
        text0 = open( path).read()
    except OSError:
        text0 = None
    doit = text != text0
    doit2 = doit
    if force is not None:
        doit2 = force
    
    if doit2:
        message = ''
        if 'f' in verbose and not doit:
            message += ' Forcing update of %s' % path
        elif 'd' in verbose:
            message += ' Updating %a' % path
        if message:
            log( message.strip())
        
        path_temp = '%s-walk-temp' % path
        ensure_parent_dir( path)
        with open( path_temp, 'w') as f:
            f.write( text)
        os.rename( path_temp, path)
    
    else:
        message = ''
        if 'F' in verbose and doit:
            message += ' Forcing no update of %s' % path
        elif 'D' in verbose:
            message += ' Not updating %s' % path
        if message:
            log( message.strip())


class CommandFailed( Exception):
    '''
    Result of running a command.
    '''
    def __init__( self, wait_status, text=None):
        self.wait_status = wait_status
        self.text = text

    
def system(
        command,
        walk_path,
        verbose=None,
        force=None,
        description=None,
        command_compare=None,
        method=None,
        out=None,
        out_prefix='',
        out_buffer=False,
        ):
    '''
    Runs command unless stored info from previous run implies that the command
    would not change output files.
    
    Returns:
        Integer termination status if we run command.
        Otherwise None.
    command:
        Command to run.
    walk_path:
        Name of generated walk file; this will contain information on what
        files the command read and wrote.
    verbose:
        A string where the presence of particular characters controls what
        diagnostics are generated:
        
            c   Show the command itself if we run the command.
            d   Show command description if we run the command.
            f   Show that we are forcing the command to be run.
            m   Show generic message if we are running the command.
            r   Show the reason for running the command.
        
        Upper-case versions of the above cause the equivalent messages to be
        generated if we /don't/ run the command.
    force:
        If None (the default), we run the command unless walk file and mtimes
        indicate it will make no changes.
        
        Otherwise if true (e.g. 1 or True) we always run the command; if false
        (e.g. 0 or False) we never run the command.
    description:
        Text used by <verbose>'s 'd' option. E.g. 'Compiling foo.c'.
    method:
        None, 'preload' or 'trace'.

        If None, we use default setting for the OS we are running on.

        If 'trace' we use Linux strace or OpenBSD ktrace to find what file
        operations the command used.

        If 'preload' we include our own code using LD_PRELOAD to find calls to
        open() etc.
    command_compare:
        If not None, should be callable taking two string commands, and return
        non-zero if these commands differ significantly.

        E.g. for gcc-style compilation commands this could ignore any -W* args
        to avoid unnecessary recompilation caused by changes to warning flags
        (unless -Werror is also used).
    out:
        Where the command's stdout and stderr go:
            None:
                If both out_prefix and out_buffer are false, the command's
                output goes directly to the inherited stdout/stderr. Otherwise
                it is sent (via a pipe) to our stdout.

            A callable taking a single <text> param.

            An object with .write() method taking a single <text> param.

            An integer >= 0, used with os.write().

            A subprocess module special value (should not be subprocess.PIPE)
            such as subprocess.DEVNULL: passed directly to subprocess.Popen().
    out_prefix:
        If not None, prepended to each line sent to <out>.
    out_buffer:
        If true, we buffer up output and send to <out> in one call after
        command has terminated.
    '''
    verbose = get_verbose( verbose)
    
    if method is None:
        if _osname == 'Linux':
            # 'preload' doesn't work yet - seems like we don't intercept
            # whatever function it is that gcc uses to open the output
            # executable when linking.
            #
            method = 'trace'
        elif _osname == 'OpenBSD':
            # Both 'trace' and 'preload' currently appear to work, but 'trace'
            # hasn't been tested that much so the default is 'preload'.
            #
            method = 'preload'
        else:
            assert 0
    
    doit, reason = _analyse_walk_file( walk_path, command, command_compare)
    
    doit2 = doit
    if force is not None:
        doit2 = force
    
    if doit2:
        # We always write a zero-length .walk file before running the command,
        # which can be used to detect when a command did not complete (e.g.
        # because we were killed.
        #
        # This allows our diagnostics to differentiate between running a
        # command because it has never been run before (no .walk file) and
        # runnng a command because previous invocation did not complete
        # or failed (zero-length .walk file).
        #
        ensure_parent_dir( walk_path)
        with open( walk_path, 'w') as f:
            pass
        
        strace_path = walk_path + '-1'
        remove( strace_path)
        
        if method == 'preload':
            command2 = '%s %s' % (_make_preload( strace_path), command)
            #log( 'command2 is: %s' % command2)
        elif method == 'trace':
            if _osname == 'Linux':
                command2 = ('strace'
                        + ' -f'
                        + ' -o ' + strace_path
                        + ' -q'
                        + ' -qq'
                        + ' -e trace=%file'
                        + ' ' + command
                        )
            elif _osname == 'OpenBSD':
                command2 = 'ktrace -i -f %s -t cn %s' % (strace_path, command)
            else:
                assert 0
        else:
            assert 0
        
        message = _make_diagnostic( verbose, command, description, reason, force=not doit, notrun=False)
        if message:
            log( message)
      
        t_begin = time.time()
        
        e = _system(
                command2,
                throw=False,
                out=out,
                out_prefix=out_prefix,
                out_buffer=out_buffer,
                )
        
        t_end = time.time()
        
        if e:
            if 'e' in verbose and 'c' not in verbose:
                # We didn't output the command above, so output it now.
                log( 'Command failed: %s' % command)

        else:
            # Command has succeeded so create the .walk file so that future
            # invocations know whether the command should be run again.
            #
            if method == 'preload':
                walk = _process_preload( command, strace_path, t_begin, t_end)
            elif method == 'trace':
                walk = _process_strace( command, strace_path, t_begin, t_end)
            else:
                assert 0
            walk.write( walk_path)
        
        remove( strace_path)
        
    else:
        message = _make_diagnostic( verbose, command, description, reason, force=doit, notrun=True)
        if message:
            log( message)
        
        e = None
    
    return e


class Concurrent:
    '''
    Simple support for running commands concurrently.
    
    Usage:
    
        Instead of calling walk.system(), create a walk.Concurrent instance and
        use its .system() method.

        To wait until all scheduled tasks have completed, call .join().

        Then to close down the internal threads, call .end().
    '''
    def __init__( self, num_threads, keep_going=False, max_load_average=None):
        '''
        num_threads:
            Number of threads to run. (If zero, out .system() methods simply
            calls walk.system() directly.)
        keep_going:
            If false (the default) we raise exception from .system() and
            .join() if a previous command has failed. Otherwise new commands
            will be scheduled regardless.
            
        Errors from scheduled commands can be retreived using .get_errors().
        '''
        self.num_threads = num_threads
        self.keep_going = keep_going
        self.max_load_average = max_load_average
        self.queue = queue.Queue( maxsize=1)
        self.errors = queue.Queue()
        self.threads = []
        for i in range( self.num_threads):
            thread = threading.Thread( target=self._thread_fn, daemon=True)
            self.threads.append( thread)
            thread.start()
        
    def _thread_fn( self):
        while 1:
            item = self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            e = system( *item)
            if e:
                (
                        command,
                        walk_path,
                        verbose,
                        force,
                        description,
                        command_compare,
                        out,
                        out_prefix,
                        out_buffer,
                        ) = item
                self.errors.put( (command, walk_path, e))
            self.queue.task_done()
        
    def _raise_if_errors( self):
        if self.keep_going:
            return
        if not self.errors.empty():
            raise Exception( 'task(s) failed')
    
    def system( self,
            command,
            walk_path,
            verbose=None,
            force=None,
            description=None,
            command_compare=None,
            out=None,
            out_prefix=None,
            out_buffer=None,
            ):
        '''
        Schedule a command to be run. This will call walk.system() on one of
        our internal threads.
        
        Will raise an exception if an earlier command failed (unless we were
        constructed with keep_going=true).
        
        Will block until a thread is free to handle the new command, or for
        load average to reduce below self.max_load_average.
        '''
        self._raise_if_errors()
        
        if self.max_load_average is not None:
            it = 0
            while 1:
                current_load_average = os.getloadavg()[0]
                if current_load_average < self.max_load_average:
                    break
                if it % 5 == 0:
                    log( f'[Waiting for load_average={current_load_average:.1f} to reduce below {self.max_load_average:.1f}...]')
                time.sleep(1)
                it += 1
        
        if self.num_threads:
            self.queue.put(
                    (
                    command,
                    walk_path,
                    verbose,
                    force,
                    description,
                    command_compare,
                    out,
                    out_prefix,
                    out_buffer,
                    ))
        else:
            e = system(
                    command,
                    walk_path,
                    verbose,
                    force,
                    description,
                    command_compare,
                    out=out,
                    out_prefix=out_prefix,
                    out_buffer=out_buffer,
                    )
            if e:
                self.errors.put( (command, walk_path, e))
    
    def join( self):
        '''
        Waits until all current tasks have finished.
        
        Will raise an exception if an earlier command failed (unless we were
        constructed with keep_going=true).
        '''
        self.queue.join()
        self._raise_if_errors()
    
    def get_errors( self):
        '''
        Returns list of errors from completed tasks.

        These errors will not be returned again by later calls to
        .get_errors().

        Each returned error is (command, walk_path, e).
        '''
        ret = []
        while 1:
            if self.errors.empty():
                break
            e = self.errors.get()
            ret.append( e)
        return ret
    
    def end( self):
        '''
        Tells all threads to terminate and returns when they have terminated.
        '''
        for i in range( self.num_threads):
            self.queue.put( None)
        self.queue.join()
        for t in self.threads:
            t.join()



#
# Everything below here is internal implementation details, and not for
# external use.
#


def _make_diagnostic( verbose, command, description, reason, force, notrun):
    '''
    Returns diagnostic text, such as:
    
        Running command because foo.h is new: gcc -o foo.c.o foo.c
    
    verbose:
        String describing what elements should be included in diagnostics. See
        walk.system()'s documentation for details.
    command:
        The command itself.
    description:
        Alternative description of the command.
    reason:
        The reason for (not) running the command.
    force:
        Whether we are forcing (not) running.
    notrun:
        If true, we are not running the command and we reverse the case of
        <verbose> when checking for flags.
    '''
    notrun_text = ''
    if notrun:
        verbose = verbose.swapcase()
        notrun_text = ' not'
    
    message_tail = ''
    if 'd' in verbose and description:
        # Show description of command.
        message_tail += '(%s)' % description
    if 'c' in verbose:
        # Show the command itself.
        if message_tail:
            message_tail += ': '
        message_tail += command

    message_head = ''
    if 'f' in verbose and force:
        # Show that we are forcing run/not run of command.
        message_head += ' forcing%s running of command' % notrun_text
    if 'r' in verbose:
        # Show reason for running the command.
        if not message_head:
            if notrun:
                message_head += '%s running command' % notrun_text
            else:
                message_head += 'running command'
        if reason:
            message_head += ' because %s' % reason
    if 'm' in verbose and not message_head:
        # Show generic message.
        message_head += '%s running command' % notrun_text_initial
    message_head = message_head.strip()
    if message_head:
        message_head = message_head[0].upper() + message_head[1:]

    message = message_head
    if message_tail:
        if message:
            message += ': '
        message += message_tail
    
    if 0:
        log( f'verbose={verbose} command={command!r} description={description!r} reason={reason!r}, force={force} notrun={notrun}: returning: {message!r}')
    return message


def _system(
        command,
        out=None,
        capture=False,
        throw=True,
        encoding='latin_1',
        encoding_errors='strict',
        out_prefix='',
        out_buffer=False,
        ):
    '''
    Runs a command, with support for capturing the output etc.
    
    Note that stdout and stderr always go to the same place.
    
    Args:
        command:
            A string, the command to run.
        out:
            Where the command's stdout and stderr go:
                None:
                    If both out_prefix and out_buffer are false, the command's
                    output goes to the inherited stdout/stderr. Otherwise it is
                    sent to our stdout.
                
                A callable taking single <text> param.
                
                Object with .write() method taking single <text> param.
                
                Integer >= 0, a file descriptor.
                
                Other subprocess module special value (should not be
                subprocess.PIPE): passed directly to subprocess.Popen().
        capture:
            If true, we also capture the output text and include it in the
            returned information.
        throw:
            If true, we raise a CommandFailed exception if command failed.
        out_prefix:
            If not None, prepended to each line sent to <out>. Not included
            in output returned if <capture> is true.
        out_buffer:
            If true, we buffer up output and send to <out> in one call after
            command has terminated.
    Returns:
        Returned value depends on <out_capture> and <throw>:
        
        capture throw   Return
        ---------------------------
        false   false   wait_status
        false   true    None or raise CommandFailed instance.
        true    false   (wait_status, out_text)
        true    true    out_text or raise CommandFailed instance.
    '''
    stdout = out
    
    outfn = None
    if callable( out):
        stdout = subprocess.PIPE
        outfn = out
    elif getattr( out, 'write', None):
        stdout = subprocess.PIPE
        outfn = lambda text: out.write(text)
    elif isinstance( out, int) and out >= 0:
        stdout = subprocess.PIPE
        outfn = lambda text: os.write( out, text)
    
    if capture or out_buffer or out_prefix:
        stdout = subprocess.PIPE
    
    buffer_ = None
    if capture or out_buffer:
        buffer_ = io.StringIO()
    
    if stdout == subprocess.PIPE and not out:
        outfn = sys.stdout.write
    
    #log( f'stdout={stdout} command={command}')
    child = subprocess.Popen(
            command,
            shell=True,
            stdout=stdout,
            stderr=subprocess.STDOUT,
            )
    
    if encoding and stdout == subprocess.PIPE:
        child_out = codecs.getreader( encoding)( child.stdout, encoding_errors)
    else:
        child_out = child.stdout
    
    if stdout == subprocess.PIPE:
        for line in child_out:
            #log( f'out_prefix={out_prefix!r}. have read line={line!r}')
            if not out_buffer:
                outfn( out_prefix + line)
            if buffer_:
                buffer_.write( line)
    
    wait_status = child.wait()
    
    text = None
    if buffer_:
        text = buffer_.getvalue()
    if out_buffer:
        t = text
        if out_prefix:
            lines = t.split('\n')
            t = [out_prefix + line for line in lines]
            t = '\n'.join(t)
        outfn( t)
    
    if wait_status and throw:
        raise SystemFailed( wait_status, text)
    if capture:
        return wait_status, text
    return wait_status
    

def _analyse_walk_file( walk_path, command, command_compare=None):
    '''
    Looks at information about previously opened files and decides whether we
    can avoid running the command again. This is run every time the user calls
    walk.system() so is fairly time-critical.
    
    walk_path:
        Path of the walk-file containing information about what files the
        command read/wrote when it was run before.
    command:
        The command that was run previously.
    command_compare:
        If not None, should be callable taking two string commands, and return
        non-zero if these commands differ significantly. E.g. for gcc commands
        this could ignore any -W* args to avoid unnecessary recompilation
        caused by changes to warning flags.
    
    Returns (doit, reason):
        doit:
            True iff command should be run again.
        explanation:
            Text description of why <doit> is set to true/false.
    '''
    reason = []
    
    try:
        f = open( walk_path)
    except Exception:
        doit = True
        reason.append( 'no info available on previous invocation')
    
    else:
        # We want to find oldest file that was opened for writing by previous
        # invocation of this command, and the newest file that was opened for
        # reading. If the current mtime of the newest read file is older than
        # the current mtime of the oldest written file, then we don't need to
        # run the command again.
        #
        oldest_write = None
        oldest_write_path = None
        newest_read = None
        newest_read_path = None

        command_old = None
        t_begin = None
        t_end = None
        
        num_lines = 0
        for line in f:
            #log( 'looking at line: %r' % line)
            # Using regexes is slower, e.g. 1.6ms vs 2.2ms.
            num_lines += 1
            
            # Exclude trailing \n.
            line = line[:-1]
            
            if 0:
                pass
            elif not command_old and line.startswith( 'command: '):
                command_old = line[ len('command: '):]
                
                if command_compare:
                    diff = command_compare(command, command_old)
                else:
                    diff = (command != command_old)
                if diff:
                    if 0:
                        log( 'command has changed:')
                        log( '    from %s' % command_old)
                        log( '    to   %s' % command)
                    return True, 'command has changed'
                    #return True, 'command has changed %r => %r' % (command_old, command)
            elif not t_begin and line.startswith( 't_begin: '):
                t_begin = float( line[ len( 't_begin: '):])
            
            elif not t_end and line.startswith( 't_end: '):
                t_end = float( line[ len( 't_end: '):])
            
            else:
                pos = line.find( ' ')
                assert pos >= 0
                ret = int( line[:pos])
                read = line[pos+1] == 'r'
                write = line[pos+2] == 'w'
                path = line[pos+4:]
                
                # Previous invocation of command opened <path>, so we need to
                # look at its mtime and update newest_read or oldest_write
                # accordingly.
                
                if path.startswith( '/tmp/'):
                    continue
                
                if path.startswith( '/sys/'):
                    # E.g. gcc seems to read /sys/devices/system/cpu/online,
                    # which can have new mtime and thus cause spurious reruns
                    # of command.
                    continue
                
                # This gives a modest improvement in speed.
                #if path.startswith( '/usr/'):
                #    continue
                
                if _osname == 'OpenBSD' and path == '/var/run/ld.so.hints':
                    # This is always new, so messes things up.
                    continue

                if _osname == 'Linux' and path.startswith( '/etc/ld.so'):
                    # This is sometimes updated (maybe after apt install?), so
                    # messes things up.
                    continue

                t = mtime( path)
                
                if 0 and path.startswith( os.getcwd()):
                    log( 't=%s ret=%s read=%s write=%s path: %s' % (date_time(t), ret, read, write, path))

                if read and not write and ret < 0:
                    # Open for reading failed last time.
                    if t:
                        # File exists, so it might open successfully this time,
                        # so pretend it is new.
                        #
                        if 0: log( 'forcing walk_path t=%s walk_path=%s path=%s' % (
                                date_time( mtime( walk_path)),
                                walk_path,
                                path,
                                ))
                        newest_read = time.time()
                        newest_read_path = path
                if read and ret >= 0:
                    # Open for reading succeeded last time.
                    if t:
                        if newest_read == None or t > newest_read:
                            newest_read = t
                            newest_read_path = path
                    else:
                        # File has been removed.
                        newest_read = time.time()
                        newest_read_path = path
                if write and ret < 0:
                    # Open for writing failed.
                    pass
                if write and ret >= 0:
                    # Open for writing succeeded.
                    if t:
                        if oldest_write == None or t < oldest_write:
                            oldest_write = t
                            oldest_write_path = path
                    else:
                        # File has been removed.
                        oldest_write = 0
                        oldest_write_path = path

        #log( 'oldest_write: %s %s' % (date_time(oldest_write), oldest_write_path))
        #log( 'newest_read:  %s %s' % (date_time(newest_read), newest_read_path))

        # Note that don't run command if newest read and oldest write have the
        # same mtimes, just in case they are the same file.
        #
        doit = False
        if num_lines == 0:
            doit = True
            reason.append( 'previous invocation failed or was interrupted')
        elif newest_read is None:
            doit = True
            reason.append( 'no input files found')
        elif oldest_write is None:
            doit = True
            reason.append( 'no output files found')
        elif newest_read > oldest_write:
            doit = True
            reason.append( 'input is new: %r' % (
                    os.path.relpath( newest_read_path)
                    #oldest_write_path,
                    ))
        else:
            doit = False
            reason.append( 'newest input %r not newer then oldest output %r' % (
                    os.path.relpath( newest_read_path),
                    os.path.relpath( oldest_write_path),
                    ))
    
    reason = ', '.join( reason)
    
    return doit, reason


_osname = os.uname()[0]

class WalkFile:
    '''
    Creates a walk file, used by code that parses strace or preload output.
    '''
    def __init__( self, command, t_begin, t_end, verbose=False):
        self.command = command
        self.t_begin = t_begin
        self.t_end = t_end
        self.path2info = dict()
        self.verbose = verbose
    
    def add_open( self, ret, path, r, w):
        if self.verbose:
            print('open: ret=%s r=%s w=%s path=%s' % (ret, r, w, path))
        path = os.path.abspath( path)
        mtime_cache_clear( path)
        # Look for earlier mention of <path>.
        prev = self.path2info.get( path)
        if prev:
            prev_ret, prev_r, prev_w = prev
            if prev_ret == ret and prev_r == r and prev_w == w:
                pass
            elif prev_ret < 0 and ret >= 0:
                self.path2info[ path] = ret, r, w
            elif prev_ret >= 0 and ret >= 0:
                self.path2info[ path] = ret, prev_r or r, prev_w or w
        else:
            # We ignore opens of directories, because mtimes are not useful.
            if not os.path.isdir( path):
                self.path2info[ path] = ret, r, w
    
    def add_delete( self, path):
        if self.verbose:
            print('delete: path=%s' % path)
        path = os.path.abspath( path)
        mtime_cache_clear( path)
        self.path2info.pop( path, None)
    
    def add_rename( self, path_from, path_to):
        if self.verbose:
            print('rename: path_from=%s path_to=%s' % (path_from, path_to))
        path_from = os.path.abspath( path_from)
        path_to = os.path.abspath( path_to)
        mtime_cache_clear( path_from)
        mtime_cache_clear( path_to)
        if 0: log( 'rename: %s => %s' % (path_from, path_to))
        prev = self.path2info.get( path_from)
        ok = False
        if prev:
            prev_ret, prev_r, prev_w = prev
            if prev_w:
                ok = True
                del self.path2info[ path_from]
                self.path2info[ path_to] = prev_ret, prev_r, prev_w
                if 0: log( 'rename %s => %s. have set %s to ret=%s r=%s w=%s' % (
                        path_from, path_to, path_to, prev_ret, prev_r, prev_w))
        if not ok:
            # Not much we can do here. maybe mark the command as always run?
            self.path2info.pop( path_from, None)
            self.path2info.pop( path_to, None)
    
    def write( self, walk_path):
        walk_path_ = walk_path + '-'
        with open( walk_path_, 'w') as f:
            f.write( 'command: %s\n' % self.command)
            f.write( 't_begin: %s\n' % self.t_begin)
            f.write( 't_end: %s\n' % self.t_end)
            for path in sorted( self.path2info.keys()):
                ret, r, w = self.path2info[ path]
                f.write( '%s %s%s %s\n' % (ret, 'r' if r else '-', 'w' if w else '-', path))
        os.rename( walk_path_, walk_path)
        

def _process_strace( command, strace_path, t_begin, t_end):
    '''
    Analyses info in strace (or ktrace on OpenBSD) output file <strace_path>,
    and returns a WalkFile.

    We use a temp file and rename, to ensure that we are safe against crashing
    or SIGKILL etc.
    '''
    walk = WalkFile( command, t_begin, t_end)
    
    if _osname == 'Linux':
        with open( strace_path) as f:
            for line in f:
                #log( 'line is: %r' % line)
                m = None
                if not m:
                    m = re.match( '^[0-9]+ +(openat)[(]([A-Z0-9_]+), "([^"]*)", ([^)]+)[)] = ([0-9A-Z-]+).*\n$', line)
                    if m:
                        syscall = m.group(1)
                        dirat = m.group(2)
                        path = m.group(3)
                        flags = m.group(4)
                        ret = int( m.group(5))
                        read = 'O_RDONLY' in flags or 'O_RDWR' in flags
                        write = 'O_WRONLY' in flags or 'O_RDWR' in flags
                if not m:
                    m = re.match( '^[0-9]+ +(open)[(]"([^"]*)", ([A-Z|_]+)[)] = ([0-9A-Z-]+).*\n$', line)
                    if m:
                        syscall = m.group(1)
                        path = m.group(2)
                        flags = m.group(3)
                        ret = int( m.group(4))
                        read = 'O_RDONLY' in flags or 'O_RDWR' in flags
                        write = 'O_WRONLY' in flags or 'O_RDWR' in flags

                if m:
                    # We should look for changes to current directory in the
                    # strace output, and use this to convert <path> to absolute
                    # path. For now, walk.add_open() uses os.path.abspath(),
                    # which could be incorrect.
                    #
                    
                    # maybe do this only if <write> is true?
                    if 0:
                        log( 'syscall=%s ret=%s. write=%s: %s' % (syscall, ret, write, path))
                    walk.add_open( ret, path, read, write)
                    continue
                
                m = re.match( '^[0-9]+ +rename[(]"([^"]*)", "([^"]*)"[)] = ([0-9A-Z-]+).*\n$', line)
                if m:
                   # log( 'found rename: %r' % line)
                    ret = int( m.group(3))
                    if ret == 0:
                        from_ = m.group(1)
                        to_ = m.group(2)
                        walk.add_rename( from_, to_)
                
    elif _osname == 'OpenBSD':
        # Not sure how reliable this is. The output from kdump seems to have
        # two lines per syscall, with NAMI lines in-between, but sometimes
        # other syscall lines can appear inbetween too, which could maybe cause
        # our simple parser some problems?
        #
        # [Luckily the preload library approach seems to work on OpenBSD.]
        #
        strace_path2 = strace_path + '-'
        e = os.system( 'kdump -n -f %s >%s' % (strace_path, strace_path2))
        assert not e
        write_items = []
        os.remove( strace_path)
        with open( strace_path2) as f:
            while 1:
                line = f.readline()
                if not line:
                    break
                def next_path():
                    while 1:
                        line = f.readline()
                        if not line:
                            raise Exception('expecting path, but eof')
                        m = re.match( '^ *[0-9]+ +[^ ]+ +NAMI +"([^"]*)"', line)
                        if m:
                            return m.group( 1)
                def next_ret( syscall):
                    while 1:
                        line = f.readline()
                        if not line:
                            raise Exception('expecting path, but eof')
                        m = re.match( '^ *[0-9]+ +[^ ]+ +RET +%s ([x0-9-]+)' % syscall, line)
                        if m:
                            ret = m.group( 1)
                            if ret.startswith( '0x'):
                                return int( ret[2:], 16)
                            else:
                                return int( ret)
                m = None
                if not m:
                    m = re.match( '^ *[0-9]+ +[^ ]+ +CALL +open[(]0x[0-9a-z]+,0x([0-9a-z]+)', line)
                    if m:
                        path = next_path()
                        ret = next_ret( 'open')
                        flags = int( m.group(1), 16)
                        flags &= 3
                        if flags == 0:
                            read, write = True, False
                        elif flags == 1:
                            read, write = False, True
                        elif flags == 2:
                            read, write = True, True
                        else:
                            read, write = False, False
                        walk.add_open(ret, path, read, write)
                        
                if not m:
                    m = re.match( '^ *[0-9]+ +[^ ]+ +CALL +rename[(]0x[0-9a-z]+,0x([0-9a-z]+)[)]', line)
                    if m:
                        path_from = next_path()
                        path_to = next_path()
                        walk.add_rename( path_from, path_to)
                
                if not m:
                    m = re.match( '^ *[0-9]+ +[^ ]+ +CALL +unlink[(]0x[0-9a-z]+[)]', line)
                    if m:
                        path = next_path()
                        walk.add_delete( path)
        os.remove( strace_path2)
    else:
        assert 0
    
    return walk


# C code for preload library that intercepts open() etc in order to detect the
# reads/write operations of a process and its child processes.
#
# As of 2020-06-02 this builds ok on OpenBSD and Linux, but on Linux we seem to
# miss out on some calls to open64() which breaks use with (for example) ld.
#
_preload_c = '''
#include <stdio.h>
#include <stdarg.h>
#include <stdlib.h>
#include <errno.h>
#include <string.h>

#include <pthread.h>

/* the following works ok on OpenBSD and Linux.
__USE_GNU is required on linux, otherwise RTLD_NEXT is
undefined. */

/* On both OpenBSD and Linux, fcntl.h declares:
    int open( const char*, int, ...);
- which makes it difficult to write our wrapper. So we temporarily
#define open to something else.*/

#define creat creat_yabs_bad
#define fopen fopen_bad
#define freopen freopen_bad
#define openat openat_yabs_bad  
#define open open_yabs_bad
#define rename rename_bad
#define remove remove_bad
#define unlinkat unlinkat_bad
#define unlink unlink_bad
#define __libc_open64 __libc_open64_bad
#define open64 open64_bad
#define __fopen_internal __fopen_internal_bad

#define __USE_GNU
#include <dlfcn.h>
#include <unistd.h>
#include <sys/param.h>


#include <fcntl.h>

#undef creat
#undef fopen
#undef freopen
#undef open
#undef openat
#undef rename
#undef unlink
#undef unlinkat
#undef remove
#undef __libc_open64
#undef open64
#undef __fopen_internal

static int debug = 0;

static int
    raw_open(
        const char* path, 
        int         flags, 
        mode_t      mode)
{
    static int (*real_open)( const char*, int, mode_t) = NULL;
    if ( !real_open)
    {
        real_open = dlsym( RTLD_NEXT, "open");
    }
    return real_open( path, flags, mode);
}

static int
    raw_openat(
        int         dirfd,
        const char* path, 
        int         flags, 
        mode_t      mode)
{
    static int (*real_openat)( int, const char*, int, mode_t) = NULL;
    if ( !real_openat)
    {
        real_openat = dlsym( RTLD_NEXT, "openat");
    }
    return real_openat( dirfd, path, flags, mode);
}

static FILE*
    raw_fopen(
        const char* path, 
        const char* mode
        )
{
    static FILE* (*real_fopen)( const char*, const char*) = NULL;
    if ( !real_fopen)
    {
        real_fopen = dlsym( RTLD_NEXT, "fopen");
    }
    return real_fopen( path, mode);
}

static void printf_log( const char* format, ...)
{
    static pthread_mutex_t lock = PTHREAD_MUTEX_INITIALIZER;
    
    int e;
    e = pthread_mutex_lock( &lock);
    if (e)
    {
        fprintf( stderr, "pthread_mutex_lock() failed\\n");
    }
    
    const char*         varname = "WALK_preload_out";
    static const char*  log_filename;
    
    log_filename = getenv( varname);
    if ( !log_filename)
    {
        fprintf( stderr, "getenv() returned NULL: %s\\n", varname);
        return;
    }
    
    int f = raw_open( log_filename, O_WRONLY|O_APPEND|O_CREAT, 0777);
    if ( f<0)
    {
        fprintf( stderr, "Couldn't raw_open %s, error=%i\\n",
                log_filename, f);
        return;
    }
    
    FILE* ff = fdopen( f, "a");
    if ( !ff)
    {
        fprintf( stderr, "Couldn't fdopen %i\\n", f);
        close( f);
        return;
    }
    
    va_list ap;
    va_start( ap, format);
    vfprintf( ff, format, ap);
    va_end( ap);
    
    fclose( ff);
    close( f);
    
    e = pthread_mutex_unlock( &lock);
    if (e)
    {
        fprintf( stderr, "pthread_mutex_unlock() failed\\n");
    }
    return;
}

static void register_open( const char* path, int read, int write, int ret)
{
    int ret_errno = errno;
    
    /* we sometimes call getcwd(), which can recurse into open(), so we protect
    against being reentered. this is not exactly thread-safe... */
    
    static int  nesting = 0;
    ++nesting;
    
    if ( nesting>1)  goto end;
    
    char    read_c = (read) ? 'r' : '-';
    char    write_c = (write) ? 'w' : '-';
    
    if (path[0] == '/')
    {
        printf_log( "%i %c%c %s\\n", ret, read_c, write_c, path);
    }
    else
    {
        char cwd[ PATH_MAX];
        getcwd( cwd, sizeof(cwd));
        printf_log( "%i %c%c %s/%s\\n", ret, read_c, write_c, cwd, path);
    }
    
    end:
    --nesting;
    
    #ifdef USE_PTHREADS
        wrap( pthread_mutex_unlock( &global_lock));
    #endif
    errno = ret_errno;
    /* make sure error info is correct, even after we've called realpath()
    etc. */
}

static void register_rename( const char* from, const char* to)
{
    int ret_errno = errno;
    
    /* we sometimes call getcwd(), which can recurse into open(), so we protect
    against being reentered. this is not exactly thread-safe... */
    
    static int  nesting = 0;
    ++nesting;
    
    if ( nesting>1)  goto end;
    
    char cwd[ PATH_MAX];
    getcwd( cwd, sizeof(cwd));
    if (0)
    {
        fprintf( stderr, "cwd is: %s\\n", cwd);
        fprintf( stderr, "from=%s to=%s\\n", from, to);
    }
    // This won't work if paths containg spaces.
    //
    printf_log( "r %s%s%s %s%s%s\\n",
            from[0] == '/' ? "" : cwd,
            from[0] == '/' ? "" : "/",
            from,
            to[0] == '/' ? "" : cwd,
            to[0] == '/' ? "" : "/",
            to);
    
    end:
    --nesting;
    errno = ret_errno;
    /* make sure error info is correct, even after we've called realpath()
    etc. */
}

int
    open(
        const char* path,
        int         flags,
        mode_t      mode
        )
{
    if (debug) fprintf( stderr, "getpid()=%i: open: flags=0x%x mode=0x%x %s\\n", getpid(), flags, mode, path);
    int     ret;
    
    
    int accmode = flags & O_ACCMODE;
    int read = (accmode == O_RDONLY || accmode == O_RDWR);
    int write = (accmode == O_WRONLY || accmode == O_RDWR);
    
    ret = raw_open( path, flags, mode);
    if (debug) fprintf( stderr, "getpid()=%i: open: flags=0x%x r=%i w=%i mode=0x%x %s => %i\\n", getpid(), flags, read, write, mode, path, ret);
    
    register_open( path, read, write, ret);
    
    if (debug) fprintf( stderr, "open() returning %i\\n", ret);
    return ret;
}

int
    creat(const char *path, mode_t mode)
{
    if (debug) fprintf( stderr, "getpid()=%i: creat() called. path=%s mode=0x%x\\n", getpid(), path, mode);
    return open( path, O_CREAT|O_WRONLY|O_TRUNC, mode);
}

int
    openat(
        int         dirfd,
        const char* path,
        int         flags,
        mode_t      mode
        )
{
    if (debug) fprintf( stderr, "getpid()=%i: openat() called. dirfd=%i path=%s flags=0x%x mode=0x%x\\n",
            getpid(), dirfd, path, flags, mode);
    if (dirfd != AT_FDCWD)
    {
        fprintf( stderr, "Unable to handle openat() with dirfd\\n");
        return raw_openat( dirfd, path, flags, mode);
    }
    
    return open( path, flags, mode);
}

FILE* fopen( const char *path, const char *mode)
{
    if (debug) fprintf( stderr, "getpid()=%i: fopen path=%s mode=%s\\n", getpid(), path, mode);
    
    int read = 0;
    int write = 0;
    if (strchr( mode, 'r')) read = 1;
    if (strchr( mode, 'w')) write = 1;
    if (strchr( mode, 'a')) write = 1;
    if (strchr( mode, '+')) write = 1;
    
    FILE* ret = raw_fopen( path, mode);
    
    if (debug) fprintf( stderr, "getpid()=%i: fopen ret=%p\\n", getpid(), ret);
    
    register_open( path, read, write, (ret) ? 0 : -1);
    if (debug) fprintf( stderr, "getpid()=%i: fopen returning %p\\n", getpid(), ret);
    return ret;
}

FILE *freopen(const char *path, const char *mode, FILE *stream)
{
    if (debug) fprintf( stderr, "getpid()=%i: freopen path=%s mode=%s\\n", getpid(), path, mode);
    static FILE* (*real_freopen)(const char *path, const char *mode, FILE *stream) = NULL;
    if ( !real_freopen)
    {
        real_freopen = dlsym( RTLD_NEXT, "freopen");
    }
    FILE* ret = real_freopen( path, mode, stream);
    
    int read = 0;
    int write = 0;
    if (strchr( mode, 'r')) read = 1;
    if (strchr( mode, 'w')) write = 1;
    if (strchr( mode, 'a')) write = 1;
    if (strchr( mode, '+')) write = 1;
    
    register_open( path, read, write, (ret) ? 0 : -1);
    return ret;
}

int rename( const char* old, const char* new)
{
    if (debug) fprintf( stderr, "getpid()=%i: rename old=%s new=%s\\n", getpid(), old, new);
    static int (*real_rename)(const char*, const char*) = NULL;
    if (!real_rename)
    {
        real_rename = dlsym( RTLD_NEXT, "rename");
    }
    int ret = real_rename( old, new);
    if (!ret)
    {
        register_rename( old, new);
    }
    return ret;
}

int renameat2( int olddirfd, const char* old, int newdirfd, const char* new, unsigned flags)
{
    if (debug) fprintf( stderr, "getpid()=%i: renameat2 old=%i:%s new=%i:%s flags=0x%x\\n", getpid(), olddirfd, old, newdirfd, new, flags);
    
    static int (*real_renameat2)(int olddirfd, const char*, int, const char*, unsigned) = NULL;
    if (!real_renameat2)
    {
        real_renameat2 = dlsym( RTLD_NEXT, "renameat2");
    }
    
    int ret = real_renameat2( olddirfd, old, newdirfd, new, flags);
    
    if (olddirfd != AT_FDCWD || newdirfd != AT_FDCWD)
    {
        fprintf( stderr, "Unable to handle renameat2() with dirfd\\n");
    }
    else
    {
        if (!ret)
        {
            register_rename( old, new);
        }
    }
    return ret;
}

int renameat( int olddirfd, const char* old, int newdirfd, const char* new)
{
    if (debug) fprintf( stderr, "getpid()=%i: renameat old=%i:%s new=%i:%s\\n", getpid(), olddirfd, old, newdirfd, new);
    return renameat2( olddirfd, old, newdirfd, new, 0 /*flags*/);
}

int unlinkat( int dirfd, const char *path, int flags)
{
    if (debug) fprintf( stderr, "getpid()=%i: unlinkat pathame=%s flags=0x%x\\n", getpid(), path, flags);
    static int (*real_unlinkat)(int dirfd, const char *path, int flags) = NULL;
    if ( !real_unlinkat)
    {
        real_unlinkat = dlsym( RTLD_NEXT, "unlinkat");
    }
    int ret = real_unlinkat( dirfd, path, flags);
    
    if (ret >= 0)
    {
        if (path[0] == '/')
        {
            printf_log( "d %s\\n", path);
        }
        else
        {
            char    cwd[ PATH_MAX];
            getcwd( cwd, sizeof(cwd));
            printf_log( "d %s/%s\\n", cwd, path);
        }
    }
    
    if (debug) fprintf( stderr, "getpid()=%i: unlinkat returning ret=%i\\n", getpid(), ret);
    return ret;
}

int unlink( const char *path)
{
    if (debug) fprintf( stderr, "getpid()=%i: unlink pathame=%s\\n", getpid(), path);
    return unlinkat( AT_FDCWD, path, 0);
}
int remove( const char *path)
{
    if (debug) fprintf( stderr, "getpid()=%i: remove pathame=%s\\n", getpid(), path);
    return unlinkat( AT_FDCWD, path, 0 /*flags*/);
}

#ifdef __linux__
/*
Below are various attempts to intercept calls to Linux's open64() which ld appears to use to open the executable that it
generates. So far i've not been able to find a function name that catches this.

The backtrace for the actual syscall indicates that the following fns are involved:

    __libc_open64
    __GI__IO_file_open
    _IO_new_file_fopen
    __fopen_internal

The middle two take special args so it's not clear how to intercep them. Other
two seem straightforward, but including them in our preload library doesn't
work - they are not called.

Catchpoint 1 (call to syscall openat), 0x00007f7b8c7711ae in __libc_open64 (file=0x55a357e98700 "./walk_test_foo.exe", oflag=578) at ../sysdeps/unix/sysv/linux/open64.c:48
48      in ../sysdeps/unix/sysv/linux/open64.c
(gdb) bt
#0  0x00007f7b8c7711ae in __libc_open64 (file=0x55a357e98700 "./walk_test_foo.exe", oflag=578) at ../sysdeps/unix/sysv/linux/open64.c:48
#1  0x00007f7b8c702e52 in __GI__IO_file_open (fp=fp@entry=0x55a357e81d80, filename=<optimized out>, posix_mode=<optimized out>, prot=prot@entry=438, read_write=0, 
    is32not64=is32not64@entry=1) at fileops.c:189
#2  0x00007f7b8c702ffd in _IO_new_file_fopen (fp=fp@entry=0x55a357e81d80, filename=filename@entry=0x55a357e98700 "./walk_test_foo.exe", mode=<optimized out>, 
    mode@entry=0x7f7b8cb5a80d "w+", is32not64=is32not64@entry=1) at fileops.c:281
#3  0x00007f7b8c6f7159 in __fopen_internal (filename=0x55a357e98700 "./walk_test_foo.exe", mode=0x7f7b8cb5a80d "w+", is32=1) at iofopen.c:75
#4  0x00007f7b8cab41eb in ?? () from /usr/lib/x86_64-linux-gnu/libbfd-2.31.1-system.so
#5  0x00007f7b8cab4ab3 in bfd_open_file () from /usr/lib/x86_64-linux-gnu/libbfd-2.31.1-system.so
#6  0x00007f7b8cabd437 in bfd_openw () from /usr/lib/x86_64-linux-gnu/libbfd-2.31.1-system.so
#7  0x000055a35762e4a2 in ?? ()
#8  0x000055a35762bc00 in ?? ()
#9  0x000055a357631e70 in ?? ()
#10 0x000055a35762041a in ?? ()
#11 0x00007f7b8c6ab09b in __libc_start_main (main=0x55a35761fe10, argc=45, argv=0x7ffcb7d1f008, init=<optimized out>, fini=<optimized out>, rtld_fini=<optimized out>, 
    stack_end=0x7ffcb7d1eff8) at ../csu/libc-start.c:308
#12 0x000055a357620a9a in ?? ()
*/
int unlink_if_ordinary( const char* path)
{
    if (1) fprintf( stderr, "getpid()=%i: unlink_if_ordinary path=%s\\n", getpid(), path);
    static int (*real_unlink_if_ordinary)(const char* path) = NULL;
    if (!real_unlink_if_ordinary)
    {
        real_unlink_if_ordinary = dlsym( RTLD_NEXT, "unlink_if_ordinary");
    }
    if (1) fprintf( stderr, "real_unlink_if_ordinary=%p\\n", real_unlink_if_ordinary);
    int ret = real_unlink_if_ordinary( path);
    if (1) fprintf( stderr, "ret=%i\\n", ret);
    if (ret >= 0)
    {
        printf_log( "d %s\\n", path);
    }
    return ret;
}

FILE* __fopen_internal( const char* path, const char* mode, int is32)
{
    fprintf( stderr, "*************************** __fopen_internal: path=%s mode=%s is32=%i\\n", path, mode, is32);
    static FILE* (*real___fopen_internal)(const char* path, const char* mode, int is32) = NULL;
    if (!real___fopen_internal)
    {
        real___fopen_internal = dlsym( RTLD_NEXT, "__fopen_internal");
    }
    fprintf( stderr, "real___fopen_internal=%p\\n", real___fopen_internal);
    FILE* ret = real___fopen_internal( path, mode, is32);
    fprintf( stderr, "real___fopen_internal returning %p\\n", ret);
    return ret;
}

int __libc_open64( const char* path, int oflag)
{
    fprintf( stderr, "*** __libc_open64: path=%s oflag=0x%x\\n", path, oflag);
    static int (*real___libc_open64)( const char* path, int oflag) = NULL;
    if (!real___libc_open64)
    {
        real___libc_open64 = dlsym( RTLD_NEXT, "__libc_open64");
    }
    return real___libc_open64( path, oflag);
}

int open64( const char* path, int oflag)
{
    fprintf( stderr, "*** open64: path=%s oflag=0x%x\\n", path, oflag);
    static int (*real_open64)( const char* path, int oflag) = NULL;
    if (!real_open64)
    {
        real_open64 = dlsym( RTLD_NEXT, "open64");
    }
    return real_open64( path, oflag);
}
#endif
'''

def _process_preload( command, walk_path0, t_begin, t_end):
    '''
    Takes file created by preload library, and processes it into a walk file.

    The main thing we do is to handle sequences of calls where a file is opened
    for writing, but then renamed or deleted - in this case it's important to
    omit this file from the list of output files.
    '''
    walk = WalkFile( command, t_begin, t_end)
    
    with open( walk_path0) as f:
        lines = f.read().split('\n')
        path2line = dict()
        
        for i, line in enumerate(lines):
            #log( 'looking at line: %r' % line)
            if not line:
                continue
            if line.startswith( 'r'):
                # rename
                #log( 'rename: %r' % line)
                _, from_, to_ = line.split( ' ')
                walk.add_rename( from_, to_)
            elif line.startswith( 'd'):
                path = line[2:]
                walk.add_delete( path)
            else:
                # open
                sp = line.find( ' ')
                assert sp >= 0
                ret = int(line[:sp])
                r = line[ sp+1] == 'r'
                w = line[ sp+2] == 'w'
                p = line[ sp+4:]
                walk.add_open( ret, p, r, w)
    
    return walk

import threading
_make_preload_up_to_date = False
_make_preload_lock = threading.Lock()

def _make_preload( walk_file):
    '''
    Ensures our ldpreload library is up to date, and returns string to be used
    as a prefix for the command, setting LD_PRELOAD etc.
    '''
    global _make_preload_up_to_date
    
    path_c = '/tmp/walk_preload.c'
    path_lib = '/tmp/walk_preload.so'
    
    if not _make_preload_up_to_date:
        with _make_preload_lock:
            if not _make_preload_up_to_date:
                file_write( _preload_c, path_c)
                if mtime( path_c, 0) > mtime( path_lib, 0):
                    ldl = '-ldl' if _osname == 'Linux' else ''
                    command = 'gcc -g -W -Wall -shared -fPIC %s -o %s %s' % (
                            ldl,
                            path_lib,
                            path_c,
                            )
                    #log( 'building preload library with: %s' % command)
                    e = os.system( command)
                    assert not e, 'Failed to build preload library.'
                _make_preload_up_to_date = True
    
    return 'LD_PRELOAD=%s WALK_preload_out=%s' % (path_lib, walk_file)


def _do_tests(method=None):
    '''
    Runs some very simple tests.
    
    method:
        Passed directly to walk.system(), so controls whether we use preload or
        trace.
    '''
    with LogPrefixScope( f'test method={method}: '):
        log( 'Running tests...')

        build_c = 'walk_test_foo.c'
        build_h = 'walk_test_foo.h'
        build_exe = './walk_test_foo.exe'
        build_walkfile = f'{build_exe}.walk'

        w = 'walk_test_rename.walk'
        a = 'walk_test_rename_a'
        b = 'walk_test_rename_b'
        c = 'walk_test_rename_c'
        
        try:
            # Testing with compilation.
            #
            with LogPrefixScope( 'compilation: '):
            
                file_write( '''
                        #include "walk_test_foo.h"
                        int main(){ int x; return 0;}
                        '''
                        ,
                        build_c
                        )
                file_write( '''
                        '''
                        ,
                        build_h
                        )

                command = f'cc -W -Wall -o {build_exe} {build_c}'

                remove( build_exe)
                remove( build_walkfile)

                # Build executable.
                log( '== doing initial build')
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method)
                assert not e
                assert os.path.isfile( build_exe)
                assert not os.system( build_exe)
                assert os.path.isfile( build_walkfile)

                # Check rebuild does nothing.
                log( '== testing rebuild with no changes')
                t = mtime( build_exe)
                time.sleep(1)
                mtime_cache_clear()
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method)
                assert e is None
                t2 = mtime( build_exe)
                assert t2 == t, f'{date_time(t)} => {date_time(t2)}'

                # Check rebuild with updated header updates executable.
                log( '== testing rebuild with modified header')
                mtime_cache_clear()
                os.system( f'touch {build_h}')
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method)
                t2 = mtime( build_exe)
                assert e == 0
                assert t2 > t

            with LogPrefixScope( 'rename: '):
            
                # Check we correctly handle a command that reads from a, writes to b
                # and renames b to c. In this case, the command behaves as though it
                # reads from a and writes to b. It's a common idiom in tools so that
                # the creation of an output file is atomic.
                #
                log( '=== testing rename')
                w = 'walk_test_rename.walk'
                a = 'walk_test_rename_a'
                b = 'walk_test_rename_b'
                c = 'walk_test_rename_c'
                remove( w)
                remove( a)
                remove( b)
                mtime_cache_clear()
                os.system( f'touch {a}')
                # This command is implemented by this python script itself. It reads
                # from a, writes to b, then renames b to c.
                #
                command = f'{sys.argv[0]} --test-abc {a} {b} {c}'
                log( f'command is: {command}')

                log( '')
                log( '== running command for first time')
                mtime_cache_clear()
                e = os.system( f'touch {a}')
                e = system( command, w, verbose='derR', out_prefix='    ', method=method)
                #os.system( 'ls -lt|head')
                assert e == 0, f'e={e}'

                log( '')
                log( '== running command again')
                mtime_cache_clear()
                e = system( command, w, verbose='derR', out_prefix='    ', method=method)
                #os.system( 'ls -lt|head')
                assert e is None, f'e={e}'

                log( '')
                log( f'== running command after touching {a}')
                mtime_cache_clear()
                e = os.system( f'touch {a}')
                e = system( command, w, verbose='derR', out_prefix='    ', method=method)
                #os.system( 'ls -lt|head')
                assert e == 0, f'e={e}'

            log( 'tests passed')

        finally:
            if 1:
                remove( build_c)
                remove( build_h)
                remove( build_exe)
                remove( build_walkfile)
                remove( a)
                remove( b)
                remove( c)
    
    

class Args:
    '''
    Iterates over argv items. Does getopt-style splitting of args starting with
    single '-' character.
    '''
    def __init__( self, argv):
        self.argv = argv
        self.pos = 0
        self.pos_sub = None
    def next( self):
        while 1:
            if self.pos >= len(self.argv):
                self.pos += 1
                raise StopIteration()
            arg = self.argv[self.pos]
            if (not self.pos_sub
                    and arg.startswith('-')
                    and not arg.startswith('--')
                    ):
                # Start splitting current arg.
                self.pos_sub = 1
            if self.pos_sub and self.pos_sub >= len(arg):
                # End of '-' sub-arg.
                self.pos += 1
                self.pos_sub = None
                continue
            if self.pos_sub:
                # Return '-' sub-arg.
                ret = arg[self.pos_sub]
                self.pos_sub += 1
                return f'-{ret}'
            # Return normal arg.
            self.pos += 1
            return arg


def main():
    
    force = None
    verbose = None
    method = None
    global _mtime_cache
    args = Args( sys.argv[1:])
    
    while 1:
        try:
            arg = args.next()
        except StopIteration:
            break
        
        if not arg.startswith( '-'):
            break
            
        if 0:
            pass
        elif arg == '--new':
            path = args.next()
            mtime_cache_mark_new( path)
        elif arg == 'f':
            force = int(args.next)
        elif arg == '-h' or arg == '--help':
            sys.stdout.write( __doc__)
        elif arg == '-m':
            method = args.next()
        elif arg == '--test':
            _do_tests()
            if _osname == 'OpenBSD':
                _do_tests( method='trace')
        elif arg == '--test-abc':
            a = args.next()
            b = args.next()
            c = args.next()
            with open( a) as f:
                pass
            with open( b, 'w') as f:
                pass
            os.rename( b, c)
        elif arg == '--test-profile':
            walk_file = args.next()
            t0 = time.time()
            t1 = t0 + 2
            i = 0
            while 1:
                i += 1
                _analyse_walk_file( walk_file)
                t = time.time()
                if t > t1:
                    t -= t0
                    break
                mtime_cache_clear = dict()
            print( 'sec/it=%s' % (t/i))
        else:
            raise Exception( 'Unrecognised arg: %r' % arg)
            
    if args.pos < len( args.argv):
        walk_path = args.argv[ args.pos-1]
        command = ' '.join( args.argv[ args.pos:])
        e = system( command, walk_path, verbose, force, method=method)
        sys.exit(e)

if __name__ == '__main__':
    main()
