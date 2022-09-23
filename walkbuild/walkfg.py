#!/usr/bin/env python3

'''
Build script for Flightgear on Unix systems.

Copyright (C) 2020-2022 Julian Smith.
SPDX-License-Identifier: GPL-3.0-only


Example usage:
    
    * Install packages such as `qtbase5-dev`, `openscenegraph` etc.

    * Get Flightgear code::
    
        git clone https://git.code.sf.net/p/flightgear/flightgear
        git clone https://git.code.sf.net/p/flightgear/simgear
        git clone https://git.code.sf.net/p/flightgear/fgdata
        git clone https://git.code.sf.net/p/libplib/code plib
    
    * Get Walk build system::
    
        git clone https://git.code.sf.net/p/walk/walk
    
    * Build Flightgear::
    
        ./walk/walkbuild/walkfg.py -b
    
    * Run Flightgear::
    
        ./build-walk/fgfs.exe-run.sh


Details:

    We expect to be in a directory containing the following git checkouts::
    
        flightgear/
        plib/
        simgear/
        fgdata/
    
    In this directory, run this script (wherever it happens to be) with the
    '-b' flag so it builds Flightgear::
    
        .../walkbuild/walkfg.py -b
    
    All generated files will be in a new directory::
    
        build-walk/
    
    The generated executable and wrapper scripts include information in their
    names to distinguish different builds::
    
        build-walk/fgfs,<flags>.exe
        build-walk/fgfs,<flags>.exe-run.sh
        build-walk/fgfs,<flags>.exe-run-gdb.sh
    
    For convenience we generate soft-links to the most recent build::
    
        build-walk/fgfs.exe
        build-walk/fgfs.exe-run.sh
        build-walk/fgfs.exe-run-gdb.sh
    
    So Flightgear can be run with::
    
        build-walk/fgfs.exe-run.sh --aircraft=... --airport=... ...

Args:
    -b
    --build
        Do a build.    
    --clang 0 | 1
        If 1, we force use of clang instead of system compiler. Default is 0.
    --debug 0 | 1
        If 1 (default), we compile and link with `-g` to include debug symbols.    
    --optimise-prefix 0|1 <prefix>
        Force optimise/no-optimise build for paths starting with `prefix`.
    --doctest
        Run doctest on this module.    
    --flags-all 0 | 1
        If 1, we use same compiler flags for all files (except for
        file-specific `-W` warning flags). So for example everything gets
        compiled with the same include path and defines.
        
        Default is 0 - files get compiled with flags specific to their
        location; this avoids unnecessary recompilation if flags for specific
        files or locations are changed.
    --force 0 | 1 | default
        If '0', we never run commands; depending on `-v` and `-w`, we may output
        diagnostics about what we would have run.

        If '1', we always run commands, regardless of whether output files are up
        to date.
        
        If 'default', commands are run only if necessary. This is also the
        default.    
    --fp 0 | 1
        If 1 we force use of frame pointer with
        `-fno-omit-frame-pointer`. Default is 0.
    --gperf 0 | 1
        If 1, build with support for google perf.    
    -h
    --help
        Show help.    
    -j N
        Set concurrency level - the maximum number of
        concurrent compiles. Default is derived from Python's
        `multiprocessing.cpu_count()`.
    -l <maxload>
        Only schedule new concurrent commands when load average
        is less than `maxload`. Default is derived from Python's
        `multiprocessing.cpu_count()`.    
    --link-only
        Only do link, do not compile.    
    -n
        Don't run commands. Equivalent to '--force 0'.
    --new <path>
        Treat `path` as new.
    --old <path>
        Treat `path` as old.    
    --optimise 0 | 1
        If 1 (the default), we build with compiler optimisations.    
    --osg-dir <directory>
        Use local OSG install instead of system OSG.
        
        For example::
        
            time (true \
                    && cd openscenegraph \
                    && git checkout OpenSceneGraph-3.6 \
                    && (rm -r build || true) \
                    && mkdir build \
                    && cd build \
                    && cmake -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=`pwd`/install .. \
                    && time make -j 3 \
                    && make install \
                    && cd ../../ \
                    ) 2>&1|tee out
            .../walkbuild/walkfg.py --osg openscenegraph/build/install -b
    
            time (true \
                    && cd openscenegraph \
                    && (rm -r build-relwithdebinfo || true) \
                    && mkdir build-relwithdebinfo \
                    && cd build-relwithdebinfo \
                    && cmake -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -g -DNDEBUG" -DCMAKE_CC_FLAGS_RELWITHDEBINFO="-O2 -g -DNDEBUG" -DCMAKE_BUILD_TYPE=RelWithDebInfo .. \
                    && VERBOSE=1 make -j 3 \
                    && VERBOSE=1 make install \
                    ) 2>&1|tee out
            .../walkbuild/walkfg.py --osg openscenegraph/build-relwithdebinfo/install -b    
    
    -o fgfs | test-suite | props-test | yasim-test
        Set what to build. Default is **fgfs**, the main Flightgear executable.    
    --osg 0|1
        Experimental: if 1, we also compile files in `openscenegraph/` instead of
        using an existing build.
        
        As of 2021-11-06, this does not work because the build does not create
        the OSG plugin libraries.
    --out-dir <directory>
        Set the directory that will contain all generated files.
        
        Default is `build-walk/`.    
    --props-locking 0 | 1
        If 0, build with `SG_PROPS_UNTHREADSAFE` pre-defined.    
    -q
        Reduce diagnostics (use `-v` to increase).    
    --show
        Show settings.    
    -t
        Show detailed timing information at end.    
    -v
        Increase diagnostics (use `-v` to decrease).    
    --v-src <path>
        Show compile command when compiling `path`.    
    -w [+-fFdDrRcCe]
        Set Walk verbose flags:
            
            * **f**   Show if we are forcing running of a command.
            * **F**   Show if we are forcing non-running of a command.
            
            * **m**   Show message if we are running command (only if d not specified).
            * **M**   Show message if we are not running command (only if d not specified).
            
            * **d**   Show description if available, if we are running command.
            * **D**   Show description if available, if we are not running command.
            
            * **r**   Show reason why a command is being run.
            * **R**   Show reason why a command is not being run.
            
            * **c**   Show the command if we are running it.
            * **C**   Show the command if we are not running it.
            
            * **e**   If command fails, show command if we haven't already shown it.
        
        Default is 'der'.
        
        If arg starts with +/-, we add/remove the specified flags to/from the
        existing settings.

Requirements:

    The `walk.py` command optimiser module.
    
    Packages for this script::
    
        python3
        strace
    
    Packages for flightgear:
    
        * Linux::
        
            apt install \
                cmake \
                freeglut3-dev \
                g++ \
                libasound-dev \
                libboost-dev \
                libcurl4-openssl-dev \
                libdbus-1-dev \
                libevent-dev \
                libjpeg-dev \
                libopenal-dev \
                libpng-dev \
                libqt5opengl5-dev \
                libqt5svg5-dev \
                libqt5websockets5-dev \
                libudev-dev \
                pkg-config \
                qml-module-qtquick-controls2 \
                qml-module-qtquick-dialogs \
                qml-module-qtquick-window2 \
                qml-module-qtquick2 \
                qtbase5-dev-tools \
                qtbase5-private-dev \
                qtchooser \
                qtdeclarative5-dev \
                qtdeclarative5-private-dev \
                qttools5-dev \
                qttools5-dev-tools \
                openscenegraph \
    
        * OpenBSD::
        
            pkg_add \
                    freeglut \
                    openal \
                    openscenegraph \
                    qtdeclarative \
'''

import glob
import inspect
import io
import multiprocessing
import os
import re
import resource
import subprocess
import sys
import textwrap
import time
import traceback
import types

sys.path.append( os.path.relpath( f'{__file__}/../'))
import walk 
del sys.path[-1]

def time_duration( seconds, verbose=0, decimals=0, align=False):
    '''
    Returns string representation of an interval.

    seconds:
        Duration in seconds
    verbose:
        * If 0, return things like: 4d3h2m23.4s.
        * If 1, return things like: 4d 3h 2m 23.4s.
        * If 2, return things like: 4 days 1 hour 2 mins 23.4 secs.
    decimals:
        Number of fractional decimal digits for seconds.
    align:
        If true, we pad items with leading spaces (`verbose==2`) or zeros
        (`verbose=0` or `verbose=1`) to make returned text have fixed
        alignment. If `2`, we also pad positive durations with a space so that
        positive and negative durations align.
    
    >>> m=60
    >>> h=m*60
    >>> d=24*h
    >>> time_duration( 0)
    '0s'
    >>> time_duration( 0, verbose=1)
    '0s'
    >>> time_duration( 0, verbose=2)
    '0 sec'
    >>> time_duration( 3)
    '3s'
    >>> time_duration( 2*m + 3)
    '2m3s'
    >>> time_duration( h*3 + m*2 + 3, align=True)
    ' 3h02m03s'
    >>> time_duration( d*3 + h*12 + m*15 + 3)
    '3d12h15m3s'
    >>> time_duration( h*3 + 3)
    '3h3s'
    >>> time_duration( h*3 + m*20 + 3)
    '3h20m3s'
    >>> time_duration( h*3 + 3, align=True)
    ' 3h00m03s'
    >>> time_duration( h*3 + 3, align=True, verbose=1)
    ' 3h  0m  3s'
    >>> time_duration( h*3, align=True, verbose=1)
    ' 3h  0m  0s'
    >>> time_duration( d*3 + h*12 + m*15 + 33)
    '3d12h15m33s'
    >>> time_duration( m*50 + 3.34567, decimals=1, align=True)
    '50m03.3s'
    >>> time_duration( d*3 + h*12 + m*5 + 3.34567, decimals=1, align=True)
    ' 3d12h05m03.3s'
    >>> time_duration( d*3 + h*12 + m*5 + 33, verbose=2)
    '3 days 12 hours 5 mins 33 secs'
    >>> time_duration( d*3 + h*12 + m*1 + 33.123456, verbose=2, decimals=3)
    '3 days 12 hours 1 min 33.123 secs'
    >>> time_duration( d*3 + h*12 + m*1 + 33.123456, verbose=2, decimals=3, align=True)
    ' 3 days 12 hours  1 min  33.123 secs'
    '''
    assert verbose in ( 0, 1, 2)
    x = abs(seconds)
    ret = ''
    for i, (div, name) in enumerate([
            ( 60, 'sec'),
            ( 60, 'min'),
            ( 24, 'hour'),
            ( None, 'day'),
            ]):
        force = ( x == 0 and i == 0)
        if div:
            value = x % div
            x = int( x / div)
        else:
            value = x
            x = 0
        if verbose in ( 0, 1):
            name = name[0]  # Just use first letter of <name>.
        if value or (x and align) or force:
            if verbose == 2:
                name += 's' if value > 1 else ' ' if align else ''
                name = ' ' + name
            if verbose in (1, 2) and i:
                name += ' '
            value = str(value) if i else f'{value:.{decimals}f}'
            if x and align:
                # There are more items to add, so pad current item with leading
                # zeros/spaces to give fixed alignment.
                length = value.find( '.')
                if length == -1:
                    length = len( value)
                assert length <= 2
                n = 2 - length
                c = '0' if verbose == 0 else ' '
                value = c * n + value
            ret = f'{value}{name}{ret}'
        i += 1
    
    if seconds < 0:
        ret = '-' + ret
    elif align == 2:
        ret = ' ' + ret
    
    return ret


class LogPrefix:
    '''
    Creates dynamic prefix text showing elapsed time and progress as a
    percentage.
    
    Code should update `self.progress` between `0` and `1` to indicate progress.
    '''
    def __init__( self):
        self.t0 = time.time()
        self.progress = 0
    def __call__( self):
        dt = time.time() - self.t0
        elapsed = time_duration( dt, verbose=0, decimals=1, align=True)
        progress = self.progress() if callable( self.progress) else self.progress
        percent = f'{100*progress:3.0f}'
        #return f'{elapsed:>8s} {percent}% progress={self.progress}: '
        return f'{elapsed:>8s} {percent}%: '

_log_prefix = LogPrefix()

# Tell walk.log() to use _log_prefix as prefix for each line.
walk.log_prefix_set( _log_prefix)


g_build_debug = 1
g_build_optimise = 1
g_clang = False
g_concurrency = None
g_verbose = 0
g_flags_all = False
g_force = None
g_keep_going = False
g_link_only = False
g_max_load_average = None
g_osg = False   # If true, we build osg ourselves; does not yet work.
g_osg_dir = None
g_outdir = 'build-walk'
g_gperf = 0
g_show_timings = False
g_walk_verbose = 'der'
g_verbose_srcs = []
g_props_locking = True
g_frame_pointer = False
g_ffmpeg = True
g_optimise_prefixes = []

g_os = os.uname()[0]
g_openbsd = (g_os == 'OpenBSD')
g_linux = (g_os == 'Linux')

def system_out( text):
    walk.log( f'> {text}')

