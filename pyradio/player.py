# -*- coding: utf-8 -*-
import subprocess
import threading
import os
import logging
from os.path import expanduser
from sys import platform, version_info
from sys import exit

logger = logging.getLogger(__name__)

class Player(object):
    """ Media player class. Playing is handled by player sub classes """
    process = None

    icy_title_prefix = 'Title: '
    title_prefix = ''

    # Input:   old user input     - used to early suppress output
    #                               in case of consecutive equal messages
    # Volume:  old volume input   - used to suppress output (and firing of delay thread)
    #                               in case of consecutive equal volume messages
    # Title:   old title input    - printed by delay thread
    oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}

    """ volume percentage """
    volume = -1

    delay_thread = None
    connection_timeout_thread = None

    """ make it possible to change volume but not show it """
    show_volume = True

    muted = False

    status_update_lock = threading.Lock()

    ctrl_c_pressed = False

    """ When found in station transmission, playback is on """
    _playback_token_tuple = ( 'AO: [', )

    playback_is_on = False

    _station_encoding = 'utf-8'

    def __init__(self, outputStream, playback_timeout, playback_timeout_handler):
        self.outputStream = outputStream
        try:
            self.playback_timeout = int(playback_timeout)
        except:
            self.playback_timeout = 10
        self.playback_timeout_handler = playback_timeout_handler

    def __del__(self):
        self.close()

    def save_volume(self):
        pass

    def _do_save_volume(self, config_string):
        if not self.config_files:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Volume not daved!!! (config file not found!!!)')
            return 'Volume not saved!!!'
        ret_strings = ('Volume: already saved...',
                    'Volume: {}% saved',
                    'Volume: {}% NOT saved (Error writing file)')
        log_strings = ('Volume is -1. Aborting...',
                    'Volume is {}%. Saving...',
                    'Error saving profile "{}"')
        if self.volume == -1:
            """ inform no change """
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug(log_strings[0])
            return ret_strings[0]
        else:
            """ change volume """
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug(log_strings[1].format(self.volume))
            profile_found = False
            config_file = self.config_files[0]
            ret_string = ret_strings[1].format(str(self.volume))
            if os.path.exists(config_file):
                if platform.startswith('win'):
                    with open(config_file, 'r') as c_file:
                        config_string = c_file.read()
                    if "volume=" in config_string:
                        vol = config_string.splitlines()
                        for i, v_string in enumerate(vol):
                            if v_string.startswith('volume'):
                                vol[i] = 'volume={}'.format(self.volume)
                                break
                        config_string = '\n'.join(vol)
                    else:
                        out = config_string + 'volume={}'.format(self.volume)
                        config_string = out
                    try:
                        with open(config_file, "w") as c_file:
                            c_file.write(config_string)
                    except:
                        if (logger.isEnabledFor(logging.DEBUG)):
                            logger.debug(log_strings[2].format(config_file))
                        return ret_strings[2].format(str(self.volume))
                        self.volume = -1
                else:
                    if self.PROFILE_FROM_USER:
                        with open(config_file, 'r') as c_file:
                            config_string = c_file.read()

                        if "[pyradio]" in config_string:
                            profile_found = True

                            """ split on [pyradio]
                            last item has our options """
                            sections = config_string.split("[pyradio]")

                            """ split at [ - i.e. isolate consecutive profiles
                            first item has pyradio options """
                            py_section = sections[-1].split("[")

                            """ split to lines in order to get '^volume=' """
                            py_options = py_section[0].split("\n")

                            """ replace volume line """
                            vol_set = False
                            for i, opt in enumerate(py_options):
                                if opt.startswith("volume="):
                                    py_options[i]="volume=" + str(self.volume)
                                    vol_set = True
                                    break
                            """ or add it if it does not exist """
                            if not vol_set:
                                py_options.append("volume=" + str(self.volume))

                            """ join lines together in py_section's first item """
                            py_section[0] = "\n".join(py_options)

                            """ join consecutive profiles (if exist)
                            in last item of sections """
                            if len(py_section) > 1:
                                sections[-1] = "[".join(py_section)
                            else:
                                sections[-1] = py_section[0]

                            """ finally get the string back together """
                            config_string = "[pyradio]".join(sections)

                        try:
                            with open(config_file, "w") as c_file:
                                c_file.write(config_string)
                        except EnvironmentError:
                            if (logger.isEnabledFor(logging.DEBUG)):
                                logger.debug(log_strings[2].format(config_file))
                            return ret_strings[2].format(str(self.volume))
                        self.volume = -1

                    """ no user profile or user config file does not exist """
                    if not profile_found:
                        if not os.path.isdir(os.path.dirname(config_file)):
                            try:
                                os.mkdir(os.path.dirname(config_file))
                            except OSError:
                                if (logger.isEnabledFor(logging.DEBUG)):
                                    logger.debug(log_strings[2].format(config_file))
                                return ret_strings[2].format(str(self.volume))
                        new_profile_string = "volume=100\n\n" + config_string
                        try:
                            with open(config_file, "a") as c_file:
                                c_file.write(new_profile_string.format(str(self.volume)))
                        except EnvironmentError:
                            if (logger.isEnabledFor(logging.DEBUG)):
                                logger.debug(log_strings[2].format(config_file))
                            return ret_strings[2].format(str(self.volume))
                        self.volume = -1
                        self.PROFILE_FROM_USER = True
            return ret_string

    def _is_in_playback_token(self, a_string):
        for a_token in self._playback_token_tuple:
            if a_token in a_string:
                return True
        return False

    def updateStatus(self, *args):
        has_error = False
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread started.")
        try:
            out = self.process.stdout
            while(True):
                subsystemOutRaw = out.readline()
                try:
                    subsystemOut = subsystemOutRaw.decode(self._station_encoding, "replace")
                except:
                    subsystemOut = subsystemOutRaw.decode("utf-8", "replace")
                if subsystemOut == '':
                    break
                if not self._is_accepted_input(subsystemOut):
                    continue
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace("\r", "").replace("\n", "")
                if self.oldUserInput['Input'] != subsystemOut:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        if version_info < (3, 0):
                            disp = subsystemOut.encode('utf-8', 'replace').strip()
                            logger.debug("User input: {}".format(disp))
                        else:
                            logger.debug("User input: {}".format(subsystemOut))
                    self.oldUserInput['Input'] = subsystemOut
                    if self.volume_string in subsystemOut:
                        #logger.error("***** volume")
                        if self.oldUserInput['Volume'] != subsystemOut:
                            self.oldUserInput['Volume'] = subsystemOut
                            self.volume = ''.join(c for c in subsystemOut if c.isdigit())

                            # IMPORTANT: do this here, so that cvlc actual_volume
                            # gets updated in _format_volume_string
                            string_to_show = self._format_volume_string(subsystemOut) + self._format_title_string(self.oldUserInput['Title'])

                            if self.show_volume and self.oldUserInput['Title']:
                                self.outputStream.write(string_to_show, args[0])
                                self.threadUpdateTitle(args[0])
                    elif self._is_in_playback_token(subsystemOut):
                        if self.connection_timeout_thread is not None:
                            self.connection_timeout_thread.cancel()
                        if (logger.isEnabledFor(logging.INFO)):
                            logger.info('start of playback detected')
                        if self.outputStream.last_written_string.startswith('Connecting '):
                            new_input = self.outputStream.last_written_string.replace('Connecting to', 'Playing')
                            self.outputStream.write(new_input, args[0])
                            if self.oldUserInput['Title'] == '':
                                self.oldUserInput['Input'] = new_input
                            else:
                                self.oldUserInput['Title'] = new_input
                        self.playback_is_on = True
                    elif self._is_icy_entry(subsystemOut):
                        #logger.error("***** icy_entry")
                        title = self._format_title_string(subsystemOut)
                        if title[len(self.icy_title_prefix):].strip():
                            self.oldUserInput['Title'] = subsystemOut
                            # make sure title will not pop-up while Volume value is on
                            ok_to_display = False
                            if self.delay_thread is None:
                                ok_to_display = True
                            else:
                                if (not self.delay_thread.isAlive()):
                                    ok_to_display = True
                            if ok_to_display:
                                string_to_show = self.title_prefix + title
                                self.outputStream.write(string_to_show, args[0])
                        else:
                            if (logger.isEnabledFor(logging.INFO)):
                                logger.info('Icy-Title is NOT valid')
                    else:
                        if self.oldUserInput['Title'] == '':
                            self.oldUserInput['Title'] = 'Connecting to: "{}"'.format(self.name)
                            if (logger.isEnabledFor(logging.INFO)):
                                logger.info('Connecting to: "{}"'.format(self.name))
                            self.outputStream.write(self.oldUserInput['Title'])
        except:
            has_error = True
            if logger.isEnabledFor(logging.ERROR):
                logger.error("Error in updateStatus thread.", exc_info=True)
            return
        if (logger.isEnabledFor(logging.INFO)):
            logger.info("updateStatus thread stopped.")

    def threadUpdateTitle(self, a_lock, delay=1):
        if self.oldUserInput['Title'] != '':
            if self.delay_thread is not None:
                if self.delay_thread.isAlive():
                    self.delay_thread.cancel()
            try:
               self.delay_thread = threading.Timer(delay, self.updateTitle,  [ self.outputStream, self.title_prefix + self._format_title_string(self.oldUserInput['Title']), a_lock ] )
               self.delay_thread.start()
            except:
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug("delay thread start failed")

    def updateTitle(self, *arg, **karg):
        arg[0].write(arg[1], arg[2])

    def _is_icy_entry(self, a_string):
        #logger.error("**** a_string = {}".format(a_string))
        for a_tokken in self.icy_tokkens:
            if a_tokken in a_string:
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

    def play(self, name, streamUrl, encoding = ''):
        """ use a multimedia player to play a stream """
        self.close()
        self.name = name
        self.oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}
        self.muted = False
        self.show_volume = True
        self.title_prefix = ''
        self.playback_is_on = False
        self.outputStream.write('Station: "{}"'.format(name), self.status_update_lock)
        if logger.isEnabledFor(logging.INFO):
            logger.info('Selected Station: "{}"'.format(name))
        if encoding:
            self._station_encoding = encoding
        else:
            self._station_encoding = 'utf-8'
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts = self._buildStartOpts(streamUrl, isPlayList)
        self.process = subprocess.Popen(opts, shell=False,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        t = threading.Thread(target=self.updateStatus, args=(self.status_update_lock, ))
        t.start()
        # start playback check timer thread
        try:
            self.connection_timeout_thread = threading.Timer(self.playback_timeout, self.playback_timeout_handler)
            self.connection_timeout_thread.start()
        except:
            self.connection_timeout_thread = None
            if (logger.isEnabledFor(logging.ERROR)):
                logger.error("playback detection thread start failed")
        if logger.isEnabledFor(logging.INFO):
            logger.info("Player started")

    def _sendCommand(self, command):
        """ send keystroke command to player """

        if(self.process is not None):
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Command: {}".format(command).strip())
                self.process.stdin.write(command.encode('utf-8', 'replace'))
                self.process.stdin.flush()
            except:
                msg = "Error when sending: {}"
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(msg.format(command).strip(), exc_info=True)

    def close(self):
        """ exit pyradio (and kill player instance) """

        self._no_mute_on_stop_playback()

        # First close the subprocess
        self._stop()

        # Here is fallback solution and cleanup
        if self.connection_timeout_thread is not None:
            self.connection_timeout_thread.cancel()
        if self.delay_thread is not None:
            self.delay_thread.cancel()
        if self.process is not None:
            if platform.startswith('win'):
                try:
                    #subprocess.check_output("Taskkill /PID %d /F" % self.process.pid)
                    #subprocess.Popen(["Taskkill", "/PID", "{}".format(self.process.pid), "/F"])
                    subprocess.Call(['Taskkill', '/PID', '{}'.format(self.process.pid), '/F'])
                except:
                    pass
            else:
                os.kill(self.process.pid, 15)
                self.process.wait()
            self.process = None

    def _buildStartOpts(self, streamUrl, playList):
        pass

    def toggleMute(self):
        """ mute / unmute player """

        if not self.muted:
            self._mute()
            if self.delay_thread is not None:
                self.delay_thread.cancel()
            self.title_prefix = '[Muted] '
            self.muted = True
            self.show_volume = False
        else:
            self._mute()
            self.title_prefix = ''
            self.muted = False
            self.show_volume = True
        if self.oldUserInput['Title'] == '':
            self.outputStream.write(self.title_prefix + self._format_title_string(self.oldUserInput['Input']))
        else:
            self.outputStream.write(self.title_prefix + self._format_title_string(self.oldUserInput['Title']))

    def _mute(self):
        """ to be implemented on subclasses """
        pass

    def _stop(self):
        pass

    def _get_volume(self):
        """ get volume, if player can report it """
        pass

    def volumeUp(self):
        """ increase volume """
        if self.muted is not True:
            self._volume_up()

    def _volume_up(self):
        """ to be implemented on subclasses """
        pass

    def volumeDown(self):
        """ decrease volume """
        if self.muted is not True:
            self._volume_down()

    def _volume_down(self):
        """ to be implemented on subclasses """
        pass

    def _no_mute_on_stop_playback(self):
        """ make sure player does not stop muted, i.e. volume=0

            Currently implemented for vlc only."""
        pass

    def _is_accepted_input(self, input_string):
        """ subclasses are able to reject input messages
            thus limiting message procesing.
            By default, all messages are accepted.

            Currently implemented for vlc only."""
        return True

class MpvPlayer(Player):
    """Implementation of Player object for MPV"""

    PLAYER_CMD = "mpv"

    """ items of this tupple are considered icy-title
        and get displayed after first icy-title is received """
    icy_tokkens = ('icy-title: ', )

    """ USE_PROFILE
    -1 : not checked yet
     0 : do not use
     1 : use profile"""
    USE_PROFILE = -1

    """ True if profile comes from ~/.config/mpv/mpv.conf """
    PROFILE_FROM_USER = False

    """ String to denote volume change """
    volume_string = 'Volume: '
    config_files = [expanduser("~") + "/.config/mpv/mpv.conf"]

    if platform.startswith('darwin'):
        config_files.append("/usr/local/etc/mpv/mpv.conf")
    elif platform.startswith('win'):
        config_files[0] = os.path.join(os.getenv('APPDATA'), "mpv", "mpv.conf")
    else:
        # linux, freebsd, etc.
        config_files.append("/etc/mpv/mpv.conf")

    mpvsocket = '/tmp/mpvsocket.{}'.format(os.getpid())
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('mpv socket is "{}"'.format(self.mpvsocket))
    if os.path.exists(mpvsocket):
        os.system("rm " + mpvsocket + " 2>/dev/null");

    def save_volume(self):
        """ Saving Volume in Windows does not work;
            Profiles not supported... """
        return self._do_save_volume("[pyradio]\nvolume={}\n")

    def _configHasProfile(self):
        """ Checks if mpv config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        volume-max=300
        volume=50"""

        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file) as f:
                    config_string = f.read()
                if "[pyradio]" in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                    return 1
        return 0

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""

        """ Test for newer MPV versions as it supports different IPC flags. """
        p = subprocess.Popen([self.PLAYER_CMD, "--input-ipc-server"], stdout=subprocess.PIPE, stdin=subprocess.PIPE, shell=False)
        out = p.communicate()
        if "not found" not in str(out[0]):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("--input-ipc-server is supported.")
            newerMpv = 1;
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("--input-ipc-server is not supported.")
            newerMpv = 0;

        if playList:
            if newerMpv:
                opts = [self.PLAYER_CMD, "--quiet", "--playlist", streamUrl, "--input-ipc-server=" + self.mpvsocket]
            else:
                opts = [self.PLAYER_CMD, "--quiet", "--playlist", streamUrl, "--input-unix-socket=" + self.mpvsocket]
        else:
            if newerMpv:
                opts = [self.PLAYER_CMD, "--quiet", streamUrl, "--input-ipc-server=" + self.mpvsocket]
            else:
                opts = [self.PLAYER_CMD, "--quiet", streamUrl, "--input-unix-socket=" + self.mpvsocket]
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

        if self.USE_PROFILE == 1:
            opts.append("--profile=pyradio")
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug("using profile [pyradio]")
        return opts

    def _mute(self):
        """ mute mpv """
        os.system("echo 'cycle mute' | socat - " + self.mpvsocket + " 2>/dev/null");

    def pause(self):
        """ pause streaming (if possible) """
        os.system("echo 'cycle pause' | socat - " + self.mpvsocket + " 2>/dev/null");

    def _stop(self):
        """ exit pyradio (and kill mpv instance) """
        os.system("echo 'quit' | socat - " + self.mpvsocket + " 2>/dev/null");
        os.system("rm " + self.mpvsocket + " 2>/dev/null");

    def _volume_up(self):
        """ increase mpv's volume """
        os.system("echo 'cycle volume' | socat - " + self.mpvsocket + " 2>/dev/null");

    def _volume_down(self):
        """ decrease mpv's volume """
        os.system("echo 'cycle volume down' | socat - " + self.mpvsocket + " 2>/dev/null");

    def _format_title_string(self, title_string):
        """ format mpv's title """
        return self._title_string_format_text_tag(title_string.replace(self.icy_tokkens[0], self.icy_title_prefix))

    def _format_volume_string(self, volume_string):
        """ format mplayer's volume """
        return '[' + volume_string[volume_string.find(self.volume_string):].replace('ume', '')+'] '

