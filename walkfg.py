#!/usr/bin/env python3

r'''Build script for Flightgear on Unix systems.

Status:
    As of 2020-07-05 we can build on Linux Devuan Beowulf and OpenBSD 6.7.


Usage:
    We expect to be in a directory looking like:
        flightgear/
        plib/
        simgear/
        fgdata/
        
    Each of these will typically be a git checkout.
    
    In this directory, run this script (wherever it happens to be).    
        .../walkfg.py
    
    All generated files will be in a new directory:    
        build-walk/
        
    The generated executable and wrapper scripts include information in their
    names to distinguish different builds:
        build-walk/fgfs,<flags>.exe
        build-walk/fgfs,<flags>.exe-run.sh
        build-walk/fgfs,<flags>.exe-run-gdb.sh
    
    For convenience we generate soft-links to the most recent build:
        build-walk/fgfs.exe
        build-walk/fgfs.exe-run.sh
        build-walk/fgfs.exe-run-gdb.sh
        
    So for example Flightgear can be run with:
        build-walk/fgfs.exe-run.sh --aircraft=... --airport=... ...


Args:
    Arguments are processed in the order they occur on the command line, so
    typically -b or --build should be last.

    -b
    --build
        Build fgfs.
    
    --clang 0 | 1
        If 1, we force use of clang instead of system compiler.
        
        Default is 0.
    
    --compositor 0 | 1
        If 1 (the default), we build with compositor.
    
    --debug 0 | 1
        If 1 (default), we compile and link with -g to include debug symbols.
    
    --flags-all 0 | 1
        If 1, we use same compiler flags for all files (except for
        file-specific -W warning flags). So for example everything gets
        compiled with the same include path and defines.
        
        Default is 0.
    
    --force 0 | 1 | default
        If 0, we never run commands; depending on --verbose, we may output
        diagnostics about what we would have run.

        If 1, we always run commands, regardless of whether output files are up
        to date.
        
        If default, commands are run only if necessary.
    
    --gperf 0 | 1
        If 1, build with support for google perf.
    
    -h
    --help
        Show help.
    
    -j N
        Set concurrency level.
    
    -l <maxload>
        Only schedule new concurrent commands when load average is less than
        <maxload>.
    
    --link-only
        Only do link.
    
    --new <path>
        Treat <path> as new.

    --old <path>
        Treat <path> as old.
    
    --optimise 0 | 1
        If 1 (the default), we build with compiler optimisations.
    
    --osg <directory>
        Use local OSG install instead of system OSG.
        
        For example:
            (cd openscenegraph && mkdir build && cd build && cmake -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_BUILD_TYPE=RelWithDebInfo .. && time make -j 3 && make install)
            .../walkfg.py --osg openscenegraph/build/install -b
            
            time (true \
                    && cd openscenegraph \
                    && git checkout OpenSceneGraph-3.6 \
                    && (rm -r build-3.6.5 || true) \
                    && mkdir build-3.6.5 \
                    && cd build-3.6.5 \
                    && cmake -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_BUILD_TYPE=RelWithDebInfo .. \
                    && time make -j 3 \
                    && make install \
                    && cd ../../ \
                    && ../todo/walkfg.py --osg openscenegraph/build-3.6.5/install -b \
                    ) 2>&1|tee out
    
            time (true \
                    && cd openscenegraph \
                    && (rm -r build-3.6.5-relwithdebinfo || true) \
                    && mkdir build-3.6.5-relwithdebinfo \
                    && cd build-3.6.5-relwithdebinfo \
                    && cmake -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_CXX_FLAGS_RELWITHDEBINFO="-O2 -g -DNDEBUG" -DCMAKE_CC_FLAGS_RELWITHDEBINFO="-O2 -g -DNDEBUG" -DCMAKE_BUILD_TYPE=RelWithDebInfo .. \
                    && VERBOSE=1 make -j 3 \
                    && VERBOSE=1 make install \
                    ) 2>&1|tee out
                    ../todo/walkfg.py --osg openscenegraph/build-3.6.5-relwithdebinfo/install -b
    
    -o <directory>
    --out-dir <directory>
        Set the directory that will contain all generated files.
        
        Default is build-walk.
    
    --show
        Show settings.
    
    -t
        Show detailed timing information at end.
    
    -v
    --verbose [+-fFdDrRcCe]
        Set verbose flags:
            
            f   Show if we are forcing running of a command.
            F   Show if we are forcing non-running of a command.
            
            m   Show message if we are running command (only if d not specified).
            M   Show message if we are not running command (only if d not specified).
            
            d   Show description if available, if we are running command.
            D   Show description if available, if we are not running command.
            
            r   Show reason why a command is being run.
            R   Show reason why a command is not being run.
            
            c   Show the command if we are running it.
            C   Show the command if we are not running it.
            
            e   If command fails, show command if we haven't already shown it.
        
        Default is 'der'.
        
        If arg starts with +/-, we add/remove the specified flags to/from the
        existing settings.


Requirements:

    The walk.py command optimiser module.
    
    Packages for this script:
        python3
        strace
    
    Packages for flightgear:
    
        Linux:
            apt install \
                freeglut3-dev \
                libasound-dev \
                libboost-dev \
                libcurl4-openssl-dev \
                libdbus-1-dev \
                libevent-dev \
                libopenal-dev \
                libpng-dev \
                libqt5opengl5-dev \
                libqt5svg5-dev \
                libqt5websockets5-dev \
                libudev-dev \
                openscenegraph \
                pkg-config \
                qml-module-qtquick2 \
                qml-module-qtquick-dialogs \
                qml-module-qtquick-window2 \
                qt5-default \
                qtbase5-dev-tools \
                qtbase5-private-dev \
                qtdeclarative5-dev \
                qtdeclarative5-private-dev \
                qttools5-dev \
                qttools5-dev-tools \
    
        OpenBSD:
            pkg_add \
                    freeglut \
                    openal \
                    openscenegraph \
                    qtdeclarative \

'''