def system( command, walk_path, description=None, verbose=None):
    '''
    Wrapper for `walk.system()` which sets default verbose and force flags,
    and raises an exception if the command fails instead of returning an error
    value.
    '''
    if verbose is None:
        verbose = g_walk_verbose
    e = walk.system(
            command,
            walk_path,
            verbose=verbose,
            force=g_force,
            description=description,
            #out_prefix='    ',
            out=system_out,
            )
    if e:
        raise Exception( f'command failed: {command}')

def system_concurrent(
        walk_concurrent,
        command,
        walk_path,
        description=None,
        verbose=None,
        command_compare=None,
        ):
    '''
    Wrapper for `walk_concurrent.system()` which sets default verbose and force
    flags.
    '''
    if verbose is None:
        verbose = g_walk_verbose
    doit, reason, e = walk_concurrent.system_r(
            command,
            walk_path,
            verbose=verbose,
            force=g_force,
            description=description,
            command_compare=command_compare,
            #out_prefix='    ',
            out=system_out,
            )
    return doit or g_force, reason, e

def file_write( text, path, verbose=None):
    '''
    Wrapper for `walk.file_write()` which uses `g_walk_verbose` and `g_force`.
    '''
    if verbose == None:
        verbose = g_walk_verbose
    walk.file_write( text, path, verbose, g_force)


def cmp(a, b):
    '''
    Not sure why python3 dropped `cmp()`, but this recreates it.
    '''
    return (a > b) - (a < b) 


def get_gitfiles( directory):
    '''
    Returns list of all files known to git in `directory`; `directory` must be
    somewhere within a git checkout.
    '''
    command = 'cd ' + directory + '; git ls-files .'
    text = subprocess.check_output( command, shell=True)
    ret = []
    text = text.decode('latin-1')
    for f in text.split('\n'):
        f = f.strip()
        if not f:   continue
        ret.append( os.path.join(directory, f))
    return ret

def git_id( directory):
    '''
    Returns git sha.
    '''
    id = subprocess.check_output( f'cd {directory} && PAGER= git show --pretty=oneline', shell=True)
    id = id.decode( 'latin-1')
    id = id.split( '\n', 1)[0]
    id = id.split( ' ', 1)[0]
    return id


def get_files( target):
    '''
    Returns `(all, cpp)` where `all` is list of files known to git and `cpp` is
    subset of these files that are not headers and are used to build `target`.
    
    We find all files known to git, then prune out various files which we don't
    want to include in the build.
    
    target:
        One of:
            * 'fgfs'
            * 'props-test'
            * 'test-suite'
            * 'yasim-test'
    '''
    
    exclude_patterns = [
            'flightgear/3rdparty/cjson/test.c',
            'flightgear/3rdparty/flite_hts_engine/bin/flite_hts_engine.c',
            'flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex/cmu_lex_data_raw.c',
            'flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex/cmu_lex_entries_huff_table.c',
            'flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex/cmu_lex_num_bytes.c',
            'flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex/cmu_lex_phones_huff_table.c',
            'flightgear/3rdparty/hidapi/hidparser/testparse.c',
            'flightgear/3rdparty/hidapi/mac/hid.c',
            'flightgear/3rdparty/hidapi/windows/hid.c',
            'flightgear/3rdparty/hts_engine_API/bin/hts_engine.c',
            'flightgear/3rdparty/iaxclient/lib/audio_portaudio.c',
            'flightgear/3rdparty/iaxclient/lib/codec_ffmpeg.c',
            'flightgear/3rdparty/iaxclient/lib/codec_ilbc.c',
            'flightgear/3rdparty/iaxclient/lib/codec_theora.c',
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/miniphone.c',
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/winiphone.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/modes_noglobals.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/testdenoise.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/testecho.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/testenc.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/testenc_uwb.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/testenc_wb.c',
            'flightgear/3rdparty/iaxclient/lib/portaudio/*',
            'flightgear/3rdparty/iaxclient/lib/portmixer/*',
            'flightgear/3rdparty/iaxclient/lib/video.c',
            'flightgear/3rdparty/iaxclient/lib/video_portvideo.cpp',
            'flightgear/3rdparty/iaxclient/lib/winfuncs.c',
            'flightgear/3rdparty/iaxclient/lib/win/iaxclient_dll.c',
            #'flightgear/3rdparty/joystick/jsBSD.cxx',
            'flightgear/3rdparty/joystick/jsMacOSX.cxx',
            #'flightgear/3rdparty/joystick/jsNone.cxx',
            'flightgear/3rdparty/joystick/jsWindows.cxx',
            'flightgear/examples/*',
            'flightgear/scripts/example/fgfsclient.c',
            'flightgear/scripts/example/fgfsclient.cxx',
            'flightgear/src/Airports/calc_loc.cxx',
            'flightgear/src/EmbeddedResources/fgrcc.cxx',
            'flightgear/src/FDM/JSBSim/JSBSim.cpp',
            'flightgear/src/FDM/LaRCsim/c172_main.c',
            'flightgear/src/FDM/LaRCsim/ls_trim.c',
            'flightgear/src/FDM/LaRCsim/mymain.c',
            'flightgear/src/FDM/YASim/proptest.cpp',
            #'flightgear/src/FDM/YASim/yasim-test.cpp',
            'flightgear/src/GUI/FGWindowsMenuBar.cxx',
            'flightgear/src/GUI/WindowsFileDialog.cxx',
            'flightgear/src/GUI/WindowsMouseCursor.cxx',
            'flightgear/src/Viewer/VRManager.cxx',
            
            'flightgear/3rdparty/osgXR/*',
            'flightgear/src/Viewer/VRManager.cxx',
            
            # 2020-6-10: needs qt5-qtbase-private-devel, which isn't
            # in devuan ? fgfs seems to build ok without it.
            #
            'flightgear/src/GUI/QQuickDrawable.cxx',
            
            'flightgear/src/Input/fgjs.cxx',
            'flightgear/src/Input/js_demo.cxx',
            'flightgear/src/Main/metar_main.cxx',
            'flightgear/src/Navaids/awynet.cxx',
            'flightgear/src/Network/HLA/hla.cxx',
            'flightgear/src/Scripting/ClipboardFallback.cxx',
            'flightgear/src/Scripting/ClipboardWindows.cxx',

            # 2021-03-06 DDS is new but seems to be broken.
            'flightgear/src/Network/DDS/*',
            'flightgear/src/Network/dds_props.cxx',
            'simgear/simgear/io/SGDataDistributionService.cxx',
            
            # Things to allow legacy builds to work:
            #'flightgear/src/Viewer/renderingpipeline.cxx',
            'flightgear/src/Viewer/CameraGroup_compositor.cxx',
            'flightgear/src/Viewer/renderer_compositor.cxx',
            
            'flightgear/utils/*',
            'plib/demos/*',
            'plib/examples/*',
            'plib/src/fnt/fntBitmap.cxx',
            'plib/src/fnt/fnt.cxx',
            'plib/src/fnt/fntTXF.cxx',
            'plib/src/js/jsBSD.cxx',
            'plib/src/js/js.cxx',
            'plib/src/js/jsLinux.cxx',
            'plib/src/js/jsLinuxOld.cxx',
            'plib/src/js/jsMacOS.cxx',
            'plib/src/js/jsMacOSX.cxx',
            'plib/src/js/jsNone.cxx',
            'plib/src/js/jsWindows.cxx',
            'plib/tools/src/af2rgb/af2rgb.cxx',
            'plib/tools/src/plibconvert.cxx',
            'simgear/3rdparty/expat/*',
            'simgear/3rdparty/udns/dnsget.c',
            'simgear/3rdparty/udns/ex-rdns.c',
            'simgear/3rdparty/udns/getopt.c',
            'simgear/3rdparty/udns/inet_XtoX.c',
            'simgear/3rdparty/udns/rblcheck.c',
            'simgear/simgear/bucket/test_bucket.cxx',
            'simgear/simgear/bvh/bvhtest.cxx',
            'simgear/simgear/canvas/elements/canvas_element_test.cpp',
            'simgear/simgear/canvas/events/event_test.cpp',
            'simgear/simgear/canvas/events/input_event_demo.cxx',
            'simgear/simgear/canvas/layout/canvas_layout_test.cxx',
            'simgear/simgear/canvas/ShaderVG/*',
            'simgear/simgear/debug/logtest.cxx',
            'simgear/simgear/embedded_resources/embedded_resources_test.cxx',
            'simgear/simgear/emesary/test_emesary.cxx',
            'simgear/simgear/environment/test_metar.cxx',
            'simgear/simgear/environment/test_precipitation.cxx',
            'simgear/simgear/hla/*',
            'simgear/simgear/io/decode_binobj.cxx',
            'simgear/simgear/io/httpget.cxx',
            #'simgear/simgear/io/HTTPClient.cxx',
            'simgear/simgear/io/http_repo_sync.cxx',
            'simgear/simgear/io/iostreams/CharArrayStream_test.cxx',
            'simgear/simgear/io/iostreams/sgstream_test.cxx',
            'simgear/simgear/io/iostreams/zlibstream_test.cxx',
            'simgear/simgear/io/lowtest.cxx',
            'simgear/simgear/io/socktest.cxx',
            'simgear/simgear/io/tcp_client.cxx',
            'simgear/simgear/io/tcp_server.cxx',
            'simgear/simgear/io/test_*',
            'simgear/simgear/io/text_DNS.cxx',
            'simgear/simgear/magvar/testmagvar.cxx',
            'simgear/simgear/math/SGGeometryTest.cxx',
            'simgear/simgear/math/SGMathTest.cxx',
            'simgear/simgear/math/test_sgvec4.cxx',
            'simgear/simgear/misc/argparse_test.cxx',
            'simgear/simgear/misc/CSSBorder_test.cxx',
            'simgear/simgear/misc/path_test.cxx',
            'simgear/simgear/misc/sg_dir_test.cxx',
            'simgear/simgear/misc/sha1.c',
            'simgear/simgear/misc/SimpleMarkdown_test.cxx',
            'simgear/simgear/misc/strutils_test.cxx',
            'simgear/simgear/misc/SVGpreserveAspectRatio_test.cxx',
            'simgear/simgear/misc/swap_test.cpp',
            'simgear/simgear/misc/tabbed_values_test.cxx',
            'simgear/simgear/misc/utf8tolatin1_test.cxx',
            'simgear/simgear/nasal/cppbind/test/cppbind_test.cxx',
            'simgear/simgear/nasal/cppbind/test/cppbind_test_ghost.cxx',
            'simgear/simgear/nasal/cppbind/test/nasal_gc_test.cxx',
            'simgear/simgear/nasal/cppbind/test/nasal_num_test.cxx',
            'simgear/simgear/package/CatalogTest.cxx',
            'simgear/simgear/package/pkgutil.cxx',
            'simgear/simgear/props/easing_functions_test.cxx',
            'simgear/simgear/props/propertyObject_test.cxx',
            #'simgear/simgear/props/props_test.cxx',
            'simgear/simgear/props/props-unsafe.cxx',
            'simgear/simgear/scene/dem/*',
            'simgear/simgear/scene/material/EffectData.cxx',
            'simgear/simgear/scene/material/ElementBuilder.cxx',
            'simgear/simgear/scene/material/parseBlendFunc_test.cxx',
            'simgear/simgear/scene/model/animation_test.cxx',
            'simgear/simgear/scene/tgdb/BucketBoxTest.cxx',
            'simgear/simgear/scene/util/parse_color_test.cxx',
            'simgear/simgear/serial/testserial.cxx',
            'simgear/simgear/sound/aeonwave_test1.cxx',
            'simgear/simgear/sound/openal_test1.cxx',
            'simgear/simgear/sound/soundmgr_aeonwave.cxx',
            'simgear/simgear/sound/soundmgr_test2.cxx',
            'simgear/simgear/sound/soundmgr_test.cxx',
            'simgear/simgear/std/integer_sequence_test.cxx',
            'simgear/simgear/std/type_traits_test.cxx',
            'simgear/simgear/structure/event_mgr_test.cxx',
            'simgear/simgear/structure/test_*',
            'simgear/simgear/structure/SGAction.cxx',
            'simgear/simgear/structure/expression_test.cxx',
            'simgear/simgear/structure/function_list_test.cxx',
            'simgear/simgear/structure/intern.cxx',
            'simgear/simgear/structure/shared_ptr_test.cpp',
            'simgear/simgear/structure/state_machine_test.cxx',
            'simgear/simgear/structure/subsystem_test.cxx',
            'simgear/simgear/structure/test_*',
            'simgear/simgear/timing/testtimestamp.cxx',
            'simgear/simgear/xml/testEasyXML.cxx',
            ]
    
    if g_osg:
        exclude_patterns += [
                'openscenegraph/src/OpenThreads/win32/*',
                'openscenegraph/src/osgPlugins/jp2/*',
                'openscenegraph/src/osgPlugins/las/*',
                'openscenegraph/include/osgViewer/api/Win32/*',
                'openscenegraph/src/osgViewer/PixelBufferWin32.cpp',
                'openscenegraph/src/osgViewer/GraphicsWindowWin32.cpp',
                'openscenegraph/src/osgViewer/PixelBufferWin32.cpp',
                'openscenegraph/src/osgPlugins/lua/*',
                'openscenegraph/src/osgPlugins/dae/*',
                'openscenegraph/src/osgPlugins/ffmpeg/*',
                'openscenegraph/src/osgPlugins/vnc/*',
                'openscenegraph/src/osgPlugins/txp/*',
                'openscenegraph/src/osgPlugins/sdl/*',
                'openscenegraph/src/osgPlugins/svg/*',
                'openscenegraph/src/osgPlugins/quicktime/*',
                'openscenegraph/src/osgPlugins/pdf/*',
                'openscenegraph/src/osgPlugins/osc/*',
                'openscenegraph/src/osgPlugins/ogr/*',
                'openscenegraph/src/osgPlugins/nvtt/*',
                'openscenegraph/src/osgPlugins/gstreamer/*',
                'openscenegraph/src/osgPlugins/imageio/*',
                'openscenegraph/src/osgPlugins/fbx/*',
                'openscenegraph/src/osgPlugins/ffmpeg/*',
                'openscenegraph/src/osgPlugins/exr/*',
                'openscenegraph/src/osgPlugins/directshow/*',
                'openscenegraph/src/osgPlugins/dicom/*',
                'openscenegraph/src/osgPlugins/bsp/*',
                'openscenegraph/src/osgPlugins/ZeroConfDevice/*',
                'openscenegraph/src/osgPlugins/Inventor/*',
                'openscenegraph/src/osgPlugins/OpenCASCADE/*',
                'openscenegraph/src/osgPlugins/python/*',
                'openscenegraph/src/osgPlugins/gdal/*',
                'openscenegraph/src/osgPlugins/gif/*',
                'openscenegraph/src/osgPlugins/RestHttpDevice/*',
                'openscenegraph/src/osgPlugins/gta/*',
                'openscenegraph/src/osgPlugins/avfoundation/*',
                'openscenegraph/src/osgPlugins/QTKit/*',
                'openscenegraph/src/osgPlugins/V8/*',
                
                'openscenegraph/src/osgPlugins//*',
                'openscenegraph/src/osgPlugins//*',
                'openscenegraph/src/osgPlugins//*',
                'openscenegraph/src/osgPlugins//*',
                'openscenegraph/src/osgPlugins//*',

                'openscenegraph/src/osg/Matrix_implementation.cpp',
                'openscenegraph/examples/*',
                'openscenegraph/applications/*',
                
                # duplicates simgear/simgear/scene/tgdb/VPBTechnique.cxx
                #'openscenegraph/src/osgTerrain/GeometryTechnique.cpp',
                
                'openscenegraph/src/osgWrappers/deprecated-dotosg/*',
                
                # Is #include-d by src/osg/glu/libtess/priorityq.cpp.
                'openscenegraph/src/osg/glu/libtess/priorityq-heap.cpp',
                
                'openscenegraph/src/osgWrappers/serializers/osgUI/Widget.cpp',
                
                'openscenegraph/src/osgUtil/shaders/*',
                
                'openscenegraph/src/osgPlugins/ive/*',
                #'openscenegraph/src/osgTerrain/TerrainTile.cpp',
                ]
    
    if g_openbsd:
        exclude_patterns += [
                'flightgear/3rdparty/hidapi/linux/*',
                'flightgear/3rdparty/iaxclient/lib/audio_alsa.c',
                'flightgear/3rdparty/iaxclient/lib/libspeex/*',
                'flightgear/3rdparty/joystick/jsLinux.cxx',
                'flightgear/3rdparty/joystick/jsBSD.cxx',
                'flightgear/src/Input/FGLinuxEventInput.cxx',
                #'plib/*',
                'flightgear/src/Input/FGHIDEventInput.cxx',
                'flightgear/test_suite/unit_tests/Input/*',
                ]
    else:
        exclude_patterns += [
                'flightgear/3rdparty/joystick/jsBSD.cxx',
                'flightgear/3rdparty/joystick/jsNone.cxx',
                ]
    
    if target == 'yasim-test':
        exclude_patterns += [
                #'simgear/*',
                'flightgear/src/AIModel/*',
                'flightgear/src/ATC/*',
                'flightgear/src/Add-ons/*',
                'flightgear/src/Aircraft/*',
                'flightgear/src/Airports/*',
                'flightgear/src/Autopilot/*',
                'flightgear/src/Canvas/*',
                'flightgear/src/Cockpit/*',
                'flightgear/src/Environment/*',
                'flightgear/src/FDM/AIWake/*',
                'flightgear/src/FDM/ExternalNet/*',
                'flightgear/src/FDM/ExternalPipe/*',
                'flightgear/src/FDM/JSBSim/*',
                'flightgear/src/FDM/LaRCsim/*',
                'flightgear/src/FDM/Navaids/*',
                'flightgear/src/FDM/SP/*',
                'flightgear/src/FDM/UIUCModel/*',
                'flightgear/src/FDM/fdm_shell.cxx',
                'flightgear/src/GUI/*',
                'flightgear/src/Main/*',
                'flightgear/src/Main/bootstrap.cxx',
                'flightgear/src/Main/fg_props.cxx',
                'flightgear/src/Model/*',
                'flightgear/src/Time/*',
                'flightgear/src/FDM/UFO.cxx',
                'plib/*',
                ]
    else:
        exclude_patterns += [
                'flightgear/src/FDM/YASim/yasim-test.cpp'
                ]
    
    if target in ( 'fgfs', 'yasim-test'):
        exclude_patterns += [
                'flightgear/test_suite/*',
                'flightgear/3rdparty/cppunit/*',
                'simgear/simgear/props/props_test.cxx',
                ]
    
    if target == 'test-suite':
        exclude_patterns += [
                'flightgear/src/Main/bootstrap.cxx',
                'flightgear/src/Scripting/NasalUnitTesting.cxx',
                'flightgear/test_suite/system_tests/Instrumentation/testgps.cxx',
                'flightgear/test_suite/system_tests/Navaids/testnavs.cxx',
                'flightgear/test_suite/attic/*',
                'flightgear/3rdparty/cppunit/src/cppunit/DllMain.cpp',
                'flightgear/3rdparty/cppunit/src/cppunit/Win32DynamicLibraryManager.cpp',
                'simgear/simgear/props/props_test.cxx',
                ]
    
    if target == 'props-test':
        exclude_patterns += [
                'flightgear/*',
                'plib/*',
                ]
    
    
    # We sort <exclude_patterns> so that we can short-cut the searches we do
    # below.
    #
    exclude_patterns.sort()

    files_flightgear = get_gitfiles( 'flightgear')
    files_simgear = get_gitfiles( 'simgear')
    files_plib = get_gitfiles( 'plib')
    
    files_osg = files_osg = get_gitfiles( 'openscenegraph') if g_osg else []

    all_files = ([]
            + files_flightgear
            + files_simgear
            + files_plib
            + files_osg
            )

    ret = []
    exclude_patterns_pos = 0
    for path in all_files:
        _, suffix = os.path.splitext( path)
        if suffix not in ('.c', '.cpp', '.cxx'):
            continue
        include = True
        for i, exclude_pattern in enumerate(exclude_patterns, exclude_patterns_pos):
            if exclude_pattern.endswith( '*'):
                if path.startswith( exclude_pattern[:-1]):
                    include = False
                    break
            else:
                c = cmp( exclude_pattern, path)
                if c > 0:
                    # <exclude_pattern> does not match <path>, and later
                    # exclude patterns will also not match <path>.
                    break
                
                # If we get here, <exclude_pattern> will not match later paths.
                exclude_patterns_pos = i + 1
                
                # <exclude_pattern> matches <path>, so exclude <path>.
                if c == 0:
                    include = False
                    break
        if include:
            ret.append( path)
    
    if target == 'yasim-test':
        ret2 = [
                'flightgear/src/FDM/YASim/Airplane.cpp',
                'flightgear/src/FDM/YASim/YASimAtmosphere.cpp',
                'flightgear/src/FDM/YASim/ControlMap.cpp',
                'flightgear/src/FDM/YASim/ElectricEngine.cpp',
                'flightgear/src/FDM/YASim/FGFDM.cpp',
                'flightgear/src/FDM/YASim/Gear.cpp',
                'flightgear/src/FDM/YASim/Glue.cpp',
                'flightgear/src/FDM/YASim/Ground.cpp',
                'flightgear/src/FDM/YASim/Hitch.cpp',
                'flightgear/src/FDM/YASim/Hook.cpp',
                'flightgear/src/FDM/YASim/Integrator.cpp',
                'flightgear/src/FDM/YASim/Jet.cpp',
                'flightgear/src/FDM/YASim/Launchbar.cpp',
                'flightgear/src/FDM/YASim/Model.cpp',
                'flightgear/src/FDM/YASim/PistonEngine.cpp',
                'flightgear/src/FDM/YASim/PropEngine.cpp',
                'flightgear/src/FDM/YASim/Propeller.cpp',
                'flightgear/src/FDM/YASim/RigidBody.cpp',
                'flightgear/src/FDM/YASim/Rotor.cpp',
                'flightgear/src/FDM/YASim/Rotorpart.cpp',
                'flightgear/src/FDM/YASim/SimpleJet.cpp',
                'flightgear/src/FDM/YASim/Surface.cpp',
                'flightgear/src/FDM/YASim/TurbineEngine.cpp',
                'flightgear/src/FDM/YASim/Turbulence.cpp',
                'flightgear/src/FDM/YASim/Wing.cpp',
                'flightgear/src/FDM/YASim/Version.cpp',
                'flightgear/src/FDM/YASim/yasim-common.cpp',
                'flightgear/src/FDM/YASim/yasim-test.cpp',
                ]
        for i in ret:
            if i.startswith( 'simgear/'):
                ret2.append( i)
        ret = ret2
    
    return all_files, ret


