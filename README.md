# Walk

## Overview

`walk.py` is a Python module that provides a mechanism for running external
commands, which avoids running these commands if we can infer that they would
not change any generated files.

Also provided is a Python script `walkfg.py` which uses `walk.py` to build
the [Flightgear](https://flightgear.org) open-source flight simulator.


## Use as a build system

Walk allows a build system to be written simply as a list of external commands
to be run, with no need for explicit dependency information.

By specifying these commands as calls to `walk.system()`, we ensure that
they will not be run if the command would not modify any existing generated
files. So we end up running only the commands that are necessary to bring
things up to date.

For example to build a project consisting of two `.c` files, one could do (in
Python):

    import walk
    walk.system( 'cc -c -o foo.o foo.c', 'foo.o.walk')
    walk.system( 'cc -c -o bar.o bar.c', 'bar.o.walk')
    walk.system( 'cc -o myapp foo.o bar.o', 'myapp.walk')


## Concurrency

The Concurrent class allows commands to be run concurrently on multiple
threads. One can use the `.join()` method to wait for a set of commands to
complete before running further commands.

### Example:

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


## Other features
    
Unlike conventional build systems, we are in control of the order in which
commands are run. For example one could choose to compile newer source
files first, which often finds compilation errors more quickly when one is
developing.

Commands are always re-run if the command itself has changed. But one can
provide a custom comparison function, which allows one to avoid re-running
commands if they are changed in only a trivial way. For example one could
ignore a compiler's warning flags.

See `walk.system()` for more details.
    

## How it works

The first time we run a command, we create a per-command `.walk` file which
contains the command itself, plus md5 hashes of all files that the command (or
its child commands) read or wrote.

On subsequent invocations of the command, we check for changes to the md5
hashes of the files listed in the `.walk` file. We also look at whether the
command itself has changed.

If the command is unchanged and all of the hashes are unchanged, we do not run
the command.

Otherwise we re-run the command and re-create the `.walk` file.


### Edge cases
    
We are careful to handle failure to open input files (e.g. failed to open for
reading) where the file now exists - in this case we always run the command.

We are resilient to being interrupted by signals or system crashes, because we
always write a zero-length `.walk` file before re-running a command. If we are
killed before the command completes, then the next time we are run we will find
this zero-lenth `.walk` file and know the command was interrupted, and will
always re-run the command.


## Implementation details

We have two ways of finding out what files a command (or its sub-commands)
opened for reading and/or writing:

* An `LD_PRELOAD` library which intercepts `open()` etc.

* Running commands under a syscall tracer:

    * Linux `strace`.
    * OpenBSD `ktrace`.

As of 2020-06-01, the `LD_PRELOAD` approach on Linux doesn't work due to the
`ld` linker appearing to open the output file using a direct syscall (which
cannot be easily intercepted by our preload library), so we default to using
`strace`.

On OpenBSD we can use either approach but default to `LD_PRELOAD` as it appears
to be slightly faster.

If using the `LD_PRELOAD` approach, we automatically build the library in
`/tmp` as required (walk.py contains the C source code).


## Command line usage

We are primarily a python module, but can also be used from the command
line:

    walk.py <args> <walk-path> <command> ...

Args:

    --doctest
        Runs doctest on the `walk` module.

    --new <path>
        Treat file <path> as new, like make's -W.

    -f 0 | 1
        Force running/not-running of the command:
            0 - never run the command.
            1 - always run the command.

    -m preload | trace
        Override the default use of preload library or strace/ktrace
        mechanisms.

    --test
        Runs some tests.

    --test-abc
        For internal use by --test.

    --test-profile <walk>
        Measures speed of processing walk file.

    --time-load-all <root>
        Times processing of all .walk files within <root>.

### Examples

    walk.py cc myapp.exe.walk -Wall -W -o myapp.exe foo.c bar.c


## Related projects

* [https://code.google.com/archive/p/fabricate/](https://code.google.com/archive/p/fabricate/)
* [https://github.com/buildsome/buildsome/](https://github.com/buildsome/buildsome/)
* [https://github.com/kgaughan/memoize.py](https://github.com/kgaughan/memoize.py)
* [https://gittup.org/tup/](https://gittup.org/tup/)


## Future

### Automatic ordering/concurrency
    
It might be possible to use the information in `.walk` files to do automatic
command ordering: look at existing build files to find dependency information
between commands (i.e. find commands whose output files are read by other
commands) and run commands in the right order without the caller needing to
specify anything other than an unordered list of commands.

This could be extended to do automatic concurrency - run multiple commands
concurrently when they are known to not depend on each otheer.

Dependency information in walk files is not available the first time a build is
run, and might become incorrect if commands or input files are changed. So we'd
always have to re-scan walk files after commands have completed, and re-run
commands in the correct order as required. But most of the time this wouldn't
be necessary.
    
### Automatic selection of source files
    
A large part of the Walk build script for building Flightgear is concerned with
selecting the source files to compile and link together.

It might be possible to write code that finds the unresolved and defined
symbols after each compilation and stores this information in .walk files (or
a separate file next to each .walk file. Then one could tell the script to
compile the file that contains main() and have it automatically look for, and
build, other files that implement the unresolved symbols.

We would need help to resolve situations where more than one file implements
the same symbol. And perhaps heuristics could be used to find likely source
files by grepping for missing symbols names.


## License

    Copyright 2020-2022 Julian Smith.
    SPDX-License-Identifier: GPL-3.0-only
