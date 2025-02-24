# -*- coding: utf-8 -*-
import locale
import csv
import sys
import logging
import glob
import curses
import collections
import json
# import socket
from os import path, getenv, makedirs, remove, rename, readlink, SEEK_END, SEEK_CUR, getpid, listdir
from sys import platform
from time import ctime, sleep
from datetime import datetime
from shutil import which, copyfile, move, Error as shutil_Error, rmtree as remove_tree
import threading
from copy import deepcopy
from platform import system
from rich.console import Console
from rich.table import Table
from rich.align import Align
from rich import print
from pyradio import version, stations_updated
from .common import validate_resource_opener_path
from .keyboard import kbkey, lkbkey, read_keyboard_shortcuts, read_localized_keyboard, get_lkbkey, set_lkbkey, check_localized
from .browser import probeBrowsers
from .install import get_github_long_description
from .common import is_rasberrypi
from .player import pywhich
from .server import IPsWithNumbers
from .xdg import XdgDirs, XdgMigrate, CheckDir
from .install import get_a_linux_resource_opener
from .html_help import is_graphical_environment_running
from .log import Log, TIME_FORMATS

try:
    from subprocess import Popen, DEVNULL
except ImportError:
    from subprocess import Popen
if system().lower() == 'windows':
    from os import startfile
else:
    from os import getuid
HAS_REQUESTS = True

try:
    import requests
except:
    HAS_REQUESTS = False

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

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")

def to_ip_port(string):
    host = 'localhost'
    port = '11111'
    if string:
        sp = string.lower().split(':')
        if sp:
            if sp[0] == 'lan' or sp[0] == 'localhost':
                host = sp[0]
            else:
                x = IPsWithNumbers(
                        default_ip=sp[0],
                        fat=True
                )
                if x.current() == sp[0]:
                    host = sp[0]
                    # try:
                    #     x = socket.inet_pton(socket.AF_INET, sp[0])
                    #     host = sp[0]
                    # except:
                    #     return 'localhost', '11111'
                else:
                    return 'localhost', '11111'
            try:
                x = int(sp[1])
                if x > 1025:
                    port = sp[1]
                else:
                    host = 'localhost'
            except ValueError:
                host = 'localhost'
    return host, port

