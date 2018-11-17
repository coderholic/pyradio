#!/usr/bin/env python

# PyRadio: Curses based Internet Radio Player
# http://www.coderholic.com/pyradio
# Ben Dowling - 2009 - 2010
# Kirill Klenov - 2012
# Peter Stevenson (2E0PGS) - 2018

import curses
import logging
import os
import random

from .log import Log
from . import player

import locale
locale.setlocale(locale.LC_ALL, "")


logger = logging.getLogger(__name__)


def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


class PyRadio(object):
    startPos = 0
    selection = 0
    playing = -1
    jumpnr = ""

    def __init__(self, stations, play=False, req_player=''):
        self.stations = stations
        self.play = play
        self.stdscr = None
        self.requested_player = req_player

    def setup(self, stdscr):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("GUI initialization")
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
        # For the time being, supported players are mpv, mplayer and vlc.
        self.player = player.probePlayer(requested_player=self.requested_player)(self.log)

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

        info = " PyRadio {0} ".format(version)
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
        for lineNum in range(maxDisplay - 1):
            i = lineNum + self.startPos
            if i < len(self.stations):
                self.__displayBodyLine(lineNum, self.stations[i])
        self.bodyWin.refresh()

    def __displayBodyLine(self, lineNum, station):
        col = curses.color_pair(5)

        if lineNum + self.startPos == self.selection and \
                self.selection == self.playing:
            col = curses.color_pair(9)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        elif lineNum + self.startPos == self.selection:
            col = curses.color_pair(6)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        elif lineNum + self.startPos == self.playing:
            col = curses.color_pair(4)
            self.bodyWin.hline(lineNum + 1, 1, ' ', self.bodyMaxX - 2, col)
        line = "{0}. {1}".format(lineNum + self.startPos + 1, station[0])
        self.bodyWin.addstr(lineNum + 1, 1, line, col)

    def run(self):

        if not self.play is False:
            if self.play is None:
                num = random.randint(0, len(self.stations))
            else:
                num = int(self.play) - 1
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
        # If we press up at the first station, we go to the last one
        # and if we press down on the last one we go back to the first one.
        if number < 0:
            number = len(self.stations) - 1
        elif number >= len(self.stations):
            number = 0

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
                           'Are you sure a supported player is installed?')

    def keypress(self, char):
        # Number of stations to change with the page up/down keys
        pageChange = 5

        if char == ord('v'):
            ret_string = self.player.save_volume()
            if ret_string:
                self.log.write(ret_string)
                self.player.threadUpdateTitle(delay=1)
            return

        if char == ord('G'):
            if self.jumpnr == "":
                self.setStation(-1)
            else:
                jumpto=min(int(self.jumpnr)-1,len(self.stations)-1)
                jumpto=max(0,jumpto)
                self.setStation(jumpto)
            self.jumpnr = ""
            self.refreshBody()
            return

        if char in map(ord,map(str,range(0,10))):
            self.jumpnr += chr(char)
            return
        else:
            self.jumpnr = ""

        if char == ord('g'):
            self.setStation(0)
            self.refreshBody()
            return

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

        if char == ord('+') or char == ord('='):
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
