# -*- coding: utf-8 -*-
import sys
import curses
import logging
from argparse import ArgumentParser
from os import path, getenv, environ
from sys import platform, version_info
from contextlib import contextmanager

from .radio import PyRadio
from .config import PyRadioConfig

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

if platform.startswith('win'):
	IMPLEMENTED_PLAYERS =('mplayer', 'cvlc')
else:
	IMPLEMENTED_PLAYERS =('mpv', 'mplayer', 'cvlc')

@contextmanager
def pyradio_config_file():
    cf = PyRadioConfig()
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

def __configureLogger():
    logger = logging.getLogger("pyradio")
    logger.setLevel(logging.DEBUG)

    # Handler
    fh = logging.FileHandler(path.join(path.expanduser("~"), "pyradio.log"))
    fh.setLevel(logging.DEBUG)

    # create formatter
    formatter = logging.Formatter(PATTERN)

    # add formatter to ch
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)

def shell():
    version_too_old = False
    if sys.version_info[0] == 2:
        if sys.version_info < (2, 7):
            version_too_old = True
        elif sys.version_info.major == 3 and sys.version_info < (3, 5):
            version_too_old = True
    if version_too_old:
        print('Pyradio requires python 2.7 or 3.5+...')
        sys.exit(1)

    requested_player = ''
    parser = ArgumentParser(description="Curses based Internet radio player")
    parser.add_argument("-s", "--stations", default='',
                        help="Use specified station CSV file.")
    parser.add_argument("-p", "--play", nargs='?', default='False',
                        help="Start and play."
                        "The value is num station or empty for random.")
    parser.add_argument("-u", "--use-player", default='',
            help="Use specified player. "
            "A comma-separated list can be used to specify detection order. "
            "Supported players: mpv, mplayer, vlc.")
    parser.add_argument("-a", "--add", action='store_true',
                        help="Add station to list.")
    parser.add_argument("-ls", "--list-playlists", action='store_true',
                        help="List of available playlists in config dir.")
    parser.add_argument("-l", "--list", action='store_true',
                        help="List of available stations in a playlist.")
    parser.add_argument("-t", "--theme", default='', help="Use specified theme.")
    parser.add_argument("-scd", "--show-config-dir", action='store_true',
                        help="Print config directory [CONFIG DIR] location and exit.")
    parser.add_argument("-ocd", "--open-config-dir", action='store_true',
                        help="Open config directory [CONFIG DIR] with default file manager.")
    parser.add_argument('--unlock', action='store_true',
                        help="Remove sessions' lock file.")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Start pyradio in debug mode.")
    args = parser.parse_args()
    sys.stdout.flush()

    with pyradio_config_file() as pyradio_config:

        if args.unlock:
            pyradio_config.locked = False
            pyradio_config.force_to_remove_lock_file = True
            sys.exit()

        if args.show_config_dir:
            print('PyRadio config dir: "{}"'.format(pyradio_config.stations_dir))
            sys.exit()

        if args.open_config_dir:
            open_conf_dir(pyradio_config)
            sys.exit()

        if args.list_playlists:
            pyradio_config.list_playlists()
            sys.exit()

        if args.list is False and args.add is False:
            print('Reading config...')
        ret = pyradio_config.read_config()
        if ret == -1:
            print('Error opening config: "{}"'.format(pyradio_config.config_file))
            sys.exit(1)
        elif ret == -2:
            print('Config file is malformed: "{}"'.format(pyradio_config.config_file))
            sys.exit(1)

        if args.use_player != '':
            requested_player = args.use_player

        if args.list is False and args.add is False:
            print('Reading playlist...')
        sys.stdout.flush()
        ret = pyradio_config.read_playlist_file(stationFile=args.stations)
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
            header_format_string, format_string = get_format_string(pyradio_config.stations)
            header_string = header_format_string.format('[Name]','[URL]','[Encoding]')
            print(header_string)
            print(len(header_string) * '-')
            for num, a_station in enumerate(pyradio_config.stations):
                if a_station[2]:
                    encoding = a_station[2]
                else:
                    encoding = pyradio_config.default_encoding
                print(format_string.format(str(num+1), a_station[0], a_station[1], encoding))
            sys.exit()

        if args.debug:
            __configureLogger()
            if platform.startswith('win'):
                print('Debug mode activated\n  printing messages to file: "{}\pyradio.log"'.format(getenv('USERPROFILE')))
            else:
                print('Debug mode activated; printing messages to file: "~/pyradio.log"')
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
        if args.play == '-1':
            args.play = 'False'

        theme_to_use = args.theme
        if not theme_to_use:
            theme_to_use = pyradio_config.theme

        # Starts the radio TUI.
        pyradio = PyRadio(
            pyradio_config,
            play=args.play,
            req_player=requested_player,
            theme=theme_to_use
        )
        """ Setting ESCAPE key delay to 25ms
        Refer to: https://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses"""
        environ.setdefault('ESCDELAY', '25')
        set_terminal_title()
        curses.wrapper(pyradio.setup)
        if pyradio.setup_return_status:
            print('\nThank you for using PyRadio. Cheers!')
        else:
            print('\nThis terminal can not display colors.\nPyRadio cannot function in such a terminal.\n')

