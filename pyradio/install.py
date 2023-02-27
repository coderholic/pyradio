import sys
import os
import subprocess
import shutil
import zipfile
import platform
import json
from time import sleep
import site
import glob

import locale
locale.setlocale(locale.LC_ALL, "")

try:
    from os.path import curdir, exists
    import ctypes
    import win32api
    import win32ui
except:
    pass

try:
    from urllib.request import urlopen
except:
    try:
        from urllib2 import urlopen
    except:
        pass

try:
    import requests
    HAVE_REQUESTS = True
except:
    HAVE_REQUESTS = False

VERSION = ''

PY3 = sys.version[0] == '3'

if PY3:
    try:
        from rich import print
    except:
        if platform.system().lower().startswith('win'):
            subprocess.call('python -m pip install rich 1>NUL 2>NUL', shell=True)
            from rich import print
        else:
            print('''Error: Module "rich" not found!

Please install the above module and try again.

Debial based distros:
    sudo apt install python3-rich

Arch based distros:
    sudo apt install python-rich

Fedora based distros:
    sudo dnf install python-rich

OpenSUSE based distros:
    sudo zypper install python3-rich

If everything else fails, try:
    python -m pip install rich
or
    python3 -m pip install rich

''')
            sys.exit(1)

# import logging
# logger = logging.getLogger(__name__)

''' This is PyRadio version this
    install.py was released for
'''
PyRadioInstallPyReleaseVersion = '0.9.2'

def print_pyradio_on():
    msg = '''[bold magenta]
                     _____       _____           _ _
                    |  __ \     |  __ \         | (_)
                    | |__) |   _| |__) |__ _  __| |_  ___
                    |  ___/ | | |  _  // _` |/ _` | |/ _ \\
                    | |   | |_| | | \ \ (_| | (_| | | (_) |
                    |_|    \__, |_|  \_\__,_|\__,_|_|\___/
                            __/ |
                           |___/
[/bold magenta]
                               [bold]installation script
                                   running on[/bold]
'''
    if PY3:
        print(msg)
    else:
        print(msg.replace('[bold]', '').replace('[/bold]', '').replace('[bold magenta]', '').replace('[/bold magenta]', ''))

def print_python2():
    print('''                   _____       _   _                    ___
                  |  __ \     | | | |                  |__ \\
                  | |__) |   _| |_| |__   ___  _ __       ) |
                  |  ___/ | | | __| '_ \ / _ \| '_ \     / /
                  | |   | |_| | |_| | | | (_) | | | |   / /_
                  |_|    \__, |\__|_| |_|\___/|_| |_|  |____|
                          __/ |
                         |___/


    ''')

def print_python3():
    msg = '''[bold green]                   _____       _   _                    ____
                  |  __ \     | | | |                  |___ \\
                  | |__) |   _| |_| |__   ___  _ __      __) |
                  |  ___/ | | | __| '_ \ / _ \| '_ \    |__ <
                  | |   | |_| | |_| | | | (_) | | | |   ___) |
                  |_|    \__, |\__|_| |_|\___/|_| |_|  |____/
                          __/ |
                         |___/
[/bold green]

    '''
    print(msg)

def print_no_python2():
    print('''                                 not Supported!!!
                             Please upgade to Python 3
''')

def print_trying_to_install():
    print('                              trying to install for')

def find_pyradio_win_exe():
    ''' find pyradio EXE files

        Return (system_exe, user_exe)
    '''
    exe = [None, None]
    for a_path in site.getsitepackages():
        if a_path.split(os.sep)[-1].startswith('Python'):
            py_with_ver = a_path.split(os.sep)[-1]
        an_exe = os.path.join(a_path, 'Scripts' , 'pyradio.exe')
        if os.path.exists(an_exe):
            exe[0] = an_exe
    an_exe = os.path.join(site.getuserbase(), py_with_ver, 'Scripts' , 'pyradio.exe')
    # print('an_exe: {}'.format(an_exe))
    if os.path.exists(an_exe):
        exe[1] = an_exe
    # print('exe: {}'.format(exe))
    return exe

def fix_pyradio_win_exe():
    exe = find_pyradio_win_exe()
    if exe[0]:
        a_path = os.getenv('PROGRAMFILES(x86)')
        if a_path:
            exe[0] = exe[0].replace(a_path, '%PROGRAMFILES(x86)%')
        a_path = os.getenv('PROGRAMFILES')
        if a_path:
            exe[0] = exe[0].replace(a_path, '%PROGRAMFILES%')
    if exe[1]:
        a_path = os.getenv('APPDATA')
        if a_path:
            exe[1] = exe[1].replace(a_path, '%APPDATA%')
    return exe

def is_pyradio_user_installed():
    if platform.system().lower().startswith('darwin'):
        return False
    p = subprocess.Popen('which pyradio',
                         shell=True,
                         stdout=subprocess.PIPE,
                         stderr=subprocess.DEVNULL
                         )
    ret = str(p.communicate()[0])
    home = os.path.expanduser('~')
    return True if ret.startswith(home) else False

def isRunning():
    count = 1
    ctypes.windll.kernel32.SetConsoleTitleW('PyRadio Installation')
    while WindowExists('PyRadio: Your Internet Radio Player') or \
            WindowExists('PyRadio: Your Internet Radio Player (Session Locked)'):
        sleep(1)
        if count > 2:
            print('[bold magebta]PyRadio[/bold magebta] is still running. Please terminate it to continue ... ')
        cout += 1
    print('')