_cc_command_compare_regex = None

def cc_command_compare( a, b):
    '''
    Compares cc comamnds, ignoring differences in warning flags.
    
    >>> cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Wno-xyz -Werror')
    False
    >>> cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Werror')
    False
    >>> cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Wno-q -Werror')
    False
    >>> cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -O2 -Werror')
    1
    >>> cc_command_compare( 'cc -o foo bar.c -fmax-errors=10', 'cc -o foo bar.c -fmax-errors=11')
    False
    >>> cc_command_compare( 'cc -o foo bar.c -fmax-errors=10 l', 'cc -o foo bar.c l')
    False
    '''
    global _cc_command_compare_regex
    if _cc_command_compare_regex is None:
        _cc_command_compare_regex = re.compile( '( -Wno-[^ ]+)|( -std=[^ ]+)|( -fmax-errors=[^ ]+)')
    aa = re.sub( _cc_command_compare_regex, '', a)
    bb = re.sub( _cc_command_compare_regex, '', b)
    #print(f'aa={aa!r}')
    #print(f'bb={bb!r}')
    ret = aa != bb
    ret0 = a != b
    if not ret and ret0:
        pass
        #print( f'ignoring command diff:\n    {a}\n    {b}')
    if ret and not ret0:
        assert 0
    return ret


class CompileFlags:
    '''
    Compile flags for different parts of the source tree.
    '''
    def __init__( self):
        self.items = []
    
    def add( self, path_prefixes, flags):
        '''
        Add `flags` when compiling source files which start with any item in
        `path_prefixes`.
        '''
        assert flags == '' or flags.startswith( ' ')
        flags = flags.replace( ' -D ', ' -D')
        flags = flags.replace( ' -I ', ' -I')
        if isinstance( path_prefixes, str):
            path_prefixes = path_prefixes,
        self.items.append( ( path_prefixes, flags))
    
    def get_flags( self, path):
        '''
        Returns compile flags to use when compiling `path`.
        '''
        ret = ''
        for path_prefixes, flags in self.items:
            for path_prefix in path_prefixes:
                #walk.log( f'looking at path_prefix: {path_prefix}')
                if path.startswith( path_prefix):
                    #walk.log( f'adding flags: {flags}')
                    ret += flags
                    break
        return ret
    
    def get_flags_all( self, path):
        '''
        Returns compile flags for compiling `path`, using a union of all flags
        (except for warning flags which are still calculated specifically for
        `path`).
        '''
        ret_flags = set()
        ret = ''
        ret_warnings = ''
        for path_prefixes, flags in self.items:
            match = False
            for path_prefix in path_prefixes:
                if path.startswith( path_prefix):
                    match = True
                    break
            for flag in flags.split():
                flag = flag.strip()
                if flag in ret_flags:
                    continue
                is_warning = flag.startswith( '-W')
                if is_warning:
                    if match:
                        ret_flags.add( flag)
                        ret_warnings += f' {flag}'
                else:
                    # Change '-DFOO' to '-D FOO' etc. Not sure why we do this.
                    ret_flags.add( flag)
                    for prefix in 'DI':
                        if flag.startswith( '-'+prefix):
                            flag = f'-{prefix} {flag[2:]}'
                    ret += f' {flag}'
                    
        return ret + ret_warnings


