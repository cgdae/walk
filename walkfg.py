#!/usr/bin/env python3

'''
Build script for Flightgear on Unix systems.


Status:

    As of 2020-07-05 we can build on Linux Devuan Beowulf and OpenBSD 6.7.


Requirements:

    The walk.py command optimiser module.
    
    Packages for this script:
    
        python3
        strace
    
    Packages for flightgear code:
    
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
    
    For OpenBSD:
        pkg_add \
                freeglut \
                openscenegraph \
                qtdeclarative \
                

Usage:

    We expect to be in a directory looking like:
    
        flightgear/
        plib/
        simgear/
        fgdata/
        
    Each of these will typically be a git checkout.
    
    In this directory, run this script (wherever it happens to be).
    
        .../walkfg.py -b
    
    All generated files will be in a new directory:
    
        build-walk/
        
    The generated executable will be called:
    
        build-walk/fgfs,debug,opt.exe
    
    It can be run with:
    
        ./build-walk/fgfs,debug,opt.exe --fg-root=fgdata
    
    or:
        ./build-walk/run_fgfs_gdb.sh


Args:

    Arguments are processed in the order they occur on the command line, so
    typically -b or --build should be last.

    -b
    --build
        Build fgfs.
    
    --compositor 0 | 1
        If 1, we build with compositor.
    
    --debug 0 | 1
        If 1, we compile and link with -g to include debug symbols.
    
    --force 0 | 1 | default
        If 0, we never run commands; depending on --verbose, we may output
        diagnostics about what we would have run.

        If 1, we always run commands, regardless of whether output files are up
        to date.
        
        If default, commands are run only if necessary.
    
    -h
    --help
        Show help.
    
    -j N
        Set concurrency level.
    
    --old <path>
        Treat <path> as old.
    
    --optimise 0 | 1
        If 1, we build with compiler optimisations.
    
    -o <directory>
    --out-dir <directory>
        Set the directory that will contain all generated files.
    
    --osg <directory>
        Use local OSG install instead of system OSG.
        
        For example:
            (cd openscenegraph; mkdir build; cd build; cmake -DCMAKE_INSTALL_PREFIX=`pwd`/install -DCMAKE_BUILD_TYPE=Debug ..; time make -j 4; make install)
            .../walkfg.py --osg openscenegraph/build/install -b
    
    --show
        Show settings.
    
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
        
        Default is 'de'.
        
        If arg starts with +/-, we add/remove the specified flags to/from the
        existing settings.
    
    --new <path>
        Treat <path> as new.


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
g_compositor = 1
g_concurrency = 0
g_force = None
g_outdir = 'build-walk'
g_verbose = None
g_clang = False
g_max_load_average = None
g_osg_dir = None

g_os = os.uname()[0]
g_openbsd = g_os == 'OpenBSD'
g_linux = g_os == 'Linux'

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
    #all_files.sort()

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


_gcc_command_compare_regex = None
def gcc_command_compare( a, b):
    global _gcc_command_compare_regex
    if _gcc_command_compare_regex is None:
        _gcc_command_compare_regex = re.compile( ' (-Wno-[^ ]+)|(-std=[^ ]+)')
    aa = re.sub( _gcc_command_compare_regex, '', a)
    bb = re.sub( _gcc_command_compare_regex, '', b)
    #print( 'aa=%s' % aa)
    #print( 'bb=%s' % bb)
    ret = aa != bb
    ret0 = a != b
    if not ret and ret0:
        pass
        #print( 'ignoring command diff:\n    %s\n    %s' % (a, b))
    if ret and not ret0:
        assert 0
    return ret

if 0:
    print( re.sub( ' -Wno-[^ ]+', '', 'gcc -o foo bar.c -Wno-xyz -Werror'))
    print( gcc_command_compare( 'gcc -o foo bar.c -Wno-xyz -Werror', 'gcc -o foo bar.c -Wno-xyz -Werror'))
    print( gcc_command_compare( 'gcc -o foo bar.c -Wno-xyz -Werror', 'gcc -o foo bar.c -Werror'))
    print( gcc_command_compare( 'gcc -o foo bar.c -Wno-xyz -Werror', 'gcc -o foo bar.c -Wno-q -Werror'))
    print( gcc_command_compare( 'gcc -o foo bar.c -Wno-xyz -Werror', 'gcc -o foo bar.c -O2 -Werror'))

def build( link_only=False):

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

    all_files, src_fgfs = get_files()

    # Generate .moc files. We look for files containing Q_OBJECT.
    #
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
                            )


    # Create flightgear's config file.
    #
    fg_version = open('flightgear/flightgear-version').read().strip()
    root = os.path.abspath( '.')

    file_write( textwrap.dedent('''
            #pragma once
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

    file_write(
            '#define REVISION "%s"\n' % git_id( 'flightgear'),
            '%s/walk-generated/Include/build.h' % g_outdir,
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

    if g_openbsd:
        system(
                'rcc'
                        ' -name resources'
                        ' -o %s/walk-generated/flightgear/src/GUI/qrc_resources.cpp'
                        ' flightgear/src/GUI/resources.qrc'
                        % g_outdir
                        ,
                '%s/walk-generated/flightgear/src/GUI/qrc_resources.cpp.walk' % g_outdir,
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
            )

    e = system(
            '%s -o %s/walk-generated/ui_SetupRootDialog.h'
                    ' flightgear/src/GUI/SetupRootDialog.ui' % (uic, g_outdir)
                    ,
            '%s/walk-generated/ui_SetupRootDialog.h.walk' % g_outdir,
            )

    # Set up softlinks that look like a plib install - some code requires plib
    # installation header tree.
    #
    def find( root, leaf):
        for dirpath, dirnames, filenames in os.walk( root):
            if leaf in filenames:
                return os.path.join( dirpath, leaf)
        assert 0

    dirname = '%s/walk-generated/plib-include/plib' % g_outdir
    command = 'mkdir -p %s; cd %s' % (dirname, dirname)
    for leaf in 'pw.h pu.h sg.h netSocket.h js.h ssg.h puAux.h sl.h sm.h sl.h psl.h ul.h pw.h ssgAux.h ssgaSky.h fnt.h ssgaBillboards.h net.h ssgMSFSPalette.h ulRTTI.h puGLUT.h'.split():
        path = find( 'plib', leaf)
        path = os.path.abspath( path)
        command += ' && ln -sf %s %s' % (path, leaf)
    os.system( command)



    # Set up compile/link commands.
    #
    gcc_base = 'cc'
    gpp_base = 'c++ -std=gnu++17'
    if g_clang:
        gcc_base = 'clang'
        gpp_base = 'clang++ -std=c++14'
    gcc_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    gpp_base += ' -pthread -W -Wall -fPIC -Wno-unused-parameter'
    
    # On Linux we end up with compilation errors if we use the results of the
    # feature checking below. But things seem to build ok without.
    #
    # On OpenBSD, we need to do the feature checks, and thy appear to work.
    #
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

    # Define compile/link commands. For linking, we write the .o filenames to a
    # separate file and use gcc's @<filename> to avoid the command becoming too
    # long.
    #
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

    exe += '.exe'

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
                ' openthreads'
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
                ' -l OpenThreads'
                ' -l z'
                ' -pthread'
                )
    
    if g_osg_dir:
        #link_command += f' -L {g_osg_dir}/lib64'
        for l in (
                'osg',
                'osgDB',
                'osgFX',
                'osgGA',
                'osgParticle',
                'osgSim',
                'osgText',
                'osgUtil',
                'osgViewer',
                ):
            # use 'd' to select debug build of osg?
            ll = f'{g_osg_dir}/lib64/lib{l}d.so.*.*.*'
            lll = glob.glob( ll)
            assert len(lll) == 1, f'll={ll!r} lll={lll!r}'
            lll = lll[0]
            link_command += f' {lll}'
        
    if g_linux and not g_osg_dir:
        link_command += (
                ' -l osg'
                ' -l osgDB'
                ' -l osgFX'
                ' -l osgGA'
                ' -l osgParticle'
                ' -l osgSim'
                ' -l osgText'
                ' -l osgUtil'
                ' -l osgViewer'
                )
    
    if g_openbsd:
        link_command += (
                ' -l z'
                ' -l ossaudio'
                ' -l execinfo'  # for backtrace*().
                )
        
    link_command += ' %s' % libs_linkflags
    
    link_command_files = []

    # Sort the source files by mtime so that we compile recently-modified ones
    # first, which helps save time when investigating/fixing compile failures.
    #
    src_fgfs.sort( key=lambda path: -walk.mtime( path))
    
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
                command += ' -O2'
                path_o += ',opt'

            if g_compositor:
                if (0
                        or path.startswith( 'flightgear/src/Canvas/')
                        or path.startswith( 'flightgear/src/Scenery/')
                        or path.startswith( 'flightgear/src/GUI/')
                        or path.startswith( 'flightgear/src/Main/')
                        or path.startswith( 'flightgear/src/Viewer/')
                        or path.startswith( 'flightgear/src/Time/')
                        or path.startswith( 'flightgear/src/Cockpit/')
                        or path.startswith( 'flightgear/src/Network/')
                        or path.startswith( 'flightgear/src/Environment/')
                        ):
                    path_o += ',compositor'
                    command += ' -D ENABLE_COMPOSITOR'
            
            if g_osg_dir:
                path_o += ',osg'
                command += f' -I {g_osg_dir}/include'

            # Add various args to the compile command depending on source path.
            #
            # We could probably use many of the same flags for everything.
            #
            
            # Warnings.
            #
            if path in (
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
                    ):
                command += ' -Wno-implicit-fallthrough'
            
            if g_clang and (0
                    or path.startswith( 'flightgear/')
                    or path.startswith( 'simgear/')
                    or path.startswith( 'plib/')
                    ):
                command += (
                        ' -Wno-inconsistent-missing-override'
                        ' -Wno-overloaded-virtual'
                        ' -Wno-macro-redefined'
                        )
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/flite_hts_engine/flite/')
                    or path.startswith( 'flightgear/3rdparty/hts_engine_API/lib')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/gsm/src/preprocess.c')
                    or path.startswith( 'flightgear/src/GUI')
                    or path.startswith( 'flightgear/src/Navaids/FlightPlan.cxx')
                    or path.startswith( 'simgear/simgear/canvas/elements/CanvasImage.cxx')
                    or path.startswith( 'simgear/simgear/nasal/codegen.c')
                    or path.startswith( 'simgear/simgear/nasal/iolib.c')
                    or path.startswith( 'simgear/simgear/nasal/parse.c')
                    or path.startswith( 'simgear/simgear/nasal/utf8lib.c')
                    or path.startswith( 'simgear/simgear/nasal/utf8lib.c')
                    ):
                command += ' -Wno-sign-compare'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/iaxclient_lib.c')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/unixfuncs.c')
                    or path.startswith( 'flightgear/3rdparty/sqlite3/sqlite3.c')
                    ):
                command += ' -Wno-cast-function-type'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax2-parser.c')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c')
                    or path.startswith( 'flightgear/3rdparty/mongoose/mongoose.c')
                    or path.startswith( 'flightgear/src/Airports/runways.cxx')
                    or path.startswith( 'flightgear/src/ATC/trafficcontrol.cxx')
                    or path.startswith( 'flightgear/src/FDM/ExternalNet/ExternalNet.cxx')
                    or path.startswith( 'flightgear/src/FDM/LaRCsim/ls_interface.c')
                    or path.startswith( 'flightgear/src/GUI/gui_funcs.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/clock.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/gps.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/KLN89/kln89_page_alt.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/KLN89/kln89_page_apt.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/KLN89/kln89_page_cal.cxx')
                    or path.startswith( 'flightgear/src/Instrumentation/kr_87.cxx')
                    or path.startswith( 'flightgear/src/Network/atlas.cxx')
                    or path.startswith( 'flightgear/src/Network/nmea.cxx')
                    ):
                command += ' -Wno-format-truncation'
            
            if (0
                    or path.startswith( 'flightgear/src/FDM/YASim/')
                    or path.startswith( 'flightgear/src/Radio/itm.cpp')
                    or path.startswith( 'simgear/simgear/structure/SGExpression.cxx')
                    or path.startswith( 'simgear/simgear/structure/subsystem_mgr.cxx')
                    ):
                command += ' -Wno-unused-variable'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/flite_hts_engine/flite/src')
                    or path.startswith( 'flightgear/src/Radio/itm.cpp')
                    or path.startswith( 'simgear/simgear/structure/SGExpression.cxx')
                    or path.startswith( 'simgear/simgear/structure/subsystem_mgr.cxx')
                    ):
                command += ' -Wno-unused-function'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/flite_hts_engine/flite/src/lexicon/cst_lexicon.c')
                    ):
                command += ' -Wno-discarded-qualifiers'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/gsm/src/short_term.c')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/libspeex/bits.c')
                    ):
                command += ' -Wno-shift-negative-value'
            
            if (0
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/iaxclient_lib.c')
                    or path.startswith( 'flightgear/3rdparty/iaxclient/lib/libiax2/src/iax.c')
                    ):
                command += ' -Wno-stringop-truncation'
            
            if (0
                    or path.startswith( 'simgear/3rdparty/expat/xmltok.c')
                    ):
                command += ' -Wno-missing-field-initializers'
            
            if (0
                    
                    ):
                command += ' -Wno-'
            
            command += libs_cflags
            
            # Include/define flags.
            if (0
                    or path.startswith( 'flightgear/')
                    or path.startswith( '%s/flightgear/' % g_outdir)
                    or path.startswith( 'simgear/')
                    or path.startswith( '%s/simgear/' % g_outdir)
                    or path.startswith( '%s/walk-generated/flightgear/' % g_outdir)
                    ):
                
                command += cpp_feature_defines

            if path.startswith( 'flightgear/') or path.startswith( '%s/flightgear/' % g_outdir):
                stdcpp = ''
                if path.endswith( '.c'):
                    stdcpp = ''
                command += (
                        ' -I simgear'
                        ' -I flightgear/src'
                        ' -I %s/walk-generated'
                        '%s'
                        ' -D ENABLE_AUDIO_SUPPORT'
                        ' -D JENKINS_BUILD_NUMBER=0'
                        ' -D JENKINS_BUILD_ID=0'
                        % (g_outdir, stdcpp)
                        )

            if path.startswith( 'flightgear/src/AIModel/'):
                command +=  (
                        ' -I flightgear'
                        )
            if path.startswith( 'flightgear/3rdparty/iaxclient'):
                command += (
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
                    command += ' -I flightgear/3rdparty/iaxclient/lib/libspeex/include'

            if path.startswith( 'flightgear/3rdparty/joystick'):
                command += (
                        ' -I flightgear/3rdparty/joystick/lib/portaudio/bindings/cpp/include'
                        ' -I flightgear/3rdparty/joystick/lib/portaudio/include'
                        )

            if path.startswith( 'flightgear/src/FDM/JSBSim/'):
                command += (
                        ' -I flightgear/src/FDM/JSBSim'
                        )

            if path.startswith( 'flightgear/src/FDM/'):
                command += (
                        ' -I flightgear/src/FDM/JSBSim'
                        ' -D ENABLE_JSBSIM'
                        ' -D ENABLE_YASIM'
                        )

            if path.startswith( 'flightgear/src/FDM/JSBSim/FGJSBBase.cpp'):
                command += (
                        ' -D JSBSIM_VERSION="\\"compiled from FlightGear 2020.2.0\\""'
                        )

            if path.startswith( 'flightgear/src/FDM/SP/AISim.cpp'):
                command += (
                        ' -D ENABLE_SP_FDM'
                        )

            if path.startswith( 'flightgear/src/GUI/') or path.startswith( '%s/flightgear/src/GUI/' % g_outdir):
                command += (
                        ' -I %s/walk-generated/Include'
                        ' -I flightgear/3rdparty/fonts'
                        ' -I %s/flightgear/src/GUI'
                        % (g_outdir, g_outdir)
                        )


            if path.startswith( 'flightgear/src/Viewer/') or path.startswith( '%s/flightgear/src/Viewer/' % g_outdir):
                command += (
                        ' -D HAVE_PUI'
                        #' %s' % cflags_libs
                        )

            if path.startswith( 'flightgear/src/Input/'):
                command += (
                        ' -I flightgear/3rdparty/hidapi'
                        ' -I flightgear/3rdparty/joystick'
                        ' -D HAVE_CONFIG_H'
                        )

            if path.startswith( 'flightgear/3rdparty/fonts/'):
                command += (
                        ' -I build-walk/walk-generated/plib-include'
                        )
            
            if path.startswith( 'flightgear/3rdparty/hidapi/'):
                command += (
                        ' -I flightgear/3rdparty/hidapi/hidapi'
                        )

            if path.startswith( 'flightgear/src/Instrumentation/HUD/'):
                command += (
                        ' -I flightgear/3rdparty/fonts'
                        ' -I build-walk/walk-generated/plib-include'
                        )


            if path.startswith( 'flightgear/src/Airports/'):
                if g_linux:
                    command += (
                            ' -DBOOST_BIMAP_DISABLE_SERIALIZATION -DBOOST_NO_STDLIB_CONFIG -DBOOST_NO_AUTO_PTR -DBOOST_NO_CXX98_BINDERS'
                            )
            
            if path.startswith( 'flightgear/src/Main/'):
                command += (
                        ' -I flightgear'
                        ' -D HAVE_CONFIG_H'
                        #' %s' % cflags_libs2
                        )

            if path.startswith( 'flightgear/src/MultiPlayer'):
                command += (
                        ' -I flightgear'
                        )

            if path.startswith( 'flightgear/src/Navaids'):
                command += (
                        ' -I flightgear/3rdparty/sqlite3'
                        )

            if path.startswith( 'flightgear/src/Network'):
                command += (
                        ' -I flightgear'
                        #' %s' % cflags_libs3
                )

            if path.startswith( 'flightgear/src/Scripting/'):
                command += (
                        ' -D HAVE_SYS_TIME_H'
                        )

            if path.startswith( 'flightgear/src/Sound'):
                command += (
                        ' -I flightgear/3rdparty/flite_hts_engine/include'
                        ' -I flightgear/3rdparty/hts_engine_API/include'
                        )

            if path.startswith( 'flightgear/src/Cockpit'):
                command += (
                        ' -I flightgear/3rdparty/fonts'
                        )

            if path.startswith( 'simgear/simgear/'):
                command += (
                        ' -I simgear'
                        ' -I simgear/simgear/canvas/ShivaVG/include'
                        ' -I simgear/3rdparty/udns'
                        ' -I %s/walk-generated'
                        ' -I %s/walk-generated/simgear'
                        ' -D HAVE_STD_INDEX_SEQUENCE' # prob not necessary.
                        % (g_outdir, g_outdir)
                        )
            if (0
                    or path.startswith( 'simgear/simgear/canvas/Canvas.cxx')
                    or path.startswith( 'flightgear/src/AIModel/AIBase.cxx')
                    ):
                command += cpp_feature_defines
            
            if path.startswith( 'simgear/simgear/sound'):
                command += (
                        ' -D ENABLE_SOUND'
                        )

            if path.startswith( 'simgear/simgear/xml'):
                command += (
                        ' -I simgear/3rdparty/expat'
                        )

            if path.startswith( 'simgear/3rdparty/expat'):
                command += (
                        ' -D HAVE_MEMMOVE'
                        )

            if path.startswith( 'plib/'):
                command += (
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
                        )
                
                if g_openbsd:
                    command += ' -I /usr/X11R6/include'

            if path.startswith( 'plib/src/ssgAux'):
                command += (
                        ' -I plib/src/ssg'
                        )

            if path.startswith( '%s/walk-generated/EmbeddedResources' % g_outdir):
                command += (
                        ' -I simgear'
                        )
            
            #if g_openbsd and path.startswith( '%s/walk-generated/flightgear/src/GUI' % g_outdir):
            #    command += (
            #            #' %s' % cflags_libs5
            #            )

            if path.startswith( 'flightgear/3rdparty/flite_hts_engine'):
                command += (
                        ' -I flightgear/3rdparty/flite_hts_engine/flite/include'
                        ' -I flightgear/3rdparty/flite_hts_engine/include'
                        ' -I flightgear/3rdparty/hts_engine_API/include'
                        ' -I flightgear/3rdparty/flite_hts_engine/flite/lang/usenglish'
                        ' -I flightgear/3rdparty/flite_hts_engine/flite/lang/cmulex'
                        ' -D FLITE_PLUS_HTS_ENGINE'
                        )

            if path.startswith( 'flightgear/3rdparty/hts_engine_API/lib'):
                command += (
                        ' -I flightgear/3rdparty/hts_engine_API/include'
                        )


            if path.startswith( 'simgear/simgear/canvas/ShivaVG'):
                command += (
                        ' -D HAVE_INTTYPES_H'
                        )

            if path.startswith( 'flightgear/src/Network/Swift'):
                command += (''
                        #' %s' % cflags_libs3
                        )

            if ( 0
                    or path.startswith( 'flightgear/src/ATC/')
                    or path.startswith( 'flightgear/src/Cockpit/')
                    or path.startswith( 'flightgear/src/GUI/')
                    or path.startswith( 'flightgear/src/Main/')
                    or path.startswith( 'flightgear/src/Model/')
                    or path.startswith( 'flightgear/src/Viewer/')
                    ):
                command += (
                        ' -I %s/walk-generated/plib-include' % g_outdir
                        )


            path_o += '.o'
            link_command_files.append( ' %s' % path_o)

            if not link_only:
                command += ' -o %s %s' % (path_o, path)

                # Tell walk to schedule running of the compile command if necessary.
                #
                system_concurrent(
                        walk_concurrent,
                        command,
                        '%s.walk' % path_o,
                        description='Compiling to %s' % path_o,
                        command_compare=gcc_command_compare,
                        )

        # Wait for all compile commands to finish before doing the link.
        #
        walk_concurrent.join()
        
        walk.log( 'Finished compiling.')
        
        link_command_extra_path = '%s-link-extra' % exe
        link_command_files.sort()
        link_command_files = '\n'.join( link_command_files)
        file_write( link_command_files, link_command_extra_path)

        link_command += ' @%s' % link_command_extra_path
        
        #link_command += ' -Wl,--verbose'

        # Tell walk to run our link command if necessary.
        #
        system( link_command, '%s.walk' % exe, description='Linking %s' % exe)

        # Create a script to run our generated executable via gdb.
        #
        walk.log( 'Creating gdb wrapper script for fgfs.')
        run_fgfs_path = '%s-run-gdb.sh' % exe
        file_write(''
                + '#!/bin/sh\n'
                    + ('egdb' if g_openbsd else 'gdb')
                    + ' -ex "handle SIGPIPE noprint nostop"'
                    + ' -ex "set print thread-events off"'
                    + ' -ex "set print pretty on"'
                    + ' -ex run'
                    + f' --args  {exe} "$@"'
                    + '\n'
                ,
                run_fgfs_path,
                )
        os.system( 'chmod u+x %s' % run_fgfs_path)
        
        walk.log_prefix_set( '[100%] ')
        walk.log( 'Build finished successfully.')

    finally:

        # Terminate and wait for walk_concurrent's threads before we finish.
        #
        walk_concurrent.end()


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
    global g_force
    global g_outdir
    global g_verbose
    global g_max_load_average
    global g_osg_dir
    
    args = Args( sys.argv[1:])
    
    while 1:
        try: arg = args.next()
        except StopIteration: break
        #walk.log( 'arg=%s' % arg)
        if 0:
            pass
        
        elif arg == '-b' or arg == '--build':
            build()
        
        elif arg == '-l':
            g_max_load_average = float( args.next())
        
        elif arg == '--link-only':
            build( link_only=True)
        
        elif arg == '--clang':
            g_clang = int( args.next())
        
        elif arg == '--compositor':
            g_compositor = int( args.next())
        
        elif arg == '--debug':
            g_debug = int( args.next())
        
        elif arg == '--force':
            force = args.next()
            if force == 'default':
                g_force = None
            else:
                g_force = int( force)
        
        elif arg == '-h' or arg == '--help':
            print( __doc__)
        
        elif arg == '-j':
            g_concurrency = abs(int( args.next()))
            assert g_concurrency >= 0
        
        elif arg == '--old':
            walk.mtime_cache_mark_old( path)
        
        elif arg == '--osg':
            g_osg_dir = args.next()
        
        elif arg == '--optimise':
            g_optimise = int( args.next())
        
        elif arg == '--out-dir' or arg == '-o':
            g_outdir = args.next()
        
        elif arg == '--show':
            print( 'compositor:     %s' % g_compositor)
            print( 'concurrency:    %s' % g_concurrency)
            print( 'debug:          %s' % g_build_debug)
            print( 'force:          %s' % ('default' if g_force is None else g_force))
            print( 'optimise:       %s' % g_build_optimise)
            print( 'outdir:         %s' % g_outdir)
            print( 'verbose:        %s' % walk.get_verbose( g_verbose))
        
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
        
        elif arg == '--new':
            path = args.next()
            walk.mtime_cache_mark_new( path)
        
        else:
            raise Exception( 'Unrecognised arg: %s' % arg)
        

if __name__ == '__main__':
    main()
