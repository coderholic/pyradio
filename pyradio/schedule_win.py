# -*- coding: utf-8 -*-
from sys import exit
from datetime import date, datetime, timedelta
from calendar import monthrange
from time import sleep
import curses
import logging
import threading
import platform

from .simple_curses_widgets import DisabledWidget, SimpleCursesCheckBox, SimpleCursesPushButton, SimpleCursesTime, SimpleCursesString, SimpleCursesDate, SimpleCursesLineEdit
from .cjkwrap import cjklen, cjkslices
from .schedule import PyRadioScheduleItem, PyRadioScheduleItemType, PyRadioScheduleTimeType, PyRadioTime, PyRadioScheduleList, format_date_to_iso8851, random_string, datetime_to_my_time, is_date_before

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

class PyRadioSimpleScheduleWindow(object):

    _X = _Y = _maxY = maxX = 0
    _widgets = _win = None
    _global_functions = {}
    _showed = False
    _too_small = False
    _stop = False
    _thread_date = None
    _error_num = 0
    _error_messages = {
        3: 'Item is invalid!',
        6: 'Start time is in the past!',
        7: 'End time is in the past!',
        8: 'Start time is after End time!'
    }

    _repeat = (
        'day',
        'week',
        'month',
        'Monday',
        'Tuesday',
        'Wednesday',
        'Thursday',
        'Friday',
        'Saturday',
        'Sunday'
            )
    _max_repeat_len = max([len(x) for x in _repeat])
    _repeat_index = 0

    '''     0  1  2   3  4  5   6   7  8  9  10 11 12 13 14  15  16  17  18  19  20  21  22 23'''
    _up = (23, 0, 1, 19, 2, 3, 21, 22, 4, 5, 8, 9, 6, 7, 10, 14, 11, 15, 17, 16, 18, 12, 13, 20)

    lock = threading.Lock()
    _tips = (
        'The playlist to open',
        'The stations to play',
        'Enable Start Timer (time to start playback)',
        'The date the playback will start',
        'Absolute time to start playback',
        'Absolute time to start playback',
        'Start playback XX:XX:XX after the time "OK" is pressed',
        'Start playback XX:XX:XX after the time "OK" is pressed',
        'Enable Stop Timer (time to stop playback)',
        'The date the playback will stop',
        'Absolute time to stop playback',
        'Absolute time to stop playback',
        'Stop playback XX:XX:XX after the time "OK" is pressed',
        'Stop playback XX:XX:XX after the time "OK" is pressed',
        'The player to use',
        'Enable recording the station to a file',
        'Play no sound while recording',
        'Enable buffering (using default parameters)',
        'Enable recurrence for this setup',
        'Recurrence parameter for this setup',
        'Remove this schedule',
        'Save changes to this schedule item',
        'Cancel changes to this schedule item',
        'Optional name for this item'
    )

    def __init__(
            self, parent,
            supported_players,
            current_player,
            my_op_mode,
            cur_op_mode,
            playlist=None, station=None,
            schedule_item=None,
            global_functions={}
    ):
        self._exit = False
        self._my_op_mode = my_op_mode
        self._cur_op_mode = cur_op_mode
        self._playlist = playlist
        self._station = station
        self._supported_players = supported_players
        self._maxX = 60
        self._displacement = 3
        self._maxY = 20
        self._global_functions = global_functions
        self._get_parent(parent)
        self._focus = 8
        try:
            self._current_player_id = supported_players.index(current_player)
        except ValueError:
            self._current_player_id = 0
        self._player_id = self._current_player_id
        self.set_item(schedule_item, playlist, station)

    def __del__(self):
        self._exit = True
        self._stop = True

    def exit(self):
        self._stop = True
        self._exit = True

    @property
    def too_small(self):
        return self._too_small

    @property
    def playlist(self):
        return self._schedule_item.item['playlist']

    @playlist.setter
    def playlist(self, val):
        self._schedule_item.item['playlist'] = val
        self._widgets[0].string = val

    @property
    def station(self):
        return self._schedule_item.item['station']

    @station.setter
    def station(self, val):
        self._schedule_item.item['station'] = val
        self._widgets[1].string = val

    def get_error_message(self):
        return self._error_messages[self._error_num]

    def set_item(self, schedule_item=None, playlist=None, station=None):
        if schedule_item is None:
            self._schedule_item = PyRadioScheduleItem()
            self._schedule_item.item['type'] = 0
            self._schedule_item.item['end_date'] = [2023, 11, 12]
            self._schedule_item.item['end_time'] = [20, 1, 2, 0]
            self._schedule_item.item['start_duration'] = [1, 32, 15, 0]
            self._schedule_item.item['end_duration'] = [3, 15, 2, 0]
            self._schedule_item.item['repeat'] = 'Sunday'
            if playlist:
                self._schedule_item.playlist = playlist
            if station:
                self._schedule_item.station = station
            self._remove_enabled = False
        else:
            self._schedule_item = PyRadioScheduleItem(schedule_item)
            self._remove_enabled = True

        logger.error('set_item')
        for n in self._schedule_item.item:
            logger.error('{0}: {1}'.format(n, self._schedule_item.item[n]))

        ''' parse and assign values '''

    def _move_widgets(self):
        # self._widgets[0].move(1,2)
        # self._widgets[1].move(2,2)
        # Start
        self._widgets[2].move(6 + self._Y, 5 + self._X)
        self._widgets[3].move(6, self._widgets[2].X + self._widgets[2].width - self._X)
        self._widgets[4].move(7 + self._Y, 9 + self._X)
        self._widgets[5].move(7, self._widgets[4].X + self._widgets[4].width - self._X)
        self._widgets[6].move(7 + self._Y, self._X + self._widgets[5].X + self._widgets[5].width + 4)
        self._widgets[7].move(7, self._widgets[6].X + self._widgets[6].width - self._X)
        # End
        self._widgets[8].move(8 + self._Y, 5 + self._X)
        self._widgets[9].move(8, self._widgets[8].X + self._widgets[8].width - self._X)
        self._widgets[10].move(9 + self._Y, 9 + self._X)
        self._widgets[11].move(9, self._widgets[10].X + self._widgets[10].width - self._X)
        self._widgets[12].move(9 + self._Y, self._X + self._widgets[11].X + self._widgets[11].width + 4)
        self._widgets[13].move(9, self._widgets[12].X + self._widgets[12].width - self._X)
        # options
        # self._widgets[14].move(8, 3)
        self._widgets[15].move(8 + self._displacement + self._Y, self._X + 9)
        self._widgets[16].move(8 + self._displacement + self._Y, self._widgets[15].X + self._widgets[15].width + 4)
        self._widgets[17].move(9 + self._displacement + self._Y, self._X + 9)
        self._widgets[18].move(10 + self._displacement + self._Y, self._X + 5)
        # self._widgets[19].move(8 + self._displacement + self._Y, self._widgets[17].X + self._widgets[18].width)
        # Buttons
        self._widgets[20].move(12 + self._displacement + self._Y, self._X + 2)
        self._widgets[21].move(self._widgets[20].Y, self._X + self._maxX - 19)
        self._widgets[22].move(self._widgets[20].Y, self._X + self._maxX - (len(self._widgets[13].caption) + 12))
        self._widgets[23].move(
                self._win,
                self._Y + self._widgets[0].Y - 1,
                self._X + 12,
                )

    def _get_parent(self, parent):
        self._parent = parent
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        new_Y = int((self._parent_maxY - self._maxY) / 2) + 1
        new_X = int((self._parent_maxX - self._maxX) / 2)
        if self._Y != new_Y or self._X != new_X:
            self._Y = new_Y
            self._X = new_X
        self._win = curses.newwin(self._maxY, self._maxX, self._Y, self._X)
        self._init_win()

    def _init_win(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._print_header()

    def _print_header(self):
        msg = ' Simple Scheduling '
        self._win.addstr(
            0, int((self._maxX - len(msg)) / 2),
            msg, curses.color_pair(11)
        )

    def move(self, new_Y=None, new_X=None):
        if new_Y:
            self._Y = new_Y
        if new_X:
            self._X = new_X
        if self._win:
            self._win.mvwin(self._Y, self._X)

    def _add_widgets(self):
        self._widgets = []

        ''' id 0 playlist string '''
        self._widgets.append(
            SimpleCursesString(
                Y=2,X=2,
                parent=self._win,
                caption='Playlist: ',
                string='Any playlist',
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
                max_selection = 46
            )
        )
        self._widgets[-1].w_id = 0

        ''' id 1 stations string '''
        self._widgets.append(
            SimpleCursesString(
                Y=3, X=2,
                parent=self._win,
                caption=' Station: ',
                string='Any station',
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
                max_selection = 46
            )
        )
        self._widgets[-1].w_id = 1

        ''' id 2 start check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'Start playback on: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 2

        ''' id 3 start at date box '''
        self._widgets.append(
            SimpleCursesDate(
                Y=0, X=0,
                window=self._win,
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions
            )
        )
        self._widgets[-1].w_id = 3

        ''' id 4 start at check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'At: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 4

        ''' id 5 start at time '''
        self._widgets.append(
            SimpleCursesTime(
                Y=7, X=0,
                window=self._win,
                color=curses.color_pair(10),
                show_am_pm=True,
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions,
                string=PyRadioTime.pyradio_time_to_string(self._schedule_item.item['start_time'])
            )
        )
        self._widgets[-1].w_id = 5

        ''' id 6 start in check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'In: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 6

        ''' id 7 start in time '''
        self._widgets.append(
            SimpleCursesTime(
                Y=7, X=0,
                window=self._win,
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions,
                string=PyRadioTime.pyradio_time_to_string(self._schedule_item.item['start_duration'])
            )
        )
        self._widgets[-1].w_id = 7

        ''' id 8 stop check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0,0, 'End playback on: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 8

        ''' id 9 stop at date box '''
        self._widgets.append(
            SimpleCursesDate(
                Y=7, X=0,
                window=self._win,
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions
            )
        )
        self._widgets[-1].w_id = 9

        ''' id 10 stop at check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'At: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 10

        ''' id 11 stop at time '''
        self._widgets.append(
            SimpleCursesTime(
                Y=9, X=0,
                window=self._win,
                show_am_pm=True,
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions,
                string=PyRadioTime.pyradio_time_to_string(self._schedule_item.item['end_time'])
            )
        )
        self._widgets[-1].w_id = 11

        ''' id 12 stop in check box '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'In: ',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 12

        ''' id 13 stop in time '''
        self._widgets.append(
            SimpleCursesTime(
                Y=9,X=0,
                window=self._win,
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                next_widget_func=self._next_widget,
                previous_widget_func=self._previous_widget,
                global_functions=self._global_functions,
                string=PyRadioTime.pyradio_time_to_string(self._schedule_item.item['end_duration'])
            )
        )
        self._widgets[-1].w_id = 13


        ''' id 14 player '''
        self._widgets.append(
            SimpleCursesString(
                Y=10, X=3,
                parent=self._win,
                caption='Player: ',
                string=self._supported_players[self._current_player_id],
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
                max_selection = 10
            )
        )
        self._widgets[-1].w_id = 14

        ''' id 15 recording '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'Record to file',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 15

        ''' id 16 silent recording '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'Silent recording',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 16

        ''' id 17 buffering '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'Use buffering',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 17

        ''' id 18 cancel scheduling button '''
        self._widgets.append(
            SimpleCursesCheckBox(
                0, 0, 'Repeat every:',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 18

        ''' id 19 silent recording '''
        self._widgets.append(
            SimpleCursesString(
                Y=13,
                X=23,
                parent=self._win,
                caption='',
                string='day',
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
                max_selection = 10
            )
        )
        self._widgets[-1].w_id = 19

        ''' id 20 cancel scheduling button '''
        cap = 'Remove Schedule'
        self._widgets.append(SimpleCursesPushButton(
            Y=12 + self._displacement + self._Y,
            X=self._X + 2,
            caption=cap,
            color_focused=curses.color_pair(9),
            color=curses.color_pair(11),
            bracket_color=curses.color_pair(10),
            parent=self._parent))
        self._widgets[-1].w_id = 20

        ''' id 21 ok button '''
        cap = 'OK'
        self._widgets.append(SimpleCursesPushButton(
            Y=0, X=0,
            caption=cap,
            color_focused=curses.color_pair(9),
            color=curses.color_pair(11),
            bracket_color=curses.color_pair(10),
            parent=self._parent))
        self._widgets[-1].w_id = 21

        ''' id 22 cancel button '''
        cap = 'Cancel'
        self._widgets.append(SimpleCursesPushButton(
            Y=0, X=0,
            caption=cap,
            color_focused=curses.color_pair(9),
            color=curses.color_pair(11),
            bracket_color=curses.color_pair(10),
            parent=self._parent))
        self._widgets[-1].w_id = 22

        self._widgets.append(SimpleCursesLineEdit(
            parent=self._win,
            width=46,
            begin_y=self._Y + self._widgets[0].Y - 1,
            begin_x=self._X + 12,
            boxed=False,
            has_history=False,
            caption='',
            box_color=curses.color_pair(9),
            caption_color=curses.color_pair(11),
            edit_color=curses.color_pair(9),
            cursor_color=curses.color_pair(8),
            unfocused_color=curses.color_pair(10),
            key_up_function_handler=self._go_up,
            key_down_function_handler=self._go_down,
            key_tab_function_handler=self._next_widget,
            key_stab_function_handler=self._previous_widget
            )
        )
        ''' enables direct insersion of ? and \ '''
        self._widgets[-1]._paste_mode = False
        self._widgets[-1].w_id = 23
        self._widgets[-1].string = self._schedule_item.item['name']

        self._move_widgets()

    def show(self, parent=None):
        if parent:
            self._get_parent(parent)
            if self._showed:
                self._move_widgets()
        if self._widgets == None:
            self._add_widgets()
        with self.lock:
            try:
                self._win.addstr(self._maxY-3, 2, '─' * (self._maxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(self._maxY-3, 2, '─'.encode('utf-8') * (self._maxX - 4), curses.color_pair(3))
            self._win.addstr(self._maxY-3, 3, ' Tip ', curses.color_pair(11))
        disp_msg = self._tips[self._focus]
        # if self._focus in (4, 9) and \
        #         not self._stop_only():
        #     disp_msg = self._tips[self._focus].replace('the time "OK" is pressed.', 'starting playback.')
        with self.lock:
            self._win.addstr(1, 6, 'Name: ',  curses.color_pair(10))
            self._win.addstr(self._maxY-2, 2, disp_msg.ljust(self._maxX-4), curses.color_pair(10))
            self._win.refresh()

        if self._widgets:
            if not self._showed:
                self._dummy_enable()
            self._fix_focus()
            for n in range(0, len(self._widgets)):
                if n == len(self._widgets) -1:
                    self._widgets[n].show(parent_win=self._win, opening=False)
                else:
                    try:
                        with self.lock:
                            self._widgets[n].show(self._win)
                    except:
                        logger.error('exception!')
                        with self.lock:
                            self._widgets[n].show()
        self._win.refresh()
        self._showed = True
        if self._thread_date is None:
            self._thread_date = threading.Thread(
                target=self._thread_show_date,
                args =(
                    lambda: self._win,
                    self.lock,
                    lambda: self._can_show_date,
                    lambda: self._stop
                )
            )
            self._thread_date.start()

    def _can_show_date(self):
        if self._too_small:
            return False
        if self._my_op_mode == self._cur_op_mode():
            return True
        return False

    def _apply_repeat_to_widget(self, repeat):
        if repeat is None:
            self._widgets[18].enabled = False
            self._widgets[19].enabled = False
            self._repeat_index = 0
        else:
            self._widgets[19].enabled = True
            if repeat in self._repeat:
                self._repeat_index = self._repeat.index(repeat)
            else:
                self._repeat_index = 0
        self._widgets[19].string = self._repeat[self._repeat_index].ljust(self._max_repeat_len)

    def _dummy_enable(self):
        logger.error('\n\n{}\n\n'.format(self._schedule_item.item))
        ''' assign values '''
        self._widgets[3].date = self._schedule_item.item['start_date']
        self._widgets[5].time = self._schedule_item.item['start_time']
        self._widgets[7].time = self._schedule_item.item['start_duration']
        self._widgets[9].date = self._schedule_item.item['end_date']
        self._widgets[11].time = self._schedule_item.item['end_time']
        self._widgets[13].time = self._schedule_item.item['end_duration']
        if self._schedule_item.item['recording'] == 1:
            self._widgets[15].checked = True
            self._widgets[16].checked = False
        elif self._schedule_item.item['recording'] == 2:
            self._widgets[15].checked = True
            self._widgets[16].checked = True
        else:
            self._widgets[15].checked = False
            self._widgets[16].checked = False
        if self._schedule_item.item['buffering'] == 0:
            self._widgets[17].checked = False
        else:
            self._widgets[17].checked = True
        if self._schedule_item.item['repeat'] is None:
            self._widgets[18].checked = False
            self._widgets[19].checked = False
        else:
            self._widgets[18].checked = True
            self._widgets[19].checked = False

        if self._schedule_item.item['type'] == PyRadioScheduleItemType.TYPE_END:
            self._widgets[0].string = 'Any playlist'
            self._widgets[1].string = 'Any station'
            self._widgets[0].enabled = False
            self._widgets[1].enabled = False
            rec = False
            start_fields = False
            end_fields = True
        else:
            self._widgets[0].string = self._schedule_item.item['playlist']
            self._widgets[1].string = self._schedule_item.item['station']
            self._widgets[0].enabled = True
            self._widgets[0].enabled = True
            rec = True
            start_fields = True
            end_fields = True
        # enable: set start fields
        for i in range(3, 8):
            self._widgets[i].enabled = start_fields
        # enable: set end fields
        for i in range(9, 14):
            self._widgets[i].enabled = end_fields
        # enable: set recording, buffering, repeat
        for i in range(14, 20):
            self._widgets[i].enabled = rec

        self._apply_repeat_to_widget(self._schedule_item.item['repeat'])
        if self._schedule_item.item['type'] == PyRadioScheduleItemType.TYPE_END:
            self._widgets[4].checked = True
            self._widgets[8].enabled = True
            self._widgets[8].checked = True
            if self._schedule_item.item['end_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                self._widgets[10].checked = True
                self._focus = 10
            else:
                self._widgets[13].checked = True
                self._focus = 13
            self._widgets[18].enabled = False
            self._widgets[20].enabled = self._remove_enabled
        elif self._schedule_item.item['type'] == PyRadioScheduleItemType.TYPE_START:
            self._widgets[10].checked = True
            self._widgets[2].enabled = True
            self._widgets[2].checked = True
            if self._schedule_item.item['start_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                self._widgets[4].checked = True
                self._focus = 4
            else:
                self._widgets[6].checked = True
                self._focus = 6
        else:
            self._widgets[4].checked = True
            self._widgets[8].enabled = True
            self._widgets[8].checked = True
            if self._schedule_item.item['end_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                self._widgets[10].checked = True
            else:
                self._widgets[13].checked = True
            self._widgets[10].checked = True
            self._widgets[2].enabled = True
            self._widgets[2].checked = True
            if self._schedule_item.item['start_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                self._widgets[4].checked = True
                self._focus = 4
            else:
                self._widgets[6].checked = True
                self._focus = 6

    def _stop_only(self):
        if ((not self._widgets[2].checked) and \
                self._widgets[8].checked) or \
                (not (self._widgets[2].checked and self._widgets[8].checked)):
            return True
        return False

    def _fix_focus(self):
        for i in (2, 8):
            for k in range(1, 6):
                # logger.error('setting {}'.format(i+k))
                self._widgets[i+k].enabled = self._widgets[i].checked

        for i in range(14, 20):
            # logger.debug('{0} enabled is now {1}'.format(i, self._widgets[2].checked))
            self._widgets[i].enabled = self._widgets[2].checked

        self._widgets[-2].enabled = self._widgets[2].checked or self._widgets[8].checked

        for i in (4, 6, 10, 12):
            if self._widgets[i].enabled:
                self._widgets[i+1].enabled = self._widgets[i].checked

        # for n in ((6,3), (12, 9)):
        #     if self._widgets[n[0]].enabled and \
        #             self._widgets[n[0]].checked:
        #         self._widgets[n[1]].enabled = False
        #     else:
        #         self._widgets[n[1]].enabled = True

        for i in (15, 18):
            if self._widgets[i].enabled:
                self._widgets[i+1].enabled = self._widgets[i].checked

        self._fix_recording_from_player_selection()

        for i in range(0, len(self._widgets)):
            if self._focus == i:
                self._widgets[i].focused = True
            else:
                self._widgets[i].focused = False

    def _go_up(self):
        self._focus = self._up[self._focus]
        while not self._widgets[self._focus].enabled:
            self._focus = self._up[self._focus]
        if self._focus in (5, 7, 11, 13):
            self._widgets[self._focus].reset_selection()

    def _go_down(self):
        self._focus = self._up.index(self._focus)
        while not self._widgets[self._focus].enabled:
            self._focus = self._up.index(self._focus)
        if self._focus in (5, 7, 11, 13):
            self._widgets[self._focus].reset_selection()

    def _next_widget(self):
        old_focus = self._focus
        self._focus += 1
        if self._focus >= len(self._widgets):
            self._focus = 0

        while(not self._widgets[self._focus].enabled):
            self._focus += 1

        if self._focus in (5, 7, 11, 13):
            self._widgets[self._focus].reset_selection()
        self.show()

    def _previous_widget(self):
        self._focus -= 1
        if self._focus < 0:
            self._focus = len(self._widgets) - 1

        while(not self._widgets[self._focus].enabled):
            self._focus -= 1
            if self._focus == -1:
                self._focus = len(self._widgets) -1

        if self._focus in (5, 7, 11, 13):
            self._widgets[self._focus].reset_selection(last=True)
        self.show()

    def _form_to_item(self):
        rec = 1 if self._widgets[15].checked else 0
        rep = None
        if self._widgets[18].checked:
            rep = self._widgets[19].string.strip()
        if rec == 1 and self._widgets[16].checked:
            rec = 2
        if self._widgets[2].checked:
            ''' start and stop '''
            playlist = self._widgets[0].string
            station = self._widgets[1].string
            if self._widgets[8].checked:
                the_type = 0
            else:
                the_type = 1

            buf = 1 if self._widgets[17].checked else 0
        else:
            ''' stop only '''
            the_type = 2
            rep = None
            buf = 0
            rec = 0
            playlist = None
            station = None
        tmp_item = PyRadioScheduleItem({
            'type': the_type, # TYPE_START_END, TYPE_START, TYPE_END
            'start_type': 0 if self._widgets[4].checked else 1, # TIME_ABSOLUTE, TIME_RELATIVE
            'start_date':  list(self._widgets[3].date_tuple),
            'start_time': self._widgets[5].get_time()[0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'start_duration': self._widgets[7].get_time()[0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'end_type': 0 if self._widgets[10].checked else 1, # TIME_ABSOLUTE, TIME_RELATIVE
            'end_date': list(self._widgets[9].date_tuple),
            'end_time': self._widgets[11].get_time()[0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'end_duration': self._widgets[13].get_time()[0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'player': self._widgets[14].string,
            'recording': rec,
            'buffering': buf,
            'repeat': rep,
            'playlist': playlist,
            'station': station,
            'token': self._schedule_item.item['token']
        })
        logger.error('--== item ==--')
        for n in tmp_item.item:
            logger.error('{0}: {1}'.format(n, tmp_item.item[n]))
        return tmp_item

    def _show_info(self):
        ret = 10
        if not self._widgets[2].checked and not self._widgets[8].checked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Invalid item')
                self._info_result = '''
                    ________--== |Invalid item| ==--
                    ___No |Start| or |Stop| time specified___
                '''
                return 10
        tmp_item = self._form_to_item()
        ac_tmp_item = tmp_item.get_active_item()
        logger.error('--== active item ==--')
        for n in tmp_item.active_item:
            logger.error('{0}: {1}'.format(n, tmp_item.active_item[n]))
        ac_tmp_item = tmp_item.get_active_item()
        logger.error(ac_tmp_item)

        err_out = []
        error = False
        logger.error('tmp_item.item["repeat"] = {}'.format(tmp_item.item['repeat']))
        if tmp_item.item['repeat'] is None:
            if tmp_item.item['type'] == 0:
                if is_date_before(ac_tmp_item[1], ac_tmp_item[0]):
                    if not error:
                        err_out.append('--== |Invalid item| ==--')
                        error = True
                    err_out.append('|Start time| is after |End time|!')
                elif is_date_before(ac_tmp_item[0], datetime.now()):
                    if not error:
                        err_out.append('--== |Invalid item| ==--')
                        error = True
                    err_out.append('|Start time| is in the |past|!')
                    error = True
                    if is_date_before(ac_tmp_item[1], datetime.now()):
                        if not error:
                            err_out.append('--== |Invalid item| ==--')
                            error = True
                        err_out.append('|Stop time| is in the |past|!')
            elif tmp_item.item['type'] == 1:
                if is_date_before(ac_tmp_item[0], datetime.now()):
                    err_out.append('--== |Invalid item| ==--')
                    err_out.append('|Start time| is in the |past|!')
                    error = True
            elif tmp_item.item['type'] == 2:
                if is_date_before(ac_tmp_item[1], datetime.now()):
                    err_out.append('--== |Invalid item| ==--')
                    err_out.append('|Stop time| is in the |past|!')
                    error = True
        else:
            if tmp_item.item['type'] == 0:
                if is_date_before(ac_tmp_item[1], ac_tmp_item[0]):
                    err_out.append('--== |Invalid item| ==--')
                    err_out.append('|Start time| is after |End time|!')
                    error = True

        out = []
        if tmp_item.item['repeat'] is None or error:
            out.extend(self._format_info_lines(tmp_item.item['type'], ac_tmp_item))
        else:
            # get list of occurrences
            it_count=3 if tmp_item.item['type'] == 0 else 6
            logger.error('\n\n{}\n\n'.format(it_count))
            the_r_list = PyRadioScheduleList(a_file='', a_list=[tmp_item.item])
            the_list = the_r_list.get_list_of_repeating_dates(it_count)
            out.append('Displaying |{}| subsequent occurrences:'.format(it_count))
            for n in the_list:
                out.append('__|#| Start: |' + n[0] + '__')
                if tmp_item.item['type'] == 0:
                    out.append('_____Stop: |' + n[1] + '__')

        if err_out:
            length = max([len(x) for x in out])
            for i in range(len(err_out)):
                num = int((length - len(err_out[i].replace('|', ''))) / 2)
                err_out[i] = num * '_' + err_out[i]
            err_out.append('')
            out = err_out + out

        while max([len(x) for x in out]) < 40:
            for i in range(len(out)):
                out[i] = '__' + out[i] + '__'

        if out[0] != '':
            out.reverse()
            out.append('')
            out.reverse()
        if out[-1] != '':
            out.append('')
        self._info_result = '\n'.join(out)
        logger.error('self._info_result\n{}'.format(self._info_result))
        logger.error('ret = {}'.format(ret))

    def _format_info_lines(self, the_type, item):
        out = []
        if the_type == 0:
            out.append('__# Start: |' + datetime_to_my_time(item[0]) + '__')
            out.append('_____Stop: |' + datetime_to_my_time(item[1]) + '__')
        elif the_type == 1:
            out.append('__# Start: |' + datetime_to_my_time(item[0]) + '__')
        elif the_type == 2:
            out.append('__#__Stop: |' + datetime_to_my_time(item[1]) + '__')
        return out

    def _validate_selection(self):
        ''' validate form input
            Return
              0: All ok
              3: Invalid item
              6: Start time is in the past
              7: Stop time is in the past
              8: Stop time before Start time
        '''
        if not self._widgets[2].checked and not self._widgets[8].checked:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Invalid item')
                return 3
        tmp_item = self._form_to_item()
        logger.error('--== active item ==--')
        for n in tmp_item.active_item:
            logger.error('{0}: {1}'.format(n, tmp_item.active_item[n]))
        logger.error('\n\n{}\n\n'.format(tmp_item))
        ac_tmp_item = tmp_item.get_active_item()
        logger.error(ac_tmp_item)

        if the_type == 2:
            # stop playback
            if ac_tmp_item[0] <= datetime.now():
                if ac_tmp_item[-3] is None:
                    # no repeat
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Stop time is in the past')
                    return 7
        elif ac_tmp_item[-4] is None:
            # start or start and stop
            if ac_tmp_item[0] <= datetime.now():
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Start time is in the past')
                return 6
            if the_type == 0:
                # start and stop
                if ac_tmp_item[1] <= datetime.now():
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Stop time is in the past')
                    return 7
                elif ac_tmp_item[0] >= ac_tmp_item[1]:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Start time < end time')
                    return 8
        self._schedule_item = tmp_item
        return 0

    def _fix_recording_from_player_selection(self):
        if platform.system().lower().startswith('win') and \
                self._widgets[14].string == 'vlc':
            self._widgets[15].enabled = False
            self._widgets[16].enabled = False
        else:
            self._widgets[15].enabled = self._widgets[2].checked
            if self._widgets[15].enabled and \
                    self._widgets[15].checked:
                self._widgets[16].enabled = True
            else:
                self._widgets[16].enabled = False

    def _thread_show_date(self, win, lock, go_on, stop):
        ''' display current date

            Parameters
            win     function to return the window to print to
            lock    threading lock
            go_on   function to indicate if we can print string
            stop    function to make the thread stop
        '''
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('_thread_show_date started!')
        d = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
        while True:
            if go_on()():
                now = datetime.now()
                now_str = ' ' + now.strftime('%Y-%m-%d %H:%M:%S') + ', a ' + d[now.weekday()] + ' '
                X = int((self._maxX - len(now_str)) / 2) - 4
                if stop():
                    break
                w = win()
                if w:
                    with lock:
                        try:
                            self._win.addstr(5, 2, '─' * (self._maxX - 4), curses.color_pair(11))
                        except:
                            self._win.addstr(5, 2, '─'.encode('utf-8') * (self._maxX - 4), curses.color_pair(12))
                        if stop():
                            break
                        w.addstr(5, X, ' Now is:', curses.color_pair(10))
                        w.addstr(now_str, curses.color_pair(3))
                        w.refresh()
                for n in range(5):
                    if stop():
                        break
                    sleep(.1)
            else:
                if stop():
                    break
                sleep(.1)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('_thread_show_date terminated!')

    def keypress(self, char):
        '''
        PyRadioSimpleScheduleWindow keypress

        Return
        ======
            -1: Cancel
             0: Continue
             1: Get result
             2: Remove Schedule
             2: Show Help
             3: Invalid item
             4: Open playlist selection window
             5: Open station selection window
             6: Start time is in the past
             7: Stop time is in the past
             8: Start time < end time
        '''
        # if char == ord('0'):
        #     self._error_num = self._validate_selection()
        #     logger.error('self._error_num = {}'.format(self._error_num))
        #     return self._error_num

        if self._widgets[self._focus].w_id == 23:
            ret = self._widgets[23].keypress(self._win, char)
            logger.error('return = {}'.format(ret))
            if ret == -1:
                self._stop = True
                self._exit = True
                return -1
            elif ret == 2:
                # line editor help
                return 9

        elif char in self._global_functions.keys():
            self._global_functions[char]()
            return 0

        elif char == ord('?'):
            return 2

        elif char in (curses.KEY_EXIT, ord('q'), 27):
            self._stop = True
            self._exit = True
            return -1

        elif self._focus == 0 and char in (
                ord(' '), curses.KEY_ENTER, ord('\n'),
                curses.KEY_RIGHT, ord('l'), ord('\r'),
                ) and self._widgets[2].checked:
            return 4

        elif self._focus == 1 and char in (
                ord(' '), curses.KEY_ENTER, ord('\n'),
                curses.KEY_RIGHT, ord('l'), ord('\r'),
                ) and self._widgets[2].checked:
            return 5

        elif self._focus == 19 and char in (
                ord('l'), ord('h'), curses.KEY_LEFT, curses.KEY_RIGHT
                ):
            if char in (ord('h'), curses.KEY_LEFT):
                self._repeat_index -= 1
                if self._repeat_index < 0 :
                    self._repeat_index = len(self._repeat) - 1
            else:
                self._repeat_index += 1
                if self._repeat_index == len(self._repeat):
                    self._repeat_index = 0
            self._widgets[19].string = self._repeat[self._repeat_index].ljust(self._max_repeat_len)

        elif char in (ord('j'), curses.KEY_UP):
            self._go_up()

        elif char in (ord('k'), curses.KEY_DOWN):
            self._go_down()

        elif char in (9, ord('L')):
            if self._widgets[self._focus].w_id in (3, 5, 7, 9, 11, 13):
                self._widgets[self._focus].keypress(char)
            else:
                self._next_widget()

        elif char in (curses.KEY_BTAB, ord('H')):
            if self._widgets[self._focus].w_id in (3, 5, 7, 9, 11, 13):
                self._widgets[self._focus].keypress(char)
            else:
                self._previous_widget()

        elif char == ord('i'):
            self._show_info()
            return 10

        else:
            ret = self._widgets[self._focus].keypress(char)
            logger.error('ret = {}'.format(ret))

            if self._widgets[self._focus].w_id == 22 \
                    and not ret:
                ''' Cancel '''
                return -1

            elif self._widgets[self._focus].w_id == 21 \
                    and not ret:
                ''' OK '''
                self._validate_selection()
                return 1

            elif self._widgets[self._focus].w_id == 20 \
                    and not ret:
                ''' Remove schedule '''
                return 2

            elif self._widgets[self._focus].w_id in (3, 5, 7, 9, 11, 13):
                ''' Time
                      -1: Cancel
                       0: Continue
                       1: Show help
                '''
                pass

            elif self._widgets[self._focus].w_id == 14:
                if char in (ord('l'), curses.KEY_RIGHT):
                    self._current_player_id += 1
                    if self._current_player_id == len(self._supported_players):
                        self._current_player_id = 0
                    self._widgets[14].string = self._supported_players[self._current_player_id]
                    # self._fix_recording_from_player_selection()
                elif char in (ord('h'), curses.KEY_LEFT):
                    self._current_player_id -= 1
                    if self._current_player_id < 0:
                        self._current_player_id = len(self._supported_players) - 1
                    self._widgets[14].string = self._supported_players[self._current_player_id]
                    # self._fix_recording_from_player_selection()

            elif self._focus in (2, 4, 6, 10, 12):
                ''' Check Boxes '''
                if self._widgets[self._focus].checked:
                    if self._focus == 2:
                        self._widgets[0].string = self._schedule_item.item['playlist']
                        self._widgets[1].string = self._schedule_item.item['station']
                        self._widgets[0].enabled = True
                        self._widgets[1].enabled = True
                    elif self._focus == 4:
                        self._widgets[6].checked = False
                    elif self._focus == 6:
                        self._widgets[4].checked = False
                    elif self._focus == 10:
                        self._widgets[12].checked = False
                    elif self._focus == 12:
                        self._widgets[10].checked = False
                else:
                    if self._focus == 2:
                        self._widgets[0].string = 'Any playlist'
                        self._widgets[1].string = 'Any station'
                        self._widgets[0].enabled = False
                        self._widgets[1].enabled = False
                    elif self._focus == 4:
                        self._widgets[6].checked = True
                    elif self._focus == 6:
                        self._widgets[4].checked = True
                    elif self._focus == 10:
                        self._widgets[12].checked = True
                    elif self._focus == 12:
                        self._widgets[10].checked = True

        self.show()
        return 0

    def _display_time(self, stop, win, Y, X, lock):
        showed = False
        while True:
            if showed:
                for n in range(0, 5):
                    sleep(.1)
                    if stop():
                        # if logger.isEnabledFor(logging.DEBUG):
                        #     logger.debug('File watch thread stopped on: {}'.format(a_file))

                        break
            disp = []
            disp.append((' ─────── ', curses.color_pair(3)))
            disp.append(('Current date: ' + format_date_to_iso8851(), curses.color_pair(11)))
            disp.append((' ────────', curses.color_pair(3)))
            if stop():
                break
            showed = True
            with lock:
                for i, n in enumerate(disp):
                    if i == 0:
                        try:
                            win().addstr(Y(), X(), n[0], n[1])
                        except:
                            win().addstr(Y(), X(), n[0].encode('utf-8'), n[1])
                    else:
                        try:
                            win().addstr(n[0], n[1])
                        except:
                            win().addstr(n[0].encode('utf-8'), n[1])
                win().refresh()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Time display thread exited!')

if __name__ == '__main__':

    pass
    # x = PyRadioTime.pyradio_time_diference_in_seconds(
    #     [1, 10, 15], [1, 12, 20]
    # )
    # print(x)
    # print(PyRadioTime.seconds_to_sting(x))
    # exit()

    # old = datetime.now()
    # now = old + timedelta(seconds=1*60 + 10)

    # import time
    # import os
    # while True:
    #     d = now - old
    #     old = datetime.now()
    #     os.system('clear')
    #     print('Remaining:', PyRadioTime.delta_to_sting(d))
    #     if old >= now:
    #         break
    #     time.sleep(.5)

