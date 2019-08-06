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

    _caption = 'Search'

    def __init__(self, parent, width, begin_y, begin_x, **kwargs):
        SimpleCursesLineEdit.__init__(self, parent, width, begin_y, begin_x,
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
        new_y = y - self._height + 1
        new_x = x - self._width
        super(PyRadioSearch, self).show(self.parent_win, new_y=new_y, new_x=new_x)
        y, x = self._caption_win.getmaxyx()
        if self._boxed:
            try:
                self._caption_win.addstr(2, 0, '┴', self.box_color)
                self._caption_win.addstr(0, x-1, '┤', self.box_color)
                pass
            except:
                self._caption_win.addstr(2, 0, '┴'.encode('utf-8'), self.box_color)
                try:
                    self._caption_win.addstr(0, x-1, '┤'.encode('utf-8'), self.box_color)
                except:
                    pass
        if not repaint:
            self.string = ''
            self._curs_pos = 0
            if self._has_history:
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
        self._edit_win.addstr(0,0,'Term not found!'.ljust(self._max_chars_to_display), self.edit_color)
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
    _adding = True

    """ Indicates that we append to the stations' list
        Only valid when adding = True """
    _append = False

    _focus = 0

    _line_editor = [ None, None ]
    _line_editor_yx = ( (3, 2), (6, 2) )

    _item = []
    _orig_item = []
    _encoding ='utf-8'

    _dirty = False

    def __init__(self, stations, selection, parent, adding=True):
        self._stations = stations
        self._selection = selection
        self._pos_to_insert = selection + 1
        self._parent_win = parent
        self._adding = adding

    @property
    def append(self):
        return self._append

    @append.setter
    def append(self, val):
        if self._adding:
            self._append = val
            self._pos_to_insert = len(self._stations)

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0,5):
            self._focus = val
        else:
            if val < 0:
                self._focus = 4
            else:
                self._focus = 0
        self.show()

    def set_parent(self, val, refresh=True):
        self._parent_win = val
        if refresh:
            self.show()

    @property
    def item(self):
        return self._item

    @item.setter
    def item(self, item):
        self._set_item(item)
        self.show()

    def _set_item(self, item):
        self._add_editors()
        if item:
            self._line_editor[0].string = item[0]
            self._line_editor[1].string = item[1]
        else:
            self._line_editor[0].string = ''
            self._line_editor[1].string = ''
        if item[2]:
            self._encoding = item[2]
        else:
            self._encoding = 'utf-8'
        self._item = item
        self._orig_item = item

    def _add_editors(self):
        for ed in range(0,2):
            if self._line_editor[ed] is None:
                self._line_editor[ed] = SimpleCursesLineEdit(parent = self._win,
                    width = -2,
                    begin_y = self._line_editor_yx[ed][0],
                    begin_x = self._line_editor_yx[ed][1],
                    boxed = False,
                    has_history = False,
                    caption='',
                    box_color = curses.color_pair(9),
                    caption_color = curses.color_pair(4),
                    edit_color = curses.color_pair(9),
                    cursor_color = curses.color_pair(6),
                    unfocused_color = curses.color_pair(5))
                self._line_editor[ed].bracket = False

    def show(self, item=None):
        self._win = None
        self.maxY, self.maxX = self._parent_win.getmaxyx()

        self._win = curses.newwin(self.maxY, self.maxX, 1, 0)
        self._add_editors()
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()

        self._show_title()

        logger.error('DE maxY = {}'.format(self.maxY))
        if self.maxY < 22 or self.maxX < 72:
            txt = ' Window too small to display content '
            error_win = curses.newwin(3, len(txt) + 2, int(self.maxY / 2) - 1, int((self.maxX - len(txt)) / 2))
            error_win.bkgdset(' ', curses.color_pair(3))
            error_win.erase()
            error_win.box()
            error_win.addstr(1, 1, txt, curses.color_pair(4))
            self._win.refresh()
            error_win.refresh()
            return 0

        self._win.addstr(1, 2, 'Name', curses.color_pair(4))
        self._win.addstr(4, 2, 'URL', curses.color_pair(4))
        self._show_encoding()
        self._show_buttons()
        try:
            self._win.addstr(11, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(11, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(11, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
        self._win.addstr(12, 5, 'TAB', curses.color_pair(4))
        self._win.addstr(', ', curses.color_pair(5))
        self._win.addstr('Up', curses.color_pair(4))
        self._win.addstr('    Go to next field.', curses.color_pair(5))
        self._win.addstr(13, 5, 'Down', curses.color_pair(4))
        self._win.addstr('       Go to previous field.', curses.color_pair(5))
        self._win.addstr(14, 5, 'ENTER', curses.color_pair(4))
        self._win.addstr('      When in line editor, go to next field.', curses.color_pair(5))
        self._win.addstr(15, 16, 'When in Encoding field, open Encoding selection window.', curses.color_pair(5))
        self._win.addstr(16, 16, 'Otherwise, save station data or cancel operation.', curses.color_pair(5))
        step = 0
        if not self._adding:
            self._win.addstr(17, 5, '^R', curses.color_pair(4))
            self._win.addstr(17, 16, 'Revert to original data (start over).', curses.color_pair(5))
            step = 1
        self._win.addstr(17 + step, 5, 'Esc', curses.color_pair(4))
        self._win.addstr(17 + step, 16, 'Cancel operation.', curses.color_pair(5))


        self._win.addstr(18 + step, 5, 's', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('q', curses.color_pair(4))
        self._win.addstr('      Save data / Cancel operation (not in line editor).', curses.color_pair(5))

        self._win.addstr(19 + step, 5, '?', curses.color_pair(4))
        self._win.addstr(19 + step, 16, 'Line editor help.', curses.color_pair(5))

        if item:
            self._set_item(item)
            self._show_encoding()
        self._win.refresh()
        self._update_focus()
        for ed in range(0,2):
            self._line_editor[ed].show(self._win, opening=False)

    def _show_encoding(self):
        sid = 2
        if self._focus == sid:
            col = 9
        else:
            col = 5
        self._win.addstr(7, 2, 'Encoding:', curses.color_pair(4))
        self._win.addstr(' ' * (self.maxX - 13), curses.color_pair(4))
        self._win.addstr(7, 11, ' ' + self._encoding + ' ', curses.color_pair(col))

    def _show_title(self):
        token = ''
        if not self._adding:
            try:
                if (self._line_editor[0].string == self._orig_item[0]) and \
                        (self._line_editor[1].string == self._orig_item[1]):
                    if (self._encoding == self._orig_item[2]) or \
                            (self._encoding == 'utf-8' and self._orig_item[2] == ''):
                        self._dirty = False
                    else:
                        self._dirty = True
                        token = '*'
                else:
                    self._dirty = True
                    token = '*'
            except:
                pass

        title = '── {}Station Editor '.format(token)
        x = int((self.maxX - len(title)) / 2)
        try:
            self._win.addstr(0, x, title, curses.color_pair(4))
        except:
            self._win.addstr(0, x, title.encode('utf-8'), curses.color_pair(4))
        if token:
            self._win.chgat(0, x, 4, curses.color_pair(3))
        else:
            self._win.chgat(0, x, 2, curses.color_pair(3))
        self._win.refresh()


    def _show_buttons(self):
        sid = 3
        if self._focus == sid:
            col = 9
        else:
            col = 5
        self._win.addstr(9, int((self.maxX - 18) /2), '[', curses.color_pair(4))
        self._win.addstr(' OK ', curses.color_pair(col))
        self._win.addstr(']  [', curses.color_pair(4))

        sid = 4
        if self._focus == sid:
            col = 9
        else:
            col = 5
        self._win.addstr(' Cancel ', curses.color_pair(col))
        self._win.addstr(']', curses.color_pair(4))

    def _update_focus(self):
        self._line_editor[0].focused = False
        self._line_editor[1].focused = False
        if self._focus == 0:
            self._line_editor[0].focused = True
        elif self._focus == 1:
            self._line_editor[1].focused = True

    def keypress(self, char):
        """ Returns:
                -1: Cancel
                 0: go on
                 1: Ok
                 2: display line editor help
        """
        ret = 0
        if char in ( ord('\t'), 9, curses.KEY_DOWN):
            self.focus +=1
        elif char == curses.KEY_UP:
            self.focus -=1
        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            if self._focus == 0:
                # Name
                self.focus +=1
            elif self._focus == 1:
                # URL
                self.focus +=1
            elif self._focus == 2:
                # encoding
                pass
            elif self._focus == 3:
                # ok
                ret = -1
            elif self._focus == 4:
                # cancel
                ret = -1
        elif char in (curses.KEY_EXIT, 27):
            ret = -1
        elif char == ord('s') and self._focus > 1:
            ret = -1
        elif char == ord('q') and self._focus > 1:
            ret = -1
        elif char == ord('?'):
            ret = 2
        elif char == curses.ascii.DC2 and not self._adding:
            # ^R, revert to saved
            self.item = self._orig_item
        elif self._focus <= 1:
            """
             Returns:
                2: display help
                1: get next char
                0: exit edit mode, string isvalid
               -1: cancel
            """
            ret = self._line_editor[self._focus].keypress(self._win, char)
            if ret == 2:
                # display help
                ret = 2
            elif ret == 1:
                # get next char
                ret = 0
            elif ret == 0:
                # exit, string is valid
                ret = -1
            elif ret == -1:
                # cancel
                ret = -1
        self._show_title()
        return ret
