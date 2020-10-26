# -*- coding: utf-8 -*-
import curses
from sys import version_info
import logging

logger = logging.getLogger(__name__)


class Log(object):
    """ Log class that outputs text to a curses screen """

    msg = suffix = counter = cursesScreen = None

    last_written_string = ''
    last_written_suffix=''
    display_help_message = False

    asked_to_stop = False

    _color_change = False

    lock = None

    def __init__(self):
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = int(cursesScreen.getmaxyx()[1] -1)

        # Redisplay the last message
        if self.msg:
            self.write(self.msg)

    def _do_i_print_last_char(self, first_print):
        if first_print:
            first_print = False
            try:
                self.cursesScreen.addstr(0, self.width +1, ' ')
            except:
                pass
        return first_print

    def write(self, msg=None, suffix=None, counter=None, help_msg=False, notify_function=None):
        if self.asked_to_stop:
            self.counter = None
            return
        if self.cursesScreen:
            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('before ----------------------------')
            #    logger.debug('msg = "{}"'.format(msg))
            #    logger.debug('self.msg = "{}"'.format(self.msg))
            #    logger.debug('suffix = "{}"'.format(suffix))
            #    logger.debug('self.suffix = "{}"'.format(self.suffix))
            #    logger.debug('counter = "{}"'.format(counter))
            #    logger.debug('self.counter = "{}"'.format(self.counter))

            first_print = True
            if msg is not None: self.msg = msg
            if suffix is not None: self.suffix = suffix
            if counter is not None: self.counter = counter

            #if logger.isEnabledFor(logging.DEBUG):
            #    logger.debug('after ----------------------------')
            #    logger.debug('msg = "{}"'.format(msg))
            #    logger.debug('self.msg = "{}"'.format(self.msg))
            #    logger.debug('suffix = "{}"'.format(suffix))
            #    logger.debug('self.suffix = "{}"'.format(self.suffix))
            #    logger.debug('counter = "{}"'.format(counter))
            #    logger.debug('self.counter = "{}"'.format(self.counter))

            """ update main message """
            if self.msg:
                if self.lock is not None:
                    self.lock.acquire()
                self.cursesScreen.erase()
                try:
                    d_msg = self.msg.strip()[0: self.width].replace("\r", "").replace("\n", "")
                    self.cursesScreen.addstr(0, 1, d_msg)
                except:
                    try:
                        d_msg = self.msg.encode('utf-8', 'replace').strip()[0: self.width].replace("\r", "").replace("\n", "")
                        self.cursesScreen.addstr(0, 1, d_msg)
                    except:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('Cannot update the Status Bar...')
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        logger.debug('Status: "{}"'.format(self.msg))
                    except:
                        pass
                self.cursesScreen.refresh()
                if self.lock is not None:
                    self.lock.release()

            self._active_width = self.width

            """ display suffix """
            if self.suffix:
                d_msg = ' [' + self.suffix + ']'
                if self.lock is not None:
                    self.lock.acquire()
                self.cursesScreen.addstr(0, self._active_width - len(d_msg), d_msg)
                self.cursesScreen.chgat(0, self._active_width - len(d_msg) +1, len(d_msg) -1, curses.color_pair(1))
                first_print = self._do_i_print_last_char(first_print)
                self.cursesScreen.refresh()
                if self.lock is not None:
                    self.lock.release()
                self._active_width -= len(d_msg)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Suffix: {}'.format(self.suffix))

            """ display counter """
            if self.counter:
                if self.counter == '0':
                    self.counter = None
                if self.counter:
                    if self.suffix:
                        self._active_width += 1
                    d_msg = ' [' + self.counter + ']'
                    if self.lock is not None:
                        self.lock.acquire()
                    self.cursesScreen.addstr(0, self._active_width - len(d_msg), d_msg)
                    first_print = self._do_i_print_last_char(first_print)
                    self.cursesScreen.refresh()
                    if self.lock is not None:
                        self.lock.release()
                    self._active_width -= len(d_msg)
            if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Counter: {}'.format(self.counter))

            """ display press ? """
            if help_msg or self.display_help_message:
                self.counter = None
                suffix_string = ' Press ? for help'
                if self.lock is not None:
                    self.lock.acquire()
                self.cursesScreen.addstr(0, self._active_width - len(suffix_string), suffix_string)
                self.cursesScreen.refresh()
                if self.lock is not None:
                    self.lock.release()
                self.display_help_message = True
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Press ? for help: yes')
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Press ? for help: no')

    def readline(self):
        pass
