# -*- coding: utf-8 -*-
import sys
import curses
import logging, logging.handlers
import subprocess
import argparse
import shutil
from argparse import ArgumentParser, SUPPRESS as SUPPRESS
from os import path, getenv, environ, remove, chmod, makedirs
from sys import platform, version_info, executable
from contextlib import contextmanager
from platform import system
import re
import glob

from .radio import PyRadio
from .config import PyRadioConfig, SUPPORTED_PLAYERS
from .install import PyRadioUpdate, PyRadioUpdateOnWindows, PyRadioCache, \
    is_pyradio_user_installed, version_string_to_list, get_github_tag, \
    open_cache_dir
from .cjkwrap import cjklen, cjkslices, fill
from .log import Log
from .common import StationsChanges

import locale
locale.setlocale(locale.LC_ALL, "")

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
PATTERN_TITLE = '%(asctime)s | %(message)s'

PY3 = sys.version[0] == '3'

if PY3:
    HAS_PIPX = True if shutil.which('pipx') else False
else:
    HAS_PIPX = False

HAS_RICH = False
if PY3:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.align import Align
        from rich import print
        HAS_RICH = True
    except:
        pass

class MyArgParser(ArgumentParser):

    def __init(self):
        super(MyArgParser, self).__init__(
            description = description
        )

    def print_usage(self, file=None):
        if file is None:
            file = sys.stdout
        usage = self.format_usage()
        if PY3:
            print(self._add_colors(self.format_usage()))
        else:
            print(self.format_usage())

    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        if PY3:
            print(self._add_colors(self.format_help()))
        else:
            print(self.format_help())

    def _add_colors(self, txt):
        t = txt.replace('show this help', 'Show this help').replace('usage:', 'Usage:').replace('options:', 'Options:').replace('[', '|').replace(']', '||')
        x = re.sub(r'([^a-zZ-Z0-9])(--*[^ ,\t|]*)', r'\1[red]\2[/red]', t)
        t = re.sub(r'([A-Z_][A-Z_]+)', r'[green]\1[/green]', x)
        x = re.sub('([^"]pyradio)', r'[magenta]\1[/magenta]', t, flags=re.I)
        t = re.sub(r'(player_name:[a-z:_]+)', r'[plum2]\1[/plum2]', x)
        x = t.replace('mpv', '[green]mpv[/green]').replace('mplayer', '[green]mplayer[/green]').replace('vlc', '[green]vlc[/green]')
        return '[bold]' + x.replace('||', r']').replace('|', r'\[') + '[/bold]'

@contextmanager
def pyradio_config_file(a_dir):
    cf = PyRadioConfig(user_config_dir=a_dir)
    try:
        yield cf
    finally:
        try:
            ret, lfile = cf.remove_session_lock_file()
            if cf.force_to_remove_lock_file:
                if ret == 0:
                    if PY3:
                        print('Lock file removed: "[red]{}[/red]"'.format(lfile))
                    else:
                        if PY3:
                            print('Lock file removed: "[red]{}[/red]"'.format(lfile))
                        else:
                            print('Lock file removed: "{}"'.format(lfile))
                elif ret == 1:
                    if PY3:
                        print('Failed to remove Lock file: "[red]{}[/red]"'.format(lfile))
                    else:
                        print('Failed to remove Lock file: "{}"'.format(lfile))
                else:
                 if PY3:
                     print('Lock file not found: "[red]{}[/red]"'.format(lfile))
                 else:
                     print('Lock file not found: "{}"'.format(lfile))
        except:
            pass

def do_update_stations(pyradio_config):
    stations_change = StationsChanges(pyradio_config)
    if stations_change.stations_csv_needs_sync():
        stations_change.update_stations_csv()
    sys.exit()

def __configureLogger(pyradio_config, debug=None, titles=None):
    if debug or titles:

        if debug and not pyradio_config.log_degub:
            if platform.startswith('win'):
                if PY3:
                    print('Debug mode activated\n  printing messages to file: "[red]{}\pyradio.log[/red]"'.format(getenv('USERPROFILE')))
                else:
                    print('Debug mode activated\n  printing messages to file: "{}\pyradio.log"'.format(getenv('USERPROFILE')))
            else:
                if PY3:
                    print('Debug mode activated; printing messages to file: "[red]~/pyradio.log[/red]"')
                else:
                    print('Debug mode activated; printing messages to file: "~/pyradio.log"')

        pyradio_config.titles_log.configure_logger(
            debug=debug,
            titles=titles
        )

def print_session_is_locked():
    print_simple_error('Error: This session is locked!')
    print('       Please exist any other instances of the program')
    print('       that are currently running and try again.')
    sys.exit(1)

