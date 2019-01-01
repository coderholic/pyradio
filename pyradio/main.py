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
    parser.add_argument("-a", "--add", action='store_true',
                        help="Add station to list.")
    parser.add_argument("-ls", "--list-playlists", action='store_true',
                        help="List of available playlists in config dir.")
    parser.add_argument("-l", "--list", action='store_true',
                        help="List of added stations.")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Start pyradio in debug mode.")
    parser.add_argument("-u", "--use-player", default='',
            help="Use specified player. "
            "A comma-separated list can be used to specify detection order. "
            "Supported players: mpv, mplayer, vlc.")
    args = parser.parse_args()

    sys.stdout.flush()
    pyradio_config = PyRadioConfig()

    if args.list_playlists:
        pyradio_config.list_playlists()
        sys.exit()

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

    # No need to parse the file if we add station
    if args.add:
        if sys.version_info < (3, 0):
            params = raw_input("Enter the name: "), raw_input("Enter the url: ")
        else:
            params = input("Enter the name: "), input("Enter the url: ")
        pyradio_config.append_station(params, args.stations)
        sys.exit()

    print('Reading playlist...')
    sys.stdout.flush()
    ret = pyradio_config.read_playlist_file(args.stations)
    if ret == -1:
        print('Error loading playlist: "{}"'.format(args.stations))
        sys.exit(1)

    if args.list:
        for name, url in pyradio_config.stations:
            print(('{0:50.50s} {1:s}'.format(name, url)))
        sys.exit()

    if args.debug:
        __configureLogger()
        print('Debug mode acitvated; printing messages to file: "~/pyradio.log"')

    if requested_player is '':
        requested_player = pyradio_config.player_to_use
    #else:
    #    pyradio_config.requested_player_to_use = requested_player

    if args.play is not None:
        if args.play is False:
            args.play = pyradio_config.default_station

    # Starts the radio gui.
    pyradio = PyRadio(pyradio_config, play=args.play, req_player=requested_player)
    """ Setting ESCAPE key delay to 25ms
    Refer to: https://stackoverflow.com/questions/27372068/why-does-the-escape-key-have-a-delay-in-python-curses"""
    environ.setdefault('ESCDELAY', '25')
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()
