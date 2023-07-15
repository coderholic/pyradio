# -*- coding: utf-8 -*-
import subprocess
import threading
import os
import random
import logging
from os.path import expanduser
from platform import uname as platform_uname
from sys import platform, version_info, platform
from sys import exit
from time import sleep
from datetime import datetime
import collections
import json
import socket
from shutil import copyfile as shutil_copy_file
import locale
locale.setlocale(locale.LC_ALL, "")

try:
    import psutil
except:
    pass
if platform.startswith('win'):
    import win32pipe, win32file, pywintypes
try:
    from urllib import unquote
except:
    from urllib.parse import unquote

''' In case of import from win.py '''
try:
    from .cjkwrap import wrap
except:
    pass
''' In case of import from win.py '''
try:
    from .encodings import get_encodings
except:
    pass

logger = logging.getLogger(__name__)

available_players = []

try:  # Forced testing
    from shutil import which
    def pywhich (cmd):
        pr = which(cmd)
        if pr:
            return pr
        else:
            return None
except:
    # Versions prior to Python 3.3 don't have shutil.which

    def pywhich (cmd, mode=os.F_OK | os.X_OK, path=None):
        ''' Given a command, mode, and a PATH string, return the path which
            conforms to the given mode on the PATH, or None if there is no such
            file.
            `mode` defaults to os.F_OK | os.X_OK. `path` defaults to the result
            of os.environ.get("PATH"), or can be overridden with a custom search
            path.
            Note: This function was backported from the Python 3 source code.
        '''
        # Check that a given file can be accessed with the correct mode.
        # Additionally check that `file` is not a directory, as on Windows
        # directories pass the os.access check.

        def _access_check(fn, mode):
            return os.path.exists(fn) and os.access(fn, mode) and not os.path.isdir(fn)

        # If we're given a path with a directory part, look it up directly
        # rather than referring to PATH directories. This includes checking
        # relative to the current directory, e.g. ./script
        if os.path.dirname(cmd):
            if _access_check(cmd, mode):
                return cmd

            return None

        if path is None:
            path = os.environ.get('PATH', os.defpath)
        if not path:
            return None

        path = path.split(os.pathsep)

        if platform.startswith('win'):
            # The current directory takes precedence on Windows.
            if os.curdir not in path:
                path.insert(0, os.curdir)

            # PATHEXT is necessary to check on Windows.
            pathext = os.environ.get('PATHEXT', '').split(os.pathsep)
            # See if the given file matches any of the expected path
            # extensions. This will allow us to short circuit when given
            # "python.exe". If it does match, only test that one, otherwise we
            # have to try others.
            if any(cmd.lower().endswith(ext.lower()) for ext in pathext):
                files = [cmd]
            else:
                files = [cmd + ext for ext in pathext]
        else:
            # On other platforms you don't have things like PATHEXT to tell you
            # what file suffixes are executable, so just pass on cmd as-is.
            files = [cmd]

        seen = set()
        for dir in path:
            normdir = os.path.normcase(dir)
            if normdir not in seen:
                seen.add(normdir)
                for thefile in files:
                    name = os.path.join(dir, thefile)
                    if _access_check(name, mode):
                        return name

        return None


def find_vlc_on_windows(config_dir=None):
    PLAYER_CMD = ''
    for path in (
        os.path.join(os.getenv('PROGRAMFILES'), 'VideoLAN', 'VLC', 'vlc.exe'),
        os.path.join(os.getenv('PROGRAMFILES') + ' (x86)', 'VideoLAN', 'VLC', 'vlc.exe'),
    ):
        if os.path.exists(path):
            PLAYER_CMD = path
            break
    return PLAYER_CMD

    #result = []
    #for root, dirs, files in os.walk(path):
    #    for name in files:
    #        if fnmatch.fnmatch(name, pattern):
    #            result.append(os.path.join(root, name))
    #return result

def find_mpv_on_windows():
    for a_path in (
        os.path.join(os.getenv('APPDATA'), 'pyradio', 'mpv', 'mpv.exe'),
        os.path.join(os.getenv('APPDATA'), 'mpv', 'mpv.exe'),
        os.path.join(expanduser("~"), 'mpv', 'mpv.exe')
    ):
        if os.path.exists(a_path):
            return a_path
    return 'mpv'

def find_mplayer_on_windows():
    for a_path in (
        os.path.join(os.getenv('APPDATA'), 'pyradio', 'mplayer', 'mplayer.exe'),
        os.path.join(os.getenv('APPDATA'), 'mplayer', 'mplayer.exe'),
        os.path.join(expanduser("~"), 'mplayer', 'mplayer.exe')
    ):
        if os.path.exists(a_path):
            return a_path
    return 'mplayer'

def info_dict_to_list(info, fix_highlight, max_width):
    max_len = 0
    for a_title in info.keys():
        if len(a_title) > max_len:
            max_len = len(a_title)
        if version_info < (3, 0) and type(info[a_title]).__name__ != 'str':
            try:
                info[a_title] = info[a_title].encode('utf-8', 'replace')
            except:
                info[a_title] = ''
        info[a_title] = info[a_title].replace('_','¸')
    # logger.error('DE info\n{}\n\n'.format(info))

    a_list = []
    for n in info.keys():
        a_list.extend(wrap(n.rjust(max_len, ' ') + ': |' + info[n],
                             width=max_width,
                             subsequent_indent=(2+max_len)*'_'))

    # logger.error('DE a_list\n\n{}\n\n'.format(a_list))

    ''' make sure title is not alone in line '''
    for a_title in ('URL:', 'site:'):
        for n, an_item in enumerate(a_list):
            if an_item.endswith(a_title):
                url = a_list[n+1].split('_|')[1]
                # merge items
                bar = '' if a_title.endswith('L:') else '|'
                a_list[n] = a_list[n] + ' ' + bar + url
                a_list.pop(n+1)
                break

    # logger.error('DE a_list\n\n{}\n\n'.format(a_list))

    a_list[0] = a_list[0].replace('|', '')

    if fix_highlight:
        for x in fix_highlight:
            for n, an_item in enumerate(a_list):
                if x[0] in an_item:
                    rep_name = n
                if x[1] in an_item:
                    web_name = n
                    break
            for n in range(rep_name + 1, web_name):
                a_list[n] = '|' + a_list[n]
    return a_list

