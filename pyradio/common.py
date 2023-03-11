# -*- coding: utf-8 -*-
import io
import csv
from sys import version as sys_version
from os import rename, remove
from os.path import exists, dirname, join
from copy import deepcopy
from rich import print

PY3 = sys_version[0] == '3'

""" Theming constants """
def FOREGROUND(): return 0
def BACKGROUND(): return 1

# for pop up window
CAPTION = 2
BORDER = 3

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

""" Messages to display when player starts / stops
    Used in log to stop runaway threads from printing
    messages after playback is stopped """
player_start_stop_token = ('Initialization: ',
                           ': Playback stopped',
                           ': Player terminated abnormally!')

def erase_curses_win(self, Y, X, beginY, beginX, char=' ', color=5):
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




class StationsChanges(object):
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
    #   added     - stations added                                          #
    #   changed   - stations changed                                        #
    #   deleted   - stations deleted                                        #
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
            ],

            [
                [0, ['Reggae Dancehall (Ragga Kings)', 'https://raggakings.radio:8443/stream.ogg']]
            ],

            []
        ],

        (0, 9, 1):
        [
            [
                ['0.9.1 Groove Salad Classic (Early 2000s Ambient)', 'https://somafm.com/gsclassic.pls'],
                ['0.9.1 n5MD Radio (Ambient and Experimental)', 'https://somafm.com/n5md.pls'],
                ['0.9.1 Vaporwaves [SomaFM]', 'https://somafm.com/vaporwaves.pls'],
                ['0.9.1 The Trip: [SomaFM]', 'https://somafm.com/thetrip.pls'],
                ['0.9.1 Heavyweight Reggae', 'https://somafm.com/reggae.pls'],
                ['0.9.1 Metal Detector', 'https://somafm.com/metal.pls'],
                ['0.9.1 Synphaera Radio (Space Music)', 'https://somafm.com/synphaera.pls']
            ],

            [
                [0, ['Reggae Dancehall (Ragga Kings)', 'https://raggakings.radio:8443/stream.ogg']]
            ],

            [
                ['0.9.0 Vaporwaves [SomaFM]', 'https://somafm.com/vaporwaves.pls'],
                ['0.9.0 The Trip: [SomaFM]', 'https://somafm.com/thetrip.pls'],
            ]
        ],

        (0, 9, 0):
        [
            [
                ['0.9.0 Groove Salad Classic (Early 2000s Ambient)', 'https://somafm.com/gsclassic.pls'],
                ['0.9.0 n5MD Radio (Ambient and Experimental)', 'https://somafm.com/n5md.pls'],
                ['0.9.0 Vaporwaves [SomaFM]', 'https://somafm.com/vaporwaves.pls'],
                ['0.9.0 The Trip: [SomaFM]', 'https://somafm.com/thetrip.pls'],
                ['0.9.0 Heavyweight Reggae', 'https://somafm.com/reggae.pls'],
                ['0.9.0 Metal Detector', 'https://somafm.com/metal.pls'],
                ['0.9.0 Synphaera Radio (Space Music)', 'https://somafm.com/synphaera.pls']
            ],

            [
                [0, ['Reggae Dancehall (Ragga Kings)', 'https://raggakings.radio:8443/stream.ogg']]
            ],

            []
        ],

        (0, 8, 9):
        [
            [
                ['0.8.9 Groove Salad Classic (Early 2000s Ambient)', 'https://somafm.com/gsclassic.pls'],
                ['0.8.9 n5MD Radio (Ambient and Experimental)', 'https://somafm.com/n5md.pls'],
                ['0.8.9 Vaporwaves [SomaFM]', 'https://somafm.com/vaporwaves.pls'],
                ['0.8.9 The Trip: [SomaFM]', 'https://somafm.com/thetrip.pls'],
                ['0.8.9 Heavyweight Reggae', 'https://somafm.com/reggae.pls'],
                ['0.8.9 Metal Detector', 'https://somafm.com/metal.pls'],
                ['0.8.9 Synphaera Radio (Space Music)', 'https://somafm.com/synphaera.pls']
            ],

            [
                [0, ['Reggae Dancehall (Ragga Kings)', 'https://raggakings.radio:8443/stream.ogg']]
            ],

            []
        ]
    }

    def __init__(self, config):
        self._cnf = config
        self._last_sync_file = join(self._cnf.data_dir, 'last_sync')
        self._asked_sync_file = join(self._cnf.data_dir, 'asked_sync')

        self.PLAYLIST_HAS_NAME_URL = 0
        self.PLAYLIST_HAS_NAME_URL_ENCODING = 1
        self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER = 2



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
                with open(in_file, 'r', encoding='utf-8') as l:
                    line = l.readline().strip()
                    return eval(line)
            except:
                pass
        return None

    def _write_synced_version(self, asked=False):
        out_file = self._asked_sync_file if asked else self._last_sync_file
        try:
            with open(out_file, 'w', encoding='utf-8') as l:
                l.write(str(self.version_changed).replace('(', '').replace(')', ''))
        except:
            pass

    def _open_stations_file(self):
        self._stations = []
        self._stations_file = join(self._cnf.stations_dir, 'stations.csv')
        self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL
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
                                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING
                            except:
                                name, url, enc, onl = [s.strip() for s in row]
                                self._stations.append([name, url, enc, onl])
                                self._read_playlist_version = self._playlist_version = self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER
                except:
                    self._stations = []
                    self._playlist_version = self.PLAYLIST_HAS_NAME_URL
                    return False
            return True
        return False

    def _save_stations_file(self):
        self._out_stations_file = join(self._cnf.stations_dir, 'stations-new.csv')
        self._bck_stations_file = join(self._cnf.stations_dir, 'stations.csv.bck')
        try:
            with open(self._out_stations_file, 'w', encoding='utf-8') as cfgfile:
                writter = csv.writer(cfgfile)
                for a_station in self._stations:
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
        print('File "stations.csv" updated...')
        return True

    def _format_playlist_row_out(self, a_row):
        ''' Return a 2-column if in old format,
            a 3-column row if has encoding, or
            a 4 column row if has online browser flag too '''
        if self._playlist_version == self.PLAYLIST_HAS_NAME_URL_ENCODING_BROWSER:
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

    def check_if_version_needs_sync(self):
        ''' check if we need to sync stations.csv
            takes under consideration the answer
            the user gave at the TUI
        '''
        ret = self.stations_csv_needs_sync(print_messages=False)
        self.asked_sync = self._read_synced_version(asked=True)
        if self.version_changed == self.asked_sync:
            return False
        return ret

    def stations_csv_needs_sync(self, print_messages=True):
        ''' check if we need to sync stations.csv
            it will return true no matter what the user has
            replied about syncing, at the TUI

            Used by update_stations_csv()
        '''
        self.keys = [x for x in self.versions.keys()]
        self.keys.sort()
        # print('keys = {}'.format(self.keys))
        self.last_sync = self._read_synced_version()
        if exists(self._last_sync_file):
            try:
                with open(self._last_sync_file, 'r', encoding='utf-8') as l:
                    line = l.readline().strip()
                    self.last_sync = eval(line)
            except:
                ret = False
            if self.last_sync is None:
                ret = True
            else:
                ret = True if self.keys[-1] > self.last_sync else False
        else:
            ret = True

        if ret and self.last_sync is not None:
            self.keys.reverse()
            while self.keys[-1] <= self.last_sync:
                self.keys.pop()
            self.keys.reverse()
        # print('keys = {}'.format(self.keys))
        self.version_changed = self.keys[-1]
        if print_messages:
            print('Updating "stations.csv"')
            print('Last updated version: {}'.format(self._format_vesion(self.version_changed)))
            print(' Last synced version: {}'.format(self._format_vesion(self.last_sync)))
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

    def update_stations_csv(self):
        ''' update stations.csv '''
        if self.stations_csv_needs_sync(print_messages=True):
            if not self._open_stations_file():
                print('Cannot read "stations.csv"')
                return -1
            # for n in self._stations:
            #     print(n)

            for k in self.keys:
                print('  From version: {}'.format('.'.join(map(str, k))))
                for n in self.versions[k][2]:
                    found = [x for x in self._stations if x[0] == n[0]]
                    if found:
                        for an_item in found:
                            if PY3:
                                print('[red]    --- deleting: "[green]{}[/green]"[/red]'.format(an_item[0]))
                            else:
                                print('    --- deleting: "{}"'.format(an_item[0]))
                            self._stations.pop(self._stations.index(an_item))
                for n in self.versions[k][1]:
                    found = [x for x in self._stations if x[0] == n[1][n[0]]]
                    if found:
                        if PY3:
                            print('[plum4]    +/- updating: "[green]{}[/green]"[/plum4]'.format(found[0][0]))
                        else:
                            print('    +/- updating: "{}"'.format(found[0][0]))
                        index = self._stations.index(found[0])
                        self._stations[index] = self._format_playlist_row_in(n[1])
                for n in self.versions[k][0]:
                    if PY3:
                        print('[magenta]    +++   adding: "[green]{}[/green]"[/magenta]'.format(n[0]))
                    else:
                        print('    +++   adding: "{}"'.format(n[0]))
                    self._stations.append(self._format_playlist_row_in(n))

            if self._save_stations_file():
                self._write_synced_version()

        # print('\n\n\n')
        # for n in self._stations:
        #     print(n)

