import csv
import sys
from os import path, getenv, makedirs, remove
from shutil import copyfile

class PyRadioStations(object):
    """ PyRadio stations file management """

    stations_file = ''

    def __init__(self, stationFile=''):

        if sys.platform.startswith('win'):
            usr_path = path.join(getenv('APPDATA'), 'pyradio')
        else:
            usr_path = path.join(getenv('HOME', '~'), '.config', 'pyradio')
        root_path = path.join(path.dirname(__file__), 'stations.csv')

        """ If a station.csv file exitst, which is wrong,
            we rename it to stations.csv """
        if path.exists(path.join(usr_path, 'station.csv')):
                copyfile(path.join(usr_path, 'station.csv'),
                        path.join(usr_path, 'stations.csv'))
                remove(path.join(usr_path, 'station.csv'))

        self._move_old_csv(usr_path)
        self._check_stations_csv(usr_path, root_path)

        if stationFile:
            if path.exists(stationFile) and path.isfile(stationFile):
                self.stations_file = stationFile

        if not self.stations_file:
            for p in [path.join(usr_path, 'pyradio.csv'),
                      path.join(usr_path, 'stations.csv'),
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
            if not path.exists(usr):
                try:
                    makedirs(usr)
                except:
                    print('Error: Cannot create config directory "{}"'.format(usr))
                    sys.exit(1)
            copyfile(root, path.join(usr, 'stations.csv'))

    def read(self, stationFile=''):
        """ Read a csv file """

        if stationFile:
            self.stations = stationFile

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

