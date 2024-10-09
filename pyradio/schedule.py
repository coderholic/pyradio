# -*- coding: utf-8 -*-
from sys import version_info as python_version
from datetime import date as ddate, datetime, timedelta
from dateutil.relativedelta import *
from dateutil.rrule import *
from dateutil.parser import *
from datetime import *
from calendar import monthrange
from random import choice
from string import printable
from platform import system
import logging
import json
import sys

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)


a_file = '/home/spiros/.config/pyradio/data/schedule.json'


def is_date_before(a_date, b_date):
    if (a_date - b_date).days < 0:
        return True
    return False

def is_date_after(a_date, b_date):
    return not is_date_before(a_date, b_date)

def datetime_to_my_time(a_date, shorten=True):
    t = a_date.ctime().split()
    now = datetime.now()
    if shorten:
        if a_date.date() == now.date():
            return 'At ' + t[-2]
        # now = now.replace(day=now.day+1)
        now = now + timedelta(days=1)
        if a_date.date() == now.date():
            return 'Tomorrow, at ' + t[-2]

    if datetime.now().year == a_date.year:
        return t[0] + ', ' + t[1] + ' ' + t[2] + ', ' + t[-2]
    else:
        return t[0] + ', ' + t[1] + ' ' + t[2] + ' ' + t[-1] +', ' + t[-2]

def random_string(length=10):
    return ''.join(choice(printable) for i in range(length))

def format_date_to_iso8851(a_date=None):
    ''' format a datetime.date in ISO-8851 format
    '''
    if a_date is None:
        a_date = datetime.now()
    days = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
    months = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
              'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')

    cur_day = days[a_date.weekday()]
    cur_month = months[a_date.month-1]
    return cur_day + ', ' + str(a_date.day) + ' ' + \
        cur_month + ' ' + str(a_date.year) + \
        a_date.strftime(' %H:%M:%S')

class PyRadioScheduleItemType(object):

    TYPE_START_END = 0
    TYPE_START = 1
    TYPE_END = 2

    items = TYPE_START_END, TYPE_START, TYPE_END

    @classmethod
    def to_string(cls, a_type):
        if a_type == 0:
            return 'TYPE_START_END'
        elif a_type == 1:
            return 'TYPE_START'
        elif a_type == 2:
            return 'TYPE_END'
        else:
            return 'UNKNOUN'


class PyRadioScheduleTimeType(object):

    TIME_ABSOLUTE = 0
    TIME_RELATIVE = 1

    items = 0, 1

    @classmethod
    def to_string(cls, a_type):
        if a_type == 0:
            return 'TIME_ABSOLUTE'
        elif a_type == 1:
            return 'TIME_RELATIVE'
        else:
            return 'UNKNOUN'


