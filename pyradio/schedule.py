# -*- coding: utf-8 -*-
from sys import version_info as python_version
from datetime import date as ddate, datetime, timedelta
from dateutil.relativedelta import *
from calendar import monthrange
import logging

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

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

    items = 0, 1, 2

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

    @property
    def item(self):
        st, en = self.get_active_dates()
        out = {
            'type': self._item['type'],
            'start_type': 0,
            'start_date': [st.year, st.month, st.day],
            'start_time': [st.hour, st.minute, st.second, 0],
            'start_duration': [0, 0, 0, 0],
            'end_type': 0,
            'end_date': [en.year, en.month, en.day],
            'end_time': [en.hour, en.minute, en.second, 0],
            'end_duration': [0, 0, 0, 0],
            'playlist': self._item['playlist'],
            'station': self._item['station']
        }
        return out

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

    @property
    def default_item(self):
        n_date, n_time = self._get_today_plus_one_hour()
        t_date, t_time = self._get_today()
        return {
            'type': 2,
            'start_type': 0,
            'start_date':  t_date,
            'start_time': t_time,
            'start_duration': [0, 0, 0, 0],
            'end_type': 0,
            'end_date': n_date,
            'end_time': n_time,
            'end_duration': [0, 0, 0, 0],
            'playlist': 'stations',
            'station': ''
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
        if self._check_start_end_type(val):
            self._item['start_type'] = val
        else:
            raise ValueError('Invalid item start_type')

    @property
    def end_type(self):
        return self._item['end_type']

    @end_type.setter
    def end_type(self, val):
        if self._check_start_end_type(val):
            self._item['end_type'] = val
        else:
            raise ValueError('Invalid item end_type')

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

    def get_active_dates(self):
        '''
        return a tuple of datetimes representing
        the (starting date-time, ending date-time)
        '''
        today = datetime.now().replace(microsecond=0)
        if self._item['start_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
            start_date = datetime(
                year=self._item[ 'start_date' ][0],
                month=self._item[ 'start_date' ][1],
                day=self._item[ 'start_date' ][2],
            ) + PyRadioTime.pyradio_time_to_timedelta(
                self._item['start_time']
            )
        else:
            start_date = today + PyRadioTime.pyradio_time_to_timedelta(
                self._item['start_duration']
            )

        if self._item['end_type'] == PyRadioScheduleTimeType.TIME_ABSOLUTE:
            end_date = datetime(
                self._item['end_date'][0],
                self._item['end_date'][1],
                self._item['end_date'][1]
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

        return start_date, end_date

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
            self.time = PyRadioTime.string_to_pyradio_time(datetime.now().strftime('%H:%M%S'))
        return self.date.strftime('%Y-%m-%d') + ' ' + PyRadioTime.pyradio_time_to_string(self.time)

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
        # print('    a_time_string:', a_time_string)
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
            # print('    is_12_format:', is_12_format)
            # print('    my_string:', my_string)
            sp = my_string.split(':')
            # print('    sp =', sp)
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

        # print('    hour: ', hour)
        # print('    minute: ', minute)
        # print('    seconds: ', seconds)
        # print('    valid =', valid)
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

        # print('    valid =', valid)
        if not valid:
            a_date_time = datetime.now()
            hour = a_date_time.hour
            minute = a_date_time.minute
            seconds = a_date_time.second

        self.time = [hour, minute, seconds, is_12_format]
        # print('!!! self.time =', self.time)

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
    print(format_date_to_iso8851(datetime.now()))

    print('\n\n============')
    an_item = {
        'type': PyRadioScheduleItemType.TYPE_START_END,
        'start_type': 0,                            # TIME_ABSOLUTE, TYPE_RELATIVE
        'start_date':  [2022, 10, 15],
        'start_time': [11, 15, 12, 2],              # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
        'start_duration': [0, 0, 0, 0],
        'end_type': 1,                              # TIME_ABSOLUTE, TYPE_RELATIVE
        'end_date': [2023, 1, 1],
        'end_time': [3, 12, 2, 1],                  # NO_AM_PM_FORMAT, AM_FORMAT, PM_FORMAT
        'end_duration': [2, 15, 11, 0],
        'playlist': 'myplaylist',
        'station': 'mystation'
    }

    for n,k in an_item.items():
        print(n, ":", k)
    print('\n\n============')

    b = PyRadioScheduleItem(an_item)
    x, y = b.get_active_dates()
    print('start_date:', str(x))
    print('  end_date:', str(y))
    for n,k in b.item.items():
        print(n, ":", k)
