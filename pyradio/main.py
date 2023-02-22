# -*- coding: utf-8 -*-
import sys
import curses
import logging, logging.handlers
import subprocess
import argparse
from argparse import ArgumentParser, SUPPRESS as SUPPRESS
from os import path, getenv, environ, remove, chmod, makedirs
from sys import platform, version_info, executable
from contextlib import contextmanager
from platform import system

from .radio import PyRadio
from .config import PyRadioConfig, SUPPORTED_PLAYERS
from .install import PyRadioUpdate, PyRadioUpdateOnWindows, is_pyradio_user_installed, version_string_to_list, get_github_tag
from .cjkwrap import cjklen, cjkslices, fill
from .log import Log

import locale
locale.setlocale(locale.LC_ALL, "")

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
PATTERN_TITLE = '%(asctime)s | %(message)s'

PY3 = sys.version[0] == '3'

HAS_PRINTY = False
if PY3:
    try:
        from printy import printy as pr_printy
        import re
        HAS_PRINTY = True
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
        if HAS_PRINTY:
            pr_printy(self._add_colors(self.format_usage()))
        else:
            print(self.format_usage())

    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        if HAS_PRINTY:
            pr_printy(self._add_colors(self.format_help()))
        else:
            print(self.format_help())

    def _add_colors(self, txt):
        t = txt.replace('show this help', 'Show this help').replace('usage:', 'Usage:').replace('options:', 'Options:').replace('[', '|').replace(']', '||')
        x = re.sub(r'([^a-zZ-Z0-9])(--*[^ ,\t|]*)', r'\1[r]\2@', t)
        t = re.sub(r'([A-Z_][A-Z_]+)', r'[n]\1@', x)
        x = re.sub('([^"]pyradio)', r'[m]\1@', t, flags=re.I)
        t = re.sub(r'(player_name:[a-z:_]+)', r'[n]\1@', x)
        x = t.replace('mpv', '[n]mpv@').replace('mplayer', '[n]mplayer@').replace('vlc', '[n]vlc@')
        return x.replace('||', r'\]').replace('|', r'\[')

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
                    print('Lock file removed: "{}"'.format(lfile))
                elif ret == 1:
                    print('Failed to remove Lock file: "{}"'.format(lfile))
                else:
                 print('Lock file not found: "{}"'.format(lfile))
        except:
            pass

def __configureLogger(pyradio_config, debug=None, titles=None):
    if debug or titles:

        if debug and not pyradio_config.log_degub:
            if platform.startswith('win'):
                print('Debug mode activated\n  printing messages to file: "{}\pyradio.log"'.format(getenv('USERPROFILE')))
            else:
                print('Debug mode activated; printing messages to file: "~/pyradio.log"')

        pyradio_config.titles_log.configure_logger(
            debug=debug,
            titles=titles
        )

