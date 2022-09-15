# '''- coding: utf-8 -*- '''
import curses
from sys import version_info, platform, stdout
import logging
import threading
from .common import player_start_stop_token

logger = logging.getLogger(__name__)

if platform.lower().startswith('win'):
    import ctypes

class Log(object):
    ''' Log class that outputs text to a curses screen '''

    old_window_title = None
    locked = False

    msg = suffix = counter = cursesScreen = None

    last_written_string = ''
    last_written_suffix = ''
    display_help_message = False

    asked_to_stop = False

    _color_change = False

    lock = threading.Lock()

    _player_stopped = 0

    _show_status_updates = False


    def __init__(self, config):
        self._cnf = config
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = int(cursesScreen.getmaxyx()[1] - 1)

        ''' Redisplay the last message '''
        if self.msg:
            self.write(self.msg)

    def _do_i_print_last_char(self, first_print):
        if first_print:
            first_print = False
            try:
                self.cursesScreen.addstr(0, self.width + 1, ' ')
            except:
                pass
        return first_print

    def write(self,
              msg=None,
              suffix=None,
              counter=None,
              help_msg=False,
              error_msg=False,
              notify_function=None):
        if self.cursesScreen:
            with self.lock:
                if msg:
                    if player_start_stop_token[1] in msg or \
                            player_start_stop_token[2] in msg:\
                        self._player_stopped += 1
                    elif msg.startswith(player_start_stop_token[0]):
                        self._player_stopped = 0
                if msg and self._player_stopped > 1:
                    ''' Refuse to print anything if "Playback stopped"
                        was the last message printed
                    '''
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Refusing to show message; player is stopped: "{}"'.format(msg))
                    # return
                elif self._player_stopped == 1:
                    self._player_stopped = 2
                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    self._player_stopped = 0
                    return
                #if logger.isEnabledFor(logging.DEBUG):
                #    logger.debug('before ----------------------------')
                #    logger.debug('msg = "{}"'.format(msg))
                #    logger.debug('self.msg = "{}"'.format(self.msg))
                #    logger.debug('suffix = "{}"'.format(suffix))
                #    logger.debug('self.suffix = "{}"'.format(self.suffix))
                #    logger.debug('counter = "{}"'.format(counter))
                #    logger.debug('self.counter = "{}"'.format(self.counter))

                first_print = True
                if msg is not None:
                    self.msg = msg
                if suffix is not None:
                    self.suffix = suffix
                if counter is not None:
                    self.counter = counter
                self.error_msg = True if error_msg else False

                #if logger.isEnabledFor(logging.DEBUG):
                #    logger.debug('after ----------------------------')
                #    logger.debug('msg = "{}"'.format(msg))
                #    logger.debug('self.msg = "{}"'.format(self.msg))
                #    logger.debug('suffix = "{}"'.format(suffix))
                #    logger.debug('self.suffix = "{}"'.format(self.suffix))
                #    logger.debug('counter = "{}"'.format(counter))
                #    logger.debug('self.counter = "{}"'.format(self.counter))

                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    self._player_stopped = 0
                    return
                ''' update main message '''
                if self.msg:
                    self.cursesScreen.erase()
                    d_msg = ''
                    try:
                        d_msg = self.msg.strip()[0: self.width].replace('\r', '').replace('\n', '')
                        self.cursesScreen.addstr(0, 1, d_msg)
                    except:
                        try:
                            d_msg = self.msg.encode('utf-8', 'replace').strip()[0: self.width].replace('\r', '').replace('\n', '')
                            self.cursesScreen.addstr(0, 1, d_msg)
                        except:
                            pass
                            # if logger.isEnabledFor(logging.ERROR):
                            #     logger.error('Error updating the Status Bar')
                    self.set_win_title(d_msg)
                    self._write_title_to_log(d_msg)
                    if self._show_status_updates:
                        if logger.isEnabledFor(logging.DEBUG):
                            try:
                                logger.debug('Status: "{}"'.format(self.msg))
                            except:
                                pass

                self._active_width = self.width

                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    self._player_stopped = 0
                    return
                ''' display suffix '''
                if self.suffix:
                    d_msg = ' [' + self.suffix + ']'
                    try:
                        self.cursesScreen.addstr(
                            0, self._active_width - len(d_msg),
                            d_msg + ' ')
                    except:
                        pass
                    self.cursesScreen.chgat(
                        0, self._active_width - len(d_msg) + 1,
                        len(d_msg) - 1,
                        curses.color_pair(1))
                    first_print = self._do_i_print_last_char(first_print)
                    self.cursesScreen.refresh()
                    self._active_width -= len(d_msg)
                if self._show_status_updates:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Suffix: {}'.format(self.suffix))

                ''' display counter '''
                if self.counter:
                    if self.counter == '0':
                        self.counter = None
                    if self.counter:
                        if self.suffix:
                            self._active_width += 1
                        d_msg = ' [' + self.counter + ']'
                        self.cursesScreen.addstr(
                            0,
                            self._active_width - len(d_msg),
                            d_msg)
                        first_print = self._do_i_print_last_char(first_print)
                        self.cursesScreen.refresh()
                        self._active_width -= len(d_msg)
                        self.display_help_message = False
                if self._show_status_updates:
                    if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Counter: {}'.format(self.counter))

                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    return
                ''' display press ? '''
                if help_msg or self.display_help_message:
                    if not self.error_msg:
                        self.counter = None
                        suffix_string = ' Press ? for help'
                        try:
                            self.cursesScreen.addstr(
                                0,
                                self._active_width - len(suffix_string),
                                suffix_string)
                        except:
                            pass
                        self.cursesScreen.refresh()
                        self.display_help_message = True
                        if self._show_status_updates:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Press ? for help: yes')
                else:
                    if self._show_status_updates:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Press ? for help: no')

                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    self._player_stopped = 0
                    return
                self.cursesScreen.refresh()
                # logger.error('DE _player_stopped = {}'.format(self._player_stopped))

    def readline(self):
        pass

    def _write_title_to_log(self, msg=None, force=False):
        if msg is None:
            d_msg = None
        else:
            d_msg = msg.replace('[Muted] ', '')
        if d_msg is None and self._cnf._current_log_title:
            try:
                logger.critical(self._cnf._current_log_title.replace('Title: ', '    ') + ' (LIKED)')
                self._cnf._last_liked_title = self._cnf._current_log_title
            except:
                logger.critical('Error writing LIKED title...')
        elif d_msg.startswith('Title: '):
                if logger.isEnabledFor(logging.CRITICAL):
                    try:
                        if force or not d_msg in self._cnf._old_log_title:
                            try:
                                logger.critical(d_msg.replace('Title: ', '    '))
                            except:
                                logger.critical('Error writing title...')
                            self._cnf._old_log_title = d_msg
                    except UnicodeDecodeError:
                        ''' try to handle it for python2 '''
                        try:
                            if force or not d_msg.decode('utf-8', 'replace') in self._cnf._old_log_title.decode('utf-8', 'replace'):
                                try:
                                    logger.critical(d_msg.replace('Title: ', '    '))
                                except:
                                    logger.critical('Error writing title...')
                                self._cnf._old_log_title = d_msg
                        except:
                            logger.critical('Error writing title...')
                self._cnf._current_log_title = d_msg
        elif d_msg.startswith('Playing: '):
            if logger.isEnabledFor(logging.CRITICAL):
                try:
                    if force or not d_msg in self._cnf._old_log_station:
                        try:
                            logger.critical(d_msg.replace('Playing: ', '>>> Station: '))
                        except:
                            logger.critical('Error writing station name...')
                        self._cnf._old_log_station = d_msg
                except UnicodeDecodeError:
                    ''' try to handle it for python2 '''
                    try:
                        if force or not d_msg.decode('utf-8', 'replace') in self._cnf._old_log_title.decode('utf-8', 'replace'):
                            try:
                                logger.critical(d_msg.replace('Playing: ', '>>> Station: '))
                            except:
                                logger.critical('Error writing station name...')
                            self._cnf._old_log_station = d_msg
                    except:
                        logger.critical('Error writing station name...')
            self._cnf._current_log_station = d_msg

    def write_start_log_station_and_title(self):
        if self._cnf._current_log_station:
            self._write_title_to_log(self._cnf._current_log_station, force=True)
        if self._cnf._current_log_title:
            self._write_title_to_log(self._cnf._current_log_title, force=True)

    @staticmethod
    def set_win_title(msg=None):
        default = 'Your Internet Radio Player'
        do_not_update = (
            ': Playback stopped',
            'Selected ',
            'Failed to connect to: ',
            'Connecting to: ',
            'Initialization: ',
            'Station: ',
            'abnormally',
        )
        token_id = 1
        tokens = ('PyRadio: ', 'PyRadio - ')
        if logger.isEnabledFor(logging.DEBUG):
            if msg is None:
                logger.debug('set_win_title(): msg is None')
            else:
                logger.debug('set_win_title(): msg = "' + msg + '"')
        if msg is None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('set_win_title(): d_msg = default')
            d_msg = default
            token_id = 0
        else:
            if msg.startswith('['):
                return
            d_msg = msg
            if d_msg.endswith(' (Session Locked)'):
                token_id = 0
                Log.locked = True
                d_msg = default
            else:
                # if stopped...
                for a_stop_token in do_not_update:
                    if a_stop_token in msg:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('set_win_title(): d_msg = default')
                        d_msg = default
                        token_id = 0
                        break

                if Log.old_window_title is not None:
                    ''' fix for python2 '''
                    logger.debug('set_win_title(): Old title is "' + Log.old_window_title+ '"')
                    if Log.old_window_title == d_msg:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('set_win_title(): same title... return')
                        return
                    Log.old_window_title = d_msg
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('set_win_title(): set_win_title(): Old title is None')
                    Log.old_window_title = d_msg

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('set_win_title(): d_msg = "' + d_msg + '"')

        if token_id == 0 and Log.locked:
            d_msg += '(Session Locked)'

        if platform.lower().startswith('win'):
            # ctypes.windll.kernel32.SetConsoleTitleW('● ' + tokens[token_id] + d_msg)
            ctypes.windll.kernel32.SetConsoleTitleW(tokens[token_id] + d_msg)
        else:
            stdout.write('\33]0;' + tokens[token_id] + d_msg + '\a')
            stdout.flush()

