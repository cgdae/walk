#! /usr/bin/env python3

'''
Provides a mechanism for running external commands which avoids actually
running these commands if we can infer that they would not change any generated
files.

Copyright (C) 2020-2022 Julian Smith.

SPDX-License-Identifier: GPL-3.0-only
'''


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
        use_hash=True,
        ):
    '''
    Runs the specified command unless stored info from previous run implies
    that the command would not change output files.
    
    Returns:
        `None` if we did not run the command. Otherwise a subprocess-style
        integer termination status: zero or positive exit code, or negative
        signal number
    
    Args:
        command:
            The command to run.
        walk_path:
            Name of walk file; if it already exists it will contain information
            on the most recent invocation of the command. If we re-run the
            command, this file is updated.
        verbose:
            A string where the presence of particular characters controls what
            diagnostics are generated:

            * **c**     Show the command itself if we run the command.
            * **d**     Show command description if we run the command.
            * **e**     Show command if it failed and 'c' was not specified.
            * **m**     Show generic message if we are running the command.
            * **r**     Show the reason for running the command.

            Upper-case versions of the above cause the equivalent messages to
            be generated if we do *not* run the command.
        force:
            If `None` (the default), we run the command unless walk file and/or
            hash/mtimes indicate it will make no changes.

            Otherwise if true (e.g. `1` or `True`) we always run the command;
            if false (e.g. `0` or `False`) we never run the command.
        description:
            Text used by `verbose`'s **d** option. E.g. 'Compiling foo.c'.
        method:
            Must be `None`, 'preload' or 'trace'.

            If `None`, we use the default for the OS we are running on.

            If 'trace' we use Linux strace or OpenBSD ktrace to find what file
            operations the command used.

            If 'preload' we include our own code using LD_PRELOAD which
            intercepts calls to `open()` etc.
        command_compare:
            If not `None`, should be callable taking two string commands,
            returning non-zero if these commands differ significantly.

            For example for gcc-style compilation commands one could specify a
            function that ignores differences in `-W*` args; this will avoid
            unnecessary recompilation caused by changes only to warning flags.
        out:
            Where the command's stdout and stderr go:
                `None`:
                    If both `out_prefix` and `out_buffer` are false, the
                    command's output goes directly to the inherited
                    stdout/stderr. Otherwise it is sent (via a pipe) to our
                    stdout.

                A callable taking a single `text` param.

                An object with `.write()` method taking a single `text` param.

                An integer >= 0, used with `os.write()`.

                A subprocess module special value (should not be
                `subprocess.PIPE`) such as `subprocess.DEVNULL`: passed
                directly to `subprocess.Popen()`.
        out_prefix:
            If not `None`, prepended to each line sent to `out`.
        out_buffer:
            If true, we buffer up output and send to `out` in one call after
            command has terminated. Otherwise if false (the default) typically
            `out` will be called multiple times.
        use_hash:
            If true (the default) we use md5 hashes to detect whether files have
            changed. Otherwise if false we use file mtimes.
    '''
    doit, reason = _system_check(
            walk_path,
            command,
            command_compare,
            force,
            use_hash,
            )
    
    return _system_doit(
            doit,
            reason,
            command,
            walk_path,
            verbose,
            description,
            command_compare,
            method,
            out,
            out_prefix,
            out_buffer,
            )


class CommandFailed( Exception):
    '''
    Exception for a failed command.
    '''
    def __init__( self, wait_status, text=None):
        self.wait_status = wait_status
        self.text = text
    def __str__( self):
        return f'wait_status={self.wait_status}: {self.text!r}'

    