def shell():
    version_too_old = False
    if sys.version_info[0] == 2:
        if sys.version_info < (2, 7):
            version_too_old = True
        elif sys.version_info.major == 3 and sys.version_info < (3, 5):
            version_too_old = True
    if version_too_old:
        print('PyRadio requires python 2.7 or 3.5+...')
        sys.exit(1)

    if not HAS_RICH and PY3:
        print('''Module "rich" not found!

Please install it and try executing PyRadio again.

The module name is "python-rich" (or "python3-rich" on Debian-based and
Ubuntu-based distributions).

If nothing else works, try the following command:
    python -m pip install rich
''')
        sys.exit()

    requested_player = ''
    # parser = ArgumentParser(description='Curses based Internet radio player')
    parser = MyArgParser(
        description='Curses based Internet radio player'
    )
    if not system().lower().startswith('win'):
        parser.add_argument('-c', '--config-dir', default='',
                            help='Use specified configuration directory instead of the default one. '
                            'PyRadio will try to create it, if it does not exist. '
                            'Not available on Windows.')
    parser.add_argument('-s', '--stations', default='',
                        help='Use specified station CSV file.')
    parser.add_argument('-p', '--play', nargs='?', default='False',
                        help='Start and play.'
                        'The value is num station or empty for random.')
    parser.add_argument('-u', '--use-player', default='',
            help='Use specified player. '
            'A comma-separated list can be used to specify detection order. '
            'Supported players: mpv, mplayer, vlc.')
    parser.add_argument('-a', '--add', action='store_true',
                        help='Add station to list.')
    parser.add_argument('-ls', '--list-playlists', action='store_true',
                        help='List of available playlists in config dir.')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List of available stations in a playlist.')
    parser.add_argument('-t', '--theme', default='', help='Use specified theme.')
    parser.add_argument('--show-themes', action='store_true',
                       help='Show Internal and System Themes names.')
    parser.add_argument('--no-themes', action='store_true',
                       help='Disable themes (use default theme).')
    parser.add_argument('--write-theme', nargs=2, metavar=('IN_THEME', 'OUT_THEME,'),
                        help='Write an Internal or System Theme to themes directory.')

    if not system().lower().startswith('darwin') and \
            not system().lower().startswith('win'):
        parser.add_argument('--terminal', help='Use this terminal for Desktop file instead of the auto-detected one. Use "none" to reset to the default terminal or "auto" to reset to the auto-detected one.')
        parser.add_argument('--terminal-param', help='Use this as PyRadio parameter in the Desktop File. Please replace hyphens with underscores when passing the parameter, for example: --terminal-param "_p 3 _t light" (which will result to "pyradio -p 3 -t light").')

    parser.add_argument('-tlp', '--toggle-load-last-playlist', action='store_true',
                        help='Toggle autoload last opened playlist.')
    parser.add_argument('-scd', '--show-config-dir', action='store_true',
                        help='Print config directory [CONFIG DIR] location and exit.')
    parser.add_argument('-ocd', '--open-config-dir', action='store_true',
                        help='Open config directory [CONFIG DIR] with default file manager.')
    parser.add_argument('-ep', '--extra-player_parameters', default=None,
                        help="Provide extra player parameters as a string. The parameter is saved in the configuration file and is activated for the current session. The string\'s format is [player_name:parameters]. player_name can be 'mpv', 'mplayer' or 'vlc'. Alternative format to pass a profile: [player_name:profile:profile_name]. In this case, the profile_name must be a valid profile defined in the player\'s config file (not for VLC).")
    parser.add_argument('-ap', '--active-player-param-id', default=0, help='Specify the extra player parameter set to be used with the default player. ACTIVE_PLAYER_PARAM_ID is 1-11 (refer to the output of the -lp option)')
    parser.add_argument('-lp', '--list-player-parameters', default=None,
                        action='store_true',
                        help='List extra players parameters.')
    parser.add_argument('--record', action='store_true',
                        help='Turn recording on (not available for VLC player on Windows).')
    if platform.startswith('win'):
        parser.add_argument('--exe', action='store_true', default=False,
                            help='Show EXE file location (Windows only).')
    parser.add_argument('-U', '--update', action='store_true',
                        help='Update PyRadio.')
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='Uninstall PyRadio.')
    if HAS_PIPX:
        parser.add_argument('-oc', '--open-cache', action='store_true',
                           help='Open the Cache folder')
        parser.add_argument('-sc', '--show-cache', action='store_true',
                           help='Show Cache contents')
        parser.add_argument('-cc', '--clear-cache', action='store_true',
                           help='Clear Cache contents')
        parser.add_argument('-gc', '--get-cache', action='store_true',
                            help='Download source code, keep it in the cache and exit.')
    else:
        parser.add_argument('-oc', '--open-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-sc', '--show-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-cc', '--clear-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-gc', '--get-cache', action='store_true', help=SUPPRESS)

    parser.add_argument('--unlock', action='store_true',
                        help="Remove sessions' lock file.")
    parser.add_argument('-us', '--update-stations', action='store_true',
                        help='Update "stations.csv" (if needed).')
    parser.add_argument('-lt', '--log-titles', action='store_true',
                        help='Log titles to file.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Start PyRadio in debug mode.')
    parser.add_argument('-V', '--version', action='store_true',
                        help='Display version information.')
    ''' extra downloads
        only use them after the developer says so,
        for debug purposes only
            --devel           download official devel branch
            --sng-master      download developer release (master)
            --sng-devel       download developer devel branch
            --force-update    give a versio > than current,
                              to check update notification functionality
    '''
    parser.add_argument('--sng-master', action='store_true', help=SUPPRESS)
    parser.add_argument('--sng-devel', action='store_true', help=SUPPRESS)
    parser.add_argument('--devel', action='store_true', help=SUPPRESS)
    parser.add_argument('--force-update', default='', help=SUPPRESS)
    args = parser.parse_args()
    sys.stdout.flush()

    user_config_dir = None
    if not system().lower().startswith('win'):
        if args.config_dir:
            if '..' in args.config_dir:
                if PY3:
                    print('Error in config path: "[red]{}[/red]"\n      Please do not use "[green]..[/green]" in the path!'.format(args.config_dir))
                else:
                    print('Error in config path: "{}"\n      Please do not use ".." in the path!'.format(args.config_dir))
                sys.exit(1)
            user_config_dir = validate_user_config_dir(args.config_dir)
            if user_config_dir is None:
                if PY3:
                    print('Error in config path: "[red]{}[/red]"\n      This directory cannot be used by [magenta]PyRadio[/magenta]!'.format(args.config_dir))
                else:
                    print('Error in config path: "{}"\n      This directory cannot be used by PyRadio!'.format(args.config_dir))
                sys.exit(1)

    config_already_read = False

    if not system().lower().startswith('darwin') and \
            not system().lower().startswith('win'):
        if args.terminal:
            try:
                from urllib.request import urlretrieve
            except:
                from urllib import urlretrieve
            try:
                r = urlretrieve('https://raw.githubusercontent.com/coderholic/pyradio/master/devel/fix_pyradio_desktop_file')
            except:
                print('Cannot contact github...')
                sys.exit(1)
            if int(r[1]['content-length']) < 1000:
                print('Cannot contact github...')
                sys.exit(1)
            script = r[0]
            # script = '/home/spiros/projects/my-gits/pyradio/devel/fix_pyradio_desktop_file'
            chmod(script , 0o766)
            if args.terminal_param:
                command = 'bash -c "' + script + ' -t ' + args.terminal + " -p '-" + args.terminal_param + "'" + '"'
                command = 'bash -c "' + script + ' -t ' + args.terminal + " -p '" + args.terminal_param.replace('\\', '') + "'" + '"'
                # print(command)
                subprocess.call(command, shell=True)
            else:
                subprocess.call('bash -c "' + script + ' -t ' + args.terminal + '"', shell=True)
            remove(r[0])
            sys.exit()

    with pyradio_config_file(user_config_dir) as pyradio_config:
        if args.write_theme:
            if args.write_theme[0]:
                from .themes import PyRadioTheme
                read_config(pyradio_config)
                theme = PyRadioTheme(pyradio_config)
                ret, msg = theme.create_theme_from_theme(
                    args.write_theme[0],
                    args.write_theme[1]
                )
                print(msg)
                sys.exit()

        if args.version:
            pyradio_config.get_pyradio_version()
            if PY3:
                print('PyRadio version: [green]{}[/green]'.format(pyradio_config.current_pyradio_version))
                print('Python version: [green]{}[/green]'.format(sys.version.replace('\n', ' ').replace('\r', ' ')))
            else:
                print('PyRadio version: {}'.format(pyradio_config.current_pyradio_version))
                print('Python version: {}'.format(sys.version.replace('\n', ' ').replace('\r', ' ')))
            pyradio_config.read_config()
            if pyradio_config.distro != 'None':
                if PY3:
                    print('Distribution: [green]{}[/green]'.format(pyradio_config.distro))
                else:
                    print('Distribution: {}'.format(pyradio_config.distro))
            sys.exit()

        if args.show_themes:
            pyradio_config.read_config()
            int_themes = [x for x in pyradio_config.internal_themes if x != 'wob' and x != 'bow']
            sys_themes = list(pyradio_config.system_themes)
            user_themes = glob.glob(path.join(pyradio_config.themes_dir, '*.pyradio-theme'))
            for i in range(0, len(user_themes)):
                user_themes[i] = path.basename(user_themes[i]).replace('.pyradio-theme', '')

            # remove project themes names from user_themes
            projects_data = []
            for n in pyradio_config.auto_update_frameworks:
                projects_data.append([
                    n.NAME,
                    'Yes' if n.can_auto_update else 'No'
                ])
                if n.default_filename_only in user_themes:
                    projects_data[-1].append(n.default_filename_only)
                    user_themes.remove(n.default_filename_only)
                else:
                    projects_data[-1].append('-')
            if PY3:
                console = Console()
                table = Table(show_header=True, header_style="bold magenta")
                table.title = '[bold magenta]PyRadio Themes[/bold magenta]'
                centered_table = Align.center(table)
                table.add_column("Internal Themes")
                table.add_column("System Themes")
                table.add_column("User Themes")
                x = max(len(int_themes), len(sys_themes), len(user_themes))
                while len(int_themes) < x:
                    int_themes.append('')
                while len(sys_themes) < x:
                    sys_themes.append('')
                while len(user_themes) < x:
                    user_themes.append('')
                for n in zip(
                        int_themes,
                        sys_themes,
                        user_themes
                ):
                    table.add_row(n[0], n[1], n[2])
                console.print(centered_table)

                table1 = Table(show_header=True, header_style="bold magenta")
                centered_table1 = Align.center(table1)
                table1.title = '[bold magenta]Ext. Projects Themes[/bold magenta]'
                table1.add_column('Projects')
                table1.add_column('Can auto-update', justify='center')
                table1.add_column('Theme name')
                for n in projects_data:
                    table1.add_row(
                        '[bold magenta]' + n[0].replace(' Project', '') + '[/bold magenta]',
                        '[green]' + n[1] + '[/green]' if n[1] == 'Yes' else '[red]' + n[1] + '[/red]',
                        '[red]' + n[2] + '[/red]' if n[2] == '-' else n[2]
                    )
                console.print(centered_table1)
            else:
                print('Internal Themes')
                for n in int_themes:
                    if n not in ('bow', 'wob'):
                        print('  ' + n)
                print('System Themes')
                for n in sys_themes:
                    print('  ' + n)
                print('User Themes')
                if user_themes:
                    for n in user_themes:
                        print('  ' + n)
                print('Ext. Projects Themes')
                for n in projects_data:
                    print('  Theme name: ' + n[2])
                    print('    Project name: ' + n[0])
                    print('    Can auto-update: ' + n[1])
            sys.exit()

        if platform.startswith('win'):
            if args.exe:
                print_exe_paths()
                sys.exit()

        if args.toggle_load_last_playlist:
            if pyradio_config.locked:
                print_session_is_locked()
                sys.exit(1)
            else:
                read_config(pyradio_config)
                pyradio_config.opts['open_last_playlist'][1] = not pyradio_config.opts['open_last_playlist'][1]
                pyradio_config.opts['dirty_config'][1] =  True
                if PY3:
                    print('Setting auto load last playlist to: "[red]{}[/red]"'.format(pyradio_config.opts['open_last_playlist'][1]))
                else:
                    print('Setting auto load last playlist to: {}'.format(pyradio_config.opts['open_last_playlist'][1]))
                save_config()
            sys.exit(0)

        package = 0
        if args.uninstall or args.update:
            if args.sng_master:
                package = 1
            elif args.sng_devel:
                package = 2
            elif args.devel:
                package = 3
            if not config_already_read:
                read_config(pyradio_config)
                config_already_read = True
            if pyradio_config.distro != 'None' and \
                    not platform.startswith('win'):
                no_update(args.uninstall)

        if args.update:
            if package == 0:
                pyradio_config.get_pyradio_version()
                last_tag = get_github_tag()
                if last_tag:
                    if PY3:
                        print('Released version   :  [green]{}[/green]'.format(last_tag))
                        print('Installed version  :  [red]{}[/red]'.format(pyradio_config.current_pyradio_version))
                    else:
                        print('Released version   :  {}'.format(last_tag))
                        print('Installed version  :  {}'.format(pyradio_config.current_pyradio_version))
                    if version_string_to_list(last_tag) <= version_string_to_list(pyradio_config.current_pyradio_version):
                        print('Latest version already installed. Nothing to do....')
                        sys.exit()
                else:
                    print('Error reading online version.\nPlease make sure you are connected to the internet and try again.')
                    sys.exit(1)

            python_version_to_use = 3 if PY3 else 2
            try:
                upd = PyRadioUpdate(
                    package=package,
                    python_version_to_use=python_version_to_use
                )
                upd.update_pyradio()
            except RuntimeError:
                upd = PyRadioUpdateOnWindows(
                    package=package,
                    python_version_to_use=python_version_to_use
                )
                upd.update_or_uninstall_on_windows(mode='update-open')
            sys.exit()

        if args.uninstall:
            python_version_to_use = 3 if PY3 else 2
            try:
                upd = PyRadioUpdate(
                    package=package,
                    python_version_to_use=python_version_to_use
                )
                upd.remove_pyradio()
            except RuntimeError:
                upd = PyRadioUpdateOnWindows(
                    package=package,
                    python_version_to_use=python_version_to_use
                )
                upd.update_or_uninstall_on_windows(
                    mode='uninstall-open',
                    from_pyradio=True
                )
            sys.exit()

        ''' check conflicting parameters '''
        if args.active_player_param_id and \
                args.extra_player_parameters:
            if PY3:
                print('[red]Error:[/red] You cannot use parameters "[green]-ep[/green]" and "[green]-ap[/green]" together!\n')
            else:
                print('Error: You cannot use parameters "-ep" and "-ap" together!\n')
            sys.exit(1)

        ''' user specified extra player parameter '''
        if args.active_player_param_id:
            try:
                a_param = int(args.active_player_param_id)
            except ValueError:
                if PY3:
                    print('[red]Error:[/red] Parameter "[green]-ap[/green]" is not a number\n')
                else:
                    print('Error: Parameter "-ap" is not a number\n')
                sys.exit(1)
            if 1 <= a_param <= 11:
                pyradio_config.user_param_id = a_param
            else:
                if PY3:
                    print('[red]Error:[/red] Parameter "[green]-ap[/green]" must be between 1 and 11')
                else:
                    print('Error: Parameter -ap must be between 1 and 11')
                print('       Actually, it must be between 1 and the maximum')
                print('       number of parameters for your default player.\n')
                args.list_player_parameters = True

        ''' list extra player parameters '''
        if args.list_player_parameters:
            read_config(pyradio_config)
            default_player_name = pyradio_config.opts['player'][1].replace(' ', '').split(',')[0]
            if default_player_name == '':
                default_player_name = SUPPORTED_PLAYERS[0]
            if PY3:
                console = Console()
                table = Table(show_header=True, header_style="bold magenta")
                table.title = '[bold magenta]Player Extra Parameters[/bold magenta]'
                table.title_justify = "left"
                centered_table = Align.center(table)
                table.add_column("Player")
                table.add_column("Parameters")
                for n, a_player in enumerate(SUPPORTED_PLAYERS):
                    if default_player_name == a_player:
                        pl_field = '[green]' + a_player + '[/green]'
                    else:
                        pl_field = '[red]' + a_player + '[/red]'
                    default = 0
                    param_field = ''
                    for i, a_param in enumerate(pyradio_config.saved_params[a_player]):
                        if i == 0:
                            default = int(a_param)
                        else:
                            str_default = ''
                            if a_player != 'vlc':
                                str_default = '([green]default[/green])' if i == default else ''
                            count = str(i) if i > 9 else ' ' + str(i)
                            param_field = '[green]{0}[/green]. {1} {2}'.format(count, a_param, str_default)
                            table.add_row(
                                pl_field,
                                param_field
                            )
                            pl_field = ''
                    if n < len(SUPPORTED_PLAYERS) - 1:
                        table.add_row('', '')
                console.print(centered_table)
            else:
                print('Player Extra Parameters')
                print(32 * '-')
                for a_player in SUPPORTED_PLAYERS:
                    if default_player_name == a_player:
                        print('Player: ' + a_player + ' (default)')
                    else:
                        print('Player: ' + a_player)
                    default = 0
                    for i, a_param in enumerate(pyradio_config.saved_params[a_player]):
                        if i == 0:
                            default = int(a_param)
                        else:
                            str_default = '(default)' if i == default else ''
                            count = str(i) if i > 9 else ' ' + str(i)
                            print('    {0}. {1} {2}'.format(count, a_param, str_default))
                print('')
            sys.exit()

        ''' extra player parameters '''
        if args.extra_player_parameters:
            if ':' in args.extra_player_parameters:
                if pyradio_config.locked:
                    print_session_is_locked()
                    sys.exit(1)
                else:
                    if args.extra_player_parameters.startswith('vlc:profile'):
                        if PY3:
                            print('Error in parameter: "[green]-ep[/green]".')
                            print('  [green]VLC[/green] does not supports profiles\n')
                        else:
                            print('Error in parameter: "-ep".')
                            print('  VLC does not supports profiles\n')
                        sys.exit()
                    else:
                        pyradio_config.command_line_params = args.extra_player_parameters
            else:
                if PY3:
                    print('Error in parameter: "[green]-ep[/green]".')
                    print('  Parameter format: [red]player_name[/red]:[green]parameters[/green]')
                    print('                 or [red]player_name[/red]:[magenta]profile[/magenta]:[green]name_of_profile[/green]\n')
                else:
                    print('Error in parameter: "-ep".')
                    print('  Parameter format: "player_name:parameters"')
                    print('                 or "player_name:profile:name_of_profile"\n')
                sys.exit()

        if args.unlock:
            pyradio_config.locked = False
            pyradio_config.force_to_remove_lock_file = True
            sys.exit()

        if args.show_config_dir:
            if PY3:
                print('[magenta]PyRadio[/magenta] config dir: "[red]{}[/red]"'.format(pyradio_config.stations_dir))
            else:
                print('PyRadio config dir: "{}"'.format(pyradio_config.stations_dir))
            sys.exit()

        if args.open_config_dir:
            open_conf_dir(pyradio_config)
            sys.exit()

        if args.list_playlists:
            if not config_already_read:
                pyradio_config.read_config()
            config_already_read = True
            pyradio_config.list_playlists()
            sys.exit()

        if args.list is False and \
                args.add is False and \
                args.show_cache is False and \
                args.clear_cache is False and \
                args.open_cache is False:
            print('Reading config...')
        if not config_already_read:
            read_config(pyradio_config)
            config_already_read = True

        if args.update_stations:
            if pyradio_config.locked:
                print_session_is_locked()
                sys.exit(1)
            elif not pyradio_config.user_csv_found:
                stations_change = StationsChanges(pyradio_config)
                stations_change .stations_csv_needs_sync(print_messages=False)
                stations_change.write_synced_version()
                print_simple_error('Error: "stations.csv" already up to date!')
                sys.exit(1)
            else:
                do_update_stations(pyradio_config)

        if args.open_cache:
            open_cache_dir()
            sys.exit()

        if args.show_cache:
            c = PyRadioCache()
            c.list()
            sys.exit()

        if args.clear_cache:
            c = PyRadioCache()
            if c.exists():
                if len(c.files) > 1:
                    c.clear()
                if PY3:
                    print('[magenta]PyRadio Cache[/magenta]: [green]cleared[/green]\n')
                else:
                    print('PyRadio Cache: cleared\n')
                sys.exit()
            c.list()
            sys.exit(1)

        if args.get_cache:
            upd = PyRadioUpdate(
                package=0,      # always get latest stable release
                github_long_description=None,
                python_version_to_use=3,
                pix_isolated=False
            )
            upd._get_cache = True
            upd.user = is_pyradio_user_installed()
            upd.update_pyradio()
            sys.exit()

        if args.no_themes:
            pyradio_config.use_themes = False
            pyradio_config.no_themes_from_command_line = True

        if args.use_player != '':
            requested_player = args.use_player

        if args.list is False and args.add is False:
            print('Reading playlist...')
        sys.stdout.flush()
        is_last_playlist = False
        if pyradio_config.open_last_playlist:
            last_playlist = pyradio_config.get_last_playlist()
            if last_playlist:
                args.stations = last_playlist
                is_last_playlist = True

        ret = pyradio_config.read_playlist_file(
            stationFile=args.stations,
            is_last_playlist=is_last_playlist)
        if ret < 0:
            print_playlist_selection_error(args.stations, pyradio_config, ret)

        # No need to parse the file if we add station
        # Actually we do need to do so now, so that we
        # handle 2-column vs. 3 or 4-column playlists
        if args.add:
            if sys.version_info < (3, 0):
                params = raw_input("Enter the name: "), raw_input("Enter the url: "), raw_input("Enter the encoding (leave empty for '" + pyradio_config.default_encoding + "'): ", raw_input("Enter the icon url: "))
            else:
                params = input("Enter the name: "), input("Enter the url: "), input("Enter the encoding (leave empty for '" + pyradio_config.default_encoding + "'): ", raw_input("Enter the icon url: "))
            msg = ('name', 'url')
            for i, a_param in enumerate(params):
                if i < 2:
                    if a_param.strip() == '':
                        print('** Error: No {} entered. Aborting...'.format(msg[i]))
                        sys.exit(1)
            ret = pyradio_config.append_station(params, args.stations)
            if ret < 0:
                print_playlist_selection_error(args.stations, pyradio_config, ret)
            sys.exit()

        if args.list:
            if PY3:
                console = Console()

                table = Table(show_header=True, header_style="bold magenta")
                table.title = 'Playlist: [bold magenta]{}[/bold magenta]'.format(pyradio_config.station_title)
                table.title_justify = "left"
                table.row_styles = ['', 'plum4']
                centered_table = Align.center(table)
                table.add_column("#", justify="right")
                table.add_column("Name")
                table.add_column("URL")
                table.add_column("Encoding")
                for i, n in enumerate(pyradio_config.stations):
                    if n[1] == '-':
                        table.add_row(
                            '[green]' + str(i+1) + '[/green]',
                            '[green]' + n[0] + '[/green]',
                            '[green]Group Header[/green]'
                            '',
                            style = 'bold'
                        )
                    else:
                        table.add_row(
                            str(i+1),
                            n[0],
                            n[1],
                            'utf-8' if not n[2] else n[2],
                            style = '' if not n[2] else 'bold'
                        )
                console.print(centered_table)
            else:
                m_len, header_format_string, format_string = get_format_string(pyradio_config.stations)
                header_string = header_format_string.format('[Name]','[URL]','[Encoding]')
                print(header_string)
                print(len(header_string) * '-')
                for num, a_station in enumerate(pyradio_config.stations):
                    station_name = pad_string(a_station[0], m_len)
                    if a_station[1] == '-':
                        print(format_string.format(str(num+1), '>>> ' + station_name, '', ''))
                    else:
                        if a_station[2]:
                            encoding = a_station[2]
                        else:
                            encoding = pyradio_config.default_encoding
                        print(format_string.format(str(num+1), station_name, a_station[1], encoding))
            sys.exit()

        #pyradio_config.log.configure_logger(titles=True)
        if args.debug or args.log_titles:
            __configureLogger(debug=args.debug,
                              titles=args.log_titles,
                              pyradio_config=pyradio_config
                              )
            logging.raiseExceptions = False
        else:
            ''' Refer to https://docs.python.org/3.7/howto/logging.html
                section "What happens if no configuration is provided"
            '''
            logging.raiseExceptions = False
            logging.lastResort = None

        if requested_player == '':
            requested_player = pyradio_config.player
        #else:
        #    pyradio_config.requested_player = requested_player

        if args.play == 'False':
            if args.stations == '':
                args.play = pyradio_config.default_station
        elif args.play is not None:
            try:
                check_int = int(args.play)
            except:
                if PY3:
                    print('[red]Error:[/red] Invalid parameter ([green]-p[/green] [red]' + args.play + '[/red])')
                else:
                    print('Error: Invalid parameter (-p ' + args.play + ')')
                sys.exit(1)
        if args.play == '-1':
            args.play = 'False'

        ''' get auto play last playlist data '''
        if pyradio_config.last_playlist_to_open != []:
            pre_select = pyradio_config.last_playlist_to_open[1]
            if pyradio_config.last_playlist_to_open[2] > -1:
                args.play = str(pyradio_config.last_playlist_to_open[2] + 1)
            else:
                args.play = 'False'
        else:
            pre_select = 'False'

        theme_to_use = args.theme
        if not theme_to_use:
            theme_to_use = pyradio_config.theme

        # Starts the radio TUI.
        if not sys.platform.startswith('win'):
            term = getenv('TERM')
            # print('TERM = {}'.format(term))
            if term is None:
                if PY3:
                    print('[plum4]== Warning: [green]TERM[/green] is not set. Using "[green]xterm-256color[/green]"[/plum4]')
                else:
                    print('== Warning: TERM is not set. Using "xterm-256color"')
                environ['TERM'] = 'xterm-256color'
            elif term == 'xterm' \
                    or term.startswith('screen') \
                    or term.startswith('tmux'):
                if PY3:
                    print('[plum4]== Warning: [green]TERM[/green] is set to [green]{}[/green]. Using "[green]xterm-256color[/green]"[/plum4]'.format(term))
                else:
                    print('== Warning: TERM is set to "{}". Using "xterm-256color"'.format(term))
                environ['TERM'] = 'xterm-256color'
            # this is for linux console (i.e. init 3)
            if term == 'linux':
                pyradio_config.use_themes = False
                pyradio_config.no_themes_from_command_line = True

        pyradio_config.active_remote_control_server_ip = pyradio_config.remote_control_server_ip
        pyradio_config.active_remote_control_server_port = pyradio_config.remote_control_server_port
        pyradio = PyRadio(
            pyradio_config,
            play=args.play,
            pre_select=pre_select,
            req_player=requested_player,
            theme=theme_to_use,
            force_update=args.force_update,
            record=args.record
        )
        ''' Setting ESCAPE key delay to 25ms
            Refer to: https://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses
        '''
        environ.setdefault('ESCDELAY', '25')

        ''' set window title '''
        try:
            if pyradio_config.locked:
                win_title = ' (Session Locked)'
            else:
                win_title = None
            Log.set_win_title(win_title)
        except:
            pass

        ''' curses wrapper '''
        curses.wrapper(pyradio.setup)

        ''' curses is off '''
        if pyradio.setup_return_status:
            if pyradio_config.WIN_UNINSTALL and platform.startswith('win'):
                # doing it this way so that python2 does not break (#153)
                from .win import win_press_any_key_to_unintall
                win_press_any_key_to_unintall()
                sys.exit()

            if pyradio_config.WIN_PRINT_PATHS and platform.startswith('win'):
                ''' print exe path '''
                # doing it this way so that python2 does not break (#153)
                from .win import win_print_exe_paths
                print('')
                win_print_exe_paths()

            if pyradio_config.WIN_MANAGE_PLAYERS and platform.startswith('win'):
                ''' manage players'''
                from .win import install_player
                install_player()

            elif pyradio_config.PROGRAM_UPDATE:
                if platform.startswith('win'):
                    upd = PyRadioUpdateOnWindows()
                    upd.update_or_uninstall_on_windows(mode='update-open')
                else:
                    upd = PyRadioUpdate()
                    upd.user = is_pyradio_user_installed()
                    upd.update_pyradio()
            else:
                if PY3:
                    print('\nThank you for using [magenta]PyRadio[/magenta]. Cheers!')
                else:
                    print('\nThank you for using PyRadio. Cheers!')
        else:
            print('\nThis terminal can not display colors.\nPyRadio cannot function in such a terminal.\n')