class Player(object):
    ''' Media player class. Playing is handled by player sub classes '''
    process = None
    update_thread = None

    icy_title_prefix = 'Title: '
    title_prefix = ''

    # Input:   old user input     - used to early suppress output
    #                               in case of consecutive equal messages
    # Volume:  old volume input   - used to suppress output (and firing of delay thread)
    #                               in case of consecutive equal volume messages
    # Title:   old title input    - printed by delay thread
    oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}

    delay_thread = None
    connection_timeout_thread = None

    ''' make it possible to change volume but not show it '''
    show_volume = True

    muted = paused = False

    ctrl_c_pressed = False

    ''' When found in station transmission, playback is on
        These strings are used by MPlayer
     '''
    _playback_token_tuple = ( 'AO: [', )
    # _playback_token_tuple = ( 'AO: [', 'Cache size')

    icy_tokens = ()
    icy_audio_tokens = {}

    playback_is_on = connecting = False

    _station_encoding = 'utf-8'

    # used to stop mpv update thread on python3
    stop_mpv_status_update_thread = False

    # used to stop vlc update thread on windows
    stop_win_vlc_status_update_thread = False

    # bitrate, url, audio_format etc.
    _icy_data = {}

    GET_TITLE = b'{ "command": ["get_property", "metadata"], "request_id": 100 }\n'
    GET_AUDIO_FORMAT = b'{ "command": ["get_property", "audio-out-params"], "request_id": 200 }\n'
    GET_AUDIO_CODEC = b'{ "command": ["get_property", "audio-codec"], "request_id": 300 }\n'
    GET_AUDIO_CODEC_NAME = b'{ "command": ["get_property", "audio-codec-name"], "request_id": 400 }\n'

    all_config_files = {}

    NO_RECORDING = 0
    RECORD_AND_LISTEN = 1
    RECORD_WITH_SILENCE = 2
    _recording = 0
    _recording_from_schedule = 0
    recording_filename = ''

    name = ''

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler,
                 history_add_function,
                 recording_lock):
        self.outputStream = outputStream
        self._cnf = config
        self.stations_history_add_function = history_add_function
        self.config_encoding = self._cnf.default_encoding
        self.config_dir = self._cnf.stations_dir
        try:
            self.playback_timeout = int(self._cnf.connection_timeout_int)
        except ValueError:
            self.playback_timeout = 10
        self.force_http = self._cnf.force_http
        self.playback_timeout_counter = playback_timeout_counter
        self.playback_timeout_handler = playback_timeout_handler
        self.info_display_handler = info_display_handler
        self.status_update_lock = outputStream.lock

        self.config_files = []
        self._get_all_config_files()
        #if self.WIN and self.PLAYER_NAME == 'vlc':
        if platform.startswith('win'):
            ''' delete old vlc files (vlc_log.*) '''
            from .del_vlc_log import RemoveWinVlcLogFiles
            threading.Thread(target=RemoveWinVlcLogFiles(self.config_dir)).start()

        ''' Recording monitor player for MPlayer and VLC '''
        self.monitor = self.monitor_process = None
        self.monitor_opts = self.monitor_update_thread = None
        self._recording_lock = recording_lock
        self.already_playing = False

        ''' I True, we have mplayer on Windows
            ehich will not support profiles
        '''
        self._mplayer_on_windows7 = False

    @property
    def recording(self):
        if self._recording_from_schedule > 0:
            return self._recording_from_schedule
        else:
            return self._recording

    @recording.setter
    def recording(self, val):
        if val in range(0, 3):
            self._recording = val
        else:
            self._recording = 0
        logger.error('\n\nsetting recording to {}'.format(self._recording))

    def get_recording_filename(self, name, extension):
        f = datetime.now().strftime('%Y-%m-%d %H-%M-%S') + " " + name + extension
        return os.path.join(self._cnf.recording_dir, f)

    def _get_all_config_files(self):
        ''' MPV config files '''
        config_files = []
        config_files = [expanduser("~") + "/.config/mpv/mpv.conf"]

        if platform.startswith('darwin'):
            config_files.append("/usr/local/etc/mpv/mpv.conf")
        elif platform.startswith('win'):
            config_files[0] = os.path.join(os.getenv('APPDATA'), "mpv", "mpv.conf")
        else:
            # linux, freebsd, etc.
            config_files.append("/etc/mpv/mpv.conf")
        self.all_config_files['mpv'] = config_files[:]

        ''' MPlayer config files '''
        config_files = []
        config_files = [expanduser("~") + "/.mplayer/config"]
        if platform.startswith('darwin'):
            config_files.append("/usr/local/etc/mplayer/mplayer.conf")
        elif platform.startswith('win'):
            if os.path.exists('C:\\mplayer\\mplayer.exe'):
                config_files[0] = 'C:\\mplayer\mplayer\\config'
            elif os.path.exists(os.path.join(os.getenv('USERPROFILE'), "mplayer", "mplayer.exe")):
                config_files[0] = os.path.join(os.getenv('USERPROFILE'), "mplayer", "mplayer", "config")
            elif os.path.exists(os.path.join(os.getenv('APPDATA'), "pyradio", "mplayer", "mplayer.exe")):
                config_files[0] = os.path.join(os.getenv('APPDATA'), "pyradio", "mplayer", "mplayer", "config")
            else:
                config_files = []
        self.all_config_files['mplayer'] = config_files[:]
        config_files = [os.path.join(self._cnf.data_dir, 'vlc.conf')]
        self.all_config_files['vlc'] = config_files[:]
        self._restore_win_player_config_file()
        if not os.path.exists(self.all_config_files['vlc'][0]):
            ''' create a default vlc config file '''
            try:
                with open(self.all_config_files['vlc'][0], 'w') as f:
                    f.write('50')
            except:
                pass

    @property
    def profile_name(self):
        return self._cnf.profile_name

    @profile_name.setter
    def progile_name(self, value):
        raise ValueError('property is read only')

    @property
    def profile_token(self):
        return  '[' + self.profile_name + ']'

    @profile_token.setter
    def profile_token(self, value):
        raise ValueError('property is read only')

    def __del__(self):
        self.close()

    def _url_to_use(self, streamUrl):
        if self.force_http:
            return streamUrl.replace('https://', 'http://')
        else:
            return streamUrl

    def _on_connect(self):
        pass

    def set_volume(self, vol):
        if self.isPlaying() and \
                not self.muted:
            executed = []
            wanted = '010'
            self.get_volume()
            while vol != int(self.volume):
                old_vol = int(self.volume)
                if vol > int(self.volume):
                    self._volume_up()
                    executed.append(0)
                else:
                    self._volume_down()
                    executed.append(1)
                if wanted in ''.join(map(str, executed)):
                    break
                if self.PLAYER_NAME == 'mpv':
                    sleep(.01)
                while old_vol == int(self.volume):
                    sleep(.1)

    def create_monitor_player(self, stop, limit, notify_function):
        logger.info('\n\n======|||==========')
        # self.monitor_opts.append('--volume')
        # self.monitor_opts.append('300')
        logger.info(self.monitor_opts)
        logger.error('limit = {}'.format(limit))
        while not os.path.exists(self.recording_filename):
            sleep(.1)
            if stop():
                logger.error('Asked to stop. Exiting....')
                return
        # logger.error('while 2')
        while os.path.getsize(self.recording_filename) < limit:
            sleep(.1)
            if stop():
                logger.error('\n\nAsked to stop. Exiting....\n\n')
                return
        logger.error('if stop')
        if stop():
            logger.error('\n\nAsked to stop. Exiting....\n\n')
            return
        # logger.error('----------------------starting!')
        self.monitor_process = subprocess.Popen(
            self.monitor_opts, shell=False,
            stdout=subprocess.PIPE,
            stdin=subprocess.PIPE,
            stderr=subprocess.STDOUT
        )
        # logger.error('self.monitor_process.pid = {}'.format(self.monitor_process))
        # logger.error('------------------ to notify function')
        notify_function()
        # logger.error('------------------ after notify function')
        if logger.isEnabledFor(logging.INFO):
            logger.info('Executing command: {}'.format(' '.join(self.monitor_opts)))
            logger.info('----==== {} monitor started ====----'.format(self.PLAYER_NAME))

    def save_volume(self):
        pass

    def icy_data(self, a_member):
        ret = ''
        with self.status_update_lock:
            if self._icy_data:
                if a_member in self._icy_data:
                    ret = self._icy_data[a_member]
        return ret

    def icy_data_available(self):
        with self.status_update_lock:
            l = len(self._icy_data)
        if l == 0:
            return False
        return True

    def get_info_string(self, a_station, max_width=60):
        guide = (
            ('Reported Name',  'icy-name'),
            ('Website', 'icy-url'),
            ('Genre', 'icy-genre'),
            ('Bitrate', 'icy-br'),
            ('Audio', 'audio_format'),
            ('Codec Name', 'codec-name'),
            ('Codec', 'codec')
        )

        enc = get_encodings()
        if self._station_encoding == '':
            this_enc = self._config_encoding
        else:
            this_enc = self._station_encoding
        try:
            this_enc_string = [x for x in enc if x[0] == this_enc][0][2]
        except:
            this_enc_string = 'Unknown'
        enc_to_show = '{0} ({1})'.format(this_enc, this_enc_string)


        info = collections.OrderedDict()
        info['Playlist Name'] = a_station[0]
        for x in guide:
            if x[1] in self._icy_data.keys():
                info[x[0]] = self._icy_data[x[1]].strip()
            else:
                info[x[0]] = ''
            if x[0] == 'Bitrate':
                if info[x[0]]:
                    info[x[0]] += ' kb/s'
            if x[0] == 'Genre':
                info['Encoding'] = enc_to_show
            if x[0].startswith('Reported'):
                info['Station URL'] = a_station[1].strip()
        info['Website'] = unquote(info['Website']).strip()

        a_list = []
        fix_highlight = (
                ('Reported ', 'Station URL:'),
                ('Website:', 'Genre:'),
                ('Genre:', 'Encoding:')
                )
        a_list = info_dict_to_list(info, fix_highlight, max_width)

        if 'Codec:' not in a_list[-1]:
            a_list[n] = '|' + a_list[n]

        ret = '|' + '\n'.join(a_list).replace('Encoding: |', 'Encoding: ').replace('URL: |', 'URL: ').replace('\n', '\n|')
        tail = ''
        if 'icy-name' in self._icy_data.keys():
            if a_station[0] != self._icy_data['icy-name'] and \
                    self._icy_data['icy-name'] and \
                    self._icy_data['icy-name'] != '(null)':
                tail = '\n\nPress |r| to rename station to |Reported Name|, or'
        # logger.error('DE ret\n{}\n'.format(ret))
        return ret + '\n\n|Highlighted values| are user specified.\nOther values are station provided (live) data.', tail

    def _do_save_volume(self, config_string):
        logger.error('\n\nself.volume = {}\n\n'.format(self.volume))
        if not self.config_files:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Volume not saved!!! (config file not found!!!)')
            return 'Volume not saved!!!'
        ret_strings = ('Volume: already saved...',
                       'Volume: {}% saved',
                       'Volume: {}% NOT saved (Error writing file)',
                       'Volume: NOT saved!')
        log_strings = ('Volume is -1. Aborting...',
                       'Volume is {}%. Saving...',
                       'Error saving profile "{}"',
                       'Error saving volume...')
        if self.volume == -1:
            ''' inform no change '''
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug(log_strings[0])
            return ret_strings[0]
        elif self.volume == -2:
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug(log_strings[3])
            return ret_strings[3]
        else:
            ''' change volume '''
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug(log_strings[1].format(self.volume))
            profile_found = False
            config_file = self.config_files[0]
            ret_string = ret_strings[1].format(str(self.volume))
            if self.PLAYER_NAME == 'vlc':
                ret = self._write_config()
                if not ret:
                    ret_string = ret_strings[2]
            else:
                if os.path.exists(config_file):
                    if self._mplayer_on_windows7:
                        ''' we are on Windows7 with player
                            write global mplayer config section
                        '''
                        """ This is actually only for mplayer
                            which does not support profiles on Windows
                        """
                        lines_no_profile, lines_with_profile = \
                                self._split_config_file(config_file)
                        ind = [(i,x) for i,x in enumerate(lines_no_profile) if 'volume=' in x]
                        if ind:
                            lines_no_profile[ind[0][0]] = 'volume={}'.format(self.volume)
                        else:
                            lines_no_profile.append('volume={}\n'.format(self.volume))
                        try:
                            with open(config_file, "w") as c_file:
                                c_file.write(
                                    '\n'.join(lines_no_profile) + \
                                    '\n'.join(lines_with_profile)
                                )
                            volume = self.volume
                            # self.volume = -1
                            self.PROFILE_FROM_USER = False
                            return ret_strings[1].format(str(self.volume))
                        except:
                            if (logger.isEnabledFor(logging.DEBUG)):
                                logger.debug(log_strings[2].format(config_file))
                            return ret_strings[2].format(str(self.volume))
                    else:
                        if self.PROFILE_FROM_USER:
                            with open(config_file, 'r', encoding='utf-8') as c_file:
                                config_string = c_file.read()

                            if self.profile_token in config_string:
                                profile_found = True

                                ''' split on self.profile_token
                                last item has our options '''
                                sections = config_string.split(self.profile_token)

                                ''' split at [ - i.e. isolate consecutive profiles
                                first item has pyradio options '''
                                py_section = sections[-1].split('[')

                                ''' split to lines in order to get '^volume=' '''
                                py_options = py_section[0].split('\n')

                                ''' replace volume line '''
                                vol_set = False
                                for i, opt in enumerate(py_options):
                                    if opt.startswith('volume='):
                                        py_options[i]='volume=' + str(self.volume)
                                        vol_set = True
                                        break
                                ''' or add it if it does not exist '''
                                if not vol_set:
                                    py_options.append('volume=' + str(self.volume))

                                ''' join lines together in py_section's first item '''
                                py_section[0] = '\n'.join(py_options)

                                ''' join consecutive profiles (if exist)
                                in last item of sections '''
                                if len(py_section) > 1:
                                    sections[-1] = '['.join(py_section)
                                else:
                                    sections[-1] = py_section[0]

                                ''' finally get the string back together '''
                                config_string = self.profile_token.join(sections)

                            try:
                                with open(config_file, 'w', encoding='utf-8') as c_file:
                                    c_file.write(config_string)
                                self.volume = -1
                            except EnvironmentError:
                                if (logger.isEnabledFor(logging.DEBUG)):
                                    logger.debug(log_strings[2].format(config_file))
                                return ret_strings[2].format(str(self.volume))

                ''' no user profile or user config file does not exist '''
                if not profile_found:
                    if os.path.isdir(os.path.dirname(config_file)):
                        if os.path.exists(config_file):
                            new_profile_string = '\n' + config_string
                        else:
                            new_profile_string = self.NEW_PROFILE_STRING + config_string
                    else:
                        try:
                            os.mkdir(os.path.dirname(config_file))
                        except OSError:
                            if (logger.isEnabledFor(logging.DEBUG)):
                                logger.debug(log_strings[2].format(config_file))
                            return ret_strings[2].format(str(self.volume))
                        new_profile_string = self.NEW_PROFILE_STRING + config_string
                    try:
                        with open(config_file, 'a', encoding='utf-8') as c_file:
                            c_file.write(new_profile_string.format(str(self.volume)))
                    except EnvironmentError:
                        if (logger.isEnabledFor(logging.DEBUG)):
                            logger.debug(log_strings[2].format(config_file))
                        return ret_strings[2].format(str(self.volume))
                    self.volume = -1
                    self.PROFILE_FROM_USER = True
            self.bck_win_player_config_file(config_file)
            return ret_string

    def _split_config_file(self, config_file):
        with open(config_file, 'r') as c_file:
            config_string = c_file.read()
            config_string = config_string.replace('#Volume set from pyradio\n', '')
            lines = config_string.split('\n')
        no_comment_or_empty=[d for d in lines if d and not d.startswith('#')]
        l_ind=[(i,d) for i,d in enumerate(no_comment_or_empty) if d.startswith('[')]
        '''
            no global, with profiles:
                [(0, '[silent]'), (2, '[pyradio]')]
        '''

        if l_ind:
            lines_no_profile = lines[:l_ind[0][0]]
            lines_with_profile = lines[l_ind[0][0]:]
        else:
            lines_no_profile = []
            lines_with_profile = lines
        return lines_no_profile, lines_with_profile
        return lines_no_profile, lines_with_profile

    def bck_win_player_config_file(self, config_file=None):
        if platform.startswith('win'):
            ''' backup player config '''
            if config_file is None:
                cnf_file = self.config_files[0]
            else:
                cnf_file = config_file
            if os.path.exists(cnf_file):
                bck_file = os.path.join(os.getenv('APPDATA'), "pyradio", self.PLAYER_NAME + "-active.conf")
                try:
                    shutil_copy_file(cnf_file, bck_file)
                except:
                    pass

    def _restore_win_player_config_file(self):
        if platform.startswith('win'):
            ''' restore player config '''
            for k in ('mplayer', 'mpv'):
                bck_file = os.path.join(os.getenv('APPDATA'), "pyradio", k + "-active.conf")
                if os.path.exists(bck_file):
                    cnf_file = self.all_config_files[k][0]
                    try:
                        shutil_copy_file(bck_file, cnf_file)
                    except:
                        pass

    def _stop_delay_thread(self):
        if self.delay_thread is not None:
            try:
                self.delay_thread.cancel()
            except:
                pass
            self.delay_thread = None

    def _is_in_playback_token(self, a_string):
        for a_token in self._playback_token_tuple:
            if a_token in a_string:
                return True
        return False

    def _clear_empty_mkv(self):
        if self.recording > 0 and self.recording_filename:
            if os.path.exists(self.recording_filename):
                if os.path.getsize(self.recording_filename) == 0:
                    os.remove(self.recording_filename)

    def updateStatus(self, *args):
        stop = args[0]
        process = args[1]
        stop_player = args[2]
        detect_if_player_exited = args[3]
        enable_crash_detection_function = args[4]
        recording_lock = args[5]
        on_connect = args[6]
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('updateStatus thread started.')
        #with lock:
        #    self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
        #    self.outputStream.write(msg=self.oldUserInput['Title'])
        ''' Force volume display even when icy title is not received '''
        with recording_lock:
            self.oldUserInput['Title'] = 'Playing: ' + self.name
        try:
            out = self.process.stdout
            while(True):
                subsystemOutRaw = out.readline()
                with recording_lock:
                    try:
                        subsystemOut = subsystemOutRaw.decode(self._station_encoding, 'replace')
                    except:
                        subsystemOut = subsystemOutRaw.decode('utf-8', 'replace')
                if subsystemOut == '':
                    break
                # logger.error('DE subsystemOut = "{0}"'.format(subsystemOut))
                with recording_lock:
                    tmp = self._is_accepted_input(subsystemOut)
                if not tmp:
                    continue
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace('\r', '').replace('\n', '')
                # logger.error('DE subsystemOut = "{0}"'.format(subsystemOut))

                with recording_lock:
                    tmp = self.oldUserInput['Input']
                if tmp != subsystemOut:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            logger.debug('User input: {}'.format(disp))
                        else:
                            logger.debug('User input: {}'.format(subsystemOut))

                    with recording_lock:
                        self.oldUserInput['Input'] = subsystemOut
                        self_volume_string = self.volume_string
                    if self_volume_string in subsystemOut:
                        # disable volume for mpv
                        if self.PLAYER_NAME != 'mpv':
                            # logger.error('***** volume')
                            with recording_lock:

                                self_oldUserInput_Volume = self.oldUserInput['Volume']
                            if self_oldUserInput_Volume != subsystemOut:
                                with recording_lock:
                                    self.oldUserInput['Volume'] = subsystemOut
                                if self.PLAYER_NAME == 'vlc':
                                    if '.' in subsystemOut:
                                        token = '.'
                                    elif ',' in subsystemOut:
                                        token = ','
                                    else:
                                        token = ''
                                    if token:
                                        sp = subsystemOut.split(token)
                                        subsystemOut = sp[0]
                                with recording_lock:
                                    self.volume = ''.join(c for c in subsystemOut if c.isdigit())

                                    self_show_volume = self.show_volume
                                    self_oldUserInput_Title = self.oldUserInput['Title']
                                    # IMPORTANT: do this here, so that vlc actual_volume
                                    # gets updated in _format_volume_string
                                    string_to_show = self._format_volume_string(subsystemOut) + self._format_title_string(self.oldUserInput['Title'])

                                if self_show_volume and self_oldUserInput_Title:
                                    self.outputStream.write(msg=string_to_show, counter='')
                                    self.threadUpdateTitle()
                    elif self._is_in_playback_token(subsystemOut):
                        self.stop_timeout_counter_thread = True
                        try:
                            self.connection_timeout_thread.join()
                        except:
                            pass
                        with recording_lock:
                            self.connecting = False
                        if enable_crash_detection_function:
                            enable_crash_detection_function()
                        with recording_lock:
                            if (not self.playback_is_on) and (logger.isEnabledFor(logging.INFO)):
                                    logger.info('*** updateStatus(): Start of playback detected ***')
                            #if self.outputStream.last_written_string.startswith('Connecting to'):
                            if self.oldUserInput['Title'] == '':
                                new_input = 'Playing: ' + self.name
                            else:
                                new_input = self.oldUserInput['Title']
                        if not self.playback_is_on:
                            on_connect()
                        self.outputStream.write(msg=new_input, counter='')
                        with recording_lock:
                            self.playback_is_on = True
                            self.connecting = False
                        self._stop_delay_thread()
                        self.stations_history_add_function()
                        if 'AO: [' in subsystemOut:
                            with self.status_update_lock:
                                if version_info > (3, 0):
                                    self._icy_data['audio_format'] = subsystemOut.split('] ')[1].split(' (')[0]
                                else:
                                    self._icy_data['audio_format'] = subsystemOut.split('] ')[1].split(' (')[0].encode('utf-8')
                                self.info_display_handler()
                        if self.PLAYER_NAME == 'mpv' and version_info < (3, 0):
                            for a_cmd in (
                                    b'{ "command": ["get_property", "metadata"], "request_id": 100 }\n',
                                    self.GET_AUDIO_CODEC,
                                    self.GET_AUDIO_CODEC_NAME):
                                response = self._send_mpv_command( a_cmd, return_response=True)
                                if response:
                                    self._get_mpv_metadata(response, lambda: False, enable_crash_detection_function)
                                    self.info_display_handler()
                                else:
                                    if logger.isEnabledFor(logging.INFO):
                                        logger.info('no response!!!')
                        # logger.error('DE 3 {}'.format(self._icy_data))
                    elif self._is_icy_entry(subsystemOut):
                        if not subsystemOut.endswith('Icy-Title=(null)'):
                            if enable_crash_detection_function:
                                enable_crash_detection_function()
                            # logger.error('***** icy_entry: "{}"'.format(subsystemOut))
                            title = self._format_title_string(subsystemOut)
                            # logger.error('DE title = "{}"'.format(title))
                            ok_to_display = False
                            self.stop_timeout_counter_thread = True
                            try:
                                self.connection_timeout_thread.join()
                            except:
                                pass
                            if not self.playback_is_on:
                                if logger.isEnabledFor(logging.INFO):
                                    logger.info('*** updateStatus(): Start of playback detected (Icy-Title received) ***')
                                    on_connect()
                            with self.status_update_lock:
                                self.playback_is_on = True
                                self.connecting = False
                            self._stop_delay_thread()
                            self.stations_history_add_function()
                            ''' detect empty Icy-Title '''
                            title_without_prefix = title[len(self.icy_title_prefix):].strip()
                            # logger.error('DE title_without_prefix = "{}"'.format(title_without_prefix))
                            if title_without_prefix:
                                #self._stop_delay_thread()
                                # logger.error("***** updating title")
                                if title_without_prefix.strip() == '-':
                                    ''' Icy-Title is empty '''
                                    if logger.isEnabledFor(logging.DEBUG):
                                        logger.debug('Icy-Title = " - ", not displaying...')
                                else:
                                    self.oldUserInput['Title'] = title
                                    # make sure title will not pop-up while Volume value is on
                                    if self.delay_thread is None:
                                        ok_to_display = True
                                    if ok_to_display and self.playback_is_on:
                                        string_to_show = self.title_prefix + title
                                        self.outputStream.write(msg=string_to_show, counter='')
                                    else:
                                        if logger.isEnabledFor(logging.DEBUG):
                                            logger.debug('***** Title change inhibited: ok_to_display = {0}, playbabk_is_on = {1}'.format(ok_to_display, self.playback_is_on))
                            else:
                                ok_to_display = True
                                if (logger.isEnabledFor(logging.INFO)):
                                    logger.info('Icy-Title is NOT valid')
                                if ok_to_display and self.playback_is_on:
                                    title = 'Playing: ' + self.name
                                    self.oldUserInput['Title'] = title
                                    string_to_show = self.title_prefix + title
                                    self.outputStream.write(msg=string_to_show, counter='')
                    #else:
                    #    if self.oldUserInput['Title'] == '':
                    #        self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
                    #        self.outputStream.write(msg=self.oldUserInput['Title'], counter='')

                    else:
                        for a_token in self.icy_audio_tokens.keys():
                            if a_token in subsystemOut:
                                if not self.playback_is_on:
                                    if logger.isEnabledFor(logging.INFO):
                                        logger.info('*** updateStatus(): Start of playback detected (Icy audio token received) ***')
                                        on_connect()
                                self.stop_timeout_counter_thread = True
                                try:
                                    self.connection_timeout_thread.join()
                                except:
                                    pass
                                self.playback_is_on = True
                                self.connecting = False
                                self.stations_history_add_function()
                                if enable_crash_detection_function:
                                    enable_crash_detection_function()
                                # logger.error('DE token = "{}"'.format(a_token))
                                # logger.error('DE icy_audio_tokens[a_token] = "{}"'.format(self.icy_audio_tokens[a_token]))
                                a_str = subsystemOut.split(a_token)
                                # logger.error('DE str = "{}"'.format(a_str))
                                with self.status_update_lock:
                                    if self.icy_audio_tokens[a_token] == 'icy-br':
                                        self._icy_data[self.icy_audio_tokens[a_token]] = a_str[1].replace('kbit/s', '')
                                    else:
                                        self._icy_data[self.icy_audio_tokens[a_token]] = a_str[1]
                                    if self.icy_audio_tokens[a_token] == 'codec':
                                        if '[' in self._icy_data['codec']:
                                            self._icy_data['codec-name'] = self._icy_data['codec'].split('] ')[0].replace('[', '')
                                            self._icy_data['codec'] = self._icy_data['codec'].split('] ')[1]
                                    if version_info < (3, 0):
                                        for an_item in self._icy_data.keys():
                                            try:
                                                self._icy_data[an_item] = self._icy_data[an_item].encode(self._station_encoding, 'replace')
                                            except UnicodeDecodeError as e:
                                                self._icy_data[an_item] = ''
                                    if 'codec-name' in self._icy_data.keys():
                                        self._icy_data['codec-name'] = self._icy_data['codec-name'].replace('"', '')
                                # logger.error('DE audio data\n\n{}\n\n'.format(self._icy_data))
                        self.info_display_handler()
        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Error in updateStatus thread.', exc_info=True)
            # return

        ''' crash detection '''
        # logger.error('detect_if_player_exited = {0}, stop = {1}'.format(detect_if_player_exited(), stop()))

        if not stop():
            if not platform.startswith('win'):
                poll = process.poll()
                if poll is not None:
                    if not stop():
                        if detect_if_player_exited():
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('----==== player disappeared! ====----')
                            stop_player(
                                from_update_thread=True,
                                player_disappeared=True
                            )
                        else:
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('Crash detection is off; waiting to timeout')
            else:
                if not stop():
                    if detect_if_player_exited():
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('----==== player disappeared! ====----')
                        stop_player(
                            from_update_thread=True,
                            player_disappeared = True
                        )
                    else:
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('Crash detection is off; waiting to timeout')
        if (logger.isEnabledFor(logging.INFO)):
            logger.info('updateStatus thread stopped.')
        self._clear_empty_mkv()


    def updateRecordingStatus(self, *args):
        stop = args[0]
        process = args[1]
        recording_lock = args[2]
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('updateRecordingStatus thread started.')
        #with lock:
        #    self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
        #    self.outputStream.write(msg=self.oldUserInput['Title'])
        ''' Force volume display even when icy title is not received '''
        # self.oldUserInput['Title'] = 'Playing: ' + self.name
        try:
            out = self.monitor_process.stdout
            while(True):
                subsystemOutRaw = out.readline()
                with recording_lock:
                    try:
                        subsystemOut = subsystemOutRaw.decode(self._station_encoding, 'replace')
                    except:
                        subsystemOut = subsystemOutRaw.decode('utf-8', 'replace')
                if subsystemOut == '':
                    break
                # logger.error('DE subsystemOut = "{0}"'.format(subsystemOut))
                with recording_lock:
                    tmp = self._is_accepted_input(subsystemOut)
                if not tmp:
                    continue
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace('\r', '').replace('\n', '')
                # logger.error('DE subsystemOut = "{0}"'.format(subsystemOut))

                with recording_lock:
                    tmp = self.oldUserInput['Input']
                if tmp != subsystemOut:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            logger.debug('Monitor User input: {}'.format(disp))
                        else:
                            logger.debug('Monitor User input: {}'.format(subsystemOut))

                    with recording_lock:
                        self.oldUserInput['Input'] = subsystemOut
                        self_volume_string = self.volume_string
                        self_player_name = self.PLAYER_NAME
                    if self_volume_string in subsystemOut:
                        # disable volume for mpv
                        if self_player_name != 'mpv':
                            # logger.error('***** volume')
                            with recording_lock:
                                if self.oldUserInput['Volume'] != subsystemOut:
                                    self.oldUserInput['Volume'] = subsystemOut
                                    if self_player_name == 'vlc':
                                        if '.' in subsystemOut:
                                            token = '.'
                                        elif ',' in subsystemOut:
                                            token = ','
                                        else:
                                            token = ''
                                        if token:
                                            sp = subsystemOut.split(token)
                                            subsystemOut = sp[0]
                                self.volume = ''.join(c for c in subsystemOut if c.isdigit())

                                # IMPORTANT: do this here, so that vlc actual_volume
                                # gets updated in _format_volume_string
                                string_to_show = self._format_volume_string(subsystemOut) + self._format_title_string(self.oldUserInput['Title'])

                                if self.show_volume and self.oldUserInput['Title']:
                                    self.outputStream.write(msg=string_to_show, counter='')
                                    self.threadUpdateTitle()
        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Error in updateRecordingStatus thread.', exc_info=True)
            # return

        if (logger.isEnabledFor(logging.INFO)):
            logger.info('updateRecordingStatus thread stopped.')

    def updateMPVStatus(self, *args):
        stop = args[0]
        process = args[1]
        stop_player = args[2]
        detect_if_player_exited = args[3]
        enable_crash_detection_function = args[4]
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('MPV updateStatus thread started.')

        while True:
            try:
                sock = self._connect_to_socket(self.mpvsocket)
            finally:
                if sock:
                    break
                if stop():
                    if (logger.isEnabledFor(logging.INFO)):
                        logger.info('MPV updateStatus thread stopped (no connection to socket).')
                    return
        # Send data
        message = b'{ "command": ["observe_property", 1, "metadata"] }\n'
        try:
            if platform.startswith('win'):
                win32file.WriteFile(sock, message)
            else:
                sock.sendall(message)
            go_on = True
        except:
            # logger.error('DE \n\nBroken pipe\n\n')
            go_on = False
        if go_on:
            while True:
                if stop():
                    break
                try:
                    if platform.startswith('win'):
                        try:
                            data = win32file.ReadFile(sock, 64*1024)
                        except pywintypes.error as e:
                            data = b''
                    else:
                        try:
                            data = sock.recvmsg(4096)
                        except:
                            data = b''
                    a_data = self._fix_returned_data(data)
                    logger.error('DE Received: "{!r}"'.format(a_data))
                    if a_data == b'' or stop():
                        break

                    if a_data:
                        all_data = a_data.split(b'\n')
                        for n in all_data:
                            if self._get_mpv_metadata(n, stop, enable_crash_detection_function):
                                self._request_mpv_info_data(sock)
                            else:
                                try:
                                    if stop():
                                        break
                                    d = json.loads(n)
                                    if 'event' in d.keys():
                                        if d['event'] == 'metadata-update':
                                            try:
                                                if platform.startswith('win'):
                                                    win32file.WriteFile(sock, self.GET_TITLE)
                                                else:
                                                    sock.sendall(self.GET_TITLE)
                                            except:
                                                break
                                            ret = self._set_mpv_playback_is_on(stop, enable_crash_detection_function)
                                            if not ret:
                                                break
                                            self._request_mpv_info_data(sock)
                                            self.info_display_handler()
                                        elif d['event'] == 'playback-restart':
                                            if not self.playback_is_on:
                                                ret = self._set_mpv_playback_is_on(stop, enable_crash_detection_function)
                                            if not ret:
                                                break
                                            self._request_mpv_info_data(sock)
                                            self.info_display_handler()
                                except:
                                    pass
                finally:
                    pass
        self._close_pipe(sock)

        if not stop():
            ''' haven't been asked to stop '''
            if detect_if_player_exited():
                if logger.isEnabledFor(logging.INFO):
                    logger.info('----==== MPV disappeared! ====----')
                stop_player(
                    from_update_thread=True,
                    player_disappeared = True
                )
            else:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Crash detection is off; waiting to timeout')
        if (logger.isEnabledFor(logging.INFO)):
            logger.info('MPV updateStatus thread stopped.')
        self._clear_empty_mkv()

    def _close_pipe(self, sock):
        if platform.startswith('win'):
            win32file.CloseHandle(sock)
        else:
            sock.close()

    def updateWinVLCStatus(self, *args):
        def do_crash_detection(detect_if_player_exited, stop):
            if self.playback_is_on:
                poll = process.poll()
                if poll is not None:
                    if not stop():
                        if detect_if_player_exited():
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('----==== VLC disappeared! ====----')
                            stop_player(from_update_thread=True)
                            return True
                        else:
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('Crash detection is off; waiting to timeout')
            return False
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('Win VLC updateStatus thread started.')
        fn = args[0]
        enc = args[1]
        stop = args[2]
        process = args[3]
        stop_player = args[4]
        detect_if_player_exited = args[5]
        enable_crash_detection_function = args[6]
        on_connect = args[7]
        ''' Force volume display even when icy title is not received '''
        self.oldUserInput['Title'] = 'Playing: ' + self.name
        # logger.error('DE ==== {0}\n{1}\n{2}'.format(fn, enc, stop))
        #with lock:
        #    self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
        #    self.outputStream.write(msg=self.oldUserInput['Title'])

        go_on = False
        while not go_on:
            if stop():
                break
            try:
                fp = open(fn, mode='r', encoding=enc, errors='ignore')
                go_on = True
            except:
                pass

        try:
            while(True):
                if stop():
                    break
                subsystemOut = fp.readline()
                subsystemOut = subsystemOut.strip().replace(u'\ufeff', '')
                subsystemOut = subsystemOut.replace('\r', '').replace('\n', '')
                if subsystemOut == '':
                    continue
                # logger.error('DE subsystemOut = "{0}"'.format(subsystemOut))
                if not self._is_accepted_input(subsystemOut):
                    continue
                # logger.error('DE accepted inp = "{0}"'.format(subsystemOut))
                if self.oldUserInput['Input'] != subsystemOut:
                    if stop():
                        break
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            # logger.debug("User input: {}".format(disp))
                        else:
                            # logger.debug("User input: {}".format(subsystemOut))
                            pass
                    self.oldUserInput['Input'] = subsystemOut
                    # logger.error('DE subsystemOut = "' + subsystemOut + '"')
                    if self.volume_string in subsystemOut:
                        if stop():
                            break
                        # logger.error("***** volume")
                        if self.oldUserInput['Volume'] != subsystemOut:
                            self.oldUserInput['Volume'] = subsystemOut
                            self.volume = ''.join(c for c in subsystemOut if c.isdigit())

                            # IMPORTANT: do this here, so that vlc actual_volume
                            # gets updated in _format_volume_string
                            string_to_show = self._format_volume_string(subsystemOut) + self._format_title_string(self.oldUserInput['Title'])

                            if self.show_volume and self.oldUserInput['Title']:
                                self.outputStream.write(msg=string_to_show, counter='')
                                self.threadUpdateTitle()
                    elif self._is_in_playback_token(subsystemOut):
                        # logger.error('DE \n\ntoken = "' + subsystemOut + '"\n\n')
                        if stop():
                            break
                        self.stop_timeout_counter_thread = True
                        try:
                            self.connection_timeout_thread.join()
                        except:
                            pass
                        if enable_crash_detection_function:
                            enable_crash_detection_function()
                        if not self.playback_is_on:
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('*** updateWinVLCStatus(): Start of playback detected ***')
                            on_connect()
                        #if self.outputStream.last_written_string.startswith('Connecting to'):
                        if self.oldUserInput['Title'] == '':
                            new_input = 'Playing: ' + self.name
                        else:
                            new_input = self.oldUserInput['Title']
                        self.outputStream.write(msg=new_input, counter='')
                        self.playback_is_on = True
                        self.connecting = False
                        self._stop_delay_thread()
                        self.stations_history_add_function()
                        if 'AO: [' in subsystemOut:
                            with self.status_update_lock:
                                if version_info > (3, 0):
                                    self._icy_data['audio_format'] = subsystemOut.split('] ')[1].split(' (')[0]
                                else:
                                    self._icy_data['audio_format'] = subsystemOut.split('] ')[1].split(' (')[0].encode('utf-8')
                                self.info_display_handler()
                        # logger.error('DE 3 {}'.format(self._icy_data))
                    elif self._is_icy_entry(subsystemOut):
                        if stop():
                            break
                        if not self.playback_is_on:
                            self.stop_timeout_counter_thread = True
                            try:
                                self.connection_timeout_thread.join()
                            except:
                                pass
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('*** updateWinVLCStatus(): Start of playback detected (Icy-Title received) ***')
                            if not self.playback_is_on:
                                on_connect()
                        self.stop_timeout_counter_thread = True
                        try:
                            self.connection_timeout_thread.join()
                        except:
                            pass
                        self.playback_is_on = True
                        self.connecting = False
                        self._stop_delay_thread()
                        self.stations_history_add_function()
                        if enable_crash_detection_function:
                            enable_crash_detection_function()

                        if not subsystemOut.endswith('Icy-Title=(null)'):
                            # logger.error("***** icy_entry")
                            title = self._format_title_string(subsystemOut)
                            ok_to_display = False
                            if title[len(self.icy_title_prefix):].strip():
                                self.oldUserInput['Title'] = title
                                # make sure title will not pop-up while Volume value is on
                                if self.delay_thread is None:
                                    ok_to_display = True
                                if ok_to_display and self.playback_is_on:
                                    string_to_show = self.title_prefix + title
                                    self.outputStream.write(msg=string_to_show, counter='')
                            else:
                                ok_to_display = True
                                if (logger.isEnabledFor(logging.INFO)):
                                    logger.info('Icy-Title is NOT valid')
                                if ok_to_display and self.playback_is_on:
                                    title = 'Playing: ' + self.name
                                    self.oldUserInput['Title'] = title
                                    string_to_show = self.title_prefix + title
                                    self.outputStream.write(msg=string_to_show, counter='')
                    #else:
                    #    if self.oldUserInput['Title'] == '':
                    #        self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
                    #        self.outputStream.write(msg=self.oldUserInput['Title'], counter='')

                    else:
                        if stop():
                            break
                        for a_token in self.icy_audio_tokens.keys():
                            if a_token in subsystemOut:
                                self.stop_timeout_counter_thread = True
                                try:
                                    self.connection_timeout_thread.join()
                                except:
                                    pass
                                if not self.playback_is_on:
                                    if logger.isEnabledFor(logging.INFO):
                                        logger.info('*** updateWinVLCStatus(): Start of playback detected (Icy audio token received) ***')
                                    on_connect()
                                self.playback_is_on = True
                                self.connecting = False
                                self._stop_delay_thread()
                                self.stations_history_add_function()
                                if enable_crash_detection_function:
                                    enable_crash_detection_function()
                                # logger.error('DE token = "{}"'.format(a_token))
                                # logger.error('DE icy_audio_tokens[a_token] = "{}"'.format(self.icy_audio_tokens[a_token]))
                                a_str = subsystemOut.split(a_token)
                                # logger.error('DE str = "{}"'.format(a_str))
                                with self.status_update_lock:
                                    if self.icy_audio_tokens[a_token] == 'icy-br':
                                        self._icy_data[self.icy_audio_tokens[a_token]] = a_str[1].replace('kbit/s', '')
                                    else:
                                        self._icy_data[self.icy_audio_tokens[a_token]] = a_str[1]
                                    if self.icy_audio_tokens[a_token] == 'codec':
                                        if '[' in self._icy_data['codec']:
                                            self._icy_data['codec-name'] = self._icy_data['codec'].split('] ')[0].replace('[', '')
                                            self._icy_data['codec'] = self._icy_data['codec'].split('] ')[1]
                                    if version_info < (3, 0):
                                        for an_item in self._icy_data.keys():
                                            try:
                                                self._icy_data[an_item] = self._icy_data[an_item].encode(self._station_encoding, 'replace')
                                            except UnicodeDecodeError as e:
                                                self._icy_data[an_item] = ''
                                    if 'codec-name' in self._icy_data.keys():
                                        self._icy_data['codec-name'] = self._icy_data['codec-name'].replace('"', '')
                                # logger.error('DE audio data\n\n{}\n\n'.format(self._icy_data))
                        self.info_display_handler()
        except:
            has_error = True
            if logger.isEnabledFor(logging.ERROR):
                logger.error('Error in Win VLC updateStatus thread.', exc_info=True)
        if has_error or not stop():
            do_crash_detection(detect_if_player_exited, stop)
        try:
            fp.close()
        except:
            pass
        self._clear_empty_mkv()

    def _request_mpv_info_data(self, sock):
        with self.status_update_lock:
            ret = len(self._icy_data)
        if ret == 0:
            if platform.startswith('win'):
                win32file.WriteFile(sock, self.GET_TITLE)
                win32file.WriteFile(sock, self.GET_AUDIO_FORMAT)
                win32file.WriteFile(sock, self.GET_AUDIO_CODEC)
                win32file.WriteFile(sock, self.GET_AUDIO_CODEC_NAME)
            else:
                sock.sendall(self.GET_TITLE)
                sock.sendall(self.GET_AUDIO_FORMAT)
                sock.sendall(self.GET_AUDIO_CODEC)
                sock.sendall(self.GET_AUDIO_CODEC_NAME)

    def _get_mpv_metadata(self, *args):
        ''' Get MPV metadata

            Parameters
            ==========
            a_data (args[0]
                Data read from socket
            lock (args[1])
                Thread lock
            stop (args[2])
                function to indicate thread stopping

            Returns
            =======
            True
                Manipulated no data (other functions must
                manipulate them)
            False
                Data read and manipulated, or stop condition
                triggered. Other functions do not have to deal
                with this data, of thread will terminate.

            Populates
            =========
            self._icy_data
                Fields:
                    icy-title    : Title of song (python 3 only)
                    icy-name     : Station name
                    icy-url      : Station URL
                    icy-genre    : Station genres
                    icy-br       : Station bitrate
                    audio_format : XXXXHx stereo/mono 1/2ch format
        '''

        a_data = args[0]
        stop = args[1]
        enable_crash_detection_function = args[2]
        if b'"icy-title":"' in a_data:
            if version_info > (3, 0):
                title = a_data.split(b'"icy-title":"')[1].split(b'"}')[0]
                if title:
                    if title == b'-' or title == b' - ':
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Icy-Title = " - ", not displaying...')
                    else:
                        try:
                            self.oldUserInput['Title'] = 'Title: ' + title.decode(self._station_encoding, 'replace')
                        except:
                            self.oldUserInput['Title'] = 'Title: ' + title.decode('utf-8', 'replace')
                        string_to_show = self.title_prefix + self.oldUserInput['Title']
                        #logger.critical(string_to_show)
                        if stop():
                            return False
                        self.outputStream.write(msg=string_to_show, counter='')
                    if not self.playback_is_on:
                        if stop():
                            return False
                        return self._set_mpv_playback_is_on(stop, enable_crash_detection_function)
                else:
                    if (logger.isEnabledFor(logging.INFO)):
                        logger.info('Icy-Title is NOT valid')
                    title = 'Playing: ' + self.name
                    string_to_show = self.title_prefix + title
                    if stop():
                        return False
                    self.outputStream.write(msg=string_to_show, counter='')
                    self.oldUserInput['Title'] = title

        # logger.info('DE a_data {}'.format(a_data))
        if b'icy-br' in a_data:
            # logger.info('DE check {}'.format(self._icy_data))
            if not 'icy-br' in self._icy_data.keys():
                for icy in ('icy-name', 'icy-url', 'icy-genre', 'icy-br'):
                    if stop():
                        return False
                    if version_info < (3, 0):
                        bytes_icy = icy
                    else:
                        bytes_icy = bytes(icy, encoding='utf-8')
                    if icy in ('icy-name', 'icy-genre'):
                        enc = self._station_encoding
                    else:
                        enc = 'utf-8'
                    if bytes_icy in a_data :
                        with self.status_update_lock:
                            if version_info < (3, 0):
                                try:
                                    self._icy_data[icy] = a_data.split(bytes_icy + b'":"')[1].split(b'",')[0].split(b'"}')[0].encode(enc, 'replace')
                                except UnicodeDecodeError as e:
                                    pass
                            else:
                                try:
                                    self._icy_data[icy] = a_data.split(bytes_icy + b'":"')[1].split(b'",')[0].split(b'"}')[0].decode(enc)
                                except UnicodeDecodeError as e:
                                    pass
                    # logger.error('DE 0 {}'.format(self._icy_data))
            return True

        elif b'request_id' in a_data and b'"error":"success"' in a_data:
            if b'"request_id":200' in a_data:
                try:
                    d = json.loads(a_data)
                except:
                    d = None
                if d:
                    self.status_update_lock.acquire()
                    try:
                        self._icy_data['audio_format'] = '{0}Hz {1} {2}ch {3}'.format(
                                d['data']['samplerate'],
                                d['data']['channels'],
                                d['data']['channel-count'],
                                d['data']['format'])
                    finally:
                        self.status_update_lock.release()
            elif b'"request_id":300' in a_data:
                self.status_update_lock.acquire()
                try:
                    if version_info < (3, 0):
                        self._icy_data['codec'] = a_data.split(b'"data":"')[1].split(b'",')[0].encode('utf-8')
                    else:
                        self._icy_data['codec'] = a_data.split(b'"data":"')[1].split(b'",')[0].decode('utf-8')
                finally:
                    self.status_update_lock.release()
                self.info_display_handler()
            elif b'"request_id":400' in a_data:
                self.status_update_lock.acquire()
                try:
                    if version_info < (3, 0):
                        self._icy_data['codec-name'] = a_data.split(b'"data":"')[1].split(b'",')[0].encode('utf-8')
                    else:
                        self._icy_data['codec-name'] = a_data.split(b'"data":"')[1].split(b'",')[0].decode('utf-8')
                finally:
                    self.status_update_lock.release()
            # logger.error('DE 1 {}'.format(self._icy_data))
            self.info_display_handler()
            return True
        else:
            return False

    def _set_mpv_playback_is_on(self, stop, enable_crash_detection_function):
        self.stop_timeout_counter_thread = True
        try:
            self.connection_timeout_thread.join()
        except:
            pass
        self.detect_if_player_exited = True
        if (not self.playback_is_on) and (logger.isEnabledFor(logging.INFO)):
                    logger.info('*** _set_mpv_playback_is_on(): Start of playback detected ***')
        self.stop_timeout_counter_thread = True
        try:
            self.connection_timeout_thread.join()
        except:
            pass
        self.stations_history_add_function()
        new_input = 'Playing: ' + self.name
        self.outputStream.write(msg=new_input, counter='')
        if self.oldUserInput['Title'] == '':
            self.oldUserInput['Input'] = new_input
        self.oldUserInput['Title'] = new_input
        self.playback_is_on = True
        self.connecting = False
        if stop():
            return False
        enable_crash_detection_function()
        return True

    def threadUpdateTitle(self, delay=1):
        if self.oldUserInput['Title'] != '':
            self._stop_delay_thread()
            try:
               self.delay_thread = threading.Timer(delay,
                                                   self.updateTitle,
                                                   [ self.outputStream,
                                                    None ]
                                                   )
               self.delay_thread.start()
            except:
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug('delay thread start failed')

    def updateTitle(self, *arg, **karg):
        self._stop_delay_thread()
        if arg[1]:
            arg[0].write(msg=arg[1])
        else:
            arg[0].write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Title']))

    def _is_icy_entry(self, a_string):
        for a_token in self.icy_tokens:
            if a_token in a_string:
                return True
        return False

    def _format_title_string(self, title_string):
        return self._title_string_format_text_tag(title_string)

    def _title_string_format_text_tag(self, a_string):
        i = a_string.find(' - text="')
        if i == -1:
            return a_string
        else:
            ret_string = a_string[:i]
            text_string = a_string[i+9:]
            final_text_string = text_string[:text_string.find('"')]
            if ret_string == self.icy_title_prefix + final_text_string:
                return ret_string
            else:
                return ret_string + ': ' + final_text_string

    def _format_volume_string(self, volume_string):
        return self._title_string_format_text_tag(volume_string)

    def isPlaying(self):
        return bool(self.process)

    def _start_monitor_update_thread(self):
        self.monitor_update_thread = threading.Thread(
            target=self.updateRecordingStatus,
            args=(
                lambda: self.stop_mpv_status_update_thread,
                self.monitor_process,
                self._recording_lock
            )
        )
        ''' make sure the counter is stopped
            and a message other than "Connecting..."
            is displayed
        '''
        with self._recording_lock:
            self.stop_timeout_counter_thread = True
            self.connecting = False
            self.playback_is_on = True
            the_title = self.oldUserInput['Title']
        self.outputStream.write(msg=the_title, counter='')
        # self.threadUpdateTitle()
        self.monitor_update_thread.start()

    def play(self,
             name,
             streamUrl,
             stop_player,
             detect_if_player_exited,
             enable_crash_detection_function=None,
             encoding=''
         ):
        ''' use a multimedia player to play a stream '''
        self.monitor = self.monitor_process = self.monitor_opts = None
        # logger.error('self.monitor_process.pid = {}'.format(self.monitor_process))
        self.recording_filename = ''
        self.volume = -1
        self.close()
        self.name = name
        self.oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}
        self.muted = self.paused = False
        self.show_volume = True
        self.title_prefix = ''
        self.playback_is_on = False
        self.delay_thread = None
        # self.outputStream.write(msg='Station: "{}" - Opening connection...'.format(name), counter='')
        self.outputStream.write(msg='Station: ' + name + ' - Opening connection...', counter='')
        if logger.isEnabledFor(logging.INFO):
            logger.info('Selected Station: ' + name)
        if encoding:
            self._station_encoding = encoding
        else:
            self._station_encoding = self.config_encoding
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts, self.monitor_opts = self._buildStartOpts(streamUrl, isPlayList)
        self.stop_mpv_status_update_thread = False
        if logger.isEnabledFor(logging.INFO):
            logger.info('Executing command: {}'.format(' '.join(opts)))
        if platform.startswith('win') and self.PLAYER_NAME == 'vlc':
            self.stop_win_vlc_status_update_thread = False
            ''' Launches vlc windowless '''
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            self.process = subprocess.Popen(opts, shell=False,
                                            startupinfo=startupinfo)
            self.update_thread = threading.Thread(
                target=self.updateWinVLCStatus,
                args=(
                    self._vlc_stdout_log_file,
                    self.config_encoding,
                    lambda: self.stop_win_vlc_status_update_thread,
                    self.process,
                    stop_player,
                    detect_if_player_exited,
                    enable_crash_detection_function,
                    self._on_connect
                )
            )
        else:
            if self.PLAYER_NAME == 'mpv' and version_info > (3, 0):
                self.process = subprocess.Popen(opts, shell=False,
                                                stdout=subprocess.DEVNULL,
                                                stdin=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL)
                self.update_thread = threading.Thread(
                    target=self.updateMPVStatus,
                    args=(lambda: self.stop_mpv_status_update_thread,
                          self.process,
                          stop_player,
                          detect_if_player_exited,
                          enable_crash_detection_function
                    )
                )
            else:
                self.process = subprocess.Popen(
                    opts, shell=False,
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
                self.update_thread = threading.Thread(
                    target=self.updateStatus,
                    args=(
                        lambda: self.stop_mpv_status_update_thread,
                        self.process,
                        stop_player,
                        detect_if_player_exited,
                        enable_crash_detection_function,
                        self._recording_lock,
                        self._on_connect
                    )
                )
        self.update_thread.start()
        if self.PLAYER_NAME == 'vlc':
            self.get_volume()
        # start playback check timer thread
        self.stop_timeout_counter_thread = False
        if self.playback_timeout > 0:
            ''' set connecting here insead of Player.play()
                so that we do not use it when timeout = 0
            '''
            self.connecting = True
            try:
                self.connection_timeout_thread = threading.Thread(
                    target=self.playback_timeout_counter,
                    args=(self.playback_timeout,
                          self.name,
                          lambda: self.stop_timeout_counter_thread)
                )
                self.connection_timeout_thread.start()
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug('playback detection thread started')
            except:
                self.connecting = False
                self.connection_timeout_thread = None
                if (logger.isEnabledFor(logging.ERROR)):
                    logger.error('playback detection thread failed to start')
        else:
            self.connecting = False
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('playback detection thread not starting (timeout is 0)')
        if logger.isEnabledFor(logging.INFO):
            logger.info('----==== {} player started ====----'.format(self.PLAYER_NAME))
        if self.recording == self.RECORD_AND_LISTEN \
                and self.PLAYER_NAME != 'mpv':
                    # logger.error('=======================\n\n')
                    limit = 120000
                    if self.PLAYER_NAME == 'mplayer':
                        if not platform.startswith('win'):
                            limit = 12000
                        threading.Thread(
                                target=self.create_monitor_player,
                                args=(lambda: self.stop_mpv_status_update_thread or \
                                        self.stop_win_vlc_status_update_thread,  limit, self._start_monitor_update_thread)
                                ).start()
                    else:
                        threading.Thread(
                                target=self.create_monitor_player,
                                args=(lambda: self.stop_mpv_status_update_thread,  limit, self._start_monitor_update_thread)
                                ).start()
                    # logger.error('=======================\n\n')

    def _sendCommand(self, command):
        ''' send keystroke command to player '''
        if [x for x in ('q', 'shutdown') if command.startswith(x)]:
            self._command_to_player(self.process, command)
            # logger.error('self.monitor_process.pid = {}'.format(self.monitor_process))
            if self.monitor_process is not None:
                self._command_to_player(self.monitor_process, command)
            return
        # logger.error('self.monitor_process.pid = {}'.format(self.monitor_process))
        if self.monitor_process is not None and \
                [x for x in
                 ('/', '*', 'p', 'm', 'vol', 'pause' ) if command.startswith(x)
                 ]:
                    # logger.error('\n\nsending command: "{}"\n\n'.format(command))
                    self._command_to_player(self.monitor_process, command)
        else:
            self._command_to_player(self.process, command)

    def _command_to_player(self, a_process, command):
        if a_process is not None:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Sending Command: {}'.format(command).strip())
            try:
                a_process.stdin.write(command.encode('utf-8', 'replace'))
                a_process.stdin.flush()
            except:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('Error while sending Command: {}'.format(command).strip(), exc_info=True)

    def close_from_windows(self):
        ''' kill player instance when window console is closed '''
        if self.process:
            self.close()
            self._stop()

    def close(self):
        ''' kill player instance '''
        self._no_mute_on_stop_playback()

        ''' First close the subprocess '''
        self._stop()
        ''' Here is fallback solution and cleanup '''
        self.stop_timeout_counter_thread = True
        try:
            self.connection_timeout_thread.join()
        except:
            pass
        self._stop_delay_thread()
        if self.process is not None:
            self._kill_process_tree(self.process.pid)
            try:
                self.process.wait()
            except:
                pass
            finally:
                self.process = None
            try:
                self.update_thread.join()
            except:
                pass
            finally:
                self.update_thread = None
        if self.monitor_process is not None:
            self._kill_process_tree(self.monitor_process.pid)
            try:
                self.monitor_process.wait()
            except:
                pass
            finally:
                self.monitor_process = None
            try:
                self.monitor_update_thread.join()
            except:
                pass
            finally:
                self.monitor_update_thread = None
        self.monitor = self.monitor_process = self.monitor_opts = None

    def _kill_process_tree(self, pid):
        if psutil.pid_exists(pid):
            parent = psutil.Process(pid)
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('PID {} does not exist...'.format(pid))
            return
        try:
            children = parent.children(recursive=True)
            try:
                os.kill(parent.pid, 9)
            except:
                pass
            for child in children:
                try:
                    os.kill(child.pid, 9)
                except:
                    pass
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('PID {} (and its children)  killed...'.format(pid))
        except psutil.NoSuchProcess:
            pass

    def _killall(self, name):
        if name:
            try:
                # iterating through each instance of the process
                for line in os.popen("ps ax | grep " + name + " | grep -v grep"):
                    fields = line.split()
                    if name in fields[4]:
                        # extracting Process ID from the output
                        pid = fields[0]

                        # terminating process
                        # os.kill(int(pid), signal.SIGKILL)
                        os.kill(int(pid), 9)
                        # os.kill(int(pid), 15)
            except:
                pass

    def _buildStartOpts(self, streamUrl, playList):
        pass

    def _write_silenced_profile(self):
        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_string = f.read()
                if '[silent]' in config_string:
                    if i == 0:
                        return

        ''' profile not found in config
            create a default profile
        '''
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('No [silent] profile found!')
        try:
            with open(self.config_files[0], 'a', encoding='utf-8') as f:
                f.write('\n[{}]\n'.format('silent'))
                f.write('volume=0\n\n')
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Written [silent] profile in: "{}"'.format(self.config_files[0]))
        except:
            pass

    def togglePause(self):
        if self.PLAYER_NAME == 'mpv':
            self.paused = self._pause()
        elif self.PLAYER_NAME == 'vlc':
            self.paused = not self.paused
            self._pause()
        else:
            self.paused = not self.paused
            self._pause()
        if self.paused:
            # self._stop_delay_thread()
            self.title_prefix = '[Paused] '
            self.show_volume = False
            self.muted = False
        else:
            self.title_prefix = ''
            self.show_volume = True
        # logger.info('\n\nself.paused = {}\n\n'.format(self.paused))
        if self.oldUserInput['Title'] == '':
            self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Input']), counter='')
        else:
            self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Title']), counter='')

    def toggleMute(self):
        ''' mute / unmute player '''

        if not self.paused:
            if self.PLAYER_NAME == 'mpv':
                self.muted = bool(self._mute())
            elif self.PLAYER_NAME == 'vlc':
                self._mute()
            else:
                self.muted = not self.muted
                self._mute()
            if self.muted:
                self._stop_delay_thread()
                self.title_prefix = '[Muted] '
                self.show_volume = False
            else:
                self.title_prefix = ''
                self.show_volume = True
            logger.info('\n\nself.muted = {}\n\n'.format(self.muted))
            if self.oldUserInput['Title'] == '':
                self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Input']), counter='')
            else:
                self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Title']), counter='')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Cannot toggle mute, player paused!')

    def _mute(self):
        ''' to be implemented on subclasses '''
        pass

    def _stop(self):
        pass

    def get_volume(self):
        ''' get volume, if player can report it '''
        pass

    def volumeUp(self):
        ''' increase volume '''
        if self.muted is not True:
            self._volume_up()

    def _volume_up(self):
        ''' to be implemented on subclasses '''
        pass

    def volumeDown(self):
        ''' decrease volume '''
        if self.muted is not True:
            self._volume_down()

    def _volume_down(self):
        ''' to be implemented on subclasses '''
        pass

    def _no_mute_on_stop_playback(self):
        ''' make sure player does not stop muted, i.e. volume=0

            Currently implemented for vlc only.'''
        pass

    def _is_accepted_input(self, input_string):
        ''' subclasses are able to reject input messages
            thus limiting message procesing.
            By default, all messages are accepted.

            Currently implemented for vlc only.'''
        return True