class Concurrent:
    '''
    Support for running commands concurrently.
    
    Usage:
        Instead of calling `walk.system()`, create a `walk.Concurrent` instance
        and use its `.system()` or `.system_r()` methods.

        To wait until all scheduled tasks have completed, call `.join()`.

        Then to close down the internal threads, call `.end()`.
        
    `self.num_commands` is number of times `.system()` was called.

    `self.num_commands_run` is number of times that `.system()` actually ran
    the specified command.
    '''
    def __init__( self, num_threads, keep_going=False, max_load_average=None, use_hash=True):
        '''
        num_threads:
            Number of threads to run. (If zero, our `.system()` methods simply
            calls `walk.system()` directly.)
        keep_going:
            If false (the default) we raise exception from `.system()` and
            `.join()` if a previous command has failed. Otherwise new commands
            will be scheduled regardless.
        max_load_average:
            If not `None`, threads do not start new commands if current load
            average is above this value.
        use_hash:
            Used when we check commands scheduled by calls to `.system()` and
            `.system_r()`.
            
        Errors from scheduled commands can be retreived using `.get_errors()`.
        '''
        self.num_threads = num_threads
        self.keep_going = keep_going
        self.max_load_average = max_load_average
        self.use_hash = use_hash
        
        self.num_commands = 0
        self.num_commands_run = 0
        
        self.queue = queue.Queue()
        self.errors = queue.Queue()
        
        # self.errors contains a list of errors from commands run by our
        # threads. It is mainly used as a boolean indication that one or more
        # commands have failed - our threads stop work if self.errors is not
        # empty, and our .system*() and .join() methods similarly raise an
        # exception if self.errors is not empty.
        self.threads = []
        
        # Start our threads.
        for i in range( self.num_threads):
            thread = threading.Thread( target=self._thread_fn, daemon=True)
            self.threads.append( thread)
            thread.start()
    
    def _thread_fn( self):
        while 1:
            item = self.queue.get()
            
            if item is None:
                # This is self.end() telling us to exit.
                self.queue.task_done()
                return
                
            if not self.keep_going and not self.errors.empty():
                # Error has occurred, so don't process any more tasks.
                self.queue.task_done()
                continue
            
            if self.max_load_average is not None:
                # Block while load average is high.
                it = 0
                while 1:
                    current_load_average = os.getloadavg()[0]
                    if current_load_average < self.max_load_average:
                        break
                    if it % 5 == 0:
                        log( f'[Waiting for load_average={current_load_average:.1f} to reduce below {self.max_load_average:.1f}...]')
                    time.sleep(1)
                    it += 1
            
            # <item> is a command for us to run.
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
            if isinstance(force, tuple):
                # This item was queued by Concurrent.system_r(), which has
                # already called _system_check() on the main thread.
                doit, reason = force
            else:
                # This item was queued by Concurrent.system().
                doit, reason = _system_check(
                        walk_path,
                        command,
                        command_compare,
                        force,
                        self.use_hash,
                        )
            
            e = _system_doit(
                    doit,
                    reason,
                    command,
                    walk_path,
                    verbose,
                    description,
                    command_compare,
                    None,   # method
                    out,
                    out_prefix,
                    out_buffer,
                    )
            if e is not None:
                self.num_commands_run += 1
            if e:
                #log( f'*** appending error e={e} walk_path={walk_path}')
                self.errors.put( (command, walk_path, e))
            self.queue.task_done()
        
    def _raise_if_errors( self):
        '''
        Raises exception if self.keep_going is false and self.errors is not empty.
        '''
        if self.keep_going:
            #log( f'*** keep_going is true. self.errors.empty()={self.errors.empty()}')
            return
        if not self.errors.empty():
            #log( f'raising exception')
            raise Exception( 'task(s) failed')
    
    def system_r( self,
            command,
            walk_path,
            verbose=None,
            force=None,
            description=None,
            command_compare=None,
            out=None,
            out_prefix='',
            out_buffer=None,
            ):
        '''
        Like `.system()` but calls `_system_check()` on the current thread
        before queueing the item, allowing us to return information on whether
        the command is to be run.
        
        Returns `(doit, reason, e)` where `e` is `None` if `self.num_threads`
        is non-zero.
        
        If `self.num_threads` is zero, we run the command immediately and `e`
        is the termination status as with `walk.system()`.
        '''
        self.num_commands += 1
        self._raise_if_errors()
        doit, reason = _system_check(
                walk_path,
                command,
                command_compare,
                force=force,
                use_hash=self.use_hash,
                )
        #log( f'_system_check() returned doit={doit} walk_path={walk_path}')
        if doit and self.num_threads:
            self.queue.put(
                (
                    command,
                    walk_path,
                    verbose,
                    (doit, reason),
                    description,
                    command_compare,
                    out,
                    out_prefix,
                    out_buffer,
                )
                )
            return doit, reason, None
        else:
            # If doit is false this will output diagnostics.
            e = _system_doit(
                    doit,
                    reason,
                    command,
                    walk_path,
                    verbose,
                    description,
                    command_compare,
                    out=out,
                    out_prefix=out_prefix,
                    out_buffer=out_buffer,
                    )
            return doit, reason, e
            
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
        Schedule a command to be run. This will call `walk.system()` on one of
        our internal threads.
        
        Will raise an exception if an earlier command failed (unless we were
        constructed with `keep_going=true`).
        '''
        self._raise_if_errors()
        
        self.num_commands += 1
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
                    use_hash=self.use_hash,
                    )
            if e:
                self.errors.put( (command, walk_path, e))
            if e is not None:
                self.num_commands_run += 1
    
    def join( self):
        '''
        Waits until all current tasks have finished.
        
        Will raise an exception if an earlier command failed (unless we were
        constructed with `keep_going=true`).
        '''
        self._raise_if_errors()
        self.queue.join()
        self._raise_if_errors()
    
    def get_errors( self):
        '''
        Returns list of errors from completed tasks. Must only be called after
        `.join()`.

        These errors will not be returned again by later calls to
        `.get_errors()`.

        Each returned error is `(command, walk_path, e)`.
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

_log_prefix = ''
_log_last_t = 0

def log_prefix_set( prefix):
    '''
    prefix:
        A string or a callable returning a string.
    '''
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

def log( text):
    global _log_last_t
    out = sys.stdout
    if text.endswith( '\n'):
        text = text[:-1]
    prefix = _log_prefix() if callable(_log_prefix) else _log_prefix
    for line in text.split( '\n'):
        out.write( f'{prefix}{line}\n')
    out.flush()
    _log_last_t = time.time()

def log_ping( text, interval):
    '''
    Outputs `text` with `walk.log()` if it is more than `interval` seconds
    since `walk.log()` was last called.
    '''
    t = time.time()
    if t - _log_last_t > interval:
        log( text)


