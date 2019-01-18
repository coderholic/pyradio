import sys
import curses
import logging
from argparse import ArgumentParser
from os import path, getenv, environ

from .radio import PyRadio
from .config import PyRadioConfig

PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

IMPLEMENTED_PLAYERS =('mpv', 'mplayer', 'cvlc')

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
    requested_player = ''
    parser = ArgumentParser(description="Curses based Internet radio player")
    parser.add_argument("-s", "--stations", default='',
                        help="Use specified station CSV file.")
    parser.add_argument("-p", "--play", nargs='?', default=False,
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
    parser.add_argument("-scd", "--show-config-dir", action='store_true',
                        help="Print config directory location and exit.")
    parser.add_argument("-ocd", "--open-config-dir", action='store_true',
                        help="Open config directory with default file manager.")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Start pyradio in debug mode.")
    args = parser.parse_args()

    sys.stdout.flush()
    pyradio_config = PyRadioConfig()

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
    ret = pyradio_config.read_playlist_file(args.stations)
    if ret < 0:
        print_playlist_selection_error(args.stations, pyradio_config, ret)

    # No need to parse the file if we add station
    # Actually we do need to do so now, so that we
    # handle 2-column vs. 3-column playlists
    if args.add:
        if sys.version_info < (3, 0):
            params = raw_input("Enter the name: "), raw_input("Enter the url: "), raw_input("Enter the encoding (leave empty for 'utf-8'): ")
        else:
            params = input("Enter the name: "), input("Enter the url: "), input("Enter the encoding (leave empty for 'utf-8'): ")
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
        print('Debug mode activated; printing messages to file: "~/pyradio.log"')

    if requested_player is '':
        requested_player = pyradio_config.player_to_use
    #else:
    #    pyradio_config.requested_player_to_use = requested_player

    if args.play is False:
        if args.stations == '':
            args.play = pyradio_config.default_station
    if args.play == '-1':
        args.play = False

    # Starts the radio gui.
    pyradio = PyRadio(pyradio_config, play=args.play, req_player=requested_player)
    """ Setting ESCAPE key delay to 25ms
    Refer to: https://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses"""
    environ.setdefault('ESCDELAY', '25')
    curses.wrapper(pyradio.setup)

def print_playlist_selection_error(a_selection, cnf, ret, exit_if_malformed=True):
    if exit_if_malformed:
        if ret == -1:
            print('Error: playlist is malformed: "{}"'.format(a_selection))
            #print('Error: playlist is malformed: "{}"'.format(args.stations))
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
