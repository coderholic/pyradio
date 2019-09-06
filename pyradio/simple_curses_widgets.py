# -*- coding: utf-8 -*-
import curses
import curses.ascii
import logging
from sys import version_info, platform

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
    _parent_win = None
    _caption_win = None     # contains box and caption
    _edit_win = None        # contains the "input box"

    """ Default value for string length """
    _max_chars_to_display = 0

    """ Cursor position within _max_chars_to_display """
    _curs_pos = 0
    """ First char of sting to display """
    _first = 0

    """ init values """
    y = x = 0
    _caption = 'Insert string'
    _disp_caption =  ' Insert string: '
    title = ''
    _disp_title = ''
    _boxed = False
    bracket = False
    box_color = 0
    caption_color = 0
    title_color = 0
    edit_color = 0
    unfocused_color = -1
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

    _focused = True

    """ if width < 1, auto_width gets this value,
        so that width gets parent.width - auto_width """
    _auto_width = 1

    """ string to redisplay after exiting help """
    _restore_data = []

    log = None
    _log_file = ''

    def __init__(self, parent, width, begin_y, begin_x, **kwargs):

        self._parent_win = parent
        self.width = width
        self._height = 3
        self.y = begin_y
        self.x = begin_x

        if kwargs:
            for key, value in kwargs.items():
                if key == 'boxed':
                    self._boxed = value
                    if not self._boxed:
                        self.height = 1
                elif key == 'bracket':
                    self.bracket = True
                elif key == 'string':
                    self._string = value
                elif key == 'caption':
                    """ string on editing line """
                    self._caption = value
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
                elif key == 'unfocused_color':
                    self.unfocused_color = value
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
        self._calculate_window_metrics()

    @property
    def width(self):
        if self._auto_width < 1:
            h , self._width = self._parent_win.getmaxyx()
            self._width += self._auto_width
            self._width -= self.x
        return self._width

    @width.setter
    def width(self, val):
        if val < 1:
            h , self._width = self._parent_win.getmaxyx()
            self._width -= val
            self._auto_width = val
        else:
            self._width = val
            self._auto_width = val

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
        if self._caption:
            if self._boxed:
                self.bracket = False
                self._disp_caption = ' ' + self._caption + ': '
                if self.title:
                    self._disp_title = ' ' + self._disp_title + ' '
                else:
                    self._disp_title = ''
            else:
                if self.bracket:
                    self._disp_caption = self._caption + ': ['
                else:
                    self._disp_caption = self._caption + ': '
                if self.title:
                    self._disp_title = self._disp_title
                else:
                    self._disp_title = ''
        else:
            if self.bracket:
                self._disp_caption = '['
            else:
                self._disp_caption = ''
        width = len(self._disp_caption) + self._max_chars_to_display + 4
        logger.error('DE 0 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        self._max_chars_to_display = self.width - len(self._disp_caption) - 4
        logger.error('DE 1 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        if self._boxed:
            self._height = 3
        else:
            self._height = 1
            self._max_chars_to_display += 2
            if not self.bracket:
                self._max_chars_to_display += 1
        if self.log is not None:
            self.log('string_len = {}'.format(self._max_chars_to_display))
        logger.error('DE 2 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        return

    def _prepare_to_show(self):
        caption_col = self.caption_color
        self._calculate_window_metrics()
        self._caption_win = curses.newwin(self._height, self.width, self.y, self.x)
        maxY, maxX = self._caption_win.getmaxyx()
        if self._boxed:
            self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 2, self.y + 1, self.x + len(self._disp_caption) + 1)
            self._caption_win.addstr(1, 1, self._disp_caption, self.caption_color)
        else:
            self._caption_win.addstr(0, 0, self._disp_caption, self.caption_color)
            if self.bracket:
                self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 1, self.y, self.x + len(self._disp_caption))
                try:
                    # printing at the end of the window, do not break...
                    self._caption_win.addstr(0, maxX - 1, ']', self.caption_color)
                except:
                    pass
            else:
                self._edit_win = curses.newwin(1, maxX - len(self._disp_caption), self.y, self.x + len(self._disp_caption))

        maxY, maxX = self._edit_win.getmaxyx()

    def refreshEditWindow(self, opening=False):
        if self._focused:
            active_edit_color = self.edit_color
        else:
            if self.unfocused_color >= 0:
                active_edit_color = self.unfocused_color
            else:
                active_edit_color = self.caption_color
        self._edit_win.erase()
        if opening:
            if self._restore_data:
                self._string = self._restore_data[0]
                self._curs_pos = self._restore_data[1]
                self._first = self._restore_data[2]
                self._edit_win.addstr(0, 0, self._string[self._first:self._first+self._max_chars_to_display], active_edit_color)
                self._restore_data = []
            else:
                self._curs_pos = 0
        else:
            if self._string:
                self._edit_win.addstr(0, 0, self._string[self._first:self._first+self._max_chars_to_display], active_edit_color)
            else:
                self._curs_pos = 0
        if self.log is not None:
            self.log(' - curs_pos = {}\n'.format(self._curs_pos))
        if self.focused:
            self._edit_win.chgat(0, self._curs_pos, 1, self.cursor_color)
            logger.error('curs = {}'.format(self._curs_pos))
        logger.error('DE string length = {}'.format(len(self.string)))

        self._edit_win.refresh()

    #def show(self, parent_win, new_y=-1, new_x=-1):
    def show(self, parent_win, **kwargs):
        opening = True
        self._caption_win = None
        self._edit_win = None
        if parent_win is not None:
            self._parent_win = parent_win
        if kwargs:
            for key, value in kwargs.items():
                if key == 'new_y':
                    self.y = value
                    if self.log is not None:
                        self.log('self.y = {}\n'.format(self.y))
                elif key == 'new_x':
                    self.x = value
                    if self.log is not None:
                        self.log('self.x = {}\n'.format(self.x))
                elif key == 'opening':
                    opening = value
        self._prepare_to_show()
        if self._focused:
            self._caption_win.bkgdset(' ', self.box_color)
            self._edit_win.bkgdset(' ', self.box_color)
        else:
            if self.unfocused_color >= 0:
                self._caption_win.bkgdset(' ', self.unfocused_color)
                self._edit_win.bkgdset(' ', self.unfocused_color)
            else:
                self._caption_win.bkgdset(' ', self.box_color)
                self._edit_win.bkgdset(' ', self.box_color)
        if self._boxed:
            self._caption_win.box()
            if self._disp_title:
                self._title_win.addstr(0, 1, self._disp_title, self.title_color)
        self._caption_win.refresh()
        self.refreshEditWindow(opening)

    def _delete_char(self):
            if self._first + self._curs_pos < len(self._string):
                self._string = self._string[:self._first + self._curs_pos] + self._string[self._first + self._curs_pos+1:]
                if self._first + self._max_chars_to_display > len(self.string):
                    if self._first > 0:
                        self._first -= 1

    def _backspace_char(self):
        if self._first + self._curs_pos > 0:
            self._string = self._string[:self._first + self._curs_pos-1] + self._string[self._first + self._curs_pos:]
            if len(self.string) < self._max_chars_to_display:
                self._first = 0
                if self._curs_pos > 0:
                    self._curs_pos -= 1
            elif self._first + self._max_chars_to_display >= len(self.string):
                self._first -= 1
            else:
                if self._curs_pos > 0:
                    self._curs_pos -= 1

    def keypress(self, win, char):
        """
         returns:
            2: display help
            1: get next char
            0: exit edit mode, string is valid
           -1: cancel
        """
        word_delim = (' ', '-', '_', '+', '=',
                    '~', '~', '!', '@', '#',
                    '$', '%', '^', '&', '*', '(', ')',
                    '[', ']', '{', '}', '|', '\\', '/',
                    )
        #self._log_file='/home/spiros/edit.log'
        #self._log_file='C:\\Users\\spiros\\edit.log'
        #self.log = self._log
        if not self._focused:
            return 1
        if self.log is not None:
            self.log('char = {}\n'.format(char))

        if platform.startswith('win'):
            if char == 420:
                """ A-D, clear to end of line """
                self.string = self._string[:self._first + self._curs_pos]
                self.refreshEditWindow()
                return 1
            elif char == 422:
                """ A-F, move to next word """
                pos = len(self._string)
                for n in range(self._curs_pos + 1, len(self._string)):
                    if self._string[n] in word_delim:
                        pos = n
                        break
                self._curs_pos = pos
                self.refreshEditWindow()
                return 1
            elif char == 418:
                """ A-B, move to previous word """
                pos = 0
                for n in range(self._curs_pos - 1, 0, -1):
                    if self._string[n] in word_delim:
                        pos = n
                        break
                self._curs_pos = pos
                self.refreshEditWindow()
                return 1

        if char in (ord('?'), ):
            # display help
            self._restore_data = [ self.string, self._curs_pos, self._first ]
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
                    if self.string:
                        self.string = self._string[:self._first + self._curs_pos]
                elif char in (ord('f'), ):
                    """ A-F, move to next word """
                    pos = len(self._string)
                    for n in range(self._first + self._curs_pos + 1, len(self._string)):
                        if self._string[n] in word_delim:
                            pos = n
                            break
                    if pos == len(self._string):
                        # word delimiter not found
                        self._curs_pos = pos - self._first
                        self._first = len(self.string) - self._max_chars_to_display
                        if self._first < 0:
                            self._first = 0
                    else:
                        # word delimiter found
                        if len(self.string) < self._max_chars_to_display or \
                                pos < self._first + self._max_chars_to_display:
                            # pos is on screen
                            self._curs_pos = pos - self._first + 1
                        else:
                            # pos is not on screen
                            logger.error('DE 1 pos = {0}, len = {1}, max = {2}'.format(pos, len(self.string), self._max_chars_to_display))
                            self._first = pos
                            self._curs_pos = 1
                            pos = 0
                            while len(self.string) - (self._first + pos + 1) < self._max_chars_to_display:
                                pos -= 1
                            self._first = self._first + pos + 1
                            self._curs_pos = self._curs_pos + abs(pos) - 1
                            logger.error('DE 2 pos = {0}, len = {1}, max = {2}'.format(pos, len(self.string), self._max_chars_to_display))

                elif char in (ord('b'), ):
                    """ A-B, move to previous word """
                    pos = 0
                    for n in range(self._first + self._curs_pos - 1, 0, -1):
                        if self._string[n] in word_delim:
                            pos = n
                            break
                    if pos == 0:
                        self._curs_pos = pos
                        self._first = 0
                    else:
                        pass
                else:
                    return 1
        elif char in (curses.KEY_RIGHT, ):
            """ KEY_RIGHT """
            if self.string:
                logger.error('DE max = {0}, curs = {1}, first = {2}'.format(self._max_chars_to_display, self._curs_pos, self._first))
                if len(self.string) < self._max_chars_to_display:
                    self._curs_pos += 1
                    logger.error('DE 1 curs increased = {}'.format(self._curs_pos))
                    if self._curs_pos > len(self.string):
                            self._curs_pos = len(self.string)
                    else:
                        if len(self._string) < self._first + self._curs_pos:
                            self._curs_pos = len(self._string) - self._max_chars_to_display
                            logger.error('DE 2 curs modified = {}'.format(self._curs_pos))
                else:
                    if self._curs_pos == self._max_chars_to_display:
                        if len(self._string) > self._first + self._curs_pos:
                            self._first += 1
                            logger.error('DE 3 first increased = {}'.format(self._first))
                    else:
                        self._curs_pos += 1
                        logger.error('DE 4 curs increased = {}'.format(self._curs_pos))
        elif char in (curses.KEY_LEFT, ):
            """ KEY_LEFT """
            if self.string:
                if len(self.string) < self._max_chars_to_display:
                    self._curs_pos -= 1
                    if self._curs_pos < 0:
                        self._curs_pos = 0
                else:
                    if self._curs_pos == 0:
                        self._first -= 1
                        if self._first < 0:
                            self._first = 0
                    else:
                        self._curs_pos -= 1
        elif char in (curses.KEY_HOME, curses.ascii.SOH):
            """ KEY_HOME, ^A """
            self._curs_pos = 0
            self._first = 0
        elif char in (curses.KEY_END, curses.ascii.ENQ):
            """ KEY_END, ^E """
            if self.string:
                self._curs_pos = len(self._string)
                if self._curs_pos > self._max_chars_to_display:
                    self._curs_pos = self._max_chars_to_display
                self._first = len(self.string) - self._max_chars_to_display
                if self._first < 0:
                    self._first = 0
        elif char in (curses.ascii.ETB, ):
            """ ^W, clear to start of line """
            if self.string:
                self.string = self._string[self._first + self._curs_pos:]
                self._curs_pos = 0
                self._first = 0
        elif char in (curses.ascii.NAK, ):
            """ ^U, clear line """
            self.string = ''
            self._curs_pos = self._first = 0
        elif char in (curses.KEY_DC, curses.ascii.EOT):
            """ DEL key, ^D """
            if self.string:
                self._delete_char()
        elif char in (curses.KEY_BACKSPACE, curses.ascii.BS,127):
            """ KEY_BACKSPACE """
            if self.string:
                self._backspace_char()
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
            if self.string:
                self._string = self._string[:self._first + self._curs_pos]
        elif 0<= char <=31:
            pass
        else:
            if self.log is not None:
                self.log('====================\n')
            #if len(self._string) + 1 == self._max_width:
            if len(self._string) == self._max_chars_to_display:
                logger.error('DE max width reached {0} - {1}'.format(len(self._string), self._max_chars_to_display))
                #self._first += 1
                # return 1
            if version_info < (3, 0):
                if 32 <= char < 127:
                    # accept only ascii characters
                    if len(self._string) == self._first + self._curs_pos:
                        self._string += chr(char)
                    else:
                        self._string = self._string[:self._first + self._curs_pos] + chr(char) + self._string[self._first + self._curs_pos:]
            else:
                if platform.startswith('win'):
                    char = chr(char)
                else:
                    char = self._get_char(win, char)
                if len(self._string) == self._first + self._curs_pos:
                    self._string += char
                else:
                    self._string = self._string[:self._first + self._curs_pos] + char + self._string[self._first + self._curs_pos:]
            if self._curs_pos == self._max_chars_to_display:
                self._first += 1
            else:
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
            logger.error('de out = "{0}", len = {1}'.format(out, len(out)))
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
        if a_string:
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

