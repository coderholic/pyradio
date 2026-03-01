# pyradio_mpris.py
#
# MPRIS2 support for PyRadio using dbus-next (asyncio in a dedicated thread).
#
# Design:
# - DBus thread: exports org.mpris.MediaPlayer2 + org.mpris.MediaPlayer2.Player
# - Main thread (curses): owns the real player and executes commands
# - Communication:
#     DBus thread -> main thread: cmd_queue  (PLAY/STOP/NEXT/PREV/SET_VOLUME)
#     main thread -> DBus thread: state_queue (updates to properties)
#
# Main loop integration point:
#     c = getch()
#     if c == -1:
#         mpris.poll()   # drains cmd_queue; applies debounced volume; sends updates to DBus thread
#         continue

import os
import time
import queue
import threading
import asyncio
import locale
import logging

OBJ_PATH = "/org/mpris/MediaPlayer2"

locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

try:
    from dbus_next.aio import MessageBus
    from dbus_next.service import ServiceInterface, method, dbus_property
    from dbus_next.constants import PropertyAccess
    from dbus_next import Variant

    # NameFlag / DO_NOT_QUEUE may not exist in older dbus-next versions
    try:
        from dbus_next.constants import NameFlag  # newer
        _NAMEFLAG_DO_NOT_QUEUE = getattr(NameFlag, "DO_NOT_QUEUE", None)
    except Exception:
        NameFlag = None
        _NAMEFLAG_DO_NOT_QUEUE = None

except Exception:
    MessageBus = None
    ServiceInterface = None
    method = None
    dbus_property = None
    PropertyAccess = None
    Variant = None
    NameFlag = None
    _NAMEFLAG_DO_NOT_QUEUE = None


def _variant_equal(a, b):
    if a is b:
        return True
    if a is None or b is None:
        return False
    if not isinstance(a, Variant) or not isinstance(b, Variant):
        return a == b
    return (a.signature == b.signature) and (a.value == b.value)

def _metadata_equal(old, new):
    if old.keys() != new.keys():
        return False
    for k in old.keys():
        if not _variant_equal(old.get(k), new.get(k)):
            return False
    return True

# -------------------------------
# DBus interfaces (thread-owned)
# -------------------------------

