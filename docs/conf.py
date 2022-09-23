'''
Example build command: sphinx-build -M html docs docs/_build
'''

import glob
import os
import resource
import shutil
import subprocess
import sys
import textwrap
import time


def _log( text):
    print( text)

def _system( command, env_extra=None):
    env = None
    if env_extra:
        env = os.environ.copy()
        env.update(env_extra)
    _log( f'Running: {command}')
    subprocess.run( command, shell=True, check=True, env=env)


def _sphinx_index_rst_toctree( path):
    '''
    Finds the `.. toctree::` text in specified file.
    
    Returns `(text, toc_begin, toc_end)`.
    '''
    text = _fs_read( path)
    begin = text.find( '\n.. toctree::')
    assert begin >= 0
    begin += 1
    end = begin
    pos = end
    begin = None
    assert text[pos] == '.'
    while 1:
        pos = text.find( '\n', pos)
        if begin is None:
            begin = pos+1 if pos >= 0 else len(text)
        if end is None:
            end = pos+1 if pos >= 0 else len(text)
        if pos == -1 or pos + 1 == len(text):
            break
        pos += 1
        if text[ pos] == ' ':
            end = None
        elif text[ pos] == '\n':
            pass
        else:
            break
    return text, begin, end


def _make_list( value):
    '''
    Converts None or comma-separated string into a list.
    '''
    if value is None:
        return []
    if isinstance( value, str):
        return value.split( ',')
    assert isinstance( value, list)
    return value


def _pythons_to_pythonpath( pythons):
    '''
    Returns: string suitable for :envvar:`$PYTHONPATH`, containing absolete
    paths.
    
    Args:
        pythons: List of directories.
    '''
    value = []
    for python in pythons:
        python = os.path.abspath( python)
        value.append( python)
    value = ':'.join( value)
    return dict( PYTHONPATH=value)

def _git_get_files( directory, submodules=False):
    '''
    Returns list of all files known to git in `directory`; `directory` must be
    somewhere within a git checkout.

    Returned names are all relative to `directory`.

    If `<directory>.git` exists we use git-ls-files and write list of files to
    `<directory>/jtest-git-files`.

    Otherwise we require that `<directory>/jtest-git-files` already exists.
    '''
    def is_within_git_checkout( d):
        while 1:
            #log( '{d=}')
            if not d:
                break
            if os.path.isdir( f'{d}/.git'):
                return True
            d = os.path.dirname( d)

    if is_within_git_checkout( directory):
        command = 'cd ' + directory + ' && git ls-files'
        if submodules:
            command += ' --recurse-submodules'
        command += ' > jtest-git-files'
        system( command, verbose=False)

    with open( '%s/jtest-git-files' % directory, 'r') as f:
        text = f.read()
    ret = text.strip().split( '\n')
    return ret

def _apidoc_git_excludes( directory):
    '''
    Returns list of files in `directory` that are
    not known to git.
    '''
    git_files = _git_get_files( directory)
    ret = []
    for leaf in os.listdir( directory):
        if leaf.endswith( '.py') and leaf not in git_files:
            ret.append( leaf)
    return ret

def _fs_read( path, binary=False):
    with open( path, 'rb' if binary else 'r') as f:
        return f.read()

def _fs_write( path, data, binary=False):
    with open( path, 'wb' if binary else 'w') as f:
        return f.write( data)

def _fs_remove( path):
    '''
    Removes file or directory, without raising exception if it doesn't exist.

    path:
        The path to remove.

    We assert-fail if the path still exists when we return, in case of
    permission problems etc.
    '''
    try:
        os.remove( path)
    except Exception:
        pass
    shutil.rmtree( path, ignore_errors=1)
    assert not os.path.exists( path)


