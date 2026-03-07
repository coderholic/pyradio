import os
import sys
import json
import queue
import socket
import argparse
import logging
import threading

from objc import super

from Cocoa import (
    NSApplication,
    NSApplicationActivationPolicyAccessory,
    NSImage,
    NSObject
)

from Foundation import NSTimer
from PyObjCTools import AppHelper

from MediaPlayer import (
    MPNowPlayingInfoCenter,
    MPRemoteCommandCenter,
    MPNowPlayingPlaybackStatePlaying,
    MPNowPlayingPlaybackStatePaused,
    MPMediaItemPropertyTitle,
    MPMediaItemPropertyArtist,
    MPMediaItemPropertyAlbumTitle,
    MPMediaItemPropertyArtwork,
    MPNowPlayingInfoPropertyPlaybackRate,
    MPMediaItemArtwork
)

from urllib.parse import urlparse, unquote

try:
    from MediaPlayer import MPNowPlayingPlaybackStateStopped
except Exception:
    MPNowPlayingPlaybackStateStopped = None


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("pyradio-macos-helper")


class HelperIPCServer(threading.Thread):

    def __init__(self, socket_path, incoming_queue, stop_event):
        threading.Thread.__init__(self, name="helper-ipc-server", daemon=True)
        self._socket_path = socket_path
        self._incoming_queue = incoming_queue
        self._stop_event = stop_event
        self._server = None

    def run(self):
        try:
            if os.path.exists(self._socket_path):
                try:
                    os.unlink(self._socket_path)
                except Exception as e:
                    logger.error("MEDIA: Failed removing stale socket path: %s", e)
                    return

            self._server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server.bind(self._socket_path)
            self._server.listen(5)
            self._server.settimeout(0.5)

            logger.info("MEDIA: IPC server listening on %s", self._socket_path)

            while not self._stop_event.is_set():
                try:
                    conn, _ = self._server.accept()
                except socket.timeout:
                    continue
                except Exception as e:
                    if not self._stop_event.is_set():
                        logger.error("MEDIA: IPC accept failed: %s", e)
                    continue

                try:
                    self._handle_connection(conn)
                except Exception as e:
                    logger.error("MEDIA: IPC connection handling failed: %s", e)
                finally:
                    try:
                        conn.close()
                    except Exception as e:
                        logger.error("MEDIA: IPC connection close failed: %s", e)

        except Exception as e:
            logger.error("MEDIA: IPC server failed: %s", e)

        finally:
            self.close()

    def _handle_connection(self, conn):
        data = b""

        while not self._stop_event.is_set():
            try:
                chunk = conn.recv(4096)
            except Exception as e:
                logger.error("MEDIA: IPC recv failed: %s", e)
                return

            if not chunk:
                break

            data += chunk

            while b"\n" in data:
                raw_line, data = data.split(b"\n", 1)
                line = raw_line.decode("utf-8", "replace").strip()

                if not line:
                    continue

                try:
                    msg = json.loads(line)
                except Exception as e:
                    logger.error("MEDIA: Failed decoding IPC json line: %s", e)
                    continue

                self._incoming_queue.put(msg)

    def close(self):
        if self._server is not None:
            try:
                self._server.close()
            except Exception as e:
                logger.error("MEDIA: Failed closing IPC server socket: %s", e)
            self._server = None

        if os.path.exists(self._socket_path):
            try:
                os.unlink(self._socket_path)
            except Exception as e:
                logger.error("MEDIA: Failed unlinking IPC socket path: %s", e)


