# -*- coding: utf-8 -*-
import curses
import curses.ascii
from os.path import basename
from sys import exit
from datetime import date, time, datetime, timedelta
try:
    from dateutil.relativedelta import relativedelta
except:
    print('''Error: Module "dateutil" not found!

Please install the above module and try again.

Debian based distros:
sudo apt install python3-dateutil

Arch based distros:
sudo pacman install python-dateutil

Fedora based distros:
sudo dnf install python-dateutil

openSUSE based distros:
sudo zypper install python3-dateutil

If everything else fails, try:
python -m pip install dateutil
or
python3 -m pip install dateutil
or even
python -m pip install --user dateutil

''')
    exit(1)
import logging
from sys import version_info, platform, version
# try:
#     from .cjkwrap import PY3, is_wide, cjklen
#     from .schedule import PyRadioTime
# except:
#     from cjkwrap import PY3, is_wide, cjklen
#     from schedule import PyRadioTime
from .cjkwrap import PY3, is_wide, cjklen, cjkljust
from .schedule import PyRadioTime
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)


class DisabledWidget(object):
    '''A dummy class that only returns enabled = False

    To be used in complex dialogs
    '''
    Y = X = width = height = 0
    _enabled = False
    focus = focused = False
    checked = False

    def __init__(self):
        pass

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        pass

    def show(self, parent=None):
        pass

class SimpleCursesWidget(object):
    '''An abstract widget class '''
    _win = _parent = _callback_function = None
    _focused = _showed = False
    _enabled = True
    _Y = _X = _width = _color_focused = _color = 0
    _height = 1
    _caption = _display_caption = ''

    @property
    def window(self):
        return self._win

    @window.setter
    def window(self, value):
        raise ValueError('parameter is read only')

    @property
    def Y(self):
        return self._Y

    @Y.setter
    def Y(self, value):
        self._Y = value

    @property
    def X(self):
        return self._X

    @X.setter
    def X(self, value):
        self._X = value

    @property
    def height(self):
        return self._height

    @height.setter
    def height(self, value):
        raise ValueError('parameter is read only')

    @property
    def width(self):
        return self._width

    @width.setter
    def width(self, value):
        raise ValueError('parameter is read only')

    @property
    def caption(self):
        '''The text of the widget'''
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value
        if self._showed:
            self.resize_and_show()

    @property
    def enabled(self):
        '''Returns if the widget is enabled'''
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if self._showed:
            self.refresh()

    @property
    def focused(self):
        '''Returns if the widget has focus'''
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value
        if self._showed:
            self.refresh()

    @property
    def color_focused(self):
        '''The color to use when the widget has the focus'''
        return self._color_focused

    @color_focused.setter
    def color_focused(self, value):
        self._color = value
        if self._showed:
            self.refresh()

    @property
    def color(self):
        '''The normal color of the widget (no focus)'''
        return self._color

    @color.setter
    def color(self, value):
        self._color = value
        if self._showed:
            self.refresh()

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value

    @property
    def callback_function(self):
        '''The function to call when the widget is "clicked"'''
        return self._callback_function

    @callback_function.setter
    def callback_function(self, value):
        self._callback_function = value

    def getmaxyx(self):
        return self._win.getmaxyx() if self._win else (0, 0)

    def mvwin(self, Y, X, show=True, erase=False):
        '''Move the widget

            Parameters
            ==========
            Y, X
                New T and X coodrinates
            show
                If True, display the widget at its new location.
                Otherwise, just calculate the new location.
            erase
                If True, erase the window before moving it
                if False (the default), do not erase the
                  window; the parent will erase itself
        '''

        if self._win:
            if erase:
                self._win.erase()
                self._win.touchwin()
                self._win.refresh()
            try:
                self._win.mvwin(Y, X)
            except:
                pass
            self._Y = Y
            self._X = X
            if show:
                self._win.touchwin()
                self.refresh()

    def set_focus(self, focus):
        if focus:
            self._focused = True
        else:
            self._focused = False
        if self._showed:
            self.refresh()

    def toggle_focus(self):
        self._focused = not self._focused
        if self._showed:
            self.refresh()

    def resize(self):
        '''Resize the widget.
        The window (_win) gets created here'''

        pass

    def resize_and_show(self):
        '''Resize and show the widget'''
        self.resize()
        self.show()

    def show(self):
        '''Display the widget'''
        self._showed = True

    def refresh(self):
        '''Refresh the widget'''
        pass

    def keypress(self, char):
        '''Handle keyboard input

            Returns
            =======
                True
                    The character was not handled by the widget.
                    The calling function can go on and handle it.
                False
                    The character was handled by the widget.
                    The calling function does not need to handle it.
        '''
        return False


class SimpleCursesString(SimpleCursesWidget):
    ''' A class to provide a String value

        Parameters
        ==========
        Y, X, window
            Coordinates and parent window
        caption
            preffix string
        string
            the string to display (variable)
        color
            text color
        color_focused
            counter color when enabled and focused
        color_not_focused
            counter color when enabled but not focused
        color_disabled
            counter color when disabled
        full_slection
            if not None, it should be a tuple:
                (go left from self._X, numbder of chars to print)
            draw selection cursor as a full line
    '''


    _max_string = 0

    def __init__(
        self,
        Y, X, parent,
        caption,
        string,
        color, color_focused,
        color_not_focused,
        color_disabled,
        right_arrow_selects=True,
        callback_function_on_activation=None,
        full_selection=None
    ):
        self._Y = Y
        self._X = X
        self._win = self._parent = parent
        self._string = string
        if cjklen(self._string) > self._max_string:
            self._max_string = cjklen(self._string)
        self._caption = caption
        self._color = color
        self._color_focused = color_focused
        self._color_not_focused = color_not_focused
        self._color_disabled = color_disabled
        self._right_arrow_selects = right_arrow_selects
        self._callback_function_on_activation = callback_function_on_activation
        self._full_selection = full_selection

    @property
    def caption(self):
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value

    @property
    def string(self):
        return self._string

    @string.setter
    def string(self, value):
        self._string = value
        if cjklen(self._string) > self._max_string:
            self._max_string = cjklen(self._string)

    @property
    def string_len(self):
        return len(self._string)

    @property
    def caption_len(self):
        return len(self._caption)

    @property
    def string_Y(self):
        return self._Y

    @property
    def string_X(self):
        return self._X + len(self._string)

    def move(self, newY=-1, newX=-1, parent=None):
        if newY > 0:
            self._Y = newY
        if newX > 0:
            self._X = newX
        if parent:
            self._win = self._parent = parent

    def keypress(self, char):
        ''' SimpleCursesString key press
            Returns:
                -1 continue
                 0 action (select)
        '''
        ret = -1
        if self._right_arrow_selects and char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            ret = 0
        elif not self._right_arrow_selects and char in (
            ord(' '), ord('\n'), ord('\r'),
            curses.KEY_ENTER
        ):
            ret = 0
        if ret == 0 and self._callback_function_on_activation:
            self._callback_function_on_activation()
        return ret

    def _print_full_line(self, col):
        tmp = self._full_selection[0] * ' ' + self.caption + self._string
        self._win.addstr(
            self._Y,
            self._X - self._full_selection[0],
            tmp.ljust(self._full_selection[1]),
            col
        )

    def show(self, parent=None):
        if parent:
            self._win = self._parent = parent
        if self._full_selection and self._enabled and self._focused:
            self._print_full_line(self._color_focused)
        else:
            if self._full_selection:
                self._win.addstr(
                    self._Y,
                    self._X - self._full_selection[0],
                    (self._full_selection[1] ) * ' ',
                    self._color
                )
            if self._enabled:
                self._win.addstr(self._Y, self._X, self._caption, self._color)
                if self._focused:
                    self._win.addstr(self._string.ljust(self._max_string), self._color_focused)
                else:
                    self._win.addstr(self._string.ljust(self._max_string), self._color_not_focused)
            else:
                self._win.addstr(self._Y, self._X, self._caption, self._color_disabled)
                self._win.addstr(self._string.ljust(self._max_string), self._color_disabled)


