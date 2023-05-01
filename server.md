# PyRadio Remote Control Server

**PyRadio:** Command line internet radio player.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Remote Control Server](#remote-control-server)
    * [Using the Web Server](#using-the-web-server)
    * [Using the Text Server](#using-the-text-server)
    * [Examples](#examples)
    * [Text vs. Web commands](#text-vs.-web-commands)

<!-- vim-markdown-toc -->

## Remote Control Server

**PyRadio** can be controlled remotely using normal http requests either form the command line (with *curl* for example) or from a browser.

For this purpose, a simple web server has been integrated in **PyRadio**; this server can be started

- automatically \
Setting the **Remote Control Server** options ins the config file, especially setting the **Auto-start Server** to **True**, or
- by pressing "**\\s**" at the main window, selecting the desired options and pressing "**s**".

The options one can set are:

1. **Server IP** \
This can either be **localhost** (the server will be accessible from the current system only) or **LAN** (the server will be accessible from any PC on the local network).

2. **Server Port** \
This is the port the server is listening to. Any free port number between 1025 and 65535 can be set here (default value is 9998).

3. **Auto-start Server** \
This option is available in the config only. If set to True, the server will be automatically started when **PyRadio** starts.

After the server is up, pressing "**\\s**" will display the following window:

![Pyradio](https://members.hellug.gr/sng/pyradio/server-on.jpg)


This window will display both the server's **Text** and **Web** address.

### Using the Web Server

So, inserting the **Web** address displayed in the previous window in a web browser will result to the output shown at the left of following image, (which is actually a screenshot of my mobile phone).

![Pyradio](https://members.hellug.gr/sng/pyradio/phone.jpg)

The idea is that while **PyRadio** is running on the PC, people relaxing on the sofa, chilling with friends, listening to music from their favorite radio station, being able to increase / decrease the volume, change stations, etc. using their phones.

The available commands are "encoded" in the buttons shown on the screen; the right part of the image shows the output of the "**Stations List**" button. To start a station, I would just click (well, tap) on its name, and viola!

The **Web** interface will also show the song's title, if availabe, or the name of the station that's playing, if it's not. In order to achieve this functionality, *javascript* is heavily used, so one should keep that in mind (in case *javascript* has been disabled in the browser, for example).

### Using the Text Server

Why having the **Text** interface as well, one might ask...

Well, first of all it's lighter, then one can use it to locally control **PyRadio** from a script and provide a way to adjust the volume for example, using some assigned shortcut key combination.

Inserting the **Text** address on a terminal using *curl* or *wget* or any similar software:

```
$ curl http://192.168.122.4:9998
```

or

```
$ wget http://192.168.122.4:9998  -q -O -
```

would result to displaying the list of available commands:

```
PyRadio Remote Service

Global Commands
Long             Short      Description
--------------------------------------------------------------------
/info            /i         display PyRadio info
/volumeup        /vu        increase volume
/volumedown      /vd        decrease volume
/vulumesave      /vs        save volume
/mute            /m         toggle mute
/log             /g         toggle stations logging
/like            /l         tag (like) station

Restricted Commands (Main mode only)
--------------------------------------------------------------------
/toggle          /t         toggle playback
/playlists       /pl        get playlists list
/playlists/x     /pl/x      get stations list from playlist id x
                            (x comes from command /pl)
/playlists/x,y   /pl/x,y    play station id y from playlist id x
/stations        /st        get stations list from current playlist
/stations/x      /st/x      play station id x from current playlist
/next            /n         play next station
/previous        /p         play previous station
/histnext        /hn        play next station from history
/histprev        /hp        play previous station from history
```

The "**Restricted Commands**" will not work in **Playlist mode**; the "**Global Commands**" will work everywhere.

### Examples

The following commands will increase / decrease the volume and mute the player:

```
$ curl http://192.168.122.4:9998/vu
$ wget http://192.168.122.4:9998/vd  -q -O -
$ wget http://192.168.122.4:9998/m  -q -O -
```

The following command will display the contents of the loaded playlist:

```
$ curl http://192.168.122.4:9998/st
```

The stations will be numbered, like so:

```
Stations List for Playlist: "stations"
   1. Alternative (BAGeL Radio - SomaFM)
   2. Alternative (The Alternative Project)
  ...
  17. Jazz (Sonic Universe - SomaFM)
+ 18. Lounge (Illinois Street Lounge - SomaFM)
  19. Pop (PopTron! - SomaFM)
  20. Pop/Rock/Urban  (Frequence 3 - Paris)
  ...
> 34. Echoes of Bluemars - Cryosleep
  34. Echoes of Bluemars - Voices from Within
First column
  [> ]: Selected, [+ ]: Playing, [+>]: Both
```

so that in order to start playing station No 20, for example, one would just use the command:

```
$ curl http://192.168.122.4:9998/st/20
```

### Text vs. Web commands

On first glance, the difference between a **Text** and a **Web** command is the */html* part that exists in the later.

But things are actually more complex that that.

For example, when the */st* command is issued, the server will return the list of stations as text and keep listening for connections. In this case, one requests has been made to the server and one response has been returned.

Now, if the */html/st* command was issued, the server will return the same list, but formatted as html, so that a browser can correctly display it.

This output would pretty much be unusable to a user issuing the "**html**" command on a terminal.

Furthermore, using it from a browser, clicking or tapping the corresponding button, will lead to a number of requests from the browser to the server (requesting the mute status, the player's status, the song's title, etc.).