'''
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

import glob
import os
import re
import resource
import subprocess
import sys
import textwrap
import time

import walk


g_build_debug = 1
g_build_optimise = 1
g_clang = False
g_compositor = 1
g_concurrency = 3
g_flags_all = False
g_force = None
g_link_only = False
g_max_load_average = 6
g_osg_dir = None
g_outdir = 'build-walk'
g_gperf = None
g_timings = False
g_verbose = 'der'

g_os = os.uname()[0]
g_openbsd = (g_os == 'OpenBSD')
g_linux = (g_os == 'Linux')

if g_openbsd:
    g_clang = True


def system( command, walk_path, description=None, verbose=None):
    '''
    Wrapper for walk.system() which sets default verbose and force flags, and
    raises an exception if the command fails instead of returning an error
    value.
    '''
    if verbose is None:
        verbose = g_verbose
    e = walk.system(
            command,
            walk_path,
            verbose=verbose,
            force=g_force,
            description=description,
            #out_prefix='    ',
            )
    if e:
        raise Exception( 'command failed: %s' % command)

def system_concurrent( walk_concurrent, command, walk_path, description=None, verbose=None, command_compare=None):
    '''
    Wrapper for walk_concurrent.system() which sets default verbose and force
    flags.
    '''
    if verbose is None:
        verbose = g_verbose
    walk_concurrent.system(
            command,
            walk_path,
            verbose=verbose,
            force=g_force,
            description=description,
            command_compare=command_compare,
            #out_prefix='    ',
            )

def file_write( text, path, verbose=None):
    '''
    Wrapper for walk.file_write() which sets default verbose flag, and
    raises an exception if the command fails instead of returning an error
    value.
    '''
    if verbose == None:
        verbose = g_verbose
    walk.file_write( text, path, verbose, g_force)


def cmp(a, b):
    '''
    Not sure why python3 dropped cmp(), but this recreates it.
    '''
    return (a > b) - (a < b) 


def get_gitfiles( directory):
    '''
    Returns list of all files known to git in <directory>; <directory> must be
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
    id = subprocess.check_output( 'cd %s && PAGER= git show --pretty=oneline' % directory, shell=True)
    id = id.decode( 'latin-1')
    id = id.split( '\n', 1)[0]
    return id


def get_files():
    '''
    Returns list source files to build from.
    
    We find all files known to git, then prune out various files which we don't
    want to include in the build.
    '''
    exclude_patterns = [
            'flightgear/3rdparty/cjson/test.c',
            'flightgear/3rdparty/cppunit/*',
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
            'flightgear/examples/netfdm/main.cpp',
            'flightgear/scripts/example/fgfsclient.c',
            'flightgear/scripts/example/fgfsclient.cxx',
            'flightgear/src/Airports/calc_loc.cxx',
            'flightgear/src/EmbeddedResources/fgrcc.cxx',
            'flightgear/src/FDM/JSBSim/JSBSim.cpp',
            'flightgear/src/FDM/LaRCsim/c172_main.c',
            'flightgear/src/FDM/LaRCsim/ls_trim.c',
            'flightgear/src/FDM/LaRCsim/mymain.c',
            'flightgear/src/FDM/YASim/proptest.cpp',
            'flightgear/src/FDM/YASim/yasim-test.cpp',
            'flightgear/src/GUI/FGWindowsMenuBar.cxx',
            'flightgear/src/GUI/WindowsFileDialog.cxx',
            'flightgear/src/GUI/WindowsMouseCursor.cxx',
            
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
            'flightgear/test_suite/*',
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
            'simgear/simgear/io/test_binobj.cxx',
            'simgear/simgear/io/test_DNS.cxx',
            'simgear/simgear/io/test_HTTP.cxx',
            'simgear/simgear/io/test_repository.cxx',
            'simgear/simgear/io/test_untar.cxx',
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
            'simgear/simgear/props/props_test.cxx',
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
            'simgear/simgear/structure/expression_test.cxx',
            'simgear/simgear/structure/function_list_test.cxx',
            'simgear/simgear/structure/intern.cxx',
            'simgear/simgear/structure/shared_ptr_test.cpp',
            'simgear/simgear/structure/state_machine_test.cxx',
            'simgear/simgear/structure/subsystem_test.cxx',
            'simgear/simgear/structure/test_commands.cxx',
            'simgear/simgear/timing/testtimestamp.cxx',
            'simgear/simgear/xml/testEasyXML.cxx',
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
                ]
    else:
        exclude_patterns += [
                'flightgear/3rdparty/joystick/jsBSD.cxx',
                'flightgear/3rdparty/joystick/jsNone.cxx',
                ]
    
    if g_compositor:
        exclude_patterns += [
                'flightgear/src/Viewer/CameraGroup_legacy.cxx',
                'flightgear/src/Viewer/renderer_legacy.cxx',
                'flightgear/src/Viewer/renderingpipeline.cxx',
                ]
    else:
        exclude_patterns += [
                'flightgear/src/Viewer/CameraGroup_compositor.cxx',
                'flightgear/src/Viewer/renderer_compositor.cxx',
                ]

    
    # It's important to sort exclude_patterns because we rely on ordering to
    # short-cut the searches we do below.
    #
    exclude_patterns.sort()

    files_flightgear = get_gitfiles( 'flightgear')
    files_simgear = get_gitfiles( 'simgear')
    files_plib = get_gitfiles( 'plib')

    all_files = ([]
            + files_flightgear
            + files_simgear
            + files_plib
            )

    ret = []
    exclude_patterns_pos = 0
    for path in all_files:
        _, suffix = os.path.splitext( path)
        if suffix not in ('.c', '.cpp', '.cxx'):
            continue
        include = True
        for i, ep in enumerate(exclude_patterns, exclude_patterns_pos):
            if ep.endswith( '*'):
                if path.startswith( ep[:-1]):
                    include = False
                    break
            else:
                c = cmp( ep, path)
                if c < 0:
                    exclude_patterns_pos = i + 1
                if c == 0:
                    include = False
                    exclude_patterns_pos = i + 1
                    break
                if c > 0:
                    break
        if include:
            ret.append( path)
    
    return all_files, ret