class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    PLAYER_CMD = "mplayer"

    """ items of this tupple are considered icy-title
        and get displayed after first icy-title is received """
    icy_tokkens = ('ICY Info:', )

    """ USE_PROFILE
    -1 : not checked yet
     0 : do not use
     1 : use profile"""
    USE_PROFILE = -1

    """ True if profile comes from ~/.mplayer/config """
    PROFILE_FROM_USER = False

    """ String to denote volume change """
    volume_string = 'Volume: '

    config_files = [expanduser("~") + "/.mplayer/config"]
    if platform.startswith('darwin'):
        config_files.append("/usr/local/etc/mplayer/mplayer.conf")
    elif platform.startswith('win'):
        if os.path.exists('C:\\mplayer\\mplayer.exe'):
            config_files[0] = 'C:\\mplayer\mplayer\\config'
        elif os.path.exists(os.path.join(os.getenv('USERPROFILE'), "mplayer", "mplayer.exe")):
            config_files[0] = os.path.join(os.getenv('USERPROFILE'), "mplayer", "mplayer", "config")
        else:
            config_files = []
    else:
        # linux, freebsd, etc.
        config_files.append("/etc/mplayer/mplayer.conf")

    def save_volume(self):
        if platform.startswith('win'):
            return self._do_save_volume("volume={}\r\n")
            return 0
        return self._do_save_volume("[pyradio]\nvolstep=1\nvolume={}\n")

    def _configHasProfile(self):
        """ Checks if mplayer config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        volstep=2
        volume=28"""

        """ Existing mplayer Windows implementations do not support profiles """
        if platform.startswith('win'):
            return 0
        for i, config_file in enumerate(self.config_files):
            if os.path.exists(config_file):
                with open(config_file) as f:
                    config_string = f.read()
                if "[pyradio]" in config_string:
                    if i == 0:
                        self.PROFILE_FROM_USER = True
                    return 1
        return 0

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        if playList:
            opts = [self.PLAYER_CMD, "-quiet", "-playlist", streamUrl]
        else:
            opts = [self.PLAYER_CMD, "-quiet", streamUrl]
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

        if self.USE_PROFILE == 1:
            opts.append("-profile")
            opts.append("pyradio")
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug("using profile [pyradio]")
        return opts

    def _mute(self):
        """ mute mplayer """
        self._sendCommand("m")

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("p")

    def _stop(self):
        """ exit pyradio (and kill mplayer instance) """
        self._sendCommand("q")

    def _volume_up(self):
        """ increase mplayer's volume """
        self._sendCommand("*")

    def _volume_down(self):
        """ decrease mplayer's volume """
        self._sendCommand("/")

    def _format_title_string(self, title_string):
        """ format mplayer's title """
        if "StreamTitle='" in title_string:
            tmp = title_string[title_string.find("StreamTitle='"):].replace("StreamTitle='", self.icy_title_prefix)
            ret_string = tmp[:tmp.find("';")]
        else:
            ret_string = title_string
        if '"artist":"' in ret_string:
            """ work on format:
                ICY Info: START_SONG='{"artist":"Clelia Cafiero","title":"M. Mussorgsky-Quadri di un'esposizione"}';
                Fund on "ClassicaViva Web Radio: Classical"
            """
            ret_string = self.icy_title_prefix + ret_string[ret_string.find('"artist":')+10:].replace('","title":"', ' - ').replace('"}\';', '')
        return self._title_string_format_text_tag(ret_string)

    def _format_volume_string(self, volume_string):
        """ format mplayer's volume """
        return '[' + volume_string[volume_string.find(self.volume_string):].replace(' %','%').replace('ume', '')+'] '

