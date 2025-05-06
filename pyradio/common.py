# -*- coding: utf-8 -*-
import logging
import locale
import io
import csv
import curses
from os import rename, remove, access, X_OK, getenv, makedirs
from os.path import exists, dirname, join, expanduser
from shutil import which, move, Error as shutil_Error
from rich import print
from enum import IntEnum
from sys import platform

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")

""" Theming constants """
def FOREGROUND():
    return 0
def BACKGROUND():
    return 1

# for pop up window
CAPTION = 2
BORDER = 3

class Station(IntEnum):
    name = 0
    url = 1
    encoding =2
    icon = 3
    profile = 4
    buffering = 5
    http = 6
    volume = 7
    referer = 8

M_STRINGS = {
	'checking-playlist': ' (Checking Playlist)',
	'session-locked': ' (Session Locked)',
	'session-locked-title': 'Session Locked',
	'win-title': 'Your Internet Radio Player',
	'init_': 'Initialization: ',
	'connecting_': 'Connecting to: ',
	'playing_': 'Playing: ',
	'buffering_': 'Buffering: ',
	'station_': 'Station: ',
	'station_buffering': 'Station Buffering',
	'station-open': ' - Opening connection...',
	'selected_player_': 'Selected player: ',
	'down-icon': 'Downloading icon...',
	'player-acivated_': ': Player activated!!!',
	'hist-empty': 'History is empty!!!',
	'hist-first': 'Already at first item!!!',
	'hist-last': 'Already at last item!!!',
    'muted': '[Muted] ',
    'title_': 'Title: ',
    'player-stopped': 'Player is stopped!',
    'plb-stopped': 'Playback stopped',
    'html-player-stopped': '<div class="alert alert-danger">Player is <b>stopped!</b></div>',
	'press-?': ' Press ? for help',
	'error-str': 'error',
	'vol_': 'Vol: ',
    'error-403': 'Server returned "Forbidden" (error 403)',
    'error-404': 'Station does not exist (error 404)',
    'error-503': 'Service not available (error 503)',
    'error-1000': 'Player terminated abnormally! (error 1000)',
    'error-1001': 'Connection failed (error 1001)',
    'error-1002': 'No stream found (error 1002)',
    'error-1003': 'Connection refused (error 1003)',
    'error-1004': 'Unrecognized file format (error 1004)',
    'error-1005': 'DNS Resolution failure (error 1005)',
    'error-1006': 'Server is unreachable (error 1006)',
    'error-1007': 'Permission denied (error 1007)',
    'error-1008': 'Unrecognized file format (error 1008)',
}

""" Messages to display when player starts / stops
    Used in log to stop runaway threads from printing
    messages after playback is stopped """
player_start_stop_token = {
    0:       M_STRINGS['init_'],
    1:       M_STRINGS['plb-stopped'],
    3:       M_STRINGS['player-acivated_'],
    403:     M_STRINGS['error-403'],
    404:     M_STRINGS['error-404'],
    503:     M_STRINGS['error-503'],
    1000:    M_STRINGS['error-1000'],
    1001:    M_STRINGS['error-1001'],
    1002:    M_STRINGS['error-1002'],
    1003:    M_STRINGS['error-1003'],
    1004:    M_STRINGS['error-1004'],
    1005:    M_STRINGS['error-1005'],
    1006:    M_STRINGS['error-1006'],
    1007:    M_STRINGS['error-1007'],
    1008:    M_STRINGS['error-1008'],
}

seconds_to_KB_128 = (
    0, 78, 93, 109, 125, 140, 156, 171, 187, 203, 218, 234,
    250, 265, 281, 296, 312, 328, 343, 359, 375, 390, 406,
    421, 437, 453, 468, 484, 500, 515, 531, 546, 562, 578,
    593, 609, 625, 640, 656, 671, 687, 703, 718, 734, 750,
    765, 781, 796, 812, 828, 843, 859, 875, 890, 906, 921, 937
)

seconds_to_KB_192 = (
    0, 117, 140, 164, 187, 210, 234, 257, 281, 304, 328, 351,
    375, 398, 421, 445, 468, 492, 515, 539, 562, 585, 609, 632,
    656, 679, 703, 726, 750, 773, 796, 820, 843, 867, 890, 914,
    937, 960, 984, 1007, 1031, 1054, 1078, 1101, 1125, 1148, 1171,
    1195, 1218, 1242, 1265, 1289, 1312, 1335, 1359, 1382, 1406
)

seconds_to_KB_320 = (
    0, 195, 234, 273, 312, 351, 390, 429, 468, 507, 546, 585, 625,
    664, 703, 742, 781, 820, 859, 898, 937, 976, 1015, 1054, 1093,
    1132, 1171, 1210, 1250, 1289, 1328, 1367, 1406, 1445, 1484, 1523,
    1562, 1601, 1640, 1679, 1718, 1757, 1796, 1835, 1875, 1914, 1953,
    1992, 2031, 2070, 2109, 2148, 2187, 2226, 2265, 2304, 2343
)


