#!/bin/python
import curses
import curses.ascii

def log(msg):
    with open('test.log', 'a') as log_file:
        log_file.write(msg)

class SimpleCursesLineEdit(object):
    """ Class to insert one line of text """
    string = ''

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
    _boxed = False
    box_color = 0
    caption_color = 0
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

    log = None
    # uncomment this to have logging
    #log = _log

    def __init__(self, parent, begin_y, begin_x, **kwargs):
        self.parent_win = parent
        self.y = begin_y
        self.x = begin_x

        for key, value in kwargs.items():
            if key == 'boxed':
                self._boxed = value
            elif key == 'string_len':
                self._string_len = value
            elif key == 'caption':
                self.caption = value
            elif key == 'box_color':
                self.box_color = value
            elif key == 'caption_color':
                self.caption_color = value
            elif key == 'edit_color':
                self.edit_color = value
            elif key == 'cursor_color':
                self.cursor_color = value
            elif key == 'has_history':
                self._has_history = value
            elif key == 'ungetch_unbound_keys':
                self._ungetch_unbound_keys =  value
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
            self.refreshEditWindow()

    def getmaxyx(self):
        return self._caption_win.getmaxyx()

    def _calculate_window_metrics(self):
        if self._boxed:
            self._disp_caption = ' ' + self.caption + ': '
        else:
            self._disp_caption = self.caption + ': ['
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

    def refreshEditWindow(self):
        if self.focused:
            active_edit_color = self.edit_color
            active_cursor_color = self.cursor_color
        else:
            active_edit_color = self.caption_color
            active_cursor_color = self.caption_color
        self._edit_win.erase()
        #self._edit_win.bkgd('-', curses.A_REVERSE)
        if self.string:
            self._edit_win.addstr(0, 0, self.string, active_edit_color)
        else:
            self._curs_pos = 0
        if self.log is not None:
            self.log(' - curs_pos = {}\n'.format(self._curs_pos))
        self._edit_win.chgat(0, self._curs_pos, 1, active_cursor_color)

        self._edit_win.refresh()

    def show(self, parent_win, new_y=-1, new_x=-1):
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
        if self._boxed:
            self._caption_win.box()
        self._caption_win.refresh()
        self.refreshEditWindow()

    def keypress(self, char):
        """
         returns:
            1: get next char
            0: exit edit mode, string isvalid
           -1: cancel
        """
        if self._focused is False:
            return 1
        if self.log is not None:
            self.log('char = {}\n'.format(char))
        if char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            """ ENTER """
            if self._has_history:
                self._input_history.add_to_history(self.string)
            return 0
        elif char in (curses.KEY_EXIT, 27):
            """ ESCAPE """
            self.string = ''
            self._curs_pos = 0
            return -1
        elif char in (curses.KEY_RIGHT, curses.ascii.ACK):
            """ KEY_RIGHT, Alt-F """
            self._curs_pos += 1
            if len(self.string) < self._curs_pos:
                self._curs_pos = len(self.string)
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
            self._curs_pos = len(self.string)
        elif char in (curses.KEY_DC, curses.ascii.EOT):
            """ DEL key, ^D """
            if self._curs_pos < len(self.string):
                self.string = self.string[:self._curs_pos] + self.string[self._curs_pos+1:]
        elif char in (curses.KEY_BACKSPACE, curses.ascii.BS,127):
            """ KEY_BACKSPACE """
            if self._curs_pos > 0:
                self.string = self.string[:self._curs_pos-1] + self.string[self._curs_pos:]
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
            self.string = self.string[:self._curs_pos]
        elif 0<= char <=31:
            pass
        else:
            if len(self.string) + 1 == self._max_width:
                return 1
            if 32 <= char < 127:
                # accept only ascii characters
                if len(self.string) == self._curs_pos:
                    self.string += chr(char)
                    self._curs_pos += 1
                else:
                    self.string = self.string[:self._curs_pos] + chr(char) + self.string[self._curs_pos:]

        self.refreshEditWindow()
        return 1

    def _log(self, msg):
        with open('test.log', 'a') as log_file:
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
                self._active_history_index = -1
                return ''
            elif self._active_history_index >= len(self._history):
                self._active_history_index = len(self._history)
                return ''
            ret =  self._history[self._active_history_index]
            return ret
        return ''




def test(win):
    curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
    curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
    curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
    curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
    curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)
    curses.init_pair(8, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
    curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)

    xx = SimpleCursesLineEdit(win, 10, 10, boxed=True, string_len=25,
                box_color = curses.color_pair(5),
                caption_color = curses.color_pair(5),
                edit_color = curses.color_pair(8),
                cursor_color = curses.color_pair(6))
    xx.log = xx._log
    #x = SimpleCursesLineEdit(win, 5, 5)
    #x.string = '12345678901234567890'
    y, x = win.getmaxyx()
    #log('== w_y = {0}, w_x = {1}\n'.format(y, x))
    new_y = y - xx.height
    new_x = x - xx.width
    #log('== new_y = {0}, new_x = {1}\n'.format(new_y, new_x))
    xx.show(win, new_y, new_x)
    ret = xx.run()
    if ret != 1:
        return ret, xx.string

ret, rets = curses.wrapper(test)
print('ret = {0}, string = "{1}"'.format(ret, rets))