class SimpleCursesDate(SimpleCursesWidget):
    ''' A class to provide a time insertion widget

        Parameters
        ==========
        Y, X, window
            Coordinates and parent window
        string
            Date string
                format is YYYY-MM-DD
        date_tuple
            Date as a tuple
                Format (YYYY, M, D) od int
        color
            text color
        color_focused
            counter color when enabled and focused
        next_widget_func
            Function to call when going from days
            field to next widget. If set to None, go
            to hours fields
        previous_widget_func
            Function to call when going from years field
            to previous widget. If set to None, go to
            seconds field
    '''
    def __init__(
        self, Y, X, window,
        color, color_focused,
        string=None,
        date_tuple=None,
        next_widget_func=None,
        previous_widget_func=None,
        global_functions=None
    ):
        # logger.error('   ---===***===---   ')
        self._Y = Y
        self._X = X
        self._win = self._parent = window
        self._color = color
        self._color_focused = color_focused
        self._date = None
        self.datetime = None
        self._next_func = next_widget_func
        self._previous_func = previous_widget_func
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}

        self._set_date()

        # logger.error('DE num = {}'.format(self._num))

        self.selected = 0
        self._showed = False

    def __str__(self):
        return self._date.strftime('%Y-%m-%d')

    @property
    def date(self):
        return self._date

    @date.setter
    def date(self, val):
        if isinstance(val, str):
            self._set_date(date_string=val)
        else:
            self._set_date(date_tuple=val)

    def increase(self, delta=1):
        if self.selected == 0:
            self._date = self._date + relativedelta(years=+delta)
        elif self.selected == 1:
            self._date = self._date + relativedelta(months=+delta)
        elif self.selected == 2:
            self._date = self._date + relativedelta(days=+delta)
        self.show()

    def decrease(self, delta=1):
        if self.selected == 0:
            self._date = self._date + relativedelta(years=-delta)
        elif self.selected == 1:
            self._date = self._date + relativedelta(months=-delta)
        elif self.selected == 2:
            self._date = self._date + relativedelta(days=-delta)
        self.show()

    def set_date_string(self, a_string=None):
        self._set_date(date_string=a_string)

    def set_date_tupple(self, a_tuple=None):
        self._set_date(date_tuple=a_tuple)

    def _set_date(self, date_string=None, date_tuple=None):
        ''' set date
            Either specify:
                sting: format "YYYY-MM-YY"
            or
                date_tuple = (YYYY, M, D) of int

            On error, get today
        '''
        a_date = []
        if date_string is None and date_tuple is None:
            self._date = datetime.now()
            return True
        elif date_string is not None:
            sp = date_string.split('-')
            try:
                for i in range(0, 3):
                    a_date.append(int(sp[i]))
            except ValueError:
                self._date = datetime.now()
                return True
        elif date_tuple is not None:
            a_date = list(date_tuple)
        try:
            self._date = datetime(
                year=a_date[0],
                month=a_date[1],
                day=a_date[2]
            )
            return True
        except:
            self._date = datetime.now()
            return False

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X

    def show(self, parent=None):
        sel = (
            (self._X, 4),
            (self._X + 5, 2),
            (self._X + 8, 2),
        )
        if parent is not None:
            self._win = self._parent = parent
        if self._win is None:
            return
        if self._enabled:
            if self._focused:
                self._win.addstr(
                    self._Y, self._X,
                    str(self._date.year),
                    self.color_focused if self.selected == 0 else self._color
                )
                self._win.addstr('-', self._color)
                self._win.addstr(
                    str(self._date.month).zfill(2),
                    self.color_focused if self.selected == 1 else self._color
                )
                self._win.addstr('-', self._color)
                self._win.addstr(
                    str(self._date.day).zfill(2),
                    self.color_focused if self.selected == 2 else self._color
                )
            else:
                self._win.addstr(self._Y, self._X, self.__str__(), self._color)
        else:
            self._win.addstr(self._Y, self._X, '====-==-==', self._color)
        self._win.refresh()
        self._showed = True

    def keypress(self, char):
        '''
        SimpleCursesDate keypress
        Returns:
            -1: Cancel
             0: Continue
             1: Show help
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 0

        if char == ord('t'):
            self._enabled = not self._enabled
            self.show()
            return 0

        if char in (curses.KEY_EXIT, ord('q'), 27):
            return -1

        elif char == ord('?'):
            return 1

        elif char in (curses.KEY_HOME, ):
            self._date = datetime.today()
            self.show()

        elif char in (curses.KEY_NPAGE, ):
            delta = 5
            if self.selected == 1:
                delta = 3
            self.decrease(delta=delta)

        elif char in (curses.KEY_PPAGE, ):
            delta = 5
            if self.selected == 1:
                delta = 3
            self.increase(delta=delta)

        elif char in (ord('h'), curses.KEY_LEFT):
            self.decrease()

        elif char in (ord('l'), curses.KEY_RIGHT):
                self.increase()

        elif char in (9, ord('L')):
            ''' TAB '''
            if self._next_func and self.selected == 2:
                self._next_func()
                self._focused = False
            else:
                self.selected += 1
                if self.selected > 2:
                    self.selected = 0
            self.show()

        elif char in (curses.KEY_BTAB, ord('H')):
            ''' Shift-TAB '''
            if self._previous_func and self.selected == 0:
                self._previous_func()
                self._focused = False
            else:
                self.selected -= 1
                if self.selected < 0:
                    self.selected = 2
            self.show()

        return 0
    pass

class SimpleCursesTime(SimpleCursesWidget):
    ''' A class to provide a time insertion widget

        Parameters
        ==========
        Y, X, window
            Coordinates and parent window
        string
            Time string
                format is XX:XX [AM/PM]
                          XX:XX:XX [AM/PM]
        time_format
            The format to use to display the time
            It is PyRadioTime.NO_AM_PM_FORMAT, or
                  PyRadioTime.AM_FORMAT, or
                  PyRadioTime.PM_FORMAT
        show_am_pm
            True or false to show or hide AM/PM check boxes
        color
            text color
        color_focused
            counter color when enabled and focused
        time_format_changed_func
            Function to call whenever we go from
            AM to PM (or vice-versa)
        next_widget_func
            Function to call when going from seconds
            field to next widget. If set to None, go
            to hours fields
        previous_widget_func
            Function to call when going from hours field
            to previous widget. If set to None, go to
            seconds field
    '''
    def __init__(
        self, Y, X, window,
        color, color_focused,
        string=None,
        show_am_pm=False,
        check_box_char='✔',
        time_format=PyRadioTime.NO_AM_PM_FORMAT,
        time_format_changed_func=None,
        next_widget_func=None,
        previous_widget_func=None,
        global_functions=None
    ):
        # logger.error('   ---===***===---   ')
        self._Y = Y
        self._X = X
        self._win = self._parent = window
        self._color = color
        self._color_focused = color_focused
        self.time = PyRadioTime.string_to_pyradio_time(string)
        self.date = None
        self.datetime = None
        self.time_format = time_format
        self._time_format_changed_func = time_format_changed_func
        self._next_func = next_widget_func
        self._previous_func = previous_widget_func
        self._show_am_pm = show_am_pm
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}
        if self._show_am_pm:
            self._max_selection = 4
            self._width = 20
        else:
            self._max_selection = 2
            self._width = 8
        # logger.error('time = {}'.format(self.time))
        # logger.error('timeformat = {}'.format(self.time_format))

        self._char = check_box_char
        if platform.lower().startswith('win') and \
                self._char == '✔':
            self._char = 'X'
        '''
        Values for the hour part of self._num
        '''
        self._hour_formats = [
            [0, 0, 23, 1, 3],
            [0, 1, 12, 1, 3]
        ]
        '''
        Time contents
        Format is: value, min, max, step, big step
        '''
        self._num = [
            [0, 0, 23, 1, 3],
            [self.time[1], 0, 59, 1, 10],
            [self.time[2], 0, 59, 1, 10]
        ]

        self._apply_time_format()

        # logger.error('DE num = {}'.format(self._num))

        self.selected = 0
        self._showed = False

    @property
    def show_am_pm(self):
        return self._show_am_pm

    def set_time_string(self, time_string):
        self.time = PyRadioTime.string_to_pyradio_time(time_string)
        if self._showed:
            self.show()

    def set_time_pyradio_time(self, t_time):
        self.time = t_time
        if self._showed:
            self.show()

    def get_time(self):
        '''
        Return the time
        returns [pyradio time], [string time]
        '''
        t_time = (
            self._num[0][0],
            self._num[1][0],
            self._num[2][0],
            self.time_format
        )
        return t_time, PyRadioTime.pyradio_time_to_string(t_time)

    def toggle_time_format(self):
        # logger.info('1 num[0] = {}'.format(self._num[0]))
        old_time_format = self.time_format
        if self.time_format == PyRadioTime.NO_AM_PM_FORMAT:
            if self._num[0][0] > 12:
                self.time_format = PyRadioTime.PM_FORMAT
                # self._num[0][0] -= 12
            else:
                self.time_format = PyRadioTime.AM_FORMAT
            if self._num[0][0] == 0:
                self._num[0][0] = 12
        else:
            self.time_format = PyRadioTime.NO_AM_PM_FORMAT
        # logger.info('2 num[0] = {}'.format(self._num[0]))
        self._time_format_changed(old_time_format)
        # logger.info('3 num[0] = {}'.format(self._num[0]))
        if self._showed:
            self.show()
        # logger.info('4 num[0] = {0}\ntime format = {1}'.format(self._num[0], self.time_format))


    def set_time_format(self, t_time_format):
        old_time_format = self.time_format
        self.time_format = t_time_format
        self._time_format_changed(old_time_format)
        if self._showed:
            self.show()

    def _apply_time_format(self):
        if self.time_format == PyRadioTime.NO_AM_PM_FORMAT:
            self._num[0] = self._hour_formats[0][:]
            self._num[0][0] = self.time[0]
        else:
            self._num[0] = self._hour_formats[1][:]
            # logger.error('time = {}'.format(self.time))
            # logger.error('_num = {}'.format(self._num))
            if self.time[0] > 12:
                self.time_format = PyRadioTime.PM_FORMAT
                self._num[0][0] = self.time[0] - 12
                if self._time_format_changed_func:
                    self._time_format_changed_func()
            else:
                self._num[0][0] = self.time[0]
            if self._num[0][0] == 0:
                self._num[0][0] = 12
        # logger.error('_num = {}'.format(self._num))

    def _time_format_changed(self, old_time_format):
        if self.time_format == old_time_format:
            return
        if self.time_format == PyRadioTime.NO_AM_PM_FORMAT:
            if old_time_format == PyRadioTime.NO_AM_PM_FORMAT:
                return
            self._num[0][1:] = self._hour_formats[0][1:][:]
            if old_time_format == PyRadioTime.PM_FORMAT:
                self._num[0][0] += 12
            if self._num[0][0] == 24:
                self._num[0][0] = 0
        else:
            if old_time_format in (
                PyRadioTime.AM_FORMAT,
                PyRadioTime.PM_FORMAT
            ):
                return
            self._num[0][1:] = self._hour_formats[1][1:][:]
            if self._num[0][0] > 12:
                self._num[0][0] -= 12
            if self._num[0][0] == 0:
                self._num[0][0] = 12

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X

    def reset_selection(self, last=False):
        if last:
            self.selected = self._max_selection
        else:
            self.selected = 0

    def show(self, window=None):
        if window:
            self._win = self._parent = window
        if self._enabled:
            h = str(self._num[0][0]).zfill(2)
            m = str(self._num[1][0]).zfill(2)
            s = str(self._num[2][0]).zfill(2)
            if self._focused:
                col = self.color_focused if self.selected == 0 else self.color
                self._win.addstr(
                    self._Y, self._X, h,
                    col
                )
                self._win.addstr(':', self.color)
                col = self.color_focused if self.selected == 1 else self.color
                self._win.addstr(m, col)
                self._win.addstr(':', self.color)
                col = self.color_focused if self.selected == 2 else self.color
                self._win.addstr(s, col)
            else:
                self._win.addstr(
                    self._Y, self._X,
                    '{0}:{1}:{2}'.format(h, m ,s),
                    self.color
                )
        else:
            self._win.addstr(self._Y, self._X, '==:==:==', self.color)

        if self._show_am_pm:
            if self._enabled:
                self._win.addstr(' [', self.color)
                if self._focused:
                    col = self.color_focused if self.selected == 3 else self.color
                else:
                    col = self.color
                tok = self._calculate_token(3)
                self._win.addstr(tok, col)
                self._win.addstr(']AM [', self.color)
                if self._focused:
                    col = self.color_focused if self.selected == 4 else self.color
                else:
                    col = self.color
                tok = self._calculate_token(4)
                self._win.addstr(tok, col)
                self._win.addstr(']PM', self.color)
            else:
                self._win.addstr(' [ ]== [ ]==', self.color)
        self._win.refresh()
        self._showed = True

    def _check_time_format(self, old_hours):
        '''
        Adjust self.time_format when using the keyboard
        '''
        if self.selected == 0 and \
                self.time_format != PyRadioTime.NO_AM_PM_FORMAT:
            if old_hours + self._num[0][0] == 23:
                if self.time_format == PyRadioTime.PM_FORMAT:
                    self.time_format = PyRadioTime.AM_FORMAT
                else:
                    self.time_format = PyRadioTime.PM_FORMAT
                if self._time_format_changed_func:
                    self._time_format_changed_func()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('time format changed to: {}'.format(self.time_format))

    def _calculate_token(self, chbox_id):
        if self._show_am_pm:
            if self.time_format == PyRadioTime.AM_FORMAT:
                return self._char if chbox_id == 3 else ' '
            elif self.time_format == PyRadioTime.PM_FORMAT:
                return self._char if chbox_id == 4 else ' '
            else:
                return ' '
        return ''

    def keypress(self, char):
        '''
        SimpleCursesTime keypress
        Returns:
            -1: Cancel
             0: Continue
             1: Show help
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 0

        if char == ord('t'):
            self._enabled = not self._enabled
            self.show()
            return 0

        if char in (curses.KEY_EXIT, ord('q'), 27):
            return -1

        elif char in (ord('f'), ):
            self.set_time_format(PyRadioTime.NO_AM_PM_FORMAT)

        elif char == ord('?'):
            return 1

        elif self.selected in (3, 4) and \
                char in (curses.KEY_LEFT, curses.KEY_RIGHT,
                         curses.KEY_ENTER, ord('\n'), ord('\r'),
                         ord(' '), ord('h'), ord('l')
                ):
            old_time_format = self.time_format
            if self.selected == 3:
                '''' change AM check box  '''
                if self.time_format == PyRadioTime.AM_FORMAT:
                    self.time_format = PyRadioTime.NO_AM_PM_FORMAT
                elif self.time_format == PyRadioTime.PM_FORMAT:
                    self.time_format = PyRadioTime.AM_FORMAT
                else:
                    self.time_format = PyRadioTime.AM_FORMAT
            else:
                '''' change PM check box  '''
                if self.time_format == PyRadioTime.PM_FORMAT:
                    self.time_format = PyRadioTime.NO_AM_PM_FORMAT
                elif self.time_format == PyRadioTime.AM_FORMAT:
                    self.time_format = PyRadioTime.PM_FORMAT
                else:
                    self.time_format = PyRadioTime.PM_FORMAT
            self._time_format_changed(old_time_format)
            self.show()

        elif char in (curses.KEY_NPAGE, ):
            old_hours = self._num[0][0]
            self._num[self.selected][0] -= self._num[self.selected][4]
            if self._num[self.selected][0] < self._num[self.selected][1]:
                self._num[self.selected][0] = self._num[self.selected][2]
            self._check_time_format(old_hours)
            self.show()

        elif char in (curses.KEY_PPAGE, ):
            old_hours = self._num[0][0]
            self._num[self.selected][0] += self._num[self.selected][4]
            if self._num[self.selected][0] > self._num[self.selected][2]:
                self._num[self.selected][0] = self._num[self.selected][1]
            self._check_time_format(old_hours)
            self.show()

        elif char in (ord('h'), curses.KEY_LEFT):
            old_hours = self._num[0][0]
            self._num[self.selected][0] -= self._num[self.selected][3]
            if self._num[self.selected][0] < self._num[self.selected][1]:
                self._num[self.selected][0] = self._num[self.selected][2]
            self._check_time_format(old_hours)
            self.show()

        elif char in (ord('l'), curses.KEY_RIGHT):
            old_hours = self._num[0][0]
            self._num[self.selected][0] += self._num[self.selected][3]
            if self._num[self.selected][0] > self._num[self.selected][2]:
                self._num[self.selected][0] = self._num[self.selected][1]
            self._check_time_format(old_hours)
            self.show()

        elif char in (9, ord('L')):
            ''' TAB '''
            if self._next_func and self.selected == self._max_selection:
                self._next_func()
                self._focused = False
            else:
                self.selected += 1
                if self.selected > self._max_selection:
                    self.selected = 0
            self.show()

        elif char in (curses.KEY_BTAB, ord('H')):
            ''' Shift-TAB '''
            if self._previous_func and self.selected == 0:
                self._previous_func()
                self._focused = False
            else:
                self.selected -= 1
                if self.selected < 0:
                    self.selected = self._max_selection
            self.show()

        return 0


class SimpleCursesCounter(SimpleCursesWidget):
    ''' A class to provide a counter

        Parameters
        ==========
        Y, X, window
            Coordinates and parent window
        value, minumum, maximum, step, big_step
            counter parameters
            step : small changer (h, l)
            big_step : big change (PgUp, PgDn)
        number_length
            minimum length of number when displayed
            the number is right alligned, i.e. a value of 11
            with a number_length of 4, will display '  11'
        pad
            left pad numbers with 0
            This is the length of the string,
              including current value
            A value of 0 disables it
        color
            text color
        color_focused
            counter color when enabled and focused
        color_not_focused
            counter color when enabled but not focused
        color_disabled
            counter color when disabled
        full_slection
            if not None, it should be a tuple:
                (go left from self._X, numbder of chars to print)
            draw selection cursor as a full line
    '''
    def __init__(
        self, Y, X, window,
        color, color_focused,
        color_not_focused,
        color_disabled,
        minimum=0, maximum=100,
        step=1, big_step=5, value=1, pad=0,
        number_length=3, string='{0}',
        full_selection=None
    ):
        self._Y = Y
        self._X = X
        self._win = self._parent = window
        self._min = minimum
        self._max = maximum
        self._step = step
        self._big_step = big_step
        self._value = int(value)
        self._pad = pad
        if self._value < self._min:
            self._value = self.min
        if self._value > self._max:
            self._value = self._max
        self._len = number_length
        max_len = len(str(self._max))
        if self._len < max_len:
            self._len = max_len
        self.string = string
        self._color = color
        self._color_focused = color_focused
        self._color_not_focused = color_not_focused
        self._color_disabled = color_disabled
        self._full_selection = full_selection

    def refresh(self):
        self.show(self._win)

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = int(val)

    @property
    def minimum(self):
        return self._min

    @minimum.setter
    def minimum(self, val):
        self._min = val

    @property
    def maximum(self):
        return self._max

    @maximum.setter
    def maximum(self, val):
        self._max = val
        max_len = len(srt(self._max))
        if self._len < max_len:
            self._len = max_len

    @property
    def step(self):
        return self._step

    @step.setter
    def step(self, val):
        self._step = val

    @property
    def big_step(self):
        return self._big_step

    @big_step.setter
    def big_step(self, val):
        self._big_step = val

    @property
    def number_length(self):
        return self._len

    @number_length.setter
    def number_length(self, val):
        self._len = val
        max_len = len(srt(self._max))
        if self._len < max_len:
            self._len = max_len

    @property
    def string(self):
        return self._prefix + self._number + self._suffix

    @string.setter
    def string(self, value):
        self._number = '{0}'
        if value:
            sp = value.split('{0}')
            self._prefix = sp[0]
            if len(sp) > 1:
                self._suffix = sp[1]
        else:
            self._prefix = ''
            self._suffix = ''

    def move(self, newY=-1, newX=-1, parent=None):
        if newY > 0:
            self._Y = newY
        if newX > 0:
            self._X = newX
        if parent:
            self._win = self._parent = parent

    def _print_full_line(self, col):
        tmp = self._full_selection[0] * ' ' + self._prefix + str(self._value).rjust(self._len) + self._suffix
        self._win.addstr(
            self._Y,
            self._X - self._full_selection[0],
            tmp.ljust(self._full_selection[1]),
            col
        )

    def show(self, window, opening=False):
        if window:
            self._win = self._parent = window
        if self._enabled:
            if self._focused:
                col = self._color_focused
            else:
                col = self._color_not_focused
        else:
            col = self._color_disabled
        if self._full_selection and self._enabled and self._focused:
            self._print_full_line(col)
        else:
            if self._full_selection:
                self._win.addstr(
                    self._Y,
                    self._X - self._full_selection[0],
                    (self._full_selection[1] ) * ' ',
                    self._color
                )
            self._win.move(self._Y, self._X)
            if self._prefix:
                self._win.addstr(self._prefix, self._color)
            self._win.addstr(self._number.format(str(self._value).zfill(self._pad).rjust(self._len)), col)
            if self._suffix:
                self._win.addstr(self._suffix, self._color)
            ''' overwrite last self._len characters '''
            self._win.addstr(' ' * self._len, self._color)
        self._showed = True

    def keypress(self, char):
        ''' SimpleCursesCounter keypress

            Returns
            -------
               -1 - Cancel
                0   Counter changed
                1 - Continue
                2 - Display help
        '''
        if (not self._focused) or (not self._enabled):
            return 1

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
        ):
            return -1

        elif char == ord('?'):
            return 2

        elif char in (curses.KEY_NPAGE, ):
            self._value -= self._big_step
            if self._value < self._min:
                self._value = self._min
            self.show(self._win)
            return 0

        elif char in (curses.KEY_PPAGE, ):
            self._value += self._big_step
            if self._value > self._max:
                self._value = self._max
            self.show(self._win)
            return 0

        elif char in (ord('h'), curses.KEY_LEFT):
            self._value -= self._step
            if self._value < self._min:
                self._value = self._min
            self.show(self._win)
            return 0

        elif char in (ord('l'), curses.KEY_RIGHT):
            self._value += self._step
            if self._value > self._max:
                self._value = self._max
            self.show(self._win)
            return 0

        return 1


