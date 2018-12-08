import csv
import sys
from os import path, getenv, makedirs, remove
from shutil import copyfile

class PyRadioStations(object):
    """ PyRadio stations file management """

    stations_file = ''
    stations_dir = ''

    def __init__(self, stationFile=''):

        if sys.platform.startswith('win'):
            self.stations_dir = path.join(getenv('APPDATA'), 'pyradio')
        else:
            self.stations_dir = path.join(getenv('HOME', '~'), '.config', 'pyradio')
        """ Make sure config dir exists """
        if not path.exists(self.stations_dir):
            try:
                makedirs(self.stations_dir)
            except:
                print('Error: Cannot create config directory: "{}"'.format(self.stations_dir))
                sys.exit(1)
        root_path = path.join(path.dirname(__file__), 'stations.csv')

        """ If a station.csv file exitst, which is wrong,
            we rename it to stations.csv """
        if path.exists(path.join(self.stations_dir, 'station.csv')):
                copyfile(path.join(self.stations_dir, 'station.csv'),
                        path.join(self.stations_dir, 'stations.csv'))
                remove(path.join(self.stations_dir, 'station.csv'))

        self._move_old_csv(self.stations_dir)
        self._check_stations_csv(self.stations_dir, root_path)

        if stationFile:
            if path.exists(stationFile) and path.isfile(stationFile):
                self.stations_file = stationFile

        if not self.stations_file:
            for p in [path.join(self.stations_dir, 'pyradio.csv'),
                      path.join(self.stations_dir, 'stations.csv'),
                      root_path]:
                if path.exists(p) and path.isfile(p):
                    self.stations_file = p
                    break

    def _move_old_csv(self, usr):
        """ if a ~/.pyradio files exists, relocate it in user
            config folder and rename it to stations.csv, or if 
            that exists, to pyradio.csv """

        src = path.join(getenv('HOME', '~'), '.pyradio')
        dst = path.join(usr, 'pyradio.csv')
        dst1 = path.join(usr, 'stations.csv')
        if path.exists(src) and path.isfile(src):
            if path.exists(dst1):
                copyfile(src, dst)
            else:
                copyfile(src, dst1)
            try:
                remove(src)
            except:
                pass

    def _check_stations_csv(self, usr, root):
        ''' Reclocate a stations.csv copy in user home for easy manage.
            E.g. not need sudo when you add new station, etc '''

        if path.exists(path.join(usr, 'stations.csv')):
            return
        else:
            copyfile(root, path.join(usr, 'stations.csv'))

    def read(self, stationFile=''):
        """ Read a csv file """

        if stationFile:
            self.stations_file = stationFile

        self.stations = []
        with open(self.stations_file, 'r') as cfgfile:
            try:
                for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    name, url = [s.strip() for s in row]
                    self.stations.append((name, url))
            except:
                return 0
        return len(self.stations)

    def append(self, params, stationFile=''):
        """ Append a station to csv file"""

        if stationFile:
            st_file = stationFile
        else:
            st_file = self.stations_file

        with open(st_file, 'a') as cfgfile:
            writter = csv.writer(cfgfile)
            writter.writerow(params)

