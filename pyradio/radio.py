# -*- coding: utf-8 -*-

# PyRadio: Curses based Internet Radio Player
# http://www.coderholic.com/pyradio
# Ben Dowling - 2009 - 2010
# Kirill Klenov - 2012
# Peter Stevenson (2E0PGS) - 2018
# Spiros Georgaras - 2018, 2023

import curses
import curses.ascii
import threading
import logging
import os
import random
import signal
from copy import deepcopy
from sys import version as python_version, version_info, platform
from os.path import join, basename, getmtime, getsize
from os import remove, rename
from platform import uname
from time import ctime, sleep
from datetime import datetime
from tempfile import gettempdir
import glob
import requests
try:
    import psutil
    HAVE_PSUTIL = True
except:
    HAVE_PSUTIL = False

from .config import HAS_REQUESTS, HAS_DNSPYTHON
from .common import *
from .window_stack import Window_Stack
from .config_window import *
from .log import Log
from .edit import PyRadioSearch, PyRadioEditor, PyRadioRenameFile, PyRadioConnectionType, PyRadioServerWindow
from .themes import *
from .cjkwrap import cjklen, cjkcenter, cjkslices
from . import player
from .install import version_string_to_list, get_github_tag, fix_pyradio_win_exe
from .html_help import HtmlHelp
from .browser import RadioBrowserConfig, RadioBrowserConfigWindow
from .schedule_win import PyRadioSimpleScheduleWindow
from .simple_curses_widgets import SimpleCursesMenu

CAN_CHECK_FOR_UPDATES = True
try:
    from urllib.request import urlopen
except:
    try:
        from urllib2 import urlopen
    except:
        CAN_CHECK_FOR_UPDATES = False

import locale
locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

from .server import IPs, PyRadioServer, HAS_NETIFACES

def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)

def is_ascii(s):
    return all(ord(c) < 128 for c in s)

def shift_only(event):
    if (event & curses.BUTTON_SHIFT) \
            and not (event & curses.BUTTON_CTRL) \
            and not (event & curses.BUTTON_ALT):
        return True
    else:
        return False

def ctrl_only(event):
    if (event & curses.BUTTON_CTRL) \
            and not (event & curses.BUTTON_SHIFT) \
            and not (event & curses.BUTTON_ALT):
        return True
    else:
        return False

def alt_only(event):
    if (event & curses.BUTTON_ALT) \
            and not (event & curses.BUTTON_SHIFT) \
            and not (event & curses.BUTTON_CTRL):
        return True
    else:
        return False

def alt_ctrl(event):
    if (event & curses.BUTTON_ALT) \
            and not (event & curses.BUTTON_SHIFT) \
            and (event & curses.BUTTON_CTRL):
        return True
    else:
        return False

def number_of_modifiers(event):
    ret = 0
    for a_mod in (curses.BUTTON_SHIFT,
                  curses.BUTTON_CTRL,
                  curses.BUTTON_ALT):
        if event & a_mod:
            ret += 1
    return ret

def no_modifiers(event):
    ret = number_of_modifiers(event)
    return True if ret == 0 else False

def multi_modifiers(event):
    return not no_modifiers(event)

def invalid_encoding(enc):
    try:
        'aaa'.encode(enc, 'replace')
    except LookupError:
        return True
    return False

def calc_can_change_colors(config):
    '''
    check if current terminal is "blacklisted"
    i.e. cannot display colors correctly
    '''
    if not curses.can_change_color():
        return False
    ret = True
    if curses.can_change_color() and curses.COLORS > 16:
        blacklisted_terminal = config.is_blacklisted_terminal()
        if blacklisted_terminal:
            ret = False
    if not ret:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('curses.can_change_color() : {}'.format(curses.can_change_color()))
            logger.debug('curses.COLORS: {}'.format(curses.COLORS))
            logger.debug('config.is_blacklisted_terminal(): {}'.format(blacklisted_terminal))
        if logger.isEnabledFor(logging.INFO):
            logger.info('Terminal can change colors: {}'.format(ret))
    return ret

class SelectPlayer(object):

    X = Y = maxX = maxY = 0
    _win = _parent = None


    def __init__(self, active_player, parent, recording, vlc_no_recording):
        self._players = {
            'mpv': '  MPV Media Player',
            'mplayer': '  MPlayer Media Player',
            'vlc': '  VLC Media Player',
        }
        self._selected = 0
        self._active_player = active_player
        self._recording = recording
        self._vlc_no_recording = vlc_no_recording
        self._no_vlc = False
        if recording > 0 and \
                platform.startswith('win'):
            self._players['vlc'] += ' (Not Supported)'
            self._no_vlc = True
        self._available_players = [x.PLAYER_NAME for x in player.available_players if x.PLAYER_NAME != self._active_player]
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('available players = {}'.format(player.available_players))
            logger.debug('players: active = {0}, available = {1}'.format(self._active_player, self._available_players))
        self.maxX = 45
        self.hline = 36
        self.maxY = 8 + len(self._available_players)
        self._get_window(parent)

    def _get_window(self, parent):
        self._parent = parent
        parent_maxY, parent_maxX = self._parent.getmaxyx()
        self.Y = int((parent_maxY - self.maxY) / 2) + 2
        self.X = int((parent_maxX - self.maxX) / 2)
        self._win = curses.newwin(
            self.maxY, self.maxX,
            self.Y, self.X
        )
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()

    def _print_header(self):
        txt_col = curses.color_pair(10)
        box_col = curses.color_pair(3)
        caption_col = curses.color_pair(11)
        header = ' Switch Media Player '
        X = int( ( self.maxX - len(header) ) / 2 )
        self._win.addstr(0, X, header, curses.color_pair(11))

    def show(self, parent=None):
        y = 0
        if parent is not None:
            self._get_window(parent)
        self._win.box()
        self._print_header()
        self._win.addstr(1, 2, 'Active Media Player: ', curses.color_pair(10))
        self._win.addstr(self._active_player, curses.color_pair(11))
        self._win.addstr(3, 2, 'Please select a Media Player to activate', curses.color_pair(10))
        for n in range(0, len(self._available_players)):
            y = 6 + n
            if self._selected == n:
                self._win.addstr(4+n, 4, self._players[self._available_players[n]].ljust(self.hline), curses.color_pair(6))
            else:
                self._win.addstr(4+n, 4, self._players[self._available_players[n]].ljust(self.hline), curses.color_pair(10))
        self._win.addstr(y, 2, 'and press ', curses.color_pair(10))
        self._win.addstr('s', curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Enter', curses.color_pair(11))
        self._win.addstr(' or ', curses.color_pair(10))
        self._win.addstr('Space', curses.color_pair(11))
        self._win.addstr(' to Switch to', curses.color_pair(10))
        self._win.addstr(y + 1, 2, 'it, or ', curses.color_pair(10))
        self._win.addstr('Escape', curses.color_pair(11))
        self._win.addstr(' to Cancel.', curses.color_pair(10))

        self._win.refresh()

    def _update_selection(self):
        if len(self._available_players) > 1:
            for n in range(0, len(self._available_players)):
                col = 6 if self._selected == n else 10
                self._win.chgat(4 + n, 4, self.hline, curses.color_pair(col))
            self._win.refresh()

    def keypress(self, char):
        if char in (
            ord('j'), curses.KEY_DOWN,
            ord('k'), curses.KEY_UP
        ):
            self._selected = 1 if self._selected == 0 else 0
            self._update_selection()
        elif char in (
            curses.KEY_ENTER,
            ord('\n'), ord('\r'),
            ord('s'), ord(' '),
            ord('l'), curses.KEY_RIGHT
        ):
            if not (self._no_vlc and \
                    self._available_players[self._selected] == 'vlc'):
                return self._available_players[self._selected]
            else:
                self._vlc_no_recording()
        elif char in (ord('h'), curses.KEY_LEFT,
                      ord('q'), curses.KEY_EXIT, 27):
            return None
        return ''

class PyRadio(object):
    player = None
    ws = Window_Stack()

    _i_am_resizing = False
    _redisplay_list = []

    ''' number of items (stations or playlists) in current view '''
    number_of_items = 0

    _playing = -1
    jumpnr = ''
    _backslash_pressed = False
    _register_assign_pressed = False
    _register_open_pressed = False
    ''' Help window
        also used for displaying messages,
        asking for confirmation etc. '''
    helpWinContainer = None
    helpWin = None

    ''' Window to display line number (jumpnr) '''
    transientWin = None

    ''' Used when loading new playlist.
        If the first station (selection) exists in the new playlist,
        we mark it as selected
        If the second station (playing) exists in the new playlist,
        we continue playing, otherwise, we stop playback '''
    active_stations = [['', 0], ['', -1]]

    ''' Used when loading a playlist from ''.
        If the first station (selection) exists in the new playlist,
        we mark it as selected
        If the second station (playing) exists in the new playlist,
        we continue playing, otherwise, we stop playback '''
    saved_active_stations = [['', 0], ['', -1]]

    ''' Used when opening a station after rename.
        If the first station (selection) exists in the new playlist,
        we mark it as selected
        If the second station (playing) exists in the new playlist,
        we continue playing, otherwise, we stop playback '''
    rename_stations = [['', 0], ['', -1]]

    ''' Characters to be "ignored" by windows, so that certain
        functions still work (like changing volume) '''
    # _chars_to_bypass = (ord('m'), ord('v'), ord('.'),
    #                     ord(','), ord('+'), ord('-'),
    #                     ord('?'), ord('#'), curses.KEY_RESIZE)
    _chars_to_bypass = (ord('?'), )

    ''' Characters to be "ignored" by windows that support search'''
    _chars_to_bypass_for_search = (ord('/'), ord('n'), ord('N'))

    ''' Characters to "ignore" when station editor window
        is onen and focus is not in line editor '''
    _chars_to_bypass_on_editor = (ord('m'), ord('v'), ord('.'),
                                  ord(','), ord('+'), ord('-'))
    ''' Number of stations to change with the page up/down keys '''
    pageChange = 5

    search = None

    _last_played_station = []

    _random_requested = False

    _theme = None
    _theme_name = 'dark'
    _theme_selector = None
    _theme_not_supported_thread = None
    _theme_not_supported_notification_duration = 1.75
    theme_forced_selection = []

    _config_win = None
    _browser_config_win = None
    _server_selection_window  = None
    _color_config_win = None

    _change_player = None
    _player_select_win = None
    _encoding_select_win = None
    _playlist_select_win = None
    _station_select_win = None
    _simple_schedule = None
    _old_config_encoding = ''

    ''' update notification '''
    _update_version = ''
    _update_version_do_display = ''
    _watch_theme_thread = _update_notification_thread = _update_stations_thread = None
    stop_watch_theme_thread = stop_update_notification_thread = False
    _watch_theme_lock = threading.Lock()
    _update_notify_lock = threading.Lock()
    _update_stations_lock = threading.Lock()
    _server_send_lock = threading.Lock()
    _recording_lock = threading.Lock()

    ''' editor class '''
    _station_editor = None
    _rename_playlist_dialog = None

    _force_exit = False

    _help_metrics = {}

    _playlist_error_message = ''

    _status_suffix = ''

    _unnamed_register = None

    _main_help_id = 0

    _station_rename_from_info = False

    ''' to get notification about stations
        update set it to 2
    '''
    _need_to_update_stations_csv = 3

    _limited_height_mode = False
    _limited_width_mode = False

    detect_if_player_exited = True

    _saved_colors = {}

    ''' It is False before running setupAndDrawScreen
        fir the first time. Then it is True...
    '''
    _screen_ready = False

    _last_html_song_title = ''

    _remote_control_window = None
    _group_selection_window = None

    def ll(self, msg):
        logger.error('DE ==========')
        logger.error('DE ===> {}'.format(msg))
        logger.error('DE NORMAL_MODE: {0}, {1}, {2}'.format(*self.selections[0]))
        logger.error('DE PLAYLIST_MODE: {0}, {1}, {2}'.format(*self.selections[1]))
        logger.error('DE REGISTER_MODE: {0}, {1}, {2}'.format(*self.selections[2]))

        logger.error('DE')
        logger.error('DE p NORMAL_MODE: {0}, {1}, {2}'.format(*self.playlist_selections[0]))
        logger.error('DE p PLAYLIST_MODE: {0}, {1}, {2}'.format(*self.playlist_selections[1]))
        logger.error('DE p REGISTER_MODE: {0}, {1}, {2}'.format(*self.playlist_selections[2]))

    def __init__(self, pyradio_config,
                 pre_select='False',
                 play='False',
                 req_player='',
                 theme='',
                 force_update='',
                 record=False):
        temp_dir = gettempdir()
        self._station_images = (
            join(temp_dir, 'station.jpg'),
            join(temp_dir, 'station.png'),
            join(temp_dir, 'station-icon.raw'),
        )

        self._request_recording = record
        self._no_netifaces = False
        self._current_selection = 0
        self._force_print_all_lines = False
        self._system_asked_to_terminate = False
        self._cnf = pyradio_config
        self._cnf.update_calculated_colors = self._update_calculated_colors
        self._theme = PyRadioTheme(self._cnf)
        self._force_update = force_update
        if theme:
            self._theme_name = theme
        ind = self._cnf.current_playlist_index()
        self.selections = [
            [0, 0, -1, self._cnf.stations],
            [ind, 0, ind, self._cnf.playlists],
            [0, 0, -1, self._cnf.playlists]]

        ''' To be used when togglind between playlists / registers
            index 0 not used
        '''
        self.playlist_selections = [[0, 0, -1],
                                    [0, 0, -1],
                                    [0, 0, -1]]
        # self.ll('__init__')
        self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
        # self.ll('begining...')
        self.play = play
        self._pre_select = pre_select
        self.stdscr = None
        self.requested_player = req_player
        self.number_of_items = len(self._cnf.stations)
        self._playlist_in_editor = self._cnf.station_path

        self._cnf.set_station_history(
            execute_funct=self._load_playlist_and_station_from_station_history,
            no_items_funct=self._show_no_station_history_notification,
            pass_first_item_funct=self._show_first_station_history_notification,
            pass_last_item_funct=self._show_last_station_history_notification
        )

        ''' list of functions to open for entering
        or redisplaying a mode '''
        self._redisplay = {
            self.ws.NOT_IMPLEMENTED_YET_MODE: self._print_not_implemented_yet,
            self.ws.NORMAL_MODE: self._redisplay_stations_and_playlists,
            self.ws.PLAYLIST_MODE: self._redisplay_stations_and_playlists,
            self.ws.CONFIG_MODE: self._redisplay_config,
            self.ws.SELECT_PLAYER_MODE: self._redisplay_player_select_win_refresh_and_resize,
            self.ws.SELECT_ENCODING_MODE: self._redisplay_encoding_select_win_refresh_and_resize,
            self.ws.SELECT_STATION_ENCODING_MODE: self._redisplay_encoding_select_win_refresh_and_resize,
            self.ws.SELECT_PLAYLIST_MODE: self._playlist_select_win_refresh_and_resize,
            self.ws.PASTE_MODE: self._playlist_select_paste_win_refresh_and_resize,
            self.ws.SELECT_STATION_MODE: self._redisplay_station_select_win_refresh_and_resize,
            self.ws.MAIN_HELP_MODE: self._show_main_help,
            self.ws.MAIN_HELP_MODE_PAGE_2: self._show_main_help_page_2,
            self.ws.MAIN_HELP_MODE_PAGE_3: self._show_main_help_page_3,
            self.ws.MAIN_HELP_MODE_PAGE_4: self._show_main_help_page_4,
            self.ws.MAIN_HELP_MODE_PAGE_5: self._show_main_help_page_5,
            self.ws.PLAYLIST_HELP_MODE: self._show_playlist_help,
            self.ws.THEME_HELP_MODE: self._show_theme_help,
            self.ws.CONFIG_HELP_MODE: self._show_config_help,
            self.ws.SELECT_PLAYER_HELP_MODE: self._show_config_player_help,
            self.ws.SELECT_PLAYLIST_HELP_MODE: self._show_config_playlist_help,
            self.ws.SELECT_STATION_HELP_MODE: self._show_config_station_help,
            self.ws.SESSION_LOCKED_MODE: self._print_session_locked,
            self.ws.UPDATE_NOTIFICATION_MODE: self._print_update_notification,
            self.ws.UPDATE_NOTIFICATION_OK_MODE: self._print_update_ok_notification,
            self.ws.UPDATE_NOTIFICATION_NOK_MODE: self._print_update_nok_notification,
            self.ws.SELECT_ENCODING_HELP_MODE: self._show_config_encoding_help,
            self.ws.SELECT_STATION_ENCODING_MODE: self._redisplay_encoding_select_win_refresh_and_resize,
            self.ws.EDIT_STATION_ENCODING_MODE: self._redisplay_encoding_select_win_refresh_and_resize,
            self.ws.PLAYLIST_NOT_FOUND_ERROR_MODE: self._print_playlist_not_found_error,
            self.ws.PLAYLIST_LOAD_ERROR_MODE: self._print_playlist_load_error,
            self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE: self._redisplay_print_save_modified_playlist,
            self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE: self._redisplay_print_save_modified_playlist,
            self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE: self._redisplay_print_save_modified_playlist,
            self.ws.PLAYLIST_RELOAD_CONFIRM_MODE: self._print_playlist_reload_confirmation,
            self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE: self._print_playlist_dirty_reload_confirmation,
            self.ws.PLAYLIST_RELOAD_ERROR_MODE: self._print_playlist_reload_error,
            self.ws.SAVE_PLAYLIST_ERROR_1_MODE: self._print_save_playlist_error_1,
            self.ws.SAVE_PLAYLIST_ERROR_2_MODE: self._print_save_playlist_error_2,
            self.ws.REMOVE_STATION_MODE: self._ask_to_remove_station,
            self.ws.REMOVE_GROUP_MODE: self._ask_to_remove_group,
            self.ws.FOREIGN_PLAYLIST_ASK_MODE: self._print_handle_foreign_playlist,
            self.ws.FOREIGN_PLAYLIST_MESSAGE_MODE: self._print_foreign_playlist_message,
            self.ws.FOREIGN_PLAYLIST_COPY_ERROR_MODE: self._print_foreign_playlist_copy_error,
            self.ws.SEARCH_NORMAL_MODE: self._redisplay_search_show,
            self.ws.SEARCH_PLAYLIST_MODE: self._redisplay_search_show,
            self.ws.SEARCH_THEME_MODE: self._redisplay_search_show,
            self.ws.SEARCH_SELECT_STATION_MODE: self._redisplay_search_show,
            self.ws.SEARCH_SELECT_PLAYLIST_MODE: self._redisplay_search_show,
            self.ws.GROUP_SEARCH_MODE: self._redisplay_search_show,
            self.ws.THEME_MODE: self._redisplay_theme_mode,
            self.ws.PLAYLIST_RECOVERY_ERROR_MODE: self._print_playlist_recovery_error,
            self.ws.ASK_TO_CREATE_NEW_THEME_MODE: self._redisplay_ask_to_create_new_theme,
            self.ws.SEARCH_HELP_MODE: self._show_search_help,
            self.ws.ADD_STATION_MODE: self._show_station_editor,
            self.ws.EDIT_STATION_MODE: self._show_station_editor,
            self.ws.LINE_EDITOR_HELP_MODE: self._show_line_editor_help,
            self.ws.EDIT_STATION_NAME_ERROR: self._print_editor_name_error,
            self.ws.EDIT_STATION_URL_ERROR: self._print_editor_url_error,
            self.ws.EDIT_STATION_ICON_URL_ERROR: self._print_icon_url_error,
            self.ws.EDIT_STATION_ICON_FORMAT_ERROR: self._print_icon_url_format_error,
            self.ws.PY2_EDITOR_ERROR: self._print_py2_editor_error,
            self.ws.REQUESTS_MODULE_NOT_INSTALLED_ERROR: self._print_requests_not_installed_error,
            self.ws.NETIFACES_MODULE_NOT_INSTALLED_ERROR: self._print_netifaces_not_installed_error,
            self.ws.DNSPYTHON_MODULE_NOT_INSTALLED_ERROR: self._print_dnspython_not_installed_error,
            self.ws.CLEAR_REGISTER_MODE: self._print_clear_register,
            self.ws.CLEAR_ALL_REGISTERS_MODE: self._print_clear_all_registers,
            self.ws.REGISTER_HELP_MODE: self._show_register_help,
            self.ws.EXTRA_COMMANDS_HELP_MODE: self._show_extra_commands_help,
            self.ws.YANK_HELP_MODE: self._show_yank_help,
            self.ws.STATION_INFO_ERROR_MODE: self._print_station_info_error,
            self.ws.STATION_INFO_MODE: self._show_station_info,
            self.ws.STATION_DATABASE_INFO_MODE: self._browser_station_info,
            self.ws.RENAME_PLAYLIST_MODE: self._show_rename_dialog,
            self.ws.CREATE_PLAYLIST_MODE: self._show_rename_dialog,
            self.ws.PLAYLIST_COPY_ERROR: self._print_playlist_copy_error,
            self.ws.PLAYLIST_RENAME_ERROR: self._print_playlist_rename_error,
            self.ws.PLAYLIST_CREATE_ERROR: self._print_playlist_create_error,
            self.ws.PLAYLIST_NOT_SAVED_ERROR_MODE: self._print_playlist_not_saved_error,
            self.ws.CONNECTION_MODE: self._show_http_connection,
            self.ws.UNNAMED_REGISTER_MODE: self._show_unnamed_register,
            self.ws.PROFILE_EDIT_DELETE_ERROR_MODE: self._print_default_profile_edit_delete_error,
            self.ws.MAXIMUM_NUMBER_OF_PROFILES_ERROR_MODE: self._print_max_number_of_profiles_error,
            self.ws.PLAYER_PARAMS_MODE: self._redisplay_player_select_win_refresh_and_resize,
            self.ws.MOUSE_RESTART_INFO_MODE: self._print_mouse_restart_info,
            self.ws.IN_PLAYER_PARAMS_EDITOR: self._redisplay_player_select_win_refresh_and_resize,
            self.ws.USER_PARAMETER_ERROR: self._print_user_parameter_error,
            self.ws.IN_PLAYER_PARAMS_EDITOR_HELP_MODE: self._show_params_ediror_help,
            self.ws.VOTE_RESULT_MODE: self._print_vote_result,
            self.ws.BROWSER_SEARCH_MODE: self._browser_search,
            self.ws.BROWSER_SORT_MODE: self._browser_sort,
            self.ws.BROWSER_SERVER_SELECTION_MODE: self._browser_server_selection,
            self.ws.SERVICE_CONNECTION_ERROR: self._print_service_connection_error,
            self.ws.BROWSER_OPEN_MODE: self._show_connect_to_server_message,
            self.ws.RADIO_BROWSER_SEARCH_HELP_MODE: self._show_radio_browser_search_help,
            self.ws.RADIO_BROWSER_CONFIG_HELP_MODE: self._show_radio_browser_config_help,
            self.ws.BROWSER_PERFORMING_SEARCH_MODE: self._show_performing_search_message,
            self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER: self._ask_to_save_browser_config_from_config,
            self.ws.RADIO_BROWSER_CONFIG_MODE: self._redisplay_browser_config,
            self.ws.BROWSER_CONFIG_SAVE_ERROR_MODE: self._print_browser_config_save_error,
            self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG: self._ask_to_save_browser_config_from_config,
            self.ws.SERVICE_SERVERS_UNREACHABLE: self._print_servers_unreachable,
            self.ws.ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT: self._ask_to_save_browser_config_to_exit,
            self.ws.WIN_MANAGE_PLAYERS_MSG_MODE: self._show_win_manage_players,
            self.ws.WIN_PRINT_EXE_LOCATION_MODE: self._show_win_print_exe_paths,
            self.ws.UNKNOWN_BROWSER_SERVICE_ERROR: self._print_unknown_browser_service,
            self.ws.SCHEDULE_PLAYER_STOP_MODE: self._show_schedule_player_stop,
            self.ws.SCHEDULE_PLAYER_STOP_HELP_MODE: self._show_schedule_player_stop_help,
            self.ws.NO_THEMES_MODE: self._show_no_themes,
            self.ws.REMOTE_CONTROL_SERVER_START_ERROR_MODE: self._print_remote_control_server_error,
            self.ws.REMOTE_CONTROL_SERVER_DEAD_ERROR_MODE: self._print_remote_control_server_dead_error,
            self.ws.REMOTE_CONTROL_SERVER_ACTIVE_MODE: self._show_remote_control_server_active,
            self.ws.REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE: self._show_remote_control_server_not_active,
            self.ws.REMOTE_CONTROL_SERVER_ERROR_MODE: self._show_remote_control_error,
            self.ws.CHANGE_PLAYER_SAME_PLAYER_ERROR_MODE: self._print_change_player_same_player_error,
            self.ws.CHANGE_PLAYER_ONE_PLAYER_ERROR_MODE: self._print_change_player_one_player_error,
            self.ws.CHANGE_PLAYER_MODE: self._redisplay_select_player,
            self.ws.UPDATE_STATIONS_CSV_RESULT_MODE: self._update_stations_result,
            self.ws.ASK_TO_UPDATE_STATIONS_CSV_MODE: self._ask_to_update_stations_csv,
            self.ws.GROUP_SELECTION_MODE: self._show_group_selection,
            self.ws.GROUP_HELP_MODE: self._show_group_help,
            self.ws.RECORD_WINDOW_MODE: self._show_recording_toggle_window,
            self.ws.WIN_VLC_NO_RECORD_MODE: self._show_win_no_record,
        }

        ''' list of help functions '''
        self._display_help = {
            self.ws.NORMAL_MODE: self._show_main_help,
            self.ws.PLAYLIST_MODE: self._show_playlist_help,
            self.ws.THEME_MODE: self._show_theme_help,
            self.ws.SEARCH_NORMAL_MODE: self._show_search_help,
            self.ws.SEARCH_PLAYLIST_MODE: self._show_search_help,
            self.ws.CONFIG_MODE: self._show_config_help,
            self.ws.SELECT_PLAYER_MODE: self._show_config_player_help,
            self.ws.SELECT_PLAYLIST_MODE: self._show_config_playlist_help,
            self.ws.PASTE_MODE: self._show_config_playlist_help,
            self.ws.SELECT_STATION_MODE: self._show_config_station_help,
            self.ws.SELECT_STATION_ENCODING_MODE: self._show_config_encoding_help,
            self.ws.SELECT_ENCODING_MODE: self._show_config_encoding_help,
            self.ws.EDIT_STATION_ENCODING_MODE: self._show_config_encoding_help,
            self.ws.LINE_EDITOR_HELP_MODE: self._show_line_editor_help,
            self.ws.REGISTER_HELP_MODE: self._show_register_help,
            self.ws.EXTRA_COMMANDS_HELP_MODE: self._show_extra_commands_help,
            self.ws.YANK_HELP_MODE: self._show_yank_help,
            self.ws.PROFILE_EDIT_DELETE_ERROR_MODE: self._print_default_profile_edit_delete_error,
            self.ws.MAXIMUM_NUMBER_OF_PROFILES_ERROR_MODE: self._print_max_number_of_profiles_error,
            self.ws.PLAYER_PARAMS_MODE: self._show_config_player_help,
            self.ws.IN_PLAYER_PARAMS_EDITOR: self._show_params_ediror_help,
            self.ws.RADIO_BROWSER_SEARCH_HELP_MODE: self._show_radio_browser_search_help,
            self.ws.RADIO_BROWSER_CONFIG_HELP_MODE: self._show_radio_browser_config_help,
            self.ws.BROWSER_CONFIG_SAVE_ERROR_MODE: self._print_browser_config_save_error,
            self.ws.GROUP_HELP_MODE: self._show_group_help,
        }

        ''' search classes
            0 - station search
            1 - playlist search
            2 - theme search
            3 - paste mode
            4 - group selection
        '''
        self._search_classes = [None, None, None, None, None]

        ''' the files that the search terms are stored to  '''
        self._search_files = (
                path.join(self._cnf.data_dir, 'search-station.txt'),
                path.join(self._cnf.data_dir, 'search-playlist.txt'),
                path.join(self._cnf.data_dir, 'search-theme.txt'),
                path.join(self._cnf.data_dir, 'search-paste.txt'),
                path.join(self._cnf.data_dir, 'search-group.txt'),
                )

        ''' points to list in which the search will be performed '''
        self._search_list = []

        ''' points to _search_classes for each supported mode '''
        self._mode_to_search = {
            self.ws.NORMAL_MODE: 0,
            self.ws.SELECT_STATION_MODE: 0,
            self.ws.PLAYLIST_MODE: 1,
            self.ws.SELECT_PLAYLIST_MODE: 1,
            self.ws.THEME_MODE: 2,
            self.ws.PASTE_MODE: 3,
            self.ws.GROUP_SELECTION_MODE: 4,
        }

        ''' which search mode opens from each allowed mode '''
        self._search_modes = {
            self.ws.NORMAL_MODE: self.ws.SEARCH_NORMAL_MODE,
            self.ws.PLAYLIST_MODE: self.ws.SEARCH_PLAYLIST_MODE,
            self.ws.THEME_MODE: self.ws.SEARCH_THEME_MODE,
            self.ws.SELECT_PLAYLIST_MODE: self.ws.SEARCH_SELECT_PLAYLIST_MODE,
            self.ws.PASTE_MODE: self.ws.SEARCH_SELECT_PLAYLIST_MODE,
            self.ws.SELECT_STATION_MODE: self.ws.SEARCH_SELECT_STATION_MODE,
            self.ws.GROUP_SELECTION_MODE: self.ws.GROUP_SEARCH_MODE,
        }

        ''' search modes opened from main windows '''
        self.search_main_window_modes = (
            self.ws.SEARCH_NORMAL_MODE,
            self.ws.SEARCH_PLAYLIST_MODE,
        )

        ''' volume functions '''
        self.volume_functions = {
            '+': self._volume_up,
            '=': self._volume_up,
            '.': self._volume_up,
            '-': self._volume_down,
            ',': self._volume_down,
            'v': self._volume_save
        }

        self.buttons = {
            curses.BUTTON1_CLICKED: 'BUTTON1_CLICKED',
            curses.BUTTON1_DOUBLE_CLICKED: 'BUTTON1_DOUBLE_CLICKED',
            curses.BUTTON1_PRESSED: 'BUTTON1_PRESSED',
            curses.BUTTON1_RELEASED: 'BUTTON1_RELEASED',
            curses.BUTTON1_TRIPLE_CLICKED: 'BUTTON1_TRIPLE_CLICKED',
            curses.BUTTON2_CLICKED: 'BUTTON2_CLICKED',
            curses.BUTTON2_DOUBLE_CLICKED: 'BUTTON2_DOUBLE_CLICKED',
            curses.BUTTON2_PRESSED: 'BUTTON2_PRESSED',
            curses.BUTTON2_RELEASED: 'BUTTON2_RELEASED',
            curses.BUTTON2_TRIPLE_CLICKED: 'BUTTON2_TRIPLE_CLICKED',
            curses.BUTTON3_CLICKED: 'BUTTON3_CLICKED',
            curses.BUTTON3_DOUBLE_CLICKED: 'BUTTON3_DOUBLE_CLICKED',
            curses.BUTTON3_PRESSED: 'BUTTON3_PRESSED',
            curses.BUTTON3_RELEASED: 'BUTTON3_RELEASED',
            curses.BUTTON3_TRIPLE_CLICKED: 'BUTTON3_TRIPLE_CLICKED',
            curses.BUTTON4_CLICKED: 'BUTTON4_CLICKED',
            curses.BUTTON4_DOUBLE_CLICKED: 'BUTTON4_DOUBLE_CLICKED',
            curses.BUTTON4_PRESSED: 'BUTTON4_PRESSED',
            curses.BUTTON4_RELEASED: 'BUTTON4_RELEASED',
            curses.BUTTON4_TRIPLE_CLICKED: 'BUTTON4_TRIPLE_CLICKED',
            curses.BUTTON_ALT: 'BUTTON_ALT',
            curses.BUTTON_CTRL: 'BUTTON_CTRL',
            curses.BUTTON_SHIFT: 'BUTTON_SHIFT',
        }

        self._global_functions = {
            ord('w'): self._tag_a_title,
            ord('W'): self._toggle_titles_logging,
            ord('T'): self._toggle_transparency,
            ord('+'): self._volume_up,
            ord('='): self._volume_up,
            ord('.'): self._volume_up,
            ord('-'): self._volume_down,
            ord(','): self._volume_down,
            ord('m'): self._volume_mute,
            ord('v'): self._volume_save,
            ord('~'): self._toggle_claculated_colors,
            ord('<'): self._stations_history_previous,
            ord('>'): self._stations_history_next,
            curses.ascii.DLE: self._play_previous_station,
            curses.KEY_PREVIOUS: self._play_previous_station,
            curses.ascii.SO: self._play_next_station,
            curses.KEY_NEXT: self._play_next_station,
            # ord('d'): self._html_song_title,
            # ord('b'): self._show_schedule_player_stop,
        }

        self._remote_control_server = self._remote_control_server_thread = None

        self._cls_update_stations = None
        self._cls_update_stations_message = ''


    def __del__(self):
        self.transientWin = None

    @property
    def playing(self):
        return self._playing

    @playing.setter
    def playing(self, value):
        # logger.error('-------')
        self._playing = value
        self._update_history_positions_in_list()

    def _save_colors(self):
        if self._cnf.use_themes:
            for i in range(0, 16):
                try:
                    self._saved_colors[i] = curses.color_content(i)
                except:
                    return

    def _text_info(self):
        out = []
        out.append('PyRadio {}'.format(self._cnf.current_pyradio_version))
        out.append('Player: {}'.format(self.player.PLAYER_NAME))
        out.append('Playlist: "{}"'.format(basename(self._playlist_in_editor)[:-4]))
        if self.player.isPlaying():
            out.append('Status: In playback {}'.format('(muted)' if self.player.muted else ''))
            out.append('  Station (id={0}): "{1}"'.format(self.playing+1, self.stations[self.playing][0]))
        else:
            out.append('Status: Idle')
        out.append('Selection (id={0}): "{1}"'.format(self.selection+1, self.stations[self.selection][0]))
        return '\n'.join(out)

    def _html_info(self):
        out = []
        out.append('<div class="alert alert-info">')
        out.append('<b>PyRadio {}</b><br>'.format(self._cnf.current_pyradio_version))
        out.append('<span style="padding-left: 1em;">Player: <b>{}</b></span><br>'.format(self.player.PLAYER_NAME))
        out.append('<span style="padding-left: 1em;">Playlist: <b>{}</b></span><br>'.format(basename(self._playlist_in_editor)[:-4]))
        if self.player.isPlaying():
            out.append('<span style="padding-left: 1em;">Status: <b>In playback {}</b></span><br>'.format('(muted)' if self.player.muted else ''))
            out.append('<span style="padding-left: 1em;">Station: <b>{}</b></span><br>'.format(self.stations[self.playing][0]))
        else:
            out.append('<span style="padding-left: 1em;">Status: <b>Idle</b></span><br>')
            out.append('<span style="padding-left: 1em;">Selection: <b>{}</b></span><br>'.format(self.stations[self.selection][0]))
        out.append('</div>')
        return '\n'.join(out)

    def _set_text_volume(self, vol):
        if self.player.isPlaying() and \
                not self.player.muted:
            ivol = int(vol)
            self.player.set_volume(vol)
            sleep(.1)
            return 'Volume set to: {}'.format(vol)
        else:
             if self.player.muted:
                 return 'Player is Muted!'
             else:
                 return 'Player is Idle!'

    def _get_text_volume(self):
        if self.player.isPlaying() and \
                not self.player.muted:
            self.player.get_volume()
            if self.player.PLAYER_NAME == 'vlc':
                return 'Volume: {}'.format(int(round(100*int(self.player.volume)/self.player.max_volume)))
            else:
                return 'Volume: {}'.format(self.player.volume)
        else:
             if self.player.muted:
                 return 'Player is Muted!'
             else:
                 return 'Player is Idle!'

    def _html_init_song_title(self):
        self._html_song_title()

    def _html_song_title(self):
        if self._remote_control_server:
            title = self.log.song_title
            if not title:
                title = self.log.station_that_is_playing_now
                if title:
                    title = 'Playing: ' + title
            if not title:
                if not self.player.isPlaying():
                    title =  'Player is stopped!'
                else:
                    title = 'No Title'
            # return title
            self._remote_control_server.send_song_title(title)

    def restore_colors(self):
        if self._cnf.use_themes:
            for i in range(0,16):
                try:
                    curses.init_color(
                        i,
                        self._saved_colors[i][0],
                        self._saved_colors[i][1],
                        self._saved_colors[i][2]
                    )
                except:
                    return

    def setup(self, stdscr):
        if logger.isEnabledFor(logging.INFO):
            ver = self._cnf.get_pyradio_version()
            logger.info('<<<===---  Program start  ---===>>>')
            if self._cnf.distro == 'None':
                logger.info('PyRadio {0}: TUI initialization on python v. {1} on "{2}"'.format(self._cnf.current_pyradio_version, python_version.replace('\n', ' ').replace('\r', ' '), ', '.join(uname())))
            else:
                logger.info('PyRadio {0}: TUI initialization on python v. {1} on {2} ({3})'.format(self._cnf.current_pyradio_version, python_version.replace('\n', ' ').replace('\r', ' '), self._cnf.distro, ', '.join(uname())))
        self.setup_return_status = True
        if not curses.has_colors():
            self.setup_return_status = False
            return
        curses.start_color()
        curses.use_default_colors()

        self._group_color_normal = 2
        self._group_color_active = 9

        if self._cnf.use_themes:
            self._cnf.use_themes = calc_can_change_colors(self._cnf)
        #self._cnf.use_themes = False
        self._save_colors()
        # curses.savetty()
        if not self._cnf.use_themes:
            self._cnf.change_to_no_theme_mode(self._show_colors_cannot_change)
        else:
            if curses.COLORS > 32:
                self._cnf.start_colors_at = 15
            logger.info('Terminal supports {0} colors (first color to define = {1})'.format(curses.COLORS, self._cnf.start_colors_at))
        self.stdscr = stdscr

        try:
            curses.curs_set(0)
        except:
            pass

        if self._cnf.use_themes:
            # TODO: maybe delete this line?
            self._theme._transparent = self._cnf.use_transparency
            self._theme.config_dir = self._cnf.stations_dir
            ''' In case we have to download a theme, and it takes too long  '''
            if not self._cnf.locked:
                if self._cnf.is_project_theme:
                    stdscr.addstr(0, 0, 'Downloading default theme...', curses.color_pair(0))
                    stdscr.refresh()
            ret, ret_theme_name = self._theme.readAndApplyTheme(self._theme_name, print_errors=stdscr)
            if ret == 0:
                self._theme_name = self._theme.applied_theme_name
                self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
                self._update_calculated_colors()
            else:
                self._theme_name = ret_theme_name
                self._cnf.theme_not_supported = True
                self._cnf.theme_has_error = True if ret == -1 else False
                if self._cnf.is_project_theme:
                    stdscr.addstr('\nTheme download failed...', curses.color_pair(0))
                    stdscr.refresh()
                    sleep(1)

        rev = self._cnf.get_pyradio_version()
        if logger.isEnabledFor(logging.INFO) and rev:
            logger.info(rev)

        self.log = Log(self._cnf, lambda: self._remote_control_server)
        self.log.can_display_help_msg = self._can_display_help_msg
        ''' For the time being, supported players are mpv, mplayer and vlc. '''
        try:
            self.player = player.probePlayer(
                requested_player=self.requested_player)(
                    self._cnf,
                    self.log,
                    self.playbackTimeoutCounter,
                    self.connectionFailed,
                    self._show_station_info_from_thread,
                    self._add_station_to_stations_history,
                    self._recording_lock
                )
            if self._request_recording:
                if not (platform.startswith('win') and \
                        self.player.PLAYER_NAME == 'vlc'):
                    self.player.recording = 1
                else:
                    self.ws.operation_mode = self.ws.WIN_VLC_NO_RECORD_MODE
        except:
            ''' no player '''
            self.ws.operation_mode = self.ws.NO_PLAYER_ERROR_MODE

        self._cls_update_stations = StationsChanges(self._cnf)
        if self.ws.operation_mode != self.ws.NO_PLAYER_ERROR_MODE:
            if self._cnf.command_line_params_not_ready is not None:
                self._cnf.command_line_params = self._cnf.command_line_params_not_ready
            else:
                if self._cnf.backup_player_params is None:
                    self._cnf.init_backup_player_params()

            ''' activate user specified player parameter set '''
            if self._cnf.user_param_id > 0:
                if self.set_param_set_by_id(self._cnf.user_param_id):
                    self._cnf.user_param_id = 0
                else:
                    self._cnf.user_param_id = -1

            if self._cnf.remote_control_server_auto_start and \
                    not self._cnf.locked:
                self._start_remote_control_server()

        self.stdscr.nodelay(0)
        self.setupAndDrawScreen(init_from_setup=True)
        self._screen_ready = True

        ''' position playlist in window '''
        try:
            self.outerBodyMaxY, self.outerBodyMaxX = self.outerBodyWin.getmaxyx()
            self.bodyMaxY, self.bodyMaxX = self.bodyWin.getmaxyx()
        except:
            pass
        try:
            if self.selections[self.ws.PLAYLIST_MODE][0] < self.bodyMaxY:
                self.selections[self.ws.PLAYLIST_MODE][1] = 0
            elif self.selections[self.ws.PLAYLIST_MODE][0] > len(self._cnf.playlists) - self.bodyMaxY + 1:
                # TODO make sure this is ok
                self.selections[self.ws.PLAYLIST_MODE][1] = len(self._cnf.playlists) - self.bodyMaxY
            else:
                self.selections[self.ws.PLAYLIST_MODE][1] = self.selections[self.ws.PLAYLIST_MODE][0] - int(self.bodyMaxY/2)
        except:
            self.selections[self.ws.PLAYLIST_MODE][1] = 0
        self.playlist_selections[self.ws.PLAYLIST_MODE] = self.selections[self.ws.PLAYLIST_MODE][:-1][:]
        self.ll('setup')
        self.run()

    def change_player(self, a_player):
        if a_player == self.player.PLAYER_NAME:
            pass
        else:
            for a_available_player in player.available_players:
                if a_player == a_available_player.PLAYER_NAME:
                    new_player = a_player(
                        self._cnf,
                        self.log,
                        self.playbackTimeoutCounter,
                        self.connectionFailed,
                        self._show_station_info_from_thread,
                        self._add_station_to_stations_history
                    )
        if new_player:
            pass
        else:
            pass

    def _redraw(self):
        self.footerWin.noutrefresh()
        self.outerBodyWin.noutrefresh()
        self.bodyWin.noutrefresh()
        # self.txtWin.noutrefresh()

    def setupAndDrawScreen(self, init_from_setup=False):
        self._limited_height_mode = False
        self.maxY, self.maxX = self.stdscr.getmaxyx()

        self.headWin = None
        self.bodyWin = None
        self.outerBodyWin = None
        self.footerWin = None
        self.footerWin = curses.newwin(1, self.maxX, self.maxY - 1, 0)
        self.headWin = curses.newwin(1, self.maxX, 0, 0)

        # logger.error('DE maxY = {0}, maxX = {1}'.format(self.maxY, self.maxX))
        #if self.maxY < 8 or self.maxX < 20:
        if self.maxY < 8:
            self._print_limited_info()
        else:
            self.outerBodyWin = curses.newwin(self.maxY - 2, self.maxX, 1, 0)
            #self.bodyWin = curses.newwin(self.maxY - 2, self.maxX, 1, 0)
            self.bodyWinStartY = 2 + self._cnf.internal_header_height
            self.bodyWinEndY = self.maxY - 1
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('body starts at line {0}, ends at line {1}'.format(self.bodyWinStartY, self.bodyWinEndY))
            self.bodyWin = self.outerBodyWin.subwin(
                self.maxY - 4 - self._cnf.internal_header_height,
                self.maxX - 2,
                self.bodyWinStartY,
                1)

            ''' set browser parent so that ir resizes correctly '''
            if self._cnf.browsing_station_service:
                self._cnf._online_browser.outer_parent = self.outerBodyWin
                self._cnf._online_browser.parent = self.bodyWin

            # txtWin used mainly for error reports
            self.txtWin = None
            try:
                self.txtWin = curses.newwin(self.maxY - 4, self.maxX - 4, 2, 2)
            except:
                pass
            if not self._limited_height_mode:
                self.initHead(self._cnf.info)
            ''' for light color scheme '''
            # TODO
            self.outerBodyWin.bkgdset(' ', curses.color_pair(13))
            self.outerBodyWin.erase()
            self.bodyWin.bkgdset(' ', curses.color_pair(13))
            self.initBody()

        #self.stdscr.timeout(100)
        self.bodyWin.keypad(1)

        #self.stdscr.noutrefresh()

        self.initFooter()
        self.log.setScreen(self.footerWin)
        if init_from_setup:
            if self.player:
                self.log.write(msg='Selected player: ' + self.player.PLAYER_NAME, help_msg=True)
        else:
            self.footerWin.refresh()
        # self._redraw()
        # logger.error('1 redraw')
        curses.doupdate()

    def _print_limited_info(self):
        self._limited_height_mode = True
        if self.maxY == 1:
            self.bodyWin = self.footerWin
        else:
            ''' this is so that on windows I will not crash '''
            try:
                self.bodyWin = curses.newwin(
                    self.maxY - 1, self.maxX, 0, 0)
            except:
                return

            self.bodyWin.bkgdset(' ', curses.color_pair(5))
            self.bodyWin.erase()
            if self.player.isPlaying():
                try:
                    if self.player.recording and self.player.recording_filename:
                        self.bodyWin.addstr(self.maxY - 2, 0, ' Recording Station: ', curses.color_pair(5))
                    else:
                        self.bodyWin.addstr(self.maxY - 2, 0, ' Station: ', curses.color_pair(5))
                    self.bodyWin.addstr(self._last_played_station[0], curses.color_pair(4))
                except:
                    pass
            else:
                try:
                    self.bodyWin.addstr(self.maxY - 2, 0, ' Status: ', curses.color_pair(5))
                    self.bodyWin.addstr('Idle', curses.color_pair(4))
                    if self.player.recording:
                        self.bodyWin.addstr(' (', curses.color_pair(5))
                        self.bodyWin.addstr('recording enabled', curses.color_pair(4))
                        self.bodyWin.addstr(')', curses.color_pair(5))
                except:
                    pass
            if self.maxY - 3 >= 0:
                try:
                    if self._cnf.browsing_station_service:
                        self.bodyWin.addstr(self.maxY - 3, 0, ' Service: ', curses.color_pair(5))
                    else:
                        self.bodyWin.addstr(self.maxY - 3, 0, ' Playlist: ', curses.color_pair(5))
                    self.bodyWin.addstr(self._cnf.station_title, curses.color_pair(4))
                except:
                    pass
            if self.maxY - 4 >= 0:
                try:
                    self._cnf.get_pyradio_version(),
                    self.bodyWin.addstr(self.maxY - 4, 0, 'PyRadio ' + self._cnf.current_pyradio_version, curses.color_pair(4))
                except:
                    pass

            self.bodyMaxY, self.bodyMaxX = self.bodyWin.getmaxyx()
            self.bodyWin.refresh()

    def initHead(self, info):
        self.headWin.hline(0, 0, ' ', self.maxX, curses.color_pair(5))
        try:
            self.headWin.addstr(0, 0, info, curses.color_pair(4))
            if self._cnf.locked:
                self.headWin.addstr('[', curses.color_pair(4))
                self.headWin.addstr('Session Locked', curses.color_pair(4))
                self.headWin.addstr('] ', curses.color_pair(4))
            else:
                self.headWin.addstr(' ', curses.color_pair(4))
        except:
            pass
        # if self.maxX - len() > len(rightStr)
        _, curX = self.headWin.getyx()
        rightStr = " https://github.com/coderholic/pyradio"
        if self.maxX - curX > len(rightStr) + 3:
            try:
                self.headWin.addstr(
                    0, self.maxX - len(rightStr) -1,
                    rightStr, curses.color_pair(2)
                )
            except:
                pass
        # self.headWin.bkgd(' ', curses.color_pair(5))
        self.headWin.noutrefresh()

    def initBody(self):
        ''' Initializes the body/story window '''
        #self.bodyWin.timeout(100)
        #self.bodyWin.keypad(1)
        self.bodyMaxY, self.bodyMaxX = self.bodyWin.getmaxyx()
        logger.debug('maxY = {0}, maxX = {1}'.format(self.bodyMaxY, self.bodyMaxX))
        self.outerBodyMaxY, self.outerBodyMaxX = self.outerBodyWin.getmaxyx()
        self.bodyWin.noutrefresh()
        self.outerBodyWin.noutrefresh()
        if not HAVE_PSUTIL:
            self.ws.operation_mode = self.ws.DEPENDENCY_ERROR
            self._missing_dependency = 'psutil'
            self.refreshNoDepencency()
        elif self.ws.operation_mode == self.ws.NO_PLAYER_ERROR_MODE:
            if self.requested_player:
                if self.requested_player in ('mpv', 'mplayer', 'vlc'):
                    atxt = '''PyRadio is not able to use the player you specified.

                    This player ({}) is supported by PyRadio, but it probably
                    is not installed in your system.

                    Keep in mind that you can choose a player to use by specifying
                    the "-u" command line parameter.'''
                    txt = atxt.format(self.requested_player)

                else:
                    txt = '''PyRadio is not able to use the player you specified.

                    This means that either this particular player is not supported
                    by PyRadio, or that you have simply misspelled its name.

                    PyRadio currently supports three players: mpv, mplayer and vlc,
                    automatically detected in this order.'''
            else:
                txt = '''PyRadio is not able to detect any players.

                PyRadio currently supports three players: mpv, mplayer and vlc,
                automatically detected in this order.

                Please install any one of them and try again.'''
            if platform.startswith('win'):
                txt = txt.replace('mpv, ', '')
                txt = txt.replace('three', 'two')
            self.refreshNoPlayerBody(txt)
        else:
            self._put_selection_in_the_middle()
            self.refreshBody()

    def initFooter(self):
        ''' Initializes the body/story window '''

        ''' This would be the first step to make the status bar
            appear as plain text in "Listening Mode"

            col = 5 if self._limited_height_mode else 7
            self.footerWin.bkgd(' ', curses.color_pair(col))
        '''
        self.footerWin.bkgd(' ', curses.color_pair(7))
        self.footerWin.noutrefresh()

    def _update_redisplay_list(self):
        def _get_redisplay_index():
            for n in range(-1, - len(self.ws._dq) - 1, -1):
                if self.ws._dq[n][0] == self.ws._dq[n][1]:
                    return n
            return 0
        self._redisplay_list = list(self.ws._dq)[_get_redisplay_index():]
        if not self._redisplay_list:
            self._redisplay_list = [0, 0]

    def refreshBody(self, start=0):
        if self.player.ctrl_c_pressed:
            return
        if self._limited_height_mode or self._limited_width_mode:
            self._print_limited_info()
            return
        self._update_redisplay_list()
        end = len(self._redisplay_list)
        if end == 0:
            end = 1
        if start == 0:
            st = [i for i, x in enumerate(self._redisplay_list) if x[0] in self.ws.FULL_SCREEN_MODES]
            if st:
                start = st[-1]
                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug('refreshBody(): start = {}'.format(start))
        for n in range(start, end):
            if n == 1:
                if self._theme_selector and not self._cnf.locked:
                    self.theme_forced_selection = self._theme_selector._themes[self._theme_selector.selection]
            display = True
            if n != len(self._redisplay_list) - 1 and self._redisplay_list[n][0] == self.ws.NORMAL_MODE:
                if self._redisplay_list[n+1][0] in self.ws.FULL_SCREEN_MODES:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Not displaying stations, next mode is full screen')
                    display = False
            if display:
                # logger.error('DE \n\ndisplaying mode {}\n\n'.format(self.ws.MODE_NAMES[self._redisplay_list[n][0]]))
                self._redisplay[self._redisplay_list[n][0]]()

        # logger.error('DE window mode = {}'.format(self.ws.window_mode))
        # logger.error('DE operation mode = {}'.format(self.ws.operation_mode))
        # logger.error('DE Browser search mode = {}'.format(self.ws.BROWSER_SEARCH_MODE))
        if self.ws.operation_mode == self.ws.BROWSER_SEARCH_MODE and \
                self._i_am_resizing:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Redisplaying RadioBrowser Search Window!!!')
            self._browser_search()

        if self._cnf.playlist_recovery_result == -1:
            ''' display playlist recovered '''
            self._show_playlist_recovered()
        elif self._cnf.theme_not_supported:
            ''' display theme not supported '''
            self._show_theme_not_supported()
        elif self._cnf.user_param_id == -1:
            self._print_user_parameter_error()
        elif self._no_netifaces:
            self._no_netifaces = False
            self._print_netifaces_not_installed_error()
        # elif not self._cnf.use_themes:
        #     self._show_no_themes()
        else:
            with self._update_stations_lock:
                if self._need_to_update_stations_csv == 2:
                    logger.error('\n\nstations title = "{0}"\ndirty = {1}\n\n'.format(self._cnf.station_title, self._cnf.dirty_playlist))
                    if self._cnf.station_title == 'stations' and \
                            self._cnf.dirty_playlist:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Not asking to update stations.csv; playlist is dirty!!!')
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Asking to update stations.csv!!!')
                        self._need_to_update_stations_csv = 3
                        self._ask_to_update_stations_csv()

        self._update_history_positions_in_list()

    def refreshNoDepencency(self):
        col = curses.color_pair(13)
        self.outerBodyWin.bkgdset(' ', col)
        self.bodyWin.bkgdset(' ', col)
        self.outerBodyWin.erase()
        self.bodyWin.erase()
        self.outerBodyWin.box()
        self.bodyWin.addstr(1,1, 'PyRadio ', curses.color_pair(4))
        self.bodyWin.addstr('has a new dependency: ', curses.color_pair(5))
        self.bodyWin.addstr(self._missing_dependency, curses.color_pair(4))
        self.bodyWin.addstr(3,1, 'Please use you distro package manager to install it (named ', curses.color_pair(5))
        self.bodyWin.addstr('python-psutil', curses.color_pair(4))
        self.bodyWin.addstr(4,1, 'or ', curses.color_pair(5))
        self.bodyWin.addstr('python3-psutil', curses.color_pair(4))
        self.bodyWin.addstr('), or execute:', curses.color_pair(5))
        self.bodyWin.addstr(6,1, '      pip install ' + self._missing_dependency, curses.color_pair(4))
        self.bodyWin.addstr(8,1, 'to install it and then try to execute ', curses.color_pair(5))
        self.bodyWin.addstr('PyRadio ', curses.color_pair(4))
        self.bodyWin.addstr('again.', curses.color_pair(5))
        self.bodyWin.addstr(10,1, 'While you are at it, please make sure you have all ', curses.color_pair(5))
        self.bodyWin.addstr('PyRadio ', curses.color_pair(4))
        self.bodyWin.addstr('dependencies', curses.color_pair(5))
        self.bodyWin.addstr(11,1, 'installed:', curses.color_pair(5))
        self.bodyWin.addstr(12,1, '      1. ', curses.color_pair(5))
        self.bodyWin.addstr('requests', curses.color_pair(4))
        self.bodyWin.addstr(13,1, '      2. ', curses.color_pair(5))
        self.bodyWin.addstr('dnspython', curses.color_pair(4))
        self.bodyWin.addstr(14,1, '      3. ', curses.color_pair(5))
        self.bodyWin.addstr('psutil ', curses.color_pair(4))
        self.bodyWin.addstr(15,1, '      4. ', curses.color_pair(5))
        self.bodyWin.addstr('rich', curses.color_pair(4))
        self.bodyWin.addstr(16,1, '      5. ', curses.color_pair(5))
        self.bodyWin.addstr('netifaces', curses.color_pair(4))
        self.outerBodyWin.refresh()
        self.bodyWin.refresh()

    def refreshNoPlayerBody(self, a_string):
        col = curses.color_pair(13)
        self.outerBodyWin.bkgdset(' ', col)
        self.bodyWin.bkgdset(' ', col)
        self.outerBodyWin.erase()
        self.bodyWin.erase()
        # self.bodyWin.box()
        self.outerBodyWin.box()
        lines = a_string.split('\n')
        lineNum = 0
        self.txtWin.bkgdset(' ', col)
        self.txtWin.erase()
        for line in lines:
            try:
                self.txtWin.addstr(lineNum , 0, line.replace('\r', '').strip(), col)
            except:
                break
            lineNum += 1
        self.outerBodyWin.refresh()
        self.bodyWin.refresh()
        self.txtWin.refresh()

    def _print_body_header(self):
        http_conn = {
            False: ('', '' ),
            True: ('[http forced (z)]', '[f]')
        }
        cur_mode = self.ws.window_mode
        if cur_mode == self.ws.THEME_MODE:
            cur_mode = self.ws.previous_operation_mode
        if cur_mode == self.ws.NORMAL_MODE:
            if self._cnf.browsing_station_service:
                ticks = None
                if self._cnf.online_browser:
                    if self._cnf._online_browser:
                        ticks = self._cnf.online_browser.get_columns_separators(self.bodyMaxX, adjust_for_header=True)
                if ticks:
                    for n in ticks:
                        if version_info < (3, 0):
                            self.outerBodyWin.addstr(0, n + 2, u'┬'.encode('utf-8', 'replace'), curses.color_pair(13))
                            self.outerBodyWin.addstr(self.outerBodyMaxY - 1, n + 2, u'┴'.encode('utf-8', 'replace'), curses.color_pair(13))
                        else:
                            try:
                                self.outerBodyWin.addstr(0, n + 2, '┬', curses.color_pair(13))
                                self.outerBodyWin.addstr(self.outerBodyMaxY - 1, n + 2, '┴', curses.color_pair(13))
                            except:
                                pass

            align = 1

            ''' TODO show recording status '''
            self._show_recording_status_in_header(from_header_update=True)

            ''' show force http indication '''
            w_header = self._cnf.station_title
            w_conn = http_conn[self.player.force_http][0]
            if self._cnf.dirty_playlist:
                align += 1
                w_header = '*' + self._cnf.station_title
            while len(w_header) > self.bodyMaxX - 14:
                w_header = w_header[:-1]
                w_conn = False
            w_header_left = int((self.bodyMaxX - len(w_header)) / 2) - align
            if w_header_left < 14:
                w_conn = False
            self.outerBodyWin.addstr(
                0, w_header_left, '[', curses.color_pair(13)
            )
            self.outerBodyWin.addstr(w_header, curses.color_pair(4))
            self.outerBodyWin.addstr(']', curses.color_pair(13))

            if w_conn:
                w_conn_left = self.bodyMaxX - len(w_conn) + 1
                if w_header_left + len(w_header) + 10 > w_conn_left:
                    w_conn = '[h]'
                    w_conn_left = self.bodyMaxX - len(w_conn) + 1
                self.outerBodyWin.addstr(0, w_conn_left,'[', curses.color_pair(13))
                if w_conn == '[h]':
                    self.outerBodyWin.addstr('h', curses.color_pair(14))
                else:
                    self.outerBodyWin.addstr('http forced (z)', curses.color_pair(14))
                self.outerBodyWin.addstr(']', curses.color_pair(13))

                # self.outerBodyWin.addstr(0, w_conn_left,'[', curses.color_pair(13))
                # if w_conn == '[h]':
                #     self.outerBodyWin.addstr('h', curses.color_pair(14))
                # else:
                #     self.outerBodyWin.addstr('http forced (', curses.color_pair(14))
                #     self.outerBodyWin.addstr('z', curses.color_pair(4))
                #     self.outerBodyWin.addstr(')', curses.color_pair(14))
                # self.outerBodyWin.addstr(']', curses.color_pair(13))

        elif cur_mode == self.ws.PLAYLIST_MODE or \
                self.ws.operation_mode == self.ws.PLAYLIST_LOAD_ERROR_MODE or \
                self.ws.operation_mode == self.ws.PLAYLIST_NOT_FOUND_ERROR_MODE:
            ''' display playlists header '''
            if self._cnf.open_register_list:
                if self.number_of_items > 0:
                    w_header = ' Select register to view '
                else:
                    w_header = ' All registers are empty '
            else:
                w_header = ' Select playlist to open '
            try:
                self.outerBodyWin.addstr(
                    0, int((self.bodyMaxX - len(w_header)) / 2),
                    w_header, curses.color_pair(4)
                )
            except:
                pass

    def __displayBodyLine(self, lineNum, pad, station, return_line=False):
        col = curses.color_pair(5)
        sep_col = None
        # logger.error('DE selection  = {0},{1},{2},{3}'.format(
        #     lineNum,
        #     self.selection,
        #     self.startPos,
        #     self.playing))
        # logger.error('DE selections = {0},{1},{2},{3}'.format(
        #     lineNum,
        #     self.selections[0][0],
        #     self.selections[0][1],
        #     self.selections[0][2]))
        if not return_line:
            if station:
                if station[1] == '-':
                    if lineNum + self.startPos == self.selection:
                        col = curses.color_pair(self._group_color_active)
                    else:
                        col = curses.color_pair(self._group_color_normal)
                else:
                    if lineNum + self.startPos == self.selection and \
                            self.selection == self.playing:
                        col = curses.color_pair(9)
                        ''' initialize col_sep here to have separated cursor '''
                        sep_col = curses.color_pair(13)
                        # self.bodyWin.hline(lineNum, 0, ' ', self.bodyMaxX, col)
                    elif lineNum + self.startPos == self.selection:
                        col = curses.color_pair(6)
                        ''' initialize col_sep here to have separated cursor '''
                        sep_col = curses.color_pair(13)
                        # self.bodyWin.hline(lineNum, 0, ' ', self.bodyMaxX, col)
                    elif lineNum + self.startPos == self.playing:
                        col = curses.color_pair(4)
                        sep_col = curses.color_pair(13)
                        # self.bodyWin.hline(lineNum, 0, ' ', self.bodyMaxX, col)
            else:
                ''' this is only for a browser service '''
                col = curses.color_pair(5)

        ## self.maxY, self.maxX = self.stdscr.getmaxyx()
        ## logger.error('DE ==== width = {}'.format(self.maxX - 2))
        #if self.ws.operation_mode == self.ws.PLAYLIST_MODE or \
        #        self.ws.operation_mode == self.ws.PLAYLIST_LOAD_ERROR_MODE or \
        #            self.ws.operation_mode == self.ws.PLAYLIST_NOT_FOUND_ERROR_MODE:

        column_num = 0
        column_text = None
        ticks = None
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            line = self._format_playlist_line(lineNum, pad, station)
            try:
                self.bodyWin.addstr(lineNum, 0, line, col)
            except:
                pass
        else:
            if self._cnf.browsing_station_service and \
                    self._cnf._online_browser:
                if ticks is None:
                    ticks = self._cnf.online_browser.get_columns_separators(self.bodyMaxX, adjust_for_body=True)
                    if ticks:
                        column_num = ticks[0] - 3
                        if len(ticks) == 1:
                            column_num += 1
                if station:
                    line, column_text = self._cnf.online_browser.format_station_line(lineNum + self.startPos, pad, self.bodyMaxX)
                else:
                    column_num = 0
                    played, line = self._cnf.online_browser.format_empty_line(self.bodyMaxX)
            else:
                if station:
                    if station[1] == '-':
                        line = self._format_group_line(lineNum, pad, station)
                    else:
                        line = self._format_station_line("{0}. {1}".format(str(lineNum + self.startPos + 1).rjust(pad), station[0]))
                else:
                    line = ' ' * (self.bodyMaxX - 2)

            if return_line:
                ''' return empty line '''
                return line

            self.bodyWin.hline(lineNum, 0, ' ', self.bodyMaxX, col)
            try:
                # logger.error('line: "{}"'.format(line))
                self.bodyWin.addstr(lineNum, 0, line, col)
                if column_num > 0:
                    self.bodyWin.addstr(lineNum, column_num, column_text, col)
            except:
                pass
            if column_num > 0:
                if ticks is None:
                    ticks = self._cnf.online_browser.get_columns_separators(self.bodyMaxX, adjust_for_body=True)
                for n in ticks:
                    self.bodyWin.chgat(lineNum, n, 1, curses.color_pair(13))

            if station and self._cnf.browsing_station_service and sep_col:
                self._change_browser_ticks(lineNum, sep_col, all_ticks=ticks)

    def _format_group_line(self, lineNum, pad, station):
        old_disp = ' ' + station[0] + ' '
        old_len = cjklen(old_disp)
        # if cjklen(to_disp) < self.maxX - (pad + 6):
        if version_info < (3, 0):
            to_disp = cjkcenter(old_disp + '__', self.bodyMaxX, '_')
            # logger.error('cjklen = {0}, old cjklen = {1}'.format(cjklen(to_disp), old_len))
            out = cjkslices(to_disp, pad + 5)[1] + ' '
            # logger.error('out = "{}"'.format(out))
            if out[0] == '_' or out[0] == ' ':
                return '{0}. __{1}'.format(str(lineNum + self.startPos + 1).rjust(pad), out)
            else:
                return '{0}. __{1}'.format(str(lineNum + self.startPos + 1).rjust(pad), self._cjk_ljust(old_disp, self.bodyMaxX - pad - 4, '_'))
        else:
            to_disp = cjkcenter(old_disp + '──', self.bodyMaxX, '─')
            # logger.error('cjklen = {0}, old cjklen = {1}'.format(cjklen(to_disp), old_len))
            out = cjkslices(to_disp, pad + 5)[1] + ' '
            # logger.error('out = "{}"'.format(out))
            if out[0] == '─' or out[0] == ' ':
                return '{0}. ──{1}'.format(str(lineNum + self.startPos + 1).rjust(pad), out)
            else:
                return '{0}. ──{1}'.format(str(lineNum + self.startPos + 1).rjust(pad), self._cjk_ljust(old_disp, self.bodyMaxX - pad - 4, '─'))

    def _cjk_ljust(self, text, width, char):
        if cjklen(text) >= width:
            return cjkslices(text, width-1)[0] + ' '
        else:
            out = text
            # while cjklen(out) < width - 1:
            #     out += char
            if cjklen(out) < width - 1:
                out += (width - 1 - cjklen(out)) * char
            return out + ' '

    def _change_browser_ticks(self, lineNum, sep_col, all_ticks=None):
        ticks = all_ticks
        if self._cnf._online_browser:
            if ticks is None:
                ticks = self._cnf.online_browser.get_columns_separators(self.bodyMaxX, adjust_for_body=True)
        if ticks:
            for n in ticks:
                self.bodyWin.chgat(lineNum, n, 1, sep_col)

    def _watch_theme(self, theme_path=None):
        ''' watch a file for changes

            Parameters
            =========
            path    the path to the file
                    if it's None, the thread is terminated
        '''
        if self._watch_theme_thread:
            self.stop_watch_theme_thread = True
            self._watch_theme_thread.join()
            self._watch_theme_thread = None
            self.stop_watch_theme_thread = False
        if theme_path is None:
            return
        else:
            a_path = theme_path
        self._watch_theme_thread = threading.Thread(
            target=self._wait_for_theme_to_change,
            # args=(self._cnf,
            # args=(path.basename(a_path).replace('.pyradio-theme', ''),
            #       a_path,
            args=(self._cnf.theme,
                  self._cnf.theme_path,
                  self._watch_theme_lock,
                  lambda: self.stop_watch_theme_thread,
                  self._auto_update_theme,
                  self._cnf))
        self._watch_theme_thread.start()

    def _auto_update_theme(self):
        logger.error('_auto_update_theme(): triggered! - updating theme: ' + self._cnf.theme)
        ret, ret_theme_name = self._theme.readAndApplyTheme(self._cnf.theme)
        if ret == 0:
            self._theme_name = self._cnf.theme
            self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
            self._update_calculated_colors()
        else:
            self._theme_name = ret_theme_name
            self._cnf.theme_has_error = True if ret == -1 else False
            self._cnf.theme_not_supported = True
        self._redraw()
        curses.doupdate()
        if self._cnf.theme_download_failed:
            logger.info('_print_theme_download_error 1')
            self._print_theme_download_error()

    def _wait_for_theme_to_change(self, theme, file, a_lock, stop, func, config):
        is_project_theme = False
        a_file = file
        ret, ret_ind = config.is_project_theme(theme)
        if ret is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Watching project theme: ' + theme)
            is_project_theme = True
            a_file = ret.check_file
            ret.theme_id = ret_ind
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Wathcing a non project theme: ' + theme)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('File watch thread started on: {}'.format(a_file))

        showed = False
        while not path.exists(a_file):
            if logger.isEnabledFor(logging.DEBUG) and not showed:
                logger.debug('Waiting for watched file to appear: {}'.format(a_file))
                showed = True
            for n in range(0, 5):
                sleep(.15)
                if stop():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('File watch thread stopped on: {}'.format(a_file))
                    return

        if logger.isEnabledFor(logging.DEBUG) and showed:
            logger.debug('Watched file appeared: {}'.format(a_file))
            showed = False
        st_time = cur_time = getmtime(a_file)
        st_size = cur_size = getsize(a_file)
        while True:
            if path.exists(a_file):
                for n in range(0, 5):
                    sleep(.15)
                    if stop():
                        break
                try:
                    cur_time = getmtime(a_file)
                    showed = False
                except:
                    if logger.isEnabledFor(logging.DEBUG) and not showed:
                        logger.debug('Watched file disappeared: {}'.format(a_file))
                        showed = True
                if st_time != cur_time:
                    if stop():
                        break
                    try:
                        st_time = cur_time = getmtime(a_file)
                        st_size = cur_size = getsize(a_file)
                        showed = False
                    except:
                        if logger.isEnabledFor(logging.DEBUG) and not showed:
                            logger.debug('Watched file disappeared: {}'.format(a_file))
                            showed = True
                    if stop():
                        break
                    # with a_lock:
                    #     func()
                    func()
                if stop():
                    break
                try:
                    cur_size = getsize(a_file)
                    showed = False
                except:
                    if logger.isEnabledFor(logging.DEBUG) and not showed:
                        logger.debug('Watched file disappeared: {}'.format(a_file))
                        showed = True
                if st_size != cur_size:
                    if stop():
                        break
                    st_time = cur_time = getmtime(a_file)
                    st_size = cur_size = getsize(a_file)
                    if stop():
                        break
                    # with a_lock:
                    #     func()
                    func()
                if stop():
                    break
            else:
                if logger.isEnabledFor(logging.DEBUG) and not showed:
                    logger.debug('File watched does not exist: {}'.format(a_file))
                    showed = True
                for n in range(0, 5):
                    sleep(.15)
                    if stop():
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('File watch thread stopped on: {}'.format(a_file))
                        return
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('File watch thread stopped on: {}'.format(a_file))

    def run(self):
        # self._watch_theme()
        self._register_signals_handlers()
        if self.ws.operation_mode == self.ws.DEPENDENCY_ERROR:
            self.log.write(msg="Dependency missing. Press any key to exit....", error_msg=True)
            try:
                self.bodyWin.getch()
            except KeyboardInterrupt:
                pass
        elif self.ws.operation_mode == self.ws.NO_PLAYER_ERROR_MODE:
            if self.requested_player:
                if ',' in self.requested_player:
                    self.log.write(msg='None of "{}" players is available. Press any key to exit....'.format(self.requested_player), error_msg=True)
                else:
                    self.log.write(msg='Player "{}" not available. Press any key to exit....'.format(self.requested_player), error_msg=True)
            else:
                self.log.write(msg="No player available. Press any key to exit....", error_msg=True)
            try:
                self.bodyWin.getch()
            except KeyboardInterrupt:
                pass
        else:
            ''' start update detection and notification thread '''
            if CAN_CHECK_FOR_UPDATES:
                if self._cnf.locked:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('(detectUpdateThread): session locked. Not starting!!!')
                else:
                    distro_package_found = False
                    if self._cnf.distro != 'None' and not platform.startswith('win'):
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('(detectUpdateThread): distro installation detected. Not starting!!!')
                        distro_package_found = True
                    if not distro_package_found:
                        self._update_notification_thread = threading.Thread(
                            target=self.detectUpdateThread,
                            args=(self._cnf,
                                  self._update_notify_lock,
                                  lambda: self.stop_update_notification_thread))
                        self._update_notification_thread.start()

            ''' check if stations.csv is updated '''
            if self._cnf.locked:
                self._update_stations_thread = None
                if logger.isEnabledFor(logging.INFO):
                    logger.info('(detectUpdateStationsThread): not starting; session is locked!!!')
            elif not self._cnf.user_csv_found:
                self._update_stations_thread = None
                self._cls_update_stations.stations_csv_needs_sync(print_messages=False)
                self._cls_update_stations.write_synced_version()
                if logger.isEnabledFor(logging.INFO):
                    logger.info('(detectUpdateStationsThread): not starting; copied stations.csv!!!')
            else:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('(detectUpdateStationsThread): checking in 10 seconds')
                self._update_stations_thread = threading.Thread(
                    target=self.detectUpdateStationsThread,
                    args=(self._cls_update_stations.check_if_version_needs_sync,
                          self._update_stations_lock,
                          lambda: self.stop_update_notification_thread))
                self._update_stations_thread.start()

            #signal.signal(signal.SIGINT, self.ctrl_c_handler)
            self.log.write(msg='Selected player: ' + self.player.PLAYER_NAME, help_msg=True)
            if self.play != 'False':
                if self.play is None:
                    num = random.randint(0, len(self.stations))
                    self._random_requested = True
                else:
                    if self.play.replace('-', '').isdigit():
                        num = int(self.play) - 1
                if num < self.number_of_items:
                    self.setStation(num)
                    if self.number_of_items > 0:
                        self.playSelection()
                        self._goto_playing_station(changing_playlist=True)
                    self.refreshBody()
                    self.selections[self.ws.NORMAL_MODE] = [self.selection,
                                                            self.startPos,
                                                            self.playing,
                                                            self.stations]
                    # self.ll('run')

            elif self._pre_select != 'False':
                if self._pre_select < self.number_of_items:
                    self.setStation(self._pre_select)
                    self._put_selection_in_the_middle(force=True)
                    self.refreshBody()
                    self.selections[self.ws.NORMAL_MODE] = [self.selection,
                                                            self.startPos,
                                                            self.playing,
                                                            self.stations]

            if self._cnf.foreign_file:
                ''' ask to copy this playlist in config dir '''
                self._print_handle_foreign_playlist()

            self._cnf.setup_mouse()

            if not self._cnf.use_themes \
                    and not self._cnf.no_themes_notification_shown \
                    and not self._cnf.no_themes_from_command_line:
                self._show_no_themes()
            elif self._cnf.theme_has_error:
                self._show_theme_not_supported()
            elif self._cnf.theme_download_failed:
                self._print_theme_download_error()
            ''' start theme file thread  '''
            if self._cnf.auto_update_theme:
                self._watch_theme(self._cnf.theme_path)
            while True:
                try:
                    c = self.bodyWin.getch()
                    # logger.error('DE pressed "{0} - {1}"'.format(c, chr(c)))
                    ret = self.keypress(c)
                    if (ret == -1):
                        return
                except KeyboardInterrupt:
                    # ok
                    self.detect_if_player_exited = False
                    self.player.stop_mpv_status_update_thread = True
                    self.player.stop_win_vlc_status_update_thread = True
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Ctrl-C pressed... Terminating...')
                    self.player.ctrl_c_pressed = True
                    self.ctrl_c_handler(0, 0)
                    break

    def _give_me_a_search_class(self, operation_mode):
        ''' get a search class for a given operation mode
            the class is returned in self.search
        '''
        try:
            if self._search_classes[self._mode_to_search[operation_mode]] is None:
                self._search_classes[self._mode_to_search[operation_mode]] \
                    = \
                    PyRadioSearch(
                        parent=self.outerBodyWin,
                        width=33,
                        begin_y=0,
                        begin_x=0,
                        boxed=True,
                        has_history=True,
                        box_color=curses.color_pair(5),
                        caption_color=curses.color_pair(4),
                        edit_color=curses.color_pair(5),
                        cursor_color=curses.color_pair(8),
                        is_locked=self._cnf.locked,
                        search_history_file=\
                            self._search_files[self._mode_to_search[operation_mode]],
                    )
        except KeyError:
            self.search = None
            return
        self.search = self._search_classes[self._mode_to_search[operation_mode]]
        #self.search.pure_ascii = True
        if self.ws.previous_operation_mode == self.ws.CONFIG_MODE:
            self.search.box_color = curses.color_pair(3)
        else:
            self.search.box_color = curses.color_pair(5)

    def ctrl_c_handler(self, signum, frame, save_playlist=True):
        # ok
        if self._cnf.titles_log.titles_handler:
            logger.critical('=== Logging stopped')
        logger.error('signum = {}'.format(signum))
        logger.error('frame = {}'.format(frame))
        search_cls = [x for x in self._search_classes if x is not None]
        for n in range(len(search_cls)):
            search_cls[n].save_search_history()
            search_cls[n] = None
        self.player.stop_update_notification_thread = True
        self.player.stop_win_vlc_status_update_thread = True
        if self.player:
            # ok
            self.detect_if_player_exited = False
            self.stopPlayer(
                show_message=False,
                reset_playing=False
            )
        self._cls_update_stations = None
        self.detect_if_player_exited = False
        if self._cnf.dirty_playlist and save_playlist:
            ''' Try to auto save playlist on exit
                Do not check result!!! '''
            self.saveCurrentPlaylist()
        ''' Try to auto save config on exit
            Do not check result!!! '''
        self._cnf.save_config()
        if self._cnf.open_last_playlist:
            self._cnf.save_last_playlist(self.selections[0])
        ''' Try to auto save online browser config on exit
            Do not check result!!! '''
        if self._cnf.browsing_station_service:
            if self._cnf.online_browser:
                if self._cnf.online_browser.is_config_dirty():
                    self._cnf.online_browser.save_config()
                self._cnf.online_browser = None
        self._wait_for_threads()
        '''
        this a daemonic thread, to make sure it always
        terminates at program exit.
        If that causes problems, uncomment lines
        '''
        while self._remote_control_server is not None:
            ret, _ = self._remote_control_server.close_server()
            if ret:
                self._remote_control_server = None
        self.restore_colors()
        self._remove_station_images()

    def _wait_for_threads(self):
        self.log._stop_desktop_notification_thread = True
        if self._watch_theme_thread:
            self.stop_watch_theme_thread = True
            self._watch_theme_thread.join()
        if self._update_notification_thread is not None:
            if self._update_notification_thread.is_alive():
                self.stop_update_notification_thread = True
                if self._update_notification_thread:
                    self._update_notification_thread.join()
        if self._update_stations_thread is not None:
            try:
                if self._update_stations_thread.is_alive():
                    self.stop_update_notification_thread = True
                    if self._update_stations_thread:
                        self._update_stations_thread.join()
            except AttributeError:
                pass
        self.stop_update_notification_thread = True
        try:
            while self.log._desktop_notification_thread.is_alive():
                self.log._stop_desktop_notification_thread = True
        except:
            self.log._stop_desktop_notification_thread = True

    def _goto_playing_station(self, changing_playlist=False):
        ''' make sure playing station is visible '''
        if (self.player.isPlaying() or self.ws.operation_mode == self.ws.PLAYLIST_MODE) and \
                (self.selection != self.playing or changing_playlist):
            if changing_playlist:
                self.startPos = 0
            # logger.error('DE self.bodyMaxY = {0}, items = {1}, self.playing = {2}'.format(self.bodyMaxY, self.number_of_items, self.playing))
            if self.number_of_items < self.bodyMaxY:
                self.startPos = 0
            elif self.playing < self.startPos or \
                    self.playing >= self.startPos + self.bodyMaxY:
                # logger.error('DE ==== _goto:adjusting startPos')
                if self.playing < self.bodyMaxY:
                    self.startPos = 0
                    if self.playing - int(self.bodyMaxY/2) > 0:
                        self.startPos = self.playing - int(self.bodyMaxY/2)
                elif self.playing > self.number_of_items - self.bodyMaxY:
                    self.startPos = self.number_of_items - self.bodyMaxY
                else:
                    self.startPos = int(self.playing+1/self.bodyMaxY) - int(self.bodyMaxY/2)
            # logger.error('DE ===== _goto:startPos = {0}, changing_playlist = {1}'.format(self.startPos, changing_playlist))
            self.selection = self.playing
            self.refreshBody()

    def _update_history_positions_in_list(self):
        if self.ws.operation_mode == self.ws.NORMAL_MODE and \
                self._cnf.is_local_playlist:
            self._cnf.history_startPos = self.startPos
            self._cnf.history_selection = self.selection
            self._cnf.history_playing = self._playing
        # logger.error('DE new selections = {}'.format(self._cnf._ps._p))

    def _put_selection_in_the_middle(self, force=False):
        if self.number_of_items < self.bodyMaxY or self.selection < self.bodyMaxY:
            self.startPos = 0
        elif force or self.selection < self.startPos or \
                self.selection >= self.startPos + self.bodyMaxY:
            # if logger.isEnabledFor(logging.ERROR):
            #     logger.error('===== _put:adjusting startPos')
            if self.selection < self.bodyMaxY:
                self.startPos = 0
                if self.selection - int(self.bodyMaxY/2) > 0:
                    self.startPos = self.selection - int(self.bodyMaxY/2)
            elif self.selection > self.number_of_items - self.bodyMaxY:
                self.startPos = self.number_of_items - self.bodyMaxY
            else:
                self.startPos = int(self.selection+1/self.bodyMaxY) - int(self.bodyMaxY/2)
        # if logger.isEnabledFor(logging.ERROR):
        #     logger.error('DE ===== _put:startPos -> {0}, force = {1}'.format(self.startPos, force))

    def setStation(self, number):
        ''' Select the given station number '''

        ''' If we press up at the first station, we go to the last one and
            if we press down on the last one we go back to the first one.
        '''
        old_start_pos = self.startPos
        if number < 0:
            number = len(self.stations) - 1
        elif number >= len(self.stations):
            number = 0

        self.selection = number

        if self.selection - self.startPos >= self.bodyMaxY:
            self.startPos = self.selection - self.bodyMaxY + 1
        elif self.selection < self.startPos:
            self.startPos = self.selection

        self._force_print_all_lines = self.startPos != old_start_pos
        self._update_history_positions_in_list()
        # logger.error('de setStation: selection = {}'.format(self.selection))

    def playSelectionBrowser(self, a_url=None):
            self.log.display_help_message = False

            # self.log.write(msg=player_start_stop_token[0] + self._last_played_station[0])

            #### self._cnf.browsing_station_service = True
            ''' Add a history item to preserve browsing_station_service
                Need to add TITLE, if service found
            '''
            self._cnf.add_to_playlist_history(
                    station_path=a_url if a_url else self.stations[self.selection][0],
                    browsing_station_service=True
                    )
            if a_url:
                ''' dirty hack here...  '''
                self._cnf._ps._p[-2][-1] = False
                # logger.error(self._cnf._ps._p)
            self._check_to_open_playlist(a_url)

    def restartPlayer(self, msg=''):
        if self.player.isPlaying():
            # ok
            self.detect_if_player_exited = False
            if msg and logger.isEnabledFor(logging.INFO):
                logger.info(msg)
            self.stopPlayer()
            while self.player.isPlaying():
                sleep(.25)
            self.playSelection(restart=True)

    def _remove_station_images(self):
        for n in self._station_images:
            if exists(n):
                try:
                    remove(n)
                except:
                    pass

    def playSelection(self, restart=False):
        ''' start playback using current selection
            if restart = True, start the station that has
            been played last
        '''
        if self.stations[self.selection][1] == '-':
            ''' this is a group '''
            return
        # logger.error('DE \n\n\nplaying = {}'.format(self.playing))
        self._station_rename_from_info = False
        # logger.info('\n\nselected station\n{}\n\n'.format(self.stations[self.selection]))

        # logger.error('DE \n\nselection = {0}, playing = {1}\nlast played = {2}\n\n'.format(self.selection, self.playing, self._last_played_station))
        # logger.error('DE \n\nselection = {}'.format(self.selections))
        stream_url = ''
        self.log.display_help_message = False
        if restart:
            stream_url = self._last_played_station[1]
            enc = self._last_played_station[2]
            if invalid_encoding(enc):
                enc = ''
            # logger.error('setting playing to {}'.format(self._last_played_station_id))
            self.playing = self._last_played_station_id
        else:
            self._remove_station_images()
            if self._cnf.enable_notifications and \
                    self._cnf.use_station_icon and \
                    not platform.startswith('win'):
                if 'image' in self.stations[self.selection][3]:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('+++ need to download icon: "{}"'.format(self.stations[self.selection][3]['image']))
                    self.log.write(msg='Downloading icon...')
                    self._download_station_image(
                        self.stations[self.selection][3]['image'],
                        lambda: self.stop_update_notification_thread
                    )
            # if self._cnf.browsing_station_service:
            #     if self._cnf.online_browser.have_to_retrieve_url:
            #         self.log.display_help_message = False
            #         self.log.write(msg='Station: ' + self._last_played_station[0] + ' - Retrieving URL...')
            #         stream_url = self._cnf.online_browser.url(self.selection)
            self._last_played_station = self.stations[self.selection]
            self._last_played_station_id = self.selection
            # logger.error('setting playing to {}'.format(self.selection))
            self.playing = self.selection
            if not stream_url:
                stream_url = self.stations[self.selection][1]
            try:
                enc = self.stations[self.selection][2].strip()
                if invalid_encoding(end):
                    enc = ''
            except:
                enc = ''
        ''' start player '''
        self.log.write(msg=player_start_stop_token[0] + self._last_played_station[0])
        # logger.error('DE \n\nself.detect_if_player_exited = {}\n\n'.format(self.detect_if_player_exited))
        if self._random_requested:
            self.detect_if_player_exited = False
        try:
            self.player.play(name=self._last_played_station[0],
                             streamUrl=stream_url,
                             stop_player=self.stopPlayerFromKeyboard,
                             detect_if_player_exited=lambda: self.detect_if_player_exited,
                             enable_crash_detection_function=self._enable_player_crash_detection,
                             encoding=self.get_active_encoding(enc)
                             )
        except OSError:
            self.log.write(msg='Error starting player.'
                           'Are you sure a supported player is installed?')
            # logger.error('setting playing to 0')
            self.playing = -1
            return
        self._set_active_stations()
        self.selections[0][2] = self.playing
        self._do_display_notify()
        try:
            self.playback_timeout = int(self._cnf.connection_timeout_int)
        except ValueError:
            self.playback_timeout = 10
        self._click_station()

    def _enable_player_crash_detection(self):
        if logger.isEnabledFor(logging.INFO):
            logger.info('Enabling crash detection')
        self.detect_if_player_exited = True

    def _click_station(self):
        if self._cnf._online_browser:
            self._cnf._online_browser.click(self.playing)

    def playbackTimeoutCounter(self, *args):
        timeout = args[0]
        station_name = args[1]
        stop = args[2]
        if stop():
            return
        not_showed = True
        lim = int((7 * timeout) / 10)
        for n in range(timeout, -1, -1):
            ''' 8 * .12 =~ 1 sec '''
            for k in range(0, 8):
                sleep(.12)
                if stop():
                    return
            #if n <= 7:"
            if n <= lim:
                if stop():
                    return
                self.log.write(msg='Connecting to: ' + station_name)
                self.log.write(counter='{}'.format(n))
            else:
                if stop():
                    return
                if not_showed:
                    self.log.write(msg='Connecting to: ' + station_name)
                    not_showed = False
        self.connectionFailed()

    def connectionFailed(self):
        # ok
        self.detect_if_player_exited = False
        if self.ws.operation_mode in (self.ws.STATION_INFO_MODE,
                self.ws.STATION_DATABASE_INFO_MODE,
                self.ws.STATION_INFO_ERROR_MODE):
            self.ws.close_window()
        old_playing = self.playing
        self.stopPlayer(False)
        self.selections[self.ws.NORMAL_MODE][2] = -1
        if self.ws.window_mode == self.ws.NORMAL_MODE:
            if self.ws.operation_mode == self.ws.NORMAL_MODE:
                self.refreshBody()
        else:
            self.playing = old_playing
            #self._update_redisplay_list()
            #self._redisplay_transient_window()
            self.refreshBody(start=1)
        if logger.isEnabledFor(logging.INFO):
            logger.info('*** Start of playback NOT detected!!! ***')
        self.player.stop_mpv_status_update_thread = True
        self.log.write(msg='Failed to connect to: ' + self._last_played_station[0])
        self.player.connecting = False
        if self._random_requested and \
                self.ws.operation_mode == self.ws.NORMAL_MODE:
            if logger.isEnabledFor(logging.INFO):
                logger.info('Looking for a working station (random is on)')
            self.play_random()
        self._show_recording_status_in_header()

    def stopPlayerFromKeyboard(
        self,
        from_update_thread=False,
        player_disappeared=False
    ):
        ''' stops the player with a keyboard command
            Also used at self.player.play as a loopback function
            for the status update thread.
        '''
        logger.error('stopPlayerFromKeyboard()!!!!!')
        self.player.stop_update_notification_thread = True
        self.player.stop_win_vlc_status_update_thread = True
        if from_update_thread:
            self.detect_if_player_exited = True
            self.player.stop_timeout_counter_thread = True
        with self.log.lock:
            self.log.counter = None
        self._update_status_bar_right()
        if self.player.isPlaying():
            self.stopPlayer(show_message=True, from_update_thread=from_update_thread)
        self._show_recording_status_in_header(player_disappeared=player_disappeared)
        # if from_update_thread and self.ws.operation_mode == self.ws.NORMAL_MODE:
        #     with self.log.lock:
        #         pass
        #         # this one breaks the layout
        #         # self._redisplay_stations_and_playlists()

    def stopPlayer(self,
                   show_message=True,
                   from_update_thread=False,
                   reset_playing=True):
        ''' stop player
            it is ready for any mode
        '''
        if from_update_thread:
            self.detect_if_player_exited = True
        try:
            self.player.close()
        except:
            pass
        finally:
            self.player.connecting = False
            if self.ws.window_mode == self.ws.PLAYLIST_MODE:
                self._last_played_station_id = self.selections[0][2]
            else:
                self._last_played_station_id = self.playing
            self.selections[0][2] = -1
            # logger.error('self.selection = {}'.format(self.selection))
            # logger.error('self.playing = {}'.format(self.playing))
            # logger.error('self.selections = {}'.format(self.selections[0][:3]))
            # logger.error('self._last_played_station = {}'.format(self._last_played_station))
            # logger.error('self._last_played_station_id = {}'.format(self._last_played_station_id))
            if reset_playing \
                    and self.ws.window_mode != self.ws.PLAYLIST_MODE:
                self.playing = -1
            self.player.process = None
            if show_message:
                self._show_player_is_stopped(from_update_thread)
            self._show_recording_status_in_header()

    def _show_player_is_stopped(self, from_update_thread=False):
        if from_update_thread:
            msg_id = 2
        else:
            msg_id = 1
        self.log.write(
            msg=self.player.PLAYER_NAME
            + player_start_stop_token[msg_id],
            help_msg=True, suffix=self._status_suffix, counter=''
        )

    def _download_station_image(self, url, stop):
        threading.Thread(
            target=self._thread_download_station_image,
            args=(url, stop),
        ).start()

    def _thread_download_station_image(self, url, stop):
        if url:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('+++ downloading icon...')
            file_to_write = self._station_images[0] if url.endswith('.jpg') else self._station_images[1]
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('+++ icon download: asked to stop. Stopping...')
                return
            try:
                response = requests.get(url)
            except requests.exceptions.RequestException as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('+++ icon download failed: {}'.format(e))
                return
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('+++ icon download: asked to stop. Stopping...')
                return
            if response.status_code == 200:
                with open(self._station_images[2], 'wb') as local_file:
                    for chunk in response.iter_content(chunk_size=128):
                        if stop():
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('+++ icon download: asked to stop. Stopping...')
                            return
                        local_file.write(chunk)
            if not (exists(self._station_images[0]) or exists(self._station_images[1])):
                if stop():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('+++ icon download: asked to stop. Stopping...')
                    return
                try:
                    rename(self._station_images[2], file_to_write)
                except:
                    self._remove_station_images()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('+++ icon downloaded...')
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('+++ icon downloaded, but already exists...')



    def _ask_to_remove_group(self):
        txt = '''
        Are you sure you want to delete this group header:
        "|{}|"?

        Press "|y|" to confirm, or any other key to cancel
        '''

        ''' truncate parameter to text width '''
        mwidth = self._get_message_width_from_string(txt)
        msg = self.stations[self.selection][0]
        if len(msg) > mwidth - 3:
            msg = msg[:mwidth-6] + '...'
        self._show_help(txt.format(msg),
                self.ws.REMOVE_GROUP_MODE, caption=' Group Deletion ',
                prompt='', is_message=True)

    def _ask_to_remove_station(self):
        if self._cnf.confirm_station_deletion and not self._cnf.is_register:
            if self._cnf.locked:
                txt = '''
                Are you sure you want to delete station:
                "|{}|"?

                Press "|y|" to confirm, or any other key to cancel
                '''
            else:
                txt = '''
                Are you sure you want to delete station:
                "|{}|"?

                Press "|y|" to confirm, "|Y|" to confirm and not
                be asked again, or any other key to cancel
                '''

            ''' truncate parameter to text width '''
            mwidth = self._get_message_width_from_string(txt)
            msg = self.stations[self.selection][0]
            if len(msg) > mwidth - 3:
                msg = msg[:mwidth-6] + '...'

            self._show_help(txt.format(msg),
                    self.ws.REMOVE_STATION_MODE, caption=' Station Deletion ',
                    prompt='', is_message=True)
        else:
            self.ws.operation_mode = self.ws.REMOVE_STATION_MODE
            self._remove_station()

    def saveCurrentPlaylist(self, stationFile=''):
        ret = self._cnf.save_playlist_file(stationFile)
        self.refreshBody()
        if ret == 0 and not self._cnf.is_register:
            self._show_notification_with_delay(
                    txt='___Playlist saved!!!___',
                    mode_to_set=self.ws.NORMAL_MODE,
                    callback_function=self.refreshBody)
        elif ret == -1:
            self._print_save_playlist_error_1()
        elif ret == -2:
            self._print_save_playlist_error_2()
        if ret < 0 and logger.isEnabledFor(logging.DEBUG):
            logger.debug('Error saving playlist: "{}"'.format(self._cnf.station_path))
        return ret

    def reloadCurrentPlaylist(self, mode):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Reloading current playlist')
        self._set_active_stations()
        #txt = '''Reloading playlist. Please wait...'''
        #self._show_help(txt, self.ws.NORMAL_MODE, caption=' ', prompt=' ', is_message=True)
        self._update_status_bar_right()
        ret = self._cnf.read_playlist_file(stationFile=self._cnf.station_path)
        if ret == -1:
            #self.stations = self._cnf.playlists
            self.ws.close_window()
            self.refreshBody()
            self._print_playlist_reload_error()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Error reloading playlist: "{}"'.format(self._cnf.station_path))
        else:
            self.number_of_items = ret
            self._align_stations_and_refresh(self.ws.NORMAL_MODE)
            self.ws.close_window()
            self.refreshBody()
        return

    def readPlaylists(self):
        num_of_playlists, playing = self._cnf.read_playlists()
        if num_of_playlists == 0 and not self._cnf.open_register_list:
            txt = '''
            No playlists found!!!

            This should never have happened; PyRadio is missing its
            default playlist. Therefore, it has to terminate now.
            It will re-create it the next time it is lounched.
            '''
            self._show_help(
                txt.format(self._cnf.station_file_name),
                mode_to_set=self.ws.PLAYLIST_SCAN_ERROR_MODE,
                caption=' Error ',
                prompt=' Press any key to exit ',
                is_message=True)
            if logger.isEnabledFor(logging.ERROR):
                logger.error('No playlists found!!!')
        return num_of_playlists, playing

    def _show_theme_selector_from_config(self):
        if not self._cnf.use_themes:
            # TODO show msg
            self._show_colors_cannot_change()
            return
        self._theme_name = self._config_win._config_options['theme'][1]
        # if logger.isEnabledFor(logging.ERROR):
        #     logger.error('DE\n\nreseting self._theme_name = {}\n\n'.format(self._theme_name))
        #self.ws.previous_operation_mode = self.ws.operation_mode
        self.ws.operation_mode = self.ws.THEME_MODE
        self._show_theme_selector(changed_from_config=True)

    def _show_theme_selector(self, changed_from_config=False):
        self._update_status_bar_right()
        if not changed_from_config:
            if self._theme_selector is not None:
                ''' if theme selector already exists
                    use the same changed_from_config
                '''
                changed_from_config = self._theme_selector.changed_from_config
        self._theme_selector = None
        #if logger.isEnabledFor(logging.ERROR):
        #    logger.error('DE\n\nself._theme = {0}\nself._theme_name = {1}\nself._cnf.theme = {2}\n\n'.format(self._theme, self._theme_name, self._cnf.theme))
        self._theme_selector = PyRadioThemeSelector(
            self.outerBodyWin,
            self._cnf,
            self._theme,
            self._theme_name,
            self._cnf.theme,
            11, 3, 11, 10, 6, 9,
            self._cnf.auto_update_theme,
            self._watch_theme_lock
        )
            #'/home/spiros/edit.log')
        self._theme_selector.changed_from_config = changed_from_config
        self._theme_selector.show()
        self._theme_selector.set_global_functions(self._global_functions)

    def _get_message_width_from_list(self, lines):
        mwidth = 0
        for n in lines:
            llen = cjklen(n.replace('|', ''))
            if llen > mwidth:
                mwidth = llen
        return mwidth

    def _get_message_width_from_string(self, txt):
        lines = txt.split('\n')
        st_lines = [item.replace('\r', '') for item in lines]
        lines = [item.strip() for item in st_lines]
        return self._get_message_width_from_list(lines)

    def _show_msg(self, txt,
                   mode_to_set=0,
                   caption=' Help ',
                   prompt=' Press any key to hide ',
                   too_small_msg='Window too small to show message',
                   is_message=False,
                   reset_metrics=True):
        txt_col = curses.color_pair(10)
        box_col = curses.color_pair(3)
        caption_col = curses.color_pair(11)
        lines = txt.split('\n')
        st_lines = [item.replace('\r', '') for item in lines]
        lines = [item.strip() for item in st_lines]
        inner_height = len(lines) + 2
        inner_width = self._get_message_width_from_list(lines) + 4
        outer_height = inner_height + 2
        outer_width = inner_width + 2
        if outer_width + 2 < self.bodyMaxX and outer_height + 2 < self.bodyMaxY:
            win = curses.newwin(inner_height,inner_width - 2,int((self.maxY-inner_height)/2),int((self.maxX-inner_width)/2))
            win.bkgdset(' ', box_col)
            win.erase()
            win.box()
            for i, a_line in enumerate(lines):
                #a_line = self._replace_starting_undesscore(n)
                win.addstr(i + 1, 1, a_line.replace('_', ' ').replace('¸', '_'), txt_col)
        win.refresh()

    def _show_help(self, txt,
                   mode_to_set=0,
                   caption=' Help ',
                   prompt=' Press any key to hide ',
                   too_small_msg='Window too small to show message',
                   is_message=False,
                   reset_metrics=True):
        if reset_metrics:
            if mode_to_set in self._help_metrics.keys():
                del self._help_metrics[mode_to_set]

        ''' Display a help, info or question window.  '''
        if mode_to_set == self.ws.MAIN_HELP_MODE:
            caption = ' Help (1/5) '
            prompt = ' Press n/p or any other key to hide '
        elif mode_to_set == self.ws.MAIN_HELP_MODE_PAGE_2:
            caption = ' Help (2/5) '
            prompt = ' Press n/p or any other key to hide '
        elif mode_to_set == self.ws.MAIN_HELP_MODE_PAGE_3:
            caption = ' Help (3/5) '
            prompt = ' Press n/p or any other key to hide '
        elif mode_to_set == self.ws.MAIN_HELP_MODE_PAGE_4:
            caption = ' Help (4/5) '
            prompt = ' Press n/p or any other key to hide '
        elif mode_to_set == self.ws.MAIN_HELP_MODE_PAGE_5:
            caption = ' Help (5/5) '
            prompt = ' Press n/p or any other key to hide '
        self.helpWinContainer = None
        self.helpWin = None
        self.ws.operation_mode = mode_to_set
        txt_col = curses.color_pair(10)
        box_col = curses.color_pair(3)
        caption_col = curses.color_pair(11)
        lines = txt.split('\n')
        st_lines = [item.replace('\r', '') for item in lines]
        lines = [item.strip() for item in st_lines]

        if mode_to_set in self._help_metrics.keys():
            inner_height, inner_width, outer_height, outer_width = self._help_metrics[mode_to_set]
        else:
            inner_height = len(lines) + 2
            inner_width = self._get_message_width_from_list(lines) + 4
            outer_height = inner_height + 2
            outer_width = inner_width + 2
            self._help_metrics[mode_to_set] = [inner_height, inner_width, outer_height, outer_width]
            if mode_to_set == self.ws.MAIN_HELP_MODE:
                self._help_metrics[self.ws.MAIN_HELP_MODE_PAGE_2] = self._help_metrics[mode_to_set]

        if ((self.ws.window_mode == self.ws.CONFIG_MODE and \
                self.ws.operation_mode > self.ws.CONFIG_HELP_MODE) or \
                (self.ws.window_mode == self.ws.NORMAL_MODE and \
                self.ws.operation_mode == self.ws.SELECT_ENCODING_HELP_MODE)) and \
                self.ws.operation_mode != self.ws.ASK_TO_CREATE_NEW_THEME_MODE:
            use_empty_win = True
            height_to_use = outer_height
            width_to_use = outer_width
        else:
            use_empty_win = False
            height_to_use = inner_height
            width_to_use = inner_width
        if self.maxY - 2 < outer_height or self.maxX < outer_width:
            if self.ws.operation_mode == self.ws.STATION_INFO_MODE:
                ''' reset view of main window '''
                self.outerBodyWin.touchwin()
                self.bodyWin.touchwin()
                self.outerBodyWin.refresh()
                self.bodyWin.refresh()
            txt = too_small_msg
            prompt = ''
            caption = ''
            inner_height = 3
            inner_width = cjklen(txt) + 4
            if use_empty_win:
                height_to_use = inner_height + 2
                width_to_use = inner_width + 2
            else:
                height_to_use = inner_height
                width_to_use = inner_width
            if self.maxX < width_to_use:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  ***  Window too small even to show help warning  ***')
                self.ws.close_window()
                self.refreshBody()
                return
            lines = [txt, ]
        if use_empty_win:
            self.helpWinContainer = curses.newwin(height_to_use,width_to_use,
                    int((self.maxY-height_to_use)/2),
                    int((self.maxX-width_to_use)/2))
            self.helpWinContainer.bkgdset(' ', box_col)
            self.helpWinContainer.erase()
        self.helpWin = curses.newwin(inner_height,inner_width,int((self.maxY-inner_height)/2),int((self.maxX-inner_width)/2))
        self.helpWin.bkgdset(' ', box_col)
        self.helpWin.erase()
        self.helpWin.box()
        if is_message:
            start_with = txt_col
            follow = caption_col
        else:
            start_with = caption_col
            follow = txt_col
        if caption.strip():
            self.helpWin.addstr(0, int((inner_width-cjklen(caption))/2), caption, caption_col)
        splited = []
        for i, n in enumerate(lines):
            #a_line = self._replace_starting_undesscore(n)
            a_line = n
            if a_line.startswith('%'):
                self.helpWin.move(i + 1, 0)
                try:
                    self.helpWin.addstr('├', curses.color_pair(3))
                    self.helpWin.addstr('─' * (inner_width - 2), curses.color_pair(3))
                    self.helpWin.addstr('┤', curses.color_pair(3))
                except:
                    self.helpWin.addstr('├'.encode('utf-8'), curses.color_pair(3))
                    self.helpWin.addstr('─'.encode('utf-8') * (inner_width - 2), curses.color_pair(3))
                    self.helpWin.addstr('┤'.encode('utf-8'), curses.color_pair(3))
                self.helpWin.addstr(i + 1, inner_width-cjklen(a_line[1:]) - 1, a_line[1:].replace('_', ' ').replace('¸', '_'), caption_col)
                #self.helpWin.addstr(i + 1, int((inner_width-len(a_line[1:]))/2), a_line[1:].replace('_', ' '), caption_col)
            elif a_line.startswith('!'):
                self.helpWin.move(i + 1, 2)
                lin = ' ' + a_line[1:] + ' '
                llin = cjklen(lin)

                wsp = inner_width - 4
                try:
                    self.helpWin.addstr('─' * wsp, curses.color_pair(3))
                except:
                    self.helpWin.addstr('─'.encode('utf-8') * wsp, curses.color_pair(3))
                self.helpWin.addstr(i + 1, 5, lin, caption_col)

            else:
                splited = a_line.split('|')
                self.helpWin.move(i + 1, 2)
                for part, part_string in enumerate(splited):
                    if part_string.strip():
                        if part == 0 or part % 2 == 0:
                            self.helpWin.addstr(splited[part].replace('_', ' ').replace('¸', '_'), start_with)
                        else:
                            self.helpWin.addstr(splited[part].replace('_', ' ').replace('¸', '_'), follow)
        if prompt.strip():
            self.helpWin.addstr(inner_height - 1, int(inner_width-cjklen(prompt)-1), prompt)
        if use_empty_win:
            self.helpWinContainer.refresh()
        self.helpWin.refresh()

    def _replace_starting_undesscore(self, a_string):
        ret = ''
        for i, ch in enumerate(a_string):
            if ch == '_':
                ret += ' '
            else:
                ret += a_string[i:]
                break
        return ret

    def _format_playlist_line(self, lineNum, pad, station):
        ''' format playlist line so that if fills self.maxX '''
        pl_line = "{0}. {1}".format(str(lineNum + self.startPos + 1).rjust(pad), station[0])
        if self._cnf.open_register_list:
            line = pl_line.replace('register_', 'Register: ')
        else:
            line = pl_line
        f_data = ' [{0}, {1}]'.format(station[2], station[1])
        if version_info < (3, 0):
            if cjklen(line.decode('utf-8', 'replace')) + cjklen(f_data.decode('utf-8', 'replace')) > self.bodyMaxX:
                ''' this is too long, try to shorten it
                    by removing file size '''
                f_data = ' [{0}]'.format(station[1])
            if cjklen(line.decode('utf-8', 'replace')) + cjklen(f_data.decode('utf-8', 'replace')) > self.bodyMaxX:
                ''' still too long. start removing chars '''
                while cjklen(line.decode('utf-8', 'replace')) + cjklen(f_data.decode('utf-8', 'replace')) > self.bodyMaxX - 1:
                    f_data = f_data[:-1]
                f_data += ']'
            ''' if too short, pad f_data to the right '''
            if cjklen(line.decode('utf-8', 'replace')) + cjklen(f_data.decode('utf-8', 'replace')) < self.bodyMaxX:
                while cjklen(line.decode('utf-8', 'replace')) + cjklen(f_data.decode('utf-8', 'replace')) < self.maxX:
                    line += ' '
        else:
            if cjklen(line) + cjklen(f_data) > self.bodyMaxX:
                ''' this is too long, try to shorten it
                    by removing file size '''
                f_data = ' [{0}]'.format(station[1])
            if cjklen(line) + cjklen(f_data) > self.bodyMaxX:
                ''' still too long. start removing chars '''
                while cjklen(line) + cjklen(f_data) > self.bodyMaxX - 1:
                    f_data = f_data[:-1]
                f_data += ']'
            ''' if too short, pad f_data to the right '''
            if cjklen(line) + cjklen(f_data) < self.maxX:
                while cjklen(line) + cjklen(f_data) < self.bodyMaxX:
                    line += ' '
        line += f_data
        return line

    def _format_station_line(self, line):
        if version_info < (3, 0):
            if len(line.decode('utf-8', 'replace')) != cjklen(line.decode('utf-8', 'replace')):
                while cjklen(line.decode('utf-8', 'replace')) > self.bodyMaxX:
                    line = line[:-1]
                return line
            else:
                return line[:self.bodyMaxX]
        else:
            if len(line) != cjklen(line):
                while cjklen(line) > self.bodyMaxX:
                    line = line[:-1]
                return line
            else:
                return line[:self.bodyMaxX]

    def _print_help(self):
        # logger.error('DE \n\nself.ws.operation_mode = {}'.format(self.ws.operation_mode))
        if self.ws.operation_mode in self._display_help.keys():
            self._display_help[self.ws.operation_mode]()
        else:
            self._redisplay[self.ws.operation_mode]()

    def _show_remote_control_error(self):
        txt = '''
______This session is |locked|, so the
__|Remote Control Server| cannot be started!__
        '''
        self._show_help(txt,
                        self.ws.SERVICE_SERVERS_UNREACHABLE,
                        caption=' Not Available ',
                        prompt=' Press any key ',
                        is_message=True)

    def _show_port_number_invalid(self):
        self._show_notification_with_delay(
                txt='___Invalid port number!!!___',
                mode_to_set=self.ws.operation_mode,
                delay=1.25,
                callback_function=self.refreshBody)

    def _show_playlist_recovered(self):
        self._show_notification_with_delay(
                txt='___Playlist recovered!!!___',
                mode_to_set=self.ws.operation_mode,
                delay=1.25,
                callback_function=self.closeRecoveryNotification)

    def closeRecoveryNotification(self, *arg, **karg):
        #arg[1].acquire()
        self._cnf.playlist_recovery_result = 0
        #arg[1].release()
        self.refreshBody()

    def _show_no_browser_results(self):
        self._show_notification_with_delay(delay=1.5,
                txt='''
                _____Query fetched no results!!!______

                __Please change your search criteria__
                __________and try again...
                ''',
                mode_to_set=self.ws.NO_BROWSER_SEARCH_RESULT_NOTIFICATION,
                callback_function=self.closeTimedNotificationWindow)

    def _show_no_more_playlist_history(self):
        self._show_notification_with_delay(
                txt='___Top of history reached!!!___',
                mode_to_set=self.ws.HISTORY_EMPTY_NOTIFICATION,
                callback_function=self.closeTimedNotificationWindow)

    def closeTimedNotificationWindow(self):
        ''' closes a window opend by _show_notification_with_delay
            (threaded delayed notification)
        '''
        self.ws.close_window()
        self.refreshBody()

    def _show_theme_not_supported(self):
        if self._cnf.theme_not_supported_notification_shown \
                or not self._screen_ready:
            return
        txt = '|Error loading selected theme!|\n____Using |fallback| theme.'
        # if self._cnf.theme_has_error:
        #     txt = '|Error loading selected theme!|\n____Using |fallback| theme.'
        # else:
        #     tmp = ['', '', '']
        #     tmp[0] = '|Theme not supported!|'
        #     tmp[1] = 'This terminal supports up to |{}| colors...'.format(curses.COLORS)
        #     tmp[2] = 'Using |fallback| theme.'
        #     while len(tmp[0]) < len(tmp[1]) - 2:
        #         tmp[0] = '_' + tmp[0] + '_'
        #     while len(tmp[2]) < len(tmp[1]):
        #         tmp[2] = '_' + tmp[2] + '_'
        #     txt = '\n'.join(tmp)
        self._show_help(txt,
                        mode_to_set=self.ws.operation_mode,
                        caption='',
                        prompt='', is_message=True)
        # start 1750 ms counter
        if self._theme_not_supported_thread:
            if self._theme_not_supported_thread.is_alive:
                self._theme_not_supported_thread.cancel()
            self._theme_not_supported_thread = None
        self._theme_not_supported_thread = threading.Timer(
            self._theme_not_supported_notification_duration,
            self.closeThemeNotSupportedNotification)
        self._theme_not_supported_thread.start()
        self._redraw()
        # logger.error('2 redraw')
        curses.doupdate()
        self._theme_not_supported_thread.join()

    def closeThemeNotSupportedNotification(self, *arg, **karg):
        #arg[1].acquire()
        self._cnf.theme_not_supported = False
        self._cnf.theme_has_error = False
        self._cnf.theme_download_failed = False
        self._cnf.theme_not_supported_notification_shown = True
        self._theme_not_supported_notification_duration = 0.75
        #arg[1].release()
        self.refreshBody()

    def _show_win_manage_players(self):
        ''' show message on Windows '''
        txt = '''
            |Players management |enabled|!

            PyRadio| will now terminate so that you can
            |manage installed players.
        '''
        self._show_help(txt,
                        prompt=' Press any key to exit ',
                        mode_to_set=self.ws.WIN_MANAGE_PLAYERS_MSG_MODE,
                        caption=' Players Management ')

    def _show_win_print_exe_paths(self):
        ''' show message on Windows '''
        txt = '''
            {}

            |Use |Shift| and |Left Mouse Button| to select the path, and
            |then press |ENTER| to copy it to the clipboard.

            |For your convinience, the path file will also be printed
            |in the terminal after you exit |PyRadio|.
        '''
        exe = fix_pyradio_win_exe()
        if exe[0] and exe[1]:
            add_msg = '|PyRadio EXE files:\n__|System:\n____{0}\n__|User:\n____{1}'.format(exe[0], exe[1])
        else:
            add_msg = '|PyRadio EXE file:\n__{}'.format(exe[0] if exe[0] else exe[1])

        self._show_help(txt.format(add_msg),
                        prompt=' Press q or ESCAPE to hide... ',
                        mode_to_set=self.ws.WIN_PRINT_EXE_LOCATION_MODE,
                        caption=' Exe Location ')

    def _show_win_uninstall(self):
        ''' show uninstall message on Windows '''
        txt = '''
            |Are you sure you want to uninstall |PyRadio|?

            |Please press |y| to confirm or any other key to decline.
        '''
        self._show_help(txt,
                        prompt='',
                        mode_to_set=self.ws.WIN_UNINSTALL_MODE,
                        caption=' Uninstall PyRadio ')

    def _show_win_remove_old_installation(self):
        ''' show old installation removal message '''
        txt = '''
            PyRadio| will now try to remove any files found on your
            |system belonging to a pre |0.8.9.15| installation.
        '''
        self._show_help(txt,
                        mode_to_set=self.ws.WIN_REMOVE_OLD_INSTALLATION_MODE,
                        caption=' PyRadio ')

    def _show_radio_browser_search_help(self):
        txt = '''Tab| / |Sh-Tab     |Go to next / previous field.
                 j|, |Up| / |k|, |Down  |Go to next / previous field vertivally.
                 h|, |Left| / |l|, |Right
                 _________________|Go to next / previous field (when
                 _________________|applicable). Also, change counter value.
                 Space            |Toggle check buttons.
                 _________________|Toggle multiple selection.
                 Enter            |Perform search / cancel (on push buttons).
                 s                |Perform search (not on Line editor).
                 Esc              |Cancel operation.
                 _
                 |Search history navigation works with normal keys as well
                 |(|^N| is the same as |n| when not in a line editor).
                 %_Global functions (with \ on Line editor)_
                 -|/|+| or |,|/|.       |Change volume.
                 m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                 W| / |w            |Toggle title log / like a station'''
        self._show_help(txt,
                        mode_to_set=self.ws.RADIO_BROWSER_SEARCH_HELP_MODE,
                        caption=' RadioBrowser Search Help ')

    def _show_radio_browser_config_help(self):
        txt = '''Tab| / |Sh-Tab
                 j|, |Up| / |k|, |Down  |Go to next / previous field.
                 h|, |Left| / |l|, |Right
                 _________________|Change |auto save| and |counters| value.
                 _________________|Navigate through |Search Terms|.
                 g|, |G|, |Home|, |End|, |PgUp|, |PgDn|
                 _________________|Navigate through |Search Terms|.
                 Space|, |Enter     |Toggle |auto save|  value.
                 _________________|Open |Server Selection| window.
                 r| / |d            |Revert to |saved| / |default| values.
                 s                |Save config.
                 Esc              |Exit without saving.
                 %_Global functions (with \ on Line editor)_
                 -|/|+| or |,|/|.       |Change volume.
                 m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                 W| / |w            |Toggle title log / like a station.'''
        self._show_help(txt,
                        mode_to_set=self.ws.RADIO_BROWSER_CONFIG_HELP_MODE,
                        caption=' RadioBrowser Config Help ')

    def _show_group_help(self):
        txt = '''Up|,|j|,|PgUp|,
                 Down|,|k|,|PgDown    |Change Group Header selection.
                 g G              |Go to first / last Group Header.
                 H M L            |Go to top / middle / bottom of screen.
                 / n N            |Perform search.
                 Space|, |Left|, |Enter
                 _________________|Select a Group Header.
                 Esc|,|q            |Cancel.
                 %_Global functions_
                 -|/|+| or |,|/|.       |Change volume.
                 m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                 W| / |w            |Toggle title log / like a station.'''
        self._show_help(txt,
                        mode_to_set=self.ws.GROUP_HELP_MODE,
                        caption=' Group Selection Help ')

    def _show_main_help(self, from_keyboard=False):
        txt = '''Up|,|j|,|PgUp|,
                 Down|,|k|,|PgDown    |Change station selection.
                 <n>g| / |<n>G      |Jump to first /last or n-th station.
                 H M L            |Go to top / middle / bottom of screen.
                 P                |Go to |P|laying station.
                 Enter|,|Right|,|l    |Play selected station.
                 ^N| / |^P          |Play |N|ext or |P|revious station.
                 i                |Display station |i|nfo (when playing).
                 r                |Select and play a random station.
                 Space|,|Left|,|h     |Stop / start playing selected station.
                 Esc|,|q            |Quit.
                 !Volume management
                 -|/|+| or |,|/|.       |Change volume.
                 m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                 !Misc
                 o| / |s| / |R        ||O|pen / |S|ave / |R|eload playlist.
                 t| / |T| / |~        |Change |t|heme / |T|ransparency / Calc. Background.
                 c                |Open Configuration window.'''
        self._show_help(txt,
                        mode_to_set=self.ws.MAIN_HELP_MODE,
                        reset_metrics=False)
        self._help_metrics[self.ws.MAIN_HELP_MODE_PAGE_2] = self._help_metrics[self.ws.MAIN_HELP_MODE]
        self._help_metrics[self.ws.MAIN_HELP_MODE_PAGE_3] = self._help_metrics[self.ws.MAIN_HELP_MODE]
        self._help_metrics[self.ws.MAIN_HELP_MODE_PAGE_4] = self._help_metrics[self.ws.MAIN_HELP_MODE]
        self._help_metrics[self.ws.MAIN_HELP_MODE_PAGE_5] = self._help_metrics[self.ws.MAIN_HELP_MODE]
        if self._cnf.browsing_station_service and not from_keyboard:
            self._show_main_help_page_from_browser()

    def _show_main_help_page_2(self, from_keyboard=False):
        txt = '''!Playlist editing
                 a| / |A            |Add / append new station.
                 e                |Edit current station.
                 E                |Change station's encoding.
                 DEL|,|x            |Delete selected station.
                 !Alternative modes
                 \\                |Enter |Extra Commands| mode.
                 y                |Enter |Copy| mode.
                 '                |Enter |Register| mode.
                 Esc|,|q            |Exit alternative mode.
                 !Moving stations
                 J                |Create a |J|ump tag.
                 <n>^U|,|<n>^D      |Move station |U|p / |D|own.
                 ||_________________|If a |jump tag| exists, move it there.
                 !Searching
                 /| / |n| / |N        |Search, go to next / previous result.
                 !Stations' history
                 < |/| >            |Move to previous / next station.'''
        self._show_help(txt,
                        mode_to_set=self.ws.MAIN_HELP_MODE_PAGE_2,
                        reset_metrics=False)

    def _show_main_help_page_3(self, from_keyboard=False):
        txt = '''p                |Paste unnamed register.
                 !Extra Command mode (\\)
                 \\                |Open previous playlist.
                 ]                |Open first opened playlist.
                 n                |Create a |n|ew playlist.
                 p                |Select playlist/register to |p|aste to.
                 r                ||R|ename current playlist.
                 C                ||C|lear all registers.
                 h                |Display |H|TML help.
                 !Copy mode (y)
                 ENTER            |Copy station to unnamed register.
                 a-z| / |0-9        |Copy station to named register.
                 !Registe mode (')
                 '                |Open registers list.
                 a-z| / |0-9        |Open named register.
                 !Player Customization
                 z                |Toggle "Force http connections"
                 Z                |Extra player parameters'''
        self._show_help(txt,
                        mode_to_set=self.ws.MAIN_HELP_MODE_PAGE_3,
                        reset_metrics=False)

    def _show_main_help_page_4(self, from_keyboard=False):
        txt = '''!Mouse Support
                 Click            |Change selection.
                 Double click     |Start / stop the player.
                 Middle click     |Toggle mute.
                 Wheel            |Page up / down.
                 Shift-Wheel      |Adjust volume.
                 !RadioBrowser
                 O                |Open |RadioBrowser|.
                 c                |Open |c|onfig window.
                 C                |Select server to |c|onnect to.
                 s                ||S|earch for stations.
                 S                ||S|ort search results.
                 I                |Station |i|nfo (current selection).
                 V                ||V|ote for station.
                 \\\\ q Escape      |Close Browser (go back in history).

                 |Search history navigation works with normal keys as well
                 |(|^N| is the same as |n| when not in a line editor).'''
        self._show_help(txt,
                        mode_to_set=self.ws.MAIN_HELP_MODE_PAGE_4,
                        reset_metrics=False)

    def _show_main_help_page_5(self, from_keyboard=False):
        txt = '''!Recording
                 Veritcal line    |Enable / disable |recording|.
                 Space            |Pause / resume playback.
                 !Change Player
                 \m               |Open the |Player Selection| window.
                 !Remote Control Server
                 \s               |Start/Stop the |Server|.
                 !Title Logger
                 W                |Toggle Logger on/off
                 w                |Tag a station as liked
                 !Group Management
                 a A              |Add a |Group| (set |URL| = |-|).
                 ^E |/ |^Y          |Go to next /previous |Group|.
                 ^G               |Open the |Group Selection| window.
                 !Windows Only
                 F8               |Players management.
                 F9               |Show |EXE| location.
                 F10              |Uninstall |PyRadio|.'''
        self._show_help(txt,
                        mode_to_set=self.ws.MAIN_HELP_MODE_PAGE_5,
                        reset_metrics=False)

    def _show_main_help_page_from_browser(self):
        if self._cnf._online_browser.BROWSER_NAME == 'RadioBrowser':
            self.ws.close_window()
            self._show_main_help_page_4()
            self._main_help_id = 3

    def _show_playlist_help(self):
        txt = '''Up|,|j|,|PgUp|,
                 Down|,|k|,|PgDown    |Change register selection.
                 <n>g| / |<n>G      |Jump to first /last or n-th station.
                 M| / |P            |Jump to |M|iddle / loaded register.
                 Enter|,|Right|,|l    |Open selected register.
                 r                |Re-read registers from disk.
                 '                |Toggle between playlists / registers.
                 /| / |n| / |N        |Search, go to next / previous result.
                 \\                |Enter |Extra Commands| mode.
                 Esc|,|q|,|Left|,|h     |Cancel.
                 %_Global functions (with \ on Line editor)_
                 -|/|+| or |,|/|.       |Change volume.
                 m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                 W| / |w            |Toggle title log / like a station.
                 %_Other Keys_
                 t| / |T            |Load |t|heme / |T|oggle transparency.'''
        if self._cnf.open_register_list:
            self._show_help(txt,
                            mode_to_set=self.ws.PLAYLIST_HELP_MODE,
                            caption=' Registers List Help ')
        else:
            self._show_help(txt,
                            mode_to_set=self.ws.PLAYLIST_HELP_MODE,
                            caption=' Playlist Help ')

    def _show_theme_help(self):
            txt = '''Up|,|j|,|PgUp|,
                     Down|,|k|,|PgDown    |Change theme selection.
                     g| / |<n>G         |Jump to first or n-th / last theme.
                     Enter|,|Right|,|l    |Apply selected theme.
                     Space            |Apply theme and make it default.
                     c                |Make theme default and watch it for
                     |                 changes (|User Themes| only).
                     T                |Toggle theme transparency.
                     r                |Rescan disk for user themes.
                     /| / |n| / |N        |Search, go to next / previous result.
                     Esc|,|q|,|Left|,|h     |Close window.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.       |Change volume.
                     m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w            |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.THEME_HELP_MODE,
                            caption=' Themes Help ')

    def _show_search_help(self):
        if platform.lower().startswith('darwin'):
            txt = '''Left| / |Right        |Move to next / previous character.
            HOME|,|^A| / |END|,|^E    |Move to start / end of line.
            ^W| / |^K             |Clear to start / end of line.
            ^U                  |Clear line.
            DEL|,|^D              |Delete character.
            Backspace|,|^H        |Backspace (delete previous character).
            Up|,|^P| / |Down|,|^N     |Get previous / next history item.
            \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
            Enter| / |Esc         |Perform / cancel search.

            |Global functions work when preceded with a "|\|".
            '''
        else:
            txt = '''Left| / |Right        |Move to next / previous character.
            Up| / |Down           |Cycle within history.
            M-F| / |M-B           |Move to next / previous word.
            HOME|,|^A| / |END|,|^E    |Move to start / end of line.
            ^W| / |M-D|,|^K         |Clear to start / end of line.
            ^U                  |Clear line.
            ^X                  |Remove history item.
            DEL|,|^D              |Delete character.
            Backspace|,|^H        |Backspace (delete previous character).
            Up|,|^P| / |Down|,|^N     |Get previous / next history item.
            \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
            Enter| / |Esc         |Perform / cancel search.

            |Global functions work when preceded with a "|\|".
            '''
            if platform.startswith('win'):
                txt = txt.replace('M-', 'A-')
        self._show_help(txt,
                        mode_to_set=self.ws.SEARCH_HELP_MODE,
                        caption=' Search Help ')

    def _show_params_ediror_help(self):
        if platform.lower().startswith('darwin'):
            txt = '''Left| / |Right        |Move to next / previous character.
            HOME|,|^A| / |END|,|^E    |Move to start / end of line.
            ^W| / |^K             |Clear to start / end of line.
            ^U                  |Clear line.
            DEL|,|^D              |Delete character.
            Backspace|,|^H        |Backspace (delete previous character).
            Up| / |Down           |Go to previous / next field.
            \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
            Esc                 |Cancel operation.

            |Global functions work when preceded with a "|\|".
            '''
        else:
            txt = '''Left| / |Right        |Move to next / previous character.
            M-F| / |M-B           |Move to next / previous word.
            HOME|,|^A| / |END|,|^E    |Move to start / end of line.
            ^W| / |M-D|,|^K         |Clear to start / end of line.
            ^U                  |Clear line.
            DEL|,|^D              |Delete character.
            Backspace|,|^H        |Backspace (delete previous character).
            Up| / |Down           |Go to previous / next field.
            \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
            Esc                 |Cancel operation.

            |Global functions work when preceded with a "|\|".
            '''
            if platform.startswith('win'):
                txt = txt.replace('M-', 'A-')
        self._show_help(txt,
                        mode_to_set=self.ws.IN_PLAYER_PARAMS_EDITOR_HELP_MODE,
                        caption=' Line Editor Help ')

    def _show_line_editor_help(self):
        if self.ws.operation_mode in (self.ws.RENAME_PLAYLIST_MODE, self.ws.CREATE_PLAYLIST_MODE) \
                or  self.ws.previous_operation_mode in (self.ws.RENAME_PLAYLIST_MODE, self.ws.CREATE_PLAYLIST_MODE):
            if platform.lower().startswith('darwin'):
                txt = '''Left| / |Right        |Move to next / previous character.
                HOME|,|^A| / |END|,|^E    |Move to start / end of line.
                ^W| / |^K             |Clear to start / end of line.
                ^U                  |Clear line.
                DEL|,|^D              |Delete character.
                Backspace|,|^H        |Backspace (delete previous character).
                Up| / |Down           |Go to previous / next field.
                \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
                Esc                 |Cancel operation.

                |Global functions work when preceded with a "|\|".
                '''
            else:
                txt = '''Left| / |Right        |Move to next / previous character.
                M-F| / |M-B           |Move to next / previous word.
                HOME|,|^A| / |END|,|^E    |Move to start / end of line.
                ^W| / |M-D|,|^K         |Clear to start / end of line.
                ^U                  |Clear line.
                DEL|,|^D              |Delete character.
                Backspace|,|^H        |Backspace (delete previous character).
                Up| / |Down           |Go to previous / next field.
                \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
                Esc                 |Cancel operation.

                |Global functions work when preceded with a "|\|".
                '''
        else:
            if platform.lower().startswith('darwin'):
                txt = '''Left| / |Right        |Move to next / previous character.
                HOME|,|^A| / |END|,|^E    |Move to start / end of line.
                ^W| / |^K             |Clear to start / end of line.
                ^U                  |Clear line.
                DEL|,|^D              |Delete character.
                Backspace|,|^H        |Backspace (delete previous character).
                Up| / |Down           |Go to previous / next field.
                \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
                \p                  |Enable |p|aste mode to correctly paste
                ____________________|URLs (and stations' names).
                Esc                 |Cancel operation.

                |Global functions work when preceded with a "|\|".
                '''
            else:
                txt = '''Left| / |Right        |Move to next / previous character.
                M-F| / |M-B           |Move to next / previous word.
                HOME|,|^A| / |END|,|^E    |Move to start / end of line.
                ^W| / |M-D|,|^K         |Clear to start / end of line.
                ^U                  |Clear line.
                DEL|,|^D              |Delete character.
                Backspace|,|^H        |Backspace (delete previous character).
                Up| / |Down           |Go to previous / next field.
                \\?| / |\\\\             |Insert a "|?|" or a "|\\|", respectively.
                \p                  |Enable |p|aste mode to correctly paste
                ____________________|URLs (and stations' names).
                Esc                 |Cancel operation.

                |Global functions work when preceded with a "|\|".
                '''
            if platform.startswith('win'):
                txt = txt.replace('M-', 'A-')
        self._show_help(txt,
                        mode_to_set=self.ws.LINE_EDITOR_HELP_MODE,
                        caption=' Line Editor Help ')

    def _show_config_help(self):
            txt = '''Up|,|j|,|PgUp|,
                     Down|,|k|,|PgDown          |Change option selection.
                     g|,|Home| / |G|,|End         |Jump to first / last option.
                     Enter|,|Space|,|Right|,|l    |Change option value.
                     r                      |Revert to saved values.
                     d                      |Load default values.
                     s                      |Save config.
                     Esc|,|q|,|Left|,|h           |Cancel.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.             |Change volume.
                     m| / |v                  ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w                  |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.CONFIG_HELP_MODE,
                            caption=' Configuration Help ')

    def _show_config_player_help(self):
        if self._player_select_win.editing > 0:
            self._show_line_editor_help()
        elif self._player_select_win.focus:
            txt = '''TAB              |Move selection to |Extra Parameters| column.
                     Up|,|j|,|Down|,|k      |Change player selection.
                     Enter|,|Space
                     Right|,|l          |Enable / disable player.
                     ^U|/|^D            |Move player |u|p or |d|own.
                     r                |Revert to saved values.
                     s                |Save players (selection and parameters).
                     Esc|,|q|,|Left|,|h     |Cancel.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.       |Change volume.
                     m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w            |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.SELECT_PLAYER_HELP_MODE,
                            caption=' Player Selection Help ')
        else:
            if self._player_select_win.from_config:
                txt = ''' TAB              |Move selection to |Player Selection| column.
                         Up|,|j|,|Down|,|k
                         PgUp|, |PgDn       |Change selection.
                         g| / |G            |Move to first / last item.
                         Enter|,|Space
                         Right|,|l          |Activate current selection.
                         a| / |e| / |x|,|DEL    ||A|dd / |e|dit / |d|elete item.
                         r                |Revert to saved values.
                         s                |Save players (selection and parameters).
                         Esc|,|q|,|Left|,|h     |Cancel.
                         %_Global functions (with \ on Line editor)_
                         -|/|+| or |,|/|.       |Change volume.
                         m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                         W| / |w            |Toggle title log / like a station.'''
            else:
                txt = '''Up|,|j|,|Down|,|k
                         PgUp|, |PgDn       |Change selection.
                         g| / |G            |Move to first / last item.
                         Enter|,|Space
                         Right|,|l          |Activate current selection.
                         Esc|,|q|,|Left|,|h     |Cancel.
                         %_Global functions (with \ on Line editor)_
                         -|/|+| or |,|/|.       |Change volume.
                         m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                         W| / |w            |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.SELECT_PLAYER_HELP_MODE,
                            caption=' Player Extra Parameters Help ')

    def _show_config_playlist_help(self):
            txt = '''Up|,|j|,|PgUp|,
                     Down|,|k|,|PgDown    |Change playlist selection.
                     g| / |<n>G         |Jump to first or n-th / last playlist.
                     Enter|,|Space|,
                     Right|,|l          |Select default playlist.
                     /| / |n| / |N        |Search, go to next / previous result.
                     r                |Revert to saved value.
                     Esc|,|q|,|Left|,|h     |Canel.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.       |Change volume.
                     m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w            |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.SELECT_PLAYLIST_HELP_MODE,
                            caption=' Playlist Selection Help ')

    def _show_config_station_help(self):
            txt = '''Up|,|j|,|PgUp|,
                     Down|,|k|,|PgDown    |Change station selection.
                     g| / |<n>G         |Jump to first or n-th / last station.
                     M                |Jump to the middle of the list.
                     Enter|,|Space|,
                     Right|,|l          |Select default station.
                     /| / |n| / |N        |Search, go to next / previous result.
                     r                |Revert to saved value.
                     Esc|,|q|,|Left|,|h     |Canel.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.       |Change volume.
                     m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w            |Toggle title log / like a station.'''
            self._show_help(txt,
                            mode_to_set=self.ws.SELECT_STATION_HELP_MODE,
                            caption=' Station Selection Help ')

    def _show_config_encoding_help(self):
            txt = '''Arrows|,|h|,|j|,|k|,|l|,|PgUp|,|,PgDn
                     g|,|Home|,|G|,|End     |Change encoding selection.
                     Enter|,|Space|,|s    |Save encoding.
                     r c              |Revert to station / |c|onfig value.
                     Esc|,|q            |Cancel.
                     %_Global functions (with \ on Line editor)_
                     -|/|+| or |,|/|.       |Change volume.
                     m| / |v            ||M|ute player / Save |v|olume (not in vlc).
                     W| / |w            |Toggle title log / like a station.'''
            if self.ws.operation_mode == self.ws.SELECT_ENCODING_MODE:
                txt = txt.replace('r c              |Revert to station / |c|onfig value.', 'r                |Revert to saved value.')
            self._show_help(txt,
                            mode_to_set=self.ws.SELECT_ENCODING_HELP_MODE,
                            caption=' Encoding Selection Help ')

    def _show_register_help(self):
        txt = ''''            |Open registers list.
                 a-z| / |0-9    |Open named register.

                 |Any other key exits current mode.
              '''
        self._show_help(txt, mode_to_set=self.ws.REGISTER_HELP_MODE, caption=' Registers Mode Help ')

    def _show_extra_commands_help(self):
        if self.ws.operation_mode == self.ws.NORMAL_MODE or \
                (self.ws.operation_mode == self.ws.EXTRA_COMMANDS_HELP_MODE and \
                 self.ws.previous_operation_mode == self.ws.NORMAL_MODE):
            txt = '''\\      |Open previous playlist.
                     ]      |Open first opened playlist.
                     l      |Toggle |Open last playlist|.
                     m      |Cahnge |m|edia player.
                     n      |Create a |n|ew playlist.
                     p      |Select playlist/register to |p|aste to.
                     r      ||R|ename current playlist.
                     C      ||C|lear all registers.
                     u      |Show |U|nnamed Register.
                     o      ||O|pen  config dir in file manager.

                    |Any other key exits current mode.
                  '''
            if self._cnf.is_register:
                txt = txt.replace('C  ', 'c      |Clear |c|urrent register.\nC  ').replace('current playlist', 'current register')
        else:
            ''' we are on playlist view '''
            if self._cnf.open_register_list:
                txt = '''r      ||R|ename current register.
                         p      ||P|aste to current register.
                         c      |Clear |c|urrent register.
                         C      ||C|lear all registers.
                         u      |Show |U|nnamed Register.
                         o      ||O|pen  config dir in file manager.

                        |Any other key exits current mode.
                       '''
            else:
                txt = '''n      |Create a |n|ew playlist.
                         p      ||P|aste to current playlist.
                         r      ||R|ename current playlist.
                         u      |Show |U|nnamed Register.
                         o      ||O|pen  config dir in file manager.

                        |Any other key exits current mode.
                       '''
        self._show_help(txt,
                        mode_to_set=self.ws.EXTRA_COMMANDS_HELP_MODE,
                        caption=' Extra Commands Help ')

    def _show_unnamed_register(self):
        if self._unnamed_register:
            txt = '\n|___' + self._unnamed_register[0] + '___\n'
        else:
            txt = '\n|___----==== Empty ====----___\n'
        self._show_help(txt,
                        mode_to_set=self.ws.UNNAMED_REGISTER_MODE,
                        caption=' Unnamed Register ',
                        prompt='')

    def _show_yank_help(self):
        txt = '''ENTER        |Copy station to unnamed register.
                 a-z| / |0-9    |Copy station to named register.

                 |Any other key exits current mode.
                 '''
        self._show_help(txt,
                        mode_to_set=self.ws.YANK_HELP_MODE,
                        caption=' Copy Mode Help')

    def _print_vote_result(self):
        txt = '''
                You have just voted for the following station:
                ____|{0}|

                 Voting result:
                 ____|{1}|
                 '''
        self._show_help(txt.format(self._cnf._online_browser.vote_result[0],
                                   self._cnf._online_browser.vote_result[1]),
                        self.ws.VOTE_RESULT_MODE,
                        caption=' Station Vote Result ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_mouse_restart_info(self):
        txt = '''
                You have just changed the mouse support config
                 option.

                 |PyRadio| must be |restarted| for this change to
                 take effect.
                 '''
        self._show_help(txt, self.ws.MOUSE_RESTART_INFO_MODE,
                        caption=' Program Restart required ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_session_locked(self):
        txt = '''
                This session is |locked| by another |PyRadio instance|.

                 You can still play stations, load and edit playlists,
                 load and test themes, but any changes will |not| be
                 recorded in the configuration file.

                 If you are sure this is the |only| active |PyRadio|
                 instance, exit |PyRadio| now and execute the following
                 command: |pyradio --unlock|
                 '''
        self._show_help(txt, self.ws.SESSION_LOCKED_MODE,
                        caption=' Session Locked ',
                        prompt=' Press any key... ',
                        is_message=True)

        txt = '''
                This session is |locked| by another |PyRadio instance|.

                 You can still play stations, load and edit playlists,
                 load and test themes, but any changes will |not| be
                 recorded in the configuration file.

                 If you are sure this is the |only| active |PyRadio|
                 instance, exit |PyRadio| now and execute the following
                 command: |pyradio --unlock|
                 '''
        self._show_help(txt, self.ws.SESSION_LOCKED_MODE,
                        caption=' Session Locked ',
                        prompt=' Press any key... ',
                        is_message=True)

        txt = '''
                This session is |locked| by another |PyRadio instance|.

                 You can still play stations, load and edit playlists,
                 load and test themes, but any changes will |not| be
                 recorded in the configuration file.

                 If you are sure this is the |only| active |PyRadio|
                 instance, exit |PyRadio| now and execute the following
                 command: |pyradio --unlock|
                 '''
        self._show_help(txt, self.ws.SESSION_LOCKED_MODE,
                        caption=' Session Locked ',
                        prompt=' Press any key... ',
                        is_message=True)

        txt = '''
                This session is |locked| by another |PyRadio instance|.

                 You can still play stations, load and edit playlists,
                 load and test themes, but any changes will |not| be
                 recorded in the configuration file.

                 If you are sure this is the |only| active |PyRadio|
                 instance, exit |PyRadio| now and execute the following
                 command: |pyradio --unlock|
                 '''
        self._show_help(txt, self.ws.SESSION_LOCKED_MODE,
                        caption=' Session Locked ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_remote_control_server_error(self, msg=None):
        if msg:
            self._server_error_msg = str(msg)
        txt = '''
            The Remote Control Server |failed| to start!
            The error message is:
            __|{}

            This is probably because another (|PyRadio?|) process
            is already using the requested |Server Port|.

            Close this window, press "|\s|", select a |different
            |port| and try to start the |Server| again.
        '''.format(self._server_error_msg)
        self._show_help(txt, self.ws.REMOTE_CONTROL_SERVER_START_ERROR_MODE,
                        caption=' Server Error ',
                        prompt=' Press any key... ',
                        is_message=True)
        self._remote_control_server = self._remote_control_server_thread = None

    def _print_remote_control_server_dead_error(self, msg=None):
        if msg:
            self._server_dead_msg = str(msg)
        txt = '''
            The Remote Control Server |terminated| with
            message:
            __|{}

        '''.format(self._server_dead_msg)
        self._show_help(txt, self.ws.REMOTE_CONTROL_SERVER_DEAD_ERROR_MODE,
                        caption=' Server Error ',
                        prompt=' Press any key... ',
                        is_message=True)
        self._remote_control_server = self._remote_control_server_thread = None

    def _print_change_player_one_player_error(self):
        players = [x.PLAYER_NAME for x in player.Player.__subclasses__() if x.PLAYER_NAME != self.player.PLAYER_NAME]
        logger.error('players = {}'.format(players))
        txt = '''
            You have requested to change the |Media Player| but
            there's only one player detected.

            If you have already installed any other player
            (|{0}| or |{1}|), please make sure its executable
            is in your PATH.
        '''.format(
                players[0],
                players[1]
        )
        self._show_help(txt, self.ws.CHANGE_PLAYER_ONE_PLAYER_ERROR_MODE,
                        caption=' PyRadio ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_change_player_same_player_error(self):
        txt = '''
            |{}|: Media Player already active.

            You have requested to change the |Media Player| to
            the one that's already active.

            Please try selecting a different |Media Player|.
        '''.format(self.player.PLAYER_NAME)
        self._show_help(txt, self.ws.CHANGE_PLAYER_SAME_PLAYER_ERROR_MODE,
                        caption=' PyRadio ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_not_implemented_yet(self):
        txt = '''
            This feature has not been implemented yet...
        '''
        self._show_help(txt, self.ws.NOT_IMPLEMENTED_YET_MODE,
                        caption=' PyRadio ',
                        prompt=' Press any key... ',
                        is_message=True)

    def _print_handle_foreign_playlist(self):
        txt = '''
            This is a "|foreign|" playlist (i.e. it does not
            reside in PyRadio's config directory). If you
            want to be able to easily load it again in the
            future, it should be copied there.

            Do you want to copy it in the config directory?

            Press "|y|" to confirm or "|n|" to reject'''
        self._show_help(txt, self.ws.FOREIGN_PLAYLIST_ASK_MODE,
                        caption=' Foreign playlist ',
                        prompt=' ',
                        is_message=True)

    def _print_foreign_playlist_message(self):
        ''' reset previous message '''
        self.ws.close_window()
        self.refreshBody()
        ''' display new message '''
        txt = '''
            A playlist by this name:
            __"|{0}|"
            already exists in the config directory.

            This playlist was saved as:
            __"|{1}|"
            '''.format(self._cnf.foreign_title, self._cnf.station_title)
        self._show_help(txt, self.ws.FOREIGN_PLAYLIST_MESSAGE_MODE,
                        caption=' Foreign playlist ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_foreign_playlist_copy_error(self):
        ''' reset previous message '''
        self.ws.close_window()
        self.refreshBody()
        txt = '''
            Foreign playlist copying |failed|!

            Make sure the file is not open with another
            application and try to load it again
            '''
        self._show_help(txt, self.ws.FOREIGN_PLAYLIST_COPY_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_recovery_error(self):
        if self._playlist_error_message:
            txt = self._playlist_error_message
        else:
            if self._cnf.playlist_recovery_result == 1:
                txt = '''
                    Both a playlist file (CSV) and a playlist backup
                    file (TXT) exist for the selected playlist. In
                    this case, PyRadio would try to delete the CSV
                    file, and then rename the TXT file to CSV.\n
                    Unfortunately, deleting the CSV file has failed,
                    so you have to manually address the issue.
                    '''
            else:
                txt = '''
                    A playlist backup file (TXT) has been found for
                    the selected playlist. In this case, PyRadio would
                    try to rename this file to CSV.\n
                    Unfortunately, renaming this file has failed, so
                    you have to manually address the issue.
                    '''
        self._show_help(txt, self.ws.PLAYLIST_RECOVERY_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _show_no_themes(self):
        if self._cnf.show_no_themes_message:
            txt = '''||Curses| (the library this program is based on), will not display
                     |colors |correctly| in this terminal, (after they have been |changed by
                     |PyRadio.

                     |Therefore, using |themes is disabled| and the |default theme| is used.

                     |For more info, please refer to:
                     ||https://github.com/coderholic/pyradio/#virtual-terminal-restrictions

                     |Press "|x|" to never display this message in the future, or
                  '''
            caption = ' Themes Disabled '

            self._show_help(txt, mode_to_set=self.ws.NO_THEMES_MODE, caption=caption)
            self._cnf.no_themes_notification_shown = True

    def _print_playlist_not_found_error(self):
        if self._playlist_error_message:
            txt = self._playlist_error_message
        else:
            txt = '''
                Playlist |not| found!

                This means that the playlist file was deleted
                (or renamed) some time after you opened the
                Playlist Selection window.
                '''
        self._show_help(txt, self.ws.PLAYLIST_NOT_FOUND_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_load_error(self):
        if self._playlist_error_message:
            txt = self._playlist_error_message
        else:
            txt = '''
                Playlist loading |failed|!

                This means that either the file is corrupt,
                or you are not permitted to access it.
                '''
        self._show_help(txt, self.ws.PLAYLIST_LOAD_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_reload_error(self):
        txt = '''
            Playlist reloading |failed|!

            You have probably edited the playlist with an
            external program. Please re-edit it and make
            sure that only one "," exists in each line.
            '''
        self._show_help(txt, self.ws.PLAYLIST_RELOAD_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_py2_editor_error(self):
        txt = '''
            Non-ASCII characters editing is |not supported!|

            You are running |PyRadio| on |Python 2|. As a result,
            the station editor only supports |ASCII characters|,
            but the station name you are trying to edit contains
            |non-ASCII| characters.

            To edit this station, either run |PyRadio| on |Python 3|,
            or edit the playlist with an external editor and then
            reload the playlist.
            '''
        self._show_help(txt, self.ws.PY2_EDITOR_ERROR,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_dnspython_not_installed_error(self):
        txt = '''
        Module "|dnspython|" not found!

        In order to use |RadioBrowser| stations directory
        service, the "|dnspython|" module must be installed.

        Exit |PyRadio| now, install the module (named
        |python-dnspython| or |python{}-dnspython|) and try
        executing |PyRadio| again.
        '''
        self._show_help(txt.format(python_version[0]),
                        self.ws.DNSPYTHON_MODULE_NOT_INSTALLED_ERROR,
                        caption=' Module Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_netifaces_not_installed_error(self):
        txt = '''
        Module "|netifaces|" not found!

        In order to use the |Remote Control Server|, the
        "|netifaces|" module must be installed.

        Exit |PyRadio| now, install the module (named
        |python-netifaces| or |python{}-netifaces|) and try
        executing |PyRadio| again.
        '''
        self._show_help(txt.format(python_version[0]),
                        self.ws.NETIFACES_MODULE_NOT_INSTALLED_ERROR,
                        caption=' Module Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_requests_not_installed_error(self):
        txt = '''
        Module "|requests|" not found!

        In order to use an online stations directory
        service, the "|requests|" module must be installed.

        Exit |PyRadio| now, install the module (named
        |python-requests| or |python{}-reuqests|) and try
        executing |PyRadio| again.
        '''
        self._show_help(txt.format(python_version[0]),
                        self.ws.REQUESTS_MODULE_NOT_INSTALLED_ERROR,
                        caption=' Module Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_not_saved_error(self):
        txt = '''
            Current playlist is modified and cannot be renamed.

            Please save the playlist and try again.
            '''
        self._show_help(txt,
                        self.ws.PLAYLIST_NOT_SAVED_ERROR_MODE,
                        caption=' Playlist Modified ',
                        prompt=' Press any key to hide ',
                        is_message=True)

    def _print_register_save_error(self):
        txt = '''
            Error saving register file:
            __"|{}|"
            '''
        if len(self._failed_register_file) + 10 > self.bodyMaxX:
            string_to_display = self._failed_register_file.replace(self._cnf.stations_dir, '[CONFIG DIR]').replace('_', '¸')
        else:
            string_to_display = self._failed_register_file.replace('_', '¸')
        self._show_help(txt.format(string_to_display),
                        self.ws.REGISTER_SAVE_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key to hide ',
                        is_message=True)

    def _print_station_info_error(self):
        txt = '''
        Station info not available at this time,
        since it comes from the data provided by
        the station when connecting to it.

        Please play a station to get its info, (or
        wait until one actually starts playing).
        '''
        self._show_help(txt, self.ws.STATION_INFO_ERROR_MODE,
                        caption=' Station Info Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_copy_error(self):
        txt = '''
        An error occured while copying the playlist
        "|{0}|"
        to
        "|{1}|"

        Please make sure that:
        __1. The file system (disk/partition) is not full.
        __2. The original playlist has not been deleted.
        and try again.
        '''
        x = (self.old_filename, self.new_filename)
        tmp = []
        too_wide = False
        for n in x:
            if cjklen(n) > self.bodyMaxX - 10:
                too_wide = True
                break
        for n in x:
            if too_wide:
                tmp.append(n.replace(self._cnf.stations_dir, '[CONFIG DIR]').replace('_', '¸'))
            else:
                tmp.append(n.replace('_', '¸'))

        caption = ' Playlist Copy Error '
        if (self.ws.window_mode == self.ws.NORMAL_MODE and
                self._cnf.is_register) or \
                (self.ws.window_mode == self.ws.PLAYLIST_MODE and
                self._cnf._open_register_list):
            caption = ' Register Copy Error '
            txt = txt.replace('playlist', 'register')

        self._show_help(txt.format(*tmp),
                        self.ws.PLAYLIST_COPY_ERROR,
                        caption,
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_create_error(self):
        # TODO: write it!!!
        pass

    def _print_playlist_rename_error(self):
        txt = '''
        Succesfully copied playlist
        "|{0}|"
        to
        "|{1}|"
        but |deleting| the original playlist |has failed|.

        You will have to manually remove the original
        playlist (make sure that it is not used by
        another program before attempting it).
        '''
        x = (self.old_filename, self.new_filename)
        tmp = []
        too_wide = False
        for n in x:
            if cjklen(n) > self.bodyMaxX - 10:
                too_wide = True
                break
        for n in x:
            if too_wide:
                tmp.append(n.replace(self._cnf.stations_dir, '[CONFIG DIR]').replace('_', '¸'))
            else:
                tmp.append(n.replace('_', '¸'))

        caption = ' Playlist Copy Error '
        if (self.ws.window_mode == self.ws.NORMAL_MODE and
                self._cnf.is_register) or \
                (self.ws.window_mode == self.ws.PLAYLIST_MODE and
                self._cnf._open_register_list):
            caption = ' Register Copy Error '
            txt = txt.replace('playlist', 'register')
        self._show_help(txt.format(*tmp),
                        self.ws.PLAYLIST_RENAME_ERROR,
                        caption,
                        prompt=' Press any key ',
                        is_message=True)

    def _print_user_parameter_error(self):
        txt = '''
                The player parameter set you specified does
                not exist!

                |{0}| currently has |{1}| sets of parameters.
                You can press "|Z|" to access them, after you
                close this window.
        '''.format(self._cnf.PLAYER_NAME, len(self._cnf.params[self._cnf.PLAYER_NAME]) - 1)
        self._show_help(txt, self.ws.USER_PARAMETER_ERROR,
                        caption=' Parameter Set Error ',
                        prompt=' Press any key ',
                        is_message=True)
        self._cnf.user_param_id = 0

    def _print_unknown_browser_service(self):
        txt = '''
        The service you are trying to use is not supported.

        The service "|{0}|"
        (url: "|{1}|")
        is not implemented (yet?)

        If you want to help implementing it, please open an
        issue at "|https://github.com/coderholic/pyradio/issues|".
        '''
        self._show_help(txt.format(self.stations[self.selection][0],
                                   self.stations[self.selection][1]),
                        self.ws.UNKNOWN_BROWSER_SERVICE_ERROR,
                        caption=' Unknown Service ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_theme_download_error(self):
        if self._screen_ready:
            self._cnf.theme_not_supported = False
            self._cnf.theme_has_error = False
            self._cnf.theme_download_failed = False
            self._cnf.theme_not_supported_notification_shown = False
            txt='____|Theme download failed!!!|____\n______Loading |default| theme..._____'

            self._show_help(txt,
                            mode_to_set=self.ws.operation_mode,
                            caption='',
                            prompt='', is_message=True)
            a_thread = threading.Timer(1.75, self.refreshBody)
            a_thread.start()
            a_thread.join()

    def _print_not_applicable(self):
        txt = ('_Operation not applicable here_',
               '___Nope, not here!___'
        )
        msg = None
        for n in txt:
            if len(n) + 2 < self.bodyMaxX:
                msg = n
                break
        if msg is not None:
            self._show_notification_with_delay(
                txt=msg,
                delay=1.25,
                mode_to_set=self.ws.operation_mode,
                callback_function=self.refreshBody
            )

    def _print_service_connection_error(self):
        txt = '''
        Service temporarily unavailable.

        This may mean that your internet connection has
        failed, or that the service has failed, in which
        case you should try again later.
        '''
        self._show_help(txt,
                        self.ws.SERVICE_CONNECTION_ERROR,
                        caption=' Service Unavailable ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_servers_unreachable(self):
        txt = '''
        No server responds to ping.

        You will be able to edit the config file, but
        you will not be able to select a default server.
        '''
        self._show_help(txt,
                        self.ws.SERVICE_SERVERS_UNREACHABLE,
                        caption=' Servers Unreachable ',
                        prompt=' Press any key ',
                        is_message=True)

    def _show_player_changed_in_config(self):
        txt = '''
        |PyRadio| default player has changed from
        __"|{0}|"
        to
        __"|{1}|".

        This change may lead to changing the player used,
        and will take effect next time you open |PyRadio|.
        '''
        self._show_help(txt.format(*self._cnf.player_values),
                        self.ws.PLAYER_CHANGED_INFO_MODE,
                        caption=' Default Player Changed ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_playlist_reload_confirmation(self):
        if self._cnf.locked:
            txt = '''
                This playlist has not been modified within
                PyRadio. Do you still want to reload it?

                Press "|y|" to confirm, or any other key to cancel
                '''
        else:
            txt = '''
                This playlist has not been modified within
                PyRadio. Do you still want to reload it?

                Press "|y|" to confirm, "|Y|" to confirm and not
                be asked again, or any other key to cancel
                '''
        self._show_help(txt, self.ws.PLAYLIST_RELOAD_CONFIRM_MODE,
                        caption=' Playlist Reload ',
                        prompt=' ',
                        is_message=True)

    def _print_playlist_dirty_reload_confirmation(self):
        if self._cnf.locked:
            txt = '''
                This playlist has been modified within PyRadio.
                If you reload it now, all modifications will be
                lost. Do you still want to reload it?

                Press "|y|" to confirm, or "|n|" to cancel
                '''
        else:
            txt = '''
                This playlist has been modified within PyRadio.
                If you reload it now, all modifications will be
                lost. Do you still want to reload it?

                Press "|y|" to confirm, "|Y|" to confirm and not be
                asked again, or "|n|" to cancel
                '''
        self._show_help(txt, self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE,
                        caption=' Playlist Reload ',
                        prompt=' ',
                        is_message=True)

    def _print_save_modified_playlist(self, mode):
        if self._cnf.locked:
            txt = '''
                This playlist has been modified within
                PyRadio. Do you want to save it?

                If you choose not to save it now, all
                modifications will be lost.

                Press "|y|" to confirm, "|n|" to reject,
                or "|q|" or "|ESCAPE|" to cancel
                '''
        else:
            txt = '''
                This playlist has been modified within
                PyRadio. Do you want to save it?

                If you choose not to save it now, all
                modifications will be lost.

                Press "|y|" to confirm, "|Y|" to confirm and not
                be asked again, "|n|" to reject, or "|q|" or
                "|ESCAPE|" to cancel
                '''
        self._show_help(txt, mode,
                        caption=' Playlist Modified ',
                        prompt=' ',
                        is_message=True)

    def _print_save_playlist_error_1(self):
        txt = '''
            Saving current playlist |failed|!

            Could not open file for writing
            "|{}|"
            '''
        self._show_help(txt.format(self._cnf.station_path.replace('.csv',
                                                                  '.txt')),
                        mode_to_set=self.ws.SAVE_PLAYLIST_ERROR_1_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_save_playlist_error_2(self):
        txt = '''
            Saving current playlist |failed|!

            You will find a copy of the saved playlist in
            "|{}|"

            PyRadio will open this file when the playlist
            is opened in the future.
            '''
        self._show_help(txt.format(self._cnf.station_path.replace('.csv',
                                                                  '.txt')),
                        mode_to_set=self.ws.SAVE_PLAYLIST_ERROR_2_MODE,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_editor_name_error(self):
        txt = '''
            ___Incomplete Station Data provided!___

            ____Please provide a Station Name.___

            '''
        self._show_help(txt,
                        mode_to_set=self.ws.EDIT_STATION_NAME_ERROR,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_editor_url_error(self):
        if self._station_editor._line_editor[1].string.strip():
            txt = '''
                ____Errorenous Station Data provided!___

                _________Station URL is invalid!___
                ___Please provide a valid Station URL.___

                '''
        else:
            txt = '''
                ____Incomplete Station Data provided!___

                _________Station URL is empty!___
                ___Please provide a valid Station URL.___

                '''
        self._show_help(txt,
                        mode_to_set=self.ws.EDIT_STATION_URL_ERROR,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_icon_url_error(self):
        txt = '''
            ______Errorenous Station Data provided!___

            ________Station Icon URL is invalid!___
            ___Please provide a valid Station Icon URL.___

            '''
        self._show_help(txt,
                        mode_to_set=self.ws.EDIT_STATION_ICON_URL_ERROR,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_icon_url_format_error(self):
        txt = '''
            ______Errorenous Station Data provided!___

            ________Station Icon URL is invalid!___
            ____It must point to a JPG or a PNG file.__
            ___Please provide a valid Station Icon URL.___

            '''
        self._show_help(txt,
                        mode_to_set=self.ws.EDIT_STATION_ICON_FORMAT_ERROR,
                        caption=' Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_browser_config_save_error(self):
        if platform.startswith('win'):
            txt = '''
                ___Saving your configuration has failed!!!___

                ___Please make sure that the configuration file___
                ___is not opened in another application and that___
                ___there is enough free space in the drive and ___
                ___try again.___

                '''
        else:
            txt = '''
                ___Saving your configuration has failed!!!___

                ___Please make sure there is enought free space in___
                ___the file system and try again.___

                '''
        self._show_help(txt,
                        mode_to_set=self.ws.BROWSER_CONFIG_SAVE_ERROR_MODE,
                        caption=' Config Saving Error ',
                        prompt=' Press any key ',
                        is_message=True)

    def _print_ask_to_create_theme(self):
        txt = '''
            You have requested to edit a |read-only| theme,
            which is not possible. Do you want to create a
            new theme instead?

            Press "|y|" to accept or any other key to cancel.
            '''
        self._show_help(txt, self.ws.ASK_TO_CREATE_NEW_THEME_MODE,
                        caption=' Read-only theme ',
                        prompt=' ',
                        is_message=True)

    def _print_config_save_error(self):
        txt = '''An error occured while saving the configuration file!

            |PyRadio| will try to |restore| your previous settings,
            but in order to do so, it has to |terminate now!

            '''
        self._show_help(txt,
                        mode_to_set=self.ws.CONFIG_SAVE_ERROR_MODE,
                        caption=' Error Saving Config ',
                        prompt=' Press any key to exit ',
                        is_message=True)

    def _print_default_profile_edit_delete_error(self):
        txt = '''||
            This is the default parameter set for this player
            which cannot be edited or deleted.

            If you want to add a new parameter set, please press
            "|a|" to do so, after you close this window.
            '''
        self._show_help(txt,
                        mode_to_set=self.ws.PROFILE_EDIT_DELETE_ERROR_MODE,
                        caption=' Error ',
                        prompt=' Press any key to hide ',
                        is_message=True)

    def _print_max_number_of_profiles_error(self):
        txt = '''
            |||PyRadio| provides support for up to |10| extra player
            parameters sets, a limit which has already been reached.

            At this point you can either |e|dit an existing set or
            delete (|x|,|DEL|) an existing one and then |a|dd a new one.
            '''
        self._show_help(
            txt,
            mode_to_set=self.ws.MAXIMUM_NUMBER_OF_PROFILES_ERROR_MODE,
            caption=' Error ',
            prompt=' Press any key to hide ',
            is_message=True)

    def _print_update_notification(self):
        txt = '''
                A new |PyRadio| release (|{0}|) is available!

                 You are strongly encouraged to update now, so that
                 you enjoy new features and bug fixes.

                 Press |y| to update or any other key to cancel.
            '''
        self._show_help(txt.format(self._update_version_do_display),
                        mode_to_set=self.ws.UPDATE_NOTIFICATION_MODE,
                        caption=' Update Notification ',
                        prompt='',
                        is_message=True)
        self._update_version = ''

    def _print_update_ok_notification(self):
        if platform.startswith('win'):
            txt = '''
                    |PyRadio| will now terminate and the update script
                     will be created.

                     When Explorer opens please double click on
                     "|update.bat|" to start the update procedure.

                     Press any key to exit |PyRadio|.
                '''
        else:
            txt = '''
                    |PyRadio| will now be updated!

                     The program will now terminate so that the update_
                     procedure can start.

                     Press any key to exit |PyRadio|.
                '''
        self._show_help(txt.format(self._update_version_do_display),
                        mode_to_set=self.ws.UPDATE_NOTIFICATION_OK_MODE,
                        caption=' Update Notification ',
                        prompt='',
                        is_message=True)

    def _print_update_nok_notification(self):
        txt = '''
                You have chosen not to update |PyRadio| at this time!

                 Please keep in mind that you are able to update
                 at any time using the command:

                 ___________________|pyradio -U|
            '''
        self._show_help(txt.format(self._update_version_do_display),
                        mode_to_set=self.ws.UPDATE_NOTIFICATION_NOK_MODE,
                        caption=' Update Notification ',
                        prompt=' Press any key to hide ',
                        is_message=True)
        # delete date file?

    def _print_clear_register(self):
        txt = '''
            Are you sure you want to clear the contents
            of this register?

            This action is not recoverable!

            Press "|y|" to confirm, or "|n|" to cancel
            '''
        self._show_help(txt, self.ws.CLEAR_REGISTER_MODE,
                        caption=' Clear register ',
                        prompt=' ',
                        is_message=True)

    def _print_clear_all_registers(self):
        txt = '''
            Are you sure you want to clear the contents
            of all the registers?

            This action is not recoverable!

            Press "|y|" to confirm, or "|n|" to cancel
            '''
        self._show_help(txt, self.ws.CLEAR_ALL_REGISTERS_MODE,
                        caption=' Clear all registers ',
                        prompt=' ',
                        is_message=True)

    def _align_stations_and_refresh(self,
                                    cur_mode,
                                    a_startPos=-1,
                                    a_selection=-1,
                                    force_scan_playlist=False):
        # logger.error('DE al 1 active_stations = \n\n{}\n\n'.format(self.active_stations))
        need_to_scan_playlist = False
        ''' refresh reference '''
        self.stations = self._cnf.stations
        self.number_of_items = len(self.stations)

        if self.number_of_items == 0:
            ''' The playlist is empty '''
            # ok
            self.detect_if_player_exited = False
            if self.player.isPlaying():
                self.stopPlayer()
            self.playing, self.selection, self.stations, \
                self.number_of_items = (-1, 0, 0, 0)
            self.refreshBody()
            return
        else:
            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('self.playing = {}'.format(self.playing))
            if cur_mode == self.ws.REMOVE_STATION_MODE:
                # ok
                self.detect_if_player_exited = False
                ''' Remove selected station '''
                if self.player.isPlaying():
                    if self.selection == self.playing:
                        self.stopPlayer()
                        self.playing = -1
                    elif self.selection < self.playing:
                        self.playing -= 1
                else:
                    self.playing = -1
                if self.selection > self.number_of_items - self.bodyMaxY:
                    self.startPos -= 1
                    if self.selection >= self.number_of_items or \
                            self.selection >= self.startPos + self.maxY - 4:
                        self.selection -= 1
                if self.startPos < 0:
                    self.startPos = 0
            else:
                if not force_scan_playlist and self.player.isPlaying():
                    ''' The playlist is not empty '''
                    if self.playing > self.number_of_items - 1 or self._cnf.is_register:
                        ''' Previous playing station is now invalid
                            Need to scan playlist '''
                        need_to_scan_playlist = True
                    else:
                        if self.stations[self.playing][0] == self.active_stations[1][0]:
                            ''' ok, self.playing found, just find selection '''
                            self.selection = self._get_station_id(self.active_stations[0][0])
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('** Selected station is {0} at {1}'.format(self.stations[self.selection], self.selection))
                        else:
                            ''' station playing id changed, try previous station '''
                            self.playing -= 1
                            if self.playing == -1:
                                self.playing = len(self.stations) - 1
                            if self.stations[self.playing][0] == self.active_stations[1][0]:
                                ''' ok, self.playing found, just find selection '''
                                self.selection = self._get_station_id(self.active_stations[0][0])
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug('** Selection station is {0} at {1}'.format(self.stations[self.playing], self.playing))
                            else:
                                ''' self.playing still not found, have to scan playlist '''
                                need_to_scan_playlist = True
                else:
                    ''' not playing, can i get a selection? '''
                    need_to_scan_playlist = True

            if need_to_scan_playlist:
                # ok
                self.detect_if_player_exited = False
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Scanning playlist for stations...')
                # logger.error('DE \n\n{}\n\n'.format(self.active_stations))
                self.selection, self.playing = self._get_stations_ids((
                    self.active_stations[0][0],
                    self.active_stations[1][0]))
                if self.playing == -1:
                    self.stopPlayer()

                ''' calculate new position '''
                if self.player.isPlaying():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Setting playing station at {}'.format(self.playing))
                    self.setStation(self.playing)
                else:
                    if self.selection == -1:
                        if a_selection > -1:
                            self.selection = a_selection
                            self.startPos = a_startPos
                        else:
                            self.selection = 0
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Setting selection station at {}'.format(self.selection))
                    self.setStation(self.selection)

        if self.selection < 0:
            ''' make sure we have a valid selection '''
            self.selection = 0
            self.startPos = 0
        ''' make sure playing station is visible '''
        if cur_mode != self.ws.REMOVE_STATION_MODE:
            self._goto_playing_station(changing_playlist=True)

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('self.selection = {0}, self.playing = {1}, self.startPos = {2}'.format(self.selection, self.playing, self.startPos))
        if self._cnf.is_register:
            self.selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing, self._cnf.stations]
        else:
            self.selections[self.ws.NORMAL_MODE] = [self.selection, self.startPos, self.playing, self._cnf.stations]
        # self.ll('_align_stations_and_refresh')
        if self.ws.operation_mode == self.ws.NORMAL_MODE:
            self.refreshBody()
        else:
            logger.error('\n\n2 not refreshing\n\n')

    def _show_connect_to_server_message(self):
        ''' display a passive message telling the user
            to wait while connecting to server.

            To be used with onlines services only
        '''
        txt = '''Connecting to service.
                 ____Please wait...'''
        self._show_help(txt, self.ws.BROWSER_OPEN_MODE, caption=' ', prompt=' ', is_message=True)

    def _show_performing_search_message(self):
        ''' display a passive message telling the user
            to wait while performing search.

            To be used with onlines services only
        '''
        txt = '''__Performing search.__
                 ____Please wait...'''
        self._show_help(txt, self.ws.BROWSER_PERFORMING_SEARCH_MODE, caption=' ', prompt=' ', is_message=True)

    def _show_recording_status_in_header(
        self,
        from_header_update=False,
        player_disappeared=False
    ):
        logger.error('\n\n')
        if self._limited_height_mode or \
                self._limited_width_mode:
            return
        logger.info('player_disappeared = {}'.format(player_disappeared))
        if self.player.recording == 0:
            if not from_header_update:
                try:
                    self.outerBodyWin.addstr(
                        0, 1, '───', curses.color_pair(13)
                    )
                except:
                    self.outerBodyWin.addstr(
                        0, 1, '───'.encode('utf-8'), curses.color_pair(13)
                    )
            logger.info('w_header = " "')
        else:
            w_header = 'R' if self.player.isPlaying() else 'r'
            if player_disappeared or \
                    self.player.already_playing:
                w_header = 'r'
            logger.info('w_header = "{}"'.format(w_header))
            self.outerBodyWin.addstr(
                0, 1, '[', curses.color_pair(13)
            )
            self.outerBodyWin.addstr(w_header, curses.color_pair(4))
            self.outerBodyWin.addstr(']', curses.color_pair(13))
            if player_disappeared:
                logger.error('with refreshBody')
                self.refreshBody()

    def _open_playlist(self, a_url=None):
        ''' open playlist

            Parameters:
                a_url:  this should be an online service url
        '''
        self._cnf.save_station_position(self.startPos, self.selection, self.playing)
        self._set_active_stations()
        self._update_status_bar_right()
        if self._cnf.browsing_station_service:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Opening RadioBrowser...')
            # TODO
            if HAS_REQUESTS:
                if HAS_DNSPYTHON:
                    self._show_connect_to_server_message()
                    online_service_url = 'https://' + a_url if a_url else self.stations[self.selection][1]
                    try:
                        self._cnf.open_browser(
                            online_service_url,
                            self._return_from_online_browser_search,
                            None,
                            self._cannot_delete_function)
                    except TypeError:
                        pass
                    # logger.error('DE online browser = {}'.format(self._cnf._online_browser))
                    if self._cnf.online_browser:
                        self._cnf.online_browser.set_global_functions(self._global_functions)
                        tmp_stations = []
                        self._cnf.stations_history = self._cnf.online_browser.set_station_history(
                            execute_funct=self._load_playlist_and_station_from_station_history,
                            no_items_funct=self._show_no_station_history_notification,
                            pass_first_item_funct=self._show_first_station_history_notification,
                            pass_last_item_funct=self._show_last_station_history_notification
                        )

                        if not self._cnf._online_browser.initialize():
                            ''' browser cannot be opened '''
                            self._cnf.remove_from_playlist_history()
                            self.ws.close_window()
                            self._print_service_connection_error()
                            self._cnf.browsing_station_service = False
                            self._cnf.online_browser = None
                            self._cnf.stations_history = self._cnf.normal_stations_history
                            return

                        self.ws.close_window()

                        ''' make sure we don't send a wrong click '''
                        self._cnf._online_browser.search()
                    else:
                        self._cnf.remove_from_playlist_history()
                        self._print_unknown_browser_service()
                        self._cnf.browsing_station_service = False
                        self._cnf.online_browser = None
                else:
                    self._cnf.remove_from_playlist_history()
                    self._print_dnspython_not_installed_error()
                    self._cnf.browsing_station_service = False
            else:
                self._cnf.remove_from_playlist_history()
                self._print_requests_not_installed_error()
                self._cnf.browsing_station_service = False
        elif self._cnf.register_to_open:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Opening a playlist or a register...')
            ''' open a register '''
            # self.ws.window_mode = self.ws.PLAYLIST_MODE
            self._playlist_in_editor = self._cnf.register_to_open
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('opening register: ' + self._cnf.register_to_open)
            self._playlist_error_message = ''
            self.number_of_items = self._cnf.read_playlist_file(is_register=True)
            logger.error('DE number of items = {}'.format(self.number_of_items))
            # self.ll('before opening a register')
            self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
            self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
            self._give_me_a_search_class(self.ws.operation_mode)
            self._cnf.station_path = path.join(self._cnf.registers_dir, 'register_' + self._cnf.register_to_open + '.csv')
            self._cnf.station_file_name = path.basename(self._cnf.station_path)
            self._cnf.station_title = 'Register: ' + self._cnf.register_to_open
            if self.playing < 0 or self.selection < 0:
                self._put_selection_in_the_middle(force=True)
                self.refreshBody()
            if not path.exists(self._cnf.station_path):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Creating empty register file: ' + self._cnf.register_to_open)
                with open(self._cnf.station_path, "w", encoding='utf-8') as rr:
                    pass
            self._find_renamed_selection(self.ws.REGISTER_MODE,
                                         self._cnf.registers_dir,
                                         self._cnf.station_path)
            self.playlist_selections[self.ws.REGISTER_MODE] = self.selections[self.ws.REGISTER_MODE][:-1][:]
            self._cnf.register_to_open = None
            # self.ll('opening a register')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Opening list of playlists or registers...')
            ''' Open list of playlists or registers '''
            #if self._cnf._open_register_list:
            #    txt = '''Reading registers. Please wait...'''
            #else:
            #    txt = '''Reading playlists. Please wait...'''
            #self._show_help(txt, self.ws.NORMAL_MODE, caption=' ', prompt=' ', is_message=True)
            if self.ws.operation_mode != self.ws.PLAYLIST_MODE:
                self.selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing, self._cnf.stations]
            self.ws.window_mode = self.ws.PLAYLIST_MODE
            if self._cnf.open_register_list:
                if self._cnf.registers_exist():
                    self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.REGISTER_MODE]
                    self.selection, self.startPos, self.playing = self.playlist_selections[self.ws.REGISTER_MODE]
                    self.number_of_items, self.playing = self.readPlaylists()
                else:
                    self.ws.close_window()
                    self._update_status_bar_right(status_suffix='')
                    self._show_notification_with_delay(
                            txt='____All registers are empty!!!____',
                            mode_to_set=self.ws.NORMAL_MODE,
                            callback_function=self.refreshBody)
                    return
            else:
                self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
                self.selection, self.startPos, self.playing = self.playlist_selections[self.ws.operation_mode]
                self.number_of_items, self.playing = self.readPlaylists()
            self.stations = self._cnf.playlists
            if self.number_of_items > 0 or self._cnf.open_register_list:
                self.refreshBody()
        # self.ll('_open_playlist(): returning')

    def _return_from_online_browser_search(self, ret):
        ''' ret is (success, from user search)
                success
                    True or False
                from user search
                    if success is False
                        True if from user search or server change
                        False if from opening browser
        '''

        if self.ws.operation_mode in (
            self.ws.BROWSER_OPEN_MODE,
            self.ws.BROWSER_PERFORMING_SEARCH_MODE,
        ):
            self.ws.close_window()
        if not ret[0]:
            logger.error('DE operation mode = {}'.format(self.ws.operation_mode))
            if ret[2]:
                self._goto_history_back_handler()
            self._print_service_connection_error()
            return

        ''' get stations with online field '''
        tmp_stations = self._cnf._online_browser.stations(2)

        ''' set browser parent so that it resizes correctly '''
        if self._cnf.browsing_station_service:
            self._cnf._online_browser.parent = self.bodyWin

        if ret[1] == 0 and not self._cnf._online_browser.first_search:
            logger.error('DE --== no items found ==--\noperating mode = {}'.format(self.ws.operation_mode))
            ''' go back to search mode '''
            self.ws.operation_mode = self.ws.BROWSER_SEARCH_MODE
            ''' display no results message '''
            self._show_no_browser_results()

        else:
            self._cnf.stations = tmp_stations[:]
            self.stations = self._cnf.stations
            self._cnf._online_browser.vote_callback = self._print_vote_result
            self._cnf.online_browser.stations_history.clear()
            self._cnf.number_of_stations = len(self.stations)
            self._cnf.dirty_playlist = False
            #self._cnf.add_to_playlist_history(self._cnf.online_browser.BASE_URL, '', self._cnf.online_browser.TITLE, browsing_station_service=True)
            self._cnf.station_path = self._cnf.online_browser.BASE_URL
            self._cnf.station_title = self._cnf.online_browser.title
            self.number_of_items = len(self.stations)
            self.selection = 0
            self.startPos = 0
            self.setupAndDrawScreen()
            # self.detect_if_player_exited = False
            self._align_stations_and_refresh(self.ws.operation_mode)
            self._set_active_stations()

        ''' all consecutive searches will display the
            the 'no result' message'
        '''
        self._cnf._online_browser.first_search = False

    def _open_playlist_from_history(self,
                                    reset=False,
                                    list_of_registers=False,
                                    from_rename_action=False):
        '''Loads a playlist from history

        Parameters
        ----------
            reset
                If True, load the first history item (which will
                always be a local playlist).
                Default is False.
            list_of_registers
                If False, a playlist is loaded and displayed.
                If True, the list of registers is opened.
                Default is False.
            from_rename_action
                If True, do not update self.active_stations

        Returns
        -------
            True:  Browsing_station_service goes from True to False
                   i.e. going from online service browsing to local
                   playlist (needs resize to repaint the whole screen
                   and recalculate all windows)
            False: We do not need resize
        '''

        # logger.error('DE\n\n\n')
        # logger.error('DE\n\n =1= ps.p {}\n\n'.format(self._cnf._ps._p))
        result = True
        if not self._cnf.can_go_back_in_time and not list_of_registers:
            self._show_no_more_playlist_history()
            result = False
        if result:
            playlist_history = self._cnf.copy_playlist_history()
            # logger.error('DE playlist_history\n\n{}\n\n'.format(playlist_history))
            if not from_rename_action:
                self._set_active_stations()
            if reset:
                self._cnf.reset_playlist_history()
            if list_of_registers:
                self._cnf.pop_to_first_real_playlist()
                removed_playlist_history_item = self._cnf.history_item(-1)
            else:
                if from_rename_action:
                    removed_playlist_history_item = self._cnf.history_item(-1)
                else:
                    removed_playlist_history_item = self._cnf.remove_from_playlist_history()
            err_string = '"|{}|"'.format(self._cnf.station_title)

            # logger.error('DE {}'.format(self._cnf._ps._p))

            # logger.error('DE\n\n =2= ps.p {}\n\n'.format(self._cnf._ps._p))

            # logger.error('DE \nself._cnf.station_path = {}\n'.format(self._cnf.station_path))
            ret = self._cnf.read_playlist_file(stationFile=self._cnf.station_path)
            # logger.error('DE \nret = {}\n'.format(ret))
            # logger.error('DE\n\n\n')

            if ret == -1:
                #self.stations = self._cnf.playlists
                self._cnf.add_to_playlist_history(*removed_playlist_history_item)
                self._playlist_error_message = '''Cannot restore playlist
                    {}

                    The playlist file has been edited (and corrupted)
                    time after you opened subsequent playlist(s), or
                    its access rights have been changed since then.
                    '''.format(err_string.center(48, '_'))
                self._print_playlist_load_error()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Error loading playlist: "{}"'.format(self.stations[self.selection][-1]))
                result = False
            elif ret == -2:
                #self.stations = self._cnf.playlists
                self._cnf.add_to_playlist_history(*removed_playlist_history_item)
                self._playlist_error_message = '''Cannot restore playlist
                    {}

                    The playlist file was deleted (or renamed) some
                    time after you opened subsequent playlist(s).
                    '''.format(err_string.center(48, '_'))
                self._print_playlist_not_found_error()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Playlist not found: "{}"'.format(self.stations[self.selection][-1]))
                result = False
            elif ret == -7:
                self._cnf.add_to_playlist_history(*removed_playlist_history_item)
                if self._cnf.playlist_recovery_result == 1:
                    self._playlist_error_message = '''Cannot restore playlist
                        {}

                        Both a playlist file (CSV) and a playlist backup
                        file (TXT) exist for the selected playlist. In
                        this case, PyRadio would try to delete the CSV
                        file, and then rename the TXT file to CSV.\n
                        Unfortunately, deleting the CSV file has failed,
                        so you have to manually address the issue.
                        '''.format(err_string.center(48, '_'))
                else:
                    self._playlist_error_message = '''Cannot restore playlist
                        {}

                        A playlist backup file (TXT) has been found for
                        the selected playlist. In this case, PyRadio would
                        try to rename this file to CSV.\n
                        Unfortunately, renaming this file has failed, so
                        you have to manually address the issue.
                        '''.format(err_string.center(50, '_'))
                self._print_playlist_recovery_error()
                result = False
            else:
                self._playlist_in_editor = self._cnf.station_path
                self._playlist_error_message = ''
                self.number_of_items = ret
                if removed_playlist_history_item[-1]:
                    ''' coming back from online browser '''
                    self.playing = removed_playlist_history_item[-2]
                    self.selection = removed_playlist_history_item[-3]
                    self.startPos = removed_playlist_history_item[-4]
                    self._cnf.online_browser = None
                    self._cnf.stations_history = self._cnf.normal_stations_history
                else:
                    ''' coming back from local playlist '''
                    self.selection = self._cnf.history_selection
                    self.startPos = self._cnf.history_startPos

                # logger.error('DE old {}'.format(removed_playlist_history_item))
                #for n in self._cnf._ps._p:
                #    logger.error('DE cur {}'.format(n))
                # logger.error('DE \n\nselection = {0}, startPos = {1}, playing = {2}\n\n'.format(self.selection, self.startPos, self.playing))
                ''' check to if online browser config is dirty '''
                self.stations = self._cnf.stations
                self._align_stations_and_refresh(self.ws.PLAYLIST_MODE,
                        a_startPos=self.startPos,
                        a_selection=self.selection,
                        force_scan_playlist=from_rename_action)
                if self.playing < 0:
                    self._put_selection_in_the_middle(force=True)
                    self.refreshBody()
                if not self._cnf.browsing_station_service and \
                        self._cnf.online_browser:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Closing online browser!')
                    self._cnf.online_browser = None
                    self._cnf.stations_history = self._cnf.normal_stations_history
                    self._cnf.browsing_station_service = False
                ''' check if browsing_station_service has changed '''
                if not self._cnf.browsing_station_service and \
                        removed_playlist_history_item[-1]:
                    result = True
                else:
                    result = False
                # if self._cnf.open_last_playlist and \
                #         not self._cnf.browsing_station_service:
                #     self._cnf.save_last_playlist()
            if result:
                self._normal_mode_resize()
        return result

    def _get_station_id(self, find):
        for i, a_station in enumerate(self.stations):
            if a_station[0] == find:
                return i
        return -1

    def _get_stations_ids(self, find):
        ch = -2
        i_find = [-1, -1]
        debug_str = ('selection', 'playing')
        for j, a_find in enumerate(find):
            if a_find.strip():
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        logger.debug('** Looking for {0} station: "{1}"'.format(debug_str[j], a_find))
                    except:
                        logger.debug('** Looking for {0} station: "{1}"'.format(debug_str[j], a_find.encode('utf-8', 'replace')))

                for i, a_station in enumerate(self.stations):
                    if i_find[j] == -1:
                        if j == 1 and find[0] == find[1]:
                            ''' No need to scan again for the same station '''
                            i_find[1] = i_find[0]
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('** Got it at {}'.format(i_find[0]))
                            break
                        ''' python 2 fix
                            a_find may be unicode under python 2, so convert to str
                        '''
                        if isinstance(a_find, str):
                            a_find_str = a_find
                        else:
                            a_find_str = a_find.encode('utf-8', 'ignore')
                        if a_station[0] == a_find_str:
                            i_find[j] = i
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('** Found at {}'.format(i))
                            ch += 1
                            if ch == 0:
                                break
        return i_find

    def _set_active_stations(self):
        if self.stations:
            if self.player.isPlaying():
                self.active_stations = [
                        [self.stations[self.selection][0], self.selection],
                        [self.stations[self.playing][0], self.playing]
                        ]
            else:
                if self.number_of_items > 0:
                    self.active_stations = [
                            [self.stations[self.selection][0], self.selection],
                            ['', -1]]
                else:
                    self.active_stations = [
                            ['', self.selection],
                            ['', -1]]
        logger.error('DE active_stations = \n\n{}\n\n'.format(self.active_stations))

    def _set_rename_stations(self):
        if self.stations:
            if self.player.isPlaying():
                self.rename_stations = [
                        [self.stations[self.selection][0], self.selection],
                        [self.stations[self.playing][0], self.playing]
                        ]
            else:
                if self.number_of_items > 0:
                    self.rename_stations = [
                            [self.stations[self.selection][0], self.selection],
                            ['', -1]]
                else:
                    self.rename_stations = [
                            ['', self.selection],
                            ['', -1]]

    def get_active_encoding(self, an_encoding):
        if an_encoding:
            return an_encoding
        else:
            return self._cnf.default_encoding

    def play_random(self):
        # Pick a random radio station
        if self.number_of_items > 0:
            while True:
                rnd = random.randint(0, len(self.stations) - 1)
                if self.stations[rnd][1] != '-':
                    break
            self.setStation(rnd)
            self.playSelection()
            self._put_selection_in_the_middle(force=True)
            self.refreshBody()

    def _toggle_transparency(self, changed_from_config_window=False, force_value=None):
        ''' Toggles theme transparency.

            changed_from_config_window is used to inhibit toggling from within
            Config Window when 'T' is pressed.

            force_value will set transparency if True or False,
            or toggle transparency if None
        '''
        if self.ws.window_mode == self.ws.CONFIG_MODE and not changed_from_config_window:
            return
        if not self._cnf.use_themes:
            # TODO show msg
            self._show_colors_cannot_change()
            return
        logger.error('\n==========================\nself._cnf.use_transparency = {}'.format(self._cnf.use_transparency))
        logger.error('force_value = {}'.format(force_value))
        self._cnf.use_transparency = not self._cnf.use_transparency
        self._theme.restoreActiveTheme()
        logger.error('self._cnf.use_transparency = {}'.format(self._cnf.use_transparency))
        if self.ws.operation_mode == self.ws.THEME_MODE:
            self._theme_selector.transparent = self._cnf.use_transparency
            logger.error('self._theme_selector.transparent = {}\n=========================='.format(self._theme_selector.transparent))
        self.headWin.refresh()
        self.outerBodyWin.refresh()
        self.bodyWin.refresh()
        self.footerWin.refresh()
        if self._config_win:
            self._config_win._config_options['use_transparency'][1] = self._cnf.use_transparency
            if not changed_from_config_window:
                self._config_win._saved_config_options['use_transparency'][1] = self._cnf.use_transparency
                self._config_win._old_use_transparency = self._cnf.use_transparency

    def _toggle_claculated_colors(self):
        self._cnf.use_calculated_colors = not self._cnf.use_calculated_colors
        self._update_calculated_colors()

    def _update_calculated_colors(self):
        self._theme._do_init_pairs()
        self._theme._update_colors()
        try:
            self.headWin.refresh()
            self.outerBodyWin.refresh()
            self.bodyWin.refresh()
            self.footerWin.refresh()
        except AttributeError:
            pass

    def _save_parameters(self):
        if self._player_select_win is not None:
            self._cnf.params = deepcopy(self._player_select_win._extra.params)
            self._player_select_win = None

    def _reset_parameters(self):
        if self._player_select_win is not None:
            self._player_select_win.reset()
        self._cnf.dirty_config = False
        self._cnf.params_changed = False

    def _show_config_window(self):
        if self._config_win is None:
            self._config_win = PyRadioConfigWindow(
                self.outerBodyWin,
                self._cnf,
                self._toggle_transparency,
                self._show_theme_selector_from_config,
                self._save_parameters,
                self._reset_parameters,
                self._show_port_number_invalid,
                global_functions=self._global_functions
            )
        else:
            self._config_win.parent = self.outerBodyWin
            self._config_win.refresh_config_win()

    def _show_station_info_from_thread(self):
        if self.ws.operation_mode in (
                self.ws.STATION_INFO_MODE,
                self.ws.STATION_INFO_ERROR_MODE):
            if self.ws.operation_mode == self.ws.STATION_INFO_ERROR_MODE:
                self.ws.close_window()
            self._show_station_info()

    def _browser_station_info(self):
        max_width = self.bodyMaxX - 24
        if max_width < 56:
            max_width = 56
        txt, tail = self._cnf._online_browser.get_info_string(
            self.selection,
            max_width=max_width)
        self._station_rename_from_info = False
        self._show_help(txt,
                        mode_to_set=self.ws.STATION_DATABASE_INFO_MODE,
                        caption=' Station Database Info ', is_message=True)

    def _show_station_info(self):
        max_width = self.bodyMaxX - 24
        if max_width < 56:
            max_width = 56
        txt, tail = self.player.get_info_string(
            self._last_played_station,
            max_width=max_width)

        if tail and not self._cnf.browsing_station_service:
            self._station_rename_from_info = True
            self._show_help(
                txt + tail,
                mode_to_set=self.ws.STATION_INFO_MODE,
                caption=' Station Info ', is_message=True,
                prompt=' Press any other key to hide ',
                too_small_msg='Window too small to display info')
        else:
            self._station_rename_from_info = False
            self._show_help(txt,
                            mode_to_set=self.ws.STATION_INFO_MODE,
                            caption=' Station Info ', is_message=True)

    def detectUpdateStationsThread(self, check_function, a_lock, stop):
        ''' a thread to check if stations.csv is updated '''

        def delay(secs, stop):
            for i in range(0, 5 * secs):
                sleep(.2)
                if stop():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('detectUpdateStationsThread: Asked to stop. Stoping...')
                    return False
            return True

        if not delay(10, stop):
            return
        if stop():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('detectUpdateStationsThread: Asked to stop. Stoping...')
            return
        ret = check_function(stop)
        if stop():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('detectUpdateStationsThread: Asked to stop. Stoping...')
            return
        x = stop()
        if ret:
            with a_lock:
                if x:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('detectUpdateStationsThread: Asked to stop. Stoping...')
                    return
                else:
                    self._need_to_update_stations_csv = 2
        else:
            if logger.isEnabledFor(logging.DEBUG):
                if x:
                    logger.debug('detectUpdateStationsThread: Asked to stop. Stoping...')
                else:
                    logger.debug('detectUpdateStationsThread: stations.csv is up to date!!!')

    def detectUpdateThread(self, config, a_lock, stop):
        ''' a thread to check if an update is available '''

        def delay(secs, stop):
            for i in range(0, 5 * secs):
                sleep(.2)
                if stop():
                    return

        def clean_date_files(files, start=0):
            files_to_delete = files[start+1:]
            for a_file in files_to_delete:
                try:
                    remove(a_file)
                except:
                    pass

        def create_tadays_date_file(a_path):
            d1 = datetime.now()
            now_str = d1.strftime('%Y-%m-%d')
            try:
                with open(path.join(a_path, '.' + now_str + '.date'), 'w', encoding='utf-8') as f:
                    pass
            except:
                pass

        def to_time(secs):
            if secs < 60:
                return secs
            hour = int(secs/60)
            min = secs % 60
            return str(hour) + ':' + str(min)

        if logger.isEnabledFor(logging.INFO):
            logger.info('detectUpdateThread: Starting...')
        a_path = config.stations_dir
        if config.current_pyradio_version:
            this_version = config.current_pyradio_version
        else:
            this_version = config.get_pyradio_version()
        check_days = 10
        connection_fail_count = 0
        ran = 5
        if logger.isEnabledFor(logging.INFO):
            logger.info('detectUpdateThread: Will check in {} seconds'.format(ran))
        delay(ran, stop)
        if stop():
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('detectUpdateThread: Asked to stop. Stoping...')
            return
        files = glob.glob(path.join(a_path, 'data', '.*.date'))
        if files:
            files.sort(reverse=True)
            if len(files) > 1:
                clean_date_files(files)
            a_date = path.split(path.splitext(files[0])[0])[1][1:]

            d1 = datetime.now()
            d2 = datetime.strptime(a_date, '%Y-%m-%d')
            delta = (d1 - d2).days

            if self._force_update:
                ''' enable update check '''
                delta = check_days
            if delta < check_days:
                clean_date_files(files)
                if logger.isEnabledFor(logging.INFO):
                    if check_days - delta == 1:
                        logger.info('detectUpdateThread: PyRadio is up to date. Will check again tomorrow...')
                    else:
                        logger.info('detectUpdateThread: PyRadio is up to date. Will check again in {} days...'.format(check_days - delta))
                return

        if logger.isEnabledFor(logging.INFO):
            logger.info('detectUpdateThread: Checking for updates')
        while True:
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('detectUpdateThread: Asked to stop. Stoping...')
                break
            last_tag = get_github_tag(do_not_exit=True)
            if stop():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('detectUpdateThread: Asked to stop. Stoping...')
                break

            # logger.error('DE last_tag = "{}"'.format(last_tag))
            if self._force_update:
                last_tag = self._force_update
            # logger.error('DE last_tag = "{}"'.format(last_tag))

            if last_tag:
                connection_fail_count = 0
                if logger.isEnabledFor(logging.INFO):
                    logger.info('detectUpdateThread: Upstream version found: {}'.format(last_tag))
                if this_version == last_tag:
                    clean_date_files(files, -1)
                    create_tadays_date_file(path.join(a_path, 'data'))
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('detectUpdateThread: No update found. Will check again in {} days. Terminating...'.format(check_days))
                    break
                else:
                    existing_version = version_string_to_list(this_version)
                    new_version = version_string_to_list(last_tag)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('current version = {0}, upstream version = {1}'.format(existing_version, new_version))
                    if existing_version < new_version:
                        if stop():
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('detectUpdateThread: Asked to stop. Stoping...')
                            break
                        ''' remove all existing date files '''
                        clean_date_files(files, -1)
                        if stop():
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('detectUpdateThread: Asked to stop. Stoping...')
                            break
                        ''' set new version '''
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('detectUpdateThread: Update available: {}'.format(last_tag))
                        a_lock.acquire()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('detectUpdateThread: Update notification sent!!!')
                        self._update_version = last_tag
                        a_lock.release()
                        while True:
                            ''' Wait until self._update_version becomes ''
                                which means that notification window has been
                                displayed. Then create date file and exit.
                                If asked to terminate, do not write date file
                            '''
                            delay(5, stop)
                            if stop():
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug('detectUpdateThread: Asked to stop. Stoping but not writing date file...')
                                return
                            a_lock.acquire()
                            if self._update_version == '':
                                a_lock.release()
                                ''' create today's date file '''
                                create_tadays_date_file(path.join(a_path, 'data'))
                                if logger.isEnabledFor(logging.INFO):
                                    logger.info('detectUpdateThread: Terminating after notification issued... I will check again in {} days'.format(check_days))
                                return
                            a_lock.release()
                    else:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('detectUpdateThread: Ahead of upstream? (current version: {0}, upstream version: {1})'.format(this_version, last_tag))
                        break

            else:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('detectUpdateThread: Error: Cannot get upstream version!!!')
                connection_fail_count += 1
                if connection_fail_count > 4:
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error('detectUpdateThread: Error: Too many connection failures. Terminating...')
                    break
                delay(60, stop)

    def is_search_mode(self, a_mode):
        for it in self._search_modes.items():
            if it[1] == a_mode:
                return True
        return False

    def _apply_search_result(self, ret, reapply=False):
        def _apply_main_windows(ret):
            self.setStation(ret)
            self._put_selection_in_the_middle(force=True)
        if reapply:
            if self.ws.operation_mode in \
                    [self._mode_to_search[x] for x in self._mode_to_search.keys()]:
                _apply_main_windows(ret)
            elif self.ws.operation_mode == self.ws.THEME_MODE:
                self._theme_selector.set_theme(self._theme_selector._themes[ret])
            elif self.ws.operation_mode in (self.ws.SELECT_PLAYLIST_MODE,
                                            self.ws.PASTE_MODE):
                self._playlist_select_win.setPlaylistById(ret, adjust=True)
            elif self.ws.operation_mode == self.ws.SELECT_STATION_MODE:
                self._station_select_win.setPlaylistById(ret, adjust=True)
            elif self.ws.operation_mode in (self.ws.GROUP_SELECTION_MODE, self.ws.GROUP_SEARCH_MODE):
                self._group_selection_window.selection = ret
            self.refreshBody()

        else:
            if self.ws.operation_mode in self.search_main_window_modes:
                _apply_main_windows(ret)
            elif self.ws.previous_operation_mode == self.ws.THEME_MODE:
                self._theme_selector.set_theme(self._theme_selector._themes[ret])
            elif self.ws.previous_operation_mode in (self.ws.SELECT_PLAYLIST_MODE,
                                                     self.ws.PASTE_MODE):
                self._playlist_select_win.setPlaylistById(ret, adjust=True)
            elif self.ws.previous_operation_mode == self.ws.SELECT_STATION_MODE:
                self._station_select_win.setPlaylistById(ret, adjust=True)
            elif self.ws.operation_mode in (self.ws.GROUP_SELECTION_MODE, self.ws.GROUP_SEARCH_MODE):
                self._group_selection_window.selection = ret
            self.ws.close_window()
            self.refreshBody()

    def _show_rename_dialog(self):
        self._rename_playlist_dialog.set_parent(self.outerBodyWin)

    def _show_station_editor(self):
        self._station_editor.set_parent(self.outerBodyWin)

    def _move_station(self, direction):
        if self.jumpnr:
            try:
                target = self.number_of_items - 1 if self.number_of_items < int(self.jumpnr) else int(self.jumpnr) - 1
            except:
                return False
            self.jumpnr = ''
            self._cnf.jump_tag = -1
            source = self.selection
        elif self._cnf.jump_tag >= 0:
            source = self.selection
            target = self._cnf.jump_tag
            self._cnf.jump_tag = -1
        else:
            source = self.selection
            target = self.selection + direction
        ret = self._cnf.move_station(source, target)
        if ret:
            ''' refresh reference '''
            self.stations = self._cnf.stations
            self._cnf.dirty_playlist = True
            if self.playing == source:
                self.playing = target
            elif self.playing == target:
                self.playing = source - 1
            self.selection = target
            self.setStation(self.selection)
            self.refreshBody()
        return ret

    def _do_display_notify(self):
        self._update_notify_lock.acquire()
        if self._update_version:
            self._update_version_do_display = self._update_version
            self._print_update_notification()
        self._update_notify_lock.release()

    def _check_to_open_playlist(self, a_url=None):
        ''' Open a playlist after saving current playlist (if needed)

            Parameters
                a_url:  An online service url
        '''
        if self._cnf.dirty_playlist:
            if self._cnf.auto_save_playlist:
                ''' save playlist and open playlist '''
                ret = self.saveCurrentPlaylist()
                if ret == 0:
                    self._open_playlist(a_url)
                else:
                    if self._cnf.browsing_station_service:
                        self._cnf.removed_playlist_history_item()
            else:
                ''' ask to save playlist '''
                self._print_save_modified_playlist(self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE)
        else:
            self._open_playlist(a_url)

    def _normal_mode_resize(self):
        if platform.startswith('win'):
            curses.resize_term(0, 0)
            try:
                curses.curs_set(0)
            except:
                pass

        maxY, maxX = self.stdscr.getmaxyx()
        if maxX < 41:
            while self.ws.operation_mode not in (
                self.ws.NORMAL_MODE,
                self.ws.PLAYLIST_MODE
            ):
                self.ws.close_window()
            ''' close all windows '''
            self.helpWinContainer = None
            self.helpWin = None
            self._config_win = None
            self._browser_config_win = None
            self._player_select_win = None
            self._playlist_select_win = None
            self._station_editor = None
            self._station_select_win = None
            self._theme_selector = None
            self._color_config_win = None
            self._connection_type_edit = None
            self._encoding_select_win = None
            self._encoding_select_win =None
        if maxX < 20:
            self._limited_width_mode = True
            self._limited_height_mode = True
            self._print_limited_info()
            return
        self._limited_width_mode = False
        if self.player.isPlaying():
            self.log.display_help_message = False
        self.setupAndDrawScreen()
        if self.selection >= self.number_of_items - self.bodyMaxY and \
                self.number_of_items > self.bodyMaxY:
            self.startPos = self.number_of_items - self.bodyMaxY
            self.refreshBody()

    def _reset_status_bar_right(self, random_request=False):
        self.jumpnr = ''
        self._cnf.jump_tag = -1
        self._update_status_bar_right(random_requested=random_request,
                                      status_suffix='')
        self._random_requested = random_request

    def _update_status_bar_right(self,
                                 status_suffix=None,
                                 backslash=False,
                                 reg_y_pressed=False,
                                 reg_open_pressed=False,
                                 random_requested=False):
        self._random_requested = random_requested
        if status_suffix is not None:
            self._status_suffix = status_suffix
        self._backslash_pressed = backslash
        self._register_assign_pressed = reg_y_pressed
        self._register_open_pressed = reg_open_pressed
        self.log.write(suffix=self._status_suffix)

    def _cannot_delete_function(self):
        self._show_notification_with_delay(
            txt='___Cannot delete item!___',
            mode_to_set=self.ws.operation_mode,
            callback_function=self.refreshBody
        )

    def _show_colors_cannot_change(self):
        self._show_notification_with_delay(
                txt='______Curses cannot change__\n____the colors of this window.__\n__Default colors are being used!___',
                delay=1.5,
                mode_to_set=self.ws.operation_mode,
                callback_function=self.refreshBody)

    def _clear_register_file(self):
        '''Clear the contents of a register
           and delete the register file.
        '''

        if self.ws.operation_mode == self.ws.NORMAL_MODE:
            self._set_active_stations()
            self.stations = []
            self.number_of_items = 0
            self.selection = 0
            self.startPos = 0
            self.playing = -1
            self.selections[self.ws.REGISTER_MODE] = [
                    self.selection,
                    self.startPos,
                    self.playing,
                    self.stations
                    ]
            self._set_active_stations()
            self._cnf.dirty_playlist = True
            self.saveCurrentPlaylist()
            file_to_remove = self._cnf.station_path
        else:
            file_to_remove = path.join(
                self._cnf.registers_dir,
                self.stations[self.selection][0] + '.csv')
        try:
            remove(file_to_remove)
        except:
            if self.ws.operation_mode == self.ws.PLAYLIST_MODE:
                self._show_notification_with_delay(
                        txt='___Failed to clear register...___',
                        mode_to_set=self.ws.NORMAL_MODE,
                        callback_function=self.refreshBody)
                return
        if self.ws.operation_mode == self.ws.PLAYLIST_MODE:
            self._reload_playlists()
            if self.number_of_items == 0:
                self.ws.close_window()
                self._open_playlist_from_history(list_of_registers=True)
            if self.selection >= self.number_of_items:
                self.selection = self.number_of_items - 1
                if self.selection < 0:
                    self.selection = 0
                self._put_selection_in_the_middle()

    def _clear_all_register_files(self):
        self._set_active_stations()
        if self._cnf.is_register:
            self._clear_register_file()
        files = glob.glob(path.join(self._cnf.registers_dir, '*.csv'))
        if files:
            for a_file in files:
                try:
                    remove(a_file)
                except:
                    pass
        if self.ws.operation_mode == self.ws.PLAYLIST_MODE:
            self.ws.close_window()
            self._open_playlist_from_history(list_of_registers=True)

    def _show_notification_with_delay(self,
                                      txt,
                                      mode_to_set,
                                      callback_function,
                                      delay=.75,
                                      reset_metrics=True):
        self._show_msg(txt, mode_to_set, caption='',
                        prompt='', is_message=True,
                        reset_metrics=reset_metrics)
        th = threading.Timer(delay, callback_function)
        th.start()
        th.join()

    def _paste(self, playlist=''):
        if self._unnamed_register:
            ''' ok, I have something to paste '''

            if playlist == '':
                ''' paste to current playlist / register '''
                self._cnf.dirty_playlist = True
                if self.number_of_items == 0:
                    self._cnf.stations = [self._unnamed_register]
                    self.number_of_items = self._cnf.number_of_stations = 1
                    self.selection = -1
                    self.startPos = 0
                else:
                    ret, self.number_of_items = self._cnf.insert_station(self._unnamed_register, self.selection + 1)
                self.stations = self._cnf.stations
                self.selection += 1
                if self.selection >= self.startPos + self.bodyMaxY:
                    self.startPos += 1
                ''' auto save register files '''
                if self._cnf.is_register:
                    self.saveCurrentPlaylist()
                self.refreshBody()
            else:
                ''' paste to playlist / register file '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('pasting to "{}"'.format(playlist))
                ret = self._cnf.paste_station_to_named_playlist(
                    self._unnamed_register,
                    playlist
                )
                if ret == 0:
                    self._show_station_pasted()
                else:
                    self._show_paste_failed()
        else:
            self._show_nothing_to_paste()

    def _fix_playlist_highlight_after_rename(self, old_file, new_file, copy_file, open_file):
        search = (old_file if copy_file else new_file, new_file)
        found_id = [-1, -1]
        selection = playing = found = -1
        for i, n in enumerate(self._cnf.playlists):
            for k in range(0, 2):
                if search[k] == n[3]:
                    found_id[k] = i
                    found += 1
                if k == 0 and search[0] == search[1]:
                    found_id[1] = found_id[0]
                    found += 1
                if found > 1:
                    break
        if open_file:
            selection = playing = found_id[1]
        else:
            if copy_file:
                selection = found_id[1]
            else:
                selection = playing = found_id[1]
        if selection == self.selections[self.ws.PLAYLIST_MODE][0]:
            ret = False
        else:
            ret = True
        self.selections[self.ws.PLAYLIST_MODE][0] = selection
        self.selections[self.ws.PLAYLIST_MODE][2] = playing
        return ret

    def _page_up(self):
        self._reset_status_bar_right()
        if self.number_of_items > 0:
            sel = self.selection - self.pageChange
            if sel < 0 and self.selection > 0:
                sel = 0
            self.setStation(sel)
            self._handle_cursor_move_up()

    def _page_down(self):
        self._reset_status_bar_right()
        if self.number_of_items > 0:
            sel = self.selection + self.pageChange
            if self.selection == len(self.stations) - 1:
                sel = 0
            elif sel >= len(self.stations):
                sel = len(self.stations) - 1
            self.setStation(sel)
            self._handle_cursor_move_down()

    def _handle_mouse(self, main_window=True):
        my, mx, a_button = self._get_mouse()
        if a_button == -1:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Mouse event: assuming scroll down')
            self._page_down()
            return

        stop_here = self._handle_middle_mouse(a_button)
        if not stop_here:
            stop_here = self._handle_all_windows_mouse_event(my, mx, a_button)
            # logger.error('DE stop_here = {}'.format(stop_here))
            if not stop_here:
                if main_window:
                    _, update = self._handle_main_window_mouse_event(my, mx, a_button)

                    if update:
                        self.refreshBody()

    def _get_mouse(self):
        ''' Gets a mouse event
            Returns mouse Y, mouse X, button info
            If an error occurs, returns 0, 0, -1
        '''
        try:
            _, mx, my, _, a_button = curses.getmouse()
        except curses.error:
            return 0, 0, -1

        ''' This code is from ranger
            x-values above ~220 suddenly became negative, apparently
            it's sufficient to add 0xFF to fix that error.
        '''
        if my < 0:
            my += 0xFF

        if mx < 0:
            mx += 0xFF

        return my, mx, a_button

    def _handle_all_windows_mouse_event(self, my, mx, a_button):
        ''' Common mouse handler: volume up/down/mute
            Returns True if activated
                    False if not (someone else has to
                                  handle this event)
        '''
        if shift_only(a_button):
            ''' looking for wheel '''
            if a_button ^ curses.BUTTON_SHIFT not in self.buttons.keys():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event: assuming volume down')
                self._volume_down()
                return True
            elif a_button & curses.BUTTON4_PRESSED:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event: volume up')
                self._volume_up()
                return True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Mouse event: not applicable')
            return False
        elif no_modifiers(a_button):
            if a_button & curses.BUTTON2_CLICKED:
                ''' middle mouse: do not handle here '''
                return False
            elif self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
                self._handle_passive_windows()
                return True
            return False
        else:
            return False

    def _handle_middle_mouse(self, a_button):
        if a_button & curses.BUTTON2_CLICKED:
            if no_modifiers(a_button):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event: volume mute')
                self._volume_mute()
                return True
        return False

    def _handle_main_window_mouse_event(self, my, mx, a_button):
        if no_modifiers(a_button):
            if a_button not in self.buttons.keys():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event on main window: page down')
                self._page_down()
                return True, True

            if a_button & curses.BUTTON4_PRESSED:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event on main window: page up')
                self._page_up()
                return True, True

            ''' looging for BUTTON 1 events '''
            do_update = True
            if self.bodyWinStartY <= my <= self.bodyWinEndY:
                if a_button & curses.BUTTON1_DOUBLE_CLICKED \
                        or a_button & curses.BUTTON1_TRIPLE_CLICKED \
                        or a_button & curses.BUTTON1_CLICKED \
                        or a_button & curses.BUTTON1_RELEASED:
                    new_selection = self.startPos + my - self.bodyWinStartY
                    if new_selection >= self.number_of_items:
                        return False, False
                    if new_selection == self.selection:
                        do_update = False
                    else:
                        self.selection = new_selection

                    if a_button & curses.BUTTON1_DOUBLE_CLICKED \
                            or a_button & curses.BUTTON1_TRIPLE_CLICKED:
                        # ok
                        self.detect_if_player_exited = False
                        if logger.isEnabledFor(logging.DEBUG):
                            if a_button & curses.BUTTON1_DOUBLE_CLICKED:
                                logger.debug('Mouse button 1 double click on line {0} with start pos {1}, selection {2} and playing = {3}'.format(my, self.startPos, self.selection, self.playing))
                            else:
                                logger.debug('Mouse button 1 triple click on line {0} with start pos {1}, selection {2} and playing = {3}'.format(my, self.startPos, self.selection, self.playing))
                        if self.player.isPlaying() and self.selection == self.playing:
                            self.stopPlayer(show_message=True)
                        else:
                            self.playSelection()
                        do_update = True
                    elif a_button & curses.BUTTON1_CLICKED \
                            or a_button & curses.BUTTON1_RELEASED:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Mouse button 1 click on line {0} with start pos {1} and selection {2}'.format(my, self.startPos, self.selection))
                    return True, do_update
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Mouse event on main window: button not handled')
                    return False, False
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Mouse event on main window: not on Body window')
                return False, False
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Mouse event on main window: not applicable')
            return False, False

    def _handle_passive_windows(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Mode is in PASSIVE_WINDOWS')
        self.helpWinContainer = None
        self.helpWin = None
        self.ws.close_window()
        self.refreshBody()
        self._main_help_id = 0

    def _normal_station_info(self):
        if self.player.isPlaying():
            self._show_station_info()
        else:
            self._print_station_info_error()

    def _browser_server_selection(self):
        if self._cnf._online_browser:
            self._cnf._online_browser.select_servers()
        else:
            self._browser_config_win.select_servers()

    def _browser_init_config_from_config(self, parent=None, init=False):
        ''' Show browser config window from config
        '''
        if parent is None:
            parent = self.outerBodyWin
        self._cnf._online_browser.show_config(parent, init, self._cannot_delete_function)

    def _redisplay_select_player(self):
        self._change_player.show(self.bodyWin)

    def _redisplay_browser_config(self):
        if self._cnf._online_browser:
            self._cnf._online_browser._config_win.show(parent=self.outerBodyWin)
        else:
            self._browser_config_win.show(parent=self.outerBodyWin)

    def _browser_init_config(self, parent=None, init=False, browser_name=None, distro='None'):
        ''' Show browser config window from online browseer
        '''
        if parent is None:
            parent = self.outerBodyWin
        if self._cnf._online_browser:
            self._cnf._online_browser.show_config(parent, init, self._cannot_delete_function)
        else:
            if self._browser_config_win is None:
                self._show_connect_to_server_message()
                self._browser_config_win = RadioBrowserConfigWindow(
                    parent=parent,
                    stations_dir=self._cnf.stations_dir,
                    init=init,
                    distro=distro,
                    global_functions=self._global_functions,
                    cannot_delete_function=self._cannot_delete_function
                )
                self.ws.close_window()
            # if title:
            #     if self._browser_config_win.BROWSER_NAME == browser_name:
            #         pass
            if self._browser_config_win.urls:
                self._browser_config_win.enable_servers = True
            else:
                self._browser_config_win.enable_servers = False
            self._browser_config_win.show(parent=parent)
            if not self._browser_config_win.enable_servers:
                self._print_servers_unreachable()

    def _browser_init_search(self, parent):
        ''' Start browser search window
        '''
        self._cnf._online_browser.do_search(parent, init=True)

    def _browser_search(self):
        ''' Redisplay browser search window
        '''
        self._cnf._online_browser.do_search()
        # self._cnf._online_browser.redisplay_search()

    def _browser_sort(self):
        self._cnf._online_browser.sort()

    def _goto_history_back_handler(self):
        self._update_status_bar_right(status_suffix='')
        if self.ws.operation_mode == self.ws.NORMAL_MODE:
            if self._cnf.can_go_back_in_time:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('opening previous playlist')
                self._open_playlist_from_history()
            else:
                self._show_no_more_playlist_history()

    def _handle_cursor_move_up(self):
        # logger.error('DE selection = {}, start pos = {}, current selection = {}, b_start = {}, b_end = {}, maxY = {}, maxX = {}'.format(self.selection, self.startPos, self._current_selection, self.bodyWinStartY, self.bodyWinEndY, self.bodyMaxY, self.maxX))
        if self._limited_height_mode or self._limited_width_mode:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('_handle_cursor_move_up(): Not touching window, it\'s small')
            self._force_print_all_lines = False
            return
        if self._force_print_all_lines:
            self._force_print_all_lines = False
        else:
            if self.selection < self._current_selection:
                if self.selection >= self.startPos:
                    self.bodyWin.untouchwin()
                    self._unselect_line(self._current_selection)
                    self._select_line(self.selection)
                    self.bodyWin.refresh()
                    return
        self.refreshBody()

    def _handle_cursor_move_down(self):
        # logger.error('DE selection = {}, start pos = {}, current selection = {}, b_start = {}, b_end = {}, maxY = {}, maxX = {}'.format(self.selection, self.startPos, self._current_selection, self.bodyWinStartY, self.bodyWinEndY, self.bodyMaxY, self.maxX))
        if self._limited_height_mode or self._limited_width_mode:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('_handle_cursor_move_down(): Not touching window, it\'s small')
            self._force_print_all_lines = False
            return
        if self._force_print_all_lines:
            self._force_print_all_lines = False
        else:
            if self.selection > self._current_selection:
                lines = self.maxY - 2 - self.bodyWinStartY - self.selection
                lines = self.bodyMaxY - (self.selection-self.startPos)
                # logger.error('DE lines = {}'.format(lines))
                if lines > 0:
                    self.bodyWin.untouchwin()
                    self._unselect_line(self._current_selection)
                    self._select_line(self.selection)
                    self.bodyWin.refresh()
                    return
        self.refreshBody()

    def _select_line(self, a_line):
        # if a_line - self.startPos < 0:
        #     logger.error('DE *** _unselect_line: a_line:{0} -  start pos:{1} = {2}'.format(a_line, self.startPos, a_line-self.startPos))
        #     return
        if self.stations[a_line][1] == '-':
            col = self._group_color_active if a_line == self.selection else self._group_color_normal
        else:
            col = 9 if a_line == self.playing else 6
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug('selecting line {}, color {}'.format(a_line - self.startPos, col))
        ''' chgat also touches the line '''
        try:
            self.bodyWin.chgat(a_line - self.startPos, 0, -1, curses.color_pair(col))
        except:
            pass
        if self._cnf.browsing_station_service:
            try:
                self._change_browser_ticks(a_line - self.startPos, curses.color_pair(13))
            except:
                pass

    def _unselect_line(self, a_line):
        # if a_line - self.startPos < 0:
        #     if logger.isEnabledFor(logging.ERROR):
        #         logger.error('*** _unselect_line: a_line:{0} -  start pos:{1} = {2}'.format(a_line, self.startPos, a_line-self.startPos))
        #     return
        if self.stations[a_line][1] == '-':
            col = self._group_color_active if a_line == self.selection else self._group_color_normal
        else:
            col = 4 if a_line == self.playing else 5
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug('unselecting line {}, color {}'.format(a_line - self.startPos, col))
        ''' chgat also touches the line '''
        try:
            self.bodyWin.chgat(a_line - self.startPos, 0, -1, curses.color_pair(col))
        except:
            pass
        if self._cnf.browsing_station_service:
            try:
                self._change_browser_ticks(a_line - self.startPos, curses.color_pair(13))
            except:
                pass

    def _move_cursor_one_up(self):
        self._reset_status_bar_right()
        if self.number_of_items > 0:
            self.setStation(self.selection - 1)
            self._handle_cursor_move_up()

    def _move_cursor_one_down(self):
        self._reset_status_bar_right()
        if self.number_of_items > 0:
            self.setStation(self.selection + 1)
            self._handle_cursor_move_down()

    def _html_play_next_station(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        elif self.player.connecting:
            return '<div class="alert alert-success">Please wait for the player to settle...</div>'
        else:
            self._move_cursor_one_down()
            self.playSelection()
            self.refreshBody()
            return '<div class="alert alert-success">Playing <b>{}</b>!</div>'.format(self.stations[self.selection][0])

    def _play_next_station(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            self._show_stations_history_notification(2)
        # elif not self.player.isPlaying():
        #     self._show_stations_history_notification(3)
        elif self.player.connecting:
            self._show_stations_history_notification(1)
        else:
            # if self.playing > -1:
            #     self.selection = self.playing
            self._move_cursor_one_down()
            self.playSelection()
            self.refreshBody()

    def _html_play_previous_station(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        elif self.player.connecting:
            return '<div class="alert alert-success">Please wait for the player to settle...</div>'
        else:
            self._move_cursor_one_up()
            self.playSelection()
            self.refreshBody()
            return '<div class="alert alert-success">Playing <b>{}</b>!</div>'.format(self.stations[self.selection][0])

    def _play_previous_station(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            self._show_stations_history_notification(2)
        # elif not self.player.isPlaying():
        #     self._show_stations_history_notification(3)
        elif self.player.connecting:
            self._show_stations_history_notification(1)
        else:
            # if self.playing > -1:
            #     self.selection = self.playing
            self._move_cursor_one_up()
            self.playSelection()
            self.refreshBody()

    def _show_schedule_player_stop(self):
        # return
        logger.error('_show_schedule_player_stop() !!!')
        logger.error(self._last_played_station)
        if self.player.isPlaying():
            station = None
        else:
            if self.ws.window_mode != self.ws.NORMAL_MODE:
                station = self._last_played_station[0]
            else:
                station = self.stations[self.selection][0]

        if self._simple_schedule is None:
            self._simple_schedule = PyRadioSimpleScheduleWindow(
                parent=self.outerBodyWin,
                playlist=self._cnf.station_title,
                station=station,
                global_functions=self._global_functions
            )
            self.ws.operation_mode = self.ws.SCHEDULE_PLAYER_STOP_MODE
            self._simple_schedule.show()
        else:
            logger.error('with parent')
            self._simple_schedule.show(parent=self.outerBodyWin)

    def _show_schedule_player_stop_help(self):
        pass

    def _update_stations_result(self):
        '''
        Value of self._need_to_update_stations_csv:

        from update stations:
            1 : Update not needed
            0 : All ok
           -1 : Cannot read stations.csv
           -2 : File not saved
        from reply of
            -3 : No pressed, do not notify for this version
            -4 : Other key pressed, notify me at next PyRadio execution
        from write_synced_version(asked=True)
            -5 : Cannot write last_asked file
            -6 : Cannot write last_synced file
        '''
        logger.debug('stations update result = {}'.format(self._need_to_update_stations_csv))
        try:
            logger.debug('stations update counter = {}'.format(self._update_stations_error_count))
        except:
            pass
        prompt=' Press any key... '
        if self._need_to_update_stations_csv == 1:
            caption = ' PyRadio '
            prompt = ''
            txt = '''
                  ___Stations already up to date!___
                  '''
        elif self._need_to_update_stations_csv == 0:
            if self._cls_update_stations is not None:
                self._cls_update_stations_message = '''
                Your "|stations.csv|" file has been successfully updated.
                The following number of stations have been affected:
                ________________stations added:_|{0}|
                ______________stations updated:_|{1}|
                ______________stations deleted:_|{2}|
                '''.format(
                    self._cls_update_stations.counts[0],
                    self._cls_update_stations.counts[1],
                    self._cls_update_stations.counts[2]
                )
            caption = ' Stations Updated! '
            txt = self._cls_update_stations_message
        elif self._need_to_update_stations_csv == -1:
            caption = ' Stations Update Error '
            txt = '''
                There was an error reading your "|stations.csv|" file.
                This should not be happening!

                Please close all open programs and restart |PyRadio| now,
                to try again.
            '''
        elif self._need_to_update_stations_csv == -2:
            caption = ' Stations Update Error '
            txt = '''
                There was an error saving your "|stations.csv"
                file. This should not be happening!

                Please close all open programs and restart
                |PyRadio| now, to try again.
            '''
        elif self._need_to_update_stations_csv == -3:
            caption=' Stations not updated '
            txt = '''
                    You have chosen not to update "|stations.csv|" at this time.

                    You will not be asked to do so until |PyRadio| updates its
                    default stations again.

                    You can always update them manually with the following
                    command:
                    _______________________|pyradio -us|
                     '''
        elif self._need_to_update_stations_csv == -4:
            caption=' Stations not updated '
            txt = '''
                    You have chosen not to update "|stations.csv|" at this time.
                    You can always update it manually with the following command:
                    _______________________|pyradio -us|
                     '''
        elif self._need_to_update_stations_csv == -5 and \
                self._update_stations_error_count < 6:
            caption = ' Error writing file ({}/5) '.format(self._update_stations_error_count)
            txt = '''
                |PyRadio| cannot write the "|asked_sync|" file.
                This means that you will be asked to sync the stations next time
                the program is executed.

                Please close all open programs and documents and press any key to
                try to write it again.
            '''
        elif self._need_to_update_stations_csv == -5 and \
                self._update_stations_error_count >= 6:
            self.ws.close_window()
            self.refreshBody()
            caption = ' Error writing file '
            if self._cls_update_stations is not None:
                self._cls_update_stations_message = '''
                    |PyRadio| did not write the "|asked_sync|" file.
                    Please create the file
                    |{0}|
                    and write in it
                    ______"|{1}|" (no quotes).
                '''.format(
                    self._cls_update_stations._asked_sync_file,
                    self._cls_update_stations.version_to_write
                )
            txt = self._cls_update_stations_message
        elif self._need_to_update_stations_csv == -6 and \
                self._update_stations_error_count < 6:
            caption = ' Error writing file ({}/5) '.format(self._update_stations_error_count)
            txt = '''
                |PyRadio| cannot write the "|last_sync|" file.
                This means that although stations have been synced, |PyRadio|
                will try to sync them again next time, which means that you
                may end up with duplicates.

                Please close all open programs and documents and press any key
                to try to write it again.
            '''
        elif self._need_to_update_stations_csv == -6 and \
                self._update_stations_error_count >= 6:
            self.ws.close_window()
            self.refreshBody()
            caption = ' Error writing file '
            if self._cls_update_stations is not None:
                self._cls_update_stations_message = '''
                    |PyRadio| did not write the "|last_sync|" file.
                    Please create the file
                    |{0}|
                    and write in it
                    ______"|{1}|" (no quotes).
                '''.format(
                    self._cls_update_stations._last_sync_file,
                    self._cls_update_stations.version_to_write
                )
            txt = self._cls_update_stations_message
        else:
            return
        self._show_help(txt,
                        self.ws.UPDATE_STATIONS_CSV_RESULT_MODE,
                        caption=caption,
                        prompt=prompt,
                        is_message=True)

    def _ask_to_update_stations_csv(self):
        txt = '''
                |PyRadio| default stations (file "|stations.csv|") has been
                updated upstream.

                Do you want to update your "|stations.csv|" file with the
                upstream changes?

                Press |y| to update, |n| to decline and not be asked again
                for this version, or any other key to close this window and
                be asked next time you execute |PyRadio|.
                 '''
        self._show_help(txt,
                        self.ws.ASK_TO_UPDATE_STATIONS_CSV_MODE,
                        caption=' Stations update ',
                        prompt='',
                        is_message=True)

    def _ask_to_save_browser_config_to_exit(self):
        if self._cnf.online_browser:
            title = self._cnf.online_browser.BROWSER_NAME
        else:
            title = self._browser_config_win.BROWSER_NAME
        txt = '''
                |{}|'s configuration has been altered
                but not saved. Do you want to save it now?

                Press |y| to save it or |n| to disregard it.
            '''
        self._show_help(txt.format(title),
                        mode_to_set=self.ws.ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT,
                        caption=' Online Browser Config not Saved! ',
                        prompt='',
                        is_message=True)

    def _ask_to_save_browser_config_from_config(self):
        if self._cnf.online_browser:
            title = self._cnf.online_browser.BROWSER_NAME
        else:
            title = self._browser_config_win.BROWSER_NAME
        txt = '''
                |{}|'s configuration has been altered
                but not saved. Do you want to save it now?

                Press |y| to save it or |n| to disregard it.
            '''
        self._show_help(txt.format(title),
                        mode_to_set=self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG,
                        caption=' Online Browser Config not Saved! ',
                        prompt='',
                        is_message=True)

    def _ask_to_save_browser_config_from_browser(self):
        txt = '''
                |{}|'s configuration has been altered
                but not saved. Do you want to save it now?

                Press |y| to save it or |n| to disregard it.
            '''
        self._show_help(txt.format(self._cnf.online_browser.BROWSER_NAME),
                        mode_to_set=self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER,
                        caption=' Online Browser Config not Saved! ',
                        prompt='',
                        is_message=True)

    def _show_win_no_record(self):
        txt = '''
                |VLC| on |Windows| does not support recording.

                If you really need to record a station, please use one
                of the other two supported players, preferably |MPV|.

                To use one of them (|MPV| or |MPlayer|), close this window
                and press |\m| to activate it.

                If none of them is installed, close this window and
                press |F8| to get to the player installation window.
            '''
        self._show_help(txt,
                        mode_to_set=self.ws.WIN_VLC_NO_RECORD_MODE,
                        caption=' Recording not supported! ',
                        prompt='',
                        is_message=True)

    def _show_recording_toggle_window(self):
        if self.player.recording > 0:
            caption = ' Recording Enable '
            txt = ''' _____Next time you play a station,
                      _____it will be |written to a file|!

                      A |[r]| at the right top corner of the window
                      indicates that recording is |enabled|.
                      A |[R]| indicates that a station is actually
                      |being recorded| to a file.

                     Press |x| to not show this message again, or'''
        else:
            if self.player.isPlaying() and \
                    self.player.recording_filename != '':
                caption = ' Recording Disabled '
                txt = '''
                          Recording will actually continue until
                          you stop the playback of the station!
                '''
            else:
                self.refreshBody()
                return
        self._show_help(txt,
                        mode_to_set=self.ws.RECORD_WINDOW_MODE,
                        caption=caption,
                        is_message=True)

    def _return_from_server_selection(self, a_server):
        self._cnf._online_browser._config_win.get_server_value(a_server)
        self._cnf._online_browser._config_win.calculate_dirty()
        #    self._cnf._online_browser.keyboard_handler = None
        self._cnf._online_browser._config_win._server_selection_window = None
        self._cnf._online_browser.keyboard_handler = self._cnf._online_browser._config_win
        self._cnf._online_browser._config_win._widgets[4].show()
        self.ws.close_window()
        self.refreshBody()

    def _can_show_theme_window_in_browser_search(self):
        if self.ws.operation_mode == self.ws.BROWSER_SEARCH_MODE:
            return not self._cnf._online_browser.line_editor_has_focus()
        else:
            return True

    def _html_toggle_titles_logging(self):
        self.toggle_titles_logging()
        self.log.write_start_log_station_and_title()
        if self._cnf.titles_log.titles_handler:
            return '<div class="alert alert-success">Title Log <b>Enabled</b></div>'
        else:
            return '<div class="alert alert-success">Title Log <b>Disabled</b></div>'

    def _toggle_titles_logging(self):
        self.toggle_titles_logging()
        self.log.write_start_log_station_and_title()
        if self._cnf.titles_log.titles_handler:
            self._show_delayed_notification('___Title Log Enabled___')
        else:
            self._show_delayed_notification('___Title Log Disabled___')

    def _html_tag_a_title(self):
        return self._tag_a_title(html=True)

    def _tag_a_title(self, html=False):
        if self.player.isPlaying():
            if self._cnf.can_like_a_station():
                toggled = False
                if self._cnf.titles_log.titles_handler is None:
                    self.toggle_titles_logging()
                    self.log.write_start_log_station_and_title()
                    toggled = True
                ret = self._cnf.titles_log.tag_title(self.log)
                if toggled:
                    self.toggle_titles_logging()
            else:
                ret = 2
            if ret == 0:
                if html:
                    return '<div class="alert alert-success">Title <b>tagged</b> as liked!</div>'
                else:
                    self._show_delayed_notification('___Title tagged as liked___')
            elif ret == 1:
                if html:
                    return '<div class="alert alert-danger"><b>Error</b> liking Title</div>'
                else:
                    self._show_delayed_notification('___Error liking Title___', delay=1.2)
            else:
                if html:
                    return '<div class="alert alert-info">Title <b>already tagged</b> as liked!</div>'
                else:
                    self._show_delayed_notification('___Title already tagged as liked___')
        else:
            if html:
                return '<div class="alert alert-danger">Player is <b>stopped!</b></div>'
            else:
                self._show_delayed_notification('___Error: Player not in playback___', delay=1.2)

    def _show_stations_history_notification(self, msg_id):
        if self._limited_height_mode or self._limited_width_mode:
            msg = (
                'Operation not supported',
                'Please wait for the player to settle...',
                'Operation supported in stations mode only...',
                'Player not playing...'
            )
            if self.player.isPlaying():
                self.log.write(msg=msg[msg_id])
                self.player.threadUpdateTitle()
            else:
                self.log.write(msg=msg[msg_id], help_msg=True, suffix=self._status_suffix)
                self.player.threadUpdateTitle()
        else:
            msg = (
                '___Operation not suported!!!___\n____Connection timeout is 0 ',
                '___Please wait for the player___\n__________to settle',
                '___Operation supported in___\n_____station mode only___',
                '___Player not playing...___'
            )
            self._show_notification_with_delay(
                txt=msg[msg_id],
                mode_to_set=self.ws.NORMAL_MODE,
                callback_function=self.refreshBody
            )

    def _html_stations_history_previous(self):
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        elif self.player.connecting:
            return '<div class="alert alert-danger">Please wait for the player to settle...</div>'
        else:
            if self._cnf.stations_history.item == -1:
                return '<div class="alert alert-danger">History is <b>empty</b>!</div>'
            elif self._cnf.stations_history.item == 0:
                return '<div class="alert alert-danger">Already at <b>first</b> item!</div>'
            self._cnf.play_from_history = True
            self._cnf.stations_history.play_previous()
            return '<div class="alert alert-success">Playing <b>{}</b>!</div>'.format(self.stations[self.selection][0])

    def _stations_history_previous(self):
        self._update_status_bar_right(status_suffix='')
        if int(self._cnf.connection_timeout_int) == 0:
            self._show_stations_history_notification(0)
        elif self.ws.window_mode == self.ws.PLAYLIST_MODE:
            self._show_stations_history_notification(2)
        else:
            if self.player.connecting:
                self._show_stations_history_notification(1)
            else:
                self._cnf.play_from_history = True
                self._cnf.stations_history.play_previous()

    def _html_is_player_stopped(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            return '1'
        return '0'

    def _html_stations_history_next(self):
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        elif self.player.connecting:
            return '<div class="alert alert-danger">Please wait for the player to settle...</div>'
        else:
            if self._cnf.stations_history.item == -1:
                return '<div class="alert alert-danger">History is <b>empty</b>!</div>'
            elif self._cnf.stations_history.item == len(self._cnf.stations_history.items) - 1:
                return '<div class="alert alert-danger">Already at <b>last</b> item!</div>'
            self._cnf.play_from_history = True
            self._cnf.stations_history.play_next()
            return '<div class="alert alert-success">Playing <b>{}</b>!</div>'.format(self.stations[self.selection][0])

    def _stations_history_next(self):
        self._update_status_bar_right(status_suffix='')
        if int(self._cnf.connection_timeout_int) == 0:
            self._show_stations_history_notification(0)
        elif self.ws.window_mode == self.ws.PLAYLIST_MODE:
            self._show_stations_history_notification(2)
        else:
            if self.player.connecting:
                self._show_stations_history_notification(1)
            else:
                self._cnf.play_from_history = True
                self._cnf.stations_history.play_next()

    def _show_remote_control_server_not_active(self):
        if self._cnf.locked:
            self._show_remote_control_error()
        else:
            if self._remote_control_window is None:
                self._remote_control_window = PyRadioServerWindow(
                    config=self._cnf,
                    parent=self.outerBodyWin,
                    port_number_error_message=self._show_port_number_invalid
                )
                self.ws.operation_mode = self.ws.REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE
            self._remote_control_window.show(self.outerBodyWin)

    def _show_remote_control_server_active(self):
        if self._remote_control_server is not None:
            txt = '''
                   |PyRadio Remote Control Server| is active!

                   ||Text Address: |http://{0}
                   ||_Web Address: |http://{0}/html

                   ||Press "|s|" to stop the server, or'''.format(
                self._remote_control_server.ip + \
                '|:|' + str(
                    self._cnf.active_remote_control_server_port
                )
            )
            self._show_help(
                txt,
                self.ws.REMOTE_CONTROL_SERVER_ACTIVE_MODE,
                caption=' Remote Control Enabled ',
                is_message=True
            )

    def _reload_playlist_after_confirmation(self, char=121):
        if char in (ord('y'), ord('Y')):
            if not self._cnf.locked and char == ord('Y'):
                self._cnf.confirm_playlist_reload = False
            self.reloadCurrentPlaylist(self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE)
            self.ws.close_window()
            self.refreshBody()
        else:
            ''' close confirmation message '''
            self.stations = self._cnf.stations
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Canceling Playlist Reload')
            self.ws.close_window()
            self.refreshBody()

    def _remove_station(self, char=121):
        ''' removes a station
            char=121 is ord('y')
        '''
        self._set_active_stations()
        deleted_station, self.number_of_items = self._cnf.remove_station(self.selection)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Deleted station: "{}"'.format(deleted_station[0]))
        self.ws.close_window()
        self._align_stations_and_refresh(self.ws.REMOVE_STATION_MODE)
        if not self._cnf.locked and char == ord('Y'):
            self._cnf.confirm_station_deletion = False
        self._cnf.stations_history.remove_station(deleted_station[0])

        ''' auto save register file '''
        if self._cnf.is_register:
            self.saveCurrentPlaylist()
            if self.number_of_items == 0:
                try:
                    remove(self._cnf.station_path)
                except:
                    pass
        self._unnamed_register = deleted_station
        self.selections[0][3] = self.stations

    def _show_group_selection(self):
        if self._group_selection_window is None:
            self._groups = [(x, y[0]) for x, y in enumerate(self.stations) if y[1] =='-']
            if self._groups == []:
                self._groups = None
                txt='___No Groups found!___'
                self._show_notification_with_delay(
                        txt=txt,
                        mode_to_set=self.ws.NORMAL_MODE,
                        callback_function=self.refreshBody)
                return
            if self.selection < self._groups[0][0]:
                active = -1
                selection = 0
            else:
                active = selection = [i for i, x in enumerate(self._groups) if self.selection>=x[0]][-1]
                logger.error(active)
            logger.error('active = {}'.format(active))
            self.ws.operation_mode = self.ws.GROUP_SELECTION_MODE
            self._group_selection_window = SimpleCursesMenu(
                Y = -1, X = -1,
                items=[x[1] for x in self._groups],
                parent=self.bodyWin,
                title=' Available Groups ',
                display_count=True,
                active=active, selection=selection,
                color=curses.color_pair(10),
                color_title=curses.color_pair(11),
                color_border=curses.color_pair(3),
                color_active=curses.color_pair(11),
                color_cursor_selection=curses.color_pair(6),
                color_cursor_active=curses.color_pair(9),
                window_type=SimpleCursesMenu.CENTERED,
                margin=1,
                global_functions=self._global_functions
            )
        self._group_selection_window.show(parent=self.bodyWin)

    def keypress(self, char):
        if self._system_asked_to_terminate:
            ''' Make sure we exit when signal received '''
            if logger.isEnabledFor(logging.debug):
                logger.debug('keypress: Asked to stop. Stoping...')
            return -1

        if char in (ord('#'), curses.KEY_RESIZE):
            self._i_am_resizing = True
            self._normal_mode_resize()
            if not self._limited_width_mode:
                if not self._limited_height_mode:
                    self._do_display_notify()
            self._i_am_resizing = False
            return

        ''' if small exit '''
        if self._limited_height_mode or self._limited_width_mode:
            if char == ord(' '):
                if self.player.isPlaying() and \
                        self.player.playback_is_on and \
                        self.player.recording and \
                        self.player.recording_filename != '':
                    self._pause_player()
                else:
                    self._stop_player()
                self.refreshBody()

            elif char in self._global_functions.keys():
                self._global_functions[char]()
            return

        if self.ws.operation_mode == self.ws.NO_THEMES_MODE:
            if char == ord('x'):
                self._cnf.show_no_themes_message = False
                self._cnf.dirty_config = True
                self._cnf.save_config()
            self.ws.close_window()
            self.refreshBody()
            return

        if self.ws.operation_mode == self.ws.WIN_UNINSTALL_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.ws.close_window()
                if char in (ord('y'), ):
                    return -1
                else:
                    self._cnf.WIN_UNINSTALL = False
                    self.refreshBody()
            return

        if self.ws.operation_mode == self.ws.WIN_PRINT_EXE_LOCATION_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('q'), curses.KEY_EXIT, 27):
                self.ws.close_window()
                curses.ungetch('q')
                #self.refreshBody()
            return

        if self.ws.operation_mode == self.ws.WIN_MANAGE_PLAYERS_MSG_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.ws.close_window()
                curses.ungetch('q')
                #self.refreshBody()
            return

        if self.ws.operation_mode == self.ws.WIN_REMOVE_OLD_INSTALLATION_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.ws.close_window()
                self.refreshBody()
                from .win_del_old_inst import win_del_old_inst
                win_del_old_inst()
            return

        if self.ws.operation_mode in (
            self.ws.DEPENDENCY_ERROR,
            self.ws.NO_PLAYER_ERROR_MODE,
            self.ws.CONFIG_SAVE_ERROR_MODE
        ):
            ''' if no player or config error, don't serve keyboard '''
            return

        elif (self.jumpnr or self._cnf.jump_tag > -1) and \
                char in (curses.KEY_EXIT, ord('q'), 27) and \
                self.ws.operation_mode == self.ws.NORMAL_MODE:
            ''' Reset jumpnr '''
            self._update_status_bar_right(status_suffix='')
            self._do_display_notify()
            self.jumpnr = ''
            self._cnf.jump_tag = -1
            self._random_requested = False
            return

            ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

                Open Register - char = '

            '''
        elif not self._register_open_pressed and char == ord('\'') and \
                self.ws.operation_mode == self.ws.NORMAL_MODE:
            ''' ' pressed - get into open register mode '''
            if self._cnf.browsing_station_service:
                self._update_status_bar_right(reg_open_pressed=False, status_suffix='')
                self._print_not_applicable()
                return
            self._update_status_bar_right(reg_open_pressed=True, status_suffix='\'')
            self._do_display_notify()
            self.jumpnr = ''
            self._cnf.jump_tag = -1
            self._random_requested = False
            return
        elif (self._register_open_pressed
                and self.ws.operation_mode == self.ws.NORMAL_MODE):
            if char == ord('?'):
                self._show_register_help()
                return
            ''' get station to register - accept a-z, 0-9 and - '''
            if char == ord('\''):
                self._set_active_stations()
                self.saved_active_stations = self.active_stations[:]
                logger.error('self.saved_active_stations = {}'.format(self.saved_active_stations))
                self._status_suffix = "'"
                self._update_status_bar_right(status_suffix="'")
                self._cnf.open_register_list = True
                ''' set selections 0,1,2 to saved values '''
                self.selections[self.ws.REGISTER_MODE][:-1] = self.playlist_selections[self.ws.REGISTER_MODE][:]
            elif char in range(48, 58) or char in range(97, 123):
                self._cnf.register_to_open = chr(char).lower()
                self._update_status_bar_right(status_suffix='')
            else:
                self._update_status_bar_right(status_suffix='')
                return
            self._set_rename_stations()
            self._check_to_open_playlist()
            return
            '''
                End of pen Register - char = y

            '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

            '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

                Extra Commands - char = \
            '''
        elif not self._backslash_pressed and char == ord('\\') and \
                self.ws.operation_mode in (self.ws.NORMAL_MODE,
                    self.ws.PLAYLIST_MODE):
            ''' \ pressed '''
            self._update_status_bar_right(backslash=True, status_suffix='\\')
            self._do_display_notify()
            self.jumpnr = ''
            self._cnf.jump_tag = -1
            self._random_requested = False
            return
        elif self._backslash_pressed and \
                self.ws.operation_mode in (self.ws.NORMAL_MODE,
                self.ws.PLAYLIST_MODE):

            if char == ord('o'):
                self._cnf.open_config_dir()

            if char == ord('m') and \
                    self.ws.operation_mode == self.ws.NORMAL_MODE:
                ''' change player  '''
                self._update_status_bar_right(status_suffix='')
                if len(player.available_players) == 1:
                    self._print_change_player_one_player_error()
                else:
                    self.ws.operation_mode = self.ws.CHANGE_PLAYER_MODE
                    self._change_player = SelectPlayer(
                        active_player=self.player.PLAYER_NAME,
                        parent=self.bodyWin,
                        recording=self.player.recording,
                        vlc_no_recording=self._show_win_no_record
                    )
                    self._change_player.show()

            elif char == ord('s') and \
                    self.ws.operation_mode == self.ws.NORMAL_MODE:
                ''' open remote control '''
                self._update_status_bar_right(status_suffix='')
                if HAS_NETIFACES:
                    if self._remote_control_server_thread:
                        self._show_remote_control_server_active()
                    else:
                        self._show_remote_control_server_not_active()
                else:
                    self._print_netifaces_not_installed_error()

            elif char in (ord('h'), ):
                ''' open html help '''
                self._update_status_bar_right(status_suffix='')
                html = HtmlHelp()
                html.open_file(self._cnf.browsing_station_service)

            elif char == ord('r'):
                ''' rename playlist '''
                self._update_status_bar_right(status_suffix='')
                if self._cnf.browsing_station_service:
                    self._print_not_applicable()
                    return
                if self.ws.operation_mode == self.ws.NORMAL_MODE:
                    self._set_rename_stations()
                if self.ws.operation_mode == self.ws.NORMAL_MODE and \
                        self._cnf.dirty_playlist:
                    self._print_playlist_not_saved_error()
                else:
                    self._rename_playlist_dialog = PyRadioRenameFile(
                        self._cnf.station_path if self.ws.operation_mode == self.ws.NORMAL_MODE else self.stations[self.selection][3],
                        self.outerBodyWin,
                        opened_from_editor=True if self.ws.operation_mode == self.ws.NORMAL_MODE else False,
                        global_functions=self._global_functions,
                    )
                    if self.ws.operation_mode == self.ws.NORMAL_MODE:
                        #self._rename_playlist_dialog.checked_checkbox = (False, False)
                        if self._cnf.is_register:
                            self._rename_playlist_dialog.title = ' Rename Register '
                    elif self._cnf._open_register_list and self.ws.operation_mode == self.ws.PLAYLIST_MODE:
                            self._rename_playlist_dialog.title = ' Rename Register '
                    self._rename_playlist_dialog.show()
                    self.ws.operation_mode = self.ws.RENAME_PLAYLIST_MODE

            elif char == ord('n'):
                ''' create new playlist '''
                self._update_status_bar_right(status_suffix='')
                if self._cnf.browsing_station_service:
                    self._print_not_applicable()
                    return
                if not (self.ws.operation_mode == self.ws.PLAYLIST_MODE and \
                        self._cnf.open_register_list):
                    ''' do not create playlist from registers list '''
                    self._update_status_bar_right(status_suffix='')
                    self._rename_playlist_dialog = PyRadioRenameFile(
                        self._cnf.station_path,
                        self.outerBodyWin,
                        opened_from_editor=False,
                        global_functions=self._global_functions,
                        create=True
                    )
                    self._rename_playlist_dialog.title = ' Create Playlist '
                    self._rename_playlist_dialog.show()
                    self.ws.operation_mode = self.ws.CREATE_PLAYLIST_MODE

            elif char == ord('l'):
                self._update_status_bar_right(status_suffix='')
                self._cnf.open_last_playlist = not self._cnf.open_last_playlist
                self._show_notification_with_delay(
                        txt='___Open last playlist set to {}___'.format(
                            self._cnf.open_last_playlist
                            ),
                        mode_to_set=self.ws.operation_mode,
                        callback_function=self.refreshBody)

            elif char == ord('p'):
                ''' paste '''
                self._update_status_bar_right(status_suffix='')
                if self.ws.operation_mode == self.ws.NORMAL_MODE:
                    ''' paste to another playlist / register '''
                    if self._unnamed_register:
                        self.ws.operation_mode = self.ws.PASTE_MODE
                        self._playlist_select_win = None
                        self._playlist_select_win = PyRadioSelectPlaylist(
                            self.bodyWin,
                            self._cnf.stations_dir,
                            self._cnf.station_title,
                            include_registers=True,
                            global_functions=self._global_functions
                        )
                        self._playlist_select_win.init_window()
                        self._playlist_select_win.refresh_win()
                        self._playlist_select_win.setPlaylist(self._cnf.station_title)
                    else:
                        self._show_nothing_to_paste()
                    #self._print_not_implemented_yet()
                else:
                    self._paste(playlist=self.stations[self.selection][-1])

            elif char == ord('?'):
                self._show_extra_commands_help()
                return

            elif char == ord('u'):
                self._update_status_bar_right(status_suffix='')
                self._show_unnamed_register()
                return

            elif char == ord('\\'):
                ''' \\ pressed - go back in history '''
                if self._cnf.dirty_playlist:
                    if self._cnf.auto_save_playlist:
                        ''' save playlist '''
                        ret = self.saveCurrentPlaylist()
                        if ret == 0:
                            self._goto_history_back_handler()
                    else:
                        ''' ask to save playlist '''
                        self._print_save_modified_playlist(self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE)
                else:
                    self._goto_history_back_handler()

            elif char == ord(']'):
                ''' ] pressed - go to first playlist in history '''
                self._update_status_bar_right(status_suffix='')
                if self.ws.operation_mode == self.ws.NORMAL_MODE:
                    if self._cnf.can_go_back_in_time:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('opening first playlist')
                        self._open_playlist_from_history(reset=True)
                    else:
                        self._show_no_more_playlist_history()

            elif char == ord('c'):
                self._update_status_bar_right(status_suffix='')
                if ((self._cnf.is_register and \
                     self.ws.operation_mode == self.ws.NORMAL_MODE) or \
                        (self.ws.operation_mode == self.ws.PLAYLIST_MODE and \
                         self._cnf.open_register_list)):
                        ''' c pressed - clear register '''
                        if self.number_of_items > 0:
                            self._print_clear_register()
                        else:
                            self._show_notification_with_delay(
                                    txt='___Register is already empty!!!___',
                                    mode_to_set=self.ws.NORMAL_MODE,
                                    callback_function=self.refreshBody)

            elif char == ord('C'):
                self._update_status_bar_right(status_suffix='')
                if (self.ws.operation_mode == self.ws.NORMAL_MODE or \
                        (self.ws.operation_mode == self.ws.PLAYLIST_MODE and \
                        self._cnf.open_register_list)):
                    ''' C pressed - clear all registers '''
                    if glob.glob(path.join(self._cnf.registers_dir, '*.csv')):
                        self._print_clear_all_registers()
                    else:
                        self._update_status_bar_right(status_suffix='')
                        self._show_notification_with_delay(
                                txt='____All registers are empty!!!____',
                                mode_to_set=self.ws.NORMAL_MODE,
                                callback_function=self.refreshBody)

            else:
                ''' ESC or invalid char pressed - leave \ mode '''
                self._update_status_bar_right(status_suffix='')
            return

            '''
                End of Playlist history - char = \

            '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

        elif not self._register_assign_pressed and char == ord('y') and \
                self.ws.operation_mode == self.ws.NORMAL_MODE:
            ''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

                Add to Register - char = y
            '''

            ''' y pressed '''
            if self.number_of_items == 0:
                self._update_status_bar_right(status_suffix='')
                self._show_notification_with_delay(
                        txt='___Nothing to put in register!!!___',
                        mode_to_set=self.ws.NORMAL_MODE,
                        callback_function=self.refreshBody)
            # elif self.stations[self.selection][1] == '-':
            #     self._update_status_bar_right(status_suffix='')
            #     self._show_notification_with_delay(
            #             txt='___Cannot copy a group header!!!___',
            #             mode_to_set=self.ws.NORMAL_MODE,
            #             callback_function=self.refreshBody)
            else:
                self._update_status_bar_right(reg_y_pressed=True, status_suffix='y')
                self._do_display_notify()
            return
        elif (self._register_assign_pressed and \
                self.ws.operation_mode == self.ws.NORMAL_MODE):
            ''' get station to register - accept a-z, 0-9 and - '''
            if char == ord('?'):
                self._show_yank_help()
                return
            self._update_status_bar_right(status_suffix='')
            ch = chr(char).lower()
            if char in (ord('\n'), ord('\r'), curses.KEY_ENTER):
                self._unnamed_register = self.stations[self.selection]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('saving to unnamed register: {}'.format(self._unnamed_register))
                self._show_notification_with_delay(
                        txt='___Station copied to unnamed register!!!___',
                        mode_to_set=self.ws.NORMAL_MODE,
                        callback_function=self.refreshBody)
            elif char in range(48, 58) or char in range(97, 123):
                self._unnamed_register = self.stations[self.selection]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('saving to register: {0} - {1}'.format(ch,self.stations[self.selection]))
                if ch == self._cnf.station_title[-1] and self._cnf.is_register:
                    self._paste()
                else:
                    self._failed_register_file = self._cnf.append_to_register(ch, self.stations[self.selection])
                    if self._failed_register_file:
                        self._print_register_save_error()
                    else:
                        self._show_notification_with_delay(
                                txt='___Station copied to register: {}___'.format(ch),
                                mode_to_set=self.ws.NORMAL_MODE,
                                callback_function=self.refreshBody)
            return
            '''
                End of Add to Register - char = y

            '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''

        elif char == curses.KEY_MOUSE:
            self._reset_status_bar_right()
            self._current_selection = self.selection
            if self.ws.operation_mode in \
                    (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
                self._handle_mouse()
            else:
                self._handle_mouse(main_window=False)
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_UPDATE_STATIONS_CSV_MODE:
            self.ws.close_window()
            self.refreshBody()
            ret = -1
            if char == ord('y'):
                ret = self._need_to_update_stations_csv = self._cls_update_stations.update_stations_csv(print_messages=False)
                if self._need_to_update_stations_csv == -6:
                    self._update_stations_error_count = 0
                    while True:
                        ret = self._need_to_update_stations_csv = self._cls_update_stations.write_synced_version()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('stations update result = {}'.format(self._need_to_update_stations_csv))
                        if self._need_to_update_stations_csv == -6:
                            self._update_stations_error_count += 1
                            if self._update_stations_error_count > 4:
                                self._update_stations_error_count += 1
                                break
                            self._update_stations_result()
                            self.bodyWin.getch()
                        else:
                            break
                if self._cnf.station_title == 'stations':
                    self.reloadCurrentPlaylist(self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE)

            elif char == ord('n'):
                self._update_stations_error_count = 0
                while True:
                    ret = self._need_to_update_stations_csv = self._cls_update_stations.write_synced_version(asked=True)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('stations update result = {}'.format(self._need_to_update_stations_csv))
                    if self._need_to_update_stations_csv == -5:
                        self._update_stations_error_count += 1
                        if self._update_stations_error_count > 4:
                            self._update_stations_error_count += 1
                            break
                        self._update_stations_result()
                        self.bodyWin.getch()
                    else:
                        break
            if ret == -1:
                self._need_to_update_stations_csv = -4        # next time
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('stations update result = {}'.format(self._need_to_update_stations_csv))
            self._update_stations_result()
            return

        elif self.ws.operation_mode == self.ws.CHANGE_PLAYER_MODE:
            ret = self._change_player.keypress(char)
            if ret is None:
                self._change_player = None
                self.ws.close_window()
                self.refreshBody()
            elif ret != '':
                # set player
                self.ws.close_window()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('selected player = {}'.format(ret))
                self._change_player = None
                to_play = self.playing
                to_record = self.player.recording
                if self.player.isPlaying():
                    self.stopPlayer()
                self.player = None
                for i, n in enumerate(player.available_players):
                    if n.PLAYER_NAME == ret:
                        player_index = i
                        break
                self.player = player.available_players[player_index](
                    self._cnf,
                    self.log,
                    self.playbackTimeoutCounter,
                    self.connectionFailed,
                    self._show_station_info_from_thread,
                    self._add_station_to_stations_history,
                    self._recording_lock
                )
                if not (self.player.PLAYER_NAME == 'vlc' and \
                        platform.startswith('win')):
                    self.player.recording = to_record
                self.log.display_help_message = False
                self.log.write(ret + ': Player activated!!!', help_msg=False, suffix='')
                self.player.volume = -1
                if to_play > -1:
                    if to_play != self.selections:
                        self.setStation(to_play)
                    self.playSelection()
                self.refreshBody()
                self._change_player = None

        elif self.ws.operation_mode == self.ws.REMOTE_CONTROL_SERVER_ACTIVE_MODE:
            if char == ord('s'):
                self._stop_remote_control_server()
            self.ws.close_window()
            self.refreshBody()

        elif self.ws.operation_mode == self.ws.REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE:
            ret = self._remote_control_window.keypress(char)
            if ret == 0:
                self.ws.close_window()
                self._cnf.active_remote_control_server_ip = self._remote_control_window._the_ip
                self._cnf.active_remote_control_server_port = self._remote_control_window._the_port
                self._remote_control_window = None
                self._start_remote_control_server()
                if self._remote_control_server_thread:
                    self._show_remote_control_server_active()
                self.refreshBody()
            elif ret == -1:
                self._remote_control_window = None
                self.ws.close_window()
                self.refreshBody()

        elif char == ord('H') and self.ws.operation_mode in \
                (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
            self._reset_status_bar_right()
            if self.number_of_items > 0:
                self.selection = self.startPos
                self.refreshBody()
            self._do_display_notify()
            return

        elif char == ord('M') and self.ws.operation_mode in \
                (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
            self._reset_status_bar_right()
            if self.number_of_items > 0:
                if self.number_of_items < self.bodyMaxY:
                    self.selection = int(self.number_of_items / 2)
                else:
                    self.selection = self.startPos + int((self.bodyMaxY - 1) / 2)
                self.refreshBody()
            self._do_display_notify()
            return

        elif char == ord('L') and self.ws.operation_mode in \
                (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
            self._reset_status_bar_right()
            if self.number_of_items > 0:
                if self.number_of_items < self.bodyMaxY:
                    self.setStation(-1)
                else:
                    self.selection = self.startPos + self.bodyMaxY - 1
                self.refreshBody()
            self._do_display_notify()
            return

        elif char in (ord('t'), ) and \
                self.ws.operation_mode not in (self.ws.EDIT_STATION_MODE,
                    self.ws.ADD_STATION_MODE, self.ws.THEME_MODE,
                    self.ws.RENAME_PLAYLIST_MODE, self.ws.CREATE_PLAYLIST_MODE,) and \
                self.ws.operation_mode not in self.ws.PASSIVE_WINDOWS and \
                not self.is_search_mode(self.ws.operation_mode) and \
                self.ws.window_mode not in (self.ws.CONFIG_MODE, ) and \
                self._can_show_theme_window_in_browser_search():
            self._reset_status_bar_right()
            self._config_win = None
            self.theme_forced_selection = None
            if not self._cnf.use_themes:
                # TODO show msg
                self._show_colors_cannot_change()
                return
            if self._cnf.locked:
                self._show_notification_with_delay(
                        txt='__Sorry, you cannot change themes__\n___when the session is locked...',
                        delay=1.5,
                        mode_to_set=self.ws.operation_mode,
                        callback_function=self.refreshBody)
                return

            if self.ws.operation_mode == self.ws.NORMAL_MODE:
                self.selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing, self.stations]
                # self.ll('t')
            #self.ws.previous_operation_mode = self.ws.operation_mode
            #self.ws.operation_mode = self.ws.window_mode = self.ws.THEME_MODE
            self.ws.operation_mode = self.ws.THEME_MODE
            self._show_theme_selector()
            return

        elif char == ord('P') and self.ws.operation_mode in \
                (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
            self._reset_status_bar_right()
            self._goto_playing_station()
            return

        elif self.ws.operation_mode == self.ws.NOT_IMPLEMENTED_YET_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.ws.close_window()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.SCHEDULE_PLAYER_STOP_MODE:
            ret = self._simple_schedule.keypress(char)
            if ret == -1:
                self._simple_schedule = None
                self.ws.close_window()
                self.refreshBody()

        elif self.ws.operation_mode == self.ws.CONFIG_MODE and \
                char not in self._chars_to_bypass:
            if char in (ord('r'), ord('d')):
                self._player_select_win = None
                self._encoding_select_win = None
                self._playlist_select_win = None
                self._station_select_win = None
                self._browser_config_win = None
            ret, ret_list = self._config_win.keypress(char)
            if ret == self.ws.SELECT_PLAYER_MODE:
                ''' Config > Select Player '''
                self.ws.operation_mode = self.ws.SELECT_PLAYER_MODE
                if self._player_select_win is None:
                    self._player_select_win = PyRadioSelectPlayer(
                        self._cnf,
                        self.outerBodyWin,
                        self._config_win._config_options['player'][1],
                        global_functions=self._global_functions
                    )
                else:
                    self._player_select_win._parent = self.outerBodyWin
                    self._player_select_win._parent_maxY, self._player_select_win._parent_maxX = self.outerBodyWin.getmaxyx()
                    self._player_select_win.init_window()
                    self._player_select_win.refresh_win(do_params=True)
                    # self._player_select_win.setPlayers(self._config_win._config_options['player'][1])
                    # self._player_select_win.refresh_selection()

            elif ret == self.ws.SELECT_ENCODING_MODE:
                ''' Config > Select Default Encoding '''
                self.ws.operation_mode = self.ws.SELECT_ENCODING_MODE
                if self._encoding_select_win is None:
                    self._encoding_select_win = PyRadioSelectEncodings(
                            self.outerBodyMaxY,
                            self.outerBodyMaxX,
                            self._cnf.default_encoding,
                            self._cnf.default_encoding)
                    self._encoding_select_win.set_reduced_global_functions(self._global_functions)
                else:
                    self._encoding_select_win._parent_maxY, self._encoding_select_win._parent_maxX = self.outerBodyWin.getmaxyx()
                self._encoding_select_win.init_window()
                self._encoding_select_win.refresh_win()
                self._encoding_select_win.setEncoding(self._config_win._config_options['default_encoding'][1])

            elif ret == self.ws.SELECT_PLAYLIST_MODE:
                ''' Config > Select Default Playlist '''
                self.ws.operation_mode = self.ws.SELECT_PLAYLIST_MODE
                if self._playlist_select_win is None:
                    self._playlist_select_win = PyRadioSelectPlaylist(
                        self.bodyWin,
                        self._cnf.stations_dir,
                        self._config_win._config_options['default_playlist'][1],
                        global_functions=self._global_functions
                    )
                else:
                    self._playlist_select_win._parent_maxY, self._playlist_select_win._parent_maxX = self.bodyWin.getmaxyx()
                self._playlist_select_win.init_window()
                self._playlist_select_win.refresh_win()
                self._playlist_select_win.setPlaylist(self._config_win._config_options['default_playlist'][1])

            elif ret == self.ws.SELECT_STATION_MODE:
                ''' Config > Select Default Station '''
                self.ws.operation_mode = self.ws.SELECT_STATION_MODE
                if self._station_select_win is None:
                    self._station_select_win = PyRadioSelectStation(
                        self.bodyWin,
                        self._cnf.stations_dir,
                        self._config_win._config_options['default_playlist'][1],
                        self._config_win._config_options['default_station'][1],
                        global_functions=self._global_functions
                    )
                else:
                    self._station_select_win._parent_maxY, self._station_select_win._parent_maxX = self.outerBodyWin.getmaxyx()
                    self._station_select_win.update_playlist_and_station(self._config_win._config_options['default_playlist'][1], self._config_win._config_options['default_station'][1])
                self._station_select_win.init_window()
                self._station_select_win.refresh_win()
                self._station_select_win.setStation(self._config_win._config_options['default_station'][1])

            elif ret >= 0:
                msg = ( 'Error saving config. Press any key to exit...',
                        'Config saved successfully!!!',
                        'Config saved - Restarting playback (parameters changed)')
                if ret not in (2, 3):
                    self.ws.close_window()
                    self.bodyWin.box()
                    self._print_body_header()
                    self.refreshBody()
                if ret == 0:
                    self.detect_if_player_exited = False
                    self._cnf.backup_player_params[0] = self._cnf.params[self._cnf.PLAYER_NAME][:]
                    ret = self._cnf.save_config()
                    if ret == -1:
                        ''' Error saving config '''
                        if self.player.isPlaying():
                            self.stopPlayer()
                            self.refreshBody()
                        self.log.display_help_message = False
                        self.log.write(msg=msg[0], help_msg=False, suffix=self._status_suffix)
                        self._print_config_save_error()
                    elif ret == 0:
                        ''' Config saved successfully '''

                        ''' sync backup parameters '''
                        old_id = self._cnf.backup_player_params[1][0]
                        old_param = self._cnf.backup_player_params[1][old_id]
                        self._cnf.backup_player_params[1][1:] = self._cnf.backup_player_params[0][1:]
                        if old_param in self._cnf.backup_player_params[1]:
                            ''' old param exists, point to it '''
                            self._cnf.backup_player_params[1][0] = self._cnf.backup_player_params[1].index(old_param)
                        else:
                            ''' old param is gone, use the one from config '''
                            self._cnf.backup_player_params[1][0] = self._cnf.backup_player_params[0][0]
                        ''' if effective parameter has changed, mark it '''
                        if self._cnf.backup_player_params[1][self._cnf.backup_player_params[1][0]] != old_param:
                            self._cnf.params_changed = True

                        if self.player.isPlaying():
                            # logger.error('DE params_changed = {}'.format(self._cnf.params_changed))
                            #if self._cnf.opts['default_encoding'][1] != self._old_config_encoding or \
                            #        self._cnf.opts['force_http'][1] != self.player.force_http or \
                            #        self._cnf.params_changed:
                            if self._cnf.opts['default_encoding'][1] != self._old_config_encoding or \
                                    self._cnf.params_changed:
                                self._cnf.params_changed = False
                                self.log.write(msg=msg[2])
                                self.player.threadUpdateTitle()
                                if logger.isEnabledFor(logging.INFO):
                                    logger.info('*** Restarting playback (parameters changed)')
                                sleep(1.5)
                                self.playSelection(restart=True)
                            else:
                                self.log.write(msg=msg[1])
                                self.player.threadUpdateTitle()
                        else:
                            self.log.write(msg=msg[1], help_msg=True, suffix=self._status_suffix)
                        self._old_config_encoding = self._cnf.opts['default_encoding'][1]
                        # Do not update the active force_http
                        # self.player.force_http = self._cnf.opts['force_http'][1]
                        if self._config_win:
                            self._config_win._old_use_transparency = self._cnf.use_transparency
                        if self._cnf.player_changed:
                            self._show_player_changed_in_config()
                            self._cnf.player_changed = False
                        self.player.playback_timeout = int(self._cnf.connection_timeout)
                        if self._config_win.mouse_support_option_changed:
                            self._print_mouse_restart_info()
                        if self._config_win.need_to_update_theme:
                            self._theme.recalculate_theme(False)
                        if self._cnf.active_remote_control_server_ip != self._cnf.remote_control_server_ip or \
                                self._cnf.active_remote_control_server_port != self._cnf.remote_control_server_port:
                            self._restart_remote_control_server()
                    elif ret == 1:
                        ''' config not modified '''
                        self._show_notification_with_delay(
                                txt='___Config not modified!!!___',
                                mode_to_set=self.ws.NORMAL_MODE,
                                callback_function=self.refreshBody)
                elif ret == 3:
                    ''' open RadioBrowser  browser config '''
                    self.ws.operation_mode = self.ws.RADIO_BROWSER_CONFIG_MODE
                    self._browser_init_config(init=True, browser_name='RadioBrowser ', distro=self._cnf.distro)
                    return

                # elif ret ==2:
                #     ''' cancel a dirty config '''

                else:
                    ''' restore transparency, if necessary '''
                    if self._config_win._config_options['use_transparency'][1] != self._config_win._saved_config_options['use_transparency'][1]:
                        self._toggle_transparency(changed_from_config_window=False,
                                force_value=self._config_win._saved_config_options['use_transparency'][1])
                    ''' restore theme, if necessary '''
                    if self._cnf.opts['theme'][1] != self._config_win._config_options['theme'][1]:
                        #self._config_win._apply_a_theme(self._cnf.opts['theme'][1])
                        ret, ret_theme_name = self._theme.readAndApplyTheme(self._cnf.opts['theme'][1])
                        if ret == 0:
                            self._theme_name = self._cnf.theme
                            self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
                            self._update_calculated_colors()
                        else:
                            self._theme_name = ret_theme_name
                            self._cnf.theme_has_error = True if ret == -1 else False
                            self._cnf.theme_not_supported = True
                        self._redraw()
                        # logger.error('4 redraw')
                        curses.doupdate()
                        if self._cnf.theme_download_failed:
                            logger.info('_print_theme_download_error 2')
                            self._print_theme_download_error()
                    ''' make sure config is not saved '''
                    self._config_win._saved_config_options['dirty_config'][1] = False
                    self._cnf.dirty_config = False
                ''' clean up '''
                self._player_select_win = None
                self._encoding_select_win = None
                self._playlist_select_win = None
                self._station_select_win = None
                self._config_win = None
            return

        elif (self.ws.operation_mode == self.ws.SELECT_PLAYER_MODE  and \
              char not in self._chars_to_bypass) or \
              self.ws.operation_mode == self.ws.IN_PLAYER_PARAMS_EDITOR:

            ret = self._player_select_win.keypress(char)
            if ret >= 0:
                if ret == 0:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('new_players = {}'.format(self._player_select_win.player))
                    self._config_win._config_options['player'][1] = self._player_select_win.player
                    self.ws.close_window()
                    self._config_win.refresh_config_win()
                    ''' Do NOT set _player_select_win to None here
                        or parameters will be lost!!!
                        self._player_select_win = None
                    '''
                elif ret == 1:
                    self.ws.close_window()
                    self._config_win.refresh_config_win()
                    ''' Do NOT set _player_select_win to None here
                        or parameters will be lost!!!
                        self._player_select_win = None
                    '''
                elif ret == 2:
                    ''' display line editor help '''
                    self._show_params_ediror_help()
                elif ret == 3:
                    ''' Got into paramater editor '''
                    self.ws.operation_mode = self.ws.IN_PLAYER_PARAMS_EDITOR
                elif ret == 4:
                    ''' Parameter editor exited '''
                    self.ws.close_window()
            else:
                if ret == -2:
                    logger.error('DE number of max lines reached!!!')
                    self._print_max_number_of_profiles_error()
                elif ret == -3:
                    self._print_default_profile_edit_delete_error()
            return

        elif self.ws.operation_mode == self.ws.SELECT_STATION_ENCODING_MODE and \
                 char not in self._chars_to_bypass:
            ''' select station's encoding from main window '''
            restart_player = False
            ret, ret_encoding = self._encoding_select_win.keypress(char)
            if ret >= 0:
                if ret == 0:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('new station encoding = {}'.format(ret_encoding))
                    ''' save encoding and playlist '''
                    if self._old_station_encoding == self._cnf.default_encoding:
                        self._old_station_encoding = ''
                    if ret_encoding == self._cnf.default_encoding:
                        ret_encoding = ''
                    if self._old_station_encoding != ret_encoding:
                        self._cnf.dirty_playlist = True
                        self.stations[self.selection][2] = ret_encoding
                        self.selections[0][3] = self.stations
                        if self.selection == self.playing:
                            self._last_played_station = self.stations[self.selection]
                        if self._cnf.browsing_station_service:
                            self._cnf.dirty_playlist = False
                            self._cnf.online_browser.set_encoding(self.selection, ret_encoding)
                        if self.player.isPlaying():
                            restart_player = True
                    #self._config_win._config_options['default_encoding'][1] = ret_encoding
                self.ws.close_window()
                self.refreshBody()
                self._encoding_select_win = None
                self.player.config_encoding = self._cnf.default_encoding
                if restart_player:
                    self.restartPlayer('*** Restarting playback due to encoding change ***')
            return

        elif self.ws.operation_mode in \
                (self.ws.ADD_STATION_MODE, self.ws.EDIT_STATION_MODE):
            ''' In station editor '''
            # logger.error('DE char = {0} - {1}'.format(char, chr(char)))
            restart_player = False
            ret = self._station_editor.keypress(char)
            if ret == -5:
                self._print_icon_url_format_error()
            elif ret == -4:
                self._print_icon_url_error()
            elif ret == -3:
                self._print_editor_url_error()
            elif ret == -2:
                self._print_editor_name_error()
            elif ret == -1:
                # Cancel
                self.ws.close_window()
                self._station_editor = None
                self.refreshBody()
            elif ret == 1:
                ''' ok '''
                if self.ws.operation_mode == self.ws.EDIT_STATION_MODE:
                    ''' editing a station '''
                    if self.player.isPlaying() and self.selection == self.playing:
                        ''' editing the station that's playing '''
                        old_encoding = self.stations[self.selection]
                        if old_encoding == self._cnf.default_encoding:
                            old_encoding = ''
                        if old_encoding != self._station_editor.new_station[2]:
                            restart_player = True

                    if self.stations[self.selection] != self._station_editor.new_station:
                        self._cnf.stations_history.rename_station(
                            self._cnf.station_title,
                            self.stations[self.selection][0],
                            self._station_editor.new_station[0]
                        )
                        self._cnf.dirty_playlist = True
                    self.stations[self.selection] = self._station_editor.new_station
                    if self.selection == self.playing:
                        self._last_played_station = self._station_editor.new_station
                else:
                    ''' adding a new station '''
                    self._cnf.dirty_playlist = True
                    if self._station_editor.append and self.number_of_items > 0:
                        self.stations.append(self._station_editor.new_station)
                        self.number_of_items = len(self.stations)
                        self._cnf.number_of_stations = self.number_of_items
                        self.selection = self.number_of_items - 1
                        self.startPos = self.number_of_items - self.bodyMaxY
                    else:
                        if self.number_of_items == 0:
                            self._cnf.stations = [self._station_editor.new_station]
                            self.number_of_items = self._cnf.number_of_stations = 1
                            self.selection = -1
                            self.startPos = 0
                        else:
                            ret, self.number_of_items = self._cnf.insert_station(self._station_editor.new_station, self.selection + 1)
                        self.stations = self._cnf.stations
                        self.selection += 1
                        if self.selection >= self.startPos + self.bodyMaxY:
                            self.startPos += 1

                    self.selections[0][3] = self.stations
                    ''' auto save register files '''
                    if self._cnf.is_register:
                        self.saveCurrentPlaylist()

                self.ws.close_window()
                self._station_editor = None
                self.refreshBody()
                if restart_player:
                    self.restartPlayer('*** Restarting playback due to encoding change ***')
            elif ret == 2:
                ''' display line editor help '''
                self._show_line_editor_help()
            elif ret == 3:
                ''' show encoding '''
                if self._station_editor._encoding == '':
                    self._station_editor._encoding = self._cnf.default_encoding
                self.ws.operation_mode = self.ws.EDIT_STATION_ENCODING_MODE
                self._encoding_select_win = PyRadioSelectEncodings(self.outerBodyMaxY,
                        self.outerBodyMaxX, self._station_editor._encoding, self._cnf.default_encoding)
                self._encoding_select_win.set_reduced_global_functions(self._global_functions)
                self._encoding_select_win.init_window()
                self._encoding_select_win.refresh_win()
                self._encoding_select_win.setEncoding(self._station_editor._encoding)
            return

        elif self.ws.operation_mode in (self.ws.RENAME_PLAYLIST_MODE, self.ws.CREATE_PLAYLIST_MODE):
            '''  Rename playlist '''
            ret, self.old_filename, self.new_filename, copy, open_file, pl_create = self._rename_playlist_dialog.keypress(char)
            # logger.error('DE\n\n **** ps.p {}\n\n'.format(self._cnf._ps._p))
            if ret not in (0, 2):
                self._rename_playlist_dialog = None
            if ret == -3:
                ''' playlist delete error '''
                self.ws.close_window()
                self.refreshBody()
                self._print_playlist_rename_error()
            elif ret == -2:
                ''' playlist copy error '''
                self.ws.close_window()
                self.refreshBody()
                self._print_playlist_copy_error()
            elif ret == -1:
                ''' Cancel '''
                self.ws.close_window()
                self.refreshBody()
            elif ret == 1:
                ''' ok rename the playlist '''
                self.ws.close_window()
                last_history = self._cnf.history_item()
                last_history[0] = self.new_filename
                last_history[1] = path.basename(self.new_filename)
                last_history[2] = path.basename(self.new_filename).replace('.csv', '')
                ''' not a register, no online browser '''
                last_history[-2:] = False, False
                logger.error('DE\n\n **** ps.p {}\n\n'.format(self._cnf._ps._p))
                logger.error('DE last_history = {}'.format(last_history))
                # logger.error('DE last_history = {}'.format(last_history))
                if self.ws.window_mode == self.ws.NORMAL_MODE:
                        ''' rename the playlist on editor '''
                        self._rename_playlist_from_normal_mode(
                            copy,
                            open_file,
                            pl_create,
                            last_history
                        )
                else:
                    # self.ll('playlist before')
                    #self._playlist_in_editor = self._cnf.playlists[self.selections[self.ws.PLAYLIST_MODE][2]][-1]
                    self._reload_playlists(refresh=False)
                    if self._cnf.open_register_list:
                        self._rename_playlist_from_register_mode(
                            copy,
                            open_file,
                            last_history
                        )
                    else:
                        ''' fix playlist selection '''
                        self._rename_playlist_from_playlist_mode(
                            copy,
                            open_file,
                            last_history
                        )
                return
            elif ret == 2:
                ''' display line editor help '''
                self._show_line_editor_help()
                return

        elif self.ws.operation_mode == self.ws.EDIT_STATION_ENCODING_MODE and \
                char not in self._chars_to_bypass:
            ''' In station editor; select encoding for station '''
            ret, ret_encoding = self._encoding_select_win.keypress(char)
            if ret >= 0:
                if ret_encoding:
                    self._station_editor._encoding = ret_encoding
                    self._station_editor._old_encoding = ret_encoding
                else:
                    self._station_editor._encoding = self._station_editor._old_encoding
                self.ws.close_window()
                self._station_editor.show()
            return

        elif self.ws.operation_mode == self.ws.BROWSER_SERVER_SELECTION_MODE and \
                char not in self._chars_to_bypass:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            if self._server_selection_window:
                ret = self._server_selection_window.keypress(char)
            else:
                ret = self._cnf._online_browser.keypress(char)
            #logger.error('DE BROWSER_SERVER_SELECTION_MODE ret = {}'.format(ret))
            if ret < 1:
                self.ws.close_window()
                if self._cnf._online_browser:
                    ''' server selection from browser '''
                    if ret == 0:
                        if self._cnf._online_browser.server_window_from_config:
                            self._cnf._online_browser._config_win.get_server_value()
                            self._online_browser._config_win.calculate_dirty()
                        else:
                            self.refreshBody()
                            self._set_active_stations()
                            self._cnf._online_browser.search(go_back_in_history=False)
                    else:
                        self.refreshBody()
                    self._cnf._online_browser._server_selection_window = None
                    self._cnf._online_browser.keyboard_handler = self._cnf._online_browser._config_win
                else:
                    ''' server selection from config '''
                    if ret == 0:
                        self._browser_config_win.get_server_value()
                        self._browser_config_win.calculate_dirty()
                    self._server_selection_window = None
                    self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.RADIO_BROWSER_CONFIG_MODE:
            ''' handle browser config '''
            if self._cnf._online_browser:
                ret = self._cnf._online_browser.keypress(char)
            else:
                ret = self._browser_config_win.keypress(char)
            # logger.error('DE <<< RETURN FROM CONFIG ret = {} >>>'.format(ret))

            if ret == 2:
                self._show_radio_browser_config_help()
            elif ret == 3:
                ''' show config server selection window '''
                self.ws.operation_mode = self.ws.BROWSER_SERVER_SELECTION_MODE
                if self._cnf._online_browser:
                    self._cnf._online_browser.select_servers(
                        with_config=True,
                        return_function=self._return_from_server_selection,
                        init=True,
                        global_functions=self._global_functions
                    )
                else:
                    self._server_selection_window = self._browser_config_win.select_servers(init=True)

            elif ret == 4:
                ''' return from config server selection window '''
                # self.ws.close_window()
                self._server_selection_window = None
                self.refreshBody()

            elif ret == -4:
                ''' Online browser config not modified '''
                self._browser_config_not_modified()

            elif ret == -3:
                ''' Error saving browser config '''
                self._print_browser_config_save_error()

            elif ret == -2:
                ''' Online browser config saved '''
                self._saved_browser_config_and_exit()

            elif ret == -1:
                ''' browser config save canceled '''
                self._exit_browser_config()

        elif self.ws.operation_mode == self.ws.BROWSER_SEARCH_MODE:

            if char in self._global_functions.keys() and \
                    not self._cnf._online_browser.line_editor_has_focus():
                self._global_functions[char]()
                return

            ''' handle browser search key press '''
            ret = self._cnf._online_browser.keypress(char)
            if ret == 0:
                ''' Ok, search term is valid '''
                self._cnf._online_browser.get_history_from_search()
                self.ws.close_window()
                self.refreshBody()
                self._show_performing_search_message()
                self._cnf._online_browser.search(go_back_in_history=False)

            elif ret == -1:
                ''' Cancel '''
                self.ws.close_window()
                self.refreshBody()
            elif ret == 2:
                ''' Display help '''
                self._show_radio_browser_search_help()
            elif ret == 3:
                ''' display help editor help '''
                self._show_line_editor_help()
            elif ret == 4:
                ''' search parameter error '''
                self._show_notification_with_delay(
                        txt='___Error in search parameters!!!___',
                        mode_to_set=self.ws.BROWSER_SEARCH_MODE,
                        callback_function=self.refreshBody)
            elif ret == 5:
                ''' save search history '''
                self._cnf._online_browser.get_history_from_search()
                if self._cnf._online_browser.save_config():
                    self._show_notification_with_delay(
                            txt='___History successfully saved!___',
                            mode_to_set=self.ws.BROWSER_SEARCH_MODE,
                            callback_function=self.refreshBody)
                else:
                    self._show_notification_with_delay(
                            txt='___Error saving History!___',
                            delay=1.25,
                            mode_to_set=self.ws.BROWSER_SEARCH_MODE,
                            callback_function=self.refreshBody)
            return

        elif self.ws.operation_mode == self.ws.BROWSER_SORT_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            ret = self._cnf._online_browser.keypress(char)
            if ret < 1:
                self.ws.close_window()
                if ret == 0:
                    self._set_active_stations()
                    self._cnf.stations = self._cnf._online_browser.stations(2)
                    self.stations = self._cnf.stations
                    self._align_stations_and_refresh(self.ws.operation_mode)
                else:
                    self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.SELECT_ENCODING_MODE and \
                char not in self._chars_to_bypass:
            ''' In Config window; select global encoding '''
            ret, ret_encoding = self._encoding_select_win.keypress(char)
            if ret >= 0:
                if ret == 0:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('new encoding = {}'.format(ret_encoding))
                    self._config_win._config_options['default_encoding'][1] = ret_encoding
                self.ws.close_window()
                self._config_win.refresh_config_win()
            return

        elif self.ws.operation_mode == self.ws.SELECT_PLAYLIST_MODE and \
                char not in self._chars_to_bypass and \
                char not in self._chars_to_bypass_for_search:
            ''' In Config window; select playlist '''
            ret, ret_playlist = self._playlist_select_win.keypress(char)
            if ret >= 0:
                if ret == 0:
                    self._config_win._config_options['default_playlist'][1] = ret_playlist
                    if ret_playlist == self._config_win._saved_config_options['default_playlist'][1]:
                        self._config_win._config_options['default_station'][1] = self._config_win._saved_config_options['default_station'][1]
                    else:
                        self._config_win._config_options['default_station'][1] = 'False'
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('New default_playlist = "{0}", New default station = "{1}"'.format(ret_playlist, self._config_win._config_options['default_station'][1]))
                self.ws.close_window()
                self._config_win.refresh_config_win()
            return

        elif self.ws.operation_mode == self.ws.SELECT_STATION_MODE and \
                char not in self._chars_to_bypass and \
                char not in self._chars_to_bypass_for_search:
            ''' In Config window; select station '''
            ret, ret_station = self._station_select_win.keypress(char)
            if ret >= 0:
                if ret == 0:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('New default station = "{}"'.format(ret_station))
                    self._config_win._config_options['default_station'][1] = ret_station
                self.ws.close_window()
                self._config_win.refresh_config_win()
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_CREATE_NEW_THEME_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            if self.theme_forced_selection:
                self._theme_selector.set_theme(self.theme_forced_selection)
            if char in (ord('y'), ):
                pass
                #ret = self._cnf.copy_playlist_to_config_dir()
                #if ret == 0:
                #    self.ws.close_window()
                #    self.refreshBody()
                #    if logger.isEnabledFor(logging.DEBUG):
                #        logger.debug('MODE: self.ws.ASK_TO_CREATE_NEW_THEME_MODE -> self.ws.THEME_MODE')
                #elif ret == 1:
                #    self._print_foreign_playlist_message()
                #else:
                #    ''' error '''
                #    self._print_foreign_playlist_copy_error()
            elif not char in (ord('#'), curses.KEY_RESIZE):
                self.ws.close_window()
                self.refreshBody()
                ''' Do this here to properly resize '''
            return

        elif self.ws.operation_mode == self.ws.PASTE_MODE and \
                char not in self._chars_to_bypass and \
                char not in self._chars_to_bypass_for_search:
            ''' Return from station selection window for pasting '''
            if char == ord('?'):
                self._show_config_playlist_help()
            else:
                ret, a_playlist = self._playlist_select_win.keypress(char)
                if ret == 1:
                    self._playlist_select_win = None
                    self.ws.close_window()
                    self.refreshBody()
                elif ret == 0:
                    self._playlist_select_win = None
                    self.ws.close_window()
                    ret = self._cnf.paste_station_to_named_playlist(
                        self._unnamed_register,
                        a_playlist
                    )
                    self.refreshBody()
                    if ret == 0:
                        self._show_station_pasted()
                    else:
                        self._show_paste_failed()
                    self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.THEME_MODE and (
                char not in self._chars_to_bypass and \
                char not in self._chars_to_bypass_for_search and \
                char not in (ord('T'),)):
            theme_id, save_theme = self._theme_selector.keypress(char)

            #if self._cnf.theme_not_supported:
            #    self._show_theme_not_supported()
            if theme_id == -4:
                self.refreshBody()
            elif theme_id == -1:
                ''' cancel or hide '''
                self._theme_name = self._theme_selector._applied_theme_name
                if self._config_win:
                    self._config_win._config_options['theme'][1] = self._theme_selector._applied_theme_name
                self._theme_selector = None
                self.ws.close_window()
                if self.ws.operation_mode == self.ws.NORMAL_MODE:
                    self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
                try:
                    self._watch_theme_lock.release()
                except:
                    pass
                self.refreshBody()

            elif theme_id == -2:
                self.theme_forced_selection = self._theme_selector._themes[self._theme_selector.selection]
                ''' ask to create new theme '''
                self._print_ask_to_create_theme()

            elif theme_id >= 0:
                ''' valid theme selection '''
                self._theme_name = self._theme_selector.theme_name(theme_id)
                if self._config_win:
                    self._config_win._config_options['theme'][1] = self._theme_name
                    self._config_win._saved_config_options['theme'][1] = self._theme_name
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Activating theme: {}'.format(self._theme_name))
                ret, ret_theme_name = self._theme.readAndApplyTheme(
                    self._theme_name,
                    theme_path=self._theme_selector._themes[theme_id][1]
                )
                if isinstance(ret, tuple):
                    ret = ret[0]
                if ret == 0:
                    self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
                    self._update_calculated_colors()
                elif ret < 0:
                    ch_ret, _ = self._cnf.is_project_theme(self._theme_name)
                    if ch_ret is None and \
                            not self._cnf.auto_update_theme:
                        self._theme_name = ret_theme_name
                    self._cnf.theme_not_supported = True
                    self._cnf.theme_has_error = True if ret == -1 else False
                    self._cnf.theme_not_supported_notification_shown = False
                    self._show_theme_not_supported()
                #self.refreshBody()
                self._redraw()
                # logger.error('4 redraw')
                curses.doupdate()
                # if self._cnf.theme_download_failed:
                #     self._print_theme_download_error()
                #     logger.info('_print_theme_download_error 3')
                ''' update config window '''
                if self.ws.window_mode == self.ws.CONFIG_MODE:
                    save_theme = True
                # make default
                if save_theme:
                    self._cnf.theme = self._theme_name
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('Setting default theme: {}'.format(self._theme_name))
                    if self._theme_selector.theme_is_watched:
                        self._cnf.opts['auto_update_theme'][1] = True
                        self._watch_theme(self._theme_selector.theme_path(theme_id))
                    else:
                        self._cnf.opts['auto_update_theme'][1] = False
                        self._watch_theme()

                try:
                    self._watch_theme_lock.release()
                except:
                    pass
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('n')):
                self.ws.close_window()
                if char == ord('y'):
                    ret = self._cnf._online_browser.save_config()
                    if ret == -2:
                        ''' save ok  '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config saved!!!')
                    elif ret == -3:
                        ''' error '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Error saving Online browser config!!!')
                        self._print_browser_config_save_error()
                        return
                    else:
                        ''' not modified '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config not saved (not modifed)')
                elif char == ord('n'):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Saving Online browser config canceled!!!')
                self._open_playlist_from_history()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('n')):
                self.ws.close_window()
                if char == ord('y'):
                    ret = self._browser_config_win.save_config()
                    if ret == -2:
                        ''' save ok  '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config saved!!!')
                    elif ret == -3:
                        ''' error '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Error saving Online browser config!!!')
                        self._print_browser_config_save_error()
                        return
                    else:
                        ''' not modified '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config not saved (not modifed)')
                elif char == ord('n'):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Saving Online browser config canceled!!!')
                    self._browser_config_win.reset_dirty_config()

                self._exit_browser_config()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER:
            logger.error('DE =========================')
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('n')):
                self.ws.close_window()
                if char == ord('y'):
                    ret = self._cnf._online_browser.save_config()
                    if ret == -2:
                        ''' save ok  '''
                        self._cnf._online_browser.reset_dirty_config()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config saved!!!')
                    elif ret == -3:
                        ''' error '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Error saving Online browser config!!!')
                        self._print_browser_config_save_error()
                        return
                    else:
                        ''' not modified '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Online browser config not saved (not modifed)')
                elif char == ord('n'):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Saving Online browser config canceled!!!')
                    self._cnf._online_browser.reset_dirty_config()

                self._exit_browser_config()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.CLEAR_REGISTER_MODE:
            if char in (ord('y'), ord('n')):
                self.ws.close_window()
                if char == ord('y'):
                    self._clear_register_file()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.CLEAR_ALL_REGISTERS_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('n')):
                self.ws.close_window()
                if char == ord('y'):
                    self._clear_all_register_files()
                self.refreshBody()
            return

        elif char in (ord('/'), ) and self.ws.operation_mode in self._search_modes.keys():
            self._reset_status_bar_right()
            if self.maxY > 5:
                self._give_me_a_search_class(self.ws.operation_mode)
                self.search.show(self.outerBodyWin)
                self.ws.operation_mode = self._search_modes[self.ws.operation_mode]
            return

        elif self.ws.operation_mode == self.ws.UPDATE_NOTIFICATION_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                with self._update_notify_lock:
                    self._update_version = ''
                self.ws.close_window()
                if char == ord('y'):
                    self._print_update_ok_notification()
                else:
                    self._print_update_nok_notification()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.UPDATE_NOTIFICATION_OK_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            # ok
            self.detect_if_player_exited = False
            self._cnf.PROGRAM_UPDATE = True
            self.helpWinContainer = None
            self.helpWin = None
            self.ws.close_window()
            ''' exit program '''
            self.log.asked_to_stop = True
            if self._cnf.dirty_playlist:
                self.saveCurrentPlaylist()
            if self.player:
                self.stopPlayer(show_message=False, reset_playing=False)
            self.ctrl_c_handler(0, 0)
            return -1

        elif self.ws.operation_mode == self.ws.UPDATE_NOTIFICATION_NOK_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.helpWinContainer = None
                self.helpWin = None
                self.ws.close_window()
                self.refreshBody()
            return

        # elif char in (ord('n'), ) and \
        #         self.ws.operation_mode in self._search_modes.keys():
        elif char in (ord('n'), ) and \
                self.ws.operation_mode in self._search_modes.keys():
            self._give_me_a_search_class(self.ws.operation_mode)
            if self.ws.operation_mode == self.ws.NORMAL_MODE:
                self._update_status_bar_right()
                self._random_requested = False
            ''' search forward '''
            if self.ws.operation_mode in \
                    (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE):
                self._search_list = self.stations
                sel = self.selection + 1
            elif self.ws.operation_mode == self.ws.THEME_MODE:
                self._search_list = self._theme_selector._themes
                sel = self._theme_selector.selection + 1
            elif self.ws.operation_mode == self.ws.SELECT_PLAYLIST_MODE:
                self._search_list = self._playlist_select_win._items
                sel = self._playlist_select_win._selected_playlist_id + 1
            elif self.ws.operation_mode == self.ws.SELECT_STATION_MODE:
                self._search_list = self._station_select_win._items
                sel = self._station_select_win._selected_playlist_id + 1
            elif self.ws.operation_mode == self.ws.GROUP_SELECTION_MODE:
                self._search_list = self._group_selection_window._items
                sel = self._group_selection_window.selection + 1

            if self.search.string:
                if sel == len(self._search_list):
                    sel = 0
                if self._cnf.browsing_station_service:
                    ret = self.search.get_next(
                        self._search_list,
                        sel,
                        search_function=self._cnf._online_browser.get_next
                    )
                else:
                    ret = self.search.get_next(self._search_list, sel)
                if ret is not None:
                    self._apply_search_result(ret, reapply=True)
            else:
                curses.ungetch('/')
            return

        elif char in (ord('N'), ) and \
                self.ws.operation_mode in self._search_modes.keys():
            self._give_me_a_search_class(self.ws.operation_mode)
            if self.ws.operation_mode == self.ws.NORMAL_MODE:
                self._update_status_bar_right()
                self._random_requested = False
            ''' search backwards '''
            if self.ws.operation_mode in \
                    (self.ws.NORMAL_MODE, self.ws.PLAYLIST_MODE ):
                self._search_list = self.stations
                sel = self.selection - 1
            elif self.ws.operation_mode == self.ws.THEME_MODE:
                self._search_list = self._theme_selector._themes
                sel = self._theme_selector.selection - 1
            elif self.ws.operation_mode == self.ws.SELECT_PLAYLIST_MODE:
                self._search_list = self._playlist_select_win._items
                sel = self._playlist_select_win._selected_playlist_id - 1
            elif self.ws.operation_mode == self.ws.SELECT_STATION_MODE:
                self._search_list = self._station_select_win._items
                sel = self._station_select_win._selected_playlist_id - 1
            elif self.ws.operation_mode == self.ws.GROUP_SELECTION_MODE:
                self._search_list = self._group_selection_window._items
                sel = self._group_selection_window.selection - 1

            if self.search.string:
                if sel < 0:
                    sel = len(self._search_list) - 1
                if self._cnf.browsing_station_service:
                    ret = self.search.get_previous(
                        self._search_list,
                        sel,
                        search_function=self._cnf._online_browser.get_previous
                    )
                else:
                    ret = self.search.get_previous(self._search_list, sel)
                if ret is not None:
                    self._apply_search_result(ret, reapply=True)
            else:
                curses.ungetch('/')
            return

        elif self.ws.operation_mode in \
            [self._search_modes[x] for x in self._search_modes.keys()]:
            ''' serve search results '''
            ret = self.search.keypress(self.search._edit_win, char)
            if ret == 0:
                if self.ws.operation_mode in self.search_main_window_modes:
                    self._search_list = self.stations
                    sel = self.selection + 1
                elif self.ws.previous_operation_mode == self.ws.THEME_MODE:
                    self._search_list = self._theme_selector._themes
                    sel = self._theme_selector.selection + 1
                elif self.ws.previous_operation_mode in (
                    self.ws.SELECT_PLAYLIST_MODE,
                    self.ws.PASTE_MODE,
                ):
                    self._search_list = self._playlist_select_win._items
                    sel = self._playlist_select_win._selected_playlist_id + 1
                elif self.ws.previous_operation_mode == self.ws.SELECT_STATION_MODE:
                    self._search_list = self._station_select_win._items
                    sel = self._station_select_win._selected_playlist_id + 1
                elif self.ws.previous_operation_mode == self.ws.GROUP_SELECTION_MODE:
                    self._search_list = self._group_selection_window._items
                    sel = self._group_selection_window.selection + 1

                ''' perform search '''
                if sel == len(self._search_list):
                    sel = 0
                if self._cnf.browsing_station_service:
                    ret = self.search.get_next(
                        self._search_list,
                        sel,
                        search_function=self._cnf._online_browser.get_next
                    )
                else:
                    ret = self.search.get_next(self._search_list, sel)
                if ret is None:
                    if self.search.string:
                        self.search.print_not_found()
                else:
                    self._apply_search_result(ret)
            elif ret == 2:
                ''' display help '''
                self._show_search_help()
            elif ret == -1:
                ''' cancel search '''
                self.ws.close_window()
                self.refreshBody()
                return

        elif self.ws.operation_mode == self.ws.GROUP_SELECTION_MODE:
            ret = self._group_selection_window.keypress(char)
            if ret <= 0:
                if ret == 0:
                    ret = self._groups[self._group_selection_window.selection][0]
                    self.setStation(ret)
                    self._put_selection_in_the_middle(force=True)
                    self.refreshBody()
                    self.selections[self.ws.NORMAL_MODE] = [self.selection,
                                                            self.startPos,
                                                            self.playing,
                                                            self.stations]
                self._group_selection_window = None
                self._groups = None
                self.ws.close_window()
                self.refreshBody()
            elif ret == 2:
                ''' show help '''
                self._show_group_help()
                pass
            return

        elif char in (ord('T'), ):
            self._update_status_bar_right()
            if self.ws.operation_mode == self.ws.SESSION_LOCKED_MODE:
                self.ws.close_window()
                self.refreshBody()
            else:
                self._toggle_transparency()
            return

        elif char in self._global_functions.keys():
            self._global_functions[char]()
            return

        elif self.ws.operation_mode == self.ws.PLAYLIST_SCAN_ERROR_MODE:
            ''' exit due to scan error '''
            # ok
            self.detect_if_player_exited = False
            self.stopPlayer()
            return -1

        elif self.ws.operation_mode == self.ws.PLAYLIST_RECOVERY_ERROR_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self._cnf.playlist_recovery_result = 0
                self.ws.close_window()
                self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('Y')):
                self.ws.close_window()
                if not self._cnf.locked and char == ord('Y'):
                    self._cnf.auto_save_playlist = True
                ret = self.saveCurrentPlaylist()
                #if ret == -1:
                #    # do not exit
                #    return
                ''' exit program '''
                # ok
                self.detect_if_player_exited = False
                if self.player:
                    self.stopPlayer()
                self.ctrl_c_handler(0, 0)
                return -1
            elif char in (ord('n'), ):
                ''' exit program '''
                # ok
                self.detect_if_player_exited = False
                if self.player:
                    self.stopPlayer()
                self.ctrl_c_handler(0, 0, False)
                self._wait_for_threads()
                return -1
            elif char in (curses.KEY_EXIT, ord('q'), 27):
                self.bodyWin.nodelay(True)
                char = self.bodyWin.getch()
                self.bodyWin.nodelay(False)
                if char == -1:
                    ''' ESCAPE '''
                    self._cnf.save_config()
                    self.ws.close_window()
                    self.refreshBody()
                    #return -1
                    return
            return

        elif self.ws.operation_mode in (self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE,
                                        self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE):
            if char in self._global_functions.keys():
                self._global_functions[char]()
            else:
                self.ws.close_window()
                if char in (ord('y'), ord('Y')):
                    if not self._cnf.locked and char == ord('Y'):
                        self._cnf.auto_save_playlist = True
                    ret = self.saveCurrentPlaylist()
                    if ret == 0:
                        if self.ws.operation_mode == self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE:
                            self._open_playlist()
                        else:
                            self._goto_history_back_handler()
                    else:
                        if self._cnf.browsing_station_service:
                            self._cnf.removed_playlist_history_item()
                elif char in (ord('n'), ):
                    if self.ws.operation_mode == self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE:
                        self._open_playlist()
                    else:
                        self._goto_history_back_handler()
                elif char in (curses.KEY_EXIT, ord('q'), 27):
                    self.bodyWin.nodelay(True)
                    char = self.bodyWin.getch()
                    self.bodyWin.nodelay(False)
                    if char == -1:
                        ''' ESCAPE '''
                        if self._cnf.browsing_station_service:
                            self._cnf.removed_playlist_history_item()
                        self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ord('Y')):
                if not self._cnf.locked and char == ord('Y'):
                    self._cnf.confirm_playlist_reload = False
                self.ws.close_window()
                self.reloadCurrentPlaylist(self.ws.PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE)
            elif char in (ord('n'), ):
                ''' close confirmation message '''
                self.stations = self._cnf.stations
                self.ws.close_window()
                self.refreshBody()
            else:
                pass
            return

        elif self.ws.operation_mode == self.ws.PLAYLIST_RELOAD_CONFIRM_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            self._reload_playlist_after_confirmation(char)
            return

        elif self.ws.operation_mode in (
                self.ws.REMOVE_STATION_MODE,
                self.ws.REMOVE_GROUP_MODE
        ):
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            if char in (ord('y'), ord('Y')):
                self._remove_station(char)
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Canceling: Remove station')

            self.ws.close_window()
            self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.FOREIGN_PLAYLIST_ASK_MODE:
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (ord('y'), ):
                ret = self._cnf.copy_playlist_to_config_dir()
                if ret == 0:
                    ind = self._cnf.current_playlist_index()
                    self.selections[self.ws.PLAYLIST_MODE][0] = self.selections[self.ws.PLAYLIST_MODE][2] = ind
                    self.ws.close_window()
                    self.refreshBody()
                elif ret == 1:
                    self._print_foreign_playlist_message()
                else:
                    ''' error '''
                    self._print_foreign_playlist_copy_error()
            elif char in (ord('n'), ):
                self.ws.close_window()
                self.refreshBody()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Canceling: Move foreign playlist...')
            return

        elif self.ws.operation_mode == self.ws.STATION_INFO_MODE:
            self._update_status_bar_right()
            icy_data_name = self.player.icy_data('icy-name')
            if char == ord('r') and self.stations[self.playing][0] != icy_data_name:
                self._cnf.stations_history.rename_station(
                    self._cnf.station_title,
                    self.stations[self.playing][0],
                    icy_data_name
                )
                self.stations[self.playing][0] = icy_data_name
                self._cnf.dirty_playlist = True
                self._last_played_station = self.stations[self.playing]
                self.selections[0][3] = self.stations
                self._show_station_info()
            else:
                self.ws.close_window()
            self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.CONNECTION_MODE:
            ret = self._connection_type_edit.keypress(char)
            if ret == -1:
                ''' Cancel '''
                self.ws.close_window()
                self._connection_type_edit = None
            elif ret == 1:
                ''' changed '''
                force_http = self._connection_type_edit.connection_type
                restart = False if force_http == self.player.force_http else True
                self.player.force_http = force_http
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('force http connections = {}'.format(self.player.force_http))
                self.ws.close_window()
                self._connection_type_edit = None
                if restart:
                    self.restartPlayer('*** Restarting playback due to connection type change ***')
            self.refreshBody()
            return

        elif self.ws.operation_mode == self.ws.PLAYER_PARAMS_MODE:
            ret = self._player_select_win.keypress(char)
            if ret == -2:
                ''' Cancel '''
                self.ws.close_window()
                self._player_select_win = None
                self.refreshBody()

            elif ret == 0:
                ''' Parameter selected '''
                if self._cnf.params_changed:
                    self._cnf.params = deepcopy(self._player_select_win.params)
                self.ws.close_window()
                if self._player_select_win._extra.active != self._player_select_win._extra.original_active:
                    self.restartPlayer('*** Restarting playback due to player parameter change ***')
                self._player_select_win = None
                self.refreshBody()
                self._cnf.dirty_config = False
                self._cnf.params_changed = False
                # Do not update the active value
                self._cnf.set_backup_params_from_session()

            elif ret == 1:
                ''' Help '''
                self._player_select_win.focus = False
                self._player_select_win.from_config = False
                self._show_config_player_help()

            elif ret > 1:
                ''' error '''
                pass
            ''' set params for player at backup params, even when
                operration has been canceled
            '''
            self._cnf.get_player_params_from_backup(param_type=1)
            return

        elif self.ws.operation_mode == self.ws.RECORD_WINDOW_MODE:
            if char == ord('x'):
                self._cnf.show_recording_start_message = False
                self._cnf.dirty_config = True
            self.ws.close_window()
            self.refreshBody()
            return

        elif self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
            if char in self._global_functions.keys():
                self._global_functions[char]()
                return
            if self.ws.operation_mode in (
                    self.ws.MAIN_HELP_MODE,
                    self.ws.MAIN_HELP_MODE_PAGE_2,
                    self.ws.MAIN_HELP_MODE_PAGE_3,
                    self.ws.MAIN_HELP_MODE_PAGE_4,
                    self.ws.MAIN_HELP_MODE_PAGE_5):
                if char in (ord('n'), ord('p'), ):
                    self.helpWinContainer = None
                    self.helpWin = None
                    func = (self._show_main_help,
                            self._show_main_help_page_2,
                            self._show_main_help_page_3,
                            self._show_main_help_page_4,
                            self._show_main_help_page_5)
                    if self._main_help_id >= len(func):
                        self._main_help_id = len(func) - 1
                    if char == ord('n'):
                        self._main_help_id += 1
                        if self._main_help_id == len(func):
                            self._main_help_id = 0
                    else:
                        self._main_help_id -= 1
                        if self._main_help_id < 0:
                            self._main_help_id = len(func) - 1
                    self.ws.close_window()
                    func[self._main_help_id](from_keyboard=True)
                    return
            self._handle_passive_windows()
            return

        else:
            self._current_selection = self.selection
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug('current selection = {}'.format(self._current_selection))
            self._update_history_positions_in_list()

            if char in (ord('?'), ):
                self._update_status_bar_right()
                self._print_help()
                return

            if char in (curses.KEY_END, ):
                self._update_status_bar_right()
                if self.number_of_items > 0:
                    self.setStation(-1)
                    self.refreshBody()
                return

            if char in (ord('G'), ord('g')):
                self._jump_to_jumpnr(char)
                self.refreshBody()
                self._reset_status_bar_right()
                return

            if char in map(ord, map(str, range(0, 10))):
                self._random_requested = False
                if self.number_of_items > 0:
                    self.jumpnr += chr(char)
                    self._update_status_bar_right(status_suffix=self.jumpnr + 'G')
                    self._cnf.jump_tag = -1
                    return
            else:
                if char not in (curses.ascii.EOT, curses.ascii.NAK, 4, 21):
                    self._update_status_bar_right()

            if char in (ord('g'), curses.KEY_HOME):
                self._update_status_bar_right()
                self.setStation(0)
                self.refreshBody()
                return

            if char in (curses.KEY_EXIT, ord('q'), 27) or \
                    (self.ws.operation_mode == self.ws.PLAYLIST_MODE and \
                    char in (ord('h'), curses.KEY_LEFT)):
                ''' exit program or playlist mode '''
                self.bodyWin.nodelay(True)
                char = self.bodyWin.getch()
                self.bodyWin.nodelay(False)
                if char == -1:
                    ''' ESCAPE '''
                    self._update_status_bar_right(status_suffix='')
                    if self.ws.operation_mode == self.ws.PLAYLIST_MODE:
                        ''' return to stations view '''
                        # logger.error('DE \n    self._cnf.open_register_list = {}\n'.format(self._cnf.open_register_list))
                        if self._cnf.open_register_list:
                            self.selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                            self.playlist_selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing]
                        else:
                            self.selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                            self.playlist_selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing]
                        # self.ll('ESCAPE')
                        self.ws.close_window()
                        self._give_me_a_search_class(self.ws.operation_mode)
                        self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
                        self.stations = self._cnf.stations
                        self.number_of_items = len(self.stations)
                        self.refreshBody()
                        return
                    else:
                        if self._cnf.is_register:
                            ''' go back to playlist history '''
                            self._open_playlist_from_history()
                            return
                        elif self._cnf.browsing_station_service:
                            ''' go back to playlist history '''
                            if self._cnf.online_browser.is_config_dirty():
                                self._ask_to_save_browser_config_to_exit()
                            else:
                                self._open_playlist_from_history()
                            return
                        ''' exit program '''
                        ''' stop updating the status bar '''
                        #with self.log.lock:
                        #    self.log.asked_to_stop = True
                        self.log.asked_to_stop = True
                        if self._cnf.dirty_playlist:
                            if self._cnf.auto_save_playlist:
                                ''' save playlist and exit '''
                                ret = self.saveCurrentPlaylist()
                                #if ret == -1:
                                #    # do not exit program
                                #    return
                            else:
                                ''' ask to save playlist '''
                                self._print_save_modified_playlist(self.ws.ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE)
                                return
                        #else:
                        #    self._open_playlist()
                        if self.player:
                            # ok
                            self.detect_if_player_exited = False
                            self.stopPlayer(
                                show_message=False,
                                reset_playing=False
                            )
                        self.ctrl_c_handler(0,0)
                        return -1
                else:
                    return

            if char in (curses.KEY_DOWN, ord('j')):
                self._move_cursor_one_down()
                return

            if char in (curses.KEY_UP, ord('k')):
                self._move_cursor_one_up()
                return

            if char in (curses.KEY_PPAGE, ):
                self._page_up()
                return

            if char in (curses.KEY_NPAGE, ):
                self._page_down()
                return

            if self.ws.operation_mode == self.ws.NORMAL_MODE:
                if char == ord('|'):
                    self._reset_status_bar_right()
                    # if self.player.PLAYER_NAME != 'vlc':
                    if self.player.PLAYER_NAME == 'vlc' and \
                            platform.startswith('win'):
                        self._show_win_no_record()
                    else:
                        self.player.recording = 1 if self.player.recording == 0 else 0
                        if self.player.recording > 0:
                            if self.player.isPlaying():
                                self.player.already_playing = True
                            else:
                                self.player.already_playing = False
                        else:
                            self.player.already_playing = False
                        self._show_recording_status_in_header()
                        if self._cnf.show_recording_start_message:
                            self._show_recording_toggle_window()
                        else:
                            self.refreshBody()

                elif char == curses.ascii.BEL:
                    ''' ^G - show groups '''
                    self._reset_status_bar_right()
                    self._group_selection_window = None
                    self._show_group_selection()

                elif char in (curses.ascii.EM, curses.ascii.ENQ):
                    if self._cnf._online_browser is None:
                        # logger.error('^E ^Y')
                        d = [x for x, y in enumerate(self.stations) if y[1] == '-' ]
                        # logger.error(d)
                        if d:
                            if self.selection in d:
                                # logger.error('selection in d')
                                if len(d) == 1:
                                    txt='___No more groups found!___'
                                    self._show_notification_with_delay(
                                            txt=txt,
                                            mode_to_set=self.ws.NORMAL_MODE,
                                            callback_function=self.refreshBody)
                                    ind = -1
                                else:
                                    ind = d.index(self.selection)
                                    if char == curses.ascii.EM:
                                        ind -= 1
                                        if ind < 0:
                                            ind = len(d) - 1
                                    else:
                                        ind += 1
                                        if ind == len(d):
                                            ind = 0
                                    ind = d[ind]
                                    # logger.error('1 ind = {}'.format(ind))
                            else:
                                # logger.error('selection not in d')
                                if len(d) == 1:
                                    ind = d[0]
                                    # logger.error('x1 ind = {}'.format(ind))
                                else:
                                    if char == curses.ascii.EM:
                                        try:
                                            ind = [n for n in d if n < self.selection][-1]
                                            # logger.error('x2 ind = {}'.format(ind))
                                        except IndexError:
                                            ind = [n for n in d if n < self.number_of_items][0]
                                            # logger.error('x3 ind = {}'.format(ind))
                                    else:
                                        try:
                                            ind = [n for n in d if n > self.selection][0]
                                            # logger.error('x4 ind = {}'.format(ind))
                                        except IndexError:
                                            ind = [n for n in d if n > -1][0]
                                            # logger.error('x5 ind = {}'.format(ind))
                        else:
                            txt='___No groups found!___'
                            self._show_notification_with_delay(
                                    txt=txt,
                                    mode_to_set=self.ws.NORMAL_MODE,
                                    callback_function=self.refreshBody)
                            ind = -1
                        if ind != -1:
                            self.setStation(ind)
                            self._put_selection_in_the_middle(force=True)
                            self.refreshBody()
                            self.selections[self.ws.NORMAL_MODE] = [self.selection,
                                                                    self.startPos,
                                                                    self.playing,
                                                                    self.stations]

                elif char == curses.KEY_F8 and platform.startswith('win'):
                    ''' manage players on Windows
                        will present them after curses end
                    '''
                    self._cnf.WIN_MANAGE_PLAYERS = True
                    self._show_win_manage_players()

                elif char == curses.KEY_F9 and platform.startswith('win'):
                    ''' show exe location on Windows
                        will present them after curses end
                    '''
                    self._cnf.WIN_PRINT_PATHS = True
                    self._show_win_print_exe_paths()

                elif char == curses.KEY_F10 and platform.startswith('win'):
                    ''' uninstall on Windows '''
                    self._cnf.WIN_UNINSTALL = True
                    self._show_win_uninstall()

                elif char == curses.KEY_F7 and platform.startswith('win'):
                    ''' delete old installation files on Windows '''
                    self._show_win_remove_old_installation()

                elif char in (ord('a'), ord('A')):
                    self._reset_status_bar_right()
                    if not self._cnf.browsing_station_service:
                        self._station_editor = PyRadioEditor(
                            self.stations,
                            self.selection,
                            self.outerBodyWin,
                            self._cnf.default_encoding,
                            global_functions=self._global_functions)
                        if char == ord('A'):
                            self._station_editor.append = True
                        self._station_editor.show()
                        self._station_editor.item = ['', '', '']
                        self.ws.operation_mode = self.ws.ADD_STATION_MODE

                elif char == ord('p'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        self._print_not_applicable()
                    else:
                        self._paste()

                elif char == ord('V'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        txt = '''Voting for station. Please wait...'''
                        self._show_help(txt, self.ws.NORMAL_MODE, caption=' ', prompt=' ', is_message=True)
                        if self.player.isPlaying():
                            self._cnf._online_browser.vote(self.playing)
                        else:
                            self._cnf._online_browser.vote(self.selection)

                elif char == ord('I'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        self._browser_station_info()
                    else:
                        self._normal_station_info()

                elif char == ord('C'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        self.ws.operation_mode = self.ws.BROWSER_SERVER_SELECTION_MODE
                        self._browser_server_selection()

                elif char == ord('S'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        self.ws.operation_mode = self.ws.BROWSER_SORT_MODE
                        self._browser_sort()

                elif char == ord('i'):
                    self._reset_status_bar_right()
                    self._normal_station_info()

                elif char == ord('e'):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service: return
                    if python_version[0] == '2':
                        if not is_ascii(self.stations[self.selection][0]):
                            self._print_py2_editor_error()
                            return
                    self._station_editor = PyRadioEditor(
                        self.stations,
                        self.selection,
                        self.outerBodyWin,
                        self._cnf.default_encoding,
                        global_functions=self._global_functions,
                        adding=False)
                    self._station_editor.show(self.stations[self.selection])
                    self.ws.operation_mode = self.ws.EDIT_STATION_MODE

                elif char == ord('c'):
                    ''' open config '''
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        # self._print_not_implemented_yet()
                        # return
                        self.ws.operation_mode = self.ws.RADIO_BROWSER_CONFIG_MODE
                        self._browser_init_config(init=True)
                    else:
                        if self._cnf.locked:
                            self._print_session_locked()
                            return
                        self._old_config_encoding = self._cnf.opts['default_encoding'][1]
                        ''' open config window '''
                        #self.ws.operation_mode = self.ws.window_mode = self.ws.CONFIG_MODE
                        self.ws.window_mode = self.ws.CONFIG_MODE
                        if not self.player.isPlaying():
                            self.log.write(msg='Selected player: ' + self.player.PLAYER_NAME, help_msg=True)
                        if self._cnf.dirty_config:
                            self._cnf.save_config()
                            self._cnf.dirty_config = False
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Config saved before entering Config Window')
                        self._show_config_window()
                    return

                elif char in (ord('E'), ):
                    self._reset_status_bar_right()
                    self._old_station_encoding = self.stations[self.selection][2]
                    if self._old_station_encoding == '':
                        self._old_station_encoding = self._cnf.default_encoding
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.info('encoding = {}'.format(self._old_station_encoding))
                    self.ws.operation_mode = self.ws.SELECT_STATION_ENCODING_MODE
                    self._encoding_select_win = PyRadioSelectEncodings(
                        self.outerBodyMaxY,
                        self.outerBodyMaxX,
                        self._old_station_encoding,
                        self._cnf.default_encoding
                    )
                    self._encoding_select_win.set_reduced_global_functions(self._global_functions)
                    self._encoding_select_win.init_window()
                    self._encoding_select_win.refresh_win()
                    self._encoding_select_win.setEncoding(self._old_station_encoding)

                elif char == ord('O'):
                    ''' Open Online services
                        Currently only BrowserInfoBrowser is available
                        so go ahead and open this one.
                        If a second one is implemented in the future,
                        this should display a selection list.
                    '''
                    self._reset_status_bar_right()
                    if not self._cnf.browsing_station_service:
                        self._cnf.browsing_station_service = True
                        self.playSelectionBrowser(a_url='api.radio-browser.info')
                    return

                elif char in (ord('o'), ):
                    self._update_status_bar_right(status_suffix='')
                    self._reset_status_bar_right()
                    self._set_rename_stations()
                    self._cnf.open_register_list = False
                    if self._cnf.browsing_station_service:
                        return
                    self._check_to_open_playlist()
                    self._do_display_notify()
                    return

                elif char in (curses.KEY_ENTER,
                              ord('\n'), ord('\r'),
                              curses.KEY_RIGHT, ord('l')):
                    if self.player.isPlaying() and \
                            self.player.playback_is_on:
                        self._stop_player()
                    self._start_player()
                    self._do_display_notify()
                    return

                elif char in (curses.KEY_LEFT, ord('h')):
                    self._stop_player()
                    return

                elif char in (ord(' '), ):
                    if self.player.isPlaying() and \
                            self.player.playback_is_on and \
                            self.player.recording and \
                            self.player.recording_filename != '':
                        self._pause_player()
                    else:
                        self._stop_player()
                    return

                elif char in (ord('x'), curses.KEY_DC):
                    # TODO: make it impossible when session locked?
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        return
                    if self.number_of_items > 0:
                        if self._cnf.locked:
                            txt='___Cannot delete station!!!___\n______Session is locked'
                            if self.stations[self.selection][1] == '-':
                                txt = txt.replace('station', 'group')
                            self._show_notification_with_delay(
                                    txt=txt,
                                    mode_to_set=self.ws.NORMAL_MODE,
                                    callback_function=self.refreshBody)
                        else:
                            if self.stations[self.selection][1] == '-':
                                self._ask_to_remove_group()
                            else:
                                self._ask_to_remove_station()
                    return

                elif char in(ord('s'), ):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        # self._print_not_implemented_yet()
                        # return
                        self.ws.operation_mode = self.ws.BROWSER_SEARCH_MODE
                        self._browser_init_search(parent=self.outerBodyWin)
                    else:
                        if self._cnf.browsing_station_service or \
                                self._cnf.is_register:
                            return
                        if self._cnf.dirty_playlist:
                            self.saveCurrentPlaylist()
                        else:
                            self._show_notification_with_delay(
                                    txt='___Playlist not modified!!!___',
                                    mode_to_set=self.ws.NORMAL_MODE,
                                    callback_function=self.refreshBody)
                    return

                elif char in (ord('r'), ):
                    self._reset_status_bar_right(random_request=True)
                    ''' Pick a random radio station '''
                    self.play_random()
                    return

                elif char in (ord('R'), ):
                    self._reset_status_bar_right()
                    if self._cnf.browsing_station_service:
                        return
                    ''' Reload current playlist '''
                    if self._cnf.dirty_playlist:
                        if self._cnf.confirm_playlist_reload:
                            self._print_playlist_dirty_reload_confirmation()
                        else:
                            self.ws.operation_mode = self.ws.PLAYLIST_RELOAD_CONFIRM_MODE
                            self._reload_playlist_after_confirmation(char)
                    else:
                        if not self._cnf.is_register and self._cnf.confirm_playlist_reload:
                            self._print_playlist_reload_confirmation()
                        else:
                            self.ws.operation_mode = self.ws.PLAYLIST_RELOAD_CONFIRM_MODE
                            self._reload_playlist_after_confirmation(char)
                    return

                elif char in (ord('z'), ):
                    ''' change force http '''
                    self._reset_status_bar_right()
                    self.ws.operation_mode = self.ws.CONNECTION_MODE
                    self._connection_type_edit = PyRadioConnectionType(
                        parent=self.outerBodyWin,
                        connection_type=self.player.force_http,
                        global_functions=self._global_functions
                    )
                    self._connection_type_edit.show()
                    return

                elif char in (ord('Z'), ):
                    self._reset_status_bar_right()
                    self.ws.operation_mode = self.ws.PLAYER_PARAMS_MODE
                    self._player_select_win = PyRadioExtraParams(
                        self._cnf,
                        self.bodyWin,
                        global_functions=self._global_functions
                    )
                    self._player_select_win.show()
                    return

                elif char == ord('J'):
                    self._random_requested = False
                    self.jumpnr = ''
                    ''' tag for jump '''
                    self._cnf.jump_tag = self.selection
                    self._update_status_bar_right(status_suffix=str(self._cnf.jump_tag + 1) + 'J')
                    return

                elif char in (curses.ascii.NAK, 21):
                    ''' ^U, move station Up '''
                    self._random_requested = False
                    if self.jumpnr:
                        self._cnf.jump_tag = int(self.jumpnr) - 1
                    self._move_station(-1)
                    self._reset_status_bar_right()
                    return

                elif char in (curses.ascii.EOT, 4):
                    ''' ^D, move station Down '''
                    self._random_requested = False
                    if self.jumpnr:
                        self._cnf.jump_tag = int(self.jumpnr) - 1
                    self._move_station(1)
                    self._reset_status_bar_right()
                    return

            elif self.ws.operation_mode == self.ws.PLAYLIST_MODE:
                self._random_requested = False

                if char == ord(' '):
                    self.stopPlayer()

                # logger.error('DE pl 1 active_stations = \n\n{}\n\n'.format(self.active_stations))
                if char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
                            curses.KEY_RIGHT, ord('l')):
                    self._update_status_bar_right(status_suffix='')
                    if self._cnf.open_register_list:
                        self.playlist_selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing]
                        self.selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                    else:
                        self.playlist_selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing]
                        self.selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                    # self.ll('oooopen')
                    if self.number_of_items > 0:
                        ''' return to stations view '''
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Loading playlist: "{}"'.format(self.stations[self.selection][-1]))
                        playlist_to_try_to_open = self.stations[self.selection][-1]
                        logger.error('\n\nplaylist_to_try_to_open = "{}"\n\n'.format(playlist_to_try_to_open))
                        ret = self._cnf.read_playlist_file(stationFile=playlist_to_try_to_open)
                        logger.error('DE playlist_selections = {}'.format(playlist_to_try_to_open))

                        if ret == -1:
                            self.stations = self._cnf.playlists
                            self._print_playlist_load_error()
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Error loading playlist: "{}"'.format(self.stations[self.selection][-1]))
                        elif ret == -2:
                            self.stations = self._cnf.playlists
                            self._print_playlist_not_found_error()
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Playlist not found: "{}"'.format(self.stations[self.selection][-1]))
                        elif ret == -7:
                            self._print_playlist_recovery_error()
                        else:
                            self._playlist_in_editor = playlist_to_try_to_open
                            self._playlist_error_message = ''
                            self.number_of_items = ret
                            logger.error('self._playlist_in_editor = {0}\nself.number_of_items = {1}'.format(self._playlist_in_editor, self.number_of_items))
                            # logger.error('self.selcctions\n{0}\nself.playlist_selections\n{1}'.format(self.selections, self.playlist_selections))
                            self.ll('selecctions')
                            if self._cnf.open_register_list:
                                self.selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                                self.playlist_selections[self.ws.REGISTER_MODE] = self.selections[self.ws.REGISTER_MODE][:-1][:]
                            else:
                                self.selections[self.ws.operation_mode] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
                                self.playlist_selections[self.ws.operation_mode] = self.selections[self.ws.operation_mode][:-1][:]
                            # self.ll('ENTER')
                            self.ws.close_window()
                            self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
                            if self.saved_active_stations != [['', 0], ['', -1]]:
                                self.active_stations = self.saved_active_stations[:]
                                self.saved_active_stations = [['', 0], ['', -1]]
                            logger.error('self.saved_active_stations = {}'.format(self.saved_active_stations))
                            self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
                            self._set_active_stations()
                            self._give_me_a_search_class(self.ws.operation_mode)
                            if self.playing < 0:
                                self._put_selection_in_the_middle(force=True)
                                self.refreshBody()
                            self._do_display_notify()
                            logger.error('\n\n')
                            # logger.error('self.selcctions\n{0}\nself.playlist_selections\n{1}'.format(self.selections, self.playlist_selections))
                            self.ll('after')

                            # if self._cnf.open_last_playlist:
                            #     self._cnf.save_last_playlist()

                elif char in (ord('r'), ):
                    self._update_status_bar_right()
                    ''' read playlists from disk '''
                    txt = '''Reading playlists. Please wait...'''
                    self._show_help(txt, self.ws.PLAYLIST_MODE, caption=' ', prompt=' ', is_message=True)
                    self._reload_playlists()

                elif char in (ord('\''), ):
                    ''' Toggle playlists / registers '''
                    if self._cnf.open_register_list:
                        ''' going back to playlists '''
                        self.playlist_selections[self.ws.REGISTER_MODE] = [self.selection, self.startPos, self.playing]
                        ''' set selections 0,1,2 to saved values '''
                        self.selections[self.ws.PLAYLIST_MODE][:-1] = self.playlist_selections[self.ws.PLAYLIST_MODE][:]
                        self.selections[self.ws.REGISTER_MODE][:-1] = self.playlist_selections[self.ws.REGISTER_MODE][:]
                        self._cnf.open_register_list = not self._cnf.open_register_list
                        self._status_suffix = '\''
                        self._register_open_pressed = True
                        self._open_playlist()
                    else:
                        ''' opening registers list '''
                        if self._cnf.registers_exist():
                            self.playlist_selections[self.ws.PLAYLIST_MODE] = [self.selection, self.startPos, self.playing]
                            ''' set selections 0,1,2 to saved values '''
                            self.selections[self.ws.PLAYLIST_MODE][:-1] = self.playlist_selections[self.ws.REGISTER_MODE][:]
                            self._cnf.open_register_list = not self._cnf.open_register_list
                            self._status_suffix = '\''
                            self._register_open_pressed = True
                            self._open_playlist()
                        else:
                            self._status_suffix = ''
                            self._register_open_pressed = False
                            self._update_status_bar_right(status_suffix='')
                            self._show_notification_with_delay(
                                    txt='____All registers are empty!!!____',
                                    mode_to_set=self.ws.PLAYLIST_MODE,
                                    callback_function=self.refreshBody)
                    self._update_status_bar_right(reg_open_pressed=self._register_open_pressed, status_suffix=self._status_suffix)
                    self._do_display_notify()

                # else:
                #     self._update_status_bar_right(status_suffix='')

    def _jump_and_play_selection(self, jumpnr=None):
        self._jump_to_jumpnr('', jumpnr)
        self.playSelection()
        self.refreshBody()
        self._reset_status_bar_right()

    def _jump_to_jumpnr(self, char='', jumpnr=None):
        if jumpnr is not None:
            self.jumpnr = jumpnr
        self._random_requested = False
        if self.number_of_items > 0:
            if self.jumpnr == '':
                if char == ord('G'):
                    self.setStation(-1)
                else:
                    self.setStation(0)
            else:
                force_center = False
                jumpto = min(int(self.jumpnr) - 1, len(self.stations) - 1)
                jumpto = max(0, jumpto)
                if jumpto < self.startPos - 1 or \
                        jumpto > self.startPos + self.bodyMaxY:
                    force_center = True
                self.setStation(jumpto)
                self._put_selection_in_the_middle(force=force_center)
                self.jumpnr = ''

    def _html_start_player(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        if self.number_of_items > 0:
            self._start_player()
            return '<div class="alert alert-success">Playing <b>{}</b>!</div>'.format(self.stations[self.selection][0])
        return '<div class="alert alert-danger"><b>No stations in Playlist!</b>!</div>'

    def _start_player(self):
        self.player.already_playing = False
        self._reset_status_bar_right()
        # self._show_recording_status_in_header()
        self.log.counter = None
        self._update_status_bar_right()
        if self.number_of_items > 0:
            self.playSelection()
            self.refreshBody()

    def _html_stop_player(self):
        self._reset_status_bar_right()
        if self.ws.window_mode == self.ws.PLAYLIST_MODE:
            return '<div class="alert alert-danger">Operation not permitted (not in normal mode)</div>'
        self._stop_player()
        return '<div class="alert alert-success">Player <b>stopped</b>!</div>'

    def _pause_player(self):
        self._reset_status_bar_right()
        self.player.togglePause()

    def _stop_player(self):
        self._reset_status_bar_right()
        self._show_recording_status_in_header()
        self.log.counter = None
        self._update_status_bar_right()
        if self.number_of_items > 0:
            if self.player.isPlaying():
                self.stopPlayer(show_message=True)
            else:
                self.detect_if_player_exited = True
                self.playSelection()
            self.refreshBody()
        self.player.recording_filename = ''
        self.player.muted = self.player.paused = False

    def _browser_config_not_modified(self):
        self.ws.close_window()
        if self._cnf._online_browser:
            self._cnf._online_browser._config_win = None
        else:
            self._browser_config_win = None
        self.refreshBody()
        msg = 'Online service Config not modified!!!'
        if self.player.isPlaying():
            self.log.write(msg=msg)
            self.player.threadUpdateTitle()
        else:
            self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)

    def _saved_browser_config_and_exit(self):
        self.ws.close_window()
        if self._cnf._online_browser:
            logger.error('DE <<< READ CONFIG >>>')
            self._cnf._online_browser.read_config()
            self._cnf._online_browser._config_win = None
        else:
            self._browser_config_win = None
        self.refreshBody()
        msg = 'Online service Config saved successfully!!!'
        if self.player.isPlaying():
            self.log.write(msg=msg)
            self.player.threadUpdateTitle()
        else:
            self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)

    def _exit_browser_config(self):
        if self._cnf.online_browser:
            if self._cnf.online_browser.is_config_dirty():
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Onine Browser config is dirty!')
                self._ask_to_save_browser_config_from_browser()
                return
        else:
            if self._browser_config_win.is_config_dirty():
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Onine Browser config is dirty!')
                self._ask_to_save_browser_config_from_config()
                return

        self.ws.close_window()
        if self._cnf._online_browser:
            self._cnf._online_browser._config_win = None
        else:
            self._browser_config_win = None
        self.refreshBody()

    def _can_display_help_msg(self, msg):
        ''' len("Press ? for help") = 16 '''
        if msg is None:
            ret = False
        else:
            ret = self.outerBodyMaxX - len(msg) - 16 > 10 if msg else True
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug('Display "Press ? for help": {}'.format(ret))
        return ret

    def _show_delayed_notification(self, txt, delay=.75):
        if not (self._limited_height_mode or self._limited_width_mode):
            self._show_notification_with_delay(
                txt,
                delay=delay,
                mode_to_set=self.ws.operation_mode,
                callback_function=self.refreshBody
            )

    def _show_stations_history_playlist_modified(self):
        if self._limited_height_mode or self._limited_width_mode:
            msg = 'Playlist has been modified, cannot close it...'
            if self.player.isPlaying():
                self.log.write(msg=msg)
                self.player.threadUpdateTitle()
            else:
                self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)
        else:
            self._show_notification_with_delay(
                    txt='____Playlist has been modified____\n___Please save it and try again___',
                    delay=1.5,
                    mode_to_set=self.ws.operation_mode,
                    callback_function=self.refreshBody)

    def _show_no_station_history_notification(self):
        if self._limited_height_mode or self._limited_width_mode:
            msg = 'History is empty!!!'
            if self.player.isPlaying():
                self.log.write(msg=msg)
                self.player.threadUpdateTitle()
            else:
                self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)
        else:
            self._show_delayed_notification('___History is empty!!!___')

    def _show_first_station_history_notification(self):
        if self._limited_height_mode or self._limited_width_mode:
            msg = 'Already at first item!!!'
            if self.player.isPlaying():
                self.log.write(msg=msg)
                self.player.threadUpdateTitle()
            else:
                self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)
        else:
            self._show_delayed_notification('___Already at first item!!!___')

    def _show_last_station_history_notification(self):
        if self._limited_height_mode or self._limited_width_mode:
            msg = 'Already at last item!!!'
            if self.player.isPlaying():
                self.log.write(msg=msg)
                self.player.threadUpdateTitle()
            else:
                self.log.write(msg=msg, help_msg=True, suffix=self._status_suffix)
        else:
            self._show_delayed_notification('___Already at last item!!!___')

    def _show_station_pasted(self):
        self._show_delayed_notification('___Station pasted!!!___')

    def _show_nothing_to_paste(self):
        self._show_delayed_notification('___Nothing to paste!!!___')

    def _show_paste_failed(self):
        self._show_notification_with_delay(
            delay=1.5,
            txt='___Paste failed...___',
            mode_to_set=self.ws.operation_mode,
            callback_function=self.refreshBody)

    def _rename_playlist_from_playlist_mode(self,
                                            copy,
                                            open_file,
                                            last_history):
        it = self._search_sublist_last_item(
            self._cnf.playlists,
            self.new_filename)
        logger.error('DE it = {}'.format(it))
        if it > -1:
            self.selection = it
            self.selections[self.ws.PLAYLIST_MODE][0] = it
            self.playlist_selections[self.ws.PLAYLIST_MODE][0] = it
        else:
            if self.selections[self.ws.PLAYLIST_MODE][0] > 0:
                self.selections[self.ws.PLAYLIST_MODE][0] -= 1
                self.selection = self.selections[self.ws.PLAYLIST_MODE][0]
            self.playlist_selections[self.ws.PLAYLIST_MODE][0] = self.selections[self.ws.PLAYLIST_MODE][0]
        # self.ll('before')
        self._put_selection_in_the_middle(force=True)
        self.selections[self.ws.PLAYLIST_MODE][1] = self.startPos
        self.playlist_selections[self.ws.PLAYLIST_MODE][1] = self.startPos
        ''' fix playlist playing '''
        replace_playlist_in_history = ''
        if self.old_filename == self._playlist_in_editor:
            if copy:
                ''' copy opened playlist '''
                it = self._search_sublist_last_item(self._cnf.playlists, self.old_filename)
                logger.error('DE *** Looking for old_filename')
            else:
                ''' rename opened playlist '''
                it = self._search_sublist_last_item(self._cnf.playlists, self._playlist_in_editor)
                logger.error('DE *** Looking for self._playlist_in_editor')
                ''' replace playlist in history '''
                replace_playlist_in_history = self._playlist_in_editor
        else:
            ''' copy or raname random playlist '''
            it = self._search_sublist_last_item(self._cnf.playlists, self._playlist_in_editor)
            logger.error('DE *** Looking for self._playlist_in_editor')
            if not copy:
                ''' replace playlist in history '''
                replace_playlist_in_history = self.old_filename
        self.selections[self.ws.PLAYLIST_MODE][2] = it
        self.playlist_selections[self.ws.PLAYLIST_MODE][2] = it
        self.playing = it
        if not open_file:
            self.refreshBody()
        # logger.error('DE replace_playlist_in_history = {}'.format(replace_playlist_in_history))
        # logger.error('replace_playlist_in_history = {}'.format(replace_playlist_in_history))
        if replace_playlist_in_history:
            self._cnf.replace_playlist_history_items(
                    replace_playlist_in_history,
                    last_history
            )
            self._cnf.stations_history.rename_playlist(
                os.path.basename(replace_playlist_in_history)[:-4],
                last_history[2]
            )
        # self.ll('after')
        # logger.error('DE\n\n **** ps.p {}\n\n'.format(self._cnf._ps._p))
        # logger.error('DE self._playlist_in_editor = {}'.format(self._playlist_in_editor))
        if open_file:
            ret_it, ret_id, rev_ret_id = self._cnf.find_history_by_station_path(self.new_filename)
            logger.error('DE ret_it = {0}, ret_id = {1}, rev_ret_id = {2}'.format(ret_it, ret_id, rev_ret_id))
            self.ws.close_window()
            if rev_ret_id == 0:
                ''' return to opened playlist '''
                self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
                self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
                self._give_me_a_search_class(self.ws.operation_mode)
                if self.playing < 0:
                    self._put_selection_in_the_middle(force=True)
                    self.refreshBody()
                self._do_display_notify()
            else:
                ''' load new playlist '''
                if ret_id >= 0:
                    item = self._cnf.get_playlist_history_item(ret_id)
                    self._cnf.add_to_playlist_history(*item)
                    logger.error('DE\n\n **** after adding playlist to history ps.p {}\n\n'.format(self._cnf._ps._p))
                    self._open_playlist_from_history(from_rename_action=True)
                    if self.playing > -1:
                        self.selection = self.playing
                        self._put_selection_in_the_middle()
                    logger.error('DE playlist found: {0} at {1}'.format(item, ret_id))
                    self.refreshBody()
                    #self.active_stations = self.rename_stations
                    self._set_active_stations()
                    self._set_rename_stations()
                    logger.error('DE\n\n **** after open playlist from history ps.p {}\n\n'.format(self._cnf._ps._p))
                else:
                    self._cnf.add_to_playlist_history(*last_history)
                    logger.error('DE\n\n **** after addig playlist to history ps.p {}\n\n'.format(self._cnf._ps._p))
                    self._open_playlist_from_history(from_rename_action=True)
                    if self.playing > -1:
                        self.selection = self.playing
                        self._put_selection_in_the_middle()
                    if self.selection >= self.number_of_items:
                        self.selection = self.number_of_items - 1
                        if self.selection < 0:
                            self.selection = 0
                        self._put_selection_in_the_middle()

                self.refreshBody()
                self.playlist_selections[self.ws.NORMAL_MODE] = [self.selection, self.startPos, self.playing]
                self.selections[self.ws.NORMAL_MODE][:-1] = self.playlist_selections[self.ws.NORMAL_MODE][:]
                self.selections[self.ws.NORMAL_MODE][-1] = self.stations
                last_history[3:6] = self.playlist_selections[self.ws.NORMAL_MODE][:]
                ''' remove new playlist and re-add it with
                    correct values (selection, startPos, playing)
                '''
                self._cnf.remove_from_playlist_history()
                self._cnf.add_to_playlist_history(*last_history)

    def _rename_playlist_from_register_mode(self, copy, open_file, last_history):
        if self._cnf.playlists:
            ''' holds registers '''
            no_more_registers = False
            if self.selection >= len(self._cnf.playlists):
                self.selection -= 1
                self.selections[self.ws.PLAYLIST_MODE][0] = self.selection
                self.playlist_selections[self.ws.PLAYLIST_MODE][0] = self.selection
                if self.selection < self.startPos:
                    self.startPos = self.selection
        else:
            no_more_registers = True
            logger.error('DE no more playlists....')
            ''' if no more register files exist,
            go back to playlist view '''
            self._cnf._open_register_list = False
            ''' make first register selected
            for when a register is created '''
            self.playlist_selections[self.ws.REGISTER_MODE] = [0, 0, -1]
            self.selections[self.ws.REGISTER_MODE][:-1] = [0, 0, -1]
            self._cnf.just_read_playlists()
            self.selections[self.ws.PLAYLIST_MODE][-1] = self._cnf.playlists
            self._reload_playlists(refresh=False)
        it = self._search_sublist_last_item(self._cnf.playlists, self.new_filename)
        logger.error('DE it = {}'.format(it))
        if it > -1:
            self.selections[self.ws.PLAYLIST_MODE][0] = it
            self.playlist_selections[self.ws.PLAYLIST_MODE][0] = it
        else:
            if self.selections[self.ws.PLAYLIST_MODE][0] > 0:
                self.selections[self.ws.PLAYLIST_MODE][0] -= 1
            self.playlist_selections[self.ws.PLAYLIST_MODE][0] = self.selections[self.ws.PLAYLIST_MODE][0]
        if no_more_registers:
            self.selection, startPos, _ = self.playlist_selections[self.ws.PLAYLIST_MODE]
            self._put_selection_in_the_middle(force=True)
            self.selections[self.ws.PLAYLIST_MODE][1] = startPos
            self.playlist_selections[self.ws.PLAYLIST_MODE][1] = startPos
            # logger.error('DE selections = {}'.format(self.selections))
        # self.ll('final')
        self._reload_playlists()
        if open_file:
            self._cnf.add_to_playlist_history(*last_history)

            self.ws.close_window()
            self.active_stations = self.rename_stations
            logger.error('DE\n\n **** before open playlist from history ps.p {}\n\n'.format(self._cnf._ps._p))
            self._open_playlist_from_history(from_rename_action=True)
            if self.playing > -1:
                self.selection = self.playing
                self._put_selection_in_the_middle()
            if self.selection >= self.number_of_items:
                self.selection = self.number_of_items - 1
                if self.selection < 0:
                    self.selection = 0
                self._put_selection_in_the_middle()

        self.refreshBody()
        if open_file:
            self.playlist_selections[self.ws.NORMAL_MODE] = [self.selection, self.startPos, self.playing]
            self.selections[self.ws.NORMAL_MODE][:-1] = self.playlist_selections[self.ws.NORMAL_MODE][:]
            self.selections[self.ws.NORMAL_MODE][-1] = self.stations
            last_history[3:6] = self.playlist_selections[self.ws.NORMAL_MODE][:]
            ''' remove new playlist and re-add it with
                correct values (selection, startPos, playing)
            '''
            self._cnf.remove_from_playlist_history()
            self._cnf.add_to_playlist_history(*last_history)
        # self.ll('before return')
        logger.error('DE\n\n **** ps.p {}\n\n'.format(self._cnf._ps._p))
        #self.refreshBody()

    def _rename_playlist_from_normal_mode(self, copy, open_file, create, last_history):
        old_file_is_reg = True if os.path.basename(self.old_filename).startswith('register_') else False
        # logger.error('DE\n\n **** {}'.format(self._cnf._ps._p))

        # logger.error('DE title = {}'.format(self._cnf.station_title))
        if copy:
            # logger.error('DE rename playlist NORMAL_MODE: copy file')
            if open_file:
                # logger.error('DE rename playlist NORMAL_MODE: open file and copy')
                self._cnf.add_to_playlist_history(*last_history)
        else:
            # logger.error('DE rename playlist NORMAL_MODE: not a copy')
            if create and open_file:
                self._cnf.stations = []
                self.stations = self._cnf.stations
                self.number_of_items = 0
                self._cnf.add_to_playlist_history(*last_history)
            self._cnf.replace_playlist_history_items(
                    self.old_filename,
                    last_history)
            self._cnf.stations_history.rename_playlist(
                os.path.basename(self.old_filename)[:-4],
                last_history[2]
            )
        # logger.error('DE\n\n **** ps.p {}\n\n'.format(self._cnf._ps._p))

        self.refreshBody()
        self._cnf.remove_playlist_history_duplicates()
        # self.ll('before')
        self._find_playlists_after_rename(self.old_filename,
                                          self.new_filename,
                                          copy,
                                          open_file,
                                          old_file_is_reg)
        if not copy:
            self._cnf.replace_playlist_history_items(
                    self.old_filename,
                    last_history)
        # self.ll('after')

    def _reload_playlists(self, refresh=True):
        old_playlist = self._cnf.playlists[self.selection][0]
        self.number_of_items, self.playing = self.readPlaylists()
        if self._cnf.open_register_list:
            oper_mode = self.ws.REGISTER_MODE
            ''' refresh reference '''
        else:
            oper_mode = self.ws.PLAYLIST_MODE
        self.stations = self._cnf.playlists
        if self.playing == -1 or self.number_of_items == 0:
            self.selections[oper_mode] = [0, 0, -1, self._cnf.playlists]
        else:
            self.selections[oper_mode] = [self.selection, self.startPos, self.playing, self._cnf.playlists]
        # self.ll('r')
        if self.number_of_items > 0:
            ''' refresh reference '''
            self.stations = self._cnf.playlists
        if refresh and (self.number_of_items > 0 \
                or self._cnf.open_register_list):
            self.refreshBody()

    def _html_volume_up(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            if self.player.muted:
                return '<div class="alert alert-danger">Player is <b>muted</b>; command not applicable</div>'
            elif self.player.paused:
                return '<div class="alert alert-danger">Player is <b>paused</b>; command not applicable</div>'
            else:
                self.player.volumeUp()
                return '<div class="alert alert-success">Volume <b>increased</b>!</div>'
        else:
            return '<div class="alert alert-danger">Player is <b>stopped</b>; command not applicable</div>'

    def _volume_up(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            if not self.player.paused:
                self.player.volumeUp()
            else:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Volume adjustment inhibited because playback is paused')
        else:
            if self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
                self.ws.close_window()
                self.refreshBody()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Volume adjustment inhibited because playback is off')

    def _html_volume_down(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            if self.player.muted:
                return '<div class="alert alert-danger">Player is <b>muted</b>; command not applicable</div>'
            elif self.player.paused:
                return '<div class="alert alert-danger">Player is <b>paused</b>; command not applicable</div>'
            else:
                self.player.volumeDown()
                return '<div class="alert alert-success">Volume <b>decreased</b>!</div>'
        else:
            return '<div class="alert alert-danger">Player is <b>stopped</b>; command not applicable</div>'

    def _volume_down(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            if not self.player.paused:
                self.player.volumeDown()
            else:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Volume adjustment inhibited because playback is paused')
        else:
            if self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
                self.ws.close_window()
                self.refreshBody()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Volume adjustment inhibited because playback is off')

    def _html_volume_mute(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            self.player.toggleMute()
            return '<div class="alert alert-success">Player muted state <b>toggled!</b></div>'
        else:
            return '<div class="alert alert-danger">Player is <b>stopped</b>; command not applicable</div>'

    def _volume_mute(self):
        if self.player.isPlaying():
            if self.player.playback_is_on:
                self.player.toggleMute()
        else:
            if self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
                self.ws.close_window()
                self.refreshBody()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Muting inhibited because playback is off')

    def _html_volume_save(self):
        if self.player.isPlaying() and \
                self.player.playback_is_on:
            if self.player.muted:
                return '<div class="alert alert-danger">Player is <b>muted!</b></div>'
            else:
                ret_string = self.player.save_volume()
                if ret_string:
                    self.log.write(msg=ret_string)
                    self.player.threadUpdateTitle()
                    return '<div class="alert alert-success">Volume <b>saved!</b></div>'
                return '<div class="alert alert-danger">Volume <b>not saved!</b></div>'
        else:
            return '<div class="alert alert-danger">Player is <b>stopped</b>; command not applicable</div>'

    def _volume_save(self):
        if self.player.isPlaying():
            if self.player.playback_is_on:
                ret_string = self.player.save_volume()
                if ret_string:
                    self.log.write(msg=ret_string)
                    self.player.threadUpdateTitle()
        else:
            if self.ws.operation_mode in self.ws.PASSIVE_WINDOWS:
                self.ws.close_window()
                self.refreshBody()
            if logger.isEnabledFor(logging.INFO):
                logger.info('Volume save inhibited because playback is off')

    def _find_playlists_after_rename(self, old_file, new_file, copy, open_file, old_file_is_reg):
        ''' Find new selection, startPos, playing after a rename action

        '''
        base_old_file = os.path.basename(old_file)
        if old_file_is_reg:
            ''' work on registers '''
            self.selections[self.ws.REGISTER_MODE][:-1] = self.playlist_selections[self.ws.REGISTER_MODE][:]
            if not copy:
                self._find_renamed_selection(self.ws.REGISTER_MODE,
                                             self._cnf.registers_dir,
                                             old_file)
            search_path = self._cnf.stations_dir
            search_file = new_file
        else:
            ''' work on playlists '''
            search_path = self._cnf.stations_dir
            search_file = new_file if ((copy and open_file) or (not copy)) else old_file
            #if copy:
            #    search_file = new_file if open_file else old_file
            #else:
            #    search_file = new_file

        # self.ll('_find_playlists_after_rename(): common')
        logger.error('DE playlist_selection = {}'.format(self.playlist_selections))
        ''' set playlist selections for ' action '''
        self.playlist_selections[self.ws.PLAYLIST_MODE] = self.selections[self.ws.PLAYLIST_MODE][:-1][:]
        self.playlist_selections[self.ws.REGISTER_MODE] = self.selections[self.ws.REGISTER_MODE][:-1][:]
        logger.error('DE playlist_selection = {}'.format(self.playlist_selections))

        ''' Go on and fix playlists' selections '''
        self._find_renamed_selection(self.ws.PLAYLIST_MODE, search_path, search_file)

    def _find_renamed_selection(self, mode, search_path, search_file):
        ''' Calculates selection and startPos and playing parameters
        for a renamed station

        Parameters
        ----------
        mode
            Either PLAYLIST_MODE or REGISTER_MODE
        search_path
           self._cnf.stations_dir   or    self._cnf.registers_dir, for mode
           PLAYLIST_MODE            or    REGISTER_MODE
        search_file
            Target file of a rename action (full path)

        Sets
        ----
            self.selections[mode]
        '''
        # self.ll('_find_renamed_selection(): before')
        files = glob.glob(path.join(search_path, '*.csv'))
        if files:
            files.sort()
            try:
                sel = files.index(search_file)
            except:
                # TODO set max - 1?
                self.selections[mode][1:-1] = [0, -1]
                if self.selections[mode][0] >= len(files):
                    self.selections[mode][0] = len(files) - 1
                self.playlist_selections[self.ws.PLAYLIST_MODE] = self.selections[self.ws.PLAYLIST_MODE][:-1][:]
                # self.ll('_find_renamed_selection(): after not found')
                return
            self.selections[mode][0] = self.selections[mode][2] = sel

            ''' Set startPos '''
            if len(files) - 1 < self.bodyMaxY:
                self.selections[mode][1] = 0
            else:
                if self.selections[mode][0] < self.bodyMaxY:
                    self.selections[mode][1] = 0
                elif self.selections[mode][0] >= len(files) - self.bodyMaxY:
                    self.selections[mode][1] = len(files) - self.bodyMaxY
                else:
                    self.selections[mode][1] = self.selections[mode][0] - int(self.bodyMaxY / 2)
            # self.ll('_find_renamed_selection(): after')
        else:
            self.selections[mode][:-1] = [0, 0, -1]
            # self.ll('_find_renamed_selection(): reset parameters')
        self.playlist_selections[self.ws.PLAYLIST_MODE] = self.selections[self.ws.PLAYLIST_MODE][:-1][:]

    def _redisplay_stations_and_playlists(self):
        if self._limited_height_mode:
            return

        # self.bodyWin.erase()
        if self.maxY > 2:
            self.outerBodyWin.box()
        try:
            self.bodyWin.move(1, 1)
            self.bodyWin.move(0, 0)
        except:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('====---- cursor move failed ----====')
        self._print_body_header()
        pad = len(str(self.startPos + self.bodyMaxY))

        if self.number_of_items == 0:
            if self._cnf.browsing_station_service:
                ''' we have to fill the screen with emplty lines '''
                line = self.__displayBodyLine(0, pad, None, return_line = True)
                for n in range(0, self.bodyMaxY + 1):
                    try:
                        self.bodyWin.addstr(n, 0, line, curses.color_pair(5))
                    except:
                        pass
                pass
            else:
                self.bodyWin.erase()
        else:
            for lineNum in range(self.bodyMaxY):
                i = lineNum + self.startPos
                if i < len(self.stations):
                    if not self._cnf.browsing_station_service and \
                            self.ws.operation_mode == self.ws.NORMAL_MODE:
                        try:
                            self.bodyWin.move(lineNum, 0)
                            self.bodyWin.clrtoeol()
                        except:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('====---- clear line move failed----====')
                    self.__displayBodyLine(lineNum, pad, self.stations[i])
                else:
                    if self._cnf.browsing_station_service:
                        ''' display browser empty lines (station=None) '''
                        line = self.__displayBodyLine(0, pad, None, return_line = True)
                        if self._cnf.browsing_station_service:
                            for n in range(i+1, self.bodyMaxY + 1):
                                try:
                                    self.bodyWin.addstr(lineNum, 0, line, curses.color_pair(5))
                                except:
                                    pass
                                lineNum += 1
                        break
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('clearing window from line {} to end.'.format(i))
                        try:
                            self.bodyWin.move(i, 0)
                            self.bodyWin.clrtobot()
                        except:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('====---- clear to end of window failed----====')
                        break

        if self._cnf.browsing_station_service:
            if self._cnf.internal_header_height > 0:
                sort_column_color = 4
                highlight, headers = self._cnf.online_browser.get_internal_header(pad, self.bodyMaxX)
                # logger.error('DE highlight = {}'.format(highlight))
                # logger.error('DE headers = {}'.format(headers))
                for i, a_header in enumerate(headers):
                    if highlight == -2:
                        self.outerBodyWin.addstr(i + 1, 1, a_header[0][0], curses.color_pair(2))
                        self.outerBodyWin.addstr(i + 1, pad + 2, a_header[0][1], curses.color_pair(sort_column_color))
                    else:
                        self.outerBodyWin.addstr(i + 1, 1, a_header[0][0], curses.color_pair(2))
                        self.outerBodyWin.addstr(i + 1, pad + 2, a_header[0][1], curses.color_pair(2))
                    column_separator = a_header[1]
                    column_name = a_header[2]
                    # logger.error('DE {}'.format(column_separator))
                    # logger.error('DE {}'.format(column_name))
                    ''' clear empty space after "Name" '''
                    to_clear_start = pad + 2 + len(a_header[0][1])
                    try:
                        self.outerBodyWin.addstr((column_separator[0] - to_clear_start) * ' ', curses.color_pair(2))
                    except:
                        pass
                    for j, col in enumerate(column_separator):
                        if version_info < (3, 0):
                            self.outerBodyWin.addstr(i + 1, col + 2, u'│'.encode('utf-8', 'replace'), curses.color_pair(13))
                        else:
                            self.outerBodyWin.addstr(i + 1, col + 2, '│', curses.color_pair(13))
                        try:
                            if j == highlight:
                                self.outerBodyWin.addstr(column_name[j], curses.color_pair(sort_column_color))
                            else:
                                self.outerBodyWin.addstr(column_name[j], curses.color_pair(2))
                        except:
                            pass
        self.outerBodyWin.touchwin()
        self.outerBodyWin.refresh()
        self.bodyWin.touchwin()
        self.bodyWin.refresh()

    def _redisplay_config(self):
        self._config_win.parent = self.outerBodyWin
        self._config_win.init_config_win()
        self._config_win.refresh_config_win()

    def _redisplay_player_select_win_refresh_and_resize(self):
        if self._config_win:
            if not self._config_win.too_small:
                self._player_select_win.refresh_and_resize(self.outerBodyMaxY, self.outerBodyMaxX)
        else:
            self._player_select_win.set_parrent(self.bodyWin)

    def _redisplay_encoding_select_win_refresh_and_resize(self):
        if not self._config_win.too_small:
            self._encoding_select_win.refresh_and_resize(self.outerBodyMaxY, self.outerBodyMaxX)

    def _playlist_select_paste_win_refresh_and_resize(self):
        self._playlist_select_win.refresh_and_resize(self.bodyWin.getmaxyx())

    def _playlist_select_win_refresh_and_resize(self):
        if not self._config_win.too_small:
            self._playlist_select_win.refresh_and_resize(self.bodyWin.getmaxyx())

    def _redisplay_encoding_select_win_refresh_and_resize(self):
        if self._config_win:
            if not self._config_win.too_small:
                self._encoding_select_win.refresh_and_resize(self.outerBodyMaxY, self.outerBodyMaxX)
        else:
            self._encoding_select_win.refresh_and_resize(self.outerBodyMaxY, self.outerBodyMaxX)

    def _redisplay_station_select_win_refresh_and_resize(self):
        if not self._config_win.too_small:
            self._station_select_win.refresh_and_resize(self.bodyWin.getmaxyx())

    def _redisplay_print_save_modified_playlist(self):
        self._print_save_modified_playlist(self.ws.operation_mode)

    def _redisplay_search_show(self):
        self.search.show(self.outerBodyWin, repaint=True)

    def _redisplay_theme_mode(self):
        if self.ws.window_mode == self.ws.CONFIG_MODE and \
                self._config_win.too_small:
            return
        # if self._cnf.locked:
        #     self._theme_selector = None
        #     self.ws.close_window()
        #     return
        self._theme_selector.parent = self.outerBodyWin
        self._theme_selector._showed = False
        self._theme_selector._start_pos = 0
        self._theme_selector.show(touch_selection=False)
        return
        self._show_theme_selector()
        if self.theme_forced_selection:
            self._theme_selector.set_theme(self.theme_forced_selection)

    def _redisplay_ask_to_create_new_theme(self):
        if logger.isEnabledFor(logging.ERROR):
            logger.error('DE self.ws.previous_operation_mode = {}'.format(self.ws.previous_operation_mode))
        self._theme_selector.parent = self.outerBodyWin
        if self.ws.previous_operation_mode == self.ws.CONFIG_MODE:
            self._show_theme_selector_from_config()
        else:
            self._show_theme_selector()
        if self.theme_forced_selection:
            self._theme_selector.set_theme(self.theme_forced_selection)
        self._print_ask_to_create_theme()

    def _load_renamed_playlist(self, a_file, old_file, is_copy):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Opening renamed playlist: "{}"'.format(a_file))
        ret = self._cnf.read_playlist_file(stationFile=a_file)
        if ret == -1:
            self._print_playlist_load_error()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Error loading playlist: "{}"'.format(self.stations[self.selection][-1]))
            return
        elif ret == -2:
            self._print_playlist_not_found_error()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Playlist not found: "{}"'.format(self.stations[self.selection][-1]))
            return
        elif ret == -7:
            self._print_playlist_recovery_error()
            return
        else:
            self._playlist_in_editor = a_file
            self._playlist_error_message = ''
            self.number_of_items = ret
            # self.ll('ENTER')
            self.ws.close_window()
            while self.ws.operation_mode != self.ws.NORMAL_MODE:
                self.ws.close_window()
            self.selection, self.startPos, self.playing, self.stations = self.selections[self.ws.operation_mode]
            self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
            self._give_me_a_search_class(self.ws.operation_mode)
            if self.playing < 0:
                self._put_selection_in_the_middle(force=True)
                self.refreshBody()
            # logger.error('DE path = {}'.format(self._cnf.station_path))
            # logger.error('DE station = {}'.format(self._cnf.station_file_name))
            # logger.error('DE title = {}\n'.format(self._cnf.station_title))
            self._cnf.set_playlist_elements(a_file)
            if is_copy:
                self._cnf.add_to_playlist_history(
                        station_path=a_file,
                        station_title=self._cnf.station_title,
                        startPos=self.startPos,
                        selection=self.selection,
                        playing=self.playing)
            # logger.error('DE path = {}'.format(self._cnf.station_path))
            # logger.error('DE station = {}'.format(self._cnf.station_file_name))
            # logger.error('DE title = {}\n'.format(self._cnf.station_title))

    def _search_sublist__stem(self, a_list, a_search):
        return self._search_sublist(a_list, 0, a_search)

    def _search_sublist_last_item(self, a_list, a_search):
        return self._search_sublist(a_list, -1, a_search)

    def _search_sublist(self, a_list, ind, a_search):
        k = [r[ind] for r in a_list]
        try:
            return k.index(a_search)
        except ValueError as e:
            return -1

    def _show_http_connection(self):
        self._connection_type_edit.show(parent=self.outerBodyWin)

    def set_param_set_by_id(self, a_param_id=0):
        if a_param_id >= len(self._cnf.params[self._cnf.PLAYER_NAME]):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('No parameter set {0} for player "{1}" (max={2})'.format(
                    a_param_id,
                    self._cnf.PLAYER_NAME,
                    len(self._cnf.params[self._cnf.PLAYER_NAME]) - 1
                ))
            return False
        else:
            self._cnf.backup_player_params[1][0] = a_param_id
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Activating parameter No {0} for player "{1}"'.format(a_param_id, self._cnf.PLAYER_NAME))
            return True

    def toggle_titles_logging(self):
        self._cnf.titles_log.configure_logger(titles=not self._cnf.titles_log.log_titles)

    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    Windows only section
    '''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''''
    def _register_signals_handlers(self):
        if platform.startswith('win'):
            import win32console, win32gui, win32con, win32api
            ''' disable close button
            import win32console, win32gui, win32con, win32api

                We do not need it any more....

            hwnd = win32console.GetConsoleWindow()
            if hwnd:
                hMenu = win32gui.GetSystemMenu(hwnd, 0)
                if hMenu:
                    try:
                        win32gui.DeleteMenu(hMenu, win32con.SC_CLOSE, win32con.MF_BYCOMMAND)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('SetConsoleCtrlHandler: close button disabled')
                    except:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('SetConsoleCtrlHandler: failed to disable close button')
            '''

            ''' install handlers for exit / close signals '''
            try:
                result = win32api.SetConsoleCtrlHandler(self._windows_signal_handler, True)
                if logger.isEnabledFor(logging.DEBUG):
                    if result == 0:
                        logger.debug('SetConsoleCtrlHandler: Failed to register!!!')
                    else:
                        logger.debug('SetConsoleCtrlHandler: Registered!!!')
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('SetConsoleCtrlHandler: Failed to register (with Exception)!!!')

            ''' Trying to catch Windows log-ogg, reboot, halt
                No luck....
            '''
            # import signal
            # try:
            #     signal.signal(signal.SIGINT, self._windows_signal_handler)
            # except:
            #     if logger.isEnabledFor(logging.DEBUG):
            #         logger.debug('SetConsoleCtrlHandler: Signal SIGINT failed to register (with Exception)!!!')

            # try:
            #     signal.signal(signal.SIGINT, self._windows_signal_handler)
            # except:
            #     if logger.isEnabledFor(logging.DEBUG):
            #         logger.debug('SetConsoleCtrlHandler: Signal SIGINT failed to register (with Exception)!!!')

        else:
            self.handled_signals = {
                'SIGHUP': signal.SIGHUP,
                'SIGTERM': signal.SIGTERM,
                'SIGKIL': signal.SIGKILL,
            }
            self.def_signal_handlers = {}
            try:
                for a_sig in self.handled_signals.keys():
                    self.def_signal_handlers[a_sig] = signal.signal(
                        self.handled_signals[a_sig],
                        self._linux_signal_handler
                    )
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('SetConsoleCtrlHandler: Handler for signal {} registered'.format(a_sig))
            except:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('SetConsoleCtrlHandler: Failed to register handler for signal {}'.format(a_sig))

    def _linux_signal_handler(self, a_signal, a_frame):
        logger.error('DE ----==== _linux_signal_handler  ====----')

        if self._cnf.titles_log.titles_handler:
            logger.critical('=== Logging stopped')
        search_cls = [x for x in self._search_classes if x is not None]
        for n in range(len(search_cls)):
            search_cls[n].save_search_history()
            search_cls[n] = None
        self._cls_update_stations = None
        self.detect_if_player_exited = False
        self.log._stop_desktop_notification_thread = True
        self.player.stop_update_notification_thread = True
        self.player.stop_win_vlc_status_update_thread = True
        if self.player:
            # ok
            self.detect_if_player_exited = False
            self.stopPlayer(
                show_message=False,
                reset_playing=False
            )
        if self._system_asked_to_terminate:
            return
        self._system_asked_to_terminate = True
        if logger.isEnabledFor(logging.INFO):
            # logger.info('System asked me to terminate (signal: {})!!!'.format(list(self.handled_signals.keys())[list(self.handled_signals.values()).index(a_signal)]))
            logger.info('My terminal got closed... Terminating...')
        self._force_exit = True
        self.stop_update_notification_thread = True
        self.player.stop_timeout_counter_thread = True
        if self.ws.operation_mode != self.ws.PLAYLIST_MODE:
            if self._cnf.dirty_playlist:
                self._cnf.save_playlist_file()
        if self._cnf.browsing_station_service:
            if self._cnf.online_browser:
                if self._cnf.online_browser.browser_config.is_config_dirty:
                    self._cnf.online_browser.save_config()
                    sel._cnf.online_browser = None
        self.player.close()
        self._cnf.save_config()
        self._cnf.remove_session_lock_file()
        for a_sig in self.handled_signals.keys():
            try:
                signal.signal(
                    self.handled_signals[a_sig],
                    self.def_signal_handlers[a_sig]
                )
            except:
                pass
        while self._remote_control_server is not None:
            ret, _ = self._remote_control_server.close_server()
            if ret:
                self._remote_control_server = None
        self._wait_for_threads()

    def _windows_signal_handler(self, event):
        ''' windows signal handler
            https://danielkaes.wordpress.com/2009/06/04/how-to-catch-kill-events-with-python/
        '''
        search_cls = [x for x in self._search_classes if x is not None]
        for n in range(len(search_cls)):
            search_cls[n].save_search_history()
            search_cls[n] = None
        if self._cnf.titles_log.titles_handler:
            logger.critical('=== Logging stopped')
        self.log._stop_desktop_notification_thread = True
        import win32con, win32api
        if event in (win32con.CTRL_C_EVENT,
                     win32con.CTRL_LOGOFF_EVENT,
                     win32con.CTRL_BREAK_EVENT,
                     win32con.CTRL_SHUTDOWN_EVENT,
                     win32con.CTRL_CLOSE_EVENT,
                     signal.SIGINT,
                     signal.SIGBREAK):
            if self._system_asked_to_terminate:
                return
            self._system_asked_to_terminate = True
            if logger.isEnabledFor(logging.INFO):
                logger.info('My console window got closed... Terminating...')
            self._force_exit = True
            self.player.close_from_windows()
            self._cnf.save_config()
            self._wait_for_threads()
            self._cnf.remove_session_lock_file()
            if self.ws.operation_mode != self.ws.PLAYLIST_MODE:
                if self._cnf.dirty_playlist:
                    self._cnf.save_playlist_file()
            try:
                win32api.SetConsoleCtrlHandler(self._windows_signal_handler, False)
            except:
                pass
        return False

    def _add_station_to_stations_history(self):
        # TODO: Do I need it?
        # TODO: Do I set it?
        self._register_to_open = ''
        playlist = self._cnf.station_title
        station = self.stations[self.selection]
        sel = self.selection
        self._cnf.stations_history.add(self._cnf.station_file_name[:-4], self.stations[self.playing][0], self.playing)

    def _load_playlist_and_station_from_station_history(self, h_item, func):
        # logger.info('h_item = {}'.format(h_item))
        num = -1
        current_playlist = self._cnf.station_file_name[:-4]
        if h_item[0] == '' or h_item[1] == '' or \
                h_item[0] == h_item[1] or \
                h_item[1].startswith('register_') or \
                h_item[-1] < 0 or \
                (h_item[-1] >= self.number_of_items and current_playlist == h_item[0]):
            if logger.isEnabledFor(logging.ERROR):
                logger.error('\n===============\nInvalid h_item: "{0}"\nNumber of stations = {1}\n==============='.format(h_item, self.number_of_items))
            func()
            return
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Activating station history item: {}'.format(h_item))

        if current_playlist == h_item[0] or \
                    h_item[0] == 'Online Browser':
            ''' I am moving within the loaded playlist '''
            if self.stations[h_item[-1]][0] == h_item[1]:
                ''' station found '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Station history item found in current playlist at: {}'.format(num))
                num = h_item[-1]
                if num >= self.number_of_items:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('station num is not in playlist...')
                    func()
                    return
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Scanning other playlist for station history item: {}'.format(num))
                ''' I have to scan the playlist'''
                num = self._scan_playlist_for_station(self.stations, h_item[-1], h_item[1])
                if num == -1:
                    ''' station not found  '''
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Station "{}" not found!'.format(h_item[1]))
                    ''' Continue going through history items '''
                    func()
                    return

        else:
            ''' I have to load a new playlist '''
            if self._cnf.dirty_playlist:
                self._cnf.stations_history.restore_index(func)
                self._show_stations_history_playlist_modified()
                return

            ret = 0
            if self._register_to_open:
                # logger.error('register_to_open = {}'.format(self._register_to_open))
                stationFile, ret = self._cnf._get_register_filename_from_register()
                self._is_register = True
            else:
                stationFile, ret = self._cnf._get_playlist_abspath_from_data(stationFile=h_item[0])
                self._is_register = False
            if ret > 0:
                ''' Continue going through history items '''
                func()
                return

            ''' playlist loaded and validated '''
            num = self._open_playlist_and_station_from_station_history(stationFile, h_item)
            if num == -1:
                ''' Continue going through history items '''
                func()
            return

        try:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station "{0}" found at {1}'.format(h_item[1], num))
        except UnicodeEncodeError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station found at {}'.format(num))

        self.setStation(num)
        if self.number_of_items > 0:
            self.playSelection()
            #self._goto_playing_station(changing_playlist=False)
            self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
        self.refreshBody()
        self.selections[self.ws.NORMAL_MODE] = [
            self.selection,
            self.startPos,
            self.playing,
            self.stations
        ]
        self.saved_active_stations = [['', 0], ['', -1]]
        if self._limited_height_mode or self._limited_width_mode:
            logger.error('==== update body')
            self._print_limited_info()

    def _get_playlists_data_from_playlist_name(self, a_playlist):
        change_regs_too = False
        if self.selections[1][-1][0] == self.selections[2][-1][0]:
            change_regs_too = True
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Looking for playlist: {}'.format(a_playlist))
        found = -1
        for i, n in enumerate(self.selections[1][-1]):
            if n[0] == a_playlist:
                logger.error('Playlist found at {}'.format(i))
                found = i
                break
        if found > -1:
            self.selections[1][0] = self.selections[1][2] = found
            if found < self.bodyMaxY:
                self.selections[1][1] = 0
            elif found > self.number_of_items - self.bodyMaxY:
                self.selections[1][1] = len(self.selections[1][-1]) - self.bodyMaxY
            else:
                self.selections[1][1] = found - int(self.bodyMaxY / 2)

            if change_regs_too:
                self.selections[2][0] = self.selections[2][2] = found
                self.selections[2][1] = self.selections[1][1]

            self.playlist_selections[1][0] = self.selections[1][0]
            self.playlist_selections[1][1] = self.selections[1][1]
            self.playlist_selections[1][2] = self.selections[1][2]
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Playlist not found!')


    def _scan_playlist_for_station(self, stations, start, station_to_find):
        if logger.isEnabledFor(logging.DEBUG):
            logger.error('Scanning playlist...')
        up = down = 0
        num = -1
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('  checking start={0}: "{1}"'.format(start, stations[start]))
        if stations[start][0] == station_to_find:
            return start
        for i in range(start, -1, -1):
            up = i + 1
            down = i - 1
            if down > -1 :
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  checking down={0}: "{1}"'.format(down, stations[down]))
                if stations[down][0] == station_to_find:
                    num = down
                    break
            if up < self._cnf.number_of_stations:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  checking up={0}: "{1}"'.format(up, stations[up]))
                if stations[up][0] == station_to_find:
                    num = up
                    break
        up += 1
        down -= 1
        if num == -1 and down > -1:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station not found... Scanning to top...')
            for i in range(down, -1, -1):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  checking {0}: "{1}"'.format(i, stations[i]))
                if stations[i][0] == station_to_find:
                    num = i
                    break

        if num == -1 and up < self._cnf.number_of_stations:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Station not found... Scanning to bottom...')
            for i in range(up, self._cnf.number_of_stations - 1):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  checking {0}: "{1}"'.format(i, stations[i]))
                if stations[i][0] == station_to_find:
                    num = i
                    break

        return num

    def _open_and_check_station_in_playlist(self, playlist_file, start, station_to_find):
        ''' read a _playlist and check if a station is in it

            return num = index of file in stations' list
                   or -1 if it fails

            stations are returned in self._reading_stations
        '''
        num = -1
        self._reading_stations = []
        with open(playlist_file, 'r', encoding='utf-8') as cfgfile:
            try:
                for row in csv.reader(filter(lambda row: row[0]!='#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    try:
                        name, url = [s.strip() for s in row]
                        self._reading_stations.append([name, url, '', ''])
                    except:
                        try:
                            name, url, enc = [s.strip() for s in row]
                            self._reading_stations.append([name, url, enc, ''])
                        except:
                            name, url, enc, onl = [s.strip() for s in row]
                            self._reading_stations.append([name, url, enc, onl])
            except:
                self._reading_stations = []
                return num


        return self._scan_playlist_for_station(self._reading_stations, start, station_to_find)

    def _can_receive_remote_command(self):
        if self.ws.window_mode in (
            self.ws.NORMAL_MODE,
        ):
            return True
        else:
            return False

    def _start_remote_control_server(self):
        self._remote_control_server = PyRadioServer(
            bind_ip=self._cnf.active_remote_control_server_ip,
            bind_port=int(self._cnf.active_remote_control_server_port),
            commands={
                '/volumesave': self._volume_save,
                '/html_volumesave': self._html_volume_save,
                '/volumeup': self._volume_up,
                '/html_volumeup': self._html_volume_up,
                '/volumedown': self._volume_down,
                '/html_volumedown': self._html_volume_down,
                '/mute': self._volume_mute,
                '/html_mute': self._html_volume_mute,
                '/histprev': self._stations_history_previous,
                '/html_histprev': self._html_stations_history_previous,
                '/histnext': self._stations_history_next,
                '/html_histnext': self._html_stations_history_next,
                '/previous': self._play_previous_station,
                '/html_previous': self._html_play_previous_station,
                '/next': self._play_next_station,
                '/html_next': self._html_play_next_station,
                '/stop': self._stop_player,
                '/html_stop': self._html_stop_player,
                '/start': self._start_player,
                '/html_start': self._html_start_player,
                '/jump': self._jump_and_play_selection,
                'open_history': self._open_playlist_and_station_from_station_history,
                '/log': self._toggle_titles_logging,
                '/html_log': self._html_toggle_titles_logging,
                '/like': self._tag_a_title,
                '/html_like': self._html_tag_a_title,
                '/title': self._html_song_title,
                '/html_info': self._html_info,
                '/text_info': self._text_info,
                '/html_is_stopped': self._html_is_player_stopped,
                '/html_init': self._html_init_song_title,
                '/volume': self._get_text_volume,
                '/set_volume': self._set_text_volume,
            }
        )
        if not self._remote_control_server.has_netifaces:
            self._remote_control_server = None
            self._no_netifaces = True
            return
        self._remote_control_server_thread = threading.Thread(
            target=self._remote_control_server.start_remote_control_server,
            args=(
                lambda: self._cnf,
                lambda: self.selections,
                lambda: (self.selection, self.playing),
                lambda: self._playlist_in_editor,
                lambda: self.player.muted,
                self._can_receive_remote_command,
                self._print_remote_control_server_error,
                self._print_remote_control_server_dead_error,
                lambda: self.log.song_title,
                self._server_send_lock
            )
        )
        '''
        making this a daemonic thread, to make sure it always
        terminates at program exit.
        If that causes problems, commane the following line
        and uncomment lines in ctrl_c_handler()
        '''
        # self._remote_control_server_thread.daemon = True
        self._remote_control_server_thread.start()

    def _stop_remote_control_server(self):
        if self._remote_control_server:
            ret = self._remote_control_server.close_server()
            while not ret:
                sleep(.15)
                ret = self._remote_control_server.close_server()
        self._remote_control_server = self._remote_control_server_thread = None

    def _restart_remote_control_server(self):
        self._stop_remote_control_server()
        self._cnf._remote_control_server = self._cnf._remote_control_server_thread = None
        self._cnf.active_remote_control_server_ip = self._cnf.remote_control_server_ip
        self._cnf.active_remote_control_server_port = self._cnf.remote_control_server_port
        self._start_remote_control_server()

    def _open_playlist_and_station_from_station_history(self, stationFile, h_item):
        num = self._open_and_check_station_in_playlist(stationFile, h_item[-1], h_item[1])
        if num == -1:
            return
        self._set_rename_stations()
        self._cnf.stations = list(self._reading_stations)
        self._reading_stations = []
        self.stations = self._cnf.stations
        self._playlist_in_editor = stationFile
        self.number_of_items = len(self.stations)
        self.selection = self.playing = num
        self.active_stations[0][0] = h_item[1]
        self.active_stations[0][1] = num
        self.active_stations[1][0] = h_item[1]
        self.active_stations[1][1] = num
        self._align_stations_and_refresh(self.ws.PLAYLIST_MODE)
        ''' set active playlist in config '''
        self._cnf.set_playlist_data(stationFile ,self._cnf.station_path)
        self._playlist_in_editor = self._cnf.station_path
        self._playlist_error_message = ''
        ''' update station header on top of window '''
        if not (self._limited_height_mode or self._limited_width_mode):
            logger.error('==== update outer Body!')
            self.outerBodyWin.box()
            self._print_body_header()
            # self.outerBodyWin.refresh()
        self.playSelection()
        self._set_active_stations()
        self._get_playlists_data_from_playlist_name(h_item[0])
        self.saved_active_stations = [['', 0], ['', -1]]
        # if self._limited_height_mode or self._limited_width_mode:
        #     self._print_limited_info()
        # else:
        #     #if self.ws.operation_mode == self.ws.NORMAL_MODE:
        #     #    self.refreshBody()
        #     #else:
        #     #    logger.error('\n\n1 not refreshing\n\n')
        #     self.refreshBody()
        self.refreshBody()
        return num


# pymode:lint_ignore=W901