class SimpleCursesWidgetColumns(SimpleCursesWidget):
    ''' A widget to display selectable items
        in columns on a foreign window.
    '''

    ''' items alignment '''
    LEFT = 0        # default
    RIGHT = 1
    CENTER = 2      # not implemented

    ''' items placement '''
    VERICAL = True
    HORIZONTAL = False

    _columns = _rows = 0

    def __init__(self,
                 Y, X,
                 window,
                 items,
                 max_width,
                 color,
                 color_active,
                 color_cursor_selection,
                 color_cursor_active,
                 placement=True,
                 selection=0,
                 active=-1,
                 margin=0,
                 align=0,
                 right_arrow_selects = False,
                 on_activate_callback_function=None,
                 on_up_callback_function=None,
                 on_down_callback_function=None,
                 on_left_callback_function=None,
                 on_right_callback_function=None
                 ):
        ''' Initialize the widget.

            Parameters
            ----------
            Y, X
                Y, X position of widget in its parent (int)
            window
                The window to print items into. It must already exist
                (this widget will not create a window)
            items
                A list or tuple containing the menu items
            max_width
                The maximum width the widget can occupy.
                The number of columns is determined by this value
            color
                The normal color of the non-selected items
            color_active
                The color of the active item (no cursor on it)
            color_cursor_selection
                The cursor color
            color_cursor_active
                The cursor color when cursor is on the active item
            placement
                The items placement when displayed,
                either vertical (default) or horizontal
            selection
                The id of the currently selected item
            active
                The id of the active item
            margin
                Number of spaces to add before and after each item caption
            align
                Items alignment (left, right, center)
            right_arrow_selects
                If True, pressing right arrow will activate the selected item
            on_activate_callback_function
                A function to execute when new active item selected
            on_up_callback_function
                A function to execute when cursor is at row 0 and up is pressed
                The cursor will not move
            on_down_callback_function
                A function to execute when cursor is at the bottom row and down
                is pressed. The cursor will not move
            on_left_callback_function
                A function to execute when cursor is at the first column and left
                is pressed. The cursor will not move
            on_right_callback_function
                A function to execute when cursor is at the last column and right
                is pressed. The cursor will not move
        '''
        self._Y = Y
        self._X = X
        self._win = window
        self.items = items
        self._max_width = max_width
        self._color = color
        self._color_active = color_active
        self._color_cursor_active = color_cursor_active
        self._color_cursor_selection = color_cursor_selection
        self._margin = margin
        self._align = align
        self._right_arrow_selects = right_arrow_selects
        self._placement = placement
        self._on_activate_callback_function = on_activate_callback_function
        self._on_up_callback_function = on_up_callback_function
        self._on_down_callback_function = on_down_callback_function
        self._on_left_callback_function = on_left_callback_function
        self._on_right_callback_function = on_right_callback_function
        self.selection = selection
        self.active = active
        self._focused = True
        self._enabled = True
        self._showed = False
        self._coords = []

        self.set_items()

    @property
    def margin(self):
        '''Returns the widget's Y position '''
        return self._margin

    @property
    def columns(self):
        '''Returns the widget's number of columns '''
        return self._columns

    @columns.setter
    def columns(self, value):
        self._columns = value

    @property
    def rows(self):
        '''Returns the widget's number of rows '''
        return self._rows

    @rows.setter
    def rows(self, value):
        self._rows = value

    @property
    def height(self):
        '''Returns the widget's Y position '''
        return self._maxY

    @height.setter
    def height(self, value):
        self._maxY = value

    @property
    def width(self):
        '''Returns the widget's X position '''
        return self._maxX

    @width.setter
    def width(self, value):
        self._maxX = value

    @property
    def Y(self):
        '''Returns the widget's Y position '''
        return self._Y

    @Y.setter
    def Y(self, value):
        self._Y = value

    @property
    def X(self):
        '''Returns the widget's X position '''
        return self._X

    @X.setter
    def X(self, value):
        self._X = value

    @property
    def window(self):
        '''Returns if the widget is enabled'''
        return self._win

    @window.setter
    def window(self, value):
        self._win = value
        if self._showed:
            self.show()

    @property
    def enabled(self):
        '''Returns if the widget is enabled'''
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if self._showed:
            self.show()

    @property
    def focused(self):
        '''Returns if the widget has focus'''
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value
        if self._showed:
            self.show()

    @property
    def max_width(self):
        '''Returns if the widget has focus'''
        return self._max_width

    @max_width.setter
    def max_width(self, value):
        self._max_width = value
        self.set_items()

    def recalculate_columns(self):
        self.set_items()

    def _last_in_row(self, pY, pX):
        # logger.error('DE pY = {0}, pX = {1}'.format(pY, pX))
        test = [x for x in self._coords if x[0] == pY]
        # logger.error('DE test = {}'.format(test))
        return True if test[-1] == (pY, pX) else False

    def set_items(self, items=None):
        if items:
            self.items = tuple(items[:])
        self._item_width = len(max(self.items, key=len)) + 2 * self._margin
        self._columns = int((self._max_width / self._item_width))
        if self._columns == 1:
            self._columns = 2
        self._maxX = self._columns * self._item_width
        self._maxY = int(len(self.items) / self._columns)
        if len(self.items) % self._columns != 0:
            self._maxY += 1
        self._coords = []

    def show(self):
        # logger.error('DE columns = {}, rows ={}'.format(self._columns, self._maxY))
        for i, n in enumerate(self.items):
            ''' create string to display '''
            if self._align == self.LEFT:
                disp_item = ' ' * self._margin + n.ljust(self._item_width - 2 * self._margin) + ' ' * self._margin
            elif self._align == self.RIGHT:
                disp_item = ' ' * self._margin + n.rjust(self._item_width - 2 * self._margin) + ' ' * self._margin
            else:
                disp_item = n.center(self._item_width)

            ''' find color to use '''
            # logger.error('DE self._focused = {}'.format(self._focused))
            if self._focused and self._enabled:
                # logger.error('DE focused and enabled')
                col = self._color
                # logger.error('{0}, sel={1}, ac={2}'.format(i, self.selection, self.active))
                if i == self.selection and i == self.active:
                    col = self._color_cursor_active
                    # logger.error('active color')
                elif i == self.selection:
                    col =self._color_cursor_selection
                    # logger.error('color_cursor_selection')
                elif i == self.active:
                    col = self._color_active
                    # logger.error('color_cursor_active')
            elif self._enabled:
                # logger.error('DE enabled')
                col = self._color
                if i == self.active:
                    col = self._color_active
            else:
                # logger.error('DE not focused')
                col = self._color

            ''' fill coords list, if not filled yet '''
            if len(self._coords) != len(self.items):
                if i == 0:
                    column = row = 0
                else:
                    if self._placement == self.VERICAL:
                        row = int(i / self._maxY)
                        column = int(i % self._maxY)
                    else:
                        column = int(i / self._columns)
                        row = int(i % self._columns)
                # logger.error('DE i = {}, column = {}, row = {}'.format(i, column, row))

                self._coords.append((column, row))

            ''' display string '''
            try:
                self._win.addstr(
                    self._Y + self._coords[i][0],
                    self._X + self._coords[i][1] * self._item_width,
                    disp_item,
                    col
                )
            except:
                logger.error('error displaying item {}'.format(i))

        # for i, n in enumerate(self._coords):
        #     logger.error('Item {}: X = {}, Y = {}'.format(i, *n))

        self._rows = max([x[0] for x in self._coords]) + 1
        # logger.error('DE coords = {}'.format(self._coords))
        # logger.error('DE columns = {0}, rows = {1}'.format(self._columns, self._rows))

        self._showed = True

    def keypress(self, char):
        ''' SimpleCursesWidgetColumns keypress

            Returns
            -------
               -1 - Cancel
                0 - Item selected
                1 - Continue
                2 - Cursor moved
                3 - Display help
        '''
        if (not self._focused) or (not self._enabled):
            return 1

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
        ):
            return -1

        elif char == ord('?'):
            return 3

        elif self._right_arrow_selects and char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            self.active = self.selection
            logger.error('DE active = {}'.format(self.active))
            ''' Do not refresh the widget, it will
                probably be hidden next
            '''
            if self._on_activate_callback_function:
                self._on_activate_callback_function()
            return 0

        elif not self._right_arrow_selects and char in (
            ord(' '), ord('\n'), ord('\r'),
            curses.KEY_ENTER
        ):
            self.active = self.selection
            logger.error('DE active = {}'.format(self.active))
            self.show()
            return 0

        elif char in (ord('g'), curses.KEY_HOME):
            self.selection = 0
            self.show()
            return 2

        elif char in (ord('G'), curses.KEY_END):
            self.selection = len(self.items) - 1
            self.show()
            return 2

        elif char in (curses.KEY_PPAGE, ):
            if self.selection == 0:
                self.selection = len(self.items) - 1
            else:
                self.selection -= 5
                if self.selection < 0:
                    self.selection = 0
            self.show()
            return 2

        elif char in (curses.KEY_NPAGE, ):
            if self.selection == len(self.items) - 1:
                self.selection = 0
            else:
                self.selection += 5
                if self.selection >= len(self.items):
                    self.selection = len(self.items) - 1
            self.show()
            return 2

        elif char in (ord('k'), curses.KEY_UP):
            pY, pX = self._coords[self.selection]
            if self._on_up_callback_function and pY == 0:
                self._on_up_callback_function()
            else:
                self.selection -= 1
                if self.selection < 0:
                    self.selection = len(self.items) - 1
                self.show()
            return 2

        elif char in (ord('j'), curses.KEY_DOWN):
            pY, pX = self._coords[self.selection]
            # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
            # logger.error('DE rows = {}'.format(self._rows))
            if self._on_down_callback_function and \
                    (pY == self._rows - 1 or self.selection == len(self.items) - 1):
                self._on_down_callback_function()
            else:
                self.selection += 1
                if self.selection == len(self.items):
                    self.selection = 0
                self.show()
            return 2

        elif char in (ord('l'), curses.KEY_RIGHT):
            pY, pX = self._coords[self.selection]
            if self._on_right_callback_function and \
                    (pX == self._columns - 1 or self._last_in_row(pY, pX)):
                self._on_right_callback_function()
            else:
                # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
                pX += 1
                if pX >= self._columns:
                    pX = 0
                    pY += 1
                # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
                # logger.error('DE {}'.format(self._coords))
                try:
                    it = self._coords.index((pY, pX))
                except ValueError:
                    pX = 0
                    pY += 1
                    # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
                    try:
                        it = self._coords.index((pY, pX))
                    except:
                        it = self._coords.index((0, 0))
                # logger.error('DE it = {}'.format(it))
                self.selection = it
                self.show()
            return 2

        elif char in (ord('h'), curses.KEY_LEFT):
            pY, pX = self._coords[self.selection]
            if self._on_left_callback_function and pX == 0:
                self._on_left_callback_function()
            else:
                # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
                pX -= 1
                if pX < 0:
                    pX = self._columns - 1
                    pY -= 1
                    if pY < 0:
                        self.selection = self._coords.index(max(self._coords))
                    else:
                        # logger.error('DE pY ={0}, pX ={1}'.format(pY, pX))
                        # logger.error('DE {}'.format(self._coords))
                        try:
                            it = self._coords.index((pY, pX))
                        except ValueError:
                            pX -= 1
                            while True:
                                try:
                                    it = self._coords.index((pY, pX))
                                    break
                                except ValueError:
                                    pX -= 1
                        # logger.error('DE it = {}'.format(it))
                        self.selection = it
                else:
                    self.selection = self._coords.index((pY, pX))

                self.show()
            return 2

        return 1