class HelperAppDelegate(NSObject):

    def init(self):
        self = super().init()
        if self is None:
            return None

        self._incoming_queue = None
        self._stop_event = None
        self._socket_path = None
        self._icon_path = None

        self._center = None
        self._command_center = None
        self._image = None
        self._artwork = None
        self._default_image = None
        self._default_artwork = None
        self._timer = None
        self._shutdown_started = False

        self._title = None
        self._artist = None
        self._album = None
        self._trackid = None
        self._url = None
        self._art_url = None
        self._is_playing = False
        self._can_next = True
        self._can_prev = True
        self._has_published_state = False

        self._primed = False

        return self

    def configureWithQueue_stopEvent_socketPath_title_artist_album_iconPath_(
        self,
        incoming_queue,
        stop_event,
        socket_path,
        title,
        artist,
        album,
        icon_path
    ):
        self._incoming_queue = incoming_queue
        self._stop_event = stop_event
        self._socket_path = socket_path
        self._icon_path = icon_path

    def applicationDidFinishLaunching_(self, notification):
        try:
            logger.info("MEDIA: Helper app finished launching")
            self._setup_now_playing()
            self._install_timer()
            logger.info("MEDIA: Helper is active")
        except Exception as e:
            logger.error("MEDIA: Helper launch failed: %s", e)
            self._begin_shutdown()

    def _prime_now_playing_if_needed(self):
        if self._primed:
            return

        if self._center is None:
            return

        try:
            self._center.setPlaybackState_(MPNowPlayingPlaybackStatePlaying)

            if MPNowPlayingPlaybackStateStopped is not None:
                if self._is_playing:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStatePlaying)
                else:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStateStopped)
            else:
                if self._is_playing:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStatePlaying)
                else:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStatePaused)

            self._primed = True
            logger.info("MEDIA: Primed now playing state")

        except Exception as e:
            logger.error("MEDIA: Failed priming now playing state: %s", e)


    def _setup_now_playing(self):
        self._center = MPNowPlayingInfoCenter.defaultCenter()
        self._command_center = MPRemoteCommandCenter.sharedCommandCenter()

        if self._icon_path:
            self._default_image = NSImage.alloc().initWithContentsOfFile_(self._icon_path)
            self._default_artwork = self._make_artwork_from_image(self._default_image)

        try:
            self._command_center.playCommand().removeTarget_(None)
            self._command_center.pauseCommand().removeTarget_(None)
            self._command_center.stopCommand().removeTarget_(None)
            self._command_center.togglePlayPauseCommand().removeTarget_(None)
            self._command_center.nextTrackCommand().removeTarget_(None)
            self._command_center.previousTrackCommand().removeTarget_(None)
        except Exception as e:
            logger.error("MEDIA: Failed clearing previous command targets: %s", e)

        self._command_center.playCommand().setEnabled_(True)
        self._command_center.pauseCommand().setEnabled_(True)
        self._command_center.stopCommand().setEnabled_(True)
        self._command_center.togglePlayPauseCommand().setEnabled_(True)
        self._command_center.nextTrackCommand().setEnabled_(self._can_next)
        self._command_center.previousTrackCommand().setEnabled_(self._can_prev)

        self._command_center.playCommand().addTargetWithHandler_(self._play_handler)
        self._command_center.pauseCommand().addTargetWithHandler_(self._pause_handler)
        self._command_center.stopCommand().addTargetWithHandler_(self._stop_handler)
        self._command_center.togglePlayPauseCommand().addTargetWithHandler_(self._toggle_handler)
        self._command_center.nextTrackCommand().addTargetWithHandler_(self._next_handler)
        self._command_center.previousTrackCommand().addTargetWithHandler_(self._prev_handler)

        self._set_playback_state(False)

        logger.info("MEDIA: Native command center initialized")

    def _install_timer(self):
        try:
            self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.2,
                self,
                "tick:",
                None,
                True
            )
            logger.info("MEDIA: Helper timer installed")
        except Exception as e:
            logger.error("MEDIA: Failed installing helper timer: %s", e)

    def tick_(self, timer):
        try:
            self._drain_incoming_queue()
        except Exception as e:
            logger.error("MEDIA: Timer drain failed: %s", e)

        if self._stop_event is not None and self._stop_event.is_set():
            self._begin_shutdown()

    def _drain_incoming_queue(self):
        while True:
            try:
                msg = self._incoming_queue.get_nowait()
            except queue.Empty:
                return
            except Exception as e:
                logger.error("MEDIA: Incoming queue read failed: %s", e)
                return

            self._apply_command(msg)

    def _make_artwork_from_image(self, image):
        if image is None:
            return None

        try:
            def artwork_handler(size):
                return image

            return MPMediaItemArtwork.alloc().initWithBoundsSize_requestHandler_(
                image.size(),
                artwork_handler
            )
        except Exception as e:
            logger.error("MEDIA: Failed creating artwork from image: %s", e)
            return None

    def _artwork_from_art_url(self, art_url):
        if not art_url:
            self._image = self._default_image
            self._artwork = self._default_artwork
            return self._default_artwork

        try:
            if art_url.startswith("file://"):
                parsed = urlparse(art_url)
                path = unquote(parsed.path)
            else:
                path = art_url

            if not path:
                self._image = self._default_image
                self._artwork = self._default_artwork
                return self._default_artwork

            image = NSImage.alloc().initWithContentsOfFile_(path)
            if image is None:
                logger.error("MEDIA: Failed loading artwork image from path: %s", path)
                self._image = self._default_image
                self._artwork = self._default_artwork
                return self._default_artwork

            self._image = image
            self._artwork = self._make_artwork_from_image(image)

            if self._artwork is None:
                self._image = self._default_image
                self._artwork = self._default_artwork
                return self._default_artwork

            return self._artwork

        except Exception as e:
            logger.error("MEDIA: Failed resolving artwork from art_url: %s", e)
            self._image = self._default_image
            self._artwork = self._default_artwork
            return self._default_artwork

    def _set_playback_state(self, playing):
        self._is_playing = bool(playing)

        if self._center is None:
            return

        try:
            if self._is_playing:
                self._center.setPlaybackState_(MPNowPlayingPlaybackStatePlaying)
            else:
                if MPNowPlayingPlaybackStateStopped is not None:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStateStopped)
                else:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStatePaused)
        except Exception as e:
            logger.error("MEDIA: Failed setting playback state: %s", e)

    def _apply_now_playing_info(self):
        if self._center is None:
            return

        try:
            info = {
                MPMediaItemPropertyTitle: self._title or "",
                MPMediaItemPropertyArtist: self._artist or "",
                MPMediaItemPropertyAlbumTitle: self._album or "",
                MPNowPlayingInfoPropertyPlaybackRate: 1.0 if self._is_playing else 0.0
            }

            artwork = self._artwork_from_art_url(self._art_url)
            if artwork is not None:
                info[MPMediaItemPropertyArtwork] = artwork

            self._center.setNowPlayingInfo_(info)
            self._has_published_state = True

            self._prime_now_playing_if_needed()
            self._set_playback_state(self._is_playing)

            logger.info("MEDIA: Applied now playing info")

        except Exception as e:
            logger.error("MEDIA: Failed applying now playing info: %s", e)

    def _apply_nav_caps(self):
        if self._command_center is None:
            return

        try:
            self._command_center.playCommand().setEnabled_(True)
            self._command_center.pauseCommand().setEnabled_(True)
            self._command_center.stopCommand().setEnabled_(True)
            self._command_center.togglePlayPauseCommand().setEnabled_(True)
            self._command_center.nextTrackCommand().setEnabled_(self._can_next)
            self._command_center.previousTrackCommand().setEnabled_(self._can_prev)

            logger.info(
                "MEDIA: Applied nav caps can_next=%s can_prev=%s",
                self._can_next,
                self._can_prev
            )
        except Exception as e:
            logger.error("MEDIA: Failed applying nav caps: %s", e)

    def _emit_command(self, name, value=None):
        try:
            msg = {
                "type": "cmd",
                "name": name
            }

            if value is not None:
                msg["value"] = value

            sys.stdout.write(json.dumps(msg) + "\n")
            sys.stdout.flush()

            logger.info("MEDIA: Emitted command to parent: %s", name)

        except Exception as e:
            logger.error("MEDIA: Failed emitting command to parent: %s", e)

    def _apply_command(self, msg):
        if not isinstance(msg, dict):
            logger.error("MEDIA: Ignoring invalid IPC message")
            return

        msg_type = msg.get("type")

        if msg_type == "shutdown":
            logger.info("MEDIA: Received shutdown command")
            if self._stop_event is not None:
                self._stop_event.set()
            return

        if msg_type == "playback":
            playing = bool(msg.get("playing"))
            try:
                self._set_playback_state(playing)

                if self._has_published_state:
                    self._apply_now_playing_info()

                logger.info("MEDIA: Applied playback command: playing=%s", playing)
            except Exception as e:
                logger.error("MEDIA: Failed applying playback command: %s", e)
            return

        if msg_type == "nav_caps":
            try:
                self._can_next = bool(msg.get("can_next", True))
                self._can_prev = bool(msg.get("can_prev", True))
                self._apply_nav_caps()
            except Exception as e:
                logger.error("MEDIA: Failed applying nav caps command: %s", e)
            return

        if msg_type == "metadata":
            try:
                self._trackid = msg.get("trackid")
                self._title = msg.get("title")
                self._artist = msg.get("artist")
                self._album = msg.get("album")
                self._url = msg.get("url")
                self._art_url = msg.get("art_url")

                self._apply_now_playing_info()

                logger.info("MEDIA: Applied metadata command")
            except Exception as e:
                logger.error("MEDIA: Failed applying metadata command: %s", e)
            return

        logger.error("MEDIA: Unknown IPC command type: %s", msg_type)

    def _begin_shutdown(self):
        if self._shutdown_started:
            return

        self._shutdown_started = True

        try:
            if self._timer is not None:
                self._timer.invalidate()
                self._timer = None
        except Exception as e:
            logger.error("MEDIA: Failed invalidating helper timer: %s", e)

        try:
            self._cleanup_now_playing()
        except Exception as e:
            logger.error("MEDIA: Cleanup before shutdown failed: %s", e)

        try:
            NSApplication.sharedApplication().stop_(None)
        except Exception as e:
            logger.error("MEDIA: Failed stopping NSApplication: %s", e)

        try:
            AppHelper.stopEventLoop()
        except Exception as e:
            logger.error("MEDIA: Failed stopping helper event loop: %s", e)

    def _cleanup_now_playing(self):
        if self._center is not None:
            try:
                self._center.setNowPlayingInfo_(None)
            except Exception as e:
                logger.error("MEDIA: Failed clearing now playing info: %s", e)

            try:
                if MPNowPlayingPlaybackStateStopped is not None:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStateStopped)
                else:
                    self._center.setPlaybackState_(MPNowPlayingPlaybackStatePaused)
            except Exception as e:
                logger.error("MEDIA: Failed setting stopped playback state during cleanup: %s", e)

        if self._command_center is not None:
            try:
                self._command_center.playCommand().removeTarget_(None)
                self._command_center.pauseCommand().removeTarget_(None)
                self._command_center.stopCommand().removeTarget_(None)
                self._command_center.togglePlayPauseCommand().removeTarget_(None)
                self._command_center.nextTrackCommand().removeTarget_(None)
                self._command_center.previousTrackCommand().removeTarget_(None)
            except Exception as e:
                logger.error("MEDIA: Failed removing command targets during cleanup: %s", e)

        logger.info("MEDIA: Native media state cleaned up")

    def _play_handler(self, event):
        logger.info("MEDIA: Remote play command received")
        self._emit_command("play")
        return 0

    def _pause_handler(self, event):
        logger.info("MEDIA: Remote pause command received")
        self._emit_command("stop")
        return 0

    def _stop_handler(self, event):
        logger.info("MEDIA: Remote stop command received")
        self._emit_command("stop")
        return 0

    def _toggle_handler(self, event):
        logger.info("MEDIA: Remote toggle command received")
        self._emit_command("playpause")
        return 0

    def _next_handler(self, event):
        logger.info("MEDIA: Remote next command received")
        self._emit_command("next")
        return 0

    def _prev_handler(self, event):
        logger.info("MEDIA: Remote previous command received")
        self._emit_command("prev")
        return 0