class PyRadioScheduleList(object):

    _list = []              # initial list of dicts
    _schedule_list = []     # lisr of PyRadioScheduleItem
    _sorted = []            # list (sorted) of tasks (dicts)
    _info = False

    def __init__(self, a_file, a_list=None):
        '''
            a_file : file to read
            a_list : list of dicts of (as output of self._read_list)
        '''
        self._json_file = a_file
        self._a_list = a_list
        self._read_list()

    def _read_list(self):
        ''' read json file to self._list '''
        if self._a_list:
            logger.error('\n\nself._list\n{}\n\n'.format(self._a_list))
            self._list = self._a_list
            for i in range(len(self._list)):
                if self._list[-1]['token'] == '':
                    self._list[-1]['token'] = random_string()
        else:
            try:
                with open(self._json_file, 'r', encoding='utf-8') as f:
                    self._list = json.load(f)
            except:
                self._list = []

    def _list_to_schedule_items(self):
        self._schedule_list = []
        for i in range(0, len(self._list)):
             self._schedule_list.append(
                 PyRadioScheduleItem(self._list[i])
             )
        for i in range(len(self._schedule_list)-1, -1, -1):
            ac = self._schedule_list[i].get_active_item()
            now = datetime.now()
            if is_date_before(ac[1], now) and \
                    is_date_before(ac[2], now) and \
                    ac[7] is None:
                self._schedule_list.pop(i)
        # logger.error('\n\nself._schedule_list\n{}'.format(self._schedule_list))

    def get_list_of_active_items(self):
        if self._schedule_list == []:
            # logger.error('len(self._list) = {}'.format(len(self._list)))
            for i in range(0, len(self._list)):
                 self._schedule_list.append(
                     PyRadioScheduleItem(self._list[i])
                 )
        return [x.get_active_item() for x in self._schedule_list]

    def get_info_of_items(self):
        ''' Returns a list of items comming from self._schedule_list
            (which is a list of PyRadioScheduleItem), to be presented
            to the user
        '''
        out = []
        for i, n in enumerate(self._schedule_list):
            x = n.get_active_item()
            out.append('Item {}'.format(i+1))
            if x[2] == 0 or x[2] == 1:
                out.append('  Start playback on: ' + datetime_to_my_time(x[0]))
            if x[2] == 0 or x[2] == 2:
                out.append('   Stop playback on: ' + datetime_to_my_time(x[1]))
            if x[2] == 0 or x[2] == 1:
                out.append('  From playlist: ' + x[-3])
                out.append('        Station: ' + x[-2])
                out.append('  Player: ' + x[3])
                if x[-4]:
                    out.append('  Repeat every: ' + x[-4])
                if x[-6] == 0:
                    tmp = '  Recording is off,'
                elif x[-6] == 1:
                    tmp = '  Recording is on,'
                elif x[-6] == 2:
                    tmp = '  Recording is on (silent),'
                if x[-5] == 0:
                    tmp += ' with no buffering'
                else:
                    tmp += ' with buffering'
                out.append(tmp)
        return out

    def get_list_of_repeating_dates(self, count):
        if self._schedule_list == []:
            self._list_to_schedule_items()
        rep = self.get_repeating_dates(self._schedule_list[0].get_active_item(), count=count)
        return [(datetime_to_my_time(x[1]), datetime_to_my_time(x[2])) for x in rep]



    def get_repeating_dates(self, in_date, count=-1):
        days = {
            'Sunday': SU,
            'Monday': MO,
            'Tuesday': TU,
            'Wednesday': WE,
            'Thursday': TH,
            'Friday': FR,
            'Saturday': SA
        }

        start_date = in_date[1]
        now = datetime.now()
        if start_date < now:
            start_date = start_date.replace(year=now.year, month=now.month, day=now.day)
        now_with_correct_time = now.replace(hour=in_date[1].hour, minute=in_date[1].minute, second=in_date[1].minute)
        now_plus_seven_days = now_with_correct_time + timedelta(days=7)
        if count == -1:
            if in_date[-4] == 'day':
                ll = list(rrule(DAILY, count=12, dtstart=start_date))
            elif in_date[-4] == 'week':
                ll = list(rrule(WEEKLY, dtstart=in_date[0], until=now + timedelta(days=14)))[-2:]
            elif in_date[-4] == 'month':
                ll = list(rrule(MONTHLY, dtstart=in_date[0], until=now + timedelta(days=65)))[-3:]
                for n in range(len(ll)-1, -1,-1):
                    if ll[n] <= now_with_correct_time:
                        ll.pop(n)
            elif in_date[-4] in days.keys():
                ll = list(rrule(WEEKLY, count=3, wkst=SU, byweekday=(days[in_date[-4]],), dtstart=start_date))
            for n in range(len(ll)-1, -1,-1):
                if ll[n] > now_plus_seven_days:
                    ll.pop(n)
        else:
            if in_date[-4] == 'day':
                ll = list(rrule(DAILY, count=count, dtstart=start_date))
            elif in_date[-4] == 'week':
                ll = list(rrule(WEEKLY, dtstart=in_date[1], count=count))
            elif in_date[-4] == 'month':
                ll = list(rrule(MONTHLY, dtstart=in_date[1], count=count))
            elif in_date[-4] in days.keys():
                ll = list(rrule(WEEKLY, count=count, wkst=SU, byweekday=(days[in_date[-4]],), dtstart=start_date))

        # print('\n\nll\n{}'.format(ll))

        out = []
        if ll:
            d = in_date[2] - in_date[1]
            for i in range(len(ll)):
                out.append(list(in_date))
                out[-1][1] = ll[i]
                out[-1][2] = out[-1][1] + d
        return out

    def get_info_of_tasks(self, to_dict=False):
        ''' Returns a list of tasks comming from self._sorted
            to be presented to the user
        '''
        self.get_list_of_tasks()
        out = []
        if to_dict:
            links_found = 0
            tick = ' X ' if system().lower().startswith('win') else ' ✔ '
            for i, n in enumerate(self._sorted):
                if 'player' in n:
                    tmp = {
                            'id': str(i+1),
                            'name': n['name'],
                            'link': '',
                            'start': datetime_to_my_time(n['date']),
                            'stop': '',
                            'player': n['player'],
                            'playlist': n['playlist'],
                            'station': n['station'],
                            'recording': '' if n['recording'] == 0  else tick,
                            'buffering': '' if n['buffering'] == 0 else tick
                    }
                    if n['recording'] == 2:
                        tmp['recording'] = 'sil'
                else:
                    if out:
                        link = self._get_linked_task(n['link'], True)
                        if link:
                            out[int(link)-links_found-1]['stop'] = datetime_to_my_time(n['date'])
                            links_found += 1
                            continue
                    tmp = {
                            'id': str(i+1),
                            'link': self._get_linked_task(n['link'], to_dict),
                            'start': '',
                            'stop': datetime_to_my_time(n['date']),
                            'player': '',
                            'playlist': '',
                            'station': '',
                            'recording': '',
                            'buffering': ''
                    }
                out.append(tmp)
            for i in range(len(out)):
                if out[i]['stop'][:13] == out[i]['start'][:13]:
                    out[i]['stop'] = out[i]['stop'][13:]
        else:
            for i, n in enumerate(self._sorted):
                if 'player' in n:
                    out.append('Task: {}'.format(i+1))
                    out.append('    Name: ' + n['name'])
                    out.append('    Start playback on: ' + datetime_to_my_time(n['date']))
                    out.append('    From playlist: ' + n['playlist'])
                    out.append('          Station: ' + n['station'])
                    if n['recording'] == 0:
                        tmp = '    Recording is off,'
                    elif n['recording'] == 1:
                        tmp = '    Recording is on,'
                    elif n['recording'] == 2:
                        tmp = '    Recording is on (silent),'
                    if n['buffering'] == 0:
                        tmp += ' with no buffering'
                    else:
                        tmp += ' with buffering'
                    out.append(tmp)
                else:
                    out.append('Task: {0} {1}'.format(i+1, self._get_linked_task(n['link'])))
                    out.append('     Stop playback on: ' + datetime_to_my_time(n['date']))
        return out

    def _get_linked_task(self, a_link, to_dict=False):
        for i, n in enumerate(self._sorted):
            if a_link == n['link']:
                if to_dict:
                    return str(i + 1)
                else:
                    return '  ->   linked to Task {}'.format(i + 1)
        return ''

    def get_list_of_tasks(self):
        self._sorted = []
        if self._schedule_list == []:
            self._list_to_schedule_items()

        # for n in self._schedule_list:
        #     logger.error(n)
        # logger.error('\n\n')

        a_list= []
        for i in range(0, len(self._schedule_list)):
            if self._schedule_list[i].repeat is None:
                a_list.append(
                    self._schedule_list[i].get_active_item()
                )
            else:
                a_list.extend(
                    self.get_repeating_dates(
                        self._schedule_list[i].get_active_item(),
                    )
                )

            # logger.info('\n\na_list')
            # for n in a_list:
            #     logger.error('\n{}'.format(n))
            # logger.info('\n\n')

        if a_list:
            a_list.sort(key=lambda x: x[0])
            for n in a_list:
                self._sorted.append({
                    'name': n[0],
                    'date': n[1],
                    'player': n[4],
                    'recording': n[5],
                    'buffering': n[6],
                    'playlist': n[8],
                    'station': n[9],
                    'token': n[-1] if n[-1] else random_string(),
                    'link': random_string() if n[3] == 0 else ''
                })
                if n[3] == 0:
                    self._sorted.append({
                        'date': n[2],
                        'token': self._sorted[-1]['token'],
                        'link': self._sorted[-1]['link']
                    })

        # logger.error('\n\nself._sorted')
        # for n in self._sorted:
        #     logger.error(n)
        # logger.error('\n\n')

    def item(self, index):
        if index < len(self._list):
            return self._list[index]
        return None

    def count(self):
        return len(self._schedule_list)

