# -*- coding: utf-8 -*-
from collections import deque
import logging
logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

class Window_Stack_Constants(object):
    """ Modes of Operation """
    NO_PLAYER_ERROR_MODE = -1
    NORMAL_MODE = 0
    PLAYLIST_MODE = 1
    SEARCH_NORMAL_MODE = 2
    SEARCH_PLAYLIST_MODE = 3
    SEARCH_THEME_MODE = 4
    SEARCH_SELECT_PLAYLIST_MODE = 5
    SEARCH_SELECT_STATION_MODE = 6
    CONFIG_MODE = 7
    SELECT_PLAYER_MODE = 8
    SELECT_ENCODING_MODE = 9
    SELECT_PLAYLIST_MODE = 10
    SELECT_STATION_MODE = 11
    SELECT_STATION_ENCODING_MODE = 12
    NEW_THEME_MODE = 13
    EDIT_THEME_MODE = 14
    EDIT_STATION_ENCODING_MODE = 15
    REMOVE_STATION_MODE = 50
    SAVE_PLAYLIST_MODE = 51
    ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE = 52
    ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE = 53
    ADD_STATION_MODE = 54
    EDIT_STATION_MODE = 55
    MAIN_HELP_MODE = 100
    MAIN_HELP_MODE_PAGE_2 = 113
    PLAYLIST_HELP_MODE = 101
    CONFIG_HELP_MODE = 102
    THEME_HELP_MODE = 103
    SELECT_PLAYER_HELP_MODE = 104
    SELECT_ENCODING_HELP_MODE = 105
    SELECT_PLAYLIST_HELP_MODE = 106
    SELECT_STATION_HELP_MODE = 107
    NEW_THEME_HELP_MODE = 108
    EDIT_THEME_HELP_MODE = 109
    ASK_TO_CREATE_NEW_THEME_MODE = 110
    SEARCH_HELP_MODE = 111
    LINE_EDITOR_HELP = 112
    # TODO: return values from opening theme
    PLAYLIST_RECOVERY_ERROR_MODE = 200
    PLAYLIST_NOT_FOUND_ERROR_MODE = 201
    PLAYLIST_LOAD_ERROR_MODE = 202
    PLAYLIST_RELOAD_ERROR_MODE = 203
    PLAYLIST_RELOAD_CONFIRM_MODE = 204
    PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE = 205
    PLAYLIST_SCAN_ERROR_MODE = 206
    SAVE_PLAYLIST_ERROR_1_MODE = 207
    SAVE_PLAYLIST_ERROR_2_MODE = 208
    REQUESTS_MODULE_NOT_INSTALLED_ERROR = 209
    UNKNOWN_BROWSER_SERVICE_ERROR = 210
    SERVICE_CONNECTION_ERROR = 211
    PLAYER_CHANGED_INFO_MODE = 212
    FOREIGN_PLAYLIST_ASK_MODE = 300
    FOREIGN_PLAYLIST_MESSAGE_MODE = 301
    FOREIGN_PLAYLIST_COPY_ERROR_MODE = 302
    CONFIG_SAVE_ERROR_MODE = 303
    EDIT_STATION_NAME_ERROR = 304
    EDIT_STATION_URL_ERROR = 305
    PY2_EDITOR_ERROR = 306
    THEME_MODE = 400
    HISTORY_EMPTY_NOTIFICATION = 500
    UPDATE_NOTIFICATION_MODE = 1000
    SESSION_LOCKED_MODE = 1001
    NOT_IMPLEMENTED_YET_MODE = 1002

    MODE_NAMES = {
            NO_PLAYER_ERROR_MODE: 'NO_PLAYER_ERROR_MODE',
            NORMAL_MODE: 'NORMAL_MODE',
            PLAYLIST_MODE: 'PLAYLIST_MODE',
            SEARCH_NORMAL_MODE: 'SEARCH_NORMAL_MODE',
            SEARCH_PLAYLIST_MODE: 'SEARCH_PLAYLIST_MODE',
            SEARCH_THEME_MODE: 'SEARCH_THEME_MODE',
            SEARCH_SELECT_PLAYLIST_MODE: 'SEARCH_SELECT_PLAYLIST_MODE',
            SEARCH_SELECT_STATION_MODE: 'SEARCH_SELECT_STATION_MODE',
            CONFIG_MODE: 'CONFIG_MODE',
            SELECT_PLAYER_MODE: 'SELECT_PLAYER_MODE',
            SELECT_ENCODING_MODE: 'SELECT_ENCODING_MODE',
            SELECT_PLAYLIST_MODE: 'SELECT_PLAYLIST_MODE',
            SELECT_STATION_MODE: 'SELECT_STATION_MODE',
            SELECT_STATION_ENCODING_MODE: 'SELECT_STATION_ENCODING_MODE',
            EDIT_STATION_ENCODING_MODE: 'EDIT_STATION_ENCODING_MODE',
            NEW_THEME_MODE: 'NEW_THEME_MODE',
            EDIT_THEME_MODE: 'EDIT_THEME_MODE',
            REMOVE_STATION_MODE: 'REMOVE_STATION_MODE',
            SAVE_PLAYLIST_MODE: 'SAVE_PLAYLIST_MODE',
            ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE: 'ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE',
            ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE: 'ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE',
            MAIN_HELP_MODE: 'MAIN_HELP_MODE',
            MAIN_HELP_MODE_PAGE_2: 'MAIN_HELP_MODE_PAGE_2',
            PLAYLIST_HELP_MODE: 'PLAYLIST_HELP_MODE',
            CONFIG_HELP_MODE: 'CONFIG_HELP_MODE',
            THEME_HELP_MODE: 'THEME_HELP_MODE',
            SELECT_PLAYER_HELP_MODE: 'SELECT_PLAYER_HELP_MODE',
            SELECT_ENCODING_HELP_MODE: 'SELECT_ENCODING_HELP_MODE',
            SELECT_PLAYLIST_HELP_MODE: 'SELECT_PLAYLIST_HELP_MODE',
            SELECT_STATION_HELP_MODE: 'SELECT_STATION_HELP_MODE',
            NEW_THEME_HELP_MODE: 'NEW_THEME_HELP_MODE',
            EDIT_THEME_HELP_MODE: 'EDIT_THEME_HELP_MODE',
            ASK_TO_CREATE_NEW_THEME_MODE: 'ASK_TO_CREATE_NEW_THEME_MODE',
            SEARCH_HELP_MODE: 'SEARCH_HELP_MODE',
            PLAYLIST_RECOVERY_ERROR_MODE: 'PLAYLIST_RECOVERY_ERROR_MODE',
            PLAYLIST_NOT_FOUND_ERROR_MODE: 'PLAYLIST_NOT_FOUND_ERROR_MODE',
            PLAYLIST_LOAD_ERROR_MODE: 'PLAYLIST_LOAD_ERROR_MODE',
            PLAYLIST_RELOAD_ERROR_MODE: 'PLAYLIST_RELOAD_ERROR_MODE',
            PLAYLIST_RELOAD_CONFIRM_MODE: 'PLAYLIST_RELOAD_CONFIRM_MODE',
            PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE: 'PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE',
            PLAYLIST_SCAN_ERROR_MODE: 'PLAYLIST_SCAN_ERROR_MODE',
            SAVE_PLAYLIST_ERROR_1_MODE: 'SAVE_PLAYLIST_ERROR_1_MODE',
            SAVE_PLAYLIST_ERROR_2_MODE: 'SAVE_PLAYLIST_ERROR_2_MODE',
            FOREIGN_PLAYLIST_ASK_MODE: 'FOREIGN_PLAYLIST_ASK_MODE',
            FOREIGN_PLAYLIST_MESSAGE_MODE: 'FOREIGN_PLAYLIST_MESSAGE_MODE',
            FOREIGN_PLAYLIST_COPY_ERROR_MODE: 'FOREIGN_PLAYLIST_COPY_ERROR_MODE',
            CONFIG_SAVE_ERROR_MODE: 'CONFIG_SAVE_ERROR_MODE',
            THEME_MODE: 'THEME_MODE',
            UPDATE_NOTIFICATION_MODE: 'UPDATE_NOTIFICATION_MODE',
            SESSION_LOCKED_MODE: 'SESSION_LOCKED_MODE',
            NOT_IMPLEMENTED_YET_MODE: 'NOT_IMPLEMENTED_YET_MODE',
            ADD_STATION_MODE: 'ADD_STATION_MODE',
            EDIT_STATION_MODE: 'EDIT_STATION_MODE',
            LINE_EDITOR_HELP: 'LINE_EDITOR_HELP',
            EDIT_STATION_NAME_ERROR: 'EDIT_STATION_NAME_ERROR',
            EDIT_STATION_URL_ERROR: 'EDIT_STATION_URL_ERROR',
            PY2_EDITOR_ERROR: 'PY2_EDITOR_ERROR',
            REQUESTS_MODULE_NOT_INSTALLED_ERROR: 'REQUESTS_MODULE_NOT_INSTALLED_ERROR',
            UNKNOWN_BROWSER_SERVICE_ERROR: 'UNKNOWN_BROWSER_SERVICE_ERROR',
            SERVICE_CONNECTION_ERROR: 'SERVICE_CONNECTION_ERROR',
            PLAYER_CHANGED_INFO_MODE: 'PLAYER_CHANGED_INFO_MODE',
            HISTORY_EMPTY_NOTIFICATION: 'HISTORY_EMPTY_NOTIFICATION',
            }

    ''' When PASSIVE_WINDOWS target is one of them,
        also set window_mode '''
    MAIN_MODES = ( NORMAL_MODE,
            PLAYLIST_MODE,
            CONFIG_MODE,
            ADD_STATION_MODE,
            EDIT_STATION_MODE,
            )

    PASSIVE_WINDOWS = (
            SESSION_LOCKED_MODE,
            UPDATE_NOTIFICATION_MODE,
            MAIN_HELP_MODE,
            MAIN_HELP_MODE_PAGE_2,
            CONFIG_HELP_MODE,
            SELECT_PLAYER_HELP_MODE,
            SELECT_PLAYLIST_HELP_MODE,
            SELECT_STATION_HELP_MODE,
            PLAYLIST_RELOAD_ERROR_MODE,
            SAVE_PLAYLIST_ERROR_1_MODE,
            SAVE_PLAYLIST_ERROR_2_MODE,
            FOREIGN_PLAYLIST_MESSAGE_MODE,
            FOREIGN_PLAYLIST_COPY_ERROR_MODE,
            PLAYLIST_HELP_MODE,
            PLAYLIST_LOAD_ERROR_MODE,
            PLAYLIST_NOT_FOUND_ERROR_MODE,
            SELECT_ENCODING_HELP_MODE,
            THEME_HELP_MODE,
            SEARCH_HELP_MODE,
            LINE_EDITOR_HELP,
            EDIT_STATION_NAME_ERROR,
            EDIT_STATION_URL_ERROR,
            PY2_EDITOR_ERROR,
            REQUESTS_MODULE_NOT_INSTALLED_ERROR,
            UNKNOWN_BROWSER_SERVICE_ERROR,
            SERVICE_CONNECTION_ERROR,
            PLAYER_CHANGED_INFO_MODE,
            )

    def __init__(self):
        pass