class _MprisRoot(ServiceInterface):
    def __init__(self, identity="PyRadio", has_track_list=False):
        super().__init__("org.mpris.MediaPlayer2")
        self._identity = identity
        self._has_track_list = has_track_list

    @dbus_property(access=PropertyAccess.READ)
    def CanQuit(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanRaise(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def HasTrackList(self) -> "b":
        return bool(self._has_track_list)

    @dbus_property(access=PropertyAccess.READ)
    def Identity(self) -> "s":
        return self._identity

    @dbus_property(access=PropertyAccess.READ)
    def SupportedUriSchemes(self) -> "as":
        return []

    @dbus_property(access=PropertyAccess.READ)
    def SupportedMimeTypes(self) -> "as":
        return []


class _MprisPlayer(ServiceInterface):
    """
    Minimal Player interface for PyRadio.
    Commands go to cmd_queue.
    State is applied via apply_changed(...) from the DBus thread.
    """
    def __init__(self, cmd_queue):
        super().__init__("org.mpris.MediaPlayer2.Player")
        self._cmdq = cmd_queue

        self._playback_status = "Stopped"  # "Playing" | "Stopped"
        self._metadata = {"mpris:trackid": Variant("o", "/org/mpris/MediaPlayer2/track/idle")}
        self._volume = 0.5                 # 0..1 placeholder
        self._can_go_next = True
        self._can_go_prev = True

    # ----- Properties -----

    @dbus_property(access=PropertyAccess.READ)
    def PlaybackStatus(self) -> "s":
        return self._playback_status

    @dbus_property(access=PropertyAccess.READ)
    def Metadata(self) -> "a{sv}":
        return self._metadata

    @dbus_property(access=PropertyAccess.READWRITE)
    def Volume(self) -> "d":
        return float(self._volume)

    @dbus_property(access=PropertyAccess.READ)
    def CanGoNext(self) -> "b":
        return self._can_go_next

    @dbus_property(access=PropertyAccess.READ)
    def CanGoPrevious(self) -> "b":
        return self._can_go_prev

    @dbus_property(access=PropertyAccess.READ)
    def CanPlay(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanStop(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanPause(self) -> "b":
        return True

    @dbus_property(access=PropertyAccess.READ)
    def CanSeek(self) -> "b":
        return False

    @dbus_property(access=PropertyAccess.READ)
    def CanControl(self) -> "b":
        return True

    @Volume.setter
    def Volume(self, value):
        # client sets absolute volume 0..1 -> translate to percent and request from main thread
        try:
            v = float(value)
        except Exception:
            return

        if v < 0.0:
            v = 0.0
        elif v > 1.0:
            v = 1.0

        target_percent = int(round(v * 100))
        if target_percent < 0:
            target_percent = 0
        elif target_percent > 100:
            target_percent = 100

        # enqueue request to main; do not block DBus thread
        try:
            self._cmdq.put_nowait(("SET_VOLUME", target_percent))
        except Exception:
            pass

    # ----- Methods -----

    @method()
    def Play(self):
        self._cmdq.put(("PLAY", None))

    @method()
    def Stop(self):
        self._cmdq.put(("STOP", None))

    @method()
    def Pause(self):
        self._cmdq.put(("PAUSE", None))

    @method()
    def Next(self):
        self._cmdq.put(("NEXT", None))

    @method()
    def Previous(self):
        self._cmdq.put(("PREV", None))

    @method()
    def PlayPause(self):
        # optional toggle; main can decide actual behavior
        self._cmdq.put(("PLAYPAUSE", None))

    # ----- Apply batched changes from main thread -----

    def apply_changed(self, changed):
        """
        changed keys may include:
          PlaybackStatus: "Playing"/"Stopped"
          CanGoNext: bool
          CanGoPrevious: bool
          Volume: float 0..1
          Metadata: dict with python-native values
        """
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'MPRIS received: {changed}')
        out = {}

        if "PlaybackStatus" in changed:
            this_value = str(changed["PlaybackStatus"])
            if self._playback_status != this_value:
                self._playback_status = this_value
                out["PlaybackStatus"] = self._playback_status

        if "CanGoNext" in changed:
            this_value = bool(changed["CanGoNext"])
            if self._can_go_next != this_value:
                self._can_go_next = this_value
                # out["CanGoNext"] = Variant("b", self._can_go_next)
                out["CanGoNext"] = self._can_go_next

        if "CanGoPrevious" in changed:
            this_value = bool(changed["CanGoPrevious"])
            if self._can_go_prev != this_value:
                self._can_go_prev = this_value
                # out["CanGoPrevious"] = Variant("b", self._can_go_prev)
                out["CanGoPrevious"] = self._can_go_prev

        if "Volume" in changed:
            try:
                v = float(changed["Volume"])
            except Exception:
                v = self._volume
            if v < 0.0:
                v = 0.0
            elif v > 1.0:
                v = 1.0
            if v != self._volume:
                self._volume = v
                out["Volume"] = self._volume

        if "Metadata" in changed:
            md_plain = dict(changed["Metadata"])
            md = {}

            for k, v in md_plain.items():
                # Keep it simple: only the types we need
                if k == "mpris:trackid":
                    md[k] = Variant("o", str(v))
                elif isinstance(v, list):
                    md[k] = Variant("as", [str(x) for x in v])
                else:
                    md[k] = Variant("s", str(v))

            if not _metadata_equal(self._metadata, md):
                self._metadata = md
                # out["Metadata"] = Variant("a{sv}", self._metadata)
                out["Metadata"] = self._metadata

        if out:
            # org.freedesktop.DBus.Properties.PropertiesChanged for this interface
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'MPRIS emit_properties_changed: {out}')
            self.emit_properties_changed(out, [])
        else:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('MPRIS emit_properties_changed: None')


# -----------------------------------
# MPRIS thread runner (asyncio thread)
# -----------------------------------

class _MprisThread:
    def __init__(self, bus_name, identity, cmd_queue, state_queue):
        self.bus_name = bus_name
        self.identity = identity
        self.cmdq = cmd_queue
        self.stateq = state_queue

        self._loop = None
        self._thread = None
        self._stop = threading.Event()

        self._player_iface = None

    def start(self):
        if MessageBus is None:
            return False
        if self._thread and self._thread.is_alive():
            return True
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="pyradio-mpris", daemon=False)
        self._thread.start()
        return True

    def stop(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS Thread stooping')
        self._stop.set()
        if self._loop:
            try:
                self._loop.call_soon_threadsafe(lambda: None)
            except Exception:
                pass
        if self._thread and self._thread.is_alive():
            # self._thread.join(timeout=1.0)
            self._thread.join()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS Thread stopped')

    def _run(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS Thread starting')
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)

        main_task = self._loop.create_task(self._main())
        main_task.add_done_callback(lambda _t: self._loop.call_soon_threadsafe(self._loop.stop))

        self._loop.run_forever()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS Thread exited loop')

        try:
            self._loop.run_until_complete(asyncio.gather(main_task, return_exceptions=True))
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'MPRIS Thread loop run_until_complete exception 1: {e}')

        try:
            pending = {t for t in asyncio.all_tasks(self._loop) if t is not main_task}
        except TypeError:
            pending = {t for t in asyncio.all_tasks() if t is not main_task}

        for t in pending:
            t.cancel()
        try:
            self._loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'MPRIS Thread loop run_until_complete exception 2: {e}')

        self._loop.close()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS Thread exited')

    async def _main(self):
        bus = await MessageBus().connect()

        root = _MprisRoot(identity=self.identity, has_track_list=False)
        player = _MprisPlayer(self.cmdq)
        self._player_iface = player

        # Export FIRST so clients that react immediately can introspect safely
        bus.export(OBJ_PATH, root)
        bus.export(OBJ_PATH, player)

        # Request name AFTER export; fail-fast if another instance owns it
        try:
            if _NAMEFLAG_DO_NOT_QUEUE is None:
                await bus.request_name(self.bus_name)
            else:
                await bus.request_name(self.bus_name, flags=_NAMEFLAG_DO_NOT_QUEUE)
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'MPRIS: request_name failed for {self.bus_name}: {repr(e)}')
            # If name is taken, clean up exports and disconnect to avoid ghosting
            try:
                bus.unexport(OBJ_PATH)
            except Exception:
                pass
            try:
                bus.disconnect()
            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"MPRIS: could not acquire bus name {self.bus_name}: {e}")
            return

        try:
            # Consume state updates coming from main thread and apply to DBus properties
            while not self._stop.is_set():
                try:
                    changed = self.stateq.get_nowait()
                except queue.Empty:
                    await asyncio.sleep(0.01)
                    continue
                try:
                    player.apply_changed(changed)
                except Exception as e:
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error(f"MPRIS: player.apply_changed failed: {changed = } - {e}")

        finally:
            # Deterministic shutdown: unexport -> release name -> disconnect
            try:
                bus.unexport(OBJ_PATH)
            except Exception:
                pass

            # release_name in dbus-next is callback-style on BaseMessageBus; safe to call anyway
            released = asyncio.get_running_loop().create_future()

            def _released(_reply, _err):
                if not released.done():
                    released.set_result(True)

            try:
                bus.release_name(self.bus_name, _released)
            except Exception:
                if not released.done():
                    released.set_result(True)

            try:
                await asyncio.wait_for(released, timeout=0.5)
            except Exception:
                pass

            try:
                bus.disconnect()
                loggerlerror('MPRIS bus disconnected')
            except Exception as e:
                loggerlerror(f'MPRIS bus disconnect exception {e}')