def print_playlist_selection_error(a_selection, cnf, ret, exit_if_malformed=True):
    if exit_if_malformed:
        if ret == -1:
            print('Error: playlist is malformed: "{}"'.format(a_selection))
            sys.exit(1)

    if ret == -2:
        print('Error: Specified playlist not found')
        sys.exit(1)
    elif ret == -3:
        print('Error: Negative playlist number specified')
        sys.exit(1)
    elif ret == -4:
        print('Error: Specified numbered playlist not found')
        cnf.list_playlists()
        sys.exit(1)
    elif ret == -5:
        print('Error: Failed to write playlist')
        sys.exit(1)
    elif ret == -6:
        print('Error: Failed to rename playlist')
        sys.exit(1)
    elif ret == -7:
        print('Error: Playlist recovery failed!\n')
        if cnf.playlist_recovery_result == 1:
            msg = """Both a playlist file (CSV) and a playlist backup file (TXT)
            exist for the selected playlist. In this case, PyRadio would
            try to delete the CSV file, and then rename the TXT file to CSV.\n
            Unfortunately, deleting the CSV file has failed, so you have to
            manually address the issue."""
        else:
            msg = """A playlist backup file (TXT) has been found for the selected
            playlist. In this case, PyRadio would try to rename this file
            to CSV.\n
            Unfortunately, renaming this file has failed, so you have to
            manually address the issue."""
        print(msg)
        #open_conf_dir(cnf)
        sys.exit(1)
    elif ret == -8:
        print('File type not supported')
        sys.exit(1)

def set_terminal_title():
    # set window title
    if platform.startswith('win'):
        import ctypes
        try:
            if pyradio_config.locked:
                ctypes.windll.kernel32.SetConsoleTitleW("PyRadio: The Internet Radio player (Session Locked)")
            else:
                ctypes.windll.kernel32.SetConsoleTitleW("PyRadio: The Internet Radio player")
        except:
            pass
    else:
        try:
            if pyradio_config.locked:
                sys.stdout.write("\x1b]2;PyRadio: The Internet Radio player (Session Locked)\x07")
            else:
                sys.stdout.write("\x1b]2;PyRadio: The Internet Radio player\x07")
        except:
            pass

def open_conf_dir(cnf):
    import subprocess
    import os
    import platform
    if platform.system().lower() == "windows":
        os.startfile(cnf.stations_dir)
    elif platform.system().lower() == "darwin":
        subprocess.Popen(["open", cnf.stations_dir])
    else:
        subprocess.Popen(["xdg-open", cnf.stations_dir])

def get_format_string(stations):
    len0 = len1 = 0
    for n in stations:
        if len(n[0]) > len0:
            len0 = len(n[0])
        if len(n[1]) > len1:
            len1 = len(n[1])
    num = len(str(len(stations)))
    format_string = '{0:>' + str(num) + '.' + str(num) + 's}. ' + '{1:' + str(len0) + '.' + str(len0) + 's} | {2:' + str(len1) + '.' + str(len1) + 's} | {3}'
    header_format_string = '{0:' + str(len0+num+2) + '.' + str(len0+num+2) + 's} | {1:' + str(len1) + '.' + str(len1) + 's} | {2}'
    return header_format_string, format_string

if __name__ == '__main__':
    shell()
