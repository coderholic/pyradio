# -*- coding: utf-8 -*-
import locale
import warnings
import curses
from os import getenv
from os.path import join, exists, dirname
from sys import platform, stdout
from platform import system as platform_system
from copy import deepcopy
from time import sleep
import datetime
import logging
import threading
import subprocess
from .common import player_start_stop_token
from .cjkwrap import cjklen

locale.setlocale(locale.LC_ALL, "")

HAS_WIN10TOAST = True
try:
    from win10toast import ToastNotifier
    toaster = ToastNotifier()
    # from winotify import Notification
except:
    HAS_WIN10TOAST = False

warnings.simplefilter("ignore")

logger = logging.getLogger(__name__)

if platform.lower().startswith('win'):
    import ctypes

TIME_FORMATS = (
    '%H:%M:%S',
    '%H:%M',
    '%I:%M:%S %p',
    '%I:%M %p',
    '%I:%M:%S',
    '%I:%M',
)

def fix_chars(s):
    out = [s]
    from_str = ('\r', '\n', r'\"', r"\'")
    to_str = ('' , '', '"', "'")
    for n in range(len(to_str)):
        out.append(out[-1].replace(from_str[n], to_str[n]))
    return out[-1].strip()


class PyRadioTimer:
    """
    Timer class to manage and display the current time.

    This class handles the timing functionality, updating the current time
    at specified intervals. It provides thread-safe access to the current time
    and allows for customization of the time format.

    Time Formats:
    ---------------
    The following time formats are supported for display:

    1. 24-Hour Format with Seconds:
       - Format: %H:%M:%S
       - Example Output: 14:30:15

    2. 24-Hour Format without Seconds:
       - Format: %H:%M
       - Example Output: 14:30

    3. 12-Hour Format with Seconds:
       - Format: %I:%M:%S
       - Example Output: 02:30:15

    4. 12-Hour Format without Seconds:
       - Format: %I:%M
       - Example Output: 02:30

    Attributes:
    -----------
    current_time : str
        The current time as a formatted string.
    _timer_thread : threading.Thread
        The thread responsible for updating the current time.
    lock : threading.Lock
        A lock for thread-safe access to the current time.

    Methods:
    --------
    start()
        Starts the timer thread.

    stop()
        Stops the timer thread if it is running.

    update_time()
        Updates the current_time every specified interval.

    get_current_time()
        Returns the current time in a thread-safe manner.

    is_active()
        Checks if the timer thread is currently running.

    Class Variables:
    ----------------
    SLEEP_INTERVAL : float
        The duration (in seconds) to sleep between updates (default is 0.5 seconds).
    """

    def __init__(self, update_functions, exit_thread, time_format=0, sleep_interval=0.24):
        self._exit = exit_thread
        self.current_time = ""
        self._timer_thread = None
        self._time_format = TIME_FORMATS[time_format]
        self.lock = threading.Lock()  # Lock for thread-safe access
        self.function_lock = threading.Lock()  # Lock for thread-safe access
        self.SLEEP_INTERVAL = sleep_interval  # Set custom sleep interval
        self._update_functions = update_functions  # Store the update function

    @property
    def is_active(self):
        """ Return True if the timer thread is active, otherwise False. """
        return self._timer_thread is not None and self._timer_thread.is_alive()

    @property
    def update_functions(self):
        return self._update_functions

    @update_functions.setter
    def update_functions(self, value):
        if isinstance(value, tuple) and len(value) > 0:
            if not self.is_active:
                with self.function_lock:
                    self._update_functions = value

    @property
    def time_format(self):
        return TIME_FORMATS.index(self._time_format)

    @time_format.setter
    def time_format(self, value):
        if value in range(0, len(TIME_FORMATS)):
            if not self.is_active:
                with self.lock:
                    self._time_format = TIME_FORMATS[value]

    def start(self):
        """ Start the timer thread if it's not already running. """
        if self._timer_thread is None or not self._timer_thread.is_alive():
            self._timer_thread = threading.Thread(target=self.update_time)
            self._show_time()
            self._timer_thread.start()
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Timer thread is already running.")

    def stop(self):
        """ Stop the timer thread if it is running. """
        if self._timer_thread is not None and self._timer_thread.is_alive():
            self._timer_thread.join()
            self._timer_thread = None
            self.current_time = None
        else:
            if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Timer thread is not running.")

    def update_time(self):
        """
        Update current_time based on the specified interval.

        The function checks for exit conditions and updates
        the current time every 1 second.
        The update occurs in increments of SLEEP_INTERVAL seconds to ensure
        responsiveness to exit requests.
        """
        old_time = None
        while True:
            if self._exit():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Timer threat asked to stop. Stopping...')
                return


            # Calculate how many iterations based on 1 second
            iterations = int(1 / self.SLEEP_INTERVAL)

            for _ in range(iterations):
                if self._exit():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Timer threat asked to stop. Stopping...')
                    return
                sleep(self.SLEEP_INTERVAL)  # Sleep for SLEEP_INTERVAL seconds

            old_tme = self._show_time(old_time)

    def _show_time(self, old_time=None):
        with self.lock:  # Acquire lock before updating
            now = datetime.datetime.now()
            self.current_time = now.strftime(self._time_format)

        if old_time:
            if self.current_time == old_time:
                # do not update the display
                return

        # Call _update_functions in a new thread without blocking
        with self.function_lock:
            #logger.error(f'{self.current_time = }')
            for an_update_function in self._update_functions:
                if self._exit():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Timer threat asked to stop. Stopping...')
                    return
                threading.Thread(target=an_update_function, args=(self.current_time,)).start()

    def get_current_time(self):
        """ Safely return the current time. Returns an empty string if the timer is not running. """
        with self.lock:  # Acquire lock before reading
            return self.current_time if self._timer_thread and self._timer_thread.is_alive() else ""


