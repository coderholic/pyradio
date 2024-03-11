# -*- coding: utf-8 -*-
import sys
import requests
import subprocess
from os.path import join, exists, isdir, basename, dirname
from os import environ, makedirs, listdir, replace, remove, sep, getenv, chdir
from time import sleep
import site
from shutil import rmtree
from msvcrt import getwch
from os import sep, startfile, path
from urllib.request import urlretrieve
import glob
import threading

import locale
locale.setlocale(locale.LC_ALL, "")

HAVE_PYUNPACK = True
try:
    from pyunpack import Archive
except ModuleNotFoundError:
    HAVE_PYUNPACK = False

''' This is also to be able to execute it manually'''
try:
    from .player import find_mpv_on_windows, find_mplayer_on_windows, find_vlc_on_windows
except ImportError:
    from player import find_mpv_on_windows, find_mplayer_on_windows, find_vlc_on_windows

purl = (
    'https://sourceforge.net/projects/mpv-player-windows/files/64bit',
    'https://sourceforge.net/projects/mplayerwin/files/MPlayer-MEncoder'
)

'''
    to get the latest v3 version use this url
        https://sourceforge.net/projects/mpv-player-windows/files/latest/download
'''
zurl = [
    'https://sourceforge.com/projects/mpv-player-windows/files/64bit/mpv-x86_64-20240310-git-a56d8ff.7z/download',
    'https://sourceforge.net/projects/mplayerwin/files/MPlayer-MEncoder/r38151/mplayer-svn-38151-x86_64.7z/download'
]

