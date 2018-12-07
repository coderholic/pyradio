#!/usr/bin/env python

# PyRadio: Curses based Internet Radio Player
# http://www.coderholic.com/pyradio
# Ben Dowling - 2009 - 2010
# Kirill Klenov - 2012
# Peter Stevenson (2E0PGS) - 2018
# Spiros Georgaras - 2018

import curses
import logging
import os
import random
from sys import version as python_version

from .log import Log
from . import player

import locale
locale.setlocale(locale.LC_ALL, "")


logger = logging.getLogger(__name__)

""" Modes of Operation """
NORMAL_MODE = -1
NO_PLAYER_ERROR_MODE = 0
MAIN_HELP_MODE = 100
PLAYLIST_MODE = 101
PLAYLIST_HELP_MODE = 102

def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


class PyRadio(object):
    startPos = 0
    selection = 0
    selection_backup = 0
    playing = -1
    jumpnr = ""
    hWin = None

    operation_mode = NORMAL_MODE

    def __init__(self, stations_cnf, play=False, req_player=''):
        self.cnf = stations_cnf
        self.play = play
        self.stdscr = None
        self.requested_player = req_player

    def setup(self, stdscr):
        if logger.isEnabledFor(logging.INFO):
            logger.info("GUI initialization on python v. {}".format(python_version).replace('\n', ' ').replace('\r', ' '))
        self.stdscr = stdscr
        from pyradio import version
        self.info = " PyRadio {0} ".format(version)
        # git_description can be set at build time
        # if so, revision will be shown along with the version
        # if revision is not 0
        git_description = ''
        if git_description:
            if git_description == 'not_from_git':
                if logger.isEnabledFor(logging.INFO):
                    logger.info("RyRadio built from zip file (revision unknown)")
            else:
                git_info = git_description.split('-')
                if git_info[1] != '0':
                    self.info = " PyRadio {0}-r{1} ".format(version, git_info[1])
                if logger.isEnabledFor(logging.INFO):
                    logger.info("RyRadio built from git: https://github.com/coderholic/pyradio/commit/{0} (rev. {1})".format(git_info[-1], git_info[1]))

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
        try:
            self.player = player.probePlayer(requested_player=self.requested_player)(self.log)
        except:
            # no player
            self.operation_mode = NO_PLAYER_ERROR_MODE

        self.stdscr.nodelay(0)
        self.setupAndDrawScreen()

        self.run()

    def setupAndDrawScreen(self):
        self.maxY, self.maxX = self.stdscr.getmaxyx()

        self.headWin = curses.newwin(1, self.maxX, 0, 0)
        self.bodyWin = curses.newwin(self.maxY - 2, self.maxX, 1, 0)
        self.footerWin = curses.newwin(1, self.maxX, self.maxY - 1, 0)
        # txtWin used mainly for error reports
        self.txtWin = curses.newwin(self.maxY - 4, self.maxX - 4, 2, 2)
        self.initHead(self.info)
        self.initBody()
        self.initFooter()

        self.log.setScreen(self.footerWin)

        #self.stdscr.timeout(100)
        self.bodyWin.keypad(1)

        #self.stdscr.noutrefresh()

        curses.doupdate()

    def initHead(self, info):
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
        if self.operation_mode == NO_PLAYER_ERROR_MODE:
            if self.requested_player:
                txt = """Rypadio is not able to use the player you specified.

                This means that either this particular player is not supported
                by PyRadio, or that you have simply misspelled its name.

                PyRadio currently supports three players: mpv, mplayer and vlc,
                automatically detected in this order."""
            else:
                txt = """PyRadio is not able to detect any players."

                PyRadio currently supports three players: mpv, mplayer and vlc,
                automatically detected in this order.

                Please install any one of them and try again.

                Please keep in mind that if mpv is installed, socat must be
                installed as well."""
            self.refreshNoPlayerBody(txt)
        else:
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
        pad = len(str(len(self.cnf.stations)))
        for lineNum in range(maxDisplay - 1):
            i = lineNum + self.startPos
            if self.operation_mode == PLAYLIST_MODE:
                """ display existing playlists """
                col = curses.color_pair(5)
                self.bodyWin.addstr(0, 2, ' Select playlist to open ', col)
                pass
            else:
                """ display stations """
                if i < len(self.cnf.stations):
                    self.__displayBodyLine(lineNum, pad, self.cnf.stations[i])
        self.bodyWin.refresh()

    def refreshNoPlayerBody(self, a_string):
        col = curses.color_pair(5)
        self.bodyWin.box()
        lines = a_string.split('\n')
        lineNum = 0
        self.txtWin.erase()
        for line in lines:
            try:
                self.txtWin.addstr(lineNum , 0, line.replace('\r', '').strip(), col)
            except:
                break
            lineNum += 1
        self.bodyWin.refresh()
        self.txtWin.refresh()

    def __displayBodyLine(self, lineNum, pad, station):
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
        line = "{0}. {1}".format(str(lineNum + self.startPos + 1).rjust(pad), station[0])
        self.bodyWin.addstr(lineNum + 1, 1, line, col)

    def run(self):
        if self.operation_mode == NO_PLAYER_ERROR_MODE:
            if self.requested_player:
                if ',' in self.requested_player:
                    self.log.write('None of "{}" players is available. Press any key to exit....'.format(self.requested_player))
                else:
                    self.log.write('Player "{}" not available. Press any key to exit....'.format(self.requested_player))
            else:
                self.log.write("No player available. Press any key to exit....")
            self.bodyWin.getch()
        else:
            self.log.write('Selected player: {}'.format(self._format_player_string()))
            if not self.play is False:
                if self.play is None:
                    num = random.randint(0, len(self.cnf.stations))
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
            number = len(self.cnf.stations) - 1
        elif number >= len(self.cnf.stations):
            number = 0

        self.selection = number

        maxDisplayedItems = self.bodyMaxY - 2

        if self.selection - self.startPos >= maxDisplayedItems:
            self.startPos = self.selection - maxDisplayedItems + 1
        elif self.selection < self.startPos:
            self.startPos = self.selection

    def playSelection(self):
        self.playing = self.selection
        name = self.cnf.stations[self.selection][0]
        stream_url = self.cnf.stations[self.selection][1].strip()
        self.log.write('Playing ' + name)
        try:
            self.player.play(name, stream_url)
        except OSError:
            self.log.write('Error starting player.'
                           'Are you sure a supported player is installed?')

    def _format_player_string(self):
        if self.player.PLAYER_CMD == 'cvlc':
            return 'vlc'
        return self.player.PLAYER_CMD

    def keypress(self, char):
        # if no player, don't serve keyboard
        if self.operation_mode == NO_PLAYER_ERROR_MODE:
            return

        elif self.operation_mode == MAIN_HELP_MODE:
            """ Main help in on, just update """
            self.hWin = None
            self.operation_mode = -1
            self.setupAndDrawScreen()
            return

        elif self.operation_mode == PLAYLIST_HELP_MODE:
            """ open playlist help """
            self.operation_mode = PLAYLIST_MODE
            self.refreshBody()
            return

        else:
            # Number of stations to change with the page up/down keys
            pageChange = 5

            if char in (ord('?'), ord('/')):
                if self.operation_mode == PLAYLIST_MODE:
                    txt = """Up/j/PgUp
                             Down/k/PgDown    Change playlist selection.
                             Enter/Right/l
                             Space/Left/h     Open selected playlist.
                             g                Jump to first playlist.
                             <n>G             Jump to n-th / last playlist.
                             Esc/q            Cancel. """
                    self._show_help(txt, mode_to_set=PLAYLIST_HELP_MODE)
                else:
                    txt = """Up/j/PgUp
                             Down/k/PgDown    Change station selection.
                             g                Jump to first station.
                             <n>G             Jump to n-th / last station.
                             Enter/Right/l    Play selected station.
                             r                Select and play a random station.
                             Space/Left/h     Stop/start playing selected station.
                             -/+ or ,/.       Change volume.
                             m                Mute.
                             v                Save volume (not applicable with vlc).
                             o                Open playlist.
                             #                Redraw window.
                             Esc/q            Quit. """
                    self._show_help(txt)
                return

            if char in (ord('G'), ):
                if self.jumpnr == "":
                    self.setStation(-1)
                else:
                    jumpto=min(int(self.jumpnr)-1,len(self.cnf.stations)-1)
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

            if char in (ord('g'), ):
                self.setStation(0)
                self.refreshBody()
                return

            if char in (curses.KEY_EXIT, ord('q')):
                if self.operation_mode == PLAYLIST_MODE:
                    """ return to stations view """
                    self.selection = self.selection_backup
                    self.operation_mode = NORMAL_MODE
                    self.refreshBody()
                    return
                else:
                    """ exit """
                    try:
                        self.player.close()
                    except:
                        pass
                    return -1

            if char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
                    curses.KEY_RIGHT, ord('l')):
                self.playSelection()
                self.refreshBody()
                self.setupAndDrawScreen()
                return

            if char in (ord(' '), curses.KEY_LEFT, ord('h')):
                if self.player.isPlaying():
                    self.player.close()
                    self.log.write('Playback stopped')
                else:
                    self.playSelection()

                self.refreshBody()
                return

            if char in (curses.KEY_DOWN, ord('j')):
                self.setStation(self.selection + 1)
                self.refreshBody()
                return

            if char in (curses.KEY_UP, ord('k')):
                self.setStation(self.selection - 1)
                self.refreshBody()
                return

            if char in (curses.KEY_PPAGE, ):
                self.setStation(self.selection - pageChange)
                self.refreshBody()
                return

            if char in (curses.KEY_NPAGE, ):
                self.setStation(self.selection + pageChange)
                self.refreshBody()
                return

            if self.operation_mode == NORMAL_MODE:
                if char in (ord('o'), ):
                    """ open playlist """
                    tmp = self.selection
                    self.selection = self.selection_backup
                    self.selection_backup= tmp
                    self.operation_mode = PLAYLIST_MODE
                    self.refreshBody()
                    return

                if char in (ord('v'), ):
                    ret_string = self.player.save_volume()
                    if ret_string:
                        self.log.write(ret_string)
                        self.player.threadUpdateTitle(self.player.status_update_lock)
                    return

                if char in (ord('+'), ord('='), ord('.')):
                    self.player.volumeUp()
                    return

                if char in (ord('-'), ord(',')):
                    self.player.volumeDown()
                    return

                if char in (ord('m'), ):
                    self.player.toggleMute()
                    return

                if char in (ord('r'), ):
                    # Pick a random radio station
                    self.setStation(random.randint(0, len(self.cnf.stations)))
                    self.playSelection()
                    self.refreshBody()
                    return

                if char in (ord('#'), curses.KEY_RESIZE):
                    self.headWin = False
                    self.setupAndDrawScreen()
                    return

    def _show_help(self, txt, mode_to_set=MAIN_HELP_MODE):
        self.operation_mode = mode_to_set
        txt_col = curses.color_pair(5)
        box_col = curses.color_pair(2)
        caption_col = curses.color_pair(4)
        caption = ' Help '
        prompt = ' Press any key to hide '
        lines = txt.split('\n')
        st_lines = [item.replace('\r','') for item in lines]
        lines = [item.strip() for item in st_lines]
        mheight = len(lines) + 2
        mwidth = len(max(lines, key=len)) + 4

        if self.maxY - 2 < mheight or self.maxX < mwidth:
            txt="Window too small to show help..."
            mheight = 3
            mwidth = len(txt) + 4
            if self.maxX < mwidth:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  ***  Window too small even to show help warning  ***')
                self.operation_mode = NORMAL_MODE
                return
            lines = [ txt , ] 
        self.hWin = curses.newwin(mheight,mwidth,int((self.maxY-mheight)/2),int((self.maxX-mwidth)/2))
        self.hWin.attrset(box_col)
        self.hWin.box()
        self.hWin.addstr(0, int((mwidth-len(caption))/2), caption, caption_col)
        for i, n in enumerate(lines):
            self.hWin.addstr(i+1, 2, n.replace('_', ' '), caption_col)
        self.hWin.addstr(mheight - 1, int(mwidth-len(prompt)-1), prompt)

        self.hWin.refresh()


# pymode:lint_ignore=W901
