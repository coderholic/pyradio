# -*- coding: utf-8 -*-
import curses
import curses.ascii
import logging
from sys import version_info, platform, version
from .cjkwrap import PY3, is_wide, cjklen
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)


class DisabledWidget(object):
    """A dummy class that only returns enabled = False

    To be used in complex dialogs
    """
    enabled = False
    focus = False
    checked = False

    def __init(self):
        pass


class SimpleCursesWidget(object):
    """An abstract widget class """
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
        raise ValueError('parameter is read only')

    @property
    def X(self):
        return self._X

    @X.setter
    def X(self, value):
        raise ValueError('parameter is read only')

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
        """The text of the widget"""
        return self._caption

    @caption.setter
    def caption(self, value):
        self._caption = value
        if self._showed:
            self.resize_and_show()

    @property
    def enabled(self):
        """Returns if the widget is enabled"""
        return self._enabled

    @enabled.setter
    def enabled(self, value):
        self._enabled = value
        if self._showed:
            self.refresh()

    @property
    def focused(self):
        """Returns if the widget has focus"""
        return self._focused

    @focused.setter
    def focused(self, value):
        self._focused = value
        if self._showed:
            self.refresh()

    @property
    def color_focused(self):
        """The color to use when the widget has the focus"""
        return self._color_focused

    @color_focused.setter
    def color_focused(self, value):
        self._color = value
        if self._showed:
            self.refresh()

    @property
    def color(self):
        """The normal color of the widget (no focus)"""
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
        """Move the widget

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
        """

        if self._win:
            if erase:
                self._win.erase()
                self._win.touchwin()
                self._win.refresh()
            self._win.mvwin(Y, X)
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
        """Resize the widget.
        The window (_win) gets created here"""

        pass

    def resize_and_show(self):
        """Resize and show the widget"""
        self.resize()
        self.show()

    def show(self):
        """Display the widget"""
        self._showed = True

    def refresh(self):
        """Refresh the widget"""
        pass

    def key(char):
        """Handle keyboard input

        Returns
        =======
            True
                The character was not handled by the widget.
                The calling function can go on and handle it.
            False
                The character was handled by the widget.
                The calling function does not need to handle it.
        """
        return False


class SimpleCursesCheckBox(SimpleCursesWidget):
    """A very simple checkbox curses widget """
    _checked = False
    _highlight_all = False

    def __init__(self,
                 Y, X, caption,
                 color_focused, color, bracket_color,
                 char='✔', checked=False, focused=False,
                 highlight_all=False, callback_function=None):
        """Initialize the widget.

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
        """

        self._Y = Y
        self._X = X
        self._caption = caption
        self._char = char
        self._checked = checked
        self._focused = focused
        self._highlight_all = highlight_all
        self._color_focused = color_focused
        self._color = color
        self._bracket_color = bracket_color

        # initialize the window
        self.resize()

    @property
    def char(self):
        """Character to indicate a checked checkbox
           Default: ✔
        """

        return self._char

    @char.setter
    def char(self, value):
        self._char = value
        self.refresh()

    @property
    def checked(self):
        """Returns if the checkbox is ckecked"""

        return self._checked

    @checked.setter
    def checked(self, value):
        self._checked = value
        self.refresh()

    @property
    def highlight_all(self):
        """Returns if the whole window will use the
        focused color when focused"""
        return self._highlight_all

    @highlight_all.setter
    def highlight_all(self, value):
        self._highlight_all = value
        self.refresh()

    def resize(self):
        """Resize the widget
           For changes to be displayed,
           use show afterwards"""
        # use cjklen for cjk support
        if self._win:
            del self._win
        self._width = None
        self._width = len(self._caption) + 4
        self._win = curses.newwin(1, self._width, self._Y, self._X)

    def show(self):
        """Put the widget on the screen"""
        if self._win:
            self._win.bkgdset(' ', self._color)
            self._win.erase()
            self._win.touchwin()
            self._win.refresh()
            self.refresh()
            self._showed = True

    def refresh(self):
        """Refresh the widget's content"""
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
        """ Calculate width and height based on caption """
        self._height = 1
        self._width = len(self._title) + 4

    def key(self, char):
        if self._focused and \
                self.enabled and \
                char in (ord(' '), ):
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
        """Initialize the wizard.

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
        """

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

    def show(self):
        """Put the widget on the screen"""
        if self._win:
            self._win.bkgdset(' ', self._color)
            self._win.erase()
            self._win.touchwin()
            self._win.refresh()
            self.refresh()
            self._showed = True

    def refresh(self):
        """Refresh the widget's content"""
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
                self._win.addstr(0, 0, '[', self._color)
                self._win.addstr(' ' + self._display_caption + ' ', self._bracket_color)
                try:
                    self._win.addstr(']', self._color)
                except:
                    pass

            self._win.touchwin()
            self._win.refresh()

    def key(self, char):
        if char in (ord(' '), ord('\n'),
                    ord('\r'), curses.KEY_ENTER) and \
                self._focused:
            if self._callback_function:
                self._callback_function(self._parent)
                return True
        return False


