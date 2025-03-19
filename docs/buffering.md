# PyRadio Buffering

Command line internet radio player.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Introduction](#introduction)
* [How it all works](#how-it-all-works)
    * [MPlayer buffering](#mplayer-buffering)
* [Parameters used](#parameters-used)
* [User experience](#user-experience)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#buffering) ]

## Introduction

When a station is slow (or the internet connection is slow), one might get to a situation where the connection timeout will run out before the connection with the station can be established. Even worse, **PyRadio** will connect to the station, but the sound will be choppy and crackling.

The solution is to use a large enough **buffer** to connect to the station; this will effectively make **PyRadio** connect to the station and start receiving data, but will not start playback until the buffer is full.

All **PyRadio** supported players support buffering, using a number of command line parameters to actually set it up. **PyRadio** will remove all this complexity by making is as simple as inserting a single value to the **Configuration Window**.

In addition to that, or instead of that, one can set up a buffering value for any individual station using the "*Buffering*" window, shown below.

![PyRadio Buffering Window](https://members.hellug.gr/sng/pyradio/pyradio-buffering-win.jpg)

The window opens by pressing "**\\B**" while in the **Main** mode.

It will display the current station's buffer size (0 means no buffering), and will permit to adjust it, or use the previously used value (pressing "**r**").

## How it all works

**PyRadio** has both a configuration parameter and a station parameter that will be taken into account when trying to determine if a station will use buffering or not.

1. The global *buffering value* which will be used for all stations (if set). It can be found under the "*Connection Options*" section in the **Configuration Window**, parameter **Buffering (seconds)**.

2. The *station buffering* value set using "**\\B**" as described above. \
If used, the station will be updated and the playlist will be silently saved.\
\
In this case, a string of the form "**7@128**" will be inserted in the appropriate field of the station definition, "**7**" being the buffering value in seconds and "**128**" the bitrate of the station, which is only relevant to **MPlayer**.

In any case, one can enable or disable the use of buffering by pressing "**\\b**". This value will not be saved and will be set to True whenever a player change occurs.

### MPlayer buffering

Both *MPV* and *VLC* will directly use the buffering value (expressed in seconds) in order to buffer a stream.

This is not the case with *MPlayer* unfortunately; it has to receive the number of KBytes to buffer.

In order to do that in a consistent way, the station's bitrate must be known beforehand, which is impossible. So, a workaround is being used: the player will trigger a station update (and a silent playlist save), if:

1. **MPlayer** is installed and detected as a supported player.
2. The "**MPlayer auto save br**" configuration parameter (under **Connection Options**) is set to **True**.
3. The station streams at a bitrate different to 128 kbps (the default).

This way, the first time **MPlayer** is used to buffer the station the buffering will be incorrect (shorter or longer depending on the real bitrate), but subsequent playback of the station will correctly set the number of KBytes that corresponds to the buffering time set.

## Parameters used

The following table shows the command line parameters used by **PyRadio** when the "*Buffering*" window is used to set up buffering.

| mpv<br>(X in seconds)          | mplayer<br>(X in KBytes) | vlc<br>(X in seconds)    |
|--------------------------------|--------------------------|--------------------------|
| --demuxer-readahead-secs=X-1   | -cache X                 | --network-caching X*1000 |
| --demuxer-cache-wait=yes       | -cache-min 80            |                          |
| --cache=yes                    |                          |                          |
| --cache-secs=X                 |                          |                          |
| --cache-on-disk=yes/no \*      |                          |                          |

\* disabled if more than 500KB of memory is free

## User experience

When buffering is enabled, and a connection to a station initializes, **PyRadio** will display a "**[B]**" at the top left corner of the window, and display "**Buffering:**" and the name of the station in the status bar, until it get a token that the buffering has stopped.

![PyRadio Buffering](https://members.hellug.gr/sng/pyradio/pyradio-b.jpg)

An example is shown in the image above.

Now, this behavior depends on the station, and the data it sends (or does not send) while it is buffering. For example, an ICY title may be received while buffering, which will be displayed in the status bar.

It should be noted that, no volume adjustment can be preformed while buffering.