def mtime( path, default=None):
    '''
    Returns mtime of file, or `default` if error - e.g. doesn't
    exist. Caches previously-returned information, so it's important to
    call `_mtime_cache_clear()` if a file is updated in between calls to
    `walk.mtime()`.
    '''
    global _mtime_cache
    t = _mtime_cache.get( path, -1)
    if t == -1:
        # Not in cache.
        try:
            t = os.path.getmtime( path)
        except Exception:
            t = default
        _mtime_cache[ path] = t
    return t


def mtime_cache_mark_new( path):
    path = os.path.abspath( path)
    _mtime_cache[ path] = _mtime_new
    _force_new_files.add( path)


def mtime_cache_mark_old( path):
    path = os.path.abspath( path)
    _mtime_cache[ path] = 0


def get_verbose( v):
    '''
    Returns `v` or default verbose settings if `v` is `None`.
    '''
    if v is None:
        return 'de'
    return v


def file_write( text, path, verbose=None, force=None):
    '''
    If file `path` exists and contents are already `text`, does
    nothing. Otherwise writes `text` to file `path`.

    Will raise an exception if something goes wrong.

    `verbose` and `force` are as in walk.system().
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
        if 'd' in verbose:
            if doit:
                message += f' Updating {path}'
            else:
                message += f' Forcing update of {path}'
        if message:
            log( message.strip())
        
        path_temp = f'{path}-walk-temp'
        _ensure_parent_dir( path)
        with open( path_temp, 'w') as f:
            f.write( text)
        os.rename( path_temp, path)
    
    else:
        message = ''
        if 'D' in verbose:
            if doit:
                message += f' Forcing no update of {path}'
            else:
                message += f' Not updating {path}'
        if message:
            log( message.strip())


#
# Everything below here is internal implementation details, and not for
# external use.
#

import codecs
import hashlib
import io
import os
import pickle
import queue
import re
import subprocess
import sys
import textwrap
import threading
import time


_force_new_files = set()
_mtime_new = 3600*24*365*10*1000
_mtime_cache = dict()
_file_hash_cache = dict()
_osname = os.uname()[0]
_linux = ( _osname == 'Linux')
_openbsd = ( _osname == 'OpenBSD')


def _file_hash(path):
    '''
    Returns hash digest of <path> or -1 if it does not exist.
    '''
    global _file_hash_cache
    ret = _file_hash_cache.get(path)
    if ret is None:
        try:
            with open(path, 'rb') as f:
                contents = f.read()
            ret = hashlib.md5(contents).digest()
        except:
            ret = -1
            # Must be true so we can reuse as 'open for reading' flag, but !=
            # True.
        _file_hash_cache[path] = ret
    return ret


def _mtime_cache_clear( path=None):
    global _mtime_cache
    global _file_hash_cache
    if path:
        _mtime_cache.pop( path, None)
        _file_hash_cache.pop( path, None)
    else:
        _mtime_cache = dict()
        _file_hash_cache = dict()


def _remove( filename):
    '''
    Removes file without error if we fail or it doesn't exist.
    '''
    try:
        os.remove( filename)
    except Exception:
        pass


def _ensure_parent_dir( path):
    parent = os.path.dirname( path)
    if parent:
        os.makedirs( parent, exist_ok=True)


def _date_time( t=None):
    '''
    Returns `t` in the form YYYY-MM-DD-HH:MM:SS. If `t` is `None`, we use
    current date and time.
    '''
    if t is None:
        t = time.time()
    return time.strftime( "%F-%T", time.gmtime( t))


def _make_diagnostic( verbose, command, description, reason, doit):
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
    doit:
        If false, we are not running the command and we reverse the case of
        <verbose> when checking for flags.
    '''
    if isinstance( reason, list) and len( reason) == 1 and reason[0]:
        reason = reason[0]
    notrun_text = ''
    if not doit:
        verbose = verbose.swapcase()
        notrun_text = ' not'
    
    message_tail = ''
    if 'd' in verbose and description:
        # Show description of command.
        if 'c' in verbose:
            message_tail += f'({description})'
        else:
            message_tail += description
    if 'c' in verbose:
        # Show the command itself.
        if message_tail:
            message_tail += ': '
        message_tail += command

    message_head = ''
    if 'r' in verbose:
        # Show reason for running the command.
        if not message_head:
            if doit:
                message_head += 'running command'
            else:
                message_head += f'{notrun_text} running command' 
        if reason:
            message_head += f' because {reason}'
    if 'm' in verbose and not message_head:
        # Show generic message.
        message_head += f'{notrun_text_initial} running command'
    message_head = message_head.strip()
    if message_head:
        message_head = message_head[0].upper() + message_head[1:]

    message = message_head
    if message_tail:
        if message:
            message += ': '
        message += message_tail
    
    if 0:
        log( f'verbose={verbose} command={command!r} description={description!r} reason={reason!r} doit={doit}: returning: {message!r}')
    return message


