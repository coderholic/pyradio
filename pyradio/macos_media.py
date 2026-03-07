import os
import sys
import json
import queue
import socket
import threading
import subprocess
import logging

from .os_media_base import MediaControls


logger = logging.getLogger("pyradio.macos_media")

HELPER_MODULE = "pyradio.macos_nowplaying_helper"
SOCKET_PATH = "/tmp/pyradio-nowplaying-helper.sock"


class MacOSMediaController(MediaControls):

    def __init__(self, identity="PyRadio", instance_name=None):
        MediaControls.__init__(self, identity, instance_name)

        self._proc = None
        self._cmdq = queue.Queue()
        self._reader_thread = None
        self._running = False
        self._socket_path = SOCKET_PATH

    # ----------------------------------------------------------
    # lifecycle
    # ----------------------------------------------------------

    def start(self):
        try:
            if self._running:
                return

            cmd = [
                sys.executable,
                "-m",
                HELPER_MODULE,
                "run",
                "--icon",
                self._get_default_icon()
            ]

            self._proc = subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1
            )

            self._reader_thread = threading.Thread(
                target=self._reader_loop,
                name="macos-helper-reader",
                daemon=True
            )
            self._reader_thread.start()

            if not self._wait_for_helper_socket():
                self._running = False
                return

            self._running = True

        except Exception as e:
            logger.error("MEDIA: Failed starting macOS helper: %s", e)

    def stop(self):
        try:
            if not self._running:
                return

            self._send_command({"type": "shutdown"})

            try:
                self._proc.wait(timeout=3)
            except Exception:
                try:
                    self._proc.terminate()
                except Exception as e:
                    logger.error("MEDIA: Failed terminating helper: %s", e)

            self._running = False

        except Exception as e:
            logger.error("MEDIA: Failed stopping macOS helper: %s", e)

    # ----------------------------------------------------------
    # poll bridge
    # ----------------------------------------------------------

    def poll(self, enabled):
        try:
            while True:
                msg = self._cmdq.get_nowait()

                if msg.get("type") != "cmd":
                    continue

                name = msg.get("name")

                if name == "play" and self.cb_play:
                    self.cb_play()

                elif name == "stop" and self.cb_stop:
                    self.cb_stop()

                elif name == "next" and self.cb_next:
                    self.cb_next()

                elif name == "prev" and self.cb_prev:
                    self.cb_prev()

                elif name == "playpause" and self.cb_playpause:
                    self.cb_playpause()

                elif name == "set_volume" and self.cb_set_volume:
                    self.cb_set_volume(msg.get("value"))

        except queue.Empty:
            pass
        except Exception as e:
            logger.error("MEDIA: poll dispatch failed: %s", e)

    # ----------------------------------------------------------
    # updates from PyRadio
    # ----------------------------------------------------------

    def _wait_for_helper_socket(self, timeout=3.0):
        import time

        end_time = time.time() + timeout

        while time.time() < end_time:
            if self._proc is not None and self._proc.poll() is not None:
                logger.error("MEDIA: macOS helper exited during startup")
                return False

            if os.path.exists(self._socket_path):
                try:
                    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                    sock.connect(self._socket_path)
                    sock.close()
                    return True
                except Exception:
                    pass

            time.sleep(0.05)

        logger.error("MEDIA: timed out waiting for helper socket readiness")
        return False

    def update_playback(self, playing):
        self._send_command({
            "type": "playback",
            "playing": bool(playing)
        })

    def update_nav_caps(self, can_next, can_prev):
        self._send_command({
            "type": "nav_caps",
            "can_next": bool(can_next),
            "can_prev": bool(can_prev)
        })

    def update_metadata(
        self,
        trackid,
        title,
        artist,
        album,
        url=None,
        art_url=None
    ):
        self._send_command({
            "type": "metadata",
            "trackid": trackid,
            "title": title,
            "artist": artist,
            "album": album,
            "url": url,
            "art_url": art_url
        })

    # ----------------------------------------------------------

    def make_trackid(self, *parts):
        try:
            out = []

            for part in parts:
                if part is None:
                    continue

                text = str(part).strip()
                if text:
                    out.append(text)

            if not out:
                return "pyradio:track:unknown"

            return "pyradio:track:" + "|".join(out)

        except Exception as e:
            logger.error("MEDIA: Failed creating track id: %s", e)
            return "pyradio:track:unknown"

    # ----------------------------------------------------------
    # IPC
    # ----------------------------------------------------------

    def _send_command(self, payload):
        import errno
        import time

        if not self._running:
            return

        last_error = None

        for _ in range(10):
            try:
                if self._proc is not None and self._proc.poll() is not None:
                    logger.error("MEDIA: helper process is not running")
                    return

                sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                sock.connect(self._socket_path)

                data = json.dumps(payload).encode("utf-8") + b"\n"
                sock.sendall(data)
                sock.close()
                return

            except OSError as e:
                last_error = e

                if e.errno in (2, 61):
                    time.sleep(0.05)
                    continue

                logger.error("MEDIA: IPC send failed: %s", e)
                return

            except Exception as e:
                logger.error("MEDIA: IPC send failed: %s", e)
                return

        if last_error is not None:
            logger.error("MEDIA: IPC send failed after retries: %s", last_error)

    # ----------------------------------------------------------
    # reader
    # ----------------------------------------------------------

    def _reader_loop(self):
        try:
            while True:
                line = self._proc.stdout.readline()

                if not line:
                    break

                line = line.strip()

                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except Exception:
                    continue

                self._cmdq.put(msg)

        except Exception as e:
            logger.error("MEDIA: Helper reader loop failed: %s", e)

    # ----------------------------------------------------------

    def _get_default_icon(self):
        try:
            base = os.path.dirname(os.path.abspath(__file__))
            return os.path.join(base, "icons", "pyradio.png")
        except Exception as e:
            logger.error("MEDIA: Failed resolving default icon: %s", e)
            return ""
