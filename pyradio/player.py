# -*- coding: utf-8 -*-
import subprocess
import threading
import os
import random
import logging
from os.path import expanduser
from sys import platform, version_info, platform
from sys import exit
from time import sleep
import collections
import json
import socket

try:
    from urllib import unquote
except ImportError:
    from urllib.parse import unquote
from .cjkwrap import wrap
from .encodings import get_encodings

logger = logging.getLogger(__name__)

try:  # Forced testing
    from shutil import which
    def pywhich (cmd):
        pr = which(cmd)
        if pr:
            return pr
        else:
            return None
except ImportError:  # Forced testing
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

        if platform == 'win32':
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
    for path in ('C:\\Program Files\\VideoLAN\\VLC\\vlc.exe',
                'C:\\Program Files (x86)\\VideoLAN\\VLC\\vlc.exe'
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


def info_dict_to_list(info, fix_highlight, max_width):
    max_len = 0
    for a_title in info.keys():
        if len(a_title) > max_len:
            max_len = len(a_title)
        if version_info < (3, 0):
            info[a_title] = info[a_title].encode('utf-8', 'replace')
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

    icy_title_prefix = 'Title: '
    title_prefix = ''

    # Input:   old user input     - used to early suppress output
    #                               in case of consecutive equal messages
    # Volume:  old volume input   - used to suppress output (and firing of delay thread)
    #                               in case of consecutive equal volume messages
    # Title:   old title input    - printed by delay thread
    oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}

    ''' volume percentage '''
    volume = -1

    delay_thread = None
    connection_timeout_thread = None

    ''' make it possible to change volume but not show it '''
    show_volume = True

    muted = False

    ctrl_c_pressed = False

    ''' When found in station transmission, playback is on '''
    _playback_token_tuple = ( 'AO: [', )

    icy_tokens = ()
    icy_audio_tokens = {}

    playback_is_on = False

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

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler):
        self.outputStream = outputStream
        self._cnf = config
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
        if platform == 'win32':
            ''' delete old vlc files (vlc_log.*) '''
            from .del_vlc_log import RemoveWinVlcLogFiles
            threading.Thread(target=RemoveWinVlcLogFiles(self.config_dir)).start()

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

    @property
    def profile_name(self):
        return self._cnf.profile_name

    @profile_name.setter
    def is_register(self, value):
        raise ValueError('property is read only')

    @property
    def profile_token(self):
        return  '[' + self.profile_name + ']'

    @profile_token.setter
    def is_register(self, value):
        raise ValueError('property is read only')

    def __del__(self):
        self.close()

    def _url_to_use(self, streamUrl):
        if self.force_http:
            return streamUrl.replace('https://', 'http://')
        else:
            return streamUrl

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
                info[x[0]] = self._icy_data[x[1]]
            else:
                info[x[0]] = ''
            if x[0] == 'Bitrate':
                if info[x[0]]:
                    info[x[0]] += ' kb/s'
            if x[0] == 'Genre':
                info['Encoding'] = enc_to_show
            if x[0].startswith('Reported'):
                info['Station URL'] = a_station[1]
        info['Website'] = unquote(info['Website'])

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
            if os.path.exists(config_file):
                # if platform.startswith('win'):
                #     """ This is actually only for mplayer
                #         which does not support profiles on Windows
                #     """
                #     with open(config_file, 'r') as c_file:
                #         config_string = c_file.read()
                #     if "volume=" in config_string:
                #         config_string = config_string.replace('#Volume set from pyradio\n', '')
                #         vol = config_string.splitlines()
                #         for i, v_string in enumerate(vol):
                #             if v_string.startswith('volume'):
                #                 vol[i] = '#Volume set from pyradio\nvolume={}'.format(self.volume)
                #                 break
                #         config_string = '\n'.join(vol)
                #     else:
                #         out = config_string + 'volume={}'.format(self.volume)
                #         config_string = out
                #     try:
                #         with open(config_file, "w") as c_file:
                #             c_file.write(config_string)
                #         volume = self.volume
                #         self.volume = -1
                #         self.PROFILE_FROM_USER = True
                #         return ret_strings[1].format(str(volume))
                #     except:
                #         if (logger.isEnabledFor(logging.DEBUG)):
                #             logger.debug(log_strings[2].format(config_file))
                #         return ret_strings[2].format(str(self.volume))
                # else:
                if self.PROFILE_FROM_USER:
                    with open(config_file, 'r') as c_file:
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
                        with open(config_file, 'w') as c_file:
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
                    with open(config_file, 'a') as c_file:
                        c_file.write(new_profile_string.format(str(self.volume)))
                except EnvironmentError:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        logger.debug(log_strings[2].format(config_file))
                    return ret_strings[2].format(str(self.volume))
                self.volume = -1
                self.PROFILE_FROM_USER = True
            return ret_string

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

    def updateStatus(self, *args):
        stop = args[0]
        process = args[1]
        stop_player = args[2]
        detect_if_player_exited = args[3]
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('updateStatus thread started.')
        #with lock:
        #    self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
        #    self.outputStream.write(msg=self.oldUserInput['Title'])
        ''' Force volume display even when icy title is not received '''
        self.oldUserInput['Title'] = 'Playing: "{}"'.format(self.name)
        try:
            out = self.process.stdout
            while(True):
                subsystemOutRaw = out.readline()
                try:
                    subsystemOut = subsystemOutRaw.decode(self._station_encoding, 'replace')
                except:
                    subsystemOut = subsystemOutRaw.decode('utf-8', 'replace')
                if subsystemOut == '':
                    break
                if not self._is_accepted_input(subsystemOut):
                    continue
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace('\r', '').replace('\n', '')
                if self.oldUserInput['Input'] != subsystemOut:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            logger.debug('User input: {}'.format(disp))
                        else:
                            logger.debug('User input: {}'.format(subsystemOut))
                    self.oldUserInput['Input'] = subsystemOut
                    if self.volume_string in subsystemOut:
                        # disable volume for mpv
                        if self.PLAYER_NAME != 'mpv':
                            # logger.error('***** volume')
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
                        self.stop_timeout_counter_thread = True
                        try:
                            self.connection_timeout_thread.join()
                        except:
                            pass
                        if (not self.playback_is_on) and (logger.isEnabledFor(logging.INFO)):
                                logger.info('*** updateStatus(): Start of playback detected ***')
                        #if self.outputStream.last_written_string.startswith('Connecting to'):
                        if self.oldUserInput['Title'] == '':
                            new_input = 'Playing: "{}"'.format(self.name)
                        else:
                            new_input = self.oldUserInput['Title']
                        self.outputStream.write(msg=new_input, counter='')
                        self.playback_is_on = True
                        self._stop_delay_thread()
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
                                    self._get_mpv_metadata(response, lambda: False)
                                    self.info_display_handler()
                                else:
                                    if logger.isEnabledFor(logging.INFO):
                                        logger.info('no response!!!')
                        # logger.error('DE 3 {}'.format(self._icy_data))
                    elif self._is_icy_entry(subsystemOut):
                        if not subsystemOut.endswith('Icy-Title=(null)'):
                            # logger.error('***** icy_entry: "{}"'.format(subsystemOut))
                            title = self._format_title_string(subsystemOut)
                            ok_to_display = False
                            if not self.playback_is_on:
                                if logger.isEnabledFor(logging.INFO):
                                    logger.info('*** updateStatus(): Start of playback detected (Icy-Title received) ***')
                            self.playback_is_on = True
                            if title[len(self.icy_title_prefix):].strip():
                                #self._stop_delay_thread()
                                # logger.error("***** updating title")
                                self.oldUserInput['Title'] = title
                                # make sure title will not pop-up while Volume value is on
                                if self.delay_thread is None:
                                    ok_to_display = True
                                if ok_to_display and self.playback_is_on:
                                    string_to_show = self.title_prefix + title
                                    self.outputStream.write(msg=string_to_show, counter='')
                                else:
                                    if logger.isEnabledFor(logging.debug):
                                        logger.debug('***** Title change inhibited: ok_to_display = {0}, playbabk_is_on = {1}'.format(ok_to_display, self.playback_is_on))
                            else:
                                ok_to_display = True
                                if (logger.isEnabledFor(logging.INFO)):
                                    logger.info('Icy-Title is NOT valid')
                                if ok_to_display and self.playback_is_on:
                                    title = 'Playing: "{}"'.format(self.name)
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
                                self.playback_is_on = True
                                # logger.error(' DE token = "{}"'.format(a_token))
                                # logger.error(' DE icy_audio_tokens[a_token] = "{}"'.format(self.icy_audio_tokens[a_token]))
                                a_str = subsystemOut.split(a_token)
                                # logger.error(' DE str = "{}"'.format(a_str))
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
            return

        if detect_if_player_exited():
            if not platform.startswith('win32'):
                poll = process.poll()
                if poll is not None:
                    logger.error('----==== player disappeared! ====----')
                    stop_player(from_update_thread=True)
            logger.error('----==== player disappeared! ====----')
            stop_player(from_update_thread=True)
        if (logger.isEnabledFor(logging.INFO)):
            logger.info('updateStatus thread stopped.')

    def updateMPVStatus(self, *args):
        stop = args[0]
        process = args[1]
        stop_player = args[2]
        detect_if_player_exited = args[3]
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
                sleep(.25)
        # Send data
        message = b'{ "command": ["observe_property", 1, "metadata"] }\n'
        try:
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
                    data = sock.recvmsg(4096)
                    if isinstance(data, tuple):
                        a_data = data[0]
                    else:
                        a_data = data
                    # logger.error('DE Received: "{!r}"'.format(a_data))

                    if a_data == b'' or stop():
                        break

                    if a_data:
                        all_data = a_data.split(b'\n')
                        for n in all_data:
                            if self._get_mpv_metadata(n, stop):
                                self._request_mpv_info_data(sock)
                            else:
                                try:
                                    if stop():
                                        break
                                    d = json.loads(n)
                                    if 'event' in d.keys():
                                        if d['event'] == 'metadata-update':
                                            try:
                                                sock.sendall(self.GET_TITLE)
                                            except:
                                                break
                                            ret = self._set_mpv_playback_is_on(stop)
                                            if not ret:
                                                break
                                            self._request_mpv_info_data(sock)
                                            self.info_display_handler()
                                        elif d['event'] == 'playback-restart':
                                            if not self.playback_is_on:
                                                ret = self._set_mpv_playback_is_on(stop)
                                            if not ret:
                                                break
                                            self._request_mpv_info_data(sock)
                                            self.info_display_handler()
                                except:
                                    pass
                finally:
                    pass
        sock.close()
        if not stop():
            ''' haven't been asked to stop '''
            # logger.error('\n\nDE NOT ASKED TO STOP\n\n')
            # poll = process.poll()
            # logger.error('DE poll = {}'.format(poll))
            # if poll is not None:
            logger.error('----==== MPV disappeared! ====----')
            stop_player(from_update_thread=True)
        if (logger.isEnabledFor(logging.INFO)):
            logger.info('MPV updateStatus thread stopped.')

    def updateWinVLCStatus(self, *args):
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug('Win VLC updateStatus thread started.')
        fn = args[0]
        enc = args[1]
        stop = args[2]
        process = args[3]
        stop_player = args[4]
        detect_if_player_exited = args[5]
        ''' Force volume display even when icy title is not received '''
        self.oldUserInput['Title'] = 'Playing: "{}"'.format(self.name)
        # logger.error('DE ==== {0}\n{1}\n{2}'.format(fn, enc, stop))
        #with lock:
        #    self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
        #    self.outputStream.write(msg=self.oldUserInput['Title'])

        go_on = False
        while not go_on:
            if stop():
                break
            poll= process.poll()
            if poll is not None:
                logger.error('----==== vlc disappeared! ====----')
                stop_player(from_update_thread=True)
                break
            try:
                fp = open(fn, mode='rt', encoding=enc, errors='ignore')
                go_on = True
            except:
                pass

        try:
            while(True):
                if stop():
                    break
                poll= process.poll()
                if poll is not None:
                    logger.error('----==== vlc disappeared! ====----')
                    stop_player(from_update_thread=True)
                    break
                subsystemOut = fp.readline()
                subsystemOut = subsystemOut.strip().replace(u'\ufeff', '')
                subsystemOut = subsystemOut.replace('\r', '').replace('\n', '')
                if subsystemOut == '':
                    continue
                # logger.error('DE >>> "{}"'.format(subsystemOut))
                if not self._is_accepted_input(subsystemOut):
                    continue
                # logger.error('DE --- accepted')
                if self.oldUserInput['Input'] != subsystemOut:
                    if stop():
                        break
                    poll= process.poll()
                    if poll is not None:
                        logger.error('----==== vlc disappeared! ====----')
                        stop_player(from_update_thread=True)
                        break
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            # logger.debug("User input: {}".format(disp))
                        else:
                            # logger.debug("User input: {}".format(subsystemOut))
                            pass
                    self.oldUserInput['Input'] = subsystemOut
                    if self.volume_string in subsystemOut:
                        if stop():
                            break
                        poll= process.poll()
                        if poll is not None:
                            logger.error('----==== vlc disappeared! ====----')
                            stop_player(from_update_thread=True)
                            break
                        # disable volume for mpv
                        if self.PLAYER_CMD != "mpv":
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
                        if stop():
                            break
                        poll= process.poll()
                        if poll is not None:
                            logger.error('----==== vlc disappeared! ====----')
                            stop_player(from_update_thread=True)
                            break
                        self.stop_timeout_counter_thread = True
                        try:
                            self.connection_timeout_thread.join()
                        except:
                            pass
                        if (not self.playback_is_on) and (logger.isEnabledFor(logging.INFO)):
                                logger.info('*** updateWinVLCStatus(): Start of playback detected ***')
                        #if self.outputStream.last_written_string.startswith('Connecting to'):
                        if self.oldUserInput['Title'] == '':
                            new_input = 'Playing: "{}"'.format(self.name)
                        else:
                            new_input = self.oldUserInput['Title']
                        self.outputStream.write(msg=new_input, counter='')
                        self.playback_is_on = True
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
                        poll= process.poll()
                        if poll is not None:
                            logger.error('----==== vlc disappeared! ====----')
                            stop_player(from_update_thread=True)
                            break
                        if not self.playback_is_on:
                            if logger.isEnabledFor(logging.INFO):
                                logger.info('*** updateWinVLCStatus(): Start of playback detected (Icy-Title received) ***')
                        self.playback_is_on = True

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
                                    title = 'Playing: "{}"'.format(self.name)
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
                        poll= process.poll()
                        if poll is not None:
                            logger.error('----==== vlc disappeared! ====----')
                            stop_player(from_update_thread=True)
                            break
                        for a_token in self.icy_audio_tokens.keys():
                            if a_token in subsystemOut:
                                if not self.playback_is_on:
                                    if logger.isEnabledFor(logging.INFO):
                                        logger.info('*** updateWinVLCStatus(): Start of playback detected (Icy audio token received) ***')
                                self.playback_is_on = True
                                # logger.error(' DE token = "{}"'.format(a_token))
                                # logger.error(' DE icy_audio_tokens[a_token] = "{}"'.format(self.icy_audio_tokens[a_token]))
                                a_str = subsystemOut.split(a_token)
                                # logger.error(' DE str = "{}"'.format(a_str))
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
            poll= process.poll()
            if poll is not None:
                logger.error('----==== vlc disappeared! ====----')
                stop_player(from_update_thread=True)
        try:
            fp.close()
        except:
            pass

    def _request_mpv_info_data(self, sock):
        with self.status_update_lock:
            ret = len(self._icy_data)
        if ret == 0:
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

        if b'"icy-title":"' in a_data:
            if version_info > (3, 0):
                title = a_data.split(b'"icy-title":"')[1].split(b'"}')[0]
                if title:
                    try:
                        self.oldUserInput['Title'] = 'Title: ' + title.decode(self._station_encoding, 'replace')
                    except:
                        self.oldUserInput['Title'] = 'Title: ' + title.decode('utf-8', 'replace')
                    string_to_show = self.title_prefix + self.oldUserInput['Title']
                    if stop():
                        return False
                    self.outputStream.write(msg=string_to_show, counter='')
                    if not self.playback_is_on:
                        return self._set_mpv_playback_is_on(stop)
                else:
                    if (logger.isEnabledFor(logging.INFO)):
                        logger.info('Icy-Title is NOT valid')
                    title = 'Playing: "{}"'.format(self.name)
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

    def _set_mpv_playback_is_on(self, stop):
        self.stop_timeout_counter_thread = True
        try:
            self.connection_timeout_thread.join()
        except:
            pass
        if (not self.playback_is_on) and (logger.isEnabledFor(logging.INFO)):
                    logger.info('*** _set_mpv_playback_is_on(): Start of playback detected ***')
        new_input = 'Playing: "{}"'.format(self.name)
        self.outputStream.write(msg=new_input, counter='')
        if self.oldUserInput['Title'] == '':
            self.oldUserInput['Input'] = new_input
        self.oldUserInput['Title'] = new_input
        self.playback_is_on = True
        if stop():
            return False
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
        # logger.error("**** a_string = {}".format(a_string))
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
                return ret_string + ': "' + final_text_string + '"'

    def _format_volume_string(self, volume_string):
        return self._title_string_format_text_tag(volume_string)

    def isPlaying(self):
        return bool(self.process)

    def play(self, name, streamUrl, stop_player, detect_if_player_exited, encoding=''):
        ''' use a multimedia player to play a stream '''
        self.close()
        self.name = name
        self.oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}
        self.muted = False
        self.show_volume = True
        self.title_prefix = ''
        self.playback_is_on = False
        self.delay_thread = None
        self.outputStream.write(msg='Station: "{}" - Opening connection...'.format(name), counter='')
        if logger.isEnabledFor(logging.INFO):
            logger.info('Selected Station: "{}"'.format(name))
        if encoding:
            self._station_encoding = encoding
        else:
            self._station_encoding = self.config_encoding
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts = self._buildStartOpts(streamUrl, isPlayList)
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
            t = threading.Thread(target=self.updateWinVLCStatus, args=(
                    self._vlc_stdout_log_file,
                    self.config_encoding,
                    lambda: self.stop_win_vlc_status_update_thread,
                    self.process,
                    stop_player,
                    detect_if_player_exited))
        else:
            if self.PLAYER_NAME == 'mpv' and version_info > (3, 0):
                self.process = subprocess.Popen(opts, shell=False,
                                                stdout=subprocess.DEVNULL,
                                                stdin=subprocess.DEVNULL,
                                                stderr=subprocess.DEVNULL)
                t = threading.Thread(
                    target=self.updateMPVStatus,
                    args=(lambda: self.stop_mpv_status_update_thread,
                          self.process,
                          stop_player,
                          detect_if_player_exited)
                )
            else:
                self.process = subprocess.Popen(
                    opts, shell=False,
                    stdout=subprocess.PIPE,
                    stdin=subprocess.PIPE,
                    stderr=subprocess.STDOUT
                )
                t = threading.Thread(
                    target=self.updateStatus,
                    args=(lambda: self.stop_mpv_status_update_thread,
                          self.process,
                          stop_player,
                          detect_if_player_exited))
        t.start()
        if self.PLAYER_NAME == 'vlc':
            self._get_volume()
        # start playback check timer thread
        self.stop_timeout_counter_thread = False
        if self.playback_timeout > 0:
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
                self.connection_timeout_thread = None
                if (logger.isEnabledFor(logging.ERROR)):
                    logger.error('playback detection thread failed to start')
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('playback detection thread not starting (timeout is 0)')
        if logger.isEnabledFor(logging.INFO):
            logger.info('Player started')

    def _sendCommand(self, command):
        ''' send keystroke command to player '''

        if(self.process is not None):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Sending Command: {}'.format(command).strip())
            try:
                self.process.stdin.write(command.encode('utf-8', 'replace'))
                self.process.stdin.flush()
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
            if platform.startswith('win'):
                try:
                    subprocess.Call(['Taskkill', '/PID', '{}'.format(self.process.pid), '/F', '/T'])
                    logger.error('Taskkill killed PID {}'.format(self.process.pid))
                    self.process = None
                    # logger.error('***** self.process = None')
                except:
                    logger.error('Taskkill failed to kill PID {}'.format(self.process.pid))
            else:
                try:
                    os.kill(self.process.pid, 15)
                    self.process.wait()
                except:
                    # except ProcessLookupError:
                    pass
            self.process = None

    def _buildStartOpts(self, streamUrl, playList):
        pass

    def toggleMute(self):
        ''' mute / unmute player '''

        if self.PLAYER_NAME == 'mpv':
            self.muted = self._mute()
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
        if self.oldUserInput['Title'] == '':
            self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Input']), counter='')
        else:
            self.outputStream.write(msg=self.title_prefix + self._format_title_string(self.oldUserInput['Title']), counter='')

    def _mute(self):
        ''' to be implemented on subclasses '''
        pass

    def _stop(self):
        pass

    def _get_volume(self):
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
    NEW_PROFILE_STRING = 'volume=50\n\n'
    if pywhich(PLAYER_CMD):
        executable_found = True
    else:
        executable_found = False

    if executable_found:
        ''' items of this tupple are considered icy-title
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

        mpvsocket = '/tmp/mpvsocket.{}'.format(os.getpid())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('mpv socket is "{}"'.format(self.mpvsocket))
        if os.path.exists(mpvsocket):
            os.system('rm ' + mpvsocket + ' 2>/dev/null');

        commands = {
                'volume_up':   b'{ "command": ["cycle", "volume", "up"], "request_id": 1000 }\n',
                'volume_down': b'{ "command": ["cycle", "volume", "down"], "request_id": 1001 }\n',
                'mute':        b'{ "command": ["cycle", "mute"], "request_id": 1002 }\n',
                'pause':       b'{ "command": ["pause"], "request_id": 1003 }\n',
                'quit':        b'{ "command": ["quit"], "request_id": 1004}\n',
                }

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler):
        config.PLAYER_NAME = 'mpv'
        super(MpvPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler
        )
        self.config_files = self.all_config_files['mpv']

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
                with open(config_file) as f:
                    config_string = f.read()
                if self.profile_token in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                        return 1

        ''' profile not found in config
            create a default profile
        '''
        try:
            with open(self.config_files[0], 'a') as f:
                f.write('\n[{}]\n'.format(self.profile_name))
                f.write(self.NEW_PROFILE_STRING)
            self.PROFILE_FROM_USER = True
            return 1
        except:
            return 0

    def _buildStartOpts(self, streamUrl, playList=False):
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

        ''' Do I have user profile in config?
            If so, can I use it?
        '''
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

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

        return opts

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
                sock.sendall(b'{ "command": ["get_property", "mute"], "request_id": 600 }\n')
            except:
                sock.close()
                return
            # wait for response
            try:
                if version_info < (3, 0):
                    data = sock.recv(4096)
                else:
                    data = sock.recvmsg(4096)
                if isinstance(data, tuple):
                    a_data = data[0]
                else:
                    a_data = data
                # logger.error('DE Received: "{!r}"'.format(a_data))

                if a_data:
                    all_data = a_data.split(b'\n')
                    for n in all_data:
                        try:
                            d = json.loads(n)
                            if d['error'] == 'success':
                                if isinstance(d['data'], bool):
                                    sock.close()
                                    return d['data']
                        except:
                            pass
            finally:
                pass

    def pause(self):
        ''' pause streaming (if possible) '''
        self._send_mpv_command('pause')

    def _stop(self):
        ''' kill mpv instance '''
        self.stop_mpv_status_update_thread = True
        self._send_mpv_command('quit')
        os.system('rm ' + self.mpvsocket + ' 2>/dev/null');
        self._icy_data = {}

    def _volume_up(self):
        ''' increase mpv's volume '''
        self._send_mpv_command('volume_up')
        self._display_mpv_volume_value()

    def _volume_down(self):
        ''' decrease mpv's volume '''
        self._send_mpv_command('volume_down')
        self._display_mpv_volume_value()

    def _format_title_string(self, title_string):
        ''' format mpv's title '''
        return self._title_string_format_text_tag(title_string.replace(self.icy_tokens[0], self.icy_title_prefix))

    def _format_volume_string(self, volume_string):
        ''' format mpv's volume '''
        return '[' + volume_string[volume_string.find(self.volume_string):].replace('ume', '')+'] '

    def _connect_to_socket(self, server_address):
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        try:
            sock.connect(server_address)
            return sock
        except:
            sock.close()
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
            if a_command in self.commands.keys():
                sock.sendall(self.commands[a_command])
            else:
                sock.sendall(a_command)
        except:
            sock.close()
            if return_response:
                return ''
            else:
                return False
        # read the response
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
        sock.close()
        if return_response:
            return data
        else:
            return True

    def _display_mpv_volume_value(self):
        ''' Display volume for MPV

            Currently working with python 2 and 3
            Eventually will be used for python 2 only

            Python 2 cannot correctly read icy-title from
            the socket (unidoce issue), so it has to read
            it from stdout.
        '''

        #if version_info > (3, 0):
        #    return
        vol = 0
        while True:
            sock = self._connect_to_socket(self.mpvsocket)
            if sock:
                break
            sleep(.25)

        # Send data
        message = b'{ "command": ["get_property", "volume"] }\n'
        try:
            sock.sendall(message)
        except:
            sock.close()
            return

        # wait for response
        got_it = True
        while got_it:
            try:
                if version_info < (3, 0):
                    data = sock.recv(4096)
                else:
                    data = sock.recvmsg(4096)
                if isinstance(data, tuple):
                    a_data = data[0]
                else:
                    a_data = data
                # logger.error('DE Received: "{!r}"'.format(a_data))

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
        sock.close()
        if self.oldUserInput['Title']:
            info_string = self._format_title_string(self.oldUserInput['Title'])
        else:
            info_string = self._format_title_string(self.oldUserInput['Input'])
        string_to_show = self._format_volume_string('Volume: ' + str(vol) + '%') + info_string
        self.outputStream.write(msg=string_to_show, counter='')
        self.threadUpdateTitle()
        self.volume = vol