class SimpleCursesMenu(SimpleCursesWidget):
    ''' A bordered wrapper around
        SimpleCursesListEntries
    '''

    ''' items alignment '''
    LEFT = 0        # default
    RIGHT = 1
    CENTER = 2      # not implemented

    ''' window type '''
    FULL_SCREEN = 0
    CENTERED = 1
    POS_Y_X = 2

    _selection = _start_pos = 0
    _global_functions = _local_functions = {}
    _can_add_items = _can_delete_items = False
    def __init__(self,
                 Y, X,
                 parent,
                 window_type,
                 items,
                 title,
                 color,
                 color_title,
                 color_border,
                 color_active,
                 color_cursor_selection,
                 color_cursor_active,
                 mode=-1,
                 selection=0,
                 active=-1,
                 max_height=0,
                 max_width=0,
                 min_height=8,
                 min_width=25,
                 auto_adjust_width=False,
                 full_window=False,
                 outer_margin=2,
                 margin=0,
                 align=0,
                 has_captions = False,
                 color_captions = None,
                 captions = None,
                 display_count = False,
                 right_arrow_selects=True,
                 can_add_items=False,
                 can_delete_items=False,
                 on_activate_callback_function=None,
                 on_up_callback_function=None,
                 on_down_callback_function=None,
                 on_left_callback_function=None,
                 on_right_callback_function=None,
                 global_functions=None,
                 local_functions=None,
                 external_keypress_function=None
                 ):
        ''' Initialize the widget.

            Parameters
            ----------
            Y, X
                Y, X position of widget in its parent (int)
            parent
                The window to print items into. It must already exist
                (this widget will not create a window)
            window_type
                The type of window to create
                Types are:
                    0 - Full screen; occupy the whole of the parent window
                    1 - centered; center in parent window, obbey outer_margin
                    2 - at Y,X with max_width and max_height
            items
                A list containing the menu items
            mode
                The way to display the widget.
                If mode = -1:
                    Captions will start with a "-" on margin=0
                    Items will obey margin
                If mode = x:
                    Captions will obey margin, no indicator.
                    Items will be margin + x
            color_captions
                The color to show captions in
            has_captions
                Set True to enable captions
                A caption item starts with a '-' and cannot be
                selected. It is displayed in color_captions color
                or color_active if that is not defined
            captions
                A list to indicate captions items. Set true to
                corresponding item id to turn it into a caption.
                Will be calculated from items if None
            display_count
                If True, display itme id + 1 before item data
                If True, captions will not be displayed
            color
                The normal color of the non-selected items
            color_border
                The color of the border
            color_title
                The color of the title (caption) of the widget
            color_active
                The color of the active item (no cursor on it)
            color_cursor_selection
                The cursor color
            color_cursor_active
                The cursor color when cursor is on the active item
            selection
                The id of the currently selected item
            active
                The id of the active item
            max_height
                The maximum number of lines to display
                If 0, use parent's max_height - 2
            max_width
                The maximum line length to display
                If 0, use parent's max_width - 2
            auto_adjust_width
                If False, obbey self._max_width
                If True, set max_width to maximum length of items
            outer_margin
                Margin from parent
            margin
                Number of spaces to add before and after each item caption
            align
                Items alignment (left, right, center)
            right_arrow_selects
                If True (default) right arrow and "l" selects the new
                active item (for example a menu). Set it to False if
                the widget is part of a composite widget.
            can_add_items
            can_delete_items
                Set either to True, to enable item addition or deletion
            on_activate_callback_function
                A function to execute when new active item selected
            global_functions
                A dict with functions to execute when keys pressed,
                before handling keys internally
                    Format: {ord('key'): function}
                    Example: {ord('R'): self._reload}
                return is 1 (continue) in the widget
            local_functions
                A dict with functions to execute when keys pressed,
                after handling keys internally
                    Format: {ord('key'): function}
                    Example: {ord('R'): self._reload}
                return is 1 (continue) in the widget
            external_keypress_function
                An external keypress function to call, after handling
                all other key handling routines.
                The function will be called as
                    external_keypress_function(char)
                and must return:
                   -1 - Cancel
                    1 - Continue
                    2 - Display help
        '''
        self._too_small = False
        self._showed = False
        self._window_type = window_type
        self._title = title
        self._items = items
        self._Y = Y
        self._X = X
        self._parent = parent
        self._items = []
        self._color = color
        self._color_border = color_border
        self._color_title = color_title
        self._color_active = color_active
        self._color_cursor_active = color_cursor_active
        self._color_cursor_selection = color_cursor_selection
        self._maxY = self._max_height = max_height
        self._body_maxY = self._maxY - 2
        self._maxX = self._max_width = max_width
        # log_it('init maxX = {}\n'.format(self._maxX))
        self._minY = min_height
        self._minX = min_width
        self._body_maxX = self._maxX - 2
        self._auto_adjust_width = auto_adjust_width
        self._full_window = full_window
        self._outer_margin = outer_margin
        self._margin = margin
        self._align = align
        self._has_captions = has_captions
        if captions:
            self._captions = captions
        else:
            self._captions = []
        self._color_captions = color_captions
        self._display_count = display_count
        if self._display_count:
            self._caption = None
            self._has_captions = False
        self._can_add_items = can_add_items
        self._can_delete_items = can_delete_items
        self._right_arrow_selects = right_arrow_selects
        self._on_activate_callback_function = on_activate_callback_function
        self._on_up_callback_function = on_up_callback_function
        self._on_down_callback_function = on_down_callback_function
        self._on_left_callback_function = on_left_callback_function
        self._on_right_callback_function = on_right_callback_function
        self._selection = selection
        if global_functions is not None:
            self._global_functions = global_functions
        if local_functions is not None:
            self._local_functions = local_functions
        self._external_keypress__function = external_keypress_function
        self.active = active
        self._focused = True
        self._enabled = True
        self._showed = False
        if color_captions:
            self._color_captions = color_captions
        else:
            self._color_captions = self._color_active

        self.set_items(
            items=items,
            captions=self._captions,
            has_captions=self._has_captions,
            can_add_items=self._can_add_items,
            can_delete_items=self._can_delete_items
        )
        self._get_window()
        self._calculate_max_height_max_width()
        self._make_sure_selection_is_visible()

    @property
    def too_small(self):
        '''Returns if the widget is too small '''
        return self.too_small

    @property
    def string(self):
        '''Returns the widget's active string '''
        return self._items[self.active]

    @property
    def current_string(self):
        '''Returns the widget's seldcted string '''
        return self._items[self._selection]

    @property
    def selection(self):
        '''Returns the widget's max_height '''
        return self._selection

    @selection.setter
    def selection(self, value):
        if 0 <= value < len(self._items):
            self._set_selection(value)
        else:
            raise ValueError('selection out of bounds!')

    @property
    def max_height(self):
        '''Returns the widget's max_height '''
        return self._maxY

    @max_height.setter
    def max_height(self, value):
        self._maxY = val
        self._calculate_max_height_max_width()
        self._showed = False

    @property
    def max_width(self):
        '''Returns the widget's max_width '''
        return self._maxX

    @max_width.setter
    def max_width(self, value):
        self._maxX = val
        self._calculate_max_height_max_width()
        self._showed = False

    @property
    def parent(self):
        '''Returns the widget's window '''
        return self._win

    @parent.setter
    def parent(self, value):
        self._win = value
        self._showed = False
        self._calculate_max_height_max_width()

    @property
    def enabled(self):
        '''Returns if the widget is enabled'''
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value

    @property
    def focused(self):
        '''Returns if the widget has focus'''
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value

    @property
    def count(self):
        '''Returns number of items'''
        return len(self._items)

    def _set_selection(self, a_sel):
        if a_sel >= 0 and a_sel < len(self._items):
            self._old_selection = self._selection
            self._old_start_pos = self._start_pos

            self._selection = a_sel

            if self._make_sure_selection_is_visible():
                self._refresh()
            else:
                self._toggle_selected_item()


            # self._make_sure_selection_is_visible()

            # # log_it('last line = {}'.format(self._start_pos + self._maxY))
            # if a_sel < self._start_pos or a_sel >= self._start_pos + self._body_maxY:
            #     self._start_pos = self._selection - int(self._body_maxY / 2) + 1
            #     self._refresh()
            # else:
            #     self._toggle_selected_item()


    def _get_window(self):
        Y, X = self._parent.getmaxyx()
        # log_it('== WIN Y = {0}, X = {1}'.format(Y, X))
        if self._window_type == self.FULL_SCREEN:
            self._Y = self._X = 0
            self._maxY = Y
            self._maxX = X
        elif self._window_type == self.CENTERED:
            self._maxY = items_max_Y = len(self._items)
            if self._maxY > Y - 2 * self._outer_margin:
                self._maxY = Y - 2 * self._outer_margin

            # logger.error('max = {}'.format(max(len(x) for x in self._items)))
            self._maxX = items_max_X = max(cjklen(x) for x in self._items) + 2
            if self._margin > 0:
                self._maxX = self._maxX + 2 * self._margin
            if self._display_count:
                self._maxX = self._maxX + len(str(items_max_Y)) + 3
            if self._maxX > X - 2 * self._outer_margin:
                self._maxX = X - 2 * self._outer_margin

            ''' make sure we have a big enough window '''
            if self._maxY < 10:
                self._maxY = 10
            if self._maxX < 30:
                self._maxX = 30

            aY, aX = self._parent.getbegyx()
            self._Y = aY + int((Y-self._maxY)/2)
            self._X = aX + int((X-self._maxX)/2)

        else:
            aY, aX = self._parent.getbegyx()

        if self._maxY <= self._minY or \
                self._maxX <= self._minX or \
                self._X < 2 or \
                self._Y < 2:
            self._too_small = True
            aY, aX = self._parent.getbegyx()
            self._win = curses.newwin(
                4, 13,
                aY + int((Y-4)/2),
                aX + int((X-13)/2)
            )
            self._print_box()
        else:
            self._too_small = False
            # logger.info('Y={0}, X={1}, maxY={2}, maxX={3}'.format(
            #     self._Y, self._X,
            #     self._maxY, self._maxX
            # ))
            self._win = curses.newwin(
                self._maxY, self._maxX,
                self._Y, self._X
            )
        self._body_maxY = self._maxY - 2
        self._body_maxX = self._maxX - 2

    def _get_item_id(self, item=None):
        ''' returns item id in visible window
            if item is not visible, return -1
        '''
        if item is None:
            item = self._selection
        ret = item - self._start_pos
        # log_it('== ret = {}'.format(ret))
        if ret < 0 or ret >= self._body_maxY:
            return -1
        return ret

    def toSrt(self, a_str):
        return a_str

    def _calculate_max_height_max_width(self):
        return
        Y, X = self._win.getmaxyx()
        if self._maxY == 0:
            self._maxY = Y - 2

        if self._maxX == 0:
            self._maxX = X - 2
        if self._auto_adjust_width:
            self._maxX = cjklen(max(self._items)) + 2 * self._margin
        if self._maxX > self._max_width:
            self._maxX = self._max_width

    def set_items(
        self,
        items=None,
        captions=None,
        has_captions=False,
        can_add_items=False,
        can_delete_items=False
    ):
        if items:
            if has_captions:
                if captions:
                    self._items = items
                    self._captions = captions
                else:
                    cap = []
                    itms = []
                    for n in range(0, len(items)):
                        if n.starts_with('-'):
                            itms.append(items[n][1:])
                            cap.append(n)
                        else:
                            itms.append(items[n])
                    self._items = itms
                    self._captions = cap
            else:
                self._items = items
                self._captions = []
            self._showed = False
        self._scroll = True if len(self._items) > self._body_maxY else False

    def show(self, parent=None):
        ''' show the widget

            Paramters
            =========
            parent
                the window to print output
        '''
        # log_it('show')
        new_win = False
        if (not self._showed or parent != self._parent) \
                and parent is not None:
            # log_it('\n\nhere\n\n')
            # log_it('got new parent')
            self._parent = parent
            self._get_window()
            # logger.error('too_small = {}'.format(self._too_small))
            self._calculate_max_height_max_width()
            new_win = True

        if self._too_small:
            self._win.addstr(1, 1, ' Window is', self._color)
            self._win.addstr(2, 1, ' Too small', self._color)
            self._win.refresh()
            return

        if new_win:
            self._make_sure_selection_is_visible()
            self.show()
            return

        self._print_box_and_title()
        self._refresh()

    def _print_box_and_title(self):
        self._print_box()
        self._print_title()

    def _print_box(self):
        self._win.bkgdset(' ', self._color_border)
        self._win.erase()
        self._win.box()

    def _print_title(self):
        self._win.addstr(
            0, int((self._maxX-len(self._title))/2),
            self._title, self._color_title
        )

    def _refresh(self):
        if len(self._items) == 0:
            self._win.hline(self._Y, self._X, ' ', self._maxX, self._color)
            self._win.refresh()
            return
        # calculate start item
        # TODO: calculate start_pos

        self._item_max_width = cjklen(max(self._items, key=cjklen))
        active_item_length = self._maxX - 2 * self._margin - 2
        if self._start_pos < 0:
            self._start_pos = 0
        elif self._start_pos > len(self._items) - 1 - self._body_maxY:
            self._start_pos = len(self._items) - self._body_maxY
        ''' make sure we have a valid self._start_pos '''
        if self._start_pos < 0:
            self._start_pos = 0
        # logger.error('refresh (st={0}, sel={1})'.format(self._start_pos, self._selection))
        for i in range(0, self._body_maxY):
            item_id = i + self._start_pos
            disp_item = self._format_line(i, active_item_length)
            if disp_item is None:
                continue
            # log_it('X={0}, item = "{1}"'.format(self._X, disp_item))
            col = self._get_item_color(item_id)
            try:
                self._win.addstr(i+1, 1, disp_item, col)
            except:
                pass
        self._win.refresh()
        self._showed = True

    def _format_line(self, i, active_item_length):
        cap = False
        #print('i=',i)
        item_id = i + self._start_pos
        if item_id < len(self._items):
            if self._has_captions and not self._display_count:
                if item_id in self._captions:
                    cap = True
            if cap:
                disp_item = '─ ' + self._items[item_id][:active_item_length-2] + ' ─'
                self._win.addstr(i + self._Y, self._X, disp_item, self._color_captions)
                return None
            elif self._display_count:
                if self._scroll:
                    count_len = len(str(self._start_pos + self._body_maxY))
                    # log_it('scroll count_len = {0}, start_pos = {1}'.format(count_len, self._start_pos))
                else:
                    count_len = len(str(len(self._items)))
                    # log_it('count_len = {}'.format(count_len))
                disp_item_pref = '{}. '.format(str(item_id+1).rjust(count_len))
                # disp_item_suf = self._items[item_id][:active_item_length-cjklen(disp_item_pref)]
                disp_item_suf = cjkljust(self._items[item_id], self._body_maxX - len(disp_item_pref) - 2 * self._margin)
                disp_item = ' ' * self._margin + disp_item_pref + disp_item_suf + ' ' * self._margin
            else:
                #print('item_id = {}'.format(item_id))
                item = self._items[item_id][:active_item_length]
                if self._align == self.LEFT:
                    disp_item = ' ' * self._margin + item.cjkljust(active_item_length) + ' ' * self._margin
                elif self._align == self.RIGHT:
                    disp_item = ' ' * self._margin + item.cjkrjust(active_item_length) + ' ' * self._margin
                else:
                    disp_item = ' ' * self._margin + item.cjkcenter(active_item_length) + ' ' * self._margin
                # disp_item = disp_item.ljust(self._body_maxX)
        else:
            # create empty lines
            disp_item = ' ' * self._body_maxX
        return disp_item

    def _get_item_color(self, item_id):
        # log_it('--- START ---')
        # log_it(f'  _get_item_color: item_id = {item_id}, selection = {self._selection}')
        if self._focused and self._enabled:
            col = self._color
            # log_it('  color: color (default)')
            if item_id == self._selection == self.active:
                col = self._color_cursor_active
                # log_it('  color: color cursor active')
            elif item_id == self._selection:
                col =self._color_cursor_selection
                # log_it('  color: color cursor selection')
            elif item_id == self.active:
                col = self._color_active
                # log_it('  color: color active')
        elif self._enabled:
            col = self._color
            if item_id == self.active:
                col = self._color_active
        else:
            col = self._color
            # log_it('  color: color (else)')
        # log_it('--- END ---')
        return col

    def _make_sure_selection_is_visible(self, mov=1):
        ''' adjust self._start_pos to make self._selection visible
            Returns
                True    self._start_pos changed (use self._refresh)
                False   self._start_pos not changed (use self._toggle_selected_item)
        '''
        if len(self._items) <= self._body_maxY:
            self._start_pos = 0
            return
        self._verify_selection_not_on_caption(mov)
        self._old_start_pos = self._start_pos
        meso = int(self._body_maxY / 2)
        self._end_pos = self._start_pos + self._body_maxY - 1

        if self._start_pos <= self._selection <= self._end_pos:
            return False

        self._start_pos = self._selection - meso

        if self._start_pos < 0:
            self._start_pos = 0
        return True

    def _verify_selection_not_on_caption(self, movement=1):
        # log_it('\n\n1 mov = {0}, sel = {1}, items = {2}'.format(movement, self._selection, len(self._items)))
        if len(self._items) == 0:
            return
        if self._selection < 0 and movement != -1:
            self._selection = 0
        elif self._selection >= len(self._items):
            self._selection = len(self._items) - 1
        if self._has_captions:
            if len(self._items) == len(self._captions):
                self._selection = -1
                return
            while self._selection in self._captions:
                self._selection += movement
                if self._selection == len(self._items):
                    self._selection = 0
                elif self._selection < 0:
                    self._selection = len(self._items) - 1
        # log_it('\n\n2 mov = {0}, sel = {1}, items = {2}'.format(movement, self._selection, len(self._items)))

    def delete_item(self, target):
        d = deque(self._items)
        d.rotate(-target)
        ret = d.popleft()
        d.rotate(target)
        self._items = list(d)
        # log_it('=======> id = {0}, captions = {1}'.format(target, self._captions))
        if self._has_captions:
            for i in range(0, len(self._captions)):
                if target < self._captions[i]:
                    self._captions[i] -= 1

        # log_it('-------> id = {0}, captions = {1}'.format(target, self._captions))

        mov = 1
        if self._selection >= len(self._items):
            self._selection -= 1
            mov = -1
        if self.active > target:
            self.active -= 1
        elif self.active == target:
            self.active = -1

        self._verify_selection_not_on_caption(mov)
        if self._make_sure_selection_is_visible():
            self._refresh()
        else:
            self._toggle_selected_item()

        return len(self._items)

    def _toggle_selected_item(self):
        active_item_length = self._body_maxX - 2 * self._margin
        # log_it('_toggle_selected_item')
        update = False
        old_selection_id = self._get_item_id(self._old_selection)
        if old_selection_id > -1:
            self._win.chgat(old_selection_id + 1, 1, self._body_maxX, self._get_item_color(self._old_selection))
            # self._win.addstr(
            #     old_selection_id + 1,
            #     1,
            #     self._format_line(old_selection_id, active_item_length),
            #     self._get_item_color(self._old_selection)
            # )
            # log_it('_toggle_selection_item: X={0}, changing old selection: {1}, line: {2}'.format(self._X, old_selection_id, self._Y + old_selection_id))
            update = True
        else:
            # log_it('_toggle_selection_item: NOT changing old selection: {0}, line: {1}'.format(old_selection_id, self._Y + old_selection_id))
            # log_it('                        start: {}'.format(self._start_pos))
            # log_it('                        selection: {}'.format(self._selection))
            # log_it('                        old_selection: {}'.format(self._old_selection))
            pass
        selection_id = self._get_item_id(self._selection)
        if selection_id > -1:
            self._win.chgat(selection_id + 1, 1, self._body_maxX, self._get_item_color(self._selection))
            # self._win.addstr(
            #     selection_id + 1,
            #     1,
            #     self._format_line(selection_id, active_item_length),
            #     self._get_item_color(self._selection)
            # )
            # log_it('_toggle_selection_item: X={0}, setting new selection: {1}, line: {2}'.format(self._X, selection_id, self._Y + selection_id))
            update = True
        # logger.error('toggle (st={0}, sel={1})'.format(self._start_pos, self._selection))
        if update:
            self._win.refresh()
            return True
        return False

    def _toggle_active_item(self):
        active_item_length = self._body_maxX - 2 * self._margin
        self._old_active = self.active
        self.active = self._selection
        old_active_id = self._get_item_id(self._old_active)
        if old_active_id > -1:
            self._win.addstr(
                old_active_id + 1,
                1,
                self._format_line(old_active_id, active_item_length),
                self._get_item_color(old_active_id)
            )
            # self._win.chgat(old_active_id + 1, 1, self._body_maxX, self._color)
            # log_it('_toggle_active_item: changind old active: {0}, line: {1}'.format(old_active_id, self._Y + old_active_id))
        active_id = self._get_item_id(self.active)
        # self._win.chgat(active_id + 1, 1, self._body_maxX, self._color_cursor_active)
        self._win.addstr(
            active_id + 1,
            1,
            self._format_line(active_id, active_item_length),
            self._get_item_color(self._selection)
        )
        # log_it('_toggle_active_item: setting new active: {0}, line: {1}'.format(active_id, self._Y + active_id))
        self._win.refresh()

    def keypress(self, char):
        ''' SimpleCursesMenuEntries keypress

            Returns
            -------
               -1 - Cancel
                0 - Item selected
                1 - Continue
                2 - Display help
        '''
        if self._too_small:
            return 1

        if (not self._focused) or (not self._enabled):
            return 1

        self._old_selection = self._selection
        self._old_start_pos = self._start_pos
        # log_it('  == old_sel = {0}, start = {1}'.format(self._old_selection, self._old_start_pos))

        if char in self._global_functions.keys():
            self._global_functions[char]()

        elif char in (
            curses.KEY_EXIT, ord('q'), 27,
            ord('h'), curses.KEY_LEFT
        ):
            return -1

        elif char == ord('?'):
            return 2

        elif self._can_delete_items and \
                char in (ord('x'), curses.KEY_DC):
            if len(self._items) == 0:
                return 0
            if self._has_captions:
                if len(self._items) == len(self._captions) + 1:
                    return 0
            self.delete_item(self._selection)
            self._refresh()
            return 0

        elif self._right_arrow_selects and char in (
            ord('l'), ord(' '), ord('\n'), ord('\r'),
            curses.KEY_RIGHT, curses.KEY_ENTER
        ):
            ''' Do not refresh the widget, it will
                probably be hidden next
            '''
            self._toggle_active_item()
            if self._on_activate_callback_function:
                self._on_activate_callback_function()
            return 0

        elif not self._right_arrow_selects and char in (
            ord(' '), ord('\n'), ord('\r'),
            curses.KEY_ENTER
        ):
            self._toggle_active_item()
            return 0

        elif char in (ord('g'), curses.KEY_HOME):
            if len(self._items) == 0:
                return 1
            self._selection = 0
            self._verify_selection_not_on_caption()
            if self._start_pos == 0:
                self._toggle_selected_item()
            else:
                self._start_pos = 0
                self._refresh()

        elif char in (ord('G'), curses.KEY_END):
            if len(self._items) == 0:
                return 1
            self._selection = len(self._items) - 1
            self._verify_selection_not_on_caption(-1)
            # log_it('\n\n=====> max = {0}, items = {1}\n\n'.format(self._body_maxY, len(self._items)))
            if len(self._items) >= self._body_maxY:
                if self._start_pos > self._selection - self._body_maxY:
                    self._start_pos = self._selection - self._body_maxY + 1
                    self._toggle_selected_item()
                else:
                    self._start_pos = self._selection - self._body_maxY + 1
                    self._refresh()
            else:
                self._start_pos = 0
                self._refresh()

        elif char == ord('H'):
            if len(self._items) == 0:
                return 1
            self._selection = self._start_pos
            self._verify_selection_not_on_caption()
            self._toggle_selected_item()

        elif char == ord('M'):
            if len(self._items) == 0:
                return 1
            self._selection = self._start_pos + int(self._body_maxY /2) - 1
            self._verify_selection_not_on_caption()
            self._toggle_selected_item()

        elif char == ord('L'):
            if len(self._items) == 0:
                return 1
            self._selection = self._start_pos + self._body_maxY - 1
            self._verify_selection_not_on_caption()
            self._toggle_selected_item()

        elif char in (curses.KEY_PPAGE, ):
            if len(self._items) == 0:
                return 1
            if self._selection == 0:
                self._selection = len(self._items) - 1
                self._verify_selection_not_on_caption()
                if self._scroll:
                    self._start_pos = self._selection - self._body_maxY + 1
                    self._refresh()
                    return 1
            else:
                self._selection -= 5
                self._verify_selection_not_on_caption()
                if self._selection < self._start_pos:
                    self._start_pos = self._selection
                    self._refresh()
                    return 1
            if not self._toggle_selected_item():
                self._refresh()

        elif char in (curses.KEY_NPAGE, ):
            if len(self._items) == 0:
                return 1
            if self._selection == len(self._items) - 1:
                self._selection = 0
                self._verify_selection_not_on_caption()
                self._start_pos = 0
                if self._scroll:
                    self._refresh()
                    return 1
            else:
                self._selection += 5
                self._verify_selection_not_on_caption()
                if self._selection >= len(self._items):
                    self._selection = len(self._items) - 1
                    self._verify_selection_not_on_caption(-1)
                if self._scroll:
                    # log_it('sel = {1}, start = {1}'.format(self._selection, self._start_pos))
                    if self._selection - self._start_pos > self._body_maxY - 1:
                        self._start_pos = self._selection - self._body_maxY + 1
                        self._refresh()
                        return 1
            if not self._toggle_selected_item():
                self._refresh()

        elif char in (ord('k'), curses.KEY_UP):
            if len(self._items) == 0:
                return 1
            self._selection -= 1
            self._verify_selection_not_on_caption(-1)
            if self._selection < 0:
                self._selection = len(self._items) - 1
                self._verify_selection_not_on_caption(-1)
                self._start_pos = 0
                if self._scroll:
                    self._start_pos = self._selection - self._body_maxY + 1
                    self._refresh()
                    return 1
            if self._scroll:
                # we have scrolling items
                if self._selection < self._start_pos:
                    # we need to scroll!
                    self._start_pos -= 1
                    # log_it('We need to scroll: start: {0}, selection = {1}'.format(self._start_pos,self._selection))
                    self._refresh()
                    return 1
            # log_it('going from {0} to {1}, start at {2}'.format(self._old_selection, self._selection, self._start_pos))
            if not self._toggle_selected_item():
                # log_it('self._refresh')
                self._refresh()

        elif char in (ord('j'), curses.KEY_DOWN):
            if len(self._items) == 0:
                return 1
            self._selection += 1
            if self._has_captions:
                if self._selection in self._captions:
                    self._selection += 1
            if self._selection == len(self._items):
                self._selection = 0
                self._verify_selection_not_on_caption()
                self._start_pos = 0
                if self._scroll:
                    self._refresh()
                    return 1
            if self._scroll:
                # we have scrolling items
                if self._selection >= self._start_pos + self._body_maxY:
                    # we need to scroll!
                    self._start_pos = self._selection - self._body_maxY + 1
                    # log_it('We need to scroll: start: {0}, selection {1}'.format(self._start_pos, self._selection))
                    self._refresh()
                    return 1

            if not self._toggle_selected_item():
                self._refresh()

        elif char in self._local_functions.keys():
            self._local_functions(char)

        elif self._external_keypress__function:
            return self._external_keypress__function(char)

        return 1