class MpvPlayer(Player):
    '''Implementation of Player object for MPV'''

    PLAYER_NAME = 'mpv'
    PLAYER_CMD = 'mpv'
    WIN = False
    if platform.startswith('win'):
        WIN = True
    if WIN:
        PLAYER_CMD = find_mpv_on_windows()
    NEW_PROFILE_STRING = 'volume=50\n\n'

    if pywhich(PLAYER_CMD):
        executable_found = True
    else:
        executable_found = False

    if executable_found:
        ''' items of this tuple are considered icy-title
            and get displayed after first icy-title is received '''
        icy_tokens = ('icy-title: ', )

        icy_audio_tokens = {}

        ''' USE_PROFILE
            -1 : not checked yet
             0 : do not use
             1 : use profile
         '''
        USE_PROFILE = -1

        ''' True if profile comes from ~/.config/mpv/mpv.conf '''
        PROFILE_FROM_USER = False

        ''' String to denote volume change '''
        volume_string = 'Volume: '
        if platform.startswith('win'):
            mpvsocket = r'\\.\pipe\mpvsocket.{}'.format(os.getpid())
        else:
            mpvsocket = '/tmp/mpvsocket.{}'.format(os.getpid())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('mpv socket is "{}"'.format(self.mpvsocket))
        if os.path.exists(mpvsocket):
            os.system('rm ' + mpvsocket + ' 2>/dev/null');

        commands = {
                'volume_up':   b'{ "command": ["cycle", "volume", "up"], "request_id": 1000 }\n',
                'volume_down': b'{ "command": ["cycle", "volume", "down"], "request_id": 1001 }\n',
                'mute':        b'{ "command": ["cycle", "mute"], "request_id": 1002 }\n',
                'pause':       b'{ "command": ["cycle", "pause"], "request_id": 1003 }\n',
                'quit':        b'{ "command": ["quit"], "request_id": 1004}\n',
                }

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler,
                 history_add_function,
                 recording_lock):
        config.PLAYER_NAME = 'mpv'
        super(MpvPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler,
            history_add_function,
            recording_lock
        )
        self.config_files = self.all_config_files['mpv']
        self.recording_filename = ''
        logger.error('\n\nMPV recording = {}\n\n'.format(self._recording))

    def save_volume(self):
        ''' Saving Volume in Windows does not work;
            Profiles not supported... '''
        if int(self.volume) > 999:
            self.volume = -2
        return self._do_save_volume(self.profile_token + '\nvolume={}\n')

    def _configHasProfile(self):
        ''' Checks if mpv config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        volume-max=300
        volume=50'''

        self.PROFILE_FROM_USER = False
        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_string = f.read()
                if self.profile_token in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                        return 1

        ''' profile not found in config
            create a default profile
        '''
        try:
            with open(self.config_files[0], 'a', encoding='utf-8') as f:
                f.write('\n[{}]\n'.format(self.profile_name))
                f.write(self.NEW_PROFILE_STRING)
            self.PROFILE_FROM_USER = True
            return 1
        except:
            return 0

    def _buildStartOpts(self, streamUrl, playList=False):
        logger.error('\n\nself._recording = {}'.format(self._recording))
        ''' Builds the options to pass to mpv subprocess.'''

        ''' Test for newer MPV versions as it supports different IPC flags. '''
        p = subprocess.Popen([self.PLAYER_CMD, '--no-video',  '--input-ipc-server'], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False)
        out = p.communicate()
        if 'not found' not in str(out[0]):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('--input-ipc-server is supported.')
            newerMpv = 1
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('--input-ipc-server is not supported.')
            newerMpv = 0
        if playList:
            if newerMpv:
                opts = [self.PLAYER_CMD, '--no-video', '--quiet', '--playlist=' + self._url_to_use(streamUrl), '--input-ipc-server=' + self.mpvsocket]
            else:
                opts = [self.PLAYER_CMD, '--no-video', '--quiet', '--playlist=' + self._url_to_use(streamUrl), '--input-unix-socket=' + self.mpvsocket]
        else:
            if newerMpv:
                opts = [self.PLAYER_CMD, '--no-video', '--quiet', self._url_to_use(streamUrl), '--input-ipc-server=' + self.mpvsocket]
            else:
                opts = [self.PLAYER_CMD, '--no-video', '--quiet', self._url_to_use(streamUrl), '--input-unix-socket=' + self.mpvsocket]


        ''' this will set the profile too '''
        params = []
        if self._cnf.command_line_params:
            params = self._cnf.command_line_params.split(' ')

        self._write_silenced_profile()
        ''' Do I have user profile in config?
            If so, can I use it?
        '''
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

        if self._recording == self.RECORD_WITH_SILENCE:
            opts.append('--profile=silent')
        else:
            if self.USE_PROFILE == 1:
                opts.append('--profile=' + self.profile_name)
                if (logger.isEnabledFor(logging.INFO)):
                    logger.info('Using profile: "[{}]"'.format(self.profile_name))
            else:
                if (logger.isEnabledFor(logging.INFO)):
                    if self.USE_PROFILE == 0:
                        logger.info('Profile "[{}]" not found in config file!!!'.format(self.profile_name))
                    else:
                        logger.info('No usable profile found')

        ''' add command line parameters '''
        if params:
            for a_param in params:
                opts.append(a_param)

        logger.error('\n\nself._recording = {}'.format(self._recording))
        if self._recording > 0:
            self.recording_filename = self.get_recording_filename(self.name, '.mkv')
            opts.append('--stream-record=' + self.recording_filename)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('---=== Starting Recording: "{}" ===---',format(self.recording_filename))
        return opts, None


    def _fix_returned_data(self, data):
        if isinstance(data, tuple):
            if 'int' in str(type(data[0])):
                a_data = data[1]
            else:
                a_data = data[0]
        else:
            a_data = data
        return a_data

    def _pause(self):
        ''' pause mpv '''
        ret = self._send_mpv_command('pause')
        while not ret:
            ret = self._send_mpv_command('pause')
        return self._get_pause_status()

    def _get_pause_status(self):
        while True:
            sock = self._connect_to_socket(self.mpvsocket)
            try:
                if platform.startswith('win'):
                    win32file.WriteFile(sock, b'{ "command": ["get_property", "pause"], "request_id": 600 }\n')
                else:
                    sock.sendall(b'{ "command": ["get_property", "pause"], "request_id": 600 }\n')
            except:
                self._close_pipe(sock)
                return
            # wait for response

            try:
                if platform.startswith('win'):
                    try:
                        data = win32file.ReadFile(sock, 64*1024)
                    except pywintypes.error as e:
                        data = b''
                else:
                    if version_info < (3, 0):
                        data = sock.recv(4096)
                    else:
                        data = sock.recvmsg(4096)
                a_data = self._fix_returned_data(data)
                # logger.error('DE Received: "{!r}"'.format(a_data))

                if a_data:
                    all_data = a_data.split(b'\n')
                    for n in all_data:
                        try:
                            d = json.loads(n)
                            if d['error'] == 'success':
                                if isinstance(d['data'], bool):
                                    self._close_pipe(sock)
                                    return d['data']
                        except:
                            pass
            finally:
                pass
            self._close_pipe(sock)

    def _mute(self):
        ''' mute mpv '''
        ret = self._send_mpv_command('mute')
        while not ret:
            ret = self._send_mpv_command('mute')
        return self._get_mute_status()

    def _get_mute_status(self):
        while True:
            sock = self._connect_to_socket(self.mpvsocket)
            try:
                if platform.startswith('win'):
                    win32file.WriteFile(sock, b'{ "command": ["get_property", "mute"], "request_id": 600 }\n')
                else:
                    sock.sendall(b'{ "command": ["get_property", "mute"], "request_id": 600 }\n')
            except:
                self._close_pipe(sock)
                return
            # wait for response

            try:
                if platform.startswith('win'):
                    try:
                        data = win32file.ReadFile(sock, 64*1024)
                    except pywintypes.error as e:
                        data = b''
                else:
                    if version_info < (3, 0):
                        data = sock.recv(4096)
                    else:
                        data = sock.recvmsg(4096)
                a_data = self._fix_returned_data(data)
                # logger.error('DE Received: "{!r}"'.format(a_data))

                if a_data:
                    all_data = a_data.split(b'\n')
                    for n in all_data:
                        try:
                            d = json.loads(n)
                            if d['error'] == 'success':
                                if isinstance(d['data'], bool):
                                    self._close_pipe(sock)
                                    return d['data']
                        except:
                            pass
            finally:
                pass
            self._close_pipe(sock)

    def _stop(self):
        ''' kill mpv instance '''
        self.stop_mpv_status_update_thread = True
        self._send_mpv_command('quit')
        if not platform.startswith('win'):
            os.system('rm ' + self.mpvsocket + ' 2>/dev/null');
        self._icy_data = {}
        self.monitor = self.monitor_process = self.monitor_opts = None

    def _volume_up(self):
        ''' increase mpv's volume '''
        self._send_mpv_command('volume_up')
        self._display_mpv_volume_value()

    def _volume_down(self):
        ''' decrease mpv's volume '''
        self.get_volume()
        if self.volume > 0:
            self._send_mpv_command('volume_down')
            self._display_mpv_volume_value()

    def _format_title_string(self, title_string):
        ''' format mpv's title '''
        return self._title_string_format_text_tag(title_string.replace(self.icy_tokens[0], self.icy_title_prefix))

    def _format_volume_string(self, volume_string):
        ''' format mpv's volume '''
        return '[' + volume_string[volume_string.find(self.volume_string):].replace('ume', '')+'] '

    def _connect_to_socket(self, server_address):
        if platform.startswith('win'):
            count = 0
            # logger.error('\n\n_connect_to_socket: {}\n\n'.format(server_address))
            try:
                handle = win32file.CreateFile(
                    server_address,
                    win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                    0,
                    None,
                    win32file.OPEN_EXISTING,
                    0,
                    None
                )
                res = win32pipe.SetNamedPipeHandleState(handle, win32pipe.PIPE_READMODE_MESSAGE, None, None)
                return handle
            except pywintypes.error as e:
                return None
        else:
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(server_address)
                return sock
            except:
                self._close_pipe(sock)
                return None

    def _send_mpv_command(self, a_command, return_response=False):
        ''' Send a command to MPV

            Parameters
            =========
            a_command
                The command to send.
            return_response
                if True, return a string, otherwise
                return a boolean

            Returns
            =======
            If return_response is False (default), returns
                True, if the operation was a success or False
                if it failed.
            If return_response if True, return the response
                we get after issuing the command ('' if failed).

        '''

        #while True:
        #    sock = self._connect_to_socket(self.mpvsocket)
        #    if sock:
        #        break
        #    sleep(.25)
        sock = self._connect_to_socket(self.mpvsocket)
        if sock is None:
            if return_response:
                return ''
            else:
                return False

        # Send data
        try:
            if platform.startswith('win'):
                if a_command in self.commands.keys():
                    win32file.WriteFile(sock, self.commands[a_command])
                else:
                    win32file.WriteFile(sock, a_command)
            else:
                if a_command in self.commands.keys():
                    sock.sendall(self.commands[a_command])
                else:
                    sock.sendall(a_command)
        except:
            self._close_pipe(sock)
            if return_response:
                return ''
            else:
                return False
        # read the response
        if platform.startswith('win'):
            try:
                data = win32file.ReadFile(sock, 64*1024)
            except pywintypes.error as e:
                data = b''
        else:
            try:
                if version_info < (3, 0):
                    data = sock.recv(4096)
                else:
                    data = sock.recvmsg(4096)
            except sock.error as e:
                data = ''
        # logger.error('DE data = {}'.format(data))
            #sock.colse()
            #return False
        # logger.error('DE data = "{}"'.format(data))
        self._close_pipe(sock)
        if return_response:
            return data
        else:
            return True

    def get_volume(self):
        ''' Display volume for MPV '''
        vol = 0
        while True:
            sock = self._connect_to_socket(self.mpvsocket)
            if sock:
                break
            sleep(.25)

        # Send data
        message = b'{ "command": ["get_property", "volume"] }\n'
        try:
            if platform.startswith('win'):
                win32file.WriteFile(sock, message)
            else:
                sock.sendall(message)
        except:
            self._close_pipe(sock)
            return

        # wait for response
        got_it = True
        while got_it:
            try:
                if platform.startswith('win'):
                    try:
                        data = win32file.ReadFile(sock, 64*1024)
                    except pywintypes.error as e:
                        data = b''
                else:
                    if version_info < (3, 0):
                        data = sock.recv(4096)
                    else:
                        data = sock.recvmsg(4096)

                # logger.error('DE Received: "{!r}"'.format(a_data))
                a_data = self._fix_returned_data(data)

                if a_data == b'':
                    break

                if data:

                    all_data = a_data.split(b'\n')
                    for n in all_data:
                        try:
                            d = json.loads(n)
                            if d['error'] == 'success':
                                try:
                                    vol = int(d['data'])
                                    got_it = False
                                    break
                                except:
                                    pass
                        except:
                            pass
            finally:
                pass
        self._close_pipe(sock)
        self.volume = vol

    def _display_mpv_volume_value(self):
        ''' Display volume for MPV

            Calling get_volume
        '''

        self.get_volume()
        if self.oldUserInput['Title']:
            info_string = self._format_title_string(self.oldUserInput['Title'])
        else:
            info_string = self._format_title_string(self.oldUserInput['Input'])
        string_to_show = self._format_volume_string('Volume: ' + str(self.volume) + '%') + info_string
        self.outputStream.write(msg=string_to_show, counter='')
        self.threadUpdateTitle()