class Window_Stack(Window_Stack_Constants):
    _dq = deque()

    def __init__(self):
        super(Window_Stack_Constants, self).__init__()
        self._dq.append( [ self.NORMAL_MODE, self.NORMAL_MODE])

    def __del__(self):
        self._dq.clear()
        self._dq = None

    @property
    def operation_mode(self):
        return self._dq[-1][0]

    @operation_mode.setter
    def operation_mode(self, a_mode):
        if a_mode in self.MAIN_MODES:
            self.window_mode = a_mode
        else:
            tmp = [ a_mode, self._dq[-1][1] ]
            if self._dq[-1] != tmp:
                self._dq.append( [ a_mode, self._dq[-1][1] ])
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: {0} -> {1} - {2}'.format(self.mode_name(self._dq[-2][0]), self.mode_name(self._dq[-1][0]), list(self._dq)))
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Refusing to add duplicate {0} Remaining at {1}'.format(tmp, list(self._dq)))

    @property
    def window_mode(self):
        return self._dq[-1][1]

    @window_mode.setter
    def window_mode(self, a_mode):
        tmp = [ a_mode, a_mode ]
        if self._dq[-1] != tmp:
            self._dq.append( [ a_mode, a_mode  ])
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('WIN MODE: {0} -> {1} - {2}'.format(self.mode_name(self._dq[-2][0]), self.mode_name(self._dq[-1][0]), list(self._dq)))
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('WIN MODE: Refusing to add duplicate {0} Remaining at {1}'.format(tmp, list(self._dq)))

    @property
    def previous_operation_mode(self):
        try:
            return self._dq[-2][0]
        except:
            return -2

    @previous_operation_mode.setter
    def previous_open_window(self, a_mode):
        return

    @property
    def previous_window_mode(self):
        return self._dq[-2][1]

    @previous_window_mode.setter
    def previous_window_mode(self, a_mode):
        return

    def str_to_mode(self, stringToFind):
        """ return mode number when givven mode name """
        for item in self.MODE_NAMES.items():
            if item[1] == self.stringToFind:
                return item[0]
        return -2

    def str_to_mode_tuple(self, stringToFind):
        """ return mode tuple when givven mode name """
        for item in self.MODE_NAMES.items():
            if item[1] == stringToFind:
                return item
        return ( -2, 'UNKNOWN' )

    def mode_name(self, intToFind):
        if intToFind in self.MODE_NAMES.keys():
            return self.MODE_NAMES[intToFind]
        return 'UNKNOWN'

    def close_window(self):
        if len(self._dq) == 1 and self._dq[0] != [ self.NORMAL_MODE, self.NORMAL_MODE ]:
            self._dq[0] = [ self.NORMAL_MODE, self.NORMAL_MODE ]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: Resetting...')

        if len(self._dq) > 1:
            tmp = self._dq.pop()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: {0} -> {1} - {2}'.format(self.mode_name(tmp[0]), self.mode_name(self._dq[-1][0]), list(self._dq)))
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: Refusing to clear que...')