class STATES():
    ANY = -1
    RESET = 0
    INIT = 1
    CONNECT = 2
    PLAY = 10
    TITLE = 11
    STOPPED = 12
    # Do not move it!
    PLAYER_ACTIVATED = 13

    CONNECT_ERROR = 100
    VOLUME = 101
    BUFF_MSG = 102
    BUFFER = 103

    ERROR_NO_PLAYER = 200
    ERROR_DEPENDENCY = 201
    ERROR_CONNECT = 202
    ERROR_START = 203

"""
Format of theme configuration
    Name, color_pair, foreground, background
If foreground == 0, color can be edited
If > 0, get color from list item referred to by number
Same for the background
"""
_param_to_color_id = {
    'Extra Func': (12, ),
    'PyRadio URL': (11, ),
    'Messages Border': (10, ),
    'Status Bar': (8, 9),
    'Stations': (1, 2),
    'Active Station': (3, ),
    'Active Cursor': (6, 7),
    'Normal Cursor': (4, 5),
}

THEME_ITEMS = (
    ('PyRadio URL', 2, 0, 3),
    ('Messages Border', 3, 0, 3),
    ('Status Bar', 7, 0, 0),
    ('Stations', 5, 0, 0),
    ('Active Station', 4, 0, 3),
    ('Normal Cursor', 6, 0, 0),
    ('Active Cursor', 9, 0, 0),
    ('Edit Cursor', 8, 0, 0)
)

def describe_playlist(value):
    # Check if the value is within the range of the enum
    if value < 0 or value >= len(Station.__members__):
        # Return the default message if the value is out of range
        return f"Playlist has {Station.name.name} {Station.url.name}"

    # Collect all names from 0 to the given value
    names = [station.name for station in list(Station)[:value + 1]]

    # Join the names with spaces and return the result
    return f"Playlist has {' '.join(names)}"

def remove_consecutive_empty_lines(input_list):
    cleaned_list = []
    previous_line_empty = False
    # remove empty fields
    work_list = [x for x in input_list if x]
    for line in work_list:
        stripped_line = line.strip()
        if stripped_line:
            cleaned_list.append(line)
            previous_line_empty = False
        elif not previous_line_empty:
            cleaned_list.append('\n')
            previous_line_empty = True
    return cleaned_list

def erase_curses_win(Y, X, beginY, beginX, char=' ', color=5):
    ''' empty a part of the screen
    '''
    empty_win = curses.newwin(
        Y - 2, X - 2,
        beginY + 1, beginX + 1
    )
    empty_win.bkgdset(char, curses.color_pair(color))
    empty_win.erase()
    empty_win.refresh()

def is_rasberrypi():
    ''' Try to detest rasberry pi '''
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r', encoding='utf-8') as m:
            if 'raspberry pi' in m.read().lower():
                return True
    except Exception:
        pass
    return False

    # if exists('/usr/bin/raspi-config'):
    #     return True
    # return False