def version_string_to_list(this_version):
    # logger.error('DE this_version = "{}"'.format(this_version))
    poped = False
    tokens = ('sng', 'dev', 'git')
    sp = this_version.split('-')
    while sp[-1] in tokens:
        p = sp.pop()
        if p != 'git':
            poped = True
    if poped:
        sp.pop()
    a_v = '.'.join(sp).lower()
    # a_v = this_version.replace('-', '.').lower()
    a_l = a_v.split('.')
    while len(a_l) < 4:
        a_l.append('0')
    a_n_l = []
    # logger.error('DE a_n_l = "{}"'.format(a_n_l))
    for i, n in enumerate(a_l):
        if 'beta' in n:
            a_n_l.append(-200+int(a_l[-1].replace('beta', '')))
        elif 'rc' in n:
            a_n_l.append(-100+int(a_l[-1].replace('rc', '')))
        elif 'r' in n:
            pass
        else:
            if len(n) < 4 and i > 0:
                try:
                    a_n_l.append(int(n))
                except ValueError:
                    pass
        # logger.error('DE a_n_l = "{}"'.format(a_n_l))
    return a_n_l

def get_github_long_description_for_script():
    ret = get_github_long_description()
    if ret[1]:
        print(ret[1])
    else:
        print('')

def get_github_long_description(
    only_tag_name=False,
    devel=False,
    use_sng_repo=False,
    sng_branch=False,
    do_not_exit=False
):
    ''' get PyRadio GitHub data

        Parameters
        ----------
            only_tag_name
                If True, just return the latest tag name

            use_sng_repo
                If True, user is 's-n-g'
                This means that a development release is being built

            sng_branch
                Only maked sense if use_sng_repo is True

                If False, use branch devel
                If True, use branch master

                Not Implemented yet!

        Returns
        -------
        If only_tag_name is True
            (str) tag name

        If only_tag_name is False
            (tuple) tag name, git long description

            `git long description` is equivalant to the command:
                git describe --long --tags
    '''
    user = 'coderholic'
    if only_tag_name:
        points = ('tags', )
    else:
        points = ('commits', 'tags')
        if use_sng_repo:
            user = 's-n-g'
    returns = []
    for n in points:
        ret = None
        if n == 'tags':
            url = 'https://api.github.com/repos/coderholic/pyradio/tags'
        else:
            url = 'https://api.github.com/repos/' + user + '/pyradio/' + n
            if use_sng_repo and not sng_branch:
                url += '?sha=devel'
            else:
                url += '?sha=master'
            url += '&per_page=50'
        try:
            if sys.version_info < (3, 0):
                ret = urlopen(url).read()
            else:
                with urlopen(url) as https_response:
                    ret = https_response.read()
        except:
            if do_not_exit:
                ret = None
            else:
                print('Error: Cannot contact GitHub!\n       Please make sure your internet connection is up and try again.')
                sys.exit(1)

        try:
            returns.append(json.loads(ret))
        except:
            if do_not_exit:
                ret = None
            else:
                print('Error: Malformed GitHub response!\n       Please make sure your internet connection is up and try again.')
                sys.exit(1)

        # for r in returns:
        #     for n in r:
        #         print(n, '\n\n')

    if ret is None:
        if only_tag_name:
            return None
        else:
            return None, None

    if only_tag_name:
        return returns[0][0]['name']

    tag_hash = returns[1][0]['commit']['sha']
    tag_name = returns[1][0]['name']

    for i, n in enumerate(returns[0]):
        if n['sha'] == tag_hash:
            revision = i
            break
    else:
        revision = 0

    # print('\n\n' + tag_name)
    # print(tag_hash)
    # print(str(use_sng_repo))
    # revision=15
    # print(revision)

    if revision > 0:
        if devel:
            ''' coderholic devel branch
                currently it does not exist
            '''
            this_version = tag_name + '-r' + str(revision) + '-' + returns[0][0]['sha'][:8] + '-dev'
        else:
            ''' coderholic master branch '''
            this_version = tag_name + '-' + str(revision) + '-' + returns[0][0]['sha'][:8]
        if use_sng_repo:
            ''' sng repo '''
            this_version = tag_name + '-r' + str(revision) + '-' + returns[0][0]['sha'][:8] + '-sng'
            if not sng_branch:
                ''' sng devel branch '''
                this_version += '-dev'
    else:
        this_version = None

    # if this_version:
    #     print('this_version = ' + this_version)
    return tag_name, this_version

def get_github_tag(do_not_exit=False):
    ''' get the name of the latest PyRadio tag on GitHub '''
    return get_github_long_description(only_tag_name=True, do_not_exit=do_not_exit)

def get_next_release():
    ''' not used '''
    r = get_github_long_description()
    print('Description: {}'.format(r))

    sp = r[1].split('-')
    print('sp = {}'.format(sp))
    x = int(sp[1]) + 1
    return sp[0] + '-{}'.format(x)

def get_devel_version():
    long_descpr = get_github_long_description(do_not_exit=True)
    if long_descpr[0]:
        if long_descpr[1]:
            return 'PyRadio ' + long_descpr[1]
        else:
            return 'PyRadio ' + long_descpr[0]
    else:
        return None