def _system(
        command,
        out=None,
        capture=False,
        throw=True,
        encoding='utf-8',
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
                `None`:
                    If both `out_prefix` and `out_buffer` are false,
                    the command's output goes to the inherited
                    stdout/stderr. Otherwise it is sent to our stdout.
                
                A callable taking single `text` param.
                
                Object with `.write()` method taking single `text` param.
                
                Integer >= 0, a file descriptor.
                
                Other subprocess module special value (should not be
                `subprocess.PIPE`): passed directly to `subprocess.Popen()`.
        capture:
            If true, we also capture the output text and include it in the
            returned information.
        throw:
            If true, we raise a `CommandFailed` exception if command failed.
        encoding:
            The encoding to use when decoding child output. Ignored if false.
        encoding_errors:
            The codecs module's 'errors' param if `encoding` is specified.
        out_prefix:
            If not `None`, prepended to each line sent to `out`. Not included
            in output returned if `capture` is true.
        out_buffer:
            If true, we buffer up output and send to `out` in one call after
            command has terminated.
    Returns:
        Returned value depends on `out_capture` and `throw`:
        
        capture throw   Return
        ---------------------------
        false   false   wait_status
        false   true    None or raise CommandFailed instance.
        true    false   (wait_status, out_text)
        true    true    out_text or raise CommandFailed instance.

    >>> _system( 'echo hello world; false', out=subprocess.DEVNULL, capture=False, throw=False)
    1
    >>> _system( 'echo hello world; false', out=subprocess.DEVNULL, capture=False, throw=True)
    Traceback (most recent call last):
    CommandFailed: wait_status=1: None
    >>> _system( 'echo hello world; false', out=subprocess.DEVNULL, capture=True, throw=False)
    (1, 'hello world\\n')
    >>> _system( 'echo hello world; false', out=subprocess.DEVNULL, capture=True, throw=True)
    Traceback (most recent call last):
    CommandFailed: wait_status=1: 'hello world\\n'
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
                if outfn:
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
        if outfn:
            outfn( t)
    
    if wait_status and throw:
        raise CommandFailed( wait_status, text)
    if capture:
        return wait_status, text
    return wait_status


def _time_load_all( root):
    '''
    Timing test. Processes all .walk files within <root> and outputs timing
    information.
    '''
    t = time.time()
    i = 0
    for it in range(1):
        for dirpath, dirnames, filenames in os.walk( root):
            for filename in filenames:
                if filename.endswith( '.walk'):
                    path = os.path.join( dirpath, filename)
                    i += 1
                    if i % 100 == 0:
                        log( f'i={i} {path}')
                    _system_check(
                            path, None,
                            lambda command1,
                            command2: 0,
                            use_hash,
                            )
    t = time.time() - t
    log( f't={t} i={i}')


def _system_check( walk_path, command, command_compare=None, force=None, use_hash=True):
    '''
    Looks at information about previously opened files and decides whether we
    can avoid running the specified command. This is run every time the user
    calls walk.system() so is fairly time-critical.

    walk_path:
        Path of the walk-file containing information about what files the
        command read/wrote when it was run before.
    command:
        The command to be run.
    command_compare:
        As in `walk.system()`.
        If not None, should be callable taking two string commands which
        returns non-zero if these commands differ significantly. For example
        for gcc commands this could ignore any differences in -W* args to avoid
        unnecessary recompilation caused by changes only to warning flags.
    use_hash:
        If true, we look at md5 of files instead of mtime.

    Returns (doit, reason):
        doit:
            True iff command should be run again.
        reason:
            Text description of why <doit> is set to true/false.
    '''
    if force is not None:
        if force:
            return True, 'Force running of command'
        else:
            return False, 'Force not running of command'
    
    reason = []
    verbose = 0
    
    try:
        f = open( walk_path, 'rb')
    except Exception as e:
        doit = True
        reason.append( f'No previous build')
        return doit, reason
    
    with f:
        try:
            w = pickle.load( f)
        except Exception as e:
            import shutil
            shutil.copy2( walk_path, '{walk_path}-bad')
            doit = True
            reason.append( f'Previous build interrupted f={f}: {e}')
            return doit, reason
    if w is None or isinstance(w, int):
        r = 'Previous build failed'
        if not w is None:
            r += f' ({w})'
        reason.append( r)
        doit = True
        return doit, reason
        
    if command_compare:
        diff = command_compare( w.command, command)
    else:
        diff = (command != w.command)
    if diff:
        if 0 or verbose:
            log( 'command has changed:')
            log( f'    from {w.command}')
            log( f'    to   {command}')
        return True, 'command has changed'

    # If use_hash is false, we want to find oldest file that was opened for
    # writing by previous invocation of this command, and the newest file that
    # was opened for reading. If the current mtime of the newest read file is
    # older than the current mtime of the oldest written file, then we don't
    # need to run the command again.
    #

    oldest_write = None
    oldest_write_path = None
    newest_read = None
    newest_read_path = None
    
    read_hash_changed_path = None
    read_hash_changed_mtime = 0
    
    command_old = None
    t_begin = None
    t_end = None

    num_lines = 0

    use_mtime = False
    
    for path, (ret, read_or_hash, write) in w.path2info.items():
        num_lines += 1
        if verbose:
            log(f'ret={ret} read_or_hash={read_or_hash} write={write}: {path}')
        
        # Previous invocation of command opened <path>, so we need to look at
        # its hash/mtime and update newest_read or oldest_write accordingly.

        # Just comparing with /home makes a surprisingly large difference
        # to the nothing-to-do case. E.g. for Flightgear it reduces time
        # from 10.5s to 5.8s.
        #
        # Most of this seems to come with not looking at files in /usr/
        #
        if 0:
            # E.g. 6.8s for null build.
            if not path.startswith( '/home/'):
                continue
        else:
            # E.g. 7.0s for null build. 10.5s if we don't check for /usr/.
            if path.startswith( '/tmp/'):
                continue

            if path.startswith( '/usr/'):
                continue

            if path.startswith( '/sys/'):
                # E.g. gcc seems to read /sys/devices/system/cpu/online,
                # which can have new mtime and thus cause spurious reruns
                # of command.
                continue

            # This gives a modest improvement in speed.
            #if path.startswith( '/usr/'):
            #    continue

            if _openbsd and path == '/var/run/ld.so.hints':
                # This is always new, so messes things up unless we ignore it.
                continue

            if _linux and path.startswith( '/etc/ld.so'):
                # This is sometimes updated (maybe after apt install?), so
                # messes things up unless we ignore it.
                continue

        # mtime() can be slow so we only call it if we need to. If we have
        # called it, we put the result into <t>.
        t = -1

        #if 0 and path.startswith( os.getcwd()):
        if verbose:
            log( f't={_date_time(t)} ret={ret} read_or_hash={read_or_hash} write={write} path: {path}')

        if read_or_hash and not write and ret < 0:
            # Open for reading failed last time.
            if t == -1:
                t = mtime( path)
            if t:
                # File exists, so it might open successfully this time,
                # so pretend it is new.
                #
                if 0: log( f'forcing walk_path t={_date_time( mtime( walk_path))} walk_path={walk_path} path={path}')
                newest_read = time.time()
                newest_read_path = path
        if read_or_hash and ret >= 0:
            # Open for reading succeeded last time.
            if verbose:
                log(f'opened for reading succeeded last time: {path}')
            if use_hash and (isinstance(read_or_hash, bytes) or read_or_hash == -1):
                # read_or_hash is hash digest.
                hash_ = _file_hash(path)
                #log(f'path={path}')
                #log(f'    read_or_hash: {read_or_hash}')
                #log(f'    hash_:     {hash_}')
                if hash_ != read_or_hash or path in _force_new_files:
                    #log(f'hash has changed: {path}')
                    # Keep track of newest modified input file to include in
                    # diagnostics.
                    #if read_or_hash == -1:
                    #    log(f'No previous has for: {path}')
                    if t == -1:
                        t = mtime( path)
                    if t and t > read_hash_changed_mtime:
                        read_hash_changed_mtime = t
                        read_hash_changed_path = path
            else:
                # hash info not available - presumably an old .walk file.
                use_mtime = True
            
            # Currently we always look at mtime even if we also use hash, but
            # this could be 'if not use_hash: ...', as long as we update
            # earlier hash code to force rebuild if file no longer exists.
            if 1:
                #log(f'read_or_hash not hash: {read_or_hash}')
                if t == -1:
                    t = mtime( path)
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
            if t == -1:
                t = mtime( path)
            if t:
                if oldest_write == None or t < oldest_write:
                    oldest_write = t
                    oldest_write_path = path
            else:
                # File has been removed.
                oldest_write = 0
                oldest_write_path = path

    #log( f'oldest_write: {_date_time(oldest_write)} {oldest_write_path}')
    #log( f'newest_read:  {_date_time(newest_read)} {newest_read_path}')

    # Note that don't run command if newest read and oldest write have the
    # same mtimes, just in case they are the same file.
    #
    doit = False
    if num_lines == 0:
        doit = True
        reason.append( 'Previous build failed or interrupted')
    elif newest_read is None:
        doit = True
        reason.append( 'No input files found')
    elif oldest_write is None:
        doit = True
        reason.append( 'No output files found')
    elif read_hash_changed_path:
        doit = True
        reason.append( f'hash changed: {os.path.relpath(read_hash_changed_path)}')
    elif oldest_write == 0:
        doit = True
        reason.append( f'Output file not present: {oldest_write_path}')
    elif newest_read > oldest_write:
        if use_hash and not use_mtime:
            # If we get here, no hash changed was detected, so we will not be
            # rebuilding, but we would have rebuilt if relying on mtimes.
            reason.append( f'hash unchanged: {newest_read_path}')
            #log(f'Ignoring newer input because hash unchanged: {newest_read_path}')
        else:
            doit = True
            reason.append( f'Input is newer: {os.path.relpath( newest_read_path)!r}')
    else:
        doit = False
        if newest_read_path:
            reason.append( f'Newest input {os.path.relpath( newest_read_path)!r} not newer then oldest output {os.path.relpath( oldest_write_path)!r}')
        else:
            reason.append( 'No input hash has changed')

    reason = ', '.join( reason)

    if verbose:
        log( f'returning {doit} {reason}')
    return doit, reason


def _system_doit(
        doit,
        reason,
        command,
        walk_path,
        verbose=None,
        description=None,
        command_compare=None,
        method=None,
        out=None,
        out_prefix='',
        out_buffer=False,
        ):
    '''
    Runs command if <doit> is true.
    
    May output diagnostics whether or not <doit> is true, depending on
    <verbose>.
    
    Returns as walk.system().
    
    Args:
        doit:
            If true, we run the command.
        reason:
            Used in diagnostics.
        ...
            Other args are same as in walk.system().
    '''
    verbose = get_verbose( verbose)
    
    if not doit:
        message = _make_diagnostic( verbose, command, description, reason, doit)
        if message:
            log( message)
        return
    
    if method is None:
        if _linux:
            # 'preload' doesn't work yet - seems like we don't intercept
            # whatever function it is that gcc uses to open the output
            # executable when linking.
            #
            method = 'trace'
        elif _openbsd:
            # Both 'trace' and 'preload' currently appear to work, but 'trace'
            # hasn't been tested that much so the default is 'preload'.
            #
            method = 'preload'
        else:
            assert 0
    
    # We always write None to .walk file before running the command,
    # which can be used to detect when a command did not complete (e.g.
    # because we were killed.
    #
    # This allows our diagnostics to differentiate between running a
    # command because it has never been run before (no .walk file) and
    # runnng a command because previous invocation did not complete
    # or failed (.walk file contains None).
    #
    _ensure_parent_dir( walk_path)
    with open( walk_path, 'wb') as f:
        pickle.dump( None, f)

    strace_path = walk_path + '-1'
    _remove( strace_path)

    if method == 'preload':
        command2 = f'{_make_preload( strace_path)} {command}'
        #log( f'command2 is: {command2}')
    elif method == 'trace':
        if _linux:
            command2 = ('strace'
                    + ' -f'
                    + ' -o ' + strace_path
                    + ' -q'
                    + ' -qq'
                    + ' -e trace=%file'
                    + ' ' + command
                    )
        elif _openbsd:
            command2 = f'ktrace -i -f {strace_path} -t cn {command}'
        else:
            assert 0
    else:
        assert 0

    message = _make_diagnostic( verbose, command, description, reason, doit=True)
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
            log( f'Command failed: {command}')
        # Write error code to .walk file so next time we know the command
        # failed.
        with open( walk_path, 'wb') as f:
            pickle.dump( e, f)

    else:
        # Command has succeeded so create the .walk file so that future
        # invocations know whether the command should be run again.
        #
        if method == 'preload':
            walk = _process_preload( command, strace_path, t_begin, t_end)
        elif method == 'trace':
            walk = _process_trace( command, strace_path, t_begin, t_end)
        else:
            assert 0
        walk.write( walk_path)

    _remove( strace_path)
    
    return e


class _WalkFile:
    '''
    Creates a walk file; used by code that parses strace or preload output.
    '''
    def __init__( self, command, t_begin, t_end, verbose=False):
        self.command = command
        self.t_begin = t_begin
        self.t_end = t_end
        self.path2info = dict()
        self.verbose = verbose
    
    def add_open( self, ret, path, r, w):
        '''
        Add an attempt to open a file.
        '''
        if self.verbose:
            print( f'open: ret={ret} r={r} w={w} path={path}')
        path = os.path.abspath( path)
        _mtime_cache_clear( path)
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
        '''
        Add deletion of a file.
        '''
        if self.verbose:
            print( f'delete: path={path}')
        path = os.path.abspath( path)
        _mtime_cache_clear( path)
        self.path2info.pop( path, None)
    
    def add_rename( self, path_from, path_to):
        '''
        Add a rename.
        '''
        if self.verbose:
            print( f'rename: path_from={path_from} path_to={path_to}')
        path_from = os.path.abspath( path_from)
        path_to = os.path.abspath( path_to)
        _mtime_cache_clear( path_from)
        _mtime_cache_clear( path_to)
        if 0: log( f'rename: {path_from} => {path_to}')
        prev = self.path2info.get( path_from)
        ok = False
        if prev:
            prev_ret, prev_r, prev_w = prev
            if prev_w:
                ok = True
                del self.path2info[ path_from]
                self.path2info[ path_to] = prev_ret, prev_r, prev_w
                if 0: log( f'rename {path_from} =>{path_to}. have set {path_to} to ret={prev_ret} r={prev_r} w={prev_w}')
        if not ok:
            # Not much we can do here. maybe mark the command as always run?
            self.path2info.pop( path_from, None)
            self.path2info.pop( path_to, None)
    
    def write( self, walk_path):
        '''
        Write all added items to pickle file.
        '''
        walk_path_ = walk_path + '-'
        # Find md5 of input files.
        for path, (ret, r, w) in self.path2info.items():
            if r:
                hash_ = _file_hash(path)
                self.path2info[path] = (ret, hash_, w)
        with open( walk_path_, 'wb') as f:
            pickle.dump( self, f)
        os.rename( walk_path_, walk_path)
        

def _process_trace( command, strace_path, t_begin, t_end):
    '''
    Analyses info in strace (or ktrace on OpenBSD) output file <strace_path>,
    and returns a _WalkFile.
    '''
    walk = _WalkFile( command, t_begin, t_end)
    
    if _linux:
        with open( strace_path) as f:
            for line in f:
                #log( f'line is: {line!r}')
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
                        log( f'syscall={syscall} ret=%{ret}. write={write}: {path}')
                    walk.add_open( ret, path, read, write)
                    continue
                
                m = re.match( '^[0-9]+ +rename[(]"([^"]*)", "([^"]*)"[)] = ([0-9A-Z-]+).*\n$', line)
                if m:
                   # log( f'found rename: {line!r}')
                    ret = int( m.group(3))
                    if ret == 0:
                        from_ = m.group(1)
                        to_ = m.group(2)
                        walk.add_rename( from_, to_)
                
    elif _openbsd:
        # Not sure how reliable this is. The output from kdump seems to have
        # two lines per syscall, with NAMI lines in-between, but sometimes
        # other syscall lines can appear inbetween too, which could maybe cause
        # our simple parser some problems?
        #
        # [Luckily the preload library approach seems to work on OpenBSD.]
        #
        strace_path2 = strace_path + '-'
        e = os.system( f'kdump -n -f {strace_path} >{strace_path2}')
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
                        m = re.match( f'^ *[0-9]+ +[^ ]+ +RET +{syscall} ([x0-9-]+)', line)
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
    '''
    walk = _WalkFile( command, t_begin, t_end)
    
    with open( walk_path0) as f:
        lines = f.read().split('\n')
        path2line = dict()
        
        for i, line in enumerate(lines):
            #log( f'looking at line: {line!r}')
            if not line:
                continue
            if line.startswith( 'r'):
                # rename
                #log( f'rename: {line!r}')
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


_make_preload_up_to_date = False
_make_preload_lock = threading.Lock()

def _make_preload( walk_file):
    '''
    Ensures our ldpreload library in /tmp is up to date, and returns string to
    be used as a prefix for the command, setting LD_PRELOAD etc.
    '''
    global _make_preload_up_to_date
    
    path_c = '/tmp/walk_preload.c'
    path_lib = '/tmp/walk_preload.so'
    
    if not _make_preload_up_to_date:
        with _make_preload_lock:
            if not _make_preload_up_to_date:
                file_write( _preload_c, path_c)
                if mtime( path_c, 0) > mtime( path_lib, 0):
                    ldl = '-ldl' if _linux else ''
                    command = f'cc -g -W -Wall -shared -fPIC {ldl} -o {path_lib} {path_c}'
                    #log( f'building preload library with: {command}')
                    e = os.system( command)
                    assert not e, 'Failed to build preload library.'
                _make_preload_up_to_date = True
    
    return f'LD_PRELOAD={path_lib} WALK_preload_out={walk_file}'


def _do_test( use_hash, method):
    '''
    Runs some tests.
    
    use_hash:
        Passed directly to walk.system().
    method:
        Passed directly to walk.system(), so controls whether we use preload or
        trace.
    '''
    with LogPrefixScope( f'test method={method} use_hash={use_hash}: '):
        log( 'Running tests...')

        build_c = 'walk_test_foo.c'
        build_h = 'walk_test_foo.h'
        build_exe = './walk_test_foo.exe'
        build_walkfile = f'{build_exe}.walk'

        rename_w = 'walk_test_rename.walk'
        rename_a = 'walk_test_rename_a'
        rename_b = 'walk_test_rename_b'
        rename_c = 'walk_test_rename_c'
        
        t = time.time()
        try:
            # Testing with compilation.
            #
            with LogPrefixScope( 'compilation: '):
                file_write( '''
                        #include "walk_test_foo.h"
                        int main(){ return 0;}
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

                _remove( build_exe)
                _remove( build_walkfile)

                # Build executable.
                log( '== doing initial build')
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method, use_hash=use_hash)
                assert not e
                assert os.path.isfile( build_exe)
                assert not os.system( build_exe)
                assert os.path.isfile( build_walkfile)

                log( '== testing rebuild with no changes')
                t = mtime( build_exe)
                time.sleep(1)
                _mtime_cache_clear()
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method, use_hash=use_hash)
                assert e is None
                t2 = mtime( build_exe)
                assert t2 == t, f'{_date_time(t)} => {_date_time(t2)}'

                log( '== testing rebuild with modified header')
                _mtime_cache_clear()
                os.system( f'touch {build_h}')
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method, use_hash=use_hash)
                t2 = mtime( build_exe)
                if use_hash:
                    assert e is None
                    assert t2 == t
                else:
                    assert e == 0
                    assert t2 > t

                log( '== testing rebuild with modified header')
                _mtime_cache_clear()
                os.system( f'echo >> {build_h}')
                e = system( command, build_walkfile, verbose='cderR', out=log, out_prefix='    ', method=method, use_hash=use_hash)
                t2 = mtime( build_exe)
                assert e == 0
                assert t2 > t

                log( '')
                log( f'== running command after removing {build_exe}')
                _mtime_cache_clear()
                os.system(f'rm {build_exe}')
                e = system( command, build_walkfile, verbose='derR', out_prefix='    ', method=method, use_hash=use_hash)
                assert e == 0, f'e={e}'

            with LogPrefixScope( 'rename: '):
            
                # Check we correctly handle a command that reads from a, writes to b
                # and renames b to c. In this case, the command behaves as though it
                # reads from a and writes to b. It's a common idiom in tools so that
                # the creation of an output file is atomic.
                #
                log( '=== testing rename')
                t = time.time()
                _remove( rename_w)
                _remove( rename_a)
                _remove( rename_b)
                _mtime_cache_clear()
                os.system( f'touch {rename_a}')
                # This command is implemented by this python script itself. It reads
                # from rename_a, writes to rename_b, then renames rename_b to rename_c.
                #
                command = f'{sys.argv[0]} --test-abc {rename_a} {rename_b} {rename_c}'
                log( f'command is: {command}')

                log( '')
                log( '== running command for first time')
                _mtime_cache_clear()
                e = os.system( f'touch {rename_a}')
                e = system( command, rename_w, verbose='derR', out_prefix='    ', method=method, use_hash=use_hash)
                #os.system( 'ls -lt|head')
                assert e == 0, f'e={e}'

                log( '')
                log( '== running command again')
                _mtime_cache_clear()
                e = system( command, rename_w, verbose='derR', out_prefix='    ', method=method, use_hash=use_hash)
                #os.system( 'ls -lt|head')
                assert e is None, f'e={e}'

                log( '')
                log( f'== running command after touching {rename_a}')
                _mtime_cache_clear()
                e = os.system( f'touch {rename_a}')
                e = system( command, rename_w, verbose='derR', out_prefix='    ', method=method, use_hash=use_hash)
                #os.system( 'ls -lt|head')
                if use_hash:
                    assert e is None, f'e={e}'
                else:
                    assert e == 0, f'e={e}'

                log( '')
                log( f'== running command after touching {rename_a}')
                _mtime_cache_clear()
                e = os.system( f'echo >> {rename_a}')
                e = system( command, rename_w, verbose='derR', out_prefix='    ', method=method, use_hash=use_hash)
                #os.system( 'ls -lt|head')
                assert e == 0, f'e={e}'
            
            t = time.time() - t
            log( f'tests took {t:.2f}s')

            log( 'tests passed')

        finally:
            _remove( build_c)
            _remove( build_h)
            _remove( build_exe)
            _remove( build_walkfile)
            _remove( rename_w)
            _remove( rename_a)
            _remove( rename_b)
            _remove( rename_c)
    
    