def send_command(socket_path, payload):
    sock = None

    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        data = json.dumps(payload).encode("utf-8") + b"\n"
        sock.sendall(data)
        logger.info("MEDIA: Command sent: %s", payload.get("type"))
        return 0

    except Exception as e:
        logger.error("MEDIA: Failed sending command: %s", e)
        return 1

    finally:
        if sock is not None:
            try:
                sock.close()
            except Exception as e:
                logger.error("MEDIA: Failed closing client socket: %s", e)


def run_helper(args):
    incoming_queue = queue.Queue()
    stop_event = threading.Event()

    server = HelperIPCServer(args.socket_path, incoming_queue, stop_event)
    server.start()

    try:
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        delegate = HelperAppDelegate.alloc().init()
        delegate.configureWithQueue_stopEvent_socketPath_title_artist_album_iconPath_(
            incoming_queue,
            stop_event,
            args.socket_path,
            args.title,
            args.artist,
            args.album,
            args.icon
        )
        app.setDelegate_(delegate)

        logger.info("MEDIA: Starting helper event loop")
        AppHelper.runEventLoop()
        logger.info("MEDIA: Helper event loop exited")
        return 0

    except Exception as e:
        logger.error("MEDIA: Helper run failed: %s", e)
        stop_event.set()
        return 1

    finally:
        try:
            server.close()
        except Exception as e:
            logger.error("MEDIA: Helper server cleanup failed: %s", e)


