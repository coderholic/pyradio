# PyRadio

Command line internet radio player.

Ben Dowling - [http://www.coderholic.com/pyradio](http://www.coderholic.com/pyradio)

## Table of contents

* [Requirements](#requirements)
* [Installation via pip](#installation-via-pip)
* [Building from source](#building-from-source)
* [Shell commands](#shell-commands)
* [Controls](#controls)
* [Stations file](#stations-file)
* [Player detection / selection](#player-detection-selection)
* [Player default volume level](#player-default-volume-level)
* [Debug mode](#debug-mode)

## Requirements

* python 2.6+/3.2+
* python-pip
* MPV, MPlayer or VLC installed and in your path.
* [socat](http://www.dest-unreach.org/socat/) (if you wish to use MPV)

## Installation via pip

This is the simplist method for installing **PyRadio**.

The first thing is to make sure MPV, MPlayer or VLC are installed and are in the
PATH. To check this, go in your favorite terminal and make sure these programs
are launched when you type "mpv", "mplayer" or "cvlc".

#### MacOSX

MPlayer is one of the available packages provided by [Homebrew](https://github.com/Homebrew/homebrew).

But it is not the case of VLC. Nevertheless, **PyRadio** will also work with the binary of the application [VLC](http://www.videolan.org/vlc/download-macosx.html).

You simply can add a symbolic link to the executable as follows (this link must of course be in your PATH):

    ln -s /Applications/VLC.app/Contents/MacOS/VLC cvlc

The second step is to use pip to install the python package:

    pip install pyradio

#### Linux

    pip install pyradio

## Building from source

#### MaxOSX and Linux

    python setup.py build

The second step is to install the build:

    sudo python setup.py install

## Shell commands

```
$ pyradio -h

usage: pyradio [-h] [-s STATIONS] [-p [PLAY]] [-a] [-l] [-d] [-u USE_PLAYER]

Curses based Internet radio player

optional arguments:
  -h, --help            show this help message and exit
  -s STATIONS, --stations STATIONS
                        Use specified station CSV file.
  -p [PLAY], --play [PLAY]
                        Start and play.The value is num station or empty for
                        random.
  -a, --add             Add station to list.
  -l, --list            List of added stations.
  -d, --debug           Start pyradio in debug mode.
  -u USE_PLAYER, --use-player USE_PLAYER
                        Use specified player. A comma-separated list can be
                        used to specify detection order. Supported players:
                        mpv, mplayer, vlc.
```

## Controls

```
Up/Down/j/k/PgUp/PgDown   Change station selection.
g                         Jump to first station.
<n>G                      Jump to n-th / last station.
Enter/Right/l             Play selected station.
r                         Select and play a random station.
Space/Left/h              Stop/start playing selected station.
-/+ or ,/.                Change volume.
m                         Mute.
v                         Save volume (not applicable for vlc).
?,/                       Show keys help.
Esc/q                     Quit.
```

## Stations file

**PyRadio** reads the stations to use from a CSV file (named *stations.csv*), where each line contains two columns, the first being the station name and the second being the stream URL.

**PyRadio** will by default use the user's configuration file (e.g. *~/.config/pyradio/stations.csv*) to read the stations. If this file is not found, it will be created and populated with a default set of stations.

**Tip:** If you already have a custom *stations.csv* file, but want to update it with **PyRadio**'s default one, you just rename it, run **PyRadio** (so that the default one get created) and then merge the two files.

## Player detection / selection

**PyRadio** is basically built around the existence of a valid media player it can use. Thus, it will auto detect the existence of its supported players upon its execution.

Currently, it supports MPV, MPlayer and VLC, and it will look for them in that order. If none of them is found, the program will terminate with an error.

MPV will be used only when the [socat](http://www.dest-unreach.org/socat/) multipurpose relay is also installed.

Users can alter this default behavior by using the ***-u*** command line option. This option will permit the user either to specify the player to use, or change the detection order.

Example:

```
pyradio -u vlc
```
will instruct **PyRadio** to use VLC; if it is not found, the program will terminate with an error.

```
pyradio -u vlc,mplayer,mpv
```
will instruct **PyRadio** to look for VLC, then MPlayer and finaly for MPV and use whichever it finds first; if none is found, the program will terminate with an error.

## Player default volume level

MPV and MPlayer, when started, use their saved (or default) volume level to play any multimedia content. Fortunately, this is not the case with VLC.

This introduces a problem to **PyRadio**: every time we change a station (i.e restart playback), even though we may have already set the volume to a desired level, the playback starts at the player's default level.

The way to come around it, is to save our desired volume level in a way that it will be used by the player whenever is restarted.

This is done by typing "***v***" right after setting a desired volume level.

### MPV

MPV uses profiles to customize its behavior.

**PyRadio** defines a profile called "**[pyradio]**" in MPV's configuration file (e.g. *~/.config/mpv/mpv.conf*). This profile will be used every time playback is started.

Example:

    volume=100

    [pyradio]
    volume=50

### MPlayer

MPlayer uses profiles to customize its behavior as well.

**PyRadio** defines a profile called "**[pyradio]**" in MPV's configuration file (e.g. *~/.mplayer/config*). This profile will be used every time playback is started.


Example:

    volume=100

    [pyradio]
    volstep=1
    volume=28

## Debug mode

Adding the ***-d*** option to the command line will instruct **PyRadio** to enter *Debug mode*, which means that it will print debug messages to a file. This file will always reside in the user's home directory and will be named *pyradio.log*.

In case of a bug or a glitch, please include this file to the issue you will [open in github](https://github.com/coderholic/pyradio/issues).