class SimpleCursesCheckBox(SimpleCursesWidget):
    '''A very simple checkbox curses widget '''
    _checked = False
    _highlight_all = False

    def __init__(self,
                 Y, X, caption,
                 color_focused, color, bracket_color,
                 char='✔', checked=False, focused=False,
                 highlight_all=False, callback_function=None):
        ''' Initialize the widget.

            Parameters
            ----------
            Y, X
                Y, X position of widget in its parent (int)
            caption
                The caption of the widget (string).
            color_focused
                Active checkbox color (curses.color_pair)
            color
                Inactive checkbox color (curses.color_pair)
            bracket_color
                The color of the brackets (curses.color_pair)
                Also the color to use when widget is disabled
            char
                The character to indicate a checked checkbox (string)
            checked
                Index of checked checkbox (int)
            focused
                True if widget has focus (boolean)
            highlight_all
                Focused behaviour (boolean).
                If True, the whole window uses the active color.
                If False, only char uses the active color.
        '''

        self._Y = Y
        self._X = X
        self._caption = caption
        self._char = char
        if platform.lower().startswith('win') and \
                self._char == '✔':
            self._char = 'X'
        self._checked = checked
        self._focused = focused
        self._highlight_all = highlight_all
        self._color_focused = color_focused
        self._color = color
        self._bracket_color = bracket_color

        ''' initialize the window '''
        self.resize()

    @property
    def char(self):
        '''Character to indicate a checked checkbox
           Default: ✔
        '''
        return self._char

    @char.setter
    def char(self, value):
        self._char = value
        self.refresh()

    @property
    def checked(self):
        '''Returns if the checkbox is ckecked'''
        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = value
        self.refresh()

    @property
    def highlight_all(self):
        '''Returns if the whole window will use the
        focused color when focused'''
        return self._highlight_all

    @highlight_all.setter
    def highlight_all(self, value):
        self._highlight_all = value
        self.refresh()

    def resize(self):
        '''Resize the widget
           For changes to be displayed,
           use show afterwards'''

        ''' use cjklen for cjk support '''
        if self._win:
            del self._win
        self._width = None
        self._width = len(self._caption) + 4
        self._win = curses.newwin(1, self._width, self._Y, self._X)

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X
        if self._win:
            self._win.mvwin(self._Y, self._X)

    def show(self, parent=None):
        '''Put the widget on the screen'''
        if self._win:
            self._win.bkgdset(' ', self._color)
            self._win.erase()
            self._win.touchwin()
            self._win.refresh()
            self.refresh()
            self._showed = True

    def refresh(self):
        '''Refresh the widget's content'''
        if self._win:
            char = self._char if self._checked else ' '
            if not self._enabled:
                try:
                    self._win.addstr(0, 0, '[ ] ', self._bracket_color)
                    self._win.addstr(self._caption, self._bracket_color)
                except curses.error:
                    pass
            elif self._focused:
                if self._highlight_all:
                    try:
                        self._win.addstr(0, 0,
                                         '[' + char + '] ' + self._caption,
                                         self._color_focused)
                    except curses.error:
                        pass
                else:
                    try:
                        self._win.addstr(0, 0, '[', self._bracket_color)
                        self._win.addstr(char, self._color_focused)
                        self._win.addstr('] ', self._bracket_color)
                        self._win.addstr(self._caption, self._color)
                    except curses.error:
                        pass
            else:
                try:
                    self._win.addstr(0, 0, '[', self._bracket_color)
                    self._win.addstr(char, self._color)
                    self._win.addstr('] ', self._bracket_color)
                    self._win.addstr(self._caption, self._color)
                except curses.error:
                    pass
            self._win.touchwin()
            self._win.refresh()

    def toggle_checked(self):
        self._checked = not self._checked
        self.refresh()

    def _get_metrics(self):
        ''' Calculate width and height based on caption '''
        self._height = 1
        self._width = len(self._title) + 4

    def keypress(self, char):
        if self._focused and \
                self.enabled and \
                char in (
                    ord(' '),
                    curses.KEY_ENTER,
                    ord('\n'),
                    ord('\r')
                ):
            self.checked = not self._checked
            if self._checked and \
                    self._callback_function is not None:
                self._callback_function()
            return False
        return True


class SimpleCursesPushButton(SimpleCursesWidget):

    def __init__(self,
                 Y, X, caption,
                 color_focused,
                 color,
                 bracket_color,
                 constant_width=0,
                 parent=None,
                 callback_function=None):
        '''Initialize the wizard.

        Parameters
        ----------
        Y, X
            Y, X position of wizard in its parent (int)
        caption
            The caption of the wizard (string).
        color_focused
            Focused button caption color (curses.color_pair)
        color
            Normal button caption color (curses.color_pair)
        bracket_color
            The color to use for the surrounding brackets
        focused
            True if wizard has focus (boolean)
        constant_width
            if > 0 make the widget this wide (int)
            May have to adjust the caption
        parent
            The widget's parent window
        callback_function
            The function to call when the button
            is "clicked". Default is None
        '''

        self._Y = Y
        self._X = X
        self._caption = caption
        self._color_focused = color_focused
        self._color = color
        self._constant_width = constant_width
        self._bracket_color = bracket_color
        if 0 < self._constant_width < 6:
            raise ValueError('constant_width must be at least 6')
        self._callback_function = callback_function
        self.resize()

    @property
    def constant_width(self):
        return self.__constant_width

    @constant_width.setter
    def constant_width(self, value):
        raise ValueError('parameter is read only')

    @property
    def X(self):
        return self._X

    @X.setter
    def X(self, value):
        # logger.info('new X = {}'.format(value))
        if value != self._X:
            self._X = value
            self._win = curses.newwin(1, self._width, self._Y, self._X)

    def resize(self):
        old_width = self._width
        self._display_caption = self._caption
        if self._constant_width == 0:
            self._width = len(self._caption) + 4
        else:
            self._width = self._constant_width
            if len(self._caption) + 4 > self._width:
                self._display_caption = self._caption[:self._width - 4]

        if self._width != old_width:
            if self._win:
                del self._win
            self._win = None
            self._win = curses.newwin(1, self._width, self._Y, self._X)

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X
        if self._win:
            self._win.mvwin(self._Y, self._X)

    def show(self, parent=None):
        '''Put the widget on the screen'''
        if self._win:
            self._win.bkgdset(' ', self._color)
            self._win.erase()
            self._win.touchwin()
            self._win.refresh()
            self.refresh()
            self._showed = True

    def refresh(self):
        '''Refresh the widget's content'''
        if self._win:
            if self._enabled:
                self._win.addstr(0, 0, '[', self._bracket_color)
                if self._focused:
                    col = self._color_focused
                else:
                    col = self._color
                self._win.addstr(' ' + self._display_caption + ' ', col)
                try:
                    self._win.addstr(']', self._bracket_color)
                except:
                    pass
            else:
                self._win.addstr(0, 0, '[', self._bracket_color)
                self._win.addstr(' ' + self._display_caption + ' ', self._bracket_color)
                try:
                    self._win.addstr(']', self._bracket_color)
                except:
                    pass

            self._win.touchwin()
            self._win.refresh()

    def keypress(self, char):
        if char in (ord(' '), ord('\n'),
                    ord('\r'), curses.KEY_ENTER) and \
                self._focused:
            if self._callback_function:
                self._callback_function(self._parent, w_id=None)
                return True
        return False


