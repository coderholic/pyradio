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
    import requests
    HAVE_REQUESTS = True
except ModuleNotFoundError:
    HAVE_REQUESTS = False

def isRunning():
    ctypes.windll.kernel32.SetConsoleTitleW(curdir)
    print('PyRadio is still running. Please terminate it to continue ... ')
    while WindowExists('PyRadio: The Internet Radio Player') or \
            WindowExists('PyRadio: The Internet Radio Player (Session Locked)'):
        sleep(1)
    print('')

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
    '''

    GIT_URL = ('https://github.com/coderholic/pyradio.git',
                'https://github.com/s-n-g/pyradio.git',
                'https://github.com/s-n-g/pyradio.git',
                )

    ZIP_URL = ('https://github.com/coderholic/pyradio/archive/master.zip',
                'https://github.com/s-n-g/pyradio/archive/master.zip',
                'https://github.com/s-n-g/pyradio/archive/devel.zip',
                )

    ZIP_DIR  = ('pyradio-master', 'pyradio-master', 'pyradio-devel')


    def __init__(self, package=0):
        package = 2
        if platform.system().lower().startswith('win'):
            raise RuntimeError('This is a linux only class...')
        self._dir = self._install_dir = ''
        self._package = package

    def update_pyradio(self, win_open_dir=False):
        if platform.system().lower().startswith('win'):
            ''' create BAT file to update or execute '''
            if win_open_dir:
                self.update_or_uninstall_on_windows('update-open')
            else:
                self.update_or_uninstall_on_windows('update')
        else:
            ''' update PyRadio under Linux and MacOS '''
            print('Updating PyRadio...')
            if self._do_it():
                print('\n\nPyRadio updated to the latest release!')
                print('Thank you for your continuous support to this project!')
                print('Enjoy!\n')
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
        isRunning()
        ''' Creates BAT file to update or unisntall PyRadio on Windows'''
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp_pyradio')
        shutil.rmtree(self._dir, ignore_errors=True)
        os.makedirs(self._dir, exist_ok=True)
        if mode.startswith('update'):
            bat = os.path.join(self._dir, 'update.bat')
            PyRadioUpdateOnWindows.print_update_bat_created()
        else:
            bat = os.path.join(self._dir, 'uninstall.bat')
            os.system('CLS')
            PyRadioUpdateOnWindows.print_uninstall_bat_created()
        try:
            with open(bat, "w") as b:
                b.write('@ECHO OFF\n')
                b.write('CLS\n')
                b.write('pip install requests --upgrade 1>NUL 2>NUL\n')
                if mode.startswith('update'):
                    b.write('COPY "{}" . 1>NUL\n'.format(__file__))
                    b.write('python update.py --do-update\n')
                    b.write('cd "' + os.path.join(self._dir, self.ZIP_DIR[self._package]) + '"\n')
                    b.write('devel\\build_install_pyradio.bat -U\n')
                else:
                    b.write('COPY "{}" uninstall.py 1>NUL\n'.format(__file__))
                    b.write('python uninstall.py --do-uninstall\n')
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
        ''' do I have git installed? '''
        if subprocess.call('git --version 2>/dev/null 1>&2' ,shell=True) == 0:
            self.git_found = True
        else:
            self.git_found = False
            if not HAVE_REQUESTS:
                self._no_download_method()

        ''' Am I root ?'''
        self._prompt_sudo()

        '''' get tmp dir '''
        if os.path.isdir('/tmp'):
            self._dir = os.path.join('/tmp', 'tmp_pyradio')
        else:
            self._dir = os.path.join(os.path.expanduser('~'), 'tmp_pyradio')
        print('Using directory: "{}"'.format(tmp))

        ''' create tmp directory '''
        self._mkdir(self._dir, self._empty_dir, self._permission_error)
        if not os.path.isdir(self._dir):
            print('Error: Cannot create temp directory: "{}"'.format(self._dir))
            sys.exit(1)

        ''' downloaad pyradio '''
        self._download_pyradio()

        ''' change to pyradio directory '''
        self._install_dir = os.path.join(self._dir, self._install_dir)
        if os.path.isdir(self._install_dir):
           os.chdir(self._install_dir)
           os.chmod('devel/build_install_pyradio', 0o766)
        else:
            print('Error: Failed to download PyRadio source code...\n')
            sys.exit(1)

        if mode == 'update':
            ''' install pyradio '''
            try:
                subprocess.call('sudo devel/build_install_pyradio', shell=True)
                ret = True
            except:
                ret = False
            self._clean_up()
            return ret
        else:
            ''' install pyradio '''
            try:
                subprocess.call('sudo devel/build_install_pyradio -u', shell=True)
                ret = True
            except:
                ret = False
            self._clean_up()
            return ret

    def _download_pyradio(self):
        need_the_zip = True
        os.chdir(self._dir)
        if self.git_found and self._package == 0:
            self._install_dir = 'pyradio'
            if subprocess.call('git clone https://github.com/coderholic/pyradio.git', shell=True) == 0:
                need_the_zip = False
        if need_the_zip:
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
        print('Error: You don\'t have permission to create: ""\n'.format(self._dir))
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
        package = 2
        if not platform.system().lower().startswith('win'):
            raise RuntimeError('This is a windows only class...')
        self._dir = os.path.join(os.path.expanduser('~'), 'tmp_pyradio')
        self._package = package
        self._fromTUI = fromTUI

    @classmethod
    def print_update_bat_created(cls):
        print('To complete the process you will have to execute a batch file.')
        print('Windows Explorer will open the location of the batch file to run.\n')
        print('Please double click\n\n    update.bat\n\nto get PyRadio\'s latest version.\n')
        print('After you are done, you can delete the folder named "tmp-pyradio"')

    @classmethod
    def print_uninstall_bat_created(cls):
        print('To complete the process you will have to execute a batch file.')
        print('Windows Explorer will open the location of the batch file to run.\n')
        print('Please double click\n\n    uninstall.bat\n\nto remove PyRadio from your system.\n')
        print('After you are done, you can delete the folder named "tmp-pyradio"')

    def update_pyradio(self):
        self._do_it()

    def remove_pyradio(self):
        self._do_it(mode='uninstall')

    def _do_it(self, mode='update'):
        ''' do I have git installed? '''
        if subprocess.call('git --version 1>NUL 2>NUL', shell=True) == 0:
            self.git_found = True
        else:
            self.git_found = False
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
        cur_dir = os.path.join(self._dir, self.ZIP_DIR[self._package])


        shutil.copyfile('C:\\Users\\Spiros\\pyradio\\devel\\build_install_pyradio.bat',
            'C:\\Users\\Spiros\\tmp_pyradio\\pyradio-devel\\devel\\build_install_pyradio.bat')
        sys.exit()
        # input('File copyied... Press ENTER to continue ')
        if mode == 'update':
            ''' install pyradio '''
            try:
                subprocess.call(os.path.join(cur_dir, 'devel\\build_install_pyradio.bat'), shell=True)
                ret = True
            except:
                ret = False
            self._clean_up()
            return ret
        else:
            ''' uninstall pyradio '''
            try:
                # path = os.path.join(cur_dir, 'devel\\build_install_pyradio.bat')
                # print('Running BAT file... "{}"'.format(path))
                subprocess.call(os.path.join(cur_dir, 'devel\\build_install_pyradio.bat') + ' -u', shell=True)
                ret = True
            except:
                ret = False
                print('Error running BAT file!!!')
            self._clean_up()
            return ret

