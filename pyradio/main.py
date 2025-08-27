# -*- coding: utf-8 -*-
import locale
import sys
import curses
import logging
import logging.handlers
import shutil
from argparse import ArgumentParser, SUPPRESS as SUPPRESS, REMAINDER
from os import path, getenv, environ, remove, chmod, makedirs, rmdir, access, R_OK
from sys import platform
from contextlib import contextmanager
from platform import system
import re
import glob

from .radio import PyRadio
from .config import PyRadioConfig
from .install import PyRadioUpdate, PyRadioUpdateOnWindows, PyRadioCache, \
    is_pyradio_user_installed, version_string_to_list, get_github_tag
from .cjkwrap import cjklen, cjkslices
from .log import Log
from .common import StationsChanges, M_STRINGS, CsvReadWrite
from .schedule import PyRadioScheduleList
from .install import get_a_linux_resource_opener
from .html_help import is_graphical_environment_running
from .client import client
from .m3u import list_to_m3u, parse_m3u

try:
    # Windows
    import msvcrt
    def _getch():
        return msvcrt.getch().decode()
except ImportError:
    # Unix (Linux/Mac)
    import tty
    import termios
    def _getch():
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
        return ch

locale.setlocale(locale.LC_ALL, "")

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
PATTERN_TITLE = '%(asctime)s | %(message)s'

HAS_PIPX = True if shutil.which('pipx') else False

try:
    import netifaces
    HAS_NETIFACES = True
except:
    HAS_NETIFACES = False

HAS_RICH = False
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
        print(self._add_colors(self.format_usage()))

    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        print(self._add_colors(self.format_help()))

    def _add_colors(self, txt):
        t = txt.replace(
        'show this help',
        'Show this help').replace(
        'usage:', '• Usage:').replace(
        'options:', '• General options:').replace(
        '[', '|').replace(
        ']', '||')
        x = re.sub(r'([^a-zZ-Z0-9])(--*[^ ,\t|]*)', r'\1[red]\2[/red]', t)
        t = re.sub(r'([A-Z_][A-Z_]+)', r'[green]\1[/green]', x)
        x = re.sub('([^"]pyradio)', r'[magenta]\1[/magenta]', t, flags=re.I)
        t = re.sub(r'(player_name:[a-z:_]+)', r'[plum2]\1[/plum2]', x)
        x = re.sub(r'(•.*:)', r'[orange_red1]\1[/orange_red1]', t)
        t = x.replace(
        'mpv', '[green]mpv[/green]').replace(
        'mplayer', '[green]mplayer[/green]').replace(
        'vlc', '[green]vlc[/green]').replace(
        'Curses based Internet Radio Player',
        '[magenta]Curses based Internet Radio Player[/magenta]'
        )
        return '[bold]' + t.replace('||', r']').replace('|', r'\[').replace('• ', '') + '[/bold]'

@contextmanager
def pyradio_config_file(a_dir, headless=None):
    if headless and not HAS_NETIFACES:
        print(r'''Module "netifaces" not found!

In order to use the [red]Remote Control Server[/red], the "netifaces"
module must be installed.

Please install the module (named "python-netifaces" or
"python3-netifaces") and try executing [magenta]PyRadio[/magenta] again.
''')
        sys.exit(1)
    cf = PyRadioConfig(user_config_dir=a_dir, headless=headless)
    try:
        yield cf
    finally:
        try:
            ret, lfile = cf.remove_session_lock_file()
            if cf.force_to_remove_lock_file:
                if ret == 0:
                    print(f'Lock file removed: "[red]{lfile}[/red]"')
                elif ret == 1:
                    print(f'Failed to remove Lock file: "[red]{lfile}[/red]"')
                else:
                    print(f'Lock file not found: "[red]{lfile}[/red]"')
            cf.remove_remote_control_server_report_file()
        except:
            pass
        if cf.dirty_config:
            cf.save_config()

def __configureLogger(pyradio_config, debug=None, titles=None):
    if debug or titles:

        if debug and \
                not pyradio_config.log_debug and \
                not pyradio_config.check_playlist:
            if platform.startswith('win'):
                print(r'''Debug mode activated
  printing messages to file: "[red]{}\pyradio.log[/red]"'''.format(getenv('USERPROFILE')))
            else:
                print('Debug mode activated; printing messages to file: "[red]~/pyradio.log[/red]"')

        ret = pyradio_config.titles_log.configure_logger(
            recording_dir=pyradio_config.recording_dir,
            debug=debug,
            titles=titles
        )
        if not ret:
            print('error creating log folder')
            sys.exit(1)

def print_session_is_locked():
    print_simple_error('Error: This session is locked!')
    print('       Please exist any other instances of the program')
    print('       that are currently running and try again.')

