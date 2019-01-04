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
#import signal
from sys import version as python_version, version_info
from os.path import join, basename, getmtime, getsize
from time import ctime

from .log import Log
from . import player

import locale
locale.setlocale(locale.LC_ALL, "")


logger = logging.getLogger(__name__)

""" Modes of Operation """
NO_PLAYER_ERROR_MODE = -1
NORMAL_MODE = 0
PLAYLIST_MODE = 1
REMOVE_STATION_MODE = 50
SAVE_PLAYLIST_MODE = 51
ASK_TO_SAVE_PLAYLIST_MODE = 52
MAIN_HELP_MODE = 100
PLAYLIST_HELP_MODE = 101
PLAYLIST_LOAD_ERROR_MODE = 200
PLAYLIST_RELOAD_ERROR_MODE = 201
PLAYLIST_RELOAD_CONFIRM_MODE = 202
PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE = 203
PLAYLIST_SCAN_ERROR_MODE = 204
SAVE_PLAYLIST_ERROR_1_MODE = 204
SAVE_PLAYLIST_ERROR_2_MODE = 205

def rel(path):
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), path)


class PyRadio(object):
    operation_mode = NORMAL_MODE

    """ number of items (stations or playlists) in current view """
    number_of_items = 0

    playing = -1
    jumpnr = ""
    """ Help window
        also used for displaying messages,
        asking for confirmation etc. """
    helpWin = None

    """ Used when loading new playlist.
        If the first station (selection) exists in the new playlist,
        we mark it as selected
        If the seconf station (playing) exists in the new playlist,
        we continue playing, otherwise, we stop playback """
    active_stations = [ [ '', 0 ], [ '', -1 ] ]

    # Number of stations to change with the page up/down keys
    pageChange = 5

    def __init__(self, pyradio_config, play=False, req_player=''):
        self.cnf = pyradio_config
        self.selections = [ (0, 0, -1, self.cnf.stations),
                            (0, 0, -1, self.cnf.playlists)]
        self.selection, self.startPos, self.playing, self.stations = self.selections[self.operation_mode]
        self.play = play
        self.stdscr = None
        self.requested_player = req_player
        self.number_of_items = len(self.cnf.stations)

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
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE = NO_PLAYER_ERROR_MODE')

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
            if self.operation_mode == MAIN_HELP_MODE:
                self.operation_mode = NORMAL_MODE
                self.helpWin = None
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: MAIN_HELP_MODE => NORMAL_MODE')
            elif self.operation_mode == PLAYLIST_HELP_MODE:
                self.operation_mode = PLAYLIST_MODE
                self.helpWin = None
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: PLAYLIST_HELP_MODE =>  PLAYLIST_MODE')
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
        self._print_body_header()
        if self.number_of_items > 0:
            pad = len(str(len(self.stations)))
            for lineNum in range(maxDisplay - 1):
                i = lineNum + self.startPos
                if i < len(self.stations):
                    self.__displayBodyLine(lineNum, pad, self.stations[i])
                else:
                    break
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

    def _print_body_header(self):
        if self.operation_mode == NORMAL_MODE:
            align = 1
            w_header = self.cnf.stations_filename_only_no_extension
            if self.cnf.dirty_playlist:
                align += 1
                w_header = '*' + self.cnf.stations_filename_only_no_extension
            while len(w_header)> self.bodyMaxX - 14:
                w_header = w_header[:-1]
            self.bodyWin.addstr(0,
                    int((self.bodyMaxX - len(w_header)) / 2) - align, '[',
                    curses.color_pair(5))
            self.bodyWin.addstr(w_header,curses.color_pair(4))
            self.bodyWin.addstr(']',curses.color_pair(5))

        elif self.operation_mode == PLAYLIST_MODE or \
                self.operation_mode == PLAYLIST_LOAD_ERROR_MODE:
            """ display playlists header """
            w_header = ' Select playlist to open '
            self.bodyWin.addstr(0,
                    int((self.bodyMaxX - len(w_header)) / 2),
                    w_header,
                    curses.color_pair(5))

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

        if self.operation_mode == NORMAL_MODE or \
            self.operation_mode == REMOVE_STATION_MODE or \
            self.operation_mode == PLAYLIST_RELOAD_ERROR_MODE or \
            self.operation_mode == PLAYLIST_RELOAD_CONFIRM_MODE or \
            self.operation_mode == PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE or \
            self.operation_mode == SAVE_PLAYLIST_ERROR_1_MODE or \
            self.operation_mode == SAVE_PLAYLIST_ERROR_2_MODE or \
            self.operation_mode == ASK_TO_SAVE_PLAYLIST_MODE:
            line = "{0}. {1}".format(str(lineNum + self.startPos + 1).rjust(pad), station[0])
        elif self.operation_mode == PLAYLIST_MODE or \
                self.operation_mode == PLAYLIST_LOAD_ERROR_MODE:
            line = self._format_playlist_line(lineNum, pad, station)
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
            try:
                self.bodyWin.getch()
            except KeyboardInterrupt:
                pass
        else:
            #signal.signal(signal.SIGINT, self.ctrl_c_handler)
            self.log.write('Selected player: {}'.format(self._format_player_string()))
            if self.play is not False:
                if self.play is None:
                    num = random.randint(0, len(self.stations))
                else:
                    if self.play.replace('-', '').isdigit():
                        num = int(self.play) - 1
                self.setStation(num)
                if self.number_of_items > 0:
                    self.playSelection()
                self.refreshBody()

            while True:
                try:
                    c = self.bodyWin.getch()
                    ret = self.keypress(c)
                    if (ret == -1):
                        return
                except KeyboardInterrupt:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Ctrl-C pressed... Exiting...')
                    self.player.ctrl_c_pressed = True
                    self.ctrl_c_handler(0, 0)
                    break

    def ctrl_c_handler(self, signum, frame):
        self.ctrl_c_pressed = True
        if self.cnf.dirty_playlist:
            """ Try to auto save playlist on exit
                Do not check result!!! """
            self.saveCurrentPlaylist()
        """ Try to auto save config on exit
            Do not check result!!! """
        self.cnf._save_config()

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
            self.player.play(name, stream_url)
        except OSError:
            self.log.write('Error starting player.'
                           'Are you sure a supported player is installed?')

    def stopPlayer(self):
        """ stop player """
        try:
            self.player.close()
        except:
            pass
        finally:
            self.playing = -1
            self.log.write('{}: Playback stopped'.format(self._format_player_string()))
            #self.log.write('Playback stopped')

    def removeStation(self):
        if self.cnf.confirm_station_deletion:
            txt = '''Are you sure you want to delete station:
            "{}"?

            Press "y" to confirm, "Y" to confirm and not
            be asked again, or any other key to cancel'''
            self._show_help(txt.format(self.stations[self.selection][0]),
                    REMOVE_STATION_MODE, caption = ' Station Deletion ', prompt = '')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE = REMOVE_STATION_MODE')
        else:
            self.operation_mode = REMOVE_STATION_MODE
            curses.ungetch('y')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE = Auto REMOVE_STATION_MODE')

    def saveCurrentPlaylist(self, stationFile =''):
        ret = self.cnf.save_playlist_file(stationFile)
        self.refreshBody()
        if ret == -1:
            self._print_save_playlist_error_1()
        elif ret == -2:
            self._print_save_playlist_error_2()
        if ret < 0 and logger.isEnabledFor(logging.DEBUG):
            logger.debug('Error saving playlist: "{}"'.format(self.cnf.stations_file))
        return ret

    def reloadCurrentPlaylist(self, mode):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Reloading current playlist')
        self._get_active_stations()
        txt = '''Reloading playlist. Please wait...'''
        self._show_help(txt, NORMAL_MODE, caption=' ', prompt=' ')
        self.jumpnr = ''
        ret = self.cnf.read_playlist_file(self.cnf.stations_file)
        if ret == -1:
            self.stations = self.cnf.playlists
            self._print_playlist_reload_error()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Error reloading playlist: "{}"'.format(self.cnf.stations_file))
        else:
            self.number_of_items = ret
            self.operation_mode = NORMAL_MODE
            self._align_stations_and_refresh(PLAYLIST_RELOAD_CONFIRM_MODE)
            if logger.isEnabledFor(logging.DEBUG):
                if mode == PLAYLIST_RELOAD_CONFIRM_MODE:
                    logger.debug('MODE: PLAYLIST_RELOAD_CONFIRM_MODE -> NORMAL_MODE')
                else:
                    logger.debug('MODE: PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE -> NORMAL_MODE')
        return



        #self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.stations)
        #self.operation_mode = PLAYLIST_MODE
        #self.selection, self.startPos, self.playing, self.stations = self.selections[self.operation_mode]
        #self.number_of_items, self.playing = self.read_playlists()
        #self.stations = self.cnf.playlists
        #if self.number_of_items == 0:
        #    return
        #else:
        #    self.refreshBody()
        #    if logger.isEnabledFor(logging.DEBUG):
        #        logger.debug('MODE: NORMAL_MODE -> PLAYLIST_MODE')
        #    return

        #playing = self.playing
        #selection = self.selections
        #number_of_items = self.number_of_items
        #if self.player.isPlaying() and self.cnf.dirty_playlist:
        #    # TODO: ask to save previous playlist
        #    pass

    def readPlaylists(self):
        num_of_playlists, playing = self.cnf.read_playlists()
        if num_of_playlists == 0:
            txt = '''No playlists found!!!

            This should never have happened; PyRadio is missing its
            default playlist. Therefore, it has to terminate now.
            It will re-create it the next time it is lounched.
            '''
            self._show_help(txt.format(self.cnf.stations_filename_only),
                    mode_to_set = PLAYLIST_SCAN_ERROR_MODE,
                    caption = ' Error ',
                    prompt = ' Press any key to exit ')
            if logger.isEnabledFor(logging.ERROR):
                logger.error('No playlists found!!!')
        return num_of_playlists, playing

    def _format_player_string(self):
        if self.player.PLAYER_CMD == 'cvlc':
            return 'vlc'
        return self.player.PLAYER_CMD

    def _show_help(self, txt,
                mode_to_set=MAIN_HELP_MODE,
                caption=' Help ',
                prompt=' Press any key to hide ',
                too_small_msg='Window too small to show message'):
        self.operation_mode = mode_to_set
        txt_col = curses.color_pair(5)
        box_col = curses.color_pair(2)
        caption_col = curses.color_pair(4)
        lines = txt.split('\n')
        st_lines = [item.replace('\r','') for item in lines]
        lines = [item.strip() for item in st_lines]
        mheight = len(lines) + 2
        mwidth = len(max(lines, key=len)) + 4

        if self.maxY - 2 < mheight or self.maxX < mwidth:
            txt = too_small_msg
            mheight = 3
            mwidth = len(txt) + 4
            if self.maxX < mwidth:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('  ***  Window too small even to show help warning  ***')
                self.operation_mode = NORMAL_MODE
                return
            lines = [ txt , ]
        self.helpWin = curses.newwin(mheight,mwidth,int((self.maxY-mheight)/2),int((self.maxX-mwidth)/2))
        self.helpWin.attrset(box_col)
        self.helpWin.box()
        if caption.strip():
            self.helpWin.addstr(0, int((mwidth-len(caption))/2), caption, caption_col)
        for i, n in enumerate(lines):
            self.helpWin.addstr(i+1, 2, n.replace('_', ' '), caption_col)
        if prompt.strip():
            self.helpWin.addstr(mheight - 1, int(mwidth-len(prompt)-1), prompt)
        self.helpWin.refresh()

    def _format_playlist_line(self, lineNum, pad, station):
        """ format playlist line so that if fills self.maxX """
        line = "{0}. {1}".format(str(lineNum + self.startPos + 1).rjust(pad), station[0])
        f_data = ' [{0}, {1}]'.format(station[2], station[1])
        if version_info < (3, 0):
            if len(line.decode('utf-8')) + len(f_data.decode('utf-8')) > self.bodyMaxX -2:
                """ this is too long, try to shorten it
                    by removing file size """
                f_data = ' [{0}]'.format(station[1])
            if len(line.decode('utf-8')) + len(f_data.decode('utf-8')) > self.bodyMaxX - 2:
                """ still too long. start removing chars """
                while len(line.decode('utf-8')) + len(f_data.decode('utf-8')) > self.bodyMaxX - 3:
                    f_data = f_data[:-1]
                f_data += ']'
            """ if too short, pad f_data to the right """
            if len(line.decode('utf-8')) + len(f_data.decode('utf-8')) < self.maxX - 2:
                while len(line.decode('utf-8')) + len(f_data.decode('utf-8')) < self.maxX - 2:
                    line += ' '
        else:
            if len(line) + len(f_data) > self.bodyMaxX -2:
                """ this is too long, try to shorten it
                    by removing file size """
                f_data = ' [{0}]'.format(station[1])
            if len(line) + len(f_data) > self.bodyMaxX - 2:
                """ still too long. start removing chars """
                while len(line) + len(f_data) > self.bodyMaxX - 3:
                    f_data = f_data[:-1]
                f_data += ']'
            """ if too short, pad f_data to the right """
            if len(line) + len(f_data) < self.maxX - 2:
                while len(line) + len(f_data) < self.maxX - 2:
                    line += ' '
        line += f_data
        return line

    def _print_playlist_load_error(self):
        txt ="""Playlist loading failed!

            This means that either the file is corrupt,
            or you are not permitted to access it.
            """
        self._show_help(txt, PLAYLIST_LOAD_ERROR_MODE,
                caption = ' Error ',
                prompt = ' Press any key ')

    def _print_playlist_reload_error(self):
        txt ='''Playlist reloading failed!

            You have probably edited the playlist with an
            external program. Please re-edit it and make
            sure that only one "," exists in each line.
            '''
        self._show_help(txt, PLAYLIST_RELOAD_ERROR_MODE,
                caption = ' Error ',
                prompt = ' Press any key ')

    def _print_playlist_reload_confirmation(self):
        txt ='''This playlist has not been modified within
            PyRadio. Do you still want to reload it?

            Press "y" to confirm, "Y" to confirm and not
            be asked again, or any other key to cancel'''
        self._show_help(txt, PLAYLIST_RELOAD_CONFIRM_MODE,
                caption = ' Playlist Reload ',
                prompt = ' ')

    def _print_playlist_dirty_reload_confirmation(self):
        txt ='''This playlist has been modified within PyRadio.
            If you reload it now, all modifications will be
            lost. Do you still want to reload it?

            Press "y" to confirm, "Y" to confirm and not be
            asked again, or "n" to cancel'''
        self._show_help(txt, PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE,
                caption = ' Playlist Reload ',
                prompt = ' ')

    def _print_save_modified_playlist(self):
        txt ='''This playlist has been modified within
            PyRadio. Do you want to save it?

            If you choose not to save it now, all modifi-
            cations will be lost.

            Press "y" to confirm, "Y" to confirm and not
            be asked again, or any other key to cancel'''
        self._show_help(txt, ASK_TO_SAVE_PLAYLIST_MODE,
                caption = ' Playlist Modified ',
                prompt = ' ')
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MODE = ASK_TO_SAVE_PLAYLIST_MODE')

    def _print_save_playlist_error_1(self):
        txt = '''Saving current playlist failed!

            Could not open file for writing
            "{}"
            '''
        self._show_help(txt.format(self.cnf.stations_file.replace('.csv', '.txt')),
                mode_to_set = SAVE_PLAYLIST_ERROR_1_MODE,
                caption = ' Error ',
                prompt = ' Press any key ')

    def _print_save_playlist_error_2(self):
        txt = '''Saving current playlist failed!

            You will find a copy of the saved playlist in
            "{}"
            '''
        self._show_help(txt.format(self.cnf.stations_file.replace('.csv', '.txt')),
                mode_to_set = SAVE_PLAYLIST_ERROR_2_MODE,
                caption = ' Error ',
                prompt = ' Press any key ')

    def _align_stations_and_refresh(self, cur_mode):
        """ refresh reference """
        self.stations = self.cnf.stations

        if not self.stations:
            """ The playlist is empty """
            if self.player.isPlaying():
                self.stopPlayer()
            self.playing,self.selection, self.stations, \
                self.number_of_items = (-1, 0, 0, 0)
            self.operation_mode = NORMAL_MODE
            return
        else:
            self.number_of_items = len(self.stations)

            if cur_mode == REMOVE_STATION_MODE:
                """ Remove selected station """
                if self.player.isPlaying():
                    if self.selection == self.playing:
                        self.stopPlayer()
                        self.playing = -1
                    elif self.selection < self.playing:
                        self.playing -= 1
                else:
                    self.playing = -1

                if self.selection > self.number_of_items - self.bodyMaxY:
                    self.startPos -= 1
                    if self.selection >= self.number_of_items:
                        self.selection -= 1
                if self.startPos < 0:
                    self.startPos = 0
            else:
                if self.player.isPlaying():
                    """ The playlist is not empty """
                    if self.stations[self.playing][0] == self.active_stations[1][0]:
                        """ ok, self.playing found, just find selection """
                        self.selection = self._get_station_id(self.active_stations[0][0])
                    else:
                        """ station playing id changed, try previous station """
                        self.playing -= 1
                        if self.stations[self.playing][0] == self.active_stations[1][0]:
                            """ ok, self.playing found, just find selection """
                            self.selection = self._get_station_id(self.active_stations[0][0])
                        else:
                            """ self.playing still not found, have to scan playlist """
                            self.selection, self.playing = self._get_stations_ids((
                                self.active_stations[0][0],
                                self.active_stations[1][0]))
                            if self.playing == -1:
                                self.stopPlayer()

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('self.playing = {}'.format(self.playing))

                if cur_mode == NORMAL_MODE:
                    """ Reloading playlist """
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('playlist reloaded')
                    # TODO
                    if self.player.isPlaying():
                        pass
                    else:
                        self.playing = -1
                elif cur_mode == PLAYLIST_MODE:
                    """ Opening another playlist """
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('new playlist')
                    if self.player.isPlaying():
                        self.selection = self.playing
                        self.startPos = 0
                        max_lines = self.maxY - 4
                        #logger.debug('self.playing = {}'.format(self.playing))
                        if self.selection >= max_lines:
                            if self.selection > len(self.stations) - max_lines:
                                self.startPos = len(self.stations) - max_lines
                                logger.debug('1')
                            else:
                                self.startPos = int(self.selection+1/max_lines) - int(max_lines/2)
                                logger.debug('2')
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('new selection = {}'.format(self.selection))
                        pass
                    else:
                        self.selection = 0
                        self.startPos = 0

        self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.stations)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('self.selection = {}'.format(self.selection))
            logger.debug('len = {}'.format(len(self.stations)))

        self.refreshBody()

    def _open_playlist(self):
        """ open playlist """
        self._get_active_stations()
        txt = '''Reading playlists. Please wait...'''
        self._show_help(txt, NORMAL_MODE, caption=' ', prompt=' ')
        self.jumpnr = ''
        self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.stations)
        self.operation_mode = PLAYLIST_MODE
        self.selection, self.startPos, self.playing, self.stations = self.selections[self.operation_mode]
        self.number_of_items, self.playing = self.readPlaylists()
        self.stations = self.cnf.playlists
        if self.number_of_items == 0:
            return
        else:
            self.refreshBody()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE: NORMAL_MODE -> PLAYLIST_MODE')
            return

    def _get_station_id(self, find):
        for i, a_station in enumerate(self.stations):
            if a_station[0] == find:
                return i
        return -1

    def _get_stations_ids(self, find):
        ch = -2
        i_find = [ -1, -1 ]
        for j, a_find in enumerate(find):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('looking for {}'.format(a_find))

            for i, a_station in enumerate(self.stations):
                if i_find[j] == -1:
                    if a_station[0] == a_find:
                        i_find[j] = i
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('found at {}'.format(i))
                        ch += 1
                        if ch == 0:
                            break
        return i_find

    def _get_active_stations(self):
        if self.player.isPlaying():
            self.active_stations = [
                    [ self.stations[self.selection][0], self.selection ],
                    [ self.stations[self.playing][0], self.playing ]
                    ]
        else:
            if self.number_of_items > 0:
                self.active_stations = [
                        [ self.stations[self.selection][0], self.selection ],
                        [ '', -1 ] ]
            else:
                self.active_stations = [
                        [ '', self.selection ],
                        [ '', -1 ] ]

    def keypress(self, char):
        if char in (ord('#'), curses.KEY_RESIZE):
            cur_mode = self.operation_mode
            self.headWin = False
            self.setupAndDrawScreen()
            if cur_mode == MAIN_HELP_MODE or \
                cur_mode == PLAYLIST_HELP_MODE:
                    curses.ungetch('?')
            elif cur_mode == PLAYLIST_LOAD_ERROR_MODE:
                self._print_playlist_load_error()
            elif cur_mode == ASK_TO_SAVE_PLAYLIST_MODE:
                self._print_save_modified_playlist()
            elif cur_mode == PLAYLIST_RELOAD_CONFIRM_MODE:
                self._print_playlist_reload_confirmation()
            elif cur_mode == PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE:
                self._print_playlist_dirty_reload_confirmation()
            elif cur_mode == PLAYLIST_RELOAD_ERROR_MODE:
                self._print_playlist_reload_error()
            elif cur_mode == SAVE_PLAYLIST_ERROR_1_MODE:
                self._print_save_playlist_error_1()
            elif cur_mode == SAVE_PLAYLIST_ERROR_2_MODE:
                self._print_save_playlist_error_2()
            elif cur_mode == REMOVE_STATION_MODE:
                self.removeStation()
            return

        elif char in (ord('+'), ord('='), ord('.')):
            if self.player.isPlaying():
                self.player.volumeUp()
            return

        elif char in (ord('-'), ord(',')):
            if self.player.isPlaying():
                self.player.volumeDown()
            return

        elif char in (ord('m'), ):
            if self.player.isPlaying():
                self.player.toggleMute()
            return

        elif char in (ord('v'), ):
            if self.player.isPlaying():
                ret_string = self.player.save_volume()
                if ret_string:
                    self.log.write(ret_string)
                    self.player.threadUpdateTitle(self.player.status_update_lock)
            return

        elif self.operation_mode == NO_PLAYER_ERROR_MODE:
            """ if no player, don't serve keyboard """
            return

        elif self.operation_mode == PLAYLIST_SCAN_ERROR_MODE:
            """ exit """
            self.stopPlayer()
            return -1

        elif self.operation_mode == MAIN_HELP_MODE:
            """ Main help in on, just update """
            self.helpWin = None
            self.operation_mode = NORMAL_MODE
            self.setupAndDrawScreen()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE: MAIN_HELP_MODE -> NORMAL_MODE')
            return

        elif self.operation_mode == ASK_TO_SAVE_PLAYLIST_MODE:
            if char in (ord('y'), ord('Y')):
                if char == 'Y':
                    self.cnf.auto_save_playlist = True
                ret = self.saveCurrentPlaylist()
                if ret == 0:
                    self._open_playlist()
                else:
                    self.operation_mode = NORMAL_MODE
                    self.refreshBody()
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('MODE: Canceled ASK_TO_SAVE_PLAYLIST_MODE -> NORMAL_MODE')
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Cancel ASK_TO_SAVE_PLAYLIST_MODE -> NORMAL_MODE')
                self.operation_mode = NORMAL_MODE
                self.refreshBody()
            return

        elif self.operation_mode == PLAYLIST_RELOAD_CONFIRM_MODE:
            if char in (ord('y'), ord('Y')):
                self.reloadCurrentPlaylist(PLAYLIST_RELOAD_CONFIRM_MODE)
                if char == 'Y':
                    self.cnf.confirm_playlist_reload = False
            else:
                """ close confirmation message """
                self.stations = self.cnf.stations
                self.operation_mode = NORMAL_MODE
                self.refreshBody()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Cancel PLAYLIST_RELOAD_CONFIRM_MODE -> NORMAL_MODE')
            return

        elif self.operation_mode == PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE:
            if char in (ord('y'), ord('Y')):
                self.reloadCurrentPlaylist(PLAYLIST_DIRTY__RELOAD_CONFIRM_MODE)
                if char == 'Y':
                    self.cnf.confirm_playlist_reload = False
            elif char in (ord('n'), ):
                """ close confirmation message """
                self.stations = self.cnf.stations
                self.operation_mode = NORMAL_MODE
                self.refreshBody()
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Cancel PLAYLIST_DIRTY_RELOAD_CONFIRM_MODE -> NORMAL_MODE')
            else:
                pass
            return

        elif self.operation_mode == PLAYLIST_RELOAD_ERROR_MODE:
            """ close error message """
            self.stations = self.cnf.stations
            self.operation_mode = NORMAL_MODE
            self.refreshBody()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MODE: PLAYLIST_RELOAD_ERROR_MODE -> NORMAL_MODE')
            return

        elif self.operation_mode == PLAYLIST_HELP_MODE or \
                self.operation_mode == PLAYLIST_LOAD_ERROR_MODE:
            """ close playlist help """
            self.operation_mode = PLAYLIST_MODE
            self.refreshBody()
            if logger.isEnabledFor(logging.DEBUG):
                if self.operation_mode == PLAYLIST_HELP_MODE:
                    logger.debug('MODE: PLAYLIST_HELP_MODE -> PLAYLIST_MODE')
                else:
                    logger.debug('MODE: PLAYLIST_LOAD_ERROR_MODE -> PLAYLIST_MODE')
            return

        elif self.operation_mode == SAVE_PLAYLIST_ERROR_1_MODE or \
                self.operation_mode == SAVE_PLAYLIST_ERROR_2_MODE:
            """ close playlist help """
            if logger.isEnabledFor(logging.DEBUG):
                if self.operation_mode == SAVE_PLAYLIST_ERROR_1_MODE:
                    logger.debug('MODE: SAVE_PLAYLIST_ERROR_1_MODE -> NORMAL_MODE')
                else:
                    logger.debug('MODE: SAVE_PLAYLIST_ERROR_2_MODE -> NORMAL_MODE')
            self.operation_mode = NORMAL_MODE
            self.refreshBody()
            return

        elif self.operation_mode == REMOVE_STATION_MODE:
            if char in (ord('y'), ord('Y')):
                self._get_active_stations()
                deleted_station, self.number_of_items = self.cnf.remove_station(self.selection)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Deleted station: "{}"'.format(deleted_station[0]))
                self.operation_mode = NORMAL_MODE
                self._align_stations_and_refresh(REMOVE_STATION_MODE)
                if char == ord('Y'):
                    self.cnf.confirm_station_deletion = False
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: REMOVE_STATION_MODE -> NORMAL_MODE')
            else:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('MODE: Cancel REMOVE_STATION_MODE -> NORMAL_MODE')
            self.operation_mode = NORMAL_MODE
            self.setupAndDrawScreen()
            return

        else:

            if char in (ord('?'), ):
                if self.operation_mode == PLAYLIST_MODE:
                    txt = """Up/j/PgUp
                             Down/k/PgDown    Change playlist selection.
                             g                Jump to first playlist.
                             <n>G             Jump to n-th / last playlist.
                             Enter            Open selected playlist.
                             r                Re-read playlists from disk.
                             #                Redraw window.
                             Esc/q            Cancel. """
                    self._show_help(txt, mode_to_set=PLAYLIST_HELP_MODE)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('MODE = PLAYLIST_HELP_MODE')
                else:
                    txt = """Up/j/PgUp
                             Down/k/PgDown    Change station selection.
                             g                Jump to first station.
                             <n>G             Jump to n-th / last station.
                             Enter/Right/l    Play selected station.
                             r                Select and play a random station.
                             Space/Left/h     Stop/start playing selected station.
                             -/+ or ,/.       Change volume.
                             m                Mute / unmute player.
                             v                Save volume (not applicable with vlc).
                             o s R            Open / Save / Reload playlist.
                             DEL,x            Delete selected station.
                             #                Redraw window.
                             Esc/q            Quit. """
                    self._show_help(txt)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('MODE = MAIN_HELP_MODE')
                return

            if char in (ord('G'), ):
                if self.number_of_items > 0:
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
                if self.number_of_items > 0:
                    self.jumpnr += chr(char)
                    return
            else:
                self.jumpnr = ""

            if char in (ord('g'), ):
                self.setStation(0)
                self.refreshBody()
                return

            if char in (curses.KEY_EXIT, ord('q'), 27):
                if self.operation_mode == PLAYLIST_MODE:
                    """ return to stations view """
                    self.jumpnr = ''
                    self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.playlists)
                    self.operation_mode = NORMAL_MODE
                    self.selection, self.startPos, self.playing, self.stations = self.selections[self.operation_mode]
                    self.stations = self.cnf.stations
                    self.refreshBody()
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('MODE: Cancel PLAYLIST_MODE -> NORMAL_MODE')
                    return
                else:
                    """ exit """
                    if self.player:
                        self.stopPlayer()
                        self.ctrl_c_handler(0,0)
                    return -1

            if char in (curses.KEY_DOWN, ord('j')):
                if self.number_of_items > 0:
                    self.setStation(self.selection + 1)
                    self.refreshBody()
                return

            if char in (curses.KEY_UP, ord('k')):
                if self.number_of_items > 0:
                    self.setStation(self.selection - 1)
                    self.refreshBody()
                return

            if char in (curses.KEY_PPAGE, ):
                if self.number_of_items > 0:
                    self.setStation(self.selection - self.pageChange)
                    self.refreshBody()
                return

            if char in (curses.KEY_NPAGE, ):
                if self.number_of_items > 0:
                    self.setStation(self.selection + self.pageChange)
                    self.refreshBody()
                return

            if self.operation_mode == NORMAL_MODE:
                if char in (ord('o'), ):
                    if self.cnf.dirty_playlist:
                        if self.cnf.auto_save_playlist:
                            # TODO save playlist
                            #      open playlist
                            pass
                        else:
                            # TODO ask to save playlist
                            self._print_save_modified_playlist()
                    else:
                        self._open_playlist()
                    return

                elif char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
                        curses.KEY_RIGHT, ord('l')):
                    if self.number_of_items > 0:
                        self.playSelection()
                        self.refreshBody()
                        self.setupAndDrawScreen()
                    return

                elif char in (ord(' '), curses.KEY_LEFT, ord('h')):
                    if self.number_of_items > 0:
                        if self.player.isPlaying():
                            self.stopPlayer()
                        else:
                            self.playSelection()
                        self.refreshBody()
                    return

                elif char in(ord('x'), curses.KEY_DC):
                    if self.number_of_items > 0:
                        self.removeStation()
                    return

                elif char in(ord('s'), curses.KEY_DC):
                    if self.number_of_items > 0 and \
                            self.cnf.dirty_playlist:
                        self.saveCurrentPlaylist()
                    return

                elif char in (ord('r'), ):
                    # Pick a random radio station
                    if self.number_of_items > 0:
                        self.setStation(random.randint(0, len(self.stations)))
                        self.playSelection()
                        self.refreshBody()
                    return

                elif char in (ord('R'), ):
                    # Reload current playlist
                    if self.cnf.dirty_playlist:
                        if self.cnf.confirm_playlist_reload:
                            self._print_playlist_dirty_reload_confirmation()
                        else:
                            self.operation_mode = PLAYLIST_RELOAD_CONFIRM_MODE
                            curses.ungetch('y')
                    else:
                        if self.cnf.confirm_playlist_reload:
                            self._print_playlist_reload_confirmation()
                        else:
                            self.operation_mode = PLAYLIST_RELOAD_CONFIRM_MODE
                            curses.ungetch('y')
                    return

            elif self.operation_mode == PLAYLIST_MODE:

                if char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
                    """ return to stations view """
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Loading playlist: "{}"'.format(self.stations[self.selection][-1]))
                    ret = self.cnf.read_playlist_file(self.stations[self.selection][-1])
                    if ret == -1:
                        self.stations = self.cnf.playlists
                        self._print_playlist_load_error()
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Error loading playlist: "{}"'.format(self.stations[self.selection][-1]))
                        return
                    else:
                        self.number_of_items = ret
                        self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.playlists)
                        self.operation_mode = NORMAL_MODE
                        self.selection, self.startPos, self.playing, self.stations = self.selections[self.operation_mode]
                        self._align_stations_and_refresh(PLAYLIST_MODE)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('MODE: PLAYLIST_MODE -> NORMAL_MODE')
                    return

                elif char in (ord('r'), ):
                    """ read playlists from disk """
                    txt = '''Reading playlists. Please wait...'''
                    self._show_help(txt, PLAYLIST_MODE, caption=' ', prompt=' ')
                    old_playlist = self.cnf.playlists[self.selection][0]
                    self.number_of_items, self.playing = self.readPlaylists()
                    if self.number_of_items == 0:
                        return
                    else:
                        """ refresh reference """
                        self.stations = self.cnf.playlists
                        if self.playing == -1:
                            self.selections[self.operation_mode] = (0, 0, -1, self.cnf.playlists)
                        else:
                            self.selections[self.operation_mode] = (self.selection, self.startPos, self.playing, self.cnf.playlists)
                        self.refreshBody()

# pymode:lint_ignore=W901