def _do_tests( use_hashs, methods):
    '''
    Runs tests for all combinations of <use_hashs> and <methods>.
    '''
    if not isinstance( use_hashs, (tuple, list)):
        use_hashs = use_hashs,
    if not isinstance( methods, (tuple, list)):
        methods = methods,
    for method in methods:
        for use_hash in use_hashs:
            _do_test( use_hash, method)
    

def _get_args( argv):
    '''
    Generator that iterates over argv items. Does getopt-style splitting of
    args starting with single '-' character.
    '''
    for arg in argv:
        if arg.startswith('-') and not arg.startswith('--'):
            for arg2 in arg[1:]:
                yield '-' + arg2
        else:
            yield arg


def _main():
    
    force = None
    verbose = None
    method = None
    use_hash = True
    
    args = _get_args( sys.argv[1:])
    arg = None
    while 1:
        try:
            arg = next( args)
        except StopIteration:
            break
        
        if not arg.startswith( '-'):
            walk_path = arg
            command = ''
            for arg in args:
                command += f' {arg}'
            e = system( command, walk_path, verbose, force, method=method)
            sys.exit(e)
            
        if arg == '-h' or arg == '--help':
            sys.stdout.write( __doc__)
            sys.stdout.write( textwrap.dedent( '''
                    Walk is primarily a python module, but can also be used from the command line:

                        walk.py <args> [<walk-path> <command>...]
                        walk.py --doctest

                    Args:
                        --doctest
                            Runs doctest on the `walk` module. Must be the only arg.
                        -f 0 | 1
                            Force running/not-running of the command:
                                0 - never run the command.
                                1 - always run the command.
                        --hash 0 | 1
                            1 - use hash (default).
                            0 - use mtimes.
                        -m preload | trace
                            Override the default use of preload library or strace/ktrace
                            mechanisms.
                        --new <path>
                            Treat file `path` as new, like make's `-W`.
                        --test
                            Runs some tests.
                        --test-abc
                            For internal use by `--test`.
                        --test-profile <walk>
                            Measures speed of processing walk file.
                        --time-load-all <root>
                            Times processing of all `.walk` files within `root`.

                    For example:
                        walk.py myapp.exe.walk cc -Wall -W -o myapp.exe foo.c bar.c
                    '''))
        
        elif arg == '-f':
            force = int( next( args))
        
        elif arg == '--hash':
            use_hash = int( next( args))
        
        elif arg == '-m':
            method = next( args)
        
        elif arg == '--new':
            path = next( args)
            mtime_cache_mark_new( path)
        
        elif arg == '--test':
            if _openbsd:
                methods = ('preload', 'trace')
            else:
                methods = ('trace',)
            use_hashs = True, False
            _do_tests( use_hashs, methods)
        
        elif arg == '--test-abc':
            a = next( args)
            b = next( args)
            c = next( args)
            with open( a) as f:
                pass
            with open( b, 'w') as f:
                pass
            os.rename( b, c)
        
        elif arg == '--test-profile':
            walk_file = next( args)
            t0 = time.time()
            t1 = t0 + 2
            i = 0
            while 1:
                i += 1
                _system_check( walk_file, command='', use_hash=use_hash)
                t = time.time()
                if t > t1:
                    t -= t0
                    break
                _mtime_cache_clear = dict()
            print( f'sec/it={t/i}')
        
        elif arg == '--time-load-all':
            root = next( args)
            _time_load_all( root)
        
        else:
            raise Exception( f'Unrecognised arg: {arg}')


if __name__ == '__main__':
    if len( sys.argv) == 2 and sys.argv[1] == '--doctest':
        log( 'Running doctest.testmod().')
        import doctest
        doctest.testmod()
    else:
        _main()
