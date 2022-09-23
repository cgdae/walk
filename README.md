<!--
multimarkdown README.md > README.md.html
markdown_py -v -x markdown.extensions.toc README.md > README.md.html
[TOC]
-->

# *"Walk, don't run."*


## Overview

Walk is a Python module that provides a mechanism for running commands, where
commands are not run if Walk can infer that they would not change any generated
files.

* An `LD_PRELOAD` library or syscall tracing is used to detect what files a
command reads and/or writes.

* Tested and used on Linux and OpenBSD.

* Also provided is an example Python script `walkbuild/walkfg.py` which uses
Walk to work as a build system for the [Flightgear](https://flightgear.org)
open-source flight simulator.


## Use as a build system

Walk allows a build system to be written simply as a list of commands to be
run, with no need for explicit dependency information.

By specifying these commands as calls to the function
`walkbuild.walk.system()`, one ensures that they will not be run if the command
would not modify any existing generated files. So only the commands that are
necessary to bring things up to date, will be run.

For example to build a project consisting of two `.c` files, one could do (in
Python):

```python
import walkbuild.walk as walk
walk.system( 'cc -c -o foo.o foo.c', 'foo.o.walk')
walk.system( 'cc -c -o bar.o bar.c', 'bar.o.walk')
walk.system( 'cc -o myapp foo.o bar.o', 'myapp.walk')
```


## Other features

* **Look at file content not modification times**

    Walk uses md5 hashes to detect changes to files, instead of file modification
    times.

    This means that Walk will not do unnecessary builds if a file is merely touched
    without its contents being changed (for example from a `git` operation).

* **Allow control over ordering of commands**

    Unlike conventional build systems, one can control the order in which
    commands are run. For example the `walkbuild/walkfg.py` Flightgear build script
    compiles newer source files first, which often finds compilation errors
    more quickly when one is developing.

* **Detect non-trivial changes to commands**

    By default commands are always re-run if the command itself has changed.

    One can provide a custom comparison function, which allows one to avoid
    re-running commands if they are changed in only a trivial way. For example
    the `walkbuild/walkfg.py` Flightgear build script ignores changes to the
    compiler's `-W*` warning flags.

* **Verbose output only on failure**

    By default Walk only shows commands if they have failed. This gives concise
    output but, unlike `make -s` for example, it still allows one to see the
    details of failed commands.

    [Command _output_ is always shown by default.]
    

## Concurrency

The `Concurrent` class allows commands to be run concurrently on multiple
threads. One can use the `.join()` method to wait for scheduled commands to
complete.

For example:

```python
import walkbuild.walk as walk

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
```


## How it works

### Detecting command input and output files

Walk supports two ways of finding out what files a command (or its
sub-commands) opened for reading and/or writing:

* An `LD_PRELOAD` library which intercepts functions such as `open()`,
`rename()` etc.

* Running commands under a syscall tracer:

    * Linux `strace`.
    * OpenBSD `ktrace`.

On Linux the `LD_PRELOAD` approach doesn't work due to the `ld` linker
appearing to open the output file using a direct syscall (which cannot be
easily intercepted by the preload library), so Walk defaults to using `strace`.

On OpenBSD both approaches work but Walk defaults to `LD_PRELOAD` as it appears
to be slightly faster.

If using the `LD_PRELOAD` approach, Walk automatically builds the library in
`/tmp` as required (Walk contains the C source code).


### Managing `.walk` files

The first time Walk runs a command, it creates a per-command `.walk` file which
contains the command itself, plus md5 hashes of all files that the command (or
its child commands) read or wrote.

On subsequent invocations of the command, Walk checks for changes to the md5
hashes of the files listed in the `.walk` file. It also looks at whether the
command itself has changed.

If the command is unchanged and all of the hashes are unchanged, Walk does not
run the command.

Otherwise Walk runs the command and recreates the `.walk` file.


### Edge cases
    
Walk is careful to handle previous failure to open input files (for example a
failure to open for reading) where the file now exists - in this case it will always
run the command.

Walk is resilient to being interrupted by signals or system crashes, because
it always write a zero-length `.walk` file before re-running a command. If
the build process is killed before the command completes, then the next time
Walk runs it will find this zero-lenth `.walk` file and know the command was
interrupted, and will always re-run the command.


## Command line usage

Walk is primarily a python module, but can also be used from the command line:

    walkbuild/walk.py <args> <walk-path> <command> ...

For example:

```shell
walkbuild/walk.py myapp.exe.walk cc -Wall -W -o myapp.exe foo.c bar.c
```

For more information run:

```shell
walk/__init__.py -h
```


## Links

* Development: [https://github.com/cgdae/walk](https://github.com/cgdae/walk)
* Docs: [https://walk.readthedocs.io/](https://walk.readthedocs.io/)

### Related projects

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

Dependency information in walk files is not available the first time a build
is run, and might become incorrect if commands or input files are changed. So
we would always have to re-scan walk files after commands have completed, and
re-run commands in the correct order as required. But most of the time this
wouldn't be necessary.

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
