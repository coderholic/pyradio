# -*- coding: utf-8 -*-
import curses
import curses.ascii
from time import sleep
import logging
from sys import version_info
from .simple_curses_widgets import SimpleCursesLineEdit
from .log import Log

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

class PyRadioSearch(SimpleCursesLineEdit):

    caption = 'Search'

    def __init__(self, parent, begin_y, begin_x, **kwargs):
        SimpleCursesLineEdit.__init__(self, parent, begin_y, begin_x,
            key_up_function_handler=self._get_history_previous,
            key_down_function_handler=self._get_history_next,
            **kwargs)
        if version_info < (3, 0):
            self._range_command='xrange'
        else:
            self._range_command='range'

    def show(self, parent_win, repaint=False):
        if parent_win is not None:
            self.parent_win = parent_win

        y, x = self.parent_win.getmaxyx()
        new_y = y - self.height + 1
        new_x = x - self.width
        super(PyRadioSearch, self).show(self.parent_win, new_y, new_x)
        self._caption_win.addstr(2, 0, u'\u2534'.encode('utf-8'), self.box_color)
        y, x = self._caption_win.getmaxyx()
        try:
            self._caption_win.addstr(0, x-1, u'\u2524'.encode('utf-8'), self.box_color)
        except:
            pass
        if not repaint:
            self.string = ''
            self._curs_pos = 0
            self._input_history.reset_index()
        self._caption_win.refresh()
        self._edit_win.refresh()

    def _get_history_next(self):
        """ callback function for key down """
        if self._has_history:
            ret = self._input_history.return_history(1)
            self.string = ret
            self._curs_pos = len(ret)

    def _get_history_previous(self):
        """ callback function for key up """
        if self._has_history:
            ret = self._input_history.return_history(-1)
            self.string = ret
            self._curs_pos = len(ret)

    def get_next(self, a_list, start=0, stop=None):
        if self.string:
            for n in eval(self._range_command)(start, len(a_list)):
                if self.string.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list top """
            for n in eval(self._range_command)(0, start):
                if self.string.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('forward search term "{}" not found'.format(self.string))
            return None
        else:
            return None

    def get_previous(self, a_list, start=0, stop=None):
        if self.string:
            for n in eval(self._range_command)(start, -1, -1):
                if self.string.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list end """
            for n in eval(self._range_command)(len(a_list) - 1, start, -1):
                if self.string.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('backward search term "{}" not found'.format(self.string))
            return None
        else:
            return None

    def print_not_found(self):
        self._edit_win.addstr(0,0,'Term not found!'.ljust(self._max_width), self.edit_color)
        self._edit_win.refresh()
        sleep(.3)
        self.refreshEditWindow()

    def _get_string(self, item):
        if isinstance(item, str):
            return item.lower()
        else:
            return item[0].lower()

class PyRadioEditor(object):
    """ PyRadio stations editor """

    _stations = []
    _selection = _pos_to_insert = maxY = maxX = 0

    _win = None
    _parent_win = None

    """ Adding a new station or editing an existing one """
    adding = True

    """ Indicates that we append to the stations' list
        Only valid when adding = True """
    _append = False

    def __init__(self, stations, selection, parent, adding=True):
        self._stations = stations
        self._selection = selection
        self._pos_to_insert = selection + 1
        self._parent_win = parent
        self.adding = adding

    @property
    def append(self):
        return self._append

    @append.setter
    def append(self, val):
        if self.adding:
            self._append = val
            self._pos_to_insert = len(self._stations)

    def set_parent(self, val, refresh=True):
        self._parent_win = val
        if refresh:
            self.show()

    def show(self):
        self._win = None
        self.maxY, self.maxX = self._parent_win.getmaxyx()
        self._win = curses.newwin(self.maxY, self.maxX, 1, 0)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()

        title = ' Station Editor '
        self._win.addstr(0,
                int((self.maxX - len(title)) / 2),
                title,
                curses.color_pair(4))

        self._win.addstr(1, 2, 'Name', curses.color_pair(4))
        self._win.addstr(4, 2, 'URL', curses.color_pair(4))
        self._win.addstr(7, 2, 'Encoding: ', curses.color_pair(4))
        self._win.addstr(9, int((self.maxX - 18) /2), '[ OK ]  [ Cancel ]', curses.color_pair(4))
        try:
            self._win.addstr(11, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(11, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(11, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
        self._win.addstr(12, 5, 'TAB', curses.color_pair(4))
        self._win.addstr('      Go to next field.', curses.color_pair(5))
        self._win.addstr(13, 5, 'S-TAB', curses.color_pair(4))
        self._win.addstr('    Go to previous field.', curses.color_pair(5))
        self._win.addstr(14, 5, 'ENTER', curses.color_pair(4))
        self._win.addstr('    When in line editor, go to next field.', curses.color_pair(5))
        self._win.addstr(15, 14, 'When in Encoding field, open Encoding selection window.', curses.color_pair(5))
        self._win.addstr(16, 14, 'Otherwise, save station data or cancel operation.', curses.color_pair(5))

        self._win.refresh()


    def keypress(self, char):
        """ Returns:
                -1: Cancel
                 0: go on
                 1: Ok
        """
        if char in (ord('q'), ):
            return -1
        return 0
