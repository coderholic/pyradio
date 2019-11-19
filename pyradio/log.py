# -*- coding: utf-8 -*-
from sys import version_info
import logging

logger = logging.getLogger(__name__)


class Log(object):
    """ Log class that outputs text to a curses screen """

    msg = None
    cursesScreen = None

    last_written_string = ''
    display_help_message = False

    asked_to_stop = False

    def __init__(self):
        self.width = None

    def setScreen(self, cursesScreen):
        self.cursesScreen = cursesScreen
        self.width = cursesScreen.getmaxyx()[1] - 5

        # Redisplay the last message
        if self.msg:
            self.write(self.msg)

    def write(self, msg, thread_lock=None, help_msg=False):
        if self.asked_to_stop:
            return
        """ msg may or may not be encoded """
        if self.cursesScreen:
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
            if help_msg or self.display_help_message:
                self.write_right('Press ? for help', thread_lock)
                self.display_help_message = True

    def write_right(self, msg, thread_lock=None):
        if self.asked_to_stop:
            return
        """ msg may or may not be encoded """
        if self.cursesScreen:
            if thread_lock is not None:
                thread_lock.acquire()
            try:
                a_msg = msg.strip()
                self.cursesScreen.addstr(0, self.width + 5 - len(a_msg) - 1, a_msg.replace("\r", "").replace("\n", ""))
            except:
                a_msg = msg.encode('utf-8', 'replace').strip()
                self.cursesScreen.addstr(0, self.width + 5 - len(a_msg) - 1, a_msg.replace("\r", "").replace("\n", ""))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Status right: "{}"'.format(a_msg))
            self.cursesScreen.refresh()
            if thread_lock is not None:
                thread_lock.release()

    def readline(self):
        pass
