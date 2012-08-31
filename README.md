# PyRadio

Command line internet radio player.

Ben Dowling - [http://www.coderholic.com/pyradio](http://www.coderholic.com/pyradio)


## Requirements

* python 2.6+
* mplayer


## Installation

    pip install pyradio


## Shell

    $ pyradio -h

    usage: main.py [-h] [--stations STATIONS] [--random] [--add] [--list]

    Console radio player

    optional arguments:
    -h, --help            show this help message and exit
    --stations STATIONS, -s STATIONS
                            Path on stations csv file.
    --random, -r          Start and play random station.
    --add, -a             Add station to list.
    --list, -l            List of added stations.


## Controls
```
Up/Down/PgUp/PgDown 	Change station selection
Enter 					Play selected station
-/+						Change volume
m						Mute
r						Select and play a random station
Space                   Stop/start playing selected station
Esc/q					Quit
```
