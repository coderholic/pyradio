# -*- coding: utf-8 -*-
import locale
from collections import deque
import logging
import locale
locale.setlocale(locale.LC_ALL, "")
logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")


class Window_Stack_Constants():
    ''' Modes of Operation '''
    DEPENDENCY_ERROR = -2
    NO_PLAYER_ERROR_MODE = -1
    NORMAL_MODE = 0
    PLAYLIST_MODE = 1
    REGISTER_MODE = 2
    SEARCH_NORMAL_MODE = 3
    SEARCH_PLAYLIST_MODE = 4
    SEARCH_THEME_MODE = 5
    SEARCH_SELECT_PLAYLIST_MODE = 6
    SEARCH_SELECT_STATION_MODE = 7
    CONFIG_MODE = 8
    SELECT_PLAYER_MODE = 9
    SELECT_ENCODING_MODE = 10
    SELECT_PLAYLIST_MODE = 11
    SELECT_STATION_MODE = 12
    SELECT_STATION_ENCODING_MODE = 13
    NEW_THEME_MODE = 14
    EDIT_THEME_MODE = 15
    EDIT_STATION_ENCODING_MODE = 16
    IN_PLAYER_PARAMS_EDITOR = 17
    REMOVE_STATION_MODE = 50
    SAVE_PLAYLIST_MODE = 51
    ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE = 52
    ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE = 53
    ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE = 54
    ADD_STATION_MODE = 55
    EDIT_STATION_MODE = 56
    CLEAR_REGISTER_MODE = 57
    CLEAR_ALL_REGISTERS_MODE = 58
    STATION_INFO_MODE = 59
    CREATE_PLAYLIST_MODE = 60
    RENAME_PLAYLIST_MODE = 61
    COPY_PLAYLIST_MODE = 62
    CONNECTION_MODE = 63
    PASTE_MODE = 64
    UNNAMED_REGISTER_MODE = 65
    PLAYER_PARAMS_MODE = 66
    STATION_DATABASE_INFO_MODE = 67
    BROWSER_SORT_MODE = 69
    BROWSER_SERVER_SELECTION_MODE = 70
    BROWSER_SEARCH_MODE = 71
    BROWSER_OPEN_MODE = 72
    BROWSER_PERFORMING_SEARCH_MODE = 73
    RADIO_BROWSER_CONFIG_MODE = 74
    SCHEDULE_EDIT_MODE = 75
    REMOVE_GROUP_MODE = 76
    RECORD_WINDOW_MODE = 77
    BUFFER_SET_MODE = 78
    SCHEDULE_PLAYLIST_SELECT_MODE = 79
    SCHEDULE_STATION_SELECT_MODE = 80
    INSERT_RECORDINGS_DIR_MODE = 82
    MOVE_RECORDINGS_DIR_ERROR_MODE = 84
    INSERT_RESOURCE_OPENER = 85
    OPEN_DIR_MODE = 86
    KEYBOARD_CONFIG_MODE = 87
    LOCALIZED_CONFIG_MODE = 88
    MESSAGING_MODE = 100
    NEW_THEME_HELP_MODE = 101
    EDIT_THEME_HELP_MODE = 102
    ASK_TO_CREATE_NEW_THEME_MODE = 103
    ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER = 104
    ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG = 105
    ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT = 106
    WIN_MANAGE_PLAYERS_MSG_MODE = 107
    WIN_PRINT_EXE_LOCATION_MODE = 108
    WIN_UNINSTALL_MODE = 109
    WIN_REMOVE_OLD_INSTALLATION_MODE = 110
    REMOTE_CONTROL_SERVER_ACTIVE_MODE = 112
    REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE = 113
    CHANGE_PLAYER_MODE = 114
    ASK_TO_UPDATE_STATIONS_CSV_MODE = 115
    GROUP_SELECTION_MODE = 117
    GROUP_SEARCH_MODE = 118
    SCHEDULE_PLAYLIST_SEARCH_MODE = 119,
    SCHEDULE_STATION_SEARCH_MODE = 120,
    DELETE_PLAYLIST_MODE = 121,
    # TODO: return values from opening theme
    PLAYLIST_NOT_FOUND_ERROR_MODE = 201
    PLAYLIST_LOAD_ERROR_MODE = 202
    PLAYLIST_RELOAD_CONFIRM_MODE = 204
    PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE = 205
    PLAYLIST_SCAN_ERROR_MODE = 206
    SERVICE_CONNECTION_ERROR = 211
    FOREIGN_PLAYLIST_ASK_MODE = 300
    CONFIG_SAVE_ERROR_MODE = 303
    STATION_INFO_ERROR_MODE = 308
    PLAYLIST_CREATE_ERROR = 311
    WIN_VLC_NO_RECORD_MODE = 324
    KEYBOARD_CONFIG_ERROR_MODE = 325
    THEME_MODE = 400
    NO_BROWSER_SEARCH_RESULT_NOTIFICATION = 501
    UPDATE_NOTIFICATION_MODE = 1000
    UPDATE_NOTIFICATION_OK_MODE = 1001
    NO_THEMES_MODE = 1005

    MODE_NAMES = {
        DEPENDENCY_ERROR: 'DEPENDENCY_ERROR',
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
        REMOVE_GROUP_MODE: 'REMOVE_GROUP_MODE',
        SAVE_PLAYLIST_MODE: 'SAVE_PLAYLIST_MODE',
        ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE: 'ASK_TO_SAVE_PLAYLIST_WHEN_OPENING_PLAYLIST_MODE',
        ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE: 'ASK_TO_SAVE_PLAYLIST_WHEN_BACK_IN_HISTORY_MODE',
        ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE: 'ASK_TO_SAVE_PLAYLIST_WHEN_EXITING_MODE',
        NEW_THEME_HELP_MODE: 'NEW_THEME_HELP_MODE',
        EDIT_THEME_HELP_MODE: 'EDIT_THEME_HELP_MODE',
        ASK_TO_CREATE_NEW_THEME_MODE: 'ASK_TO_CREATE_NEW_THEME_MODE',
        PLAYLIST_NOT_FOUND_ERROR_MODE: 'PLAYLIST_NOT_FOUND_ERROR_MODE',
        PLAYLIST_LOAD_ERROR_MODE: 'PLAYLIST_LOAD_ERROR_MODE',
        PLAYLIST_RELOAD_CONFIRM_MODE: 'PLAYLIST_RELOAD_CONFIRM_MODE',
        PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE: 'PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE',
        PLAYLIST_SCAN_ERROR_MODE: 'PLAYLIST_SCAN_ERROR_MODE',
        FOREIGN_PLAYLIST_ASK_MODE: 'FOREIGN_PLAYLIST_ASK_MODE',
        CONFIG_SAVE_ERROR_MODE: 'CONFIG_SAVE_ERROR_MODE',
        THEME_MODE: 'THEME_MODE',
        UPDATE_NOTIFICATION_MODE: 'UPDATE_NOTIFICATION_MODE',
        UPDATE_NOTIFICATION_OK_MODE: 'UPDATE_NOTIFICATION_OK_MODE',
        ADD_STATION_MODE: 'ADD_STATION_MODE',
        EDIT_STATION_MODE: 'EDIT_STATION_MODE',
        SERVICE_CONNECTION_ERROR: 'SERVICE_CONNECTION_ERROR',
        CLEAR_REGISTER_MODE: 'CLEAR_REGISTER_MODE',
        CLEAR_ALL_REGISTERS_MODE: 'CLEAR_ALL_REGISTERS_MODE',
        STATION_INFO_MODE: 'STATION_INFO_MODE',
        STATION_DATABASE_INFO_MODE: 'STATION_DATABASE_INFO_MODE',
        STATION_INFO_ERROR_MODE: 'STATION_INFO_ERROR_MODE',
        CREATE_PLAYLIST_MODE: 'CREATE_PLAYLIST_MODE',
        RENAME_PLAYLIST_MODE: 'RENAME_PLAYLIST_MODE',
        PLAYLIST_CREATE_ERROR: 'PLAYLIST_CREATE_ERROR',
        CONNECTION_MODE: 'CONNECTION_MODE',
        PASTE_MODE: 'PASTE_MODE',
        UNNAMED_REGISTER_MODE: 'UNNAMED_REGISTER_MODE',
        PLAYER_PARAMS_MODE: 'PLAYER_PARAMS_MODE',
        IN_PLAYER_PARAMS_EDITOR: 'IN_PLAYER_PARAMS_EDITOR',
        BROWSER_SORT_MODE: 'BROWSER_SORT_MODE',
        BROWSER_SERVER_SELECTION_MODE: 'BROWSER_SERVER_SELECTION_MODE',
        BROWSER_SEARCH_MODE: 'BROWSER_SEARCH_MODE',
        NO_BROWSER_SEARCH_RESULT_NOTIFICATION: 'NO_BROWSER_SEARCH_RESULT_NOTIFICATION',
        BROWSER_OPEN_MODE: 'BROWSER_OPEN_MODE',
        BROWSER_PERFORMING_SEARCH_MODE: 'BROWSER_PERFORMING_SEARCH_MODE',
        ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER: 'ASK_TO_SAVE_BROWSER_CONFIG_FROM_BROWSER',
        ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG: 'ASK_TO_SAVE_BROWSER_CONFIG_FROM_CONFIG',
        ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT: 'ASK_TO_SAVE_BROWSER_CONFIG_TO_EXIT',
        RADIO_BROWSER_CONFIG_MODE: 'RADIO_BROWSER_CONFIG_MODE',
        WIN_MANAGE_PLAYERS_MSG_MODE: 'WIN_MANAGE_PLAYERS_MSG_MODE',
        WIN_PRINT_EXE_LOCATION_MODE: 'WIN_PRINT_EXE_LOCATION_MODE',
        WIN_UNINSTALL_MODE: 'WIN_UNINSTALL_MODE',
        WIN_REMOVE_OLD_INSTALLATION_MODE: 'WIN_REMOVE_OLD_INSTALLATION_MODE',
        SCHEDULE_EDIT_MODE: 'SCHEDULE_EDIT_MODE',
        SCHEDULE_PLAYLIST_SELECT_MODE: 'SCHEDULE_PLAYLIST_SELECT_MODE',
        SCHEDULE_STATION_SELECT_MODE: 'SCHEDULE_STATION_SELECT_MODE',
        NO_THEMES_MODE: 'NO_THEMES_MODE',
        REMOTE_CONTROL_SERVER_ACTIVE_MODE: 'REMOTE_CONTROL_SERVER_ACTIVE_MODE',
        REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE: 'REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE',
        CHANGE_PLAYER_MODE: 'CHANGE_PLAYER_MODE',
        ASK_TO_UPDATE_STATIONS_CSV_MODE: 'ASK_TO_UPDATE_STATIONS_CSV_MODE',
        GROUP_SELECTION_MODE: 'GROUP_SELECTION_MODE',
        GROUP_SEARCH_MODE: 'GROUP_SEARCH_MODE',
        RECORD_WINDOW_MODE: 'RECORD_WINDOW_MODE',
        WIN_VLC_NO_RECORD_MODE: 'WIN_VLC_NO_RECORD_MODE',
        BUFFER_SET_MODE: 'BUFFER_SET_MODE',
        SCHEDULE_PLAYLIST_SEARCH_MODE: 'SCHEDULE_PLAYLIST_SEARCH_MODE',
        SCHEDULE_STATION_SEARCH_MODE: 'SCHEDULE_STATION_SEARCH_MODE',
        INSERT_RECORDINGS_DIR_MODE: 'INSERT_RECORDINGS_DIR_MODE',
        MOVE_RECORDINGS_DIR_ERROR_MODE: 'MOVE_RECORDINGS_DIR_ERROR_MODE',
        OPEN_DIR_MODE: 'OPEN_DIR_MODE',
        DELETE_PLAYLIST_MODE: 'DELETE_PLAYLIST_MODE',
        MESSAGING_MODE: 'MESSAGING_MODE',
        INSERT_RESOURCE_OPENER: 'INSERT_RESOURCE_OPENER',
        KEYBOARD_CONFIG_MODE: 'KEYBOARD_CONFIG_MODE',
        KEYBOARD_CONFIG_ERROR_MODE: 'KEYBOARD_CONFIG_ERROR_MODE',
        LOCALIZED_CONFIG_MODE: 'LOCALIZED_CONFIG_MODE',
}

    ''' When PASSIVE_WINDOWS target is one of them,
    also set window_mode '''
    MAIN_MODES = (
        NORMAL_MODE,
        PLAYLIST_MODE,
        CONFIG_MODE,
        ADD_STATION_MODE,
        EDIT_STATION_MODE,
    )

    FULL_SCREEN_MODES = (
        NORMAL_MODE,
        CONFIG_MODE,
        BROWSER_SEARCH_MODE,
        EDIT_STATION_MODE,
        ADD_STATION_MODE,
        RENAME_PLAYLIST_MODE,
        RADIO_BROWSER_CONFIG_MODE,
        INSERT_RECORDINGS_DIR_MODE,
        KEYBOARD_CONFIG_MODE,
        LOCALIZED_CONFIG_MODE,
    )

    PASSIVE_WINDOWS = (
        PLAYLIST_LOAD_ERROR_MODE,
        PLAYLIST_NOT_FOUND_ERROR_MODE,
        SERVICE_CONNECTION_ERROR,
        STATION_INFO_ERROR_MODE,
        PLAYLIST_CREATE_ERROR,
        UNNAMED_REGISTER_MODE,
        STATION_DATABASE_INFO_MODE,
        WIN_VLC_NO_RECORD_MODE,
    )

    def __init__(self):
        pass