class MpPlayer(Player):
    '''Implementation of Player object for MPlayer'''

    PLAYER_NAME = 'mplayer'
    PLAYER_CMD = 'mplayer'
    WIN = False
    if platform.startswith('win'):
        WIN = True
    if WIN:
        PLAYER_CMD = find_mplayer_on_windows()
    NEW_PROFILE_STRING = 'softvol=1\nsoftvol-max=300\nvolstep=1\nvolume=50\n\n'
    if pywhich(PLAYER_CMD):
        executable_found = True
    else:
        executable_found = False

    if executable_found:
        ''' items of this tuple are considered icy-title
            and get displayed after first icy-title is received
        '''
        icy_tokens = ('ICY Info:', )

        # 'audio-data' comes from playback start
        icy_audio_tokens = {
                'Name   : ': 'icy-name',
                'Genre  : ': 'icy-genre',
                'Website: ': 'icy-url',
                'Bitrate: ': 'icy-br',
                'Opening audio decoder: ': 'codec',
                }


        ''' USE_PROFILE
            -1 : not checked yet
             0 : do not use
             1 : use profile
        '''
        USE_PROFILE = -1

        ''' True if profile comes from ~/.mplayer/config '''
        PROFILE_FROM_USER = False

        ''' String to denote volume change '''
        volume_string = 'Volume: '

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler,
                 history_add_function,
                 recording_lock):
        config.PLAYER_NAME = 'mplayer'
        super(MpPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler,
            history_add_function,
            recording_lock
        )
        self.config_files = self.all_config_files['mplayer']
        if platform.startswith('win') and \
                int(platform_uname().release) < 10:
            ''' Existing mplayer Windows 7 and earlier
                implementations do not support profiles
            '''
            self._mplayer_on_windows7 = True

    def save_volume(self):
        if platform.startswith('win'):
            return self._do_save_volume('volume={}\r\n')
            return 0
        return self._do_save_volume(self.profile_token + '\nvolstep=1\nvolume={}\n')

    def _configHasProfile(self):
        ''' Checks if mplayer config has [pyradio] entry / profile.

            Profile example:

            [pyradio]
            volstep=2
            volume=28
        '''

        self.PROFILE_FROM_USER = False
        if self._mplayer_on_windows7:
            if logger.isEnabledFor(logging.INFO):
                logger.info('>>>>> Disabling profiles usage on Windows 7 <<<<<')
            return 0
        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_string = f.read()
                if self.profile_token in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                        return 1

        ''' profile not found in config
            create a default profile
        '''
        try:
            with open(self.config_files[0], 'a', encoding='utf-8') as f:
                f.write('\n[{}]\n'.format(self.profile_name))
                f.write(self.NEW_PROFILE_STRING)
            self.PROFILE_FROM_USER = True
            return 1
        except:
            return 0

    def _buildStartOpts(self, streamUrl, playList=False):
        ''' Builds the options to pass to mplayer subprocess.'''
        opts = [self.PLAYER_CMD, '-vo', 'null', '-quiet']
        monitor_opts = None

        ''' this will set the profile too '''
        params = []
        if self._cnf.command_line_params:
            params = self._cnf.command_line_params.split(' ')

        self._write_silenced_profile()
        ''' Do I have user profile in config?
            If so, can I use it?
        '''
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

        if self.USE_PROFILE == 1:
            opts.append('-profile')
            opts.append(self.profile_name)
            if (logger.isEnabledFor(logging.INFO)):
                logger.info('Using profile: "[{}]"'.format(self.profile_name))
        else:
            if (logger.isEnabledFor(logging.INFO)):
                if self.USE_PROFILE == 0:
                    logger.info('Profile "[{}]" not found in config file!!!'.format(self.profile_name))
                else:
                    logger.info('No usable profile found')

        if playList:
            opts.append('-playlist')

        opts.append(self._url_to_use(streamUrl))

        ''' add command line parameters '''
        if params:
            for a_param in params:
                opts.append(a_param)

        #opts.append('-dumpstream')
        #opts.append('-dumpfile')
        #opts.append('/home/spiros/.config/pyradio/recordings/rec.mkv')
        ## opts.append(r'C:\Users\Spiros\AppData\Roaming\pyradio\recordings\rec.mkv')
        logger.error('\n\nself._recording = {}'.format(self._recording))
        if self._recording > 0:
            monitor_opts = opts[:]
            if self._recording == self.RECORD_WITH_SILENCE:
                try:
                    i = [y for y, x in enumerate(opts) if x == '-profile'][0]
                    opts[i+1] = 'silent'
                except IndexError:
                    opts.append('-profile')
                    opts.append('silent')
            try:
                ''' find and remove -playlist url '''
                i = [y for y, x in enumerate(monitor_opts) if x == '-playlist'][0]
                del monitor_opts[i+1]
                del monitor_opts[i]
            except IndexError:
                ''' not -playlist, find and remove url '''
                i = [y for y, x in enumerate(monitor_opts) if x == streamUrl][0]
                del monitor_opts[i]
            self.recording_filename = self.get_recording_filename(self.name, '.mkv')
            monitor_opts.append(self.recording_filename)
            opts.append('-dumpstream')
            opts.append('-dumpfile')
            opts.append(self.recording_filename)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('---=== Starting Recording: "{}" ===---',format(self.recording_filename))
        logger.error('Opts:\n{0}\n{1}'.format(opts, monitor_opts))
        return opts, monitor_opts

    def _mute(self):
        ''' mute mplayer '''
        self._sendCommand('m')

    def _pause(self):
        ''' pause streaming (if possible) '''
        self._sendCommand('p')

    def pause(self):
        ''' pause streaming (if possible) '''
        self._sendCommand('p')

    def _stop(self):
        ''' kill mplayer instance '''
        self.stop_mpv_status_update_thread = True
        self._sendCommand('q')
        self._icy_data = {}

    def _volume_up(self):
        ''' increase mplayer's volume '''
        self._sendCommand('*')

    def _volume_down(self):
        ''' decrease mplayer's volume '''
        self._sendCommand('/')

    def get_volume(self):
        ''' get mplayer's actual_volume'''
        if int(self.volume) < 0:
            self.show_volume = False
            count = 0
            self._volume_down()
            sleep(.1)
            old_vol = self.volume
            self._volume_up()
            while self.volume == old_vol:
                sleep(.1)
                count += 1
                if count > 4:
                    break
            self.show_volume = True

    def _format_title_string(self, title_string):
        ''' format mplayer's title '''
        if "StreamTitle='" in title_string:
            tmp = title_string[title_string.find("StreamTitle='"):].replace("StreamTitle='", self.icy_title_prefix)
            ret_string = tmp[:tmp.find("';")]
        else:
            ret_string = title_string
        if '"artist":"' in ret_string:
            ''' work on format:
                ICY Info: START_SONG='{"artist":"Clelia Cafiero","title":"M. Mussorgsky-Quadri di un'esposizione"}';
                Fund on "ClassicaViva Web Radio: Classical"
            '''
            ret_string = self.icy_title_prefix + ret_string[ret_string.find('"artist":')+10:].replace('","title":"', ' - ').replace('"}\';', '')
        return self._title_string_format_text_tag(ret_string)

    def _format_volume_string(self, volume_string):
        ''' format mplayer's volume '''
        return '[' + volume_string[volume_string.find(self.volume_string):].replace(' %','%').replace('ume', '')+'] '