_cc_command_compare_regex = None
def cc_command_compare( a, b):
    '''
    Compares cc comamnds, ignoring differences in warning flags.
    '''
    global _cc_command_compare_regex
    if _cc_command_compare_regex is None:
        _cc_command_compare_regex = re.compile( ' (-Wno-[^ ]+)|(-std=[^ ]+)')
    aa = re.sub( _cc_command_compare_regex, '', a)
    bb = re.sub( _cc_command_compare_regex, '', b)
    ret = aa != bb
    ret0 = a != b
    if not ret and ret0:
        pass
        #print( 'ignoring command diff:\n    %s\n    %s' % (a, b))
    if ret and not ret0:
        assert 0
    return ret

if 1:
    assert cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Wno-xyz -Werror') == 0
    assert cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Werror') == 0
    assert cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -Wno-q -Werror') == 0
    assert cc_command_compare( 'cc -o foo bar.c -Wno-xyz -Werror', 'cc -o foo bar.c -O2 -Werror') != 0



class CompileFlags:
    '''
    Compile flags for different parts of the source tree.
    '''
    def __init__( self):
        self.items = []
    
    def add( self, path_prefixes, flags):
        assert flags == '' or flags.startswith( ' ')
        flags = flags.replace( ' -D ', ' -D')
        flags = flags.replace( ' -I ', ' -I')
        if isinstance( path_prefixes, str):
            path_prefixes = path_prefixes,
        self.items.append( ( path_prefixes, flags))
    
    def get_flags( self, path):
        '''
        Returns compile flags for compiling <path>.
        '''
        ret = ''
        for path_prefixes, flags in self.items:
            for path_prefix in path_prefixes:
                #walk.log( 'looking at path_prefix: %s' % path_prefix)
                if path.startswith( path_prefix):
                    #walk.log( 'adding flags: %s' % flags)
                    ret += flags
                    break
        return ret
    
    def get_flags_all( self, path):
        '''
        Returns compile flags for compiling <path>, using a union of all flags
        except for warning flags which are calculated specificall for <path>.
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
                        ret_warnings += ' %s' % flag
                else:
                    ret_flags.add( flag)
                    for prefix in 'DI':
                        if flag.startswith( '-'+prefix):
                            flag = '-%s %s' % (prefix, flag[2:])
                    ret += ' %s' % flag
                    
        return ret + ret_warnings


g_compositor_prefixes = (        
        'flightgear/src/Canvas/',
        'flightgear/src/Scenery/',
        'flightgear/src/GUI/',
        'flightgear/src/Main/',
        'flightgear/src/Viewer/',
        'flightgear/src/Time/',
        'flightgear/src/Cockpit/',
        'flightgear/src/Network/',
        'flightgear/src/Environment/',
        )

def make_compile_flags( libs_cflags, cpp_feature_defines):
    '''
    Returns a CompileFlags instance set up for building Flightgear.
    
    (libs_cflags, cpp_feature_defines) are particular pre-defined flags that
    our caller passes to us that have been found by running config tests and/or
    pkg-add.
    '''     
    cf = CompileFlags()

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
    
    if g_clang:
        cf.add( (
                'flightgear/',
                'simgear/',
                'plib/',
                ),
                    ' -Wno-inconsistent-missing-override'
                    ' -Wno-overloaded-virtual'
                    ' -Wno-macro-redefined'
                )
    
    cf.add( (
            'flightgear/3rdparty/flite_hts_engine/flite/',
            'flightgear/3rdparty/hts_engine_API/lib',
            'flightgear/3rdparty/iaxclient/lib',
            'flightgear/3rdparty/iaxclient/lib/gsm/src/preprocess.c',
            'flightgear/src/GUI',
            'flightgear/src/Navaids/FlightPlan.cxx',
            'simgear/simgear/canvas/elements/CanvasImage.cxx',
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
            '%s/flightgear/' % g_outdir,
            'simgear/',
            '%s/simgear/' % g_outdir,
            '%s/walk-generated/flightgear/' % g_outdir,
            ),
            cpp_feature_defines
            )

    cf.add( (
            'flightgear/',
            '%s/flightgear/' % g_outdir,
            ),
            ' -I simgear'
            ' -I flightgear/src'
            ' -I %s/walk-generated'
            ' -D ENABLE_AUDIO_SUPPORT'
            ' -D JENKINS_BUILD_NUMBER=0'
            ' -D JENKINS_BUILD_ID=0'
            % g_outdir
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
            ' -D ENABLE_JSBSIM'
            ' -D ENABLE_YASIM'
            )

    cf.add( 'flightgear/src/FDM/JSBSim/FGJSBBase.cpp'
            ,
            ' -D JSBSIM_VERSION="\\"compiled from FlightGear 2020.2.0\\""'
            )

    cf.add( 'flightgear/src/FDM/SP/AISim.cpp'
            ,
            ' -D ENABLE_SP_FDM'
            )

    cf.add( (
            'flightgear/src/GUI/',
            '%s/flightgear/src/GUI/' % g_outdir,
            ),
            ' -I %s/walk-generated/Include'
            ' -I flightgear/3rdparty/fonts'
            ' -I %s/flightgear/src/GUI'
            % (g_outdir, g_outdir)
            )

    cf.add( (
            'flightgear/src/Viewer/',
            '%s/flightgear/src/Viewer/' % g_outdir,
            ),
            ' -D HAVE_PUI'
            )

    cf.add( 'flightgear/src/Input/',
            ' -I flightgear/3rdparty/hidapi'
            ' -I flightgear/3rdparty/joystick'
            ' -D HAVE_CONFIG_H'
            )

    cf.add( 'flightgear/3rdparty/fonts/',
            ' -I %s/walk-generated/plib-include' % g_outdir
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
            ' -D HAVE_CONFIG_H'
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

    cf.add( 'flightgear/src/Scripting/',
            ' -D HAVE_SYS_TIME_H'
            )

    cf.add( 'flightgear/src/Sound',
            ' -I flightgear/3rdparty/flite_hts_engine/include'
            ' -I flightgear/3rdparty/hts_engine_API/include'
            )

    cf.add( 'flightgear/src/Cockpit',
            ' -I flightgear/3rdparty/fonts'
            )

    cf.add( 'simgear/simgear/',
            ' -I simgear'
            ' -I simgear/simgear/canvas/ShivaVG/include'
            ' -I simgear/3rdparty/udns'
            ' -I %s/walk-generated'
            ' -I %s/walk-generated/simgear'
            ' -D HAVE_STD_INDEX_SEQUENCE' # prob not necessary.
            % (g_outdir, g_outdir)
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

    cf.add('%s/walk-generated/EmbeddedResources' % g_outdir,
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


    cf.add( 'simgear/simgear/canvas/ShivaVG',
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
            ' -I %s/walk-generated/plib-include' % g_outdir
            + ' -I %s/walk-generated/plib-include/plib' % g_outdir
            )
    
    if g_compositor:
        cf.add( g_compositor_prefixes, ' -D ENABLE_COMPOSITOR')
    
    if g_gperf:
        cf.add( (
                'flightgear/src/Main/fg_commands.cxx',
                'src/Main/fg_scene_commands.cxx',
                ),
                ' -D FG_HAVE_GPERFTOOLS'
                )
    
    return cf


class Timing:
    '''
    Internal item for Timings class.
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
    Maintains a tree of Timing items.
    Example usage:
        timings = Timings()
        timings.begin('all')
        timings.begin('init')
        timings.begin('phase 1')
        timings.end('init') # will also end 'phase 1'.
        timings.begin('phase 2')
        timings.end()   # will end everything.
        print(timings)
    This will create timing tree like:
        all
            init
                phase 1
            phase 2
    '''
    def __init__( self):
        self.current = None # Points to most recent in-progress item.
        self.first = None   # Points to top item.
        self.name_max_len = 0
    
    def begin( self, name):
        '''
        Starts a new timing item as child of most recent in-progress timing
        item.
        '''
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
        matching <name>.
        '''
        # end all until we have reached <name>.
        t = time.time()
        while self.current:
            name2 = self.current.name
            self.current.end( t)
            self.current = self.current.parent
            if name2 == name:
                break
    
    def text( self, t, depth):
        ret = ''
        ret += ' ' * 4 * depth + f' {t.get():6.1f} {t.name}\n'
        for child in t.children:
            ret += self.text( child, depth + 1)
        return ret
    
    def __str__( self):
        ret = 'Timings (in seconds):\n'
        ret += self.text( self.first, 0)
        return ret