def make_compile_flags( libs_cflags, cpp_feature_defines):
    '''
    Returns a `CompileFlags` instance set up for building Flightgear.
    
    `(libs_cflags, cpp_feature_defines)` are particular pre-defined flags that
    our caller passes to us that have been found by running config tests and/or
    pkg-add.
    '''     
    cf = CompileFlags()
    
    cf.add( ('openscenegraph/'),
            ' -DOSG_LIBRARY -Dosg_EXPORTS -I openscenegraph/include -isystem /usr/X11R6/include -Wno-deprecated-copy',
            )
    
    cf.add( ('openscenegraph/src/osgTerrain/GeometryTechnique.cpp'),
            ' -D WALKFG_OSG',
            )
    
    cf.add( ('openscenegraph/src/osgPlugins/zip'),
            ' -D ZIP_STD',
            )

    cf.add(
            'openscenegraph/src/osgUtil/tristripper/src/',
            ' -I openscenegraph/src/osgUtil/tristripper/include',
            )
    
    cf.add(
            'openscenegraph/src/osgPlugins/osc/',
            ' -I openscenegraph/src/osgPlugins/osc',
            )
    
    cf.add(
            'openscenegraph/src/osgPlugins/txp/',
            ' -I openscenegraph/src/osgPlugins/txp',
            )
    
    cf.add(
            'openscenegraph/src/osgPlugins/freetype/',
            ' -I /usr/include/freetype2',
            )
    
    cf.add( (
            'flightgear/',
            'simgear/',
            ),
            ' -Wno-deprecated-copy'
            )

    cf.add( (
            'flightgear/3rdparty/cjson/cJSON.c',
            'flightgear/3rdparty/iaxclient/lib/gsm/src/rpe.c',
            'flightgear/3rdparty/sqlite3/sqlite3.c',
            'flightgear/src/FDM/JSBSim/JSBSim.cxx',
            'flightgear/src/GUI/FGQmlPropertyNode.cxx',
            'flightgear/src/MultiPlayer/multiplaymgr.cxx',
            'flightgear/src/Radio/itm.cpp',
            'flightgear/src/Radio/itm.cpp',
            'flightgear/src/Viewer/PUICamera.cxx',
            'simgear/3rdparty/expat/xmlparse.c',
            'simgear/3rdparty/expat/xmltok_impl.c',
            'simgear/simgear/canvas/ShivaVG/src/shGeometry.c',
            'simgear/simgear/canvas/ShivaVG/src/shPipeline.c',
            ),
            ' -Wno-implicit-fallthrough'
            )
    
    if g_clang or g_openbsd:
        cf.add( (
                'flightgear/',
                'simgear/',
                'plib/',
                ),
                    ' -Wno-inconsistent-missing-override'
                    ' -Wno-overloaded-virtual'
                    ' -Wno-macro-redefined'
                )
        cf.add(
                '',
                ' -Wno-deprecated-copy'
                ' -Wno-implicit-int-float-conversion'   # osg-3.6's template<class ValueType> struct range
                )
    
    cf.add( 'flightgear/',
            ' -D HAVE_CONFIG_H'
            )
    
    cf.add( (
            'flightgear/3rdparty/flite_hts_engine/flite/',
            'flightgear/3rdparty/hts_engine_API/lib',
            'flightgear/3rdparty/iaxclient/lib',
            'flightgear/3rdparty/iaxclient/lib/gsm/src/preprocess.c',
            'flightgear/src/GUI',
            'flightgear/src/Navaids/FlightPlan.cxx',
            'simgear/simgear/canvas/elements/CanvasImage.cxx',
            'simgear/simgear/canvas/layout/',
            'simgear/simgear/nasal/codegen.c',
            'simgear/simgear/nasal/iolib.c',
            'simgear/simgear/nasal/parse.c',
            'simgear/simgear/nasal/utf8lib.c',
            'simgear/simgear/nasal/utf8lib.c',
            ),
            ' -Wno-sign-compare'
            )
    cf.add( (
            'flightgear/3rdparty/iaxclient/lib/iaxclient_lib.c',
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c',
            'flightgear/3rdparty/iaxclient/lib/unixfuncs.c',
            'flightgear/3rdparty/sqlite3/sqlite3.c',
            ),
            ' -Wno-cast-function-type'
            )
    cf.add( (
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax2-parser.c',
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c',
            'flightgear/3rdparty/mongoose/mongoose.c',
            'flightgear/src/Airports/runways.cxx',
            'flightgear/src/ATC/trafficcontrol.cxx',
            'flightgear/src/FDM/ExternalNet/ExternalNet.cxx',
            'flightgear/src/FDM/LaRCsim/ls_interface.c',
            'flightgear/src/GUI/gui_funcs.cxx',
            'flightgear/src/Instrumentation/clock.cxx',
            'flightgear/src/Instrumentation/gps.cxx',
            'flightgear/src/Instrumentation/KLN89/kln89_page_alt.cxx',
            'flightgear/src/Instrumentation/KLN89/kln89_page_apt.cxx',
            'flightgear/src/Instrumentation/KLN89/kln89_page_cal.cxx',
            'flightgear/src/Instrumentation/kr_87.cxx',
            'flightgear/src/Network/atlas.cxx',
            'flightgear/src/Network/nmea.cxx',
            ),
            ' -Wno-format-truncation'
            )


    cf.add( (
            'flightgear/src/FDM/YASim/',
            'flightgear/src/Radio/itm.cpp',
            'simgear/simgear/structure/SGExpression.cxx',
            'simgear/simgear/structure/subsystem_mgr.cxx',
            ),
            ' -Wno-unused-variable'
            )

    cf.add( (
            'flightgear/3rdparty/flite_hts_engine/flite/src',
            'flightgear/src/Radio/itm.cpp',
            'simgear/simgear/structure/SGExpression.cxx',
            'simgear/simgear/structure/subsystem_mgr.cxx',
            ),
            ' -Wno-unused-function'
            )

    cf.add( (
            'flightgear/3rdparty/flite_hts_engine/flite/src/lexicon/cst_lexicon.c',
            ),
            ' -Wno-discarded-qualifiers'
            )

    cf.add( (
            'flightgear/3rdparty/iaxclient/lib/gsm/src/short_term.c',
            'flightgear/3rdparty/iaxclient/lib/libspeex/bits.c',
            ),
            ' -Wno-shift-negative-value'
            )

    cf.add( (
            'flightgear/3rdparty/iaxclient/lib/iaxclient_lib.c',
            'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c',
            ),
            ' -Wno-stringop-truncation'
            )

    cf.add( (
            'simgear/3rdparty/expat/xmltok.c',
            ),
            ' -Wno-missing-field-initializers'
            )

    cf.add( '', libs_cflags)

    # Include/define flags.

    cf.add( (
             'flightgear/',
            f'{g_outdir}/flightgear/',
             'simgear/',
            f'{g_outdir}/simgear/',
            f'{g_outdir}/walk-generated/flightgear/',
            ),
            cpp_feature_defines
            )

    cf.add( (
             'flightgear/',
            f'{g_outdir}/flightgear/',
            ),
             ' -I simgear'
             ' -I flightgear/src'
            f' -I {g_outdir}/walk-generated'
             ' -D ENABLE_AUDIO_SUPPORT'
            )

    cf.add( (
            'flightgear/src/',
            ),
            ' -I flightgear/3rdparty/cjson'
            ' -I flightgear/3rdparty/cjson'
            ' -I flightgear/3rdparty/iaxclient/lib'
            ' -I flightgear/3rdparty/mongoose'
            )

    cf.add( (
            'flightgear/src/AIModel/',
            ),
            ' -I flightgear'
            )

    cf.add(
            'flightgear/3rdparty/iaxclient'
            ,
            ' -I flightgear/3rdparty/iaxclient/lib/portaudio/bindings/cpp/include'
            ' -I flightgear/3rdparty/iaxclient/lib/portaudio/include'
            ' -I flightgear/3rdparty/iaxclient/lib/libiax2/src'
            ' -I flightgear/3rdparty/iaxclient/lib/portmixer/px_common'
            ' -I flightgear/3rdparty/iaxclient/lib/gsm/inc'
            ' -D LIBIAX'
            ' -D AUDIO_OPENAL'
            ' -D ENABLE_ALSA'
            )
    if g_linux:
        cf.add(
                'flightgear/3rdparty/iaxclient'
                ,
                ' -I flightgear/3rdparty/iaxclient/lib/libspeex/include'
                )

    if g_linux:
        cf.add(
                'flightgear/3rdparty/iaxclient/lib/audio_openal.c'
                ,
                ' -I /usr/include/AL'
                )

    if g_openbsd:
        cf.add(
                'flightgear/3rdparty/iaxclient/lib/audio_openal.c'
                ,
                ' -I /usr/local/include/AL'
                )

    cf.add( 'flightgear/3rdparty/joystick'
            ,
            ' -I flightgear/3rdparty/joystick/lib/portaudio/bindings/cpp/include'
            ' -I flightgear/3rdparty/joystick/lib/portaudio/include'
            )

    cf.add( 'flightgear/src/FDM/JSBSim/'
            ,
            ' -I flightgear/src/FDM/JSBSim'
            )

    cf.add( 'flightgear/src/FDM/'
            ,
            ' -I flightgear/src/FDM/JSBSim'
            )

    cf.add( 'flightgear/src/FDM/JSBSim/FGJSBBase.cpp'
            ,
            ' -D JSBSIM_VERSION="\\"compiled from FlightGear 2020.2.0\\""'
            )

    cf.add( (
            f'flightgear/src/GUI/',
            f'{g_outdir}/flightgear/src/GUI/',
            ),
            f' -I {g_outdir}/walk-generated/Include'
            f' -I flightgear/3rdparty/fonts'
            f' -I {g_outdir}/flightgear/src/GUI'
            )

    cf.add( 'flightgear/src/Input/',
            ' -I flightgear/3rdparty/hidapi'
            ' -I flightgear/3rdparty/joystick'
            )

    cf.add( 'flightgear/3rdparty/fonts/',
            f' -I {g_outdir}/walk-generated/plib-include'
            )

    cf.add( 'flightgear/3rdparty/hidapi/',
            ' -I flightgear/3rdparty/hidapi/hidapi'
            )

    cf.add( 'flightgear/src/Instrumentation/HUD/',
            ' -I flightgear/3rdparty/fonts'
            f' -I {g_outdir}/walk-generated/plib-include'
            f' -I {g_outdir}/walk-generated/plib-include/plib'
            )


    if g_linux:
        cf.add( 'flightgear/src/Airports/',
                ' -DBOOST_BIMAP_DISABLE_SERIALIZATION -DBOOST_NO_STDLIB_CONFIG -DBOOST_NO_AUTO_PTR -DBOOST_NO_CXX98_BINDERS'
                )

    cf.add( 'flightgear/src/Main/',
            ' -I flightgear'
            f' -I {g_outdir}/walk-generated/Include'
            )

    cf.add( 'flightgear/src/MultiPlayer',
            ' -I flightgear'
            )

    cf.add( 'flightgear/src/Navaids',
            ' -I flightgear/3rdparty/sqlite3'
            )

    cf.add('flightgear/src/Network',
            ' -I flightgear'
            f' -I {g_outdir}/walk-generated/Include'
            )
    
    cf.add( 'flightgear/src/Scripting/ClipboardX11.cxx',
            ' -D FLIGHTGEAR_WALK'
            )

    cf.add( 'flightgear/src/Sound',
            ' -I flightgear/3rdparty/flite_hts_engine/include'
            ' -I flightgear/3rdparty/hts_engine_API/include'
            )

    cf.add( 'flightgear/src/Cockpit',
            ' -I flightgear/3rdparty/fonts'
            )

    cf.add( 'simgear/simgear/canvas/ShaderVG',
            ' -I simgear/simgear/canvas/ShaderVG/include'
            )
    
    cf.add( 'simgear/simgear/',
            ' -I simgear'
            ' -I simgear/simgear/canvas/ShivaVG/include'
            ' -I simgear/3rdparty/udns'
            f' -I {g_outdir}/walk-generated'
            f' -I {g_outdir}/walk-generated/simgear'
            )

    cf.add( (
            'simgear/simgear/canvas/Canvas.cxx',
            'flightgear/src/AIModel/AIBase.cxx',
            ),
            cpp_feature_defines
            )

    cf.add( 'simgear/simgear/sound',
            ' -D ENABLE_SOUND'
            )

    cf.add( 'simgear/simgear/xml',
            ' -I simgear/3rdparty/expat'
            )

    cf.add('simgear/3rdparty/expat',
            ' -D HAVE_MEMMOVE'
            )

    cf.add('simgear/simgear/scene/model',
            ' -I simgear/3rdparty/tiny_gltf'
            )

    cf.add('plib/',
            ' -I plib/src/fnt'
            ' -I plib/src/sg'
            ' -I plib/src/util'
            ' -I plib/src/pui'
            ' -Wno-dangling-else'
            ' -Wno-empty-body'
            ' -Wno-extra'
            ' -Wno-format-overflow'
            ' -Wno-ignored-qualifiers'
            ' -Wno-implicit-fallthrough'
            ' -Wno-int-to-pointer-cast'
            ' -Wno-maybe-uninitialized'
            ' -Wno-misleading-indentation'
            ' -Wno-missing-field-initializers'
            ' -Wno-missing-field-initializers'
            ' -Wno-parentheses'
            ' -Wno-restrict'
            ' -Wno-stringop-overflow'
            ' -Wno-stringop-truncation'
            ' -Wno-stringop-truncation'
            ' -Wno-type-limits'
            ' -Wno-unused-but-set-variable'
            ' -Wno-unused-function'
            ' -Wno-unused-variable'
            ' -Wno-write-strings'
            ' -D register=' # register causes errors with clang and C++17.
            )

    if g_openbsd:
        cf.add( 'plib/',
            ' -I /usr/X11R6/include'
            )

    cf.add( 'plib/src/ssgAux',
            ' -I plib/src/ssg'
            )

    cf.add( f'{g_outdir}/walk-generated/EmbeddedResources',
            ' -I simgear'
            )

    cf.add( 'flightgear/3rdparty/flite_hts_engine',
            ' -I flightgear/3rdparty/flite_hts_engine/flite/include'
            ' -I flightgear/3rdparty/flite_hts_engine/include'
            ' -I flightgear/3rdparty/hts_engine_API/include'
            ' -I flightgear/3rdparty/flite_hts_engine/flite/lang/usenglish'
            ' -I flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex'
            ' -D FLITE_PLUS_HTS_ENGINE'
            )

    cf.add( 'flightgear/3rdparty/hts_engine_API/lib',
            ' -I flightgear/3rdparty/hts_engine_API/include'
            )


    cf.add( 'simgear/simgear/canvas/',
            ' -D HAVE_INTTYPES_H'
            )

    cf.add( (
            'flightgear/src/ATC/',
            'flightgear/src/Cockpit/',
            'flightgear/src/GUI/',
            'flightgear/src/Main/',
            'flightgear/src/Model/',
            'flightgear/src/Viewer/',
            ),
            f' -I {g_outdir}/walk-generated/plib-include'
            + f' -I {g_outdir}/walk-generated/plib-include/plib'
            )
    
    # Cmake build puts FG_HAVE_GPERFTOOLS in config.h, but this requires
    # complete rebuild if changed, so we make it specific to the code that
    # actually refers to it.
    cf.add( (
            'flightgear/src/Main/fg_commands.cxx',
            'src/Main/fg_scene_commands.cxx',
            ),
            f' -D FG_HAVE_GPERFTOOLS={g_gperf}'
            )
    
    cf.add( (
            'flightgear/test_suite/',
            ),
            ' -I flightgear/3rdparty/cppunit/include'
            ' -I flightgear'
            )
    cf.add( (
            'flightgear/3rdparty/cppunit/',
            'flightgear/test_suite/',
            ),
            # Show complete pathname in cppunit assert failures.
            ' -D CPPUNIT_COMPILER_LOCATION_FORMAT=\'"%p:%l: "\''
            )
    
    cf.add( (
            'flightgear/test_suite/system_tests/FDM',
            'flightgear/test_suite/simgear_tests/math',
            ),
            ' -I flightgear/src/FDM/JSBSim'
            f' -I {g_outdir}/walk-generated/plib-include'
            )
    
    cf.add( (
            'flightgear/3rdparty/cppunit/'
            ),
            ' -I flightgear/3rdparty/cppunit/include'
            )
    
    cf.add( 'simgear/simgear/screen/video-encoder.cxx',
            ' -D SG_FFMPEG'
            )

    return cf


