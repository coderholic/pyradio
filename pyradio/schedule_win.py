# -*- coding: utf-8 -*-
from sys import exit
from datetime import date, datetime, timedelta
from calendar import monthrange
from time import sleep
import curses
import logging
import threading
import platform

from .simple_curses_widgets import DisabledWidget, SimpleCursesCheckBox, SimpleCursesPushButton, SimpleCursesTime, SimpleCursesString, SimpleCursesDate
from .cjkwrap import cjklen, cjkslices
from .schedule import PyRadioScheduleItem, PyRadioScheduleItemType, PyRadioScheduleTimeType, PyRadioTime, format_date_to_iso8851

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

class PyRadioSimpleScheduleWindow(object):

    _X = _Y = _maxY = maxX = 0
    _widgets = _win = None
    _global_functions = {}
    _showed = False

    '''     0  1  2   3  4  5   6   7  8  9  10 11 12 13 14  15  16  17  18  19  20  21  22'''
    _up = (20, 0, 1, 19, 2, 3, 21, 22, 4, 5, 8, 9, 6, 7, 10, 14, 11, 15, 17, 16, 18, 12, 13)

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
        'Cancel changes to this schedule item'
    )
    def __init__(
            self, parent,
            supported_players,
            current_player,
            playlist=None, station=None,
            schedule_item=None,
            global_functions={}
    ):
        self._exit = False
        self._playlist = playlist
        self._station = station
        self._supported_players = supported_players
        self._maxX = 60
        self._displacement = 3
        self._maxY = 18
        self._global_functions = global_functions
        self._get_parent(parent)
        self._focus = 8
        try:
            self._current_player_id = supported_players.index(current_player)
        except ValueError:
            self._current_player_id = 0
        self._player_id = self._current_player_id
        self.set_item(schedule_item, playlist, station)

    def set_item(self, schedule_item=None, playlist=None, station=None):
        if schedule_item is None:
            self._schedule_item = PyRadioScheduleItem()
            self._schedule_item.item['type'] = 0
            self._schedule_item.item['end_date'] = [2023, 11, 12]
            self._schedule_item.item['end_time'] = [20, 1, 2, 0]
            self._schedule_item.item['start_duration'] = [1, 32, 15, 0]
            self._schedule_item.item['end_duration'] = [3, 15, 2, 0]
            if playlist:
                self._schedule_item.playlist = playlist
            if station:
                self._schedule_item.station = station
            self._remove_enabled = False
        else:
            self._schedule_item = PyRadioScheduleItem(schedule_item)
            self._remove_enabled = True

        ''' parse and assign values '''

    def _move_widgets(self):
        # self._widgets[0].move(1,2)
        # self._widgets[1].move(2,2)
        # Start
        self._widgets[2].move(4 + self._Y, 5 + self._X)
        self._widgets[3].move(4, self._widgets[2].X + self._widgets[2].width - self._X)
        self._widgets[4].move(5 + self._Y, 9 + self._X)
        self._widgets[5].move(5, self._widgets[4].X + self._widgets[4].width - self._X)
        self._widgets[6].move(5 + self._Y, self._X + self._widgets[5].X + self._widgets[5].width + 4)
        self._widgets[7].move(5, self._widgets[6].X + self._widgets[6].width - self._X)
        # End
        self._widgets[8].move(6 + self._Y, 5 + self._X)
        self._widgets[9].move(6, self._widgets[8].X + self._widgets[8].width - self._X)
        self._widgets[10].move(7 + self._Y, 9 + self._X)
        self._widgets[11].move(7, self._widgets[10].X + self._widgets[10].width - self._X)
        self._widgets[12].move(7 + self._Y, self._X + self._widgets[11].X + self._widgets[11].width + 4)
        self._widgets[13].move(7, self._widgets[12].X + self._widgets[12].width - self._X)
        # options
        # self._widgets[14].move(8, 3)
        self._widgets[15].move(6 + self._displacement + self._Y, self._X + 9)
        self._widgets[16].move(6 + self._displacement + self._Y, self._widgets[15].X + self._widgets[15].width + 4)
        self._widgets[17].move(7 + self._displacement + self._Y, self._X + 9)
        self._widgets[18].move(8 + self._displacement + self._Y, self._X + 5)
        self._widgets[19].move(8 + self._displacement + self._Y, self._widgets[17].X + self._widgets[18].width)
        # Buttons
        self._widgets[20].move(10 + self._displacement + self._Y, self._X + 2)
        self._widgets[21].move(self._widgets[20].Y, self._X + self._maxX - 19)
        self._widgets[22].move(self._widgets[20].Y, self._X + self._maxX - (len(self._widgets[13].caption) + 12))

    def _get_parent(self, parent):
        self._parent = parent
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        new_Y = int((self._parent_maxY - self._maxY) / 2) + 1
        new_X = int((self._parent_maxX - self._maxX) / 2)
        if self._Y != new_Y or self._X != new_X:
            self._Y = new_Y
            self._X = new_X
        self._win = curses.newwin(self._maxY, self._maxX, self._Y, self._X)
        logger.error('This is the Window! get_parrent: self._win = {}'.format(self._win))
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
        logger.error('passing win to widgets = {}'.format(self._win))
        self._widgets.append(
            SimpleCursesString(
                Y=1,X=2,
                parent=self._win,
                caption='Playlist: ',
                string='Any playlist',
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
            )
        )
        self._widgets[-1].w_id = 0

        ''' id 1 stations string '''
        self._widgets.append(
            SimpleCursesString(
                Y=2, X=2,
                parent=self._win,
                caption=' Station: ',
                string='Any station',
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
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
                Y=5, X=0,
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
                Y=5, X=0,
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
                Y=6, X=0,
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
                Y=7, X=0,
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
                Y=7,X=0,
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
                Y=8, X=3,
                parent=self._win,
                caption='Player: ',
                string=self._supported_players[self._current_player_id],
                color=curses.color_pair(10),
                color_focused=curses.color_pair(9),
                color_not_focused=curses.color_pair(11),
                color_disabled=curses.color_pair(10),
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
            SimpleCursesCheckBox(
                0, 0, 'Never',
                curses.color_pair(9), curses.color_pair(11), curses.color_pair(10)
            )
        )
        self._widgets[-1].w_id = 19

        ''' id 20 cancel scheduling button '''
        cap = 'Remove Schedule'
        self._widgets.append(SimpleCursesPushButton(
            Y=10 + self._displacement + self._Y,
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

        self._move_widgets()


    def show(self, parent=None):
        if parent:
            logger.error('windows passed to show! = {}'.format(parent))
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
            self._win.addstr(self._maxY-2, 2, disp_msg.ljust(self._maxX-4), curses.color_pair(10))
            self._win.refresh()

        logger.error('1 self._win = {}'.format(self._win))
        if self._widgets:
            if not self._showed:
                self._dummy_enable()
            logger.error('2 self._win = {}'.format(self._win))
            self._fix_focus()
            logger.error('3 self._win = {}'.format(self._win))
            for n in range(0, len(self._widgets)):
                try:
                    with self.lock:
                        self._widgets[n].show(self._win)
                except:
                    logger.error('exception!')
                    with self.lock:
                        self._widgets[n].show()

        # # self._win.addstr(1, 2, 'Playlist: ', curses.color_pair(10))
        # stop_only = self._stop_only()
        # occupied = self._maxX -4 - len('Playlist: ')
        # if stop_only:
        #     disp_playlist = 'Any Playlist'
        # else:
        #     disp_playlist = cjkslices(self._playlist, occupied)[0]
        # # self._win.addstr(disp_playlist.ljust(occupied), curses.color_pair(11))

        # occupied = self._maxX -4 - len('Station: ')
        # # self._win.addstr(2, 2, 'Station: ', curses.color_pair(10))
        # if self._stop_only():
        #     disp_station = 'Any Station'
        # else:
        #     if self._station:
        #         disp_station = cjkslices(self._station, occupied)[0]
        #     else:
        #         disp_station = 'Any Station'
        # # self._win.addstr(disp_station.ljust(occupied), curses.color_pair(11))
        # self._win.refresh()

        # if not self._showed:
        #     threading.Thread(target=self._display_time,
        #                      args=[lambda: self._exit,
        #                            lambda: self._parent,
        #                            lambda: self._Y + 2,
        #                            lambda: self._X + 1,
        #                            self.lock,
        #                            ]
        #                      ).start()
        logger.info('here')
        self._win.refresh()
        self._showed = True

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
            self._widgets[20].enabled = self._remove_enabled
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
        logger.info('entering _fix_focus')
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

    def _validate_selection(self):
        if self._widgets[3].checked and \
                self._widgets[7].checked:
            ''' type B '''

            return 3
        return 1

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
             3: Invalid date range
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return 0

        elif char == ord('?'):
            return 2

        elif char in (curses.KEY_EXIT, ord('q'), 27):
            self._exit = True
            return -1

        elif char in (ord('j'), curses.KEY_UP):
            logger.error('===================================')
            logger.error('start self._focus = {}'.format(self._focus))
            self._focus = self._up[self._focus]
            while not self._widgets[self._focus].enabled:
                self._focus = self._up[self._focus]
            if self._focus in (5, 7, 11, 13):
                self._widgets[self._focus].reset_selection()
            logger.error('final self._focus = {}'.format(self._focus))

        elif char in (ord('k'), curses.KEY_DOWN):
            self._focus = self._up.index(self._focus)
            while not self._widgets[self._focus].enabled:
                self._focus = self._up.index(self._focus)
            if self._focus in (5, 7, 11, 13):
                self._widgets[self._focus].reset_selection()

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
            else:
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

