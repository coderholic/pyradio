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
from .config import SUPPORTED_PLAYERS
from .encodings import *
from .themes import *
from .simple_curses_widgets import SimpleCursesLineEdit, SimpleCursesHorizontalPushButtons
import logging
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale


logger = logging.getLogger(__name__)


class PyRadioConfigWindow(object):
    n_u = Window_Stack_Constants

    parent = None
    _win = None

    _title = 'PyRadio Configuration'

    selection = __selection = 1

    ''' Keep a copy of saved values for theme and transparency
        Work-around for 'T' auto save (trasnsparency), and
        's'/Space them saving
    '''
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
    _help_text.append(['If this options is enabled, the mouse can be used to scroll the playlist, start, stop and mute the player, adjust its volume etc.', '|', 'Mouse support is highly terminal dependent, that\'s why it is disabled by default.', '|', 'Default value: False'])
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
                 show_theme_selector_function,
                 save_parameters_function,
                 reset_parameters_function
                 ):
        self.parent = parent
        self._cnf = config
        self._toggle_transparency_function = toggle_transparency_function
        self._show_theme_selector_function = show_theme_selector_function
        self._save_parameters_function = save_parameters_function
        self._reset_parameters_function = reset_parameters_function
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

        self._cnf.get_player_params_from_backup()

        ''' Config window parameters check '''
        # logger.error('DE \n\ncheck params\n{0}\n{1}'.format(self._cnf.saved_params, self._cnf.params))
        for a_key in self._cnf.saved_params.keys():
            if self._cnf.saved_params[a_key] != self._cnf.params[a_key]:
                self._cnf.dirty_config = True

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
        self._second_column = int(self.maxX / 2)
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
                self._win.addstr(
                    int(self.maxY / 2),
                    int((self.maxX - len(msg)) / 2),
                    msg, curses.color_pair(5))
            except:
                pass
        else:
            self._win.addstr(1, self._second_column, 'Option Help', curses.color_pair(4))
        self.refresh_selection()

    def _print_title(self):
        if self._cnf.dirty_config:
            dirty_title = ' *'
        else:
            if self._config_options == self._saved_config_options and \
                self._old_theme == self._saved_config_options['theme'][1] and \
                    self._old_use_transparency == self._saved_config_options['use_transparency'][1] and not self._cnf.params_changed:
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
                                ''' random station '''
                                self._win.addstr('{}'.format('Random'), hcol)
                            else:
                                self._win.addstr('{}'.format(it[1][:self._second_column - len(it[0]) - 6]), hcol)
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
        '''
        Uncomment if trouble with help lines
        '''
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('self._num_of_help_lines = {}'.format(self._num_of_help_lines))

    def _load_default_values(self):
        self._config_options['general_title'][1] = ''
        self._config_options['player'][1] = 'mpv,mplayer,vlc'
        self._config_options['default_playlist'][1] = 'stations'
        self._config_options['default_station'][1] = 'False'
        self._config_options['default_encoding'][1] = 'utf-8'
        self._config_options['enable_mouse'][1] = 'False'
        self._config_options['connection_timeout'][1] = '10'
        self._config_options['theme_title'][1] = ''
        ''' Transparency '''
        #self._old_use_transparency = self._config_options['use_transparency'][1]
        self._config_options['use_transparency'][1] = False
        self._config_options['force_http'][1] = False
        self._toggle_transparency_function(changed_from_config_window=True, force_value=False)
        self._config_options['playlist_manngement_title'][1] = ''
        self._config_options['confirm_station_deletion'][1] = True
        self._config_options['confirm_playlist_reload'][1] = True
        self._config_options['auto_save_playlist'][1] = False
        self._config_options['requested_player'][1] = ''
        ''' Theme
            Put this AFTER applying transparency, so that _do_init_pairs in
            _toggle_transparency does not overwrite pairs with applied theme values
        '''
        self._config_options['theme'][1] = 'dark'
        self._apply_a_theme('dark', False)
        self._check_if_config_is_dirty()

    def _check_if_config_is_dirty(self):
        if self._config_options == self._saved_config_options:
            self._config_options['dirty_config'] = ['', False]
        else:
            self._config_options['dirty_config'] = ['', True]

    def _apply_a_theme(self, a_theme, use_transparency=None):
        theme = PyRadioTheme(self._cnf)
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
                    self._win.addstr(
                        self.selection+1,
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
                    self._win.addstr(
                        self.selection+1,
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
            old_theme = self._config_options['theme'][1]
            old_transparency = self._config_options['use_transparency'][1]
            self._config_options = deepcopy(self._saved_config_options)
            ''' Transparency '''
            self._config_options['use_transparency'][1] = self._old_use_transparency
            self._toggle_transparency_function(
                changed_from_config_window=True,
                force_value=self._old_use_transparency)
            ''' Theme
                Put it after applying transparency, so that saved color_pairs
                do not get loaded instead of active ones
            '''
            self._config_options['theme'][1] = self._old_theme
            self._saved_config_options['theme'][1] = self._old_theme
            self._apply_a_theme(self._config_options['theme'][1], self._old_use_transparency)
            self._reset_parameters_function()
            self.refresh_selection()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Saved options loaded')
        elif char in (curses.KEY_EXIT, 27, ord('q'), ord('h'), curses.KEY_LEFT):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
                #self._config_options['theme'][1] = self._old_theme
                self._saved_config_options['theme'][1] = self._old_theme
                self._cnf.opts['theme'][1] = self._old_theme
                self._cnf.theme = self._old_theme
                return 1, []
        elif char in (ord('s'), ):
            ''' save and exit '''
            self._old_theme = self._config_options['theme'][1]
            if self._saved_config_options['enable_mouse'][1] == self._config_options['enable_mouse'][1]:
                self.mouse_support_option_changed = False
            else:
                self.mouse_support_option_changed = True
            self._saved_config_options = deepcopy(self._config_options)
            if self._cnf.opts != self._saved_config_options:
                ''' check if player has changed '''
                if self._cnf.opts['player'][1] != self._saved_config_options['player'][1]:
                    self._cnf.player_changed = True
                    self._cnf.player_values = [self._cnf.opts['player'][1], self._saved_config_options['player'][1]]
                self._cnf.opts = deepcopy(self._saved_config_options)
                self._old_theme == self._saved_config_options['theme'][1]
                self._config_options = deepcopy(self._cnf.opts)
                self._cnf.dirty_config = True
            else:
                self._cnf.dirty_config = False
            self._save_parameters_function()
            return 0, [1]
        elif char in (
                curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord(' '), ord('l'), curses.KEY_RIGHT):
            ''' alter option value '''
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
                    sel == 'enable_mouse' or \
                    sel == 'auto_save_playlist' or \
                    sel == 'force_http':
                self._config_options[sel][1] = not self._config_options[sel][1]
                self.refresh_selection()
            elif sel == 'use_transparency':
                #self._old_use_transparency = not self._config_options[ 'use_transparency' ][1]
                self._toggle_transparency_function(
                    changed_from_config_window=True,
                    force_value=not self._config_options['use_transparency'][1]
                )
                self.refresh_selection()
        return -1, []


class PyRadioExtraParams(object):
    ''' Class to display extra player parameters on
        main window. No editing allowed!
    '''

    def __init__(self,
                 config,
                 parent):
        ''' setting editing to 0 so that help functions work '''
        self.editing = 0
        self._max_lines = 16
        self._note_text = ' Note '
        self._note_line1 = 'Changes made here wil not be'
        self._note_line2 = 'saved in the configuration file'
        self._extra = None
        self._cnf = config
        self._parent = parent
        self._win = None
        self._title = ' Player Extra Parameters '
        self._too_small_str = 'Window too small'
        self._cnf.get_player_params_from_backup(param_type=1)
        self._redisplay()

    @property
    def params(self):
        return self._extra._working_params

    @params.setter
    def params(self, val):
        raise ValueError('property is read only')

    def set_parrent(self, window):
        self._parent = window
        self._redisplay()

    def _redisplay(self):
        pY, pX = self._parent.getmaxyx()
        if pY < self._max_lines + 2 or pX < 30:
            self._too_small = True
            self._win = curses.newwin(
                3, len(self._too_small_str) + 4,
                int((pY - 3) / 2) + 2,
                int((pX - len(self._too_small_str)) / 2)
            )
            self.show()
        else:
            self._too_small = False
            self.maxX = pX - 2 if pX < 40 else 40
            self._win = curses.newwin(
                self._max_lines, self.maxX,
                int((pY - self._max_lines) / 2) + 2,
                int((pX - self.maxX) / 2)
            )
        if self._extra:
            self._extra.set_window(self._win)
            self.show()
        else:
            self._extra = ExtraParameters(
                self._cnf,
                self._cnf.PLAYER_NAME,
                self._win,
                lambda: True,
                from_config=False
            )

    def show(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        if self._too_small:
            self._win.addstr(1, 1, self._too_small_str,
                             curses.color_pair(5))
            self._win.refresh()
        else:
            self._win.addstr(
                0, int((self.maxX - len(self._title)) / 2),
                self._title,
                curses.color_pair(4))
            ''' show note '''
            try:
                self._win.addstr(12, 2, '─' * (self.maxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(12, 2, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
            self._win.addstr(12, int((self.maxX - len(self._note_text))/2), self._note_text, curses.color_pair(3))

            self._win.addstr(13, int((self.maxX - len(self._note_line1)) / 2), self._note_line1, curses.color_pair(5))
            self._win.addstr(14, int((self.maxX - len(self._note_line2)) / 2), self._note_line2, curses.color_pair(5))

            self._extra.refresh_win()

    def keypress(self, char):
        return self._extra.keypress(char)


class ExtraParametersEditor(object):
    ''' Class to edit or add parameters
    '''

    def __init__(self,
                 parent,
                 config,
                 string=''):
        self._parent = parent
        self._cnf = config
        self.edit_string = string
        self._caption = ' Parameter value '
        self._string = self._orig_string = string

        self.Y, self.X = self._parent.getbegyx()
        self.Y += 1
        self.X += 1
        self.maxY, self.maxX = self._parent.getmaxyx()
        self.maxY -= 2
        self.maxX -= 2
        self._win = curses.newwin(
            self.maxY, self.maxX,
            self.Y, self.X)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()

        self._focus = 0
        self._widgets = [None, None, None]

        self._too_small = False

        ''' add line editor '''
        self._widgets[0] = SimpleCursesLineEdit(
            parent=self._win,
            width=self.maxX - 2,
            begin_y=self.Y + 1,
            begin_x=self.X + 1,
            boxed=False,
            has_history=False,
            caption='',
            box_color=curses.color_pair(9),
            caption_color=curses.color_pair(4),
            edit_color=curses.color_pair(9),
            cursor_color=curses.color_pair(8),
            unfocused_color=curses.color_pair(5),
            string_changed_handler=self._string_changed)
        self._widgets[0].string = string
        self._widgets[0].bracket = False
        self._widgets[0]._use_paste_mode = True
        ''' enables direct insersion of ? and \ '''
        self._widgets[0]._paste_mode = True
        self._line_editor = self._widgets[0]

        ''' add horizontal push buttons '''
        self._h_buttons = SimpleCursesHorizontalPushButtons(
                Y=3, captions=('OK', 'Cancel'),
                color_focused=curses.color_pair(9),
                color=curses.color_pair(4),
                bracket_color=curses.color_pair(5),
                parent=self._win)
        self._h_buttons.calculate_buttons_position()
        self._widgets[1], self._widgets[2] = self._h_buttons.buttons
        self._widgets[1]._focused = self._widgets[2].focused = False

        if not self._orig_string:
            self._widgets[1].enabled = False

    def _string_changed(self):
        pass

    def resize(self, parent):
        self._parent = parent
        self.Y, self.X = self._parent.getbegyx()
        self.Y += 1
        self.X += 1
        self._win.mvwin(self.Y, self.X)

        self._h_buttons.calculate_buttons_position(parent=self._win)
        self._win.refresh()
        self.refresh_win()

    def show(self):
        self._win.addstr(0, 0, self._caption, curses.color_pair(5))
        try:
            self._win.addstr(5, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(5, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(5, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))


        self._win.addstr(6, 5, 'TAB', curses.color_pair(4))
        self._win.addstr(', ', curses.color_pair(5))
        self._win.addstr('Down', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('Up', curses.color_pair(4))
        self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
        self._win.addstr(7, 5, 'ENTER', curses.color_pair(4))
        self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
        step = 0
        if self._orig_string:
            self._win.addstr(8, 5, 'r', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('^R', curses.color_pair(4))
            self._win.addstr(8, 23, 'Revert to saved values (', curses.color_pair(5))
            self._win.addstr('^R', curses.color_pair(4))
            self._win.addstr(' in Line Editor).', curses.color_pair(5))
            step = 1
        self._win.addstr(8 + step, 5, 'Esc', curses.color_pair(4))
        self._win.addstr(8 + step, 23, 'Cancel operation.', curses.color_pair(5))

        self._win.addstr(9 + step, 5, 's', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('q', curses.color_pair(4))
        self._win.addstr(9 + step , 23, 'Save / Cancel (not in Line Editor).', curses.color_pair(5))

        self._win.addstr(10 + step, 5, '?', curses.color_pair(4))
        self._win.addstr(10 + step, 23, 'Line editor help (in Line Editor).', curses.color_pair(5))
        self._win.refresh()
        self.refresh_win()

    def refresh_win(self):
        if not self._too_small:
            self._line_editor.show(
                self._win, opening=False,
                new_y=self.Y + 1,
                new_x=self.X + 1)
            self._widgets[1].show()
            self._widgets[2].show()

    def _update_focus(self):
        ''' use _focused here to avoid triggering
            widgets' refresh
        '''
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

    def _focus_next(self):
        if self._focus == len(self._widgets) - 1:
            self._focus = 0
        else:
            focus = self._focus + 1
            while not self._widgets[focus].enabled:
                focus += 1
            self._focus = focus

    def _focus_previous(self):
        if self._focus == 0:
            self._focus = len(self._widgets) - 1
        else:
            focus = self._focus - 1
            while not self._widgets[focus].enabled:
                focus -= 1
            self._focus = focus

    def keypress(self, char):
        ''' Extra parameter editor keypress
            Returns:
                0: Response ready (in edit_string)
                1: Continue
                2: Display line editor help
        '''
        ret = 1
        if char == ord('?') and self._focus > 0:
            return 2
        elif char in (curses.KEY_EXIT, 27, ord('q')) and \
                self._focus > 0:
            self.edit_string = ''
            ret = 0
        elif char in (ord('\t'), 9, curses.KEY_DOWN):
            self._focus_next()
        elif char == curses.KEY_UP:
            self._focus_previous()
        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            if self._focus == 0:
                ''' go to next field '''
                self._focus_next()
            elif self._focus == 1:
                ''' save string '''
                self.edit_string = self._line_editor.string.strip()
                ret = 0
            else:
                ''' cancel '''
                self.edit_string = ''
                ret = 0
        elif char == ord('s') and self._focus > 0:
            ''' s, execute '''
            if self._widgets[1].enabled:
                self.edit_string = self._line_editor.string.strip()
                ret = 0
        elif self._focus == 0:
            '''
             Returns:
                2: display help
                1: get next char
                0: exit edit mode, string isvalid
               -1: cancel
            '''
            ret = self._line_editor.keypress(self._win, char)
            if ret == 2:
                self._win.touchwin()
            elif ret == 1:
                ''' get next char '''
                if self._line_editor.string.strip():
                    self._widgets[1].enabled = True
                else:
                    self._widgets[1].enabled = False
                ret = 1
            elif ret == 0:
                ''' exit, string is valid '''
                self.edit_string = self._line_editor.string.strip()
                ret = 0
            elif ret == -1:
                ''' cancel '''
                self.edit_string = ''
                ret = 0

        if ret == 1:
            self._update_focus()
            self.refresh_win()
        ''' Continue '''
        return ret

        try:
            self._count += 1
        except:
            self._count = 1
        if self._count > 2:
            return 0
        else:
            return 1

    def _update_focus(self):
        ''' use _focused here to avoid triggering
            widgets' refresh
        '''
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

class ExtraParameters(object):
    ''' display player's extra parameters
        in a foreign curses window ('Z')
    '''

    def __init__(self,
                 config,
                 player,
                 win,
                 focus,
                 startY=1,
                 startX=1,
                 max_lines=11,
                 from_config=True):
        self._cnf = config
        self._orig_params = deepcopy(self._cnf.saved_params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('original parameters = {}'.format(self._orig_params))
        self._orig_player = player
        # logger.error('DE orig player = {}'.format(self._orig_player))
        self._win = win
        self._focus = focus
        self.from_config = from_config

        ''' start Y, X '''
        self.startY = startY
        self.startX = startX

        ''' maximum number of lines to display '''
        self.max_lines = max_lines

        self.reset(saved=False)
        ''' set cursor to active item '''
        for a_key in self._selections.keys():
            self._selections[a_key][0] = self._selections[a_key][2]
        self._get_width()

    def check_parameters(self):
        ''' Exrta Parameters check '''
        for a_key in self._orig_params.keys():
            if self._orig_params[a_key] != self._working_params[a_key]:
                self._cnf.dirty_config = self._cnf.params_changed = True
                return True
        return False

    def reset(self, saved=True):
        ''' reset Player Selection Options

            Parameter
            ========
            saved:
                False - load params from config (default)
                True  - load saved params from config
        '''
        self._player = self._orig_player
        if saved:
            self._working_params = deepcopy(self._cnf.saved_params)
        else:
            self._working_params = deepcopy(self._cnf.params)
        self._selections = {
            'mpv': [0, 0, 0],
            'mplayer': [0, 0, 0],
            'vlc': [0, 0, 0]
        }
        self._items_dict = {
            'mpv': [],
            'mplayer': [],
            'vlc': []
        }
        self._dict_to_list()
        self._items = self._items_dict[self._player]
        self._original_active = self.active

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, a_player):
        if a_player in SUPPORTED_PLAYERS:
            self._player = a_player
            self._items = self._items_dict[a_player]
            self.refresh_win()

    @property
    def selection(self):
        return(self._selections[self._player][0])

    @selection.setter
    def selection(self, val):
        self._selections[self._player][0] = val

    @property
    def startPos(self):
        return(self._selections[self._player][1])

    @startPos.setter
    def startPos(self, val):
        self._selections[self._player][1] = val

    @property
    def original_active(self):
        if self._player == self._cnf.PLAYER_NAME:
            return self._original_active
        else:
            return self.selection

    @original_active.setter
    def original_active(self, val):
        raise ValueError('property is read only')

    @property
    def active(self):
        ''' this is the parameter to be used by the player '''
        return(self._selections[self._player][2])

    @active.setter
    def active(self, val):
        self._selections[self._player][2] = val

    @property
    def params(self):
        ''' Returns the parameters as changed by the user '''
        return self._orig_params

    @params.setter
    def params(self, val):
        raise ValueError('parameter is read only')

    def _dict_to_list(self):
        ''' convert self._working_params dict
            to self._items dict, and set self.active
        '''
        # logger.error('DE\n')
        # logger.error('DE working params = {}'.format(self._working_params))
        for a_param_set in self._working_params.keys():
            for i, a_param in enumerate(self._working_params[a_param_set]):
                if i == 0:
                    # logger.error('DE a_param = {}'.format(a_param))
                    self._selections[a_param_set][2] = int(a_param) - 1
                else:
                    self._items_dict[a_param_set].append(a_param)

    def _list_to_dict(self):
        ''' convert self._items_dict to self._working_params '''
        for a_params_set in self._items_dict.keys():
            the_list = [self._selections[a_params_set][2] + 1]
            the_list.extend(self._items_dict[a_params_set])
            self._working_params[a_params_set] = the_list[:]

    def _get_width(self):
        Y, X = self._win.getmaxyx()
        self._width = X - self.startX - 2

    def refresh_win(self):
        for a_line in range(0, self.max_lines):
            i = a_line + 1
            d_str = ' ' + str(i) + '.' if i < 10 else str(i) + '.'
            self._win.addstr(
                self.startY + a_line,
                self.startX,
                d_str,
                curses.color_pair(4)
            )
        for a_line in range(0, len(self._items)):
            if a_line == len(self._items):
                break
            else:
                col = self._get_color(a_line)
                item_str = self._items[a_line]
                cjk_len = cjklen(item_str) + 3
                if cjk_len > self._width - 1:
                    d_str = ' ' + item_str[:self._width - 4] + ' '
                else:
                    d_str = ' ' + item_str + ' ' * (self._width - cjk_len)

                self._win.addstr(
                    self.startY + a_line,
                    self.startX + 3,
                    d_str,
                    col
                )
        self._win.refresh()

    def _get_color(self, a_line):
        col = curses.color_pair(5)
        if self._focus():
            if a_line == self.active:
                if a_line == self.selection:
                    col = curses.color_pair(9)
                else:
                    col = curses.color_pair(4)
            elif a_line == self.selection:
                col = curses.color_pair(6)
        else:
            if a_line == self.active:
                col = curses.color_pair(4)
        return col

    def set_player(self, a_player):
        if a_player in SUPPORTED_PLAYERS:
            self._orig_player = self._player
            self._player = a_player
            self._items = self._items_dict[a_player]

            if len(self._items) < self.max_lines:
                ''' "erase" window '''
                empty_str = ' ' * self._width
                for a_line in range(len(self._items), self.max_lines):
                    self._win.addstr(self.startY + a_line,
                                     self.startX,
                                     empty_str,
                                     curses.color_pair(5))
            self.refresh_win()

    def resize(self, window, startY=None, startX=None):
        self._win = window
        if startY is not None:
            self.startY = startY
        if startX is not None:
            self.startX = startX
        self._get_width()

        ''' erase params window
            done by containing window
        '''

        if self.from_config:
            self.refresh_win()

    def set_window(self, window):
        self.resize(window=window)

    def _go_up(self, how_much=1):
        old_selection = self.selection
        self.selection -= how_much
        if old_selection == 0:
            self.selection = len(self._items) - 1
        else:
            if self.selection < 0:
                if how_much == 1:
                    self.selection = len(self._items) - 1
                else:
                    self.selection = 0
        self.refresh_win()

    def _go_down(self, how_much=1):
        old_selection = self.selection
        self.selection += how_much
        if old_selection == len(self._items) - 1:
            self.selection = 0
        else:
            if self.selection >= self.max_lines or \
                    self.selection >= len(self._items):
                if how_much == 1:
                    self.selection = 0
                else:
                    self.selection = len(self._items) - 1
        self.refresh_win()

    def save_results(self):
        ''' pass working parameters to original parameters
		    effectively saving any changes.
        '''
        # logger.error('DE save_results')
        # logger.error('DE 1 working_params = {}'.format(self._working_params))
        self._list_to_dict()
        # logger.error('DE 2 working_params = {}'.format(self._working_params))
        self.check_parameters()
        # logger.error('DE 3 working_params = {}'.format(self._working_params))
        self._orig_params = deepcopy(self._working_params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('new parameters (not saved) = {}'.format(self._orig_params))

    def keypress(self, char):
        ''' Extra parameters keypress
            Returns:
                -2 - cancel
                -1 - continue
                 0 - activate selection
                 1 - display help
                 2 - error, number of max lines reached
                 3 - error, cannot edit or delete first item
                 4 - edit parameter
                 5 - add parameter
                 6 - line editor help
        '''
        if char in (
            curses.KEY_ENTER, ord('\n'),
            ord('\r'), ord(' '), ord('l'),
                curses.KEY_RIGHT, ord('s')):
            ''' activate selection '''
            # logger.error('DE active ={}, selection={}'.format(self.active, self.selection))
            self.active = self.selection
            # logger.error('DE active ={}, selection={}'.format(self.active, self.selection))

            ''' reset profile '''
            if self._cnf.PLAYER_NAME == self._orig_player:
                if not self._items[self.active].startswith('profile:'):
                    self._cnf._profile_name = 'pyradio'

            if self.from_config:
                self.refresh_win()
            else:
                self.save_results()
            return 0

        elif char in (
            curses.KEY_EXIT, 27,
            ord('q'), curses.KEY_LEFT,
            ord('h')
        ):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
                self.reset()
                return -2

        elif char == ord('?'):
            ''' display help '''
            return 1

        elif char in (curses.KEY_UP, ord('k')):
            self._go_up()

        elif char in (curses.KEY_DOWN, ord('j')):
            self._go_down()

        elif char in (curses.KEY_NPAGE, ):
            self._go_down(5)

        elif char in (curses.KEY_PPAGE, ):
            self._go_up(5)

        elif char == ord('g'):
            self.selection = 0
            self.refresh_win()

        elif char == ord('G'):
            self.selection = len(self._items) - 1
            self.refresh_win()

        elif char in (ord('x'), curses.KEY_DC):
            if self.from_config:
                if self.selection == 0:
                    ''' error: cannot delete first item '''
                    return 3
                else:
                    self._win.addstr(
                        self.startY + len(self._items) - 1,
                        self.startX,
                        ' ' * (self._width + 1),
                        curses.color_pair(5)
                    )
                    if self.active == self.selection or self.selection > len(self._items):
                        self.active = 0
                    elif self.active > self.selection:
                        self.active -= 1
                    self._items.pop(self.selection)
                    while self.selection > len(self._items) - 1:
                        self.selection -= 1
                    self.refresh_win()

        elif char == ord('e'):
            if self.from_config:
                if self.selection == 0:
                    ''' error: cannot edit first item '''
                    return 3
                ''' edit parameter '''
                return 4

        elif char == ord('a'):
            if self.from_config:
                if len(self._items) == self.max_lines:
                    ''' error: cannot add more items '''
                    return 2
                ''' add parameter '''
                return 5

        return -1


class PyRadioSelectPlayer(object):

    maxY = 14
    maxX = 72
    selection = 0

    _title = ' Player Selection '

    _win = None
    _extra = None

    _working_players = [[], []]

    ''' mlength is the length of the longest item in the
        players list, which is '[ ] mplayer ' = 14
    '''
    mlength = 13

    def __init__(self, config, parent, player):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('current players = {}'.format(player))
        self._cnf = config
        self._parent = parent
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        self.player = player
        self._orig_player = player
        self.focus = True

        ''' Is editor active?
                0 - Not active
                1 - Adding a parameter
                2 - Editing a parameter
        '''
        self.editing = 0
        ''' result of parameter editing'''
        self.edit_string = None
        ''' parameter editor window '''
        self._parameter_editor = None

        ''' players contain supported players
            it is a list of lists
            each list contains three items
            0 - player name
            1 - True if enabled for detection
            2 - True if usable on platform
        '''
        self._players = []
        self._populate_players()
        self.init_window()
        self.refresh_win(do_params=True)

    @property
    def from_config(self):
        if self._extra:
            return self._extra.from_config
        else:
            return True

    @from_config.setter
    def from_config(self, val):
        raise ValueError('property is read only')

    @property
    def is_dirty(self):
        if self._extra is not None:
            return self._extra.is_dirty
        return False

    @is_dirty.setter
    def is_dirty(self, val):
        raise ValueError('property is read only')

    def init_window(self):
        self._win = None
        Y = int((self._parent_maxY - self.maxY) / 2)
        if Y % 2 == 1:
            Y += 1
        self._win = curses.newwin(
            self.maxY, self.maxX,
            Y,
            int((self._parent_maxX - self.maxX) / 2)
        )
        if self._extra is None:
            self._extra = ExtraParameters(
                self._cnf,
                self.selected_player_name(),
                self._win,
                lambda: not self.focus,
                startY=2,
                startX=self.mlength + 11,
            )
        else:
            self._extra.set_window(self._win)

    def selected_player_name(self):
        return self._players[self.selection][0]

    def _populate_players(self):
        self._players.clear()
        parts = self.player.replace(' ', '').split(',')
        for ap in parts:
            self._players.append([ap, True, True])

        if len(parts) < len(SUPPORTED_PLAYERS):
            ''' add missing player '''
            for ap in SUPPORTED_PLAYERS:
                if ap not in parts:
                    self._players.append([ap, False, True])

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('all players parameters = {}'.format(self._players))

    def refresh_win(self, do_params=False):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        if self.editing == 0:
            self._win.addstr(
                0, int((self.maxX - len(self._title)) / 2),
                self._title,
                curses.color_pair(4))
            self._win.addstr(1, 2, 'Supported Players', curses.color_pair(4))
            self._win.addstr(1, self.mlength + 11, 'Extra Player Parameters', curses.color_pair(4))
            #self._win.addstr(1, int(self.maxX / 2 + 2), 'Active' , curses.color_pair(4))
            self.refresh_selection()
            if do_params:
                self._extra.set_player(self.selected_player_name())
        else:
            if self.editing == 1:
                title = ' Add player paremeter '
            else:
                title = ' Edit player paremeter '
            self._win.addstr(
                0, int((self.maxX - len(title)) / 2),
                title, curses.color_pair(4))
            self._win.refresh()
            self._parameter_editor.show()

    def refresh_selection(self):
        for i in range(0, len(self._players)):
            token = ' [✔] ' if self._players[i][1] else ' [ ] '
            first_char = last_char = ' '
            if self.focus:
                if self.selection == i:
                    col = curses.color_pair(6)
                else:
                    col = curses.color_pair(5)
            else:
                col = curses.color_pair(5)
                if self.selection == i:
                    col = curses.color_pair(4)
                    '''
                        first_char = '>'
                        last_char = '<'
                    '''
            pad = self.mlength - (len(token) + len(self._players[i][0])) + 3
            self._win.addstr(
                i+2, 1,
                first_char + token + self._players[i][0] +
                pad * ' ' + last_char,
                col
            )
            # self._win.hline(i+2, 1, ' ', self.maxX - 2, curses.color_pair(5))
        self._win.refresh()
        return

        if self._working_players[0]:
            if self.selection[0] >= len(self._working_players[0]):
                self.selection[0] = 0

    def refresh_and_resize(self, maxY, maxX):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.init_window()
        self._extra.set_window(self._win)
        if self._parameter_editor:
            self._parameter_editor.resize(self._win)
        self.refresh_win(True)

    def reset(self):
        self._extra.reset()
        self._populate_players()
        self.refresh_win(do_params=True)
        self._cnf.params_changed = False

    def keypress(self, char):
        ''' Player selection keypress
            Returns:
              -2 - error, number of max lines reached
              -3 - error, cannot edit or delete first item
              -1 - Continue
               0 - Accept changes
               1 - Cancel
               2 - Display editor help
               3 - Editor is visible
               4 - Editor exited
        '''
        if self.editing == 0:
            ''' focus on players '''
            if char in (9, ):
                if self._players[self.selection][1]:
                    self._switch_column()
                    self.refresh_selection()

            elif char in (
                curses.KEY_EXIT, 27,
                ord('q'), curses.KEY_LEFT,
                ord('h')
            ):
                self._win.nodelay(True)
                char = self._win.getch()
                self._win.nodelay(False)
                if char == -1:
                    ''' ESCAPE '''
                    return 1

            elif char == ord('r'):
                self.reset()

            elif char == ord('s'):
                working_players = []
                for a_player in self._players:
                    if a_player[1]:
                        working_players.append(a_player[0])

                if working_players:
                    self.player = ','.join(working_players)
                else:
                    self.player = ','.join(SUPPORTED_PLAYERS)
                self._extra.save_results()
                return 0

            if self.focus:
                if char in (
                    curses.KEY_ENTER, ord('\n'), ord('\r'),
                    ord(' '), ord('l'), curses.KEY_RIGHT
                ):
                    self._players[self.selection][1] = not self._players[self.selection][1]
                    self.refresh_selection()

                elif char in (curses.ascii.NAK, 21):
                    ''' ^U, move player Up '''
                    x = self._players.pop(self.selection)
                    if self.selection == 0:
                        self._players.append(x)
                        self.selection = len(self._players) - 1
                    else:
                        self.selection -= 1
                        self._players.insert(self.selection, x)
                    self.refresh_selection()

                elif char in (curses.ascii.EOT, 4):
                    ''' ^D, move player Down '''
                    if self.selection == len(self._players) - 1:
                        x = self._players.pop(self.selection)
                        self._players.insert(0, x)
                        self.selection = 0
                    else:
                        x = self._players.pop(self.selection)
                        self.selection += 1
                        self._players.insert(self.selection, x)
                    self.refresh_selection()

                elif char in (curses.KEY_UP, ord('k')):
                    self.selection -= 1
                    if self.selection < 0:
                        self.selection = len(self._players) - 1
                    self.refresh_selection()
                    self._extra.set_player(self.selected_player_name())

                elif char in (curses.KEY_DOWN, ord('j')):
                    self.selection += 1
                    if self.selection == len(self._players):
                        self.selection = 0
                    self.refresh_selection()
                    self._extra.set_player(self.selected_player_name())

            else:
                ''' focus on parameters '''
                ret = self._extra.keypress(char)
                if ret == 2:
                    ''' error, number of max lines reached '''
                    return -2
                elif ret == 3:
                    ''' error, cannot edit or delete first item '''
                    return -3
                elif ret == 4:
                    ''' edit parameter '''
                    self.editing = 2
                    self._parameter_editor = ExtraParametersEditor(
                        self._win,
                        self._cnf,
                        string=self._extra._items[self._extra.selection])
                    self.refresh_win()
                    return 3
                elif ret == 5:
                    ''' add parameter '''
                    self._parameter_editor = ExtraParametersEditor(
                        self._win,
                        self._cnf)
                    self.editing = 1
                    self.refresh_win()
                    return 3

        else:
            ''' return from parameter editor
                adding or editing a parameter
            '''
            ret = self._parameter_editor.keypress(char)
            if ret == 0:
                ''' accept parameter or cancel '''
                if self._parameter_editor.edit_string:
                    if self.editing == 1:
                        ''' add parameter  '''
                        self._extra._items.append(self._parameter_editor.edit_string)
                        self._extra.selection = len(self._extra._items) - 1
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('New parameter: ' + self._extra._items[-1])
                    else:
                        ''' change parameter '''
                        self._extra._items[self._extra.selection] = self._parameter_editor.edit_string
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('New parameter value: ' + self._parameter_editor.edit_string)

                self.editing = 0
                self.refresh_win(True)
                self._parameter_editor = None
                return 4
            elif ret == 2:
                ''' show editor help '''
                return ret

        return -1

    def _switch_column(self):
        self.focus = not self.focus
        self.refresh_selection()
        self._extra.refresh_win()

    def setPlayers(self, these_players):
        self.player = these_players
        self._players = []
        self._populate_players()


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
        self._win = curses.newwin(
            self.maxY, self.maxX,
            int((self._parent_maxY - self.maxY) / 2) + 1,
            int((self._parent_maxX - self.maxX) / 2))
        if set_encoding:
            self.setEncoding(self.encoding, init=True)

    def _fix_geometry(self):
        self._num_of_columns = int((self._parent_maxX - 2) / (self.max_enc_len + 2))
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
        ''' Enable this to see geometry '''
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('maxY,maxX = {0},{1}'.format(self.maxY, self.maxX))
        #    logger.debug('Number of columns = {}'.format(self._num_of_columns))
        #    logger.debug('Number of rows = {}'.format(self._num_of_rows))
        #    logger.debug('Number of visible rows = {}'.format(self.list_maxY))

    def refresh_win(self, set_encoding=True):
        ''' set_encoding is False when resizing '''
        self._fix_geometry()
        self.init_window(set_encoding)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self._title)) / 2),
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
            self._win.addstr(
                int(self.maxY / 2),
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
                    if i > 0:
                        pos += i
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
                    self._win.addstr(yy, xx - 1,
                                     ' ' * (self.max_enc_len + 2),
                                     col)
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
        y = sel % (self._num_of_rows + 1)
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
            if self.selection == len(self._encodings) - 1:
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

        elif char in (curses.KEY_EXIT, 27,
                      ord('q'), curses.KEY_LEFT,
                      ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
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

    ''' offset to current item for padding calculation '''
    pad_adjustment = 0

    def __init__(self,
                 parent,
                 config_path,
                 default_playlist,
                 include_registers=False):
        ''' Select a playlist from a list

        include_registers changes its behavior

        If it is False (default), it is used by config window
        and permit playlist only selection.
        Returns: state, playlist title

        if it is True, it is used in \p (paste) function and
        permits playlist and register selection.
        default_playlist is removed from the list.
        Returns: state, playlist/register path
        '''
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        try:
            self._parent_Y, _ = parent.getbegyx()
        except:
            ''' revert to old behavior '''
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
        # logger.error('DE \n\npos = {0}, pad = {1}\n\n'.format(self.startPos + self.maxY - 2 - self.pad_adjustment, pad))
        for i in range(0, self.maxY - 2):
            # logger.error('de i = {0}, startPos = {1}'.format(i, self.startPos))
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
        ''' PyRadioSelectPlaylist format line '''
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
            ''' Remove playlist in editor '''
            try:
                self._items.remove(self._playlist_in_editor)
            except ValueError:
                pass
        else:
            ''' get already loaded playlist id '''
            for i, a_playlist in enumerate(self._items):
                if a_playlist ==self._selected_playlist:
                    self._selected_playlist_id = i
                    break
        self._max_len = cjklen(max(self._items, key=cjklen))
        self._num_of_items = len(self._items)

    def setPlaylist(self, a_playlist, adjust=True):
        self._selected_playlist = a_playlist
        if a_playlist == 'False':
            self._selected_playlist_id = 0
        elif a_playlist == 'random' or \
            a_playlist == 'Random' or \
                a_playlist is None:
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
                for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
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
            self._error_win = curses.newwin(
                5, 38,
                int((self._parent_maxY - 5) / 2) + 1,
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
        ''' Return restlt from playlist selection window

        Results are:
        -1, ''              - Continue in window
         0, station title   - selected station title (for config window)
         0, station path    - selected station path (for paste window)
         1, ''              - Cancel
        '''
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
                ''' ESCAPE '''
                self._select_playlist_error = -2
                return 1, ''

        elif char in (curses.KEY_ENTER, ord('\n'),
                      ord('\r'), ord(' '), ord('l'),
                      curses.KEY_RIGHT):
            return self._get_result()

        elif char in (curses.KEY_DOWN, ord('j')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id + 1,
                                     adjust=False)
                if self._selected_playlist_id == 0:
                    self.startPos = 0
                elif self.startPos + self.maxY - 2 == self._selected_playlist_id:
                    self.startPos += 1
                self.refresh_selection()

        elif char in (curses.KEY_UP, ord('k')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id - 1,
                                     adjust=False)
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

        elif char in map(ord, map(str, range(0, 10))):
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
        ''' adding 2 to padding calculation
            (i.e. no selection and random selection
        '''
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
                    for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
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
        ''' PyRadioSelectStation format line '''
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