class Timing:
    '''
    Internal item for `Timings` class.
    '''
    def __init__( self, name):
        self.name = name
        self.parent = None
        self.children = []
        self.t_begin = time.time()
        self.t_end = None
    def end( self, t):
        assert self.t_end is None
        self.t_end = t
    def get( self):
        assert self.t_end is not None
        return self.t_end - self.t_begin

class Timings:
    '''
    Allows gathering of hierachical timing information. Can also generate useful
    diagnostics.
    
    Caller can generate a tree of `Timing` items via our `.begin()` and `.end()`
    methods.
    
    >>> ts = Timings()
    >>> ts.begin('a')
    >>> time.sleep(0.1)
    >>> ts.begin('b')
    >>> time.sleep(0.2)
    >>> ts.begin('c')
    >>> time.sleep(0.3)
    >>> ts.end('b') # will also end 'c'.
    >>> ts.begin('d')
    >>> ts.begin('e')
    >>> time.sleep(0.1)
    >>> ts.end()    # will end everything.
    >>> print(ts)
    Timings (in seconds):
        0.7 a
            0.5 b
                0.3 c
            0.1 d
                0.1 e
    <BLANKLINE>
    '''
    def __init__( self):
        self.current = None # Points to most recent in-progress item.
        self.first = None   # Points to top item.
        self.name_max_len = 0
    
    def begin( self, name, text=None, level=0):
        '''
        Starts a new timing item as child of most recent in-progress timing
        item.
        
        name:
            Used in final statistics.
        text:
            If not `None`, this is output here with `walk.log()`.
        level:
            Verbosity. Added to `g_verbose`.
        '''
        if g_verbose + level >= 1 and text is not None:
            walk.log( f'{text}')
        self.name_max_len = max( self.name_max_len, len(name))
        new_timing = Timing( name)
        
        if self.current:
            if self.current.t_end is None:
                # self.current is in progress, so add new child item.
                new_timing.parent = self.current
                for c in self.current.children:
                    assert c.t_end is not None
                self.current.children.append( new_timing)
            else:
                # self.current is complete so create sibling.
                assert self.current.parent
                new_timing.parent = self.current.parent
                new_timing.parent.children.append( new_timing)
        else:
            # First item.
            self.first = new_timing
        
        self.current = new_timing
    
    def end( self, name=None):
        '''
        Ends currently-running timing and its parent items until we reach one
        matching `name`.
        '''
        # end all until we have reached <name>.
        t = time.time()
        while self.current:
            name2 = self.current.name
            self.current.end( t)
            self.current = self.current.parent
            if name2 == name:
                break
        else:
            if name is not None:
                walk.log( f'*** Warning: cannot end timing item called {name} because not found.')
        #walk.log( f'< {name}')
    
    def text( self, t, depth):
        '''
        Returns text showing hierachical timing information.
        '''
        ret = ''
        ret += ' ' * 4 * depth + f' {t.get():6.1f} {t.name}\n'
        for child in t.children:
            ret += self.text( child, depth + 1)
        return ret
    
    def __str__( self):
        ret = 'Timings (in seconds):\n'
        ret += self.text( self.first, 0)
        return ret


def do_compile(target, walk_concurrent, cc_base, cpp_base, cf, path, preprocess=False, force=None):
    '''
    Schedules compile of `path` (if necessary). Returns name of `.o` file.
    
    target:
        One of:
            fgfs
            test-suite
            ...
        walk_concurrent
            A walk.Concurrent instance.
        cc_base
            Base cc compiler command.
        cpp_base
            Base c++ compiler command.
        cf
            A CompileFlags instance.
        path
            Source file to compile.
        preprocess
            If true, generate preprocessed output, don't compile.
    '''
    assert isinstance( cf, CompileFlags)
    
    if path.endswith( '.c'):
        command = cc_base
    else:
        command = cpp_base

    if preprocess:
        command += ' -E'
    else:
        command += ' -c'

    path_o = f'{g_outdir}/{path}'

    if target == 'test-suite':
        # Most .o files are identical to a fgfs build.
        if path in (
                #'flightgear/src/Airports/airport.cxx',
                'flightgear/src/Main/sentryIntegration.cxx',
                'flightgear/src/Scripting/NasalSys.cxx',
                ):
            path_o += ',test-suite'
            command += ' -D BUILDING_TESTSUITE'

    if g_clang:
        path_o += ',clang'
    if g_build_debug:
        command += ' -g -gsplit-dwarf'
        path_o += ',debug'
    if g_frame_pointer:
        command += ' -fno-omit-frame-pointer'
        path_o += ',fp'
    
    optimise = g_build_optimise
    for o, prefix in g_optimise_prefixes:
        #walk.log( f'o={o!r} prefix={prefix!r}')
        if path.startswith( prefix):
            walk.log( f'Forcing optimise={o} for path={path}')
            optimise = o
    if optimise:
        command += ' -O3 -msse2 -mfpmath=sse -ftree-vectorize -ftree-slp-vectorize'
        path_o += ',opt'
    if 0 and g_build_optimise:
        # Allow selected files to be compiled without optimisation to
        # help debugging.
        if path in [
                #'flightgear/src/AIModel/AIMultiplayer.cxx',
                #'flightgear/src/Aircraft/controls.cxx',
                #'flightgear/src/Aircraft/replay.cxx',
                #'flightgear/src/Autopilot/pidcontroller.cxx',
                #'flightgear/src/FDM/YASim/ControlMap.cpp',
                #'flightgear/src/FDM/YASim/FGFDM.cpp',
                #'flightgear/src/GUI/FGPUIDialog.cxx',
                #'flightgear/src/GUI/FGPUIMenuBar.cxx',
                #'flightgear/src/Main/locale.cxx',
                #'flightgear/src/Main/options.cxx',
                #'flightgear/src/Network/fgcom.cxx',
                #'flightgear/src/Time/TimeManager.cxx',
                #'flightgear/src/Viewer/fg_os_osgviewer.cxx',
                #'flightgear/src/Viewer/renderer.cxx',
                #'flightgear/src/Viewer/sview.cxx',
                #'flightgear/src/Viewer/viewmgr.cxx',
                #'simgear/simgear/props/props.cxx',
                #'simgear/simgear/props/props.cxx',
                #'simgear/simgear/props/props.cxx',
                #'simgear/simgear/scene/model/particles.cxx',
                #'simgear/simgear/scene/viewer/CompositorPass.cxx',                
                #'simgear/simgear/screen/video-encoder.cxx',
                #'flightgear/src/FDM/YASim/Gear.cpp',
                ]:
            walk.log(f'*** not optimising {path}')
            command += ' -ggdb'
        else:
            command += ' -O3 -msse2 -mfpmath=sse -ftree-vectorize -ftree-slp-vectorize'
            path_o += ',opt'

    if g_osg_dir:
        path_o += ',osg'
        command += f' -I {g_osg_dir}/include'

    if g_flags_all:
        path_o += ',flags-all'
        command = command + cf.get_flags_all( path)
    else:
        command = command + cf.get_flags( path)
    
    if not g_props_locking:
        path_o += ',sgunsafe'
        command = command + ' -D SG_PROPS_UNTHREADSAFE'

    if preprocess:
        path_o += os.path.splitext( path)[1]
    else:
        path_o += '.o'

    if g_link_only:
        doit = False
        reason = None
        e = None
    else:
        command += f' -o {path_o} {path}'
        if path in g_verbose_srcs:
            walk.log(f'command is: {command}')

        # Tell walk to schedule running of the compile command if necessary.
        #
        doit, reason, e = system_concurrent(
                walk_concurrent,
                command,
                f'{path_o}.walk',
                description=f'Compiling to {path_o}',
                command_compare=cc_command_compare,
                )
    
    return path_o, doit, reason, e


def cc_version(cc):
    t = subprocess.check_output(f'{cc} -dumpfullversion', shell=1, text=True)
    t = t.strip()
    t = t.split('.')
    #walk.log(f'cc={cc!r} returning: {t}')
    return t


def compilers_base():
    # Set up compile/link commands.
    #
    cc_base = 'cc'
    cpp_base = 'c++'
    
    if g_linux:
        if cc_version(cpp_base)[0] == '10':
            # g++-10 get internal errors for some files.
            walk.log(f'Forcing gcc-9 and g++-9')
            cpp_base = 'g++-9'
            cc_base = 'gcc-9'
    
    if g_clang:
        cc_base = 'clang'
        cpp_base = 'clang++'
    
    if g_clang or g_openbsd:
        cc_base += ' -Wno-unknown-warning-option'
        cpp_base += ' -std=c++17 -Wno-unknown-warning-option'
    else:
        cpp_base += ' -std=gnu++17 -fmax-errors=10'
    
    cc_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    cpp_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    
    #walk.log( f'returning cpp_base={cpp_base!r}')
    return cc_base, cpp_base


