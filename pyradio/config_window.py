# -*- coding: utf-8 -*-
import curses
from copy import deepcopy
from textwrap import wrap
import glob
import csv
from os import path, sep
from sys import platform

from .common import *
from .window_stack import Window_Stack_Constants
from .cjkwrap import cjklen
#from .cjkwrap import PY3, is_wide, cjklen
from .encodings import *
from .themes import *
import logging

logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

class PyRadioConfigWindow(object):
    n_u = Window_Stack_Constants

    parent = None
    _win = None

    _title = 'PyRadio Configuration'

    selection = __selection = 1

    """ Keep a copy of saved values for theme and transparency
        Work-around for 'T' auto save (trasnsparency), and
        's'/Space them saving """
    _old_use_transparency = False
    _old_theme = ''

    _headers = []

    _num_of_help_lines = 0
    _help_text = []
    _help_text.append(None)
    _help_text.append(['Specify the player to use with PyRadio, or the player detection order.', '|',
    'This is the eqivelant to the -u , --use-player command line option.', '|',
    'Example:', '  player = vlc', 'or', '  player = vlc,mpv, mplayer', '|',
    'Default value: mpv,mplayer,vlc'])
    _help_text.append(['This is the playlist to open at start up, if none is specified.', '|',
    'This is the equivalent to the -s , --stations command line option.', '|',
    'Default value: stations'])
    _help_text.append(['The station number within the default playlist to play.', '|',
    'This is the equivalent to the -p , --play command line option.', '|',
    'Value is 1..number of stations, "False" means no auto play, "Random" means play a random station.', '|', 'Default value: False'])
    _help_text.append(['This is the encoding used by default when reading data provided by a station such as song title, etc. If reading said data ends up in an error, "utf-8" will be used instead.', '|',
    'If changed, playback must be restarted so that changes take effect.',
    '|', 'Default value: utf-8'])
    _help_text.append(None)
    _help_text.append(['PyRadio will wait for this number of seconds to get a station/server message indicating that playback has actually started.', '|',
    'If this does not happen within this number of seconds after the connection is initiated, PyRadio will consider the station unreachable, and display the "Failed to connect to: station" message.', '|', 'Press "h"/Left or "l"/Right to change value.',
    '|', 'Valid values: 5 - 60', 'Default value: 10'])
    _help_text.append(['Most radio stations use plain old http protocol to broadcast, but some of them use https.', '|', 'If this parameter is enabled, all connections will use http; results depend on the combination of station/player.', '|', 'This value is read at program startup, use "z" to change its effect while mid-session.',
    '|', 'Default value: False'])
    _help_text.append(None)
    _help_text.append(['The theme to be used by default.', '|',
    'This is the equivalent to the -t , --theme command line option.', '|',
    'If a theme uses more colors than those supported by the terminal in use, the "dark" theme will be used instead (but the "light" theme will be used, if the "light_16colors" theme was requested but not supported).',
    '|', 'Default value = dark'])
    _help_text.append(['If False, theme colors will be used.', '|',
    "If True and a compositor is running, the stations' window background will be transparent.", '|', "If True and a compositor is not running, the terminal's background color will be used.", '|', 'Default value: False'])
    _help_text.append(None)
    _help_text.append(['Specify whether you will be asked to confirm every station deletion action.',
    '|', 'Default value: True'])
    _help_text.append(['Specify whether you will be asked to confirm playlist reloading, when the playlist has not been modified within Pyradio.',
    '|', 'Default value: True'])
    _help_text.append(['Specify whether you will be asked to save a modified playlist whenever it needs saving.', '|', 'Default value: False'])

    def __init__(self, parent, config,
            toggle_transparency_function,
            show_theme_selector_function):
        self.parent = parent
        self._cnf = config
        self._toggle_transparency_function = toggle_transparency_function
        self._show_theme_selector_function = show_theme_selector_function
        self._saved_config_options = deepcopy(config.opts)
        self._config_options = deepcopy(config.opts)
        self._old_theme = self._config_options['theme'][1]
        if logger.isEnabledFor(logging.INFO):
            if self._saved_config_options == self._config_options:
                logger.info('Saved options loaded')
            else:
                logger.info('Altered options loaded')
        self.number_of_items = len(self._config_options) - 2
        for i, n in enumerate(list(self._config_options.values())):
            if n[1] == '':
                self._headers.append(i)
        self.init_config_win()
        self.refresh_config_win()
        self._old_use_transparency = self._config_options['use_transparency'][1]

    def __del__(self):
        self._toggle_transparency_function = None

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, val):
        self.__parent = val
        self.init_config_win()

    @property
    def selection(self):
        return self.__selection

    @selection.setter
    def selection(self, val):
        if val < 1:
            val = len(self._headers) - 1
        elif val >= self.number_of_items:
            val = 1
        if val in self._headers:
            self.__selection = val + 1
        else:
            self.__selection = val
        #self.refresh_config_win()

    def init_config_win(self):
        self._win = None
        self.maxY, self.maxX = self.__parent.getmaxyx()
        self._second_column = int(self.maxX / 2 )
        self._win = curses.newwin(self.maxY, self.maxX, 1, 0)
        self._populate_help_lines()

    def refresh_config_win(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._print_title()
        #self._win.addstr(0,
        #    int((self.maxX - len(self._title)) / 2),
        #    self._title,
        #    curses.color_pair(4))
        min_lines = len(self._config_options)
        if min_lines < self._max_number_of_help_lines:
            min_lines = self._max_number_of_help_lines
        if self.maxX < 80 or self.maxY < min_lines + 3:
            self.too_small = True
        else:
            self.too_small = False
        if self.too_small:
            msg = 'Window too small to display content!'
            if self.maxX < len(msg) + 2:
                msg = 'Window too small!'
            try:
                self._win.addstr(int(self.maxY / 2),
                    int((self.maxX - len(msg)) / 2),
                    msg, curses.color_pair(5))
            except:
                pass
        else:
            self._win.addstr(1, self._second_column, 'Option Help', curses.color_pair(4))
        self.refresh_selection()

    def _print_title(self):
        if self._config_options == self._saved_config_options and \
            self._old_theme == self._saved_config_options['theme'][1] and \
            self._old_use_transparency == self._saved_config_options['use_transparency'][1]:
            dirty_title = '─ '
        else:
            dirty_title = ' *'
        X = int((self.maxX - len(self._title) - 1) / 2)
        try:
            self._win.addstr(0, X, dirty_title, curses.color_pair(3))
        except:
            self._win.addstr(0, X, dirty_title.encode('utf-8'), curses.color_pair(3))
        self._win.addstr(self._title + ' ', curses.color_pair(4))

    def refresh_selection(self):
        self._print_title()
        if not self.too_small:
            for i, it in enumerate(list(self._config_options.values())):
                if i < self.number_of_items:
                    if i == self.__selection:
                        col = hcol = curses.color_pair(6)
                        self._print_options_help()
                    else:
                        col = curses.color_pair(5)
                        hcol = curses.color_pair(4)
                    hline_width = self._second_column - 2
                    self._win.hline(i+1, 1, ' ', hline_width, col)
                    if i in self._headers:
                        self._win.addstr(i+1, 1, it[0], curses.color_pair(4))
                    else:
                        self._win.addstr(i+1, 3, it[0], col)
                        if isinstance(it[1], bool):
                            self._win.addstr('{}'.format(it[1]), hcol)
                        else:
                            if it[1] is None:
                                # random station
                                self._win.addstr('{}'.format('Random'), hcol)
                            else:
                                self._win.addstr('{}'.format(it[1][:self._second_column - len(it[0]) - 6 ]), hcol)
        self._win.refresh()

    def _get_col_line(self, ind):
        if ind < self._headers:
            self._column = 3
            self._line = ind + 2
        else:
            self._column = self._second_column + 2
            self._line = ind - self._headers + 2

    def _put_cursor(self, jump):
        self.__selection += jump
        if jump > 0:
            if self.__selection in self._headers:
                self.__selection += 1
            if self.__selection >= self.number_of_items:
                self.__selection = 1
        else:
            if self.__selection in self._headers:
                self.__selection -= 1
            if self.__selection < 1:
                self.__selection = self.number_of_items - 1

    def _populate_help_lines(self):
        self._help_lines = []
        self._max_number_of_help_lines = 0
        for z in self._help_text:
            if z is None:
                self._help_lines.append(None)
            else:
                all_lines = []
                for k in z:
                    lines = []
                    lines = wrap(k, self.maxX - self._second_column - 2)
                    all_lines.extend(lines)
                self._help_lines.append(all_lines)
                if len(all_lines) > self._max_number_of_help_lines:
                    self._max_number_of_help_lines = len(all_lines)

    def _print_options_help(self):
        for i, x in enumerate(self._help_lines[self.selection]):
            if i + 2 == self.maxY:
                break
            self._win.addstr(i+2, self._second_column, ' ' * (self._second_column - 1), curses.color_pair(5))
            self._win.addstr(i+2, self._second_column, x.replace('|',''), curses.color_pair(5))
        if len(self._help_lines[self.selection]) < self._num_of_help_lines:
            for i in range(len(self._help_lines[self.selection]), self._num_of_help_lines):
                try:
                    self._win.addstr(i+2, self._second_column, ' ' * (self._second_column - 1), curses.color_pair(5))
                except:
                    pass
        self._num_of_help_lines = len(self._help_lines[self.selection])
        """
        # Uncomment if trouble with help lines
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('self._num_of_help_lines = {}'.format(self._num_of_help_lines))
        """

    def _load_default_values(self):
        self._config_options[ 'general_title' ][1] = ''
        self._config_options[ 'player' ][1] = 'mpv,mplayer,vlc'
        self._config_options[ 'default_playlist' ][1] = 'stations'
        self._config_options[ 'default_station' ][1] = 'False'
        self._config_options[ 'default_encoding' ][1] = 'utf-8'
        self._config_options[ 'connection_timeout' ][1] = '10'
        self._config_options[ 'theme_title' ][1] = ''
        # Transparency
        #self._old_use_transparency = self._config_options['use_transparency'][1]
        self._config_options[ 'use_transparency' ][1] = False
        self._config_options[ 'force_http' ][1] = False
        self._toggle_transparency_function(changed_from_config_window=True, force_value=False)
        self._config_options[ 'playlist_manngement_title' ][1] = ''
        self._config_options[ 'confirm_station_deletion' ][1] = True
        self._config_options[ 'confirm_playlist_reload' ][1] = True
        self._config_options[ 'auto_save_playlist' ][1] = False
        self._config_options[ 'requested_player' ][1] = ''
        # Theme
        # Put this AFTER applying transparency, so that _do_init_pairs in
        # _toggle_transparency does not overwrite pairs with applied theme values
        self._config_options['theme'][1] = 'dark'
        self._apply_a_theme('dark', False)
        self._check_if_config_is_dirty()

    def _check_if_config_is_dirty(self):
        if self._config_options == self._saved_config_options:
            self._config_options[ 'dirty_config' ] = [ '', False ]
        else:
            self._config_options[ 'dirty_config' ] = [ '', True ]

    def _apply_a_theme(self, a_theme, use_transparency=None):
        theme = PyRadioTheme(self._cnf.stations_dir)
        theme.readAndApplyTheme(a_theme, use_transparency=use_transparency)
        theme = None
        curses.doupdate()

    def keypress(self, char):
        if self.too_small:
            return 1, []
        val = list(self._config_options.items())[self.selection]
        if val[0] == 'connection_timeout':
            if char in (curses.KEY_RIGHT, ord('l')):
                t = int(val[1][1])
                if t < 60:
                    t += 1
                    self._config_options[val[0]][1] = str(t)
                    self._win.addstr(self.selection+1,
                        3 + len(val[1][0]),
                        str(t) + ' ', curses.color_pair(6))
                    self._print_title()
                    self._win.refresh()
                return -1, []

            elif char in (curses.KEY_LEFT, ord('h')):
                t = int(val[1][1])
                if t > 5:
                    t -= 1
                    self._config_options[val[0]][1] = str(t)
                    self._win.addstr(self.selection+1,
                        3 + len(val[1][0]),
                        str(t) + ' ', curses.color_pair(6))
                    self._print_title()
                    self._win.refresh()
                return -1, []
        if char in (ord('k'), curses.KEY_UP):
            self._put_cursor(-1)
            self.refresh_selection()
        elif char in (ord('j'), curses.KEY_DOWN):
            self._put_cursor(1)
            self.refresh_selection()
        elif char in (curses.KEY_NPAGE, ):
            if self.__selection + 4 >= self.number_of_items and \
                    self.__selection < self.number_of_items - 1:
                self.__selection = self.number_of_items - 5
            self._put_cursor(4)
            self.refresh_selection()
        elif char in (curses.KEY_PPAGE, ):
            if self.__selection - 4 < 1 and self.__selection > 1:
                self.__selection = 5
            self._put_cursor(-4)
            self.refresh_selection()
        elif char in (ord('g'), curses.KEY_HOME):
            self.__selection = 1
            self.refresh_selection()
        elif char in (ord('G'), curses.KEY_END):
            self.__selection = self.number_of_items - 1
            self.refresh_selection()
        elif char in (ord('d'), ):
            self._load_default_values()
            self.refresh_selection()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Default options loaded')
        elif char in (ord('r'), ):
            old_theme = self._config_options[ 'theme' ][1]
            old_transparency = self._config_options[ 'use_transparency' ][1]
            self._config_options = deepcopy(self._saved_config_options)
            # Transparency
            self._config_options[ 'use_transparency' ][1] = self._old_use_transparency
            self._toggle_transparency_function(changed_from_config_window=True, force_value=self._old_use_transparency)
            # Theme
            # Put it after applying transparency, so that saved color_pairs
            # do not get loaded instead of active ones
            self._config_options[ 'theme' ][1] = self._old_theme
            self._saved_config_options[ 'theme' ][1] = self._old_theme
            self._apply_a_theme(self._config_options[ 'theme' ][1], self._old_use_transparency)
            self.refresh_selection()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Saved options loaded')
        elif char in (curses.KEY_EXIT, 27, ord('q'), ord('h'), curses.KEY_LEFT):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                #self._config_options['theme'][1] = self._old_theme
                self._saved_config_options['theme'][1] = self._old_theme
                self._cnf.opts['theme'][1] = self._old_theme
                self._cnf.theme = self._old_theme
                return 1, []
        elif char in (ord('s'), ):
            self._old_theme = self._config_options['theme'][1]
            self._saved_config_options = deepcopy(self._config_options)
            if self._cnf.opts != self._saved_config_options:
                # check if player has changed
                if self._cnf.opts[ 'player' ][1] != self._saved_config_options[ 'player' ][1]:
                    self._cnf.player_changed = True
                    self._cnf.player_values = [ self._cnf.opts[ 'player' ][1], self._saved_config_options[ 'player' ][1] ]
                self._cnf.opts = deepcopy(self._saved_config_options)
                self._old_theme == self._saved_config_options['theme'][1]
                self._config_options = deepcopy(self._cnf.opts)
                self._cnf.dirty_config = True
            else:
                self._cnf.dirty_config = False
            # save and exit
            return 0, [1]
        elif char in (curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord(' '), ord('l'), curses.KEY_RIGHT):
            # alter option value
            vals = list(self._config_options.items())
            sel = vals[self.selection][0]
            if sel == 'player':
                return self.n_u.SELECT_PLAYER_MODE, []
            elif sel == 'default_encoding':
                return self.n_u.SELECT_ENCODING_MODE, []
            elif sel == 'theme':
                self._cnf.theme = self._old_theme
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('DE\n\nshowing theme self._cnf.theme = {}\n\n'.format(self._cnf.theme))
                self._show_theme_selector_function()
            elif sel == 'default_playlist':
                return self.n_u.SELECT_PLAYLIST_MODE, []
            elif sel == 'default_station':
                return self.n_u.SELECT_STATION_MODE, []
            elif sel == 'confirm_station_deletion' or \
                    sel == 'confirm_playlist_reload' or \
                    sel == 'auto_save_playlist' or \
                    sel == 'force_http':
                self._config_options[sel][1] = not self._config_options[sel][1]
                self.refresh_selection()
            elif sel == 'use_transparency':
                #self._old_use_transparency = not self._config_options[ 'use_transparency' ][1]
                self._toggle_transparency_function(changed_from_config_window=True,
                        force_value=not self._config_options[ 'use_transparency' ][1])
                self.refresh_selection()
        return -1, []

class PyRadioSelectPlayer(object):

    maxY = 6
    maxX = 25
    selection = [ 0, 0 ]

    _title = ' Player Selection '

    _win = None

    if platform == 'win32':
        _players =  ( 'mplayer', 'vlc' )
    else:
        _players =  ( 'mpv', 'mplayer', 'vlc' )
    _working_players = [ [], [] ]

    # REMINDER: column 1 is     acive players - displayed right
    #           column 0 is available players - displayed left
    _column = 1

    def __init__(self, maxY, maxX, player):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.player = player
        self._orig_player = player
        self._populate_working_players()
        self._validate_column()
        self.init_window()

    def init_window(self):
        self._win = None
        self._win = curses.newwin(self.maxY, self.maxX,
                int((self._parent_maxY - self.maxY) / 2),
                int((self._parent_maxX - self.maxX) / 2))

    def refresh_win(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(0,
            int((self.maxX - len(self._title)) / 2),
            self._title,
            curses.color_pair(4))
        self._win.addstr(1, 2, 'Supported' , curses.color_pair(4))
        self._win.addstr(1, int(self.maxX / 2 + 2), 'Active' , curses.color_pair(4))
        self.refresh_selection()

    def refresh_selection(self):
        for i in range(2, self.maxY - 1):
            self._win.hline(i, 1, ' ', self.maxX - 2, curses.color_pair(5))

        if self._working_players[0]:
            if self.selection[0] >= len(self._working_players[0]):
                self.selection[0] = 0
            for i, pl in enumerate(self._working_players[0]):
                col =curses.color_pair(5)
                if self.selection[0] == i:
                    if self._column == 0:
                        col = curses.color_pair(6)
                        self._win.hline(i+2, int(self.maxX / 2) + 1, ' ', int(self.maxX / 2) - 1, col)
                self._win.addstr(i+2, int(self.maxX / 2 + 2), pl, col)

        if self._working_players[1]:
            if self.selection[1] >= len(self._working_players[1]):
                self.selection[1] = 0
            for i, pl in enumerate(self._working_players[1]):
                col = curses.color_pair(5)
                if self.selection[1] == i:
                    if self._column == 1:
                        col = curses.color_pair(6)
                        self._win.hline(i+2, 1, ' ', int(self.maxX / 2) - 1, col)
                self._win.addstr(i+2, 2, pl, col)

        for i in range(1, self.maxY - 1):
            try:
                self._win.addch(i, int(self.maxX / 2), '│', curses.color_pair(3))
            except:
                self._win.addstr(i, int(self.maxX / 2), u'│'.encode('utf-8'), curses.color_pair(3))
        try:
            self._win.addch(self.maxY - 1, int(self.maxX / 2), '┴', curses.color_pair(3))
        except:
            self._win.addstr(self.maxY - 1, int(self.maxX / 2), u'┴'.encode('utf-8'), curses.color_pair(3))

        self._win.refresh()

    def refresh_and_resize(self, maxY, maxX):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.init_window()
        self.refresh_win()

    def _populate_working_players(self, these_players=''):
        if these_players:
            self._working_players[0] = these_players.replace(' ', '').split(',')
        else:
            self._working_players[0] = self._orig_player.replace(' ', '').split(',')
        self._working_players[1] = []
        for i, pl in enumerate(self._players):
            if pl not in self._working_players[0]:
                self._working_players[1].append(pl)

    def keypress(self, char):
        if char in (9, ):
            new_column = self._switch_column()
            if self._working_players[new_column]:
                self._column = new_column
                self.refresh_selection()

        elif char in (curses.KEY_RIGHT, ord('l')):
            if self._column == 0:
                if self._working_players[0]:
                    item = self._working_players[0][self.selection[0]]
                    self._working_players[0].remove(item)
                    self._working_players[0].append(item)
                    self.refresh_selection()

        elif char in (curses.KEY_UP, ord('k')):
            if self._working_players[self._column]:
                self.selection[self._column] -= 1
                if self.selection[self._column] == -1:
                    self.selection[self._column] = len(self._working_players[self._column]) - 1
                self.refresh_selection()

        elif char in (curses.KEY_DOWN, ord('j')):
            if self._working_players[self._column]:
                self.selection[self._column] += 1
                if self.selection[self._column] == len(self._working_players[self._column]):
                    self.selection[self._column] = 0
                self.refresh_selection()

        elif char in (curses.KEY_EXIT, 27, ord('q'), curses.KEY_LEFT, ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                return 1, []

        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
            ord(' '), ord('l'), curses.KEY_RIGHT):
            other_column = self._switch_column()
            this_item = self._working_players[self._column][self.selection[self._column]]
            self._working_players[self._column].remove(this_item)
            self._working_players[other_column].append(this_item)
            self._validate_column()
            self.refresh_selection()

        elif char == ord('r'):
            self._populate_working_players()
            self.refresh_selection()

        elif char == ord('s'):
            if self._working_players[0]:
                self.player = ','.join(self._working_players[0])
                return 0, self._working_players[0]
        return -1, []

    def _switch_column(self):
        col = (1, 0)
        return col[self._column]

    def setPlayers(self, these_players):
        self.player = these_players
        self._populate_working_players(these_players)
        self._validate_column()

    def _validate_column(self):
        if not self._working_players[self._column]:
            self._column = self._switch_column()

class PyRadioSelectEncodings(object):
    max_enc_len = 15

    _win = None

    _title = ' Encoding Selection '

    _num_of_columns = 4
    maxY = maxX = 10
    _column = _row = 0

    _encodings = []
    list_maxY = 0
    startPos = 0
    selection = 0

    _invalid = []

    def __init__(self, maxY, maxX, encoding, config_encoding):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.encoding = encoding
        self._orig_encoding = encoding
        self._config_encoding = config_encoding
        self._orig_encoding = encoding
        self._encodings = get_encodings()
        self._num_of_rows = int(len(self._encodings) / self._num_of_columns)
        self.init_window()

    def init_window(self, set_encoding=True):
        self._win = None
        self._win = curses.newwin(self.maxY, self.maxX,
                int((self._parent_maxY - self.maxY) / 2) + 1,
                int((self._parent_maxX - self.maxX) / 2))
        if set_encoding:
            self.setEncoding(self.encoding, init=True)

    def _fix_geometry(self):
        self._num_of_columns = int((self._parent_maxX - 2) / (self.max_enc_len + 2 ))
        if self._num_of_columns > 8:
            self._num_of_columns = 8
        elif self._num_of_columns > 4:
            self._num_of_columns = 4

        self.maxY = int(len(self._encodings) / self._num_of_columns) + 5
        if len(self._encodings) % self._num_of_columns > 0:
            self.maxY += 1
        if self._num_of_columns == 8:
            maxY = int(len(self._encodings) / 6) + 5
            if len(self._encodings) % 6 > 0:
                maxY += 1
            if maxY < self._parent_maxY:
                self.maxY = maxY
                self._num_of_columns = 6
        while self.maxY > self._parent_maxY - 2:
            self.maxY -= 1
        self.list_maxY = self.maxY - 5
        self.maxX = self._num_of_columns * (self.max_enc_len + 2) + 2
        # Enable this to see geometry
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('maxY,maxX = {0},{1}'.format(self.maxY, self.maxX))
        #    logger.debug('Number of columns = {}'.format(self._num_of_columns))
        #    logger.debug('Number of rows = {}'.format(self._num_of_rows))
        #    logger.debug('Number of visible rows = {}'.format(self.list_maxY))

    def refresh_win(self, set_encoding=True):
        """ set_encoding is False when resizing """
        self._fix_geometry()
        self.init_window(set_encoding)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(0,
            int((self.maxX - len(self._title)) / 2),
            self._title,
            curses.color_pair(4))
        for i in range(1, self.maxX - 1):
            try:
                self._win.addch(self.maxY - 4,  i, '─', curses.color_pair(3))
            except:
                self._win.addstr(self.maxY - 4, i, u'─'.encode('utf-8'), curses.color_pair(3))
        try:
            self._win.addch(self.maxY - 4, 0, '├', curses.color_pair(3))
            self._win.addch(self.maxY - 4, self.maxX - 1, '┤', curses.color_pair(3))
        except:
            self._win.addstr(self.maxY - 4,  0, u'├'.encode('utf-8'), curses.color_pair(3))
            self._win.addstr(self.maxY - 4,  self.maxX - 1, u'┤'.encode('utf-8'), curses.color_pair(3))

        self._num_of_rows = int(len(self._encodings) / self._num_of_columns)
        self._get_invalids()
        self.refresh_selection()

    def refresh_selection(self):
        if self._parent_maxX < 4 * (self.max_enc_len + 2) + 2 or self.maxY < 10:
            self._too_small = True
        else:
            self._too_small = False
        if self._too_small:
            msg = 'Window too small to display content!'
            if self.maxX - 2 < len(msg):
                msg = 'Window too small!'
            self._win.hline(self.maxY - 4, 1, ' ', self.maxX - 2, curses.color_pair(5))
            try:
                self._win.addch(self.maxY - 4, 0, '│', curses.color_pair(3))
                self._win.addch(self.maxY - 4, self.maxX - 1, '│', curses.color_pair(3))
            except:
                self._win.addstr(self.maxY - 4,  0, u'│'.encode('utf-8'), curses.color_pair(3))
                self._win.addstr(self.maxY - 4,  self.maxX - 1, u'│'.encode('utf-8'), curses.color_pair(3))
            self._win.addstr(int(self.maxY / 2),
                int((self.maxX - len(msg)) / 2),
                msg, curses.color_pair(5))

        else:
            self._win.hline(self.maxY - 3, 1, ' ', self.maxX - 2, curses.color_pair(5))
            self._win.hline(self.maxY - 2, 1, ' ', self.maxX - 2, curses.color_pair(5))

            self._set_startPos()
            for i in range(0, self._num_of_columns):
                for y in range(0, self.list_maxY):
                    xx = i * self.max_enc_len + 2 + i * 2
                    yy = y + 1
                    pos = self.startPos + i * self._num_of_rows + y
                    if i > 0: pos += i
                    if pos == self.selection:
                        if self._encodings[self.selection][0] == self._orig_encoding:
                            col = curses.color_pair(9)
                        else:
                            col = curses.color_pair(6)
                        self._win.addstr(self.maxY - 3, 1, ' ' * (self.maxX - 2), curses.color_pair(4))
                        self._win.addstr(self.maxY - 3, 2, '   Alias: ', curses.color_pair(4))
                        self._win.addstr(self._encodings[pos][1][:self.maxX - 14], curses.color_pair(5))
                        self._win.addstr(self.maxY - 2, 1, ' ' * (self.maxX - 2), curses.color_pair(4))
                        self._win.addstr(self.maxY - 2, 2, 'Language: ', curses.color_pair(4))
                        self._win.addstr(self._encodings[pos][2][:self.maxX - 14], curses.color_pair(5))
                    else:
                        col = curses.color_pair(5)
                        if pos < len(self._encodings):
                            if self._encodings[pos][0] == self._orig_encoding:
                                col = curses.color_pair(4)
                    self._win.addstr(yy, xx -1, ' ' * (self.max_enc_len + 2), col)
                    if pos < len(self._encodings):
                        self._win.addstr(yy, xx, self._encodings[pos][0], col)

        self._win.refresh()

    def refresh_and_resize(self, maxY, maxX):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.refresh_win(set_encoding=False)
        self._resize()

    def _get_invalids(self):
        self._invalid = []
        col = self._num_of_columns - 1
        row = self._num_of_rows
        b = self._col_row_to_selection(col, row)
        while b >= len(self._encodings):
            self._invalid.append((col, row))
            row -= 1
            b = self._col_row_to_selection(col, row)

    def _set_startPos(self):
        try:
            if self.list_maxY == self._num_of_rows + 1:
                self.startPos = 0
        except:
            pass
        if self.startPos < 0:
            self.startPos = 0

    def _resize(self, init=False):
        col, row = self._selection_to_col_row(self.selection)
        if not (self.startPos <= row <= self.startPos + self.list_maxY - 1):
            while row > self.startPos:
                self.startPos += 1
            while row < self.startPos + self.list_maxY - 1:
                self.startPos -= 1
        ''' if the selection at the end of the list,
            try to scroll down '''
        if init and row > self.list_maxY:
            new_startPos = self._num_of_rows - self.list_maxY + 1
            if row > new_startPos:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('setting startPos at {}'.format(new_startPos))
                self.startPos = new_startPos
        self.refresh_selection()

    def setEncoding(self, this_encoding, init=False):
        ret = self._is_encoding(this_encoding)
        if ret == -1:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('encoding "{}" not found, reverting to "utf-8"'.format(this_encoding))
            self.encoding = 'utf-8'
            self.selection = self._is_encoding(self.encoding)
        else:
            self.selection = ret
            self.encoding = this_encoding
        self._resize(init)

    def _is_encoding(self, a_string):
        def in_alias(a_list, a_string):
            splited = a_list.split(',')
            for n in splited:
                if n.strip() == a_string:
                    return True
            return False
        for i, an_encoding in enumerate(self._encodings):
            if a_string == an_encoding[0] or in_alias(an_encoding[1], a_string):
                return i
        return -1

    def _fix_startPos(self, direction=1):
        col, row = self._selection_to_col_row(self.selection)
        startRow = self.startPos
        endRow = self.startPos + self.list_maxY - 1
        if not (startRow <= row <= endRow):
            self.startPos = self.startPos + direction
            if direction > 0:
                #if self.startPos >= self.list_maxY or row == 0:
                if row == 0:
                    self.startPos = 0
                else:
                    self._resize()
            elif direction < 0:
                if row == self._num_of_rows - 2 or row == self._num_of_rows:
                    self.startPos = self._num_of_rows - self.list_maxY + 1
                elif self.startPos < 0:
                    self._resize(init=True)
            if self.startPos < 0:
                self.startPos = 0

    def _selection_to_col_row(self, sel):
        x = int(sel / (self._num_of_rows+1))
        y = sel % (self._num_of_rows +1)
        return x, y

    def _col_row_to_selection(self, a_column, a_row):
        return (self._num_of_rows + 1) * a_column + a_row

    def keypress(self, char):
        if char in (ord('c'), ):
            self.encoding = self._config_encoding
            self.setEncoding(self.encoding, init=True)

        elif char in (ord('r'), ):
            self.encoding = self._orig_encoding
            self.setEncoding(self.encoding, init=True)

        elif char in (curses.KEY_UP, ord('k')):
            self.selection -= 1
            if self.selection < 0:
                self.selection = len(self._encodings) - 1
            self._fix_startPos(-1)
            self.refresh_selection()

        elif char in (curses.KEY_DOWN, ord('j')):
            self.selection += 1
            if self.selection == len(self._encodings):
                self.selection = 0
            self._fix_startPos(1)
            self.refresh_selection()

        elif char in (curses.KEY_RIGHT, ord('l')):
            self._column, self._row = self._selection_to_col_row(self.selection)
            self._column += 1
            if self._column == self._num_of_columns:
                self._column = 0
                self._row += 1
                if self._row == self._num_of_rows:
                    self._row = 0
            if (self._column, self._row) in self._invalid:
                self._column = 0
                self._row += 1
                if self._row > self._num_of_rows:
                    self._row = 0
            self.selection = self._col_row_to_selection(self._column, self._row)
            self._fix_startPos(1)
            self.refresh_selection()

        elif char in (curses.KEY_LEFT, ord('h')):
            self._column, self._row = self._selection_to_col_row(self.selection)
            self._column -= 1
            if self._column == -1:
                self._column = self._num_of_columns - 1
                self._row -= 1
            if (self._column, self._row) in self._invalid:
                self._column -= 1
            self.selection = self._col_row_to_selection(self._column, self._row)
            self._fix_startPos(-1)
            self.refresh_selection()

        elif char in (curses.KEY_NPAGE, ):
            if self.selection == len(self._encodings) -1:
                self.selection = 0
            else:
                self.selection += 5
                if self.selection > len(self._encodings) - 1:
                    self.selection = len(self._encodings) - 1
            self._fix_startPos(5)
            self.refresh_selection()

        elif char in (curses.KEY_PPAGE, ):
            if self.selection == 0:
                self.selection = len(self._encodings) - 1
            else:
                self.selection -= 5
                if self.selection < 0:
                    self.selection = 0
            self._fix_startPos(-5)
            self.refresh_selection()

        elif char in (curses.KEY_HOME, ord('g')):
            self.selection = 0
            self.startPos = 0
            self.refresh_selection()

        elif char in (curses.KEY_END, ord('G')):
            self.selection = len(self._encodings) - 1
            self.startPos = self._num_of_rows - self.list_maxY + 1
            self.refresh_selection()

        elif char in (curses.KEY_EXIT, 27, ord('q'), curses.KEY_LEFT, ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                return 1, ''

        elif char in (curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord(' '), ord('s')):
            return 0, self._encodings[self.selection][0]

        return -1, ''

class PyRadioSelectPlaylist(object):
    _win = None

    _title = ' Playlist Selection '

    maxY = maxX = _parent_maxY = _parent_maxX = 0

    _items = []
    _registers_path = None

    startPos = 0
    selection = 0
    _selected_playlist_id = 0

    _select_playlist_error = -2

    pageChange = 5
    jumpnr = ''

    # offset to current item for padding calculation
    pad_adjustment = 0

    def __init__(self, parent, config_path, default_playlist, include_registers=False):
        """ Select a playlist from a list

        include_registers changes its behavior

        If it is False (default), it is used by config window
        and permit playlist only selection.
        Returns: state, playlist title

        if it is True, it is used in \p (paste) function and
        permits playlist and register selection.
        default_playlist is removed from the list.
        Returns: state, playlist/register path
        """
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        try:
            self._parent_Y, _ = parent.getbegyx()
        except:
            # revert to old behavior
            self._parent_Y = 1
        self._config_path = config_path
        self.playlist = default_playlist
        self._orig_playlist = default_playlist
        self._selected_playlist = default_playlist
        self._include_registers = include_registers
        #self._include_registers = True
        if self._include_registers:
            self._title = ' Paste: Select target '
            self._playlist_in_editor = self._selected_playlist
        self.init_window()

    def __del__(self):
        self._error_win = None
        self._items = None

    def init_window(self):
        self._read_items()
        self.maxY = self._num_of_items + 2
        if self.maxY > self._parent_maxY - 2:
            self.maxY = self._parent_maxY - 2
        self._calculate_width()
        self._win = None
        Y = int((self._parent_maxY - self.maxY) / 2) + self._parent_Y
        X = int((self._parent_maxX - self.maxX) / 2)
        self._win = curses.newwin(self.maxY, self.maxX, Y, X)

    def refresh_and_resize(self, parent_maxYX):
        self._parent_maxY = parent_maxYX[0]
        self._parent_maxX = parent_maxYX[1]
        self.init_window()
        self.refresh_win(resizing=True)

    def _calculate_width(self):
        self.maxX = self._max_len + 5 + len(str(self._num_of_items))
        max_title = len(self._title) + 8
        if self.maxX < max_title:
            self.maxX = max_title
        if self.maxX > self._parent_maxX - 4:
            self.maxX = self._parent_maxX - 4

    def refresh_win(self, resizing=False):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self._title)) / 2),
            self._title,
            curses.color_pair(4)
        )
        if resizing:
            self._resize()
        self.refresh_selection(resizing)

    def refresh_selection(self, resizing=False):
        pad = len(str(self.startPos + self.maxY - 2 - self.pad_adjustment))
        #logger.error('DE \n\npos = {0}, pad = {1}\n\n'.format(self.startPos + self.maxY - 2 - self.pad_adjustment, pad))
        for i in range(0, self.maxY - 2):
            #logger.error('de i = {0}, startPos = {1}'.format(i, self.startPos))
            if i + self.startPos < self._num_of_items:
                line, pad = self._format_line(i, pad)
                colour = self._get_color(i)
                self._win.hline(i + 1, 1, ' ', self.maxX - 2, colour)
                self._win.addstr(i + 1, 1, line[:self.maxX - 3], colour)
            else:
                break
        self._win.refresh()
        if not resizing:
            if self._select_playlist_error > -2:
                self.print_select_playlist_error()

    def _resize(self):
        if self.maxY - 2 == self._num_of_items:
            self.startPos = 0
        else:
            self._fix_startPos()

    def _get_color(self, i):
        col = curses.color_pair(5)
        if self._items[i + self.startPos] == self._orig_playlist:
            if i + self.startPos == self._selected_playlist_id:
                col = curses.color_pair(9)
            else:
                col = curses.color_pair(4)
        elif i + self.startPos == self._selected_playlist_id:
            col = curses.color_pair(6)
        return col

    def _format_line(self, i, pad):
        """ PyRadioSelectPlaylist format line """
        line = '{0}. {1}'.format(
            str(i + self.startPos + 1).rjust(pad),
            self._items[i + self.startPos]
        )
        return line, pad

    def _read_items(self):
        self._items = []
        self._items = glob.glob(path.join(self._config_path, '*.csv'))
        if len(self._items) > 0:
            self._items.sort()
        if self._include_registers:
            self._registers_path = path.join(self._config_path, '.registers')
            if platform == 'win32':
                self._registers_path.replace('.reg', '_reg')
            r_items = glob.glob(path.join(self._registers_path, '*.csv'))
            if r_items:
                r_items.sort()
                self._items.extend(r_items)
        if len(self._items) == 0:
            return 0, -1
        for i, an_item in enumerate(self._items):
            if self._include_registers:
                self._items[i] = an_item.replace(self._registers_path + sep, '').replace('.csv', '').replace('register_', 'Register: ')
                self._items[i] = self._items[i].replace(self._config_path + sep, '')
            else:
                self._items[i] = an_item.replace(self._config_path + sep, '').replace('.csv', '')
        if self._include_registers:
            """ Remove playlist in editor """
            try:
                self._items.remove(self._playlist_in_editor)
            except ValueError:
                pass
        else:
            """ get already loaded playlist id """
            for i, a_playlist in enumerate(self._items):
                if a_playlist ==self._selected_playlist:
                    self._selected_playlist_id = i
                    break
        self._max_len = cjklen(max(self._items, key=cjklen))
        self._num_of_items = len(self._items)

    def setPlaylist(self, a_playlist, adjust=True):
        old_id = self._selected_playlist_id
        self._selected_playlist = a_playlist
        if a_playlist == 'False':
            self._selected_playlist_id = 0
        elif a_playlist == 'random' or a_playlist == 'Random' or a_playlist is None:
            self._selected_playlist_id = 1
        for i, a_playlist in enumerate(self._items):
            if a_playlist == self._selected_playlist:
                self._selected_playlist_id = i
                break
        else:
            self.setPlaylistById(0, adjust)
            self.startPos = 0
            self._selected_playlist = self._items[self._selected_playlist_id]
            return
        if adjust:
            self._fix_startPos()
        self.refresh_selection()

    def setPlaylistById(self, an_id, adjust=True):
        old_id = self._selected_playlist_id
        self._selected_playlist_id = an_id
        if self._selected_playlist_id == self._num_of_items:
            self._selected_playlist_id = 0
        elif self._selected_playlist_id < 0:
            self._selected_playlist_id = self._num_of_items - 1
            #self._selected_playlist = self._items[self._selected_playlist_id]
        if adjust:
            self._fix_startPos()
        self._selected_playlist = self._items[self._selected_playlist_id]
        self.refresh_selection()

    def _get_result(self):
        if self._include_registers:
            if self._items[self._selected_playlist_id].startswith('Register: '):
                ret = self._items[self._selected_playlist_id].replace('Register: ', 'register_')
                ret = path.join(self._config_path, '.registers', ret + '.csv')
            else:
                ret = path.join(self._config_path, self._items[self._selected_playlist_id] + '.csv')
            if platform == 'win32':
                ret.replace('.registers', '_registers')
            return 0, ret

        stationFile = path.join(self._config_path, self._items[self._selected_playlist_id] + '.csv')
        self._select_playlist_error = 0
        with open(stationFile, 'r') as cfgfile:
            try:
                for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    try:
                        name, url = [s.strip() for s in row]
                        self._select_playlist_error = 1
                    except ValueError:
                        try:
                            name, url, enc = [s.strip() for s in row]
                            self._select_playlist_error = 1
                        except ValueError:
                            try:
                                name, url, enc, br = [s.strip() for s in row]
                                self._select_playlist_error = 1
                            except ValueError:
                                self._select_playlist_error = -1
                                break
            except:
                self._select_playlist_error = -1
        if self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            self.print_select_playlist_error()
            return -1, ''
        else:
            return 0, self._items[self._selected_playlist_id]

    def print_select_playlist_error(self):
        if self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            if self._select_playlist_error == 0:
                msg = 'This playlist is empty!'
            else:
                msg = 'This playlist is corrupt!'
            self._error_win = curses.newwin(5, 38,
                    int((self._parent_maxY - 5)/ 2) + 1,
                    int((self._parent_maxX - 38) / 2))
            self._error_win.bkgdset(' ', curses.color_pair(3))
            self._error_win.erase()
            self._error_win.box()
            self._error_win.addstr(0, 16, ' Error ', curses.color_pair(4))
            self._error_win.addstr(1, 2, msg, curses.color_pair(5))
            self._error_win.addstr(2, 2, 'Please select another playlist...', curses.color_pair(5))
            self._error_win.addstr(4, 14, ' Press any key to hide ', curses.color_pair(3))
            self._error_win.refresh()

    def _fix_startPos(self):
        if self._num_of_items < self.maxY - 2:
            self.startPos = 0
            return
        if self._selected_playlist_id < self.maxY - 2:
            if self._selected_playlist_id < 0:
                self._selected_playlist_id = 0
            self.startPos = 0
        elif self._selected_playlist_id >= self._num_of_items:
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
        elif self._selected_playlist_id > self._num_of_items - self.maxY + 2:
            self.startPos = self._num_of_items - self.maxY + 2
        else:
            self.startPos = self._selected_playlist_id - int((self.maxY - 2) / 2)

    def keypress(self, char):
        """ Return restlt from playlist selection window

        Results are:
        -1, ''              - Continue in window
         0, station title   - selected station title (for config window)
         0, station path    - selected station path (for paste window)
         1, ''              - Cancel
        """
        if self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            self._error_win = None
            self._select_playlist_error = -2
            self.refresh_selection()

        elif char == ord('M'):
            if self._num_of_items > 0:
                self.setPlaylistById(int(self._num_of_items / 2) - 1)
                #self._put_selection_in_the_middle(force=True)
                self.refresh_selection()

        elif char in (ord('r'), ):
            self.setPlaylist(self._orig_playlist)

        elif char in (curses.KEY_EXIT, 27, ord('q'), curses.KEY_LEFT, ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                self._select_playlist_error = -2
                return 1, ''

        elif char in (curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord(' '), ord('l'), curses.KEY_RIGHT):
            return self._get_result()

        elif char in (curses.KEY_DOWN, ord('j')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id + 1, adjust=False)
                if self._selected_playlist_id == 0:
                    self.startPos = 0
                elif self.startPos + self.maxY - 2 == self._selected_playlist_id:
                    self.startPos += 1
                self.refresh_selection()

        elif char in (curses.KEY_UP, ord('k')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id - 1, adjust=False)
                if self._selected_playlist_id == self._num_of_items - 1:
                    self.startPos = self._num_of_items - self.maxY + 2
                    if self.startPos < 0:
                        self.startPos = 0
                elif self.startPos > self._selected_playlist_id:
                    self.startPos = self._selected_playlist_id
                self.refresh_selection()

        elif char in (curses.KEY_PPAGE, ):
            self.jumpnr = ''
            if self._num_of_items > 0:
                old_id = self._selected_playlist_id
                self._selected_playlist_id -= self.pageChange
                if old_id == 0:
                    self._selected_playlist_id = self._num_of_items - 1
                    self.startPos = self._num_of_items - self.maxY + 2
                elif self._selected_playlist_id < 0:
                    self._selected_playlist_id = 0
                    self.startPos = 0
                else:
                    if not (self.startPos < self._selected_playlist_id < self.startPos + self.maxY - 2):
                        self.startPos = old_id - self.pageChange
                        if self.startPos > self._num_of_items - self.maxY + 2:
                            self.startPos = self._num_of_items - self.maxY + 2
                self.refresh_selection()

        elif char in (curses.KEY_NPAGE, ):
            self.jumpnr = ''
            old_id = self._selected_playlist_id
            self._selected_playlist_id += self.pageChange
            if old_id == self._num_of_items - 1:
                self._selected_playlist_id = 0
                self.startPos = 0
            elif self._selected_playlist_id >= self._num_of_items:
                self._selected_playlist_id = self._num_of_items - 1
                self.startPos = self._num_of_items - self.maxY + 2
            else:
                if not (self.startPos < self._selected_playlist_id < self.startPos + self.maxY - 2):
                    self.startPos = old_id + self.pageChange
                    if self.startPos > self._num_of_items - self.maxY + 2:
                        self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in (curses.KEY_HOME, ord('g')):
            self.jumpnr = ''
            self._selected_playlist_id = 0
            self.startPos = 0
            self.refresh_selection()

        elif char in (curses.KEY_END, ):
            self.jumpnr = ''
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in (ord('G'), ):
            if self.jumpnr:
                try:
                    if type(self) is PyRadioSelectStation:
                        jump = int(self.jumpnr) + 1
                    else:
                        jump = int(self.jumpnr) - 1
                    self.setPlaylistById(jump)
                    self.jumpnr = ''
                    return -1, ''
                except:
                    pass
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in map(ord,map(str,range(0,10))):
            if self._num_of_items > 0:
                self.jumpnr += chr(char)
        else:
            self.jumpnr = ""

        return -1, ''

class PyRadioSelectStation(PyRadioSelectPlaylist):

    _default_playlist = ''

    def __init__(self, parent, config_path, default_playlist, default_station):
        self._default_playlist = default_playlist
        self._orig_default_playlist = default_playlist
        if logger.isEnabledFor(logging.INFO):
            logger.info('displaying stations from: "{}"'.format(default_playlist))
        PyRadioSelectPlaylist.__init__(self, parent, config_path, default_station)
        self._title = ' Station Selection '
        # adding 2 to padding calculation (i.e. no selection and random selection
        self.pad_adjustment = 2

    def update_playlist_and_station(self, a_playlist, a_station):
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('default_playlist = {0}\norig_playlist = {1}\nselected_playlist = {2}\nplaylist = {3}'.format(self._default_playlist, self._orig_playlist, self._selected_playlist, self.playlist))
        self._default_playlist = a_playlist
        self._orig_playlist = a_station
        self._selected_playlist = a_station
        self.playlist = a_station
        self._read_items()

    def setStation(self, a_station):
        if a_station == 'False':
            self._selected_playlist_id = 0
            self.startPos = 0
            self.refresh_selection()
        elif a_station == 'random' or a_station == 'Random' or a_station is None:
            self._selected_playlist_id = 1
            self.startPos = 0
            self.refresh_selection()
        else:
            try:
                pl = int(a_station) + 1
                self.setPlaylistById(pl)
                return
            except:
                self.setPlaylist(a_station)

    def _get_result(self):
        if self._selected_playlist_id == 0:
            return 0, 'False'
        elif self._selected_playlist_id == 1:
            return 0, 'Random'
        else:
            return 0, str(self._selected_playlist_id - 1)

    def _read_items(self):
        self._items = []
        stationFile = path.join(self._config_path, self._default_playlist + '.csv')
        if path.exists(stationFile):
            with open(stationFile, 'r') as cfgfile:
                try:
                    for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                        if not row:
                            continue
                        try:
                            name, _ = [s.strip() for s in row]
                        except ValueError:
                            try:
                                name, _, _ = [s.strip() for s in row]
                            except ValueError:
                                name, _, _, _ = [s.strip() for s in row]
                        self._items.append(name)
                except:
                    pass
            self._items.reverse()
        self._items.append('Play a Random station on startup')
        self._items.append('Do not play a station on startup')
        self._items.reverse()
        self._num_of_items = len(self._items)
        self._max_len = cjklen(max(self._items, key=cjklen))

    def _get_color(self, i):
        or_pl = self._orig_playlist
        if self._orig_playlist == 'False':
            or_pl = -1
        elif self._orig_playlist == 'random' or \
                self._orig_playlist == 'Random' or \
                self._orig_playlist is None:
            or_pl = 0
        col = curses.color_pair(5)
        if i + self.startPos == int(or_pl) + 1:
            if i + self.startPos == self._selected_playlist_id:
                col = curses.color_pair(9)
            else:
                col = curses.color_pair(4)
        elif i + self.startPos == self._selected_playlist_id:
            col = curses.color_pair(6)
        return col

    def _format_line(self, i, pad):
        """ PyRadioSelectStation format line """
        fixed_pad = pad
        if i + self.startPos < 2:
            line = '{0}  {1}'.format(' '.rjust(fixed_pad),
                self._items[i + self.startPos])
        else:
            line = '{0}. {1}'.format(str(i + self.startPos - 1).rjust(fixed_pad),
                    self._items[i + self.startPos])
        return line, pad

    def keypress(self, char):
        if char in (ord('r'), ):
            self.setStation(self._orig_playlist)
            return -1, ''

        return PyRadioSelectPlaylist.keypress(self, char)

# pymode:lint_ignore=W901
