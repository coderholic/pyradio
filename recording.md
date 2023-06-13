# Recording stations

**PyRadio**: Command line internet radio player.

___


**Berfore you continue, read this!**

Generally, recording a radio streaming broadcast is considered legit, if the recording is to be used for personal use only (i.e. to listen to the broadcast at a later time).

Distributing such a recording, is illegal. Broadcasting it is also illegal. Its reproduction before an audience is also illegal. In some countries/regions, it is also illegal to split or tag the songs in the recording.

Please make sure you are informed about this topic, about what the law considers illegal at your country/region, **before using this feature!**

**You have been warned!**

**PyRadio**, its creator and maintainers do not condone any behavior that involves online piracy or copyright violation. This feature is provided strictly for personal use, and to utilize another requested feature: **pausing and resuming** playback.

___

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Intro](#intro)
    * [MPV](#mpv)
    * [MPlayer](#mplayer)
    * [VLC](#vlc)
* [Recording implementation](#recording-implementation)
    * [File location](#file-location)
    * [File type](#file-type)
    * [Pausing playback](#pausing-playback)

<!-- vim-markdown-toc -->

## Intro

**PyRadio v. 0.9.2.8** introduces the ability to record stations, a feature used mainly to facilitate another feature: the ability to *pause and resume playback*.

All supported media players (**MPV**, **MPlayer** and **VLC**) support stream recording, each implementing it in a different way, which pose a challenge for the front end implementation.

Let us see the differences.

### MPV

**MPV** stream recording has the following characteristics:

- it is done using the **--stream-record** command line parameter.
- it is considered an **experimental feature** by the **MPV** developers. \
Radio streaming uses well known and established codecs (mainly mp3 and aac) and I have had no broken recording while testing the feature (even with flac stations).
- **MPV** has the ability to play and record a stream at the same time. \
This is very convenient, since all one has to do is add a command line parameter and start recording, while listening to what's being recorded.
- adjusting the volume or muting the player will not affect what's being recorded.
- when paused, the player will pause the playback but will keep recording the stream. Furthermore, song titles will stop being updated, but will be correctly displayed and updated when playback is resumed.

### MPlayer

**Note**: **MPlayer** recording has not been implemented yet!

**MPlayer** stream recording has the following characteristics:

- it is done using the **-dumpstream** and **-dumpfile** command line parameters.
- it does not have the ability to record and play a stream at the same time. \
This means that the front end will have to use two *mplayer* instances: one to record the stream and one more to play the recorded file (as it is being recorded).

### VLC

**Note**: **VLC** recording has not been implemented yet!

**VLC** stream recording has the following characteristics:

- it is done using the **--sout** command line parameter.
- it does not have the ability to record and play a stream at the same time. \
This means that the front end will have to use two *vlc* instances: one to record the stream and one more to play the recorded file (as it is being recorded).


## Recording implementation

The following keys are used for this feature:

| Key                    | Description                 |
|------------------------|-----------------------------|
| \|<br>(pipe symbol)    | Toggle recording on and off |
| Space                  | Pause and resume playback   |

In order to record a station, recording has to be enabled **beforehand**, by pressing the *"pipe symbol*" or "*vetical line*" ("**|**"). Then the following message appears:

![Enable recording](https://members.hellug.gr/sng/pyradio/pyradio-recording1.jpg)

When this is done an "**[r]**" will be displayed at the top left corner of the window. This means that recording is enabled, but **PyRadio** is not currently recording to a file.

When playback is started (i.e. start playing a station), an "**[R]**" will be displayed at the top left corner of the window (replacing the "**[r]**" that was already there), which means that **PyRadio** is actually recording the station to a file.

The following image is a mockup presenting the difference.

![Recording mockup](https://members.hellug.gr/sng/pyradio/pyradio-recording2.jpg)

Pressing the *"pipe symbol*" or "*vetical line*" ("**|**") again will disable recording and nothing will be displayed at the top left corner of the window. The actual recording of the station will still be active, until the station is stopped.

It must be made clear that toggling the recording status for **PyRadio** will actually take effect after a station has been started or stopped. This is because of the way the players get the recording command; through command line arguments, which can only be passed when the player is executed.

### File location

Files created by the recording feature will be saved under the "**recordings**" folder inside **PyRadio**'s configuration directory.

The file will be named:

```
[date] [Station Name].mkv
```

### File type

**PyRadio** will produce a **mkv** file when recording a station.

This is just a measure of convenience since the type of audio (mp3, aac, aac+, flac, etc.) the station will broadcast cannot be known beforehand (before starting the recording, that is).

Although a **mkv** file is a video/audio/subs etc. container, it's perfectly fine to contain just a sound stream, as is the case of the files produced by **PyRadio**.

The file can be (hopefully) reproduced using any video media player.

### Pausing playback

After you have started recording a station, **PyRadio** will connect to it and start downloading the station data and at the same time will produce sound for you to hear what's downloaded.

You can then press "**Space**" to pause the playback, but still continue downloading the station's data.

Pressing "**Space**" again will resume playback from where it left off.

As a consequence, listening to the end of a show that you have paused for say 10 minutes, and then stopping the station (both playback and recording), the file recorded will have an excess of 10 minutes of data, past the end of the actual show.

Finally, please keep in mind that all other keys relevant to starting, stopping and restarting a station's playback remain the same; only the behavior of the "**Space**" key has changed when recording is on.
