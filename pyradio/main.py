import csv
import sys
import curses
from argparse import ArgumentParser
from os import path, getenv

from .radio import PyRadio


DEFAULT_FILE = ''
for p in [path.join(getenv('HOME', '~'), '.pyradio', 'stations.csv'),
          path.join(getenv('HOME', '~'), '.pyradio'),
          path.join(path.dirname(__file__), 'stations.csv')]:
    if path.exists(p) and path.isfile(p):
        DEFAULT_FILE = p
        break


def shell():
    parser = ArgumentParser(description="Console radio player")
    parser.add_argument("--stations", "-s", default=DEFAULT_FILE,
                        help="Path on stations csv file.")
    parser.add_argument("--play", "-p", nargs='?', default=False,
                        help="Start and play. "
                        "The value is num station or empty for random.")
    parser.add_argument("--add", "-a", action='store_true',
                        help="Add station to list.")
    parser.add_argument("--list", "-l", action='store_true',
                        help="List of added stations.")
    args = parser.parse_args()

    # No need to parse the file if we add station
    if args.add:
        params = input("Enter the name: "), input("Enter the url: ")
        with open(args.stations, 'a') as cfgfile:
            writter = csv.writer(cfgfile)
            writter.writerow(params)
            sys.exit()

    with open(args.stations, 'r') as cfgfile:
        stations = []
        for row in csv.reader(cfgfile, skipinitialspace=True):
            if row[0].startswith('#'):
                continue
            name, url = [s.strip() for s in row]
            stations.append((name, url))

    if args.list:
        for name, url in stations:
            print(('{0:50s} {1:s}'.format(name, url)))
        sys.exit()

    pyradio = PyRadio(stations, play=args.play)
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()
