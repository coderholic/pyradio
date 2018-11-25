# PyRadio

Command line internet radio player.

Ben Dowling - [http://www.coderholic.com/pyradio](http://www.coderholic.com/pyradio)

## Requirements

* python 2.6+/3.2+
* python-pip
* mpv, mplayer or vlc installed and in your path.
* socat (if you wish to use MPV)

## Installation via pip

This is the simplist method for installing PyRadio.

The first thing is to make sure MPV, MPlayer or VLC are installed and are in the
PATH. To check this, go in your favorite terminal and make sure thiese programs
are launched when you type "mpv", "mplayer" or "cvlc".

#### MacOSX

MPlayer is one of the available packages provided by [Homebrew](https://github.com/Homebrew/homebrew).

But it is not the case of VLC. Nevertheless, pyradio will also work with the binary of the application [VLC](http://www.videolan.org/vlc/download-macosx.html).

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

    $ pyradio -h

    usage: main.py [--help] [--stations <path>] [--random] [--add] [--list]

    Console radio player

    optional arguments:
    -s, --stations <path> Use specified station CSV file.
    -p, --play [play]     Start and play. The value is num station or empty for random.
    -a, --add             Add station to list.
    -l, --list            List of added stations.
    -u, --use-player      Specify which player to use (mpv, mplayer or cvlc).
    -d, --debug           Debug mode (pyradio.log created).
                          To be attached with any bug report.
    -h, --help            Show this help message and exit.

## Controls

```
Up/Down/j/k/PgUp/PgDown Change station selection.
g                       Jump to first station.
<n>G                    Jump to n-th / last station.
Enter/Right/l           Play selected station.
r                       Select and play a random station.
Space/Left/h            Stop/start playing selected station.
-/+ or ,/.              Change volume.
m                       Mute.
v                       Save volume (not applicable for vlc).
?,/                     Show keys help.
Esc/q                   Quit.
```

## Player default volume

### mpv

mpv uses profiles to customize its behavior.

Users can define a profile called "**[pyradio]**" in mpv's configuration file (e.g. *~/.config/mpv/mpv.conf*) and pyradio will use it when playing.

Example:

    volume=100

    [pyradio]
    volume=50

### mplayer

mplayer uses profiles to customize its behavior as well.

Users can define a profile called "**[pyradio]**" in mplayers's configuration file (e.g. *~/.mplayer/config*) and pyradio will use it when playing.

Example:

    volume=100

    [pyradio]
    volstep=1
    volume=28

### vlc

vlc by default saves the volume, so no customization is necessary.
