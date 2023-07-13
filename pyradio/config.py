# -*- coding: utf-8 -*-
import csv
import sys
import logging
import glob
import curses
import collections
import json
from os import path, getenv, makedirs, remove, rename, readlink, SEEK_END, SEEK_CUR, environ, getpid
from sys import platform
from time import ctime, sleep
from datetime import datetime
from shutil import copyfile, move, Error as shutil_Error
import threading
from copy import deepcopy
try:
    from subprocess import Popen, DEVNULL
except ImportError:
    from subprocess import Popen
from platform import system
if system().lower() == 'windows':
    from os import startfile
from pyradio import version, stations_updated

from .browser import PyRadioStationsBrowser, probeBrowsers
from .install import get_github_long_description
from .common import is_rasberrypi
from .player import pywhich
HAS_REQUESTS = True

try:
    import requests
except:
    HAS_REQUESTS = False

from .log import Log
HAS_DNSPYTHON = True
try:
    from dns import resolver
except:
    HAS_DNSPYTHON = False
HAS_PSUTIL = True
try:
    import psutil
except:
    HAS_PSUTIL = False

PY3 = sys.version[0] == '3'

if PY3:
    try:
        from rich.console import Console
        from rich.table import Table
        from rich.align import Align
        from rich import print
    except:
        pass

logger = logging.getLogger(__name__)

SUPPORTED_PLAYERS = ('mpv', 'mplayer', 'vlc')

import locale
locale.setlocale(locale.LC_ALL, "")