class VlcPlayer(Player):
    """Implementation of Player for VLC"""

    PLAYER_CMD = "cvlc"

    """ items of this tupple are considered icy-title
        and get displayed after first icy-title is received """
    icy_tokkens = ('New Icy-Title=', )

    muted = False

    """ String to denote volume change """
    volume_string = '( audio volume: '

    """ vlc reports volume in values 0..512 """
    actual_volume = -1
    max_volume = 512

    """ When found in station transmission, playback is on """
    _playback_token_tuple = ('Content-Type: audio', )

    def save_volume(self):
        pass

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        #opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
        opts = [self.PLAYER_CMD, "-Irc", "-vv", streamUrl]
        return opts

    def _mute(self):
        """ mute vlc """

        if self.muted:
            self._sendCommand("volume {}\n".format(self.actual_volume))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC unmuted: {0} ({1}%)'.format(self.actual_volume, int(100 * self.actual_volume / self.max_volume)))
        else:
            if self.actual_volume == -1:
                self._get_volume()
            self._sendCommand("volume 0\n")
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('VLC muted: 0 (0%)')

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("stop\n")

    def _stop(self):
        """ exit pyradio (and kill vlc instance) """
        if self.ctrl_c_pressed:
            return
        self._sendCommand("shutdown\n")

    def _volume_up(self):
        """ increase vlc's volume """
        self._sendCommand("volup\n")

    def _volume_down(self):
        """ decrease vlc's volume """
        self._sendCommand("voldown\n")

    def _format_volume_string(self, volume_string):
        """ format vlc's volume """
        self.actual_volume = int(volume_string.split(self.volume_string)[1].split(',')[0].split()[0])
        return '[Vol: {}%] '.format(int(100 * self.actual_volume / self.max_volume))

    def _format_title_string(self, title_string):
        """ format vlc's title """
        sp = title_string.split(self.icy_tokkens[0])
        if sp[0] == title_string:
            ret_string = title_string
        else:
            ret_string = self.icy_title_prefix + sp[1]
        return self._title_string_format_text_tag(ret_string)

    def _is_accepted_input(self, input_string):
        """ vlc input filtering """
        ret = False
        accept_filter = (self.volume_string, "http stream debug: ")
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
        """ get vlc's actual_volume"""
        self.show_volume = False
        self._sendCommand("voldown 0\n")

    def _no_mute_on_stop_playback(self):
        """ make sure vlc does not stop muted """
        if self.ctrl_c_pressed:
            return
        if self.isPlaying():
            if self.actual_volume == -1:
                self._get_volume()
                while self.actual_volume == -1:
                    pass
            if self.actual_volume == 0:
                self.actual_volume = int(self.max_volume*0.25)
                self._sendCommand('volume {}\n'.format(self.actual_volume))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Unmuting VLC on exit: {} (25%)'.format(self.actual_volume))
            elif self.muted:
                if self.actual_volume > 0:
                    self._sendCommand('volume {}\n'.format(self.actual_volume))
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('VLC volume restored on exit: {0} ({1}%)'.format(self.actual_volume, int(100 * self.actual_volume / self.max_volume)))

            self.show_volume = True

def probePlayer(requested_player=''):
    """ Probes the multimedia players which are available on the host
    system."""
    ret_player = None
    if logger.isEnabledFor(logging.INFO):
        logger.info("Probing available multimedia players...")
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info("Implemented players: " +
                    ", ".join([player.PLAYER_CMD
                              for player in implementedPlayers]))

    if requested_player:
        req = requested_player.split(',')
        for r_player in req:
            if r_player == 'vlc':
                r_player = 'cvlc'
            for player in implementedPlayers:
                if player.PLAYER_CMD == r_player:
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
        p = subprocess.Popen([a_player.PLAYER_CMD, "--help"],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             shell=False)
        p.terminate()

        # for mpv to work, socat is required...
        if a_player.PLAYER_CMD == 'mpv':
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("mpv found... Checking for socat...")
            p = subprocess.Popen(['socat', "-h"],
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 shell=False)
            p.terminate()

        if logger.isEnabledFor(logging.INFO):
            logger.info("{} supported.".format(str(a_player)))
        return a_player
    except OSError:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("{} not supported.".format(str(a_player)))
        return None
