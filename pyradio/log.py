# -*- coding: utf-8 -*-
import curses
from sys import version_info
import logging

logger = logging.getLogger(__name__)


class Log(object):
    """ Log class that outputs text to a curses screen """

    msg = None
    cursesScreen = None

    last_written_string = ''
    last_written_suffix=''
    display_help_message = False

    asked_to_stop = False

    _color_change = False

    def __init__(self):
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = cursesScreen.getmaxyx()[1] - 5

        # Redisplay the last message
        if self.msg:
            self.write(self.msg)

    def write(self, msg=None, suffix=None, thread_lock=None, help_msg=False):
        if self.asked_to_stop:
            return
        """ msg may or may not be encoded """
        if self.cursesScreen:
            if suffix == '':
                if msg is None:
                    msg = self.last_written_string
                self.last_written_suffix = ''
            if msg:
                if thread_lock is not None:
                    thread_lock.acquire()
                self.cursesScreen.erase()
                try:
                    self.msg = msg.strip()[0: self.width].replace("\r", "").replace("\n", "")
                    self.cursesScreen.addstr(0, 1, self.msg)
                except:
                    try:
                        self.msg = msg.encode('utf-8', 'replace').strip()[0: self.width].replace("\r", "").replace("\n", "")
                        self.cursesScreen.addstr(0, 1, self.msg)
                    except:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('Cannot update the Status Bar...')
                if logger.isEnabledFor(logging.DEBUG):
                    try:
                        logger.debug('Status: "{}"'.format(msg))
                    except:
                        pass
                self.cursesScreen.refresh()
                if thread_lock is not None:
                    thread_lock.release()
                self.last_written_string = msg
            suffix_string = ''
            if help_msg or self.display_help_message:
                suffix_string = ' Press ? for help'
                self.display_help_message = True
                self._color_change = False
            if suffix is None:
                # use last suffix
                if self.last_written_suffix:
                    #suffix_string += ' ' + self.last_written_suffix
                    suffix_string += ' [' + self.last_written_suffix + ']'
                    self._color_change = True
            elif suffix == '':
                # clear last suffix
                self.last_written_suffix = ''
                self._color_change = False
            else:
                # write new suffix
                suffix_string += ' [' + suffix + ']'
                #suffix_string += ' ' + suffix
                self.last_written_suffix = suffix
                self._color_change = True
                self._highlight_len = len(suffix)

            if suffix_string:
                self._write_right(suffix_string, thread_lock=thread_lock)

    def _write_right(self, msg, thread_lock=None):
        if self.asked_to_stop:
            return
        """ msg may or may not be encoded """
        if self.cursesScreen:
            if thread_lock is not None:
                thread_lock.acquire()
            try:
                a_msg = msg
                self.cursesScreen.addstr(0, self.width + 5 - len(a_msg) - 1, a_msg.replace("\r", "").replace("\n", ""))
            except:
                a_msg = msg.encode('utf-8', 'replace')
                self.cursesScreen.addstr(0, self.width + 5 - len(a_msg) - 1, a_msg.replace("\r", "").replace("\n", ""))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Status right: "{}"'.format(a_msg))
            if self._color_change:
                self.cursesScreen.chgat(0, self.width + 2 - self._highlight_len, self._highlight_len + 2, curses.color_pair(1))
            self.cursesScreen.refresh()
            if thread_lock is not None:
                thread_lock.release()

    def readline(self):
        pass