class VlcPlayer(Player):
    '''Implementation of Player for VLC'''
    PLAYER_NAME = "vlc"
    WIN = False
    if platform.startswith('win'):
        WIN = True
    if WIN:
        # TODO: search and finde vlc.exe
        # PLAYER_CMD = "C:\\Program Files\\VideoLAN\\VLC\\vlc.exe"
        PLAYER_CMD = find_vlc_on_windows()
        if PLAYER_CMD:
            executable_found = True
        else:
            executable_found = False
    else:
        PLAYER_CMD = "cvlc"
        if pywhich(PLAYER_CMD):
            executable_found = True
        else:
            executable_found = False

    if executable_found:
        ''' items of this tuple are considered icy-title
            and get displayed after first icy-title is received '''
        icy_tokens = ('New Icy-Title=', )

        icy_audio_tokens = {
                'Icy-Name:': 'icy-name',
                'Icy-Genre:': 'icy-genre',
                'icy-name:': 'icy-name',
                'icy-genre:': 'icy-genre',
                'icy-url:': 'icy-url',
                'icy-br:': 'icy-br',
                'format:': 'audio_format',
                'using audio decoder module ': 'codec-name',
                }

        muted = paused = False

        ''' String to denote volume change '''
        volume_string = '( audio volume: '

        ''' vlc reports volume in values 0..256 '''
        actual_volume = -1
        max_volume = 256

        ''' When found in station transmission, playback is on '''
        if platform.startswith('win'):
            _playback_token_tuple = (
                # ' successfully opened',
                # 'main audio ',
                # 'Content-Type: audio',
                ' Segment #',
                'using audio decoder module',
                'answer code 200'
            )
            # max_volume = 1000
        else:
            _playback_token_tuple = (
                # 'Content-Type: audio',
                ' Segment #',
                'using audio filter module',
                'using audio decoder module',
                'answer code 200'
            )

        ''' Windows only variables '''
        _vlc_stdout_log_file = ''
        _port = None
        win_show_vlc_volume_function = None

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler,
                 history_add_function,
                 recording_lock):
        config.PLAYER_NAME = 'vlc'
        super(VlcPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler,
            history_add_function,
            recording_lock
        )
        # self.config_files = self.all_config_files['vlc']
        self._config_volume = -1
        self._read_config()
        self.config_files = self.all_config_files['vlc']

    def _on_connect(self):
        logger.error('\n\n***********  VLC on connect\n\n')
        if self._config_volume > -1:
            self.get_volume()
            #self.actual_volume = int(self.max_volume*self._config_volume/100)
            #logger.info('1 self.actual_volume = {}'.format(self.actual_volume))
            if self.volume != self._config_volume:
                #self.volume = self._config_volume
                #self.set_volume(self.actual_volume)
                self.set_volume(self._config_volume)

    def _read_config(self):
        if self._config_volume == -1:
            try:
                with open(self.all_config_files['vlc'][0], 'r') as f:
                    val = f.read().strip()
            except:
                logger.error('\n\nself._config_volume = {}\n\n'.format(self._config_volume))
                return
            try:
                self._config_volume = int(val)
            except ValueError:
                pass
            logger.error('\n\nself._config_volume = {}\n\n'.format(self._config_volume))

    def _write_config(self):
        logger.error('\n\nself.volume = {}'.format(self.volume))
        logger.error('self.actual_volume = {}'.format(self.actual_volume))
        # ovol = round(int(self.volume)*100/self.max_volume)
        # logger.error('ovol = {}\n\n'.format(ovol))
        try:
            with open(self.all_config_files['vlc'][0], 'w') as f:
                # f.write(str(ovol))
                f.write(str(self.volume))
        except:
            return False
        return True

    def _volume_set(self, vol):
        ''' increase vlc's volume '''
        if self.WIN:
            self._win_volup()
            self._win_show_vlc_volume()
        else:
            self._sendCommand('volume {}\n'.format(vol))

    def set_volume(self, vol):
        if self.isPlaying() and \
                not self.muted:
            self.get_volume()
            ivol = int(vol)
            ovol = round(self.max_volume*ivol/100)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('setting volume at {0}% ({1}) with max_volume={2}'.format(ivol, ovol, self.max_volume))
            if ovol != int(self.volume):
                diff = 10 if ovol > int(self.volume) else -10
                vols = [x + diff for x in range(int(self.volume), ovol, diff)]
                vols[-1] = ovol
                if self.WIN:
                    self.show_volume = False
                    for a_vol in vols:
                        self._thrededreq('volume {}'.format(a_vol))
                        self.volume = a_vol
                        sleep(.01)
                    self._win_get_volume()
                    self.show_volume = True
                    self._win_show_vlc_volume()
                else:
                    self.show_volume = False
                    for a_vol in vols:
                        self._sendCommand('volume {}\n'.format(a_vol))
                        self.volume = a_vol
                        sleep(.01)
                    self.show_volume = True
                    self._sendCommand('status\n')

    def save_volume(self):
        return self._do_save_volume('{}')

    def _buildStartOpts(self, streamUrl, playList=False):
        ''' Builds the options to pass to vlc subprocess.'''
        #opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
        monitor_opts = None
        if self.WIN:
            ''' Get a random port (44000-44999)
                Create a log file for vlc and make sure it is unique
                and it is created beforehand
            '''
            random.seed()
            ok_to_go_on = False
            while True:
                logger.error('DE getting port for {}'.format(self.config_dir))
                self._port = random.randint(44000, 44999)
                self._vlc_stdout_log_file = os.path.join(self.config_dir, 'vlc_log.' + str(self._port))
                if os.path.exists(self._vlc_stdout_log_file):
                    ''' another instance running? '''
                    logger.error('DE file exists: "{}"'.format(self._vlc_stdout_log_file))
                    continue
                try:
                    with open(self._vlc_stdout_log_file, 'w', encoding='utf-8') as f:
                        ok_to_go_on = True
                except:
                    logger.error('DE file not opened: "{}"'.format(self._vlc_stdout_log_file))
                    continue
                if ok_to_go_on:
                    break

            opts = [self.PLAYER_CMD, '--no-one-instance', '--no-volume-save',
                '-Irc', '--rc-host', '127.0.0.1:' + str(self._port),
                '--file-logging', '--logmode', 'text', '--log-verbose', '3',
                '--logfile', self._vlc_stdout_log_file, '-vv',
                self._url_to_use(streamUrl)]

            if logger.isEnabledFor(logging.INFO):
                logger.info('vlc listening on 127.0.0.1:{}'.format(self._port))
                logger.info('vlc log file: "{}"'.format(self._vlc_stdout_log_file))

        else:
            if self.recording == self.NO_RECORDING:
                opts = [self.PLAYER_CMD, '--no-one-instance', '--no-volume-save',
                        '-Irc', '-vv', self._url_to_use(streamUrl)]
            else:
                opts = [self.PLAYER_CMD, '--no-one-instance', '--no-volume-save',
                        '-Irc', '-vv', self._url_to_use(streamUrl)]

        ''' take care of command line parameters '''
        params = []
        if self._cnf.command_line_params:
            params = self._cnf.command_line_params.split(' ')
            ''' add command line parameters '''
            if params:
                for a_param in params:
                    opts.append(a_param)

        logger.error('\n\nself._recording = {}'.format(self._recording))
        if self._recording > 0:
            monitor_opts = opts[:]
            i = [y for y, x in enumerate(monitor_opts) if x == streamUrl][0]
            del monitor_opts[i]
            self.recording_filename = self.get_recording_filename(self.name, '.mkv')
            opts.append('--sout')
            opts.append(r'file/ps:' + self.recording_filename)
            monitor_opts.append(self.recording_filename)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('---=== Starting Recording: "{}" ===---',format(self.recording_filename))
        return opts, monitor_opts

    def _mute(self):
        ''' mute vlc '''
        logger.error('DE vlc_mute(): muted = {}'.format(self.muted))
        if self.muted:
            if self.WIN:
                self._win_set_volume(self._unmuted_volume)
                self.volume = int(100 * self._unmuted_volume / self.max_volume)
            else:
                self._sendCommand('volume {}\n'.format(self.actual_volume))
                self.volume = int(100 * self.actual_volume / self.max_volume)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC unmuted: {0} ({1}%)'.format(self.actual_volume, self.volume))
            self.muted = False
        else:
            if self.actual_volume == -1:
                self.get_volume()
            if self.WIN:
                self._win_mute()
            else:
                self._sendCommand('volume 0\n')
            self.muted = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC muted: 0 (0%)')

    def _pause(self):
        ''' pause streaming (if possible) '''
        if self.WIN:
            self._win_pause()
        else:
            self._sendCommand('pause\n')

    def pause(self):
        ''' pause streaming (if possible) '''
        if self.WIN:
            self._win_pause()
        else:
            self._sendCommand('pause\n')

    def _stop(self):
        ''' kill vlc instance '''
        self.stop_win_vlc_status_update_thread = True
        if logger.isEnabledFor(logging.INFO):
            logger.info('setting self.stop_win_vlc_status_update_thread = True')
        if self.ctrl_c_pressed:
            return
        if self.WIN:
            if self.process:
                logger.error('>>>> Terminating process')
                self._req('quit')
            threading.Thread(target=self._remove_vlc_stdout_log_file, args=()).start()
        else:
            self._sendCommand('shutdown\n')
        self._icy_data = {}
        self.volume = -1
        self.monitor = self.monitor_process = self.monitor_opts = None

    def _remove_vlc_stdout_log_file(self):
        file_to_remove = self._vlc_stdout_log_file
        if file_to_remove:
            while os.path.exists(file_to_remove):
                try:
                    os.remove(file_to_remove)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('vlc log file removed: "' + file_to_remove + "'")
                except:
                    pass
                    # logger.error('DE Failed {}'.format(count))

    def _volume_up(self):
        ''' increase vlc's volume '''
        if self.WIN:
            self._win_volup()
            self._win_show_vlc_volume()
        else:
            self._sendCommand('volup\n')

    def _volume_down(self):
        ''' decrease vlc's volume '''
        if self.WIN:
            self._win_voldown()
            self._win_show_vlc_volume()
        else:
            self._sendCommand('voldown\n')

    def _format_volume_string(self, volume_string=None):
        ''' format vlc's volume '''
        if not self.WIN:
            dec_sep = '.' if '.' in volume_string else ','
            self.actual_volume = int(volume_string.split(self.volume_string)[1].split(dec_sep)[0].split()[0])
            self.volume = int(100 * self.actual_volume / self.max_volume)
        return '[Vol: {}%] '.format(self.volume)

    def _format_title_string(self, title_string):
        ''' format vlc's title '''
        sp = title_string.split(self.icy_tokens[0])
        if sp[0] == title_string:
            ret_string = title_string
        else:
            ret_string = self.icy_title_prefix + sp[1]
        return self._title_string_format_text_tag(ret_string)

    def _is_accepted_input(self, input_string):
        ''' vlc input filtering '''
        ret = False
        if self.WIN:
            ''' adding _playback_token_tuple contents here
                otherwise they may not be handled at all...
            '''
            accept_filter = (self.volume_string,
                             'error',
                             'debug: ',
                             'format: ',
                             'using: ',
                             'Content-Type',
                             'main audio',
                             'Segment #',
                             'icy-',
                             'Icy-'
                             )
        else:
            accept_filter = (self.volume_string,
                             'error',
                             'http stream debug: ',
                             'format: ',
                             ': using',
                             'icy-',
                             'Icy-',
                             )
        reject_filter = ()
        for n in accept_filter:
            if n in input_string:
                ret = True
                break
        if ret:
            for n in reject_filter:
                if n in input_string:
                    ret = False
                    break
        return ret

    def get_volume(self, repeat=False):
        ''' get vlc's actual_volume'''
        # logger.error('=======================')
        old_vol = int(self.volume)
        # logger.error('self.volume = {}'.format(self.volume))
        if old_vol <= 0:
            self.show_volume = False
            if self.WIN:
                self._win_get_volume()
            else:
                self._sendCommand('status\n')
                sleep(.1)
                count = 0
                while int(self.volume) == old_vol:
                    sleep(.1)
                    count += 1
                    if count > 4:
                        break
            self.show_volume = True
        # logger.error('self.volume = {}'.format(self.volume))
        # logger.error('repeat = {}'.format(repeat))
        if self.WIN and int(self.volume) <= 0 and not repeat:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('got volume=0, repeating after 1 second')
            sleep(1)
            self.get_volume(repeat=True)
        self.actual_volume = self.volume
        self.volume = int(100 * self.actual_volume / self.max_volume)
        # logger.error('Final')
        # logger.error('self.actual_volume = {}'.format(self.actual_volume))
        # logger.error('self.volume = {}'.format(self.volume))
        # logger.error('=======================')

    def _no_mute_on_stop_playback(self):
        ''' make sure vlc does not stop muted '''
        if self.ctrl_c_pressed:
            return
        if self.isPlaying():
            self.show_volume = False
            self.set_volume(0)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC volume set to 0 at exit')
            self.show_volume = True

    '''   WINDOWS PART '''

    def _req(self, msg, ret_function=None, full=True):
        response = ''
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                # Connect to server and send data
                sock.settimeout(0.7)
                sock.connect(('127.0.0.1', self._port))
                response = ''
                received = ''
                sock.sendall(bytes(msg + '\n', 'utf-8'))
                if msg != 'quit':
                    try:
                        while (True):
                            received = (sock.recv(4096)).decode()
                            response = response + received
                            if full:
                                if response.count('\r\n') > 1:
                                    sock.close()
                                    break
                            else:
                                if response.count('\r\n') > 0:
                                    sock.close()
                                    break
                    except:
                        response = response + received
                sock.close()
        except:
            pass
        # logger.info('response = "{}"'.format(response))
        if msg == 'quit':
            self.process.terminate()
            self.process = None
        if ret_function:
            ret_function(response)
        return response

    def _thrededreq(self, msg, ret_function=None):
        self._thrededreq_thread = threading.Thread(
            target=self._req,
            args=(msg,ret_function)
        )
        self._thrededreq_thread.start()
        self._thrededreq_thread.join()
        while self._thrededreq_thread.is_alive():
            sleep(.01)

    def _win_show_vlc_volume(self):
        #if self.win_show_vlc_volume_function:
        self._win_get_volume()
        self._thrededreq_thread.join()
        pvol = int(100 * self.actual_volume / self.max_volume)
        if pvol > 0:
            avol = '[Vol: {}%] '.format(pvol)
            if self.show_volume and self.oldUserInput['Title']:
                self.outputStream.write(msg=avol + self.oldUserInput['Title'], counter='')
                self.threadUpdateTitle()

    def _win_get_volume(self):
        self._thrededreq('status', self._get_volume_response)

    def _get_volume_response(self, msg):
        # logger.debug('msg = "{}"'.format(msg))
        parts = msg.split('\r\n')
        # logger.debug('parts = {}'.format(parts))
        for n in parts:
            if 'volume' in n:
                vol = n.split(': ')[-1].replace(' )', '')
                for n in ('.', ','):
                    ind = vol.find(n)
                    if ind > -1:
                        vol = vol[:ind]
                        break
                # logger.debug('vol = "{}"'.format(vol))
                try:
                    self.actual_volume = int(vol)
                except ValueError:
                    # logger.error('DE ValueError: vol = {}'.format(vol))
                    return
                break
        # logger.debug('self.actual_volume = {}'.format(self.actual_volume))
        if self.actual_volume == 0:
            self.muted = True
            self.volume = 0
        else:
            self.muted = False
            self.volume = int(100 * self.actual_volume / self.max_volume)
        #self.print_response(vol)

    def _win_volup(self):
        self._thrededreq('volup 1')

    def _win_voldown(self):
        self._thrededreq('voldown 1')

    def _win_set_volume(self, vol):
        ivol = int(vol)
        self._thrededreq('volume ' + str(ivol))
        self.actual_volume = ivol
        self.volume = int(100 * self.actual_volume / self.max_volume)

    def _win_mute(self):
        self._win_get_volume()
        self._unmuted_volume = self.actual_volume
        self._thrededreq('volume 0')
        self.actual_volume = self.volume = 0
        self.muted = True

    def _win_pause(self):
        self._thrededreq('pause')

    def _win_is_playing(self):
        self._thrededreq('is_playing', self._win_get_playing_state)

    def _win_get_playing_state(self, msg):
        parts = msg.split('\r\n')
        rep = False
        for n in parts:
            if n == '1' or 'play state:' in n:
                rep = True
                break
        #self.print_response(rep)