if __name__ == '__main__':
    from argparse import ArgumentParser, SUPPRESS as SUPPRESS
    parser = ArgumentParser(description='PyRadio update / uninstall tool')
    parser.add_argument('-U', '--update', action='store_true',
                        help='Update PyRadio.')
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='Uninstall PyRadio.')
    parser.add_argument('--do-update', action='store_true', help=SUPPRESS)
    parser.add_argument('--do-uninstall', action='store_true', help=SUPPRESS)

    ''' extra downloads
        only use them after the developer says so,
        for debug purposes only
            --sng           download developer release
            --sng-devel     download developer devel branch
    '''
    parser.add_argument('--sng', action='store_true', help=SUPPRESS)
    parser.add_argument('--sng-devel', action='store_true', help=SUPPRESS)

    args = parser.parse_args()
    sys.stdout.flush()

    ''' download official release '''
    package = 0
    if args.sng:
        package = 1
    if args.sng_devel:
        package = 2

    if args.uninstall:
        if platform.system().lower().startswith('win'):
            ''' ok, create BAT file on Windows'''
            uni = PyRadioUpdateOnWindows(package=package)
            uni.update_or_uninstall_on_windows(mode='uninstall-open')
            uni.print_uninstall_bat_created()
        else:
            uni = PyRadioUpdate(package=package)
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
            upd.update_pyradio()
        sys.exit()
    elif args.do_uninstall:
        ''' coming from uninstall BAT file on Windows'''
        uni = PyRadioUpdateOnWindows(package=package)
        uni.remove_pyradio()
        sys.exit()
    elif args.do_update:
        ''' coming from update BAT file on Windows'''
        print('do_update')
        upd = PyRadioUpdateOnWindows(package=package)
        upd.update_pyradio()
        sys.exit()

