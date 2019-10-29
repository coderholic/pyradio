# -*- coding: utf-8 -*-
import curses
import curses.ascii
from time import sleep
import logging
from sys import version_info
try:
    # python 3
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
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
        if repaint:
            tmp = self.string
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
        if repaint:
            self.string = tmp
            self.keep_restore_data()
            self._caption_win.refresh()
            self.refreshEditWindow(opening=True)
        else:
            self.string = self._displayed_string = ''
            self._first = self._curs_pos = self._disp_curs_pos = 0
            self._edit_win.erase()
            self._edit_win.chgat(0, 0, 1, self.cursor_color)
            if self._has_history:
                self._input_history.reset_index()
            self._caption_win.refresh()
            self._edit_win.refresh()

    def _get_history_next(self):
        """ callback function for key down """
        if self._has_history:
            self.string = self._input_history.return_history(1, self.string)

    def _get_history_previous(self):
        """ callback function for key up """
        if self._has_history:
            self.string = self._input_history.return_history(-1, self.string)

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
    _old_encoding = 'utf-8'
    _orig_encoding ='utf-8'

    _dirty = False

    _too_small = False

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
        try:
            if item[2]:
                self._encoding = item[2]
            else:
                self._encoding = 'utf-8'
        except:
            self._encoding = 'utf-8'
        self._orig_encoding = self._encoding
        self._old_encoding  = self._encoding
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
                    cursor_color = curses.color_pair(8),
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

        if self.maxY < 22 or self.maxX < 72:
            txt = ' Window too small to display content '
            error_win = curses.newwin(3, len(txt) + 2, int(self.maxY / 2) - 1, int((self.maxX - len(txt)) / 2))
            error_win.bkgdset(' ', curses.color_pair(3))
            error_win.erase()
            error_win.box()
            error_win.addstr(1, 1, txt, curses.color_pair(4))
            self._win.refresh()
            error_win.refresh()
            self._too_small = True
            if item:
                self._orig_item = item
            return 0
        else:
            if self._too_small and self._orig_item:
                self._set_item(self._orig_item)
            self._too_small = False

        self._win.addstr(1, 2, 'Name', curses.color_pair(4))
        self._win.addstr(4, 2, 'URL', curses.color_pair(4))
        self._show_encoding()
        self._show_buttons()
        try:
            self._win.addstr(10, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(10, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(10, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
        self._win.addstr(11, 5, 'TAB', curses.color_pair(4))
        self._win.addstr(', ', curses.color_pair(5))
        self._win.addstr('Up', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('Down', curses.color_pair(4))
        self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
        self._win.addstr(12, 5, 'ENTER', curses.color_pair(4))
        self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
        self._win.addstr(13, 23, 'Otherwise, execute selected function.', curses.color_pair(5))
        step = 0
        if not self._adding:
            self._win.addstr(14, 5, 'r', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('^R', curses.color_pair(4))
            self._win.addstr(14, 23, 'Revert to saved values (', curses.color_pair(5))
            self._win.addstr('^R', curses.color_pair(4))
            self._win.addstr(' when in Line Editor).', curses.color_pair(5))
            step = 1
        self._win.addstr(14 + step, 5, 'Esc', curses.color_pair(4))
        self._win.addstr(14 + step, 23, 'Cancel operation.', curses.color_pair(5))


        self._win.addstr(15 + step, 5, 's', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('q', curses.color_pair(4))
        self._win.addstr(15 + step , 23, 'Save data / Cancel operation (not in Line Editor).', curses.color_pair(5))

        self._win.addstr(16 + step, 5, '?', curses.color_pair(4))
        self._win.addstr(16 + step, 23, 'Line editor help (in Line Editor).', curses.color_pair(5))

        try:
            self._win.addstr(17 + step, 5, '─' * (self.maxX - 10), curses.color_pair(3))
        except:
            self._win.addstr(17 + step, 3, '─'.encode('utf-8') * (self.maxX - 10), curses.color_pair(3))
        self._win.addstr(17 + step, int((self.maxX - 33) / 2), ' Player Keys (Not in Line Editor) ', curses.color_pair(4))

        self._win.addstr(18 + step, 5, '-', curses.color_pair(4))
        self._win.addstr('/', curses.color_pair(5))
        self._win.addstr('+', curses.color_pair(4))
        self._win.addstr(' or ', curses.color_pair(5))
        self._win.addstr(',', curses.color_pair(4))
        self._win.addstr('/', curses.color_pair(5))
        self._win.addstr('.', curses.color_pair(4))
        self._win.addstr(18 + step, 23, 'Change volume', curses.color_pair(5))
        self._win.addstr(19 + step, 5, 'm', curses.color_pair(4))
        self._win.addstr(' / ', curses.color_pair(5))
        self._win.addstr('v', curses.color_pair(4))
        self._win.addstr(19 + step, 23, 'M', curses.color_pair(4))
        self._win.addstr('ute player / Save ', curses.color_pair(5))
        self._win.addstr('v', curses.color_pair(4))
        self._win.addstr('olume (not in vlc).', curses.color_pair(5))

        if item:
            self._set_item(item)
            self._show_encoding()
        self._win.refresh()
        self._update_focus()
        if not self._too_small:
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
        self._win.addstr(8, int((self.maxX - 18) /2), '[', curses.color_pair(4))
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

    def _return_station(self):
        ret = self._validate()
        if ret == 1:
            if self._encoding == 'utf-8':
                self._encoding = ''
            self.new_station = [ self._line_editor[0].string.strip(), self._line_editor[1].string.strip(), self._encoding, '']
        return ret

    def _validate(self):
        if not self._line_editor[0].string.strip():
            return -2
        url = urlparse(self._line_editor[1].string.strip())
        if not (url.scheme and url.netloc):
            return -3
        if url.scheme not in ('http', 'https'):
            return -3
        if url.netloc != 'localhost':
            dot = url.netloc.find('.')
            if dot == -1:
                return -3
            elif dot > len(url.netloc) - 3:
                return -3
        return 1

    def keypress(self, char):
        """ Returns:
                -3: url is invalid
                -2: Station name is empty
                -1: Cancel (new_station = None)
                 0: go on
                 1: Ok     (new_station holds data)
                 2: display line editor help
                 3: open encoding selection window
                 4: window too small
        """
        ret = 0
        if self._too_small:
            if char in (curses.KEY_EXIT, 27, ord('q')):
                self.new_station = None
                ret = -1
        else:
            if char in (curses.KEY_EXIT, 27, ord('q')) and \
                    self.focus > 1:
                self.new_station = None
                ret = -1
            elif char in ( ord('\t'), 9, curses.KEY_DOWN):
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
                    return 3
                elif self._focus == 3:
                    # ok
                    ret = self._return_station()
                    self.focus = abs(ret + 2)
                elif self._focus == 4:
                    # cancel
                    self.new_station = None
                    ret = -1
            elif char == ord('s') and self._focus > 1:
                ret = self._return_station()
                self.focus = abs(ret + 2)
            elif (char in (curses.ascii.DC2, 18) and not self._adding) or \
                    (char == ord('r') and not self._adding and self.focus >1):
                # ^R, revert to saved
                self.item = self._orig_item
                if self.item[2]:
                    self._encoding = self.item[2]
                else:
                    self._encoding = 'utf-8'
                self._orig_encoding = self._encoding
                for i in range(0,2):
                    self._line_editor[i]._go_to_end()
            elif self._focus <= 1:
                """
                 Returns:
                    2: display help
                    1: get next char
                    0: exit edit mode, string isvalid
                   -1: cancel
                """
                ret = self._line_editor[self._focus].keypress(self._win, char)
                if ret == 1:
                    # get next char
                    ret = 0
                elif ret == 0:
                    # exit, string is valid
                    self._return_station()
                    ret = -1
                elif ret == -1:
                    # cancel
                    self.new_station = None
                    ret = -1
        self._show_title()
        return ret