def hex_to_rgb(hexadecimal):
    n = hexadecimal.lstrip('#')
    return tuple(int(n[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def curses_rgb_to_hex(rgb):
    return rgb_to_hex(tuple(int(y * 255 / 1000) for y in rgb))

def rgb_to_curses_rgb(rgb):
    return tuple(int(y *1000 / 255) for y in rgb)


class StationsChanges():
    '''
    #########################################################################
    #                                                                       #
    #                         stations.csv change                           #
    #                                                                       #
    #########################################################################
    #                                                                       #
    # This section will include the changes of stations.csv                 #
    #                                                                       #
    # version_changed                                                       #
    #   The version the changes appeared (calculated)                       #
    #                                                                       #
    # It will also contain three lists:                                     #
    #   added     - list of stations added                                  #
    #   changed   - list of stations changed                                #
    #   deleted   - list of stations deleted                                #
    #                                                                       #
    # The "changed" list will be of format:                                 #
    #           [[ x , [station name, station url ]]                        #
    # where:                                                                #
    #           x : 0 / 1 index changed (0: name, 1: URL)                   #
    #                                                                       #
    #########################################################################
    '''
    version_changed = None

    '''
    versions = {
        (0, 9, 2):                       # 0.9.2 version
        [
            [...........],                 # added
            [x, [...........]],            # changed
            [...........],                 # deleted
        ],
        (0, 9, 1):                       # 0.9.1 version
        [
            [...........],                 # added
            [x, [...........]],            # changed
            [...........],                 # deleted
        ]
    ]
    '''
    versions = {
        (0, 9, 2):
        [
            [
                ['Groove Salad Classic (Early 2000s Ambient)', 'https://somafm.com/gsclassic.pls'],
                ['n5MD Radio (Ambient and Experimental)', 'https://somafm.com/n5md.pls'],
                ['Vaporwaves [SomaFM]', 'https://somafm.com/vaporwaves.pls'],
                ['The Trip: [SomaFM]', 'https://somafm.com/thetrip.pls'],
                ['Heavyweight Reggae', 'https://somafm.com/reggae.pls'],
                ['Metal Detector', 'https://somafm.com/metal.pls'],
                ['Synphaera Radio (Space Music)', 'https://somafm.com/synphaera.pls']
            ], # added

            [
                [0, ['Reggae Dancehall (Ragga Kings)', 'https://raggakings.radio:8443/stream.ogg']]
            ], # changed

            [] # deleted
        ],

        (0, 9, 3):
        [
            [
                ['Radio Levač (Serbian Folk & Country)', 'http://213.239.205.210:8046/stream'],
                ['Radio 35 (Serbian and English Pop, Folk, Country & Hits)', 'http://stream.radio035.net:8010/listen.pls']
            ], # added
            [], # changed
            [], # deleted
        ],

        (0, 9, 3, 11, 5):
        [
            [], # added
            [
				['DanceUK', 'http://uk2.internet-radio.com:8024/listen.pls'],
				['JazzGroove', r'http://199.180.72.2:8015/listen.pls\?sid\=1'],
				['Metal Detector' 'http://somafm.com/metal.pls'],
            ], # changed
            [
				['Beyond Metal (Progressive - Symphonic)', 'http://streamingV2.shoutcast.com/BeyondMetal'],
				['Vox Noctem: Rock-Goth', 'http://r2d2.voxnoctem.de:8000/voxnoctem.mp3'],
            ], # deleted
        ],
    }

    keys = None
    _stations = None
    _stations_file = None
    _playlist_version = 0

    def __init__(self, config):
        self._cnf = config
        self._last_sync_file = join(self._cnf.state_dir, 'last-sync')
        self._asked_sync_file = join(self._cnf.state_dir, 'asked-sync')

        self.PLAYLIST_HAS_NAME_URL = 0
        self.PLAYLIST_HAS_NAME_URL_ENCODING = 1
        self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON = 2
        self.counts = [0, 0, 0]

    def _read_version(self):
        the_file = join(dirname(__file__), '__init__.py')
        lin = ''
        with open(the_file, 'r', encoding='utf-8') as cfg:
            while not lin.startswith('version_info'):
                lin = cfg.readline().strip()
        lin = lin[15:].replace('(', '').replace(')', '')
        # this_version = tuple(map(int, lin.split(', ')))
        return eval(lin)

    def _read_synced_version(self, asked=False):
        in_file = self._asked_sync_file if asked else self._last_sync_file
        # print('in_file = "{}"'.format(in_file))
        if exists(in_file):
            try:
                with open(in_file, 'r', encoding='utf-8') as sync_file:
                    line = sync_file.readline().strip()
                    return eval(line)
            except:
                pass
        return None

    def write_synced_version(self, asked=False):
        out_file = self._asked_sync_file if asked else self._last_sync_file
        try:
            with open(out_file, 'w', encoding='utf-8') as sync_file:
                sync_file.write(self.version_to_write)
        except:
            return -5 if asked else -6
        return -3 if asked else 0

    def _open_stations_file(self):
        self._stations = []
        self._stations_file = join(self._cnf.stations_dir, 'stations.csv')
        self._playlist_version = self.PLAYLIST_HAS_NAME_URL
        if exists(self._stations_file):
            with open(self._stations_file, 'r', encoding='utf-8') as cfgfile:
                try:
                    for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                        if not row:
                            continue
                        try:
                            name, url = [s.strip() for s in row]
                            self._stations.append([name, url, '', ''])
                        except:
                            try:
                                name, url, enc = [s.strip() for s in row]
                                self._stations.append([name, url, enc, ''])
                                self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING
                            except:
                                name, url, enc, onl = [s.strip() for s in row]
                                self._stations.append([name, url, enc, onl])
                                self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON
                except:
                    self._stations = []
                    self._playlist_version = self.PLAYLIST_HAS_NAME_URL
                    return False
            return True
        return False

    def _save_stations_file(self, print_messages=True):
        self._out_stations_file = join(self._cnf.stations_dir, 'stations-new.csv')
        self._bck_stations_file = join(self._cnf.stations_dir, 'stations.csv.bck')
        try:
            with open(self._out_stations_file, 'w', encoding='utf-8') as cfgfile:
                writter = csv.writer(cfgfile)
                for a_station in self._stations:
                    if a_station[3] != '':
                        a_station[3] = a_station[3]['image']
                    writter.writerow(self._format_playlist_row_out(a_station))
        except:
            print('Error: Cannot create the updated stations file.')
            print('       The updated stations file would be\n         "{}".'.format(self._out_stations_file))
            return False
        ''' rename stations.csv to stations.csv.bck '''
        try:
            rename(self._stations_file, self._bck_stations_file)
        except:
            print('Error: Cannot create the stations backup file.')
            print('       The updated stations file can be found at\n         "{}".'.format(self._out_stations_file))
            return False
        ''' rename stations-new.csv to stations.csv '''
        try:
            rename(self._out_stations_file, self._stations_file)
        except:
            print('Error: Cannot rename the updated stations file.')
            print('       The updated stations file can be found at\n         "{}".'.format(self._out_stations_file))
            print('       The old stations file has been backed up as\n         "{}".'.format(self._bck_stations_file))
            return False
        ''' remove bck file '''
        try:
            remove(self._bck_stations_file)
        except:
            pass
        if print_messages:
            print('File "stations.csv" updated...')
        return True

    def _format_playlist_row_out(self, a_row):
        ''' Return a 2-column if in old format,
            a 3-column row if has encoding, or
            a 4 column row if has online browser flag too '''
        if self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_ICON:
            return a_row
        elif self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING:
            return a_row[:-1]
        else:
            return a_row[:-2]

    def _format_vesion(self, a_version_tuple):
        ret = str(a_version_tuple)
        ret = ret.replace('(', '')
        ret = ret.replace(')', '')
        ret = ret.replace(', ', '.')
        return ret

    def check_if_version_needs_sync(self, stop=None):
        ''' check if we need to sync stations.csv
            takes under consideration the answer
            the user gave at the TUI
        '''
        ret = self.stations_csv_needs_sync(print_messages=False)
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        self.asked_sync = self._read_synced_version(asked=True)
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        if self.version_changed == self.asked_sync:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('asked_sync is equal to version_changed!!!')
            return False
        return ret

    def stations_csv_needs_sync(self, print_messages=True, stop=None):
        ''' check if we need to sync stations.csv
            it will return true no matter what the user has
            replied about syncing, at the TUI

            Used by update_stations_csv()
        '''
        self.keys = [x for x in self.versions]
        self.keys.sort()
        # print('keys = {}'.format(self.keys))
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        self.last_sync = self._read_synced_version()
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        if exists(self._last_sync_file):
            try:
                with open(self._last_sync_file, 'r', encoding='utf-8') as sync_file:
                    line = sync_file.readline().strip()
                    self.last_sync = eval(line)
            except:
                ret = False
            if self.last_sync is None:
                ret = True
            else:
                ret = True if self.keys[-1] > self.last_sync else False
        else:
            if stop is not None:
                if stop():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('asked to stop! Terminating!')
                    return False
            ret = True

        if ret and self.last_sync is not None:
            self.keys.reverse()
            while self.keys[-1] <= self.last_sync:
                self.keys.pop()
            self.keys.reverse()
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        # print('keys = {}'.format(self.keys))
        self.version_changed = self.keys[-1]
        self.version_to_write = str(self.version_changed).replace('(', '').replace(')', '')
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        if print_messages:
            print('Updating "stations.csv"')
            print('Last updated version: {}'.format(self._format_vesion(self.version_changed)))
            print(' Last synced version: {}'.format(self._format_vesion(self.last_sync)))
        if stop is not None:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('asked to stop! Terminating!')
                return False
        if print_messages and not ret:
            print('Already synced: "stations.csv"')
        return ret

    def _format_playlist_row_in(self, a_row):
        ''' Return a 2-column if in old format,
            a 3-column row if has encoding, or
            a 4 column row if has online browser flag too '''
        while len(a_row) < 4:
            a_row.append('')
        return a_row

    def update_stations_csv(self, print_messages=True):
        ''' update stations.csv
            Returns:
                 1 : Update not needed
                 0 : All ok
                -1 : Cannot read stations.csv
                -2 : File not saved


        '''
        # if self.stations_csv_needs_sync(print_messages=print_messages):
        if self.stations_csv_needs_sync(print_messages=False):
            if not self._open_stations_file():
                if print_messages:
                    print('Cannot read "stations.csv"')
                return -1
            # for n in self._stations:
            #     print(n)

            for k in self.keys:
                if print_messages:
                    print('  From version: {}'.format('.'.join(map(str, k))))
                for n in self.versions[k][2]:
                    found = [x for x in self._stations if x[0] == n[0]]
                    if found:
                        for an_item in found:
                            if print_messages:
                                print('[red]    --- deleting: "[green]{}[/green]"[/red]'.format(an_item[0]))
                            self.counts[2] += 1
                            self._stations.pop(self._stations.index(an_item))
                for n in self.versions[k][1]:
                    found = []
                    if n[0] == 0:
                        found = [x for x in self._stations if x[0] == n[1][0] and x[1] != n[1][1]]
                    elif n[0] == 1:
                        found = [x for x in self._stations if x[1] == n[1][1] and x[0] != n[1][0]]
                    if found:
                        if print_messages:
                            print('[plum4]    +/- updating: "[green]{}[/green]"[/plum4]'.format(found[0][0]))
                        self.counts[1] += 1
                        index = self._stations.index(found[0])
                        self._stations[index] = self._format_playlist_row_in(n[1])
                for n in self.versions[k][0]:
                    found = [x for x in self._stations if x[0] == n[0]]
                    if not found:
                        if print_messages:
                            print('[magenta]    +++   adding: "[green]{}[/green]"[/magenta]'.format(n[0]))
                        self.counts[0] += 1
                        self._stations.append(self._format_playlist_row_in(n))

            if self._save_stations_file(print_messages=print_messages):
                ret = self.write_synced_version()
                if ret == -6:
                    if print_messages:
                        txt = '''
[red]Error:[/red] [magenta]PyRadio[/magenta] could not write the "last_sync" file.
This means that although stations have been synced, [magenta]PyRadio[/magenta] will try
to sync them again next time, which means that you may end up with
duplicate stations.

Please close all open programs and documents and create the file
[green]{0}[/green]
and write in it
      "[green]{1}[/green]" (no quotes).
                        '''.format(
                            self._last_sync_file,
                            self.version_to_write
                        )
                        print(txt)

                elif print_messages:
                    print('\n[bold]Summary[/bold]\n[magenta]    +++ added   :[/magenta]  {0}\n[plum4]    +/- updated :[/plum4]  {1}\n[red]    --- deleted :[/red]  {2}'.format(self.counts[0], self.counts[1], self.counts[2]))
                return ret
            return -2
        return 1

        # print('\n\n\n')
        # for n in self._stations:
        #     print(n)

class CsvReadWrite():
    ''' A base class to read and write a PyRadio playlist '''
    _items = None

    encoding_to_remove = None

    def __init__(self, a_file=None):
        self._file = a_file

    @property
    def items(self):
        return self._items

    @items.setter
    def items(self, value):
        self._items = value[:]

    @property
    def version(self):
        return self._version

    @version.setter
    def version(self, value):
        delf._version = value

    @property
    def groups(self):
        if self._items:
            return [i for i,x in enumerate(self._items) if x[1] == '-']
        else:
            return None

    def read(self, a_file=None):
        ''' Reads a PyRadio playlist

            The file is a_file or self._file (if a_file is None)
            Populates self._items and self._version
            Returns True or False (if error)
        '''
        current_version = Station.url
        in_file = a_file if a_file else self._file
        self._items = []
        try:
            with open(in_file, 'r', encoding='utf-8') as cfgfile:
                try:
                    for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
                        if not row:
                            continue

                        # logger.error(f'{row = }')
                        # Initialize variables with default values
                        name = url = enc = icon = volume = http = referer = profile = buffering = ''
                        this_row_version = Station.url
                        # Assign values based on the length of the row
                        row_length = len(row)
                        name = row[0].strip()
                        url = row[1].strip()
                        if row_length > Station.encoding:
                            enc = row[Station.encoding].strip()
                            this_row_version = Station.encoding
                        if row_length > Station.icon:
                            icon = row[Station.icon].strip()
                            this_row_version = Station.icon
                        if row_length > Station.profile:
                            profile = row[Station.profile].strip()
                            this_row_version = Station.profile
                        if row_length > Station.buffering:
                            buffering = row[Station.buffering].strip()
                            this_row_version = Station.buffering
                        if row_length > Station.volume:
                            volume = row[Station.volume].strip()
                            this_row_version = Station.volume
                        if row_length > Station.http:
                            http = row[Station.http].strip()
                            this_row_version = Station.http
                        if row_length > Station.referer:
                            referer = row[Station.referer].strip()
                            this_row_version = Station.referer

                        if buffering:
                            if '@' not in buffering:
                                buffering += '@128'
                        else:
                            buffering = '0@128'

                        if self.encoding_to_remove is not None:
                            if enc == self.encoding_to_remove:
                                enc = ''

                        # Append the parsed values to the reading stations list
                        station_info = [
                            name, url, enc, {'image': icon} if icon else '',
                            profile, buffering, http, volume, referer
                        ]

                        self._items.append(station_info)

                        # Update playlist version based on the presence of optional fields
                        if this_row_version > current_version:
                            current_version = this_row_version
                        self._version = current_version
                except (csv.Error, ValueError):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Playlist is malformed: {e}')
                    self._items = []
                    self._version = current_version
                    return False
        except (FileNotFoundError, IOError) as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Cannot open playlist file: {e}')
            # Handle file not found or IO errors
            self._items = []
            self._version = current_version
            return False
        return True

    def _format_playlist_row(self, a_row):
        ''' Returns a formatted row (list)
            Functionality:
                Removes {'image': '...'}
                Removes '0@128'
                Eliminates any trailing empty fields
        '''
        this_row = a_row[:]
        # Extract the 'image' from the icon dictionary if present
        if len(this_row) > Station.icon and 'image' in this_row[Station.icon]:
            this_row[Station.icon] = this_row[Station.icon]['image']
        if self.encoding_to_remove is not None:
            if this_row[Station.encoding] == self.encoding_to_remove:
                this_row[Station.encoding] = ''

        if len(this_row) > Station.buffering:
            if this_row[Station.buffering] == '0@128':
                this_row[Station.buffering] = ''
        while this_row and this_row[-1] == '':
            this_row.pop()
        return this_row

    def write(self, a_file=None, items=None):
        ''' Saves a PyRadio playlist
        Creates a txt file and write stations in it.
        Then renames it to final target

        Returns   0: All ok
                 -1: Error writing file
                 -2: Error renaming file
        '''
        out_file = a_file if a_file else self._file
        out_items = items if items else self._items
        txt_out_file = out_file.replace('.csv', '.txt')

        try:
            with open(txt_out_file, 'w', encoding='utf-8') as cfgfile:
                writter = csv.writer(cfgfile)
                writter.writerow(['# PyRadio Playlist File Format:'])
                writter.writerow(
                    ['# name', 'url', 'encoding', 'icon',
                     'profile', 'buffering', 'force-http',
                     'volume', 'referer'])
                for a_station in out_items:
                    writter.writerow(self._format_playlist_row(a_station))
        except (IOError, OSError, UnicodeEncodeError) as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Cannot open playlist file for writing: {e}')
            return -1
        try:
            move(txt_out_file, out_file)
        except (shutil.Error, FileNotFoundError, PermissionError) as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Cannot rename playlist file: {e}...')
            return -2
        return 0


class ProfileManager():

    _config_file = None

    def __init__(self):
        pass

    @property
    def config_files(self):
        if self._config_file is None:
            self._config_files = self.get_config_files()
        return self._config_files

    @config_files.setter
    def config_files(self, value):
        self._config_files = vlaue

    def reread_files(self):
        self._config_file = None
        return self.config_files

    @classmethod
    def get_config_files(cls):
        out = {}
        ''' MPV config files '''
        if platform.startswith('win'):
            config_files = [join(getenv('APPDATA'), "mpv", "mpv.conf")]
        else:
            # linux, freebsd, etc.
            xdg_config = getenv('XDG_CONFIG_HOME')
            if xdg_config:
                config_files = [xdg_config + "/mpv/mpv.conf"]
            else:
                config_files = [expanduser("~") + "/.config/mpv/mpv.conf"]
            config_files.append("/etc/mpv/mpv.conf")
            config_files.append("/usr/local/etc/mpv/mpv.conf")
        out['mpv'] = config_files[:]

        ''' MPlayer config files '''
        config_files = [expanduser("~") + "/.mplayer/config"]
        if platform.startswith('win'):
            if exists(r'C:\\mplayer\\mplayer.exe'):
                config_files[0] = r'C:\\mplayer\mplayer\\config'
            elif exists(os.path.join(getenv('USERPROFILE'), "mplayer", "mplayer.exe")):
                config_files[0] = join(getenv('USERPROFILE'), "mplayer", "mplayer", "config")
            elif exists(join(getenv('APPDATA'), "pyradio", "mplayer", "mplayer.exe")):
                config_files[0] = join(getenv('APPDATA'), "pyradio", "mplayer", "mplayer", "config")
            else:
                config_files = []
        else:
            config_files.append("/usr/local/etc/mplayer/mplayer.conf")
            config_files.append('/etc/mplayer/config')
        out['mplayer'] = config_files[:]
        # logger.error(f'{out =  }')
        return out

    def set_vlc_config_file(self, config):
        self._config_files['vlc'] = config

    def all_profiles(self):
        # out = {'mpv': [], 'mplayer': [], 'vlc': []}
        out = {'mpv': [], 'mplayer': []}
        try:
            # for player_name in ('mpv', 'mplayer', 'vlc'):
            for player_name in ('mpv', 'mplayer'):
                profiles = self.profiles(player_name)
                # logger.error('{}: {}'.format(player_name, profiles))
                if profiles:
                    out[player_name] = profiles[:]
        except KeyError:
            pass
        result = self._create_profile_list(out)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'all_profiles: {result = }')
        return result

    def _create_profile_list(self, players_dict):
        # Create a set of profile names for each player
        profile_sets = [set(profiles) for profiles in players_dict.values()]

        # Find the intersection of all profile sets
        common_profiles = set.intersection(*profile_sets)

        # Initialize the result list with common profiles
        result = list(common_profiles)

        # Add profiles that are not common, appending the player name
        for player, profiles in players_dict.items():
            for profile in profiles:
                if profile not in common_profiles:
                    result.append(f'{player}: {profile}')

        return sorted(result)

    def profiles(self, player_name):
        profiles_list = []
        for a_file in self.config_files[player_name]:
            config_list = self._read_a_config_file(a_file)
            if config_list:
                config_list = [ x.strip() for x in config_list ]
                profiles = [ x[1:-1] for x in config_list if x.startswith('[') and x.endswith(']') ]
                if profiles:
                    profiles_list.extend(profiles)
        profiles_list = list(set(profiles_list))
        profiles_list = [ x for x in profiles_list if x != 'pyradio-volume' and x != 'silent']
        return sorted(profiles_list)

    def _read_a_config_file(self, config_file):
        # Read config file
        if not exists(config_file):
            return []
        try:
            with open(config_file, 'r', encoding='utf-8') as file:
                ret = [line.lstrip() if line.strip() else line for line in file.readlines()]
        except Exception as e:
            ret = []
        return ret

    def _write_config_file(self, config_file, a_string=None, a_list=None):
        try:
            makedirs(dirname(config_file), exist_ok=True)
            with open(config_file, 'w', encoding='utf-8') as file:
                if a_string is None:
                    file.writelines(a_list)
                else:
                    file.write(a_string)
            return True
        except (FileNotFoundError, PermissionError, IsADirectoryError,
                UnicodeEncodeError, OSError, IOError):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Error writing profile [{}] in "{}"'.format(profile_name, config_file))
            return False

    def save_volume(self, player_name, profile_name, volume):
        ''' save volume value in a profile

            Parameters
                player_name         : string
                profile_name        : string
                volume              : any

            Returns
                profile_name        : if success
                None                : if failure
        '''
        # logger.error('before profile name: "{}"'.format(profile_name))
        config_file = self.config_files[player_name][0]
        if profile_name.startswith('[') and \
                profile_name.endswith(']'):
            profile_name = profile_name[1:-1]
        # logger.error('after  profile name: "{}"'.format(profile_name))
        if not exists(config_file):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(
                    '[{}] file not found! Adding profile [{}] with volume {}\n\n'.format(
                        config_file, profile_name, volume
                    )
                )
            makedirs(dirname(config_file), exist_ok=True)
            return self.append_to_config(player_name, profile_name, 'volume=' + str(volume))

        else:
            config_string = self._read_a_config_file(config_file)
            # logger.error(f'{config_file = }')
            # logger.error(f'before remove {config_string = }')
            if '[' + profile_name + ']' in config_string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('[{}] profile found!\n\n'.format(profile_name))
                config_list = remove_consecutive_empty_lines(config_string.split('\n'))
                config_string = '\n'.join(config_list)
                # logger.error(f'after  remove {config_string = }')
                # find all lines starting with '['
                indexes = [i for i, x  in enumerate(config_list) if x.startswith('[')]
                # logger.error(f'{indexes = }')
                # get [profile_name] index
                profile_index = config_list.index('[' + profile_name + ']')
                # logger.error(f'{profile_index = }')
                volume_adjusted = False
                for i in range(profile_index+1, len(config_list)):
                    # logger.error('checking "{}"'.format(config_list[i]))
                    if config_list[i].startswith('volume='):
                        config_list[i] = 'volume=' + str(volume)
                        volume_adjusted = True
                        break
                    elif i in indexes:
                        # volume not found in profile
                        break
                if not volume_adjusted:
                    config_list[profile_index] += '\nvolume={}\n'.format(volume)
                config_list = ['\n' + x if x.startswith('[') else x for x in config_list]
                # logger.error('\n\n')
                # for n in config_list:
                #     logger.error(f'"{n}"')
                # logger.error(config_list)
                # logger.error('\n'.join(config_list))
                # logger.error('\n\n')
                ret = self._write_config_file(config_file, a_string='\n'.join(config_list) + '\n\n')
                if ret:
                    return profile_name
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Error writing profile [{}] in "{}"'.format(profile_name, config_file))
                    return None
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('[{}] profile not found! Adding it with volume'.format(profile_name))
                return self.append_to_config(player_name, profile_name, 'volume=' + str(volume))

    def write_silenced_profile(self, player_name):
        self.add_to_config(player_name, 'silent', 'volume=0')

    def add_to_config(self, player_name, profile_name, profile_string):
        ''' appends a profile to the user's player config file
            it is a wrapper function for append_to_config

            checks if profile already exists in user's config file

            Paramaters
                player_name         : string
                profile_name        : string
                profile_contents    : string

            Returns
                profile_name        : if success or profile exists
                None                : if failure

        '''
        for i, config_file in enumerate(self.config_files[player_name]):
            if exists(config_file):
                config_string = self._read_a_config_file(config_file)
                if '[' + profile_name + ']' in config_string:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('[{}] profile found!'.format(profile_name))
                    return profile_name

        ''' profile not found in config
            create a default profile
        '''
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'No [{profile_name}] profile found!')
        # fix for #229
        base_path = dirname(self.config_files[player_name][0])
        if not exists(base_path):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Dir created: "{base_path}')
            makedirs(base_path)
        ret = self.append_to_config(player_name, profile_name, profile_string)
        if ret is None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Cannot wirte [{}] profile in: "{}"'.format(profile_name, self.config_files[player_name][0]))
        return ret

    def append_to_config(self, player_name, profile_name, profile_contents):
        ''' appends a profile to the user's player config file

            Paramaters
                player_name         : string
                profile_name        : string
                profile_contents    : string

            Returns
                profile_name        : if success
                None                : if failure
        '''
        try:
            config_file = self.config_files[player_name][0]

            # Read the current contents of the config file
            config_list = self._read_a_config_file(config_file)

            # append new profile
            if profile_name and profile_contents:
                config_list.append('[' + profile_name + ']\n')
                config_list.append(profile_contents + '\n\n')

            # Remove consecutive empty lines, leaving at least one
            cleaned_list = remove_consecutive_empty_lines(config_list)

            # Write back the updated list to the config file
            self._write_config_file(config_file, a_list=cleaned_list)
            profile = profile_name
        except (FileNotFoundError, PermissionError, IsADirectoryError,
                UnicodeEncodeError, OSError, IOError):
            profile = None
        return profile

    def copy_profile_with_new_volume(self, player_name, existing_profile, new_profile, volume):
        ''' copy a profile and chnge the volume in the new profile

            Parameters:
                player_name         : the player
                existing_profile    : the source profile
                new_profile         : the new profile
                volume              : volume value

            if new_profile exists, it will be overwritten

            Returns:
                new_profile         : success
                None                : failed to write the file
        '''
        if existing_profile:
            existing_profile = existing_profile.replace('[', '').replace(']', '')
        new_profile = new_profile.replace('[', '').replace(']', '')

        # Read config file
        out_file = self.config_files[player_name][0]
        config_file = self.config_files[player_name][0]
        config_list = self._read_a_config_file(config_file)

        # Extract existing profile section if it exists
        existing_section = None
        if existing_profile:
            # Find existing profile section
            section = []
            in_section = False
            for line in config_list:
                stripped = line.strip()
                if stripped == f'[{existing_profile}]':
                    in_section = True
                    section.append(line)
                elif in_section:
                    if stripped.startswith('['):
                        break
                    section.append(line)
            if in_section:
                existing_section = section

        # Create or update the new profile section
        if existing_section:
            # Update volume in copied section
            new_section = []
            volume_found = False
            for line in existing_section:
                stripped = line.strip()
                if stripped.startswith('volume='):
                    new_section.append(f'volume={volume}\n')
                    volume_found = True
                else:
                    new_section.append(line)
            if not volume_found:
                new_section.append(f'volume={volume}\n')
            # Rename profile
            new_section[0] = f'[{new_profile}]\n'
        else:
            # Create new section
            new_section = [f'[{new_profile}]\n', f'volume={volume}\n']

        # Remove existing new_profile entries
        cleaned_config = []
        skip = False
        for line in config_list:
            stripped = line.strip()
            if stripped == f'[{new_profile}]':
                skip = True
            elif skip:
                if stripped.startswith('['):
                    skip = False
                    cleaned_config.append(line)
            else:
                cleaned_config.append(line)

        # Add new profile section
        cleaned_config += ['\n'] + new_section

        # Clean up formatting
        # cleaned_config = ['\n' + x if x.startswith('[') else x for x in cleaned_config]
        cleaned_config = remove_consecutive_empty_lines(cleaned_config)

        # Write back to file
        ret = self._write_config_file(out_file, a_list=cleaned_config)
        if ret:
            return new_profile
        else:
            logger.error(f"Error saving {player_name} config: {str(e)}")
            return None


def validate_resource_opener_path(a_file):
    # Check if the file exists
    if not exists(a_file):
        # If the file doesn't exist, try to find it using shutil.which
        full_path = which(a_file)
        if full_path is None:
            return None
        else:
            a_file = full_path
    # Check if the file is executable
    if not access(a_file, X_OK):
        return None
    # Return the validated path
    return a_file