def windows_put_devel_version():
    ''' not used '''
    long_descr = get_github_long_description()[1]
    if long_descr:
        from shutil import copyfile
        cur_dir = os.getcwd()
        copyfile(os.path.join(cur_dir, 'config.py'), os.path.join(cur_dir, 'config.py.dev'))
        try:
            with open(os.path.join(cur_dir, 'config.py'), 'r', encoding='utf-8') as con:
                lines = con.read()
            lines = lines.replace("git_description = ''", "git_description = '" + long_descr + "'")
            with open(os.path.join(cur_dir, 'config.py'), 'w', encoding='utf-8') as con:
                con.write(lines)
        except:
            print('Error: Cannot change downloaded files...\n       Please close all running programs and try again.')
            sys.exit(1)

def WindowExists(title):
    ''' fixing #146  '''
    try:
        import win32api
        import win32ui
    except:
        pass
    try:
        win32ui.FindWindow(None, title)
    except UnboundLocalError:
        # os.system('cls')
        msg = '''\n\n[bold magenta]PyRadio[/bold magenta] has installed all required python modules.
In order for them to be properly loaded, the installation script
has to [bold green]start afresh[/bold green].

Please execute the installation script again, like so:

    [bold red]python install.py[/bold red]

'''
        print(msg)
        sys.exit()
    except win32ui.error:
        return False
    else:
        return True


