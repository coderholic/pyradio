# -*- coding: utf-8 -*-
import curses
import sys
import logging
import glob
from sys import version_info
from os import path, getenv, makedirs, remove
from shutil import copyfile, move
from copy import deepcopy
from .log import Log


logger = logging.getLogger(__name__)

FOREGROUND = 0
BACKGROUND = 1
# for pop up window
CAPTION = 2
BORDER = 3


class PyRadioTheme(object):
    _colors = {}
    _active_colors = {}
    _read_colors = {}

    transparent = False
    _transparent = False

    applied_theme_name = 'dark'

    def __init__(self):
        _applied_theme_max_colors = 8

    def __del__(self):
        self._colors = None
        self._active_colors = None
        self._read_colors = None

    def _do_init_pairs(self):
        # not used
        curses.init_pair(1, curses.COLOR_CYAN, self._active_colors['Stations'][BACKGROUND])
        # PyRadio URL
        curses.init_pair(2, self._active_colors['PyRadio URL'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        # help border
        curses.init_pair(3, self._active_colors['Messages Border'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        # station playing no cursor
        curses.init_pair(4, self._active_colors['Active Station'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        # body win
        curses.init_pair(5, self._active_colors['Stations'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        # cursor
        curses.init_pair(6, self._active_colors['Normal Cursor'][FOREGROUND], self._active_colors['Normal Cursor'][BACKGROUND])
        # status bar
        curses.init_pair(7, self._active_colors['Status Bar'][FOREGROUND], self._active_colors['Status Bar'][BACKGROUND])
        # search cursor
        curses.init_pair(8, self._active_colors['Normal Cursor'][BACKGROUND], self._active_colors['Stations'][BACKGROUND])
        # cursor when playing
        curses.init_pair(9, self._active_colors['Active Cursor'][FOREGROUND], self._active_colors['Active Cursor'][BACKGROUND])

    def restoreActiveTheme(self):
        self._active_colors = deepcopy(self._read_colors)
        if self._transparent:
            self._active_colors['Stations'][BACKGROUND] = -1
        self._do_init_pairs()

    def readAndApplyTheme(self, a_theme, use_transparency=None):
        self.open_theme(a_theme)
        if self._applied_theme_max_colors > curses.COLORS:
            # TODO: return error
            self._load_default_theme(self.applied_theme_name)
        else:
            self.applied_theme_name = a_theme

        self._active_colors = None
        self._active_colors = deepcopy(self._colors)
        if use_transparency is None:
            if self._transparent:
                self._active_colors['Stations'][BACKGROUND] = -1
        else:
            if use_transparency:
                self._active_colors['Stations'][BACKGROUND] = -1
        self._do_init_pairs()
        self._read_colors = deepcopy(self._colors)

    def _load_default_theme(self, a_theme):
        self.applied_theme_name = 'dark'
        self._applied_theme_max_colors = 8
        try_theme = a_theme.replace('_16_colors', '')
        if try_theme == 'light':
            self.applied_theme_name = try_theme
        self.open_theme(self.applied_theme_name)

    def open_theme(self, a_theme = ''):
        if not a_theme.strip():
            a_theme = 'dark'

        if a_theme == 'dark' or a_theme == 'default':
            self._colors['Stations'] = [ curses.COLOR_WHITE, curses.COLOR_BLACK ]
            self._colors['Status Bar'] = [ curses.COLOR_BLACK, curses.COLOR_GREEN ]
            # selection
            self._colors['Normal Cursor'] = [ curses.COLOR_BLACK, curses.COLOR_MAGENTA ]
            self._colors['Active Cursor'] = [ curses.COLOR_BLACK, curses.COLOR_GREEN ]
            self._colors['Active Station']  = [ curses.COLOR_GREEN, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ curses.COLOR_GREEN, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ curses.COLOR_BLUE, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], curses.COLOR_YELLOW ]
            self._colors['Messages Border'] = [ curses.COLOR_YELLOW, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 8
            self._colors['Name'] = 'dark'
            self._colors['Path'] = ''

        elif a_theme == 'dark_16_colors':
            self._colors['Stations'] = [ 15, 8 ]
            self._colors['Status Bar'] = [ curses.COLOR_BLACK, 10 ]
            # selection
            self._colors['Normal Cursor'] = [ curses.COLOR_BLACK, 13 ]
            self._colors['Active Cursor'] = [ curses.COLOR_BLACK, 10 ]
            self._colors['Active Station']  = [ 10, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ 10, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ 12, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], 11 ]
            self._colors['Messages Border'] = [ 11, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 16
            self._colors['Name'] = 'dark_16_colors'
            self._colors['Path'] = ''

        elif a_theme == 'light':
            self._colors['Stations'] = [ curses.COLOR_BLACK, curses.COLOR_WHITE ]
            self._colors['Status Bar'] = [ curses.COLOR_WHITE, curses.COLOR_BLUE ]
            # selection
            self._colors['Normal Cursor'] = [ curses.COLOR_WHITE, curses.COLOR_MAGENTA ]
            self._colors['Active Cursor'] = [ curses.COLOR_WHITE, curses.COLOR_BLUE ]
            self._colors['Active Station']  = [ curses.COLOR_RED, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ curses.COLOR_RED, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ curses.COLOR_BLUE, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], curses.COLOR_RED ]
            self._colors['Messages Border'] = [ curses.COLOR_MAGENTA, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 8
            self._colors['Name'] = 'dark'
            self._colors['Path'] = ''

        elif a_theme == 'light_16_colors':
            self._colors['Stations'] = [ 8, 15 ]
            self._colors['Status Bar'] = [ 15, 12 ]
            # selection
            self._colors['Normal Cursor'] = [ 15, 13 ]
            self._colors['Active Cursor'] = [ 15, 12 ]
            self._colors['Active Station']  = [ 9, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ 9, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ 12, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], 9 ]
            self._colors['Messages Border'] = [ 13, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 16
            self._colors['Name'] = 'light_16_colors'
            self._colors['Path'] = ''

        elif a_theme == 'black_on_white' or a_theme == 'bow':
            self._colors['Stations'] = [ 245, 15 ]
            self._colors['Status Bar'] = [ 15, 245 ]
            # selection
            self._colors['Normal Cursor'] = [ 15, 245 ]
            self._colors['Active Cursor'] = [ 0, 245 ]
            self._colors['Active Station']  = [ 0, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ 0, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ 0, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], 245 ]
            self._colors['Messages Border'] = [ 245, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 256
            self._colors['Name'] = 'black_on_white'
            self._colors['Path'] = ''

        elif a_theme == 'white_on_black' or a_theme == 'wob':
            self._colors['Stations'] = [ 247, 235 ]
            self._colors['Status Bar'] = [ 234, 253 ]
            # selection
            self._colors['Normal Cursor'] = [ 235, 247, ]
            self._colors['Active Cursor'] = [ 235, 253 ]
            self._colors['Active Station']  = [ 255, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ 255, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ 253, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], 235 ]
            self._colors['Messages Border'] = [ 247, self._colors['Stations'][BACKGROUND] ]
            # info
            self._colors['Colors'] = 256
            self._colors['Name'] = 'white_on_black'
            self._colors['Path'] = ''

        else:
            # TODO: read a theme from disk
            self._load_default_theme(self.applied_theme_name)

        self._applied_theme_max_colors = self._colors['Colors']
        self.applied_theme_name = self._colors['Name']

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

class PyRadioThemeSelector(object):
    """ Theme Selector Window """
    TITLE = ' Available Themes '
    parent = None
    _win = None
    _width = _height = X = Y = 0
    selection = _selection = _start_pos = _items = 0

    _themes = []

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

    def __init__(self, parent, theme,
            applied_theme_name, applied_theme_max_colors,
            config_theme_name,
            title_color_pair, box_color_pair,
            applied_color_pair, normal_color_pair,
            cursor_color_pair, applied_cursor_color_pair,
            is_transparent, log_file=''):
        self.parent = parent
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
            self._themes.append([ 'dark_16_colors', 'dark_16_colors' ])
            self._items += 1
        self._themes.append([ 'light', 'light' ])
        if curses.COLORS >= 16:
            self._themes.append([ 'light_16_colors', 'light_16_colors' ])
            self._items += 1
        if curses.COLORS == 256:
            self._themes.append([ 'black_on_white', 'black_on_white' ])
            self._themes.append([ 'white_on_black', 'white_on_black' ])
            self._items += 2
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('*** items = {}'.format(self._items))
        self._max_title_width = len(self.TITLE)


        ###################################################################
        #self._themes.append([ 'p light', 'p light' ])
        #self._themes.append([ 'p black_on_white', 'p black_on_white' ])
        #self._themes.append([ 'p white_on_black', 'p white_on_black' ])
        ###################################################################
        #self._themes.append([ 'my light', 'my light' ])
        #self._themes.append([ 'my black_on_white', 'my black_on_white' ])
        #self._themes.append([ 'my white_on_black', 'my white_on_black' ])
        ###################################################################

        for a_theme in self._themes:
            if len(a_theme[0]) > self._max_title_width:
                self._max_title_width = len(a_theme[0])

        if self.log:
            self.log('max_title_width = {}\n'.format(self._max_title_width))
        self._get_config_and_applied_theme()
        self._get_metrics()

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
        self._win=curses.newwin(self._height, self._width, self.Y, self.X)
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

    def refresh(self):
        if self.log:
            self.log('======================\n')
            self.log('{}\n'.format(self._themes))
        for i in range(self._start_pos, self._start_pos + self._items):
            token = ' '
            if self._start_pos + i == self.selection:
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
            self._win.addstr(i+1, 1, token + self._themes[i][0], col)

        try:
            self._win.move(sel, self._width - 2)
        except:
            pass
        # display trasnparency indicator
        if self._transparent:
            self._win.addstr(self._height-1, self._width -4, '[T]', curses.color_pair(self._box_color_pair))
        else:
            self._draw_box()
        self._win.refresh()
        curses.doupdate()

    def _draw_box(self):
        self._win.box()
        self._win.move(0,1)
        self._win.addstr(self.TITLE, curses.color_pair(self._title_color_pair))

    def _go_up(self):
        self._selection -= 1
        if self._selection < 0:
            self.selection = len(self._themes) - 1
        elif self._selection == self._start_pos -1:
            self._start_pos -= 1
        self.refresh()

    def _go_down(self):
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

    def keypress(self, char):
        """ returns theme_id, save_theme
            return_id
              0-..  : id in self._theme
              -1    : end or canel
              -2    : go no
            save_them
              True  : theme is to be saved in config
              False : theme is not to be saved in config
        """
        if char in (curses.KEY_ENTER, ord('\n'),
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
                if num >= 0:
                    self.selection = num
                    self.jumpnr = ''
        elif char in (curses.KEY_NPAGE, ):
            self.jumpnr = ''
            sel = self._selection + self._page_jump
            if self._selection == len(self._themes) - 1:
                sel = 0
            elif sel >= len(self._themes):
                sel = len(self._themes) - 1
            self.selection = sel
        elif char in (curses.KEY_PPAGE, ):
            self.jumpnr = ''
            sel = self._selection - self._page_jump
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
                        self._theme.readAndApplyTheme(self._config_theme_name)
                        self._applied_theme = self._config_theme
                        self._applied_theme_name = self._config_theme_name
                self.selection = -1
                return -1, False
        return -2, False

    def _log(self, msg):
        with open(self._log_file, 'a') as log_file:
            log_file.write(msg)

