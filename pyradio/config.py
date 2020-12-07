# -*- coding: utf-8 -*-
import csv
import sys
import logging
import glob
import curses
import collections
from os import path, getenv, makedirs, remove, rename
from sys import platform
from time import ctime
from datetime import datetime
from shutil import copyfile, move
import threading
from .browser import PyRadioStationsBrowser, probeBrowsers
HAS_REQUESTS = True
try:
    import requests
except ImportError:
    HAS_REQUESTS = False
from .log import Log


logger = logging.getLogger(__name__)


class PyRadioStations(object):
    """ PyRadio stations file management """
    #station_path = ''
    #station_file_name = ''
    #station_title = ''
    foreign_title = ''
    previous_station_path = ''

    """ this is always on users config dir """
    stations_dir = ''
    registers_dir = ''

    """ True if playlist not in config dir """
    foreign_file = False

    stations = []
    _reading_stations = []
    playlists = []

    selected_playlist = -1
    number_of_stations = -1

    """ playlist_version:
            2: 4 columns (name,URL,encoding,online browser)
            1: 3 columns (name,URL,encoding)
            0: 2 columns (name,URL)
    """
    PLAYLIST_HAS_NAME_URL = 0
    PLAYLIST_HAS_NAME_URL_ENCODING = 1
    PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER = 2
    _playlist_version = PLAYLIST_HAS_NAME_URL
    _read_playlist_version = PLAYLIST_HAS_NAME_URL

    _playlist_version_to_string = {
            PLAYLIST_HAS_NAME_URL: 'PLAYLIST_HAS_NAME_URL',
            PLAYLIST_HAS_NAME_URL_ENCODING: 'PLAYLIST_HAS_NAME_URL_ENCODING',
            PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER: 'PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER'
        }

    dirty_playlist = False

    playlist_recovery_result = 0

    _open_string = [ "open(stationFile, 'r')", "open(stationFile, 'r', encoding='utf-8')" ]
    _open_string_id = 0

    jump_tag = -1

    # station directory service object
    _online_browser = None

    _register_to_open = None
    _open_register_list = False

    _registers_lock = threading.Lock()

    def __init__(self, stationFile=''):
        if platform.startswith('win'):
            self._open_string_id = 1

        if sys.platform.startswith('win'):
            self.stations_dir = path.join(getenv('APPDATA'), 'pyradio')
            self.registers_dir = path.join(self.stations_dir, '_registers')
        else:
            self.stations_dir = path.join(getenv('HOME', '~'), '.config', 'pyradio')
            self.registers_dir = path.join(self.stations_dir, '.registers')
        """ Make sure config dirs exists """
        for a_dir in (self.stations_dir, self.registers_dir):
            if not path.exists(a_dir):
                try:
                    makedirs(a_dir)
                except:
                    print('Error: Cannot create config directory: "{}"'.format(a_dir))
                    sys.exit(1)
        self.root_path = path.join(path.dirname(__file__), 'stations.csv')

        self._ps = PyRadioPlaylistStack()

        if not self.locked:
            """ If a station.csv file exitst, which is wrong,
                we rename it to stations.csv """
            if path.exists(path.join(self.stations_dir, 'station.csv')):
                    copyfile(path.join(self.stations_dir, 'station.csv'),
                            path.join(self.stations_dir, 'stations.csv'))
                    remove(path.join(self.stations_dir, 'station.csv'))

            self._move_old_csv(self.stations_dir)
            self._check_stations_csv(self.stations_dir, self.root_path)

    @property
    def is_register(self):
        return self._ps.is_register

    @is_register.setter
    def is_register(self, value):
        raise ValueError('property is read only')

    @property
    def internal_header_height(self):
        if self._online_browser:
            return self._online_browser.internal_header_height
        return 0

    @internal_header_height.setter
    def internal_header_height(self, value):
        raise ValueError('property is read only')

    @property
    def online_browser(self):
        return self._online_browser

    @online_browser.setter
    def online_browser(self, value):
        self._online_browser = value

    @property
    def playlist_version(self):
        return self._playlist_version

    @playlist_version.setter
    def playlist_version(self, value):
        raise ValueError('property is read only')

    #@property
    #def browsing_station_service(self):
    #    return self._ps.browsing_station_service

    #@browsing_station_service.setter
    #def browsing_station_service(self, value):
    #    self._ps.browsing_station_service = value

    @property
    def history_selection(self):
        return self._ps.selection

    @history_selection.setter
    def history_selection(self, value):
        self._ps.selection = value

    @property
    def history_startPos(self):
        return self._ps.startPos

    @history_startPos.setter
    def history_startPos(self, value):
        self._ps.startPos = value

    @property
    def browsing_station_service(self):
        return self._ps.browsing_station_service

    @browsing_station_service.setter
    def browsing_station_service(self, value):
        self._ps.browsing_station_service = value

    @property
    def open_register_list(self):
        return self._open_register_list

    @open_register_list.setter
    def open_register_list(self, value):
        self._open_register_list = value

    @property
    def register_to_open(self):
        return self._register_to_open

    @register_to_open.setter
    def register_to_open(self, value):
        self._register_to_open = value

    @property
    def station_path(self):
        return self._ps.station_path

    @station_path.setter
    def station_path(self, value):
        self._ps.station_path = value

    @property
    def station_file_name(self):
        return self._ps.station_file_name

    @station_file_name.setter
    def station_file_name(self, value):
        self._ps.station_file_name = value

    @property
    def station_title(self):
        return self._ps.station_title

    @station_title.setter
    def station_title(self, value):
        self._ps.station_title = value

    @property
    def can_go_back_in_time(self):
        return True if len(self._ps._p) > 1 else False

    @can_go_back_in_time.setter
    def can_go_back_in_time(self, value):
        raise ValueError('property is read only')

    def url(self, id_in_list):
        if self._ps.browsing_station_service:
            # TODO get browser url
            return self._online_browser.url(id_in_list)
            #return self.stations[id_in_list][1].strip()
        return self.stations[id_in_list][1].strip()

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

    def copy_playlist_to_config_dir(self):
        """ Copy a foreign playlist in config dir
            Returns:
                -1: error copying file
                 0: success
                 1: playlist renamed
        """
        ret = 0
        st = path.join(self.stations_dir, self.station_file_name)
        if path.exists(st):
            ret = 1
            st = datetime.now().strftime("%Y-%m-%d_%H-%M-%S_")
            st = path.join(self.stations_dir, st + self.station_file_name)
        try:
            copyfile(self.station_path, st)
        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Cannot copy playlist: "{}"'.format(self.station_path))
            ret = -1
            return
        self._set_playlist_elements(st)
        self.read_playlists()
        self.foreign_file = False
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Playlist copied to: "{}"'.format(st))
        return ret

    def is_same_playlist(self, a_playlist):
        """ Checks if a playlist is already loaded """
        if a_playlist == self.station_path:
            return True
        else:
            return False

    def is_playlist_reloaded(self):
        return self.is_same_playlist(self.previous_station_path)

    def _is_playlist_in_config_dir(self):
        """ Check if a csv file is in the config dir """
        if path.dirname(self.station_path) == self.stations_dir:
            self.foreign_file = False
            self.foreign_title = ''
        else:
            self.foreign_file = True
            self.foreign_title = self.station_title
        self.foreign_copy_asked = False

    def _get_register_filename_from_register(self):
        if self._register_to_open:
            p = path.join(self.registers_dir,
                    'register_' + self._register_to_open + '.csv')
            if path.exists(p) and path.isfile(p):
                return p, 0
        return p, -2

    def _get_playlist_abspath_from_data(self, stationFile=''):
        """ Get playlist absolute path
            Returns: playlist path, result
              Result is:
                0  -  playlist found
               -2  -  playlist not found
               -3  -  negative number specified
               -4  -  number not found
               -8  -  file type not supported
               """
        ret = -1
        orig_input = stationFile

        if stationFile:
            if stationFile.endswith('.csv'):
                """ relative or absolute path """
                stationFile = path.abspath(stationFile)
            else:
                """ try to find it in config dir """
                if path.exists(stationFile):
                    return '', -8
                stationFile += '.csv'
                stationFile = path.join(self.stations_dir, stationFile)
            if path.exists(stationFile) and path.isfile(stationFile):
                return stationFile, 0
        else:
            for p in [path.join(self.stations_dir, 'pyradio.csv'),
                      path.join(self.stations_dir, 'stations.csv'),
                      self.root_path]:
                if path.exists(p) and path.isfile(p):
                    return p, 0

        if ret == -1:
            """ Check if playlist number was specified """
            if orig_input.replace('-', '').isdigit():
                sel = int(orig_input) - 1
                if sel == -1:
                    stationFile = path.join(self.stations_dir, 'stations.csv')
                    return stationFile, 0
                elif sel < 0:
                    """ negative playlist number """
                    return '', -3
                else:
                    n, f = self.read_playlists()
                    if sel <= n-1:
                        stationFile = self.playlists[sel][-1]
                        return stationFile, 0
                    else:
                        """ playlist number sel does not exit """
                        return '', -4
            else:
                return '', -2

    def read_playlist_file(self, stationFile='', is_register=False):
        """ Read a csv file
            Returns: number
                x  -  number of stations or
               -1  -  playlist is malformed
               -2  -  playlist not found (from _get_playlist_abspath_from_data)
               -3  -  negative number specified (from _get_playlist_abspath_from_data)
               -4  -  number not found (from _get_playlist_abspath_from_data)
               -7  -  playlist recovery failed
               -8  -  file not supported (from _get_playlist_abspath_from_data)
               """

        ret = 0
        if self._register_to_open:
            stationFile, ret = self._get_register_filename_from_register()
            self._is_register = True
        else:
            stationFile, ret = self._get_playlist_abspath_from_data(stationFile=stationFile)
            self._is_register = False
        read_file = True
        if ret < 0:
            # returns -2, -3, -4 or -8
            if self._register_to_open:
                self._reading_stations = []
                prev_file = self.station_path
                prev_format = self._playlist_version
                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER
                read_file = False
            else:
                self.stations = []
                return ret

        if read_file:
            if self._register_to_open:
                self.playlist_recovery_result = 0
            else:
                self.playlist_recovery_result = self._recover_backed_up_playlist(stationFile)
                if self.playlist_recovery_result > 0:
                    # playlist recovery failed
                    # reason in cnf.playlist_recovery_result
                    return -7
            prev_file = self.station_path
            prev_format = self._playlist_version
            self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL
            self._reading_stations = []
            with eval(self._open_string[self._open_string_id]) as cfgfile:
                try:
                    for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                        if not row:
                            continue
                        try:
                            name, url = [s.strip() for s in row]
                            self._reading_stations.append([name, url, '', ''])
                        except:
                            try:
                                name, url, enc = [s.strip() for s in row]
                                self._reading_stations.append([name, url, enc, ''])
                                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING
                            except:
                                name, url, enc, onl = [s.strip() for s in row]
                                self._reading_stations.append([name, url, enc, onl])
                                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER
                except:
                    self._reading_stations = []
                    self._playlist_version = prev_format
                    return -1

        self.stations = list(self._reading_stations)
        #logger.error('DE stations\n{}\n\n'.format(self.stations))
        self._reading_stations = []
        self._ps.add(is_register=self._open_register_list or is_register)
        self._set_playlist_elements(stationFile)
        self.previous_station_path = prev_file
        self._is_playlist_in_config_dir()
        self.number_of_stations = len(self.stations)
        self.dirty_playlist = False
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('read_playlist_file: Playlist version: {}'.format(self._playlist_version_to_string[self._playlist_version]))
        self.jump_tag = -1
        return self.number_of_stations

    def _recover_backed_up_playlist(self, stationFile):
        """ If a playlist backup file exists (.txt file), try to
            recover it (rename it to .csv)

            Return:
                -1: playlist recovered
                 0: no back up file found
                 1: remove (empty) csv file failed
                 2: rename txt to csv failed """
        backup_stationFile = stationFile.replace('.csv', '.txt')
        if path.isfile(backup_stationFile):
            try:
                tmp = curses.COLORS
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Trying to recover backed up playlist: "{}"'.format(backup_stationFile))
            except:
                print('Trying to recover backed up playlist:\n  "{}"'.format(backup_stationFile))


            if path.isfile(stationFile):
                try:
                    remove(stationFile)
                except:
                    # remove failed
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Playlist recovery failed: Cannot remove CSV file')
                    return 1
            try:
                rename(backup_stationFile, stationFile)
            except:
                # rename failed
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Playlist recovery failed: Cannot rename TXT file to CSV')
                return 2
            # playlist recovered
            if logger.isEnabledFor(logging.INFO):
                logger.info('Playlist recovery successful!!!')
            return -1
        # no playlist back up found
        return 0

    def _playlist_format_changed(self):
        """ Check if we have new or old format
            and report if format has changed

            Format type can change by editing encoding,
            deleting a non-utf-8 station etc.
        """
        playlist_version = self.PLAYLIST_HAS_NAME_URL
        for n in self.stations:
            if n[3] != '':
                playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER
                break
        if playlist_version == self.PLAYLIST_HAS_NAME_URL:
            for n in self.stations:
                if n[2] != '':
                    playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING
                    break
        if self._playlist_version == playlist_version:
            ret = False
        else:
            self._playlist_version = playlist_version
            ret = True
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('_playlist_format_changed: Playlist version: {}'.format(self._playlist_version_to_string[self._playlist_version]))
        return ret

    def save_playlist_file(self, stationFile=''):
        """ Save a playlist
        Create a txt file and write stations in it.
        Then rename it to final target

        return    0: All ok
                 -1: Error writing file
                 -2: Error renaming file
        """
        if self._playlist_format_changed():
            self.dirty_playlist = True

        if stationFile:
            st_file = stationFile
        else:
            st_file = self.station_path
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Saving playlist: "{}"'.format(st_file))

        if not self.dirty_playlist:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Playlist not modified...')
            return 0

        st_new_file = st_file.replace('.csv', '.txt')

        tmp_stations = self.stations[:]
        # Do not write comment about iheart.com
        #tmp_stations.reverse()
        #if self._playlist_version == self.PLAYLIST_HAS_NAME_URL:
        #    tmp_stations.append([ '# Find lots more stations at http://www.iheart.com' , '' ])
        #elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING:
        #    tmp_stations.append([ '# Find lots more stations at http://www.iheart.com' , '', '' ])
        #else:
        #    tmp_stations.append([ '# Find lots more stations at http://www.iheart.com' , '', '', '' ])
        #tmp_stations.reverse()
        try:
            #with open(st_new_file, 'w') as cfgfile:
            """ Convert self._open_string to
                open(st_new_file, 'w') """
            with eval(self._open_string[self._open_string_id].replace("'r'", "'w'").replace('stationFile','st_new_file')) as cfgfile:
                writter = csv.writer(cfgfile)
                for a_station in tmp_stations:
                    writter.writerow(self._format_playlist_row(a_station))
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Cannot open playlist file for writing,,,')
            return -1
        try:
            move(st_new_file, st_file)
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Cannot rename playlist file...')
            return -2
        self.dirty_playlist = False
        return 0

    def _format_playlist_row(self, a_row):
        """ Return a 2-column if in old format,
            a 3-column row if has encoding, or
            a 4 column row if has online browser flag too """
        if self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER:
            return a_row
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING:
            return a_row[:-1]
        else:
            return a_row[:-2]

    def _set_playlist_elements(self, a_playlist, a_title=''):
        self.station_path = path.abspath(a_playlist)
        self.station_file_name = path.basename(self.station_path)
        if a_title:
            self.station_title = a_title
        else:
            self.station_title = ''.join(self.station_file_name.split('.')[:-1])
        if self.is_register and self.station_title.startswith('register_'):
            self.station_title = self.station_title.replace('register_', 'Register: ')
        self._ps.remove_duplicates()
        #for n in self._ps._p:
        #    logger.error('DE ------ {}'.format(n))

    def give_me_a_new_playlist_history_item(self):
        return ['', '', '', -1, -1, -1, False,False]

    def playlist_history_len(self):
        return len(self._ps)

    def get_playlist_history_item(self, item_id=-1):
        return self._ps.item(item_id)

    def add_to_playlist_history(self, station_path='',
            station_file_name='',
            station_title='',
            startPos=0, selection=0, playing=-1,
            is_register=False,
            browsing_station_service=False):
        self._ps.add(
                station_path=station_path,
                station_file_name=station_file_name,
                station_title=station_title,
                startPos=startPos,
                selection=selection,
                playing=playing,
                is_register=is_register,
                browsing_station_service=browsing_station_service
                )

    def reset_playlist_history(self):
        self._ps.reset()

    def remove_from_playlist_history(self):
        item = self._ps.pop()
        rem_item = self.clean_playlist_history()
        return item if rem_item is None else rem_item

    def clean_playlist_history(self):
        """Remove all register items from
           the end of history"""
        item = None
        while self._ps._p[-1][6]:
            item = self._ps.pop()
        return item

    def copy_playlist_history(self):
        return self._ps.copy()

    def replace_playlist_history_items(self, a_search_path, new_item):
        """ Find a_search_path in history and replace
            the item found with new_item """
        return self._ps.replace(a_search_path, new_item)

    def _bytes_to_human(self, B):
        ''' Return the given bytes as a human friendly KB, MB, GB, or TB string '''
        KB = float(1024)
        MB = float(KB ** 2) # 1,048,576
        GB = float(KB ** 3) # 1,073,741,824
        TB = float(KB ** 4) # 1,099,511,627,776

        if B < KB:
            return '{0} B'.format(B)
        B = float(B)
        if KB <= B < MB:
            return '{0:.2f} KB'.format(B/KB)
        elif MB <= B < GB:
            return '{0:.2f} MB'.format(B/MB)
        elif GB <= B < TB:
            return '{0:.2f} GB'.format(B/GB)
        elif TB <= B:
            return '{0:.2f} TB'.format(B/TB)

    def append_station(self, params, stationFile=''):
        """ Append a station to csv file

        return    0: All ok
                 -2  -  playlist not found
                 -3  -  negative number specified
                 -4  -  number not found
                 -5: Error writing file
                 -6: Error renaming file
        """
        if stationFile:
            st_file = stationFile
        else:
            st_file = self.station_path

        st_file, ret = self._get_playlist_abspath_from_data(st_file)
        if ret < -1:
            return ret
        param_len = len(params) - 2
        self._playlist_format_changed()
        if param_len == self._playlist_version:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Appending station to playlist: "{}"'.format(stationFile))
            try:
                #with open(st_file, 'a') as cfgfile:
                """ Convert self._open_string to
                    with open(st_file, 'a') """
                with eval(self._open_string[self._open_string_id].replace("'r'", "'a'").replace('stationFile','st_file')) as cfgfile:
                    writter = csv.writer(cfgfile)
                    writter.writerow(params)
                return 0
            except:
                return -5
        else:
            #self.stations.append([ params[0], params[1], params[2] ])
            self.stations.append(params[:])
            self.dirty_playlist = True
            ret = self.save_playlist_file(st_file)
            if ret < 0:
                ret -= 4
            return ret

    def paste_station_to_named_playlist(self, a_station, a_playlist):
        """ Appends a station to a playlist or register
        which is not opened in PyRadio.

        return    0: All ok
                 -2  -  playlist not found
                 -3  -  negative number specified
                 -4  -  number not found
                 -5: Error writing file
                 -6: Error renaming file
        """
        if path.exists(a_playlist):
            m_station = a_station[:]
            ch = ('  ', ',')
            for a_ch in ch:
                if a_ch in m_station[0]:
                    m_station[0] = '"' + m_station[0] + '"'
                    break

            w_str = ','.join(m_station)
            while w_str.endswith(','):
                w_str = w_str[:-1]
            try:
                with open(a_playlist, 'a') as f:
                    f.write(w_str)
                return 0
            except:
                return -5
        else:
            return -2

    def remove_station(self, target):
        self.dirty_playlist = True
        d = collections.deque(self.stations)
        d.rotate(-target)
        ret = d.popleft()
        d.rotate(target)
        self.stations = list(d)
        #ret = self.stations.pop(target)
        self.number_of_stations = len(self.stations)
        return ret, self.number_of_stations

    def insert_station(self, station, target):
        """ Insert a station in the list at index target
        It is inserted ABOVE old target (old target becomes old target + 1)"""
        #logger.error('DE target= {0}, number_of_stations = {1}'.format(target, self.number_of_stations))
        if target < 0 or \
                target > self.number_of_stations or \
                self.number_of_stations == 0:
            return False, self.number_of_stations
        if station[2] == 'utf-8':
            station[2] = ''
        if target == self.number_of_stations:
            self.stations.append(station)
        else:
            d = collections.deque(self.stations)
            d.rotate(-target)
            d.appendleft(station)
            d.rotate(target)
            self.stations = list(d)
        self.dirty_playlist = True
        self.number_of_stations = len(self.stations)
        #logger.error('DE number_of_stations = {}'.format(self.number_of_stations))
        return True, self.number_of_stations

    def move_station(self, source, target):
        """ Moves a station in the list from index source to index target
        It is moved ABOVE old target (old target becomes old target + 1)"""
        #logger.error('DE source = {0}, target = {1}'.format(source, target))
        #logger.error('DE number_of_stations = {}'.format(self.number_of_stations))
        if source == target or \
                source < 0 or \
                target < 0 or \
                source >= self.number_of_stations or \
                target >= self.number_of_stations or \
                self.number_of_stations == 0:
            #logger.error('\n\nreturning False\n\n')
            return False
        if source < target:
            step = 1
        else:
            step = 0
        d = collections.deque(self.stations)
        d.rotate(-source)
        source_item = d.popleft()
        #logger.error('DE source_item = "{}"'.format(source_item))
        d.rotate(source)
        d.rotate(-target)
        d.appendleft(source_item)
        d.rotate(target)
        self.stations = list(d)
        self.number_of_stations = len(self.stations)
        self.dirty_playlist = True
        return True

    def switch_stations(self, source, target):
        if source == target or \
                source < 0 or \
                target < 0 or \
                source >= self.number_of_stations or \
                target >= self.number_of_stations or \
                self.number_of_stations == 0:
            return False, self.number_of_stations
        target_item = self.stations[target]
        d = collections.deque(self.stations)
        self.stations.clear()
        d.rotate(-source)
        source_item = d.popleft()
        d.appendleft(target_item)
        d.rotate(source)
        d.rotate(-target)
        d.popleft()
        d.appendleft(source_item)
        d.rotate(target)
        self.stations = list(d)
        self.number_of_stations = len(self.stations)
        return True, self.number_of_stations

    def registers_exist(self):
        return True if glob.glob(path.join(self.registers_dir, '*.csv')) else False

    def just_read_playlists(self):
        self.playlists = glob.glob(path.join(self.stations_dir, '*.csv'))

    def read_playlists(self):
        self.playlists = []
        self.selected_playlist = -1
        if self._open_register_list:
            files = glob.glob(path.join(self.registers_dir, '*.csv'))
        else:
            files = glob.glob(path.join(self.stations_dir, '*.csv'))
        if len(files) == 0:
            return 0, -1
        else:
            for a_file in files:
                a_file_name = ''.join(path.basename(a_file).split('.')[:-1])
                a_file_size = self._bytes_to_human(path.getsize(a_file))
                a_file_time = ctime(path.getmtime(a_file))
                self.playlists.append([a_file_name, a_file_time, a_file_size, a_file])
        self.playlists.sort()
        """ get already loaded playlist id """
        for i, a_playlist in enumerate(self.playlists):
            if a_playlist[-1] == self.station_path:
                self.selected_playlist = i
                break
        return len(self.playlists), self.selected_playlist

    def list_playlists(self):
        print('Playlists found in "{}"'.format(self.stations_dir))
        num_of_playlists, selected_playlist = self.read_playlists()
        pad = len(str(num_of_playlists))
        for i, a_playlist in enumerate(self.playlists):
            print('  {0}. {1}'.format(str(i+1).rjust(pad), a_playlist[0]))

    def current_playlist_index(self):
        if not self.playlists:
            self.read_playlists()
        for i, a_playlist in enumerate(self.playlists):
            #if a_playlist[0] == self.station_title:
            if a_playlist[3] == self.station_path:
                return i
        return -1

    def open_browser(self, url):
        self._online_browser = probeBrowsers(url)(self.default_encoding)
        if self._online_browser:
            self.stations = self._online_browser.stations(2)
            self._reading_stations = []
            #self._set_playlist_elements(stationFile)
            #self.previous_station_path = prev_file
            #self._is_playlist_in_config_dir()
            self.number_of_stations = len(self.stations)
            self.dirty_playlist = False

    def save_station_position(self, startPos, selection, playing):
        #logger.error('DE startPos = {0}, selection = {1}'.format(startPos, selection))
        self._ps.startPos = startPos
        self._ps.selection = selection
        self._ps.playing = playing
        #logger.error('DE  self._ps._p\n\n{}\n\n'.format(self._ps._p))

    def append_to_register(self, register, station):
        reg_file = path.join(self.registers_dir, 'register_' + register + '.csv')
        a_station = station[:]
        name = a_station[0].replace('"', '""')
        if ',' in name:
            a_station[0] = '"' + name + '"'
        else:
            a_station[0] = name
        while len(a_station) < self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER + 2:
            a_station.append('')
        string_to_write = ','.join(a_station) + '\n'
        with self._registers_lock:
            try:
                with open(reg_file, 'a') as f:
                    f.write(string_to_write)
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Failed to save to register: ' + register)
                ret = reg_file
        ret = ''
        return ret

    def pop_to_first_real_playlist(self):
        self._ps.pop_to_first_real_playlist()

    def remove_playlist_history_duplicates(self):
        self._ps.remove_duplicates()

    def history_item(self, an_item=-1):
        logger.error('DE /// history_item = {}'.format(self._ps._p[an_item]))
        return self._ps._p[an_item][:]

    def find_history_by_station_path(self, a_path):
        return self._ps._find_history_by_id(a_path, 'path')

    def find_history_by_station_name(self, a_name):
        return self._ps._find_history_by_id(a_name, 'file_name')

    def find_history_by_station_title(self, a_title):
        ret, ret_index, rev_ret_index = self._ps._find_history_by_id(a_title, 'title')
        if not ret:
            ret, ret_index, rev_ret_index = self._ps._find_history_by_id(a_title.replace('_', ' '), 'title')
        return ret, ret_index, rev_ret_index

