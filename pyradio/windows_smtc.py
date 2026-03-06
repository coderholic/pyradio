# windows_smtc_winrt.py
#
# Windows SMTC backend for PyRadio using PyWinRT (winrt-*) + MediaPlayer.
#
# This follows the exact same control model as pyradio_mpris.py:
# - STA thread: owns WinRT objects, receives state updates from state_queue
# - Main thread (curses): owns the real player and executes commands
# - Communication:
#     STA thread -> main thread: cmd_queue  (PLAY/STOP/PAUSE/NEXT/PREV/PLAYPAUSE)
#     main thread -> STA thread: state_queue (PlaybackStatus/Caps/Metadata, plus Volume which is ignored)
#
# Main loop integration point:
#     c = getch()
#     if c == -1:
#         smtc.poll(enabled)   # drains cmd_queue; applies debounced volume; sends updates to STA thread
#         continue
#
# Constraints:
# - Python 3.8+
# - No typing hints
# - Comments in English
# - All exceptions -> logger.error(...) (NO print, NO logger.exception)

import ctypes
import threading
import queue
import time
import traceback
import logging
import asyncio
import os
import urllib.parse

try:
    import ctypes.wintypes as wintypes
except Exception:
    wintypes = None

from .os_media_base import MediaControls

logger = logging.getLogger(__name__)

# --- COM/WinRT bootstrap (STA thread) ---

COINIT_APARTMENTTHREADED = 0x2

try:
    ole32 = ctypes.windll.ole32
    combase = ctypes.windll.combase
    user32 = ctypes.windll.user32
except Exception:
    ole32 = None
    combase = None
    user32 = None


def _log_error(msg):
    try:
        tb = traceback.format_exc()
        if tb and "NoneType: None" not in tb:
            logger.error("%s\n%s", msg, tb)
        else:
            logger.error("%s", msg)
    except Exception:
        pass


def _coinit_sta():
    try:
        if not ole32:
            return -1
        hr = ole32.CoInitializeEx(None, COINIT_APARTMENTTHREADED)
        return int(hr)
    except Exception:
        _log_error("SMTC-WINRT: CoInitializeEx failed")
        return -1


def _couninit():
    try:
        if ole32:
            ole32.CoUninitialize()
    except Exception:
        _log_error("SMTC-WINRT: CoUninitialize failed")


def _roinit():
    # RO_INIT_SINGLETHREADED = 0
    try:
        if not combase:
            return -1
        combase.RoInitialize.argtypes = [ctypes.c_int]
        combase.RoInitialize.restype = ctypes.c_long
        hr = combase.RoInitialize(0)
        return int(hr)
    except Exception:
        _log_error("SMTC-WINRT: RoInitialize failed")
        return -1


def _rouninit():
    try:
        if combase:
            combase.RoUninitialize()
    except Exception:
        _log_error("SMTC-WINRT: RoUninitialize failed")


def _pump_win_messages_once():
    # Minimal message pumping on STA.
    # Some WinRT event delivery can depend on it in desktop apps.
    try:
        if not user32 or not wintypes:
            return
        msg = wintypes.MSG()
        PM_REMOVE = 0x0001
        while user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_REMOVE):
            user32.TranslateMessage(ctypes.byref(msg))
            user32.DispatchMessageW(ctypes.byref(msg))
    except Exception:
        _log_error("SMTC-WINRT: message pump failed")


# --------------------------
# STA thread runner (WinRT)
# --------------------------

