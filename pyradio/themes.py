import curses
import copy
import sys
import logging
import glob
from os import path, getenv, makedirs, remove
from shutil import copyfile, move
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

    def __init__(self):
        self._colors['status_bar'] = [ -1, -1 ]
        self._colors['stations'] = [ -1, -1 ]
        self._colors['selection'] = [ -1, -1 ]
        self._colors['active_selection'] = [ -1, -1 ]
        self._colors['pop_up'] = [ -1, -1, -1, -1 ]
        self._colors['title'] = [ -1, -1 ]
        self._colors['url'] = [ -1, -1 ]

        _colors_max = 7

    def __del__(self):
        self._colors = None
        self._active_colors = None
        self._read_colors = None

    def restoreActiveTheme(self):
        self._active_colors = copy.deepcopy(self._read_colors)
        if self._transparent:
            self._active_colors['Stations'][BACKGROUND] = -1
        curses.init_pair(1, curses.COLOR_CYAN, self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(2, self._active_colors['PyRadio URL'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(3, self._active_colors['Messages Border'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(4, self._active_colors['Active Station'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(5, self._active_colors['Stations'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(6, self._active_colors['Normal Cursor'][FOREGROUND], self._active_colors['Normal Cursor'][BACKGROUND])
        curses.init_pair(7, self._active_colors['Status Bar'][FOREGROUND], self._active_colors['Status Bar'][BACKGROUND])
        curses.init_pair(8, self._active_colors['Normal Cursor'][BACKGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(9, self._active_colors['Active Cursor'][FOREGROUND], self._active_colors['Active Cursor'][BACKGROUND])


    def readAndApplyTheme(self, a_theme):
        self.open_theme(a_theme)
        self._active_colors = None
        self._active_colors = copy.deepcopy(self._colors)
        if self._transparent:
            self._active_colors['Stations'][BACKGROUND] = -1
        curses.init_pair(1, curses.COLOR_CYAN, self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(2, self._active_colors['PyRadio URL'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(3, self._active_colors['Messages Border'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(4, self._active_colors['Active Station'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(5, self._active_colors['Stations'][FOREGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(6, self._active_colors['Normal Cursor'][FOREGROUND], self._active_colors['Normal Cursor'][BACKGROUND])
        curses.init_pair(7, self._active_colors['Status Bar'][FOREGROUND], self._active_colors['Status Bar'][BACKGROUND])
        curses.init_pair(8, self._active_colors['Normal Cursor'][BACKGROUND], self._active_colors['Stations'][BACKGROUND])
        curses.init_pair(9, self._active_colors['Active Cursor'][FOREGROUND], self._active_colors['Active Cursor'][BACKGROUND])
        self._read_colors = copy.deepcopy(self._colors)


    def _load_default_theme(self):
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
            self._colors_max = 8

    def open_theme(self, a_theme = ''):
        if not a_theme.strip():
            a_theme = 'default'

        if a_theme == 'dark' or a_theme == 'default':
            self._load_default_theme()

        elif a_theme == 'light':
            self._colors['Stations'] = [ curses.COLOR_BLACK, curses.COLOR_WHITE ]
            self._colors['Status Bar'] = [ curses.COLOR_YELLOW, curses.COLOR_BLUE ]
            # selection
            self._colors['Normal Cursor'] = [ curses.COLOR_WHITE, curses.COLOR_MAGENTA ]
            self._colors['Active Cursor'] = [ curses.COLOR_YELLOW, curses.COLOR_BLUE ]
            self._colors['Active Station']  = [ curses.COLOR_RED, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ curses.COLOR_RED, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ curses.COLOR_BLUE, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], curses.COLOR_RED ]
            self._colors['Messages Border'] = [ curses.COLOR_MAGENTA, self._colors['Stations'][BACKGROUND] ]
            self._colors_max = 8

        elif a_theme == 'black_on_white' or a_theme == 'bow':
            self._colors['Stations'] = [ 245, 253 ]
            self._colors['Status Bar'] = [ 253, 245 ]
            # selection
            self._colors['Normal Cursor'] = [ 253, 245 ]
            self._colors['Active Cursor'] = [ 235, 245 ]
            self._colors['Active Station']  = [ 235, self._colors['Stations'][BACKGROUND] ]
            # Titles
            self._colors['Titles'] = [ 235, self._colors['Stations'][BACKGROUND] ]
            self._colors['PyRadio URL'] = [ 235, self._colors['Stations'][BACKGROUND] ]
            # help window
            self._colors['Messages'] = [ self._colors['Titles'][FOREGROUND], 245 ]
            self._colors['Messages Border'] = [ 245, self._colors['Stations'][BACKGROUND] ]
            self._colors_max = 255

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
            self._colors_max = 255

        else:
            # TODO: read a theme from disk
            self._load_default_theme()

        if self._colors_max >= curses.COLORS:
            # TODO: return error
            self._load_default_theme()

    def toggleTransparency(self):
        self._transparent = not self._transparent
        self.restoreActiveTheme()
