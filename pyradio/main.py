import csv
import sys
import curses
import logging
from argparse import ArgumentParser
from os import path, getenv, makedirs
from shutil import copyfile

from .radio import PyRadio

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


def check_stations(usr, root):
    ''' Reclocate a station.csv copy in user home for easy manage.
        Ej not need sudo when you add new station, etc '''

    if path.exists(path.join(usr, 'station.csv')):
        return
    else:
        if not path.exists(usr):
            try:
                makedirs(usr)
            except:
                print('Error: Cannot create config directory "{}"'.format(usr))
                sys.exit(1)
        copyfile(root, path.join(usr, 'station.csv'))

if sys.platform.startswith('win'):
    usr_path = path.join(getenv('APPDATA'), 'pyradio')
else:
    usr_path = path.join(getenv('HOME', '~'), '.config', 'pyradio')
root_path = path.join(path.dirname(__file__), 'stations.csv')
check_stations(usr_path, root_path)

DEFAULT_FILE = ''
for p in [path.join(usr_path, 'station.csv'),
          path.join(getenv('HOME', '~'), '.pyradio'),
          root_path]:
    if path.exists(p) and path.isfile(p):
        DEFAULT_FILE = p
        break


def shell():
    requested_player = ''
    parser = ArgumentParser(description="Curses based Internet radio player")
    parser.add_argument("-s", "--stations", default=DEFAULT_FILE,
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

    if args.use_player != '':
        requested_player = args.use_player

    # No need to parse the file if we add station
    if args.add:
        if sys.version_info < (3, 0):
            params = raw_input("Enter the name: "), raw_input("Enter the url: ")
        else:
            params = input("Enter the name: "), input("Enter the url: ")
        with open(args.stations, 'a') as cfgfile:
            writter = csv.writer(cfgfile)
            writter.writerow(params)
            sys.exit()

    with open(args.stations, 'r') as cfgfile:
        stations = []
        for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
            if not row:
                continue
            name, url = [s.strip() for s in row]
            stations.append((name, url))

    if args.list:
        for name, url in stations:
            print(('{0:50s} {1:s}'.format(name, url)))
        sys.exit()

    if args.debug:
        __configureLogger()
        print('Debug mode acitvated; printing messages to file: "pyradio.log"')


    # Starts the radio gui.
    pyradio = PyRadio(stations, play=args.play, req_player=requested_player)
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()