class SimpleCursesHorizontalPushButtons(object):
    '''A helper class to create horizontally
    spaced curses push buttons.

    After its creation, use show() to display them.
    Access to individual button is through <class>.buttons
    '''
    _X = _width = 0
    _parent = None
    _left_or_right_margin = 2

    def __init__(self, Y, captions,
                 color_focused, color,
                 bracket_color, constant_width=0,
                 parent = None,
                 focused=0,
                 left_or_right_margin = 2):
        '''Initialize the wizard.

        Parameters
        ----------
        Y
            Y position of wizard in its parent (int)
        captions
            The caption of the buttons contained within
            the widget (list or tuple).
        color_focused
            Focused button caption color (curses.color_pair)
        color
            Normal button caption color (curses.color_pair)
        bracket_color
            The color to use for the surrounding brackets
        focused
            True if wizard has focus (boolean)
        constant_width
            if > 0 make the widget this wide (int)
            May have to adjust the caption
        parent
            The widget's parent window (curses window)
        focused
            The id of the button which will have the focus
            the first time the widget is displayed. Default
            value is 0 (i.e. the first button). Set it to -1
            to disable it, i part of other widget. (int)
        '''

        self._buttons = []
        for n in captions:
            self._buttons.append(SimpleCursesPushButton(
                Y=Y, X=0,
                caption=n,
                color_focused=color_focused, color=color,
                bracket_color=bracket_color,
                constant_width=constant_width,
                parent=parent))
            self._width += self.buttons[-1].width + 2
        self._width -= 2
        for n in self._buttons:
            n.window.bkgdset(' ', n.color)
            n.window.erase()
            n.window.touchwin()
        self._Y = Y
        self._left_or_right_margin = left_or_right_margin
        if -1 < focused < len(self._buttons):
            ''' use _focused so that we don't refresh '''
            self._buttons[focused]._focused = True
        self._parent = parent

    def move(self, newY, newX=0):
        self._Y = newY
        for n in self._buttons:
            n.Y = newY

    def show(self, parent=None, orientation='center', show=True):
        '''Display the widget

        Parameters
        ==========
        parent
            The widget's parent
        orientation
            Can be 'center' (default), 'left' or 'right'.
            <class>.parent must be already set (either
            during creation or through property assignment.
        show
            If True, the widget is displayed at its new position.
            Never explicitly set it to False;
            use calculate_buttons_position() instead.
        '''
        if parent:
            self._parent = parent
        if self._parent:
            Y, X = self._parent.getmaxyx()
            offY, offX = self._parent.getbegyx()
            if orientation == 'left':
                self._X = offX + self._left_or_right_margin
            elif orientation == 'right':
                self._X = X - self._left_or_right_margin - self._width
            else:
                self._X = offX + int((X - self._width) / 2)
            ''' place widgets '''
            X = self._X
            Y = self._Y + offY
            for n in self._buttons:
                n.mvwin(Y, X, show)
                X += n.width + 2

    def calculate_buttons_position(self, parent=None, orientation='center'):
        '''Calculate buttons position but do not display them.
        It will call show() with show=False'''
        self.show(parent, orientation, show=False)

    @property
    def buttons(self):
        '''The list of buttons within the widget.
        This is the way to get access to an individual
        button and use its functionality.
        '''
        return self._buttons

    @buttons.setter
    def buttons(self, value):
        raise ValueError('parameter is read only')

    @property
    def parent(self):
        '''The parent window of the widget.
        This is a window, not another widget.
        If not set (or invalid), the buttons will not be
        visible even if show() is called.
        '''
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value
        if self._buttons:
            for n in self._buttons:
                n.parent = value


