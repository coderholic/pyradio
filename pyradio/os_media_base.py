# -*- coding: utf-8 -*-
#
# Base class for OS Media Controls
#
import os
import time
import queue
import locale
import logging

locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

class MediaControls:
    """
    Main-thread owner. You:
      - create it with callbacks (play/stop/next/prev/set_volume)
      - call start()
      - call poll() at your idle slot (c == -1)
      - call update_* when your player state changes
    """

    def __init__(self, identity="PyRadio", instance_name=None, default_icon=None):
        # instance_name becomes part of bus name; keep it stable-ish
        if instance_name is None:
            instance_name = "pyradio." + str(os.getpid())

        self.identity = identity
        self.default_icon = default_icon

        self._cmdq = queue.Queue()
        self._stateq = queue.Queue()

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
        self._vol_pending = None
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
            logger.debug('OS-MEDIA: MediaControls stop called')
        self._thread.stop()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('OS-MEDIA: MediaControls stop ended')

    # ------------- main-loop servicing -------------

    def poll(self, enabled):
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
        pass

    def make_trackid(self, playlist_gen, index):
        # stable object path
        return "/org/mpris/MediaPlayer2/track/pl_{}/st_{}".format(int(playlist_gen), int(index))
