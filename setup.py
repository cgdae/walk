#!/usr/bin/env python3

import os
import sys

import pipcl

#print( f'{__file__}: sys.arg={sys.argv}')

def build():
    return [
            'walkbuild/walk.py',
            'walkbuild/walkfg.py',
            ('README.md', '$dist-info/README.md'),
            ]

def sdist():
    return pipcl.git_items( os.path.abspath( f'{__file__}/..'))

with open( 'README.md') as f:
    description = f.read()

p = pipcl.Package(
        name='walkbuild',
        version='0',
        summary='Command optimiser - run commands only if they might change generated files.',
        description=description,
        keywords='walk,make,python,build',
        home_page='https://github.com/cgdae/walk',
        author='Julian Smith',
        author_email='jules@op59.net',
        license='SPDX-License-Identifier: GPL-3.0-only',
        classifier = [
            'Programming Language :: Python',
            'Topic :: Software Development :: Build Tools',
            ],
        project_url = [
            'Documentation, https://walk.readthedocs.io/',
            ],

        fn_build=build,
        fn_sdist=sdist,
        description_content_type='text/markdown',
        
        tag_python = 'py3',
        tag_platform = 'any'    # We are a pure python package.
        )

build_wheel = p.build_wheel
build_sdist = p.build_sdist


if __name__ == '__main__':
    p.handle_argv(sys.argv)
