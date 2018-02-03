# PyRadio

Command line internet radio player.

Ben Dowling - [http://www.coderholic.com/pyradio](http://www.coderholic.com/pyradio)

## Requirements

* python 2.6+/3.2+
* python-pip
* mpv, mplayer or vlc installed and in your path.

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
m                       Mute.
r                       Select and play a random station.
g                       Jump to first station.
<n>G                    Jump to n-th station.
Space                   Stop/start playing selected station.
Esc/q                   Quit.
```
