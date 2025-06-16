# -*- coding: utf-8 -*-
import locale
import curses
import curses.ascii
from time import sleep
import logging
from sys import platform
from os import path, remove, sep, access, X_OK, environ, makedirs
from string import punctuation as string_punctuation
try:
    # python 3
    from urllib.parse import urlparse
except:
    from urlparse import urlparse
from .simple_curses_widgets import SimpleCursesLineEdit, SimpleCursesCheckBox, \
        SimpleCursesHorizontalPushButtons, SimpleCursesMenu, DisabledWidget
from .player import PlayerCache
from .log import Log
from .server import IPsWithNumbers
from .cjkwrap import cjkslices
from .xdg import CheckDir
from .html_help import HtmlHelp
from .keyboard import kbkey, kb2str, kb2chr, check_localized
from .common import M_STRINGS, Station, seconds_to_KB_128, seconds_to_KB_192, seconds_to_KB_320
from .cjkwrap import cjklen

locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)


def find_executable_basename(file_path):
    # Check if it's an absolute path
    if path.isabs(file_path):
        # Check if the file exists and is executable
        if path.exists(file_path) and \
                path.isfile(file_path) and \
                access(file_path, X_OK):
            return path.basename(file_path)
    else:
        # Check if the file exists and is executable in the PATH
        for dir_path in environ["PATH"].split(':'):
            full_path = path.join(dir_path, file_path)
            if path.exists(full_path) and \
                    path.isfile(full_path) and \
                    access(full_path, X_OK):
                return file_path
    # nothing found
    return None

class PyRadioOpenDir(SimpleCursesMenu):

    def __init__(self, config, parent, global_functions):
        self._cnf = config

        if self._cnf.xdg_compliant:
            self._items = [
                    'Config Directory',
                    'Data Directory',
                    'State Directory',
                    'Cache Directory',
                    'Code Directory',
                    'Recordings Directory    ',
            ]
            self._dir = [
                    self._cnf.stations_dir,
                    self._cnf.data_dir,
                    self._cnf.state_dir,
                    self._cnf.cache_dir,
                    path.dirname(__file__),
                    self._cnf.recording_dir
            ]
            self._ord = [
                ord('1'),
                ord('2'),
                ord('3'),
                ord('4'),
                ord('5'),
                ord('6')
            ]
        else:
            self._items = [
                    'Config Directory',
                    'Data Directory',
                    'Cache Directory',
                    'Code Directory',
                    'Recordings Directory        ',
            ]
            self._dir = [
                    self._cnf.stations_dir,
                    self._cnf.data_dir,
                    self._cnf.cache_dir,
                    path.dirname(__file__),
                    self._cnf.recording_dir
            ]
            self._ord = [
                ord('1'),
                ord('2'),
                ord('3'),
                ord('4'),
                ord('5')
            ]

        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug('Open Directory Window')
        #     for n in self._dir:
        #         logger.debug('dir: "{}"'.format(n))

        # logger.error(self._cnf.profile_manager.config_files)
        for a_player in self._cnf.AVAILABLE_PLAYERS:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(a_player.PLAYER_DISPLAY_NAME + ' player found')
            try:
                base = path.dirname(self._cnf.profile_manager.config_files[a_player.PLAYER_NAME][0])
                # logger.error(f'{base = }')
                makedirs(base, exist_ok=True)
                self._items.append(a_player.PLAYER_DISPLAY_NAME + ' Config Directory')
                self._dir.append(base)
                self._ord.append( ord(str(int(chr(self._ord[-1]))+1)) )
            except KeyError:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(a_player.PLAYER_DISPLAY_NAME + ' not in config')
                pass

        SimpleCursesMenu.__init__(
            self,
            Y = -1, X = -1,
            items=self.items,
            parent=parent,
            title=' Open Directory ',
            display_count=True,
            active=0, selection=0,
            color=curses.color_pair(10),
            color_title=curses.color_pair(11),
            color_border=curses.color_pair(3),
            color_active=curses.color_pair(11),
            color_cursor_selection=curses.color_pair(6),
            color_cursor_active=curses.color_pair(9),
            window_type=SimpleCursesMenu.CENTERED,
            margin=1,
            max_height=11,
            global_functions=global_functions
        )
    # self._group_selection_window.show(parent=self.bodyWin)

    def keypress(self, char):
        ''' PyRadioOpenDir keypress
            Returns
            -------
               -1 - Cancel
                0 - Item selected
                1 - Continue
                2 - Display help
        '''
        l_char = None
        if char in self._ord:
            self.dir = self._dir[char-ord('1')]
            return 0
        else:
            ret = SimpleCursesMenu.keypress(self, char)
            if ret == 0:
                self.dir = self._dir[self.selection]
            return ret

class PyRadioSearch(SimpleCursesLineEdit):

    _caption = 'Search'

    def __init__(self, parent, width, begin_y, begin_x, **kwargs):
        SimpleCursesLineEdit.__init__(
            self, parent, width, begin_y, begin_x,
            key_up_function_handler=self._get_history_previous,
            key_down_function_handler=self._get_history_next,
            **kwargs)

    def show(self, parent_win, repaint=False):
        if repaint:
            tmp = self.string
        if parent_win is not None:
            self.parent_win = parent_win

        y, x = self.parent_win.getmaxyx()
        new_y = y - self._height + 1
        new_x = x - self._width
        super(PyRadioSearch, self).show(
            self.parent_win,
            new_y=new_y,
            new_x=new_x)
        y, x = self._caption_win.getmaxyx()
        if self._boxed:
            try:
                self._caption_win.addstr(2, 0, '┴', self.box_color)
                self._caption_win.addstr(0, x-1, '┤', self.box_color)
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

    def get_next(self,
                 a_list,
                 start=0,
                 stop=None,
                 search_term=None,
                 search_function=None
                 ):
        if self.string:
            active_search_term = self.string[1:] if self.string[0] == '+' else self.string
            if search_function and self.string[0] == '+':
                ''' use online browser search instead '''
                return search_function(
                    active_search_term,
                    start=start,
                    stop=stop
                )

            for n in range(start, len(a_list)):
                if active_search_term.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list top """
            for n in range(0, start):
                if active_search_term.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('forward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found return None """
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('forward search term "{}" not found'.format(self.string))
            return None
        else:
            return None

    def get_previous(self,
                     a_list,
                     start=0,
                     stop=None,
                     search_term=None,
                     search_function=None
                     ):
        active_search_term = self.string[1:] if self.string[0] == '+' else self.string
        if self.string:
            if search_function and self.string[0] == '+':
                ''' use online browser search instead '''
                return search_function(
                    active_search_term,
                    start=start,
                    stop=stop
                )

            for n in range(start, -1, -1):
                if active_search_term.lower() in self._get_string(a_list[n]):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('backward search term "{0}" found at {1}'.format(self.string, n))
                    return n
            """ if not found start from list end """
            for n in range(len(a_list) - 1, start, -1):
                if active_search_term.lower() in self._get_string(a_list[n]):
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
        self._edit_win.addstr(0, 0, 'Term not found!'.ljust(self._max_chars_to_display), self.edit_color)
        self._edit_win.refresh()
        sleep(.3)
        self.refreshEditWindow()

    def _get_string(self, item):
        if isinstance(item, str):
            return item.lower()
        else:
            return item[0].lower()


