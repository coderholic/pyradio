import subprocess
import threading
import os
import logging
from os.path import expanduser

logger = logging.getLogger(__name__)


class Player(object):
    """ Media player class. Playing is handled by player sub classes """
    process = None

    volume = -1

    def __init__(self, outputStream):
        self.outputStream = outputStream

    def __del__(self):
        self.close()

    def updateStatus(self):
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread started.")
        try:
            out = self.process.stdout
            while(True):
                subsystemOut = out.readline().decode("utf-8", "ignore")
                if subsystemOut == '':
                    break
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace("\r", "").replace("\n", "")
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug("User input: {}".format(subsystemOut))
                self.outputStream.write(subsystemOut)
                if "Volume:" in subsystemOut:
                    self.volume = ''.join(c for c in subsystemOut if c.isdigit())
                    if (logger.isEnabledFor(logging.DEBUG)):
                        logger.debug("Read volume {}".format(self.volume))
        except:
            logger.error("Error in updateStatus thread.",
                         exc_info=True)
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread stopped.")

    def isPlaying(self):
        return bool(self.process)

    def play(self, streamUrl):
        """ use a multimedia player to play a stream """
        self.close()
        opts = []
        isPlayList = streamUrl.split("?")[0][-3:] in ['m3u', 'pls']
        opts = self._buildStartOpts(streamUrl, isPlayList)
        self.process = subprocess.Popen(opts, shell=False,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        t = threading.Thread(target=self.updateStatus, args=())
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
            except:
                msg = "Error when sending: {}"
                logger.error(msg.format(command).strip(),
                             exc_info=True)

    def close(self):
        """ exit pyradio (and kill player instance) """

        # First close the subprocess
        self._stop()

        # Here is fallback solution and cleanup
        if self.process is not None:
            os.kill(self.process.pid, 15)
            self.process.wait()
        self.process = None

    def _buildStartOpts(self, streamUrl, playList):
        pass

    def mute(self):
        pass

    def _stop(self):
        pass

    def volumeUp(self):
        pass

    def volumeDown(self):
        pass

class MpvPlayer(Player):
    """Implementation of Player object for MPV"""

    PLAYER_CMD = "mpv"

    """ USE_PROFILE
    -1 : not checked yet
     0 : do not use
     1 : use profile"""
    USE_PROFILE = -1

    """ True if profile comes from ~/.config/mpv/mpv.conf """
    PROFILE_FROM_USER = False

    if os.path.exists('/tmp/mpvsocket'):
        os.system("rm /tmp/mpvsocket");

    def save_mpv_volume(self):
        ret_string = "Volume already saved"
        if self.volume == -1:
            """ inform no change """
            return ret_string
        else:
            """ change volume """
            profile_found = False
            config_file = expanduser("~") + "/.config/mpv/mpv.conf"
            ret_string = "Volume saved: {}%".format(str(self.volume))
            new_profile_string="\n[pyradio]\nvolume={}\n"
            if os.path.exists(config_file):
                if self.PROFILE_FROM_USER:
                    with open(config_file, 'r') as c:
                        config_strings = c.readlines()
                    for i, a_line in enumerate(config_strings):
                        if not profile_found:
                            if "[pyradio]" in a_line:
                                profile_found = True
                        else:
                            if a_line.startswith("volume="):
                                config_strings[i]="volume=" + str(self.volume) + "\n"
                                break
                    try:
                        with open(config_file, "w") as c:
                            c.writelines(config_strings)
                    except EnvironmentError:
                        return "Error while saving volume"
                    self.volume = -1
            else:
                new_profile_string = "volume=100\n" + new_profile_string
            """ no user profile or user config file does not exist """
            if not profile_found:
                try:
                    with open(config_file, "a") as c:
                        c.write(new_profile_string.format(str(self.volume)))
                except EnvironmentError:
                    return "Error while saving volume"
            return ret_string

    def _configHasProfile(self):
        """ Checks if mpv config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        volume-max=300
        volume=50"""

        config_files = [expanduser("~") + "/.config/mpv/mpv.conf"]
        config_files.append("/etc/mpv/mpv.conf")
        for i, config_file in enumerate(config_files):
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

    def mute(self):
        """ mute mpv """
        os.system("echo 'cycle mute' | socat - /tmp/mpvsocket");

    def pause(self):
        """ pause streaming (if possible) """
        os.system("echo 'cycle pause' | socat - /tmp/mpvsocket");

    def _stop(self):
        """ exit pyradio (and kill mpv instance) """
        os.system("echo 'quit' | socat - /tmp/mpvsocket");
        os.system("rm /tmp/mpvsocket");

    def volumeUp(self):
        """ increase mpv's volume """
        os.system("echo 'cycle volume' | socat - /tmp/mpvsocket");

    def volumeDown(self):
        """ decrease mpv's volume """
        os.system("echo 'cycle volume down' | socat - /tmp/mpvsocket");


class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    PLAYER_CMD = "mplayer"

    """ USE_PROFILE
    -1 : not checked yet
     0 : do not use
     1 : use profile"""
    USE_PROFILE = -1

    """ True if profile comes from ~/.mplayer/config """
    PROFILE_FROM_USER = False

    def _configHasProfile(self):
        """ Checks if mplayer config has [pyradio] entry / profile.

        Profile example:

        [pyradio]
        softvol=yes
        volstep=2
        volume=28"""

        config_files = [expanduser("~") + "/.mplayer/config"]
        config_files.append("/etc/mplayer/mplayer.conf")
        for i, config_file in enumerate(config_files):
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

    def mute(self):
        """ mute mplayer """
        self._sendCommand("m")

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("p")

    def _stop(self):
        """ exit pyradio (and kill mplayer instance) """
        self._sendCommand("q")

    def volumeUp(self):
        """ increase mplayer's volume """
        self._sendCommand("*")

    def volumeDown(self):
        """ decrease mplayer's volume """
        self._sendCommand("/")


class VlcPlayer(Player):
    """Implementation of Player for VLC"""

    PLAYER_CMD = "cvlc"

    muted = False

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        opts = [self.PLAYER_CMD, "-Irc", "--quiet", streamUrl]
        return opts

    def mute(self):
        """ mute vlc """

        if not self.muted:
            self._sendCommand("volume 0\n")
            self.muted = True
        else:
            self._sendCommand("volume 256\n")
            self.muted = False

    def pause(self):
        """ pause streaming (if possible) """
        self._sendCommand("stop\n")

    def _stop(self):
        """ exit pyradio (and kill vlc instance) """
        self._sendCommand("shutdown\n")

    def volumeUp(self):
        """ increase vlc's volume """
        self._sendCommand("volup\n")

    def volumeDown(self):
        """ decrease vlc's volume """
        self._sendCommand("voldown\n")


def probePlayer():
    """ Probes the multimedia players which are available on the host
    system."""
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug("Probing available multimedia players...")
    implementedPlayers = Player.__subclasses__()
    if logger.isEnabledFor(logging.INFO):
        logger.info("Implemented players: " +
                    ", ".join([player.PLAYER_CMD
                              for player in implementedPlayers]))

    for player in implementedPlayers:
        try:
            p = subprocess.Popen([player.PLAYER_CMD, "--help"],
                                 stdout=subprocess.PIPE,
                                 stdin=subprocess.PIPE,
                                 shell=False)
            p.terminate()
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("{} supported.".format(str(player)))
            return player
        except OSError:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("{} not supported.".format(str(player)))
