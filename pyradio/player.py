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
                         stack_info=True)
        if (logger.isEnabledFor(logging.DEBUG)):
            logger.debug("updateStatus thread stopped.")

    def isPlaying(self):
        return bool(self.process)

    def play(self, streamUrl):
        """ use mplayer to play a stream """
        self.close()
        opts = []
        if streamUrl.split("?")[0][-3:] in ['m3u', 'pls']:
            opts = self.buildStartOpts(streamUrl, True)
        else:
            opts = self.buildStartOpts(streamUrl, False)
        self.process = subprocess.Popen(opts, shell=False,
                                        stdout=subprocess.PIPE,
                                        stdin=subprocess.PIPE,
                                        stderr=subprocess.STDOUT)
        t = threading.Thread(target=self.updateStatus, args=())
        t.start()

    def buildStartOpts(self, streamUrl, playList):
        pass

    def mute(self):
        pass

    def close(self):
        pass

    def volumeUp(self):
        pass

    def volumeDown(self):
        pass


class MpPlayer(Player):
    """Implementation of Player object for MPlayer"""

    def buildStartOpts(self, streamUrl, playList=False):
        """ Builds the options to pass to subprocess."""
        if playList:
            opts = ["mplayer", "-quiet", "-playlist", streamUrl]
        else:
            opts = ["mplayer", "-quiet", streamUrl]
        return opts

    def __sendCommand(self, command):
        """ send keystroke command to mplayer """
        if(self.process is not None):
            try:
                self.process.stdin.write(command)
            except:
                pass

    def mute(self):
        """ mute mplayer """
        self.__sendCommand("m")

    def pause(self):
        """ pause streaming (if possible) """
        self.__sendCommand("p")

    def close(self):
        """ exit pyradio (and kill mplayer instance) """
        self.__sendCommand("q")
        if self.process is not None:
            os.kill(self.process.pid, 15)
            self.process.wait()
        self.process = None

    def volumeUp(self):
        """ increase mplayer's volume """
        self.__sendCommand("*")

    def volumeDown(self):
        """ decrease mplayer's volume """
        self.__sendCommand("/")
