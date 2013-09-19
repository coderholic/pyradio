#!/usr/bin/env python

# PyRadio: Curses based Internet Radio Player
# http://www.coderholic.com/pyradio
# Ben Dowling - 2009 - 2010
# Kirill Klenov - 2012
import curses
import logging
import os
import random

from .log import Log
from . import player

import locale
locale.setlocale(locale.LC_ALL,"")


logger = logging.getLogger(__name__)


def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


class PyRadio(object):
    startPos = 0
    selection = 0
    playing = -1

    def __init__(self, stations, play=False):
        self.stations = stations
        self.play = play
        self.stdscr = None

    def setup(self, stdscr):
        self.stdscr = stdscr

        try:
            curses.curs_set(0)
        except:
            pass

        curses.init_pair(1, curses.COLOR_CYAN, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_YELLOW, curses.COLOR_BLACK)
        curses.init_pair(4, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLACK)
        curses.init_pair(6, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
        curses.init_pair(7, curses.COLOR_BLACK, curses.COLOR_GREEN)
        curses.init_pair(8, curses.COLOR_MAGENTA, curses.COLOR_BLACK)
        curses.init_pair(9, curses.COLOR_BLACK, curses.COLOR_GREEN)

        self.log = Log()
        # For the time being, supported players are mplayer and vlc.
        self.player = player.probePlayer()(self.log)

        self.stdscr.nodelay(0)
        self.setupAndDrawScreen()

        self.run()

    def setupAndDrawScreen(self):
        self.maxY, self.maxX = self.stdscr.getmaxyx()

        self.headWin = curses.newwin(1, self.maxX, 0, 0)
        self.bodyWin = curses.newwin(self.maxY - 2, self.maxX, 1, 0)
        self.footerWin = curses.newwin(1, self.maxX, self.maxY - 1, 0)
        self.initHead()
        self.initBody()
        self.initFooter()

        self.log.setScreen(self.footerWin)

        #self.stdscr.timeout(100)
        self.bodyWin.keypad(1)

        #self.stdscr.noutrefresh()

        curses.doupdate()

    def initHead(self):
        from pyradio import version

        info = " PyRadio %s " % version
        self.headWin.addstr(0, 0, info, curses.color_pair(4))
        rightStr = "www.coderholic.com/pyradio"
        self.headWin.addstr(0, self.maxX - len(rightStr) - 1, rightStr,
                            curses.color_pair(2))
        self.headWin.bkgd(' ', curses.color_pair(7))
        self.headWin.noutrefresh()

    def initBody(self):
        """ Initializes the body/story window """
        #self.bodyWin.timeout(100)
        #self.bodyWin.keypad(1)
        self.bodyMaxY, self.bodyMaxX = self.bodyWin.getmaxyx()
        self.bodyWin.noutrefresh()
        self.refreshBody()

    def initFooter(self):
        """ Initializes the body/story window """
        self.footerWin.bkgd(' ', curses.color_pair(7))
        self.footerWin.noutrefresh()

    def refreshBody(self):
        self.bodyWin.erase()
        self.bodyWin.box()

        self.bodyWin.move(1, 1)
        maxDisplay = self.bodyMaxY - 1
        for idx in range(maxDisplay - 1):
            if(idx > maxDisplay):
                break
            try:
                station = self.stations[idx + self.startPos]
                col = curses.color_pair(5)

                if idx + self.startPos == self.selection and \
                        self.selection == self.playing:
                    col = curses.color_pair(9)
                    self.bodyWin.hline(idx + 1, 1, ' ', self.bodyMaxX - 2, col)
                elif idx + self.startPos == self.selection:
                    col = curses.color_pair(6)
                    self.bodyWin.hline(idx + 1, 1, ' ', self.bodyMaxX - 2, col)
                elif idx + self.startPos == self.playing:
                    col = curses.color_pair(4)
                    self.bodyWin.hline(idx + 1, 1, ' ', self.bodyMaxX - 2, col)
                self.bodyWin.addstr(idx + 1, 1,
                                    "%2.d. %s" % (idx + self.startPos + 1,
                                    station[0]), col)

            except IndexError:
                break

        self.bodyWin.refresh()

    def run(self):

        if not self.play is False:
            num = (self.play and (int(self.play) - 1)
                   or random.randint(0, len(self.stations)))
            self.setStation(num)
            self.playSelection()
            self.refreshBody()

        while True:
            try:
                c = self.bodyWin.getch()
                ret = self.keypress(c)
                if (ret == -1):
                    return
            except KeyboardInterrupt:
                break

    def setStation(self, number):
        """ Select the given station number """
        number = max(0, number)
        number = min(number, len(self.stations) - 1)

        self.selection = number

        maxDisplayedItems = self.bodyMaxY - 2

        if self.selection - self.startPos >= maxDisplayedItems:
            self.startPos = self.selection - maxDisplayedItems + 1
        elif self.selection < self.startPos:
            self.startPos = self.selection

    def playSelection(self):
        self.playing = self.selection
        name = self.stations[self.selection][0]
        stream_url = self.stations[self.selection][1].strip()
        self.log.write('Playing ' + name)
        try:
            self.player.play(stream_url)
        except OSError:
            self.log.write('Error starting player.'
                           'Are you sure mplayer is installed?')

    def keypress(self, char):
        # Number of stations to change with the page up/down keys
        pageChange = 5

        if char == curses.KEY_EXIT or char == ord('q'):
            self.player.close()
            return -1

        if char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            self.playSelection()
            self.refreshBody()
            self.setupAndDrawScreen()
            return

        if char == ord(' '):
            if self.player.isPlaying():
                self.player.close()
                self.log.write('Playback stopped')
            else:
                self.playSelection()

            self.refreshBody()
            return

        if char == curses.KEY_DOWN or char == ord('j'):
            self.setStation(self.selection + 1)
            self.refreshBody()
            return

        if char == curses.KEY_UP or char == ord('k'):
            self.setStation(self.selection - 1)
            self.refreshBody()
            return

        if char == ord('+'):
            self.player.volumeUp()
            return

        if char == ord('-'):
            self.player.volumeDown()
            return

        if char == curses.KEY_PPAGE:
            self.setStation(self.selection - pageChange)
            self.refreshBody()
            return

        if char == curses.KEY_NPAGE:
            self.setStation(self.selection + pageChange)
            self.refreshBody()
            return

        if char == ord('m'):
            self.player.mute()
            return

        if char == ord('r'):
            # Pick a random radio station
            self.setStation(random.randint(0, len(self.stations)))
            self.playSelection()
            self.refreshBody()

        if char == ord('#') or char == curses.KEY_RESIZE:
            self.setupAndDrawScreen()

# pymode:lint_ignore=W901