class Log():
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

    _show_status_updates = _station_sent = False

    _startup_title = None

    icon_path = None

    _notification_command = None
    _desktop_notification_thread = None
    _stop_desktop_notification_thread = False
    _desktop_notification_lock = threading.Lock()
    _song_title_lock = threading.Lock()
    _song_title = ''
    _station_that_is_playing_now = ''
    _last = ['', '']

    _add_chapter_function = None

    can_display_help_msg = None

    def __init__(self, config, get_web_song_title):
        self._get_web_song_title = get_web_song_title
        self._muted = self._paused = False
        self._cnf = config
        self.width = None
        self._get_startup_window_title()
        self._enable_notifications = int(self._cnf.enable_notifications)
        self._repeat_notification = RepeatDesktopNotification(
                self._cnf, lambda: self._enable_notifications
                )
        self._get_icon_path()
        self._the_time = None
        self._x_start = 1
        self._stop_thread = False
        self.timer = None
        self._started_station_name = None

    def __del__(self):
        self._stop_desktop_notification_thread = True
        self._restore_startup_window_title()

    @property
    def song_title(self):
        with self._song_title_lock:
            return self._song_title

    @property
    def station_that_is_playing_now(self):
        with self._song_title_lock:
            return self._station_that_is_playing_now

    @property
    def add_chapters_function(self):
        return self._add_chapter_function

    @add_chapters_function.setter
    def add_chapters_function(self, val):
        with self.lock:
            self._add_chapter_function = val

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

    def restart_timer(self, time_format=None, update_functions=None):
        logger.error(f'{time_format = }')
        self.start_timer(time_format, update_functions)

    def start_timer(self, time_format=None, update_functions=None):
        logger.error(f'{time_format = }')
        if self.timer is not None:
            self.stop_timer()

        if self.timer is None:
            self.timer = PyRadioTimer(
                update_functions=(self.write_time, ),
                exit_thread=lambda: self.asked_to_stop or self._stop_thread,
                sleep_interval=0.24
            )
        if time_format is not None:
            self.timer.time_format = time_format
        if update_functions is not None:
            self.timer.update_functions = update_functions
        self._stop_thread = False
        if logger.isEnabledFor(logging.DEBUG):
            if self.timer.time_format == -1:
                logger.debug('timer is disabled! Not starting!')
            else:
                logger.debug('timer\'s new time format = {} ({})'.format(self.timer.time_format, TIME_FORMATS[int(self.timer.time_format)]))
                logger.debug('timer\'s new update functions = {}'.format(self.timer.update_functions))
        self.timer.start()

    def stop_timer(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('timer is disabled! Stoping!')
        self._stop_thread = True
        if self.timer:
            self.timer.stop()
        self._the_time = None

    def write_time(self, a_time):
        self.write(p_time=a_time)

    def write(self,
              msg=None,
              suffix=None,
              counter=None,
              p_time=None,
              help_msg=False,
              error_msg=False,
              notify_function=None):
        # logger.error('**** Log.write: msg = "{}"'.format(msg))
        # logger.error(f'{p_time = }')
        if self.cursesScreen:
            with self.lock:
                ''' display time '''
                if p_time is not None:
                    self._the_time = p_time
                    self._x_start = len(self._the_time) + 3

                if self._the_time is None:
                    self._x_start = 1

                if self._the_time:
                    # self.cursesScreen.erase()
                    try:
                        # color pair: 6 or 9
                        self.cursesScreen.addstr(
                            0, 0,
                            ' ' +self._the_time + ' ',
                            curses.color_pair(self._cnf.time_color)
                        )
                    except:
                        pass
                if self.asked_to_stop:
                    self.asked_to_stop = False
                    self.counter = None
                    self._player_stopped = 0
                    return
                if p_time is not None:
                    self.cursesScreen.refresh()
                    return

                ''' start normal execution '''
                if msg:
                    if player_start_stop_token[1] in msg or \
                            player_start_stop_token[2] in msg:
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
                    self.msg = msg.strip()
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
                # logger.error('*** msg = "{}"'.format(msg))
                if self.msg:
                    # if self._x_start == 1:
                    #     self.cursesScreen.erase()
                    d_msg = ''
                    if self._x_start == 1:
                        self.cursesScreen.addstr(0, 0, ' ')
                    else:
                        self.cursesScreen.addstr(0, self._x_start-1, ' ')
                    try:
                        d_msg = fix_chars(self.msg.strip()[0: self.width])
                        ## logger.error('printing "{}" at {}'.format(d_msg, self._x_start))
                        self.cursesScreen.addstr(0, self._x_start, d_msg)
                    except:
                        try:
                            if self._the_time is None:
                                d_msg = fix_chars(self.msg.encode('utf-8', 'replace').strip()[0: self.width])
                            else:
                                d_msg = fix_chars(self.msg.encode('utf-8', 'replace').strip()[0: self.width - len(self._the_time) - 3])
                            logger.error('printing "{}" at {}'.format(d_msg, self._x_start))
                            self.cursesScreen.addstr(0, self._x_start, d_msg)
                        except:
                            pass
                            # if logger.isEnabledFor(logging.ERROR):
                            #     logger.error('Error updating the Status Bar')
                    try:
                        self.cursesScreen.clrtoeol()
                    except:
                        logger.error('\n\n\nexcept\n\n\n')
                        pass

                    if msg:
                        if msg.startswith('[Vol:') or msg.startswith('[Muted]'):
                            msg = msg.split('] ')[-1]
                    with self._song_title_lock:
                        if msg:
                            if msg.startswith('Title: '):
                                self._song_title = msg.replace('Title: ', '')
                            elif 'Title: ' in msg:
                                x = msg.index('Title: ')
                                self._song_title = msg[x+7:]
                            elif msg.startswith('mpv: ') or \
                                msg.startswith('mplayer: ') or \
                                msg.startswith('vlc: '):
                                self._song_title = 'Player is stopped!'
                                self._station_that_is_playing_now = ''
                            else:
                                self._song_title = ''
                                if msg.startswith('Playing: '):
                                    self._station_that_is_playing_now = msg[9:]
                                elif msg.startswith('Buffering: '):
                                    self._station_that_is_playing_now = msg[11:]

                    if self._add_chapter_function is not None and msg:
                        if msg.startswith('Title: '):
                            self._add_chapter_function(msg.replace('Title: ', ''))
                    if msg:
                        msg = fix_chars(msg)
                    self.set_win_title(d_msg if d_msg else msg)
                    self._write_title_to_log(msg if msg else 'No')
                    self._show_notification(msg)
                    self._set_web_title(msg)
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
                        curses.color_pair(1)
                    )
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
                # logger.error(
                #     '\n\n(help_msg: {} OR self.display_help_message: {}) AND can display help message: {} AND self.error_msg: {}\n\n'.format(
                #         'yes' if help_msg else 'no',
                #         'yes' if self.display_help_message else 'no',
                #         'yes' if self.can_display_help_msg(msg) else 'no',
                #         'no' if self.error_msg else 'yes'
                #     )
                # )
                if (help_msg or self.display_help_message) and self.can_display_help_msg(msg):
                    # logger.error('I am in')
                    if not self.error_msg:
                        # logger.error('I display ?')
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
                    ## logger.debug('Press ? for help: no')
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

    def _set_web_title(self, msg):
        if msg:
            if msg.startswith('[V') or \
                    msg.startswith('retry: '):
                return
            old_song_title = ''
            server = self._get_web_song_title()
            if server:
                ''' remote control server running '''
                title = None
                # if msg.startswith('Playing: ') or \
                #         msg.startswith('Connecting to: ') or \
                #         msg.startswith('Initialization: ') or \
                #         'abnormal' in msg:
                #    title = msg
                if msg.startswith('Playing: ') or \
                        msg.startswith('Buffering: ') or \
                        msg.startswith('Connecting to: ') or \
                        'abnormal' in msg or \
                        msg.startswith('Failed to'):
                    title = msg
                    with self._song_title_lock:
                        old_song_title = self._song_title
                        self._song_title = title
                elif 'Title: ' in msg:
                    x = msg.index('Title: ')
                    title = msg[x+7:]
                else:
                    with self._song_title_lock:
                        if self._song_title:
                            title = self._song_title
                if title:
                    title = title.replace('Initialization', 'Connecting to')
                    server.send_song_title(title)
                    if old_song_title:
                        with self._song_title_lock:
                            self._song_title = old_song_title


    def _get_icon_path(self):
        self.icon_path = self._cnf.notification_image_file
        if self.icon_path is None:
            if platform_system().lower().startswith('win'):
                the_path = (
                    join(getenv('APPDATA'), 'pyradio', 'help', 'pyradio.ico'),
                    join(dirname(__file__), 'icons', 'pyradio.ico')
                )
            else:
                the_path = (
                    join(self._cnf.data_dir, 'pyradio.png'),
                    join(dirname(__file__), 'icons', 'pyradio.png'),
                    '/usr/share/icons/pyradio.png',
                    '/usr/local/share/icons/pyradio.png'
                )
            for n in the_path:
                if exists(n):
                    self.icon_path = n
                    break
        self._repeat_notification.icon_path = self.icon_path

    def _show_notification(self, msg):
        self._enable_notifications = int(self._cnf.enable_notifications)
        if self._enable_notifications < 30:
            self._stop_desktop_notification_thread = True
            self._desktop_notification_thread = None
        else:
            self._stop_desktop_notification_thread = False
        if self._enable_notifications == -1:
            return

        if msg:
            if msg.startswith('mpv: ') or \
                    msg.startswith('mplayer: ') or \
                    msg.startswith('vlc: ') or \
                    msg.startswith('Station: ') or \
                    msg.startswith('Init'):
                self._cnf._current_notification_message = ''
                self._station_sent = False
                self._stop_desktop_notification_thread = True
                self._desktop_notification_thread = None
                self._last = ['', '']
                return

            if msg.startswith('[Muted] '):
                self._cnf._current_notification_message = ''
                self._station_sent = True
                self._stop_desktop_notification_thread = True
                self._desktop_notification_thread = None
                return

            self._get_icon_path()
            if platform.lower().startswith('win'):
                if HAS_WIN10TOAST:
                    d_title, d_msg = self._get_desktop_notification_data(msg)
                    if d_msg:
                        if self._cnf._current_notification_message != d_msg:
                            # toast = Notification(app_id="PyRadio",
                            #                      title=d_title,
                            #                      msg=d_msg,
                            #                      icon="C:\\Users\\spiros\\AppData\\Roaming\\pyradio\\help\\pyradio.ico")

                            # toast.show()
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Sending Desktop Notification: [{0}, {1}, {2}]'.format(d_title, d_msg, self.icon_path))
                            self._desktop_notification_message = d_msg
                            self._desktop_notification_title = d_title
                            try:
                                with self._desktop_notification_lock:
                                    toaster.show_toast(
                                        d_title, d_msg, threaded=True,
                                        icon_path=self.icon_path
                                    )
                            except:
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug('Failure sending Desktop Notification!')
                                return
                            if d_title == 'Station':
                                self._station_sent = True
                            self._cnf._current_notification_message = d_msg
                            if self._desktop_notification_thread is None:
                                if self._enable_notifications > 0:
                                    self._desktop_notification_thread = threading.Thread(
                                        target=self._repeat_notification._desktop_notification_handler,
                                        args=(lambda: self._desktop_notification_title,
                                              lambda: self._desktop_notification_message,
                                              lambda: self._stop_desktop_notification_thread,
                                              lambda: self._enable_notifications,
                                              None, self._desktop_notification_lock
                                              )
                                    )
                                    self._desktop_notification_thread.start()
                            else:
                                self._repeat_notification.reset_timer()

            else:
                if self._cnf._notification_command and \
                        self._cnf.enable_notifications:
                    d_title, d_msg = self._get_desktop_notification_data(msg)
                    if d_msg:
                        if self._cnf._current_notification_message != d_msg:
                            notification_command = self._repeat_notification._populate_notification_command(self._cnf._notification_command, d_title, d_msg)
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Sending Desktop Notification: {}'.format(notification_command))
                            self._desktop_notification_message = d_msg
                            self._desktop_notification_title = d_title
                            try:
                                with self._desktop_notification_lock:
                                    subprocess.Popen(
                                        notification_command,
                                        stdout=subprocess.DEVNULL,
                                        stderr=subprocess.DEVNULL
                                    )
                            except:
                                if logger.isEnabledFor(logging.DEBUG):
                                    logger.debug('Failure sending Desktop Notification!')
                                return
                            if d_title == 'Station':
                                self._station_sent = True
                            self._cnf._current_notification_message = d_msg
                            if self._desktop_notification_thread is None:
                                if self._enable_notifications > 0:
                                    self._desktop_notification_thread = threading.Thread(
                                        target=self._repeat_notification._desktop_notification_handler,
                                        args=(lambda: self._desktop_notification_title,
                                              lambda: self._desktop_notification_message,
                                              lambda: self._stop_desktop_notification_thread,
                                              lambda: self._enable_notifications,
                                              self._cnf._notification_command,
                                              self._desktop_notification_lock
                                              )
                                    )
                                    self._desktop_notification_thread.start()
                                else:
                                    logger.error('Not starting Desktop Notification Thread!!! thread = {0}, enable_notifications = {1}'.format(self._desktop_notification_thread, self._enable_notifications))
                            else:
                                self._repeat_notification.reset_timer()

    def _get_desktop_notification_data(self, msg):
        if msg.startswith('Title: '):
            d_msg = msg.replace('Title: ', '')
            d_title = 'Now playing'
            if self._last[1] == d_msg:
                ''' already shown this title '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('already shown this title: "{0}" - {1}'.format(d_msg, self._last))
                self._desktop_notification_message = d_msg
                return None, None
            self._last[1] = d_msg
        elif msg.startswith('Playing: ') or \
                msg.startswith('Buffering: '):
            if self._station_sent:
                return None, None
            d_title = 'Station'
            d_msg = msg.replace('Playing: ', '').replace('Buffering: ', '')
            # if self._last[1]:
            #     ''' already shown song title '''
            #     logger.error('already shown song title: "{0}" - {1}'.format(d_msg, self._last))
            #     return None, None
            if self._last[0] == d_msg:
                ''' already shown song title '''
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('already shown station name: "{0}" - {1}'.format(d_msg, self._last))
                return None, None
            self._last[0] = d_msg
        elif msg.startswith('[Muted] '):
            d_title = 'Player muted!'
            d_msg = msg.replace('[Muted] ', '')
            self._station_sent = False
        elif 'abnormally' in msg:
            d_title = 'Player Crash'
            d_msg = msg
            self._station_sent = False
        elif msg.startswith('Failed to connect'):
            sp = msg.split(':')
            d_title = sp[0]
            d_msg = sp[1]
            self._station_sent = False
        else:
            return None, None
        return d_title, d_msg

    def _write_title_to_log(self, msg=None, force=False):
        # logger.error('\n\nmsg = "{}"'.format(msg))
        if msg is None:
            d_msg = None
        else:
            d_msg = msg.replace('[Muted] ', '')
        if msg == 'No':
            return
        if d_msg is None and self._cnf._current_log_title:
            try:
                logger.critical(self._cnf._current_log_title.replace('Title: ', '    ') + ' (LIKED)')
                self._cnf._last_liked_title = self._cnf._current_log_title
            except:
                logger.critical('Error writing LIKED title...')
        else:
            if d_msg:
                if d_msg.startswith('Initialization: '):
                    self._started_station_name = d_msg[16:]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Early station name (initialization): "{}"'.format(self._started_station_name))
                if d_msg.startswith('Station: ') and ' - Opening connection' in d_msg:
                    self._started_station_name = d_msg[9:].split(' - Opening connection')[0]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Early station name (station): "{}"'.format(self._started_station_name))

                if d_msg.startswith('Title: '):
                    ''' print Early station name '''
                    if self._started_station_name is not None:
                        try:
                            try:
                                logger.critical('>>> Station: ' + self._started_station_name)
                                self._started_station_name = None
                            except:
                                logger.critical('>>> Error writing station name...')
                            # self._cnf._old_log_title = d_msg
                        except UnicodeDecodeError:
                            ''' try to handle it for python2 '''
                            try:
                                if force or d_msg.decode('utf-8', 'replace') not in self._cnf._old_log_title.decode('utf-8', 'replace'):
                                    try:
                                        logger.critical('>>> Station: ' + self._started_station_name.decode('utf-8', 'replace'))
                                        self._started_station_name = None
                                    except:
                                        logger.critical('>>> Error writing station name...')
                                    self._cnf._old_log_title = d_msg
                            except:
                                logger.critical('>>> Error writing station name...')

                    try:
                        if force or d_msg not in self._cnf._old_log_title:
                            try:
                                logger.critical(d_msg.replace('Title: ', '    '))
                            except:
                                logger.critical('Error writing title...')
                            self._cnf._old_log_title = d_msg
                    except UnicodeDecodeError:
                        ''' try to handle it for python2 '''
                        try:
                            if force or d_msg.decode('utf-8', 'replace') not in self._cnf._old_log_title.decode('utf-8', 'replace'):
                                try:
                                    logger.critical(d_msg.replace('Title: ', '    '))
                                except:
                                    logger.critical('Error writing title...')
                                self._cnf._old_log_title = d_msg
                        except:
                            logger.critical('Error writing title...')
                    self._cnf._current_log_title = d_msg
                elif d_msg.startswith('Playing: ') or \
                          d_msg.startswith('Buffering: '):
                    if d_msg[0] == 'P':
                        tok = 'Playing: '
                    else:
                        tok = 'Buffering: '
                    if logger.isEnabledFor(logging.CRITICAL) and tok == 'Playing: ':
                        try:
                            if force or d_msg not in self._cnf._old_log_station:
                                try:
                                    logger.critical(d_msg.replace(tok, '>>> Station: '))
                                except:
                                    logger.critical('>>> Error writing station name...')
                                self._cnf._old_log_station = d_msg
                                self._started_station_name = None
                        except UnicodeDecodeError:
                            ''' try to handle it for python2 '''
                            try:
                                if force or d_msg.decode('utf-8', 'replace') not in self._cnf._old_log_title.decode('utf-8', 'replace'):
                                    try:
                                        logger.critical(d_msg.replace(tok, '>>> Station: '))
                                    except:
                                        logger.critical('>>> Error writing station name...')
                                    self._cnf._old_log_station = d_msg
                                    self._started_station_name = None
                            except:
                                logger.critical('>>> Error writing station name...')
                    self._cnf._current_log_station = d_msg

    def write_start_log_station_and_title(self):
        if self._cnf._current_log_station:
            # logger.error('self._cnf._current_log_station = "{}"'.format(self._cnf._current_log_station))
            self._write_title_to_log(self._cnf._current_log_station, force=True)
        if self._cnf._current_log_title:
            # logger.error('self._cnf._current_log_title = "{}"'.format(self._cnf._current_log_title))
            self._write_title_to_log(self._cnf._current_log_title, force=True)

    def _get_startup_window_title(self):
        if not platform.lower().startswith('win'):
            user = getenv('USER')
            host = getenv('HOSTNAME')
            pwd = getenv('PWD')
            if user and host:
                self._startup_title = user + '@' + host
            else:
                if user:
                    self._startup_title = '-= ' + user + ' - ' + pwd + ' =-'
                else:
                    self._startup_title = '-= ' + pwd + ' =-'

    def _restore_startup_window_title(self):
        if self._startup_title is not None:
            stdout.write('\33]0;' + self._startup_title + '\a')
            stdout.flush()

    @staticmethod
    def set_win_title(msg=None):
        default = 'Your Internet Radio Player'
        just_return = (
            'Config saved',
            'Online service Config',
            'Error saving config',
            'Already at',
            'History is empty',
            'Operation not supported',
            'Please wait for the player to settle',
            'Volume: ',
        )
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
        # if logger.isEnabledFor(logging.DEBUG):
        #     if msg is None:
        #         logger.debug('set_win_title(): msg is None')
        #     else:
        #         logger.debug('set_win_title(): msg = "' + msg + '"')
        if msg is None:
            # if logger.isEnabledFor(logging.DEBUG):
            #     logger.debug('set_win_title(): d_msg = default')
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
                # no update
                for a_return_token in just_return:
                    if a_return_token in msg:
                        return
                # if stopped...
                for a_stop_token in do_not_update:
                    if a_stop_token in msg:
                        # if logger.isEnabledFor(logging.DEBUG):
                        #     logger.debug('set_win_title(): d_msg = default')
                        d_msg = default
                        token_id = 0
                        break

                if Log.old_window_title == d_msg:
                    # if logger.isEnabledFor(logging.DEBUG):
                    #     logger.debug('set_win_title(): same title... return')
                    return
                Log.old_window_title = d_msg

                # if logger.isEnabledFor(logging.DEBUG):
                #     logger.debug('set_win_title(): d_msg = "' + d_msg + '"')

        if token_id == 0 and Log.locked:
            d_msg += ' (Session Locked)'

        if platform.lower().startswith('win'):
            ctypes.windll.kernel32.SetConsoleTitleW(tokens[token_id] + d_msg)
        else:
            stdout.write('\33]0;' + tokens[token_id] + d_msg + '\a')
            stdout.flush()


class RepeatDesktopNotification():

    def __init__(self, config, timeout):
        self._cnf = config
        self._a_lock = self._start_time = None
        self.timeout = timeout

    @property
    def start_time(self):
        return self._start_time

    @start_time.setter
    def start_time(self, value):
        with self._a_lock:
            self._start_time = value
            end_time = value + datetime.timedelta(seconds=self.timeout())
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Setting repetative Desktop Notification timer to: {}'.format(end_time))

    def reset_timer(self):
        self.start_time = datetime.datetime.now()

    def _desktop_notification_handler(
            self,
            m_title,
            m_msg,
            stop,
            time_out,
            a_notification_command,
            a_lock):
        '''
        threaded Desktop Notification handler

        args=(lambda: self._desktop_notification_title,
              lambda: self._desktop_notification_message,
              lambda: self._stop_desktop_notification_thread,
              lambda: self._enable_notifications,
              notification_command,
              lock))
        '''

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Desktop Notification Thread started!!!')
        self._a_lock = a_lock
        self.start_time = datetime.datetime.now()
        while True:
            my_time_out = time_out()
            while True:
                sleep(.1)
                if stop() or my_time_out < 30:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Desktop Notification Thread stopped!!!')
                    return
                with a_lock:
                    end_time = self._start_time + datetime.timedelta(seconds=my_time_out)
                diff = (end_time - datetime.datetime.now()).seconds
                # logger.error('diff = {}'.format(diff))
                if diff >= my_time_out:
                    self.start_time = datetime.datetime.now()
                    break

            d_title = m_title().replace('Now', 'Still').replace('Station', 'Still playing Station')
            d_msg = m_msg()
            if platform.lower().startswith('win'):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Sending repetative Desktop Notification: [{0}, {1}, {2}]'.format(d_title, d_msg, self.icon_path))
                try:
                    with a_lock:
                        toaster.show_toast(
                            d_title, d_msg, threaded=True,
                            icon_path=self.icon_path
                        )
                        end_time = self._start_time + datetime.timedelta(seconds=my_time_out)
                except:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Failure sending repetative Desktop Notification!')
            else:
                notification_command = self._populate_notification_command(a_notification_command, d_title, d_msg)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Sending repetative Desktop Notification: {}'.format(notification_command))
                try:
                    with a_lock:
                        subprocess.Popen(
                            notification_command,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL
                        )
                        end_time = self._start_time + datetime.timedelta(seconds=my_time_out)
                except:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Failure sending repetative Desktop Notification!')

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Desktop Notification Thread stopped!!!')

    def _populate_notification_command(self, a_notification_command, d_title, d_msg):
        notification_command = deepcopy(a_notification_command)
        for i in range(0, len(notification_command)):
            if 'TITLE' in notification_command[i]:
                notification_command[i] = notification_command[i].replace('TITLE', d_title)
            if 'MSG' in notification_command[i]:
                notification_command[i] = notification_command[i].replace('MSG', d_msg)
            if 'ICON' in notification_command[i]:
                icon = self.icon_path
                notification_command[i] = notification_command[i].replace('ICON', icon)
        return notification_command