class PyRadioConfig(PyRadioStations):

    fallback_theme = ''

    theme_not_supported = False
    theme_has_error = False
    theme_not_supported_notification_shown = False

    # True if lock file exists
    locked = False

    opts = collections.OrderedDict()
    opts[ 'general_title' ] = [ 'General Options', '' ]
    opts[ 'player' ] = [ 'Player: ', '' ]
    opts[ 'default_playlist' ] = [ 'Def. playlist: ', 'stations' ]
    opts[ 'default_station' ] = [ 'Def station: ', 'False' ]
    opts[ 'default_encoding' ] = [ 'Def. encoding: ', 'utf-8' ]
    opts[ 'conn_title' ] = [ 'Connection Options: ', '' ]
    opts[ 'connection_timeout' ] = [ 'Connection timeout: ', '10' ]
    opts[ 'force_http' ] = [ 'Force http connections: ', False ]
    opts[ 'theme_title' ] = [ 'Theme Options', '' ]
    opts[ 'theme' ] = [ 'Theme: ', 'dark' ]
    opts[ 'use_transparency' ] = [ 'Use transparency: ', False ]
    opts[ 'playlist_manngement_title' ] = [ 'Playlist Management Options', '' ]
    opts[ 'confirm_station_deletion' ] = [ 'Confirm station deletion: ', True ]
    opts[ 'confirm_playlist_reload' ] = [ 'Confirm playlist reload: ', True ]
    opts[ 'auto_save_playlist' ] = [ 'Auto save playlist: ', False ]
    opts[ 'requested_player' ] = [ '', '' ]
    opts[ 'dirty_config' ] = [ '', False ]

    def __init__(self):
        self.player = ''
        self.requested_player = ''
        self.confirm_station_deletion = True
        self.confirm_playlist_reload = True
        self.auto_save_playlist = False
        self.default_playlist = 'stations'
        self.default_station = 'False'
        self.force_http = False
        self.default_encoding = 'utf-8'
        self.connection_timeout = '10'
        self.theme = 'dark'
        self.use_transparency = False

        self.dirty_config = False
        # True if player changed by config window
        self.player_changed = False
        # [ old player, new player ]
        self.player_values = []

        self._session_lock_file = ''
        self._get_lock_file()

        PyRadioStations.__init__(self)

        self._check_config_file(self.stations_dir)
        self.config_file = path.join(self.stations_dir, 'config')
        self.force_to_remove_lock_file = False

    @property
    def requested_player(self):
        return self.opts['requested_player'][1]

    @requested_player.setter
    def requested_player(self, val):
        self.opts['requested_player'][1] = val.replace(' ', '')
        if self.opts['player'][1] != self.opts['requested_player'][1]:
            self.opts['player'][1] = self.requested_player
            self.opts['dirty_config'][1] = True

    @property
    def player(self):
        return self.opts['player'][1]

    @player.setter
    def player(self, val):
        self.opts['player'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def force_http(self):
        return self.opts['force_http'][1]

    @force_http.setter
    def force_http(self, val):
        self.opts['force_http'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def use_transparency(self):
        return self.opts['use_transparency'][1]

    @use_transparency.setter
    def use_transparency(self, val):
        self.opts['use_transparency'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def default_encoding(self):
        return self.opts['default_encoding'][1]

    @default_encoding.setter
    def default_encoding(self, val):
        self.opts['default_encoding'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def default_playlist(self):
        return self.opts['default_playlist'][1]

    @default_playlist.setter
    def default_playlist(self, val):
        self.opts['default_playlist'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def default_station(self):
        return self.opts['default_station'][1]

    @default_station.setter
    def default_station(self, val):
        self.opts['default_station'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def confirm_station_deletion(self):
        return self.opts['confirm_station_deletion'][1]

    @confirm_station_deletion.setter
    def confirm_station_deletion(self, val):
        self.opts['confirm_station_deletion'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def confirm_playlist_reload(self):
        return self.opts['confirm_playlist_reload'][1]

    @confirm_playlist_reload.setter
    def confirm_playlist_reload(self, val):
        self.opts['confirm_playlist_reload'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def auto_save_playlist(self):
        return self.opts['auto_save_playlist'][1]

    @auto_save_playlist.setter
    def auto_save_playlist(self, val):
        self.opts['auto_save_playlist'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def connection_timeout(self):
        """ connection timeout as string """
        return self.opts['connection_timeout'][1]

    @connection_timeout.setter
    def connection_timeout(self, val):
        self.opts['connection_timeout'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def connection_timeout_int(self):
        """ connection timeout as integer
            if < 5 or > 60, set to 10
            On error set to 10
            Read only
        """
        try:
            ret = int(self.opts['connection_timeout'][1])
            if not 5 <= ret <= 60:
                ret = 10
        except:
            ret = 10
        self.opts['connection_timeout'][1] = str(ret)
        return ret

    @connection_timeout_int.setter
    def connection_timeout_int(self, val):
        return

    @property
    def theme(self):
        return self.opts['theme'][1]

    @theme.setter
    def theme(self, val):
        self.opts['theme'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def dirty_config(self):
        return self.opts['dirty_config'][1]

    @dirty_config.setter
    def dirty_config(self, val):
        self.opts['dirty_config'][1] = val

    @property
    def session_lock_file(self):
        return self._session_lock_file

    @session_lock_file.setter
    def session_lock_file(self, val):
        return

    def _get_lock_file(self):
        ''' Populate self._session_lock_file
            If it exists, locked becomes True
            Otherwise, the file is created
        '''
        if path.exists('/run/user'):
            from os import geteuid
            self._session_lock_file = path.join('/run/user', str(geteuid()), 'pyradio.lock')
            # remove old style session lock file (if it exists)
            if path.exists(path.join(self.stations_dir, '.lock')):
                try:
                    remove(path.join(self.stations_dir, '.lock'))
                except:
                    pass
        else:
            self._session_lock_file =  path.join(self.stations_dir, 'pyradio.lock')

        if path.exists(self._session_lock_file):
                self.locked = True
        else:
            try:
                with open(self._session_lock_file, 'w') as f:
                    pass
            except:
                pass

    def remove_session_lock_file(self):
        ''' remove session lock file, if session is not locked '''
        if self.locked:
            if logger.isEnabledFor(logging.INFO):
                logger.info('Not removing lock file; session is locked...')
        else:
            if path.exists(self._session_lock_file):
                try:
                    remove(self._session_lock_file)
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Lock file removed...')
                    return 0, self._session_lock_file
                except:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Failed to remove Lock file...')
                    return 1, self._session_lock_file
            else:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Lock file not found...')
                return -1, self._session_lock_file

    def _check_config_file(self, usr):
        ''' Make sure a config file exists in the config dir '''
        package_config_file = path.join(path.dirname(__file__), 'config')
        user_config_file = path.join(usr, 'config')

        ''' restore config from bck file '''
        if path.exists(user_config_file + '.restore'):
            try:
                copyfile(user_config_file + '.restore', user_config_file)
                remove(self.user_config_file + '.restore')
            except:
                pass

        ''' Copy package config into user dir '''
        if not path.exists(user_config_file):
            copyfile(package_config_file, user_config_file)

    def read_config(self):
        lines = []
        try:
            with open(self.config_file, 'r') as cfgfile:
                lines = [line.strip() for line in cfgfile if line.strip() and not line.startswith('#') ]

        except:
            self.__dirty_config = False
            return -1
        for line in lines:
            sp = line.replace(' ', '').split('=')
            if len(sp) != 2:
                return -2
            if sp[1] == '':
                return -2
            if sp[0] == 'player':
                self.opts['player'][1] = sp[1].lower().strip()
                if sys.platform.startswith('win'):
                    self.opts['player'][1] = self.opts['player'][1].replace('mpv,', '')
            elif sp[0] == 'connection_timeout':
                self.opts['connection_timeout'][1] = sp[1].strip()
                # check integer number and set to 10 if error
                x = self.connection_timeout_int
            elif sp[0] == 'default_encoding':
                self.opts['default_encoding'][1] = sp[1].strip()
            elif sp[0] == 'theme':
                self.opts['theme'][1] = sp[1].strip()
            elif sp[0] == 'default_playlist':
                self.opts['default_playlist'][1] = sp[1].strip()
            elif sp[0] == 'default_station':
                st = sp[1].strip()
                if st == '-1' or st.lower() == 'false':
                    self.opts['default_station'][1] = 'False'
                elif st == "0" or st == 'random':
                    self.opts['default_station'][1] = None
                else:
                    self.opts['default_station'][1] = st
            elif sp[0] == 'confirm_station_deletion':
                if sp[1].lower() == 'false':
                    self.opts['confirm_station_deletion'][1] = False
                else:
                    self.opts['confirm_station_deletion'][1] = True
            elif sp[0] == 'confirm_playlist_reload':
                if sp[1].lower() == 'false':
                    self.opts['confirm_playlist_reload'][1] = False
                else:
                    self.opts['confirm_playlist_reload'][1] = True
            elif sp[0] == 'auto_save_playlist':
                if sp[1].lower() == 'true':
                    self.opts['auto_save_playlist'][1] = True
                else:
                    self.opts['auto_save_playlist'][1] = False
            elif sp[0] == 'use_transparency':
                if sp[1].lower() == 'true':
                    self.opts['use_transparency'][1] = True
                else:
                    self.opts['use_transparency'][1] = False
            elif sp[0] == 'force_http':
                if sp[1].lower() == 'true':
                    self.opts['force_http'][1] = True
                else:
                    self.opts['force_http'][1] = False
        self.opts['dirty_config'][1] = False

        # check if default playlist exists
        if self.opts['default_playlist'][1] != 'stations':
            ch = path.join(self.stations_dir, self.opts['default_playlist'][1] + '.csv')
            if not path.exists(ch):
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Default playlist "({}") does not exist; reverting to "stations"'.format(self.opts['default_station'][1]))
                self.opts['default_playlist'][1] = 'stations'
                self.opts['default_station'][1] = 'False'
                #self.opts['dirty_config'][1] = True
        return 0

    def save_config(self):
        """ Save config file

            Creates config.restore (back up file)
            Returns:
                -1: Error saving config
                 0: Config saved successfully
                 1: Config not saved (not modified)
                 TODO: 2: Config not saved (session locked) """
        if self.locked:
            if logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (session locked)')
            return 1
        if not self.opts['dirty_config'][1]:
            if logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (not modified)')
            return 1
        txt ='''# PyRadio Configuration File

# Player selection
# This is the equivalent to the -u , --use-player command line parameter
# Specify the player to use with PyRadio, or the player detection order
# Example:
#   player = vlc
# or
#   player = vlc,mpv, mplayer
# Default value: mpv,mplayer,vlc
player = {0}

# Default playlist
# This is the playlist to open if none is specified
# You can scecify full path to CSV file, or if the playlist is in the
# config directory, playlist name (filename without extension) or
# playlist number (as reported by -ls command line option)
# Default value: stations
default_playlist = {1}

# Default station
# This is the equivalent to the -p , --play command line parameter
# The station number within the default playlist to play
# Value is 1..number of stations, "-1" or "False" means no auto play
# "0" or "Random" means play a random station
# Default value: False
default_station = {2}

# Default encoding
# This is the encoding used by default when reading data provided by
# a station (such as song title, etc.) If reading said data ends up
# in an error, 'utf-8' will be used instead.
#
# A valid encoding list can be found at:
#   https://docs.python.org/2.7/library/codecs.html#standard-encodings
# replacing 2.7 with specific version:
#   3.0 up to current python version.
#
# Default value: utf-8
default_encoding = {3}

# Connection timeout
# PyRadio will wait for this number of seconds to get a station/server
# message indicating that playback has actually started.
# If this does not happen (within this number of seconds after the
# connection is initiated), PyRadio will consider the station
# unreachable, and display the "Failed to connect to: [station]"
# message.
#
# Valid values: 5 - 60
# Default value: 10
connection_timeout = {4}

# Force http connections
# Most radio stations use plain old http protocol to broadcast, but
# some of them use https. If this is enabled,  all connections will
# use http; results depend on the combination of station/player.
#
# Valid values: True, true, False, false
# Default value: False
force_http = {5}

# Default theme
# Hardcooded themes:
#   dark (default) (8 colors)
#   light (8 colors)
#   dark_16_colors (16 colors dark theme alternative)
#   light_16_colors (16 colors light theme alternative)
#   black_on_white (bow) (256 colors)
#   white_on_black (wob) (256 colors)
# Default value = 'dark'
theme = {6}

# Transparency setting
# If False, theme colors will be used.
# If True and a compositor is running, the stations' window
# background will be transparent. If True and a compositor is
# not running, the terminal's background color will be used.
# Valid values: True, true, False, false
# Default value: False
use_transparency = {7}


# Playlist management
#
# Specify whether you will be asked to confirm
# every station deletion action
# Valid values: True, true, False, false
# Default value: True
confirm_station_deletion = {8}

# Specify whether you will be asked to confirm
# playlist reloading, when the playlist has not
# been modified within Pyradio
# Valid values: True, true, False, false
# Default value: True
confirm_playlist_reload = {9}

# Specify whether you will be asked to save a
# modified playlist whenever it needs saving
# Valid values: True, true, False, false
# Default value: False
auto_save_playlist = {10}

'''
        copyfile(self.config_file, self.config_file + '.restore')
        if self.opts['default_station'][1] is None:
            self.opts['default_station'][1] = '-1'
        try:
            with open(self.config_file, 'w') as cfgfile:
                cfgfile.write(txt.format(self.opts['player'][1],
                    self.opts['default_playlist'][1],
                    self.opts['default_station'][1],
                    self.opts['default_encoding'][1],
                    self.opts['connection_timeout'][1],
                    self.opts['force_http'][1],
                    self.opts['theme'][1],
                    self.opts['use_transparency'][1],
                    self.opts['confirm_station_deletion'][1],
                    self.opts['confirm_playlist_reload'][1],
                    self.opts['auto_save_playlist'][1]))
        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Error saving config')
            return -1
        try:
            remove(self.config_file + '.restore')
        except:
            pass
        if logger.isEnabledFor(logging.INFO):
            logger.info('Config saved')
        self.opts['dirty_config'][1] = False
        return 0

    def read_playlist_file(self, stationFile='', is_register=False):
        if stationFile.strip() == '':
            stationFile = self.default_playlist
        return super(PyRadioConfig, self).read_playlist_file(stationFile=stationFile, is_register=is_register)


class PyRadioPlaylistStack(object):

    _p = []

    _id = {'station_path': 0,
           'path': 0,
           'station_file_name': 1,
           'file_name': 1,
           'filename': 1,
           'station_title': 2,
           'title': 2,
           'startPos': 3,
           'selection': 4,
           'playing' : 5,
           'is_register': 6,
           'browsing_station_service': 7,
           }

    def __init__(self):
        pass

    def __len__(self):
        return len(self._p)

    @property
    def is_register(self):
        if self._p:
            return self._p[-1][self._id['is_register']]
        else:
            return False

    @is_register.setter
    def is_register(self, value):
        if self._p:
            self._p[-1][self._id['is_register']] = value

    @property
    def browsing_station_service(self):
        if self._p:
            return self._p[-1][self._id['browsing_station_service']]
        else:
            return False

    @browsing_station_service.setter
    def browsing_station_service(self, value):
        if self._p:
            self._p[-1][self._id['browsing_station_service']] = value

    @property
    def station_path(self):
        if self._p:
            return self._p[-1][self._id['station_path']]
        else:
            return ''

    @station_path.setter
    def station_path(self, value):
        if self._p:
            self._p[-1][self._id['station_path']] = value

    @property
    def station_file_name(self):
        if self._p:
            return self._p[-1][self._id['station_file_name']]
        else:
            return ''

    @station_file_name.setter
    def station_file_name(self, value):
        if self._p:
            self._p[-1][self._id['station_file_name']] = value

    @property
    def station_title(self):
        if self._p:
            return self._p[-1][self._id['station_title']]
        else:
            return ''

    @station_title.setter
    def station_title(self, value):
        if self._p:
            self._p[-1][self._id['station_title']] = value

    @property
    def selection(self):
        if self._p:
            return self._p[-1][self._id['selection']]
        else:
            return 0

    @selection.setter
    def selection(self, value):
        if self._p:
            self._p[-1][self._id['selection']] = value

    @property
    def startPos(self):
        if self._p:
            return self._p[-1][self._id['startPos']]
        else:
            return 0

    @startPos.setter
    def startPos(self, value):
        if self._p:
            self._p[-1][self._id['startPos']] = value

    @property
    def playing(self):
        if self._p:
            return self._p[-1][self._id['playing']]
        else:
            return -1

    @playing.setter
    def playing(self, value):
        if self._p:
            self._p[-1][self._id['playing']] = value

    def item(self, item_id=-1):
        try:
            return self._p[item_id]
        except:
            return []

    def remove_duplicates(self):
        if len(self._p) > 1:
            val1 = self._p[-1][self._id['station_file_name']]
            val2 = self._p[-2][self._id['station_file_name']]
            if val1 == val2:
                self._p.pop()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('PyRadioPlaylistStack: Removing duplicate entry...')
                return True
        return False

    def add(self, station_path='',
            station_file_name='',
            station_title='',
            startPos=0, selection=0, playing=-1,
            is_register=False,
            browsing_station_service=False):
        if len(self._p) > 1 and station_path:
            if self._p[-1][self._id['station_path']] == station_path:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('PyRadioPlaylistStack.add(): Refusing to add duplicate entry: "{}"\nUpdating selections instead'.format(station_path))
                    logger.debug('                            Updating selections instead')
                self._p[-1][3:6] = [startPos, selection, playing]
                return
        if is_register:
            while self._p[-1][self._id['is_register']]:
                self._p.pop()
        self._p.append([station_path,
            station_file_name,
            station_title,
            startPos, selection, playing,
            is_register,
            browsing_station_service])
        #logger.error('DE playlist history\n{}\n'.format(self._p))

    def get_item_member(self, member, item_id=-1):
        if member in self._id.keys():
            return self._p[item_id][self._id[member]]
        else:
            raise ValueError('member "{}" does not exist'.format(member))

    def _find_history_by_id(self, a_search, it_id, start=0):
        """ Find a history item

            Parameters
            ==========
            a_search search term
            it_id    one of the _id strings
            start    return id if >0 start

            Returns
            =======
            history item,
            index,
            reversed index (len - id - 1)
        """
        logger.error('DE looking for: ' + a_search + ' with id: ' + it_id)
        for i, n in enumerate(self._p):
            if (n[self._id[it_id]] == a_search) and (i >= start):
                return n, i, len(self._p) - i - 1
        return None, -1, -1

    def pop(self):
        if len(self._p) > 1:
            return self._p.pop()
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Refusing to remove first entry')
            return self._p[0]

    def set(self, a_list):
        if a_list:
            self._p = a_list[:]
        else:
            raise ValueError('playlist history cannot be empty')

    def reset(self):
        if self._p:
            self._p = self._p[:1]

    def copy(self):
        return self._p[:]

    def pop_to_first_real_playlist(self):
        if not self.get_item_member('is_register'):
            return
        while self.get_item_member('is_register'):
            self.pop()

    def replace(self, a_search_path, new_item):
        """ Find a_search_path in history and replace
            the item found with new_item """
        if not isinstance(new_item, list) and \
                not isinstance(new_item, tuple):
            return -2
        else:
            if len(new_item) != 8:
                return -1
        ret = 0
        for i,n in enumerate(self._p):
            if n[0] == a_search_path:
                self._p[i] = list(new_item[:])
                ret += 1
        return ret
