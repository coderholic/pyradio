import csv
import sys
import glob
from os import path, getenv, makedirs, remove
from time import ctime
from shutil import copyfile

class PyRadioStations(object):
    """ PyRadio stations file management """

    stations_file = ''
    stations_filename_only = ''
    previous_stations_file = ''

    """ this is always on users config dir """
    stations_dir = ''

    stations_file_in_config_dir = False

    stations = []
    playlists = []

    selected_playlist = -1

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
                self.previous_stations_file = self.stations_file
                self.stations_file = path.abspath(stationFile)
                self.stations_filename_only = path.basename(self.stations_file)

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

    def is_in_config_dir(self):
        """ Check if a csv file is in the config dir """
        if path.dirname(self.stations_file) == self.stations_dir:
            self.stations_file_in_config_dir = True
        else:
            self.stations_file_in_config_dir = False
        return self.stations_file_in_config_dir

    def read(self, stationFile=''):
        """ Read a csv file
            Returns: number, boolean
              number:
                x  -  number of stations or
               -1  -  error
              boolean
               True if file is in the config dir
               """

        if stationFile:
            if path.exists(stationFile) and path.isfile(stationFile):
                self.previous_stations_file = self.stations_file
                self.stations_file = path.abspath(stationFile)
                self.stations_filename_only = path.basename(self.stations_file)
            else:
                return -1, False

        self.stations = []
        with open(self.stations_file, 'r') as cfgfile:
            try:
                for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    name, url = [s.strip() for s in row]
                    self.stations.append((name, url))
            except:
                return -1, False
        return len(self.stations), self.is_in_config_dir()

    def _bytes_to_human(self, B):
        ''' Return the given bytes as a human friendly KB, MB, GB, or TB string '''
        KB = float(1024)
        MB = float(KB ** 2) # 1,048,576
        GB = float(KB ** 3) # 1,073,741,824
        TB = float(KB ** 4) # 1,099,511,627,776

        if B < KB:
            return '{0} {1}'.format(B,'Bytes' if 0 == B > 1 else 'Byte')
        B = float(B)
        if KB <= B < MB:
            return '{0:.2f} KB'.format(B/KB)
        elif MB <= B < GB:
            return '{0:.2f} MB'.format(B/MB)
        elif GB <= B < TB:
            return '{0:.2f} GB'.format(B/GB)
        elif TB <= B:
            return '{0:.2f} TB'.format(B/TB)

    def append(self, params, stationFile=''):
        """ Append a station to csv file"""

        if stationFile:
            st_file = stationFile
        else:
            st_file = self.stations_file

        with open(st_file, 'a') as cfgfile:
            writter = csv.writer(cfgfile)
            writter.writerow(params)

    def read_playlists(self, force=False):
        if force is True:
            self.playlists = []
        if self.playlists == []:
            self.selected_playlist = -1
            files = glob.glob(path.join(self.stations_dir, '*.csv'))
            if len(files) == 0:
                return 0, -1
            else:
                for a_file in files:
                    a_file_name = path.basename(a_file).replace('.csv', '')
                    a_file_size = self._bytes_to_human(path.getsize(a_file))
                    a_file_time = ctime(path.getmtime(a_file))
                    self.playlists.append([a_file_name, a_file_time, a_file_size, a_file])
        """ get already loaded playlist id """
        for i, a_playlist in enumerate(self.playlists):
            if a_playlist[-1] == self.stations_file:
                self.selected_playlist = i
                break
        return len(self.playlists), self.selected_playlist