# -----------------------------------
# Public controller (owned by main thread)
# -----------------------------------

class MprisController:
    """
    Main-thread owner. You:
      - create it with callbacks (play/stop/next/prev/set_volume)
      - call start()
      - call poll() at your idle slot (c == -1)
      - call update_* when your player state changes
    """

    def __init__(self, identity="PyRadio", instance_name=None):
        # instance_name becomes part of bus name; keep it stable-ish
        if instance_name is None:
            instance_name = "pyradio." + str(os.getpid())

        # Standard MPRIS name: org.mpris.MediaPlayer2.<name>
        # self.bus_name = "org.mpris.MediaPlayer2." + instance_name
        self.bus_name = "org.mpris.MediaPlayer2.pyradio"
        self.identity = identity

        self._cmdq = queue.Queue()
        self._stateq = queue.Queue()

        self._thread = _MprisThread(self.bus_name, self.identity, self._cmdq, self._stateq)

        # callbacks (set via set_callbacks)
        self.cb_play = None
        self.cb_stop = None
        self.cb_next = None
        self.cb_prev = None
        self.cb_playpause = None
        self.cb_set_volume = None  # cb_set_volume(percent) -> actual_percent or None

        # volume latest-wins + debounce (handled in poll())
        self._vol_pending = None
        self._vol_last_req_ts = 0.0
        self._vol_debounce_sec = 0.12

    def set_callbacks(self, play=None, stop=None, next_=None, prev=None, playpause=None, set_volume=None):
        self.cb_play = play
        self.cb_stop = stop
        self.cb_next = next_
        self.cb_prev = prev
        self.cb_playpause = playpause
        self.cb_set_volume = set_volume

    def start(self):
        return self._thread.start()

    def stop(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS MprisController stop called')
        self._thread.stop()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('MPRIS MprisController stop ended')

    # ------------- main-loop servicing -------------

    def poll(self, enabled):
        """
        Call this from main thread when c == -1 (idle slot).
        - drains commands from MPRIS
        - applies debounced volume (latest-wins)
        """
        # Drain all pending commands quickly (do not process only one!)
        while True:
            try:
                cmd, arg = self._cmdq.get_nowait()
            except queue.Empty:
                break

            if not enabled:
                # drop everything when not in NORMAL_MODE
                if not enabled and logger.isEnabledFor(logging.INFO):
                    logger.info('**** MPRIS actions are allowed in NORMAL MODE only')
                continue

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
                    # fallback: toggle via play/stop if you want; or ignore
                    if self.cb_play and self.cb_stop:
                        # let the app decide; ignore here by default
                        pass

            elif cmd == "SET_VOLUME":
                # latest-wins
                try:
                    self._vol_pending = int(arg)
                except Exception:
                    self._vol_pending = None
                self._vol_last_req_ts = time.monotonic()

        # Debounced apply of last requested volume
        if enabled:
            self._apply_pending_volume_if_due()
        else:
            # also drop any pending volume when disabled
            self._vol_pending = None

    def _apply_pending_volume_if_due(self):
        if self._vol_pending is None:
            return
        if self.cb_set_volume is None:
            return

        now = time.monotonic()
        if (now - self._vol_last_req_ts) < self._vol_debounce_sec:
            return

        target = self._vol_pending
        self._vol_pending = None

        # Apply (blocking is OK here; you're in main thread)
        actual = self.cb_set_volume(target)
        if actual is None:
            actual = target
        try:
            actual = int(actual)
        except Exception:
            actual = target
        if actual < 0:
            actual = 0
        elif actual > 100:
            actual = 100

        # Push Volume update to DBus thread (0..1)
        self.update_volume_percent(actual)

    # ------------- state updates (main -> DBus thread) -------------

    def update_playback(self, is_playing):
        status = "Playing" if is_playing else "Stopped"
        self._stateq.put({"PlaybackStatus": status})

    def update_nav_caps(self, can_prev, can_next):
        self._stateq.put({"CanGoPrevious": bool(can_prev), "CanGoNext": bool(can_next)})

    def update_volume_percent(self, vol_percent):
        try:
            vp = int(vol_percent)
        except Exception:
            return
        if vp < 0:
            vp = 0
        elif vp > 100:
            vp = 100
        self._stateq.put({"Volume": vp / 100.0})

    def update_metadata(self, trackid, title, station_name, playlist_name, url=None, art_url=None):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{trackid = }')
            logger.debug(f'{title = }')
            logger.debug(f'{station_name = }')
            logger.debug(f'{playlist_name = }')
            logger.debug(f'{url = }')
            logger.debug(f'{art_url = }')
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

    def make_trackid(self, playlist_gen, index):
        # stable object path
        return "/org/mpris/MediaPlayer2/track/pl_{}/st_{}".format(int(playlist_gen), int(index))