class SimpleCursesHorizontalPushButtons(object):
    """A helper class to create horizontally
    spaced curses push buttons.

    After its creation, use show() to display them.
    Access to individual button is through <class>.buttons
    """
    _X = _width = 0
    _parent = None
    _left_or_right_margin = 2

    def __init__(self, Y, captions,
                 color_focused, color,
                 bracket_color, constant_width=0,
                 parent = None,
                 focused=0,
                 left_or_right_margin = 2):
        """Initialize the wizard.

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
        """

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
            # use _focused so that we don't refresh
            self._buttons[focused]._focused = True
        self._parent = parent

    def show(self, parent=None, orientation='center', show=True):
        """Display the widget

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
        """
        if parent:
            self._parent = parent
        if self._parent:
            Y, X = self._parent.getmaxyx()
            if orientation == 'left':
                self._X = self._left_or_right_margin
            elif orientation == 'right':
                self._X = X - self._left_or_right_margin - self._width
            else:
                self._X = int((X - self._width) / 2)
            # place widgets
            X = self._X
            Y = self._Y
            for n in self._buttons:
                n.mvwin(Y, X, show)
                X += n.width + 2

    def calculate_buttons_position(self, parent=None, orientation='center'):
        """Calculate buttons position but do not display them.
        It will call show() with show=False"""
        self.show(parent, orientation, show=False)

    @property
    def buttons(self):
        """The list of buttons within the widget.
        This is the way to get access to an individual
        button and use its functionality.
        """
        return self._buttons

    @buttons.setter
    def buttons(self, value):
        raise ValueError('parameter is read only')

    @property
    def parent(self):
        """The parent window of the widget.
        This is a window, not another widget.
        If not set (or invalid), the buttons will not be
        vissible even if show() is called.
        """
        return self._parent

    @parent.setter
    def parent(self, value):
        self._parent = value
        if self._buttons:
            for n in self._buttons:
                n.parent = value