class PyRadioScheduleItem(object):
    '''
    Provide a Schedule Item

    Items Format:
        type:
            "B" "S" or "E"
                "B": Item has both a start and an end time
                "S": Item has only a start time
                "E": Item has only an end time
                     Start time is the time the Item was created

        start_date
            A PyRadioDate: [YYYY, M, D]
        start_time
            A PyRadioTime: [X, X, X, T]

        start type
            "A" or "I"
                "A": Date and Time is absolute
                "I": Date and Time is relative
                     In this case, the field becomes "IXX:XX:XX"
                     and the start date is the creation date
            This gives a hint for the presenting window

        end_date
            A PyRadioDate: [YYYY, M, D]
        end_time
            A PyRadioTime: [X, X, X, T]

        end type
            "A" or "I"
                "A": Date and Time is absolute
                "I": Date and Time is relative
                     In this case, the field becomes "IXX:XX:XX"
                     and the end date is the creation date
            This gives a hint for the presenting window

        playlist
            Playlist title

        station
            station name

    '''

    def __init__(self, item=None):
        self._item = None
        if item:
            if isinstance(item, str):
                self._item = json.loads(item)
            elif isinstance(item, dict):
                self._item = item

        if self._item is None:
           self._item = self.default_item

    def __str__(self):
        out = ['Current _item:']
        for n in self._item.keys():
            s = "  " + "'{}':  ".format(n).rjust(20)
            if n == 'type':
                out.append(s + "{} (".format(self._item[n]) + \
                        PyRadioScheduleItemType.to_string(self._item['type']) +
                           ')  -> '  + str(type(self.item[n]))
                )
            elif n in ('start_type', 'end_type'):
                out.append(s + "{} (".format(self._item[n]) + \
                        PyRadioScheduleTimeType.to_string(self._item[n]) \
                        + ')  -> ' + str(type(self._item[n]))
                )
            elif n in ('start_time', 'end_time', 'start_duration', 'end_duration'):
                t = self._item[n][-1]
                x = self._item[n][:-1]
                out.append(s + str(x)[:-1] + \
                        ', {0} ({1})]  -> {2}'.format(t, PyRadioTime.to_string(t), type(self._item[n])))
            else:
                out.append(s + str(self._item[n]) + '  -> ' + str(type(self._item[n])))
        return '\n'.join(out)

    @property
    def active_item(self):
        '''return the item after calculating all relative values'''
        name, st, en, it_type, pl, rec, buf, rep, playlist, station, token = self.get_active_item()
        if token == '':
            token = random_string()
        out = {
            'name': name,
            'type': it_type,
            'start_type': 0,
            'start_date': [st.year, st.month, st.day],
            'start_time': [st.hour, st.minute, st.second, 0],
            'start_duration': [0, 0, 0, 0],
            'end_type': 0,
            'end_date': [en.year, en.month, en.day],
            'end_time': [en.hour, en.minute, en.second, 0],
            'end_duration': [0, 0, 0, 0],
            'playlist': playlist,
            'station': station,
            'player': pl,
            'recording': rec,
            'buffering': buf,
            'repeat': rep,
            'token': token
        }
        return out

    @property
    def item(self):
        return self._item

    @item.setter
    def item(self, val):
        if isinstance(item, str):
            try:
                self._item = json.loads(item)
            except:
                raise ValueError('JSON string not supported')
        elif isinstance(item, dict):
            self._item = item

        for n in self.default_item.keys():
            if n not in self._item:
                self.item = self.default_item
                raise ValueError('Item is missing keys')

        '''make sure duration times are of NO_AM_PM_FORMAT'''
        self._item['start_duration'][-1] = 0
        self._item['end_duration'][-1] = 0

    @property
    def default_item(self):
        n_date, n_time = self._get_today_plus_one_hour()
        t_date, t_time = self._get_today()
        return {
            'name': 'Default schedule entry',
            'type': 2, # TYPE_START_END, TYPE_START, TYPE_END
            'start_type': 0, # TIME_ABSOLUTE, TIME_RELATIVE
            'start_date':  t_date, # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'start_time': t_time, # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'start_duration': [0, 0, 0, 0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'end_type': 1, # TIME_ABSOLUTE, TIME_RELATIVE
            'end_date': n_date,
            'end_time': n_time, # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'end_duration': [1, 0, 0, 0], # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
            'player': '',
            'recording': 0,
            'buffering': 0,
            'repeat': None,
            'playlist': None,
            'station': None,
            'token': random_string()
        }

    @property
    def type(self):
        return self._item['type']

    @type.setter
    def type(self, val):
        try:
            if val in (PyRadioScheduleItemType.items):
                self._item['type'] = val
                return
        except:
            pass
        raise ValueError('Invalid item type')

    @property
    def start_type(self):
        return self._item['start_type']

    @start_type.setter
    def start_type(self, val):
        self._item['start_type'] = val

    @property
    def start_date(self):
        return self._item['start_date']

    @start_date.setter
    def start_date(self, val):
        self._item['start_date'] = val

    @property
    def start_time(self):
        return self._item['start_time']

    @start_time.setter
    def start_time(self, val):
        self._item['start_time'] = val

    @property
    def start_duration(self):
        return self._item['start_duration']

    @start_duration.setter
    def start_duration(self, val):
        self._item['start_duration'] = val

    @property
    def end_type(self):
        return self._item['end_type']

    @end_type.setter
    def end_type(self, val):
        self._item['end_type'] = val

    @property
    def end_date(self):
        return self._item['end_date']

    @end_date.setter
    def end_date(self, val):
        self._item['end_date'] = val

    @property
    def end_time(self):
        return self._item['end_time']

    @end_time.setter
    def end_time(self, val):
        self._item['end_time'] = val

    @property
    def end_duration(self):
        return self._item['end_duration']

    @end_duration.setter
    def end_duration(self, val):
        self._item['end_duration'] = val

    @property
    def recording(self):
        return self._item['recording']

    @recording.setter
    def recording(self, val):
        self._item['recording'] = val

    @property
    def buffering(self):
        return self._item['buffering']

    @buffering.setter
    def buffering(self, val):
        self._item['buffering'] = val

    @property
    def repeat(self):
        return self._item['repeat']

    @repeat.setter
    def repeat(self, val):
        self._item['repeat'] = val

    @property
    def playlist(self):
        return self._item['playlist']

    @playlist.setter
    def playlist(self, val):
        self._item['playlist'] = val

    @property
    def station(self):
        return self._item['station']

    @station.setter
    def station(self, val):
        self._item['station'] = val

    @property
    def string(self):
        return json.dumps(self._item)

    def _check_start_end_type(self, val):
        try:
            if val in (
                PyRadioScheduleTimeType.TIME_ABSOLUTE,
                PyRadioScheduleTimeType.TIME_RELATIVE,
            ):
                self._item['start_type'] = val
                return True
        except:
            pass
        return False

    def get_active_item(self):
        '''
        return a tuple of datetimes representing
        (
            name
            starting date-time,
            ending date-time,
            type (start/stop/both)
            player to use
            recording (0 if TYPE_END)
            buffering (0 if TYPE_END
            repeat (None if TYPE_END)
            playlist (None if TYPE_END)
            station (None if TYPE_END)
            token
        )
        '''
        today = datetime.now().replace(microsecond=0)
        if self._item['type'] in (
                PyRadioScheduleItemType.TYPE_START_END,
                PyRadioScheduleItemType.TYPE_START
        ):
            if self._item['start_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                start_date = datetime(
                    year=self._item['start_date'][0],
                    month=self._item['start_date'][1],
                    day=self._item['start_date'][2],
                ) + PyRadioTime.pyradio_time_to_timedelta(
                    self._item['start_time']
                )
            else:
                start_date = today + PyRadioTime.pyradio_time_to_timedelta(
                    self._item['start_duration']
                )


        if self._item['type'] in (
                PyRadioScheduleItemType.TYPE_START_END,
                PyRadioScheduleItemType.TYPE_END
        ):
            if self._item['end_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
                end_date = datetime(
                    self._item['end_date'][0],
                    self._item['end_date'][1],
                    self._item['end_date'][2]
                ) + timedelta(
                    hours=self._item['end_time'][0],
                    minutes=self._item['end_time'][1],
                    seconds=self._item['end_time'][2],
                )
            else:
                if self._item['type'] == PyRadioScheduleItemType.TYPE_END:
                    use_date = today
                else:
                    use_date = start_date
                end_date = use_date + timedelta(
                    hours=self._item['end_duration'][0],
                    minutes=self._item['end_duration'][1],
                    seconds=self._item['end_duration'][2]
                )

        if self._item['type'] == PyRadioScheduleItemType.TYPE_START:
            end_date = start_date
        elif self._item['type'] == PyRadioScheduleItemType.TYPE_END:
            start_date = end_date
        rep = self._item['repeat']
        if rep is not None:
            rep = rep.strip()
        return (self._item['name'],
                start_date, end_date,
                self._item['type'],
                self._item['player'],
                self._item['recording'],
                self._item['buffering'],
                rep,
                self._item['playlist'] if self._item['type'] != PyRadioScheduleItemType.TYPE_END else None,
                self._item['station'] if self._item['type'] != PyRadioScheduleItemType.TYPE_END else None,
                self._item['token'],
                )

    def _get_today(self):
        ''' get today as pyradio date and time '''
        today = datetime.now()
        return [today.year, today.month, today.day], \
                [today.hour, today.minute, 0, 0]

    def _get_today_plus_one_hour(self):
        today = datetime.now() + relativedelta(hours=+1)
        return [today.year, today.month, today.day], \
            [today.hour, today.minute, 0, 0]


class PyRadioTime(object):
    ''' A class to provide PyRadio time and date

        PyRadio time is a tuple
        Its format is ALWAYS in 24-hour notation
        and contains
            hour, minutes, seconds, type

            type shows how the time was inserted
                type is 0: 24-hour format
                        1: AM
                        2: PM

        Parameters
        ==========
        date
            Date string
                format is YYYY-MM-DD
            if None, date will not be set
        time
            Time string
                format is XX:XX [AM/PM]
                          XX:XX:XX [AM/PM]
    '''

    NO_AM_PM_FORMAT = 0
    AM_FORMAT = 1
    PM_FORMAT = 2

    def __init__( self):
        '''
        '''
        self.date = None        # datetime.date
        self.time = None        # pyradio time

    def __str__(self):
        if self.date is None:
            self.date = date.today()
        if self.time is None:
            self.time = PyRadioTime.string_to_pyradio_time(datetime.now().strftime('%H:%M:%S'))
        return self.date.strftime('%Y-%m-%d') + ' ' + PyRadioTime.pyradio_time_to_string(self.time)

    @classmethod
    def to_string(cls, a_time_format):
        if a_time_format == 1:
            return 'AM_FORMAT'
        elif a_time_format == 2:
            return 'PM_FORMAT'
        return 'NO_AM_PM_FORMAT'

    def set_date_and_time(self, a_date_time_string):
        sp = a_date_time_string.split(' ')
        self.set_date(sp[0])
        if len(sp) == 3:
            self.set_time(sp[1] + ' ' + sp[2])
        else:
            self.set_time(sp[1])

    def set_date(self, a_date_string):
        if a_date_string:
            if python_version[0] == 2:
                sp = a_date_string.split('-')
                for i in range(0, len(sp)):
                    sp[i] = int(sp[i])
                self.date = ddate(sp[0], sp[1], sp[2])
            else:
                self.date = ddate.fromisoformat(a_date_string)
        else:
            self.date = ddate.today()

    def set_time(self, a_time_string):
        valid = True
        is_12_format = self.NO_AM_PM_FORMAT
        if a_time_string is None:
            valid = False
        else:
            if a_time_string.lower().endswith(' am'):
                is_12_format = self.AM_FORMAT
                my_string = a_time_string[:-3]
            elif a_time_string.lower().endswith(' pm'):
                is_12_format = self.PM_FORMAT
                my_string = a_time_string[:-3]
            else:
                my_string = a_time_string
            sp = my_string.split(':')
            if len(sp) > 3:
                valid = False
            if len(sp) < 3:
                sp.append('00')
            try:
                hour = int(sp[0])
                minute = int(sp[1])
                seconds = int(sp[2])
            except ValueError:
                valid = False

        if valid:
            if is_12_format == self.PM_FORMAT:
                ''' pm '''
                hour += 12
                if hour == 24:
                    hour =0
                elif hour > 24:
                    valid = False
            elif is_12_format == self.AM_FORMAT:
                ''' am '''
                if hour > 12:
                    valid = False

        if not valid:
            a_date_time = datetime.now()
            hour = a_date_time.hour
            minute = a_date_time.minute
            seconds = a_date_time.second

        self.time = [hour, minute, seconds, is_12_format]

    @classmethod
    def number_of_days_in_month(self, year, month):
        return monthrange(int(year), int(month))

    @classmethod
    def string_to_pyradio_time(cls, a_string):
        ''' convert string to hour,minutes,seconds

            Input can be
                XX:XX [AM/PM]
                XX:XX:XX [AM/PM]

            Returns hour, minutes, seconds, type
                output format is ALWAYS in 24-hour
                type shows how the time was inserted
                    type is 0: 24-hour format
                            1: AM
                            2: PM

            if time is invalid or None, return current time
                in 24-hour format
        '''

        valid = True
        is_12_format = PyRadioTime.NO_AM_PM_FORMAT
        if a_string is None:
            valid = False
        else:
            if a_string.lower().endswith(' am'):
                is_12_format = PyRadioTime.AM_FORMAT
                my_string = a_string[:-3]
            elif a_string.lower().endswith(' pm'):
                is_12_format = PyRadioTime.PM_FORMAT
                my_string = a_string[:-3]
            else:
                my_string = a_string
            sp = my_string.split(':')
            if len(sp) > 3:
                valid = False
            if len(sp) < 3:
                sp.append('00')
            try:
                hour = int(sp[0])
                minute = int(sp[1])
                seconds = int(sp[2])
            except ValueError:
                valid = False

        if valid:
            if is_12_format == PyRadioTime.PM_FORMAT:
                ''' pm '''
                hour += 12
                if hour == 24:
                    hour = 0
                elif hour > 24:
                    valid = False
            elif is_12_format == PyRadioTime.AM_FORMAT:
                ''' am '''
                if hour > 12:
                    valid = False

        if not valid:
            a_date_time = datetime.now()
            hour = a_date_time.hour
            minute = a_date_time.minute
            seconds = a_date_time.second

        return hour, minute, seconds, is_12_format

    @classmethod
    def pyradio_time_to_string(cls, a_time):
        a_date = datetime(2022, 1, 1) + timedelta(
            hours=a_time[0],
            minutes=a_time[1],
            seconds=a_time[2]
        )
        if a_time[-1] == 0:
            ''' 24-hour format '''
            return a_date.strftime('%H:%M:%S')
        else:
            if a_time[-1] == 2:
                if a_date.hour > 12:
                    a_date = a_date.replace(hour=a_date.hour - 12)
            return '{0} {1}'.format(
                a_date.strftime('%H:%M:%S'),
                'PM' if a_time[-1] == PyRadioTime.PM_FORMAT else 'AM'
            )

    @classmethod
    def to_24_format(cls, a_time):
        if a_time[-1] == self.NO_AM_PM_FORMAT:
            return a_time
        elif a_time[-1] == self.PM_FORMAT:
            ''' PM '''
            out = list(a_time)
            out[-1] = 0
            return tuple(out)
        else:
            out = list(a_time)
            out[-1] = 0
            out[0] += 12
            return tuple(out)

    @classmethod
    def pyradio_time_to_timedelta(cls, a_time):
        if a_time[-1] == PyRadioTime.NO_AM_PM_FORMAT:
            return timedelta(
                hours=a_time[0],
                minutes=a_time[1],
                seconds=a_time[2]
            )

        elif a_time[-1] == PyRadioTime.AM_FORMAT:
            return timedelta(
                hours=a_time[0] if a_time[0] < 12 else a_time[0] - 12,
                minutes=a_time[1],
                seconds=a_time[2]
            )

        elif a_time[-1] == PyRadioTime.PM_FORMAT:
            return timedelta(
                hours=a_time[0] + 12,
                minutes=a_time[1],
                seconds=a_time[2]
            )

    def schedule_datetime(self):
        ''' return final datetime for this object
            use this for further caclulations
        '''
        return self.pyradio_time_to_datetime(t_time=self.time)

    def pyradio_time_to_datetime(self, t_date=None, t_time=None):
        if t_time is None:
            a_time = self.time
        else:
            a_time = t_time
        if t_date is None:
            a_date = datetime.now()
        else:
            a_date = t_data
        b_date= a_date.replace(
            hour = a_time[0],
            minute = a_time[1],
            second = a_time[2],
            microsecond = 0
        )
        return b_date

    @classmethod
    def seconds_to_sting(cls, time_in_seconds):
        return PyRadioTime.delta_to_sting(time_in_seconds, is_seconds=True)

    @classmethod
    def delta_to_sting(cls, time_delta, is_seconds=False):
        if is_seconds:
            s = time_delta
        else:
            s = time_delta.total_seconds()
        hours, remainder = divmod(s, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            out = '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))
        else:
            out = '{:02}:{:02}'.format(int(minutes), int(seconds))
        return out

    @classmethod
    def pyradio_time_to_seconds(csl, t_time):
        ''' return number od seconds in a pyradio time'''
        return 3600 * t_time[0] + 60 * t_time[1] + t_time[2]

    @classmethod
    def pyradio_time_diference_in_seconds(cls, s_time, e_time):
        ''' return the difference of two pyradio times
            in seconds

            Paremeters
            ==========
            s_time start time
            e_time end time

            if s_time > e_time, this is a negative number
        '''
        return PyRadioTime.pyradio_time_to_seconds(e_time) - \
            PyRadioTime.pyradio_time_to_seconds(s_time)



if __name__ == '__main__':
    # print(format_date_to_iso8851(datetime.now()))

    # print('\n\n============')
    # an_item = {
    #     'type': PyRadioScheduleItemType.TYPE_START_END,
    #     'start_type': 0,                            # TIME_ABSOLUTE, TYPE_RELATIVE
    #     'start_date':  [2022, 10, 15],
    #     'start_time': [8, 15, 12, 2],              # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
    #     'start_duration': [1, 0, 0, 0],
    #     'end_type': 1,                              # TIME_ABSOLUTE, TYPE_RELATIVE
    #     'end_date': [2023, 1, 1],
    #     'end_time': [3, 12, 2, 1],                  # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
    #     'end_duration': [5, 15, 11, 0],
    #     'player': 'mpv',
    #     'recording': 0,
    #     'buffering': 0,
    #     'repeat': None,
    #     'playlist': 'myplaylist',
    #     'station': 'mystation',
    #     'token': random_string()
    # }

    # for n,k in an_item.items():
    #     print(n, ":", k)
    # print('\n\n============')

    # b = PyRadioScheduleItem(an_item)
    # print('b =', b)
    # u = b.get_active_item()
    # print('\n\n')
    # print(b.get_active_item())
    # print('start_date:', str(u[0]))
    # print('  end_date:', str(u[1]))
    # print('      type:', PyRadioScheduleItemType.to_string(u[2]))
    # print('  playlist:', u[3])
    # print('   station:', u[4])

    # print('\n\n{}'.format(b.string))


    my_list = [{
        'name': 'A test',
        'type': 1,
        'start_type': 0,
        'start_date': [2024, 11, 19],
        'start_time': (18, 23, 0, 0),
        'start_duration': (1, 32, 15, 0),
        'end_type': 0,
        'end_date': [2024, 11, 19],
        'end_time': (20, 1, 2, 0),
        'end_duration': (3, 15, 2, 0),
        'player': 'mpv',
        'recording': 0,
        'buffering': 0,
        'repeat': 'month',
        'playlist': 'reversed',
        'station': 'The UK 1940s Radio Station  1920s 1930s 1940s',
        'token': 'LhhO\x0c@>BET'
    }]
    x = PyRadioScheduleList(a_file='', a_list=my_list)
    # x = PyRadioScheduleList(a_file='/home/spiros/.config/pyradio/data/schedule.json')
    out = x.get_list_of_active_items()
    print(type(out))
    print(out)
    print('\n\nper item')
    for n in out:
        print(n)
    print('\n\n')


    if x._schedule_list == []:
        x._list_to_schedule_items()

    print(type(x))
    y = PyRadioScheduleItem(x)
    print('active_item')
    print(y.get_active_item())


    print('Repeating dates')
    rep = x.get_repeating_dates(x._schedule_list[0].get_active_item(), count=6)
    print('\n\n')
    for n in rep:
        print(n)
    # x.get_list_of_tasks()
    # print('\n\n')
    # for n in x._sorted:
    #     print(n)
    print('\n\n')

    for n in rep:
        print('n[1] =', n[1])
        print('type(n[1]) =', type(n[1]))
        print(datetime_to_my_time(n[1]))
        print(datetime_to_my_time(n[2]))
        print('')

    r = x.get_list_of_repeating_dates(6)
    print('\n\n')
    for n in r:
        print(n)

    print('\n\n\n')

    t = PyRadioTime()
    print(t)

    t.time = [11, 15, 34, 1]
    print(t)

    print('\n\n{}'.format(datetime_to_my_time(datetime.now())))

    print('\n\n{}'.format(datetime_to_my_time(datetime.now() + timedelta(days=1))))

