# -*- coding: utf-8 -*-
import curses
import curses.ascii
import logging
from sys import version_info

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

class SimpleCursesLineEdit(object):
    """ Class to insert one line of text
    Python 3 supports all chars
    Python 2 supports ascii only

    """
    string = ''
    _string = ''

    """ windows """
    parent_win = None
    _caption_win = None     # contains box and caption
    _edit_win = None        # contains the "input box"

    """ Default value for string length """
    _string_len = 20

    _curs_pos = 0

    """ init values """
    y = x = 0
    caption = 'Insert string'
    _disp_caption =  ' Insert string: '
    title = ''
    _disp_title = ''
    _boxed = False
    box_color = 0
    caption_color = 0
    title_color = 0
    edit_color = 0
    cursor_color = curses.A_REVERSE
    _has_history = False
    _input_history = None
    _key_up_function_handler = None
    _key_down_function_handler = None
    _key_pgup_function_handler = None
    _key_pgdown_function_handler = None
    _key_tab_function_handler = None
    _key_stab_function_handler = None
    _ungetch_unbound_keys = False

    focused = True
    _focused = True

    _max_width = 0

    """ string to redisplay after exiting help """
    restore_data = []

    log = None
    _log_file = ''

    def __init__(self, parent, begin_y, begin_x, **kwargs):

        self.parent_win = parent
        self.y = begin_y
        self.x = begin_x

        for key, value in kwargs.items():
            if key == 'boxed':
                self._boxed = value
            elif key == 'string':
                self._string = value
            elif key == 'string_len':
                self._string_len = value
            elif key == 'caption':
                """ string on editing line """
                self.caption = value
            elif key == 'title':
                """ string on box """
                self.title = value
            elif key == 'box_color':
                self.box_color = value
            elif key == 'caption_color':
                self.caption_color = value
            elif key == 'title_color':
                self.title_color = value
            elif key == 'edit_color':
                self.edit_color = value
            elif key == 'cursor_color':
                self.cursor_color = value
            elif key == 'has_history':
                self._has_history = value
            elif key == 'ungetch_unbound_keys':
                self._ungetch_unbound_keys =  value
            elif key == 'log_file':
                self._log_file = value
                self.log = self._log
            elif key == 'key_up_function_handler':
                # callback function for KEY_UP
                self._key_up_function_handler = value
            elif key == 'key_down_function_handler':
                # callback function for KEY_DOWN
                self._key_down_function_handler = value
            elif key == 'key_pgup_function_handler':
                # callback function for KEY_PPAGE
                self._key_pgup_function_handler = value
            elif key == 'key_pgdown_function_handler':
                # callback function for KEY_NPAGE
                self._key_pgdown_function_handler = value
            elif key == 'key_tab_function_handler':
                # callback function for TAB
                self._key_tab_function_handler = value
            elif key == 'key_stab_function_handler':
                # callback function for KEY_STAB
                self._key_stab_function_handler = value

        if self._has_history:
            self._input_history = SimpleCursesLineEditHistory()
        self.height, self.width = self._calculate_window_metrics()

    @property
    def focused(self):
        return self._focused

    @focused.setter
    def focused(self, val):
        if val != self._focused:
            self._focused = val
            #self.show(self.parent_win)

    @property
    def string(self):
        return self._string

    @string.setter
    def string(self, val):
        self._string = val
        self._curs_pos = len(self._string)

    def getmaxyx(self):
        return self._caption_win.getmaxyx()

    def _calculate_window_metrics(self):
        if self.caption:
            if self._boxed:
                self._disp_caption = ' ' + self.caption + ': '
                if self.title:
                    self._disp_title = ' ' + self._disp_title + ' '
                else:
                    self._disp_title = ''
            else:
                self._disp_caption = self.caption + ': ['
                if self.title:
                    self._disp_title = self._disp_title
                else:
                    self._disp_title = ''
        else:
            self._disp_caption = '['
        width = len(self._disp_caption) + self._string_len + 4
        if self._boxed:
            height = 3
        else:
            height = 1
            width -= 2
        if self.log is not None:
            self.log('height = {0}, width = {1}\n'.format(height, width))
        return height, width

    def _prepare_to_show(self):
        caption_col = self.caption_color
        height, width = self._calculate_window_metrics()
        self._caption_win = curses.newwin(height, width, self.y, self.x)
        maxY, maxX = self._caption_win.getmaxyx()
        if self._boxed:
            self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 2, self.y + 1, self.x + len(self._disp_caption) + 1)
            self._caption_win.addstr(1, 1, self._disp_caption, self.caption_color)
        else:
            self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 1, self.y, self.x + len(self._disp_caption))
            self._caption_win.addstr(0, 0, self._disp_caption, self.caption_color)
            try:
                # printing at the end of the window, do not break...
                self._caption_win.addstr(0, maxX - 1, ']', self.caption_color)
            except:
                pass
        maxY, maxX = self._edit_win.getmaxyx()
        #self._caption_win.bkgd('*', curses.A_REVERSE)
        if self._boxed:
            self._max_width = maxX - 1
        else:
            self._max_width = maxX

    def refreshEditWindow(self, opening=False):
        if self.focused:
            active_edit_color = self.edit_color
        else:
            active_edit_color = self.caption_color
        self._edit_win.erase()
        #self._edit_win.bkgd('-', curses.A_REVERSE)
        if opening:
            if self.restore_data:
                self._string = self.restore_data[0]
                self._curs_pos = self.restore_data[1]
                self._edit_win.addstr(0, 0, self._string, active_edit_color)
                self.restore_data = []
            else:
                self._curs_pos = 0
        else:
            if self._string:
                self._edit_win.addstr(0, 0, self._string, active_edit_color)
            else:
                self._curs_pos = 0
        if self.log is not None:
            self.log(' - curs_pos = {}\n'.format(self._curs_pos))
        if self.focused:
            self._edit_win.chgat(0, self._curs_pos, 1, self.cursor_color)

        self._edit_win.refresh()

    def show(self, parent_win, new_y=-1, new_x=-1):
        self._caption_win = None
        self._edit_win = None
        if parent_win is not None:
            self.parent_win = parent_win
        if new_y >= 0:
            self.y = new_y
            if self.log is not None:
                self.log('self.y = {}\n'.format(self.y))
        if new_x >= 0:
            self.x = new_x
            if self.log is not None:
                self.log('self.x = {}\n'.format(self.x))
        self._prepare_to_show()
        self._caption_win.bkgdset(' ', self.box_color)
        self._edit_win.bkgdset(' ', self.box_color)
        if self._boxed:
            self._caption_win.box()
            if self._disp_title:
                self._title_win.addstr(0, 1, self._disp_title, self.title_color)
        self._caption_win.refresh()
        self.refreshEditWindow(opening=True)

    def keypress(self, win, char):
        """
         returns:
            2: display help
            1: get next char
            0: exit edit mode, string isvalid
           -1: cancel
        """
        #self._log_file='/home/spiros/edit.log'
        #self.log = self._log
        if not self._focused:
            return 1
        if self.log is not None:
            self.log('char = {}\n'.format(char))
        if char in (ord('?'), ):
            # display help
            return 2
        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            """ ENTER """
            if self._has_history:
                self._input_history.add_to_history(self._string)
            return 0
        elif char in (curses.KEY_EXIT, 27):
            self._edit_win.nodelay(True)
            char = self._edit_win.getch()
            if self.log is not None:
                self.log('   *** char = {}\n'.format(char))
            self._edit_win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                self._string = ''
                self._curs_pos = 0
                self._input_history.reset_index()
                return -1
            else:
                if self.log is not None:
                    self.log('   *** char = {}\n'.format(char))
                if char in (ord('d'), ):
                    """ A-D, clear to end of line """
                    self.string = self._string[:self._curs_pos]
                elif char in (ord('f'), ):
                    """ A-F, move to next word """
                    pos = len(self._string)
                    for n in range(self._curs_pos + 1, len(self._string)):
                        if self._string[n] == ' ':
                            pos = n
                            break
                    self._curs_pos = pos
                elif char in (ord('b'), ):
                    """ A-B, move to previous word """
                    pos = 0
                    for n in range(self._curs_pos - 1, 0, -1):
                        if self._string[n] == ' ':
                            pos = n
                            break
                    self._curs_pos = pos
                else:
                    return 1
        elif char in (curses.KEY_RIGHT, ):
            """ KEY_RIGHT """
            self._curs_pos += 1
            if len(self._string) < self._curs_pos:
                self._curs_pos = len(self._string)
        elif char in (curses.KEY_LEFT, ):
            """ KEY_LEFT """
            self._curs_pos -= 1
            if self._curs_pos < 0:
                self._curs_pos = 0
        elif char in (curses.KEY_HOME, curses.ascii.SOH):
            """ KEY_HOME, ^A """
            self._curs_pos = 0
        elif char in (curses.KEY_END, curses.ascii.ENQ):
            """ KEY_END, ^E """
            self._curs_pos = len(self._string)
        elif char in (curses.ascii.ETB, ):
            """ ^W, clear to start of line """
            self.string = self._string[self._curs_pos:]
            self._curs_pos = 0
        elif char in (curses.ascii.NAK, ):
            """ ^U, clear line """
            self.string = ''
        elif char in (curses.KEY_DC, curses.ascii.EOT):
            """ DEL key, ^D """
            if self._curs_pos < len(self._string):
                self._string = self._string[:self._curs_pos] + self._string[self._curs_pos+1:]
        elif char in (curses.KEY_BACKSPACE, curses.ascii.BS,127):
            """ KEY_BACKSPACE """
            if self._curs_pos > 0:
                self._string = self._string[:self._curs_pos-1] + self._string[self._curs_pos:]
                self._curs_pos -= 1
        elif char in (curses.KEY_UP, curses.ascii.DLE):
            """ KEY_UP, ^N """
            if self._key_up_function_handler is not None:
                try:
                    self._key_up_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
        elif char in (curses.KEY_DOWN, curses.ascii.SO):
            """ KEY_DOWN, ^P """
            if self._key_down_function_handler is not None:
                try:
                    self._key_down_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
        elif char in (curses.KEY_NPAGE, ):
            """ PgDn """
            if self._key_pgdown_function_handler is not None:
                try:
                    self._key_pgdown_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
        elif char in (curses.KEY_PPAGE, ):
            """ PgUp """
            if self._key_pgup_function_handler is not None:
                try:
                    self._key_pgup_function_handler()
                except:
                    pass
        elif char in (9, ):
            """ TAB """
            if self._key_tab_function_handler is not None:
                try:
                    self._key_tab_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
        elif char in (curses.KEY_BTAB, ):
            """ Shift-TAB """
            if self._key_stab_function_handler is not None:
                try:
                    self._key_stab_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
        elif char in (curses.ascii.VT, ):
            """ Ctrl-K - delete to end of line """
            self._string = self._string[:self._curs_pos]
        elif 0<= char <=31:
            pass
        else:
            if self.log is not None:
                self.log('====================\n')
            if len(self._string) + 1 == self._max_width:
                return 1
            if version_info < (3, 0):
                if 32 <= char < 127:
                    # accept only ascii characters
                    if len(self._string) == self._curs_pos:
                        self._string += chr(char)
                    else:
                        self._string = self._string[:self._curs_pos] + chr(char) + self._string[self._curs_pos:]
                    self._curs_pos += 1
            else:
                char = self._get_char(win, char)
                if len(self._string) == self._curs_pos:
                    self._string += char
                else:
                    self._string = self._string[:self._curs_pos] + char + self._string[self._curs_pos:]
                self._curs_pos += 1

        self.refreshEditWindow()
        return 1

    def _get_char(self, win, char):
        def get_check_next_byte():
            char = win.getch()
            if 128 <= char <= 191:
                return char
            else:
                raise UnicodeError

        bytes = []
        if char <= 127:
            # 1 bytes
            bytes.append(char)
        #elif 194 <= char <= 223:
        elif 192 <= char <= 223:
            # 2 bytes
            bytes.append(char)
            bytes.append(get_check_next_byte())
        elif 224 <= char <= 239:
            # 3 bytes
            bytes.append(char)
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
        elif 240 <= char <= 244:
            # 4 bytes
            bytes.append(char)
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
        """ no zero byte allowed """
        while 0 in bytes:
            bytes.remove(0)
        if version_info < (3, 0):
            out = ''.join([chr(b) for b in bytes])
        else:
            buf = bytearray(bytes)
            out = self._decode_string(buf)
            #out = buf.decode('utf-8')
        return out

    def _encode_string(self, data):
        encodings = ['utf-8', locale.getpreferredencoding(False), 'latin1']
        for enc in encodings:
            try:
                data = data.encode(enc)
            except:
                continue
            break

        assert type(data) != bytes  # Latin1 should have worked.
        return data

    def _decode_string(self, data):
        encodings = ['utf-8', locale.getpreferredencoding(False), 'latin1']
        for enc in encodings:
            try:
                data = data.decode(enc)
            except:
                continue
            break

        assert type(data) != bytes  # Latin1 should have worked.
        return data

    def _log(self, msg):
        with open(self._log_file, 'a') as log_file:
            log_file.write(msg)

    def run(self):
        self._edit_win.nodelay(False)
        self._edit_win.keypad(True)
        # make sure we don't get into an infinite loop
        self._ungetch_unbound_keys = False
        try:
            curses.curs_set(0)
        except:
            pass

        while True:
            char = self._edit_win.getch()
            ret = self.keypress(char)
            if ret != 1:
                return ret

class SimpleCursesLineEditHistory(object):

    def __init__(self):
        self._history = []
        self._active_history_index = -1

    def add_to_history(self, a_string):
        if self._history:
            if len(self._history) > 1:
                for i, a_history_item in enumerate(self._history):
                    if a_history_item.lower() == a_string.lower():
                        self._history.pop(i)
                        break
            if self._history[-1].lower() != a_string.lower():
                self._history.append(a_string)
        else:
            self._history.append(a_string)
        self._active_history_index = len(self._history)

    def return_history(self, direction):
        if self._history:
            self._active_history_index += direction
            if self._active_history_index <= -1:
                self._active_history_index = len(self._history) - 1
            elif self._active_history_index >= len(self._history):
                self._active_history_index = 0
            ret =  self._history[self._active_history_index]
            return ret
        return ''

    def reset_index(self):
        self._active_history_index = -1

