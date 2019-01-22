#!/bin/python
import curses
import curses.ascii

class CursesLineEdit(object):
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
    cursor_color =  curses.A_REVERSE
    _has_history = False
    _input_history = None
    _key_up_function_handler = None
    _key_down_function_handler = None
    _key_pgup_function_handler = None
    _key_pgdown_function_handler = None
    _key_tab_function_handler = None
    _key_stab_function_handler = None

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
            self._input_history = CursesLineEditHistory()

    def getmaxyx(self):
        return self._caption_win.getmaxyx()

    def _prepare_to_show(self):
        caption_col = self.caption_color
        if self._boxed:
            self._disp_caption = ' ' + self.caption + ': '
        else:
            self._disp_caption = self.caption + ': ['
        width = len(self._disp_caption) + self._string_len + 4
        begin_y = self.y
        begin_x = self.x
        if self._boxed:
            height = 3
        else:
            height = 1
            width -= 2
        self._caption_win = curses.newwin(height, width, begin_y, begin_x)
        maxY, maxX = self._caption_win.getmaxyx()
        if self._boxed:
            self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 2, begin_y + 1, begin_x + len(self._disp_caption) + 1)
            self._caption_win.addstr(1, 1, self._disp_caption, self.caption_color)
        else:
            self._edit_win = curses.newwin(1, maxX - len(self._disp_caption) - 1, begin_y, begin_x + len(self._disp_caption))
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
        self._edit_win.erase()
        #self._edit_win.bkgd('-', curses.A_REVERSE)
        if self.string:
            self._edit_win.addstr(0, 0, self.string, self.edit_color)
        else:
            self._curs_pos = 0
        self.log(' - curs_pos = {}\n'.format(self._curs_pos))
        self._edit_win.chgat(0, self._curs_pos, 1, self.cursor_color)
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('string = "{}"'.format(self.string))

        self._edit_win.refresh()

    def show(self, parent_win):
        if parent_win is not None:
            self.parent_win = parent_win
        self._prepare_to_show()
        if self._boxed:
            self._caption_win.box()
        self._caption_win.refresh()
        self.refreshEditWindow()

    def keypress(self, char):
        """
        if using history:
            returns char, status
              status is:
                  True   - the caller has to act on char
                           char is KEY_UP or KEY_DOWN
                  False  - no further action required by the caller
        if no history:
           return status
             status is:
                1: remain in search mode
                0: preform search, return to normal mode
               -1: cancel search, return to normal mode
        """
        self.log('char = {}\n'.format(char))
        if char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            """ ENTER """
            if self._has_history:
                self._input_history.add_to_history(self.string)
                #if logger.isEnabledFor(logging.DEBUG):
                #    logger.debug('*** string = {}'.format(self.string))
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
            self.log('char = KEY_LEFT\n')
            self._curs_pos -= 1
            if self._curs_pos < 0:
                self._curs_pos = 0
            self.log('KEY_LEFT: curs_pos = {}\n'.format(self._curs_pos))
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
        elif char in (curses.KEY_DOWN, curses.ascii.SO):
            """ KEY_DOWN, ^P """
            if self._key_down_function_handler is not None:
                try:
                    self._key_down_function_handler()
                except:
                    pass
        elif char in (curses.KEY_NPAGE, ):
            """ PgDn """
            if self._key_pgdown_function_handler is not None:
                try:
                    self._key_pgdown_function_handler()
                except:
                    pass
        elif char in (curses.KEY_PPAGE, ):
            """ PgUp """
            if self._key_pgup_function_handler is not None:
                try:
                    self._key_pgup_function_handler()
                except:
                    pass
        elif char in (curses.KEY_BTAB, ):
            """ Shift-TAB """
            if self._key_stab_function_handler is not None:
                try:
                    self._key_stab_function_handler()
                except:
                    pass
        elif char in (9, ):
            """ TAB """
            if self._key_tab_function_handler is not None:
                try:
                    self._key_tab_function_handler()
                except:
                    pass
        elif char in (curses.ascii.VT, ):
            """ Ctrl-K - delete to end of line """
            self.string = self.string[:self._curs_pos]
        elif 0<= char <=31:
            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('*** Control char detected ***')
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

        self.log('Before refresh: curs_pos = {}\n'.format(self._curs_pos))
        self.refreshEditWindow()
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('------------')
        #    logger.debug('char = {}'.format(char))
        #    logger.debug('len(string) = {}'.format(len(self.string)))
        #    logger.debug('_curs_pos = {}'.format(self._curs_pos))
        #    logger.debug('_max_width = {}'.format(self._max_width))
        #    logger.debug('min_edit_width = {}'.format(self._string_len))
        return 1

    def run(self):
        self._edit_win.nodelay(False)
        self._edit_win.keypad(True)
        while True:
            char = self._edit_win.getch()
            ret = self.keypress(char)
            if ret != 1:
                return ret

    def log(self, msg):
        with open('test.log', 'a') as log_file:
            log_file.write(msg)

class CursesLineEditHistory(object):

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
    x = CursesLineEdit(win, 10, 10, boxed=False, string_len=35)
    #x = CursesLineEdit(win, 5, 5)
    #x.string = '12345678901234567890'
    x.show(win)
    ret = x.run()
    if ret != 1:
        return ret, x.string

ret, rets = curses.wrapper(test)
print('ret = {0}, string = "{1}"'.format(ret, rets))