class SimpleCursesLineEdit(object):
    """ Class to insert one line of text
    Python 3 supports all chars
    Python 2 supports ascii only

    """
    string = ''
    _string = ''
    _displayed_string = ''

    """ windows """
    _parent_win = None
    _caption_win = None      # contains box and caption
    _edit_win = None         # contains the "input box"
    _enabled = True
    _use_paste_mode = False  # paste mode is off by default
    _paste_mode = False      # enables direct insersion of ? and \

    """ Default value for string length """
    _max_chars_to_display = 0

    """ Cursor position within _max_chars_to_display """
    _curs_pos = 0
    _disp_curs_pos = 0
    """ First char of sting to display """
    _first = 0
    _last = 0

    """ init values """
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

    """ if width < 1, auto_width gets this value,
        so that width gets parent.width - auto_width """
    _auto_width = 1

    """ string to redisplay after exiting help """
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

    """ Set to True to restringt accepted characters to ASCII only """
    _pure_ascii = False

    """ True if backlash has been pressed """
    _backslash_pressed = False

    """ Behaviour of ? key regarding \
        If True, display ? (\? to display help)
        If False, display help """
    _show_help_with_backslash_pressed = False

    _mode_changed = None

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
                    self._ungetch_unbound_keys = value
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
                elif key == 'string_changed_handler':
                    # callback function for KEY_STAB
                    self._string_changed_handler = value

        if self._has_history:
            self._input_history = SimpleCursesLineEditHistory()
        self._calculate_window_metrics()

    @property
    def enabled(self):
        return self._enabled

    @enabled.setter
    def enabled(self, val):
        self._enabled = val

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
    def focused(self):
        return self._focused

    @focused.setter
    def focused(self, val):
        if val != self._focused:
            self._focused = val
            # self.show(self.parent_win)

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
        """ Check if string contains CJK characters.
            If string is empty reset history index """
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
        """ Keep a copy of current editor state
            so that it can be restored later. """
        self._restore_data = [
            self.string,
            self._displayed_string,
            self._curs_pos,
            self._disp_curs_pos,
            self._first
        ]

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
                    # printing at the end of the window, do not break...
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

        # opening
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
        self._edit_win.addstr(0, 0, self._displayed_string, active_edit_color)

        # reset position
        if self._reset_position:
            self._reset_position = False
            self._go_to_end()

        if self.log is not None:
            self.log('first={0}, curs={1}, dcurs={2}\n'.format(
                self._first, self._curs_pos, self._disp_curs_pos))
            self.log('     full string: "{}"\n'.format(self.string))
            self.log('displayed string: "{}"\n'.format(self._displayed_string))

        if self.focused:
            # enable this to get info on function
            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('refreshEditWindow:\n  first={0}, curs={1}, dcurs={2}, max={3}\n  len={4}, cjklen={5}\n  string="{6}"\n  len={7}, cjklen={8}\n  disstr="{9}"'.format(self._first, self._curs_pos, self._disp_curs_pos, self._max_chars_to_display, len(self.string), cjklen(self.string), self.string, len(self._displayed_string), cjklen(self._displayed_string), self._displayed_string))
            self._edit_win.chgat(0, self._disp_curs_pos, 1, self.cursor_color)

        self._edit_win.refresh()

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
                self._title_win.addstr(
                    0, 1, self._disp_title, self.title_color
                )
        self._caption_win.refresh()
        self.refreshEditWindow(opening)

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
                    # remove non visible char from the left of the string
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
                # word_delimiter not found:
                self._go_to_start()
                return
            else:
                # word delimiter found
                if str_len < self._max_chars_to_display or \
                        pos >= self._first:
                    # pos is on screen
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
                # pos is on screen
                self._curs_pos = pos + 1 - self._first
                self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
            else:
                if pos < self._first + len(self._displayed_string):
                    # pos is on middle and on screen
                    self._curs_pos = pos - self._first + 1
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    # pos is off screen
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
            # word delimiter not found
            self._go_to_end()

    def _go_right(self):
        if self.string and not self._at_end_of_sting():
            if self._cjk:
                if cjklen(self.string) < self._max_chars_to_display:
                    # just go to next char
                    if self._curs_pos <= len(self.string):
                        self._curs_pos += 1
                    self._disp_curs_pos = cjklen(self.string[:self._curs_pos])
                    self._displayed_string = self.string

                else:
                    at_end_of_disp = self._at_last_char_of_displayed_string()
                    self._curs_pos += 1
                    if self._curs_pos <= len(self._displayed_string):
                        # just go to next char
                        self._disp_curs_pos = cjklen(self.string[self._first:self._first+self._curs_pos])
                    else:
                        # scroll one char right
                        self._displayed_string = self.string[self._first:self._first+len(self._displayed_string)+1]
                        while cjklen(self._displayed_string) >= self._max_chars_to_display + 1:
                            self._first += 1
                            self._displayed_string = self._displayed_string[1:]
                        self._disp_curs_pos = cjklen(self._displayed_string) - cjklen(self._displayed_string[-1])
                        if at_end_of_disp:
                            self._disp_curs_pos += cjklen(self._displayed_string[-1])
            else:
                self.__to_right_simple()
            if self._curs_pos > len(self._displayed_string):
                self._curs_pos = len(self._displayed_string)

    def __to_right_simple(self):
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
                    # just go to previous char
                    self._curs_pos -= 1
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    self._first -= 1
                    self._displayed_string = self.string[self._first: self._first+self._max_chars_to_display]
                    while cjklen(self._displayed_string) > self._max_chars_to_display:
                        self._displayed_string = self._displayed_string[:-1]
            else:
                logger.error('simple')
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
        """ return not xor of two values
                self._backslash_pressed,
                self._show_help_with_backslash_pressed"""
        if self._paste_mode:
            return False
        return not (
            (self._backslash_pressed and
             not self._show_help_with_backslash_pressed)
            or (not self._backslash_pressed
                and self._show_help_with_backslash_pressed))

    def keypress(self, win, char):
        """
         returns:
            2: display help
            1: get next char
            0: exit edit mode, string is valid
           -1: cancel
        """
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
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_end_of_line()
                self.refreshEditWindow()
                if self._string_changed_handler:
                    self._string_changed_handler()
                return 1
            elif char == 422:
                """ A-F, move to next word """
                if self.string:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('action: next-word')
                    self._next_word()
                    self.refreshEditWindow()
                return 1
            elif char == 418:
                """ A-B, move to previous word """
                if self.string:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('action: previous-word')
                    self._previous_word()
                return 1

        if char == 92 and not self._backslash_pressed and not self._paste_mode:
            self._backslash_pressed = True
            if self._mode_changed:
                self._mode_changed()
            return 1

        elif char in (ord('?'), ) and self._can_show_help():
            # display help
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: help')
            self.keep_restore_data()
            self._backslash_pressed = False
            if self._mode_changed:
                self._mode_changed()
            return 2

        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            """ ENTER """
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: enter')
            if self._has_history:
                self._input_history.add_to_history(self._string)
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
            if char == -1:
                """ ESCAPE """
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: Cancel')
                self._string = ''
                self._curs_pos = 0
                if self._input_history:
                    self._input_history.reset_index()
                return -1
            else:
                if self.log is not None:
                    self.log('   *** char = {}\n'.format(char))
                if char in (ord('d'), ):
                    """ A-D, clear to end of line """
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: clear-to-end')
                        self._clear_to_end_of_line()
                        if self._string_changed_handler:
                            self._string_changed_handler()
                elif char in (ord('f'), ):
                    """ A-F, move to next word """
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: next-word')
                        self._next_word()
                elif char in (ord('b'), ):
                    """ A-B, move to previous word """
                    if self.string:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('action: previous-word')
                        self._previous_word()
                else:
                    return 1

        elif char in (curses.KEY_RIGHT, ):
            """ KEY_RIGHT """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: RIGHT')
            self._go_right()

        elif char in (curses.KEY_LEFT, ):
            """ KEY_LEFT """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: LEFT')
                self._go_left()

        elif char in (curses.KEY_HOME, curses.ascii.SOH):
            """ KEY_HOME, ^A """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: HOME')
                self._go_to_start()

        elif char in (curses.KEY_END, curses.ascii.ENQ):
            """ KEY_END, ^E """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: END')
                self._go_to_end()

        elif char in (curses.ascii.ETB, ):
            """ ^W, clear to start of line """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_start_of_line()
                if self._string_changed_handler:
                    self._string_changed_handler()

        elif char in (curses.ascii.VT, ):
            """ Ctrl-K - clear to end of line """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: clear-to-end')
                self._clear_to_end_of_line()
                if self._string_changed_handler:
                    self._string_changed_handler()

        elif char in (curses.ascii.NAK, ):
            """ ^U, clear line """
            self._backslash_pressed = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('action: clear')
            self.string = self._displayed_string = ''
            self._first = self._curs_pos = self._disp_curs_pos = 0
            self._is_cjk()
            if self._string_changed_handler:
                self._string_changed_handler()

        elif char in (curses.KEY_DC, curses.ascii.EOT):
            """ DEL key, ^D """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: delete')
                self._delete_char()
                if self._string_changed_handler:
                    self._string_changed_handler()

        elif char in (curses.KEY_BACKSPACE, curses.ascii.BS, 127):
            """ KEY_BACKSPACE """
            self._backslash_pressed = False
            if self.string:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('action: backspace')
                self._backspace_char()
                if self._string_changed_handler:
                    self._string_changed_handler()

        elif char in (curses.KEY_UP, curses.ascii.DLE):
            """ KEY_UP, ^N """
            self._backslash_pressed = False
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
            self._backslash_pressed = False
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
            self._backslash_pressed = False
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
            self._backslash_pressed = False
            if self._key_pgup_function_handler is not None:
                try:
                    self._key_pgup_function_handler()
                except:
                    pass

        elif char in (9, ):
            """ TAB """
            self._backslash_pressed = False
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
            self._backslash_pressed = False
            if self._key_stab_function_handler is not None:
                try:
                    self._key_stab_function_handler()
                except:
                    pass
            else:
                if self._ungetch_unbound_keys:
                    curses.ungetch(char)

        elif 0 <= char <= 31:
            """ do not accept any other control characters """
            self._backslash_pressed = False

        elif char == ord('p') and self._backslash_pressed \
                and self._use_paste_mode:
            """ toggle paste mode """
            self._backslash_pressed = False
            self._paste_mode = not self._paste_mode
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
                    # accept only ascii characters
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
                if self._pure_ascii:
                    if ord(char) > 127:
                        return 1
                #if len(self._string) == self._first + self._curs_pos:
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
                # adding to end of string
                while cjklen(self._displayed_string) > self._max_chars_to_display:
                    self._displayed_string = self._displayed_string[1:]
                    self._first += 1
                    self._curs_pos -= 1
                if self._cjk:
                    self._disp_curs_pos = cjklen(self._displayed_string)
                else:
                    self._disp_curs_pos = self._curs_pos
            else:
                # adding to middle of string
                while cjklen(self._displayed_string) > self._max_chars_to_display:
                    self._displayed_string = self._displayed_string[:-1]
                if self._cjk:
                    self._disp_curs_pos = cjklen(self._displayed_string[:self._curs_pos])
                else:
                    self._disp_curs_pos = self._curs_pos
            if self._string_changed_handler:
                self._string_changed_handler()
        self.refreshEditWindow()
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
            if PY3:
                if is_wide(out) and not self._cjk:
                    self._cjk = True
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('=== CJK editing is ON ===')
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
        self._history = ['']
        self._active_history_index = 0

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

    def return_history(self, direction, current_string):
        if self._history:
            self._active_history_index += direction
            if self._active_history_index <= -1:
                self._active_history_index = len(self._history) - 1
            elif self._active_history_index >= len(self._history):
                self._active_history_index = 0
            ret = self._history[self._active_history_index]
            if ret.lower() == current_string.lower():
                return self.return_history(direction, current_string)
            return ret
        return ''

    def reset_index(self):
        self._active_history_index = 0


