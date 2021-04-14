import sys
import os
import subprocess
import shutil
import zipfile
import platform
from time import sleep
try:
    import ctypes
    import win32api
    import win32ui
    from os.path import curdir
except:
    pass

try:
    from urllib.request import urlopen
except ImportError:
    try:
        from urllib2 import urlopen
    except ImportError:
        pass

try:
    import requests
    HAVE_REQUESTS = True
except ModuleNotFoundError:
    HAVE_REQUESTS = False

def is_pyradio_user_installed():
    if platform.system().lower().startswith('darwin'):
        return False
    p = subprocess.Popen('which pyradio', shell=True, stdout=subprocess.PIPE)
    ret = str(p.communicate()[0])
    home = os.path.expanduser('~')
    return True if ret.startswith(home) else False

def isRunning():
    ctypes.windll.kernel32.SetConsoleTitleW(curdir)
    print('PyRadio is still running. Please terminate it to continue ... ')
    while WindowExists('PyRadio: Your Internet Radio Player') or \
            WindowExists('PyRadio: Your Internet Radio Player (Session Locked)'):
        sleep(1)
    print('')

def version_string_to_list(this_version):
    a_v = this_version.replace('-', '.').lower()
    a_l = a_v.split('.')
    while len(a_l) < 4:
        a_l.append('0')
    a_n_l = []
    for n in a_l:
        if 'beta' in n:
            a_n_l.append(-200+int(a_l[-1].replace('beta', '')))
        elif 'rc' in n:
            a_n_l.append(-100+int(a_l[-1].replace('rc', '')))
        elif 'r' in n:
            pass
        else:
            a_n_l.append(int(n))
    return a_n_l

def get_github_tag():
    url = 'https://api.github.com/repos/coderholic/pyradio/tags'
    if sys.version_info < (3, 0):
        try:
            ret = urlopen(url).read(300)
        except:
            ret = None
    else:
        try:
            with urlopen(url) as https_response:
                ret = https_response.read(300)
        except:
            ret = None
    if ret:
        return str(ret).split('"name":')[1].split(',')[0].replace('"', '').replace("'", '')
    else:
        return None

def WindowExists(title):
    try:
        win32ui.FindWindow(None, title)
    except win32ui.error:
        return False
    else:
        return True

class PyRadioUpdate(object):

    ''' package values:
            0   -   official release
            1   -   s-n-g release
            2   -   s-h-g devel
            3   -   official devel
    '''

    ZIP_URL = ('https://github.com/coderholic/pyradio/archive/master.zip',
                'https://github.com/s-n-g/pyradio/archive/master.zip',
                'https://github.com/s-n-g/pyradio/archive/devel.zip',
                'https://github.com/coderholic/pyradio/archive/devel.zip',
                )

    ZIP_DIR  = ('pyradio-master', 'pyradio-master', 'pyradio-devel', 'pyradio-devel')

    install = False
    user = False
    python2 = False

    def __init__(self, package=0, user=False):
        if platform.system().lower().startswith('win'):
            raise RuntimeError('This is a linux only class...')
        self._dir = self._install_dir = ''
        self._package = package
        self.user = user

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

    def update_or_uninstall_on_windows(self, mode='update'):
        params = ('', '--sng-master', '--sng-devel')
        isRunning()
        ''' Creates BAT file to update or unisntall PyRadio on Windows'''
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        shutil.rmtree(self._dir, ignore_errors=True)
        os.makedirs(self._dir, exist_ok=True)
        if mode.startswith('update'):
            bat = os.path.join(self._dir, 'update.bat')
            os.system('CLS')
            # PyRadioUpdateOnWindows.print_update_bat_created()
        else:
            bat = os.path.join(self._dir, 'uninstall.bat')
            os.system('CLS')
            # PyRadioUpdateOnWindows.print_uninstall_bat_created()
        try:
            with open(bat, "w") as b:
                b.write('@ECHO OFF\n')
                b.write('CLS\n')
                b.write('pip install requests --upgrade 1>NUL 2>NUL\n')
                if mode.startswith('update'):
                    b.write('COPY "{}" . 1>NUL\n'.format(os.path.abspath(__file__)))
                    if self._package == 0:
                        b.write('python install.py --do-update\n')
                    else:
                        b.write('python install.py --do-update ' + params[self._package] + '\n')
                    b.write('cd "' + os.path.join(self._dir, self.ZIP_DIR[self._package]) + '"\n')
                    b.write('devel\\build_install_pyradio.bat -U\n')
                else:
                    b.write('COPY "{}" uninstall.py 1>NUL\n'.format(os.path.abspath(__file__)))
                    if self._package == 0:
                        b.write('python uninstall.py --do-uninstall\n')
                    else:
                        b.write('python uninstall.py --do-uninstall ' + params[self._package] + '\n')
                    b.write('cd "' + os.path.join(self._dir, self.ZIP_DIR[self._package]) + '"\n')
                    b.write('devel\\build_install_pyradio.bat -u\n')
        except:
            print('\nCreating the update/uninstall BAT file failed...')
            print('You should probably reboot your machine and try again.\n')
            sys.exit(1)

        if mode.endswith('-open'):
            os.startfile(self._dir)

    def open_windows_dir(self):
        os.startfile(self._dir)

    def _no_download_method(self):
        print('Error: PyRadio has no way to download files...')
        print('       Please either install "git" or python\'s')
        print('       module "requests" and try again.\n')
        sys.exit(1)

    def _do_it(self, mode='update'):
        if not HAVE_REQUESTS:
            self._no_download_method()

        ''' Am I root ?'''
        self._prompt_sudo()

        '''' get tmp dir '''
        if os.path.isdir('/tmp'):
            self._dir = os.path.join('/tmp', 'tmp-pyradio')
        else:
            self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        print('Using directory: "{}"'.format(self._dir))

        ''' create tmp directory '''
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

        ''' PROGRAM DEBUG: uncomment this to use the latest
            build_install_pyradio changes.
        '''
        # shutil.copyfile('/home/spiros/projects/my-gits/pyradio/devel/build_install_pyradio', '/tmp/tmp-pyradio/pyradio/devel/build_install_pyradio')
        param = ' 2' if sys.version_info[0] == 2 else ''
        if mode == 'update':
            ''' install pyradio '''
            if self.user:
                param += ' --user'
            try:
                subprocess.call('sudo devel/build_install_pyradio -x' + param, shell=True)
                ret = True
            except:
                ret = False
            self._clean_up()
            return ret
        else:
            ''' install pyradio '''
            try:
                subprocess.call('sudo devel/build_install_pyradio -x -u' + param, shell=True)
                ret = True
            except:
                ret = False
            self._clean_up()
            return ret

    def _download_pyradio(self):
        os.chdir(self._dir)
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

    def _mkdir(self, name, dir_exist_function=None, _permission_error_function=None):
        if os.path.isdir(name):
            self._clean_up()
        if sys.version_info[0] == 2:
          try:
              os.makedirs(name, exist_ok=True)
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

    def _empty_dir(self):
        print('Old "{}" found. Deleting...'.format(self._dir))
        shutil.rmtree(self._dir, ignore_errors=True)
        self._mkdir(self._dir, self._empty_dir, self._permission_error)

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
        # print('url = "{0}", filename = "{1}"'.format(url, filename))
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

    def __init__(self, fromTUI=False, package=0):
        if not platform.system().lower().startswith('win'):
            raise RuntimeError('This is a windows only class...')
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp-pyradio')
        self._package = package
        self._fromTUI = fromTUI

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

