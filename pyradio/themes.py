# -*- coding: utf-8 -*-
import curses
import sys
import logging
import glob
from sys import version_info
from os import path, getenv, makedirs, remove, sep as dir_sep, access, R_OK
from shutil import copyfile, move
from copy import deepcopy
from .log import Log
from .common import *

logger = logging.getLogger(__name__)



class PyRadioTheme(object):
    _colors = {}
    _active_colors = {}
    _read_colors = {}
    _temp_colors = {}

    transparent = False
    _transparent = False

    applied_theme_name = 'dark'

    config_dir = ''

    def __init__(self, cnf):
        self._cnf = cnf
        _applied_theme_max_colors = 8

    def __del__(self):
        self._colors = None
        self._active_colors = None
        self._read_colors = None
        self._temp_colors = None

    def _do_init_pairs(self):
        # not used
        curses.init_pair(1, curses.COLOR_CYAN, self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()])
        # PyRadio URL
        curses.init_pair(2, self._active_colors[THEME_ITEMS[0][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()])
        # help border
        curses.init_pair(3, self._active_colors[THEME_ITEMS[1][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()])
        # station playing no cursor
        curses.init_pair(4, self._active_colors[THEME_ITEMS[4][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()])
        # body win
        curses.init_pair(5, self._active_colors[THEME_ITEMS[3][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()])
        # cursor
        curses.init_pair(6, self._active_colors[THEME_ITEMS[5][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[5][0]][BACKGROUND()])
        # status bar
        curses.init_pair(7, self._active_colors[THEME_ITEMS[2][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[2][0]][BACKGROUND()])
        # edit cursor
        curses.init_pair(8, self._active_colors[THEME_ITEMS[7][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[7][0]][BACKGROUND()])
        # cursor when playing
        curses.init_pair(9, self._active_colors[THEME_ITEMS[6][0]][FOREGROUND()], self._active_colors[THEME_ITEMS[6][0]][BACKGROUND()])
        logger.error('DE _do_init_pairs:\n{}'.format(self._active_colors))

    def restoreActiveTheme(self):
        self._active_colors = deepcopy(self._read_colors)
        if self._transparent:
            self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()] = -1
        self._do_init_pairs()

    def readAndApplyTheme(self, a_theme, **kwargs):
        """ Read a theme and apply it

            Returns:
              -1: theme not supported (default theme loaded)
               0: all ok
        """
        result = 0
        use_transparency = None
        theme_path = ''
        for name, value in kwargs.items():
            if name == 'use_transparency':
                use_transparency = value
            elif name == 'theme_path':
                theme_path = value
        ret = self.open_theme(a_theme, theme_path)
        if ret < 0 or self._applied_theme_max_colors > curses.COLORS:
            # TODO: return error
            self._load_default_theme(self.applied_theme_name)
            result = -1, self.applied_theme_name
        else:
            self.applied_theme_name = a_theme

        self._active_colors = None
        self._active_colors = deepcopy(self._colors)
        if use_transparency is None:
            if self._transparent:
                self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()] = -1
        else:
            if use_transparency:
                self._active_colors[THEME_ITEMS[3][0]][BACKGROUND()] = -1
        self._do_init_pairs()
        self._read_colors = deepcopy(self._colors)
        return result, self.applied_theme_name

    def _load_default_theme(self, a_theme):
        logger.error('DE a_theme = {}'.format(a_theme))
        self.applied_theme_name = 'dark'
        self._applied_theme_max_colors = 8
        try_theme = a_theme.replace('_16_colors', '')
        if try_theme == 'light':
            self.applied_theme_name = try_theme
        elif self._cnf.theme.replace('_16_colors', '') == 'light':
                self.applied_theme_name = 'light'
        if logger.isEnabledFor(logging.INFO):
            logger.info('Applying default theme: {}'.format(self.applied_theme_name))
        self.open_theme(self.applied_theme_name)

    def open_theme(self, a_theme = '', a_path=''):
        """ Read a theme and place it in _colors
            a_theme: theme name
            a_path:  theme path (enpty if internal theme)

            Returns:
                0: all ok
                """
        ret = 0
        if not a_theme.strip():
            a_theme = 'dark'

        if a_theme == 'dark' or a_theme == 'default':
            self._colors[THEME_ITEMS[3][0]] = [ curses.COLOR_WHITE, curses.COLOR_BLACK ]
            self._colors[THEME_ITEMS[2][0]] = [ curses.COLOR_BLACK, curses.COLOR_GREEN ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ curses.COLOR_BLACK, curses.COLOR_MAGENTA ]
            self._colors[THEME_ITEMS[6][0]] = [ curses.COLOR_BLACK, curses.COLOR_GREEN ]
            self._colors[THEME_ITEMS[4][0]]  = [ curses.COLOR_GREEN, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ curses.COLOR_BLUE, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ curses.COLOR_YELLOW, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ curses.COLOR_WHITE, curses.COLOR_MAGENTA ]
            # info
            self._colors['Colors'] = 8
            self._colors['Name'] = 'dark'
            self._colors['Path'] = ''
            self.applied_theme_name = 'dark'

        elif a_theme == 'dark_16_colors':
            self._colors[THEME_ITEMS[3][0]] = [ 15, 8 ]
            self._colors[THEME_ITEMS[2][0]] = [ curses.COLOR_BLACK, 10 ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ curses.COLOR_BLACK, 13 ]
            self._colors[THEME_ITEMS[6][0]] = [ curses.COLOR_BLACK, 10 ]
            self._colors[THEME_ITEMS[4][0]]  = [ 10, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ 12, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ 11, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ 15, curses.COLOR_MAGENTA ]
            # info
            self._colors['Colors'] = 16
            self._colors['Name'] = 'dark_16_colors'
            self._colors['Path'] = ''
            self.applied_theme_name = 'dark_16_colors'

        elif a_theme == 'light':
            self._colors[THEME_ITEMS[3][0]] = [ curses.COLOR_BLACK, curses.COLOR_WHITE ]
            self._colors[THEME_ITEMS[2][0]] = [ curses.COLOR_WHITE, curses.COLOR_BLUE ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ curses.COLOR_WHITE, curses.COLOR_MAGENTA ]
            self._colors[THEME_ITEMS[6][0]] = [ curses.COLOR_WHITE, curses.COLOR_BLUE ]
            self._colors[THEME_ITEMS[4][0]]  = [ curses.COLOR_RED, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ curses.COLOR_BLUE, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ curses.COLOR_MAGENTA, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ curses.COLOR_WHITE, curses.COLOR_MAGENTA ]
            # info
            self._colors['Colors'] = 8
            self._colors['Name'] = 'light'
            self._colors['Path'] = ''
            self.applied_theme_name = 'light'

        elif a_theme == 'light_16_colors':
            self._colors[THEME_ITEMS[3][0]] = [ 8, 15 ]
            self._colors[THEME_ITEMS[2][0]] = [ 15, 12 ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ 15, 13 ]
            self._colors[THEME_ITEMS[6][0]] = [ 15, 12 ]
            self._colors[THEME_ITEMS[4][0]]  = [ 9, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ 12, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ 13, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ 15, 13 ]
            # info
            self._colors['Colors'] = 16
            self._colors['Name'] = 'light_16_colors'
            self._colors['Path'] = ''
            self.applied_theme_name = 'light_16_colors'

        elif a_theme == 'black_on_white' or a_theme == 'bow':
            self._colors[THEME_ITEMS[3][0]] = [ 245, 15 ]
            self._colors[THEME_ITEMS[2][0]] = [ 15, 245 ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ 15, 245 ]
            self._colors[THEME_ITEMS[6][0]] = [ 0, 245 ]
            self._colors[THEME_ITEMS[4][0]]  = [ 0, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ 0, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ 245, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ 15, 238 ]
            # info
            self._colors['Colors'] = 256
            self._colors['Name'] = 'black_on_white'
            self._colors['Path'] = ''
            self.applied_theme_name = 'black_on_white'

        elif a_theme == 'white_on_black' or a_theme == 'wob':
            self._colors[THEME_ITEMS[3][0]] = [ 247, 235 ]
            self._colors[THEME_ITEMS[2][0]] = [ 234, 253 ]
            # selection
            self._colors[THEME_ITEMS[5][0]] = [ 235, 247, ]
            self._colors[THEME_ITEMS[6][0]] = [ 235, 253 ]
            self._colors[THEME_ITEMS[4][0]]  = [ 255, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # Titles
            # calculated value: self._colors['Titles'] = self._colors[THEME_ITEMS[4][0]]
            self._colors[THEME_ITEMS[0][0]] = [ 253, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # help window
            self._colors[THEME_ITEMS[1][0]] = [ 247, self._colors[THEME_ITEMS[3][0]][BACKGROUND()] ]
            # calculated value: self._colors['Messages'] = [ self._colors[THEME_ITEMS[4][0]][FOREGROUND()], self._colors[THEME_ITEMS[2][0]][FOREGROUND()] ]
            # Edit Cursor
            self._colors[THEME_ITEMS[7][0]] = [ 15, 247 ]
            # info
            self._colors['Colors'] = 256
            self._colors['Name'] = 'white_on_black'
            self._colors['Path'] = ''
            self.applied_theme_name = 'white_on_black'

        else:
            if a_path == '':
                a_path = self._get_theme_path(a_theme)
            if a_path == '':
                #load default theme
                #self._load_default_theme(self.applied_theme_name)
                ret = -1
            else:
                # read theme from disk
                att = PyRadioThemeReadWrite()
                ret, self._temp_colors = att.read_theme(a_theme, a_path)
                if ret == 0:
                    self._colors = deepcopy(self._temp_colors)
                else:
                    #self._load_default_theme(self.applied_theme_name)
                    return -1

        self._applied_theme_max_colors = self._colors['Colors']
        self.applied_theme_name = self._colors['Name']
        return ret

    def _get_theme_path(self, a_theme):
        out_themes = []
        #self.root_path = path.join(path.dirname(__file__), 'stations.csv')
        theme_dirs = [ path.join(self._cnf.stations_dir, 'themes') ,
            path.join(path.dirname(__file__), 'themes') ]
        for theme_dir in theme_dirs:
            files = glob.glob(path.join(theme_dir, '*.pyradio-theme'))
            if files:
                for a_file in files:
                     a_theme_name = a_file.split(dir_sep)[-1].replace('.pyradio-theme', '')
                     if a_theme_name == a_theme:
                         return a_file
        return ''

    def toggleTransparency(self, force_value=None):
        """ Toggles theme trasparency.

            force_value will set trasparency if True or False,
            or toggle trasparency if None
        """
        if force_value is None:
            self._transparent = not self._transparent
        else:
            self._transparent = force_value
        self.restoreActiveTheme()

    def getTransparency(self):
        return self._transparent

class PyRadioThemeReadWrite(object):

    _tmeme_name = ''
    _theme_path = ''

    def __init__(self):
        pass

    def read_theme(self, theme_name, theme_path):
        """ Opens a theme file and return its contents in self._temp_colors

        Returns:
            0: success
            1: file not found
            2: file not readable
            3: read error
            4: file corrupt
            5: file incomplete
        """
        self._temp_colors = None
        if not path.isfile(theme_path):
            logger.error('read_theme: file not found: {}'.format(theme_path))
            return 1, None
        if not access(theme_path, R_OK):
            logger.error('read_theme: file not readable: {}'.format(theme_path))
            return 2, None

        try:
            with open(theme_path, 'r') as thmfile:
                lines = [line.strip() for line in thmfile if line.strip() and not line.startswith('#') ]

        except:
            logger.error('read_theme: read error on: {}'.format(theme_path))
            return 3, None
        max_colors = 0
        self._temp_colors = {}
        for line in lines:
            sp = line.split('=')
            sp[0] = sp[0].strip()
            vsp = sp[1].strip().split(',')
            if len(vsp) < 2:
                self._temp_colors = None
                logger.error('read_theme: file is corrupt: {}'.format(theme_path))
                return 4, None
            try:
                this_color = ( int(vsp[0]), int(vsp[1]) )
                for x in this_color:
                    if x > max_colors:
                        max_colors = x
            except:
                self._temp_colors = None
                logger.error('read_theme: file is corrupt: {}'.format(theme_path))
                return 4, None
            for it in THEME_ITEMS:
                if sp[0] == it[0]:
                    self._temp_colors[str(sp[0])] = [ this_color[0], this_color[1] ]
                    break

        if self._theme_is_incomplete():
            logger.error('read_theme: file is incomplete: {}'.format(theme_path))
            return 5, None

        self._theme_name = theme_name
        self._theme_path = theme_path
        self._temp_colors['Name'] = theme_name
        self._temp_colors['Path'] = theme_path
        self._temp_colors['Colors'] = self._get_max_color(theme_name, max_colors)
        return 0, self._temp_colors

    def _theme_is_incomplete(self):
        for i, item in enumerate(THEME_ITEMS):
            if not item[0] in self._temp_colors.keys():
                return True
        return False

    def _get_max_color(self, a_theme_name, max_color):
        checks = ('_8', '_16', '_256')
        num_of_colors = 0
        for a_check in checks:
            if a_theme_name.endswith(a_check):
                try:
                    num_of_colors = int(a_check[1:])
                except:
                    pass
                break
        checks = (8, 16, 256)
        if num_of_colors == 0 or num_of_colors not in checks:
            num_of_colors = max_color
            for check in checks:
                if num_of_colors <= check:
                    return check
        return num_of_colors

class PyRadioThemeSelector(object):
    """ Theme Selector Window """
    TITLE = ' Available Themes '
    parent = None
    _win = None
    _width = _height = X = Y = 0
    selection = _selection = _start_pos = _items = 0

    _themes = []
    _title_ids = []

    # display the 2 internal 8 color themes
    _items = 2

    # window background
    _bg_pair = 0

    # page up, down
    # when zero it will be _items / 2
    _page_jump = 0

    jumpnr = ''

    log = None
    _log_file = ''

    _max_title_width = 20
    _categories = 1

    transparent = False
    _transparent = False

    changed_from_config = False

    def __init__(self, parent, config, theme,
            applied_theme_name, applied_theme_max_colors,
            config_theme_name,
            title_color_pair, box_color_pair,
            applied_color_pair, normal_color_pair,
            cursor_color_pair, applied_cursor_color_pair,
            is_transparent, log_file=''):
        self.parent = parent
        self._cnf = config
        self._theme = theme
        self._applied_theme_name = applied_theme_name
        self._applied_theme_max_colors = applied_theme_max_colors
        self._config_theme_name = config_theme_name
        self._title_color_pair = title_color_pair
        self._box_color_pair = box_color_pair
        self._cursor_color_pair = cursor_color_pair
        self._applied_cursor_color_pair = applied_cursor_color_pair
        self._applied_color_pair = applied_color_pair
        self._normal_color_pair = normal_color_pair
        self._transparent = is_transparent
        if log_file:
            self._log_file = log_file
            self.log = self._log

        self._themes = []

    def show(self):
        self._themes = []
        self._themes = [ [ 'dark', 'dark' ] ]
        if curses.COLORS >= 16:
            self._themes.append([ 'dark_16_colors', '' ])
            self._items += 1
        self._themes.append([ 'light', '' ])
        if curses.COLORS >= 16:
            self._themes.append([ 'light_16_colors', '' ])
            self._items += 1
        if curses.COLORS == 256:
            self._themes.append([ 'black_on_white', '' ])
            self._themes.append([ 'white_on_black', '' ])
            self._items += 2
        # scan for package and user themes
        themes_to_add = self._scan_for_theme_files(self._cnf.stations_dir)
        #themes_to_add = self._scan_for_theme_files(self._cnf.stations_dir)
        if themes_to_add:
            self._themes.extend(themes_to_add)
            self._items = len(self._themes)
            self._get_titles_ids()

        for a_theme in self._themes:
            if len(a_theme[0]) > self._max_title_width:
                self._max_title_width = len(a_theme[0])

        if self.log:
            self.log('max_title_width = {}\n'.format(self._max_title_width))
        self._get_config_and_applied_theme()
        self._get_metrics()

    def _scan_for_theme_files(self, cnf_path, user_themes_first=False):
        out_themes = []
        #self.root_path = path.join(path.dirname(__file__), 'stations.csv')
        theme_dirs = [ path.join(path.dirname(__file__), 'themes'),
                path.join(cnf_path, 'themes') ]
        if user_themes_first:
            theme_dirs.reverse()
        for i, theme_dir in enumerate(theme_dirs):
            files = glob.glob(path.join(theme_dir, '*.pyradio-theme'))
            if files:
                tmp_themes = []
                for a_file in files:
                     theme_name, ret = self._can_use_theme(a_file)
                     if ret:
                         tmp_themes.append([ theme_name, a_file ])
                if tmp_themes:
                    tmp_themes.sort()
                    tmp_themes.reverse()
                    if i == 0:
                        tmp_themes.append(['System Themes', '-'])
                    else:
                        tmp_themes.append(['User Themes', '-'])
                    tmp_themes.reverse()
                    out_themes.extend(tmp_themes)
        return out_themes

    def _get_titles_ids(self):
        self._title_ids = []
        for i, a_theme in enumerate(self._themes):
            if a_theme[1] == '-':
                self._title_ids.append(i)

    def _can_use_theme(self, a_theme):
        """ Check if theme name contains number of colors.
            If so, check if the theme can be used on this terminal
            If not, return True"""
        a_theme_name = a_theme.split(dir_sep)[-1].replace('.pyradio-theme', '')
        checks = ('_8', '_16', '_256')
        for a_check in checks:
            if a_theme_name.endswith(a_check):
                try:
                    num_of_colors = int(a_check[1:])
                    if num_of_colors <= curses.COLORS:
                        return a_theme_name, True
                        #return a_theme_name.replace(a_check, ''), True
                    else:
                        return '', False
                except:
                    return a_theme_name, True
        return a_theme_name, True

    def theme_name(self, val):
        if val < len(self._themes):
            return self._themes[val][0]
        return ''

    def theme_path(self, val):
        if val < len(self._themes):
            return self._themes[val][1]
        return ''

    def _short_to_normal_theme_name(self, a_theme_name):
        if a_theme_name == 'bow':
            return 'black_on_white'
        elif a_theme_name == 'wob':
            return 'white_on_black'
        return a_theme_name

    def _get_config_and_applied_theme(self):
        self._config_theme_name = self._short_to_normal_theme_name(self._config_theme_name)
        self._applied_theme_name = self._short_to_normal_theme_name(self._applied_theme_name)
        if curses.COLORS <= self._applied_theme_max_colors - 1:
            if self._config_theme_name == 'light_16_colors':
                self._config_theme_name = 'light'
                self._applied_theme_name = 'light'
            else:
                self._config_theme_name = 'dark'
                self._applied_theme_name = 'dark'
        if self.log:
            self.log('config theme name = "{0}", applied theme name = "{1}"\n'.format(self._config_theme_name, self._applied_theme_name))
        self._config_theme = -1
        self._applied_theme = -1
        found = 0
        for i, a_theme in enumerate(self._themes):
            if a_theme[0] == self._config_theme_name:
                self._config_theme = i
                found += 1
            if a_theme[0] == self._applied_theme_name:
                self._applied_theme = i
                found += 1
            if found == 2:
                break

        if self.log:
            self.log('config theme = {0}, applied theme = {1}\n'.format(self._config_theme, self._applied_theme))
        if self._applied_theme == -1:
            self._selection = 0
        else:
            self._selection = self._applied_theme

    def _get_metrics(self):
        maxY, maxX = self.parent.getmaxyx()
        num_of_themes = len(self._themes)
        if num_of_themes > 4:
            if num_of_themes + 2 < maxY - 2:
                self._items = num_of_themes
                self.Y = int((maxY - self._items + 2) / 2)
            else:
                self._items = maxY - 4
                self.Y = 2
        else:
            self.Y = int((maxY - self._items + 2) / 2)
        self._height = self._items + 2

        if self.log:
            self.log('max_title_width = {}\n'.format(self._max_title_width))
        self._width = self._max_title_width + 4
        if self.log:
            self.log('width = {}\n'.format(self._width))
        self.X = int((maxX - self._width) / 2)



        self._page_jump = int(self._items / 2)
        self._win = None
        self._win = curses.newwin(self._height, self._width, self.Y, self.X)
        self._win.bkgdset(' ', curses.color_pair(self._box_color_pair))
        #self._win.erase()
        self._draw_box()
        self.refresh()

    def getmaxyx(self):
        return self._width, self._height

    @property
    def transparent(self):
        return self._transparent

    @transparent.setter
    def transparent(self, val):
        self._transparent = val
        self.refresh()

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, val):
        old_selection = self._selection
        if val < 0:
            self._selection =0
            self._start_pos = 0
        elif val >= len(self._themes):
            self._selection = len(self._themes) - 1
            self._start_pos = len(self._themes) - self._items
        else:
            self._selection = val
            if self._selection >= len(self._themes):
                self._selection = len(self._themes) - 1
                self._start_pos = len(self._themes) - self._items

            if self._selection > old_selection:
                while self._selection >= self._start_pos + self._items:
                    self._start_pos += self._items
                if self._start_pos >= len(self._themes) - self._items:
                    self._start_pos = len(self._themes) - self._items
            else:
                while self._selection < self._start_pos:
                    self._start_pos -= self._items
                if self._start_pos < 0:
                    self._start_pos = 0
        self.refresh()

    def set_theme(self, a_theme):
        for i, ex_theme in enumerate(self._themes):
            if ex_theme == a_theme:
                if self._selection != i:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Setting theme: "{}"'.format(a_theme))
                    self.selection = i
                break

    def refresh(self):
        if self.log:
            self.log('======================\n')
            self.log('{}\n'.format(self._themes))
        for i in range(self._start_pos, self._start_pos + self._items):
            token = ' '
            if i in self._title_ids:
                col = curses.color_pair(self._title_color_pair)
            elif self._start_pos + i == self.selection:
                # on selection, display cursor
                if self._selection == self._applied_theme:
                    col = curses.color_pair(self._applied_cursor_color_pair)
                else:
                    col = curses.color_pair(self._cursor_color_pair)
            else:
                if self._start_pos + i == self._applied_theme:
                    col = curses.color_pair(self._applied_color_pair)
                else:
                    col = curses.color_pair(self._normal_color_pair)
            self._win.hline(i + 1, 1, ' ', self._max_title_width + 2, col)
            if self._start_pos + i == self._config_theme:
                token = '*'
            if i in self._title_ids:
                self._win.move(i + 1, 0)
                try:
                    self._win.addstr('├', curses.color_pair(3))
                    self._win.move(i + 1, len(self._themes[i][0]) + 3)
                    self._win.addstr('─' * (self._width - 2 - len(self._themes[i][0]) - 2), curses.color_pair(3))
                    try:
                        self._win.addstr('┤', curses.color_pair(3))
                    except:
                        pass
                except:
                    self._win.addstr('├'.encode('utf-8'), curses.color_pair(3))
                    self._win.move(i + 1, len(self._themes[i][0]) + 2)
                    self._win.addstr('─'.encode('utf-8') * (self._width - 2 - len(self._themes[i][0]) - 2), curses.color_pair(3))
                    try:
                        self._win.addstr('┤'.encode('utf-8'), curses.color_pair(3))
                    except:
                        pass
                self._win.addstr(i+1, 1, token + self._themes[i][0], col)
            else:
                self._win.addstr(i+1, 1, token + self._themes[i][0], col)

        try:
            self._win.move(sel, self._width - 2)
        except:
            pass
        # display trasnparency indicator
        if self._transparent:
            self._win.addstr(self._height-1, self._width -4, '[T]', curses.color_pair(self._box_color_pair))
        else:
            try:
                self._win.addstr(self._height-1, self._width -4, '───', curses.color_pair(self._box_color_pair))
            except:
                self._win.addstr(self._height-1, self._width -4, '───'.encode('utf-8'), curses.color_pair(self._box_color_pair))
        self._win.refresh()
        curses.doupdate()

    def _draw_box(self):
        self._win.box()
        self._win.move(0,1)
        self._win.addstr(self.TITLE, curses.color_pair(self._title_color_pair))

    def _go_up(self):
        self._selection -= 1
        if self._selection in self._title_ids:
            self._selection -= 1
        if self._selection < 0:
            self.selection = len(self._themes) - 1
        elif self._selection == self._start_pos -1:
            self._start_pos -= 1
        self.refresh()

    def _go_down(self):
        self._selection += 1
        if self._selection in self._title_ids:
            self._selection += 1
        if self._selection == len(self._themes):
            self.selection = 0
        elif self._selection == self._start_pos + self._items:
            self._start_pos += 1
        self.refresh()

    def _go_home(self):
        self._selection = 0
        self._start_pos =0
        self.refresh()

    def _go_end(self):
        self.selection = len(self._themes)

    def _is_theme_read_only(self, theme_path):
        if theme_path:
            themes_path = path.join(path.dirname(__file__), 'themes')
            if themes_path == path.dirname(theme_path):
                return True
            else:
                if access(theme_path, R_OK):
                    return False
                else:
                    return True
        else:
            return True

    def keypress(self, char):
        """ returns theme_id, save_theme
            return_id
              0-..  : id in self._theme
              -1    : end or canel
              -2    : ask to create a new theme
              -3    : go no
            save_them
              True  : theme is to be saved in config
              False : theme is not to be saved in config
        """
        if char in (ord('e'), ):
            # edit theme
            if self._themes[self._selection][1] == '' or \
                    self._is_theme_read_only(self._themes[self._selection][1]):
                # display question to create theme instead
                return -2, False
            else:
                pass
        elif char in (ord('a'), ):
            # new theme
            pass
        elif char in (curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord('l'),
                curses.KEY_RIGHT):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            #if self.changed_from_config:
            #    self._config_theme = self._selection
            #    self._config_theme_name = self._themes[self._selection][0]
            self.refresh()
            return self._selection, False
        elif char in (ord(' '), ord('s')):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            if not self.changed_from_config:
                self._config_theme = self._selection
                self._config_theme_name = self._themes[self._selection][0]
            if char == ord('s'):
                # close window
                curses.ungetch('q')
            else:
                self.refresh()
            return self._selection, True
        elif char in (curses.KEY_UP, ord('k')):
            self.jumpnr = ''
            self._go_up()
        elif char in (curses.KEY_DOWN, ord('j')):
            self.jumpnr = ''
            self._go_down()
        elif char in (curses.KEY_HOME, ord('g')):
            self.jumpnr = ''
            self._go_home()
        elif char in (curses.KEY_END, ord('G')):
            if self.jumpnr == '':
                self._go_end()
            else:
                num = int(self.jumpnr) - 1
                if num in self._title_ids:
                    num += 1
                if num >= 0:
                    self.selection = num
                    self.jumpnr = ''
        elif char in (curses.KEY_NPAGE, ):
            self.jumpnr = ''
            sel = self._selection + self._page_jump
            if sel in self._title_ids:
                sel += 1
            if self._selection == len(self._themes) - 1:
                sel = 0
            elif sel >= len(self._themes):
                sel = len(self._themes) - 1
            self.selection = sel
        elif char in (curses.KEY_PPAGE, ):
            self.jumpnr = ''
            sel = self._selection - self._page_jump
            if sel in self._title_ids:
                sel -= 1
            if self._selection == 0:
                sel = len(self._themes) - 1
            elif sel < 0:
                sel = 0
            self.selection = sel
        elif char in map(ord,map(str,range(0,10))):
            self.jumpnr += chr(char)
        elif char in (curses.KEY_EXIT, 27, ord('q'), ord('h'), curses.KEY_LEFT):
            self.jumpnr = ''
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                if not self.changed_from_config:
                    if self._applied_theme_name != self._config_theme_name:
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('Restoring saved theme: {}'.format(self._config_theme_name))
                        ret, ret_theme_name = self._theme.readAndApplyTheme(self._config_theme_name)
                        self._applied_theme = self._config_theme
                        if ret == 0:
                            self._applied_theme_name = self._config_theme_name
                        else:
                            self._applied_theme_name = ret_theme_name
                            self._cnf.theme_not_supported = True
                self.selection = -1
                return -1, False
        return -3, False

    def _log(self, msg):
        with open(self._log_file, 'a') as log_file:
            log_file.write(msg)

class PyRadioThemeEditor(object):

    theme_name = theme_path = ''
    editing = False
    _cnf = None
    maxX = maxY = 0

    def __init__(self, theme_name, theme_path, editing, config, maxX, maxY):
        self.theme_name = theme_name
        self.theme_path = theme_path
        self.editing = editing
        self._cnf = config
        self.maxY = maxX
        self.maxY = maxY

    def keypress(self, char):
        pass