def print_active_schedule(a_file):
    x = PyRadioScheduleList(a_file)
    tasks = x.get_info_of_tasks(HAS_RICH)
    if tasks:
        if HAS_RICH:
            console = Console()
            table = Table(show_header=True, header_style="bold magenta")
            table.title = '[bold magenta]PyRadio Active Schedule[/bold magenta]'
            centered_table = Align.center(table)
            table.row_styles = ['', 'plum4']
            table.add_column("#", justify='right')
            table.add_column("Name")
            table.add_column("Start Playback")
            table.add_column("Stop Playback")
            table.add_column("Playlist")
            table.add_column("Station")
            table.add_column("Player")
            table.add_column("Rec")
            table.add_column("Buf")

            for i, n in enumerate(tasks):
                table.add_row(
                    str(i+1),
                    n['name'],
                    n['start'],
                    n['stop'],
                    n['playlist'],
                    n['station'],
                    n['player'],
                    n['recording'],
                    n['buffering'],
                )
            console.print(centered_table)
        else:
            print('           --== PyRadio Active Schedule ==--')
            print('\n'.join(tasks))
    else:
        print('No Active Schedule available...')

def _win_python_3_12():
    import _curses
    # This crashes on Python 3.12.
        # setupterm(term=_os.environ.get("TERM", "unknown"),
            # fd=_sys.__stdout__.fileno())
    stdscr = _curses.initscr()
    for key, value in _curses.__dict__.items():
        if key[0:4] == 'ACS_' or key in ('LINES', 'COLS'):
            setattr(curses, key, value)
    return stdscr

def create_systemd_service_files():
    file_names = ('start-headless-pyradio.sh', 'stop-headless-pyradio.sh', 'pyradio.service')
    if program == 'tmux':
        files = (
r'''#!|SHELL|
touch |HOME|/pyradio.log
|PROGRAM| new-session -dA -s pyradio-session |PYRADIO| --headless auto
''',
r'''#!|SHELL|
[ -z "$(|PROGRAM| ls | grep pyradio-session)" ] || |PROGRAM| send-keys -t pyradio-session q
sleep 2
[ -z "$(|PROGRAM| ls | grep pyradio-session)" ] || |PROGRAM| sennd-keys -t pyradio-session q
[ -e |HOME|/.config/pyradio/data/server-headless.txt ] && rm |HOME|/.config/pyradio/data/server-headless.txt
[ -e |HOME|/.local/state/pyradio/server-headless.txt ] && rm |HOME|/.local/state/pyradio/server-headless.txt
'''
                )
        pass
    else:
        pass