def probePlayer(requested_player=''):
    ''' Probes the multimedia players which are
        available on the host system. '''
    if logger.isEnabledFor(logging.INFO):
        logger.info('Probing available multimedia players...')
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info('Implemented players: ' +
                    ', '.join([player.PLAYER_NAME
                              for player in implementedPlayers]))

    for player in implementedPlayers:
        ret = check_player(player)
        if ret is not None:
            available_players.append(ret)
    if logger.isEnabledFor(logging.INFO):
        logger.info('Available players: ' +
                    ', '.join([player.PLAYER_NAME
                              for player in available_players]))
    if requested_player:
        req = requested_player.split(',')
        for r_player in req:
            if r_player == 'cvlc':
                r_player = 'vlc'
            for a_found_player in available_players:
                if a_found_player.PLAYER_NAME == r_player:
                    return a_found_player
        if logger.isEnabledFor(logging.INFO):
            logger.info('Requested player "{}" not supported'.format(requested_player))
        return None
    else:
        return available_players[0] if available_players else None

def check_player(a_player):
    try:
        p = subprocess.Popen([a_player.PLAYER_CMD, '--help'],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             shell=False)
        p.terminate()

        if logger.isEnabledFor(logging.INFO):
            logger.info('{} supported.'.format(str(a_player)))
        return a_player
    except OSError:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('{} not supported.'.format(str(a_player)))
        return None