def get_cpp_feature_defines( timings, cpp_base):
    '''
    Returns string containing list of `-D` options, from running tests
    extracted (crudely with regex) from `.cmake` file.
    '''
    cpp_feature_defines = ''
    if g_openbsd:
        path = 'simgear/CMakeModules/CheckCXXFeatures.cmake'
        timings.begin( 'cpp-features', f'Running tests from {path}.')
        with open( path) as f:
            text = f.read()
        for m in re.finditer('check_cxx_source_compiles[(]"([^"]*)" ([A-Z_]+)', text, re.M):
            code = m.group(1)
            define = m.group(2)
            if g_verbose >= 3:
                walk.log( f'Testing for {define}')
            with open( f'{g_outdir}/test.cpp', 'w') as f:
                f.write(code)
            e = os.system( f'{cpp_base} -o /dev/null {g_outdir}/test.cpp 1>/dev/null 2>/dev/null')
            if e == 0:
                if g_verbose >= 2:
                    walk.log( f'defining     {define}')
                cpp_feature_defines += f' -D {define}'
            else:
                if g_verbose >= 2:
                    walk.log( f'not defining {define}')
                pass
        timings.end( 'cpp-features')
    return cpp_feature_defines


def get_lib_flags():
    '''
    Returns `(libs, libs_cflags, libs_linkflags)`:
        libs
            List of libraries we should link with.
        libs_cflags
            Compile flags from `pkg-config` for `libs`.
        libs_linkflags
            Link flags from `pkg-config` for `libs`.
    '''
    # Libraries for which we call pkg-config:
    #
    # On OpenBSD, qt requires -L/usr/local/lib but pkg-config Qt* doesn't
    # provide it. However "pkg-config dbus-1" provides it.
    #
    libs = (
            ' Qt5Core'
            ' Qt5Gui'
            ' Qt5Qml'
            ' Qt5Quick'
            ' Qt5Widgets'
            ' dbus-1'
            ' gl'
            ' x11'
            ' liblzma'
            ' expat'
            )
    if not g_osg_dir:
        libs += ' openscenegraph'
    
    if g_openbsd:
        libs += (
                ' glu'
                ' libcurl'
                ' libevent'
                ' openal'
                ' speex'
                ' speexdsp'
                )
    
    libs_cflags     = ' ' + subprocess.check_output( f'pkg-config --cflags {libs}', shell=1).decode( 'latin-1').strip()
    libs_linkflags  = ' ' + subprocess.check_output( f'pkg-config --libs {libs}', shell=1).decode( 'latin-1').strip()
    return libs, libs_cflags, libs_linkflags


def preprocess( timings, target, path, walk_=None):
    '''
    Preprocess `path`, writing to `<target>.c` or `<target>.cpp`.

    Uses same code as for normal compilation, so should be representative.
    '''
    walk.log( f'preprocess target={target} path={path}')
    cc_base, cpp_base = compilers_base()
    libs, libs_cflags, libs_linkflags = get_lib_flags()
    cpp_feature_defines = get_cpp_feature_defines( timings, cpp_base)
    cf = make_compile_flags( libs_cflags, cpp_feature_defines)
    
    path_o, doit, reason, e = do_compile(
            target,
            walk_,
            cc_base,
            cpp_base,
            cf,
            path,
            preprocess=True,
            )

