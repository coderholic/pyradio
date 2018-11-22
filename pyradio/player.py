import subprocess
import threading
import os
import logging
from os.path import expanduser
from sys import platform
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
    icy_found = False

    """ make it possible to change volume but not show it """
    show_volume = True

    status_update_lock = threading.Lock()

    def __init__(self, outputStream):
        self.outputStream = outputStream

    def __del__(self):
        self.close()

    def save_volume(self):
        pass

    def _do_save_volume(self, config_string):
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

    def updateStatus(self, *args):
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread started.")
        try:
            out = self.process.stdout
            while(True):
                subsystemOut = out.readline().decode("utf-8", "ignore")
                if subsystemOut == '':
                    break
                if not self._is_accepted_input(subsystemOut):
                    continue
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace("\r", "").replace("\n", "")
                if self.oldUserInput['Input'] != subsystemOut:
                    if (logger.isEnabledFor(logging.DEBUG)):
                        logger.debug("User input: {}".format(subsystemOut))
                    self.oldUserInput['Input'] = subsystemOut
                    if self.volume_string in subsystemOut:
                        if self.oldUserInput['Volume'] != subsystemOut:
                            self.oldUserInput['Volume'] = subsystemOut
                            self.volume = ''.join(c for c in subsystemOut if c.isdigit())

                            # do this here, so that cvlc actual_volume gets updated
                            # this is done in _format_volume_string
                            string_to_show = self._format_volume_string(subsystemOut) + self._format_title_string(self.oldUserInput['Title'])

                            if self.show_volume:
                                self.outputStream.write(string_to_show, args[0])
                                self.threadUpdateTitle(args[0])
                    else:
                        # get all input before we get first icy-title
                        if (not self.icy_found):
                            self.oldUserInput['Title'] = subsystemOut
                        # once we get the first icy-title,
                        # get only icy-title entries
                        if self._is_icy_entry(subsystemOut):
                            self.oldUserInput['Title'] = subsystemOut
                            if not self.icy_found:
                                self.icy_found = True
                                self.threadUpdateTitle(args[0])

                        # some servers sends first icy-title too early; it gets overwritten once
                        # we get the first, so we block all but icy messages, after the first one
                        # is received (whenever we get an input, we print the previous icy message)
                        if self.icy_found:
                            subsystemOut = self.oldUserInput['Title']

                        # make sure title will not pop-up while Volume value is on
                        ok_to_display = False
                        if self.delay_thread is None:
                            ok_to_display = True
                        else:
                            if (not self.delay_thread.isAlive()):
                                ok_to_display = True
                        if ok_to_display:
                            string_to_show = self.title_prefix + self._format_title_string(subsystemOut)
                            self.outputStream.write(string_to_show, args[0])
        except:
            logger.error("Error in updateStatus thread.",
                         exc_info=True)
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread stopped.")

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
        for a_tokken in self.icy_tokkens:
            if a_string.startswith(a_tokken):
                return True
        return False

    def _format_title_string(self, title_string):
        return title_string

    def _format_volume_string(self, volume_string):
        return volume_string

    def isPlaying(self):
        return bool(self.process)

    def play(self, streamUrl):
        """ use a multimedia player to play a stream """
        self.close()
        self.oldUserInput = {'Input': '', 'Volume': '', 'Title': ''}
        self.icy_found = False
        self.muted = False
        self.show_volume = True
        self.title_prefix = ''
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts = self._buildStartOpts(streamUrl, isPlayList)
        self.process = subprocess.Popen(opts, shell=False,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        t = threading.Thread(target=self.updateStatus, args=(self.status_update_lock, ))
        t.start()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Player started")

    def _sendCommand(self, command):
        """ send keystroke command to player """

        if(self.process is not None):
            try:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug("Command: {}".format(command).strip())
                self.process.stdin.write(command.encode("utf-8"))
                self.process.stdin.flush()
            except:
                msg = "Error when sending: {}"
                logger.error(msg.format(command).strip(),
                             exc_info=True)

    def close(self):
        """ exit pyradio (and kill player instance) """

        # First close the subprocess
        self._stop()

        # Here is fallback solution and cleanup
        if self.delay_thread is not None:
            self.delay_thread.cancel()
        if self.process is not None:
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
        pass

    def _stop(self):
        pass

    def volumeUp(self):
        """ increase volume """
        if self.muted is not True:
            self._volume_up()

    def volumeDown(self):
        """ decrease volume """
        if self.muted is not True:
            self._volume_down()

    def _volume_up(self):
        pass

    def _volume_down(self):
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
    icy_tokkens = ('icy-title:', 'Exiting... (Quit)')

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

    if os.path.exists('/tmp/mpvsocket'):
        os.system("rm /tmp/mpvsocket");

    def save_volume(self):
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
                opts = [self.PLAYER_CMD, "--quiet", "--playlist", streamUrl, "--input-ipc-server=/tmp/mpvsocket"]
            else:
                opts = [self.PLAYER_CMD, "--quiet", "--playlist", streamUrl, "--input-unix-socket=/tmp/mpvsocket"]
        else:
            if newerMpv:
                opts = [self.PLAYER_CMD, "--quiet", streamUrl, "--input-ipc-server=/tmp/mpvsocket"]
            else:
                opts = [self.PLAYER_CMD, "--quiet", streamUrl, "--input-unix-socket=/tmp/mpvsocket"]
        if self.USE_PROFILE == -1:
            self.USE_PROFILE = self._configHasProfile()

        if self.USE_PROFILE == 1:
            opts.append("--profile=pyradio")
            if (logger.isEnabledFor(logging.DEBUG)):
                logger.debug("using profile [pyradio]")
        return opts

    def _mute(self):
        """ mute mpv """
        os.system("echo 'cycle mute' | socat - /tmp/mpvsocket 2>/dev/null");

    def pause(self):
        """ pause streaming (if possible) """
        os.system("echo 'cycle pause' | socat - /tmp/mpvsocket 2>/dev/null");

    def _stop(self):
        """ exit pyradio (and kill mpv instance) """
        os.system("echo 'quit' | socat - /tmp/mpvsocket 2>/dev/null");
        os.system("rm /tmp/mpvsocket");

    def _volume_up(self):
        """ increase mpv's volume """
        os.system("echo 'cycle volume' | socat - /tmp/mpvsocket 2>/dev/null");

    def _volume_down(self):
        """ decrease mpv's volume """
        os.system("echo 'cycle volume down' | socat - /tmp/mpvsocket 2>/dev/null");

    def _format_title_string(self, title_string):
        """ format mpv's title """
        return title_string.replace('icy-title: ', self.icy_title_prefix)

    def _format_volume_string(self, volume_string):
        """ format mplayer's volume """
        return '[' + volume_string[volume_string.find(self.volume_string):].replace('ume', '')+'] '

class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    PLAYER_CMD = "mplayer"

    """ items of this tupple are considered icy-title
        and get displayed after first icy-title is received """
    icy_tokkens = ('ICY Info:', 'Exiting... (Quit)')

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
        config_files[0] = os.path.join(os.getenv('APPDATA'), "mplayer", "config")
    else:
        # linux, freebsd, etc.
        config_files.append("/etc/mplayer/mplayer.conf")

    def save_volume(self):
        return self._do_save_volume("[pyradio]\nvolstep=1\nvolume={}\n")

    def _configHasProfile(self):
        """ Checks if mplayer config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        volstep=2
        volume=28"""

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
            return tmp[:tmp.find("';")]
        else:
            return title_string

    def _format_volume_string(self, volume_string):
        """ format mplayer's volume """
        return '[' + volume_string[volume_string.find(self.volume_string):].replace(' %','%').replace('ume', '')+'] '

class VlcPlayer(Player):
    """Implementation of Player for VLC"""

    PLAYER_CMD = "cvlc"

    """ items of this tupple are considered icy-title
        and get displayed after first icy-title is received """
    icy_tokkens = ('Icy-Title=', 'Exiting... (Quit)')

    muted = False

    """ String to denote volume change """
    volume_string = '( audio volume: '

    """ vlc reports volume in values 0..512 """
    actual_volume = -1
    max_volume = 512

    def save_volume(self):
        pass

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        #opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
        opts = [self.PLAYER_CMD, "-Irc", "-vv", streamUrl]
        return opts

    def _mute(self):
        """ mute vlc """

        if not self.muted:
            if self.actual_volume == -1:
                # read actual_volume
                self.show_volume = False
                self._sendCommand("voldown 0\n")
            self._sendCommand("volume 0\n")
        else:
            self._sendCommand("volume {}\n".format(self.actual_volume))

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("stop\n")

    def _stop(self):
        """ exit pyradio (and kill vlc instance) """
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
        if not self.icy_found:
            ret_string = ret_string.split('] ')[-1]
        return ret_string

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

def probePlayer(requested_player=''):
    """ Probes the multimedia players which are available on the host
    system."""
    ret_player = None
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Probing available multimedia players...")
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info("Implemented players: " +
                    ", ".join([player.PLAYER_CMD
                              for player in implementedPlayers]))

    for player in implementedPlayers:
        if requested_player == '':
            ret_player = check_player(player)
            if ret_player is not None:
                break
        else:
            if player.PLAYER_CMD == requested_player:
                ret_player = check_player(player)

    if ret_player is None:
        if requested_player == '':
            logger.error("No supported player found. Terminating...")
        else:
            logger.error('Requested player "' + requested_player + '" not supported. Terminating...')
        exit(1)
    return ret_player

def check_player(a_player):
    try:
        p = subprocess.Popen([a_player.PLAYER_CMD, "--help"],
                             stdout=subprocess.PIPE,
                             stdin=subprocess.PIPE,
                             shell=False)
        p.terminate()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("{} supported.".format(str(a_player)))
        return a_player
    except OSError:
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("{} not supported.".format(str(a_player)))
        return None
