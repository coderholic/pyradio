from sys import version_info as python_version
from datetime import date as ddate, datetime, timedelta
from calendar import monthrange
import logging

import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

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
            A datetime.date
        start_time
            A PyRadioTime (XX:XX:[XX] [AM/PM])

        start type
            "A" or "I"
                "A": Date and Time is absolute
                "I": Date and Time is relative
                     In this case, the field becomes "IXX:XX:XX"
                     and the start date is the creation date
            This gives a hint for the presenting window

        end_date
            A datetime.date
        end_time
            A PyRadioTime (XX:XX:[XX] [AM/PM])

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
    def __init__(self):
        self._type = None           # string (E)nd or (B)oth
        self._start_date = None     # datetime.date
        self._start_time=None       # PyRadioTime time
        self._start_type = None     # Type of time (A: absolute time, I: In time)
        self._end_date=None         # datetime.date
        self._end_time=None         # PyradioTime time
        self._end_type = None       # Type of time (T: absolute time, I: In time)
        self._playlist=None         # string (playlist title)
        self._station=None          # string
        self._start_duration = ''
        self._end_duration = ''

    @property
    def type (self):
        return self._type

    @type.setter
    def type(self, value):
        if value in ('S', 'E', 'B'):
            self._type = value

    @property
    def start_date (self):
        return self._start_date

    @property
    def start_time(self):
        return self._start_time

    @property
    def start_type (self):
        return self._start_type

    @start_type.setter
    def start_type(self, value):
        if value in ('A', 'I'):
            self._start__type = value
            if value[0] == "I":
                self._start_type = "I"
                self._start_duration = value[1:]
            else:
                self._start_duration = ''

    @property
    def end_date(self):
        return self._end_date

    @property
    def end_time(self):
        return self._end_time

    @property
    def end_type (self):
        return self._end_type

    @end_type.setter
    def end_type(self, value):
        if value in ('A', 'I'):
            self._end__type = value
            if value[0] == "I":
                self._end_type = "I"
                self._end_duration = value[1:]
            else:
                self._end_duration = ''

    @property
    def playlist(self):
        return self._playlist

    @property
    def station(self):
        return self._station

    def __str__(self):
        if self._start_date is None and \
                self._end_date is None:
            return ''
        return '{0}`|`{1}`|`{2}`|`{3}`|`{4}`|`{5}`|`{6}'.format(
            self._type,
            self._format_date_string(self._start_date, self._start_time),
            self._start_type + self._start_duration,
            self._format_date_string(self._end_date, self._end_time),
            self._end_type + self._end_duration,
            self._playlist,
            self._station
        )

    def set_item(self, a_string):
        sp = a_string.split('`|`')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('new item = "{}"'.format(sp))
        if len(sp) != 7:
            raise ValueError
            return
        self._type = sp [0]
        self._start_date, self._start_time= self._date_time_string_to_date_time(sp[1])
        self._start_type = sp[2]
        self._end_date, self._end_time= self._date_time_string_to_date_time(sp[3])
        self._end_type = sp[4]
        self._playlist = sp[5]
        self._station = sp[6]

        if self._start_type[0] == "I":
            self._start_duration = self._start_type[1:]
            self._start_type = self._start_type[0]

        if self._end_type[0] == "I":
            self._end_duration = self._end_type[1:]
            self._end_type = self._end_type[0]


        self._fix_active_times()

    def _fix_active_times(self):
        if self._start_duration:
            t = datetime(self._start_date.year,
                         self._start_date.month,
                         self._start_date.day,
                         self._start_time[0],
                         self._start_time[1],
                         self._start_time[2]
                         )
            sp = self._start_duration.split(':')
            for n in range(0, line(sp)):
                sp[i] = int(sp[i])

            e = t + deltatime(hours=sp[0], minutes=sp[1], seconds=sp[2])

            print(e)

        if self._end_duration:
            t = datetime(self._start_date.year,
                         self._start_date.month,
                         self._start_date.day,
                         self._start_time[0],
                         self._start_time[1],
                         self._start_time[2]
                         )
            sp = self._end_duration.split(':')
            for i in range(0, len(sp)):
                sp[i] = int(sp[i])

            e = t + timedelta(hours=sp[0], minutes=sp[1], seconds=sp[2])

            print(e)



    def _date_time_string_to_date_time(self, a_string):
        '''
        string (date + time + [AM/PM]) to self.date, self.time
        '''
        pt = PyRadioTime()
        s_split = a_string.split()
        pt.set_date(s_split[0])
        if len(s_split) == 2:
            pt.set_time(s_split[1])
        else:
            pt.set_time(s_split[1] + ' ' + s_split[2])
        return pt.date, pt.time

    def _format_date_string(self, a_date, a_time):
        '''
        '''
        pdt = PyRadioTime()
        pdt.date = a_date
        pdt.time = a_time
        return pdt              # return __str__

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
                    hour =0
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

    def pyradio_time_to_time(self, a_time=None):
        if t_time is None:
            a_time = self.time
        else:
            a_time = t_time

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
    a= PyRadioScheduleItem()
    a.set_item('B`|`2022-10-15 23:15:12`|`A`|`2021-08-01 03:12:02 AM`|`I02:15:11`|`myplaylist`|`mystation')
    # a.set_item('B`|`2022-10-15 23:15:12`|`A`|``|`I02:15:11`|`myplaylist`|`mystation')
    print(a)