def read_config(pyradio_config):
    ret = pyradio_config.read_config()
    if ret == -1:
        if PY3:
            print('Error opening config: "[red]{}[/red]"'.format(pyradio_config.config_file))
        else:
            print('Error opening config: "{}"'.format(pyradio_config.config_file))
        sys.exit(1)
    elif ret == -2:
        if PY3:
            print('Config file is malformed: "[red]{}[/red]"'.format(pyradio_config.config_file))
        else:
            print('Config file is malformed: "{}"'.format(pyradio_config.config_file))
        sys.exit(1)
    # for n in pyradio_config.opts.keys():
    #     print('{0}: {1}'.format(n, pyradio_config.opts[n]))

def save_config(pyradio_config):
    ret = pyradio_config.save_config(from_command_line=True)
    if ret == -1:
        print('Error saving config!')
        sys.exit(1)

def no_update(uninstall):
    action = 'uninstall' if uninstall else 'update'
    if PY3:
        print('[magenta]PyRadio[/magenta] has been installed using either [green]pip[/green] or your [green]distribution\'s\npackage manager[/green]. Please use that to {} it.\n'.format(action))
    else:
        print('PyRadio has been installed using either pip or your distribution\'s\npackage manager. Please use that to {} it.\n'.format(action))
    sys.exit(1)