class MpPlayer(Player):
    '''Implementation of Player object for MPlayer'''

    PLAYER_NAME = 'mplayer'
    PLAYER_CMD = 'mplayer'
    NEW_PROFILE_STRING = 'softvol=1\nsoftvol-max=300\nvolstep=1\nvolume=50\n\n'
    if pywhich(PLAYER_CMD):
        executable_found = True
    else:
        executable_found = False

    if executable_found:
        ''' items of this tupple are considered icy-title
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
                 info_display_handler):
        config.PLAYER_NAME = 'mplayer'
        super(MpPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler
        )
        self.config_files = self.all_config_files['mplayer']

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
        #if platform.startswith('win'):
        #    ''' Existing mplayer Windows implementations
        #        do not support profiles
        #    '''
        #    return 0
        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file) as f:
                    config_string = f.read()
                if self.profile_token in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                        return 1

        ''' profile not found in config
            create a default profile
        '''
        try:
            with open(self.config_files[0], 'a') as f:
                f.write('\n[{}]\n'.format(self.profile_name))
                f.write(self.NEW_PROFILE_STRING)
            self.PROFILE_FROM_USER = True
            return 1
        except:
            return 0

    def _buildStartOpts(self, streamUrl, playList=False):
        ''' Builds the options to pass to mplayer subprocess.'''
        opts = [self.PLAYER_CMD, '-vo', 'null', '-quiet']

        ''' this will set the profile too '''
        params = []
        if self._cnf.command_line_params:
            params = self._cnf.command_line_params.split(' ')

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

        return opts

    def _mute(self):
        ''' mute mplayer '''
        self._sendCommand('m')

    def pause(self):
        ''' pause streaming (if possible) '''
        self._sendCommand('p')

    def _stop(self):
        ''' kill mplayer instance '''
        self._sendCommand('q')
        self._icy_data = {}

    def _volume_up(self):
        ''' increase mplayer's volume '''
        self._sendCommand('*')

    def _volume_down(self):
        ''' decrease mplayer's volume '''
        self._sendCommand('/')

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
        ''' items of this tupple are considered icy-title
            and get displayed after first icy-title is received '''
        icy_tokens = ('New Icy-Title=', )

        icy_audio_tokens = {
                'Icy-Name: ': 'icy-name',
                'Icy-Genre: ': 'icy-genre',
                'icy-url: ': 'icy-url',
                'icy-br: ': 'icy-br',
                'format: ': 'audio_format',
                'using audio decoder module ': 'codec-name',
                }

        muted = False

        ''' String to denote volume change '''
        volume_string = '( audio volume: '

        ''' vlc reports volume in values 0..512 '''
        actual_volume = -1
        max_volume = 512

        ''' When found in station transmission, playback is on '''
        _playback_token_tuple = ('main audio ', 'Content-Type: audio', ' Segment #' )

        ''' Windows only variables '''
        _vlc_stdout_log_file = ''
        _port = None
        win_show_vlc_volume_function = None

    def __init__(self,
                 config,
                 outputStream,
                 playback_timeout_counter,
                 playback_timeout_handler,
                 info_display_handler):
        config.PLAYER_NAME = 'vlc'
        super(VlcPlayer, self).__init__(
            config,
            outputStream,
            playback_timeout_counter,
            playback_timeout_handler,
            info_display_handler
        )
        # self.config_files = self.all_config_files['vlc']

    def save_volume(self):
        pass

    def _buildStartOpts(self, streamUrl, playList=False):
        ''' Builds the options to pass to vlc subprocess.'''
        #opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
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
                    with open(self._vlc_stdout_log_file, 'w') as f:
                        ok_to_go_on = True
                except:
                    logger.error('DE file not opened: "{}"'.format(self._vlc_stdout_log_file))
                    continue
                if ok_to_go_on:
                    break

            opts = [self.PLAYER_CMD, '-Irc', '--rc-host',
                '127.0.0.1:' + str(self._port),
                '--file-logging', '--logmode', 'text', '--log-verbose', '4',
                '--logfile', self._vlc_stdout_log_file, '-vv',
                self._url_to_use(streamUrl)]

            if logger.isEnabledFor(logging.INFO):
                logger.info('vlc listening on 127.0.0.1:{}'.format(self._port))
                logger.info('vlc log file: "{}"'.format(self._vlc_stdout_log_file))

        else:
            opts = [self.PLAYER_CMD, '-Irc', '-vv', self._url_to_use(streamUrl)]


        ''' take care of command line parameters '''
        params = []
        if self._cnf.command_line_params:
            params = self._cnf.command_line_params.split(' ')
            ''' add command line parameters '''
            if params:
                for a_param in params:
                    opts.append(a_param)

        return opts

    def _mute(self):
        ''' mute vlc '''
        logger.error('DE vlc_mute(): muted = {}'.format(self.muted))
        if self.muted:
            if self.WIN:
                self._win_set_volume(self._unmuted_volume)
            else:
                self._sendCommand('volume {}\n'.format(self.actual_volume))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC unmuted: {0} ({1}%)'.format(self.actual_volume, int(100 * self.actual_volume / self.max_volume)))
            self.muted = False
        else:
            if self.actual_volume == -1:
                self._get_volume()
            if self.WIN:
                self._win_mute()
            else:
                self._sendCommand('volume 0\n')
            self.muted = True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC muted: 0 (0%)')

    def pause(self):
        ''' pause streaming (if possible) '''
        if self.WIN:
            self._win_pause()
        else:
            self._sendCommand('stop\n')

    def _stop(self):
        ''' kill vlc instance '''
        logger.error('setting self.stop_win_vlc_status_update_thread = True')
        self.stop_win_vlc_status_update_thread = True
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
                    # logger.error('Failed {}'.format(count))

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
        return '[Vol: {}%] '.format(int(100 * self.actual_volume / self.max_volume))

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
            accept_filter = (self.volume_string,
                             'debug: ',
                             'format: ',
                             'using: ',
                             )
        else:
            accept_filter = (self.volume_string,
                             'http stream debug: ',
                             'format: ',
                             ': using',
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

    def _get_volume(self):
        ''' get vlc's actual_volume'''
        self.show_volume = False
        if self.WIN:
            self._win_get_volume()
        else:
            self._sendCommand('volume\n')
        self.show_volume = True

    def _no_mute_on_stop_playback(self):
        ''' make sure vlc does not stop muted '''
        if self.ctrl_c_pressed:
            return
        if self.isPlaying():
            if self.actual_volume == -1:
                self._get_volume()
                if self.actual_volume == -1:
                    self.actual_volume = 0
            if self.actual_volume == 0:
                self.actual_volume = int(self.max_volume*0.25)
                if self.WIN:
                    self._win_set_volume(self.actual_volume)
                else:
                    self._sendCommand('volume {}\n'.format(self.actual_volume))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Unmuting VLC on exit: {} (25%)'.format(self.actual_volume))
            elif self.muted:
                if self.actual_volume > 0:
                    if self.WIN:
                        self._win_set_volume(self.actual_volume)
                    else:
                        self._sendCommand('volume {}\n'.format(self.actual_volume))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('VLC volume restored on exit: {0} ({1}%)'.format(self.actual_volume, int(100 * self.actual_volume / self.max_volume)))

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
        if msg == 'quit':
            self.process.terminate()
            self.process = None
        if ret_function:
            ret_function(response)
        return response

    def _thrededreq(self, msg, ret_function=None):
        threading.Thread(target=self._req, args=(msg,ret_function)).start()

    def _win_show_vlc_volume(self):
        #if self.win_show_vlc_volume_function:
        self._win_get_volume()
        pvol = int((self.actual_volume + 1) / self.max_volume * 100 * 2)
        if pvol > 0:
            avol = '[Vol: {}%] '.format(pvol)
            if self.show_volume and self.oldUserInput['Title']:
                self.outputStream.write(msg=avol + self.oldUserInput['Title'], counter='')
                self.threadUpdateTitle()

    def _win_get_volume(self):
        self._thrededreq('volume', self._get_volume_response)

    def _get_volume_response(self, msg):
        parts = msg.split('\r\n')
        for n in parts:
            if 'volume' in n:
                vol = n.split(': ')[-1].replace(' )', '')
                for n in ('.', ','):
                    ind = vol.find(n)
                    if ind > -1:
                        vol = vol[:ind]
                        break
                try:
                    self.actual_volume = int(vol)
                except ValueError:
                    logger.error('DE _get_volume_response: ValueError: vol = {}'.format(vol))
                    return
                logger.error('DE _get_volume_response: vol = {}'.format(vol))
                break
        if self.actual_volume == 0:
            self.muted = True
        else:
            self.muted = False
        #self.print_response(vol)

    def _win_volup(self):
        self._thrededreq('volup 1')

    def _win_voldown(self):
        self._thrededreq('voldown 1')

    def _win_set_volume(self, vol):
        ivol = int(vol)
        self._thrededreq('volume ' + str(ivol))
        self.actual_volume = ivol

    def _win_mute(self):
        self._win_get_volume()
        self._unmuted_volume = self.actual_volume
        self._thrededreq('volume 0')
        self.actual_volume = 0
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
    ret_player = None
    if logger.isEnabledFor(logging.INFO):
        logger.info('Probing available multimedia players...')
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info('Implemented players: ' +
                    ', '.join([player.PLAYER_NAME
                              for player in implementedPlayers]))

    if requested_player:
        req = requested_player.split(',')
        for r_player in req:
            if r_player == 'cvlc':
                r_player = 'vlc'
            for player in implementedPlayers:
                if player.PLAYER_NAME == r_player:
                    ret_player = check_player(player)
                    if ret_player is not None:
                        return ret_player
            if ret_player is None:
                if logger.isEnabledFor(logging.INFO):
                    logger.info('Requested player "{}" not supported'.format(r_player))
    else:
        for player in implementedPlayers:
            ret_player = check_player(player)
            if ret_player is not None:
                break
    return ret_player

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