if __name__ == '__main__':
    from argparse import ArgumentParser, SUPPRESS as SUPPRESS
    parser = ArgumentParser(description='PyRadio update / uninstall tool',
                            epilog='When executed without an argument, it installs PyRario.')
    parser.add_argument('-U', '--update', action='store_true',
                        help='Update PyRadio.')
    if platform.system().lower().startswith('linux'):
        parser.add_argument('--user', action='store_true',
                            help='Install only for current user (linux only).')
    parser.add_argument('--python2', action='store_true',
                        help='Install using python 2.')
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='Uninstall PyRadio.')

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
    parser.add_argument('--sng-master', action='store_true', help=SUPPRESS)
    parser.add_argument('--sng-devel', action='store_true', help=SUPPRESS)
    parser.add_argument('--devel', action='store_true', help=SUPPRESS)
    parser.add_argument('-f', '--force', action='store_true', help=SUPPRESS)

    args = parser.parse_args()
    sys.stdout.flush()

    ''' download official release '''
    package = 0
    if args.sng_master:
        package = 1
    elif args.sng_devel:
        package = 2
    elif args.devel:
        package = 3

    if args.uninstall:
        if platform.system().lower().startswith('win'):
            ''' ok, create BAT file on Windows'''
            uni = PyRadioUpdateOnWindows(package=package)
            uni.update_or_uninstall_on_windows(mode='uninstall-open')
            uni.print_uninstall_bat_created()
        else:
            uni = PyRadioUpdate(package=package)
            if args.python2:
                uni.python2 = True
            uni.remove_pyradio()
        sys.exit()
    elif args.update:
        if platform.system().lower().startswith('win'):
            ''' ok, create BAT file on Windows'''
            upd = PyRadioUpdateOnWindows(package=package)
            upd.update_or_uninstall_on_windows(mode='update-open')
            upd.print_update_bat_created()
        else:
            upd = PyRadioUpdate(package=package)
            if args.python2:
                uni.python2 = True
            upd.user = is_pyradio_user_installed()
            upd.update_pyradio()
        sys.exit()
    elif args.do_uninstall:
        ''' coming from uninstall BAT file on Windows'''
        uni = PyRadioUpdateOnWindows(package=package)
        if args.python2:
            uni.python2 = True
        uni.remove_pyradio()
        sys.exit()
    elif args.do_update:
        ''' coming from update BAT file on Windows'''
        upd = PyRadioUpdateOnWindows(package=package)
        if args.python2:
            uni.python2 = True
        upd.update_pyradio()
        sys.exit()

    ''' Installation!!! '''
    if platform.system().lower().startswith('win'):
        if not args.force:
            ret = subprocess.call('pyradio -h 1>NUL 2>NUL', shell=True)
            if ret == 0:
                print('PyRadio is already installed.\n')
                sys.exit(1)
        subprocess.call('pip install windows-curses --upgrade')
        subprocess.call('pip install pywin32 --upgrade')
        subprocess.call('pip install requests --upgrade')
        uni = PyRadioUpdateOnWindows(package=package)
        uni.update_or_uninstall_on_windows(mode='update-open')
        while not os.path.isfile(os.path.join(uni._dir, 'update.bat')):
            pass
        os.chdir(uni._dir)
        subprocess.call('update.bat')
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
        uni = PyRadioUpdate(package=package)
        if args.python2:
            uni.python2 = True
        uni.install = True
        if not platform.system().lower().startswith('darwin'):
            uni.user = args.user
        uni.update_pyradio()