def check_printy(config_use_color_on_terminal):
    if PY3 and not HAS_PRINTY and \
            config_use_color_on_terminal:
        print('\n\n*** Trying to install "printy"...')
        if (subprocess.call(
            sys.executable + \
            ' -m pip install printy', shell=True
        )
                ) > 0:
            print('''
Please execute manually
    python -m pip install printy
and then execute PyRadio again.
            ''')
            sys.exit(1)
        print('''
To see it in action, just execute
    pyradio -h
        ''')
    else:
        if HAS_PRINTY and not config_use_color_on_terminal:
            print('\n\n*** Trying to uninstall "printy"...')
            subprocess.call(
                sys.executable + \
                ' -m pip uninstall -y printy', shell=True
            )

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
    if platform.startswith('win'):
        parser.add_argument('--exe', action='store_true', default=False,
                            help='Show EXE file location (Windows only).')
    parser.add_argument('-U', '--update', action='store_true',
                        help='Update PyRadio.')
    if not platform.startswith('win'):
        parser.add_argument('--user', action='store_true', default=False,
                            help='Install only for current user (not on Windows).')
    parser.add_argument('-R', '--uninstall', action='store_true',
                        help='Uninstall PyRadio.')
    parser.add_argument('--unlock', action='store_true',
                        help="Remove sessions' lock file.")
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
                print('Error in config path: "{}"\n      Please do not use ".." in the path!'.format(args.config_dir))
                sys.exit(1)
            user_config_dir = validate_user_config_dir(args.config_dir)
            if user_config_dir is None:
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
            chmod(script , 0o766)
            if args.terminal_param:
                command = 'bash -c "' + script + ' -t ' + args.terminal + " -p '-" + args.terminal_param + "'" + '"'
                command = 'bash -c "' + script + ' -t ' + args.terminal + " -p '" + args.terminal_param.replace('\\', '') + "'" + '"'
                print(command)
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
            print('PyRadio version: {}'.format(pyradio_config.current_pyradio_version))
            print('Python version: {}'.format(sys.version.replace('\n', ' ').replace('\r', ' ')))
            pyradio_config.read_config()
            if pyradio_config.distro != 'None':
                print('Distribution: {}'.format(pyradio_config.distro))
            sys.exit()

        if args.show_themes:
            pyradio_config.read_config()
            print('Internal Themes')
            for n in pyradio_config.internal_themes:
                if n not in ('bow', 'wob'):
                    print('  ', n)
            print('System Themes')
            for n in pyradio_config.system_themes:
                print('  ', n)
            # print('Ext. Projects Themes')
            # for n in pyradio_config.auto_update_frameworks:

            #     print('  {0} {1}'.format(n.NAME, '  (Supported) ' if n.can_auto_update else '  (Not supported)'))
            #     if n.can_auto_update:
            #         for k in n.THEME:
            #             print('    ', k)
            sys.exit()

        if platform.startswith('win'):
            if args.exe:
                print_exe_paths()
                sys.exit()

        if args.toggle_load_last_playlist:
            if pyradio_config.locked:
                print_simple_error('Error: Another instance of PyRadio is already running!')
                print('       Please close it and try again...')
                sys.exit(1)
            else:
                read_config(pyradio_config)
                pyradio_config.opts['open_last_playlist'][1] = not pyradio_config.opts['open_last_playlist'][1]
                pyradio_config.opts['dirty_config'][1] =  True
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
                if not platform.startswith('win'):
                    upd.user = args.user
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
          print('Error: You cannot use parameters "-ep" and "-ap" together!\n')
          sys.exit(1)

        ''' user specified extra player parameter '''
        if args.active_player_param_id:
            try:
                a_param = int(args.active_player_param_id)
            except ValueError:
                print('Error: Parameter -ap is not a number\n')
                sys.exit(1)
            if 1 <= a_param <= 11:
                pyradio_config.user_param_id = a_param
            else:
                print('Error: Parameter -ap must be between 1 and 11')
                print('       Actually, it must be between 1 and the maximum')
                print('       number of parameters for your default player.\n')
                args.list_player_parameters = True

        ''' list extra player parameters '''
        if args.list_player_parameters:
            if HAS_PRINTY:
                pr_printy('[m]PyRadio Players Extra Parameters@')
                pr_printy('[m]' + 32 * '-' + '@')
            else:
                print('PyRadio Players Extra Parameters')
                print(32 * '-')
            read_config(pyradio_config)
            default_player_name = pyradio_config.opts['player'][1].replace(' ', '').split(',')[0]
            if default_player_name == '':
                default_player_name = SUPPORTED_PLAYERS[0]
            for a_player in SUPPORTED_PLAYERS:
                if default_player_name == a_player:
                    if HAS_PRINTY:
                        pr_printy('Player: [r]' + a_player + '@ ([n]default@)')
                    else:
                        print('Player: ' + a_player + ' (default)')
                else:
                    if HAS_PRINTY:
                        pr_printy('Player: [r]' + a_player + '@')
                    else:
                        print('Player: ' + a_player)
                default = 0
                for i, a_param in enumerate(pyradio_config.saved_params[a_player]):
                    if i == 0:
                        default = int(a_param)
                    else:
                        str_default = '(default)' if i == default else ''
                        count = str(i) if i > 9 else ' ' + str(i)
                        if HAS_PRINTY:
                            pr_printy('    [n]{0}@. {1} {2}'.format(count, a_param, str_default).replace('(default)', '([n]default@)'))
                        else:
                            print('    {0}. {1} {2}'.format(count, a_param, str_default))
                print('')
            sys.exit()

        ''' extra player parameters '''
        if args.extra_player_parameters:
            if ':' in args.extra_player_parameters:
                if pyradio_config.locked:
                    print_simple_error('Error: This session is locked!')
                    print('       Please exist any other instances of the program')
                    print('       that are currently running and try again.')
                    sys.exit(1)
                else:
                    if args.extra_player_parameters.startswith('vlc:profile'):
                        print('Error in parameter: "-ep".')
                        print('  VLC does not supports profiles\n')
                        sys.exit()
                    else:
                        pyradio_config.command_line_params = args.extra_player_parameters
            else:
                if HAS_PRINTY:
                    pr_printy('Error in parameter: "[n]-ep@".')
                    pr_printy('  Parameter format: "[r]player_name@:[n]parameters@"')
                    pr_printy('                 or "[r]player_name@:[m]profile@:[n]name_of_profile@"\n')
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
            if HAS_PRINTY:
                pr_printy('[m]PyRadio@ config dir: "[r]{}@"'.format(pyradio_config.stations_dir))
            else:
                print('PyRadio config dir: "{}"'.format(pyradio_config.stations_dir))
            sys.exit()

        if args.open_config_dir:
            open_conf_dir(pyradio_config)
            sys.exit()

        if args.list_playlists:
            pyradio_config.read_config()
            pyradio_config.list_playlists()
            sys.exit()

        if args.list is False and args.add is False:
            print('Reading config...')
        if not config_already_read:
            read_config(pyradio_config)
            config_already_read = True

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
        # handle 2-column vs. 3-column playlists
        if args.add:
            if sys.version_info < (3, 0):
                params = raw_input("Enter the name: "), raw_input("Enter the url: "), raw_input("Enter the encoding (leave empty for '" + pyradio_config.default_encoding + "'): ")
            else:
                params = input("Enter the name: "), input("Enter the url: "), input("Enter the encoding (leave empty for '" + pyradio_config.default_encoding + "'): ")
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
            m_len, header_format_string, format_string = get_format_string(pyradio_config.stations)
            header_string = header_format_string.format('[Name]','[URL]','[Encoding]')
            print(header_string)
            print(len(header_string) * '-')
            for num, a_station in enumerate(pyradio_config.stations):
                if a_station[2]:
                    encoding = a_station[2]
                else:
                    encoding = pyradio_config.default_encoding
                station_name = pad_string(a_station[0], m_len)
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
                if HAS_PRINTY:
                    pr_printy('[<y]== Warning: @[n]TERM@[<y] is not set. Using "@[n]xterm-256color@[<y]"@')
                else:
                    print('== Warning: TERM is not set. Using "xterm-256color"')
                environ['TERM'] = 'xterm-256color'
            elif term == 'xterm' \
                    or term.startswith('screen') \
                    or term.startswith('tmux'):
                if HAS_PRINTY:
                    pr_printy('[<y]== Warning:@ [n]TERM@ [<y]is set to "@[n]{}@[<y]". Using "@[n]xterm-256color@[<y]"@'.format(term))
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
            force_update=args.force_update
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
                # doing it this way so that pyton2 does not break (#153)
                from .win import win_press_any_key_to_unintall
                win_press_any_key_to_unintall()
                sys.exit()

            if pyradio_config.WIN_PRINT_PATHS and platform.startswith('win'):
                ''' print exe path '''
                # doing it this way so that pyton2 does not break (#153)
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
                if HAS_PRINTY:
                    pr_printy('\nThank you for using [m]PyRadio@. Cheers!')
                else:
                    print('\nThank you for using PyRadio. Cheers!')

                if not config_already_read:
                    pyradio_config.read_config()
                check_printy(pyradio_config.use_color_on_terminal)

        else:
            print('\nThis terminal can not display colors.\nPyRadio cannot function in such a terminal.\n')

def read_config(pyradio_config):
    ret = pyradio_config.read_config()
    if ret == -1:
        print('Error opening config: "{}"'.format(pyradio_config.config_file))
        sys.exit(1)
    elif ret == -2:
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
    print('PyRadio has been installed using either pip or your distribution\'s\npackage manager. Please use that to {} it.\n'.format(action))
    sys.exit(1)

def print_simple_error(msg):
    if HAS_PRINTY:
        msg = msg.replace('Error: ', '[r]Error: @').replace('PyRadio', '[m]PyRadio@')
        pr_printy(msg)
    else:
        print(msg)

def print_playlist_selection_error(a_selection, cnf, ret, exit_if_malformed=True):
    if exit_if_malformed:
        if ret == -1:
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