def init(
        name,
        author_=None,
        rst_dirs=None,
        clib_dirs=None,
        python_dirs=None,
        config: bool=True,
        no_maxwidth=True,
        theme=None,
        builder=None,
        extensions_=None,
        black_foreground=False,
        _apidoc=True,
        ):
    '''
    Uses sphinx to generate documentation. By default we build html
    documentation in `<__file__>/../_build/html/`.
    
    Requires `sphinx` and `doxygen` to be installed.
    
    We generate documentation from different sources:
    
        * Pre-existing `.rst files`, specified by `rst_dirs`.

        * C/C++ header files, specified by `clib_dirs` (this uses `doxygen` and
          sphinx extensions `breathe` and `exhale`).

        * Python scripts/modules, specified by `python_dirs` (this uses
          `sphinx-apidoc`).

    Note: it looks like sphinx can get the output directory into an odd state
    which makes reruns go very slowly. When this happens, deleting the output
    directory seems to fix things.

    Args:
        
        name:
            Name of project.
        author_:
            Author.
        rst_dirs:
            A list (or comma-separated string) of directories containing
            (typically hand-written) `.rst` or `.md` files to be included in
            the documentation.
        clib_dirs:
            A list (or comma-separated string) of directories with C/C++
            headers to document, using `exhale`/`breathe`/`doxygen` to extract
            comments. Can also contain specific filenames.
        python_dirs:
            A list (or comma-separated string) of directories in which to
            look for python packages and modules. We generate documentation
            for these python packages and modules from doc comments, using
            `sphinx-apidoc`. We exclude `.py` files that are not known to git.
            Dirs should be absolute or relative to `{__file__}/..`.
        config:
            If true (the default) we (re)generate `conf.py` and `index.rst` by
            running `sphinx-quickstart` and then patching the generated files.
        no_maxwidth:
            If true, we attempt to prevent generated HTML from
            having a max width, by rather crudely modifying
            `<directory>/_build/html/_static/*.css` files.
        theme:
            Name of html theme, e.g. **basic** or **scroll**.
        builder:
            The sphinx builder.
            
                * If `None` we default to **html**.
            
                * If **pdf** we uses `rst2pdf` to generate PDF output.

                * If **latexpdf** we use `latexmk` and LaTeX to generate PDF output.

                    * Does not seem to work as well as **pdf**, for example the
                      contents section can be empty.
                    * requires `latexmk` and LaTeX.
                    * On OpenBSD: `sudo pkg_add latexmk texlive_texmf-full`
        extensions_:
            Extra extensions.
        black_foreground:
            If true we set `body:color` to **#000** in our custom css.
        _apidoc:
            Experimental. Whether to run sphinx-apidoc. Unfortunately ommiting
            apidoc does not seem to improve speed of subsequent run of
            sphinx-build.

    Example commands:
        python3 -m venv pylocal
        . pylocal/bin/activate
        pip install --upgrade pip sphinx sphinx_rtd_theme breathe exhale myst_parser
        (cd docs && sphinx-build -M html . _build)
    '''
    directory = os.path.abspath( f'{__file__}/..')
    rst_dirs = _make_list( rst_dirs)
    clib_dirs = _make_list( clib_dirs)
    python_dirs = _make_list( python_dirs)
    extensions_ = _make_list( extensions_)
    
    env_pythonpath = _pythons_to_pythonpath( python_dirs)

    if builder is None:
        builder = 'html'
    
    if os.uname()[0] == 'OpenBSD':
        # Check how much memory we have.
        #
        soft, hard = resource.getrlimit( resource.RLIMIT_DATA)
        if soft < 2 * 2**30:
            _log( f'Warning: RLIMIT_DATA soft={soft} may be too small.')
    
    if config:
        # Set `conf.py` globals, create `index.rst`, and post-process.
        #
        os.makedirs( directory, exist_ok=True)
        os.makedirs( f'{directory}/_static', exist_ok=True)
        _fs_remove( f'{directory}/index.rst')

        extensions_.append( 'sphinx.ext.napoleon')
        _log( f'clib_dirs: {clib_dirs}')
        if clib_dirs:
            extensions_.append( 'breathe')
            extensions_.append( 'exhale')
        if builder == 'pdf':
            extensions_.append( 'rst2pdf.pdfbuilder')

        if theme is None:
            theme = 'sphinx_rtd_theme'

        global project
        global copyright
        global author
        global extensions
        global templates_path
        global language
        global exclude_patterns
        global html_theme
        global html_static_path
        global html_css_files
        global html_theme_options
        global breathe_projects
        global breathe_default_project
        global exhale_args
        global autoclass_content
        
        project = name
        copyright = f'{time.strftime("%Y")}, {author_}'
        author = author_
        extensions = extensions_ + [
                'sphinx.ext.autodoc',
                'sphinx.ext.doctest',
                'sphinx.ext.napoleon',
                ]
        _log( f'extensions: {extensions}')
        templates_path = ['_templates']
        language = 'en'
        exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']
        html_theme = "sphinx_rtd_theme"
        html_static_path = ['_static']
        html_css_files = ["makedocs_custom.css"]
        html_theme_options = dict()
        if no_maxwidth:
            html_theme_options[ "body_max_width"] = "none"
            #"navigation_depth": 2,
            #"collapse_navigation": True,
        breathe_projects = { "myproject": "_build/doxygen/xml/"}
        breathe_default_project = "myproject"
        autoclass_content = 'both'  # So sphinx includes __init__()'s doc-comment.

        os.makedirs( f'{directory}/_build/html/_static', exist_ok=True)
        with open( f'{directory}/_build/html/_static/makedocs_custom.css', 'w') as f:
            if black_foreground:
                f.write( textwrap.dedent( '''
                        body
                        {
                            color:#000;
                        }
                        '''))
            f.write( textwrap.dedent( '''
                    summary
                    {
                        cursor:pointer;
                    }
                    '''))

        if builder=='pdf':
            global pdf_stylesheets
            global pdf_documents
            pdf_stylesheets = ["twocolumn"]
            pdf_documents = [("index", "{name}", "{name}", "{author_}")]
    
        if python_dirs and _apidoc:
            # Create `.rst` files from Python scripts and modules.
            #
            for python_dir in python_dirs:
                # Run sphinx-apidoc. We use '-f' to force overwriting of existing
                # .rst files.
                python_dir = os.path.relpath( python_dir, directory)
                excludes = []
                if os.path.exists( f'{directory}/.git'):
                    excludes = _apidoc_git_excludes( directory)
                excludes = ' '.join( excludes)
                _log( f'Running sphinx-apidoc to extract .rst content from {python_dir}.')
                _system(
                        f'cd {directory} && sphinx-apidoc --module-first -e -f -o . {python_dir} {excludes}',
                        env_extra=env_pythonpath,
                        )

        # Copy `.rst` and `.md` files specified by `rst_dirs` (directories
        # containing typically hand-written `.rst` and `.md` files) into
        # `<directory>/`.
        #
        rst_hand_written = set()
        if rst_dirs:
            # Copy hand-written `.rst` and `.md` files into `<directory>/`.
            for rst_dir in rst_dirs:
                for path in glob.glob( f'{rst_dir}/*.rst') + glob.glob( f'{rst_dir}/*.md'):
                    if path.endswith( '/index.rst') or path.endswith( '/index.md'):
                        continue
                    path_leaf = os.path.basename( path)
                    if path_leaf in rst_hand_written:
                        raise Exception( f'Duplicate hand-written .rst/.md leafname: {path}')
                    rst_hand_written.add( path_leaf)
                    destination = f'{directory}/{path_leaf}'
                    shutil.copy2( path, destination)
        
        # Create index.rst.
        #
        title = f'{name} documentation'
        text = ''
        text += f'{title}\n{"="*len(title)}\n'
        text = textwrap.dedent(f'''
                {title}
                {"="*len(title)}
                
                .. toctree::
                   :maxdepth: 3
                   :caption: Contents:

                ''')
        for rst in rst_hand_written:
            text += f'   {os.path.basename(rst)}\n'
                
        # Add clib documentation to index.rst.
        if clib_dirs:
            text += '\n'   # This blank line seems to be important.
            text += '   about\n'
            text += '   api_exhale/library_root\n'
        
        if python_dirs:
            # Add modules.rst created by sphinx-apidoc.
            text += f'   modules.rst\n'
        
        _fs_write( f'{directory}/index.rst', text)


root = os.path.abspath( f'{__file__}/../..')

init(
        name='Walk',
        author_='Julian Smith',
        python_dirs=f'{root}/walkbuild',
        extensions_='myst_parser',  # Support for .md files.
        rst_dirs=root,  # Include README.md.
        )

# Add walkbuild/ directory to sys.path so that sphinx will find walk.py and
# walkfg.py.
#
sys.path.append( f'{root}/walkbuild')