class PyRadioEditor():
    """ PyRadio stations editor """

    _stations = []
    _selection = _pos_to_insert = maxY = maxX = 0

    _win = None
    _parent_win = None
    _old_parent_win = None

    """ Adding a new station or editing an existing one """
    _adding = True

    """ Indicates that we append to the stations' list
        Only valid when adding = True """
    _append = False

    _focus = 0
    _old_focus = 0

    _line_editor = [None, None, None, None]
    _line_editor_yx = ((3, 2), (6, 2), (6, 2), (6,2))

    _item = []
    _orig_item = []

    _dirty = False

    # 0: show too small message
    # 1: show widgets only
    # 2: show half help
    # 3: show all
    _too_small = False

    _global_functions = {}

    def __init__(self,
                 stations,
                 selection,
                 parent,
                 config_encoding,
                 global_functions=None,
                 adding=True):
        self._stations = stations
        self._selection = selection
        self._pos_to_insert = selection + 1
        self._parent_win = parent
        self._encoding = config_encoding
        self._old_encoding = config_encoding
        self._orig_encoding = config_encoding
        self._config_encoding = config_encoding
        self._adding = adding
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}
        self._volume = '-1'
        self._orig_volume = '-1'
        self._buff = '0'
        self._orig_buff = '0'
        self._profile = ''
        self._orig_profile = ''
        self._http = 'False'
        self._orig_http = 'False'

    @property
    def append(self):
        return self._append

    @append.setter
    def append(self, val):
        if self._adding:
            self._append = val
            if self._stations:
                self._pos_to_insert = len(self._stations)
            else:
                self._pos_to_insert = 0

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, value):
        self._profile = value

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0, 11):
            self._focus = val
        else:
            if val < 0:
                self._focus = 10
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
            try:
                self._line_editor[2].string = item[3]['image'] if 'image' in item[3] else ''
            except:
                self._line_editor[2].string = ''
            self._line_editor[3].string = item[Station.referer]
        else:
            self._line_editor[0].string = ''
            self._line_editor[1].string = ''
            self._line_editor[2].string = ''
            self._line_editor[3].string = ''

        try:
            if item[Station.encoding]:
                self._encoding = item[Station.encoding]
            else:
                self._encoding = self._config_encoding
        except:
            self._encoding = self._config_encoding
        # logger.error(f'{item = }')
        self._orig_encoding = self._encoding
        self._old_encoding = self._encoding
        self._orig_volume = item[Station.volume] if item[Station.volume] else '-1'
        self._volume = self._orig_volume
        # logger.error(f'{item[Station.buffering] = }')
        self._buff = '0'
        if item[Station.buffering]:
            try:
                x = item[Station.buffering]
                # logger.error(f'{x = }')
                sp = x.split('@')
                # logger.error(f'{sp = }')
                self._buff = sp[0]
            except IndexError:
                pass
        self._orig_buff = self._buff
        if item[Station.profile]:
            self._profile = item[Station.profile]
        else:
            self._profile = ''
        self._orig_profile = ''
        self._http = item[Station.http]
        if self._http == '1':
            self._http = 'True '
        else:
            self._http = 'False'
        self._orig_http = self._http
        self._item = item
        self._orig_item = item

    def _add_editors(self):
        for ed in range(0, 4):
            if self._line_editor[ed] is None:
                self._line_editor[ed] = SimpleCursesLineEdit(
                    parent=self._win,
                    width=-2,
                    begin_y=self._line_editor_yx[ed][0],
                    begin_x=self._line_editor_yx[ed][1],
                    boxed=False,
                    has_history=False,
                    caption='',
                    box_color=curses.color_pair(9),
                    caption_color=curses.color_pair(4),
                    edit_color=curses.color_pair(9),
                    cursor_color=curses.color_pair(8),
                    unfocused_color=curses.color_pair(5))
                self._line_editor[ed].bracket = False
                self._line_editor[ed]._mode_changed = self._show_alternative_modes
                self._line_editor[ed].use_paste_mode = True
                self._line_editor[ed].set_global_functions(self._global_functions)

    def _print_group_header(self):
        # logger.error('\n\nstring = "{}"\n\n'.format(self._line_editor[1].string.strip()))
        string = 'Group Header'
        str_len = cjklen(string)
        x = int((self.maxX - str_len)/2) + 1
        if self._line_editor[1].string.strip() == '-':
            self._win.addstr(1, x, string, curses.color_pair(12))
        else:
            self._win.addstr(1, x, str_len * ' ', curses.color_pair(4))

    def _set_multi_headers(self):
        col = 5
        headers = ('URL', 'Icon', 'Referrer')

        multi_header = ' {}    {}    {} '.format(*headers)

        self._win.addstr(1, 2, 'Name', curses.color_pair(4))

        # Calculate the x-coordinate for centering the text
        x = 2 + int((self.maxX - 2 - len(multi_header)) / 2)

        if self._focus == 2:
            self._win.addstr(4, x, ' ' + headers[0], curses.color_pair(4))
            self._win.addstr('   <', curses.color_pair(col))
            self._win.addstr(headers[1], curses.color_pair(4))
            self._win.addstr('>', curses.color_pair(col))
            self._win.addstr('   {} '.format(headers[2]), curses.color_pair(4))
        elif self._focus == 3:
            self._win.addstr(4, x, ' ' + headers[0] + '    ' + headers[1] + '   ', curses.color_pair(4))
            self._win.addstr('<', curses.color_pair(col))
            self._win.addstr(headers[2], curses.color_pair(4))
            self._win.addstr('>', curses.color_pair(col))
        # if self._focus == 1:
        else:
            self._win.addstr(4, x, '<', curses.color_pair(col))
            self._win.addstr(headers[0], curses.color_pair(4))
            self._win.addstr('>', curses.color_pair(col))
            self._win.addstr('   {}    {} '.format(headers[1], headers[2]), curses.color_pair(4))

    def show(self, item=None):
        # if 3 < self._focus <= 10 and \
        #         3 < self._old_focus <= 10 and \
        #         self._old_parent_win is not None and \
        #         self._parent_win == self._old_parent_win:
        #     logger.error('\n\n------ SHOW ------')
        #     self._show_extra_fields()
        #     self._show_buttons()
        #     self._win.refresh()
        #     return
        self.maxY, self.maxX = self._parent_win.getmaxyx()

        if self._parent_win is None or \
                self._old_parent_win is None or \
                self._parent_win != self._old_parent_win:
            self._win = None
            self._win = curses.newwin(self.maxY, self.maxX, 1, 0)
        self._add_editors()
        # self._win.bkgdset(' ', curses.color_pair(12))
        self._win.bkgd(' ', curses.color_pair(12))
        if self._old_parent_win is None or \
            self._parent_win != self._old_parent_win:
            # self._win.erase()
            # logger.error('\n\n======= SHOW ======\n\n')
            pass
        self._win.box()
        # self._win.refresh()
        self._show_title()

        self._old_parent_win = self._parent_win

        if self.maxY < 11 or self.maxX < 61:
            txt = ' Window too small to display content '
            error_win = curses.newwin(3,
                                      len(txt) + 2,
                                      int(self.maxY / 2) - 1,
                                      int((self.maxX - len(txt)) / 2))
            error_win.bkgdset(' ', curses.color_pair(12))
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

        # logger.error(f'{self._focus = }')

        self._set_multi_headers()
        self._show_alternative_modes()
        self._show_extra_fields()
        self._show_buttons()

        lim = 20 if self._adding else 21
        if self.maxY > lim and self.maxX > 76:
            try:
                self._win.addstr(13, 3, '─' * (self.maxX - 6), curses.color_pair(12))
            except:
                self._win.addstr(13, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(12))
            self._win.addstr(13, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
            self._win.addstr(14, 5, 'Tab', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Down', curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr('Up', curses.color_pair(4))
            self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
            self._win.addstr(15, 5, 'Enter', curses.color_pair(4))
            self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
            self._win.addstr(16, 23, 'Otherwise, execute selected function.', curses.color_pair(5))
            step = 0
            if not self._adding:
                self._win.addstr(17, 5, kb2chr('revert_saved'), curses.color_pair(4))
                self._win.addstr(', ', curses.color_pair(5))
                self._win.addstr('^R', curses.color_pair(4))
                self._win.addstr(17, 23, 'Revert to saved values (', curses.color_pair(5))
                self._win.addstr('^R', curses.color_pair(4))
                self._win.addstr(' in Line Editor).', curses.color_pair(5))
                step = 1
            self._win.addstr(17 + step, 5, 'Esc', curses.color_pair(4))
            self._win.addstr(17 + step, 23, 'Cancel operation.', curses.color_pair(5))

            self._win.addstr(18 + step, 5, kb2chr('s'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('q'), curses.color_pair(4))
            self._win.addstr(18 + step , 23, 'Save data / Cancel operation (not in Line Editor).', curses.color_pair(5))

            self._win.addstr(19 + step, 5, kb2chr('?'), curses.color_pair(4))
            self._win.addstr(19 + step, 23, 'Line editor help (in Line Editor).', curses.color_pair(5))

        lim = 24 if self._adding else 26
        if self.maxY > lim and self.maxX > 76:
            try:
                self._win.addstr(20 + step, 5, '─' * (self.maxX - 10), curses.color_pair(12))
            except:
                self._win.addstr(20 + step, 3, '─'.encode('utf-8') * (self.maxX - 10), curses.color_pair(12))
            self._win.addstr(20 + step, int((self.maxX - 42) / 2), r' Global Functions (with \ in Line Editor) ', curses.color_pair(4))

            self._win.addstr(21 + step, 5, kb2chr('v_dn2'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up1'), curses.color_pair(4))
            self._win.addstr(' or ', curses.color_pair(5))
            self._win.addstr(kb2chr('v_dn1'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up2'), curses.color_pair(4))
            self._win.addstr(21 + step, 23, 'Change volume', curses.color_pair(5))
            self._win.addstr(22 + step, 5, kb2chr('mute'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('s_vol'), curses.color_pair(4))
            self._win.addstr(22 + step, 23, 'M', curses.color_pair(4))
            self._win.addstr('ute player / Save ', curses.color_pair(5))
            self._win.addstr('v', curses.color_pair(4))
            self._win.addstr('olume.', curses.color_pair(5))
            if step + 21 < self.maxY:
                self._win.addstr(23 + step, 5, kb2chr('t_tag'), curses.color_pair(4))
                self._win.addstr(' / ', curses.color_pair(5))
                self._win.addstr(kb2chr('tag'), curses.color_pair(4))
                self._win.addstr(23 + step, 23, 'Toggle title log / like a station', curses.color_pair(5))
            if step + 22 < self.maxY:
                self._win.addstr(24 + step, 5, kb2chr('transp'), curses.color_pair(4))
                self._win.addstr(24 + step, 23, 'Toggle transparency', curses.color_pair(5))

        if item:
            self._set_item(item)
            self._show_extra_fields()
        self._print_group_header()
        ## self._win.refresh()
        self._update_focus()
        if not self._too_small:
            self._line_editor[0].show(self._win, opening=False)
            if self._focus in (1,2,3):
                self._line_editor[self._focus].show(self._win, opening=False)
            else:
                self._line_editor[1].show(self._win, opening=False)

            is_paste = False
            if self._focus in range(0,4):
                for n in self._line_editor:
                    if n.paste_mode:
                        is_paste = True
                        break
            # reset tip lines
            self._win.addstr(12, 1, (self.maxX -2) * ' ', curses.color_pair(5))

            self._display_field_tip()
            if not is_paste:
                if self._focus == 0:
                    ''' Tip: Press \\p to enter Paste mode '''
                    string = r'Tip: Press \p to enter Paste mode'
                    if cjklen(string) < self.maxX - 4:
                        x = int((self.maxX - cjklen(string) - 2 ) /2)
                        # self._win.addstr(6, self.maxX - 41, 'Tip: ', curses.color_pair(4))
                        self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                        self._win.addstr('Press ', curses.color_pair(5))
                        self._win.addstr(r'\p', curses.color_pair(4))
                        self._win.addstr(' to enter ', curses.color_pair(5))
                        self._win.addstr('Paste mode', curses.color_pair(4))
                if self._focus in range(2,4):
                    ''' Tip: Press \\p before pasting here '''
                    string = r'Tip: Press \p before pasting a URL here'
                    if cjklen(string) < self.maxX - 4:
                        x = int((self.maxX - cjklen(string) - 2 ) /2)
                        self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                        self._win.addstr('Press ', curses.color_pair(5))
                        self._win.addstr(r'\p', curses.color_pair(4))
                        self._win.addstr(' before pasting a URL here', curses.color_pair(5))
                elif self._focus == 1:
                    string = r'Tip: Press \p before pasting a URL here or type a - for a Group Header'
                    if cjklen(string) < self.maxX - 4:
                        x = int((self.maxX - cjklen(string) - 2 ) /2) + 1
                        self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                        self._win.addstr('Press ', curses.color_pair(5))
                        self._win.addstr(r'\p', curses.color_pair(4))
                        self._win.addstr(' before pasting a URL here', curses.color_pair(5))
                        self._win.addstr(' or type a ', curses.color_pair(5))
                        self._win.addstr('- ', curses.color_pair(4))
                        self._win.addstr('for a ', curses.color_pair(5))
                        self._win.addstr('Group Header', curses.color_pair(4))
            self._win.refresh()

    def _show_alternative_modes(self):
        disp = 0
        for n in self._line_editor:
            if n.paste_mode:
                disp = 100
                break
        strings = ('Paste mode', 'Extra mode')
        max_len = max([cjklen(x)+2 for x in strings])
        # logger.error(f'{disp = }')
        if disp == 100:
            """ print paste mode is on on all editors """
            """ set all editors' paste mode """
            string = strings[0]
            # reset tip lines
            self._win.addstr(12, 1, (self.maxX -2) * ' ', curses.color_pair(5))
        else:
            string = max_len * ' '
            for n in self._line_editor:
                if n.backslash_pressed:
                    string = strings[1]
                    break
        # logger.error(f'{string = }')
        x = self.maxX - 2 - max_len
        self._win.addstr(1, x, max_len * ' ', curses.color_pair(5))
        self._win.addstr(4, x, max_len * ' ', curses.color_pair(5))
        if string.strip():
            slen = cjklen(string) + 2
            while slen < max_len:
                string = ' ' + string
                slen = cjklen(string) + 2
            x = self.maxX - 2 - slen
            y = 1 if self._focus == 0 else 4
            self._win.addstr(y, x, '[', curses.color_pair(5))
            self._win.addstr(string, curses.color_pair(12))
            self._win.addstr(']', curses.color_pair(5))
        self._win.refresh()

    def _show_extra_fields(self):
        if self._item:
            col = [5, 5, 5, 5, 5]
            sid = 4
            # if self._focus == sid:
            #     col = 9
            # else:
            #     col = 5
            if self._focus >= sid:
                try:
                    col[self._focus-sid] = 9
                except IndexError:
                    pass
            disp_encoding = 'Default' if self._encoding == self._config_encoding else self._encoding
            # logger.error(f'{self.item = }')
            # logger.error(f'{self._volume = }')
            self._win.addstr(7, 2, 'Volume:', curses.color_pair(4))
            self._win.addstr(' ' + f'{self._volume:>3}' + ' ', curses.color_pair(col[0]))
            self._win.addstr('    ' + 'Buffering:', curses.color_pair(4))
            self._win.addstr(' ' + f'{self._buff:>2}' + ' ', curses.color_pair(col[1]))
            self._win.addstr('    ' + 'Encoding:', curses.color_pair(4))
            self._win.addstr(' ' + disp_encoding + ' ', curses.color_pair(col[2]))
            # delete to end of line
            y, x = self._win.getyx()
            self._win.addstr((self.maxX - x -1) * ' ', curses.color_pair(5))
            self._win.addstr(8, 2, 'Force http:', curses.color_pair(4))
            self._win.addstr(' ' + self._http + ' ', curses.color_pair(col[3]))
            self._win.addstr('    Profile:', curses.color_pair(4))
            disp_profile = self._profile
            if disp_profile == '':
                disp_profile = 'Default'
            self._win.addstr(' ' + disp_profile + ' ', curses.color_pair(col[4]))
            # delete to end of line
            y, x = self._win.getyx()
            self._win.addstr((self.maxX - x -1) * ' ', curses.color_pair(5))
            self._display_field_tip()

    def _display_field_tip(self):
        # Display tips
        self._win.addstr(12, 1, (self.maxX -2) * ' ', curses.color_pair(5))
        if self._focus in (4, 5):
            ''' Tip: Press \\p before pasting here '''
            string = 'Tip: Press Left or Right Arrow (h or l) to adjust'
            if cjklen(string) < self.maxX - 4:
                x = int((self.maxX - cjklen(string) - 2 ) /2)
                self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                self._win.addstr('Press ', curses.color_pair(5))
                self._win.addstr('Left ', curses.color_pair(4))
                self._win.addstr('or', curses.color_pair(5))
                self._win.addstr(' Right ', curses.color_pair(4))
                self._win.addstr('arrow (', curses.color_pair(5))
                self._win.addstr(kb2chr('h'), curses.color_pair(4))
                self._win.addstr(' or ', curses.color_pair(5))
                self._win.addstr(kb2chr('l'), curses.color_pair(4))
                self._win.addstr(') to adjust', curses.color_pair(5))
        elif self._focus in (6, 8):
            ''' Tip: Press \\p before pasting here '''
            string = 'Tip: Press Enter to activate'
            if cjklen(string) < self.maxX - 4:
                x = int((self.maxX - cjklen(string) - 2 ) /2)
                self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                self._win.addstr('Press ', curses.color_pair(5))
                self._win.addstr('Enter ', curses.color_pair(4))
                self._win.addstr('or ', curses.color_pair(5))
                self._win.addstr('Space ', curses.color_pair(4))
                self._win.addstr('to activate', curses.color_pair(5))
        elif self._focus == 7:
            ''' Tip: Press \\p before pasting here '''
            string = 'Tip: Press Left or Right Arrow (h or l) or Space to toggle'
            if cjklen(string) < self.maxX - 4:
                x = int((self.maxX - cjklen(string) - 2 ) /2)
                self._win.addstr(12, x, 'Tip: ', curses.color_pair(4))
                self._win.addstr('Press ', curses.color_pair(5))
                self._win.addstr('Space', curses.color_pair(4))
                self._win.addstr(' or ', curses.color_pair(5))
                self._win.addstr('Left ', curses.color_pair(4))
                self._win.addstr('or', curses.color_pair(5))
                self._win.addstr(' Right ', curses.color_pair(4))
                self._win.addstr('arrow (', curses.color_pair(5))
                self._win.addstr(kb2chr('h'), curses.color_pair(4))
                self._win.addstr(' or ', curses.color_pair(5))
                self._win.addstr(kb2chr('l'), curses.color_pair(4))
                self._win.addstr(') to toggle', curses.color_pair(5))


    def _show_title(self):
        token = ''
        if not self._adding:
            try:
                if (self._line_editor[0].string == self._orig_item[0]) and \
                        (self._line_editor[1].string == self._orig_item[1]):
                    if (self._encoding == self._orig_item[2]) or \
                            (self._encoding == self._config_encoding and self._orig_item[2] == ''):
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
            self._win.chgat(0, x, 4, curses.color_pair(12))
        else:
            self._win.chgat(0, x, 2, curses.color_pair(12))
        # self._refresh()

    def _show_buttons(self):
        sid = 9
        if self._focus == sid:
            col = 9
        else:
            col = 5
        self._win.addstr(10, int((self.maxX - 18) / 2), '[', curses.color_pair(4))
        self._win.addstr(' OK ', curses.color_pair(col))
        self._win.addstr(']  [', curses.color_pair(4))

        sid = 10
        if self._focus == sid:
            col = 9
        else:
            col = 5
        self._win.addstr(' Cancel ', curses.color_pair(col))
        self._win.addstr(']', curses.color_pair(4))

    def _update_focus(self):
        for i in range(0, 4):
            self._line_editor[i].focused = True if i == self._focus else False

    def _return_station(self):
        ret = self._validate()
        # logger.error(f'{ret = }')
        if ret == 1:
            if self._encoding == self._config_encoding:
                self._encoding = ''
            if self._line_editor[1].string.strip() == '-':
                self.new_station = [
                    self._line_editor[0].string.strip(),
                    self._line_editor[1].string.strip(),
                    '', {'image': ''}
                ]
            else:
                buff = self._orig_item[Station.buffering]
                sp = buff.split('@')
                sp[0] = self._buff
                buff = '@'.join(sp)
                if self._encoding in ('Default', self._config_encoding):
                    encoding = ''
                else:
                    encoding = self._encoding
                self.new_station = [
                    self._line_editor[0].string.strip(),
                    self._line_editor[1].string.strip(),
                    encoding,
                    {'image': self._line_editor[2].string.strip()},
                    self._profile,
                    buff,
                    '1' if self._http.strip() == 'True' else '',
                    '' if self._volume == '-1' else self._volume,
                    self._line_editor[3].string.strip()
                ]
            max_value = max(station.value for station in Station)
            while len(self.new_station) <= max_value:
                self.new_station.append('')
            # logger.error(f'new station: {self.new_station}')
        return ret

    def _is_valid_url(self, a_url):
        url = urlparse(a_url)
        if not (url.scheme and url.netloc):
            return False
        if url.scheme not in ('http', 'https'):
            return False
        if url.netloc != 'localhost':
            dot = url.netloc.find('.')
            if dot == -1:
                return False
            elif dot > len(url.netloc) - 3:
                return False
        return True

    def _validate(self):
        ''' validate a station item

            Returns:
                 1: All ok
                -2: Name is empty
                -3: URL is invalid
                -4: Icon URL is invalid
                -5: Invalid icon format
                -6: Referer URL is invalid
        '''
        if not self._line_editor[0].string.strip():
            return -2
        if self._line_editor[1].string.strip() != '-':
            if not self._is_valid_url(self._line_editor[1].string.strip()):
                return -3
        icon_url = self._line_editor[2].string.strip()
        if icon_url:
            if not self._is_valid_url(icon_url):
                return -4
            if not (icon_url.lower().endswith('.jpg') or \
                    icon_url.lower().endswith('.png')):
                return -5
        ref_url = self._line_editor[3].string.strip()
        if ref_url:
            if not self._is_valid_url(ref_url):
                return -6
        return 1

    def keypress(self, char):
        """ PyRadioEditor keypress
            Returns:
                -5: icon format is invalid
                -4: icon url is invalid
                -3: url is invalid
                -2: Station name is empty
                -1: Cancel (new_station = None)
                 0: go on
                 1: Ok     (new_station holds data)
                 2: display line editor help
                 3: open encoding selection window
                 4: window too small
                 5: open profile selection window
        """
        self._old_focus = self._focus
        ret = 0
        l_char = None
        if self._too_small:
            if char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                    check_localized(char, (kbkey['q'], )):
                self.new_station = None
                self._reset_editors_modes()
                ret = -1
        else:
            if (char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                    check_localized(char, (kbkey['q'], ))) and \
                    self.focus > 3:
                self.new_station = None
                self._reset_editors_modes()
                ret = -1
            elif char in (ord('\t'), 9, curses.KEY_DOWN, kbkey['tab']) or \
                    check_localized(char, (kbkey['tab'], )):
                self.focus +=1
                self._reset_editors_escape_mode()
            elif char in (curses.KEY_UP, curses.KEY_BTAB, kbkey['stab']) or \
                    check_localized(char, (kbkey['stab'], )):
                self.focus -= 1
                self._reset_editors_escape_mode()
            elif (char in (ord(' '), kbkey['l'], kbkey['h'], curses.KEY_LEFT, curses.KEY_RIGHT) or
                    check_localized(char, (kbkey['l'], kbkey['h']))) and \
                    self._focus == 6:
                # encoding
                return 3
            elif (char in (ord(' '), kbkey['l'], kbkey['h'], curses.KEY_LEFT, curses.KEY_RIGHT) or
                    check_localized(char, (kbkey['l'], kbkey['h']))) and \
                    self._focus == 8:
                # profile
                return 5
            elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')) \
                    and self._focus != 8:
                if self._focus == 0:
                    # Name
                    self.focus += 1
                elif self._focus == 1:
                    # URL
                    self.focus += 1
                    self._print_group_header()
                elif self._focus == 2:
                    # Icon
                    self.focus += 1
                elif self._focus == 3:
                    # referer
                    self.focus += 1
                elif self._focus == 4:
                    # volume
                    self.focus += 1
                elif self._focus == 5:
                    # buffering
                    self.focus += 1
                elif self._focus == 6:
                    # encoding
                    return 3
                elif self._focus == 7:
                    # force http
                    self.focus += 1
                elif self._focus == 8:
                    # profile
                    self.focus += 1
                elif self._focus == 9:
                    # ok
                    ret = self._return_station()
                    self.focus = abs(ret + 2)
                elif self._focus == 10:
                    # cancel
                    self.new_station = None
                    ret = -1
                self._reset_editors_escape_mode()
            elif ( char == kbkey['s'] or \
                    check_localized(char, (kbkey['s'], )) ) and \
                    self._focus > 3:
                ret = self._return_station()
                self.focus = abs(ret + 2)
                self._reset_editors_modes()
            elif (char in (curses.ascii.DC2, 18) and not self._adding) or \
                    ((char == kbkey['revert_saved'] or \
                    check_localized(char, (kbkey['revert_saved'], )) ) and \
                    not self._adding and self.focus > 3):
                # ^R, revert to saved
                self.item = self._orig_item
                if self.item[Station.encoding]:
                    self._encoding = self.item[Station.encoding]
                else:
                    self._encoding = self._config_encoding
                self._orig_encoding = self._encoding
                for i in range(0, 4):
                    self._line_editor[i]._go_to_end()
            elif self._focus <= 3:
                """
                 Returns:
                    2: display help
                    1: get next char
                    0: exit edit mode, string is valid
                   -1: cancel
                """
                ret = self._line_editor[self._focus].keypress(self._win, char)
                if ret == 1:
                    # get next char
                    self._print_group_header()
                    ret = 0
                elif ret == 0:
                    # exit, string is valid
                    self._return_station()
                    self._reset_editors_modes()
                    self._print_group_header()
                    ret = -1
                elif ret == -1:
                    # cancel
                    self.new_station = None
                    self._reset_editors_modes()
                    ret = -1
            elif self._focus == 4 and \
                    (char in (kbkey['h'], kbkey['l'], curses.KEY_RIGHT,
                             curses.KEY_LEFT, curses.KEY_NPAGE,
                             curses.KEY_PPAGE) or \
                    check_localized(char, (kbkey['h'], kbkey['l']))):
                # handle volume
                self._volume = self._get_number(char, self._volume, -1, -1, 100)
                logger.error(f'setting {self._volume = }')
                self._show_extra_fields()
                self._win.refresh()
            elif self._focus == 5 and \
                    (char in (kbkey['h'], kbkey['l'], curses.KEY_RIGHT,
                             curses.KEY_LEFT, curses.KEY_NPAGE,
                             curses.KEY_PPAGE) or \
                    check_localized(char, (kbkey['h'], kbkey['l']))):
                # handle buffering
                self._buff = self._get_number(char, self._buff, 0, 5, 60)
                logger.error(f'setting {self._buff = }')
                self._show_extra_fields()
                self._win.refresh()
            elif self._focus == 7 and \
                    (char in (kbkey['h'], kbkey['l'], curses.KEY_RIGHT,
                             curses.KEY_LEFT, ord(' ')) or \
                    check_localized(char, (kbkey['h'], kbkey['l']))):
                # handel force http
                if self._http.strip() == 'True':
                    self._http = 'False'
                else:
                    self._http = 'True '
                self._show_extra_fields()
                self._win.refresh()
            elif self._focus == 8 and \
                    char in (curses.KEY_ENTER, ord('\n'), ord('\r'), ord(' ')):
                ret = 5

            elif char in self._global_functions or \
                    (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
                if l_char is None:
                    l_char = char
                self._global_functions[l_char]()

        # logger.error(f'setting {self._focus = }')
        if self._focus > 3:
            self._reset_editors_modes()
        self._show_title()
        self._show_alternative_modes()
        return ret

    def _get_number(self, char, value, reset_value, min_value, max_value):
        x = int(value)
        if char in (kbkey['h'], curses.KEY_LEFT) or \
                check_localized(char, (kbkey['h'], )):
            x -= 1
            if x < min_value:
                x = reset_value
        elif char in (kbkey['l'], curses.KEY_RIGHT) or \
                check_localized(char, (kbkey['l'], )):
            x += 1
            if x > max_value:
                x = max_value
            elif x < min_value:
                x = min_value
        elif char == curses.KEY_NPAGE:
            x -= 5
            if x < min_value:
                x = reset_value
        elif char == curses.KEY_PPAGE:
            x += 5
            if x > max_value:
                x = max_value
            elif x < min_value:
                x = min_value
        return str(x)

    def _reset_editors_modes(self):
        for n in self._line_editor:
            if n:
                n.paste_mode = False
                n.backslash_pressed = False

    def _reset_editors_escape_mode(self):
        for n in self._line_editor:
            if n:
                n.backslash_pressed = False


class PyRadioRecordingDir():
    """ PyRadio insert recording dir dialog """

    def __init__(self, dir_path, parent, global_functions=None):
        self._invalid_chars = '<>|:"*\\/\''.replace(sep, '')
        if platform.startswith('win'):
            self._invalid_chars = self._invalid_chars.replace(':', '')
        self.maxY = self.maxX = 0
        self._win = self._parent_win = self._line_editor = None
        self._focus = 0
        self._line_editor_yx = (4, 2)
        self._create = self._too_small = False
        self._error_string = ''
        self._widgets = [None, None, None, None]
        self._orig_path = self._from_path = self.dir_path = dir_path
        self._from_file = path.basename(self.dir_path).replace('.csv', '')
        self._parent_win = parent
        self.initial_enabled = [True, True, False, True]
        self._title = ' Select Redordings Directory '
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}

    def __del__(self):
        try:
            # logger.error('DE deleting {}'.format(self._win))
            del self._win
            self._win = None
            for x in self._widgets:
                if x is not None:
                    # logger.error('DE deleting {}'.format(x))
                    del x
                    x = None
        except:
            pass
            # logger.error('DE error')

    @property
    def title(self):
        return self.title

    @title.setter
    def title(self, val):
        self._title = val

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0, len(self._widgets)):
            self._focus = val
        else:
            if val < 0:
                self._focus = len(self._widgets) - 1
            else:
                self._focus = 0
        self.show()

    def set_parent(self, val, refresh=True):
        self._parent_win = val
        if refresh:
            self.show()

    def _string_changed(self):
        self._error_string = ''
        stripped_string = self._widgets[0].string.strip()
        if stripped_string == self._orig_path:
            self._widgets[-2].enabled = False
        else:
            # logger.error('stripped_string = "{}"'.format(stripped_string))
            if self._error_string == '':
                if stripped_string.startswith(self._orig_path + sep):
                    self._error_string = 'Invalid dir_path!!!'
                else:
                    err_list = [x for x in self._invalid_chars if x in stripped_string]
                    # logger.error('l = {}'.format(l))
                    if err_list:
                        self._error_string = 'Invalid dir_path!!!'
            self._widgets[-2].enabled = False
            if stripped_string and self._error_string == '':
                self._widgets[-2].enabled = True
        self.show()

    def show(self):
        parent_maxY, parent_maxX = self._parent_win.getmaxyx()

        if self.maxY != parent_maxY or self.maxX != parent_maxX:
            self._win = None
            self._win = curses.newwin(parent_maxY, parent_maxX, 1, 0)
            self.maxY, self.maxX = (parent_maxY, parent_maxX)
            self._win.bkgdset(' ', curses.color_pair(12))
        self._win.erase()
        self._win.box()

        # add editor
        if self._widgets[0] is None:
            self._widgets[0] = SimpleCursesLineEdit(
                parent=self._win,
                width=-2,
                begin_y=self._line_editor_yx[0],
                begin_x=self._line_editor_yx[1],
                boxed=False,
                has_history=False,
                caption='',
                box_color=curses.color_pair(9),
                caption_color=curses.color_pair(4),
                edit_color=curses.color_pair(9),
                cursor_color=curses.color_pair(8),
                unfocused_color=curses.color_pair(5),
                string_changed_handler=self._string_changed)
            if platform.startswith('win'):
                self._widgets[0].paste_mode_always_on = True
            self._widgets[0].bracket = False
            self._widgets[0].set_global_functions(self._global_functions)
            self._widgets[0].id = 0
            self._widgets[0].string = self.dir_path
        self._line_editor = self._widgets[0]
        # add copy checkbox
        if self._widgets[1] is None:
            self._widgets[1] = SimpleCursesCheckBox(
                    self._line_editor_yx[0] + 2, 2,
                    'Move existing files to new location',
                    curses.color_pair(9), curses.color_pair(4), curses.color_pair(5),
                    checked=True
            )
            self._widgets[1].id = 1
        # add open afterwards checkbox
        adjust_line_Y = -1
        # add buttons
        if self._widgets[2] is None:
            self._h_buttons = SimpleCursesHorizontalPushButtons(
                    Y=8 + adjust_line_Y,
                    captions=('OK', 'Cancel'),
                    color_focused=curses.color_pair(9),
                    color=curses.color_pair(4),
                    bracket_color=curses.color_pair(5),
                    parent=self._win)
            self._h_buttons.calculate_buttons_position()
            self._widgets[2], self._widgets[3] = self._h_buttons.buttons
            self._widgets[2].focused = self._widgets[3].focused = False
        else:
            self._h_buttons.calculate_buttons_position(parent=self._win)
        self._widgets[2].id = 2
        self._widgets[3].id = 3

        adjust_line_Y = 0
        if self.initial_enabled:
            # set startup enable status
            zipped = zip(self._widgets, self.initial_enabled)
            for n in zipped:
                n[0].enabled = n[1]
            self.initial_enabled = None

        # logger.error('DE \n\nmaxY = {}, maxX = {}\n\n'.format(self.maxY, self.maxX))
        if self.maxY < 22 + adjust_line_Y or self.maxX < 74:
            if self.maxY < 11 or self.maxX < 44:
                txt = ' Window too small to display content '
                error_win = curses.newwin(3, len(txt) + 2, int(self.maxY / 2) - 1, int((self.maxX - len(txt)) / 2))
                error_win.bkgdset(' ', curses.color_pair(12))
                error_win.erase()
                error_win.box()
                error_win.addstr(1, 1, txt, curses.color_pair(4))
                self._win.refresh()
                error_win.refresh()
                self._too_small = True
                return 0
            else:
                self._too_small = False
        else:
            self._too_small = False

        if self._error_string:
            y = 2 if adjust_line_Y == 0 else 1
            self._win.addstr(y, self.maxX - 2 - len(self._error_string),
                             self._error_string,
                             curses.color_pair(5))
        else:
            self._win.addstr(2, self.maxX - 26, 25 * ' ', curses.color_pair(5))
        self._win.touchline(2, 1)

        self._show_title()
        self._win.addstr(1, 2, 'Current location: ', curses.color_pair(4))
        self._win.addstr(
            cjkslices(self.dir_path, self.maxX-4-18)[0],
            curses.color_pair(5)
            )
        self._win.addstr(2, 2, 'New location:', curses.color_pair(4))
        inv_tit = 'Invalid chars: '
        inv_chars = self._invalid_chars
        invX = self.maxX - len(inv_tit) - len(inv_chars) - 2
        y = 4 if adjust_line_Y == 0 else 3
        self._win.addstr(y, invX, inv_tit, curses.color_pair(4))
        self._win.addstr(inv_chars, curses.color_pair(5))
        adjust_line_Y -= 1
        # logger.error('\n\nadjust_line_Y = {}\n\n'.format(adjust_line_Y ))
        if self.maxY > 18 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(10 + adjust_line_Y, 3, '─' * (self.maxX - 6), curses.color_pair(12))
            except:
                self._win.addstr(10 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(12))
            self._win.addstr(10 + adjust_line_Y, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
            self._win.addstr(11 + adjust_line_Y, 5, 'Tab', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Down', curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr('Up', curses.color_pair(4))
            self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
            self._win.addstr(12 + adjust_line_Y, 5, 'Enter', curses.color_pair(4))
            self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
            self._win.addstr(13 + adjust_line_Y, 23, 'Otherwise, execute selected function.', curses.color_pair(5))


            self._win.addstr(14 + adjust_line_Y, 5, kb2chr('pause'), curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr(kb2chr('l'), curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Left', curses.color_pair(4))
            self._win.addstr('    Toggle check box state.', curses.color_pair(5))


            self._win.addstr(15 + adjust_line_Y, 5, 'Esc', curses.color_pair(4))
            self._win.addstr(15 + adjust_line_Y, 23, 'Cancel operation.', curses.color_pair(5))


            self._win.addstr(16 + adjust_line_Y, 5, 's', curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('q'), curses.color_pair(4))
            self._win.addstr(16 + adjust_line_Y, 23, 'Exeute / Cancel operation (not in Line Editor).', curses.color_pair(5))

            self._win.addstr(17 + adjust_line_Y, 5, kb2chr('?'), curses.color_pair(4))
            self._win.addstr(17 + adjust_line_Y, 23, 'Help or Line editor help.', curses.color_pair(5))

            self._win.addstr(18 + adjust_line_Y, 5, kb2chr('html_help'), curses.color_pair(4))
            self._win.addstr(18 + adjust_line_Y, 23, 'Display HTML help (not in Line Editor).', curses.color_pair(5))

        if self.maxY > 22 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(19 + adjust_line_Y, 5, '─' * (self.maxX - 10), curses.color_pair(12))
            except:
                self._win.addstr(19 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 10), curses.color_pair(12))
            self._win.addstr(19 + adjust_line_Y, int((self.maxX - 42) / 2), r' Global Functions (with \ in Line Editor) ', curses.color_pair(4))

            self._win.addstr(20 + adjust_line_Y, 5, kb2chr('v_dn2'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up1'), curses.color_pair(4))
            self._win.addstr(' or ', curses.color_pair(5))
            self._win.addstr(kb2chr('v_dn1'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up2'), curses.color_pair(4))
            self._win.addstr(20 + adjust_line_Y, 23, 'Change volume', curses.color_pair(5))
            self._win.addstr(21 + adjust_line_Y, 5, kb2chr('mute'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('s_vol'), curses.color_pair(4))
            self._win.addstr(21 + adjust_line_Y, 23, 'M', curses.color_pair(4))
            self._win.addstr('ute player / Save ', curses.color_pair(5))
            self._win.addstr('v', curses.color_pair(4))
            self._win.addstr('olume.).', curses.color_pair(5))
            if adjust_line_Y + 23 < self.maxY:
                self._win.addstr(22 + adjust_line_Y, 5, kb2chr('t_tag'), curses.color_pair(4))
                self._win.addstr(' / ', curses.color_pair(5))
                self._win.addstr(kb2chr('tag'), curses.color_pair(4))
                self._win.addstr(22 + adjust_line_Y, 23, 'Toggle title log / like a station.', curses.color_pair(5))
            if adjust_line_Y + 24 < self.maxY:
                self._win.addstr(23 + adjust_line_Y, 5, kb2chr('transp'), curses.color_pair(4))
                self._win.addstr(23 + adjust_line_Y, 23, 'Toggle transparency.', curses.color_pair(5))

        self._win.refresh()
        self._update_focus()
        if not self._too_small:
            self._line_editor.show(self._win, opening=False)
            for n in range(1,4):
                self._widgets[n].show()

    def _show_title(self, a_title=''):
        if a_title:
            title = a_title
        else:
            title = self._title
        x = int((self.maxX - len(title)) / 2)
        try:
            self._win.addstr(0, x, title, curses.color_pair(4))
        except:
            self._win.addstr(0, x, title.encode('utf-8'), curses.color_pair(4))
        self._win.refresh()

    def _update_focus(self):
        # use _focused here to avoid triggering
        # widgets' refresh
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

    def _focus_next(self):
        # logger.error('nn i self.focus = {}'.format(self.focus))
        if self._focus == len(self._widgets) - 1:
            self.focus = 0
            # logger.error('nn f self.focus = 0')
        else:
            focus = self.focus + 1
            focus = self._widgets[focus].id
            # logger.error('nn focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus += 1
                # logger.error('nn+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('nn o self.focus = {}'.format(self.focus))

    def _focus_previous(self):
        # logger.error('pp i self.focus = {}'.format(self.focus))
        if self._focus == 0:
            self.focus = len(self._widgets) - 1
            # logger.error('pp l self.focus = {}'.format(self.focus))
        else:
            focus = self.focus - 1
            focus = self._widgets[focus].id
            # logger.error('pp focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus -= 1
                # logger.error('pp+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('pp o self.focus = {}'.format(self.focus))

    def _get_result(self, ret):
        check = CheckDir(self._widgets[0].string, remove_after_validation=True)
        if check.is_valid:
            return 1, self._widgets[0].string, self._widgets[1].checked
        self.focus = 0
        return 3, None, False

    def keypress(self, char):
        """ PyRadioRecordingDir keypress
            Returns:
                -1: Cancel                      (-1, None, False)
                 0: go on                       (0, None, False)
                 1: New location ok             (1, new_location, move_files)
                 2: display line editor help    (2, None, False)
                 3: display invalid dir         (3, None, False)
                 4: display rec dir help        (4, None, False)
        """
        ret = 0
        l_char = None
        if self._too_small:
            if char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                check_localized(char, (kbkey['q'], )):
                return -1, None, False
            return 0, None, False
        else:
            if char in (curses.KEY_EXIT, 27):
                self._win.nodelay(True)
                char_esc = self._win.getch()
                self._win.nodelay(False)
                if char_esc == -1:
                    ''' ESCAPE '''
                    return -1, None, False
                curses.ungetch(char_esc)
            if ( char == kbkey['q'] or \
                    check_localized(char, (kbkey['q'], )) ) and \
                    self._focus > 0:
                return -1, None, False
            elif ( char == kbkey['?'] or \
                    check_localized(char, (kbkey['?'], )) ) and \
                    self.focus == 0:
                return 2, None, False
            elif ( char == kbkey['?'] or \
                    check_localized(char, (kbkey['?'], )) ) and \
                    self.focus > 0:
                return 4, None, False
            elif (char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
                          kbkey['pause'], kbkey['l'], curses.KEY_RIGHT) or \
                          check_localized(char, (kbkey['l'], kbkey['pause']))) and \
                          self._focus == 1:
                # check boxes
                self._widgets[self._focus].toggle_checked()
            elif char in (ord('\t'), 9, curses.KEY_DOWN, kbkey['tab']) or \
                    check_localized(char, (kbkey['tab'], )):
                self._focus_next()
            elif char in (curses.KEY_UP, curses.KEY_BTAB, kbkey['stab']) or \
                    check_localized(char, (kbkey['stab'], )):
                self._focus_previous()
            elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                if self._focus == 0:
                    # New location
                    self._focus_next()
                elif self._focus == 1:
                    # check box
                    self._widgets[1].toggle_checked()
                elif self._focus == 2:
                    # ok, execute
                    if self._line_editor.string.startswith(self._orig_path + sep):
                        return 3, None, False
                    else:
                        return self._get_result(ret)
                elif self._focus == 3:
                    # cancel
                    return -1, None, False
            elif ( char == kbkey['s'] or \
                    check_localized(char, (kbkey['s'], )) ) and \
                    self._focus > 0:
                # s, execute
                if self._line_editor.string.startswith(self._orig_path):
                    return 3, None, False
                elif self._widgets[-2].enabled:
                    return self._get_result(ret)
                return 0, None, False
            elif ( char == kbkey['html_help'] or \
                    check_localized(char, (kbkey['html_help'], )) ) and \
                    self._focus > 0:
                html = HtmlHelp()
                html.open_filename(a_file='rec-dir.html')
            elif self._focus == 0:
                """
                 Returns:
                    2: display help
                    1: get next char
                    0: exit edit mode, string isvalid
                   -1: cancel
                """
                ret = self._line_editor.keypress(self._win, char)
                if ret == 2:
                    self._win.touchwin()
                elif ret == 1:
                    # get next char
                    ret = 0
                elif ret == 0:
                    # exit, string is valid
                    ret = -1
                elif ret == -1:
                    # cancel
                    self._widgets[0].string = ''
                    ret = -1
            elif char in self._global_functions or \
                    (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
                if l_char is None:
                    l_char = char
                self._global_functions[l_char]()
        #self._show_title()
        #self.show()
        return 0, None, False


class PyRadioResourceOpener():
    """ PyRadio insert resource opener dialog """

    def __init__(self, opener, parent, global_functions=None):
        self._invalid_chars = '<>|:"*\\/\''.replace(sep, '')
        if platform.startswith('win'):
            self._invalid_chars = self._invalid_chars.replace(':', '')
        self.maxY = self.maxX = 0
        self._win = self._parent_win = self._line_editor = None
        self._focus = 0
        self._line_editor_yx = (4, 2)
        self._create = self._too_small = False
        self._error_string = ''
        self._widgets = [None, None, None]
        self._orig_opener = self.opener = opener
        self._parent_win = parent
        self.initial_enabled = [True, False, True]
        self._title = ' Select Resource Opener '
        if global_functions is None:
            self._global_functions = {}
        else:
            self._global_functions = dict(global_functions)
        self._global_functions[kbkey['revert_def']] = self._revert_to_default
        # self._global_functions[ord('s')] = self._get_result

    def __del__(self):
        try:
            # logger.error('DE deleting {}'.format(self._win))
            del self._win
            self._win = None
            for x in self._widgets:
                if x is not None:
                    # logger.error('DE deleting {}'.format(x))
                    del x
                    x = None
        except:
            pass
            # logger.error('DE error')

    @property
    def title(self):
        return self.title

    @title.setter
    def title(self, val):
        self._title = val

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0, len(self._widgets)):
            self._focus = val
        else:
            if val < 0:
                self._focus = len(self._widgets) - 1
            else:
                self._focus = 0
        self.show()

    def set_parent(self, val, refresh=True):
        self._parent_win = val
        if refresh:
            self.show()

    def _string_changed(self):
        self._error_string = ''
        tmp = self._widgets[0].string.strip().split(' ')
        if tmp[0] == 'auto':
            self._error_string = ''
            self._widgets[-2].enabled = True
        else:
            w_file = find_executable_basename(tmp[0])
            stripped_string = self._widgets[0].string.strip()
            if w_file == self._orig_opener:
                self._widgets[-2].enabled = False
            else:
                if self._error_string == '':
                    if w_file is None:
                        self._error_string = 'Invalid opener!!!'
                    else:
                        err_list = [x for x in self._invalid_chars if x in stripped_string]
                        # logger.error('l = {}'.format(l))
                        if err_list:
                            self._error_string = 'Invalid opener!!!'
                self._widgets[-2].enabled = False
                if w_file and self._error_string == '':
                    self._widgets[-2].enabled = True
        self.show()

    def show(self):
        parent_maxY, parent_maxX = self._parent_win.getmaxyx()

        if self.maxY != parent_maxY or self.maxX != parent_maxX:
            self._win = None
            self._win = curses.newwin(parent_maxY, parent_maxX, 1, 0)
            self.maxY, self.maxX = (parent_maxY, parent_maxX)
            self._win.bkgdset(' ', curses.color_pair(12))
        self._win.erase()
        self._win.box()

        # add editor
        if self._widgets[0] is None:
            self._widgets[0] = SimpleCursesLineEdit(
                parent=self._win,
                width=-2,
                begin_y=self._line_editor_yx[0],
                begin_x=self._line_editor_yx[1],
                boxed=False,
                has_history=False,
                caption='',
                box_color=curses.color_pair(9),
                caption_color=curses.color_pair(4),
                edit_color=curses.color_pair(9),
                cursor_color=curses.color_pair(8),
                unfocused_color=curses.color_pair(5),
                string_changed_handler=self._string_changed)
            if platform.startswith('win'):
                self._widgets[0].paste_mode_always_on = True
            self._widgets[0].bracket = False
            self._widgets[0].set_global_functions(self._global_functions)
            self._widgets[0].id = 0
            self._widgets[0].string = self.opener
        self._line_editor = self._widgets[0]
        adjust_line_Y = -1
        # add buttons
        if self._widgets[1] is None:
            self._h_buttons = SimpleCursesHorizontalPushButtons(
                    Y=6 + adjust_line_Y,
                    captions=('OK', 'Cancel'),
                    color_focused=curses.color_pair(9),
                    color=curses.color_pair(4),
                    bracket_color=curses.color_pair(5),
                    parent=self._win)
            self._h_buttons.calculate_buttons_position()
            self._widgets[1], self._widgets[2] = self._h_buttons.buttons
            self._widgets[1].focused = self._widgets[2].focused = False
        else:
            self._h_buttons.calculate_buttons_position(parent=self._win)
        self._widgets[1].id = 1
        self._widgets[2].id = 2

        adjust_line_Y = 0
        if self.initial_enabled:
            # set startup enable status
            zipped = zip(self._widgets, self.initial_enabled)
            for n in zipped:
                n[0].enabled = n[1]
            self.initial_enabled = None

        # logger.error('DE \n\nmaxY = {}, maxX = {}\n\n'.format(self.maxY, self.maxX))
        if self.maxY < 22 + adjust_line_Y or self.maxX < 74:
            if self.maxY < 11 or self.maxX < 44:
                txt = ' Window too small to display content '
                error_win = curses.newwin(3, len(txt) + 2, int(self.maxY / 2) - 1, int((self.maxX - len(txt)) / 2))
                error_win.bkgdset(' ', curses.color_pair(12))
                error_win.erase()
                error_win.box()
                error_win.addstr(1, 1, txt, curses.color_pair(4))
                self._win.refresh()
                error_win.refresh()
                self._too_small = True
                return 0
            else:
                self._too_small = False
        else:
            self._too_small = False

        if self._error_string:
            y = 2 if adjust_line_Y == 0 else 1
            self._win.addstr(y, self.maxX - 2 - len(self._error_string),
                             self._error_string,
                             curses.color_pair(5))
        else:
            self._win.addstr(2, self.maxX - 26, 25 * ' ', curses.color_pair(5))
        self._win.touchline(2, 1)

        self._show_title()
        self._win.addstr(1, 2, 'Current Resource Opener String: ', curses.color_pair(4))
        self._win.addstr(
            cjkslices(self.opener, self.maxX-4-18)[0],
            curses.color_pair(5)
            )
        self._win.addstr(2, 2, 'New Resource Opener String:', curses.color_pair(4))
        inv_tit = 'Invalid chars: '
        inv_chars = self._invalid_chars
        invX = self.maxX - len(inv_tit) - len(inv_chars) - 2
        y = 4 if adjust_line_Y == 0 else 3
        self._win.addstr(y, invX, inv_tit, curses.color_pair(4))
        self._win.addstr(inv_chars, curses.color_pair(5))
        adjust_line_Y -= 3
        # logger.error('\n\nadjust_line_Y = {}\n\n'.format(adjust_line_Y ))
        if self.maxY > 18 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(10 + adjust_line_Y, 3, '─' * (self.maxX - 6), curses.color_pair(12))
            except:
                self._win.addstr(10 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(12))
            self._win.addstr(10 + adjust_line_Y, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
            self._win.addstr(11 + adjust_line_Y, 5, 'Tab', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Down', curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr('Up', curses.color_pair(4))
            self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
            self._win.addstr(12 + adjust_line_Y, 5, 'Enter', curses.color_pair(4))
            self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
            self._win.addstr(13 + adjust_line_Y, 23, 'Otherwise, execute selected function.', curses.color_pair(5))


            self._win.addstr(14 + adjust_line_Y, 5, 'Esc', curses.color_pair(4))
            self._win.addstr(14 + adjust_line_Y, 23, 'Cancel operation.', curses.color_pair(5))


            self._win.addstr(15 + adjust_line_Y, 5, kb2chr('revert_def'), curses.color_pair(4))
            self._win.addstr(15 + adjust_line_Y, 23, 'Revert to default (', curses.color_pair(5))
            self._win.addstr(r'\d', curses.color_pair(4))
            self._win.addstr(' in Line Editor).', curses.color_pair(5))
            self._win.addstr(16 + adjust_line_Y, 5, kb2chr('s'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('q'), curses.color_pair(4))
            self._win.addstr(16 + adjust_line_Y, 23, 'Exeute / Cancel operation (not in Line Editor).', curses.color_pair(5))

            self._win.addstr(17 + adjust_line_Y, 5, kb2chr('?'), curses.color_pair(4))
            self._win.addstr(17 + adjust_line_Y, 23, 'Help or Line editor help.', curses.color_pair(5))

        adjust_line_Y -= 1
        if self.maxY > 22 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(19 + adjust_line_Y, 5, '─' * (self.maxX - 10), curses.color_pair(12))
            except:
                self._win.addstr(19 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 10), curses.color_pair(12))
            self._win.addstr(19 + adjust_line_Y, int((self.maxX - 42) / 2), r' Global Functions (with \ in Line Editor) ', curses.color_pair(4))

            self._win.addstr(20 + adjust_line_Y, 5, kb2chr('v_dn2'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up1'), curses.color_pair(4))
            self._win.addstr(' or ', curses.color_pair(5))
            self._win.addstr(kb2chr('v_dn1'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up2'), curses.color_pair(4))
            self._win.addstr(20 + adjust_line_Y, 23, 'Change volume', curses.color_pair(5))
            self._win.addstr(21 + adjust_line_Y, 5, kb2chr('mute'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('s_vol'), curses.color_pair(4))
            self._win.addstr(21 + adjust_line_Y, 23, 'M', curses.color_pair(4))
            self._win.addstr('ute player / Save ', curses.color_pair(5))
            self._win.addstr('v', curses.color_pair(4))
            self._win.addstr('olume.', curses.color_pair(5))
            if adjust_line_Y + 23 < self.maxY:
                self._win.addstr(22 + adjust_line_Y, 5, 'W', curses.color_pair(4))
                self._win.addstr(' / ', curses.color_pair(5))
                self._win.addstr('w', curses.color_pair(4))
                self._win.addstr(22 + adjust_line_Y, 23, 'Toggle title log / like a station.', curses.color_pair(5))
            if adjust_line_Y + 24 < self.maxY:
                self._win.addstr(23 + adjust_line_Y, 5, 'T', curses.color_pair(4))
                self._win.addstr(23 + adjust_line_Y, 23, 'Toggle transparency.', curses.color_pair(5))

        self._win.refresh()
        self._update_focus()
        if not self._too_small:
            self._line_editor.show(self._win, opening=False)
            for n in range(1,3):
                self._widgets[n].show()

    def _show_title(self, a_title=''):
        if a_title:
            title = a_title
        else:
            title = self._title
        x = int((self.maxX - len(title)) / 2)
        try:
            self._win.addstr(0, x, title, curses.color_pair(4))
        except:
            self._win.addstr(0, x, title.encode('utf-8'), curses.color_pair(4))
        self._win.refresh()

    def _update_focus(self):
        # use _focused here to avoid triggering
        # widgets' refresh
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

    def _focus_next(self):
        # logger.error('nn i self.focus = {}'.format(self.focus))
        if self._focus == len(self._widgets) - 1:
            self.focus = 0
            # logger.error('nn f self.focus = 0')
        else:
            focus = self.focus + 1
            focus = self._widgets[focus].id
            # logger.error('nn focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus += 1
                # logger.error('nn+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('nn o self.focus = {}'.format(self.focus))

    def _focus_previous(self):
        # logger.error('pp i self.focus = {}'.format(self.focus))
        if self._focus == 0:
            self.focus = len(self._widgets) - 1
            # logger.error('pp l self.focus = {}'.format(self.focus))
        else:
            focus = self.focus - 1
            focus = self._widgets[focus].id
            # logger.error('pp focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus -= 1
                # logger.error('pp+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('pp o self.focus = {}'.format(self.focus))

    def _get_result(self):
        tmp = self._widgets[0].string.strip().split(' ')
        if tmp[0] == 'auto':
            return 1, 'auto'
        w_file = find_executable_basename(tmp[0])
        if w_file is None:
            return 3, None
        ''' commanting this to preserve full path '''
        # tmp[0] = w_file
        return 1, ' '.join(tmp)

    def _revert_to_default(self):
        self._widgets[0].string = 'auto'
        self._widgets[0].keep_restore_data()
        self._widgets[0].show(self._win, opening=True)
        self._widgets[-2].enabled = True
        return 0, None

    def keypress(self, char):
        """ PyRadioResourceOpener keypress
            Returns:
                -1: Cancel                            (-1, None)
                 0: go on                             (0, None)
                 1: New resource opener ok            (1, new_resource)
                 2: display line editor help          (2, None)
                 3: display invalid opener            (3, None)
                 4: display resource opener help      (4, None)
        """
        ret = 0
        l_char = None
        if self._too_small:
            if char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                    check_localized(char, (kbkey['q'], )):
                return -1, None, False
            return 0, None
        else:
            if char in (curses.KEY_EXIT, 27):
                self._win.nodelay(True)
                char_esc = self._win.getch()
                self._win.nodelay(False)
                if char_esc == -1:
                    ''' ESCAPE '''
                    return -1, None
                curses.ungetch(char_esc)
            if (char == kbkey['q'] or \
                    check_localized(char, (kbkey['q'], ))) and \
                    self._focus > 0:
                return -1, None
            elif (char == kbkey['?'] or \
                    check_localized(char, (kbkey['?'], ))) and \
                    self.focus == 0:
                return 2, None
            elif (char == kbkey['?'] or \
                    check_localized(char, (kbkey['?'], ))) and \
                    self.focus > 0:
                return 4, None
            elif char in (ord('\t'), 9, curses.KEY_DOWN, kbkey['tab']) or \
                    check_localized(char, (kbkey['tab'], )):
                self._focus_next()
            elif char in (curses.KEY_UP, curses.KEY_BTAB, kbkey['stab']) or \
                    check_localized(char, (kbkey['stab'], )):
                self._focus_previous()
            elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                if self._focus == 0:
                    # New location
                    self._focus_next()
                elif self._focus == 1:
                    # ok, execute
                    return self._get_result()
                elif self._focus == 2:
                    # cancel
                    return -1, None
            elif (char == kbkey['s'] or \
                    check_localized(char, (kbkey['s'], ))) and \
                    self._focus > 0:
                # s, execute
                return self._get_result()
            elif (char == kbkey['revert_def'] or \
                    check_localized(char, (kbkey['revert_def'], ))) and \
                    self._focus > 0:
                # d, revert to default
                return self._revert_to_default()
            elif self._focus == 0:
                """
                 Returns:
                    2: display help
                    1: get next char
                    0: exit edit mode, string isvalid
                   -1: cancel
                """
                ret = self._line_editor.keypress(self._win, char)
                if ret == 2:
                    self._win.touchwin()
                elif ret == 1:
                    # get next char
                    ret = 0
                elif ret == 0:
                    # exit, string is valid
                    ret = -1
                elif ret == -1:
                    # cancel
                    self._widgets[0].string = ''
                    ret = -1
            elif char in self._global_functions or \
                    (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
                if l_char is None:
                    l_char = char
                self._global_functions[l_char]()
        #self._show_title()
        #self.show()
        return 0, None


class PyRadioRenameFile():
    """ PyRadio copy file dialog """

    def __init__(self, filename, parent, create=False,
                 open_afterwards=True, title='',
                 opened_from_editor=False,
                 global_functions=None):
        self._invalid_chars = '<>|:"\\/?*'
        self.maxY = self.maxX = 0
        self._win = self._parent_win = self._line_editor = None
        self._focus = 0
        self._line_editor_yx = (4, 2)
        self._create = self._too_small = False
        self._error_string = ''
        self._widgets = [None, None, None, None, None]
        self.checked_checkbox = None
        self.filename = filename
        self._from_path = path.dirname(filename)
        self._from_file = path.basename(self.filename).replace('.csv', '')
        if self._from_file.startswith('register_'):
            self._to_path = path.dirname(self._from_path)
            self._display_from_file = 'Register: ' + self._from_file.replace('register_', '')
        else:
            self._to_path = self._from_path
            self._display_from_file = self._from_file
        # logger.error('DE filename = {0}\nfrom path = {1}\nfrom file = {2}\nto path = {3}\ndisplay name = {4}'.format(
        #     filename,
        #     self._from_path,
        #     self._from_file,
        #     self._to_path,
        #     self._display_from_file))

        self._parent_win = parent
        self._create = create
        if self._create:
            self._line_editor_yx = (4, 2)
            self.initial_enabled = [True, False, True, False, True]
        else:
            self.initial_enabled = [True, True, False, False, True]
        self._open_afterwards = open_afterwards
        self._title = title if title else ' Rename Playlist '
        self._opened_from_editor = opened_from_editor
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}

    def __del__(self):
        try:
            logger.error('DE deleting {}'.format(self._win))
            del self._win
            self._win = None
            for x in self._widgets:
                if x is not None:
                    logger.error('DE deleting {}'.format(x))
                    del x
                    x = None
        except:
            pass
            logger.error('DE error')

    @property
    def create(self):
        return self._create

    @create.setter
    def create(self, val):
        raise ValueError('propery is read only')

    @property
    def title(self):
        return self.title

    @title.setter
    def title(self, val):
        self._title = val

    @property
    def focus(self):
        return self._focus

    @focus.setter
    def focus(self, val):
        if val in range(0, len(self._widgets)):
            self._focus = val
        else:
            if val < 0:
                self._focus = len(self._widgets) - 1
            else:
                self._focus = 0
        self.show()

    def set_parent(self, val, refresh=True):
        self._parent_win = val
        if refresh:
            self.show()

    def _string_changed(self):
        self._error_string = ''
        first_char = ''
        if self._widgets[0].string != '':
            first_char = self._widgets[0].string[0]
            if first_char in string_punctuation + ' ':
                self._error_string = 'Invalid filename!!!'
        stripped_string = self._widgets[0].string.strip()
        if self._error_string == '':
            if stripped_string:
                check_file = path.join(self._to_path, stripped_string + '.csv')
                if check_file == self.filename:
                    if self._create:
                        self._error_string = 'File already exists!!!'
                    else:
                        self._error_string = 'You must be joking!!!'
                elif path.exists(check_file):
                    self._error_string = 'File already exists!!!'
                elif stripped_string.startswith('register_'):
                    self._error_string = 'Register token inserted!!!'
                else:
                    for inv in self._invalid_chars:
                        if inv in stripped_string:
                            self._error_string = 'Invalid filename!!!'
                            logger.error('DE inv = ' + inv)
                            break
                    #if self._error_string == '':
                    #    for inv in range(1, 32):
                    #        if str(inv) in stripped_string:
                    #            self._error_string = 'Invalid filename!!!'
        self._widgets[-2].enabled = False
        if stripped_string and self._error_string == '':
            self._widgets[-2].enabled = True
        self.show()

    def show(self):
        parent_maxY, parent_maxX = self._parent_win.getmaxyx()

        if self.maxY != parent_maxY or self.maxX != parent_maxX:
            self._win = None
            self._win = curses.newwin(parent_maxY, parent_maxX, 1, 0)
            self.maxY, self.maxX = (parent_maxY, parent_maxX)
        self._win.bkgdset(' ', curses.color_pair(12))
        self._win.erase()
        self._win.box()

        # add editor
        if self._widgets[0] is None:
            self._widgets[0] = SimpleCursesLineEdit(
                parent=self._win,
                width=-2,
                begin_y=self._line_editor_yx[0],
                begin_x=self._line_editor_yx[1],
                boxed=False,
                has_history=False,
                caption='',
                box_color=curses.color_pair(9),
                caption_color=curses.color_pair(4),
                edit_color=curses.color_pair(9),
                cursor_color=curses.color_pair(8),
                unfocused_color=curses.color_pair(5),
                string_changed_handler=self._string_changed)
            self._widgets[0].bracket = False
            self._widgets[0].set_global_functions(self._global_functions)
            self._widgets[0].id = 0
        self._line_editor = self._widgets[0]
        # add copy checkbox
        if self._widgets[1] is None:
            if self._create:
                self._widgets[1] = DisabledWidget()
            else:
                self._widgets[1] = SimpleCursesCheckBox(
                        self._line_editor_yx[0] + 2, 2,
                        'Copy playlist instead of renaming it',
                        curses.color_pair(9), curses.color_pair(4), curses.color_pair(5))
            self._widgets[1].id = 1
        # add open afterwards checkbox
        adjust_line_Y = -1
        if self._open_afterwards:
            adjust_line_Y = 0
            if self._widgets[2] is None:
                y = 2 if self._create else 3
                self._widgets[2] = SimpleCursesCheckBox(
                        self._line_editor_yx[0] + y, 2,
                        'Open playlist for editing afterwards',
                        curses.color_pair(9), curses.color_pair(4), curses.color_pair(5))
                if self._opened_from_editor:
                    self.initial_enabled[2] = False
                else:
                    self.initial_enabled[2] = True
        else:
            self._widgets[2] = DisabledWidget()
        self._widgets[2].id = 2
        if self._create:
            adjust_line_Y = -1
        # add buttons
        if self._widgets[3] is None:
            self._h_buttons = SimpleCursesHorizontalPushButtons(
                    Y=8 + adjust_line_Y if self._open_afterwards else 7 + adjust_line_Y,
                    captions=('OK', 'Cancel'),
                    color_focused=curses.color_pair(9),
                    color=curses.color_pair(4),
                    bracket_color=curses.color_pair(5),
                    parent=self._win)
            self._h_buttons.calculate_buttons_position()
            self._widgets[3], self._widgets[4] = self._h_buttons.buttons
            self._widgets[3]._focused = self._widgets[4].focused = False
        else:
            self._h_buttons.calculate_buttons_position(parent=self._win)
        self._widgets[3].id = 3
        self._widgets[4].id = 4

        if self._create:
            adjust_line_Y = -2
        else:
            adjust_line_Y = 0
        if self.initial_enabled:
            # set startup enable status
            zipped = zip(self._widgets, self.initial_enabled)
            for n in zipped:
                n[0].enabled = n[1]
            self.initial_enabled = None
        if self.checked_checkbox:
            # set initial checkmarks
            zipped = zip((self._widgets[1], self._widgets[2]),
                         self.checked_checkbox)
            for n in zipped:
                n[0].checked = n[1]
            self.checked_checkbox = None


        # logger.error('DE \n\nmaxY = {}, maxX = {}\n\n'.format(self.maxY, self.maxX))
        if self.maxY < 22 + adjust_line_Y or self.maxX < 74:
            if self.maxY < 11 or self.maxX < 44:
                txt = ' Window too small to display content '
                error_win = curses.newwin(3, len(txt) + 2, int(self.maxY / 2) - 1, int((self.maxX - len(txt)) / 2))
                error_win.bkgdset(' ', curses.color_pair(12))
                error_win.erase()
                error_win.box()
                error_win.addstr(1, 1, txt, curses.color_pair(4))
                self._win.refresh()
                error_win.refresh()
                self._too_small = True
                return 0
            else:
                self._too_small = False
        else:
            self._too_small = False

        if self._error_string:
            y = 2 if adjust_line_Y == 0 else 1
            self._win.addstr(y, self.maxX - 2 - len(self._error_string),
                             self._error_string,
                             curses.color_pair(5))
        else:
            self._win.addstr(2, self.maxX - 26, 25 * ' ', curses.color_pair(5))
        self._win.touchline(2, 1)

        self._show_title()
        if self._create:
            self._win.addstr(1, 2, 'Name of Playlist to create:', curses.color_pair(4))
        else:
            self._win.addstr(1, 2, 'Rename: ', curses.color_pair(4))
            self._win.addstr(
                self._display_from_file,
                curses.color_pair(5)
                )
            self._win.addstr(2, 2, 'To:', curses.color_pair(4))
        inv_tit = 'Invalid chars: '
        inv_chars = self._invalid_chars
        invX = self.maxX - len(inv_tit) - len(inv_chars) - 2
        y = 4 if adjust_line_Y == 0 else 3
        self._win.addstr(y, invX, inv_tit, curses.color_pair(4))
        self._win.addstr(inv_chars, curses.color_pair(5))

        if self.maxY > 18 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(10 + adjust_line_Y, 3, '─' * (self.maxX - 6), curses.color_pair(12))
            except:
                self._win.addstr(10 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(12))
            self._win.addstr(10 + adjust_line_Y, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(4))
            self._win.addstr(11 + adjust_line_Y, 5, 'Tab', curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Down', curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr('Up', curses.color_pair(4))
            self._win.addstr('    Go to next / previous field.', curses.color_pair(5))
            self._win.addstr(12 + adjust_line_Y, 5, 'Enter', curses.color_pair(4))
            self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(5))
            self._win.addstr(13 + adjust_line_Y, 23, 'Otherwise, execute selected function.', curses.color_pair(5))


            self._win.addstr(14 + adjust_line_Y, 5, kb2chr('pause'), curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr(kb2chr('l'), curses.color_pair(4))
            self._win.addstr(', ', curses.color_pair(5))
            self._win.addstr('Left', curses.color_pair(4))
            self._win.addstr('    Toggle check box state.', curses.color_pair(5))


            self._win.addstr(15 + adjust_line_Y, 5, 'Esc', curses.color_pair(4))
            self._win.addstr(15 + adjust_line_Y, 23, 'Cancel operation.', curses.color_pair(5))


            self._win.addstr(16 + adjust_line_Y, 5, kb2chr('s'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('q'), curses.color_pair(4))
            self._win.addstr(16 + adjust_line_Y, 23, 'Exeute / Cancel operation (not in Line Editor).', curses.color_pair(5))

            self._win.addstr(17 + adjust_line_Y, 5, kb2chr('?'), curses.color_pair(4))
            self._win.addstr(17 + adjust_line_Y, 23, 'Line editor help (in Line Editor).', curses.color_pair(5))

        if self.maxY > 21 + adjust_line_Y and self.maxX > 76:
            try:
                self._win.addstr(18 + adjust_line_Y, 5, '─' * (self.maxX - 10), curses.color_pair(12))
            except:
                self._win.addstr(18 + adjust_line_Y, 3, '─'.encode('utf-8') * (self.maxX - 10), curses.color_pair(12))
            self._win.addstr(18 + adjust_line_Y, int((self.maxX - 42) / 2), r' Global Functions (with \ in Line Editor) ', curses.color_pair(4))

            self._win.addstr(19 + adjust_line_Y, 5, kb2chr('v_dn2'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up1'), curses.color_pair(4))
            self._win.addstr(' or ', curses.color_pair(5))
            self._win.addstr(kb2chr('v_dn1'), curses.color_pair(4))
            self._win.addstr('/', curses.color_pair(5))
            self._win.addstr(kb2chr('v_up2'), curses.color_pair(4))
            self._win.addstr(19 + adjust_line_Y, 23, 'Change volume', curses.color_pair(5))
            self._win.addstr(20 + adjust_line_Y, 5, kb2chr('mute'), curses.color_pair(4))
            self._win.addstr(' / ', curses.color_pair(5))
            self._win.addstr(kb2chr('s_vol'), curses.color_pair(4))
            self._win.addstr(20 + adjust_line_Y, 23, 'M', curses.color_pair(4))
            self._win.addstr('ute player / Save ', curses.color_pair(5))
            self._win.addstr('v', curses.color_pair(4))
            self._win.addstr('olume.', curses.color_pair(5))
            if adjust_line_Y + 22 < self.maxY:
                self._win.addstr(21 + adjust_line_Y, 5, kb2chr('t_tag'), curses.color_pair(4))
                self._win.addstr(' / ', curses.color_pair(5))
                self._win.addstr(kb2chr('tag'), curses.color_pair(4))
                self._win.addstr(21 + adjust_line_Y, 23, 'Toggle title log / like a station', curses.color_pair(5))
            if adjust_line_Y + 23 < self.maxY:
                self._win.addstr(22 + adjust_line_Y, 5, kb2chr('transp'), curses.color_pair(4))
                self._win.addstr(22 + adjust_line_Y, 23, 'Toggle transparency', curses.color_pair(5))

        self._win.refresh()
        self._update_focus()
        if not self._too_small:
            self._line_editor.show(self._win, opening=False)
            if not isinstance(self._widgets[1], DisabledWidget):
                self._widgets[1].show()
            if not isinstance(self._widgets[2], DisabledWidget):
                self._widgets[2].show()
            self._widgets[3].show()
            self._widgets[4].show()

    def _show_title(self, a_title=''):
        if a_title:
            title = a_title
        else:
            title = self._title
        x = int((self.maxX - len(title)) / 2)
        try:
            self._win.addstr(0, x, title, curses.color_pair(4))
        except:
            self._win.addstr(0, x, title.encode('utf-8'), curses.color_pair(4))
        self._win.refresh()

    def _update_focus(self):
        # use _focused here to avoid triggering
        # widgets' refresh
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

    def _focus_next(self):
        # logger.error('nn i self.focus = {}'.format(self.focus))
        if self._focus == len(self._widgets) - 1:
            self.focus = 0
            # logger.error('nn f self.focus = 0')
        else:
            focus = self.focus + 1
            focus = self._widgets[focus].id
            # logger.error('nn focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus += 1
                # logger.error('nn+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('nn o self.focus = {}'.format(self.focus))

    def _focus_previous(self):
        # logger.error('pp i self.focus = {}'.format(self.focus))
        if self._focus == 0:
            self.focus = len(self._widgets) - 1
            # logger.error('pp l self.focus = {}'.format(self.focus))
        else:
            focus = self.focus - 1
            focus = self._widgets[focus].id
            logger.error('pp focus = {}'.format(focus))
            while not self._widgets[focus].enabled:
                focus -= 1
                # logger.error('pp+ focus = {}'.format(focus))
            self.focus = focus
        # logger.error('pp o self.focus = {}'.format(self.focus))

    def _act_on_file(self):
        """Rename the playlist (if self._create is False)
        or Create a playlist (if self._create is True)

        If renaming, it first copies the old file to
        new file and then removes the old file (if it
        is supposed to do so).

        Returns
        =======
             1: All ok
            -2: Copy / Create file failed
            -3: Delete file failed
        """

        self.new_file_name = path.join(self._to_path, self._widgets[0].string + '.csv')
        if self._create:
            try:
                with open(self.new_file_name, 'w', encoding='utf-8'):
                    pass
            except:
                return -2
        else:
            from shutil import copy2
            try:
                copy2(self.filename, self.new_file_name)
            except:
                return -2
            if not self._widgets[1].checked:
                try:
                    remove(self.filename)
                except:
                    return -3
        return 1

    def _get_result(self, ret):
        ofile = path.join(self._to_path, self._widgets[0].string.strip() + '.csv') if self._widgets[0].string else ''
        if self._create:
            result = (
                    ret,
                    ofile, ofile,
                    False if isinstance(self._widgets[1], DisabledWidget) else self._widgets[1].checked,
                    False if isinstance(self._widgets[2], DisabledWidget) else self._widgets[2].checked,
                    self._create
                    )
        else:
            result = (
                    ret,
                    self.filename, ofile,
                    False if isinstance(self._widgets[1], DisabledWidget) else self._widgets[1].checked,
                    False if isinstance(self._widgets[2], DisabledWidget) else self._widgets[2].checked,
                    self._create
                    )
        return result

    def keypress(self, char):
        """ PyRadioRenameFile keypress
            Returns:
                -1: Cancel
                 0: go on
                 1: Operation succeeded
                 2: display line editor help
        """
        ret = 0
        l_char = None
        if self._too_small:
            if char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                    check_localized(char, (kbkey['q'], )):
                return -1, '', '', False, False, False
            return 0, '', '', False, False, False
        else:
            logger.error('self.focus = {}'.format(self.focus))
            if (char in (curses.KEY_EXIT, 27, kbkey['q']) or \
                    check_localized(char, (kbkey['q'], ))) and \
                    self.focus > 0:
                return -1, '', '', False, False, False
            elif (char in (kbkey['pause'], kbkey['l'], curses.KEY_RIGHT,
                          curses.KEY_ENTER, ord('\n'), ord('\r')) or \
                    check_localized(char, (kbkey['l'], kbkey['pause']))) and \
                    self._focus in (1, 2):
                # check boxes
                self._widgets[self._focus].toggle_checked()
                if self._focus == 1 and self._opened_from_editor:
                    self._widgets[2].enabled = self._widgets[1].checked
                logger.error('len widgets = {}'.format(len(self._widgets)))
            elif char in (ord('\t'), 9, curses.KEY_DOWN, kbkey['tab']) or \
                    check_localized(char, (kbkey['tab'], )):
                self._focus_next()
            elif char in (curses.KEY_UP, curses.KEY_BTAB, kbkey['stab']) or \
                    check_localized(char, (kbkey['stab'], )):
                self._focus_previous()
            elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                if self._focus == 0:
                    # Playlist Name
                    self._focus_next()
                elif self._focus in (1, 2):
                    # check boxes
                    self._widgets[self._focus].toggle_checked()
                elif self._focus == 3:
                    # ok, execute
                    ret = self._act_on_file()
                    return self._get_result(ret)
                elif self._focus == 4:
                    # cancel
                    return -1, '', '', False, False, False
            elif (char == kbkey['s'] or \
                    check_localized(char, (kbkey['s'], ))) and \
                    self._focus > 0:
                # s, execute
                if self._widgets[-2].enabled:
                    ret = self._act_on_file()
                    return self._get_result(ret)
                return 0, '', '', False, False, False
            elif self._focus == 0:
                """
                 Returns:
                    2: display help
                    1: get next char
                    0: exit edit mode, string isvalid
                   -1: cancel
                """
                ret = self._line_editor.keypress(self._win, char)
                if ret == 2:
                    self._win.touchwin()
                elif ret == 1:
                    # get next char
                    ret = 0
                elif ret == 0:
                    # exit, string is valid
                    ret = -1
                elif ret == -1:
                    # cancel
                    self._widgets[0].string = ''
                    ret = -1
            elif char in self._global_functions or \
                    (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
                if l_char is None:
                    l_char = char
                self._global_functions[l_char]()
        #self._show_title()
        #self.show()
        return self._get_result(ret)


class PyRadioBuffering():
    _bitrate_manager = None

    _text = 'Buffer size in seconds: '
    _text128 = 'Buffer in KB @128kbps: '
    _text192 = '             @192kbps: '
    _text320 = '             @320kbps: '
    _help_text = ' Help '
    _note_text = ' Note '
    _max_lines = 12
    _cache_data  = None
    _big_step = _min = 5
    _max = 60

    def __init__(self,
                 buffering,
                 parent,
                 global_functions=None):
        logger.error('\n\nbuffering = {}\n\n'.format(buffering))
        self._buffering = buffering
        if '@' in buffering:
            self.buffering_value, self.bitrate_value = buffering.split('@')
        else:
            self.buffering_value = buffering
            self.bitrate_value = '128'
        if self.buffering_value != '0':
            try:
                if not (5 <= int(self.buffering_value) <= 60):
                    self.buffering_value = '0'
            except ValueError:
                self.buffering_value = '0'
        self._original_buffering_value = self.buffering_value
        self._parent = parent
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}
        self.recording = lambda: self._player.recording
        self._title = ' ' + M_STRINGS['station_buffering'] + ' '

    @property
    def bitrate_value(self):
        return self._bitrate_value
        return self._bitrate_manager.bitrate

    @bitrate_value.setter
    def bitrate_value(self, value):
        self._bitrate_value = value
        return
        if self._bitrate_manager is None:
            self._bitrate_manager = BitrateManager(value)
        else:
            self._bitrate_manager.bitrate = value

    def save(self):
        self._cache_data._save()

    def show(self, parent=None):
        if parent:
            self._parent = parent
        y, x = self._parent.getmaxyx()
        new_y = int((y - self._max_lines) / 2) + 1
        new_x = int((x - len(self._text) - 9 - 4) / 2)
        self.MaxX = len(self._text) + 9 + 4
        self._win = None
        if y < self._max_lines + 2 or x < self.MaxX + 2:
            self._win = curses.newwin(3, 20, int((y-2)/2), int((x - 20) / 2))
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()
            self._win.addstr(1, 2, 'Window too small', curses.color_pair(10))
        else:

            self._win = curses.newwin(self._max_lines, self.MaxX, new_y, new_x)
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()

            # show title
            x = int((self.MaxX - len(self._title)) / 2)
            self._win.addstr(0, x, self._title, curses.color_pair(11))

            # show content
            self._win.addstr(2, 4, self._text, curses.color_pair(10))
            self._win.addstr('{}'.format(self.buffering_value), curses.color_pair(11))

            # show help
            try:
                self._win.addstr(4, 2, '─' * (self.MaxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(4, 2, '─'.encode('utf-8') * (self.MaxX - 6), curses.color_pair(3))
            self._win.addstr(4, int((self.MaxX - len(self._help_text))/2), self._help_text, curses.color_pair(3))
            self._win.addstr(5, 2, kb2str('{j} {k} Up Down'), curses.color_pair(11))
            self._win.addstr(6, 2, 'PgUp PgDown', curses.color_pair(11))
            self._win.addstr('     Adjust value', curses.color_pair(10))
            self._win.addstr(7, 2, kb2chr('revert_saved'), curses.color_pair(11))
            self._win.addstr('               Load saved value', curses.color_pair(10))
            self._win.addstr(8, 2, kb2chr('no_buffer'), curses.color_pair(11))
            self._win.addstr('               No buffering', curses.color_pair(10))
            self._win.addstr(9, 2, 'Enter ' + kb2chr('s'), curses.color_pair(11))
            self._win.addstr('         Accept value', curses.color_pair(10))
            self._win.addstr(10, 2, kb2str('Esc {q} {h} Right'), curses.color_pair(11))
            self._win.addstr('   Cancel operation', curses.color_pair(10))
        self._win.refresh()

    def keypress(self, char):
        """ PyRadioBuffering keypress
            Returns:
                -1: Cancel  - None
                 0: go on   - None
                 1: Ok      = buffering parameters
        """
        l_char = None
        if char in self._global_functions or \
                (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
            if l_char is None:
                l_char = char
            self._global_functions[l_char]()

        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r'), kbkey['s']) or \
                check_localized(char, (kbkey['s'], )):
            return 1, self.buffering_value + '@' + self.bitrate_value

        elif char in (curses.KEY_EXIT, 27, kbkey['q'], kbkey['h'], curses.KEY_LEFT) or \
                check_localized(char, (kbkey['q'], kbkey['h'])):
            return -1, None

        elif char in (kbkey['j'], curses.KEY_UP,
                      kbkey['k'], curses.KEY_DOWN,
                      curses.KEY_NPAGE, curses.KEY_PPAGE,
                      kbkey['no_buffer'], kbkey['revert_saved']
                      ) or check_localized(char, (
                       kbkey['j'], kbkey['k'],
                       kbkey['no_buffer'], kbkey['revert_saved'])):
            delay = int(self.buffering_value)
            if char == kbkey['revert_saved'] or \
                    check_localized(char, (kbkey['revert_saved'], )):
                self.buffering_value = self._original_buffering_value
            elif char in (kbkey['k'], curses.KEY_UP) or \
                    check_localized(char, (kbkey['k'], )):
                delay += 1
                if delay < self._min:
                    delay = self._min
                if delay > self._max:
                    delay = self._max
                self.buffering_value = str(delay)
            elif char in (kbkey['j'], curses.KEY_DOWN) or \
                    check_localized(char, (kbkey['j'], )):
                delay -= 1
                if delay < self._min:
                    delay = 0
                self.buffering_value = str(delay)
            elif char == curses.KEY_NPAGE:
                delay -= self._big_step
                if delay < self._min:
                    delay = 0
                self.buffering_value = str(delay)
            elif char == curses.KEY_PPAGE:
                delay += self._big_step
                if delay > self._max:
                    delay = self._max
                self.buffering_value = str(delay)
            elif char == kbkey['no_buffer'] or \
                    check_localized(char, (kbkey['no_buffer'], )):
                self.buffering_value = '0'

            self._win.addstr(2, len(self._text) + 4, '{:<7}'.format(self.buffering_value), curses.color_pair(11))
            self._win.refresh()
        return 0, None


class BitrateManager:
    bitrates = (16, 24, 32, 48, 64, 96, 128, 160, 192, 256, 320, 700, 1411)

    def __init__(self, initial_bitrate: str):
        self._initial_bitrate = initial_bitrate
        self._current_bitrate = initial_bitrate

    @property
    def bitrate(self) -> str:
        return self._current_bitrate

    @bitrate.setter
    def bitrate(self, value: str):
        self._current_bitrate = value

    def next(self) -> str:
        current = int(self._current_bitrate)
        next_bitrates = [b for b in self.bitrates if b > current]
        if next_bitrates:
            self._current_bitrate = str(min(next_bitrates))
        return self._current_bitrate

    def previous(self) -> str:
        current = int(self._current_bitrate)
        previous_bitrates = [b for b in self.bitrates if b < current]
        if previous_bitrates:
            self._current_bitrate = str(max(previous_bitrates))
        return self._current_bitrate

    def reset(self) -> None:
        self._current_bitrate = self._initial_bitrate


class PyRadioConnectionType():

    _title = ' Connection Type '
    _text = 'Force http connections: '
    _help_text = ' Help '
    _note_text = ' Note '
    _max_lines = 14

    def __init__(self, parent, connection_type, global_functions=None):
        self._parent = parent
        self._global_functions = global_functions
        if self._global_functions is None:
            self._global_functions = {}
        self.connection_type = connection_type

    def show(self, parent=None):
        if parent:
            self._parent = parent
        y, x = self._parent.getmaxyx()
        new_y = int((y - self._max_lines) / 2) + 1
        new_x = int((x - len(self._text) - 9 - 4) / 2)
        self.MaxX = len(self._text) + 9 + 4
        self._win = None
        if y < self._max_lines + 2 or x < self.MaxX + 2:
            self._win = curses.newwin(3, 20, int((y-2)/2), int((x - 20) / 2))
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()
            self._win.addstr(1, 2, 'Window too small', curses.color_pair(10))
        else:

            self._win = curses.newwin(self._max_lines, self.MaxX, new_y, new_x)
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()

            # show title
            x = int((self.MaxX - len(self._title)) / 2)
            self._win.addstr(0, x, self._title, curses.color_pair(11))

            # show content
            self._win.addstr(2, 4, self._text, curses.color_pair(10))
            self._win.addstr('{}'.format(self.connection_type), curses.color_pair(11))

            # show help
            try:
                self._win.addstr(4, 2, '─' * (self.MaxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(4, 2, '─'.encode('utf-8') * (self.MaxX - 6), curses.color_pair(3))
            self._win.addstr(4, int((self.MaxX - len(self._help_text))/2), self._help_text, curses.color_pair(3))



            self._win.addstr(5, 2, kb2str('{j} {k} {l} {pause}'), curses.color_pair(11))
            self._win.addstr(6, 2, 'Right Up Down', curses.color_pair(11))
            self._win.addstr('    Toggle parameter', curses.color_pair(10))
            self._win.addstr(7, 2, 'Enter ' + kb2chr('s'), curses.color_pair(11))
            self._win.addstr('          Accept parameter', curses.color_pair(10))
            self._win.addstr(8, 2, kb2str('Esc {q} {h} Left'), curses.color_pair(11))
            self._win.addstr('    Cancel operation', curses.color_pair(10))

            # show note
            try:
                self._win.addstr(10, 2, '─' * (self.MaxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(10, 2, '─'.encode('utf-8') * (self.MaxX - 6), curses.color_pair(3))
            self._win.addstr(10, int((self.MaxX - len(self._note_text))/2), self._note_text, curses.color_pair(3))

            self._win.addstr(11, 4, 'Changes made here will not be', curses.color_pair(10))
            self._win.addstr(12, 3, 'saved in the configuration file', curses.color_pair(10))

        self._win.refresh()

    def keypress(self, char):
        """ PyRadioConnectionType keypress
            Returns:
                -1: Cancel
                 0: go on
                 1: Ok
        """
        l_char = None
        if char in self._global_functions or \
                (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
            if l_char is None:
                l_char = char
            self._global_functions[l_char]()

        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r'), kbkey['s']) or \
                check_localized(char, (kbkey['s'], )):
            return 1

        elif char in (curses.KEY_EXIT, 27, kbkey['q'], kbkey['h'], curses.KEY_LEFT) or \
                check_localized(char, (kbkey['q'], kbkey['h'])):
            return -1

        elif char in (kbkey['j'], kbkey['k'], kbkey['l'], kbkey['pause'],
                      curses.KEY_RIGHT, curses.KEY_UP, curses.KEY_DOWN) or \
                    check_localized(char, (kbkey['j'], kbkey['k'], kbkey['l'], kbkey['pause'])):
            self.connection_type = not self.connection_type
            self._win.addstr(2, len(self._text) + 3, '{}'.format(self.connection_type), curses.color_pair(3))
            self._win.refresh()

        return 0


class PyRadioServerWindow():

    _win = _editor = None

    _nips = None

    def __init__(
            self,
            parent,
            config,
            port_number_error_message=None,
            global_functions=None
    ):
        self._nips = IPsWithNumbers()
        self._cnf = config
        self._parent = parent
        self._win = None
        self._global_functions = global_functions
        self.maxY, self.maxX = (14, 55)
        self._get_window()
        self._showed = False
        self._selection = 0
        self._field_x = 4 +  len('Server Port: ')
        self._the_ip = self._nips.validate_ip(self._cnf.active_remote_control_server_ip)
        self._nips.set(self._the_ip)
        self._the_port = self._cnf.active_remote_control_server_port
        self._editor = None
        self._port_number_error_message = port_number_error_message

    def show(self, parent=None):
        if parent:
            self._parent = parent
            self._get_window()
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()
            self._show_title()

        if self._editor is None:
            self._editor = SimpleCursesLineEdit(
                parent=self._win,
                width=self._field_width,
                begin_y=self.Y + 5,
                begin_x=self.X + self._field_x,
                boxed=False,
                has_history=False,
                caption='',
                box_color=curses.color_pair(6),
                edit_color=curses.color_pair(6),
                cursor_color=curses.color_pair(8),
                unfocused_color=curses.color_pair(11),
                key_up_function_handler=self._toggle_selection,
                key_down_function_handler=self._toggle_selection,
            )
            self._editor.visible = True
            self._editor.bracket = False
            self._editor._use_paste_mode = False
            self._editor.set_global_functions(self._global_functions)
            self._editor._paste_mode = False
            self._editor.chars_to_accept = [ str(x) for x in range(0, 10)]
            self._editor.string = self._the_port


        self._win.addstr(2, 2, 'The server is ', curses.color_pair(10))
        self._win.addstr('not active', curses.color_pair(11))

        self._win.addstr(4, 4, '  Server IP: ', curses.color_pair(10))
        if self._selection == 0:
            self._win.addstr(self._the_ip.ljust(self._field_width, ' '), curses.color_pair(6))
        else:
            self._win.addstr(self._the_ip.ljust(self._field_width, ' '), curses.color_pair(10))
        self._win.addstr(5, 4, 'Server Port: ', curses.color_pair(10))

        try:
            self._win.addstr(7, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(7, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(7, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(11))
        self._win.addstr(8, 8, kb2chr('j'), curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr(kb2chr('k'), curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Up', curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Down', curses.color_pair(11))
        self._win.addstr(8, 30, 'Change selection.', curses.color_pair(10))

        self._win.addstr(9, 8, kb2chr('h'), curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr(kb2chr('l'), curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Left', curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Right', curses.color_pair(11))

        self._win.addstr(10, 8, 'Enter', curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr(kb2chr('pause'), curses.color_pair(11))
        self._win.addstr(10, 30, 'Toggle IP.', curses.color_pair(10))

        self._win.addstr(11, 8, kb2chr('s'), curses.color_pair(11))
        self._win.addstr(11, 30, 'Start the Server.', curses.color_pair(10))

        self._win.addstr(12, 2, 'Any other key will hide the window (not in editor).', curses.color_pair(10))

        self._editor.focused = False if self._selection == 0 else True
        self._refresh()
        self._showed = True

    def _refresh(self):
        self._win.refresh()
        self._editor.keep_restore_data()
        self._editor.show(self._win)

    def _get_window(self):
        self.max_parentY, self.max_parentX = self._parent.getmaxyx()
        self.Y = int((self.max_parentY - self.maxY)/ 2) + 1
        self.X = int((self.max_parentX -self.maxX)/ 2)
        self._win = curses.newwin(
            self.maxY, self.maxX,
            self.Y, self.X
        )
        self._field_width = self.maxX - len('Server Port: ') - 6
        if self._editor is not None:
            self._editor.move(self._win, self.Y + 5, self.X + self._field_x, update=False)

    def _show_title(self):
        msg = ' PyRadio Remote Control '
        self._win.addstr(0, int((self.maxX - len(msg)) / 2), msg, curses.color_pair(11))

    def _toggle_selection(self):
        if self._selection == 0:
            self._selection = 1
            self._editor.focused = True
            self._win.chgat(4, self._field_x, self._field_width, curses.color_pair(10))
        else:
            if self._validate_port():
                self._selection = 0
                self._editor.focused = False
                self._win.chgat(4, self._field_x, self._field_width, curses.color_pair(6))
            else:
                self._port_number_error_message()
        self._refresh()


    def _validate_port(self):
        if self._editor.string:
            x = int(self._editor.string)
            if 1025 <= x <= 65535:
                return True
        return False

    def keypress(self, char):
        ''' PyRadioServerWindow keypress
            Return
                -1: cancel
                 0: saved
                 1: go on
        '''
        l_char = None
        if self._selection == 0 and \
                (char in (ord('\n'), ord('\r'), curses.KEY_ENTER,
                         kbkey['pause'], kbkey['l'], curses.KEY_RIGHT) or \
                    check_localized(char, (kbkey['l'], kbkey['pause']))):
            self._the_ip = self._nips.next()
            self._win.addstr(4, self._field_x, self._the_ip.ljust(self._field_width), curses.color_pair(6))
            self._refresh()
        elif self._selection == 0 and \
                (char in (kbkey['h'], curses.KEY_LEFT) or \
                check_localized(char, (kbkey['h'], ))):
            self._the_ip = self._nips.previous()
            self._win.addstr(4, self._field_x, self._the_ip.ljust(self._field_width), curses.color_pair(6))
            self._refresh()

        elif char == kbkey['revert_saved'] or \
                check_localized(char, (kbkey['revert_saved'], )):
            self._the_ip = self._cnf.active_remote_control_server_ip
            self._nips.set(self._the_ip)
            self._the_port = self._cnf.active_remote_control_server_port
            self._editor.string = self._the_port
            self._refresh()

        elif char == kbkey['revert_def'] or \
                check_localized(char, (kbkey['revert_def'], )):
            self._the_ip = 'localhost'
            self._nips.set('localhost')
            self._the_port = '9998'
            self._editor.string = self._the_port
            self._refresh()

        elif char in (
            kbkey['j'], curses.KEY_UP,
            kbkey['k'], curses.KEY_DOWN
        ) or check_localized(char, (kbkey['j'], kbkey['k'])):
            self._toggle_selection()

        elif char == kbkey['s'] or \
                check_localized(char, (kbkey['s'], )):
            if self._validate_port():
                return 0
            else:
                self._port_number_error_message()

        elif self._editor.focused:
            ret = self._editor.keypress(self._win, char)
            if ret in (0, 1, 2):
                return 1
            return -1
        else:
            return -1

        return 1
