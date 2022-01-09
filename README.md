## A Build system using command optimisation / automatic dependencies

Core system: walk.py.

A build system for flightgear: walkfg.py.

### Summary:

    Provides a mechanism for running commands which avoids actually running
    commands if we can infer that they would not change any generated files.
    
    As of 2021-06-24 we use md5 hashes to detect changes to files, instead of
    mtimes.


### Use as a build system:

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


### Example building of Flightgear (next branch) from scratch:

    Install packages such as qtbase5-dev, openscenegraph etc.

    # Get Flightgear code:
    #
    git clone https://git.code.sf.net/p/flightgear/flightgear
    git clone https://git.code.sf.net/p/flightgear/simgear
    git clone https://git.code.sf.net/p/flightgear/fgdata
    git clone https://git.code.sf.net/p/libplib/code plib
    
    # Get Walk build system:
    #
    git clone https://git.code.sf.net/p/walk/walk
    
    # Build Flightgear:
    #
    ./walk/walkfg.py
    
    # Run Flightgear:
    #
    ./build-walk/fgfs.exe-run.sh


### How it works:

    The first time we run a command, we create a file <walk_file> which
    contains information about the command and what files the command (or its
    child commands) read or wrote.

    On subsequent invocations of the same command, we check whether the files
    listed in <walk_file> have changed, using md5 hashes. If all input files
    (e.g. opened for reading) are unchanged, we do not run the command.

    Otherwise we run the command as before and re-create <walk_file>.

    We specially handle cases such as failed input files (e.g. failed to open
    for reading) where the file now exists - in this case we always run the
    command. We also ensure that we are resilient to being interrupted by
    signals or system crashes. For example we write a zero-length <walk_file>
    before re-running a command so that if we are killed before the command
    completes, then the next we are run we will know the command was
    interrupted and can force a re-run.


### Concurrency:

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


### Command line usage:

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


### Implementation details:

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
    profiling) but tracing syscalls could be more reliable.