class PythonExecutable(object):
    is_debian = False
    _python = [None, None]
    requested_python_version = 3

    def __init__(self, requested_python_version):
        self.requested_python_version = requested_python_version
        if not platform.system().lower().startswith('win'):
            self._check_if_is_debian_based()
        self._get_pythons()

    def __str__(self):
        return 'Is Debian: {0}\nPython: {1}, {2}\nRequested version: {3}'.format(
            self.is_debian,
            self._python[0],
            self._python[1],
            self.requested_python_version
        )

    @property
    def python(self):
        return self._python[self.requested_python_version-2]

    @python.setter
    def python(self, value):
        raise RuntimeError('ValueError: property is read only!')

    def _check_if_is_debian_based(self):
        p = subprocess.Popen(
            'apt --version',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        p.communicate()
        self.is_debian = True if p.returncode == 0 else False
        return self.is_debian

    def _get_pythons(self):
        ''' get python (no version) '''
        p = subprocess.Popen(
            'python --version',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        for com in p.communicate():
            str_com = str(com)
            if 'Python 2.' in str_com or \
                    'python 2.' in str_com:
                self._python[0] = 'python'
                break
            elif 'Python 3.' in str_com or \
                    'python 3.' in str_com:
                self._python[1] = 'python'
                break

        ''' get versioned names '''
        for n in range(2, 4):
            if self._python[n-2] is None:
                self._get_python(n)

    def _get_python(self, version):
        p = subprocess.Popen(
            'python' + str(version) + ' --version',
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        # print(p.communicate())
        # print(p.returncode)
        # if p.communicate()[0]:
        p.communicate()
        if p.returncode == 0:
            self._python[version - 2] = 'python' + str(version)

    def can_install(self):
        return True if self._python[self.requested_python_version - 2] else False


class PyRadioUpdate(object):

    ''' package values:
            0   -   official release
            1   -   s-n-g release
            2   -   s-h-g devel
            3   -   official devel
    '''

    ZIP_URL = ['https://github.com/coderholic/pyradio/archive/',
               'https://github.com/s-n-g/pyradio/archive/master.zip',
               'https://github.com/s-n-g/pyradio/archive/devel.zip',
               'https://github.com/coderholic/pyradio/archive/devel.zip',
               'https://github.com/coderholic/pyradio/archive/master.zip',
               ]

    ZIP_DIR  = ['pyradio-',
                'pyradio-master',
                'pyradio-devel',
                'pyradio-devel',
                'pyradio-master'
                ]

    install = False
    user = True
    python2 = False

    _python_exec = None

    _delete_dir_limit = 0

    def __init__(self,
                 package=0,
                 user=True,
                 github_long_description=None,
                 python_version_to_use=3):
        if platform.system().lower().startswith('win'):
            raise RuntimeError('This is a linux only class...')
        self._dir = self._install_dir = ''
        self._package = package
        self.user = user
        self._github_long_description = github_long_description
        self._python_exec = PythonExecutable(python_version_to_use)
        self.python2 = True if python_version_to_use == 2 else False

    def update_pyradio(self, win_open_dir=False):
        if platform.system().lower().startswith('win'):
            ''' create BAT file to update or execute '''
            if win_open_dir:
                self.update_or_uninstall_on_windows('update-open')
            else:
                self.update_or_uninstall_on_windows('update')
        else:
            ''' update PyRadio under Linux and MacOS '''
            if self.install:
                print('Installing PyRadio...')
            else:
                print('Updating PyRadio...')
            if self._do_it():
                if self.install:
                    print('\n\nPyRadio succesfully installed!')
                    print('Hope you have a lot of fun using it!')
                else:
                    print('\n\nPyRadio updated to the latest release!')
                    print('Thank you for your continuous support to this project!')
                print('Cheers!\n')
                sys.exit()
            else:
                print('\n\nAn error occured during the installation!')
                print('This should have never had happened...')
                print('Please report this at http://github.com/coderholic/pyradio/issues\n')
                sys.exit(1)

    def remove_pyradio(self, win_open_dir=False):
        if platform.system().lower().startswith('win'):
            ''' create BAT file to update or execute '''
            if win_open_dir:
                self.update_or_uninstall_on_windows('uninstall-open')
            else:
                self.update_or_uninstall_on_windows('uninstall')
        else:
            ''' uninstall PyRadio under Linux and MacOS '''
            print('Uninstalling PyRadio...')
            if self._do_it(mode='uninstall'):
                print('\nPyRadio has been succesfully uninstalled!')
                print('We are really sorry to see you go!')
                print('Cheers!\n')
                sys.exit()
            else:
                os.system('clear')
                print('\n\nAn error occured during the uninstallation!')
                print('This should have never had happened...')
                print('Please report this at http://github.com/coderholic/pyradio/issues\n')
                sys.exit(1)

    def update_or_uninstall_on_windows(self, mode='update', from_pyradio=False):
        # Params:
        #       mode:           the type of zip file to download
        #       from_pyradio:   True if executed by "pyradio -d"
        params = ('', '--sng-master', '--sng-devel', '--devel', '--master')
        isRunning()
        ''' Creates BAT file to update or uninstall PyRadio on Windows'''
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        shutil.rmtree(self._dir, ignore_errors=True)
        os.makedirs(self._dir, exist_ok=True)
        if mode.startswith('update'):
            bat = os.path.join(self._dir, 'update.bat')
            # os.system('CLS')
            # PyRadioUpdateOnWindows.print_update_bat_created()
        else:
            bat = os.path.join(self._dir, 'uninstall.bat')
            # os.system('CLS')
            if from_pyradio:
                PyRadioUpdateOnWindows.print_uninstall_bat_created()

        if self._package == 0:
            if self.ZIP_DIR[0].endswith('-'):
                try:
                    if VERSION == '':
                        VERSION = get_github_tag()
                except:
                    VERSION = get_github_tag()
                # print('VERSION = "{}"'.format(VERSION))
                self.ZIP_URL[0] = self.ZIP_URL[0] + VERSION + '.zip'
                self.ZIP_DIR[0] += VERSION
        try:
            with open(bat, "w", encoding='utf-8') as b:
                b.write('@ECHO OFF\n')
                # b.write('CLS\n')
                b.write('python -m pip install --upgrade wheel 1>NUL 2>NUL\n')
                b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                b.write('python -m pip install --upgrade setuptools 1>NUL 2>NUL\n')
                b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                b.write('python -m pip install --upgrade requests 1>NUL 2>NUL\n')
                b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                b.write('python -m pip install --upgrade rich 1>NUL 2>NUL\n')
                b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                b.write('python -m pip install --upgrade win10toast 1>NUL 2>NUL\n')
                b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                # b.write('PAUSE\n')
                if mode.startswith('update'):
                    b.write('COPY "{}" . 1>NUL\n'.format(os.path.abspath(__file__)))
                    if self._package == 0:
                        b.write(self._python_exec.python + ' install.py --no-logo --do-update\n')
                    else:
                        b.write(self._python_exec.python + ' install.py --no-logo --do-update ' + params[self._package] + '\n')
                    b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                    b.write('cd "' + os.path.join(self._dir, self.ZIP_DIR[self._package]) + '"\n')

                    b.write('IF EXIST C:\\Users\\Spiros\\pyradio (\n')
                    # b.write('COPY C:\\Users\\Spiros\\pyradio\\pyradio\\install.py pyradio\n')
                    b.write('COPY C:\\Users\\Spiros\\pyradio\\pyradio\\*.py pyradio\n')
                    b.write('COPY C:\\Users\\Spiros\\pyradio\\devel\\*.bat devel\n')
                    b.write(')\n')


                    b.write('devel\\build_install_pyradio.bat -U\n')
                    b.write('GOTO endofscript\n')
                else:
                    b.write('COPY "{}" uninstall.py 1>NUL\n'.format(os.path.abspath(__file__)))
                    if self._package == 0:
                        b.write(self._python_exec.python + ' uninstall.py --do-uninstall\n')
                    else:
                        b.write(self._python_exec.python + ' uninstall.py --do-uninstall ' + params[self._package] + '\n')
                    b.write('if %ERRORLEVEL% == 1 GOTO downloaderror\n')
                    # print('self._dir = "{}"'.format(self._dir))
                    # print('self._package = "{}"'.format(self._package))
                    # print('self.ZIP_DIR = "{}"'.format(self.ZIP_DIR))
                    b.write('cd "' + os.path.join(self._dir, self.ZIP_DIR[self._package]) + '"\n')

                    b.write('IF EXIST C:\\Users\\Spiros\\pyradio (\n')
                    # b.write('COPY C:\\Users\\Spiros\\pyradio\\pyradio\\install.py pyradio\n')
                    b.write('COPY C:\\Users\\Spiros\\pyradio\\pyradio\\*.py pyradio\n')
                    b.write('COPY C:\\Users\\Spiros\\pyradio\\devel\\*.bat devel\n')
                    b.write(')\n')

                    b.write('devel\\build_install_pyradio.bat -u\n')
                    # b.write('PAUSE\n')
                    b.write('GOTO endofscript\n')
                b.write('ECHO.\n\n')
                b.write(':downloaderror\n')
                # b.write('CLS\n')
                b.write('ECHO Error:\tPyRadio cannot connect to GitHub...\n')
                b.write('ECHO \tPlease make sure that your internet connection is still up and try again\n')
                b.write('ECHO.\n\n')
                b.write('PAUSE\n')
                b.write('exit 1\n')
                b.write(':endofscript\n')
                b.write('exit 0\n')
        except:
            print('\nCreating the update/uninstall BAT file failed...')
            print('You should probably reboot your machine and try again.\n')
            sys.exit(1)

        if mode.endswith('-open'):
            os.startfile(self._dir)

    def open_windows_dir(self):
        os.startfile(self._dir)

    def _no_download_method(self):
        if platform.system().lower().startswith('darwin'):
            subprocess.call('python3 -m pip install requests', shell=True)
            print('\n\nPyradio has installed the minimum necessary modules for its execution\nPlease execute the same command again...')
        else:
            print('Error: PyRadio has no way to download files...')
            print('       Please install python\'s "requests" module and try again.\n')
        sys.exit(1)

    def _do_it(self, mode='update'):
        if not HAVE_REQUESTS:
            self._no_download_method()

        ''' Am I root ?'''
        #self._prompt_sudo()

        '''' get tmp dir '''
        if os.path.isdir('/tmp'):
            self._dir = os.path.join('/tmp', 'tmp-pyradio')
        else:
            self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        print('Using directory: "{}"'.format(self._dir))

        ''' create tmp directory '''
        self._delete_dir_limit = 0
        self._mkdir(self._dir, self._empty_dir, self._permission_error)
        if not os.path.isdir(self._dir):
            print('Error: Cannot create temp directory: "{}"'.format(self._dir))
            sys.exit(1)

        ''' download pyradio '''
        self._download_pyradio()

        ''' change to pyradio directory '''
        self._install_dir = os.path.join(self._dir, self._install_dir)
        if os.path.isdir(self._install_dir):
           os.chdir(self._install_dir)
           os.chmod('devel/build_install_pyradio', 0o766)
        else:
            print('Error: Failed to download PyRadio source code...\n')
            sys.exit(1)

        self._change_git_discription_in_config_py()

        param = ' 2' if self.python2 else ''

        if mode == 'update':
            ''' install pyradio '''
            if self.user:
                param += ' --user'
            ret = subprocess.call('devel/build_install_pyradio -no-dev -x ' + self._python_exec.python + ' '  + param, shell=True)
        else:
            ''' uninstall pyradio '''
            ret = subprocess.call('devel/build_install_pyradio -no-dev -x ' + self._python_exec.python + ' -R' + param, shell=True)
        if ret > 0:
            ret = False
        else:
            ret = True
        self._clean_up()
        return ret

    def _change_git_discription_in_config_py(self):
        # print('\n\n_change_git_discription_in_config_py(): self._github_long_description = "{}"\n\n'.format(self._github_long_description))
        # logger.error('DE _change_git_discription_in_config_py(): self._github_long_description = "{}"'.format(self._github_long_description))
        ''' change git_discription in pyradio/config.py '''
        if self._github_long_description is not None:
            try:
                with open(os.path.join(self._install_dir, 'pyradio', 'config.py'), 'r', encoding='utf-8') as con:
                    lines = con.read()
                lines = lines.replace("git_description = ''", "git_description = '" + self._github_long_description + "'")
                with open(os.path.join(self._install_dir, 'pyradio', 'config.py'), 'w', encoding='utf-8') as con:
                    con.write(lines)
            except:
                print('Error: Cannot change downloaded files...\n       Please close all running programs and try again.')
                sys.exit(1)

    def _download_pyradio(self):
        os.chdir(self._dir)
        if self._package == 0:
            try:
                VERSION ==  ''
            except:
                VERSION = get_github_tag()
            self.ZIP_URL[0] = self.ZIP_URL[0] + VERSION + '.zip'
            self.ZIP_DIR[0] += VERSION
        print('Downloading PyRadio source code...')
        self._install_dir = self.ZIP_DIR[self._package]
        if not self._download_file(self.ZIP_URL[self._package],
                os.path.join(self._dir, self.ZIP_DIR[self._package] + '.zip')):
            print('Error: Failed to download PyRadio source code...\n')
            sys.exit(1)

        print('Extracting RyRadio source code...')
        with zipfile.ZipFile(os.path.join(self._dir, self.ZIP_DIR[self._package] + '.zip')) as z:
            try:
                z.extractall(path=self._dir)
            except:
                print('Error: PyRadio source code ZIP file is corrupt...\n')
                sys.exit(1)
        with open(os.path.join(self._dir, self.ZIP_DIR[self._package], 'DEV'), 'w', encoding='utf-8') as b:
            pass
        ''' DEBUG on linux
            get new install.py, copy.py (any py)
            into downloaded directory
        '''
        '''
        from shutil import copyfile
        cur_dir = os.getcwd()
        copyfile('/Users/max/pyradio/pyradio/install.py',
            os.path.join(cur_dir, 'install.py'))
        #copyfile('/Users/max/pyradio/devel/build_install_pyradio', \
        #    os.path.join(os.path.join(self._dir, self.ZIP_DIR[self._package],
        #        'devel', 'build_install_pyradio'))
        #)
        #print('\n\n{}\n\n'.format(os.path.join(self._dir, self.ZIP_DIR[self._package])))
        #print(cur_dir)
        #copyfile('/home/spiros/projects/my-gits/pyradio/pyradio/install.py',
        #    os.path.join(cur_dir, 'install.py'))
        #copyfile('/home/spiros/projects/my-gits/pyradio/devel/build_install_pyradio', \
        #    os.path.join(os.path.join(self._dir, self.ZIP_DIR[self._package],
        #        'devel', 'build_install_pyradio'))
        #)
        # copyfile('/home/spiros/projects/my-gits/pyradio/pyradio/config.py',
        #    os.path.join(self._dir, self.ZIP_DIR[self._package], 'pyradio', 'config.py'))
        '''
        ''' DEBUG on Windows
            get new install.py, build_install_pyradio.bat (any py)
            into downloaded directory
        '''
        '''
        from shutil import copyfile
        cur_dir = os.getcwd()
        print('\n\n{}\n\n'.format(os.path.join(self._dir, self.ZIP_DIR[self._package])))
        print(cur_dir)
        copyfile('C:\\Users\\Spiros\\pyradio\\pyradio\\install.py',
            os.path.join(cur_dir, 'install.py'))
        copyfile('C:\\Users\\Spiros\\pyradio\\devel\\build_install_pyradio.bat',
            os.path.join(self._dir, self.ZIP_DIR[self._package], 'devel', 'build_install_pyradio.bat'))
        '''

    def _mkdir(self, name, dir_exist_function=None, _permission_error_function=None):
        if os.path.isdir(name):
            self._clean_up()
        if sys.version_info[0] == 2:
          try:
              os.makedirs(name)
          except OSError as e:
              if e.errno == 13:
                  if _permission_error_function:
                      _permission_error_function(name)
                  else:
                      print('Insufficient permissions...')
              elif e.errno == 17:
                  if dir_exist_function:
                      dir_exist_function(name)
                  else:
                      print('Dir already exists...')
        else:
          try:
              os.makedirs(name, exist_ok=True)
          except PermissionError:
              if _permission_error_function:
                  _permission_error_function(name)
              else:
                  print('Insufficient permissions...')
          except FileExistsError:
              if dir_exist_function:
                  dir_exist_function(name)
              else:
                  print('Dir already exists...')

    def _empty_dir(self, name=None):
        ddir = self._dir if name is None else name
        print('Old "{}" found. Deleting...'.format(ddir))
        self._delete_dir_limit += 1
        if self._delete_dir_limit > 2:
            print('\n\nError: Cannot delete directory: "' + ddir  +  '"')
            print('       Please relete it manually and try again... ')
            sys.exit(1)
        shutil.rmtree(ddir, ignore_errors=True)
        self._mkdir(ddir, self._empty_dir, self._permission_error)

    def _permission_error(self):
        print('Error: You don\'t have permission to create: "{}"\n'.format(self._dir))
        sys.exit(1)

    def _clean_up(self):
        shutil.rmtree(self._dir, ignore_errors=True)

    def _prompt_sudo(self):
        ret = 0
        if os.geteuid() != 0:
            msg = "[sudo] password for %u: "
            try:
                ret = subprocess.check_call("sudo -v -p '%s'" % msg, shell=True)
                return ret
            except subprocess.CalledProcessError:
                print('\nError: You must be root to execute this script...\n')
                sys.exit(1)

    def _download_file(self, url, filename):
        print('  url: "{}"'.format(url))
        print('  filename: "{}"'.format(filename))
        try:
            r = requests.get(url)
        except:
            return False
        try:
            with open(filename, 'wb') as f:
                for chunk in r.iter_content(chunk_size=1024):
                    if chunk: # filter out keep-alive new chunks
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
        except:
            return False
        return True

class PyRadioUpdateOnWindows(PyRadioUpdate):

    def __init__(self,
                 fromTUI=False,
                 package=0,
                 github_long_description=None,
                 python_version_to_use=3):
        if not platform.system().lower().startswith('win'):
            raise RuntimeError('This is a windows only class...')
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        self._package = package
        self._fromTUI = fromTUI
        self._github_long_description = github_long_description
        self._python_exec = PythonExecutable(python_version_to_use)
        self.python2 = True if python_version_to_use == 2 else False

    @classmethod
    def print_update_bat_created(cls):
        print('To complete the process you will have to execute a batch file.')
        print('Windows Explorer will open the location of the batch file to run.\n')
        print('Please double click\n\n    update.bat\n\nto get PyRadio\'s latest version.\n')
        print('After you are done, you can delete the folder:\n\n    "{}"'.format(os.path.join(os.path.expanduser("~"), 'tmp-pyradio')))

    @classmethod
    def print_uninstall_bat_created(cls):
        print('To complete the process you will have to execute a batch file.')
        print('Windows Explorer will open the location of the batch file to run.\n')
        print('Please double click\n\n    uninstall.bat\n\nto remove PyRadio from your system.\n')
        print('After you are done, you can delete the folder:\n\n    "{}"'.format(os.path.join(os.path.expanduser("~"), 'tmp-pyradio')))

    def update_pyradio(self):
        self._do_it()

    def remove_pyradio(self):
        self._do_it(mode='uninstall')

    def _do_it(self, mode='update'):
        if not HAVE_REQUESTS:
            self._no_download_method()

        self._download_pyradio()

        ''' change to pyradio directory '''
        self._install_dir = os.path.join(self._dir, self._install_dir)
        if os.path.isdir(self._install_dir):
           os.chdir(self._install_dir)
        else:
            print('Error: Failed to download PyRadio source code...\n')
            sys.exit(1)

        os.chdir(self._dir)

        self._change_git_discription_in_config_py()


if __name__ == '__main__':
    #exe = find_pyradio_win_exe()
    #print(exe)
    #sys.exit()
    # l=get_github_long_description()
    # print(l)
    # print(get_devel_version())
    # sys.exit()
    #print_pyradio_on()
    #print_python3() if PY3 else print_python2()
    # print(get_devel_version())
    # sys.exit()
    from argparse import ArgumentParser, SUPPRESS as SUPPRESS
    parser = ArgumentParser(description='PyRadio update / uninstall tool',
                            epilog='When executed without an argument, it installs PyRadio (stable release).')
    parser.add_argument('-U', '--update', action='store_true',
                        help='update PyRadio.')
    parser.add_argument('-f', '--force', action='store_true',
                        help='force installation (even if already installed).')
    if platform.system().lower().startswith('darwin'):
        parser.add_argument('--brew', nargs='?', default='False',
                            help='Create a link to pyradio executable in PATH. [BREW] can be empty (the default will be used in this case: /urs/local/opt). If a different package manager is in use, [BREW] should be the path to the location it installs its packages.')
    if not platform.system().lower().startswith('win'):
        parser.add_argument('--python2', action='store_true',
                            help='install using python 2.')
    else:
        parser.add_argument('--python2', action='store_true', help=SUPPRESS)
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='uninstall PyRadio.')

    ''' to be used by intermediate scripts '''
    parser.add_argument('--do-update', action='store_true', help=SUPPRESS)
    parser.add_argument('--do-uninstall', action='store_true', help=SUPPRESS)

    ''' extra downloads
        only use them after the developer says so,
        for debug purposes only
            --devel         download official devel branch
            --sng-master    download developer release (master)
            --sng-devel     download developer devel branch
            --force         force installation (even if already installed)
    '''
    parser.add_argument(
        '--git', action='store_true',
        help='install master branch from github (latest unreleased).')
    parser.add_argument('--master', action='store_true', help=SUPPRESS)
    parser.add_argument('--devel', action='store_true', help=SUPPRESS)
    parser.add_argument('--sng-master', action='store_true', help=SUPPRESS)
    parser.add_argument('--sng-devel', action='store_true', help=SUPPRESS)
    parser.add_argument('--no-logo', action='store_true', help=SUPPRESS)
    parser.add_argument('--first', action='store_true', help=SUPPRESS)

    args = parser.parse_args()
    sys.stdout.flush()

    use_logo = True
    if args.no_logo:
        use_logo = False
    if platform.system().lower().startswith('darwin'):
        ''' get python version '''
        if sys.version_info < (3, 0):
            print('Error: Python 2 is not supported any more!')
            print('       Please install Python 3 and execute the command:')
            print('\n           python3 install.py')
            print('\n       to install PyRadio.\n\n')
            sys.exit(1)

        if args.brew != "False":
            if args.brew is None:
                param = ' --fix-mac-path'
            else:
                param = ' --warning --fix-mac-path "' + args.brew + '"'
            #### print('parameter: ' + param)
            try:
                from urllib.request import urlretrieve
            except:
                from urllib import urlretrieve
            try:
                r = urlretrieve('https://raw.githubusercontent.com/coderholic/pyradio/master/devel/build_install_pyradio')
            except:
                print('Cannot contact github...')
                sys.exit(1)
            if int(r[1]['content-length']) < 1000:
                print('Cannot contact github...')
                sys.exit(1)
            script = r[0]
            #### print('script:', script)
            if exists('/Users/Max/pyradio/devel/build_install_pyradio'):
                script = '/Users/Max/pyradio/devel/build_install_pyradio'
            #### print('script:', script)
            # now I can run the script
            subprocess.call('bash -c "' + script + param + '"', shell=True)
            os.remove(r[0])
            sys.exit()


    if platform.system().lower().startswith('win') and \
            (not PY3 or args.python2):
        print_pyradio_on()
        print_python2()
        print_no_python2()
        sys.exit(1)

    if use_logo:
        print_pyradio_on()
        if PY3 and not args.python2:
            print_python3()
        else:
            print_python2()

    python_version_to_use = 2 if args.python2 else 3
    python_exec = PythonExecutable(python_version_to_use)

    if not python_exec.can_install:
        print('Error: Python {} not found on your system...\n'.format('2' if python_exec.requested_python_version == 2 else '3'))
        sys.exit(1)

    ''' download official release '''
    package = 0
    tag_name = github_long_description = None
    if args.sng_master:
        ''' sng master '''
        args.force = True
        package = 1
        VERSION, github_long_description = get_github_long_description(use_sng_repo=True, sng_branch=True)
        # if not github_long_description:
        #     github_long_description = 'PyRadio'
        # if github_long_description:
        #     github_long_description = github_long_description.replace('-', '-r', 1)
        # github_long_description += '-sng'
    elif args.sng_devel:
        '''' sng devel '''
        args.force = True
        package = 2
        VERSION, github_long_description = get_github_long_description(use_sng_repo=True)
        # if not github_long_description:
        #     github_long_description = 'PyRadio'
        # id github_long_description:
        #     github_long_description = github_long_description.replace('-', '-r', 1)
        # github_long_description += '-sng-dev'
    elif args.devel:
        ''' official devel '''
        package = 3
        ''' go back to master '''
        args.force = True
        package = 0
        VERSION = get_github_tag()
    elif args.master or args.git:
        ''' official master '''
        args.force = True
        package = 4
        VERSION, github_long_description = get_github_long_description()
    else:
        VERSION = get_github_tag()

    if VERSION is None:
        VERSION = PyRadioInstallPyReleaseVersion

    if args.uninstall:
        if platform.system().lower().startswith('win'):
            ''' ok, create BAT file on Windows'''
            uni = PyRadioUpdateOnWindows(
                package=package,
                python_version_to_use=python_version_to_use
            )
            uni.update_or_uninstall_on_windows(mode='uninstall-open')
            uni.print_uninstall_bat_created()
        else:
            uni = PyRadioUpdate(
                package=package,
                python_version_to_use=python_version_to_use
            )
            uni.remove_pyradio()
        sys.exit()
    elif args.update:
        if platform.system().lower().startswith('win'):
            ''' ok, create BAT file on Windows'''
            upd = PyRadioUpdateOnWindows(
                package=package,
                github_long_description=github_long_description,
                python_version_to_use=python_version_to_use
            )
            upd.update_or_uninstall_on_windows(mode='update-open')
            upd.print_update_bat_created()
        else:
            upd = PyRadioUpdate(
                package=package,
                github_long_description=github_long_description,
                python_version_to_use=python_version_to_use
            )
            upd.user = is_pyradio_user_installed()
            upd.update_pyradio()
        sys.exit()
    elif args.do_uninstall:
        ''' coming from uninstall BAT file on Windows'''
        uni = PyRadioUpdateOnWindows(
            package=package,
            python_version_to_use=python_version_to_use
        )
        uni.remove_pyradio()
        sys.exit()
    elif args.do_update:
        ''' coming from update BAT file on Windows'''
        upd = PyRadioUpdateOnWindows(
            package=package,
            github_long_description=github_long_description,
            python_version_to_use=python_version_to_use
        )
        upd.update_pyradio()
        sys.exit()

    ''' Installation!!! '''
    if platform.system().lower().startswith('win'):
        exe = find_pyradio_win_exe()
        first_install = False
        if exe == [None, None]:
            first_install = True

        if not args.force:
            # is pyradio.exe in PATH
            ret = subprocess.call('pyradio -h 1>NUL 2>NUL', shell=True)
            if ret == 0 or not first_install:
                    print('PyRadio is already installed.\n')
                    sys.exit(1)
        for a_module in (
                'setuptools',
                'windows-curses',
                'pywin32',
                'dnspython',
                'requests',
                'rich',
                'psutil',
                'patool',
                'pyunpack',
                'wheel',
                'win10toast',
        ):
            print('Checking module: [bold green]' + a_module + '[/bold green] ...')
            ret = subprocess.call('python -m pip install --upgrade ' + a_module,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL)
            if ret != 0:
                print('\nPyradio cannot install python module: ' + a_module)
                if a_module == 'windows-curses':
                    print('''This means that either you internet connection has failed
(in which case you should fix it and try again), or that
curses packagers have not yet produced a package for this
version of python (it was probably released recently).

What can you do?
1. Wait for the package to be updated (which means you will
    not be able to use PyRadio until then), or
2. Uninstall python and then go to
          https://www.python.org/downloads/
    and download and install the second to last version.
.
Then try installing PyRadio again
''')
                else:
                    print('Please make sure your internet connection is up and try again')
                sys.exit(1)

        uni = PyRadioUpdateOnWindows(
            package=package,
            github_long_description=github_long_description,
            python_version_to_use=python_version_to_use
        )
        uni.update_or_uninstall_on_windows(
            mode='update-open'
        )
        while not os.path.isfile(os.path.join(uni._dir, 'update.bat')):
            pass

        os.chdir(uni._dir)
        if subprocess.call('update.bat') == 0:
            if first_install:
                files = glob.glob(uni._dir + '\\**\\win.py', recursive=True)
                for n in files:
                    if '\\build\\' not in n:
                        win_file = n
                        break
                subprocess.call('python ' + win_file)
            print('\n\nNow you can delete the folder:')
            print('    "{}"'.format(uni._dir))
            print('and the file:')
            print('    "{}"'.format(__file__))
    else:
        if not args.force:
            ret = subprocess.call('pyradio -h 1>/dev/null 2>&1', shell=True)
            if ret == 0:
                print('PyRadio is already installed.\n')
                sys.exit(1)
        uni = PyRadioUpdate(
            package=package,
            github_long_description=github_long_description,
            python_version_to_use=python_version_to_use
        )
        uni.install = True
        if not platform.system().lower().startswith('darwin'):
            uni.user = True
        uni.update_pyradio()