class PyRadioStations():
    ''' PyRadio stations file management '''
    #station_path = ''
    #station_file_name = ''
    #station_title = ''
    foreign_title = ''
    previous_station_path = ''

    ''' this is always on users config dir '''
    # stations_dir = ''
    # registers_dir = ''

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
    PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL = 3
    PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP = 4
    PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF = 5
    PLAYLIST_TYPE = [
        'PLAYLIST_HAS_NAME_URL',
        'PLAYLIST_HAS_NAME_URL_ENCODING',
        'PLAYLIST_HAS_NAME_URL_ENCODING_ICON',
        'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL',
        'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP',
        'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF',
    ]
    _playlist_version = PLAYLIST_HAS_NAME_URL
    _read_playlist_version = PLAYLIST_HAS_NAME_URL

    _playlist_version_to_string = {
        PLAYLIST_HAS_NAME_URL: 'PLAYLIST_HAS_NAME_URL',
        PLAYLIST_HAS_NAME_URL_ENCODING: 'PLAYLIST_HAS_NAME_URL_ENCODING',
        PLAYLIST_HAS_NAME_URL_ENCODING_ICON: 'PLAYLIST_HAS_NAME_URL_ENCODING_ICON',
        PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL: 'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL',
        PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP: 'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP',
        PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF: 'PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF',
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

    renamed_stations = []

    favorites = None

    def __init__(self, stationFile='', user_config_dir=None):
        if platform.startswith('win'):
            self._open_string_id = 1

        if user_config_dir is not None:
            self.stations_dir = user_config_dir
            self.xdg.build_paths()
        self.xdg.ensure_paths_exist()
        self.root_path = path.join(path.dirname(__file__), 'stations.csv')
        self.themes_dir = path.join(self.stations_dir, 'themes')
        self.favorites_path = path.join(self.stations_dir, 'favorites.csv')
        try:
            makedirs(self.themes_dir, exist_ok = True)
        except:
            try:
                makedirs(self.themes_dir)
            except:
                pass

        self._ps = PyRadioPlaylistStack()

        if not self.locked and not self.headless:
            ''' If a station.csv file exitst, which is wrong,
                we rename it to stations.csv '''
            if path.exists(path.join(self.stations_dir, 'station.csv')):
                copyfile(path.join(self.stations_dir, 'station.csv'),
                         path.join(self.stations_dir, 'stations.csv'))
                remove(path.join(self.stations_dir, 'station.csv'))

            self._move_old_csv(self.stations_dir)
            self._check_stations_csv(self.stations_dir, self.root_path)
            self._move_to_data()
            ''' rename radio browser config '''
            rb_config = path.join(self.stations_dir, 'radio-browser-config')
            if path.exists(rb_config):
                new_rb_config = path.join(self.stations_dir, 'radio-browser.conf')
                rename(rb_config, new_rb_config)

    def add_to_favorites(self, an_item):
        if self.favorites is None:
            self.favorites = FavoritesManager(self.favorites_path)
        return self.favorites.add(an_item)

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
                to_file = from_file.replace(self.stations_dir, self.state_dir)
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
        ''' if i still do not have the icons in the data dir
            copy it from the icons dir
        '''
        upd = path.join(self.state_dir, 'UPDATE_ICON')
        # # remove the file, to force icons update
        # # only do this if the packages's icons have been changed
        # # for example with gimp or inkscape
        # if path.exists(upd):
        #     os.remove(upd)

        for an_icon in ('pyradio.png', 'cover.png'):
            if not path.exists(path.join(self.data_dir, an_icon)) or \
                    not path.exists(upd):
                from_file = path.join(path.dirname(__file__), 'icons', an_icon)
                to_file = path.join(self.data_dir, an_icon)
                try:
                    copyfile(from_file, to_file)
                except:
                    pass
        # create file so that icons will not be forced copied
        with open(upd, 'w', encoding='utf-8') as f:
            f.write('\n')

        ''' make sure that the icons are under ~/.config/pyradio/data
            (the previous section may install it to a different location,
            if --config-dir is used).
        '''
        default_icon_location = self.data_dir
        if default_icon_location != self.data_dir:
            for an_icon in ('pyradio.png', 'cover.png'):
                from_file = path.join(path.dirname(__file__), 'icons', an_icon)
                to_file = path.join(default_icon_location, an_icon)
                try:
                    copyfile(from_file, to_file)
                except:
                    pass

    @property
    def stations_dir(self):
        return self.xdg.stations_dir

    @property
    def registers_dir(self):
        return self.xdg.registers_dir

    @property
    def data_dir(self):
        return self.xdg.data_dir

    @property
    def logos_dir(self):
        return self.xdg.logos_dir

    @property
    def state_dir(self):
        return self.xdg.state_dir

    @property
    def cache_dir(self):
        return self.xdg.cache_dir

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

    @can_go_cack_in_time.setter
    def can_go_cack_in_time(self, value):
        raise ValueError('property is read only')

    @property
    def playlist_version(self):
        return self._playlist_version

    @playlist_version.setter
    def playlist_version(self, value):
        self._playlist_version = value

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
        lp = path.join(self.state_dir, 'last-playlist')
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

        src = path.join(path.expanduser('~'), '.pyradio')
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
            with open(path.join(self.state_dir, 'last-sync'), 'w', encoding='utf-8') as f:
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
                    n, _ = self.read_playlists()
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
        prev_file = ''
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

        current_playlist_version = self.PLAYLIST_HAS_NAME_URL
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
            try:
                with open(stationFile, 'r', encoding='utf-8') as cfgfile:
                    try:
                        for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
                            if not row:
                                continue

                            # logger.error(f'{row = }')
                            # Initialize variables with default values
                            name = url = enc = icon = volume = http = referer = ''

                            # Assign values based on the length of the row
                            row_length = len(row)
                            name = row[0].strip()
                            if row_length > 1:
                                url = row[1].strip()
                            if row_length > 2:
                                enc = row[2].strip()
                            if row_length > 3:
                                icon = row[3].strip()
                            if row_length > 4:
                                volume = row[4].strip()
                            if row_length > 5:
                                http = row[5].strip()
                            if row_length > 6:
                                referer = row[6].strip()

                            # Append the parsed values to the reading stations list
                            station_info = [name, url, enc, {'image': icon} if icon else '', volume, http, referer]

                            self._reading_stations.append(station_info)

                            # Update playlist version based on the presence of optional fields
                            if referer and current_playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF:
                                current_playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF
                            elif http and current_playlist_version <self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP:
                                current_playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP
                            elif volume and current_playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL:
                                current_playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL
                            elif icon and current_playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON:
                                current_playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
                            elif enc and current_playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING:
                                current_playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING
                    except (csv.Error, ValueError):
                        self._reading_stations = []
                        self._playlist_version = prev_format
                        return -1
            except (FileNotFoundError, IOError) as e:
                # Handle file not found or IO errors
                self._reading_stations = []
                self._playlist_version = prev_format
                return -1
        self._read_playlist_version = self._playlist_version = current_playlist_version
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Playlist is: {} = {}'.format(self.PLAYLIST_TYPE[self._playlist_version], self._playlist_version))

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
            if n [6]:
                playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF
                break
            elif n[5]:
                if playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP:
                    playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP
            elif n[4]:
                if playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL:
                    playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL
            elif n[3]:
                if playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON:
                    playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
            elif n[2]:
                if playlist_version < self.PLAYLIST_HAS_NAME_URL_ENCODING:
                    playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING

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
        if self.renamed_stations:
            for n in self.renamed_stations:
                chk_referer_file = path.join(self.stations_dir, n[0] + '.referer.txt')
                if path.exists(chk_referer_file):
                    new_referer_file = path.join(self.stations_dir, n[1] + '.referer.txt')
                    try:
                        rename(chk_referer_file, new_referer_file)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('referer file renamed from "{}" to "{}"'.format(
                                path.basename(chk_referer_file),
                                path.basename(new_referer_file)
                                ))
                    except:
                        pass
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('failed to rename referer file from "{}" to "{}"'.format(
                                path.basename(chk_referer_file),
                                path.basename(new_referer_file)
                                ))
        return 0

    def _format_playlist_row(self, a_row):
        ''' Return a row formatted according to the current playlist version,
            eliminating any empty fields that are not part of the specified version. '''
        this_row = deepcopy(a_row)

        # Extract the 'image' from the icon dictionary if present
        if len(this_row) > 3 and 'image' in this_row[3]:
            this_row[3] = this_row[3]['image']

        # Determine the number of columns to return based on the playlist version
        if self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP_REF:
            return this_row  # Return all fields
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL_HTTP:
            return this_row[:-1]  # Exclude 'referer'
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON_VOL:
            return this_row[:-2]  # Exclude 'http' and 'referer'
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON:
            return this_row[:-3]  # Exclude 'volume', 'http', and 'referer'
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING:
            return this_row[:-4]  # Exclude 'icon', 'volume', 'http', and 'referer'
        else:
            return this_row[:-5]  # Exclude 'encoding', 'icon', 'volume', 'http', and 'referer'

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

    def dup_to_playlist_history(self):
        self._ps.duplicate()

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
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'pasting to "{a_playlist}"')
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
        self.read_playlists()
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

    check_playlist = False

    ''' if degub is on, this will tell the logger to
            0:  not log input from the player
            1:  input accepted input from the player
            2:  input raw input from the player

        It applies to the updateStatus, updateMPVStatus and
            updateWinVLCStatus functions
    '''
    debug_log_player_input = 0

    localize = None
    _old_localize = None

    EXTERNAL_PLAYER_OPTS = None

    ''' I will get this when a player is selected
        It will be used when command line parameters are evaluated
    '''
    SUPPORTED_PLAYERS = ('mpv', 'mplayer', 'vlc')
    AVAILABLE_PLAYERS = None

    PLAYER_NAME = None

    fallback_theme = ''
    use_themes = True
    terminal_is_blacklisted = False
    no_themes_notification_shown = False
    no_themes_from_command_line = False

    theme_not_supported = False
    theme_has_error = False
    theme_download_failed = False
    theme_not_supported_notification_shown = False

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
    opts['recording_dir'] = ['Recordings dir: ', '']
    opts['resource_opener'] = ['Resource Opener: ', 'auto']
    opts['log_titles'] = ['Log titles: ', False]
    opts['playlist_manngement_title'] = ['Playlist Management Options', '']
    opts['confirm_station_deletion'] = ['Confirm station deletion: ', True]
    opts['confirm_playlist_reload'] = ['Confirm playlist reload: ', True]
    opts['auto_save_playlist'] = ['Auto save playlist: ', False]
    opts['conn_title'] = ['Connection Options: ', '']
    opts['connection_timeout'] = ['Connection timeout: ', '10']
    opts['force_http'] = ['Force http connections: ', False]
    opts['notification'] = ['Notifications', '']
    opts['enable_notifications'] = ['Enable notifications: ', '-1']
    opts['use_station_icon'] = ['    Use station icon: ', True]
    opts['remove_station_icons'] = ['    Remove cached icons: ', True]
    opts['clock_title'] = ['Clock', '']
    opts['enable_clock'] = ['Display on startup: ', False]
    opts['time_format'] = ['Time format: ', '1']
    opts['theme_title'] = ['Theme Options', '']
    opts['theme'] = ['Theme: ', 'dark']
    opts['use_transparency'] = ['Use transparency: ', False]
    opts['force_transparency'] = ['  Force transparency: ', False]
    opts['calculated_color_factor'] = ['Calculated color: ', '0']
    opts['console_theme'] = ['Console theme: ', 'dark']
    opts['mouse_options'] = ['Mouse Support', '']
    opts['enable_mouse'] = ['Enable mouse support: ', False]
    opts['wheel_adjusts_volume'] = ['    Reverse wheel: ', False]
    opts['remote'] = ['Remote Control Server', '']
    opts['remote_control_server_ip'] = ['Server IP: ', 'localhost']
    opts['remote_control_server_port'] = ['Server Port: ', '9998']
    opts['remote_control_server_auto_start'] = ['Auto-start Server: ', False]
    opts['shortcuts'] = ['Keyboard Shortcuts', '']
    opts['shortcuts_keys'] = ['Shortcuts', '-']
    opts['localized_keys'] = ['Localized Shortcuts', '-']
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
        th_path = path.join(path.expanduser('~'), '.config', 'pyradio', 'themes', 'auto.pyradio-themes')
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
    enable_calculated_colors = True
    has_border_background  = False

    start_colors_at = 0

    buffering_data = []

    _fixed_recording_dir = None

    _linux_resource_opener = None

    need_to_fix_desktop_file_icon = False

    notification_image_file = None

    _last_station_checked = None
    _last_station_checked_id = -1
    _check_output_folder = None
    _check_output_file = None

    def __init__(self, user_config_dir=None, headless=False):
        # keep old recording / new recording dir
        self._user_config_dir = user_config_dir
        self.rec_dirs = ()
        self._first_read = True
        self._headless = headless
        self.backup_player_params = None
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
        self.xdg = XdgDirs(
                a_dir_fix_function=self._save_config_from_fixed_rec_dir
                )
        self.dirty_config = True if self.params_changed else False
        ''' True if player changed by config window '''
        self.player_changed = False
        ''' [ old player, new player ] '''
        self.player_values = []

        self._session_lock_file = ''
        self._get_lock_file()
        if user_config_dir is None:
            self.xdg.migrate(self.locked or self.headless)

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
    def log_titles(self):
        return self.opts['log_titles'][1]

    @log_titles.setter
    def log_titles(self, val):
        old_val = self.opts['log_titles'][1]
        self.opts['log_titles'][1] = val
        if old_val != val:
            self.dirty_config = True

    @property
    def linux_resource_opener(self):
        return self._linux_resource_opener

    @property
    def xdg_compliant(self):
        return self.xdg.xdg_compliant

    @xdg_compliant.setter
    def xdg_compliant(self, val):
        self.xdg.xdg_compliant = val

    @property
    def headless(self):
        if self._headless is None:
            return False
        return True

    @property
    def remote_control_server_report_file(self):
        if self.headless:
            return path.join(self.state_dir, 'server-headless.txt')
        else:
            return path.join(self.state_dir, 'server.txt')

    @property
    def enable_clock(self):
        return self.opts['enable_clock'][1]

    @enable_clock.setter
    def enable_clock(self, val):
        old_val = self.opts['enable_clock'][1]
        self.opts['enable_clock'][1] = val
        if old_val != val:
            self.dirty_config = True

    @property
    def wheel_adjusts_volume(self):
        return self.opts['wheel_adjusts_volume'][1]

    @property
    def time_format(self):
        return self.opts['time_format'][1]

    @time_format.setter
    def time_format(self, val):
        old_val = self.opts['time_format'][1]
        self.opts['time_format'][1] = val
        if old_val != val:
            self.dirty_config = True

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
        if is_graphical_environment_running():
            return self.opts['enable_notifications'][1]
        return False

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
    def remove_station_icons(self):
        return self.opts['remove_station_icons'][1]

    @remove_station_icons.setter
    def remove_station_icons(self, val):
        self.opts['remove_station_icons'][1] = val
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
    def force_transparency(self):
        return self.opts['force_transparency'][1]

    @force_transparency.setter
    def force_transparency(self, val):
        self.opts['force_transparency'][1] = val
        self.opts['dirty_config'][1] = True

    @property
    def calculated_color_factor(self):
        return float(self.opts['calculated_color_factor'][1])

    @calculated_color_factor.setter
    def calculated_color_factor(self, value):
        try:
            float(str(value))
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
    def console_theme(self):
        return self.opts['console_theme'][1]

    @console_theme.setter
    def console_theme(self, val):
        if val in ('dark', 'light'):
            if val != self.opts['console_theme'][1]:
                self.opts['dirty_config'][1] = True
            self.opts['console_theme'][1] = val

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
        return tuple(sorted([path.basename(x).replace('.pyradio-theme', '') for x in glob.glob(path.join(path.dirname(__file__), 'themes', '*.pyradio-theme'), recursive = False)]))

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

    @property
    def resource_opener(self):
        return self.opts['resource_opener'][1]

    @property
    def recording_dir(self):
        return self.opts['recording_dir'][1]

    @recording_dir.setter
    def recording_dir(self, val):
        self.opts['recording_dir'][1] = val
        # self.xdg.recording_dir = val
        self.dirty_config = True

    @property
    def last_station_checked(self):
        return self._last_station_checked

    @last_station_checked.setter
    def last_station_checked(self, value):
        self._last_station_checked = value

    @property
    def last_station_checked_id(self):
        return self._last_station_checked_id

    @last_station_checked_id.setter
    def last_station_checked_id(self, value):
        self._last_station_checked_id = value

    @property
    def check_output_folder(self):
        return self._check_output_folder

    @check_output_folder.setter
    def check_output_folder(self, value):
        self._check_output_folder = value

    @property
    def check_output_file(self):
        return self._check_output_file

    @check_output_file.setter
    def check_output_file(self, value):
        self._check_output_file = value

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
        self.user_agent_string = r'PyRadio/{}'.format(version)
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


    def remove_remote_control_server_report_file(self):
        if path.exists(self.remote_control_server_report_file):
            try:
                remove(self.remote_control_server_report_file)
            except:
                pass

    def setup_mouse(self):
        curses.mousemask(curses.ALL_MOUSE_EVENTS
                         | curses.REPORT_MOUSE_POSITION)
        #curses.mouseinterval(0)

    def open_a_dir(self, a_dir):
        if system().lower() == 'windows':
            startfile(a_dir)
        elif system().lower() == 'darwin':
            Popen([which('open'), a_dir])
        else:
            xdg_open_path = self._linux_resource_opener if self._linux_resource_opener else get_a_linux_resource_opener()
            if isinstance(xdg_open_path, str):
                xdg_open_path = xdg_open_path.split(' ')
            if xdg_open_path:
                try:
                    Popen(
                        [*xdg_open_path, a_dir],
                        stderr=DEVNULL,
                        stdout=DEVNULL
                    )
                except (FileNotFoundError, PermissionError):
                    pass

    def open_config_dir(self, recording=0):
        a_dir = self.stations_dir if recording == 0 else self.recording_dir
        if system().lower() == 'windows':
            startfile(a_dir)
        elif system().lower() == 'darwin':
            Popen([which('open'), a_dir])
        else:
            xdg_open_path = self._linux_resource_opener if self._linux_resource_opener else get_a_linux_resource_opener()
            if xdg_open_path:
                try:
                    Popen(
                        [*xdg_open_path, a_dir],
                        stderr=DEVNULL,
                        stdout=DEVNULL
                    )
                except (FileNotFoundError, PermissionError):
                    pass

    def _get_lock_file(self):
        ''' Populate self._session_lock_file
            If it exists, locked becomes True
            Otherwise, the file is created
        '''
        self._i_created_the_lock_file = False
        self.locked = False
        if platform == 'win32':
            self._session_lock_file = path.join(self.state_dir, 'pyradio.lock')
            win_lock = path.join(self.state_dir, 'data', '_windows.lock')
            if path.exists(win_lock):
                ''' pyradio lock file was probably not deleted the last
                    time Windows terminated. It should be safe to use it
                '''
                try:
                    remove(win_lock)
                except:
                    pass
        else:
            xdg_runtime_dir = getenv('XDG_RUNTIME_DIR')
            if xdg_runtime_dir:
                self._session_lock_file = path.join(xdg_runtime_dir, 'pyradio.lock')
            elif path.exists('/run/user'):
                from os import geteuid
                self._session_lock_file = path.join('/run/user', str(geteuid()), 'pyradio.lock')
                if not path.exists(self._session_lock_file):
                    self._session_lock_file = None
            if self._session_lock_file is None:
                self._session_lock_file = path.join(self.state_dir, '.pyradio.lock')
        try:
            makedirs(self.state_dir, exist_ok=True)
        except:
            print(f'[red]Error:[/red] Cannot create dir: "{self.state_dir}"')
            sys.exit(1)

        ''' remove old style session lock file (if it exists) '''
        if path.exists(path.join(self.stations_dir, '.lock')):
            try:
                remove(path.join(self.stations_dir, '.lock'))
            except:
                pass
        if path.exists(self._session_lock_file):
            self.locked = True
        else:
            if not self.headless:
                try:
                    with open(self._session_lock_file, 'w', encoding='utf-8'):
                        pass
                    self._i_created_the_lock_file = True
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
        if self.console_theme == 'light':
            curses.init_pair(1, curses.COLOR_MAGENTA, curses.COLOR_WHITE )
            curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_WHITE)
            curses.init_pair(3, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(4, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(5, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_MAGENTA)
            curses.init_pair(7, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(8, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(9, curses.COLOR_WHITE, curses.COLOR_BLUE)
            curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(11, curses.COLOR_RED, curses.COLOR_WHITE)
            curses.init_pair(12, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(13, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(14, curses.COLOR_BLACK, curses.COLOR_WHITE)
            curses.init_pair(15, curses.COLOR_BLACK, curses.COLOR_WHITE)
        else:
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
        self.bck_opts['force_transparency'] = self.opts['force_transparency'][1]
        self.bck_opts['theme'] = self.opts['theme'][1]
        self.bck_opts['auto_update_theme'] = self.opts['auto_update_theme'][1]
        self.bck_opts['calculated_color_factor'] = self.opts['calculated_color_factor'][1]
        ''' No theme values '''
        self.opts['use_transparency'][1] = False
        self.opts['force_transparency'][1] = False
        self.opts['theme'][1] = self.console_theme
        self.opts['auto_update_theme'][1] = False
        self.opts['calculated_color_factor'][1] = "0"
        self._show_colors_cannot_change = show_colors_cannot_change
        # logger.error('bck_opts = {}'.format(self.bck_opts))

    def _check_config_file(self, usr):
        ''' Make sure a config file exists in the config dir '''
        package_config_file = path.join(path.dirname(__file__), 'config')
        user_config_file = path.join(usr, 'config')

        ''' restore config from bck file '''
        if path.exists(user_config_file + '.restore'):
            try:
                copyfile(user_config_file + '.restore', user_config_file)
                remove(user_config_file + '.restore')
            except:
                pass

        ''' update pi config file '''
        if not path.exists(user_config_file) and \
                is_rasberrypi():
            self._convert_config_for_rasberrypi(package_config_file, user_config_file)

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

    def migrate_xdg(self):
        mXdg = XdgMigrate(config=self)
        mXdg.rename_files()
        self._copy_icon()
        if self.xdg_compliant:
            # I need to have ~/.config/pyradio/data hardcoded here
            dpath = path.join(path.expanduser('~'), '.config', 'pyradio', 'data')
            if path.exists(dpath):
                flist = listdir(dpath)
                if len(flist) == 0:
                    try:
                        remove_tree(dpath)
                    except:
                        pass

    def _read_localized_shortcuts(self, name=None):
        if name is None:
            name = self.localize
        if not name or name == 'english':
            return {}
        # Construct potential paths
        script_dir_path = path.join(path.dirname(__file__), 'keyboard', name + '.json')
        full_path = path.join(self.data_dir, name + '.json')
        # logger.error(f'{script_dir_path = }')
        # logger.error(f'{full_path = }')

        reversed_dict = {}
        # Check which file path exists
        if path.exists(full_path):
            target_path = full_path
        elif path.exists(script_dir_path):
            target_path = script_dir_path
        else:
            # Return an empty dictionary if neither path exists
            target_path = None

        # logger.error(f'{target_path = }')
        if target_path is None:
            set_lkbkey({})
        else:
            # Open and load the JSON file
            try:
                with open(target_path, 'r', encoding='utf-8') as file:
                    data = json.load(file)
            except Exception as e:
                reversed_dict = {}

            # Reverse the keys and values
            reversed_dict = {value: key for key, value in data.items()}

            # logger.error('\n\nsetting lkbkey 1\n{}\n\n'.format(reversed_dict))
            set_lkbkey(reversed_dict)

    def read_config(self, distro_config=False, check_playlist=False):
        if check_playlist:
            if self._i_created_the_lock_file:
                self.remove_session_lock_file()
            self.locked = True
        self.check_playlist = check_playlist
        self._read_config(distro_config=True)
        self.config_opts = deepcopy(self.opts)
        # for n in self.config_opts.items():
        #     logger.error('  {}: {}'.format(*n))
        self.re_read_config()

    def re_read_config(self):
        self._read_config()
        self.xdg.ensure_paths_exist()

    def _read_config(self, distro_config=False):
        xdg_compliant_read_from_file = False
        if distro_config:
            file_to_read = path.join(path.dirname(__file__), 'config')
        else:
            file_to_read = self.config_file
            if not path.exists(file_to_read):
                # user config does not exist, just return
                self._make_sure_dirs_exist()
                self._first_read = False
                return
        lines = []
        try:
            with open(file_to_read, 'r', encoding='utf-8') as cfgfile:
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
            sp = line.split('=')
            if len(sp) < 2:
                return -2
            if sp[1] == '':
                return -2
            for i in range(len(sp)):
                sp[i] = sp[i].strip()
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
                self.opts['player'][1] = sp[1].lower().replace(' ', '')
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
            elif sp[0] == 'console_theme':
                tmp = sp[1].strip()
                if tmp not in ('dark', 'light'):
                    self.opts['console_theme'][1] = 'dark'
                else:
                    self.opts['console_theme'][1] = tmp
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
            elif sp[0] == 'wheel_adjusts_volume':
                if sp[1].lower() == 'false':
                    self.opts['wheel_adjusts_volume'][1] = False
                else:
                    self.opts['wheel_adjusts_volume'][1] = True
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
            elif sp[0] == 'remove_station_icons':
                if sp[1].lower() == 'false':
                    self.opts['remove_station_icons'][1] = False
                else:
                    self.opts['remove_station_icons'][1] = True
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
            elif sp[0] == 'force_transparency':
                if sp[1].lower() == 'true':
                    self.opts['force_transparency'][1] = True
                else:
                    self.opts['force_transparency'][1] = False
            elif sp[0] == 'log_titles':
                if sp[1].lower() == 'true':
                    self.opts['log_titles'][1] = True
                else:
                    self.opts['log_titles'][1] = False
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
                # hosts = ('localhost', 'LAN', 'lan')
                sp[1] = sp[1].strip()
                nip = IPsWithNumbers(
                        default_ip=sp[1]
                )
                self.opts['remote_control_server_ip'][1] = nip.current()
                nip = None
                # x = [r for r in hosts if r == sp[1]]
                # if x:
                #     self.opts['remote_control_server_ip'][1] = x[0]
                # else:
                #     self.opts['remote_control_server_ip'][1] = 'localhost'
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
            elif sp[0] == 'recording_dir':
                self.opts['recording_dir'][1] = sp[1].strip()
                if self.opts['recording_dir'][1] == 'default':
                    self.opts['recording_dir'][1] = ''
                if self.opts['recording_dir'][1].startswith('~'):
                    self.opts['recording_dir'][1] = path.expanduser('~') + self.opts['recording_dir'][1][1:]
                elif self.opts['recording_dir'][1].startswith('%homepath%') or \
                        self.opts['recording_dir'][1].startswith('%HOMEPATH%'):
                    self.opts['recording_dir'][1] = path.expanduser('~') + self.opts['recording_dir'][1][len('%homepath%'):]
            elif sp[0] == 'distro' and \
                    distro_config:
                ''' mark as dirty to force saving config to remove setting '''
                # self.dirty_config = True
                self._distro = sp[1].strip()
            elif sp[0] == 'xdg_compliant' and \
                    not platform.startswith('win') and \
                    self._user_config_dir is None and \
                    sp[1].lower() == 'true':
                self.xdg_compliant = True
                xdg_compliant_read_from_file = True
            elif sp[0] == 'resource_opener' and \
                    not (platform.startswith('win') or \
                        platform.startswith('dar')):
                if sp[1] != 'auto':
                    tmp = sp[1].split(' ')
                    prog = validate_resource_opener_path(tmp[0])
                    if prog is not None:
                        tmp[0] = prog
                        self._linux_resource_opener = ' '.join(tmp)
                        self.opts['resource_opener'][1] = sp[1]
            elif sp[0] == 'enable_clock':
                if sp[1].lower() == 'false':
                    self.opts['enable_clock'][1] = False
                else:
                    self.opts['enable_clock'][1] = True
            elif sp[0] == 'time_format':
                tmp = sp[1].split(' ')[0]
                try:
                    x = int(tmp)
                    if not (0 <= x < len(TIME_FORMATS)):
                        tmp = '0'
                except (ValueError, TypeError):
                        tmp = '0'
                self.opts['time_format'][1] = tmp
            elif sp[0] == 'localized_keys':
                # logger.error(f'{sp[1] = }')
                self.localize = None if sp[1].strip().lower() == 'none' else sp[1].strip().lower()
                # logger.error(f'{self.localize = }')
                self._old_localize = self.localize

        # logger.error('\n\nself.params{}\n\n'.format(self.params))
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

        self.opts['dirty_config'][1] = False
        self.saved_params = deepcopy(self.params)

        if self.check_playlist:
            self._headless = None
            self._distro = 'Check Playlist Mode'
            self.opts['enable_notifications'][1] = '-1'
            self.opts['remote_control_server_auto_start'][1] = False
            self.opts['enable_clock'][1] = False
            self.opts['auto_update_theme'][1] = False
            self.opts['enable_clock'][1] = True
            self.opts['time_format'][1] = 0

        if self.headless:
            self.opts['remote_control_server_ip'][1], self.opts['remote_control_server_port'][1] = to_ip_port(self._headless)
            self.opts['remote_control_server_auto_start'][1] = True
            self.opts['theme'][1] = 'dark'
            self.opts['auto_update_theme'][1] = False
            self.opts['use_transparency'][1] = False
            self.opts['force_transparency'][1] = False
            self.opts['enable_mouse'][1] = False
            self.opts['calculated_color_factor'][1] = '0'
            self.opts['enable_clock'][1] = False

        ''' check if default playlist exists '''
        if self.opts['default_playlist'][1] != 'stations':
            ch = path.join(self.stations_dir, self.opts['default_playlist'][1] + '.csv')
            if not path.exists(ch):
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Default playlist "({}") does not exist; reverting to "stations"'.format(self.opts['default_station'][1]))
                self.opts['default_playlist'][1] = 'stations'
                self.opts['default_station'][1] = 'False'
        # # for n in self.opts.keys():
        # #     logger.error('  {0}: {1} '.format(n, self.opts[n]))
        # # for n in self.opts.keys():
        # #     logger.error('  {0}: {1} '.format(n, self.opts[n]))
        # for n in self.opts:
        #     print('{0}: {1}'.format(n, self.opts[n]))

        if not distro_config and self._fixed_recording_dir is not None:
            self.opts['recording_dir'][1] = self._fixed_recording_dir
            self._fixed_recording_dir = None
            self.opts['dirty_config'][1] = True

        self._make_sure_dirs_exist()
        ''' detect previous XDG Base installation '''
        if not platform.startswith('win')  and \
                self._user_config_dir is None and \
                not self.xdg_compliant and \
                distro_config:
            # d_dir = path.join(XdgDirs.get_xdg_dir('XDG_DATA_HOME'), 'pyradio')
            # s_dir = path.join(XdgDirs.get_xdg_dir('XDG_STATE_HOME'), 'pyradio')
            d_dir = XdgDirs.get_xdg_dir('XDG_DATA_HOME')
            s_dir = XdgDirs.get_xdg_dir('XDG_STATE_HOME')
            if path.exists(d_dir) and path.exists(s_dir):
                # print('[magenta]XDG Dirs[/magenta] found; enabling [magenta]XDG Base compliant[/magenta] operation')
                self.xdg_compliant = True
                self.need_to_fix_desktop_file_icon = True

        # do this here to get proper extra parameters config filepath if XDG is on
        self.player_params_file = path.join(self.data_dir, 'player-params.json')
        if not distro_config:
            # read localized shortcuts
            self._read_localized_shortcuts(name=None)

            if path.exists(self.player_params_file + '.restore'):
                try:
                    copyfile(self.player_params_file + '.restore', self.player_params_file)
                except:
                    pass
            if path.exists(self.player_params_file):
                try:
                    with open(self.player_params_file, 'r', encoding='utf-8') as jf:
                        self.params = json.load(jf)
                except:
                    pass
            self._first_read = False
            # logger.error('\n\nfile = {0}\nplayer extra params = {1}\n\n'.format(self.player_params_file, self.params))

            # do this here to get proper schedule and keyboard config filepath if XDG is on
            self.schedule_file = path.join(self.data_dir, 'schedule.json')
            self.keyboard_file = path.join(self.data_dir, 'keyboard.json')
            # logger.error(f'{self.keyboard_file = }')
        if not self.headless and not distro_config:
            read_keyboard_shortcuts(self.keyboard_file)
            read_localized_keyboard(
                self.localize,
                self.data_dir
            )
        self.active_enable_clock = self.enable_clock

    def _make_sure_dirs_exist(self):
        home_rec_dir = path.join(path.expanduser('~'), 'pyradio-recordings')
        if self.opts['recording_dir'][1] == '':
            self.opts['recording_dir'][1] = path.join(path.expanduser('~'), 'pyradio-recordings')
        ch_dir = CheckDir(
            self.opts['recording_dir'][1],
            home_rec_dir,
            remove_after_validation=True
        )
        if not ch_dir.can_be_created:
            print('Error: Recordings directory is for a folder: "{}"'.format(self.opts['recording_dir'][1]))
            sys.exit(1)
        elif not ch_dir.can_be_writable:
            print('Error: Recordings directory is not writable: "{}"'.format(self.opts['recording_dir'][1]))
            sys.exit(1)

        if not path.exists(self.opts['recording_dir'][1]):
            try:
                makedirs(self.opts['recording_dir'][1])
            except:
                print('Error: Cannot create recordings directory: "{}"'.format(self.opts['recording_dir'][1]))
                sys.exit(1)
        # logger.error('self.opts["recording_dir"][1] = "{}"'.format(self.opts['recording_dir'][1]))
        if path.exists(path.join(self.stations_dir, 'data', 'recordings')) and \
                    self._first_read:
            print('++ Need to migrate')
            ''' On startup only move recordings dir
                from  [[STATIONS DIR]]data/recordings
                to    ~/pyradio_recordings
                        (also on Windows)
            '''
            self.xdg.set_recording_dir(
                    new_dir=self.opts['recording_dir'][1],
                    print_to_console=True,
                    migrate=True,
                    first_read=path.join(self.stations_dir, 'data', 'recordings')
            )

        # remove recordings dir from home dir if it is empty, as per #253
        if path.exists(self.opts['recording_dir'][1]) and \
                self.opts['recording_dir'][1] ==  home_rec_dir and  \
                len(listdir(self.opts['recording_dir'][1])) == 0:
            # fix for #255
            try:
                remove_tree(self.opts['recording_dir'][1])
            except:
                pass

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
            path.join(self.state_dir, 'last-playlist'),
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
        if self.backup_player_params is not None:
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
        if self.backup_player_params is not None:
            self.params[self.PLAYER_NAME] = self.backup_player_params[the_param_type][:]
        # logger.error('DE params  after = {}'.format(self.params))
        # logger.error('DE backup_player_params = {}'.format(self.backup_player_params))

    def _read_player_params(self):
        pass

    def _save_player_params(self):
        pass

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
        if self.localize != self._old_localize:
            return True
        return False

    def _validate_config_key(
            self, a_key, theme, trnsp,
            f_trnsp, calcf, auto, rec_dir
            ):
        ''' check if a config parameter is different to the one in the config file
            if it has return "key = value", otherwise return None
        '''
        comment = ''
        if a_key == 'theme':
            return None if self.config_opts[a_key][-1] == theme else a_key + ' = ' + str(theme)
        elif a_key == 'use_transparency':
            return None if self.config_opts[a_key][-1] == trnsp else a_key + ' = ' + str(trnsp)
        elif a_key == 'force_transparency':
            return None if self.config_opts[a_key][-1] == f_trnsp else a_key + ' = ' + str(f_trnsp)
        elif a_key == 'calculated_color_factor':
            return None if self.config_opts[a_key][-1] == calcf else a_key + ' = ' + str(calcf)
        elif a_key == 'auto_update_theme':
            return None if self.config_opts[a_key][-1] == auto else a_key + ' = ' + str(auto)
        elif a_key == 'recording_dir':
            comment = r'''# Please do not change this paramter manually
# Use the in program Window instead
# (Config / General Options / Recordings dir)
'''
            # logger.error('\n\nself.config_opts[a_key][-1]: {} == rec_dir: {}\n\n'.format(self.config_opts[a_key][-1], rec_dir))
            if self._dir_to_shorthand(self.config_opts[a_key][-1]) == rec_dir or \
                    rec_dir == 'default':
                # logger.error('returning None')
                return None
            else:
                # logger.error('returning {}'.format(comment + a_key + ' = ' + rec_dir))
                return comment + a_key + ' = ' + rec_dir
        elif self.config_opts[a_key][-1] == self.opts[a_key][-1]:
            return None
        return comment + a_key + ' = ' + str(self.opts[a_key][-1])

    def _get_sting_to_save(
            self, theme, trnsp,
            f_trnsp, calcf, auto, rec_dir
            ):
        out = []
        prm = []
        for n in self.config_opts.keys():
            if self.config_opts[n][0] != '' and \
                    self.config_opts[n][-1] != '-' and \
                    self.config_opts[n][-1] != '':
                prm.append(n)
        for n in prm:
            chk = self._validate_config_key(
                    n, theme, trnsp, f_trnsp,
                    calcf, auto, rec_dir
                    )
            if chk:
                out.append(chk)

        if self.localize is not None:
            out.append(f'localized_keys = {self.localize}')

        if not self.show_no_themes_message:
            out.append('')
            out.append('#')
            out.append('# User option (response to a message window)')
            out.append('# Show a message if themes are disabled')
            out.append('#')
            out.append('# Default value: True')
            out.append('show_no_themes_message = False')
        if not self.show_recording_start_message:
            out.append('')
            out.append('#')
            out.append('# User option (response to a message window)')
            out.append('# Show a message when recording is enabled')
            out.append('#')
            out.append('# Default value: True')
            out.append('show_recording_message = False')

        if out:
            out.reverse()
            out.append('#')
            out.append('# or examine the file: {}'.format(path.join(path.dirname(__file__), 'config')))
            out.append('# To get a full list of options execute: pyradio -pc')
            out.append('# PyRadio User Configuration File')
            out.reverse()

        # for i, n in enumerate(out):
        #     logger.error(f'out[{i}] : {n}')
        # logger.error(out)
        return out

    def _dir_to_shorthand(self, a_dir):
        ret = a_dir.replace(
                path.expanduser('~'),
                '%HOMEPATH%' if platform.startswith('win') else '~'
                )
        return ret

    def _save_config_from_fixed_rec_dir(self, a_path):
        self._fixed_recording_dir = a_path

    def save_config(self, from_command_line=False):
        ''' Save config file

            Creates config.restore (back up file)
            Returns:
                -1: Error saving config
                 0: Config saved successfully
                 1: Config not saved (not modified)
                 TODO: 2: Config not saved (session locked) '''
        if self.check_playlist:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
                logger.info('Not saving Config (checking playlist mode activated)')
            return 1

        if self.locked:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (session locked)')
            return 1

        if self.headless:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (session is headless)')
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
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.info('* self.backup_player_params {}'.format(self.backup_player_params))
            if self.backup_player_params is not None:
                self.backup_player_params[1] = self.backup_player_params[0][:]
            # if logger.isEnabledFor(logging.DEBUG):
            #    logger.info('* self.backup_player_params {}'.format(self.backup_player_params))
        if not from_command_line and \
                logger.isEnabledFor(logging.DEBUG):
            logger.debug('saved params = {}'.format(self.saved_params))

        # logger.info('\nsaved_params\n{}\n\n'.format(self.saved_params))
        if not self.opts['dirty_config'][1]:
            if not from_command_line and \
                    logger.isEnabledFor(logging.INFO):
                logger.info('Config not saved (not modified)')
            return 1
        if path.exists(self.config_file):
            copyfile(self.config_file, self.config_file + '.restore')
        if self.opts['default_station'][1] is None:
            self.opts['default_station'][1] = '-1'

        if self.use_themes:
            theme = self.opts['theme'][1] if not self.opts['auto_update_theme'][1] else '*' + self.opts['theme'][1]
            trnsp = self.opts['use_transparency'][1]
            f_trnsp = self.opts['force_transparency'][1]
            calcf = self.opts['calculated_color_factor'][1]
            auto = self.opts['auto_update_theme'][1]
        else:
            theme = self.bck_opts['theme'] if not self.bck_opts['auto_update_theme'] else '*' + self.bck_opts['theme']
            trnsp = self.bck_opts['use_transparency']
            f_trnsp = self.bck_opts['force_transparency']
            calcf = self.bck_opts['calculated_color_factor']
            auto = self.bck_opts['auto_update_theme']

        if self.opts['recording_dir'][1] == path.join(path.expanduser('~'), 'pyradio-recordings'):
            rec_dir = 'default'
        else:
            rec_dir = self._dir_to_shorthand(self.opts['recording_dir'][1])
        self.xdg.set_recording_dir(
                new_dir=self.opts['recording_dir'][1],
                print_to_console=False,
                migrate=False
                )

        # TODO: migrate recordings dir
        # self.xdg.set_recording_dir(
        #         new_dir=rec_dir,
        #         print_to_console=False,
        #         migrate=False
        # )
        try:
            out = self._get_sting_to_save(theme, trnsp, f_trnsp, calcf, auto, rec_dir)
            with open(self.config_file, 'w', encoding='utf-8') as cfgfile:
                if out:
                    cfgfile.write('\n'.join(out) + '\n')
                # cfgfile.write(txt.format(
                #     self.opts['player'][1],
                #     self.opts['open_last_playlist'][1],
                #     self.opts['default_playlist'][1],
                #     self.opts['default_station'][1],
                #     self.opts['default_encoding'][1],
                #     self.opts['enable_mouse'][1],
                #     self.opts['enable_notifications'][1],
                #     self.opts['use_station_icon'][1],
                #     rec_dir,
                #     self.opts['connection_timeout'][1],
                #     self.opts['force_http'][1],
                #     theme,
                #     trnsp,
                #     self.opts['force_transparency'][1],
                #     calcf,
                #     self.opts['confirm_station_deletion'][1],
                #     self.opts['confirm_playlist_reload'][1],
                #     self.opts['auto_save_playlist'][1],
                #     self.show_no_themes_message,
                #     self.show_recording_start_message,
                #     self.remote_control_server_ip,
                #     self.remote_control_server_port,
                #     self.remote_control_server_auto_start
                # ))

            ''' write extra player parameters to file '''
            if path.exists(self.player_params_file):
                try:
                    copyfile(self.player_params_file, self.player_params_file + '.restore')
                except:
                    pass
            # fix self.saved_params (remove profiles)
            profiles_params_changed = False
            for a_key in self.saved_params.keys():
                # the_id = self.saved_params[a_key][0]
                the_profile = self.saved_params[a_key][self.saved_params[a_key][0]]
                # logger.error('\n\na_key = {0}\nthe_id = {1}\nthe_profile = {2}\n\n'.format(a_key, the_id, the_profile))
                for i in range(len(self.saved_params[a_key])-1, 0, -1):
                    if self.saved_params[a_key][i].startswith('profile:'):
                        if self.saved_params[a_key][i] != the_profile:
                            del self.saved_params[a_key][i]
                            profiles_params_changed = True
                    self.saved_params[a_key][0] = self.saved_params[a_key].index(the_profile)
            if profiles_params_changed and logger.isEnabledFor(logging.DEBUG):
                logger.debug('reduced saved params = {}'.format(self.saved_params))
            try:
                with open(self.player_params_file, 'w', encoding='utf-8') as jf:
                    jf.write(json.dumps(self.saved_params))
                    if path.exists(self.player_params_file + '.restore'):
                        try:
                            remove(self.player_params_file + '.restore')
                        except:
                            pass
            except:
                pass
        except:
            if not from_command_line and \
                    logger.isEnabledFor(logging.ERROR):
                logger.error('Error saving config')
            return -1
        if not out:
            remove(self.config_file)

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
        self._linux_resource_opener = self.resource_opener
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

            # logger.error('\n\n{}\n\n'.format(parents))
            if parents is not None:
                '''
                read ~/.config/pyradio/no-themes-terminals
                '''
                term_file = path.join(self.stations_dir, 'no-themes-terminals')
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
        ppid = None
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


class PyRadioPlaylistStack():

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

    def duplicate(self):
        it = self._p[-1]
        self._p.append(it)

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
        if member in self._id:
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


class PyRadioStationsStack():
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

class PyRadioLog():

    PATTERN = '%(asctime)s - %(name)s:%(funcName)s():%(lineno)d - %(levelname)s: %(message)s'
    PATTERN_TITLE = '%(asctime)s | %(message)s'

    log_titles = log_debug = False

    titles_handler = debug_handler = None

    def __init__(self, pyradio_config):
        self._cnf = pyradio_config
        self._stations_dir = pyradio_config.stations_dir

    def configure_logger(self, recording_dir=None, debug=None, titles=None):
        logger = logging.getLogger('pyradio')
        logger.setLevel(logging.DEBUG)
        if debug or titles:
            if debug and not self.log_debug:
                # Handler
                if self._cnf.check_playlist:
                    if self._cnf.check_output_folder is  None:
                        ret = self._create_check_output_folder()
                        if not ret:
                            return False
                    log_file = path.join(self._cnf.check_output_folder, 'pyradio.log')
                    self._cnf.check_output_file = log_file
                else:
                    log_file = path.join(path.expanduser('~'), 'pyradio.log')
                self.debug_handler = logging.FileHandler(log_file)
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
                if logger.isEnabledFor(logging.INFO):
                    logger.info('setting up pyradio-titles.log')
                if not path.exists(recording_dir):
                    try:
                        makedirs(recording_dir)
                    except:
                        pass
                if not path.exists(recording_dir):
                    self.log_titles = False
                    self.titles_handler = None
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error('cannot start titles log on: "{}"; directory does not exist'.format(recording_dir))
                    return False
                else:
                    self.titles_handler = logging.handlers.RotatingFileHandler(
                        path.join(
                            recording_dir,
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
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('starting titles log on: "{}"'.format(recording_dir))

        if (not titles) and self.log_titles:
            if self.titles_handler:
                logger.critical('=== Logging stopped')
                logger.removeHandler(self.titles_handler)
                self.log_titles = False
                self.titles_handler = None

        logging.raiseExceptions = False
        logging.lastResort = None
        # logger.info('self.log_titles = {}'.format(self.log_titles))
        return True

    def _create_check_output_folder(self):
        # Generate the timestamped folder name using os.strftime
        timestamp = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
        folder_name = f"{timestamp}-playlist-check"

        # Join with state directory
        self._cnf.check_output_folder = path.join(self._cnf.state_dir, folder_name)

        # print('self._cnf.check_output_folder = "{}"'.format(self._cnf.check_output_folder))
        # Check if the directory exists, if not, create it
        try:
            if not path.exists(self._cnf.check_output_folder):
                makedirs(self._cnf.check_output_folder, exist_ok=True)

            # Double-check if the folder was created successfully
            if path.isdir(self._cnf.check_output_folder):
                return True
            else:
                return False
        except Exception as e:
            # print(f"Error creating directory: {e}")
            return False

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

class PyRadioBase16Themes():

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
    _ln = path.join(path.expanduser('~'), '.config/base16-project/base16_shell_theme')
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
                except requests.exceptions.RequestException:
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
    _ln = path.join(path.expanduser('~'), '.cache', 'wal', 'colors.json')

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
            self._ln = path.join(path.expanduser('~'), '.theme_history')
        new_ln = path.join(self._cnf.state_dir, 'theme_history')
        if path.exists(self._ln) and \
                path.exists(self._cnf.state_dir):
            move(self._ln, new_ln)
        self._ln = new_ln

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


class FavoritesManager:
    def __init__(self, a_file):
        self.file_path = a_file

    def add(self, an_item):
        ''' Returns:
                -2 : Error saving file
                -1 : Invalid item
                 0 : Item added
                 1 : Item already in favorites
        '''
        items = self._read_csv()
        url = an_item[1]
        updated = False
        write_it = True

        for i, item in enumerate(an_item):
            if item is None:
                if i in range(0, 2):
                    return -1, '___Station is invalid!___'
                an_item[i] = ''
            if an_item[0] == '' or \
                    an_item[1] == '':
                return -1, '___Station is invalid!___'
        if isinstance(an_item[-1], dict):
            an_item[-1] = an_item[-1]['image']
        msg = None
        for i, item in enumerate(items):
            if item[1] == url:
                if item == an_item:
                    return 1, '___Already in favorites!___'
                if item[0] != an_item[0] or \
                        item[2] != an_item[2] or \
                        item[3] != an_item[3]:
                    items[i] = an_item
                    msg = '___Station updated!___'
                    updated = True
                    break
        if not updated:
            items.append(an_item)
            updated = True
        if updated:
            ret = self._write_csv(items)
            return ret[0], msg if msg else ret[1]
        return 1, '___Already in favorites!___'

    # def remove(self, an_item):
    #     items = self._read_csv()
    #     name = an_item[0]
    #     url = an_item[1]
    #     new_items = [item for item in items if item[0] != name and item[1] != url]

    #     if len(new_items) != len(items):
    #         self._write_csv(new_items)

    def _read_csv(self):
        items = []
        if path.exists(self.file_path):
            try:
                with open(self.file_path, mode='r', newline='', encoding='utf-8') as file:
                    reader = csv.reader(file)
                    for row in reader:
                        if not row[0].startswith('#'):
                            while len(row) < 4:
                                row.append('')
                            name, url, enc, icon = [s.strip() for s in row]
                            items.append([name, url, enc, icon])
            except:
                return []
        return items

    def _write_csv(self, items):
        ''' Returns:
                -2 : Error saving file
                 0 : Item added
        '''
        try:
            with open(self.file_path, mode='w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                writer.writerows(items)
        except:
            return -2, '___Error writing favorites!___'
        return 0, '___Added to favorites!___'