def build( timings, target):
    '''
    Builds `target` using `g_*` settings.
    
    target:
        One of:
            fgfs
            test-suite
            props-test
    '''
    timings.begin( 'all', f'Building target={target}.', 2)
    
    timings.begin( 'pre')
    if g_openbsd:
        # clang needs around 2G to compile
        # flightgear/src/Scripting/NasalCanvas.cxx.
        #
        soft, hard = resource.getrlimit( resource.RLIMIT_DATA)
        required = min(4*2**30, hard)
        if soft < required:
            if hard < required:
                walk.log( f'Warning: RLIMIT_DATA hard={hard} is less than required={required}.')
            soft_new = min(hard, required)
            resource.setrlimit( resource.RLIMIT_DATA, (soft_new, hard))
            if g_verbose >= 2:
                walk.log( f'Have changed RLIMIT_DATA from {soft} to {soft_new}.')

    timings.begin( 'get_files', 'Finding git source files.')
    all_files, src_fgfs = get_files( target)
    timings.end( 'get_files')

    if target != 'props-test' and target != 'yasim-test':
        
        # Run various commands to patch source code or run moc etc. We use
        # our system() which uses walk.system(), so after the first build we
        # usually end up not running any external commands.
        
        # Create patched version of plib/src/sl/slDSP.cxx.
        path = 'plib/src/sl/slDSP.cxx'
        timings.begin( 'plib-patch', f'Patching: {path}')
        path_patched = path + '-patched.cxx'
        with open(path) as f:
            text = f.read()
        text = text.replace(
                '#elif (defined(UL_BSD) && !defined(__FreeBSD__)) || defined(UL_SOLARIS)',
                '#elif (defined(UL_BSD) && !defined(__FreeBSD__) && !defined(__OpenBSD__)) || defined(UL_SOLARIS)',
                )
        walk.file_write( text, path_patched)
        src_fgfs.remove(path)
        src_fgfs.append( path_patched)
        timings.end( 'plib-patch')

        # Generate .moc files. We look for files containing Q_OBJECT.
        #
        timings.begin( 'moc', 'Generating Moc files.')
        moc = 'moc'
        if g_openbsd:
            moc = 'moc-qt5'
        for i in all_files:
            if i.startswith( 'flightgear/src/GUI/') or i.startswith( 'flightgear/src/Viewer/'):
                i_base, ext = os.path.splitext( i)
                if ext in ('.h', '.hxx', '.hpp'):
                    with open( i) as f:
                        text = f.read()
                    if 'Q_OBJECT' in text:
                        cpp_file = f'{g_outdir}/{i}.moc.cpp'
                        system(
                                f'{moc} {i} -o {cpp_file}',
                                f'{cpp_file}.walk',
                                f'Running moc on {i}',
                                )
                        src_fgfs.append( cpp_file)
                elif ext in ('.cpp', '.cxx'):
                    #walk.log( f'checking {i}')
                    with open( i) as f:
                        text = f.read()
                    if re.search( '\n#include ".*[.]moc"\n', text):
                        #walk.log( f'running moc on: {i}')
                        moc_file = f'{g_outdir}/{i_base}.moc'
                        system(
                                f'{moc} {i} -o {moc_file}',
                                f'{moc_file}.walk',
                                f'Running moc on {i}',
                                )
        timings.end( 'moc')

        # Create various header files. We use our file_write() which ensure
        # that files are not written if they already contain the required
        # content.
        #

        # Create flightgear's config.h file.
        #
        timings.begin( 'config', 'Generating misc headers/source files.')
        fg_version = open('flightgear/flightgear-version').read().strip()
        fg_version_major, fg_version_minor, fg_version_tail = fg_version.split('.')
        root = os.path.abspath( '.')

        file_write( textwrap.dedent(f'''
                #pragma once
                #define FLIGHTGEAR_VERSION "{fg_version}"
                #define FLIGHTGEAR_MAJOR_VERSION "{fg_version_major}"
                #define FLIGHTGEAR_MINOR_VERSION "{fg_version_minor}"
                #define VERSION    "{fg_version}"
                #define PKGLIBDIR  "{root}/fgdata"
                #define FGSRCDIR   "{root}/flightgear"
                #define FGBUILDDIR "{g_outdir}"

                /* #undef FG_NDEBUG */

                #define ENABLE_SIMD
                #define ENABLE_SP_FDM
                #define JSBSIM_USE_GROUNDREACTIONS

                // JSBSim needs this, to switch from standalone to in-FG mode
                #define FGFS

                #define PU_USE_NONE // PLIB needs this to avoid linking to GLUT

                #define ENABLE_PLIB_JOYSTICK

                // threads are required (used to be optional)
                #define ENABLE_THREADS 1

                // audio support is assumed
                #define ENABLE_AUDIO_SUPPORT 1

                #define HAVE_SYS_TIME_H
                /* #undef HAVE_WINDOWS_H */
                #define HAVE_MKFIFO

                #define HAVE_VERSION_H 1 // version.h is assumed for CMake builds

                #define ENABLE_UIUC_MODEL
                #define ENABLE_LARCSIM
                #define ENABLE_YASIM
                #define ENABLE_JSBSIM

                #define WEB_BROWSER "sensible-browser"

                // Ensure FG_HAVE_xxx always have a value
                #define FG_HAVE_HLA ( + 0)
                //#define FG_HAVE_GPERFTOOLS {g_gperf}

                /* #undef SYSTEM_SQLITE */

                #define ENABLE_IAX

                #define HAVE_DBUS

                #define ENABLE_HID_INPUT
                #define ENABLE_PLIB_JOYSTICK

                #define HAVE_QT

                #define HAVE_SYS_TIME_H
                //#define HAVE_SYS_TIMEB_H
                #define HAVE_TIMEGM
                #define HAVE_DAYLIGHT
                //#define HAVE_FTIME
                #define HAVE_GETTIMEOFDAY

                #define FG_TEST_SUITE_DATA "{root}/flightgear/test_suite/test_data"

                #define FG_BUILD_TYPE "Dev"

                #define HAVE_PUI

                // Seems to need fgdata at build time?
                //#define HAVE_QRC_TRANSLATIONS

                #define ENABLE_SWIFT

                /* #undef HAVE_SENTRY */
                #define SENTRY_API_KEY ""
                '''
                ),
                f'{g_outdir}/walk-generated/config.h',
                )


        # Create simgear's config.h file.
        #
        file_write( textwrap.dedent(
                '''
                #define HAVE_GETTIMEOFDAY
                #define HAVE_TIMEGM
                #define HAVE_SYS_TIME_H
                #define HAVE_UNISTD_H
                #define HAVE_STD_INDEX_SEQUENCE 1
                ''')
                ,
                f'{g_outdir}/walk-generated/simgear/simgear_config.h',
                )

        # Create various other headers.
        #
        file_write(
                f'#define FLIGHTGEAR_VERSION "{fg_version}"\n',
                f'{g_outdir}/walk-generated/Include/version.h',
                )

        git_id_text = git_id( 'flightgear').replace('"', '\\"')
        revision = ''
        revision += '#define JENKINS_BUILD_NUMBER 0\n'
        revision += '#define JENKINS_BUILD_ID "none"\n'
        revision += f'#define REVISION "{git_id_text}"\n'
        file_write(
                revision,
                f'{g_outdir}/walk-generated/Include/build.h',
                )
        file_write(
                revision,
                f'{g_outdir}/walk-generated/Include/flightgearBuildId.h',
                )

        file_write(
                '#pragma once\n' + 'void initFlightGearEmbeddedResources();\n',
                f'{g_outdir}/walk-generated/EmbeddedResources/FlightGear-resources.hxx',
                )

        # Generate FlightGear-resources.cxx.
        #
        # The cmake build builds and runs fgrcc to generate this file. But
        # actually it's easier to generate it directly here.
        #
        file_write( textwrap.dedent( '''
                // -*- coding: utf-8 -*-
                //
                // File automatically generated by walkfg.py instead of fgrcc.

                #include <memory>
                #include <utility>

                #include <simgear/io/iostreams/CharArrayStream.hxx>
                #include <simgear/io/iostreams/zlibstream.hxx>
                #include <simgear/embedded_resources/EmbeddedResource.hxx>
                #include <simgear/embedded_resources/EmbeddedResourceManager.hxx>

                using std::unique_ptr;
                using simgear::AbstractEmbeddedResource;
                using simgear::RawEmbeddedResource;
                using simgear::ZlibEmbeddedResource;
                using simgear::EmbeddedResourceManager;

                void initFlightGearEmbeddedResources()
                {
                  EmbeddedResourceManager::instance();
                }
                ''')
                ,
                f'{g_outdir}/walk-generated/EmbeddedResources/FlightGear-resources.cxx',
                )

        # When we generate C++ source files (not headers), we need to add them to
        # src_fgfs so they get compiled into the final executable.
        #

        src_fgfs.append( f'{g_outdir}/walk-generated/EmbeddedResources/FlightGear-resources.cxx')

        simgear_version = open('simgear/simgear-version').read().strip()
        file_write(
                f'#define SIMGEAR_VERSION {simgear_version}\n',
                f'{g_outdir}/walk-generated/simgear/version.h',
                )
        timings.end( 'config')

        timings.begin( 'rcc/uic', 'Generating Qt resources with rcc/uic.')
        rcc_in = f'flightgear/src/GUI/resources.qrc'
        rcc_out = f'{g_outdir}/walk-generated/flightgear/src/GUI/qrc_resources.cpp'
        if g_openbsd:
            system(
                    f'rcc -name resources -o {rcc_out} {rcc_in}',
                    f'{rcc_out}.walk',
                    f'Running rcc on {rcc_in}',
                    )
        else:
            system(
                    f'/usr/lib/qt5/bin/rcc --name resources --output {rcc_out} {rcc_in}',
                    f'{rcc_out}.walk',
                    f'Running rcc on {rcc_in}',
                    )
        src_fgfs.append( f'{rcc_out}')

        uic = 'uic'
        if g_openbsd:
            uic = '/usr/local/lib/qt5/bin/uic'
        system(
                f'{uic} -o {g_outdir}/walk-generated/Include/ui_InstallSceneryDialog.h'
                    f' flightgear/src/GUI/InstallSceneryDialog.ui'
                    ,
                f'{g_outdir}/walk-generated/Include/ui_InstallSceneryDialog.h.walk',
                f'Running uic on flightgear/src/GUI/InstallSceneryDialog.ui',
                )

        e = system(
                f'{uic} -o {g_outdir}/walk-generated/ui_SetupRootDialog.h'
                    f' flightgear/src/GUI/SetupRootDialog.ui'
                    ,
                f'{g_outdir}/walk-generated/ui_SetupRootDialog.h.walk',
                f'Running uic on flightgear/src/GUI/SetupRootDialog.ui',
                )
        timings.end( 'rcc/uic')

        # Set up softlinks that look like a plib install - some code requires plib
        # installation header tree.
        #
        timings.begin( 'plib-install', 'Setting up softlinks for plib install.')
        def find( root, leaf):
            for dirpath, dirnames, filenames in os.walk( root):
                if leaf in filenames:
                    return os.path.join( dirpath, leaf)
            assert 0

        dirname = f'{g_outdir}/walk-generated/plib-include/plib'
        command = f'mkdir -p {dirname}; cd {dirname}'
        for leaf in 'pw.h pu.h sg.h netSocket.h js.h ssg.h puAux.h sl.h sm.h sl.h psl.h ul.h pw.h ssgAux.h ssgaSky.h fnt.h ssgaBillboards.h net.h ssgMSFSPalette.h ulRTTI.h puGLUT.h'.split():
            path = find( 'plib/src', leaf)
            #walk.log(f'plib path: {path}')
            path = os.path.abspath( path)
            command += f' && ln -sf {path} {leaf}'
        os.system( command)
        timings.end( 'plib-install')
    
    cc_base, cpp_base = compilers_base()

    # On Linux we end up with compilation errors if we use the results of the
    # feature checking below. But things seem to build ok without.
    #
    # On OpenBSD, we need to do the feature checks, and they appear to work.
    #
    timings.begin( 'feature-check')
    cpp_feature_defines = get_cpp_feature_defines( timings, cpp_base)
    timings.end( 'feature-check')

    # Define compile/link commands. For linking, we write the .o filenames to a
    # separate file and use gcc's @<filename> to avoid the command becoming too
    # long.
    #
    link_command = cpp_base
    link_command += ' -rdynamic'    # So backtrace() and backtrace_symbols() see symbols.
    
    if target == 'fgfs':
        exe = f'{g_outdir}/fgfs'
    elif target == 'test-suite':
        exe = f'{g_outdir}/fgfs-test-suite'
    elif target == 'props-test':
        exe = f'{g_outdir}/fgfs-props-test'
    elif target == 'yasim-test':
        exe = f'{g_outdir}/fgfs-yasim-test'
    else:
        assert 0, f'Unrecognised target={target}'

    if g_clang:
        exe += ',clang'
    if g_build_debug:
        exe += ',debug'
        link_command += ' -g -gsplit-dwarf'
    if g_build_optimise:
        exe += ',opt'
        link_command += ' -O2'

    if g_osg_dir:
        exe += ',osg'
    
    if g_flags_all:
        exe += ',flags-all'
    
    if g_frame_pointer:
        exe += ',fp'
    
    if not g_props_locking:
        exe += ',sgunsafe'

    exe += '.exe'
    if g_verbose >= 1:
        walk.log( f'Executable is: {exe}')

    timings.begin( 'link-flags', 'Finding linker flags.')
    libs, libs_cflags, libs_linkflags = get_lib_flags()
    
    if 0:
        # Show linker information.
        link_command += ' -t'
        link_command += ' --verbose'
    
    link_command += f' -o {exe}'
    
    # 2021-05-22: used to put this at the end of the linker command but this
    # started failing with devuan-5.10.0-6-amd64 - seems like we need to put .o
    # files before .so files in the link command.
    #
    link_command_extra_path = f'{exe}-link-extra'
    link_command += f' @{link_command_extra_path}'
    
    # Other libraries, including OSG.
    #
    def find1(*globs):
        for g in globs:
            gg = glob.glob(g)
            if len(gg) == 1:
                return gg[0]
        raise Exception(f'Could not find match for {globs!r}')
    
    osg_libs = (
            'OpenThreads',
            'osg',
            'osgDB',
            'osgFX',
            'osgGA',
            'osgParticle',
            'osgSim',
            'osgTerrain',
            'osgText',
            'osgUtil',
            'osgViewer',
            
            'osgAnimation',
            'osgManipulator',
            'osgPresentation',
            'osgShadow',
            'osgUI',
            'osgVolume',
            'osgWidget',
            )
    
    if g_osg:
        pass
    elif g_osg_dir:
        libdir = find1(f'{g_osg_dir}/lib', f'{g_osg_dir}/lib64')
        for l in osg_libs:
            # Link with release-debug OSG libraries if available.
            lib = find1(
                    f'{libdir}/lib{l}rd.so.*.*.*',
                    f'{libdir}/lib{l}r.so.*.*.*',
                    f'{libdir}/lib{l}d.so.*.*.*',
                    f'{libdir}/lib{l}.so.*.*.*',
                    )
            link_command += f' {lib}'
    else:
        for l in osg_libs:
            link_command += f' -l {l}'
    
    if g_openbsd:
        link_command += (
                ' -l z'
                ' -l ossaudio'
                ' -l execinfo'  # for backtrace*().
                ' -l Xss'
                )
    
    if g_linux:
        link_command += (
                ' -l asound'
                ' -l curl'
                ' -l dbus-1'
                ' -l dl'
                ' -l event'
                ' -l udev'
                ' -l GL'
                ' -l GLU'
                ' -l glut'
                ' -l openal'
                ' -l z'
                ' -l Xss'
                
                # need with --osg?
                ' -l freetype'
                ' -l png'
                ' -l jpeg'
                ' -l tiff'
                
                ' -pthread'
                )

    # Things for ffmpeg. On Devuan, requires:
    #   sudo apt install libavcodec-dev libavutil-dev libswscale-dev libavformat-dev
    #
    if g_ffmpeg:
        link_command += (
                ' -l avcodec'
                ' -l avutil'
                ' -l swscale'
                ' -l avformat'
                #' -l avresample'
                #' -l avfilter'
                #' -l swresample'
                #' -Wl,--trace'
                )
        
    link_command += f' {libs_linkflags}'
    
    link_command_files = []
    timings.end( 'link-flags')

    timings.begin( 'source-sort', 'Sorting source files by mtime.')
    # Sort the source files by mtime so that we compile recently-modified ones
    # first, which helps save time when investigating/fixing compile failures.
    #
    src_fgfs.sort( key=lambda path: -walk.mtime( path))
    timings.end( 'source-sort')
    
    timings.end( 'pre')
    
    timings.begin( 'walk.Concurrent', 'Creating walk.Concurrent instance.')
    # Set things up so walk.py can run compile commands concurrently.
    #
    concurrency = g_concurrency
    max_load_average = g_max_load_average
    if concurrency is None:
        concurrency = multiprocessing.cpu_count()
        if g_verbose >= 0:
            walk.log( f'Using default concurrency of {concurrency}.')
    if max_load_average is None:
        max_load_average = concurrency * 2
        if g_verbose >= 0:
            walk.log( f'Using default max load average of {max_load_average}.')
    walk_concurrent = walk.Concurrent(
            concurrency,
            max_load_average=max_load_average,
            keep_going=g_keep_going,
            )
    timings.end( 'walk.Concurrent')
    
    timings.begin( 'compile-flags', 'Setting up compile-flags.')
    cf = make_compile_flags( libs_cflags, cpp_feature_defines)
    timings.end( 'compile-flags')

    try:

        # Compile each source file. While doing so, we also add to the final
        # link command.
        #
        timings.begin( 'compiling', 'Compiling.')

        timings.begin( 'compile-enqueing', 'Compile enqueing.')
        walk._log_last_t = 0    # Ensure we output 0% diagnostic for first file we look at.

        num_compiles_queued = 0
        for i, path in enumerate( src_fgfs):
        
            def get_progress():
                # We blend i/len(src_fgfs) with
                # walk_concurrent.num_commands_run / num_compiles_to_run.
                p = i / len(src_fgfs)
                if num_compiles_queued:
                    p = walk_concurrent.num_commands_run / (num_compiles_queued * len(src_fgfs)/i)
                else:
                    p = i / len(src_fgfs)
                return p
            _log_prefix.progress = get_progress
                      
            if g_verbose >= 0:
                walk.log_ping( f'Looking at: {path}', 4)
            path_o, doit, reason, e = do_compile(
                    target,
                    walk_concurrent,
                    cc_base,
                    cpp_base,
                    cf,
                    path,
                    force=False,
                    )
            if doit:
                num_compiles_queued += 1
            link_command_files.append( f' {path_o}')

        timings.end( 'compile-enqueing')
        
        # Wait for all compile commands to finish before doing the link.
        #
        if g_verbose >= 0:
            walk.log( f'Waiting for {num_compiles_queued} compile tasks to complete')
        
        walk_concurrent.join()
        timings.end( 'compiling')
        
        if g_keep_going:
            walk.log(f'calling walk_concurrent.get_errors()')
            ee = walk_concurrent.get_errors()
            walk.log(f'walk_concurrent.get_errors() returned {len(ee)}')
            if ee:
                raise Exception(f'Compile errors: {len(ee)}')
        
        if g_verbose >= 0:
            walk.log( f'Number of compiles run was {walk_concurrent.num_commands_run}/{walk_concurrent.num_commands}.')
        
        link_command_files.sort()
        link_command_files = '\n'.join( link_command_files)
        file_write( link_command_files, link_command_extra_path)
        
        #link_command += ' -Wl,--verbose'

        # Tell walk to run our link command if necessary.
        #
        timings.begin( 'link', 'Linking.')
        if g_force or g_force is None:
            system( link_command, f'{exe}.walk', description=f'Linking {exe}')
        if g_verbose >= 0:
            walk.log( f'{"Executable:":20s}{exe}')
        timings.end( 'link')

        # Create scripts to run our generated executable.
        #
        timings.begin( 'create-wrapper', f'Creating wrapper scripts for {exe}.')
        for gdb in '', '-gdb':
            script_path = f'{exe}-run{gdb}.sh'
            text = '#!/bin/sh\n'
            if g_osg_dir:
                l = find1(
                        f'{g_osg_dir}/lib',
                        f'{g_osg_dir}/lib64',
                        )
                text += f'LD_LIBRARY_PATH={l} '
            if gdb:
                text += 'egdb' if g_openbsd else 'gdb'
                text += ' -ex "handle SIGPIPE noprint nostop"'
                text += ' -ex "handle SIG32 noprint nostop"'
                text += ' -ex "set print thread-events off"'
                text += ' -ex "set print pretty on"'
                #text += ' -ex "catch throw"'
                text += ' -ex run'
                text += f' --args '
            else:
                text += 'exec '
            text += f'{exe} "$@"\n'
            if g_force or g_force is None:
                file_write( text, script_path)
                os.system( f'chmod u+x {script_path}')
            if g_verbose >= 0:
                walk.log( f'{"Wrapper script:":20s}{script_path}')
        
        # Make softlinks to most recent build called:
        #
        #   {g_outdir}/fgfs.exe
        #   {g_outdir}/fgfs-run.exe
        #   {g_outdir}/fgfs-run-gdb.exe
        #
        exe_leaf = os.path.basename(exe)
        rhs = exe_leaf[:exe_leaf.find(',')]
        def make_link( suffix):
            if g_force or g_force is None:
                os.system( f'cd {g_outdir} && ln -sf {exe_leaf}{suffix} {rhs}.exe{suffix}')
            if g_verbose >= 0:
                walk.log( f'{"Convenience link:":20s}{g_outdir}/{rhs}.exe{suffix} => {g_outdir}/{exe_leaf}{suffix}')
        make_link( '')
        make_link( '-run.sh')
        make_link( '-run-gdb.sh')
        
        timings.end( 'create-wrapper')
            
        _log_prefix.progress = 1
        walk.log( f'Build finished successfully: target={target}')

    finally:

        # Terminate and wait for walk_concurrent's threads before we finish.
        #
        walk_concurrent.end()
        
        timings.end()
        if g_show_timings:
            walk.log( f'{timings}')


def get_args( argv):
    '''
    Generator that iterates over `argv` items. Does getopt-style splitting of
    args starting with single '-' character.
    '''
    for arg in argv:
        if arg.startswith('-') and not arg.startswith('--'):
            for arg2 in arg[1:]:
                yield '-' + arg2
        else:
            yield arg


