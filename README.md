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

## Windows

On Windows, only mplayer or vlc can be used (mpv requires an additional program called socat, which does not exist on this platform).

In case mplayer is the player of choise, users must manually execute it on a "Command Prompt" window, so that it caches Windows fonts. This has be done once, right after mplayer is installed.

Example:

    mplayer -playlist "http://somafm.com/startstream=groovesalad.pls"

## Shell commands

    $ pyradio -h

    usage: main.py [--help] [--stations <path>] [--random] [--add] [--list]

    Console radio player

    optional arguments:
    -h, --help            Show this help message and exit.
    -s, --stations <path> Use specified station CSV file.
    -r, --random          Start and play a random station.
    -a, --add             Add station to list.
    -l, --list            List of added stations.
    -d, --debug           Debug mode (pyradio.log created).
                          To be attached with any bug report.

## Controls

```
Up/Down/j/k/PgUp/PgDown Change station selection.
Enter                   Play selected station.
-/+                     Change volume.
v                       Save volume (mpv and mplayer only).
m                       Mute.
r                       Select and play a random station.
g                       Jump to first station.
<n>G                    Jump to n-th station.
Space                   Stop/start playing selected station.
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
    softvol=yes
    volstep=1
    volume=28

### vlc

vlc by default saves the volume, so no customization is necessary.