class SimpleCursesLineEdit(object):
    ''' Class to insert one line of text
    Python 3 supports all chars
    Python 2 supports ascii only

    '''
    string = ''
    _string = ''
    _displayed_string = ''

    ''' windows '''
    _parent_win = None
    _caption_win = None             # contains box and caption
    _edit_win = None                # contains the "input box"
    _use_paste_mode = False         # paste mode is off by default
    _paste_mode = False             # enables direct insersion of ? and \
    _disable_paste_mode = False     # if True, disable paste mode
    _paste_mode_always_on = False   # set paste mode and never disable it

    ''' Default value for string length '''
    _max_chars_to_display = 0

    ''' Cursor position within _max_chars_to_display '''
    _curs_pos = 0
    _disp_curs_pos = 0
    ''' First char of sting to display '''
    _first = 0
    _last = 0

    ''' init values '''
    y = x = 0
    _caption = 'Insert string'
    _disp_caption = ' Insert string: '
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
    _string_changed_handler = None
    _ungetch_unbound_keys = False

    _focused = True
    _enabled = True
    _showed = False

    ''' if width < 1, auto_width gets this value,
        so that width gets parent.width - auto_width '''
    _auto_width = 1

    ''' string to redisplay after exiting help '''
    _restore_data = []

    log = None
    _log_file = ''

    _reset_position = False

    _add_to_end = True
    _cjk = False

    _word_delim = (' ', '-', '_', '+', '=',
                   '~', '~', '!', '@', '#',
                   '$', '%', '^', '&', '*', '(', ')',
                   '[', ']', '{', '}', '|', '\\', '/',
                   )

    ''' Set to True to restringt accepted characters to ASCII only '''
    _pure_ascii = False

    ''' True if backlash has been pressed '''
    _backslash_pressed = False

    ''' Behaviour of ? key regarding \
        If True, display ? (\? to display help)
        If False, display help '''
    _show_help_with_backslash_pressed = False

    _mode_changed = None

    _global_functions = {}
    _local_functions = {}

    _chars_to_accept = []

    _visible = True

    def __init__(self, parent, width, begin_y, begin_x, **kwargs):

        self._parent_win = parent
        self.width = width
        self._height = 3
        self.y = begin_y
        self.x = begin_x

        self._search_history_file = ''
        self._locked = False
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
                    ''' string on editing line '''
                    self._caption = value
                elif key == 'title':
                    ''' string on box '''
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
                    self._ungetch_unbound_keys = value
                elif key == 'log_file':
                    self._log_file = value
                    self.log = self._log
                elif key == 'chars_to_accept':
                    self._chars_to_accept = value
                elif key == 'key_up_function_handler':
                    ''' callback function for KEY_UP '''
                    self._key_up_function_handler = value
                elif key == 'key_down_function_handler':
                    ''' callback function for KEY_DOWN '''
                    self._key_down_function_handler = value
                elif key == 'key_pgup_function_handler':
                    ''' callback function for KEY_PPAGE '''
                    self._key_pgup_function_handler = value
                elif key == 'key_pgdown_function_handler':
                    ''' callback function for KEY_NPAGE '''
                    self._key_pgdown_function_handler = value
                elif key == 'key_tab_function_handler':
                    ''' callback function for TAB '''
                    self._key_tab_function_handler = value
                elif key == 'key_stab_function_handler':
                    ''' callback function for KEY_STAB '''
                    self._key_stab_function_handler = value
                elif key == 'string_changed_handler':
                    ''' callback function for string change '''
                    self._string_changed_handler = value
                elif key == 'paste_mode_always_on':
                    ''' set paste mode and never disable it '''
                    self._paste_mode_always_on = True
                    self._paste_mode = True
                elif key == 'search_history_file':
                    self._search_history_file = value
                elif key == 'is_locked':
                    self._locked = value

        if self._has_history:
            self._input_history = SimpleCursesLineEditHistory(
                    self._search_history_file,
                    self._locked
                    )
        self._calculate_window_metrics()

    def save_search_history(self):
        if self._has_history:
            self._input_history.save_search_history()

    @property
    def visible(self):
        '''Returns if the widget is visible'''
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = value

    @property
    def chars_to_accept(self):
        '''
        Returns the widget's accepted characters
        If [], all characters are accepted
        '''
        return self._chars_to_accept

    @chars_to_accept.setter
    def chars_to_accept(self, value):
        self._chars_to_accept = value

    @property
    def focused(self):
        '''Returns if the widget has focus'''
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value
        if self._showed:
            self.refresh()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, val):
        self._enabled = val
        if self._showed:
            self.refresh()

    @property
    def backslash_pressed(self):
        return self._backslash_pressed

    @backslash_pressed.setter
    def backslash_pressed(self, val):
        self._backslash_pressed = val

    @property
    def paste_mode(self):
        return self._paste_mode

    @paste_mode.setter
    def paste_mode(self, val):
        self._paste_mode = val

    @property
    def use_paste_mode(self):
        return self._use_paste_mode

    @use_paste_mode.setter
    def use_paste_mode(self, val):
        self._use_paste_mode = val

    @property
    def width(self):
        if self._auto_width < 1:
            h, self._width = self._parent_win.getmaxyx()
            self._width += self._auto_width
            self._width -= self.x
        return self._width

    @width.setter
    def width(self, val):
        if val < 1:
            h, self._width = self._parent_win.getmaxyx()
            self._width -= val
            self._auto_width = val
        else:
            self._width = val
            self._auto_width = val

    @property
    def string(self):
        return self._string

    @string.setter
    def string(self, val):
        self._string = val
        self._is_cjk()
        self._go_to_end()

    @property
    def show_help_with_backslash_pressed(self):
        return self._show_help_with_backslash_pressed

    @show_help_with_backslash_pressed.setter
    def show_help_with_backslash_pressed(self, val):
        self._show_help_with_backslash_pressed = val

    @property
    def pure_ascii(self):
        return self.pure_ascii

    @pure_ascii.setter
    def pure_ascii(self, val):
        self._pure_ascii = val

    def _is_cjk(self):
        ''' Check if string contains CJK characters.
            If string is empty reset history index '''
        old_cjk = self._cjk
        if len(self.string) == cjklen(self.string):
            self._cjk = False
        else:
            self._cjk = True
        if self.string == '' and self._has_history:
            self._input_history.reset_index()
        if logger.isEnabledFor(logging.DEBUG) and self._cjk != old_cjk:
                logger.debug('=== CJK editing is {} ==='.format('ON' if self._cjk else 'OFF'))

    def keep_restore_data(self):
        ''' Keep a copy of current editor state
            so that it can be restored later. '''
        self._restore_data = [
            self.string,
            self._displayed_string,
            self._curs_pos,
            self._disp_curs_pos,
            self._first
        ]

    def getmaxyx(self):
        return self._caption_win.getmaxyx()

    def set_local_functions(self, local_functions):
        self._local_functions = local_functions

    def set_global_functions(self, global_functions):
        self._global_functions = {}
        if global_functions is not None:
            self._global_functions = dict(global_functions)
            if ord('t') in self._global_functions.keys():
                del self._global_functions[ord('t')]
            # if 'T' in self._global_functions.keys():
            #     del self._global_functions['T']

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
        # width = len(self._disp_caption) + self._max_chars_to_display + 4
        # logger.error('DE 0 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        self._max_chars_to_display = self.width - len(self._disp_caption) - 4
        # logger.error('DE 1 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        if self._boxed:
            self._height = 3
        else:
            self._height = 1
            self._max_chars_to_display += 2
            if not self.bracket:
                self._max_chars_to_display += 1
        if self.log is not None:
            self.log('string_len = {}\n'.format(self._max_chars_to_display))
        # logger.error('DE 2 width = {0}, max_chars_to_display = {1}'.format(width, self._max_chars_to_display))
        return

    def _prepare_to_show(self):
        self._calculate_window_metrics()
        self._caption_win = curses.newwin(
            self._height, self.width,
            self.y, self.x
        )
        maxY, maxX = self._caption_win.getmaxyx()
        if self._boxed:
            self._edit_win = curses.newwin(
                1, maxX - len(self._disp_caption) - 2,
                self.y + 1, self.x + len(self._disp_caption) + 1
            )
            self._caption_win.addstr(
                1, 1, self._disp_caption, self.caption_color
            )
        else:
            self._caption_win.addstr(
                0, 0, self._disp_caption, self.caption_color
            )
            if self.bracket:
                self._edit_win = curses.newwin(
                    1, maxX - len(self._disp_caption) - 1,
                    self.y, self.x + len(self._disp_caption)
                )
                try:
                    ''' printing at the end of the window, do not break... '''
                    self._caption_win.addstr(0, maxX - 1, ']', self.caption_color)
                except:
                    pass
            else:
                self._edit_win = curses.newwin(
                    1, maxX - len(self._disp_caption),
                    self.y, self.x + len(self._disp_caption)
                )

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

        ''' opening '''
        # logger.error('opening = {}'.format(opening))
        if opening:
            if self._restore_data:
                self._string = self._restore_data[0]
                self._displayed_string = self._restore_data[1]
                self._curs_pos = self._restore_data[2]
                self._disp_curs_pos = self._restore_data[3]
                self._first = self._restore_data[4]
                self._restore_data = []
            else:
                self.string = self._displayed_string = ''
                self._curs_pos = self._disp_curs_pos = self._first = 0
        # logger.error('string = "{}"'.format(self._string))
        # logger.error('displayed string = "{}"'.format(self._displayed_string))
        if self._enabled:
            self._edit_win.addstr(0, 0, self._displayed_string, active_edit_color)

        ''' reset position '''
        if self._reset_position:
            self._reset_position = False
            self._go_to_end()

        if self.log is not None:
            self.log('first={0}, curs={1}, dcurs={2}\n'.format(
                self._first, self._curs_pos, self._disp_curs_pos))
            self.log('     full string: "{}"\n'.format(self.string))
            self.log('displayed string: "{}"\n'.format(self._displayed_string))

        if self.focused:
            ''' enable this to get info on function '''
            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('refreshEditWindow:\n  first={0}, curs={1}, dcurs={2}, max={3}\n  len={4}, cjklen={5}\n  string="{6}"\n  len={7}, cjklen={8}\n  disstr="{9}"'.format(self._first, self._curs_pos, self._disp_curs_pos, self._max_chars_to_display, len(self.string), cjklen(self.string), self.string, len(self._displayed_string), cjklen(self._displayed_string), self._displayed_string))
            self._edit_win.chgat(0, self._disp_curs_pos, 1, self.cursor_color)

        self._edit_win.refresh()
        self._showed = True

    def move(self, parent, newY, newX, opening=False, update=True):
        if update:
            kwargs={'new_y': newY, 'new_x': newX, 'opening': opening}
            self.show(parent, **kwargs)
        else:
            self._parent_win = parent
            self.y = newY
            self.x = newX

    def refresh(self):
        self.show(self._parent_win, opening=False)

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
        if not self._visible:
            self._caption_win.refresh()
            self._edit_win.refresh()
            return
        if self._boxed:
            self._caption_win.box()
            if self._disp_title:
                self._title_win.addstr(
                    0, 1, self._disp_title, self.title_color
                )
        self._caption_win.refresh()
        self.refreshEditWindow(opening)
        self._showed = True

    def _go_to_start(self):
        self._first = self._curs_pos = self._disp_curs_pos = 0
        self._displayed_string = self.string[:self._max_chars_to_display]
        if self._cjk:
            end = len(self._displayed_string)
            while cjklen(self._displayed_string) > self._max_chars_to_display:
                end -= 1
                self._displayed_string = self.string[:end]

    def _go_to_end(self):
        self._first = len(self.string[:-self._max_chars_to_display])
        self._displayed_string = self.string[self._first:]
        if self._cjk:
            while cjklen(self._displayed_string) > self._max_chars_to_display:
                self._first += 1
                self._displayed_string = self.string[self._first:]
            self._curs_pos = len(self._displayed_string)
            self._disp_curs_pos = cjklen(self._displayed_string)
        else:
            self._curs_pos = self._disp_curs_pos = len(self._displayed_string)

    def _at_end_of_sting(self):
        if self._at_end_of_displayed_sting():
            if self.string.endswith(self._displayed_string):
                return True
            return False
        else:
            return False

    def _at_end_of_displayed_sting(self):
        if self._disp_curs_pos >= cjklen(self._displayed_string):
            return True
        return False

    def _at_last_char_of_string(self):
        if self._at_last_char_of_displayed_string():
            if self.string.endswith(self._displayed_string):
                return True
            return False
        else:
            return False

    def _at_last_char_of_displayed_string(self):
        if self._disp_curs_pos == cjklen(self._displayed_string):
            return True
        return False

    def _delete_char(self):
        if self.string and not self._at_end_of_sting():
            self._string = self._string[:self._first + self._curs_pos] + self._string[self._first + self._curs_pos+1:]
            if self._first + self._max_chars_to_display > cjklen(self.string):
                if self._first > 0:
                    self._first -= 1
                    if self._curs_pos < self._max_chars_to_display:
                        self._curs_pos += 1
            if self._cjk:
                self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
            else:
                self._disp_curs_pos = self._curs_pos
            self._displayed_string = self.string[self._first:self._first+self._max_chars_to_display]
            while cjklen(self._displayed_string) > self._max_chars_to_display:
                self._displayed_string = self._displayed_string[:-1]
            self._is_cjk()

    def _backspace_char(self):
        if self.string:
            if self._first + self._curs_pos > 0:
                if self._curs_pos == 0:
                    ''' remove non visible char from the left of the string '''
                    self.string = self.string[:self._first-1] + self.string[self._first:]
                    self._first -= 1
                    self._curs_pos = 0
                    self._is_cjk()
                    return

                str_len = cjklen(self.string)
                if self._cjk:
                    if self._at_end_of_sting():
                        if len(self.string) == 1:
                            self.string = ''
                            self._displayed_string = ''
                            self._first = 0
                            self._curs_pos = 0
                            if self._cjk:
                                self._cjk = False
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug('CJK is {}'.format(self._cjk))
                        else:
                            self.string = self.string[:-1]
                            if len(self.string) <= self._max_chars_to_display:
                                self._displayed_string = self.string
                            else:
                                self._displayed_string = self._string[len(self.string) - self._max_chars_to_display:]
                            while cjklen(self._displayed_string) > self._max_chars_to_display:
                                self._displayed_string = self._displayed_string[1:]
                            self._curs_pos = len(self._displayed_string)
                            self._disp_curs_pos = cjklen(self._displayed_string)
                            self._first = len(self.string) - len(self._displayed_string)
                            if self._first < 0: self._first = 0
                    else:
                        self._curs_pos -= 1
                        curs = self._curs_pos
                        self.string = self.string[:self._first+self._curs_pos] + self.string[self._first+self._curs_pos+1:]
                        self._curs_pos = curs
                        self._displayed_string = self.string[self._first: self._first+self._max_chars_to_display]
                        while cjklen(self._displayed_string) > self._max_chars_to_display:
                            self._displayed_string = self._displayed_string[:-1]
                        self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    self._string = self._string[:self._first + self._curs_pos-1] + self._string[self._first + self._curs_pos:]
                    if str_len <= self._max_chars_to_display:
                        self._first = 0
                        if self._curs_pos > 0:
                            self._curs_pos -= 1
                    elif self._first + self._max_chars_to_display >= str_len:
                        if self._first > 0:
                            self._first -= 1
                    else:
                        if self._curs_pos > 0:
                            self._curs_pos -= 1
                    self._disp_curs_pos = self._curs_pos
                    self._displayed_string=self.string[self._first:self._first+self._max_chars_to_display]
                    self._is_cjk()

    def _previous_word(self):
        if self._first + self._curs_pos > 0:
            pos = 0
            str_len = cjklen(self.string)
            for n in range(self._first + self._curs_pos - 1, 0, -1):
                if self._string[n] in self._word_delim:
                    if n < self._first + self._curs_pos - 1:
                        pos = n
                        break
            if pos == 0:
                ''' word_delimiter not found: '''
                self._go_to_start()
                return
            else:
                ''' word delimiter found '''
                if str_len < self._max_chars_to_display or \
                        pos >= self._first:
                    ''' pos is on screen '''
                    self._curs_pos = pos - self._first + 1
                else:
                    self._first = n + 1
                    self._curs_pos = 0
                    self._displayed_string = self.string[self._first:self._first+self._max_chars_to_display]
                self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                while cjklen(self._displayed_string) > self._max_chars_to_display:
                    self._displayed_string = self._displayed_string[:-1]

    def _next_word(self):
        if self._at_end_of_sting():
            return
        if self._first + self._curs_pos + 1 >= len(self.string):
            self._go_to_end()
            return
        pos = 0
        for n in range(self._first + self._curs_pos + 1, len(self.string)):
            if self._string[n] in self._word_delim:
                pos = n
                break
        if pos >= len(self.string):
            pos = 0
        if pos > 0:
            if pos < len(self._displayed_string):
                ''' pos is on screen '''
                self._curs_pos = pos + 1 - self._first
                self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
            else:
                if pos < self._first + len(self._displayed_string):
                    ''' pos is on middle and on screen '''
                    self._curs_pos = pos - self._first + 1
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    ''' pos is off screen '''
                    self._first = 0
                    self._curs_pos = pos + 2
                    self._displayed_string = tmp = self.string[:self._curs_pos]
                    while cjklen(tmp) > self._max_chars_to_display:
                        self._first += 1
                        tmp = self._displayed_string[self._first:]
                    self._displayed_string = tmp
                    self._curs_pos = len(self._displayed_string) - 1
                    self._disp_curs_pos = cjklen(self._displayed_string[:-1])

        else:
            ''' word delimiter not found '''
            self._go_to_end()

    def _go_right(self):
        if self.string and not self._at_end_of_sting():
            if self._cjk:
                if cjklen(self.string) < self._max_chars_to_display:
                    ''' just go to next char '''
                    if self._curs_pos <= len(self.string):
                        self._curs_pos += 1
                    self._disp_curs_pos = cjklen(self.string[:self._curs_pos])
                    self._displayed_string = self.string

                else:
                    at_end_of_disp = self._at_last_char_of_displayed_string()
                    self._curs_pos += 1
                    if self._curs_pos <= len(self._displayed_string):
                        ''' just go to next char '''
                        self._disp_curs_pos = cjklen(self.string[self._first:self._first+self._curs_pos])
                    else:
                        ''' scroll one char right '''
                        self._displayed_string = self.string[self._first:self._first+len(self._displayed_string)+1]
                        while cjklen(self._displayed_string) >= self._max_chars_to_display + 1:
                            self._first += 1
                            self._displayed_string = self._displayed_string[1:]
                        self._disp_curs_pos = cjklen(self._displayed_string) - cjklen(self._displayed_string[-1])
                        if at_end_of_disp:
                            self._disp_curs_pos += cjklen(self._displayed_string[-1])
            else:
                self._to_right_simple()
            if self._curs_pos > len(self._displayed_string):
                self._curs_pos = len(self._displayed_string)

    def _to_right_simple(self):
        if len(self.string) < self._max_chars_to_display:
            self._curs_pos += 1
            if self._curs_pos > len(self.string):
                    self._curs_pos = len(self.string)
            else:
                if len(self._string) < self._first + self._curs_pos:
                    self._curs_pos = len(self._string) - self._max_chars_to_display
        else:
            if self._curs_pos == self._max_chars_to_display:
                if len(self._string) > self._first + self._curs_pos:
                    self._first += 1
            else:
                self._curs_pos += 1
        self._disp_curs_pos = self._curs_pos
        disp_string = self.string[self._first:self._first + self._max_chars_to_display]
        self._displayed_string = disp_string[:self._max_chars_to_display]

    def _go_left(self):
        if self._first + self._curs_pos > 0:
            if self._cjk:
                if self._curs_pos > 0:
                    ''' just go to previous char '''
                    self._curs_pos -= 1
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    self._first -= 1
                    self._displayed_string = self.string[self._first: self._first+self._max_chars_to_display]
                    while cjklen(self._displayed_string) > self._max_chars_to_display:
                        self._displayed_string = self._displayed_string[:-1]
            else:
                # logger.error('simple')
                self._go_left_simple()

    def _go_left_simple(self):
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
        self._disp_curs_pos = self._curs_pos
        disp_string = self.string[self._first:self._first + self._max_chars_to_display]
        self._displayed_string = disp_string[:self._max_chars_to_display]

    def _clear_to_start_of_line(self):
        if self.string:
            self.string = self._string[self._first + self._curs_pos:]
            self._go_to_start()
            self._is_cjk()

    def _clear_to_end_of_line(self):
        if self.string:
            self.string = self._string[:self._first + self._curs_pos]
            self._go_to_end()
            self._is_cjk()

    def _can_show_help(self):
        ''' return not xor of two values
                self._backslash_pressed,
                self._show_help_with_backslash_pressed'''
        if self._paste_mode:
            return False
        return not (
            (self._backslash_pressed and
             not self._show_help_with_backslash_pressed)
            or (not self._backslash_pressed
                and self._show_help_with_backslash_pressed))

    def keypress(self, win, char):
        '''
         returns:
            2: display help
            1: get next char
            0: exit edit mode, string is valid
           -1: cancel
        '''
        #self._log_file='/home/spiros/edit.log'
        #self._log_file='C:\\Users\\spiros\\edit.log'
        #self.log = self._log
        if not self._focused:
            return 1
        if self.log is not None:
            self.log('char = {}\n'.format(char))

        if char in self._local_functions.keys():
            self._backslash_pressed = False
            if not self._paste_mode_always_on:
                self._paste_mode = False
                if self._mode_changed:
                    self._mode_changed()
            self._local_functions[char]()

        if char in self._global_functions.keys() and \
                self._backslash_pressed:
            ''' toggle paste mode '''
            self._backslash_pressed = False
            if not self._paste_mode_always_on:
                self._paste_mode = False
                if self._mode_changed:
                    self._mode_changed()
            self._global_functions[char]()
            return 1

        if platform.startswith('win'):
            if char == 420:
                ''' A-D, clear to end of line '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_end_of_line()
                self.refreshEditWindow()
                if self._string_changed_handler:
                    self._string_changed_handler()
                if self._use_paste_mode and self._paste_mode:
                    self._paste_mode = self._disable_paste_mode = False
                    if self._mode_changed:
                        self._mode_changed()
                return 1
            elif char == 422:
                ''' A-F, move to next word '''
                if self.string:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('action: next-word')
                    self._next_word()
                    self.refreshEditWindow()

                    if not self._paste_mode_always_on:
                        if self._use_paste_mode and self._paste_mode:
                            self._paste_mode = self._disable_paste_mode = False
                            if self._mode_changed:
                                self._mode_changed()
                return 1
            elif char == 418:
                ''' A-B, move to previous word '''
                if self.string:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('action: previous-word')
                    self._previous_word()
                    if not self._paste_mode_always_on:
                        if self._use_paste_mode and self._paste_mode:
                            self._paste_mode = self._disable_paste_mode = False
                            if self._mode_changed:
                                self._mode_changed()
                return 1

        if char == 92 and not self._backslash_pressed and not self._paste_mode:
            self._backslash_pressed = True
            if self._mode_changed:
                self._mode_changed()
            return 1

        elif char in (ord('?'), ) and self._can_show_help():
            ''' display help '''
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: help')
            self.keep_restore_data()
            self._backslash_pressed = False
            if self._mode_changed:
                self._mode_changed()
            if not self._paste_mode_always_on:
                if self._use_paste_mode and self._paste_mode:
                    self._paste_mode = self._disable_paste_mode = False
                    if self._mode_changed:
                        self._mode_changed()
            return 2


        elif char == curses.ascii.CAN and \
                self._has_history:
            self._backslash_pressed = False
            self._input_history.remove_from_history(self._string)
            self._string = self._input_history.return_history(0, '')
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: CLEAR HISTORY')
            self._go_to_end()
            if not self._paste_mode_always_on:
                if self._use_paste_mode and self._paste_mode:
                    self._paste_mode = self._disable_paste_mode = False
                    if self._mode_changed:
                        self._mode_changed()

        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            ''' ENTER '''
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: enter')
            if self._has_history:
                self._input_history.add_to_history(self._string)
            if not self._paste_mode_always_on:
                if self._use_paste_mode and self._paste_mode:
                    self._paste_mode = self._disable_paste_mode = False
                    if self._mode_changed:
                        self._mode_changed()
            return 0

        elif char in (curses.KEY_EXIT, 27):
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: ESCAPE')
            self._edit_win.nodelay(True)
            char = self._edit_win.getch()
            if self.log is not None:
                self.log('   *** char = {}\n'.format(char))
            self._edit_win.nodelay(False)
            if not self._paste_mode_always_on:
                if self._use_paste_mode and self._paste_mode:
                    self._disable_paste_mode = True
            if char == -1:
                ''' ESCAPE '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: Cancel')
                self._string = ''
                self._curs_pos = 0
                if self._input_history:
                    self._input_history.reset_index()
                if not self._paste_mode_always_on:
                    if self._use_paste_mode and self._paste_mode:
                        self._paste_mode = self._disable_paste_mode = False
                        if self._mode_changed:
                            self._mode_changed()
                return -1
            else:
                if self.log is not None:
                    self.log('   *** char = {}\n'.format(char))
                if char in (ord('d'), ):
                    ''' A-D, clear to end of line '''
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: clear-to-end')
                        self._clear_to_end_of_line()
                        if self._string_changed_handler:
                            self._string_changed_handler()
                elif char in (ord('f'), ):
                    ''' A-F, move to next word '''
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: next-word')
                        self._next_word()
                elif char in (ord('b'), ):
                    ''' A-B, move to previous word '''
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: previous-word')
                        self._previous_word()
                else:
                    if not self._paste_mode_always_on:
                        if self._use_paste_mode and self._paste_mode:
                            self._paste_mode = self._disable_paste_mode = False
                            if self._mode_changed:
                                self._mode_changed()
                    return 1

        elif char in (curses.KEY_RIGHT, ):
            ''' KEY_RIGHT '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: RIGHT')
            self._go_right()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_LEFT, ):
            ''' KEY_LEFT '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: LEFT')
                self._go_left()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_HOME, curses.ascii.SOH):
            ''' KEY_HOME, ^A '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: HOME')
                self._go_to_start()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_END, curses.ascii.ENQ):
            ''' KEY_END, ^E '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: END')
                self._go_to_end()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.ascii.ETB, ):
            ''' ^W, clear to start of line '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_start_of_line()
                if self._string_changed_handler:
                    self._string_changed_handler()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.ascii.VT, ):
            ''' Ctrl-K - clear to end of line '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_end_of_line()
                if self._string_changed_handler:
                    self._string_changed_handler()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.ascii.NAK, ):
            ''' ^U, clear line '''
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: clear')
            self.string = self._displayed_string = ''
            self._first = self._curs_pos = self._disp_curs_pos = 0
            self._is_cjk()
            if self._string_changed_handler:
                self._string_changed_handler()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_DC, curses.ascii.EOT):
            ''' DEL key, ^D '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: delete')
                self._delete_char()
                if self._string_changed_handler:
                    self._string_changed_handler()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_BACKSPACE, curses.ascii.BS, 127):
            ''' KEY_BACKSPACE '''
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: backspace')
                self._backspace_char()
                if self._string_changed_handler:
                    self._string_changed_handler()
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_UP, curses.ascii.DLE):
            ''' KEY_UP, ^N '''
            self._backslash_pressed = False
            if self._key_up_function_handler is not None:
                try:
                    self._key_up_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_DOWN, curses.ascii.SO):
            ''' KEY_DOWN, ^P '''
            self._backslash_pressed = False
            if self._key_down_function_handler is not None:
                try:
                    self._key_down_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_NPAGE, ):
            ''' PgDn '''
            self._backslash_pressed = False
            if self._key_pgdown_function_handler is not None:
                try:
                    self._key_pgdown_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_PPAGE, ):
            ''' PgUp '''
            self._backslash_pressed = False
            if self._key_pgup_function_handler is not None:
                try:
                    self._key_pgup_function_handler()
                except:
                    pass
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (9, ):
            ''' TAB '''
            self._backslash_pressed = False
            if self._key_tab_function_handler is not None:
                try:
                    self._key_tab_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif char in (curses.KEY_BTAB, ):
            ''' Shift-TAB '''
            self._backslash_pressed = False
            if self._key_stab_function_handler is not None:
                try:
                    self._key_stab_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)
            if self._use_paste_mode and self._paste_mode:
                self._disable_paste_mode = True

        elif 0 <= char <= 31:
            ''' do not accept any other control characters '''
            self._backslash_pressed = False

        elif char == ord('p') and self._backslash_pressed \
                and self._use_paste_mode:
            ''' toggle paste mode '''
            self._backslash_pressed = False
            self._paste_mode = True
            self._disable_paste_mode = False
            if self._mode_changed:
                self._mode_changed()

        else:
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: add-character')
            if self.log is not None:
                self.log('====================\n')
            if version_info < (3, 0) or (self._pure_ascii and not platform.startswith('win')):
                if 32 <= char < 127:
                    ''' accept only ascii characters '''
                    if self._chars_to_accept:
                        if chr(char) not in self._chars_to_accept:
                            return 1
                    if len(self._string) == self._first + self._curs_pos:
                        self._string += chr(char)
                        self._add_to_end = True
                        self._curs_pos += 1
                        self._displayed_string = self._string[self._first:self._first+self._curs_pos]
                    else:
                        self._string = self._string[:self._first + self._curs_pos] + chr(char) + self._string[self._first + self._curs_pos:]
                        self._add_to_end = False
                        self._curs_pos += 1
                        self._disp_curs_pos = self._curs_pos
                        self._displayed_string = self.string[self._first:self._first+self._max_chars_to_display]
            else:
                if platform.startswith('win'):
                    char = chr(char)
                else:
                    char = self._get_char(win, char)
                if char is None:
                    return 1
                if self._pure_ascii:
                    if ord(char) > 127:
                        return 1
                #if len(self._string) == self._first + self._curs_pos:
                if self._chars_to_accept:
                    if char not in self._chars_to_accept:
                        return 1
                if self._at_end_of_sting():
                    self._string += char
                    self._add_to_end = True
                    self._curs_pos += 1
                    self._displayed_string = self._string[self._first:self._first+self._curs_pos]
                else:
                    self._string = self._string[:self._first + self._curs_pos] + char + self._string[self._first + self._curs_pos:]
                    self._curs_pos += 1
                    self._add_to_end = False
                    self._displayed_string = self.string[self._first:self._first+self._max_chars_to_display]
            if self._add_to_end:
                ''' adding to end of string '''
                while cjklen(self._displayed_string) > self._max_chars_to_display:
                    self._displayed_string = self._displayed_string[1:]
                    self._first += 1
                    self._curs_pos -= 1
                if self._cjk:
                    self._disp_curs_pos = cjklen(self._displayed_string)
                else:
                    self._disp_curs_pos = self._curs_pos
            else:
                ''' adding to middle of string '''
                while cjklen(self._displayed_string) > self._max_chars_to_display:
                    self._displayed_string = self._displayed_string[:-1]
                if self._cjk:
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    self._disp_curs_pos = self._curs_pos
            if self._string_changed_handler:
                self._string_changed_handler()
        self.refreshEditWindow()
        # logger.error('self._disable_paste_mode = {}'.format(self._disable_paste_mode))
        if not self._paste_mode_always_on:
            if self._disable_paste_mode:
                self._paste_mode = self._disable_paste_mode = False
            if self._mode_changed:
                self._mode_changed()
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
            ''' 1 byte '''
            bytes.append(char)
        #elif 194 <= char <= 223:
        elif 192 <= char <= 223:
            ''' 2 bytes '''
            bytes.append(char)
            bytes.append(get_check_next_byte())
        elif 224 <= char <= 239:
            ''' 3 bytes '''
            bytes.append(char)
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
        elif 240 <= char <= 244:
            ''' 4 bytes '''
            bytes.append(char)
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
            bytes.append(get_check_next_byte())
        ''' no zero byte allowed '''
        while 0 in bytes:
            bytes.remove(0)
        if version_info < (3, 0):
            out = ''.join([chr(b) for b in bytes])
        else:
            buf = bytearray(bytes)
            out = self._decode_string(buf)
            if out:
                if PY3:
                    if is_wide(out) and not self._cjk:
                        self._cjk = True
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('=== CJK editing is ON ===')
            else:
                out = None
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
        with open(self._log_file, 'a', encoding='utf-8') as log_file:
            log_file.write(msg)

    def run(self):
        self._edit_win.nodelay(False)
        self._edit_win.keypad(True)
        ''' make sure we don't get into an infinite loop '''
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

    def __init__(self, history_file=None, history_file_is_locked=None):
        self._history = ['']
        self._active_history_index = 0
        self._history_file = history_file
        if self._history_file is None:
            self._read_history_file()
        self._history_file_is_locked = False
        if history_file_is_locked is not None:
            self._history_file_is_locked = history_file_is_locked
        if self._history_file:
            self._read_history_file()
        self._dirty = False

    def _read_history_file(self, a_file=None):
        if a_file is not None:
            file_to_read = a_file
        else:
            file_to_read = self._history_file
        try:
            self._histor = ['']
            with open(file_to_read, 'r', encoding='utf-8') as f:
                line = f.read().strip()
            self._history.extend(line.split())
            self._active_history_index = len(self._history)
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('search history failed to be read from "{}"'.format(basename(file_to_read)))

    def save_search_history(self, a_file=None):
        if self._history_file_is_locked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('not saving search history; sesson is locked!')
            return False
        if self._history and self._dirty:
            if a_file is not None:
                file_to_write = a_file
            else:
                file_to_write = self._history_file
            if len(self._history) > 20:
                history = self._history[len(self._history)-20:]
            else:
                history = self._history[:]
            try:
                with open(file_to_write, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(history) + '\n')
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('search history saved to "{}"'.format(basename(file_to_write)))
                return True
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('search history failed to be saved to "{}"'.format(basename(file_to_write)))
                return False
        return False

    def add_to_history(self, a_string):
        if a_string:
            if self._history:
                if self._history[-1].lower() != a_string.lower():
                    if len(self._history) > 1:
                        i = [(x, y) for x, y in \
                                enumerate(self._history) \
                                if y.lower() == a_string.lower()
                             ]
                        if i:
                            self._history.pop(i[0][0])
                else:
                    return
            self._history.append(a_string)
            self._dirty = True
            self._active_history_index = len(self._history)

    def remove_from_history(self, a_string):
        if a_string:
            i = [(x, y) for x, y in \
                    enumerate(self._history) \
                    if y.lower() == a_string.lower()
                 ]
            if i:
                self._history.pop(i[0][0])
                self._dirty = True
                if self._history:
                    if self._active_history_index == len(self._history):
                        self._active_history_index -= 1
                else:
                    self._active_history_index = -1

    def return_history(self, direction, current_string):
        if self._history:
            self._active_history_index += direction
            if self._active_history_index <= -1:
                self._active_history_index = len(self._history) - 1
            elif self._active_history_index >= len(self._history):
                self._active_history_index = 0
            ret = self._history[self._active_history_index]
            if ret and current_string:
                if ret.lower() == current_string.lower():
                    return self.return_history(direction, current_string)
            return ret
        return ''

    def reset_index(self):
        self._active_history_index = 0