class Window_Stack(Window_Stack_Constants):
    _dq = deque()

    def __init__(self):
        super(Window_Stack_Constants, self).__init__()
        self._dq.append([self.NORMAL_MODE, self.NORMAL_MODE])

    def __del__(self):
        self._dq.clear()
        self._dq = None

    @property
    def operation_mode(self):
        return self._dq[-1][0]

    @operation_mode.setter
    def operation_mode(self, a_mode):
        if a_mode in self.MAIN_MODES:
            ''' also setting operation_mode in
                window_mode property setter
            '''
            self.window_mode = a_mode
        else:
            tmp = [a_mode, self._dq[-1][1]]
            if self._dq[-1] != tmp:
                self._dq.append([a_mode, self._dq[-1][1]])
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: {0} -> {1} - {2}'.format(
                        self.mode_name(self._dq[-2][0]),
                        self.mode_name(self._dq[-1][0]),
                        list(self._dq)))
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Refusing to add duplicate {0} Remaining at {1}'.format(tmp, list(self._dq)))

    @property
    def window_mode(self):
        return self._dq[-1][1]

    @window_mode.setter
    def window_mode(self, a_mode):
        tmp = [a_mode, a_mode]
        if self._dq[-1] != tmp:
            self._dq.append([a_mode, a_mode])
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('WIN MODE: {0} -> {1} - {2}'.format(
                    self.mode_name(self._dq[-2][0]),
                    self.mode_name(self._dq[-1][0]),
                    list(self._dq)))
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
        ''' return mode number when given mode name '''
        for item in self.MODE_NAMES.items():
            if item[1] == stringToFind:
                return item[0]
        return -2

    def str_to_mode_tuple(self, stringToFind):
        ''' return mode tuple when given mode name '''
        for item in self.MODE_NAMES.items():
            if item[1] == stringToFind:
                return item
        return -2, 'UNKNOWN'

    def mode_name(self, intToFind):
        if intToFind in self.MODE_NAMES:
            return self.MODE_NAMES[intToFind]
        return 'UNKNOWN'

    def close_window(self):
        if len(self._dq) == 1 and self._dq[0] != [self.NORMAL_MODE, self.NORMAL_MODE]:
            self._dq[0] = [self.NORMAL_MODE, self.NORMAL_MODE]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: Resetting...')

        if len(self._dq) > 1:
            tmp = self._dq.pop()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: {0} -> {1} - {2}'.format(self.mode_name(tmp[0]), self.mode_name(self._dq[-1][0]), list(self._dq)))
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('CLOSE MODE: Refusing to clear que...')