def print_simple_error(msg):
    if PY3:
        msg = msg.replace('Error: ', '[red]Error: [/red]').replace('PyRadio', '[magenta]PyRadio[/magenta]')
    print(msg)

def print_playlist_selection_error(a_selection, cnf, ret, exit_if_malformed=True):
    if exit_if_malformed:
        if ret == -1:
            if PY3:
                print('[red]Error:[/red] playlist is malformed: "[magenta]{}[/magenta]"'.format(a_selection))
            else:
                print('Error: playlist is malformed: "{}"'.format(a_selection))
            sys.exit(1)

    if ret == -2:
        print_simple_error('Error: Specified playlist not found')
        sys.exit(1)
    elif ret == -3:
        print_simple_error('Error: Negative playlist number specified')
        sys.exit(1)
    elif ret == -4:
        print_simple_error('Error: Specified numbered playlist not found')
        cnf.list_playlists()
        sys.exit(1)
    elif ret == -5:
        print_simple_error('Error: Failed to write playlist')
        sys.exit(1)
    elif ret == -6:
        print_simple_error('Error: Failed to rename playlist')
        sys.exit(1)
    elif ret == -7:
        print_simple_error('Error: Playlist recovery failed!\n')
        if cnf.playlist_recovery_result == 1:
            msg = '''Both a playlist file (CSV) and a playlist backup file (TXT)
            exist for the selected playlist. In this case, PyRadio would
            try to delete the CSV file, and then rename the TXT file to CSV.\n
            Unfortunately, deleting the CSV file has failed, so you have to
            manually address the issue.'''
        else:
            msg = '''A playlist backup file (TXT) has been found for the selected
            playlist. In this case, PyRadio would try to rename this file
            to CSV.\n
            Unfortunately, renaming this file has failed, so you have to
            manually address the issue.'''
        if PY3:
            print(txt.replace('TXT', '[red]TXT[/red]').replace('CSV', '[green]CSV[/green]').replace('PyRadio', '[magenta]PyRadio[/magenta]'))
        else:
            print(msg)
        #open_conf_dir(cnf)
        sys.exit(1)
    elif ret == -8:
        print_simple_error('Error: File type not supported')
        sys.exit(1)

