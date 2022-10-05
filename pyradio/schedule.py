from sys import exit
from datetime import date, datetime, timedelta
from calendar import monthrange

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

    def __init__( self, date=None, time=None):
        self.time = self.string_to_pyradio_time(time)
        if date:
            self.date = self.set_date(date)
        else:
            self.date = None
        self.datetime = None

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
            # if a_time[-1] == 2:
            #     a_date = a_date + timedelta(hours=12)
            return '{0} {1}'.format(
                a_date.strftime('%H:%M:%S'),
                'PM' if a_time[-1] == self.PM_FORMAT else 'AM'
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

    def set_date(self, t_date=None):
        if t_date:
            try:
                self.date = date.fromisoformat(t_date)
                return True
            except ValueError:
                return False
        else:
            self.date = date.today()

    def set_time(self, t_time):
        self.time = self.string_to_pyradio_time(t_time)

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

    x = PyRadioTime.pyradio_time_diference_in_seconds(
        [1, 10, 15], [1, 12, 20]
    )
    print(x)
    print(PyRadioTime.seconds_to_sting(x))
    exit()

    old = datetime.now()
    now = old + timedelta(seconds=1*60 + 10)

    import time
    import os
    while True:
        d = now - old
        old = datetime.now()
        os.system('clear')
        print('Remaining:', PyRadioTime.delta_to_sting(d))
        if old >= now:
            break
        time.sleep(.5)