if 0:
    ts = Timings()
    ts.add('a')
    time.sleep(0.1)
    ts.add('b')
    time.sleep(0.2)
    ts.add('c')
    time.sleep(0.3)
    ts.end('b')
    ts.add('d')
    ts.add('e')
    time.sleep(0.1)
    ts.end()
    print(ts)
    sys.exit()


def build():
    '''
    Builds Flightgear using g_* settings.
    '''
    timings = Timings()
    
    timings.begin( 'all')
    
    timings.begin( 'pre')
    if g_openbsd:
        # clang needs around 2G to compile
        # flightgear/src/Scripting/NasalCanvas.cxx.
        #
        soft, hard = resource.getrlimit( resource.RLIMIT_DATA)
        required = min(4*2**30, hard)
        if soft < required:
            if hard < required:
                walk.log( f'Warning: RLIMIT_DATA hard={hard} is less than required={required}')
            soft_new = min(hard, required)
            resource.setrlimit( resource.RLIMIT_DATA, (soft_new, hard))
            walk.log( f'Have changed RLIMIT_DATA from {soft} to {soft_new}')

    timings.begin( 'get_files')
    all_files, src_fgfs = get_files()
    timings.end( 'get_files')

    # Create patched version of plib/src/sl/slDSP.cxx.
    timings.begin( 'plib-patch')
    path = 'plib/src/sl/slDSP.cxx'
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
    timings.begin( 'moc')
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
                    cpp_file = '%s/%s.moc.cpp' % (g_outdir, i)
                    system(
                            '%s %s -o %s' % (moc, i, cpp_file),
                            '%s.walk' % cpp_file,
                            'Running moc on %s' % i,
                            )
                    src_fgfs.append( cpp_file)
            elif ext in ('.cpp', '.cxx'):
                #walk.log( 'checking %s' % i)
                with open( i) as f:
                    text = f.read()
                if re.search( '\n#include ".*[.]moc"\n', text):
                    #walk.log( 'running moc on: %s' % i)
                    moc_file = '%s/%s.moc' % (g_outdir, i_base)
                    system(
                            '%s %s -o %s' % (moc, i, moc_file),
                            '%s.walk' % moc_file,
                            'Running moc on %s' % i,
                            )
    timings.end( 'moc')


    # Create flightgear's config file.
    #
    timings.begin( 'config')
    fg_version = open('flightgear/flightgear-version').read().strip()
    root = os.path.abspath( '.')

    file_write( textwrap.dedent(f'''
            #pragma once
            #define FLIGHTGEAR_VERSION "{fg_version}"
            #define VERSION    "%s"
            #define PKGLIBDIR  "%s/fgdata"
            #define FGSRCDIR   "%s/flightgear"
            #define FGBUILDDIR "%s"

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
            #define FG_HAVE_GPERFTOOLS ( + 0)

            /* #undef SYSTEM_SQLITE */

            #define ENABLE_IAX

            #define HAVE_DBUS

            #define ENABLE_HID_INPUT
            #define ENABLE_PLIB_JOYSTICK

            #define HAVE_QT

            #define HAVE_SYS_TIME_H
            #define HAVE_SYS_TIMEB_H
            #define HAVE_TIMEGM
            #define HAVE_DAYLIGHT
            #define HAVE_FTIME
            #define HAVE_GETTIMEOFDAY

            #define FG_TEST_SUITE_DATA "/home/jules/flightgear/download_and_compile16/flightgear/test_suite/test_data"

            #define FG_BUILD_TYPE "Dev"

            #define HAVE_PUI

            // Seems to need fgdata at build time?
            //#define HAVE_QRC_TRANSLATIONS

            /* #undef ENABLE_COMPOSITOR */

            #define ENABLE_SWIFT

            /* #undef HAVE_SENTRY */
            #define SENTRY_API_KEY ""
            ''' % (
                    fg_version,
                    root,
                    root,
                    g_outdir ,
                    )
            ),
            '%s/walk-generated/config.h' % g_outdir,
            )


    # Create simgear's config file.
    #
    file_write( textwrap.dedent(
            '''
            #define HAVE_GETTIMEOFDAY
            #define HAVE_TIMEGM
            #define HAVE_SYS_TIME_H
            #define HAVE_UNISTD_H
            #define HAVE_STD_INDEX_SEQUENCE
            ''')
            ,
            '%s/walk-generated/simgear/simgear_config.h' % g_outdir,
            )

    # Create various other headers.
    #
    file_write(
            '#define FLIGHTGEAR_VERSION "%s"\n' % fg_version,
            '%s/walk-generated/Include/version.h' % g_outdir,
            )

    git_id_text = git_id( 'flightgear').replace('"', '\\"')
    revision = '#define REVISION "%s"\n' % git_id_text
    file_write(
            revision,
            '%s/walk-generated/Include/build.h' % g_outdir,
            )
    file_write(
            revision,
            '%s/walk-generated/Include/flightgearBuildId.h' % g_outdir,
            )

    file_write(
            '#pragma once\n' + 'void initFlightGearEmbeddedResources();\n',
            '%s/walk-generated/EmbeddedResources/FlightGear-resources.hxx' % g_outdir,
            )

    # We should probably have a separate step to build fgrcc and run it to generate
    # this, but actually it only seems to produce a trivially small generated file.
    #
    file_write( textwrap.dedent( '''
            // -*- coding: utf-8 -*-
            //
            // File automatically generated by fgrcc.

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
            '%s/walk-generated/EmbeddedResources/FlightGear-resources.cxx' % g_outdir,
            )

    # When we generate C++ source files (not headers), we need to add them to
    # src_fgfs so they get compiled into the final executable.
    #

    src_fgfs.append( '%s/walk-generated/EmbeddedResources/FlightGear-resources.cxx' % g_outdir)


    simgear_version = open('simgear/simgear-version').read().strip()
    file_write(
            '#define SIMGEAR_VERSION %s\n' % simgear_version,
            '%s/walk-generated/simgear/version.h' % g_outdir,
            )
    timings.end( 'config')

    timings.begin( 'rcc/uic')
    if g_openbsd:
        system(
                'rcc'
                        ' -name resources'
                        ' -o %s/walk-generated/flightgear/src/GUI/qrc_resources.cpp'
                        ' flightgear/src/GUI/resources.qrc'
                        % g_outdir
                        ,
                '%s/walk-generated/flightgear/src/GUI/qrc_resources.cpp.walk' % g_outdir,
                'Running rcc on flightgear/src/GUI/resources.qrc',
                )
    else:
        system(
                '/usr/lib/qt5/bin/rcc'
                        ' --name resources'
                        ' --output %s/walk-generated/flightgear/src/GUI/qrc_resources.cpp'
                        ' flightgear/src/GUI/resources.qrc'
                        % g_outdir
                        ,
                '%s/walk-generated/flightgear/src/GUI/qrc_resources.cpp.walk' % g_outdir,
                'Running rcc on flightgear/src/GUI/resources.qrc',
                )
    src_fgfs.append( '%s/walk-generated/flightgear/src/GUI/qrc_resources.cpp' % g_outdir)

    uic = 'uic'
    if g_openbsd:
        uic = '/usr/local/lib/qt5/bin/uic'
    system(
            '%s -o %s/walk-generated/Include/ui_InstallSceneryDialog.h'
                    ' flightgear/src/GUI/InstallSceneryDialog.ui' % (uic, g_outdir)
                    ,
            '%s/walk-generated/Include/ui_InstallSceneryDialog.h.walk' % g_outdir,
            'Running uic on flightgear/src/GUI/InstallSceneryDialog.ui',
            )

    e = system(
            '%s -o %s/walk-generated/ui_SetupRootDialog.h'
                    ' flightgear/src/GUI/SetupRootDialog.ui' % (uic, g_outdir)
                    ,
            '%s/walk-generated/ui_SetupRootDialog.h.walk' % g_outdir,
            'Running uic on flightgear/src/GUI/SetupRootDialog.ui',
            )
    timings.end( 'rcc/uic')

    # Set up softlinks that look like a plib install - some code requires plib
    # installation header tree.
    #
    timings.begin( 'plib-install')
    def find( root, leaf):
        for dirpath, dirnames, filenames in os.walk( root):
            if leaf in filenames:
                return os.path.join( dirpath, leaf)
        assert 0

    dirname = '%s/walk-generated/plib-include/plib' % g_outdir
    command = 'mkdir -p %s; cd %s' % (dirname, dirname)
    for leaf in 'pw.h pu.h sg.h netSocket.h js.h ssg.h puAux.h sl.h sm.h sl.h psl.h ul.h pw.h ssgAux.h ssgaSky.h fnt.h ssgaBillboards.h net.h ssgMSFSPalette.h ulRTTI.h puGLUT.h'.split():
        path = find( 'plib/src', leaf)
        #walk.log(f'plib path: {path}')
        path = os.path.abspath( path)
        command += ' && ln -sf %s %s' % (path, leaf)
    os.system( command)
    timings.end( 'plib-install')

    # Set up compile/link commands.
    #
    gcc_base = 'cc'
    gpp_base = 'c++ -std=gnu++17'
    if g_clang:
        gcc_base = 'clang -Wno-unknown-warning-option'
        gpp_base = 'clang++ -std=c++17 -Wno-unknown-warning-option'
    gcc_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    gpp_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    
    # On Linux we end up with compilation errors if we use the results of the
    # feature checking below. But things seem to build ok without.
    #
    # On OpenBSD, we need to do the feature checks, and the appear to work.
    #
    timings.begin( 'feature-check')
    cpp_feature_defines = ''
    if g_openbsd:
        with open( 'simgear/CMakeModules/CheckCXXFeatures.cmake') as f:
            text = f.read()
        for m in re.finditer('check_cxx_source_compiles[(]"([^"]*)" ([A-Z_]+)', text, re.M):
            code = m.group(1)
            define = m.group(2)
            with open( f'{g_outdir}/test.cpp', 'w') as f:
                f.write(code)
            e = os.system( f'{gpp_base} -o /dev/null {g_outdir}/test.cpp 1>/dev/null 2>/dev/null')
            if e == 0:
                #walk.log( f'c++ feature: defining {define}')
                cpp_feature_defines += f' -D {define}'
            else:
                pass
                #walk.log( f'c++ feature: not defining {define}')
        #walk.log( f'cpp_feature_defines: {cpp_feature_defines}')
    timings.end( 'feature-check')

    # Define compile/link commands. For linking, we write the .o filenames to a
    # separate file and use gcc's @<filename> to avoid the command becoming too
    # long.
    #
    timings.begin( 'commands')
    link_command = gpp_base
    exe = '%s/fgfs' % g_outdir

    if g_clang:
        exe += ',clang'
    if g_build_debug:
        exe += ',debug'
        link_command += ' -g'
    if g_build_optimise:
        exe += ',opt'
        link_command += ' -O2'

    if g_compositor:
        exe += ',compositor'
    
    if g_osg_dir:
        exe += ',osg'
    
    if g_flags_all:
        exe += ',flags-all'

    exe += '.exe'

    # Libraries for which we call pkg-config:
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
    
    libs_cflags     = ' ' + subprocess.check_output( 'pkg-config --cflags %s' % libs, shell=1).decode( 'latin-1').strip()
    libs_linkflags  = ' ' + subprocess.check_output( 'pkg-config --libs %s'   % libs, shell=1).decode( 'latin-1').strip()
    
    
    if 0:
        # Show linker information.
        link_command += ' -t'
        link_command += ' --verbose'
    
    link_command += ' -o %s' % exe
    
    # Other libraries, including OSG.
    #
    def find1(*globs):
        for g in globs:
            gg = glob.glob(g)
            if len(gg) == 1:
                return gg[0]
        raise Exception(f'Could not find match for {globs!r}')
    
    osg_libs = (
            'osg',
            'osgDB',
            'osgFX',
            'osgGA',
            'osgParticle',
            'osgSim',
            'osgText',
            'osgUtil',
            'osgViewer',
            'OpenThreads',
            )
    
    if g_osg_dir:
        libdir = find1(f'{g_osg_dir}/lib', f'{g_osg_dir}/lib64')
        for l in osg_libs:
            # Link with release-debug OSG libraries if available.
            lib = find1(
                    f'{libdir}/lib{l}rd.so.*.*.*',
                    f'{libdir}/lib{l}r.so.*.*.*',
                    f'{libdir}/lib{l}d.so.*.*.*',
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
                ' -pthread'
                )
        
    link_command += ' %s' % libs_linkflags
    
    link_command_files = []

    # Sort the source files by mtime so that we compile recently-modified ones
    # first, which helps save time when investigating/fixing compile failures.
    #
    src_fgfs.sort( key=lambda path: -walk.mtime( path))
    
    timings.end( 'pre')
    
    timings.begin( 'compile')
    
    # Set things up so walk.py can run compile commands concurrently.
    #
    walk_concurrent = walk.Concurrent(
            g_concurrency,
            max_load_average=g_max_load_average,
            )
    
    try:

        # Compile each source file. While doing so, we also add to the final
        # link command.
        #
        
        progress_t = 0
        for i, path in enumerate( src_fgfs):
        
            walk.log_prefix_set( '[% 3i%%] ' % (100 * i / len(src_fgfs)))
            walk.log_ping( 'looking at: %s' % path, 10)
            #walk.log( 'looking at: %s' % path)

            if path.endswith( '.c'):
                command = gcc_base
            else:
                command = gpp_base

            command += ' -c'

            path_o = '%s/%s' % (g_outdir, path)

            if g_clang:
                path_o += ',clang'
            if g_build_debug:
                command += ' -g'
                path_o += ',debug'
            if g_build_optimise:
                if 0 and path == 'simgear/simgear/props/props.cxx':
                    walk.log(f'*** not optimising {path}')
                else:
                    command += ' -O3 -msse2 -mfpmath=sse -ftree-vectorize -ftree-slp-vectorize'
                    path_o += ',opt'
            

            if g_compositor:
                for prefix in g_compositor_prefixes:
                    if path.startswith( prefix):
                        path_o += ',compositor'
                        break
            
            if g_osg_dir:
                path_o += ',osg'
                command += f' -I {g_osg_dir}/include'
            
            cf = make_compile_flags( libs_cflags, cpp_feature_defines)

            if g_flags_all:
                path_o += ',flags-all'
                command = command + cf.get_flags_all( path)
            else:
                command = command + cf.get_flags( path)

            #walk.log( 'command_cf: %s' % command_cf)
            #walk.log( 'command:    %s' % command)
            #assert command == command_cf, f'command_cf: {command_cf}\ncommand:    {command}'

            path_o += '.o'
            link_command_files.append( ' %s' % path_o)

            if not g_link_only:
                command += ' -o %s %s' % (path_o, path)

                # Tell walk to schedule running of the compile command if necessary.
                #
                system_concurrent(
                        walk_concurrent,
                        command,
                        '%s.walk' % path_o,
                        description='Compiling to %s' % path_o,
                        command_compare=cc_command_compare,
                        )

        # Wait for all compile commands to finish before doing the link.
        #
        walk_concurrent.join()
   
        timings.end( 'compile')
        
        walk.log( 'Finished compiling.')
        
        link_command_extra_path = '%s-link-extra' % exe
        link_command_files.sort()
        link_command_files = '\n'.join( link_command_files)
        file_write( link_command_files, link_command_extra_path)

        link_command += ' @%s' % link_command_extra_path
        
        #link_command += ' -Wl,--verbose'

        # Tell walk to run our link command if necessary.
        #
        timings.begin( 'link')
        
        system( link_command, '%s.walk' % exe, description='Linking %s' % exe)
        timings.end( 'link')

        # Create scripts to run our generated executable.
        #
        walk.log( 'Creating wrapper scripts for fgfs.')
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
                text += ' -ex "set print thread-events off"'
                text += ' -ex "set print pretty on"'
                text += ' -ex run'
                text += f' --args '
            text += f'{exe} "$@"\n'
            file_write( text, script_path)
            os.system( 'chmod u+x %s' % script_path)
        
        # Make softlinks to most recent build called:
        #
        #   {g_outdir}/fgfs.exe
        #   {g_outdir}/fgfs-run.exe
        #   {g_outdir}/fgfs-run-gdb.exe
        #
        exe_leaf = os.path.basename(exe)
        os.system( f'cd {g_outdir} && ln -sf {exe_leaf}            fgfs.exe')
        os.system( f'cd {g_outdir} && ln -sf {exe_leaf}-run.sh     fgfs.exe-run.sh')
        os.system( f'cd {g_outdir} && ln -sf {exe_leaf}-run-gdb.sh fgfs.exe-run-gdb.sh')
            
            
        
        walk.log_prefix_set( '[100%] ')
        walk.log( 'Build finished successfully.')

    finally:

        # Terminate and wait for walk_concurrent's threads before we finish.
        #
        walk_concurrent.end()
        walk.log_prefix_set('')
        
        if g_timings:
            timings.end()
            walk.log( f'{timings}')


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

    global g_build_debug
    global g_build_optimise
    global g_clang
    global g_compositor
    global g_concurrency
    global g_flags_all
    global g_force
    global g_link_only
    global g_max_load_average
    global g_osg_dir
    global g_outdir
    global g_gperf
    global g_timings
    global g_verbose
    
    do_build = False
    
    args = Args( sys.argv[1:])
    if not args.argv:
        args =  Args( '-j 3 -t -b'.split())
    
    while 1:
        try: arg = args.next()
        except StopIteration: break
        #walk.log( 'arg=%s' % arg)
        if 0:
            pass
        
        elif arg == '-b' or arg == '--build':
            do_build = True
        
        elif arg == '--clang':
            g_clang = int( args.next())
        
        elif arg == '--compositor':
            g_compositor = int( args.next())
        
        elif arg == '--debug':
            g_build_debug = int( args.next())
        
        elif arg == '--flags-all':
            g_flags_all = int( args.next())
        
        elif arg == '--force':
            force = args.next()
            if force == 'default':
                g_force = None
            else:
                g_force = int( force)
        
        elif arg == '--gperf':
            g_gperf = int( args.next())
        
        elif arg == '-h' or arg == '--help':
            print( __doc__)
        
        elif arg == '-j':
            g_concurrency = abs(int( args.next()))
            assert g_concurrency >= 0
        
        elif arg == '-l':
            g_max_load_average = float( args.next())
        
        elif arg == '--link-only':
            build( g_link_only=True)
        
        elif arg == '--new':
            path = args.next()
            walk.mtime_cache_mark_new( path)
        
        elif arg == '--old':
            walk.mtime_cache_mark_old( path)
        
        elif arg == '--optimise':
            g_build_optimise = int( args.next())
        
        elif arg == '--osg':
            g_osg_dir = args.next()
        
        elif arg == '--out-dir' or arg == '-o':
            g_outdir = args.next()
        
        elif arg == '--show':
            print( 'compositor:         %s' % g_compositor)
            print( 'concurrency:        %s' % g_concurrency)
            print( 'debug:              %s' % g_build_debug)
            print( 'force:              %s' % ('default' if g_force is None else g_force))
            print( 'clang:              %s' % g_clang)
            print( 'max_load_average:   %s' % g_max_load_average)
            print( 'optimise:           %s' % g_build_optimise)
            print( 'osg:                %s' % g_osg_dir)
            print( 'outdir:             %s' % g_outdir)
            print( 'verbose:            %s' % walk.get_verbose( g_verbose))
        
        elif arg == '-t':
            g_timings = True
        
        elif arg == '--verbose' or arg == '-v':
            v = args.next()
            if v.startswith( '+') or v.startswith( '-'):
                vv = walk.get_verbose( g_verbose)
                for c in v[1:]:
                    if v[0] == '+':
                        if c not in vv:
                            vv += c
                    else:
                        vv = vv.replace( c, '')
                g_verbose = vv
            else:
                g_verbose = v
        
        else:
            raise Exception( 'Unrecognised arg: %s' % arg)
    
    if do_build:
        build()


def exception_info( exception=None, limit=None, out=None, prefix='', oneline=False):
    '''
    General replacement for traceback.* functions that print/return information
    about exceptions. This function provides a simple way of getting the
    functionality provided by these traceback functions:

        traceback.format_exc()
        traceback.format_exception()
        traceback.print_exc()
        traceback.print_exception()

    Returns:
        A string containing description of specified exception and backtrace.

    Inclusion of outer frames:
        We improve upon traceback.* in that we also include stack frames above
        the point at which an exception was caught - frames from the top-level
        <module> or thread creation fn to the try..catch block, which makes
        backtraces much more useful.

        Google 'sys.exc_info backtrace incomplete' for more details.

        We deliberately leave a slightly curious pair of items in the backtrace
        - the point in the try: block that ended up raising an exception, and
        the point in the associated except: block from which we were called.

        For clarity, we insert an empty frame in-between these two items, so
        that one can easily distinguish the two parts of the backtrace.

        So the backtrace looks like this:

            root (e.g. <module> or /usr/lib/python2.7/threading.py:778:__bootstrap():
            ...
            file:line in the except: block where the exception was caught.
            ::(): marker
            file:line in the try: block.
            ...
            file:line where the exception was raised.

        The items after the ::(): marker are the usual items that traceback.*
        shows for an exception.

    Also the backtraces that are generated are more concise than those provided
    by traceback.* - just one line per frame instead of two - and filenames are
    output relative to the current directory if applicatble. And one can easily
    prefix all lines with a specified string, e.g. to indent the text.

    Returns a string containing backtrace and exception information, and sends
    returned string to <out> if specified.

    exception:
        None, or a (type, value, traceback) tuple, e.g. from sys.exc_info(). If
        None, we call sys.exc_info() and use its return value.
    limit:
        None or maximum number of stackframes to output.
    out:
        None or callable taking single <text> parameter or object with a
        'write' member that takes a single <text> parameter.
    prefix:
        Used to prefix all lines of text.
    '''
    if exception is None:
        exception = sys.exc_info()
    etype, value, tb = exception

    if sys.version_info[0] == 2:
        out2 = io.BytesIO()
    else:
        out2 = io.StringIO()
    try:

        frames = []

        # Get frames above point at which exception was caught - frames
        # starting at top-level <module> or thread creation fn, and ending
        # at the point in the catch: block from which we were called.
        #
        # These frames are not included explicitly in sys.exc_info()[2] and are
        # also omitted by traceback.* functions, which makes for incomplete
        # backtraces that miss much useful information.
        #
        for f in reversed(inspect.getouterframes(tb.tb_frame)):
            ff = f[1], f[2], f[3], f[4][0].strip()
            frames.append(ff)

        if 1:
            # It's useful to see boundary between upper and lower frames.
            frames.append( None)

        # Append frames from point in the try: block that caused the exception
        # to be raised, to the point at which the exception was thrown.
        #
        # [One can get similar information using traceback.extract_tb(tb):
        #   for f in traceback.extract_tb(tb):
        #       frames.append(f)
        # ]
        for f in inspect.getinnerframes(tb):
            ff = f[1], f[2], f[3], f[4][0].strip()
            frames.append(ff)

        cwd = os.getcwd() + os.sep
        if oneline:
            if etype and value:
                # The 'exception_text' variable below will usually be assigned
                # something like '<ExceptionType>: <ExceptionValue>', unless
                # there was no explanatory text provided (e.g. "raise Exception()").
                # In this case, str(value) will evaluate to ''.
                exception_text = traceback.format_exception_only(etype, value)[0].strip()
                filename, line, fnname, text = frames[-1]
                if filename.startswith(cwd):
                    filename = filename[len(cwd):]
                if not str(value):
                    # The exception doesn't have any useful explanatory text
                    # (for example, maybe it was raised by an expression like
                    # "assert <expression>" without a subsequent comma).  In
                    # the absence of anything more helpful, print the code that
                    # raised the exception.
                    exception_text += ' (%s)' % text
                line = '%s%s at %s:%s:%s()' % (prefix, exception_text, filename, line, fnname)
                out2.write(line)
        else:
            out2.write( '%sBacktrace:\n' % prefix)
            for frame in frames:
                if frame is None:
                    out2.write( '%s    ^except raise:\n' % prefix)
                    continue
                filename, line, fnname, text = frame
                if filename.startswith( cwd):
                    filename = filename[ len(cwd):]
                if filename.startswith( './'):
                    filename = filename[ 2:]
                out2.write( '%s    %s:%s:%s(): %s\n' % (
                        prefix, filename, line, fnname, text))

            if etype and value:
                out2.write( '%sException:\n' % prefix)
                lines = traceback.format_exception_only( etype, value)
                for line in lines:
                    out2.write( '%s    %s' % ( prefix, line))

        text = out2.getvalue()

        # Write text to <out> if specified.
        out = getattr( out, 'write', out)
        if callable( out):
            out( text)
        return text

    finally:
        # clear things to avoid cycles.
        exception = None
        etype = None
        value = None
        tb = None
        frames = None


if __name__ == '__main__':
    main()
