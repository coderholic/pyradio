import sys
import curses
import logging
from argparse import ArgumentParser
from os import path, getenv

from .radio import PyRadio
from .stations import PyRadioStations

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
    parser.add_argument("-l", "--list", action='store_true',
                        help="List of added stations.")
    parser.add_argument("-d", "--debug", action='store_true',
                        help="Start pyradio in debug mode.")
    parser.add_argument("-u", "--use-player", default='',
            help="Use specified player. "
            "A comma-separated list can be used to specify detection order. "
            "Supported players: mpv, mplayer, vlc.")
    args = parser.parse_args()


    stations_cnf = PyRadioStations()

    if args.use_player != '':
        requested_player = args.use_player

    # No need to parse the file if we add station
    if args.add:
        if sys.version_info < (3, 0):
            params = raw_input("Enter the name: "), raw_input("Enter the url: ")
        else:
            params = input("Enter the name: "), input("Enter the url: ")
        stations_cnf.append(params, args.stations)
        sys.exit()

    ret = stations_cnf.read_playlist_file(args.stations)
    if ret == -1:
        print('Error loading playlist: "{}"'.format(stations_cnf.stations_file))
        sys.exit(1)

    if args.list:
        for name, url in stations_cnf.stations:
            print(('{0:50s} {1:s}'.format(name, url)))
        sys.exit()

    if args.debug:
        __configureLogger()
        print('Debug mode acitvated; printing messages to file: "pyradio.log"')


    # Starts the radio gui.
    #pyradio = PyRadio(stations, play=args.play, req_player=requested_player)
    pyradio = PyRadio(stations_cnf, play=args.play, req_player=requested_player)
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()