def validate_user_config_dir(a_dir):
    if '~' in a_dir:
        exp_dir = a_dir.replace('~', path.expanduser('~'))
    else:
        exp_dir = a_dir
    this_dir = path.abspath(exp_dir)

    if not path.exists(this_dir):
        try:
            makedirs(this_dir)
        except:
            return None

    test_file = path.join(this_dir, 'test.txt')
    # write a file to check if directory is writable
    try:
        with open(test_file, 'w') as f:
            pass
    except:
        return None
    # try to read the file created above
    try:
        with open(test_file, 'r') as f:
            pass
    except:
        return None
    # remove the file created above
    try:
       remove(test_file)
    except:
        return None
    return this_dir

def open_conf_dir(cnf):
    import subprocess
    import os
    import platform
    if platform.system().lower() == 'windows':
        os.startfile(cnf.stations_dir)
    elif platform.system().lower() == 'darwin':
        subprocess.Popen(['open', cnf.stations_dir])
    else:
        try:
            subprocess.Popen(
                ['xdg-open', cnf.stations_dir],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except:
            subprocess.Popen(['xdg-open', cnf.stations_dir])

def get_format_string(stations):
    len0 = len1 = 0
    for n in stations:
        if cjklen(n[0]) > len0:
            len0 = cjklen(n[0])
        if cjklen(n[1]) > len1:
            len1 = cjklen(n[1])
    num = cjklen(str(cjklen(stations)))
    # format_string = '{0:>' + str(num) + '.' + str(num) + 's}. ' + '{1:' + str(len0) + '.' + str(len0) + 's} | {2:' + str(len1) + '.' + str(len1) + 's} | {3}'
    format_string = '{0:>' + str(num) + '.' + str(num) + 's}. ' + '{1} | {2:' + str(len1) + '.' + str(len1) + 's} | {3}'
    header_format_string = '{0:' + str(len0+num+2) + '.' + str(len0+num+2) + 's} | {1:' + str(len1) + '.' + str(len1) + 's} | {2}'
    return len0, header_format_string, format_string

def pad_string(a_string, width):
    st_len = cjklen(a_string)
    if st_len > width:
        return cjkslices(a_string, width)
    diff = width - st_len
    return a_string + ' ' * diff

if __name__ == '__main__':
    shell()