def exception_info(
        exception_or_traceback=None,
        limit=None,
        file=None,
        chain=True,
        outer=True,
        _filelinefn=True,
        ):
    '''
    Shows an exception and/or backtrace.

    Alternative to `traceback.*` functions that print/return information about
    exceptions and backtraces, such as::

        traceback.format_exc()
        traceback.format_exception()
        traceback.print_exc()
        traceback.print_exception()

    Install as system default with::
    
        sys.excepthook = lambda type_, exception, traceback: exception_info( exception, chain='reverse')

    Returns `None`, or the generated text if `file` is 'return'.

    Args:
        exception_or_traceback:
            `None`, an `Exception` or a `types.TracebackType`. If `None` we
            use current exception from `sys.exc_info()`, otherwise the current
            backtrace from `inspect.stack()`.
        limit:
            As in `traceback.*` functions: `None` to show all frames, positive
            to show last `limit` frames, negative to exclude outermost `-limit`
            frames.
        file:
            As in `traceback.*` functions: file-like object to which we write
            output, or `sys.stderr` if `None`. Special value 'return' makes us
            return our output as a string.
        chain:
            As in `traceback.* functions`: if true we show chained exceptions
            as described in PEP-3134. Special value 'because' reverses the
            usual ordering, showing higher-level exceptions first and joining
            with 'Because:' text.
        outer:
            If true (the default) we also show an exception's outer frames
            above the catch block (see below for details). We use `outer=False`
            for chained exceptions to avoid duplication.
        _filelinefn:
            Internal only; used with `doctest` - makes us omit `file:line:`
            information to allow simple comparison with expected output.

    Differences from `traceback.*` functions:

        Frames are displayed as one line in the form::
        
            <file>:<line>:<function>: <text>

        Filenames are displayed as relative to the current directory if
        applicable.

        Inclusion of outer frames:
            Unlike `traceback.*` functions, stack traces for exceptions include
            outer stack frames above the point at which an exception was caught
            - frames from the top-level `module` or thread creation to the
            catch block. [Search for 'sys.exc_info backtrace incomplete' for
            more details.]

            We separate the two parts of the backtrace using a marker line
            '^except raise:' where '^except' points upwards to the frame that
            caught the exception and 'raise:' refers downwards to the frame
            that raised the exception.

            So the backtrace for an exception looks like this::

                <file>:<line>:<fn>: <text>  [in root module.]
                ...                         [... other frames]
                <file>:<line>:<fn>: <text>  [the except: block where exception was caught.]
                ^except raise:              [marker line]
                <file>:<line>:<fn>: <text>  [try: block.]
                ...                         [... other frames]
                <file>:<line>:<fn>: <text>  [where the exception was raised.]

    Examples:

        Define some nested function calls which raise and except and call
        `exception_info()`. We use `file=sys.stdout` so we can check the output
        with `doctest`, and set `_filelinefn=0` so that the output can be
        matched easily.

        >>> def a():
        ...     b()
        >>> def b():
        ...     try:
        ...         c()
        ...     except Exception as e:
        ...         exception_info( file=sys.stdout, chain=g_chain, _filelinefn=0)
        >>> def c():
        ...     try:
        ...         d()
        ...     except Exception as e:
        ...         raise Exception( 'c: d() failed') from e
        >>> def d():
        ...     e()
        >>> def e():
        ...     raise Exception('e(): deliberate error')

        We use +ELLIPSIS to allow '...' to match arbitrary outer frames from
        the doctest code itself.

        With chain=True (the default), we output low-level exceptions first,
        matching the behaviour of `traceback.*` functions:

        >>> g_chain = True
        >>> a() # doctest: +REPORT_UDIFF +ELLIPSIS
        Traceback (most recent call last):
            c(): d()
            d(): e()
            e(): raise Exception('e(): deliberate error')
        Exception: e(): deliberate error
        <BLANKLINE>
        The above exception was the direct cause of the following exception:
        Traceback (most recent call last):
            ...
            <module>(): a() # doctest: +REPORT_UDIFF +ELLIPSIS
            a(): b()
            b(): exception_info( file=sys.stdout, chain=g_chain, _filelinefn=0)
            ^except raise:
            b(): c()
            c(): raise Exception( 'c: d() failed') from e
        Exception: c: d() failed


        With chain='because', we output high-level exceptions first:

        >>> g_chain = 'because'
        >>> a() # doctest: +REPORT_UDIFF +ELLIPSIS
        Traceback (most recent call last):
            ...
            <module>(): a() # doctest: +REPORT_UDIFF +ELLIPSIS
            a(): b()
            b(): exception_info( file=sys.stdout, chain=g_chain, _filelinefn=0)
            ^except raise:
            b(): c()
            c(): raise Exception( 'c: d() failed') from e
        Exception: c: d() failed
        <BLANKLINE>
        Because:
        Traceback (most recent call last):
            c(): d()
            d(): e()
            e(): raise Exception('e(): deliberate error')
        Exception: e(): deliberate error
    '''
    if isinstance( exception_or_traceback, types.TracebackType):
        exception = None
        tb = exception_or_traceback
    elif isinstance( exception_or_traceback, BaseException):
        exception = exception_or_traceback
    elif exception_or_traceback:
        assert 0, f'Unrecognised exception_or_traceback type: {type(exception_or_traceback)}'
    else:
        _, exception, tb = sys.exc_info()
        if not exception:
            tb = inspect.stack()[1:]

    if file == 'return':
        out = io.StringIO()
    else:
        out = file if file else sys.stderr

    def do_chain( exception):
        exception_info( exception, limit, out, chain, outer=False, _filelinefn=_filelinefn)

    if exception and chain and chain != 'because':
        if exception.__cause__:
            do_chain( exception.__cause__)
            out.write( '\nThe above exception was the direct cause of the following exception:\n')
        elif exception.__context__:
            do_chain( exception.__context__)
            out.write( '\nDuring handling of the above exception, another exception occurred:\n')

    cwd = os.getcwd() + os.sep

    def output_frames( frames, reverse, limit):
        if reverse:
            frames = reversed( frames)
        if limit is not None:
            frames = list( frames)
            frames = frames[ -limit:]
        for frame in frames:
            f, filename, line, fnname, text, index = frame
            text = text[0].strip() if text else ''
            if filename.startswith( cwd):
                filename = filename[ len(cwd):]
            if filename.startswith( f'.{os.sep}'):
                filename = filename[ 2:]
            if _filelinefn:
                out.write( f'    {filename}:{line}:{fnname}(): {text}\n')
            else:
                out.write( f'    {fnname}(): {text}\n')

    out.write( 'Traceback (most recent call last):\n')
    if exception:
        tb = exception.__traceback__
        if outer:
            output_frames( inspect.getouterframes( tb.tb_frame), reverse=True, limit=limit)
            out.write( '    ^except raise:\n')
        output_frames( inspect.getinnerframes( tb), reverse=False, limit=None)
    else:
        output_frames( tb, reverse=True, limit=limit)

    if exception:
        lines = traceback.format_exception_only( type(exception), exception)
        for line in lines:
            out.write( line)

    if exception and chain == 'because':
        if exception.__cause__:
            out.write( '\nBecause:\n')
            do_chain( exception.__cause__)
        elif exception.__context__:
            out.write( '\nBecause error occurred handling this exception:\n')
            do_chain( exception.__context__)

    if file == 'return':
        return out.getvalue()


def main():

    timings = Timings()
    
    global g_build_debug
    global g_build_optimise
    global g_clang
    global g_concurrency
    global g_verbose
    global g_force
    global g_frame_pointer
    global g_gperf
    global g_keep_going
    global g_link_only
    global g_max_load_average
    global g_osg
    global g_osg_dir
    global g_outdir
    global g_props_locking
    global g_show_timings
    global g_walk_verbose
    
    do_build = False
    target = 'fgfs'
    
    args = get_args( sys.argv[1:])    
    while 1:
        try: arg = next( args)
        except StopIteration: break
        #walk.log( f'arg={arg}')
        if 0:
            pass
        
        elif arg == '-b' or arg == '--build':
            do_build = True
        
        elif arg == '--check-mtime':
            t = time.time()
            n = 0
            for root in ( 'flightgear', 'simgear', 'plib'):
                for dirpath, dirnames, filenames in os.walk(root):
                    for filename in filenames:
                        for suffix in (
                                '.cxx', '.c', '.cpp',
                                '.hxx', '.h', '.hpp',
                                ):
                            if filename.endswith( suffix):
                                path = os.path.join( dirpath, filename)
                                walk.mtime( path)
                                n += 1
            walk.log( f'n={n} t={time.time()-t}')
        elif arg == '--clang':
            g_clang = int( next( args))
        
        elif arg == '--convert-walk-all':
            root = next( args)
            walk.convert_walk_all( root)
            
        elif arg == '--debug':
            g_build_debug = int( next( args))
            walk.log(f'Have set g_build_debug={g_build_debug}')
        
        elif arg == '--doctest':
            print( 'Running doctest...')
            import doctest
            if 0:
                # Run a specific test.
                doctest.run_docstring_examples(
                        Timings,
                        globals(),
                        )
            doctest.testmod(
                    #verbose=True,
                    #report=True,
                    )
        
        elif arg == '--flags-all':
            g_flags_all = int( next( args))
        
        elif arg == '--force':
            force = next( args)
            if force == 'default':
                g_force = None
            else:
                g_force = int( force)
        
        elif arg == '--fp':
            g_frame_pointer = int( next( args))
        
        elif arg == '--gperf':
            g_gperf = int( next( args))
        
        elif arg == '-h' or arg == '--help':
            print( __doc__)
        
        elif arg == '-j':
            g_concurrency = abs(int( next( args)))
            assert g_concurrency >= 0
        
        elif arg == '-k':
            g_keep_going = True
        
        elif arg == '-l':
            g_max_load_average = float( next( args))
        
        elif arg == '--link-only':
            g_link_only = True
        
        elif arg == '-n':
            g_force = False
        
        elif arg == '--new':
            path = next( args)
            walk.mtime_cache_mark_new( path)
        
        elif arg == '--old':
            walk.mtime_cache_mark_old( path)
        
        elif arg == '--optimise':
            g_build_optimise = int( next( args))
        
        elif arg == '--optimise':
            g_build_optimise = int( next( args))
        
        elif arg == '--optimise-prefix':
            optimise = int( next( args))
            prefix = next( args)
            g_optimise_prefixes.append( (optimise, prefix))
        
        elif arg == '--osg':
            g_osg = int(next( args))
            if g_osg:
                g_osg_dir = None
        
        elif arg == '--osg-dir':
            g_osg_dir = next( args)
        
        elif arg == '--out-dir':
            g_outdir = next( args)
        
        elif arg == '--preprocess':
            path = next( args)
            walk_concurrent = walk.Concurrent( 0)
            preprocess( timings, 'fgfs', path, walk_concurrent)
        
        elif arg == '--props-locking':
            g_props_locking = int(next( args))
            print(f'g_props_locking={g_props_locking}')
        
        elif arg == '--show':
            print( f'concurrency:        {g_concurrency}')
            print( f'debug:              {g_build_debug}')
            print( f'force:              {("default" if g_force is None else g_force)}')
            print( f'clang:              {g_clang}')
            print( f'max_load_average:   {g_max_load_average}')
            print( f'optimise:           {g_build_optimise}')
            print( f'osg:                {g_osg_dir}')
            print( f'outdir:             {g_outdir}')
            print( f'verbose:            {g_verbose}')
            print( f'walk-verbose:       {walk.get_verbose( g_walk_verbose)}')
        
        elif arg == '-t':
            g_show_timings = True
        
        elif arg == '-o':
            target = next( args)
            targets = 'fgfs test-suite props-test yasim-test'.split()
            assert target in targets, \
                    f'unrecognised target={target} should be one of: {" ".join(targets)}.'
        
        elif arg == '-q':
            g_verbose -= 1
        
        elif arg == '-v':
            g_verbose += 1
        
        elif arg == '-w':
            v = next( args)
            if v.startswith( '+') or v.startswith( '-'):
                vv = walk.get_verbose( g_walk_verbose)
                for c in v[1:]:
                    if v[0] == '+':
                        if c not in vv:
                            vv += c
                    else:
                        vv = vv.replace( c, '')
                g_walk_verbose = vv
            else:
                g_walk_verbose = v
        
        elif arg == '--v-src':
            p = next( args)
            g_verbose_srcs.append(p)
        
        else:
            raise Exception( f'Unrecognised arg: {arg}')
    
    if do_build:
        build( timings, target)


if __name__ == '__main__':

    sys.excepthook = lambda type_, exception, traceback: exception_info( exception, chain='reverse')
    
    if 0:
        import pprofile
        prof = pprofile.StatisticalProfile()
        with prof():
            main()
        prof.print_stats()
    else:
        main()