class _SMTCWinRTThread(object):
    def __init__(self, cmd_queue, state_queue):
        self.cmdq = cmd_queue
        self.stateq = state_queue

        self._thread = None
        self._stop = threading.Event()
        self._ready = threading.Event()

        # WinRT objects (STA thread only)
        self._player = None
        self._smtc = None
        self._updater = None
        self._media = None
        self._storage = None
        self._streams = None

        # Event token best-effort
        self._button_token = None

        # Ignore OS commands while connecting
        self._ignore_commands = True

        # Cached state to reduce churn
        self._last_title = None
        self._last_artist = None
        self._last_status = 'Stopped'
        self._last_can_next = True
        self._last_can_prev = True

        # Cached thumbnail path (absolute local file path)
        self._last_thumb = None

        # Async loop for WinRT async APIs (STA thread only)
        self._loop = None

    def start(self):
        try:
            if self._thread and self._thread.is_alive():
                return True
            self._stop.clear()
            self._ready.clear()
            self._thread = threading.Thread(target=self._run, name="pyradio-smtc-winrt", daemon=False)
            self._thread.start()
            self._ready.wait(5.0)
            return self._ready.is_set()
        except Exception:
            _log_error("SMTC-WINRT: thread start failed")
            return False

    def stop(self):
        try:
            self._stop.set()
            if self._thread and self._thread.is_alive():
                self._thread.join()
            self._thread = None
        except Exception:
            _log_error("SMTC-WINRT: thread stop failed")

    def set_ignore_commands(self, value):
        try:
            self._ignore_commands = True if value else False
        except Exception:
            _log_error("SMTC-WINRT: set_ignore_commands failed")

    def _run(self):
        try:
            _coinit_sta()
            _roinit()

            # Import WinRT namespaces on STA thread
            try:
                import winrt.windows.media as media
                import winrt.windows.storage as storage
                import winrt.windows.storage.streams as streams
                from winrt.windows.media.playback import MediaPlayer
                self._media = media
                self._storage = storage
                self._streams = streams

                # Create an event loop for WinRT async operations on this STA thread.
                try:
                    self._loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(self._loop)
                except Exception:
                    _log_error("SMTC-WINRT: asyncio loop init failed")
                    self._loop = None
            except Exception:
                _log_error("SMTC-WINRT: import winrt namespaces failed")
                self._ready.set()
                return

            # Create MediaPlayer and SMTC
            try:
                self._player = MediaPlayer()
                self._smtc = self._player.system_media_transport_controls
                self._updater = self._smtc.display_updater

                # Enable SMTC + base buttons
                self._smtc.is_enabled = True
                self._smtc.is_play_enabled = True
                self._smtc.is_pause_enabled = True
                self._smtc.is_stop_enabled = True

                # Nav caps (default false; updated by stateq)
                self._smtc.is_next_enabled = False
                self._smtc.is_previous_enabled = False

                # Hook buttons -> cmd_queue
                self._try_hook_buttons()

            except Exception:
                _log_error("SMTC-WINRT: MediaPlayer/SMTC init failed")

            # Signal ready even if partial
            self._ready.set()

            # STA loop: consume state updates
            while not self._stop.is_set():
                did_work = False

                # Coalesce updates: drain queue and keep last value per key.
                pending = {}

                for _ in range(256):
                    try:
                        changed = self.stateq.get_nowait()
                    except queue.Empty:
                        changed = None
                    if not changed:
                        break

                    did_work = True

                    # Merge dict updates; last write wins.
                    try:
                        for k in changed:
                            pending[k] = changed.get(k)
                    except Exception:
                        # If changed is not a dict for any reason, ignore it.
                        pass

                if pending:
                    try:
                        self._apply_changed(pending)
                    except Exception:
                        _log_error("SMTC-WINRT: apply_changed failed")

                _pump_win_messages_once()
                if not did_work:
                    time.sleep(0.01)


        except Exception:
            _log_error("SMTC-WINRT: STA thread crashed")
            try:
                self._ready.set()
            except Exception:
                pass
        finally:
            try:
                self._cleanup()
            except Exception:
                _log_error("SMTC-WINRT: cleanup failed")
            try:
                _rouninit()
            except Exception:
                _log_error("SMTC-WINRT: RoUninitialize failed")
            try:
                _couninit()
            except Exception:
                _log_error("SMTC-WINRT: CoUninitialize failed")

    def _try_hook_buttons(self):
        try:
            if not self._smtc or not self._media:
                return False
            media = self._media

            def _on_button(sender, args):
                try:
                    if self._ignore_commands:
                        return

                    btn = args.button
                    cmd = None

                    if btn == media.SystemMediaTransportControlsButton.PLAY:
                        cmd = "PLAY"
                    elif btn == media.SystemMediaTransportControlsButton.PAUSE:
                        cmd = "STOP"
                        # cmd = "PAUSE"
                    elif btn == media.SystemMediaTransportControlsButton.STOP:
                        cmd = "STOP"
                    elif btn == media.SystemMediaTransportControlsButton.NEXT:
                        cmd = "NEXT"
                    elif btn == media.SystemMediaTransportControlsButton.PREVIOUS:
                        cmd = "PREV"
                    elif btn == media.SystemMediaTransportControlsButton.PLAY_PAUSE:
                        cmd = "PLAYPAUSE"

                    if not cmd:
                        return

                    try:
                        self.cmdq.put_nowait((cmd, None))
                    except Exception:
                        # Never block STA thread
                        pass

                except Exception:
                    _log_error("SMTC-WINRT: button handler failed")

            # Prefer token-based add/remove
            tok = None
            try:
                tok = self._smtc.add_button_pressed(_on_button)
            except Exception:
                tok = None

            if tok is not None:
                self._button_token = tok
                return True

            # Fallback pattern if supported by projection
            try:
                self._smtc.button_pressed += _on_button
                self._button_token = None
                return True
            except Exception:
                _log_error("SMTC-WINRT: ButtonPressed hook failed")
                return False

        except Exception:
            _log_error("SMTC-WINRT: try_hook_buttons failed")
            return False


    def _normalize_thumb_path(self, value):
        # Accept absolute local path or file:// URL.
        # Returns "" if value is unusable.
        try:
            if not value:
                return ""
            v = str(value)
            if v.startswith("file://"):
                # file:///C:/... or file://C:/...
                v = v[7:]
                if v.startswith("/"):
                    # file:///C:/ -> /C:/ ; strip the leading slash
                    if len(v) > 2 and v[2] == ":":
                        v = v[1:]
                v = urllib.parse.unquote(v)
            v = v.strip().strip('"').strip("'")
            if not v:
                return ""
            # Only support absolute paths.
            if not os.path.isabs(v):
                return ""
            return v
        except Exception:
            _log_error("SMTC-WINRT: normalize_thumb_path failed")
            return ""

    def _load_thumb_stream_ref(self, abs_path):
        # Convert absolute file path to RandomAccessStreamReference (STA thread only).
        # Returns None on failure.
        _log_error("SMTC-WINRT: thumb start")
        try:
            if not abs_path:
                _log_error("SMTC-WINRT: Error 1")
                return None
            if not self._storage or not self._streams:
                _log_error("SMTC-WINRT: Error 2")
                return None
            if not self._loop:
                _log_error("SMTC-WINRT: Error 3")
                return None
            if not os.path.exists(abs_path):
                _log_error("SMTC-WINRT: Error 4")
                return None
            _log_error("SMTC-WINRT: thumb before async")
            async def _get_ref():
                f = await self._storage.StorageFile.get_file_from_path_async(abs_path)
                return self._streams.RandomAccessStreamReference.create_from_file(f)
            _log_error("SMTC-WINRT: Sending thumb")
            try:
                return self._loop.run_until_complete(_get_ref())
            except Exception:
                _log_error("SMTC-WINRT: load thumbnail stream failed")
                return None

        except Exception:
            _log_error("SMTC-WINRT: load_thumb_stream_ref failed")
            return None

    def _apply_changed(self, changed):
        # Expected keys based on MediaControls:
        #   PlaybackStatus: "Playing"/"Stopped"
        #   CanGoNext: bool
        #   CanGoPrevious: bool
        #   Volume: float 0..1   (SMTC does not own system volume; ignored)
        #   Metadata: dict (MPRIS-like or simplified)
        try:
            if not self._smtc:
                return

            media = self._media

            if "CanGoNext" in changed:
                v = True if changed.get("CanGoNext") else False
                logger.debug('SMTC-WINRT: \n\n')
                logger.debug(f'SMTC-WINRT: {self._last_can_next = } -/- {v = }')
                if v != self._last_can_next:
                    self._last_can_next = v
                    try:
                        self._smtc.is_next_enabled = v
                        logger.debug('SMTC-WINRT: CanGoNext updated\n\n')
                    except Exception:
                        _log_error("SMTC-WINRT: set is_next_enabled failed")

            if "CanGoPrevious" in changed:
                v = True if changed.get("CanGoPrevious") else False
                logger.debug('SMTC-WINRT: \n\n')
                logger.debug(f'SMTC-WINRT: {self._last_can_prev = } -/- {v = }')
                if v != self._last_can_prev:
                    self._last_can_prev = v
                    try:
                        self._smtc.is_previous_enabled = v
                        logger.debug('SMTC-WINRT: CanGoPrevious updated\n\n')
                    except Exception:
                        _log_error("SMTC-WINRT: set is_previous_enabled failed")

            if "PlaybackStatus" in changed:
                logger.debug('SMTC-WINRT: \n\n')
                st = str(changed.get("PlaybackStatus") or "")
                logger.debug(f'SMTC-WINRT: {self._last_status = } -/- {st= }')
                if st != self._last_status:
                    self._last_status = st
                    try:
                        if st == "Playing":
                            self._smtc.playback_status = media.MediaPlaybackStatus.PLAYING
                            logger.debug('SMTC-WINRT: PlaybackStatus PLAYING updated\n\n')
                        elif st == "Paused":
                            self._smtc.playback_status = media.MediaPlaybackStatus.PAUSED
                            logger.debug('SMTC-WINRT: PlaybackStatus PAUSED updated\n\n')
                        else:
                            self._smtc.playback_status = media.MediaPlaybackStatus.STOPPED
                            logger.debug('SMTC-WINRT: PlaybackStatus STOPPED updated\n\n')
                    except Exception:
                        _log_error("SMTC-WINRT: set playback_status failed")

            if "Metadata" in changed:
                md = changed.get("Metadata") or {}

                # Accept both:
                # - simplified: {"title": "...", "artist": "..."}
                # - mpris-like: {"xesam:title": "...", "xesam:artist": ["..."], ...}
                title = ""
                artist = ""

                try:
                    if "title" in md or "artist" in md:
                        title = md.get("title") or ""
                        artist = md.get("artist") or ""
                        playlist = md.get("album") or ""
                    else:
                        title = md.get("xesam:title") or ""
                        a = md.get("xesam:artist")
                        playlist = md.get("xesam:album") or ""
                        if isinstance(a, list) and a:
                            artist = str(a[0] or "")
                        else:
                            artist = ""
                except Exception:
                    title = ""
                    artist = ""
                # Thumbnail support (local absolute file path).
                # Accept md['thumbnail'] or md['mpris:artUrl'] (file path or file:// URL).
                thumb = ""
                try:
                    if "thumbnail" in md:
                        thumb = md.get("thumbnail") or ""
                    elif "mpris:artUrl" in md:
                        thumb = md.get("mpris:artUrl") or ""
                except Exception:
                    thumb = ""

                thumb_path = self._normalize_thumb_path(thumb)
                logger.debug(f'SMTC-WINRT: {thumb_path = }')

                logger.debug('SMTC-WINRT: \n\n')
                logger.debug(f'SMTC-WINRT: {title = } -/- {self._last_title = }')
                logger.debug(f'SMTC-WINRT: {artist = } -/- {self._last_artist = }')
                meta_changed = ((title != self._last_title) or (artist != self._last_artist) or (thumb_path != (self._last_thumb or "")))
                if meta_changed:
                    self._last_title = title
                    self._last_artist = artist
                    try:
                        if self._updater:
                            self._updater.type = media.MediaPlaybackType.MUSIC
                            props = self._updater.music_properties
                            props.title = title
                            props.artist = artist
                            props.album_title = playlist

                            # Apply thumbnail only when it changes (expensive async work).
                            try:
                                if thumb_path != (self._last_thumb or ""):
                                    self._last_thumb = thumb_path
                                    _log_error(f"SMTC-WINRT: thumbnail final {thumb_path = }")
                                    if not thumb_path:
                                        self._updater.thumbnail = None
                                        _log_error("SMTC-WINRT: thumbnail is None")
                                    else:
                                        ref = self._load_thumb_stream_ref(thumb_path)
                                        _log_error(f"SMTC-WINRT: thumbnail {ref = }")
                                        if ref is not None:
                                            self._updater.thumbnail = ref
                                            _log_error(f"SMTC-WINRT: thumbnail updated")
                            except Exception:
                                _log_error("SMTC-WINRT: set thumbnail failed")
                            self._updater.update()
                            logger.debug('SMTC-WINRT: update sent\n\n')
                    except Exception:
                        _log_error("SMTC-WINRT: DisplayUpdater update failed")
                else:
                    logger.debug('SMTC-WINRT: no update sent\n\n')
            # Volume is ignored on purpose.

        except Exception:
            _log_error("SMTC-WINRT: _apply_changed failed")

    def _cleanup(self):
        # Deterministic shutdown best-effort.
        # This runs on the STA thread.
        try:
            # Disable SMTC to reduce stale sessions after shutdown.
            # Even if this produces a final change event, it avoids lingering controls.
            try:
                if self._smtc:
                    self._smtc.is_enabled = False
                    self._smtc.is_play_enabled = False
                    self._smtc.is_pause_enabled = False
                    self._smtc.is_stop_enabled = False
                    self._smtc.is_next_enabled = False
                    self._smtc.is_previous_enabled = False
            except Exception:
                _log_error("SMTC-WINRT: disable SMTC failed")

            # Unsubscribe from ButtonPressed if we have a token
            try:
                if self._smtc and self._button_token is not None:
                    try:
                        self._smtc.remove_button_pressed(self._button_token)
                    except Exception:
                        _log_error("SMTC-WINRT: remove_button_pressed failed")
            except Exception:
                _log_error("SMTC-WINRT: button cleanup failed")

            self._button_token = None

            # Release WinRT objects (best-effort)
            self._updater = None
            self._smtc = None
            self._player = None
            self._media = None
            self._storage = None
            self._streams = None

            # Close asyncio loop (if any)
            try:
                if self._loop is not None:
                    try:
                        self._loop.stop()
                    except Exception:
                        pass
                    try:
                        self._loop.close()
                    except Exception:
                        pass
            except Exception:
                _log_error("SMTC-WINRT: asyncio loop cleanup failed")
            self._loop = None

        except Exception:
            _log_error("SMTC-WINRT: cleanup failed")