def shell():
    if sys.version_info[0] == 2 or \
            (sys.version_info.major == 3 and sys.version_info < (3, 7)):
        print('PyRadio requires python 3.7+...')
        sys.exit(1)

    if not HAS_RICH:
        print('''Module "rich" not found!

Please install it and try executing PyRadio again.

The module name is "python-rich" (or "python3-rich" on Debian-based and
Ubuntu-based distributions).

If nothing else works, try the following command:
    python -m pip install rich
''')
        sys.exit()

    requested_player = ''
    # parser = ArgumentParser(description='Curses based Internet Radio Player')
    parser = MyArgParser(
        description='Curses based Internet Radio Player'
    )
    if not system().lower().startswith('win'):
        parser.add_argument('-c', '--config-dir', default='',
                            help='Use specified configuration directory instead of the default one. '
                            'PyRadio will try to create it, if it does not exist. '
                            'Not available on Windows.')
    parser.add_argument('-p', '--play', nargs='?', default='False', metavar=('STATION_NUMBER', ),
                        help='Start and play.'
                        'The value is num station or empty for random.')
    parser.add_argument('-x', '--external-player', action='store_true',
                        help='Play station in external player. Can be combined with --play.')
    parser.add_argument('-u', '--use-player', default='', metavar=('PLAYER', ),
            help='Use specified player. '
            'A comma-separated list can be used to specify detection order. '
            'Supported players: mpv, mplayer, vlc.')
    parser.add_argument('-l', '--list', action='store_true',
                        help='List of available stations in a playlist.')

    parser.add_argument('-lt', '--log-titles', action='store_true',
                        help='Log titles to file.')
    parser.add_argument('-sds', '--show-dirs', action='store_true',
                        help='Print all the directories used by PyRadio and exit.')
    parser.add_argument('-sd', '--show-config-dir', action='store_true',
                        help='Print config directory [CONFIG DIR] location and exit.')
    parser.add_argument('-od', '--open-config-dir', action='store_true',
                        help='Open config directory [CONFIG DIR] with default file manager.')
    if platform.startswith('win'):
        parser.add_argument('--exe', action='store_true', default=False,
                            help='Show EXE file location (Windows only).')

    parser.add_argument('-pc', '--print-config', action='store_true',
                        help='Print PyRadio config.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Start PyRadio in debug mode.')
    parser.add_argument('--d-player-input',
                        help='When -d is used, this option will not log player input (value = 0), log accepted input (value = 1) or raw input (value = 2).')
    parser.add_argument('-ul', '--unlock', action='store_true',
                        help="Remove sessions' lock file.")
    parser.add_argument('-cp', '--check-playlist', action='store_true',
                        help='Enter playlist check mode.')
    parser.add_argument('-us', '--update-stations', action='store_true',
                        help='Update "stations.csv" (if needed).')
    parser.add_argument('-U', '--update', action='store_true',
                        help='Update PyRadio.')
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='Uninstall PyRadio.')
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

    pl_group = parser.add_argument_group('• Playlist selection')
    pl_group.add_argument('-ls', '--list-playlists', action='store_true',
                        help='List of available playlists in config dir.')
    pl_group.add_argument('-s', '--stations', default='', metavar=('PLAYLIST', ),
                        help='Load the specified playlist instead of the default one.')
    pl_group.add_argument('-tlp', '--toggle-load-last-playlist', action='store_true',
                        help='Toggle autoload last opened playlist.')



    th_group = parser.add_argument_group('• Themes')
    th_group.add_argument('-t', '--theme', default='', help='Use specified theme.')
    th_group.add_argument('--show-themes', action='store_true',
                       help='Show Internal and System Themes names.')
    th_group.add_argument('--no-themes', action='store_true',
                       help='Disable themes (use default theme).')
    th_group.add_argument('--write-theme', nargs=2, metavar=('IN_THEME', 'OUT_THEME,'),
                        help='Write an Internal or System Theme to themes directory.')

    if not system().lower().startswith('darwin') and \
            not system().lower().startswith('win'):
        term_group = parser.add_argument_group('• Terminal selection')
        term_group.add_argument('--terminal', help='Use this terminal for Desktop file instead of the auto-detected one. Use "none" to reset to the default terminal or "auto" to reset to the auto-detected one.')
        term_group.add_argument('--terminal-param', nargs=REMAINDER, help='Use this as PyRadio parameter in the Desktop File. Please make sure the parameters are at the end of the command line. For example: pyradio --terminal kitty --terminal-param "-p3 -t light".')

    if HAS_PIPX:
        cache_group = parser.add_argument_group('• Cache')
        cache_group.add_argument('-oc', '--open-cache', action='store_true',
                           help='Open the Cache folder.')
        cache_group.add_argument('-sc', '--show-cache', action='store_true',
                           help='Show Cache contents.')
        cache_group.add_argument('-cc', '--clear-cache', action='store_true',
                           help='Clear Cache contents.')
        cache_group.add_argument('-gc', '--get-cache', action='store_true',
                            help='Download source code, keep it in the cache and exit.')
    else:
        parser.add_argument('-oc', '--open-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-sc', '--show-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-cc', '--clear-cache', action='store_true', help=SUPPRESS)
        parser.add_argument('-gc', '--get-cache', action='store_true', help=SUPPRESS)



    gr_recording = parser.add_argument_group('• Recording stations')
    gr_recording.add_argument('-r', '--record', action='store_true',
                        help='Turn recording on (not available for VLC player on Windows).')
    gr_recording.add_argument('-or', '--open-recordings', action='store_true',
                       help='Open the Recordings folder.')
    gr_recording.add_argument('-lr', '--list-recordings', action='store_true',
                       help='List recorded files.')
    gr_recording.add_argument('-mkv', '--mkv-file', default='',
            help='Specify a previously recorded MKV file to be used with one of the following options. The MKV_FILE can either be an absolute or a relative path, or a number provided by the -lr command line paremater. If it is a relative path, it should be found in the current or in the Recordings directory.')
    gr_recording.add_argument('-scv', '--set-mkv-cover', default='', metavar=('PNG_FILE', ),
                        help='Add or change the cover image of a previously recorded MKV file. PNG_FILE can either be an absolute or a relative path. If relative, it should be found in the current or in the Recordings directory.')
    gr_recording.add_argument('-srt', '--export-srt', action='store_true',
                              help='Export a previously recorded MKV file chapters to an SRT file. The file produced will have the name of the input file with the "mkv" extension replaced by "srt".')
    gr_recording.add_argument('-ach', '--add-chapters', default='', action='store_true',
                              help='Add (or replace) chapter markers to a previously recorded MKV file. The chapters file will be a SRT file, much like the one produced by the previous command line parameter.')

    # sc_group = parser.add_argument_group('• Scheduler')
    # sc_group.add_argument('-si', '--show-schedule-items', action='store_true',
    #                       help='Show schedule.')

    if system().lower().startswith('win'):
        parser.add_argument('--headless', default=None, help=SUPPRESS)
        gr_remote = parser.add_argument_group('• Remote Constol Server')
        gr_remote.add_argument('--address', action='store_true',
                                help='Show remote control server address.')
        gr_remote.add_argument('--free-dead-headless-server', action='store_true', help=SUPPRESS)
        gr_remote.add_argument('-fd', '--free-dead-remote-control-server', action='store_true',
                                 help='Use this if you cannot start a new remote control server (you get a message that it is already running).')
    else:
        gr_headless = parser.add_argument_group('• Headless operation')
        gr_headless.add_argument('--headless', default=None, metavar=('IP_AND_PORT', ),
                                 help='Start in headless mode. IP_AND_PORT can be a) auto (use localhost:11111), b) localhost:XXXXX (access the web server through localhost), c) lan:XXXXX (access the web server through the LAN) or d) IP_ADDRESS:XXXX (the IP_ADDRESS must be already assigned to one of the network interfaces). XXXXX can be any port number above 1025. Please make sure it is different than the one set in the configuration file.')
        gr_headless.add_argument('--address', action='store_true',
                                help='Show remote control server address.')
        gr_headless.add_argument('-fd', '--free-dead-headless-server', action='store_true',
                                 help='Use this if your headless server has terminated unexpectedly, and you cannot start a new one (you get a message that it is already running).')
        gr_headless.add_argument('--free-dead-remote-control-server', action='store_true', help=SUPPRESS)
        # gr_headless.add_argument('-gss', '--generate-systemd-service-files', action='store_true',
        #                          help='Create systemd service files to enable / disable headless operation using tmux or screen.')

    gr_m3u = parser.add_argument_group('• m3u playlist handling')
    gr_m3u.add_argument('-cvt', '--convert', default='',
                        help='Convert CSV (PyRadio playlist) to m3u and vise-versa, based on the file extension of CONVERT. '
                        'If there\'s no file extension, .csv is assumed. '
                        'Accepts -y, -o (general options). With -o: provides '
                        'the output file for the CSV to m3u conversion. '
                        'If not specified, the same path (including the name) '
                        'as the CONVERT parameter is used, replacing .csv with .m3u. '
                        'The file extension .m3u will be automatically added if not specified.'
                        )

    gr_general = parser.add_argument_group('• options')
    gr_general.add_argument('-o', '--output', default='',
                        help='Output file path (see specific commands for default behavior)')
    gr_general.add_argument('-y', '--yes', '--force', action='store_true',
                        help='Assume yes to all prompts (dangerous: overwrites files without confirmation, etc.)')

    args = parser.parse_args()
    sys.stdout.flush()

    user_config_dir = None
    if not system().lower().startswith('win'):
        if args.config_dir:
            if '..' in args.config_dir:
                print(f'Error in config path: "[red]{args.config_dir}[/red]"\n      Please do not use "[green]..[/green]" in the path!')
                sys.exit(1)
            user_config_dir = validate_user_config_dir(args.config_dir)
            if user_config_dir is None:
                print(f'Error in config path: "[red]{args.config_dir}[/red]"\n      This directory cannot be used by [magenta]PyRadio[/magenta]!')
                sys.exit(1)

    with pyradio_config_file(user_config_dir, args.headless) as pyradio_config:
        read_config(pyradio_config, args.check_playlist)

        if args.convert:
            # Determine conversion direction and validate input file
            csv_to_m3u = False
            in_file = args.convert  # Let's say args.convert is "reversed"

            # Add extension if missing
            if not in_file.lower().endswith(('.m3u', '.csv')):
                args.convert += '.csv'  # Now args.convert = "reversed.csv"
                in_file = args.convert  # Now in_file = "reversed.csv"

            # First check - try exact path (could be full path or relative)
            if not path.exists(in_file):
                # Fallback - try in config directory with basename
                config_path = path.join(pyradio_config.stations_dir, path.basename(in_file))
                if path.exists(config_path):
                    in_file = config_path
                else:
                    print(f'[red]Error:[/red] File "{in_file}" does not exist')
                    sys.exit(1)

            # Check file permissions
            if not path.isfile(in_file):
                print(f'[red]Error:[/red] "{in_file}" is not a file')
                sys.exit(1)
            if not access(in_file, R_OK):
                print(f'[red]Error:[/red] "{in_file}" is not readable')
                sys.exit(1)

            csv_to_m3u = in_file.lower().endswith('.csv')
            # Determine output file
            if args.output:
                out_file = args.output
                if csv_to_m3u and not out_file.lower().endswith('.m3u'):
                    out_file += '.m3u'
                elif not csv_to_m3u and not out_file.lower().endswith('.csv'):
                    out_file += '.csv'
            else:
                csv_to_m3u = in_file.lower().endswith('.csv')
                if csv_to_m3u:
                    out_file = path.splitext(in_file)[0] + '.m3u'
                else:
                    out_file = path.splitext(in_file)[0] + '.csv'

            if path.exists(out_file) and not args.yes:
                print(rf'File "{out_file}" exists. Overwrite? \[y/N] ', end='', flush=True)
                try:
                    key = _getch().lower()
                    sys.stderr.write('\n')  # Move to new line
                    if key != 'y':
                        print('Operation cancelled', file=sys.stderr)
                        sys.exit(1)
                except Exception as e:
                    print(f'\nError reading input: {e}', file=sys.stderr)
                    sys.exit(1)

            # Perform conversion
            csv_handler = CsvReadWrite()
            if csv_to_m3u:
                if not csv_handler.read(in_file):
                    print(f'[red]Error:[/red] Cannot read CSV file "{in_file}"')
                    sys.exit(1)

                result = list_to_m3u(csv_handler.items, out_file)
                if result is not None:  # Returns None on success, error message on failure
                    print(result)
                    sys.exit(1)

                print(f'[green]Success:[/green] Created M3U file: "{out_file}"')
            else:
                stations, error = parse_m3u(in_file)
                if error:
                    print(f'[red]Error:[/red] {error}')
                    sys.exit(1)

                ret = csv_handler.write(a_file=out_file, items=stations)
                if ret < 0:
                    print(f'[red]Error:[/red] Cannot write CSV file "{out_file}"')
                    sys.exit(1)

                print(f'[green]Success:[/green] Created CSV file: "{out_file}"')

            sys.exit(0)

        if args.check_playlist:
            pyradio_config.check_playlist = args.check_playlist
            args.play = 'False'
            args.debug = True
            args.d_player_input = '2'

        if not system().lower().startswith('darwin') and \
                not system().lower().startswith('win'):
            # if args.generate_systemd_service_files:
            #     create_systemd_service_files()
            #     sys.exit()
            # elif args.terminal:

            if args.terminal:
                import subprocess
                r = None
                script = None
                if script is None:
                    package_file = path.join(path.dirname(__file__), 'scripts', 'fix_pyradio_desktop_file')
                    script = path.join(pyradio_config.cache_dir, 'fix_pyradio_desktop_file')
                    try:
                        shutil.copy(package_file, script)
                    except Exception as e:
                        print(f'Error copying file: "{e}"')
                        sys.exit(1)
                    # try:
                    #     from urllib.request import urlretrieve
                    # except:
                    #     from urllib import urlretrieve
                    # try:
                    #     r = urlretrieve('https://raw.githubusercontent.com/coderholic/pyradio/master/devel/fix_pyradio_desktop_file')
                    # except:
                    #     print('Cannot contact github...')
                    #     sys.exit(1)
                    # if int(r[1]['content-length']) < 1000:
                    #     print('Cannot contact github...')
                    #     sys.exit(1)
                    # script = r[0]
                chmod(script , 0o700)
                if args.terminal_param:
                    command = 'bash -c "' + script + ' -t ' + args.terminal + " -p '" + ' '.join(args.terminal_param) + "'" + '"'
                else:
                    command = 'bash -c "' + script + ' -t ' + args.terminal + '"'
                subprocess.call(command, shell=True)
                if r is not None:
                    remove(r[0])
                sys.exit()

        if args.write_theme:
            if args.write_theme[0]:
                from .themes import PyRadioTheme
                theme = PyRadioTheme(pyradio_config)
                ret, msg = theme.create_theme_from_theme(
                    args.write_theme[0],
                    args.write_theme[1]
                )
                print(msg)
                return

        if args.headless:
            # Is there another headless instance?
            if path.exists(pyradio_config.remote_control_server_report_file):
                print('Error: Headless Server already running...\n')
                return

        if platform.startswith('win'):
            fd = args.free_dead_remote_control_server
        else:
            fd = args.free_dead_headless_server

        if fd:
            if platform.startswith('win'):
                ff = path.join(pyradio_config.state_dir, 'server.txt')
            else:
                ff = path.join(pyradio_config.state_dir, 'server-headless.txt')
            if path.exists(ff):
                try:
                    remove(ff)
                    print('Headless Server lock file removed!\n')
                except:
                    print('Error: Cannot remove Headless Server lock file...\n')
            else:
                print('Headless Server lock file not found\n')
            return

        if args.print_config:
            cnf = path.join(path.dirname(__file__), 'config')
            with open(cnf, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            if not pyradio_config.show_no_themes_message:
                lines.append('')
                lines.append('# User option (response to a message window)')
                lines.append('# Show a message if themes are disabled')
                lines.append('#')
                lines.append('# Default value: True')
                lines.append('show_no_themes_message = [bold green]False[/bold green]')
            if not pyradio_config.show_recording_start_message:
                lines.append('')
                lines.append('# User option (response to a message window)')
                lines.append('# Show a message when recording is enabled')
                lines.append('#')
                lines.append('# Default value: True')
                lines.append('show_recording_message = [bold green]False[/bold green]')
            for i, a_line in enumerate(lines):
                line = a_line.strip()
                if line.startswith('#'):
                    if i == 0:
                        d_line = '[deep_sky_blue1]' + line + '[/deep_sky_blue1]' + \
                            '[deep_sky_blue1] displaying[/deep_sky_blue1] ' + \
                            '[bold green]active[/bold green] ' + \
                            '[deep_sky_blue1]values[/deep_sky_blue1]'
                        d_line = d_line.replace('PyRadio', '[magenta]PyRadio[/magenta]').replace(' File ', '')
                    else:
                        d_line = '[deep_sky_blue1]' + line + '[/deep_sky_blue1]'
                else:
                    d_line = line
                    if '=' in line:
                        sp = line.split(' = ')
                        if len(sp) == 2:
                            d_line = '[magenta]' + sp[0] + '[/magenta]' + ' = '
                        if sp[0] in pyradio_config.opts.keys():
                            if sp[0] == 'localized_keys':
                                d_line += '[bold green]' + str(pyradio_config.localize) + '[/bold green]'
                            else:
                                d_line += '[bold green]' + str(pyradio_config.opts[sp[0]][1]) + '[/bold green]'
                        else:
                            if sp[0] == 'distro':
                                d_line += '[bold green]' + str(pyradio_config.distro) + '[/bold green]'
                            elif sp[0] == 'xdg_compliant':
                                d_line += '[bold green]' + str(pyradio_config.xdg_compliant) + '[/bold green]'
                            elif sp[0] in ('show_no_themes_message','show_recording_message'):
                                d_line += sp[1]
                print(d_line)
            print('')
            return

        if args.version:
            pyradio_config.get_pyradio_version()
            print(f'PyRadio version: [green]{pyradio_config.current_pyradio_version}[/green]')
            print(f"Python version: [green]{sys.version.replace('\\n', ' ').replace('\\r', ' ')}[/green]")
            if pyradio_config.distro != 'None':
                print(f'Distribution: [green]{pyradio_config.distro}[/green]')
            return

        if args.show_themes:
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
            return

        if platform.startswith('win'):
            if args.exe:
                from .win import win_print_exe_paths
                print('')
                win_print_exe_paths()
                return

        # if args.show_schedule_items:
        #     print_active_schedule(pyradio_config.schedule_file)
        #     sys.exit()

        if args.toggle_load_last_playlist:
            if pyradio_config.locked:
                print_session_is_locked()
                return
            else:
                pyradio_config.opts['open_last_playlist'][1] = not pyradio_config.opts['open_last_playlist'][1]
                pyradio_config.opts['dirty_config'][1] =  True
                print(f"Setting auto load last playlist to: \"[red]{pyradio_config.opts['open_last_playlist'][1]}[/red]\"")
                save_config()
            return

        package = 0
        if args.uninstall or args.update:
            if args.sng_master:
                package = 1
            elif args.sng_devel:
                package = 2
            elif args.devel:
                package = 3
            if pyradio_config.distro != 'None' and \
                    not platform.startswith('win'):
                action = 'uninstall' if args.uninstall else 'update'
                print(f'[magenta]PyRadio[/magenta] has been installed using your [green]distribution\'s\npackage manager[/green]. Please use that to {action} it.\n')
                return

        if args.update:
            if package == 0:
                pyradio_config.get_pyradio_version()
                last_tag = get_github_tag()
                if last_tag:
                    print(f'Released version   :  [green]{last_tag}[/green]')
                    print(f'Installed version  :  [red]{pyradio_config.current_pyradio_version}[/red]')
                    if version_string_to_list(last_tag) <= version_string_to_list(pyradio_config.current_pyradio_version):
                        print('Latest version already installed. Nothing to do....')
                        return
                    # fixing #293
                    if platform.startswith('win'):
                        print('''
[bold magenta]PyRadio[/bold magenta] will now create the update script,
and open a [green]File Explorer[/green] window.

Double click the [red]update.bat[/red] file found in
that window to complete the update process.''')
                else:
                    print('Error reading online version.\nPlease make sure you are connected to the internet and try again.')
                    return

            try:
                upd = PyRadioUpdate(package=package)
                upd.update_pyradio()
            except RuntimeError:
                upd = PyRadioUpdateOnWindows(package=package)
                upd.update_or_uninstall_on_windows(mode='update-open')
            return

        if args.uninstall:
            try:
                upd = PyRadioUpdate(package=package)
                upd.remove_pyradio()
            except RuntimeError:
                upd = PyRadioUpdateOnWindows(package=package)
                upd.update_or_uninstall_on_windows(
                    mode='uninstall-open',
                    from_pyradio=True
                )
            return

        if args.unlock:
            pyradio_config.locked = False
            pyradio_config.force_to_remove_lock_file = True
            return

        if args.show_dirs:
            print('[magenta]Directories used by PyRadio[/magenta]')
            print(f'    Config dir: "[red]{pyradio_config.stations_dir}[/red]"')
            print(f'      Data dir: "[red]{pyradio_config.data_dir}[/red]"')
            print(f'     State dir: "[red]{pyradio_config.state_dir}[/red]"')
            print(f'     Cache dir: "[red]{pyradio_config.cache_dir}[/red]"')
            print(f'      Code dir: "[red]{path.dirname(__file__)}[/red]"')
            print(f'Recordings dir: "[red]{pyradio_config.recording_dir}[/red]"')
            return

        if args.show_config_dir:
            print(f'[magenta]PyRadio[/magenta] config dir: "[red]{pyradio_config.stations_dir}[/red]"')
            return

        if args.open_config_dir:
            open_conf_dir(
                    pyradio_config,
                    msg='[magenta]PyRadio[/magenta] Config dir: "[red]{}[/red]"'
                )
            return

        if args.open_recordings:
            open_conf_dir(
                    pyradio_config,
                    msg='[magenta]PyRadio[/magenta] Recordings dir: "[red]{}[/red]"',
                    a_dir=pyradio_config.recording_dir)
            return

        if args.list_playlists:
            pyradio_config.list_playlists()
            return

        if args.update_stations:
            if pyradio_config.locked:
                print_session_is_locked()
                sys.exit(1)
            elif not pyradio_config.user_csv_found:
                stations_change = StationsChanges(pyradio_config)
                stations_change .stations_csv_needs_sync(print_messages=False)
                stations_change.write_synced_version()
                print_simple_error('Error: "stations.csv" already up to date!')
                return
            else:
                stations_change = StationsChanges(pyradio_config)
                if stations_change.stations_csv_needs_sync():
                    stations_change.update_stations_csv()
                return

        if args.open_cache:
            open_conf_dir(
                    pyradio_config,
                    msg='[magenta]PyRadio[/magenta] Cache dir: "[red]{}[/red]"',
                    a_dir=pyradio_config.cache_dir)
            return

        if args.show_cache:
            c = PyRadioCache()
            c.list()
            return

        if args.clear_cache:
            c = PyRadioCache()
            if c.exists():
                if len(c.files) > 1:
                    c.clear()
                print('[magenta]PyRadio Cache[/magenta]: [green]cleared[/green]\n')
                return
            c.list()
            return

        if args.get_cache:
            upd = PyRadioUpdate(
                package=0,      # always get latest stable release
                github_long_description=None,
                pix_isolated=False
            )
            upd._get_cache = True
            upd.user = is_pyradio_user_installed()
            upd.update_pyradio()
            return

        mkvtoolnix = None
        if args.mkv_file or args.list_recordings:
            from .mkvtoolnix import MKVToolNix
            mkvtoolnix = MKVToolNix(pyradio_config)
            if not mkvtoolnix.HAS_MKVTOOLNIX:
                if HAS_RICH:
                    print('[red]Error:[/red] [bold magenta]MKVToolNix[/bold magenta] not found!')
                else:
                    print('Error: MKVToolNix not found!')
                return
            mkvtoolnix.mkv_file = args.mkv_file

            if args.list_recordings:
                mkvtoolnix.list_mkv_files()
                return

            if args.set_mkv_cover:
                mkvtoolnix.cover_file = args.set_mkv_cover

            if args.add_chapters:
                mkvtoolnix.chapters = True

            if args.export_srt:
                mkvtoolnix.srt = True

        if mkvtoolnix:
            mkvtoolnix.execute()
            return

        if args.address:
            disp = []
            if sys.platform.startswith('win'):
                paths = ('', path.join(
                    getenv('APPDATA'),
                    'pyradio', 'data',
                    'server.txt'
                    ))
            else:
                paths = (
                        path.join(pyradio_config.state_dir, 'server-headless.txt'),
                        path.join(pyradio_config.state_dir, 'server.txt')
                )
            tok = ('Headless server', 'Server')
            out = '''  {0}
    Text address: http://{1}
    HTML address: http://{1}/html
'''
            for n in 0, 1:
                if path.exists(paths[n]):
                    try:
                        with open(paths[n], 'r', encoding='utf-8') as f:
                            addr = f.read()
                            disp.append(out.format(tok[n], addr))
                    except:
                        pass
            if disp:
                print('[magenta]PyRadio Remote Control Server[/magenta]\n' +  ''.join(disp))
            else:
                print('No [magenta]PyRadio[/magenta] Remote Control Servers running\n')
            return

        if args.no_themes:
            pyradio_config.use_themes = False
            pyradio_config.no_themes_from_command_line = True

        if args.use_player != '':
            requested_player = args.use_player

        if not args.list:
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

        if args.list:
            console = Console()

            table = Table(show_header=True, header_style="bold magenta")
            table.title = f'Playlist: [bold magenta]{pyradio_config.station_title}[/bold magenta]'
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
            return

        if args.debug or args.log_titles or pyradio_config.log_titles:
            __configureLogger(debug=args.debug,
                              titles=args.log_titles or pyradio_config.log_titles,
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
                int(args.play)
            except:
                print('[red]Error:[/red] Invalid parameter ([green]-p[/green] [red]' + args.play + '[/red])')
                return
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
                print('[plum4]== Warning: [green]TERM[/green] is not set. Using "[green]xterm-256color[/green]"[/plum4]')
                environ['TERM'] = 'xterm-256color'
            elif term == 'xterm' \
                    or term.startswith('screen') \
                    or term.startswith('tmux'):
                print(f'[plum4]== Warning: [green]TERM[/green] is set to [green]{term}[/green]. Using "[green]xterm-256color[/green]"[/plum4]')
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
            external_player=args.external_player,
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
            if pyradio_config.check_playlist:
                win_title = ' (' + M_STRINGS['checking-playlist'] + ')'
            elif pyradio_config.locked:
                win_title = M_STRINGS['session-locked']
            else:
                win_title = None
            Log.set_win_title(win_title, args.check_playlist)
        except:
            pass

        if platform.startswith('win') and not args.record:
            from .win import find_and_remove_recording_data
            find_and_remove_recording_data(pyradio_config.recording_dir)

        if args.d_player_input:
            try:
                p_i = int(args.d_player_input)
                if p_i in range(0, 3):
                    pyradio_config.debug_log_player_input = p_i
            except (ValueError, TypeError):
                pyradio_config.debug_log_player_input = 1

        while True:
            ''' curses wrapper '''
            if platform.startswith('win') and sys.version_info >= (3, 12):
                ''' fix for windows python 3.12, base on
                    https://github.com/zephyrproject-rtos/windows-curses/issues/50#issuecomment-1840485627
                '''
                pyradio.setup(_win_python_3_12())
                try:
                    curses.endwin()
                except:
                    pass
            else:
                curses.wrapper(pyradio.setup)
            pyradio.program_restart = True

            if pyradio.setup_return_status and \
                    pyradio_config.EXTERNAL_PLAYER_OPTS is not None:
                ''' curses is off: entering external player loop '''
                # print(pyradio_config.EXTERNAL_PLAYER_OPTS)
                # pyradio_config.remove_session_lock_file()
                import subprocess
                print('\n[bold red]Launching external player[/bold red]')
                print(M_STRINGS['station_'] + f'"[cyan]{pyradio_config.EXTERNAL_PLAYER_OPTS[0]}[/cyan]"')
                print(f"Command: \"[yellow]{' '.join(pyradio_config.EXTERNAL_PLAYER_OPTS[1:])}[/yellow]\"")
                process = subprocess.Popen(pyradio_config.EXTERNAL_PLAYER_OPTS[1:], stdout=None, stderr=None)
                process.wait()
                pyradio.play = 'False'
                pyradio.stopPlayer()
            else:
                break

        if pyradio_config.check_playlist:
            pyradio.program_restart = False
            print('[blue bold]-->[/blue bold] [magenta]Check Playlist Mode[/magenta] activated!')
            if path.exists(pyradio_config.check_output_folder):
                print(f'[blue bold]-->[/blue bold] Output folder:\n    "[red]{pyradio_config.check_output_folder}[/red]"')
                pyradio.handle_check_playlist_data()
            else:
                print('[blue bold]-->[/blue bold] Operation [red bold]Cancelled![/red bold]')

        ''' curses is off '''
        pyradio_config._online_browser = None
        if pyradio.setup_return_status:
            if pyradio_config.WIN_UNINSTALL and platform.startswith('win'):
                # doing it this way so that python2 does not break (#153)
                from .win import win_press_any_key_to_unintall
                win_press_any_key_to_unintall()
                return

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
                if not pyradio_config.check_playlist:
                    st = en = ''
                    if platform.startswith('win') or \
                            platform.lower().startswith('dar'):
                        st = '\n'
                    else:
                        if is_graphical_environment_running():
                            st = '\n'
                        else:
                            import subprocess
                            subprocess.call('clear')
                            en = '\n'
                    print(st + 'Thank you for using [magenta]PyRadio[/magenta]. Cheers!' + en)
        else:
            print('\nThis terminal can not display colors.\nPyRadio cannot function in such a terminal.\n')

def read_config(pyradio_config, check_playlist):
    ret = pyradio_config.read_config(check_playlist=check_playlist)
    if ret == -1:
        print(f'Error opening config: "[red]{pyradio_config.config_file}[/red]"')
        sys.exit(1)
    elif ret == -2:
        print(f'Config file is malformed: "[red]{pyradio_config.config_file}[/red]"')
        sys.exit(1)
    # for n in pyradio_config.opts.keys():
    #     print('{0}: {1}'.format(n, pyradio_config.opts[n]))
    if pyradio_config.xdg_compliant:
        pyradio_config.migrate_xdg()

    ''' check if ~/pyradio-recordings is created
        but is not used and should be deleted
    '''
    chk = path.join(path.expanduser('~'), 'pyradio-recordings')
    if path.exists(chk):
        if pyradio_config.recording_dir != chk:
            try:
                rmdir(chk)
            except (FileNotFoundError, OSError):
                pass

def save_config(pyradio_config):
    ret = pyradio_config.save_config(from_command_line=True)
    if ret == -1:
        print('Error saving config!')
        sys.exit(1)

def print_simple_error(msg):
    msg = msg.replace('Error: ', '[red]Error: [/red]').replace('PyRadio', '[magenta]PyRadio[/magenta]')
    print(msg)

def print_playlist_selection_error(a_selection, cnf, ret, exit_if_malformed=True):
    if exit_if_malformed:
        if ret == -1:
            print(f'[red]Error:[/red] playlist is malformed: "[magenta]{a_selection}[/magenta]"')
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
        print(msg.replace('TXT', '[red]TXT[/red]').replace('CSV', '[green]CSV[/green]').replace('PyRadio', '[magenta]PyRadio[/magenta]'))
        #open_conf_dir(cnf)
        sys.exit(1)
    elif ret == -8:
        print_simple_error('Error: File type not supported')
        sys.exit(1)

def validate_user_config_dir(a_dir):
    if a_dir.startswith('~'):
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
        with open(test_file, 'w', encoding='utf-8'):
            pass
    except:
        return None
    # try to read the file created above
    try:
        with open(test_file, 'r', encoding='utf-8'):
            pass
    except:
        return None
    # remove the file created above
    try:
        remove(test_file)
    except:
        return None
    return this_dir

def open_conf_dir(cnf, msg=None, a_dir=None):
    import subprocess
    import os
    import platform
    if a_dir is None:
        op_dir = cnf.stations_dir
    else:
        op_dir = a_dir
    if platform.system().lower() == 'windows':
        os.startfile(op_dir)
    elif platform.system().lower() == 'darwin':
        subprocess.Popen([shutil.which('open'), op_dir])
    else:
        prog = cnf.linux_resource_opener if cnf.linux_resource_opener else get_a_linux_resource_opener()
        if prog:
            if isinstance(prog, str):
                prog = prog.split(' ')
            try:
                subprocess.Popen(
                    [*prog, op_dir],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            except (FileNotFoundError, PermissionError):
                pass
    if msg is None:
        print(f'Dir is: "{op_dir}"')
    else:
        print(msg.format(op_dir))

def get_format_string(stations):
    len0 = len1 = 0
    for n in stations:
        if cjklen(n[0]) > len0:
            len0 = cjklen(n[0])
        if cjklen(n[1]) > len1:
            len1 = cjklen(n[1])
    num = len(str(len(stations)))
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

def run_client():
    client()

if __name__ == '__main__':
    shell()
