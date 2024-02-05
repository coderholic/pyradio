# PyRadio Remote Control Server

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Remote Control Server](#remote-control-server)
    * [Using the Web Server](#using-the-web-server)
        * [Web Interface buttons](#web-interface-buttons)
    * [Using the Text Server](#using-the-text-server)
    * [Server lock file](#server-lock-file)
    * [Examples](#examples)
    * [Text vs. Web commands](#text-vs.-web-commands)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#remote-control-server) ]

## Remote Control Server

**PyRadio** can be controlled remotely using normal http requests either form the command line (with *curl* for example) or from a browser.

For this purpose, a simple web server has been integrated in **PyRadio**; this server can be started

- automatically \
Setting the **Remote Control Server** options ins the config file, especially setting the **Auto-start Server** to **True**, or
- by pressing "**\\s**" at the main window, selecting the desired options and pressing "**s**".

The options one can set are:

1. **Server IP** \
This can either be **localhost** (the server will be accessible from the current system only) or **LAN** (the server will be accessible from any PC on the local network). \
\
If the machine has more that one interface (network card), the actual IPs will be available for selection as well.

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

#### Web Interface buttons

The buttons shown in the web interface are:

- **Local Playlist** \
This button will permit the user to toggle between opening a local playlist (default state) and a **RadioBrowser** "playlist", actually a search result set of players.

- **Play Next** and **Play Previous** \
The buttons title says it all... \
Subsequent clicks on a button will only be accepted after the player has "settled", i.e. either started playing or failed to connect to the station.

- **Play Hist. Next** and **Play Hist. Previous** \
Same as above, but stations will come from the "**station history**" instead of the current playlist.

- **Toggle Playback** \
Nothing more to say here; start/stop the player.

- **Volume Up** and **Volume Down**, **Save Volume**, **Mute Player** \
These are the volume adjustment, saving and muting the player functions.

- **Show Stations** \
Clicking this buttons will present the list of stations in the current playlist (or search result). Clicking on a station name will start its playback.

- **Show Groups** \
This will display, and permit the selection of the groups defined within a playlist. When a group name is selected, the list of players will be opened and scrolled to the beginning of the group.

- **Show Playlists** \
This will show a list of the playlists already composed by the user. Clicking on a playlist's name will open the playlist; the stations will be available through the **Show Stations**. \
\
When **RadioBrowser** is active, the button's label will change to **Show Searches**. When clicked, the list of existing search items will be presented to the user; clicking on an item will preform the search and results can be displayed by clicking on the **Show Stations** button. \
\
No new items can be inserted using the web interface.

- **Enable Title Log** \
This will enable or disable the titles logging function.

- **Like Title** \
This will "like" the current (song).

- **System Info** \
This will display useful info about **PyRadio**.

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
Long                  Short        Description
---------------------------------------------------------------------------
/info                 /i           display PyRadio info
/volume               /v           show volume (text only)
/set_volume/x         /sv/x        set volume to x% (text only)
/volumeup             /vu          increase volume
/volumedown           /vd          decrease volume
/volumesave           /vs          save volume
/mute                 /m           toggle mute
/log                  /g           toggle stations logging
/like                 /l           tag (like) station
/title                             get title (HTML format)

Restricted Commands (Main mode only)
---------------------------------------------------------------------------
/toggle               /t           toggle playback
/playlists            /pl          get playlists list
/playlists/x          /pl/x        get stations list from playlist id x
                                     (x comes from command /pl)
/playlists/x,y        /pl/x,y      play station id y from playlist id x
/stations             /st          get stations list from current playlist
/stations/x           /st/x        play station id x from current playlist
/next                 /n           play next station
/previous             /p           play previous station
/histnext             /hn          play next station from history
/histprev             /hp          play previous station from history
/open_rb              /orb         open RadioBrowser
/close_rb             /crb         close RadioBrowser
/list_rb              /lrb         list RadioBrowser search items
/search_rb/[x]        /srb/[x]     execute RadioBrowser search item x
                                     (x comes from /lrb - execute default
                                      search item if not specified)
/rb_page              /grb         get RadioBrowser searh results page number
/rb_first_page        /frb         load RadioBrowser first results page
/rb_next_page         /nrb         load RadioBrowser next results page
/rb_previous_page     /prb         load RadioBrowser previous results page
```

The "**Restricted Commands**" will not work in **Playlist mode**; the "**Global Commands**" will work everywhere.

### Server lock file

When the server is up and running, a "server lock file" will be created; the file is named **~/.config/pyradio/data/server.txt** and contains the IP address and port the server is listening to; this is especially useful for user scripts that want to get hold of this information.

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

The following command will get the current song title:

```
$ curl http://192.168.122.4:9998/title

retry: 150
event: /html/title
data: <b>Patti Page - Jingle bells</b>

```

The **data** field will contain the HTML format of the title, which is easy to parse in a script.

If the player is idle, the output will be

```
$ curl http://192.168.122.192.168.122.4tle
retry: 150
event: /html/title
data: <b>Player is stopped!</b>
```

Several commands (such as **/v**, **/vu**, **/vd**, etc.) will return this info; this is a side effect of the way the server works, but provides useful info for the script issuing the command.

One thing that should be made clear is that getting the above info does not mean that the command has succeeded; for example issuing the **/orc** (**/open-radio-browser**) command, will return the above info, but to make sure about the state of **PyRadio**, one should issue the **/i** (**/info**) command:

```
$ curl http://192.168.122.4:9998/i
PyRadio 0.9.2.20
  Player: mpv
  Service: RadioBrowser (Netherlands)
    Search: Name: christmas, Order: votes, Reverse: true
  Status: In playback
    Station (id=5): "Classical Christmas FM"
    Title: Patti Page - Jingle bells
  Selection (id=5): "Classical Christmas FM"
```

### Text vs. Web commands

On first glance, the difference between a **Text** and a **Web** command is the */html* part that exists in the later.

But things are actually more complex that that.

For example, when the */st* command is issued, the server will return the list of stations as text and keep listening for connections. In this case, one requests has been made to the server and one response has been returned.

Now, if the */html/st* command was issued, the server will return the same list, but formatted as html, so that a browser can correctly display it.

This output would pretty much be unusable to a user issuing the "**html**" command on a terminal.

Furthermore, using it from a browser, clicking or tapping the corresponding button, will lead to a number of requests from the browser to the server (requesting the mute status, the player's status, the song's title, etc.).