def build_arg_parser():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="mode")

    run_parser = subparsers.add_parser("run")
    run_parser.add_argument("--socket-path", default="/tmp/pyradio-nowplaying-helper.sock")
    run_parser.add_argument("--icon", required=True)
    run_parser.add_argument("--title", default="PyRadio Test Track")
    run_parser.add_argument("--artist", default="PyRadio")
    run_parser.add_argument("--album", default="Now Playing Helper Test")

    shutdown_parser = subparsers.add_parser("shutdown")
    shutdown_parser.add_argument("--socket-path", default="/tmp/pyradio-nowplaying-helper.sock")

    playback_parser = subparsers.add_parser("playback")
    playback_parser.add_argument("--socket-path", default="/tmp/pyradio-nowplaying-helper.sock")
    playback_parser.add_argument("--playing", choices=("true", "false"), required=True)

    metadata_parser = subparsers.add_parser("metadata")
    metadata_parser.add_argument("--socket-path", default="/tmp/pyradio-nowplaying-helper.sock")
    metadata_parser.add_argument("--title", default="PyRadio Test Track")
    metadata_parser.add_argument("--artist", default="PyRadio")
    metadata_parser.add_argument("--album", default="Now Playing Helper Test")

    return parser


def main():
    parser = build_arg_parser()
    args = parser.parse_args()

    if args.mode == "run":
        code = run_helper(args)
        sys.exit(code)

    if args.mode == "shutdown":
        code = send_command(
            args.socket_path,
            {"type": "shutdown"}
        )
        sys.exit(code)

    if args.mode == "playback":
        code = send_command(
            args.socket_path,
            {"type": "playback", "playing": args.playing == "true"}
        )
        sys.exit(code)

    if args.mode == "metadata":
        code = send_command(
            args.socket_path,
            {
                "type": "metadata",
                "title": args.title,
                "artist": args.artist,
                "album": args.album
            }
        )
        sys.exit(code)

    parser.print_help()
    sys.exit(1)


if __name__ == "__main__":
    main()