# --------------------------
# Public controller (owned by main thread)
# --------------------------

class WindowsSMTCController(MediaControls):
    """
    Main-thread owner, mirroring MprisController semantics.
    """

    def __init__(self, identity="PyRadio", instance_name=None):
        super().__init__(identity, instance_name)
        self._thread = _SMTCWinRTThread(self._cmdq, self._stateq)

    def start(self):
        try:
            ok = self._thread.start()
            if not ok:
                logger.error("SMTC-WINRT: start failed")
                return False

            # Ignore OS commands while we publish the first snapshot
            self._thread.set_ignore_commands(True)

            # Best-effort initial snapshot (similar to how MPRIS starts with defaults)
            try:
                self._stateq.put({"PlaybackStatus": "Stopped"})
                self._stateq.put({"CanGoPrevious": False, "CanGoNext": False})
                # Provide an empty Metadata block so updater is initialized
                self._stateq.put({"Metadata": {"xesam:title": "", "xesam:artist": []}})
            except Exception:
                _log_error("SMTC-WINRT: initial snapshot failed")

            self._thread.set_ignore_commands(False)
            return True

        except Exception:
            _log_error("SMTC-WINRT: controller start failed")
            return False

    def stop(self):
        try:
            self._thread.set_ignore_commands(True)
            self._thread.stop()
        except Exception:
            _log_error("SMTC-WINRT: controller stop failed")

    # ------------- main-loop servicing -------------

    def poll(self, enabled):
        """
        Same behavior as MprisController.poll(enabled):
        - if disabled: drain all pending commands and log once
        - if enabled: drain all commands quickly and execute callbacks
        - handle debounced SET_VOLUME via base class
        """
        if not enabled:
            had_cmd = False
            while True:
                try:
                    self._cmdq.get_nowait()
                    had_cmd = True
                except queue.Empty:
                    break
            if had_cmd and logger.isEnabledFor(logging.INFO):
                logger.info("**** SMTC actions are allowed in NORMAL MODE only")
            super().poll(False)
            return

        while True:
            try:
                cmd, arg = self._cmdq.get_nowait()
            except queue.Empty:
                break

            if cmd == "PLAY" and self.cb_play:
                self.cb_play()

            elif cmd in ("STOP", "PAUSE") and self.cb_stop:
                self.cb_stop()

            elif cmd == "NEXT" and self.cb_next:
                self.cb_next()

            elif cmd == "PREV" and self.cb_prev:
                self.cb_prev()

            elif cmd == "PLAYPAUSE":
                if self.cb_playpause:
                    self.cb_playpause()
                else:
                    # Keep the same default policy as MPRIS: ignore.
                    pass

            elif cmd == "SET_VOLUME":
                # latest-wins (debounced) - identical to MPRIS
                try:
                    self._vol_pending = int(arg)
                except Exception:
                    self._vol_pending = None
                self._vol_last_req_ts = time.monotonic()

        super().poll(enabled)

    # ------------- state updates (main -> STA thread) -------------

    def update_metadata(self, trackid, title, station_name, playlist_name, url=None, art_url=None):
        """
        Keep the same metadata shape as MPRIS, but only title/artist are used by SMTC.
        """
        logger.error('SMTC-WINRT: Received')
        logger.error(f'SMTC-WINRT: {trackid = }')
        logger.error(f'SMTC-WINRT: {title = }')
        logger.error(f'SMTC-WINRT: {station_name = }')
        logger.error(f'SMTC-WINRT: {playlist_name = }')
        logger.error(f'SMTC-WINRT: {url = }')
        logger.error(f'SMTC-WINRT: {art_url = }')
        if art_url is not None:
            art_url = art_url[7:].lstrip("/").replace("/", os.sep)
            logger.error(f'SMTC-WINRT: fixed {art_url = }')
        try:
            md = {}
            md["mpris:trackid"] = trackid
            md["xesam:title"] = title
            md["xesam:artist"] = [station_name] if station_name else []
            md["xesam:album"] = playlist_name if playlist_name else ""
            if url:
                md["xesam:url"] = url
            if art_url:
                md["mpris:artUrl"] = art_url

            self._stateq.put({"Metadata": md})
        except Exception:
            _log_error("SMTC-WINRT: update_metadata failed")