def win_press_any_key_to_unintall():
    the_path = __file__.split(sep)
    the_file = sep.join(the_path[:-1]) + sep + 'install.py'
    print('\nTo complete the process you will have to [red]execute a batch file[/red].')
    print('Windows Explorer will open the location of the batch file to run.')
    print('')
    print('Please double click')
    print('')
    print('    [bold green]uninstall.bat[/bold green]')
    print('')
    print('to remove [magenta]PyRadio[/magenta] from your system.')
    print('')
    print('After you are done, you can delete the folder it resides in.')
    from .win import press_any_key_to_continue
    print('\nPress any key to exit...', end='', flush=True)
    getwch()
    #print('\nPress any key to exit...', end='', flush=True)
    #getwch()
    subprocess.call('python ' + the_file + ' -R',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

def win_print_exe_paths():
    from .install import fix_pyradio_win_exe
    exe = fix_pyradio_win_exe()
    if exe[0] and exe[1]:
        print('[magenta]PyRadio[/magenta] EXE files:')
        print('  System:\n    [red]{}[/red]'.format(exe[0]))
        print('  User:\n    [green]{}[/green]'.format(exe[1]))
    else:
        print('[magenta]PyRadio[/magenta] EXE file:')
        if exe[0]:
            print('  [green]{}[/green]'.format(exe[0]))
        else:
            print('  [green]{}[/green]'.format(exe[1]))
    # doing it this way so that python2 does not break (#153)
    from .win import press_any_key_to_continue
    print('\nPress any key to exit...', end='', flush=True)
    getwch()

def press_any_key_to_continue():
    print('\nPress any key to exit...', end='', flush=True)
    getwch()

def install_module(a_module, do_not_exit=False, print_msg=True):
    if print_msg:
        print('Installing module: [green]' + a_module + '[/green]')
    for count in range(1,6):
        ret = subprocess.call('python -m pip install --upgrade ' + a_module,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)
        if ret == 0:
            break
        else:
            if count < 5:
                if print_msg:
                    print('  Download failed. Retrying [magenta]{}[/magenta]/[red]5[/red]'.format(count+1))
            else:
                if print_msg:
                    print('Failed to download module...\nPlease check your internet connection and try again...')
                else:
                    print('Failed to download module "[magenta]{}[/magenta]"...\nPlease check your internet connection and try again...').format(a_module)
                if do_not_exit:
                    return False
                sys.exit(1)
        return True

try:
    from rich import print
except:
    install_module('rich')
    from rich import print

def find_pyradio_win_exe():
    ''' find pyradio EXE files

        Return (system_exe, user_exe)
    '''
    exe = [None, None]
    for a_path in site.getsitepackages():
        an_exe = join(a_path, 'Scripts' , 'pyradio.exe')
        if exists(an_exe):
            exe[0] = an_exe
            break
    an_exe = join(site.getuserbase(), 'Scripts' , 'pyradio.exe')
    if exists(an_exe):
        exe[1] = an_exe
    # print(exe)
    return exe

def _is_player_in_path(a_player):
    ''' Return player's path in PATH variable
        If player not in PATH, return None
        Makes sure the path is local to user
        and player EXE exists

        Parameter:
            a_player: 1=mpv, 2=mplayer
    '''
    a_player -= 1
    in_path = None
    pl = ('mpv', 'mplayer')
    for a_path in environ['PATH'].split(';'):
        if a_path.endswith(pl[a_player]):
            in_path = a_path
            break
    #print('in_payh: {}'.format(in_path))
    if in_path:
        if not environ['USERPROFILE'] in a_path:
            return None
        if not exists(join(in_path, pl[a_player] + '.exe')):
            return None
    return in_path

def _get_output_folder(package, output_folder=None, do_not_exit=False):
    if output_folder is None:
        a_path = _is_player_in_path(package)
        if a_path:
            sp = a_path.split(sep)
            output_folder = sep.join(sp[:-1])
        else:
            output_folder = join(environ['APPDATA'], 'pyradio')
        # rename mpv if already there
        if not exists(output_folder):
            # create dir
            makedirs(output_folder, exist_ok=True)
            if not exists(output_folder):
                print('Failed to create folder: "[magenta]{}[/magenta]"'.format(pyradio_dir))
                if do_not_exit:
                    return None
                sys.exit(1)
    return output_folder

def _get_out_file(output_folder, package=1):
    count = 0
    p_name=('mpv-latest', 'mplayer-latest')
    out_file = join(output_folder, '{}.7z'.format(p_name[package]))
    while True:
        if exists(out_file):
            count += 1
            out_file = join(output_folder, '{0}-{1}.7z'.format(p_name[package], count))
        else:
            break
    return join(output_folder, out_file)

def download_seven_zip(output_folder):
    PR = (
        join(getenv('PROGRAMFILES'), '7-Zip', '7z.exe'),
        join(getenv('PROGRAMFILES') + ' (x86)', '7-Zip', '7z.exe')
    )
    if exists(PR[0]) or exists(PR[1]):
        return

    url = 'https://sourceforge.net/projects/sevenzip/files/latest/download'

    out_file = join(output_folder, '7-Zip_latest.exe')

    print('[magenta]7-Zip not found...\n[green]Downloading...[/green]')
    try:
        urlretrieve(url, filename=out_file)
    except:
        print('[red]Failed to download 7-Zip...[/red]')
        print('Please check your internet connection and try again...')
        print('\nIn case you want to [green]install 7-Zip manually[/green],')
        print('go to [magenta]https://www.7-zip.org/[/magenta] to get it...')
        sys.exit(1)

    print('\n[bold]PyRadio installation will resume as soon as\nyou complete the installation of 7-Zip...[/bold]')

    subprocess.call(
        out_file,
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def get_latest_x86_64_mplayer_url():
    url = purl[1]
    try:
        r = requests.get(url)
    except:
        return None
    if r.status_code == 200:
        # print(r.text)
        sp = r.text.split('<tr title="')
        for i, n in enumerate(sp):
            if n.startswith('r'):
                rev = n.split('"')[0][1:]
                try:
                    r = int(rev)
                except ValueError:
                    return None
                existing = zurl[1].split('-svn-')[1].split('-')[0]
                # print('     rev = ' + rev[1:])
                # print('existing = ' + existing[1:])
                if existing == rev:
                    rev = None
                else:
                    zurl[1] = zurl[1].replace(existing, rev[1:])
                r.close()
                return rev
    r.close()
    return None

def get_latest_x86_64_mpv_url():
    url = purl[0]
    try:
        r = requests.get(url)
    except:
        return None
    if r.status_code == 200:
        # print(r.text)
        sp = r.text.split('"url":"')
        for i, n in enumerate(sp):
            if n.startswith('/project') and '-v3' not in n:
                # print('item: {}'.format(i))
                # print(n)
                # print('\n\n\n')
                r.close()
                return 'https://sourceforge.com' + n.split('"')[0] + 'download'
    r.close()
    return None

def download_player(output_folder=None, package=1, do_not_exit=False):
    # Parameters
    #   output_folder   : where to save files
    #   package         : 0: mpv, 1: mplayer
    package -= 1
    if package == 0:
        print('Downloading [magenta]MPV[/magenta] ([green]latest[/green])...')
    else:
        print('Downloading [magenta]MPlayer[/magenta] ([green]latest[/green])...')

    mpv_url = None
    if package == 0:
        if is_cpu_mpv_v3_compatible():
            zurl[0] = 'https://sourceforge.net/projects/mpv-player-windows/files/latest/download'
        else:
            mpv_url = get_latest_x86_64_mpv_url()
            if mpv_url:
                zurl[0] = mpv_url
    elif package == 1:
        get_latest_x86_64_mplayer_url()
    output_folder = _get_output_folder(
        output_folder=output_folder,
        package=package,
        do_not_exit=do_not_exit)
    if output_folder is None:
        return False
    if True == False and package == 0 and \
            exists(join(output_folder, 'mpv', 'updater.bat')):
        chdir(join(output_folder, 'mpv'))
        startfile('updater.bat')
    else:
        print('    from  "[plum4]{}[plum4]"'.format(purl[package]))
        print('    into  "[magenta]{}[/magenta]"'.format(output_folder))

        out_file = _get_out_file(output_folder, package)
        session = requests.Session()
        for count in range(1,6):
            try:
                r = session.get(zurl[package])
                r.raise_for_status()
                break
            except requests.exceptions.RequestException as e:
                if count < 5:
                    print('  Download failed. Retrying [magenta]{}[/magenta]/[red]5[/red]'.format(count+1))
                else:
                    print('[red]Failed to download player...[/red]\nPlease check your internet connection and try again...')
                    if do_not_exit:
                        return False
                    sys.exit(1)
        print('  Saving: "{}"'.format(out_file))
        try:
            with open(out_file, 'wb') as f:
                f.write(r.content)
        except:
            print('[red]Failed to write archive...[/red]\nPlease try again later...')
            if do_not_exit:
                return False
            sys.exit(1)

        print('Extracting archive...')
        if package == 0:
            download_seven_zip(output_folder)

        if not HAVE_PYUNPACK:
            for a_module in ('pyunpack', 'patool'):
                install_module(a_module, print_msg=False)
        from pyunpack import Archive

        patool_exec = join(site.USER_SITE.replace('site-packages', 'Scripts'), 'patool')
        if not exists(patool_exec):
            patool_exec = glob.glob(join(environ['APPDATA'], '**', 'patool.exe'), recursive=True)
            if patool_exec:
                patool_exec = patool_exe[0]
            else:
                patool_exec = None
        try:
            Archive(out_file).extractall(join(output_folder, 'mpv' if package==0 else ''),
                auto_create_dir=True,
                patool_path=patool_exec)
        except:
            file_only = basename(out_file)
            player_name = 'mpv' if package == 0 else 'mplayer'
            print('''Failed to extract the archive...

    You will have to install the player [red]MANUALLY[/red]!!!

    PyRadio's configuration folder will open now,
    along with the archive named "{0}".'''.format(basename(out_file)))
            if player_name == 'mpv':
                if exists(join(output_folder, 'mpv')):
                    print('''    Please extract the archive in the "[rev]mpv[/red]" folder
    (overwriting any existing files).''')
                else:
                    print('''    Please create a folder named "[red]mpv[/red]" and extract
    the archive there.''')
            else:
                # mplayer
                if exists(join(output_folder, 'mplayer')):
                    print('''    Please delete the "[red]mplayer[/red]" folder, extract
    the archive and rename the resulting folder
    to "[red]mplayer[/red]".''')
                else:
                    print('''
    Please extract the archive and rename the resulting
    folder to "[red]mplayer[/red]".''')

            print('Press any key to continue...')

            getwch()
            if player_name == 'mpv':
                startfile(join(dirname(out_file), 'mpv'))
            else:
                startfile(dirname(out_file))
            startfile(out_file)

            '''
            if player_name == 'mpv':
                while not exists(join(output_folder, 'mpv', 'updater.bat')):
                    sleep(1)
                chdir(join(output_folder, 'mpv'))
                startfile('updater.bat')
            '''

            if do_not_exit:
                return False
            sys.exit(1)

    if not _post_download(package, output_folder, do_not_exit):
        return False
    try:
        remove(out_file)
    except:
        pass
    return True

def is_cpu_mpv_v3_compatible(print_flags=False):
    try:
        import cpuinfo
    except:
        install_module('py-cpuinfo')
    from cpuinfo import get_cpu_info
    cpu = get_cpu_info()

    ''' Source: Difference between x86_64 and x86_64 v3
        https://github.com/shinchiro/mpv-winbuild-cmake/wiki/Difference-between-x86_64-and-x86_64-v3
    '''
    mpv_v3_cpu_flags = (
    'avx',
    'avx2',
    'bmi',
    'bmi2',
    'fma',
    'lzcnt',
    'movbe',
    'sse3',
    'sse4',
    'sse4_1',
    'sse4_2',
    'ssse3',
    'xsave',
    'sahf',
    'mwait',
    'crc32',
    'cx16',
    'popcnt',
    'f16c'
    )

    count = 0

    for n in mpv_v3_cpu_flags:
        if n in cpu['flags']:
            count += 1
            if print_flags:
                print(n, '\t', 'ok')
        else:
            if print_flags:
                print(n, '\t', 'nok')

    return True if len(mpv_v3_cpu_flags) == count else False

def _post_download(package, output_folder, do_not_exit):

    # rename MPlayer directory
    if package == 1:
        sleep(5)
        mplayer_dir_found = False
        extracted_dirname = None
        dir_list = listdir(output_folder)
        for a_file in dir_list:
            if a_file == 'mplayer':
                mplayer_dir_found = True
            elif a_file.lower().startswith('mplayer-svn') and \
                    isdir(join(output_folder, a_file)):
                extracted_dirname = a_file

        # rename extracted dir to mplayer
        if extracted_dirname:
            extracted_dirname = join(output_folder, extracted_dirname)
            mplayer_final_dir = join(output_folder, 'mplayer')
            mplayer_old_dir = join(output_folder, 'mplayer.old')

            if mplayer_dir_found:
                if exists(mplayer_old_dir):
                    try:
                        rmtree(mplayer_old_dir)
                    except OSError:
                        print('Failed to remove "[green]{}[/green]"\nPlease close all programs and try again...'.format(mplayer_old_dir))
                        if do_not_exit:
                            return False
                        sys.exit(1)
                try:
                    replace(mplayer_final_dir, mplayer_old_dir)
                except:
                    print('Failed to rename folder "[green]{0}[/green]"\n      to "[magenta]{1}[/magenta]"...\nPlease close all open programs and try again...'.format(mplayer_final_dir, mplayer_old_dir))
                    if do_not_exit:
                        return False
                    sys.exit(1)
            try:
                replace(join(output_folder, extracted_dirname), join(output_folder, 'mplayer'))
            except:
                print('Failed to rename folder "[green]{0}[/green]" to\n      "[magenta]{1}[/magenta]"...\nPlease close all open programs and try again...'.format(extracted_dirname, mplayer_final_dir))
                if do_not_exit:
                    return False
                sys.exit(1)

        else:
            print('[red]Extracted folder not found...[/red]\nPlease try again later...')
            if do_not_exit:
                return False
            sys.exit(1)
    return True

def install_player(output_folder=None, package=0, do_not_exit=False):
    while True:
        in_path = [None, None, None]
        to_do = ['[bold red]1[/bold red]. Install', '[bold red]2[/bold red]. Install', '[green]VLC[/green] media player is not installed']
        from_path = ['', '']
        for n in range(0, 2):
            in_path[n] = _is_player_in_path(n)
            if in_path[n]:
                to_do[n] = '[bold red]{}[/bold red]. Update'.format(n+1)
                from_path[n] = ' (found in [magenat]PATH[/magenta])'
        if in_path[0] is None:
            in_path[0] = find_mpv_on_windows()
        if in_path[1] is None:
            in_path[1] = find_mplayer_on_windows()

        if in_path[0] == 'mpv':
            in_path[0] = None
        if in_path[1] == 'mplayer':
            in_path[1] = None

        for n in range(0, 2):
            if in_path[n]:
                to_do[n] = '[bold red]{}[/bold red]. Update'.format(n+1)
        if find_vlc_on_windows():
            to_do[2] = '[green]VLC[/green] media player is already installed.\n[bold red]      It is not recommended to be used!!![/bold red]'
        #print(in_path)
        #print(to_do)
        #print(from_path)

        #print('\nDo you want to download a media player now? (Y/n): ', end='', flush=True)
        #x = getwch()
        #print(x)
        x = 'y'
        if in_path[0]:
            best_choise = ''
        else:
            best_choise = '([yellow]best choise[/yellow])'
        if x == 'y' or x == '\n' or x == '\r':
            x = ''
            msg = '''
Please select an action:
    {0} [green]MPV[/green]{1}      {2}
    {3} [green]MPlayer[/green]{4}'''


            print(msg.format(to_do[0], from_path[0],
                best_choise, to_do[1], from_path[1]
            ))
            msg ='''
    [plum4]Note:[/plum4]
      {}
    '''
            opts = []
            prompt = ''
            all_uninstall = False
            if in_path[0] is None and in_path[1] is None:
                opts = ['0', '1', '2', 'q']
                prompt = 'Press [bold red]1[/bold red], [bold red]2[/bold red] or [bold red]q[/bold red] to Cancel: '
            elif in_path[0] is not None and in_path[1] is not None:
                print('\n    [bold red]3[/bold red]. Uninstall [green]MPV[/green]')
                print('    [bold red]4[/bold red]. Uninstall [green]MPlayer[/green]')
                opts = ['0', '1', '2', '3', '4', 'q']
                prompt = 'Press [bold red]1[/bold red], [bold red]2[/bold red], [bold red]3,[/bold red] [bold red]4[/bold red] or [bold red]q[/bold red] to Cancel: '
            else:
                if in_path[0] is not None:
                    print('\n    [bold red]3[/bold red]. Uninstall [green]MPV[/green]')
                else:
                    print('\n    [bold red]3[/bold red]. Uninstall [green]MPlayer[/green]')
                opts = ['0', '1', '2', '3', 'q']
                prompt = 'Press [bold red]1[/bold red], [bold red]2[/bold red], [bold red]3[/bold red] or [bold red]q[/bold red] to Cancel: '
                all_uninstall = True

            print(msg.format(to_do[2]))

            while x not in opts:
                print(prompt,  end='', flush=True)
                x = getwch()
                print(x)

            # ok, parse response
            if x in ('0', 'q'):
                clean_up()
                return
            if x in ('1', '2'):
                # install ot update
                download_player(package=int(x))
                print('\n\n')
            elif x == '3':
                # find out which player to wuninstall
                print('uninstall [green]mplayer[/green] or [green]mpv[/green]')
                print('\n\n')
            elif x == '4':
                # uninstall mplayer
                print('uninstall [green]mplayer[/green]')
                print('\n\n')

def install_pylnk(a_path, do_not_exit=False):
    print('    Downloading [green]pylnk[/green]...')
    session = requests.Session()
    for count in range(1,6):
        try:
            r = session.get('https://github.com/strayge/pylnk/archive/refs/heads/master.zip')
            r.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            if count < 5:
                print('      Download failed. Retrying [magenta]{}[/magenta]/[red]5[/red]'.format(count+1))
            else:
                print('    Failed to download [green]pylnk[/green]...\nPlease check your internet connection and try again...')
                if do_not_exit:
                    return False
                sys.exit(1)
    try:
        with open(join(a_path, 'pylnk.zip'), 'wb') as f:
            f.write(r.content)
    except:
        print('    Failed to write archive...\nPlease try again later...')
        if do_not_exit:
            return False
        sys.exit(1)

    print('    Installing [green]pylnk...[/green]')
    ret = subprocess.call('python -m pip install ' + join(a_path, 'pylnk.zip'),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL)

    remove(join(a_path, 'pylnk.zip'))

def clean_up(print_msg=True):
    if print_msg:
        print('Cleaning up makedepend modules...')
    for n in ('pyunpack', 'patool', 'pylnk3', 'EasyProcess'):
        subprocess.call('python -m pip uninstall -y ' + n,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL)

def get_path(exe):
    out_exe = ''
    chk = []

    for n in site.getsitepackages():
        # print('adding: "{}"'.format(join(n, exe)))
        # print('adding: "{}"'.format(join(n, 'Scripts', exe)))
        chk.append(join(n, exe))
        chk.append(join(n, 'Scripts', exe))
    # print('------------------------')
    x = site.getusersitepackages()
    if isinstance(x, str):
            # print('adding: "{}"'.format(join(x, exe)))
            # print('adding: "{}"'.format(join(x, 'Scripts', exe)))
            chk.append(join(x, exe))
            chk.append(join(x, 'Scripts', exe))
            # print('adding: "{}"'.format(join(x, exe)).replace('\site-packages', ''))
            # print('adding: "{}"'.format(join(x, 'Scripts', exe)).replace('\site-packages', ''))
            chk.append(join(x, exe).replace(r'\site-packages', ''))
            chk.append(join(x, 'Scripts', exe).replace(r'\site-packages', ''))
    else:
        for n in site.getusersitepackages():
            # print('adding: "{}"'.format(join(n, exe)))
            # print('adding: "{}"'.format(join(n, 'Scripts', exe)))
            chk.append(join(n, exe))
            chk.append(join(n, 'Scripts', exe))
    # print('------------------------')
    for n in site.PREFIXES:
        # print('adding: "{}"'.format(join(n, exe)))
        # print('adding: "{}"'.format(join(n, 'Scripts', exe)))
        chk.append(join(n, exe))
        chk.append(join(n, 'Scripts', exe))
    # for n in range(0,4):
    #     print('')
    # for n in chk:
    #     print(n)
    # print('------------------------')
    for n in chk:
        # print('checking: "{}'.format(n))
        if exists(n):
            return n
    return ''

def get_pyradio():
    return get_path('pyradio.exe')

def get_pylnk():
    return get_path('pylnk3.exe')

def create_pyradio_link():
    pyradio_exe = 'pyradio'
    pyradio_exe = get_pyradio()
    pylnk_exe = get_pylnk()
    # print('pyradio_exe = "{}"'.format(pyradio_exe))
    # print('pylnk_exe = "{}"'.format(pylnk_exe))
    icon = join(environ['APPDATA'], 'pyradio', 'help', 'pyradio.ico')
    # print('icon = "{}"'.format(icon))
    link_path = join(environ['APPDATA'], 'pyradio', 'help', 'PyRadio.lnk')
    # print('link_path = "{}"'.format(link_path))
    workdir = join(environ['APPDATA'], 'pyradio')
    # print('workdir = "{}"'.format(workdir))
    # print('*** Updating Dekstop Shortcut')
    if not exists(workdir):
        makedirs(workdir, exist_ok=True)
        if not exists(workdir):
            print('Cannot create "' + workdir + '"')
            sys.exit(1)
    if not exists(pylnk_exe):
        install_pylnk(workdir)
    pylnk_exe = get_pylnk()
    # print('pylnk_exe = "{}"'.format(pylnk_exe))
    cmd = pylnk_exe + ' c --icon ' + icon + ' --workdir ' + workdir \
        + ' ' + pyradio_exe + ' ' + link_path
    # print('cmd = "{}"'.format(cmd))
    subprocess.Popen(
        [pylnk_exe, 'c', '--icon', icon, '--workdir', workdir, pyradio_exe, link_path],
        shell=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def install_pyradio_link():
    from shutil import copy
    desktop = getenv('DESKTOP')
    user_profile = getenv('USERPROFILE')
    appdata = getenv('APPDATA')
    to_desktop = desktop if desktop is not None else join(user_profile, 'desktop')
    to_start_menu = join(appdata, 'Microsoft', 'Windows', 'Start Menu', 'Programs')

    if exists(to_desktop):
            copy(
                join(appdata, 'pyradio', 'help', 'PyRadio.lnk'),
                join(to_desktop, 'PyRadio.lnk')
            )

    if exists(to_start_menu):
            copy(
                join(appdata, 'pyradio', 'help', 'PyRadio.lnk'),
                join(to_start_menu, 'PyRadio.lnk')
            )

def find_and_remove_recording_data(data_dir):
    threading.Thread(
        target=find_and_remove_recording_data_thread(data_dir)
        ).start()

def find_and_remove_recording_data_thread(data_dir):
    files = glob.glob(join(data_dir, 'tmp_*.mkv'))
    txt = glob.glob(join(data_dir, '*.txt'))
    xml = glob.glob(join(data_dir, '*.xml'))

    for i in range(len(txt)-1, -1, -1):
        if txt[i].startswith('search-'):
            txt.pop(i)
    for n in txt, xml:
        if n:
            files.extend(n)
    if files:
        for n in files:
            try:
                remove(path.join(data_dir, n))
            except:
                pass

if __name__ == '__main__':
    print('\n\n[red]----[green]====  [magenta]MPV Media Player Installation  [green]====[red]----[/red]')
    download_player(package=1)
    print('[red]----[green]====  [magenta]MPV Media Player Installed  [green]====[red]----[/red]')
    # _post_download(1, "C:\\Users\\spiros\\AppData\\Roaming\\pyradio")
    # download_player(package=0)
    #install_player()

    # install_pylnk("C:\\Users\\spiros")
    #create_pyradio_link()
    # find_pyradio_win_exe()
