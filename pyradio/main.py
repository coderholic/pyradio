import csv
import sys
import curses
from argparse import ArgumentParser
from os import path as op

from .radio import PyRadio


DEFAULT_FILE = ''
for path in ['~/.pyradio/stations.csv', '~/.pyradio', op.join(op.dirname(__file__), 'stations.csv')]:
    if op.exists(path) and op.isfile(path):
        DEFAULT_FILE = path
        break


def shell():
    parser = ArgumentParser(description="Console radio player")
    parser.add_argument("--stations", "-s", default=DEFAULT_FILE, help="Path on stations csv file.")
    parser.add_argument("--random", "-r", action='store_true', help="Start and play random station.")
    parser.add_argument("--add", "-a", action='store_true', help="Add station to list.")
    parser.add_argument("--list", "-l", action='store_true', help="List of added stations.")
    args = parser.parse_args()

    try:
        cfgfile = open(args.stations, 'rb')
    except IOError, e:
        print str(e)
        sys.exit(1)

    stations = []
    for row in csv.reader(cfgfile, skipinitialspace=True):
        if row[0].startswith('#'):
            continue
        name, url = map(lambda s: s.strip(), row)
        stations.append((name, url))

    if args.list:
        for name, url in stations:
            print '{0:50s} {1:s}'.format(name, url)
        sys.exit()

    if args.add:
        params = raw_input("Enter the name:"), raw_input("Enter the url:")
        cfgfile = open(args.stations, 'a+b')
        writter = csv.writer(cfgfile)
        writter.writerow(params)
        sys.exit()

    pyradio = PyRadio(stations, play=args.random)
    curses.wrapper(pyradio.setup)


if __name__ == '__main__':
    shell()