class PyRadioStations(object):
    ''' PyRadio stations file management '''
    #station_path = ''
    #station_file_name = ''
    #station_title = ''
    foreign_title = ''
    previous_station_path = ''

    ''' this is always on users config dir '''
    stations_dir = ''
    registers_dir = ''

    ''' True if playlist not in config dir '''
    foreign_file = False

    stations = []
    _reading_stations = []
    playlists = []

    selected_playlist = -1
    number_of_stations = -1

    ''' playlist_version:
            2: 4 columns (name,URL,encoding,online browser)
            1: 3 columns (name,URL,encoding)
            0: 2 columns (name,URL)
    '''
    PLAYLIST_HAS_NAME_URL = 0
    PLAYLIST_HAS_NAME_URL_ENCODING = 1
    PLAYLIST_HAS_NAME_URL_ENCODING_ICON = 2
    _playlist_version = PLAYLIST_HAS_NAME_URL
    _read_playlist_version = PLAYLIST_HAS_NAME_URL

    _playlist_version_to_string = {
            PLAYLIST_HAS_NAME_URL: 'PLAYLIST_HAS_NAME_URL',
            PLAYLIST_HAS_NAME_URL_ENCODING: 'PLAYLIST_HAS_NAME_URL_ENCODING',
            PLAYLIST_HAS_NAME_URL_ENCODING_ICON: 'PLAYLIST_HAS_NAME_URL_ENCODING_ICON'
        }

    dirty_playlist = False

    playlist_recovery_result = 0

    _open_string_id = 0

    jump_tag = -1

    ''' station directory service object '''
    _online_browser = None

    _register_to_open = None
    _open_register_list = False

    _registers_lock = threading.Lock()

    ''' set to True if a stations.csv is found in user's folder '''
    _user_csv_found = False

    ''' the playlist saved as last playlist (name only) '''
    _last_opened_playlist_name = ''

    ''' last opened playlist splitted on , '''
    last_playlist_to_open = []

    station_history = None
    play_from_history = False

    normal_stations_history = None

    show_no_themes_message = True

    def __init__(self, stationFile='', user_config_dir=None):
        if platform.startswith('win'):
            self._open_string_id = 1

        if sys.platform.startswith('win'):
            self.stations_dir = path.join(getenv('APPDATA'), 'pyradio')
            self.registers_dir = path.join(self.stations_dir, '_registers')
        else:
            if user_config_dir is None:
                self.stations_dir = path.join(getenv('HOME', '~'), '.config', 'pyradio')
            else:
                self.stations_dir = user_config_dir
            self.registers_dir = path.join(self.stations_dir, '.registers')
        self.data_dir = path.join(self.stations_dir, 'data')
        self.recording_dir = path.join(self.stations_dir, 'recordings')
        ''' Make sure config dirs exists '''
        for a_dir in (self.stations_dir,
                      self.registers_dir,
                      self.data_dir,
                      self.recording_dir
                      ):
            if not path.exists(a_dir):
                try:
                    makedirs(a_dir)
                except:
                    print('Error: Cannot create config directory: "{}"'.format(a_dir))
                    sys.exit(1)
        self.root_path = path.join(path.dirname(__file__), 'stations.csv')

        self.themes_dir = path.join(self.stations_dir, 'themes')
        try:
            makedirs(self.themes_dir, exist_ok = True)
        except:
            try:
                makedirs(self.themes_dir)
            except:
                pass

        self._ps = PyRadioPlaylistStack()

        if not self.locked:
            ''' If a station.csv file exitst, which is wrong,
                we rename it to stations.csv '''
            if path.exists(path.join(self.stations_dir, 'station.csv')):
                    copyfile(path.join(self.stations_dir, 'station.csv'),
                            path.join(self.stations_dir, 'stations.csv'))
                    remove(path.join(self.stations_dir, 'station.csv'))

            self._move_old_csv(self.stations_dir)
            self._check_stations_csv(self.stations_dir, self.root_path)
            self._move_to_data()
        self._copy_icon()

    def _move_to_data(self):
        if not path.exists(self.data_dir):
            makedirs(self.data_dir)
        files_to_move = [
            path.join(self.stations_dir, 'pyradio.png'),
        ]
        for n in ('.*.date', '.*.ver', '*.lock'):
            files = glob.glob(path.join(self.stations_dir, n))
            if files:
                files_to_move.extend(files)
        for n in files_to_move:
            from_file = path.join(self.stations_dir, n)
            if path.exists(from_file):
                to_file = from_file.replace(self.stations_dir, self.data_dir)
                if path.exists(to_file):
                    try:
                        remove(from_file)
                    except (shutil_Error, IOError, OSError):
                        pass
                else:
                    try:
                        move(from_file, self.data_dir)
                    except (shutil_Error, IOError, OSError):
                        print('\n\nError moving data files!\nPlease close all PyRadio related files and try again...\n')
                        sys.exit(1)

    def _copy_icon(self):
        ''' if i still do not have the icon in the data dir
            copy it from the icons dir
        '''
        if not path.exists(path.join(self.data_dir, 'pyradio.png')):
            from_file = path.join(path.dirname(__file__), 'icons', 'pyradio.png')
            to_file = path.join(self.data_dir, 'pyradio.png')
            try:
                copyfile(from_file, to_file)
            except:
                pass

        ''' make sure that the icon is under ~/.config/pyradio/data
            (the previous section may install it to a different location,
            if --config-dir is used).
        '''
        default_icon_location = path.join(getenv('HOME', '~'), '.config', 'pyradio', 'data')
        if default_icon_location != self.data_dir:
            to_file = path.join(default_icon_location, 'pyradio.png')
            if not path.exists(to_file):
                try:
                    copyfile(from_file, to_file)
                except:
                    pass

    @property
    def user_csv_found(self):
        return self._user_csv_found

    @user_csv_found.setter
    def user_csv_found(self, val):
        raise ValueError('parameter is read only')

    @property
    def is_local_playlist(self):
        return self._ps.is_local_playlist

    @is_local_playlist.setter
    def is_local_playlist(self, value):
        raise ValueError('property is read only')

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
    def history_playing(self):
        return self._ps.playing

    @history_playing.setter
    def history_playing(self, value):
        self._ps.playing = value

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

    def set_station_history(self,
                            execute_funct,
                            pass_first_item_funct,
                            pass_last_item_funct,
                            no_items_funct):
        self.normal_stations_history = PyRadioStationsStack(
            execute_function=execute_funct,
            pass_first_item_function=pass_first_item_funct,
            pass_last_item_function=pass_last_item_funct,
            no_items_function=no_items_funct
        )
        self.stations_history = self.normal_stations_history

    def save_last_playlist(self, sel):
        lp = path.join(self.data_dir, 'last-playlist')
        llp = self._ps.last_local_playlist
        out_pl = [llp[2], llp[4], llp[5]]
        if llp[2]:
            # logger.error(f'llp = {llp} - saved = {self._last_opened_playlist_name}')
            try:
                with open(lp, 'w', encoding='utf-8') as f:
                    writter = csv.writer(f)
                    writter.writerow(out_pl)
            except PermissionError:
                pass

    def url(self, id_in_list):
        if self._ps.browsing_station_service:
            # TODO get browser url
            return self._online_browser.url(id_in_list)
            #return self.stations[id_in_list][1].strip()
        return self.stations[id_in_list][1].strip()

    def _move_old_csv(self, usr):
        ''' if a ~/.pyradio files exists, relocate it in user
            config folder and rename it to stations.csv, or if
            that exists, to pyradio.csv '''

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
            self._user_csv_found = True
            return
        else:
            copyfile(root, path.join(usr, 'stations.csv'))
            with open(path.join(self.data_dir, 'last-sync'), 'w') as f:
                self.get_pyradio_version()
                v = self.current_pyradio_version.replace('.', ', ')
                f.write(v)

    def copy_playlist_to_config_dir(self):
        ''' Copy a foreign playlist in config dir
            Returns:
                -1: error copying file
                 0: success
                 1: playlist renamed
        '''
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
        ''' Checks if a playlist is already loaded '''
        if a_playlist == self.station_path:
            return True
        else:
            return False

    def is_playlist_reloaded(self):
        return self.is_same_playlist(self.previous_station_path)

    def _is_playlist_in_config_dir(self):
        ''' Check if a csv file is in the config dir '''
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
        ''' Get playlist absolute path
            Returns: playlist path, result
              Result is:
                0  -  playlist found
               -2  -  playlist not found
               -3  -  negative number specified
               -4  -  number not found
               -8  -  file type not supported
               '''
        ret = -1
        orig_input = stationFile

        if stationFile:
            if stationFile.endswith('.csv'):
                ''' relative or absolute path '''
                stationFile = path.abspath(stationFile)
            else:
                ''' try to find it in config dir '''
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
            ''' Check if playlist number was specified '''
            if orig_input.replace('-', '').isdigit():
                sel = int(orig_input) - 1
                if sel == -1:
                    stationFile = path.join(self.stations_dir, 'stations.csv')
                    return stationFile, 0
                elif sel < 0:
                    ''' negative playlist number '''
                    return '', -3
                else:
                    n, f = self.read_playlists()
                    if sel <= n-1:
                        stationFile = self.playlists[sel][-1]
                        return stationFile, 0
                    else:
                        ''' playlist number sel does not exit '''
                        return '', -4
            else:
                return '', -2

    def _package_stations(self):
        ''' read package stations.csv file '''
        with open(self.root_path, 'r', encoding='utf-8') as cfgfile:
            for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                if not row:
                    continue
                try:
                    name, url = [s.strip() for s in row]
                    yield [name, url, '', '']
                except:
                    try:
                        name, url, enc = [s.strip() for s in row]
                        yield [name, url, enc, '']
                    except:
                        name, url, enc, onl = [s.strip() for s in row]
                        yield [name, url, enc, onl]

    def integrate_playlists(self):
        ''''''

        ''' get user station urls '''
        self.added_stations = 0
        urls = []
        for n in self.stations:
            urls.append(n[1])
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('----==== Stations integration ====----')
        for a_pkg_station in self._package_stations():
            if a_pkg_station[1] not in urls:
                self.stations.append(a_pkg_station)
                self.added_stations += 1
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Added: {0} - {1}'.format(self.added_stations, a_pkg_station))

    def read_playlist_for_server(self, stationFile):
        out = []
        in_file = self._construct_playlist_path(stationFile)
        try:
            with open(in_file, 'r', encoding='utf-8') as cfgfile:
                for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    out.append('<b>' + row[0] + '</b>') if row[1] == '-' else out.append(row[0])
        except:
            return None, []
        return in_file, out

    def read_playlist_file(
        self,
        stationFile='',
        is_last_playlist=False,
        is_register=False):
        ''' Read a csv file
            Returns: number
                x  -  number of stations or
               -1  -  playlist is malformed
               -2  -  playlist not found (from _get_playlist_abspath_from_data)
               -3  -  negative number specified (from _get_playlist_abspath_from_data)
               -4  -  number not found (from _get_playlist_abspath_from_data)
               -7  -  playlist recovery failed
               -8  -  file not supported (from _get_playlist_abspath_from_data)
               '''

        ret = 0
        if self._register_to_open:
            stationFile, ret = self._get_register_filename_from_register()
            self._is_register = True
        else:
            stationFile, ret = self._get_playlist_abspath_from_data(stationFile=stationFile)
            self._is_register = False
        read_file = True
        if ret < 0:
            ''' returns -2, -3, -4 or -8 '''
            self.last_playlist_to_open = []
            if self._register_to_open:
                self._reading_stations = []
                prev_file = self.station_path
                prev_format = self._playlist_version
                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
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
                    ''' playlist recovery failed
                        reason in cnf.playlist_recovery_result
                    '''
                    return -7
            prev_file = self.station_path
            prev_format = self._playlist_version
            self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL
            self._reading_stations = []
            with open(stationFile, 'r', encoding='utf-8') as cfgfile:
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
                                name, url, enc, icon = [s.strip() for s in row]
                                self._reading_stations.append([name, url, enc, {'image': icon}])
                                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
                except:
                    self._reading_stations = []
                    self._playlist_version = prev_format
                    return -1

        self.stations = list(self._reading_stations)
        # logger.error('DE stations\n{}\n\n'.format(self.stations))
        self.set_playlist_data(stationFile, prev_file, is_register)
        self.number_of_stations = len(self.stations)

        # for n in self.stations:
        #     logger.info(n)
        return self.number_of_stations

    def set_playlist_data(self, stationFile, prev_file, is_register = False):
        ''' used to be part of read_playlist_file
            moved here so it can be used with station history
            when opening a playlit
        '''
        self._reading_stations = []
        self._ps.add(is_register=self._open_register_list or is_register)
        self._set_playlist_elements(stationFile)
        self.previous_station_path = prev_file
        self._is_playlist_in_config_dir()
        self.dirty_playlist = False
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('read_playlist_file: Playlist version: {}'.format(self._playlist_version_to_string[self._playlist_version]))
        self.jump_tag = -1

    def _recover_backed_up_playlist(self, stationFile):
        ''' If a playlist backup file exists (.txt file), try to
            recover it (rename it to .csv)

            Return:
                -1: playlist recovered
                 0: no back up file found
                 1: remove (empty) csv file failed
                 2: rename txt to csv failed '''
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
                    ''' remove failed '''
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Playlist recovery failed: Cannot remove CSV file')
                    return 1
            try:
                rename(backup_stationFile, stationFile)
            except:
                ''' rename failed '''
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Playlist recovery failed: Cannot rename TXT file to CSV')
                return 2
            ''' playlist recovered '''
            if logger.isEnabledFor(logging.INFO):
                logger.info('Playlist recovery successful!!!')
            return -1
        ''' no playlist back up found '''
        return 0

    def _playlist_format_changed(self):
        ''' Check if we have new or old format
            and report if format has changed

            Format type can change by editing encoding,
            deleting a non-utf-8 station etc.
        '''
        playlist_version = self.PLAYLIST_HAS_NAME_URL
        for n in self.stations:
            if n[3] != '':
                playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
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
        ''' Save a playlist
        Create a txt file and write stations in it.
        Then rename it to final target

        return    0: All ok
                 -1: Error writing file
                 -2: Error renaming file
        '''
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

        # tmp_stations = self.stations[:]
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
            with open(st_new_file, 'w', encoding='utf-8') as cfgfile:
                writter = csv.writer(cfgfile)
                for a_station in self.stations:
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
        ''' Return a 2-column if in old format,
            a 3-column row if has encoding, or
            a 4 column row if has icon too '''
        this_row = deepcopy(a_row)
        if 'image' in this_row[3]:
            this_row[3] = this_row[3] ['image']
        if self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON:
            return this_row
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING:
            return this_row[:-1]
        else:
            return this_row[:-2]

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
        '''Remove all register items from
           the end of history'''
        item = None
        while self._ps._p[-1][6]:
            item = self._ps.pop()
        return item

    def copy_playlist_history(self):
        return self._ps.copy()

    def replace_playlist_history_items(self, a_search_path, new_item):
        ''' Find a_search_path in history and replace
            the item found with new_item '''
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
        ''' Append a station to csv file

        return    0: All ok
                 -2  -  playlist not found
                 -3  -  negative number specified
                 -4  -  number not found
                 -5: Error writing file
                 -6: Error renaming file
        '''
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
                with open(st_file, 'a', encoding='utf-8') as cfgfile:
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
        ''' Appends a station to a playlist or register
        which is not opened in PyRadio.

        return    0: All ok
                 -2  -  playlist not found
                 -3  -  negative number specified
                 -4  -  number not found
                 -5: Error writing file
                 -6: Error renaming file
        '''
        if path.exists(a_playlist):
            m_station = a_station[:]
            ch = ('  ', ',')
            for a_ch in ch:
                if a_ch in m_station[0]:
                    m_station[0] = '"' + m_station[0] + '"'
                    break

            if 'image' in m_station[3]:
                m_station[3] = m_station[3]['image']
            w_str = ','.join(m_station)
            while w_str.endswith(','):
                w_str = w_str[:-1]
            try:
                with open(a_playlist, 'a', encoding='utf-8') as f:
                    f.write('\n' + w_str)
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
        ''' Insert a station in the list at index target
        It is inserted ABOVE old target (old target becomes old target + 1)'''
        # logger.error('DE target= {0}, number_of_stations = {1}'.format(target, self.number_of_stations))
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
        # logger.error('DE number_of_stations = {}'.format(self.number_of_stations))
        return True, self.number_of_stations

    def move_station(self, source, target):
        ''' Moves a station in the list from index source to index target
        It is moved ABOVE old target (old target becomes old target + 1)'''
        # logger.error('DE source = {0}, target = {1}'.format(source, target))
        # logger.error('DE number_of_stations = {}'.format(self.number_of_stations))
        if source == target or \
                source < 0 or \
                target < 0 or \
                source >= self.number_of_stations or \
                target >= self.number_of_stations or \
                self.number_of_stations == 0:
            # logger.error('DE \n\nreturning False\n\n')
            return False
        if source < target:
            step = 1
        else:
            step = 0
        d = collections.deque(self.stations)
        d.rotate(-source)
        source_item = d.popleft()
        # logger.error('DE source_item = "{}"'.format(source_item))
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
        ''' get already loaded playlist id '''
        for i, a_playlist in enumerate(self.playlists):
            if a_playlist[-1] == self.station_path:
                self.selected_playlist = i
                break
        return len(self.playlists), self.selected_playlist

    def list_playlists(self):
        num_of_playlists, selected_playlist = self.read_playlists()
        if PY3:
            console = Console()

            table = Table(show_header=True, header_style="bold magenta")
            #table.title = 'Playlist: [bold magenta]{}[/bold magenta]'.format(pyradio_config.station_title)
            table.title_justify = "left"
            table.row_styles = ['', 'plum4']
            centered_table = Align.center(table)
            table.title = 'Playlists found in "[magenta]{}[/magenta]"'.format(self.stations_dir)
            table.title_justify = "left"
            table.add_column("#", justify="right")
            table.add_column("Name")
            table.add_column("Size", justify="right")
            table.add_column("Date")
            for i, n in enumerate(self.playlists):
                table.add_row(
                    str(i+1),
                    n[0],
                    n[2],
                    n[1],
                )
            console.print(centered_table)

        else:
            print('Playlists found in "{}"'.format(self.stations_dir))
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

    def open_browser(self, url, search_return_function, message_function, cannot_delete_function):
        self._online_browser = probeBrowsers(url)(
            self,
            self.default_encoding,
            pyradio_info=self.info,
            search_return_function=search_return_function,
            message_function=message_function,
            cannot_delete_function=cannot_delete_function
        )

    def save_station_position(self, startPos, selection, playing):
        # logger.error('DE startPos = {0}, selection = {1}'.format(startPos, selection))
        self._ps.startPos = startPos
        self._ps.selection = selection
        self._ps.playing = playing
        # logger.error('DE  self._ps._p\n\n{}\n\n'.format(self._ps._p))

    def append_to_register(self, register, station):
        reg_file = path.join(self.registers_dir, 'register_' + register + '.csv')
        a_station = station[:]
        name = a_station[0].replace('"', '""')
        if ',' in name:
            a_station[0] = '"' + name + '"'
        else:
            a_station[0] = name
        while len(a_station) < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON + 2:
            a_station.append('')
        if 'image' in a_station[3]:
            a_station[3] = a_station[3]['image']
        string_to_write = ','.join(a_station) + '\n'
        with self._registers_lock:
            try:
                with open(reg_file, 'a', encoding='utf-8') as f:
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
        # logger.error('DE /// history_item = {}'.format(self._ps._p[an_item]))
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
    ''' PyRadio Config Class '''

    ''' I will get this when a player is selected
        It will be used when command line parameters are evaluated
    '''
    PLAYER_NAME = None
    command_line_params_not_ready = None

    fallback_theme = ''
    use_themes = True
    terminal_is_blacklisted = False
    no_themes_notification_shown = False
    no_themes_from_command_line = False

    theme_not_supported = False
    theme_has_error = False
    theme_download_failed = False
    theme_not_supported_notification_shown = False

    log_titles = False
    log_degub = False

    ''' Title logging '''
    _current_log_title = _current_log_station = ''
    _old_log_title = _old_log_station = ''
    _last_liked_title = ''
    _current_notification_message = ''
    _notification_command = None

    show_recording_start_message = True

    ''' True if lock file exists '''
    locked = False

    _distro = 'None'
    opts = collections.OrderedDict()
    opts['general_title'] = ['General Options', '']
    opts['player'] = ['Player: ', '']
    opts['open_last_playlist'] = ['Open last playlist: ', False]
    opts['default_playlist'] = ['Def. playlist: ', 'stations']
    opts['default_station'] = ['Def. station: ', 'False']
    opts['default_encoding'] = ['Def. encoding: ', 'utf-8']
    opts['enable_mouse'] = ['Enable mouse support: ', False]
    opts['enable_notifications'] = ['Enable notifications: ', '-1']
    opts['use_station_icon'] = ['    Use station icon: ', True]
    opts['conn_title'] = ['Connection Options: ', '']
    opts['connection_timeout'] = ['Connection timeout: ', '10']
    opts['force_http'] = ['Force http connections: ', False]
    opts['theme_title'] = ['Theme Options', '']
    opts['theme'] = ['Theme: ', 'dark']
    opts['use_transparency'] = ['Use transparency: ', False]
    opts['calculated_color_factor'] = ['Calculated color: ', '0']
    opts['playlist_manngement_title'] = ['Playlist Management Options', '']
    opts['confirm_station_deletion'] = ['Confirm station deletion: ', True]
    opts['confirm_playlist_reload'] = ['Confirm playlist reload: ', True]
    opts['auto_save_playlist'] = ['Auto save playlist: ', False]
    opts['remote'] = ['Remote Control Server', '']
    opts['remote_control_server_ip'] = ['Server IP: ', 'localhost']
    opts['remote_control_server_port'] = ['Server Port: ', '9998']
    opts['remote_control_server_auto_start'] = ['Auto-start Server: ', False]
    opts['online_header'] = ['Online services', '']
    opts['radiobrowser'] = ['RadioBrowser', '-']
    opts['requested_player'] = ['', '']
    opts['dirty_config'] = ['', False]

    '''
    Keep several config options when no themes mode is enabled
    '''
    bck_opts = {}

    if platform == 'win32':
        th_path = path.join(getenv('APPDATA'), 'pyradio', 'themes', 'auto.pyradio-themes')
    else:
        th_path = path.join(getenv('HOME', '~'), ',config', 'pyradio', 'themes', 'auto.pyradio-themes')
    opts['auto_update_theme'] = ['',  False]

    original_mousemask = (0, 0)

    ''' parameters used by the program
        may get modified by "Z" command
        but will not be saved to file
    '''
    params = {
        'mpv': [1, 'profile:pyradio'],
        'mplayer': [1, 'profile:pyradio'],
        'vlc': [1, 'Do not use any extra player parameters']
    }
    ''' parameters read from config file
        can only be modified from config window
    '''
    saved_params = deepcopy(params)

    params_changed = False

    ''' number of user specified (-pp) extra
        player parameter parameter id
    '''
    user_param_id = 0

    PROGRAM_UPDATE = False
    current_pyradio_version = None

    ''' Windows manage players trigger '''
    WIN_MANAGE_PLAYERS = False

    ''' Windows print EXE location trigger '''
    WIN_PRINT_PATHS = False

    ''' Windows Uninstall trigger '''
    WIN_UNINSTALL = False


    internal_themes = (
        'dark', 'light', 'dark_16_colors',
        'light_16_colors', 'black_on_white', 'bow',
        'white_on_black', 'wob'
    )

    use_calculated_colors = False
    has_border_background  = False

    start_colors_at = 0

    def __init__(self, user_config_dir=None):
        self.backup_player_params = None
        self._profile_name = 'pyradio'
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
        self.active_transparency = False
        self._distro = 'None'

        if self.params_changed:
            self.dirty_config = True
        else:
            self.dirty_config = False
        ''' True if player changed by config window '''
        self.player_changed = False
        ''' [ old player, new player ] '''
        self.player_values = []

        self._session_lock_file = ''
        self._get_lock_file()

        PyRadioStations.__init__(self, user_config_dir=user_config_dir)

        self._check_config_file(self.stations_dir)
        self.config_file = path.join(self.stations_dir, 'config')

        self.force_to_remove_lock_file = False
        self.titles_log = PyRadioLog(self)
        #self.titles_log = PyRadioLog(self.stations_dir)

        ''' auto update programs
            Currently, base16 only
        '''
        self.base16_themes = PyRadioBase16Themes(self)
        self.pywal_themes = PyRadioPyWalThemes(self)
        self.theme_sh_themes = PyRadioThemesShThemes(self)
        self.auto_update_frameworks = ( self.base16_themes, self.pywal_themes, self.theme_sh_themes)

        self._read_notification_command()

    @property
    def open_last_playlist(self):
        return self.opts['open_last_playlist'][1]

    @open_last_playlist.setter
    def open_last_playlist(self, val):
        old_val = self.opts['open_last_playlist'][1]
        self.opts['open_last_playlist'][1] = val
        if old_val != val:
            self.dirty_config = True

    @property
    def distro(self):
        return self._distro

    @distro.setter
    def distro(self, val):
        raise ValueError('parameter is read only')

    @property
    def profile_name(self):
        return self._profile_name

    @profile_name.setter
    def profile_name(self, val):
        raise ValueError('parameter is read only')

    @property
    def command_line_params(self):
        self._profile_name = '' if self.PLAYER_NAME == 'vlc' else 'pyradio'
        the_id = self.backup_player_params[1][0]
        if the_id == 1:
            return ''
        the_string = self.backup_player_params[1][the_id]
        if the_string.startswith('profile:'):
            self.get_profile_name_from_saved_params(the_string)
            return ''
        else:
            return the_string

    @command_line_params.setter
    def command_line_params(self, val):
        self.command_line_params_not_ready = None
        if val:
            if val.startswith('vlc:profile'):
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('VLC does not support profiles')
                self.init_backup_player_params()
                return

            if self.PLAYER_NAME:
                parts = val.replace('\'', '').replace('"', '').split(':')
                if len(parts) > 1 and parts[0] in SUPPORTED_PLAYERS:
                    ''' add to params '''
                    # logger.error('DE \n\n{0}\n{1}'.format(self.saved_params, self.params))
                    to_add = ':'.join(parts[1:])
                    if to_add in self.params[parts[0]]:
                        added_id = self.params[parts[0]].index(to_add)
                    else:
                        self.params[parts[0]].append(to_add)
                        added_id = len(self.params[parts[0]]) - 1
                    # logger.error('DE \n{0}\n{1}\n\n'.format(self.saved_params, self.params))

                    self.dirty_config = True

                    if len(parts) > 2:
                        if parts[1] == 'profile':
                            ''' Custom profile for player '''
                            self.command_line_params_not_ready = val
                            self.set_profile_from_command_line()

                ''' change second backup params item to point to this new item
                    if the parameter belongs to the player pyradio currently uses
                '''
                if parts[0] == self.PLAYER_NAME:
                    self.init_backup_player_params()
                    self.backup_player_params[1][0] = added_id
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Setting active parameters: "{}"'.format(self.backup_player_params[1]))
            else:
                ''' Since we don't know which player we use yet
                    we do not know if this profile has to be
                    applied. So set evaluate for later...
                '''
                self.command_line_params_not_ready = val

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
    def enable_mouse(self):
        return self.opts['enable_mouse'][1]

    @enable_mouse.setter
    def enable_mouse(self, val):
        self.opts['enable_mouse'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def enable_notifications(self):
        return self.opts['enable_notifications'][1]

    @enable_notifications.setter
    def enable_notifications(self, val):
        self.opts['enable_notifications'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def use_station_icon(self):
        return self.opts['use_station_icon'][1]

    @use_station_icon.setter
    def use_station_icon(self, val):
        self.opts['use_station_icon'][1] = val
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
    def calculated_color_factor(self):
        return float(self.opts['calculated_color_factor'][1])

    @calculated_color_factor.setter
    def calculated_color_factor(self, value):
        try:
            test = float(str(value))
            self.opts['calculated_color_factor'][1] = str(value)
        except (ValueError, TypeError, NameError):
            self.opts['calculated_color_factor'][1] = '0'
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
        ''' connection timeout as string '''
        return self.opts['connection_timeout'][1]

    @connection_timeout.setter
    def connection_timeout(self, val):
        self.opts['connection_timeout'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def connection_timeout_int(self):
        ''' connection timeout as integer
            if < 5 or > 60, set to 10
            On error set to 10
            Read only
        '''
        try:
            ret = int(self.opts['connection_timeout'][1])
            if ret != 0:
                if not 5 <= ret <= 60:
                    ret = 10
        except ValueError:
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
        if val.startswith('*'):
            self.opts['theme'][1] = val[1:]
            self.opts['auto_update_theme'][1] = True
        else:
            self.opts['theme'][1] = val
            self.opts['auto_update_theme'][1] = False
        self.opts['dirty_config'][1] = True

    @property
    def theme_path(self):
        return path.join(self.stations_dir, 'themes', self.opts['theme'][1] + '.pyradio-theme')

    @property
    def auto_update_theme(self):
        return self.opts['auto_update_theme'][1]

    @auto_update_theme.setter
    def auto_update_theme(self, val):
        self.opts['auto_update_theme'][1] = val
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

    @property
    def system_themes(self):
        if PY3:
            return tuple(sorted([path.basename(x).replace('.pyradio-theme', '') for x in glob.glob(path.join(path.dirname(__file__), 'themes', '*.pyradio-theme'), recursive = False)]))
        else:
            return tuple(sorted([path.basename(x).replace('.pyradio-theme', '') for x in glob.glob(path.join(path.dirname(__file__), 'themes', '*.pyradio-theme'))]))

    def is_project_theme(self, a_theme_name):
        ''' Check if a theme name is in auto_update_frameworks
            If it is, return
                classe's instance, the index in THEME
            Else, return
                None, -1
        '''
        for n in self.auto_update_frameworks:
            if a_theme_name in n.THEME:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Checking theme: ' + a_theme_name)
                return n, n.THEME.index(a_theme_name)
        return None, -1

    @property
    def remote_control_server_ip(self):
        return self.opts['remote_control_server_ip'][1]

    @property
    def remote_control_server_port(self):
        return self.opts['remote_control_server_port'][1]

    @property
    def remote_control_server_auto_start(self):
        return self.opts['remote_control_server_auto_start'][1]

    def is_default_file(self, a_theme_name):
        for n in self.auto_update_frameworks:
            if a_theme_name == n.default_filename_only:
                return True
        return False

    def _construct_playlist_path(self, a_playlist):
        return path.join(self.stations_dir, a_playlist + '.csv')

    def _read_notification_command(self):
        self._notification_command = []
        if platform == 'win32':
            return
        ns = (
            path.join(self.stations_dir, 'notification'),
            path.join(path.dirname(__file__), 'notification')
        )
        for i, n in enumerate(ns):
            if path.exists(n):
                try:
                    with open(n, 'r', encoding='utf-8') as f:
                        for line in f:
                            self._notification_command.append(line.replace('\n', '').strip())
                except:
                    self._notification_command = []
            if i == 0 and self._notification_command:
                break

        if self._notification_command == []:
            # set default commands
            if platform.lower().startswith('darwin'):
                self._notification_command = [
                    'osascript', '-e',
                    'display notification "MSG" with title "TITLE"'
                ]
            else:
                self._notification_command = [
                    'notify-send', '-i',
                    'ICON', 'TITLE', 'MSG'
                ]

    def get_pyradio_version(self):
        ''' reads pyradio version from installed files

            Retrurns
                self.info
                    The string to display at left top corner of main window
                self.get_current_pyradio_version
                    The version to use when checking for updates
        '''
        ret = None
        self.info = " PyRadio {0} ".format(version)
        ''' git_description can be set at build time
            if so, revision will be shown along with the version
        '''
        # if revision is not 0
        git_description = ''
        if git_description:
            git_info = git_description.split('-')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('versrion = {0} - git_info = {1}'.format(version, git_info))
            if git_info[0] == version:
                if git_description.endswith('-git') or \
                        git_description.endswith('-sng') or \
                        git_description.endswith('-dev'):
                    if 'rdev' in git_description:
                        ''' failed to get it on linux '''
                        git_description = 'PyRadio-git'
                    self.info = ' ' + git_description
                    ret = self.info + " (development version)"
                else:
                    try:
                        if git_info[1] == '0':
                            self.info = " PyRadio {}".format(git_info[0])
                            ret = 'PyRadio built from git master branch'
                        else:
                            self.info = " PyRadio {0}-r{1}".format(git_info[0], git_info[1])
                            ret = "RyRadio built from git: https://github.com/coderholic/pyradio/commit/{0} (rev. {1})".format(git_info[-1], git_info[1])
                    except:
                        pass
            else:
                self.info = " PyRadio {}".format(version)
                ret = ''
        self.current_pyradio_version = self.info.replace(' PyRadio ', '').replace(' ', '')
        # if self._distro != 'None':
        #     self.info += '({})'.format(self._distro)
        return ret

    def setup_mouse(self):
        if self.enable_mouse:
            curses.mousemask(curses.ALL_MOUSE_EVENTS
                             | curses.REPORT_MOUSE_POSITION)
            #curses.mouseinterval(0)

    def open_config_dir(self):
        if system().lower() == 'windows':
            startfile(self.stations_dir)
        elif system().lower() == 'darwin':
            Popen(['open', self.stations_dir])
        else:
            try:
                Popen(
                    ['xdg-open', self.stations_dir],
                    stderr=DEVNULL,
                    stdout=DEVNULL
                )
            except:
                Popen(['xdg-open', self.stations_dir])

    def reset_profile_name(self):
        self._profile_name = 'pyradio'

    def get_profile_name_from_saved_params(self, a_string=None):
        ''' populate command_line_params_not_ready because this
            is what self.set_profile_from_command_line() reads
        '''
        if a_string:
            self.command_line_params_not_ready = self.PLAYER_NAME + ':' + a_string
        else:
            self.command_line_params_not_ready = self.PLAYER_NAME + ':' + self.params[self.PLAYER_NAME][self.params[self.PLAYER_NAME][0]]
        self.set_profile_from_command_line()

    def set_profile_from_command_line(self):
        parts = self.command_line_params_not_ready.split(':')
        self.command_line_params_not_ready = None
        if self.PLAYER_NAME == 'vlc':
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC does not support profiles...')
            return
        if parts[0] == self.PLAYER_NAME:
            the_string = ':'.join(parts[2:]) if len(parts) > 1 else None

            if the_string:
                self._profile_name = the_string
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Setting profile to "[{}]"'.format(self._profile_name))
            else:
                self._profile_name = 'pyradio'
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Invalid profile... Falling back to "[pyradio]"')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Profile for other player ({0} -> {1})'.format(parts[0], self.PLAYER_NAME))

    def _get_lock_file(self):
        ''' Populate self._session_lock_file
            If it exists, locked becomes True
            Otherwise, the file is created
        '''
        if path.exists('/run/user'):
            from os import geteuid
            self._session_lock_file = path.join('/run/user', str(geteuid()), 'pyradio.lock')
            ''' remove old style session lock file (if it exists) '''
            if path.exists(path.join(self.stations_dir, '.lock')):
                try:
                    remove(path.join(self.stations_dir, '.lock'))
                except:
                    pass
        else:
            if platform == 'win32':
                self._session_lock_file = path.join(getenv('APPDATA'), 'pyradio', 'data', 'pyradio.lock')
            else:
                self._session_lock_file = path.join(getenv('HOME'), '.config', 'pyradio', 'data', 'pyradio.lock')
        if path.exists(self._session_lock_file):
            if platform == 'win32':
                win_lock = path.join(getenv('APPDATA'), 'pyradio', 'data', '_windows.lock')
                if path.exists(win_lock):
                    ''' pyradio lock file was probably not deleted the last
                        time Windows terminated. It should be safe to use it
                    '''
                    try:
                        remove(win_lock)
                    except:
                        pass
                else:
                    self.locked = True
            else:
                self.locked = True
        else:
            try:
                with open(self._session_lock_file, 'w', encoding='utf-8') as f:
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

    def change_to_no_theme_mode(self, show_colors_cannot_change):
        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(8, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(10, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(11, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(12, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(13, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(14, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(15, curses.COLOR_WHITE, curses.COLOR_BLACK)
        ''' Theme values backup '''
        self.bck_opts['use_transparency'] = self.opts['use_transparency'][1]
        self.bck_opts['theme'] = self.opts['theme'][1]
        self.bck_opts['auto_update_theme'] = self.opts['auto_update_theme'][1]
        self.bck_opts['calculated_color_factor'] = self.opts['calculated_color_factor'][1]
        ''' No theme values '''
        self.opts['use_transparency'][1] = False
        self.opts['theme'][1] = 'dark'
        self.opts['auto_update_theme'][1] = False
        self.opts['calculated_color_factor'][1] = "0"
        self._show_colors_cannot_change = show_colors_cannot_change
        logger.error('bck_opts = {}'.format(self.bck_opts))

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
            if is_rasberrypi():
                self._convert_config_for_rasberrypi(package_config_file, user_config_file)
            else:
                copyfile(package_config_file, user_config_file)

    def _convert_config_for_rasberrypi(self, package_config_file, user_config_file):
        lines = []
        with open(package_config_file, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f]
        for i in range(len(lines)):
            if lines[i].startswith('player'):
                lines[i] = 'player = mplayer,vlc,mpv'
        with open(user_config_file, 'w', encoding='utf-8') as f:
            f.write('\n'.join(lines) + '\n')

    def _validate_remote_control_server_ip(self, val):
        '''
        validate a config remote_control_server string
        Return
            input    if valid
            default  if invalid
        '''
        hosts = ('localhost', 'LAN', 'lan')
        default_remote_control_server = 'localhost:9998'
        if ':' in val:
            sp = val.split(':')
            ''' is server valid '''
            if sp[0].startswith('*'):
                sp[0] = sp[0][1:]
                auto = True
            x = [r for r in hosts if r == sp[0]]
            if not x:
                return default_remote_control_server
            ''' server is valid, is port valid? '''
            try:
                x = int(sp[1])
            except (ValueError, IndexError):
                return default_remote_control_server
        else:
            return default_remote_control_server
        return val

    def read_config(self):
        lines = []
        try:
            with open(self.config_file, 'r', encoding='utf-8') as cfgfile:
                lines = [line.strip() for line in cfgfile if line.strip() and not line.startswith('#') ]

        except:
            self.__dirty_config = False
            return -1
        self.params = {
            'mpv': [1, 'profile:pyradio'],
            'mplayer': [1, 'profile:pyradio'],
            'vlc': [1, 'Do not use any extra player parameters']
        }
        for line in lines:
            sp = line.replace(' ', '').split('=')
            if len(sp) < 2:
                return -2
            if sp[1] == '':
                return -2
            if sp[0] == 'show_no_themes_message':
                self.show_no_themes_message = True
                st = sp[1].strip()
                if st.lower() == 'false':
                    self.show_no_themes_message = False
            elif sp[0] == 'show_recording_message':
                self.show_recording_start_message = True
                st = sp[1].strip()
                if st.lower() == 'false':
                    self.show_recording_start_message = False
            elif sp[0] == 'player':
                self.opts['player'][1] = sp[1].lower().strip()
                # if sys.platform.startswith('win'):
                #     self.opts['player'][1] = self.opts['player'][1].replace('mpv,', '')
            elif sp[0] == 'connection_timeout':
                self.opts['connection_timeout'][1] = sp[1].strip()
                ''' check integer number and set to 10 if error
                    x is a dummy parameter
                '''
                x = self.connection_timeout_int
            elif sp[0] == 'default_encoding':
                self.opts['default_encoding'][1] = sp[1].strip()
            elif sp[0] == 'theme':
                self.opts['theme'][1] = sp[1].strip()
                if self.opts['theme'][1].startswith('*'):
                    self.opts['theme'][1] = self.opts['theme'][1][1:]
                    self.opts['auto_update_theme'][1] = True
                else:
                    self.opts['auto_update_theme'][1] = False
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
            elif sp[0] == 'open_last_playlist':
                if sp[1].lower() == 'false':
                    self.opts['open_last_playlist'][1] = False
                else:
                    self.opts['open_last_playlist'][1] = True
            elif sp[0] == 'enable_mouse':
                if sp[1].lower() == 'false':
                    self.opts['enable_mouse'][1] = False
                else:
                    self.opts['enable_mouse'][1] = True
            elif sp[0] == 'enable_notifications':
                self.opts['enable_notifications'][1] = sp[1]
                if sp[1] not in ('0', '-1'):
                    try:
                        t = int(int(sp[1]) / 30)
                        self.opts['enable_notifications'][1] = str(t * 30)
                    except (ValueError, TypeError):
                        self.opts['enable_notifications'][1] = '-1'
            elif sp[0] == 'use_station_icon':
                if sp[1].lower() == 'false':
                    self.opts['use_station_icon'][1] = False
                else:
                    self.opts['use_station_icon'][1] = True
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
            elif sp[0] == 'calculated_color_factor':
                try:
                    t = round(float(sp[1]), 2)
                    s_t = str(t)[:4]
                    if s_t == '0.0':
                        s_t = '0'
                    self.opts['calculated_color_factor'][1] = s_t
                except (ValueError, TypeError):
                    self.opts['calculated_color_factor'][1] = '0'
                self.use_calculated_colors = False if self.opts['calculated_color_factor'][1] == '0' else True
            elif sp[0] == 'force_http':
                if sp[1].lower() == 'true':
                    self.opts['force_http'][1] = True
                else:
                    self.opts['force_http'][1] = False
            elif sp[0] in ('mpv_parameter',
                           'mplayer_parameter',
                           'vlc_parameter'):
                self._config_to_params(sp)
            elif sp[0] == 'remote_control_server_ip':
                hosts = ('localhost', 'LAN', 'lan')
                sp[1] = sp[1].strip()
                x = [r for r in hosts if r == sp[1]]
                if x:
                    self.opts['remote_control_server_ip'][1] = x[0]
                else:
                    self.opts['remote_control_server_ip'][1] = 'localhost'
            elif sp[0] == 'remote_control_server_port':
                try:
                     x = int(sp[1])
                except (ValueError, TypeError):
                    x = 9998
                if 1025 <= x <= 65535:
                    self.opts['remote_control_server_port'][1] = str(x)
                else:
                    self.opts['remote_control_server_port'][1] = '9998'
            elif sp[0] == 'remote_control_server_auto_start':
                if sp[1].lower() == 'true':
                    self.opts['remote_control_server_auto_start'][1] = True
                else:
                    self.opts['remote_control_server_auto_start'][1] = False
            elif sp[0] == 'distro':
                ''' mark as dirty to force saving config to remove setting '''
                # self.dirty_config = True
                self._distro = sp[1].strip()

        ''' read distro from package config file '''
        package_config_file = path.join(path.dirname(__file__), 'config')
        try:
            with open(package_config_file, 'r', encoding='utf-8') as pkg_config:
                lines = [line.strip() for line in pkg_config if line.strip() and not line.startswith('#') ]
            for line in lines:
                sp = line.split('=')
                sp[0] = sp[0].strip()
                sp[1] = sp[1].strip()
                if sp[0] == 'distro':
                    self._distro = sp[1].strip()
                    if not self._distro:
                        self._distro = 'None'
        except:
            self._distro = 'None'

        ''' make sure extra params have only up to 10 items each
            (well, actually 11 items, since the first one is the
            index to the default string in the list)
        '''
        if self.params:
            for n in self.params.keys():
                self.params[n] = self.params[n][:12]

        self.opts['dirty_config'][1] = False
        self.saved_params = deepcopy(self.params)

        ''' check if default playlist exists '''
        if self.opts['default_playlist'][1] != 'stations':
            ch = path.join(self.stations_dir, self.opts['default_playlist'][1] + '.csv')
            if not path.exists(ch):
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Default playlist "({}") does not exist; reverting to "stations"'.format(self.opts['default_station'][1]))
                self.opts['default_playlist'][1] = 'stations'
                self.opts['default_station'][1] = 'False'
        # for n in self.opts.keys():
        #     logger.error('  {0}: {1} '.format(n, self.opts[n]))
        # for n in self.opts.keys():
        #     logger.error('  {0}: {1} '.format(n, self.opts[n]))
        return 0

    def get_last_playlist(self):
        ''' read last opened playlist
                reads:     ~/pyradio/last_playlist
                returns:   last playlist name
                sets:      self._last_opened_playlist_name (if successful)

            CAUTION:
                To be used by main.py only
        '''
        playlist = ''
        lps = (
            path.join(self.data_dir, 'last-playlist'),
            path.join(self.stations_dir, 'last_playlist'),
            path.join(self.stations_dir, 'last-playlist')
        )
        for lp in lps:
            # print('lp = "{}"'.format(lp))
            if path.exists(lp):
                with open(lp, 'r', encoding='utf-8') as f:
                    for row in csv.reader(filter(lambda row: row[0]!='#', f), skipinitialspace=True):
                        if not row:
                            continue
                        self.last_playlist_to_open = row

                if len(self.last_playlist_to_open) == 0:
                    self.last_playlist_to_open = []
                    return None

                if len(self.last_playlist_to_open) > 3:
                    self.last_playlist_to_open = self.last_playlist_to_open[:3]

                while len(self.last_playlist_to_open) < 3:
                    self.last_playlist_to_open.append(0)

                for i in range(-1, -3, -1):
                    try:
                        x = int(self.last_playlist_to_open[i])
                    except ValueError:
                        x = -1 if i == -1 else 0
                    self.last_playlist_to_open[i] = x


                playlist = self.last_playlist_to_open[0]
                if playlist != '':
                    if path.exists(path.join(self.stations_dir, playlist + '.csv')):
                        print('=> Opening last playlist: "' + playlist + '"')
                        self._last_opened_playlist_name = playlist
                        return playlist
                    else:
                        print('=> Last playlist does not exist: "' + playlist + '"')
                else:
                    print('=> Last playlist name is invalid!')
                try:
                    remove(lp)
                except:
                    pass
                break
        return None

    def init_backup_player_params(self):
        # logger.error('DE ====  init_backup_player_params ====')
        if self.params:
            self.backup_player_params = [self.params[self.PLAYER_NAME][:],
                                         self.params[self.PLAYER_NAME][:]]
            # logger.error('DE backup_player_params = {}'.format(self.backup_player_params))

    def set_backup_params_from_session(self):
        # logger.error('DE ==== set_backup_params_from_session  ====')
        # logger.error('DE backup params before = {}'.format(self.backup_player_params))
        self.backup_player_params[1] = self.params[self.PLAYER_NAME][:]
        # logger.error('DE backup params  after = {}'.format(self.backup_player_params))

    def get_player_params_from_backup(self, param_type=0):
        # logger.error('DE ==== get_player_params_from_backup  ====')
        if param_type in (0, 'config'):
            the_param_type = 0
        elif param_type in (1, 'session'):
            the_param_type = 1
        # logger.error('DE param_type = "{0}", {1}'.format(param_type, the_param_type))
        # logger.error('DE params before = {}'.format(self.params))
        self.params[self.PLAYER_NAME] = self.backup_player_params[the_param_type][:]
        # logger.error('DE params  after = {}'.format(self.params))
        # logger.error('DE backup_player_params = {}'.format(self.backup_player_params))

    def _config_to_params(self, a_param):
        player = a_param[0].split('_')[0]
        default = False
        if a_param[1].startswith('*'):
            default = True
            a_param[1] = a_param[1][1:]
        self.params[player].append('='.join(a_param[1:]))
        if default:
            self.params[player][0] = len(self.params[player]) - 1

    def check_parameters(self):
        ''' Config parameters check '''
        # logger.error('DE check_params: params = {}'.format(self.params))

        for a_key in self.saved_params.keys():
            if self.saved_params[a_key] != self.params[a_key]:
                self.dirty_config = True
                return True
        return False

    def save_config(self, from_command_line=False):
        ''' Save config file

            Creates config.restore (back up file)
            Returns:
                -1: Error saving config
                 0: Config saved successfully
                 1: Config not saved (not modified)
                 TODO: 2: Config not saved (session locked) '''
        if self.locked:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (session locked)')
            return 1

        ''' Check if parameters are changed
            Do it this way (not using is_ditry) to capture
            parameter changes due to 'Z' also
        '''
        # logger.error('DE save_conifg: saved params = {}'.format(self.saved_params))
        if not from_command_line:
            self.get_player_params_from_backup()
        if self.check_parameters():
            self.saved_params = deepcopy(self.params)
        if not from_command_line and \
                logger.isEnabledFor(logging.DEBUG):
            logger.debug('saved params = {}'.format(self.saved_params))

        if not self.opts['dirty_config'][1]:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
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

# Open last playlist
# If this option is enabled, the last opened playlist will be opened
# the next time PyRadio is opened. This option will take precedence
# over the "Def. playlist" option and the "-s" commans line parameter.
# Default value: False
open_last_playlist = {1}

# Default playlist
# This is the playlist to open if none is specified
# You can specify full path to CSV file, or if the playlist is in the
# config directory, playlist name (filename without extension) or
# playlist number (as reported by -ls command line option)
# Default value: stations
default_playlist = {2}

# Default station
# This is the equivalent to the -p , --play command line parameter
# The station number within the default playlist to play
# Value is 1..number of stations, "-1" or "False" means no auto play
# "0" or "Random" means play a random station
# Default value: False
default_station = {3}

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
default_encoding = {4}

# Enable mouse
# If this options is enabled, the mouse can be used to scroll the
# playlist, start, stop and mute the player, adjust its volume etc.
# Mouse integration is highly terminal dependent, that's why it
# is disabled by default.
#
# Default value: False
enable_mouse = {5}

# Desktop notifications
# If this option is enabled, a Desktop Notification will be
# displayed using the notification daemon / service.
# If enabled but no notification is displayed, please refer to
# https://github.com/coderholic/pyradio/desktop-notification.md
# Valid values are:
#    -1: disabled
#     0: enabled (no repetition)
#     x: enabled and repeat every x seconds
#
# Default value: -1
enable_notifications = {6}

# Station icon
# Radio Browser will provide an icon for some of its stations.
# This icon can be downloaded and used in Desktop Notifications,
# if this option is True.
#
# Default value: True
use_station_icon = {7}

# Connection timeout
# PyRadio will wait for this number of seconds to get a station/server
# message indicating that playback has actually started.
# If this does not happen (within this number of seconds after the
# connection is initiated), PyRadio will consider the station
# unreachable, and display the "Failed to connect to: [station]"
# message.
#
# Valid values: 5 - 60, 0 disables check
# Default value: 10
connection_timeout = {8}

# Force http connections
# Most radio stations use plain old http protocol to broadcast, but
# some of them use https. If this is enabled,  all connections will
# use http; results depend on the combination of station/player.
#
# Valid values: True, true, False, false
# Default value: False
force_http = {9}

# Default theme
# Hardcooded themes:
#   dark (default) (8 colors)
#   light (8 colors)
#   dark_16_colors (16 colors dark theme alternative)
#   light_16_colors (16 colors light theme alternative)
#   black_on_white (bow) (256 colors)
#   white_on_black (wob) (256 colors)
# If theme is watched for changes, prepend its name
# with an asterisk (i.e. '*my_theme')
# This is applicable for user themes only!
# Default value = 'dark'
theme = {10}

# Transparency setting
# If False, theme colors will be used.
# If True and a compositor is running, the stations' window
# background will be transparent. If True and a compositor is
# not running, the terminal's background color will be used.
# Valid values: True, true, False, false
# Default value: False
use_transparency = {11}

# Calculated color factor
# This is to produce Secondary Windows background color
# A value of 0 dissables it, otherwise it is the factor
# to change (lighten or darken) the base color.
# For more info, please refer to
# https://github.com/coderholic/pyradio#secondary-windows-background
# Valid values: 0-0.2
# Default value: 0
calculated_color_factor = {12}

# Playlist management
#
# Specify whether you will be asked to confirm
# every station deletion action
# Valid values: True, true, False, false
# Default value: True
confirm_station_deletion = {13}

# Specify whether you will be asked to confirm
# playlist reloading, when the playlist has not
# been modified within PyRadio
# Valid values: True, true, False, false
# Default value: True
confirm_playlist_reload = {14}

# Specify whether you will be asked to save a
# modified playlist whenever it needs saving
# Valid values: True, true, False, false
# Default value: False
auto_save_playlist = {15}

# When PyRadio determines that a restricted
# terminal is used, it will display a message
# every time it is lounched. To disable this
# message, change the value to False.
# Default value: True
show_no_themes_message = {16}

# When recording is turned on, a message will
# be displayed if this option is True (default)
#
show_recording_message = {17}

# Remote Control server
# A simple http server that can accept remote
# connections and pass commands to PyRadio
#
# Valid values:
#   remote_control_server_ip: localhost, LAN, lan
#   remote_control_server_port: 1025-65535
#
# Default value: localhost:9998
#                no auto start
remote_control_server_ip = {18}
remote_control_server_port = {19}
remote_control_server_auto_start = {20}

'''
        copyfile(self.config_file, self.config_file + '.restore')
        if self.opts['default_station'][1] is None:
            self.opts['default_station'][1] = '-1'

        if self.use_themes:
            theme = self.opts['theme'][1] if not self.opts['auto_update_theme'][1] else '*' + self.opts['theme'][1]
            trnsp = self.opts['use_transparency'][1]
            calcf = self.opts['calculated_color_factor'][1]
        else:
            theme = self.bck_opts['theme'] if not self.bck_opts['auto_update_theme'] else '*' + self.bck_opts['theme']
            trnsp = self.bck_opts['use_transparency']
            calcf = self.bck_opts['calculated_color_factor']

        try:
            with open(self.config_file, 'w', encoding='utf-8') as cfgfile:
                cfgfile.write(txt.format(
                    self.opts['player'][1],
                    self.opts['open_last_playlist'][1],
                    self.opts['default_playlist'][1],
                    self.opts['default_station'][1],
                    self.opts['default_encoding'][1],
                    self.opts['enable_mouse'][1],
                    self.opts['enable_notifications'][1],
                    self.opts['use_station_icon'][1],
                    self.opts['connection_timeout'][1],
                    self.opts['force_http'][1],
                    theme,
                    trnsp,
                    calcf,
                    self.opts['confirm_station_deletion'][1],
                    self.opts['confirm_playlist_reload'][1],
                    self.opts['auto_save_playlist'][1],
                    self.show_no_themes_message,
                    self.show_recording_start_message,
                    self.remote_control_server_ip,
                    self.remote_control_server_port,
                    self.remote_control_server_auto_start
                ))

                ''' write extra player parameters to file '''
                first_param = True
                for a_set in self.saved_params.keys():
                    if len(self.saved_params[a_set]) > 2:
                        if first_param:
                            txt = '''# Player Extra parameters section
#
# Each supported player can have up to 9 entries in this section,
# specifying extra parameters to be used when it is executed.
# The format is "[player name]_parameter=[parameters]"
# The parameter part can either be:
# 1) "profile:[name of profile]" or 2) [prayer parameters]
# When (1) is used, the [name of profile] should exist in the
# player's config file (otherwise it will be created).
# The use of profiles will be silently ignored for VLC, which
# does not support profiles.
# When (2) is used, the parameters are added to those specified
# at PyRadio's default profile (again not for VLC).
# An asterisk will indicate the parameter to be used as default.

# {} extra parameters\n'''
                            first_param = False

                        else:
                            txt = '''\n# {} extra parameters\n'''
                        cfgfile.write(txt.format(a_set))
                        for i, a_param in enumerate(self.saved_params[a_set]):
                            if i == 0:
                                default = a_param
                            elif i > 1:
                                txt = '*' + a_param if i == default else a_param
                                cfgfile.write('{}\n'.format(a_set + '_parameter=' + txt))

        except:
            if not from_command_line and \
                    logger.isEnabledFor(logging.ERROR):
                logger.error('Error saving config')
            return -1
        # if self.open_last_playlist:
        #     self.save_last_playlist()
        try:
            remove(self.config_file + '.restore')
        except:
            pass
        if logger.isEnabledFor(logging.INFO):
            logger.info('Config saved')
        self.dirty_config = False
        self.params_changed = False
        return 0

    def read_playlist_file(
            self, stationFile='',
            is_last_playlist=False,
            is_register=False
    ):
        if stationFile.strip() == '':
            stationFile = self.default_playlist
        return super(PyRadioConfig, self).read_playlist_file(
            stationFile=stationFile,
            is_last_playlist=is_last_playlist,
            is_register=is_register)

    def can_like_a_station(self):
        return True if self._current_log_title != self._last_liked_title else False

    def is_blacklisted_terminal(self):
        self.terminal_is_blacklisted = False
        if HAS_PSUTIL:
            pid = getpid()
            try:
                parents = psutil.Process(pid).parents()
            except AttributeError:
                parents = self._get_parents(pid)

            logger.error('\n\n{}\n\n'.format(parents))
            if parents is not None:
                '''
                read ~/.config/pyradio/no-themes-terminals
                '''
                term_file = path.join(self.stations_dir, 'no-themes-terminals')
                user_terminal = []
                if path.exists(term_file):
                    try:
                        with open(term_file, 'r', encoding='utf-8') as term:
                            user_terminals = term.read().splitlines()
                    except:
                        pass
                    logger.error('\n\nuser terminals: {}\n\n'.format(user_terminals))
                    if user_terminals:
                        if parent.name() in user_terminals:
                            '''
                            set this to not display notification because
                            user has customized no-themes-terminals
                            '''
                            self.no_themes_from_command_line = True
                            self.terminal_is_blacklisted = True
                            return True

                ''' blacklisted terminals '''
                terminals = [
                    'konsole',
                    'qterminal',
                    'terminology',
                    'deepin-terminal',
                    'pangoterm'
                ]
                for parent in parents:
                    if parent.name() in terminals:
                        ''' auto detected terminal; display notification '''
                        self.terminal_is_blacklisted = True
                        return True
        return False

    def _get_parents(self, pid):
        '''
        get pid parents, when psutil.Process.parents() does not exist
        '''
        procs = []
        out = []
        for proc in psutil.process_iter(['pid', 'ppid', 'name', 'username']):
            procs.append(proc)
            if proc.pid == pid:
                par = proc.parent()
                if par:
                    ppid = par.pid
        old_ppid = 0
        while ppid > 100 or old_ppid == ppid:
            for proc in procs:
                if proc.pid == ppid:
                    out.append(proc)
                    par = proc.parent()
                    if par:
                        old_ppid = ppid
                        ppid = par.pid
        return out


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
    def is_local_playlist(self):
        if self._p:
            return not self._p[-1][self._id['is_register']] and \
                not self._p[-1][self._id['browsing_station_service']]
        else:
            return True

    @is_local_playlist.setter
    def is_local_playlist(self, value):
        raise ValueError('parameter is read only')

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

    @property
    def last_local_playlist(self):
        for n in range(len(self._p) -1, -1, -1):
            if not self._p[n][-1] and not self._p[n][-2]:
                return self._p[n]

    @last_local_playlist.setter
    def last_local_playlist(self, value):
        raise ValueError('parameter is read only')

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
        # logger.error('DE playlist history\n{}\n'.format(self._p))

    def get_item_member(self, member, item_id=-1):
        if member in self._id.keys():
            return self._p[item_id][self._id[member]]
        else:
            raise ValueError('member "{}" does not exist'.format(member))

    def _find_history_by_id(self, a_search, it_id, start=0):
        ''' Find a history item

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
        '''
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
        ''' Find a_search_path in history and replace
            the item found with new_item '''
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


class PyRadioStationsStack(object):
    pass_first_item_func=None
    pass_last_item_func=None
    no_items_func=None
    play_from_history = False

    ''' items: list of lists
        [
            [playlist name, station name, station id],
            ...
        ]
    '''

    def __init__(
        self,
        execute_function,
        pass_first_item_function=None,
        pass_last_item_function=None,
        no_items_function=None
    ):
        self.items = []
        self.item = -1

        ######## DEBUG START
        self.items = [
            ['reversed', 'Lounge (Illinois Street Lounge - SomaFM)', 10],
            ['reversed', 'Folk (Folk Forward - SomaFM)', 17],
            ['Κέρκυρα', 'Ράδιο Επτάνησα 98,8', 11]
        ]
        self.item = 0
        self.play_from_history = True
        self.clear()
        ######## DEBUG END

        self.execute_func = execute_function
        self.pass_first_item_func = pass_first_item_function
        self.pass_last_item_func = pass_last_item_function
        self.no_items_func = no_items_function

    def _show_station_history_debug(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('>>> Stations history')
            if self.items:
                for n in self.items:
                    logger.debug('   {}'.format(n))
                logger.debug('   item was = {}'.format(self.item))
            else:
                logger.debug('   No items in list')
                logger.debug('   item = {}'.format(self.item))

    def add(self, a_playlist, a_station, a_station_id):
        if a_playlist and a_station:
            if a_playlist == a_station:
                return
            if self.item == -1:
                self.items.append([a_playlist, a_station, a_station_id])
                self.item = 0
                self._show_station_history_debug()
            else:
                if not a_station.startswith('register_') and \
                        (not self.play_from_history) and \
                        (not a_playlist.startswith('register_')) and \
                        (self.items[-1][0] != a_playlist \
                        or self.items[-1][1] != a_station) and \
                        (self.items[self.item][0] != a_playlist \
                         or self.items[self.item][1] != a_station):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Adding station history item...')
                    self.items.append([a_playlist, a_station, a_station_id])
                    self.item = len(self.items) - 1
                    self._show_station_history_debug()
            self.play_from_history = False

    def clear(self):
        self.items = []
        self.item = -1
        self.play_from_history = False

    def remove_station(self, a_station):
        for i in range(len(self.items) - 1, -1, -1):
            if self.items[i][1] == a_station:
                self.items.pop(i)
        if self.item >= len(self.items):
            self.item = len(self.items) - 1
        self._show_station_history_debug()

    def rename_station(self, playlist, orig_station, new_station):
         # logger.error('playlist = "{}"'.format(playlist))
         # logger.error('orig_station = "{}"'.format(orig_station))
         # logger.error('new_station = "{}"'.format(new_station))
         self._show_station_history_debug()
         for i in range(len(self.items) - 1, -1, -1):
             if self.items[i][0] == playlist and \
                     self.items[i][1] == orig_station:
                 logger.error('item = {}'.format(self.items[i]))
                 self.items[i][1] = new_station
                 logger.error('item = {}'.format(self.items[i]))
         self._show_station_history_debug()

    def rename_playlist(self, orig, new):
        self._show_station_history_debug()
        for i in range(0, len(self.items)):
            if self.items[i][0] == orig:
                self.items[i][0] = new
        self._show_station_history_debug()

    def _get(self):
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        return tuple(self.items[self.item])

    def play_previous(self):
        self._show_station_history_debug()
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        elif self.item == 0:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   Already on first item')
            if self.pass_first_item_func is not None:
                self.pass_first_item_func()
        else:
            self.item -= 1
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   item is  = {}'.format(self.item))
            self.execute_func(self._get(), self.play_previous)

    def play_next(self):
        self._show_station_history_debug()
        if self.item == -1:
            if self.no_items_func is not None:
                self.no_items_func()
        elif self.item == len(self.items) - 1:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   Already on last item')
            if self.pass_last_item_func is not None:
                self.pass_last_item_func()
        else:
            self.item += 1
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('   item is  = {}'.format(self.item))
            self.execute_func(self._get(), self.play_next)

    def restore_index(self, a_func):
        if a_func == self.play_next:
            self.item -= 1
        else:
            self.item += 1
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('   item restored  = {}'.format(self.item))

class PyRadioLog(object):

    PATTERN = '%(asctime)s - %(name)s:%(funcName)s():%(lineno)d - %(levelname)s: %(message)s'
    PATTERN_TITLE = '%(asctime)s | %(message)s'

    log_titles = log_debug = False

    titles_handler = debug_handler = None

    def __init__(self, pyradio_config):
        self._cnf = pyradio_config
        self._stations_dir = pyradio_config.stations_dir

    def configure_logger(self, debug=None, titles=None):
        logger = logging.getLogger('pyradio')
        logger.setLevel(logging.DEBUG)
        if debug or titles:
            if debug and not self.log_debug:
                # Handler
                self.debug_handler = logging.FileHandler(path.join(path.expanduser('~'), 'pyradio.log'))
                self.debug_handler.setLevel(logging.DEBUG)

                # create formatter
                formatter = logging.Formatter(self.PATTERN)

                # add formatter to ch
                self.debug_handler.setFormatter(formatter)

                # add ch to logger
                #l = logging.getLogger()
                logger.addHandler(self.debug_handler)

                # inform config
                self.log_degub = True

            if titles and not self.log_titles:
                self.titles_handler = logging.handlers.RotatingFileHandler(
                    path.join(
                        self._stations_dir,
                        'pyradio-titles.log'),
                    maxBytes=50000,
                    backupCount=5)
                self.titles_handler.setFormatter(logging.Formatter(
                    fmt=self.PATTERN_TITLE,
                    datefmt='%b %d (%a) %H:%M')
                )
                self.titles_handler.setLevel(logging.CRITICAL)
                #l = logging.getLogger()
                logger.addHandler(self.titles_handler)
                self.log_titles = True
                logger.critical('=== Logging started')

        if (not titles) and self.log_titles:
            if self.titles_handler:
                logger.critical('=== Logging stopped')
                logger.removeHandler(self.titles_handler)
                self.log_titles = False
                self.titles_handler = None

        logging.raiseExceptions = False
        logging.lastResort = None
        # logger.info('self.log_titles = {}'.format(self.log_titles))

    def tag_title(self, the_log):
        ''' tags a title

            Returns:
                0: All ok
                1: Error
                2: Already tagged
        '''
        if self._cnf.can_like_a_station():
            if logger.isEnabledFor(logging.CRITICAL):
                try:
                    the_log._write_title_to_log()
                except:
                    return 1
                return 0
        return 2

class PyRadioBase16Themes(object):

    NAME = 'Base16 Project'
    ''' theme name to be found in themes window '''
    THEME = (
        'base16-pyradio-default',
        'base16-pyradio-default-alt',
        'base16-pyradio-variation',
        'base16-pyradio-variation-alt'
    )
    ''' To be used in get_url (along with theme_id) '''
    URL_PART = (
        'default',
        'default-alt',
        'variation',
        'variation-alt'
    )
    ''' last used theme name (no "base16-", no extension) '''
    _last_used_theme = None
    '''  link to last used base16 theme '''
    _ln = path.join(getenv('HOME', '~'), '.config/base16-project/base16_shell_theme')
    ''' pyradio base16 file for auto download '''
    _default_theme_file = None
    ''' the default base16 file, without path and extension '''
    default_filename_only = 'base16-pyradio'
    ''' pyradio base16 them for download '''
    _custom_theme_file = None

    ''' working parameters'''
    ''' applied name
        to be used by download()
    '''
    theme_id = 0
    ''' applied theme filename (if autoloaed, = _default_theme_file)
        to be used by download()
    '''
    theme_file_name = _default_theme_file
    # applied theme url
    theme_url = None


    def __init__(self, config):
        self._cnf = config
        self._themes_dir = config.themes_dir
        ''' base16 autoload filename '''
        self._custom_theme_file = path.join(self._themes_dir, self.THEME[self.theme_id] + '.pyradio-theme')
        self._default_theme_file = path.join(self._themes_dir, 'base16-pyradio.pyradio-theme')

    @property
    def check_file(self):
        return self._ln

    @property
    def default_theme_path(self):
        return self._default_theme_file

    @property
    def theme_path(self):
        return self._custom_theme_file

    @property
    def can_auto_update(self):
        if platform.startswith('win'):
            ''' base16 does not work on windows '''
            return False
        return True if path.exists(self._ln) else False

    @property
    def last_used_theme(self):
        if path.exists(self._ln):
            try:
                self._last_used_theme = path.basename(readlink(self._ln)[7:-3])
            except:
                self._last_used_theme = None
        else:
            self._last_used_theme = None
        return self._last_used_theme

    def get_url(self, a_theme=None):
        base_url = 'https://raw.githubusercontent.com/edunfelt/base16-pyradio/master/themes'
        w_theme = self.last_used_theme if a_theme is None else a_theme
        # if self._last_used_theme is None:
        #     return None
        if not w_theme.startswith('base16-'):
            w_theme = 'base16-' + w_theme
        if not w_theme.endswith('.pyradio-theme'):
            w_theme += '.pyradio-theme'
        # logger.error('get_url(): url = {}'.format(base_url + '/' + self.URL_PART[self.theme_id] + '/' + w_theme))
        return base_url + '/' + self.URL_PART[self.theme_id] + '/' + w_theme

    def download(self, a_theme=None, a_path=None, print_errors=None):
        ''' download a theme
            return False if failed...
            delete downloaded file if failed

            Parameters
            ==========
            a_theme
                the theme name (no path, no extension)
                if None, use self.check_file content
            a_path
                full path to save the theme to
                if None, use self._custom_theme_file
        '''
        w_path = self._default_theme_file if a_path is None else a_path
        if self._cnf.locked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(' Theme creation inhibited (session if locked)... Waiting for 2 seconds...')
            ret = True
            sleep(2)
        else:
            if a_theme is None:
                try:
                    if self.can_auto_update:
                        # w_theme = path.basename(readlink(self._ln)[:-3]) + '.pyradio-theme'
                        w_theme = path.basename(readlink(self._ln))[7:-3]
                    else:
                        return False, None
                except:
                    return False, None
            else:
                w_theme = a_theme

            url = self.get_url(w_theme)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Project theme URL: "{}"'.format(url))

            ret = False
            # logger.error('w_path = {}'.format(w_path))
            requests_response = None
            written = False
            line_num = 1
            for n in range(0,5):
                requests_response = None
                try:
                    requests_response = requests.get(url, timeout=1)
                    requests_response.raise_for_status()
                    try:
                        with open(w_path, 'w', encoding='utf-8') as f:
                            f.write(requests_response.text)
                        written = True
                    except:
                        logger.error('cannot write file')
                        if print_errors is not None:
                            print_errors.addstr(n + 1, 0, '  download failed, retrying...', curses.color_pair(0))
                            print_errors.refresh()
                except requests.exceptions.RequestException as e:
                    if print_errors is not None:
                        print_errors.addstr(n + 1, 0, '  download failed, retrying...', curses.color_pair(0))
                        print_errors.refresh()
                    logger.error('requests through an exception')
                    sleep(.15)
                if requests_response is not None:
                    if requests_response.status_code == 200 and written:
                        break

            self.theme = self._last_used_theme
            self.theme_file_name = w_path
            self.theme_url = url
            try:
                self.status = requests_response.status_code
            except AttributeError:
                self.status = 404

            ret = self.status == 200 and written
            if not ret:
                try:
                   remove(w_path)
                except:
                    pass
        return ret, w_path


class PyRadioPyWalThemes(PyRadioBase16Themes):
    NAME = 'PyWal Project'
    ''' theme name to be found in themes window '''
    THEME = (
        'pywal-pyradio-default',
        'pywal-pyradio-default-alt',
    )
    '''  link to last used base16 theme '''
    _ln = path.join(getenv('HOME', '~'), '.cache/wal/colors.json')

    def __init__(self, config):
        self._cnf = config
        self._themes_dir = config.themes_dir
        self._custom_theme_file = path.join(self._themes_dir, self.THEME[self.theme_id] + '.pyradio-theme')
        self._default_theme_file = path.join(self._themes_dir, 'pywal-pyradio.pyradio-theme')
        ''' the default pywal file, without path and extension '''
        self.default_filename_only = 'pywal-pyradio'

    def download(self, a_theme=None, a_path=None, print_errors=None):
        ''' download a theme
            return False if failed...
            delete downloaded file if failed

            Parameters
            ==========
            a_theme
                the theme name (no path, no extension)
                if None, use self.check_file content
            a_path
                full path to save the theme to
                if None, use self._custom_theme_file
        '''
        w_path = self._default_theme_file if a_path is None else a_path
        if self._cnf.locked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(' Theme creation inhibited (session if locked)... Waiting for 1 second...')
            ret = True
            sleep(1)
        else:
            templates = ('''# Main foreground and background
Stations            {color15} {color0}

# Playing station text color
# (background color will come from Stations)
Active Station      {color1}

# Status bar foreground and background
Status Bar          {color0} {color3}

# Normal cursor foreground and background
Normal Cursor       {color0} {color1}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {color0} {color3}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {color15} {color5}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color7}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {color2}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color4}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
''', '''# Main foreground and background
Stations            {color15} {color0}

# Playing station text color
# (background color will come from Stations)
Active Station      {color3}

# Status bar foreground and background
Status Bar          {color0} {color6}

# Normal cursor foreground and background
Normal Cursor       {color0} {color3}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {color0} {color6}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {color15} {color5}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color7}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {color4}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color2}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
'''
            )
            if a_theme is None:
                try:
                    if not self.can_auto_update:
                        return False, None
                except:
                    return False, None
            else:
                w_theme = a_theme

            with open(self._ln, 'r', encoding='utf-8') as jfile:
                jdata = json.load(jfile)

            lines = templates[self.theme_id].split('\n')
            for k in jdata['colors'].keys():
                for i in range(0, len(lines)):
                    lines[i] = lines[i].replace('{' + k + '}', jdata['colors'][k])

            ret = True
            try:
                with open(w_path, 'w', encoding='utf-8') as out_file:
                    for n in lines:
                        out_file.write(n + '\n')
            except:
                ret = False

        if ret:
            return True, w_path
        else:
            try:
                remove(w_path)
            except:
                pass
            return False, None


class PyRadioThemesShThemes(PyRadioBase16Themes):
    NAME = 'Theme.sh Project'
    ''' theme name to be found in themes window '''
    THEME = (
        'theme-sh-pyradio-default',
        'theme-sh-pyradio-default-alt',
        'theme-sh-pyradio-variation',
        'theme-sh-pyradio-variation-alt',
    )
    ''' To be used in get_url (along with theme_id) '''
    '''  link to last used base16 theme '''

    def __init__(self, config):
        self._cnf = config
        self._themes_dir = config.themes_dir
        self._custom_theme_file = path.join(self._themes_dir, self.THEME[self.theme_id] + '.pyradio-theme')
        self._default_theme_file = path.join(self._themes_dir, 'theme-sh-pyradio.pyradio-theme')
        self._theme_sh_executable = pywhich('theme.sh')
        ''' the default theme.sh file, without path and extension '''
        self.default_filename_only = 'theme-sh-pyradio'

        xdg = getenv('XDG_CONFIG_HOME')
        if xdg:
            self._ln = path.join(xdg, '.theme_history')
        else:
            self._ln = path.join(getenv('HOME', '~'), '.theme_history')

    @property
    def can_auto_update(self):
        if platform.startswith('win'):
            ''' theme.sh does not work on windows '''
            return False

        if not path.exists(self._ln):
            return False

        if self._theme_sh_executable is None:
            return False
        return True

    def download(self, a_theme=None, a_path=None, print_errors=None):
        ''' read theme name from self._ln
            read theme data from self._theme_sh_executable
            return False if failed...
            delete downloaded file if failed

            Parameters
            ==========
            a_theme
                the theme name (no path, no extension)
                if None, use self.check_file content
            a_path
                full path to save the theme to
                if None, use self._custom_theme_file
        '''
        w_path = self._default_theme_file if a_path is None else a_path
        if self._cnf.locked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(' Theme creation inhibited (session if locked)... Waiting for 1 second...')
            ret = True
            sleep(1)
        else:
            theme_name = self._read_last_line_from_ln()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Actual theme name: ' + theme_name)
            theme_data = self._read_theme_sh(theme_name)
            templates = ('''# Main foreground and background
Stations            {foreground} {background}

# Playing station text color
# (background color will come from Stations)
Active Station      {color1}

# Status bar foreground and background
Status Bar          {background} {color4}

# Normal cursor foreground and background
Normal Cursor       {background} {color1}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {background} {color4}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {background} {foreground}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color1}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {color2}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color8}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
''', '''# Main foreground and background
Stations            {foreground} {background}

# Playing station text color
# (background color will come from Stations)
Active Station      {color4}

# Status bar foreground and background
Status Bar          {background} {color1}

# Normal cursor foreground and background
Normal Cursor       {background} {color4}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {background} {color1}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {background} {foreground}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color4}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {color2}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color8}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency       0
''', '''# Main foreground and background
Stations            {foreground} {background}

# Playing station text color
# (background color will come from Stations)
Active Station      {color1}

# Status bar foreground and background
Status Bar          {background} {color2}

# Normal cursor foreground and background
Normal Cursor       {background} {color1}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {background} {color2}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {background} {foreground}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color1}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {foreground}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color8}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
''', '''# Main foreground and background
Stations            {foreground} {background}

# Playing station text color
# (background color will come from Stations)
Active Station      {color2}

# Status bar foreground and background
Status Bar          {background} {color1}

# Normal cursor foreground and background
Normal Cursor       {background} {color2}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {background} {color1}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {background} {foreground}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {color2}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {foreground}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     {color8}

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
'''
            )

            lines = templates[self.theme_id].split('\n')
            for k in 'foreground', 'background':
                for i in range(0, len(lines)):
                    lines[i] = lines[i].replace('{' + k + '}', theme_data[k])

            for k in range(15, -1, -1):
                if k == 8 and \
                        theme_data[str(8)] == theme_data['background']:
                    ''' fix border color when it's equal to background '''
                    color_data = theme_data[str(5 + (self.theme_id % 2))]
                else:
                    color_data = theme_data[str(k)]
                token = '{color' + str(k) + '}'
                for i in range(0, len(lines)):
                    lines[i] = lines[i].replace(token, color_data)
            ret = True
            # enable this to see the contents of the theme
            # for n in lines:
            #     logger.error(n)
            try:
                with open(w_path, 'w', encoding='utf-8') as out_file:
                    for n in lines:
                        out_file.write(n + '\n')
            except:
                ret = False

        if ret:
            return True, w_path
        else:
            try:
                remove(w_path)
            except:
                pass
            return False, None


    def _read_last_line_from_ln(self):
        last_line = ''
        with open(self._ln, "rb") as file:
            try:
                file.seek(-2, SEEK_END)
                while file.read(1) != b'\n':
                    file.seek(-2, SEEK_CUR)
            except:
                file.seek(0)
            last_line = file.readline().decode()
        return last_line.replace('\n', '')

    def _read_theme_sh(self, theme_name):
        lines = {}
        in_theme = False
        with open(self._theme_sh_executable, 'r', encoding='utf-8') as f:
            for line in f:
                if in_theme:
                    l = line.replace('\n', '').split(': ')
                    lines[l[0]] = l[1]
                    if l[0].startswith('cursor'):
                        break
                if line.startswith(theme_name):
                    in_theme = True
        return lines


