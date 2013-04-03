import subprocess
import threading
import os
import logging

logger = logging.getLogger(__name__)


class Player(object):
    """ Media player class. Playing is handled by mplayer """
    process = None

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
                subsystemOut = out.readline().decode("utf-8")
                if subsystemOut == '':
                    break
                subsystemOut = subsystemOut.strip()
                subsystemOut = subsystemOut.replace("\r", "").replace("\n", "")
                if (logger.isEnabledFor(logging.DEBUG)):
                    logger.debug("User input: {}".format(subsystemOut))
                self.outputStream.write(subsystemOut)
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
        """ send keystroke command to mplayer """

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
        """ exit pyradio (and kill mplayer instance) """

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


class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    PLAYER_CMD = "mplayer"

    def _buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        if playList:
            opts = [self.PLAYER_CMD, "-quiet", "-playlist", streamUrl]
        else:
            opts = [self.PLAYER_CMD, "-quiet", streamUrl]
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
        """ mute mplayer """

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
        """ exit pyradio (and kill mplayer instance) """
        self._sendCommand("shutdown\n")

    def volumeUp(self):
        """ increase mplayer's volume """
        self._sendCommand("volup\n")

    def volumeDown(self):
        """ decrease mplayer's volume """
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