class SimpleCursesBoolean(SimpleCursesCounter):
    ''' A class to provide a Boolean value

        Parameters
        ==========
        Y, X, window
            Coordinates and parent window
        value
            the value, either Tru of False (default)
        color
            text color
        color_focused
            counter color when enabled and focused
        color_not_focused
            counter color when enabled but not focused
        color_disabled
            counter color when disabled
        full_slection
            if not None, it should be a tuple:
                (go left from self._X, numbder of chars to print)
            draw selection cursor as a full line
    '''

    def __init__(
        self, Y, X, window,
        color, color_focused,
        color_not_focused,
        color_disabled,
        string='{0}', value=False,
        full_selection=None
    ):
        self._Y = Y
        self._X = X
        self._win = self._parent = window
        self._value = value
        self.string = string
        self._color = color
        self._color_focused = color_focused
        self._color_not_focused = color_not_focused
        self._color_disabled = color_disabled
        self._full_selection = full_selection

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, val):
        self._value = val

    def _print_full_line(self, col):
        tmp = self._full_selection[0] * ' ' + self._prefix + str(self._value) + self._suffix
        self._win.addstr(
            self._Y,
            self._X - self._full_selection[0],
            tmp.ljust(self._full_selection[1]),
            col
        )

    def show(self, window=None):
        if window:
            self._win = self._parent = window
        if self._enabled:
            if self._focused:
                col = self._color_focused
            else:
                col = self._color_not_focused
        else:
            col = self._color_disabled
        if self._full_selection and self._enabled and self._focused:
            self._print_full_line(col)
        else:
            if self._full_selection:
                self._win.addstr(
                    self._Y,
                    self._X - self._full_selection[0],
                    (self._full_selection[1] ) * ' ',
                    self._color
                )
            self._win.move(self._Y, self._X)
            if self._prefix:
                self._win.addstr( self._prefix, self._color)
            self._win.addstr(str(self._value).ljust(5), col)
            if self._suffix:
                self._win.addstr(self._suffix, self._color)
            ''' overwrite last self._len characters '''
            self._win.addstr(' ' * 2, self._color)
        self._showed = True

    def keypress(self, char):
        ''' SimpleCursesBoolean keypress

            Returns
            -------
               -1 - Cancel
                0   Value changed
                1 - Continue
                2 - Display help
        '''
        if (not self._focused) or (not self._enabled):
            return 1

        if char in (
            curses.KEY_EXIT, ord('q'), 27,
        ):
            return -1

        elif char == ord('?'):
            return 2

        elif char in (ord(' '),
                      ord('\n'), ord('\r'),
                      curses.KEY_ENTER,
                      ord('h'),
                      curses.KEY_LEFT,
                      ord('l'),
                      curses.KEY_RIGHT):
            self.toggle()
            self.show(self._win)
            return 0

        return 1

    def toggle(self):
        ''' toggles SimpleCursesBoolean value '''
        self._value = not self._value


#
#   Testing part
#

import logging
logger = logging.getLogger('pyradio')
logger.setLevel(logging.DEBUG)

def main(stdscr):
    __configureLogger()
    curses.start_color()
    curses.use_default_colors()
    try:
        curses.curs_set(0)
    except:
        pass

    #stdscr.addstr('Number of colors: {0}, number of pairs: {1}\n'.format(curses.COLORS, curses.COLOR_PAIRS), curses.color_pair(0))
    #stdscr.getch()

    #pr(stdscr)
    #stdscr.getch()

    curses.init_pair(4,curses.COLOR_RED, curses.COLOR_BLACK)
    curses.init_pair(5,curses.COLOR_BLACK,curses.COLOR_BLUE)
    curses.init_pair(6,curses.COLOR_BLACK,curses.COLOR_RED)
    curses.init_pair(9,curses.COLOR_RED,curses.COLOR_WHITE)
    #curses.init_pair(1,237,248)
    #for n in range(3,13):
    #    stdscr.addstr(n,1,str(n),curses.color_pair(1))

    stdscr.bkgdset(' ', curses.color_pair(5))
    # stdscr.bkgdset(' ', 5)
    stdscr.erase()
    stdscr.touchwin()
    #stdscr.refresh()
    x = SimpleCursesDate(
        1, 2, stdscr,
        5, 9,
    )
    x.enabled = True
    x.focused = True
    x.show()

    while True:
        try:
            c = stdscr.getch()
            # logger.error('DE pressed "{0} - {1}"'.format(c, chr(c)))
            ret = x.keypress(c)
            if (ret == -1):
                return
        except KeyboardInterrupt:
            break

def up():
    logger.error('up')

def down():
    logger.error('down')

def left():
    logger.error('left')

def right():
    logger.error('right')

def __configureLogger():
    logger = logging.getLogger('pyradio')
    logger.setLevel(logging.DEBUG)

    # Handler
    fh = logging.FileHandler('/home/spiros/pyradio.log')
    fh.setLevel(logging.DEBUG)

    # create formatter
    PATTERN = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    formatter = logging.Formatter(PATTERN)

    # add formatter to ch
    fh.setFormatter(formatter)

    # add ch to logger
    logger.addHandler(fh)

if __name__ == "__main__":
    # x = SimpleCursesDate(0,0,None,0,0)
    # x.set_date_string('2023-1-12')
    # print(x)
    # print(x._date)
    # x.selected = 1
    # x.increase()
    # print(x)
    # x.selected = 2
    # for n in range(1, 21):
    #     x.increase()
    #     print(x)
    # x.selected = 1
    # x.increase(9)
    # print('========')
    # print(x)
    # x.selected = 2
    # for n in range(1, 31):
    #     x.increase()
    #     print(x)
    curses.wrapper(main)
    # # curses.wrapper(main)
    # print(SimpleCursesTime.string_to_pyradio_time('2:35:15 aM'))
    # print(SimpleCursesTime.string_to_pyradio_time(''))

    # a = SimpleCursesTime.string_to_pyradio_time('1:35:15 aM')
    # print(SimpleCursesTime.pyradio_time_to_string(a))
    # print(SimpleCursesTime._to_time_datetime(a))
    # a = SimpleCursesTime.string_to_pyradio_time('')
    # print(SimpleCursesTime.pyradio_time_to_string(a))

    # print(SimpleCursesTime.pyradio_time_to_string(
    #     SimpleCursesTime.to_24_format([4, 23, 12, 2])
    # ))
    # print(SimpleCursesTime.to_24_format([4, 23, 12, 2]))

