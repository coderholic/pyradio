import curses
import curses.ascii
import logging
from sys import version_info
from .simple_widgets import SimpleCursesLineEdit
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
        if repaint is False:
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
                if self.string.lower() in a_list[n][0].lower():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list top """
            for n in eval(self._range_command)(0, start):
                if self.string.lower() in a_list[n][0].lower():
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
                if self.string.lower() in a_list[n][0].lower():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list end """
            for n in eval(self._range_command)(len(a_list) - 1, start, -1):
                if self.string.lower() in a_list[n][0].lower():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('backward search term "{}" not found'.format(self.string))
            return None
        else:
            return None

