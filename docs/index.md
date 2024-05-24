# PyRadio

Command line internet radio player.

![Pyradio](https://members.hellug.gr/sng/pyradio/pyradio.png)

## IMPORTANT NOTICE 1

**PyRadio** may fail to install/update on some linux distros (mainly Ubuntu 23.04, Debian and derivatives, etc.) due to a change to the underlined python installation.

If you face this situation, please refer to [this page](pip-error.md) to resolve the problem.

## IMPORTANT NOTICE 2 (v. 0.9.3)

This is a big update, with heavy refactoring and introducing a lot of new concepts, so I expect to have a lot of BUG reports.

Please be kind ;)

Once you execute **PyRadio v. 0.9.3** these things will happen:

1. Your *recordings* dir will be moved to your home folder and renamed to *pyradio-recordings*.

2. Your **titles log** files will be moved to the new **Recordings Dir**.

3. **PyRadio's** cache will be moved to *~/.cache/pyradio* (**not on Windows**).

If you are using a **Linux Distro Package**, there's a chance the packager has decided to enable support for the [XDG Base Directory specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html).

In this case:

1. most of the files that reside in *~/config/pyradio* and *~/.config/pyradio/data* will be moved to **~/.local/share/pyradio** or  **~/.local/state/pyradio**.

2. Any file that you may have saved under *~/.config/pyradio* and has not been created by **PyRadio**, will be moved into a folder called **pyradio-not-migrated** in your home folder.

3. Your *~/.config/pyradio/data* folder will be removed.

4. All your playlists and the main configuraton files will remain in *~/.config/pyradio*.

## IMPORTANT NOTICE 3 (headles v. 0.9.3)

If you use the "headless" functionality and upgrading to v. 0.9.3, please keep in mind that a headless session will not perform any of the tasks described in **NOTICE 2**, leading to unpredictable result.

To ensure the correct operation, please take these actions:

1. Terminate headless instance of **PyRadio**.

2. Execute **PyRadio** in a terminal at least once, permitting the directory changes to take effect.

3. Start a new headless instance of **PyRadio**.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Features](#features)
* [Requirements](#requirements)
* [Installation](#installation)
* [Command line options](#command-line-options)
* [Controls](#controls)
    * [Global shortcuts](#global-shortcuts)
* [HTML help](#html-help)
* [PyRadio Modes](#pyradio-modes)
    * [Secondary Modes](#secondary-modes)
    * [Tiling manager modes](#tiling-manager-modes)
* [Config file](#config-file)
    * [The package config file](#the-package-config-file)
    * [The user config file](#the-user-config-file)
* [About Playlist files](#about-playlist-files)
    * [Defining and using Groups](#defining-and-using-groups)
    * [Integrating new stations](#integrating-new-stations)
    * [Specifying a playlist to load (command line)](#specifying-a-playlist-to-load-(command-line))
    * [Autoloading playlists](#autoloading-playlists)
    * [Managing playlists (within PyRadio)](#managing-playlists-(within-pyradio))
    * [Managing "foreign" playlists](#managing-"foreign"-playlists)
    * [Playlist history](#playlist-history)
* [Stations history](#stations-history)
* [Search function](#search-function)
* [Line editor](#line-editor)
    * [CJK characters support](#cjk-characters-support)
* [Moving stations around](#moving-stations-around)
* [Specifying stations' encoding](#specifying-stations'-encoding)
    * [Station by station encoding declaration](#station-by-station-encoding-declaration)
    * [Global encoding declaration](#global-encoding-declaration)
* [Player detection / selection](#player-detection-/-selection)
    * [Changing player mid-session](#changing-player-mid-session)
    * [Extra Player Parameters](#extra-player-parameters)
        * [Using the Configuration Window](#using-the-configuration-window)
* [Player connection protocol](#player-connection-protocol)
    * [Visual reminder](#visual-reminder)
* [Player default volume level](#player-default-volume-level)
    * [MPV](#mpv)
    * [MPlayer](#mplayer)
    * [VLC](#vlc)
* [Buffering](#buffering)
    * [Parameters used](#parameters-used)
    * [Customizing the buffering behavior](#customizing-the-buffering-behavior)
    * [How it works](#how-it-works)
* [Displaying Station Info](#displaying-station-info)
* [Copying and pasting - Registers](#copying-and-pasting---registers)
* [PyRadio Themes](#pyradio-themes)
* [Recording stations](#recording-stations)
* [Mouse support](#mouse-support)
* [Title logging](#title-logging)
    * [Tagging a title](#tagging-a-title)
* [Online radio directory services](#online-radio-directory-services)
* [Desktop Notifications](#desktop-notifications)
* [Desktop File](#desktop-file)
    * [Specifying the terminal to use](#specifying-the-terminal-to-use)
        * [Specifying PyRadio parameters](#specifying-pyradio-parameters)
* [Session Locking](#session-locking)
    * [Session unlocking](#session-unlocking)
* [Update notification](#update-notification)
* [Remote Control Server](#remote-control-server)
    * [Remote Control Client](#remote-control-client)
* [Debug mode](#debug-mode)
* [Reporting bugs](#reporting-bugs)
* [Packaging PyRadio](#packaging-pyradio)

<!-- vim-markdown-toc -->

## Features

**PyRadio** provides the following features:

 - vi like keys in addition to arrows and special keys
 - [RadioBrowser](docs/radio-browser.md) support
 - Remote Control Server
 - Multiple playlist support
 - vi like station registers
 - Theming support
 - Station editor (add/edit) with [CJK characters support](#cjk-characters-support)
 - Configuration editor
 - Search function
 - Easy installation / updating
 - Runs on Linux, macOS and Windows

and much more...

## Requirements
* python 3.7+
    - setuptools
    - wheel
    - requests
    - dnspython
    - psutil
    - rich
    - python-dateutil
    - netifaces
* MPV, MPlayer or VLC installed and in your path
* MKVToolNix (cli files) to insert tags, chapters and cover to recordings (optional, if MPV or VLC is to be used, but mandatory in the case of MPlayer)

Linux users will have to install a [resource opener](https://wiki.archlinux.org/title/default_applications#Resource_openers) package, a utility to open directories, html pages, etc. **PyRadio** will look for *xdg-open*, *gio*, *mimeopen*, *mimeo* or *handlr*, in that order of detection. If a different *resource opener* is used, one can declare it in the **Configuration Window**.

<!-- Changelog -->

## Installation

The best way to install **PyRadio** is via a distribution package, if one exists (*Arch Linux* and derivatives can install [any of these packages](https://aur.archlinux.org/packages/?K=pyradio) from the AUR, *FreeBSD* users will find it in the [ports](https://www.freshports.org/audio/py-pyradio/), etc.).

In any other case, and since **PyRadio** is currently not available via pip, you will have to [build it from source](build.md).

## Command line options

```
Usage: pyradio [-h] [-c CONFIG_DIR] [-p [STATION_NUMBER]] [-u PLAYER] [-a]
               [-l] [-lt] [-sd] [-od] [-pc] [-d] [-ul] [-us] [-U] [-R] [-V]
               [-ls] [-s PLAYLIST] [-tlp] [-t THEME] [--show-themes]
               [--no-themes] [--write-theme IN_THEME OUT_THEME,]
               [--terminal TERMINAL] [--terminal-param TERMINAL_PARAM] [-oc]
               [-sc] [-cc] [-gc] [-r] [-or] [-lr] [-mkv MKV_FILE]
               [-scv PNG_FILE] [-srt] [-ach] [--headless IP_AND_PORT]
               [--address] [-fd]

Curses based Internet Radio Player

General options:
  -h, --help            Show this help message and exit
  -c CONFIG_DIR, --config-dir CONFIG_DIR
                        Use specified configuration directory instead of the
                        default one. PyRadio will try to create it, if it does
                        not exist. Not available on Windows.
  -p [STATION_NUMBER], --play [STATION_NUMBER]
                        Start and play.The value is num station or empty for
                        random.
  -u PLAYER, --use-player PLAYER
                        Use specified player. A comma-separated list can be
                        used to specify detection order. Supported players:
                        mpv, mplayer, vlc.
  -a, --add             Add station to list.
  -l, --list            List of available stations in a playlist.
  -lt, --log-titles     Log titles to file.
  -sd, --show-config-dir
                        Print config directory [CONFIG DIR] location and exit.
  -od, --open-config-dir
                        Open config directory [CONFIG DIR] with default file
                        manager.
  -pc, --print-config   Print PyRadio config.
  -d, --debug           Start PyRadio in debug mode.
  -ul, --unlock         Remove sessions' lock file.
  -us, --update-stations
                        Update "stations.csv" (if needed).
  -U, --update          Update PyRadio.
  -R, --uninstall       Uninstall PyRadio.
  -V, --version         Display version information.

Playlist selection:
  -ls, --list-playlists
                        List of available playlists in config dir.
  -s PLAYLIST, --stations PLAYLIST
                        Load the specified playlist instead of the default
                        one.
  -tlp, --toggle-load-last-playlist
                        Toggle autoload last opened playlist.

Themes:
  -t THEME, --theme THEME
                        Use specified theme.
  --show-themes         Show Internal and System Themes names.
  --no-themes           Disable themes (use default theme).
  --write-theme IN_THEME OUT_THEME,
                        Write an Internal or System Theme to themes directory.

Terminal selection:
  --terminal TERMINAL   Use this terminal for Desktop file instead of the
                        auto-detected one. Use "none" to reset to the default
                        terminal or "auto" to reset to the auto-detected one.
  --terminal-param TERMINAL_PARAM
                        Use this as PyRadio parameter in the Desktop File.
                        Please replace hyphens with underscores when passing
                        the parameter, for example: --terminal-param "_p 3 _t
                        light" (which will result to "pyradio -p 3 -t light").

Cache:
  -oc, --open-cache     Open the Cache folder.
  -sc, --show-cache     Show Cache contents.
  -cc, --clear-cache    Clear Cache contents.
  -gc, --get-cache      Download source code, keep it in the cache and exit.

Recording stations:
  -r, --record          Turn recording on (not available for VLC player on
                        Windows).
  -or, --open-recordings
                        Open the Recordings folder.
  -lr, --list-recordings
                        List recorded files.
  -mkv MKV_FILE, --mkv-file MKV_FILE
                        Specify a previously recorded MKV file to be used with
                        one of the following options. The MKV_FILE can either
                        be an absolute or a relative path, or a number
                        provided by the -lr command line paremater. If it is a
                        relative path, it should be found in the current or in
                        the Recordings directory.
  -scv PNG_FILE, --set-mkv-cover PNG_FILE
                        Add or change the cover image of a previously recorded
                        MKV file. PNG_FILE can either be an absolute or a
                        relative path. If relative, it should be found in the
                        current or in the Recordings directory.
  -srt, --export-srt    Export a previously recorded MKV file chapters to an
                        SRT file. The file produced will have the name of the
                        input file with the "mkv" extension replaced by "srt".
  -ach, --add-chapters  Add (or replace) chapter markers to a previously
                        recorded MKV file. The chapters file will be a SRT
                        file, much like the one produced by the previous
                        command line parameter.

Headless operation:
  --headless IP_AND_PORT
                        Start in headless mode. IP_AND_PORT can be a) auto
                        (use localhost:11111), b) localhost:XXXXX (access the
                        web server through localhost), c) lan:XXXXX (access
                        the web server through the LAN) or d) IP_ADDRESS:XXXX
                        (the IP_ADDRESS must be already assigned to one of the
                        network interfaces). XXXXX can be any port number
                        above 1025. Please make sure it is different than the
                        one set in the configuration file.
  --address             Show remote control server address.
  -fd, --free-dead-headless-server
                        Use this if your headless server has terminated
                        unexpectedly, and you cannot start a new one (you get
                        a message that it is already running).

```

## Controls

                      Main window                                      Playlists window                   Themes window
    -------------------------------------------------------------------------------------------------------------------------------------
    Up/Down/j/k/
    PgUp/PgDown       Change station selection                         Change station playlist            Change station theme
    g                 Jump to first station                            Jump to first playlist             Jump to first theme
    <n>G              Jump to n-th / last station                      Jump to n-th / last playlist       Jump to n-th / last theme
    H M L             Jump to the top / middle bottom of the list      [Valid]                            -
    P                 Jump to playing station                          Jump to playing playlist           -
    Enter/Right/l     Play selected station                            Open selected playlist             Apply selected theme
    ^N / ^P           Play next/previous station                       -                                  -
    r                 Select and play a random station                 Re-read playlists from disk        -
    Space/Left/h      Stop/start playing selected station              -                                  -
    Space             -                                                -                                  Apply theme and make it default
    -/+ or ,/.        Change volume                                    [Valid]                            [Valid]
    m                 Mute / unmute player                             [Valid]                            [Valid]
    v                 Save volume (not applicable for vlc)             [Valid]                            [Valid]
    o s R             Open / Save / Reload playlist                    -                                  -
    a A               Add / append a new station                       -                                  -
    e                 Edit current station                             -                                  -
    E                 Change station's encoding                        -                                  -
    DEL,x             Delete selected station                          -                                  -
    O                 Open RadioBrowser                                -                                  -
    < >               Browse the Stations history list                 -                                  -
    t T               Load theme / Toggle transparency                 [Valid]                            [Valid]
    c                 Open Configuration window.                       -                                  -
    | (vertical       Enable / disable recording
       line or
       pipe symbol)
    / n N             Search, go to next / previous result             [Valid]                            [Valid]
    J                 Create a jump tag
    <n>^U <n>^D       Move station up / down.                          -                                  -
    ' \ y             Get into Registers, Extra Commands               y (yank) is not applicable         -
                      and Yank modes, respectively
    z                 Toggle "Force http connections"                  -                                  -
    Z                 Display the "Extra Player Parameter" window      -                                  -
    ?                 Show keys help                                   [Valid]                            [Valid]
    #                 Redraw window                                    [Valid]                            [Valid]
    Esc/q             Quit                                             -                                  -
    Esc/q/Left/h      -                                                Cancel / close window              Cancel / close window

The same logic applies to all **PyRadio** windows.

**Note:** When inserting numbers (either to jump to a station or to move a station), the number will be displayed at the right bottom corner of the window, suffixed by a "*G*", i.e. pressing *35* will display *[35G]*.

**Note:** When tagging a station position for a move action (by pressing "**J**"), the position will be displayed at the right bottom corner of the window, suffixed by a "*J*", i.e. pressing "*J*" on position *35* will display *[35J]*.


### Global shortcuts

Some of the functions provided by **PyRadio** will always be available to the user. These functions are:

| Shortcut                       |   Function            |Shortcut                       |   Function            |
|--------------------------------|-----------------------|-------------------------------|-----------------------|
| **\+** / **\-** and **,** / **\.** | adjust volume         |**W**                          | toggle title logging |
| **m**                          | mute player           |**w**                          | like a station        |
| **v**                          | save volume           |**^N** / **^P** [1] [2]|play next / previous station|
| **T**                          | toggle transparency   |**<** / **>** [1]             | play next / previous station history entry|

Every window in **PyRadio** will respect these shortcuts, even the ones with a "*Press any key to...*" message.

When focus is on a "*Line editor*", all shortcuts will work when preceded by a "**\\**".

**Notes**

[1] Function not available when in **Playlist** and **Registers** mode. More info on *PyRadio's modes* below.

[2] Function not available in the **RadioBrowser** Search window.

## HTML help

While in **PyRadio** main window, one can open the HTML (offline) help using "**\\h**".

This is just a helper function for windows users who cannot use the man pages, but is still available for all platforms.

## PyRadio Modes

**PyRadio** has the following primary modes:

1. The **Main** mode, which is the one you get when you open the program, showing you a list of stations (a playlist), that you can play and edit; this is why it is also called the **editing mode**. All other modes derive from this one, and it's the mode you have to get to in order to terminate the program.

2. The **Playlist** mode, which you can open by pressing "**o**". Then you can open, create, paste a station, etc.

3. The **Registers** mode. This is identical to the "*Playlist*" mode, but instead of displaying playlists, it displays register. You can enter this mode by pressing "**''**" (two single quotes) and exit from it by pressing "**Esc**" or "**q**". You can also press "**'**" (single quote) to get to the **Playlist** mode and back.

4. The **Register Main** mode, which is identical to the "*Main*" mode, except it displays the content of a **named** register.

5. The **Listening** mode, which is intended to be used when you want **PyRadio** to just play your favorite station and not take up too much space. It is ideal for tilling window manager use, as the whole TUI can be reduced all the way down to a single line (displaying the "*Status Bar*"). In this mode, adjusting, muting and saving the volume are the only action available. To get **PyRadio** back to normal operation one would just resize its window to a reasonable size (7 lines vertically, or more).

### Secondary Modes

A set of **secondary modes** is also available (a secondary mode works within a primary one):

1. The **Extra Commands** mode, which gives you access to extra commands. You can enter this mode by pressing "**\\**" (backslash). Then a backslash is displayed at the bottom right corner of the window.

2. The **Yank (Copy)** mode, which is used to copy stations to **registers**. You can enter this mode by pressing "**y**". Then a "*y*" is displayed at the bottom right corner of the window.

3. The **Open Register** mode, which is used to open a register or get into the *Registers* mode. You can enter this mode by pressing "**'**" (single quote). Then a single quote is displayed at the bottom right corner of the window.

4. The **Paste** mode, which is available in the *Station editor* window only. It is designed to help the user paste a URL (and optionally a station's name). Why you might ask... Well, the *Station editor* normally treats the "*?*" and "*\\*" characters as special characters (actually commands). So, if a URL which contains these characters (more frequently the "*?*" character) is pasted it will be corrupted unless the **Paste** mode is enabled.

The functions available through the *secondary modes* are content dependent, so you can see what command is available by pressing "**?**" while within a secondary mode. Pressing any other key will exit the secondary mode.

### Tiling manager modes

These modes are specifically designed to be used with tiling window managers, trying to face a rapid reduction of window height or width (or both).

1. The **Limited Height** mode, which is automatically enabled when the window height gets below 8 lines.

    - In this mode, only a limited information is visible and if playback is on, the volume is the only thing that can be adjusted (or muted) and saved. This is the **Limited display**.

2. The **Limited Width** mode, which is automatically enabled when the window width get below certain limits:

    - When the width gets below 40 columns, all windows will be closed and the main window will be the only visible one (either displaying stations, playlists or registers).

    - When the width gets below 20 columns, the **Limited display** will be activated.

![Pyradio reduced to the "Limited display"](https://members.hellug.gr/sng/pyradio/pyradio-limited-display.jpg)

**Note:** These two modes do not work on Windows, either 7 or 10. The "*Console*"window will shrink as desired, but will not always notify **PyRadio** about it, so results will vary.

## Config file

**PyRadio** upon its execution will first read its *package* configuration file and then will try to read the *user* configuration file. If an error occurs while parsing it, an error message will be displayed and **PyRadio** will terminate.

### The package config file

The *package* configuration file contains the program's **default** parameters. These are the player to use, the playlist to load etc.

It is heavily commented (as you can see [here](pyradio/config)), so that it can be used as a template in order to manual create the *user* configuration file.

One can also get the configuration file with the **active parameter values** (i.e. after changed by the *user* config file), by executing the command:

    pyradio -pc

### The user config file

This file (typically *~/.config/pyradio/config*) is created by **PyRadio** when needed.

It will contain only the parameters whose value is different to the one set in the *package* configuration file.

One can easily edit it manually, though. The best practice to do so is by executing **PyRadio** with the **-ocd** command line option, which will open the configuration directory in your file manager, and then edit (or create it) it using your preferable text editor. Don't forget you can get the list of parameters by executing **pyradio -pc**.

The file can also be altered while **PyRadio** is running by pressing "**c**", which will open the "**Configuration window**". This window presents all **PyRadio** options and provide the way to change them and finally save them by pressing "**s**".

In any case, **PyRadio** will save the file before exiting (or in case Ctrl-C is pressed) if needed (e.g. if a config parameter has been changed during its execution).

If saving the configuration file fails, **PyRadio** will create a back up file and terminate. When restarted, **PyRadio** will try to restore previously used settings from the said back up file.

## About Playlist files

**PyRadio** reads the stations to use from a CSV file, where each line contains two columns, the first being the station name and the second being the stream URL.

Optionally, two more columns can be used.

The third column will define the encoding used by the station (more on this at [Specifying stations' encoding](#specifying-stations-encoding)).

The fourth column will set an  *Icon URL*, to be used when displaying [Desktop Notifications](#desktop-notifications).

**PyRadio** will by default load the user's stations file (e.g. *~/.config/pyradio/stations.csv*) to read the stations from. If this file is not found, it will be created and populated with a default set of stations.

**Note:** Older versions used to use **~/.pyradio** as default stations file. If this file is found, it will be copied to use's config directory (e.g. **~/.config/pyradio**) and renamed to **stations.csv** or if this file exists, to **pyradio.csv**. In this case, this file will be the default one.

### Defining and using Groups

In order to better organize stations within a (large) playlist, **PyRadio** supports *Groups*.

A *Group* is defined as a normal "station" entry, whose URL field is a hyphen ("**-**"). For example, the following will define a **Group Header** for a *Group* called **Blues**.

    Blues,-

A **Group Header** entry does not define a station, and subsequently cannot stat a playback session. Other that that, it can be moved, copied, deleted, etc, just like any other playlist entry.

To add a **Group Header**, just press "**a**", fill in the name and type a "**-**" in the *URL* field.

Navigation among **Groups** can be achieved by:

| Key             | Description                                          |
|-----------------|------------------------------------------------------|
| **^E** / **^Y** | Go to next / previous **Group**                      |
| **^G**          | Display a list of existing **Groups** to select from |


### Integrating new stations

When the package's "*stations.csv*" files is updated, the changes it has will not automatically appear in the user's stations file.

**PyRadio** will display a message asking the user to either update the file, ignore the changes for this version or postpone his decision for the next time **PyRadio** will be executed.

![Pyradio stations update](https://members.hellug.gr/sng/pyradio/pyradio-stations-update.png)

Either way, the user can always manually update his **stations file**, by issuing the following command:

```
pyradio -us
```

If changes have been applied, a message resembling the following will appear:

```
Reading config...
Updating "stations.csv"
Last updated version: 0.9.2
 Last synced version: None
  From version: 0.9.2
    +/- updating: "Reggae Dancehall (Ragga Kings)"
    +++   adding: "Groove Salad Classic (Early 2000s Ambient)"
    +++   adding: "n5MD Radio (Ambient and Experimental)"
    +++   adding: "Vaporwaves [SomaFM]"
    +++   adding: "The Trip: [SomaFM]"
    +++   adding: "Heavyweight Reggae"
    +++   adding: "Metal Detector"
    +++   adding: "Synphaera Radio (Space Music)"

Summary
    +++ added   :  7
    +/- updated :  1
    --- deleted :  0
```

If the file is already up to date, the following message will be displayed:

```
Reading config...
Updating "stations.csv"
Last updated version: 0.9.2
 Last synced version: 0.9.2
Already synced: "stations.csv"
```

### Specifying a playlist to load (command line)

**PyRadio** will normally load its default playlist file, as described above, upon its execution. A different file can be loaded when the **-s** command line option is used.

The **-s** option will accept:

* a relative or absolute file name.
* the name of a playlist file which is already in its configuration directory.
* the number of a playlist file, as provided by the **-ls** command line option.

Examples:

To load a playlist called "**blues.csv**", one would use the command:

    pyradio -s /path/to/blues.csv

If this file was saved inside **PyRadio**'s configuration directory, one could use the following command:

    pyradio -s blues

To use the playlist number, one would execute the commands:

    $ pyradio -ls

           Playlists found in "/home/user/.config/pyradio"
           ┏━━━━┳━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┓
           ┃  # ┃ Name     ┃    Size ┃ Date                     ┃
           ┡━━━━╇━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━┩
           │  1 │ hip-hop  │ 6.41 KB │ Mon Nov  7 18:17:47 2022 │
           │  2 │ party    │ 1.94 KB │ Fri Nov 29 10:49:39 2021 │
           │  3 │ stations │ 5.30 KB │ Sat Jul 18 23:32:04 2022 │
           │  4 │ huge     │ 1.94 MB │ Wed Oct 23 11:05:09 2019 │
           │  5 │ blues    │ 5.30 KB │ Thu Jul 16 16:30:51 2020 │
           │  6 │ rock     │ 2.56 KB │ Fri Jan 10 00:20:07 2023 │
           │  7 │ pop      │ 1.01 KB │ Fri Sep 18 00:06:51 2020 │
           └────┴──────────┴─────────┴──────────────────────────┘

    $ pyradio -s 5

**Note:** The default playlist to load can also be set in **PyRadio**'s [configuration file](#config-file), parameter **default_playlist** (default value is **stations**).

### Autoloading playlists

As already stated, **PyRadio** will normally load its default playlist (called "**stations**") upon startup.

This behavior can be then changed in two ways:

1. Changing the default playlist.

    This is accomplished using the "**Def. playlist**" configuration option (optionally along with the "**Def. station**" option).

2. Always loading the last used playlist at startup.

    This is accomplished using the "**Open last playlist**" configuration option.

    In this case, the last used playlist will be opened the next time **PyRadio** will be executed, trying to restore the previously selected station or starting playback.

    This option will take precedence before the "**Def. playlist**" configuration option (if it is used) and the "**-s**" ("**--stations**") command line option.

**Note:** When the "**Open last playlist**" configuration option is set, all playlist operations will be performed to the last opened playlist. In order to use the "**-a**" ("**--add**") or "**-l**" ("**--list**") command line options along with the "**-s**" ("**--stations**") command line option, the "**-tlp**" ("**--toggle-load-last-playlist**") option can be used to temporarily deactivate autoloading.

### Managing playlists (within PyRadio)

Once **PyRadio** has been loaded, one can perform a series of actions on the current playlist and set of playlists saved in its configuration directory.

Currently, the following actions are available:

Pressing "**a**" or "**A**" will enable you to add a new station (either below the currently selected station or at the end of the list), while "**e**" will edit the currently selected station. All of these actions will open the "*Station editor*".

If you just want to change the encoding of the selected station, just press "**E**". If the station is currently playing, playback will be restarted so that the encoding's change takes effect (hopefully correctly displaying the station/song title).

Then, when this is done, you can either save the modified playlist, by pressing "**s**", or reload the playlist from disk, by pressing "**R**". A modified playlist will automatically be saved when **PyRadio** exits (or Ctrl-C is pressed).

One thing you may also want to do is remove a station from a playlist, e.g. when found that it not longer works. You can do that by pressing "**DEL**" or "**x**". The deleted station is copied to the **unnamed register** (refer to section [Copying and pasting - Registers](#copying-and-pasting---registers) for more information).

Finally, opening another playlist is also possible. Just press "**o**" and you will be presented with a list of saved playlists to choose from. These playlists must be saved beforehand in **PyRadio**'s configuration directory.

While executing any of the previous actions, you may get confirmation messages (when opening a playlist while the current one is modified but not saved, for example) or error messages (when an action fails). Just follow the on screen information, keeping in mind that a capital letter as an answer will save this answer in **PyRadio**'s configuration file for future reference.

### Managing "foreign" playlists

A playlist that does not reside within the program's configuration directory is considered a "**foreign**" playlist. This playlist can only be opened by the "**-s**" command line option.

When this happens, **PyRadio** will offer you the choice to copy the playlist in its configuration directory, thus making it available for manipulation within the program.

If a playlist of the same name already exists in the configuration directory, the "**foreign**" playlist will be time-stamped. For example, if a "**foreign**" playlist is named "*stations.csv*", it will be named "*2019-01-11_13-35-47_stations.csv*" (provided that the action was taken on January 11, 2019 at 13:35:47).

### Playlist history

**PyRadio** will keep a history of all the playlists opened (within a given session), so that navigating between them is made easy.

In order to go back to the previous playlist, the user just has to press "**\\\\**" (double backslash). To get to the first playlist "**\\]**" (backslash - closing square bracket) can be used.

Going forward in history is not supported.

## Stations history

Playing several stations, sometimes among different playlists, and returning to them is sometimes a tedious operation.

This problem is addressed with the "**Station history**" functionality, which is actually a list of stations which have been played back.

The user can go back and forth in this list using the "**<**" and "**>**" keys.

The list is not saved between sessions (restarting the program will lead to an empty list). When an "**online service** is used (e.g. **RadioBrowser**) the list is reseted with every search that is performed.

## Search function

On any window presenting a list of items (stations, playlists, themes) a **search function** is available by pressing "**/**".

The *Search Window* supports normal and extend editing and in session history.

One can always get help by pressing the "**?**" key.

After a search term has been successfully found (search is case insensitive), next occurrence can be obtained using the "**n**" key and previous occurrence can be obtained using the "**N**" key.

All search widgets provide a "*search history*" function; pressing the **Up** or **Down** arrow will cycle through previously used search terms (maximum number remembered is 20). Pressing **^X** will remove an item from the history.

## Line editor

**PyRadio** "*Search function*" and "*Station editor*" use a *Line editor* to permit typing and editing stations' data.

One can always display help by pressing "**?**", but that pauses a drawback; one cannot actually have a "**?**" withing the string.

To do that, one would have to use the backslash key "**\\**" and then press "**?**".

To sum it all up:

1. Press "**?**" to get help.
2. Press "**\\?**" to get a "**?**".
3. Press "**\\\\**" to get a "**\\**".

When in *Station editor*, the **Line editor** recognizes an extra mode: **Paste mode**.

This mode is enabled by pressing "**\\p**" and gets automatically disabled when the focus moves off the line editors.

This mode is designed to directly accept the "*?*" and "*\\*" characters (which are normally used as commands indicators). This makes it possible to easily paste a station's name and URL, especially when the "*?*" and "*\\*" characters exist in them; it is very common to have them in URLs.

### CJK characters support

The *Line editor* supports the insertion of [CJK Unified Ideographs](https://en.wikipedia.org/wiki/CJK_Unified_Ideographs), as described on [CJK Unified Ideographs (Unicode block)](https://en.wikipedia.org/wiki/CJK_Unified_Ideographs_(Unicode_block)) also known as URO, abbreviation of Unified Repertoire and Ordering. These characters, although encoded as a single code-point (character), actually take up a 2-character space, when rendered on the terminal.

A depiction of the editor's behavior can be seen at this image:

![CJK Characters on Pyradio](https://members.hellug.gr/sng/pyradio/pyradio-editor.jpg)

## Moving stations around

Rearranging the order of the stations in the playlist is another feature **PyRadio** offers.

All you have to do is specify the *source* station (the station to be moved) and the position it will be moved to (*target*).

There are three way to do that:

1. Press **Ctrl-U** or **Ctrl-D** to move the current station up or down.
2. Type a station number and press **Ctrl-U** or **Ctrl-D** to move the current station there.
3. Go to the position you want to move a station to, and press "**J**". This will *tag* this position (making it the *target* of the move). Then go to the station you want to move and press **Ctrl-U** or **Ctrl-D** to move it there.

## Specifying stations' encoding

Normally, stations provide information about their status (including the title of the song playing, which **PyRadio** displays) in Unicode (**utf-8** encoded). Therefore, **PyRadio** will use **utf-8** to decode such data, by default.

In an ideal world that would be the case for all stations and everything would be ok and as far as **PyRadio** is concerned, songs' titles would be correctly displayed. Unfortunately, this is not the case.

A lot of stations encode and transmit data in a different encoding (typically the encoding used at the region the come from). The result in **PyRadio** would be that a song title would be incorrectly displayed, not displayed at all, or trying to displaying it might even break **PyRadio**'s layout.

**Note:** **vlc** will not work in this case; it presumably tries to decode the said data beforehand, probably using **utf-8** by default, and when it fails, it provides a "**(null)**" string, instead of the actual data. So, you'd better not use **vlc** if such stations are in your playlists.

**PyRadio** addresses this issue by allowing the user to declare the encoding to use either in a station by station mode or globally.

### Station by station encoding declaration

As previously stated, a **PyRadio**'s playlist can optionally contain a third column (in addition to the station name and station URL columns), which declares the station's encoding.

So, when a **non-utf-8** encoded station is inserted in a playlist, its encoding can also be declared along with its other data. The drawback of this feature is that an encoding must be declared for **all stations** (so that the **CSV** file structure remains valid). To put it simple, since one station comprises the third column, all stations must do so as well.

This may seem intimidating (and difficult to achieve), but it's actually really simple; just add a "**,**" character at the end of the line of each station that uses the default encoding. In this way, all stations comprise the third column (either by declaring an actual encoding or leaving it empty).

Example:

Suppose we have a playlist with one **utf-8** encoded station:

    Station1,Station1_URL

Now we want to add "**Station2**" which is **iso-8859-7** (Greek) encoded.

Since we know **all stations** must comprise the third (encoding) column, we add it to the existing station:


    Station1,Station1_URL,

Finally, we insert the new station to the playlist:


    Station1,Station1_URL,
    Station2,Station2_URL,iso-8859-7

**Note:**
Using the **-a** command line option will save you all this trouble, as it will automatically take care of creating a valid **CSV** file. Alternatively, you can change the selected station's encoding by pressing "**E**" while in **PyRadio**.

### Global encoding declaration

**PyRadio**'s configuration file contains the parameter **default_encoding**, which by default is set to **utf-8**.

Setting this parameter to a different encoding, will permit **PyRadio** to successfully decode such stations.

This would be useful in the case where most of your stations do not use **utf-8**. Instead of editing the playlist and add the encoding to each and every affected station, you just set it globally.

## Player detection / selection

**PyRadio** is basically built around the existence of a valid media player it can use. Thus, it will auto detect the existence of its supported players upon its execution.

Currently, it supports MPV, MPlayer and VLC, and it will look for them in that order. If none of them is found, the program will terminate with an error.

Users can alter this default behavior by using the **-u** command line option. This option will permit the user either to specify the player to use, or change the detection order.

Example:

    pyradio -u vlc

will instruct **PyRadio** to use VLC; if it is not found, the program will terminate with an error.

    pyradio -u vlc,mplayer,mpv

will instruct **PyRadio** to look for VLC, then MPlayer and finaly for MPV and use whichever it finds first; if none is found, the program will terminate with an error.

The default player to use can also be set in **PyRadio**'s [configuration file](#config-file), parameter **player** (default value is **mpv, mplayer, vlc**), using the "*Configuration Window*", through which **extra player parameters** can be set.

### Changing player mid-session

If the user faces a playback problem with a given station, chances are that a different player will successfully play it.

Pressing "**\\m**" will bring up the "*Switch Media Player*" window, where a different player can be activated.

If **recording is on** while using the previously activated player, it will remain on with the newly activated one. This actually means that the recording will stop when the old player is stopped and resumed when the new player is activated (creating a new recorder file). There is just one exception to that; selecting **VLC** is not possible on **Windows**, since **VLC** does not support recording on this platform.

**Note:** The activated player will not be saved; **PyRadio** will still use the player defined at its config next time it is executed.

### Extra Player Parameters

All three supported players can accept a significant number of "*command line options*", which are well documented and accessible through man pages (on linux and MacOs) or the documentation (on Windows).

**PyRadio** uses some of these parameters in order to execute and communicate with the players. In particular, the following parameters are in use **by default**:

| Player  | Parameters                                                                                    |
|---------|-----------------------------------------------------------------------------------------------|
| mpv     | --no-video, --quiet, --input-ipc-server, --input-unix-socket, --playlist, --profile           |
| mplayer | -vo, -quiet, -playlist, -profile                                  |
| vlc     | -Irc, -vv<br>**Windows only:** --rc-host, --file-logging, --logmode, --log-verbose, --logfile |

**Note:** The user should not use or change the above player parameters. Failing to do so, may render the player ***unusable***.

**PyRadio** provides a way for the user to add extra parameters to the player, either by a command line option, or the "*Configuration Window*" (under "*Player:*").

#### Using the Configuration Window

When the user uses the configuration window (shown in the following image), he is presented with an interface which will permit him to select the player to use with **PyRadio** and edit its extra parameters.

![PyRadio Player Selection Window](https://members.hellug.gr/sng/pyradio/pyradio-player-selection.jpg)

For each of the supported players the existing profiles (not for *VLC*) and existing extra parameters will be displayed.

The user can add ("**a**") a new parameter, edit ("**e**") an existing set and delete ("**x**" or "**DEL**") one; profiles cannot be edited or deleted, though.

## Player connection protocol

Most radio stations use plain old http protocol to broadcast, but some of them use https.

Experience has shown that playing a **https** radio station depends on the combination of the station's configuration and the player used.

If such a station fails to play, one might as well try to use **http** protocol to connect to it.

**PyRadio** provides a way to instruct the player used to do so; the "*Force http connections*" configuration parameter. If it is *False* (the default), the player will use whatever protocol the station proposes (either **http** or **https**). When changed to **True**, all connections will use the **http** protocol.

When the selected player is initialized (at program startup), it reads this configuration parameter and acts accordingly.

If the parameter has to be changed mid-session (without restarting the program), one would press "**z**" to display the "*Connection Type*" window, where the parameter's value can be set as desired.

**Note:** Changes made using the "*Connection Type*" window are not stored; next time the program is executed, it will use whatever value the configuration parameter holds. Furthermore, changing the configuration stored value, will not affect the "working" value of the parameter.

### Visual reminder

When this option is activated, either through the config or the keyboard, a "*[http forced (z)]*"message appears on the top right corner of the window, as shown in the following image.

![http force](https://members.hellug.gr/sng/pyradio/http-force.jpg)

The "**z**" in parenthesis is just a hint to remind the user that he can change the behavior by pressing "**z**".

As the window shrinks in width, the message becomes a "*[h]*"; when it shrinks even more, it disappears completely.

## Player default volume level

All players, when started, use their saved (or default) volume level to play any multimedia content. Fortunately, this is not the case with VLC.

This introduces a problem to **PyRadio**: every time a user plays a station (i.e restarts playback), even though he may have already set the volume to a desired level, the playback starts at the player's default level.

The way to come around it, is to save the desired volume level in a way that it will be used by the player whenever it is restarted.

This is done by typing "**v**" right after setting a desired volume level.

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
    softvol=1
    softvol-max=300
    volstep=1
    volume=50

**Note:** Starting with **PyRadio v. 0.8.9**, *mplayer*'s default profile will use its internal mixer to adjust its volume; this is accomplished using the "*softvol=1*" and "*softvol-max=300*" lines above. The user may choose to remove these lines from the config (to activate system-wide volume adjustment) or add them to the config (in case the profile was created by an older **PyRadio** version).

### VLC

Although **VLC** can use a local configuration file, there seems to be no reliable way of defining the playback volume in it.

In the past, **VLC** would just use any volume setting it had saved from a previous execution, but now it is possible to save the volume it will use when executed by **PyRadio**.

This means that **VLC** will start and connect to a station, use whatever volume level it's stored for it and then **PyRadio** will reset the volume to the desired one (as saved within **PyRadio**).

The volume will be saved is a file called *vlc.conf* and reside withing the *data* directory, inside **PyRadio**'s configuration folder.

## Buffering

When a station is slow (or the internet connection is slow), one might get to a situation where the connection timeout will run out before the connection with the station can be established. Even worse, **PyRadio** will connect to the station, but the sound will be choppy and crackling.

The solution is to use a large enough **buffer** to connect to the station; this will effectively make **PyRadio** connect to the station and start receiving data, but will not start playback until the buffer is full.

All **PyRadio** supported support buffering, using a number of command line parameters to actually set it up. **PyRadio** will remove all this complexity by making is as simple as inserting a single value to the "*Buffering*" window, shown below.

![PyRadio Buffering Window](https://members.hellug.gr/sng/pyradio/pyradio-buffering-win.jpg)

The window opens by pressing "**\\B**" while in the **Main** mode.

It will display the current buffer size (0 means no buffering), and will permit to adjust it, or use the previously used value (pressing "**r**").

In any case, one can enable or disable the use of buffering by pressing "**\\b**" (using either the default value or the one set in the "*Buffering*" window).

### Parameters used

The following table shows the command line parameters used by **PyRadio** when the "*Buffering*" window is used to set up buffering.

| mpv<br>(X in seconds)          | mplayer<br>(X in KBytes) | vlc<br>(X in seconds)    |
|--------------------------------|--------------------------|--------------------------|
| --demuxer-readahead-secs=X-1   | -cache X                 | --network-caching X*1000 |
| --demuxer-cache-wait=yes       | -cache-min 80            |                          |
| --cache=yes                    |                          |                          |
| --cache-secs=X                 |                          |                          |
| --cache-on-disk=yes/no \*      |                          |                          |

\* disabled if more than 500KB of memory is free

### Customizing the buffering behavior

In case one wants to use a different set of parameters (when using **mpv** or **mplayer**, but not **vlc**), one would just not use the integrated solution; one would just use a **profile**.

Please refer to the players' documentation on profiles and the "[Player default volume level](#player-default-volume-level)" section in this document.

As long as the word "**cache**" is contained in the profile's name, **PyRadio** will understand this is a buffering profile and act accordingly. But it's up to the user to make sure this presupposition is honored.

### How it works

When buffering is enabled, and a connection to a station initializes, **PyRadio** will display a "**[B]**" at the top left corner of the window, and display "**Buffering:**" and the name of the station in the status bar, until it get a token that the buffering has stopped.

![PyRadio Buffering](https://members.hellug.gr/sng/pyradio/pyradio-b.jpg)

An example is shown in the image above.

Now, this behavior depends on the station, and the data it sends (or does not send) while it is buffering. For example, an ICY title may be received while buffering, which will be displayed in the status bar.

It should be noted that, no volume adjustment can be preformed while buffering.

## Displaying Station Info

When a connection to a radio station has been established, the station starts sending audio data for the user to listen to.

Well, that's obvious, right?

Yes, but this is just half of the story.

The station actually also sends identification data, audio format data, notifications, etc. Part of this non-audio data transmitted by a station is the title of the song currently playing; this is why we can have this data displayed at the bottom of the screen.

Now, not all stations send the whole set of data; most send their name, website, genre and bit rate, for example, but some may omit the website or the genre.

**PyRadio** can receive, decode and display this data, and even help the user to identify an unknown station. This is the way to do it:

After a connection to a station has been established (after playback has started), just press "**i**" to display the station's info.

The window that appears includes the "*Playlist Name*" (the station name we have in the playlist) and the "*Reported Name*" (the name the station transmitted to us) among other fields; an example can bee seen here:

![PyRadio Station Info Window](https://members.hellug.gr/sng/pyradio/pyradio-station-info.jpg)

If these two names are not identical, the user can press "**r**" to rename the station in the playlist using the "*Reported Name*". This way an unknown station (when only the URL is known) can be correctly identified (after being inserted in a playlist with a dummy station name).

## Copying and pasting - Registers

**PyRadio** takes the concept of **registers** from [vim](https://www.vim.org), and adapts their function to its own needs. So this is how it all works.

There are 36 named registers (name is **a-z**, **0-9**) and one unnamed register.

* **Named registers** are actually files that contain stations and can be opened and edited as regular playlist files. There are some differences in handling them: they are accessible either individually or using a special window, they are automatically saved, and writing errors are ignored. The later means that registers should not be regarded as normal playlist files that can be safely saved and used forever; this is true as long as there's no problem with writing to them; if a writing error occurs they may get overwritten or emptied. To permanently save a register, on would **rename** it to a normal playlist file.

* The **unnamed register** holds just one station (the one that has been copied or added to a register or deleted from a playlist), and it is the one used when pasting to a register or a playlist. One can see its contents by pressing "**\u**".

To **copy** a station to a register one would press "**y**" and:

* one of "**a-z**", "**0-9**" to add it to the corresponding *named* register. The *unnamed* register is also populated.

* **ENTER** to add it to the *unnamed* register.

To **open** a *named* register, one would press "**'**" (single quote) and:

* one of "**a-z**", "**0-9**" to open the corresponding register.

* "**'**" (single quote) to open the "*Registers window*", so that a register can be selected.

To **rename** a *named* register, one would press "**\\r**" either in the "*Registers window*" or while editing the register.

To **clear a named register**, one would press "**\\c**" either in the "*Registers window*" or while editing the register.

To **clear all registers**, one would press "**\\C**" either in the "*Registers window*" or while editing a playlist or a register.

To **paste** the *unnamed* register to a playlist or register, one would press:

* "**p**" while editing a playlist or register.

* "**\\p**" while editing a playlist or register. This would open the "*Paste selection*" window.

* "**\\p**" in the "*Playlist Selection* or the "*Registers*" window.

## PyRadio Themes

**PyRadio** supports **CSS themes**; it comes with a number of predefined ones and can use external programs that can provide automatically created and updated themes.

To set a theme you just press "**t**" and

- select a theme and press the **Right Arrow** to activate it.

- when you have found a theme you like, press **Space** to make it the default one.

To get more info about using and creating a **PyRadio theme**, please refer to [this page](themes.md).


## Recording stations

**PyRadio** supports recording of stations, as much as this feature is provided by the players it supports.


___

**Berfore you continue, read this!**

Generally, recording a radio streaming broadcast is considered legit, if the recording is to be used for personal use only (i.e. to listen to the broadcast at a later time).

Distributing such a recording, is illegal. Broadcasting it is also illegal. Its reproduction before an audience is also illegal. In some countries/regions, it is also illegal to split or tag the songs in the recording.

Please make sure you are informed about this topic, about what the law considers illegal at your country/region, **before using this feature!**

**You have been warned!**

**PyRadio**, its creator and maintainers do not condone any behavior that involves online piracy or copyright violation. This feature is provided strictly for personal use, and to utilize another requested feature: **pausing and resuming** playback.

___

Please refer to [this page](recording.md) to read more about his feature.

## Mouse support

Being a console application, **PyRadio** was never intended to work with a mouse.

Furthermore, when using the mouse on a console application, the result is highly dependent on the terminal used and the way it implements mouse support.

Having said that, and since the question of using the mouse with **PyRadio** has been risen, basic mouse support has been implemented; starting, stopping and muting the player, scrolling within the playlist and adjusting the player's volume is now possible using the mouse.

All one has to do is enable mouse support in the "*Config Window*" (mouse support is disabled by default) and restart **PyRadio** for the change to take effect.

Then, the mouse can be used as follows:

| Action       | Result                                                     |
|----------------------|------------------------------------------------------------|
| **Click**        | Change selection                                           |
| **Double click** | Start / stop the player                                    |
| **Middle click** | Toggle player muting<br>(does not work with all terminals) |
| **Wheel**        | Scroll up / down                                           |
| **Shift-Wheel**  | Adjust volume<br>(does not work with all terminals)        |

## Title logging

Version **0.8.9.17** adds to **PyRadio** the ability to log the titles displayed at the bottom of its window, in a log file, for reference.

The logger, which is a special kind of *debug logger*, but works independently from the "*debug*" function, is actually a [Rotating File Handler](https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler), configured to write up to 5 files of around 50KB each (parameters **maxBytes=50000** and **backupCount=5**).

The way this works, according to the documentation, is that one "can use the **maxBytes** and **backupCount** values to allow the file to rollover at a predetermined size. When the size is about to be exceeded, the file is closed and a new file is silently opened for output. Rollover occurs whenever the current log file is nearly **maxBytes** in length… When **backupCount** is non-zero, the system will save old log files by appending the extensions ‘.1’, ‘.2’ etc., to the filename. For example, with a backupCount of 5 and a base file name of **app.log**, you would get *app.log*, *app.log.1*, *app.log.2*, up to *app.log.5*. The file being written to is always **app.log**. When this file is filled, it is closed and renamed to *app.log.1*, and if files *app.log.1*, *app.log.2*, etc. exist, then they are renamed to *app.log.2*, *app.log.3* etc. respectively.

The function can be enabled:

1. using the `-lt` (`--log-titles`) command line option, or
2. by pressing "**W**" while in the **Main**, the **Playlist** or the **Register** mode.

The titles are written in a file called *pyradio-titles.log* which is located in the **Recordings Directory**.

Log file sample:

```
Apr 18 (Mon) 13:12 | >>> Station: Lounge (Illinois Street Lounge - SomaFM)
Apr 18 (Mon) 13:12 |     Jack Costanzo - La Cumparsa, Harlem Nocturne
Apr 18 (Mon) 13:14 |     Don Baker Trio - Third Man Theme
Apr 18 (Mon) 13:16 |     Gillian Hills - Un Petit Baiser
```

### Tagging a title

An extra functionality is made possible because of "*titles' logging*": tagging a title (a kind of "liking" a song).

The idea is that when users play a station and hear a song, they may like and want to look it up later. With this functionality, they can tag the song (make a note in the log file) for later.

To tag a title, one has to press the "**w**" key.

Then, if title logging is already enabled, the log file will show up an entry like the example below:

    Apr 18 (Mon) 13:39 |     Tom Russell - Bus Station
    Apr 18 (Mon) 13:40 |     Tom Russell - Bus Station (LIKED)

If title logging is disabled, it will be temporarily turned on only for the tagging of that song:

    Apr 18 (Mon) 15:38 | === Logging started
    Apr 18 (Mon) 15:38 | >>> Station: Folk (Folk Forward - SomaFM)
    Apr 18 (Mon) 15:38 |     Lord Huron - Lullaby
    Apr 18 (Mon) 15:38 |     Lord Huron - Lullaby (LIKED)
    Apr 18 (Mon) 15:38 | === Logging stopped

## Online radio directory services

**PyRadio** supports the following *Online radio directory services*:

- [RadioBrowser](https://www.radio-browser.info/)

    This is a community driven effort (like wikipedia) with the aim of collecting as many internet radio and TV stations as possible.

    Read more at [PyRadio RadioBrowser Implementation](radio-browser.md)

To access supported services, just press "**O**" (capital "*o*") at the program's main window.

## Desktop Notifications

**PyRadio** can provide Desktop Notifications if a notification daemon is already present (on Linux and BSD), or via **Windows Notification Service** (**WNS**).

If enabled, **PyRadio** will display:

1. The playlist name, when playback starts.
2. Song info (as provided by the radio station).
3. Connection failure messages.
4. Player crash messages.

To find out more about configuring this feature, please refer to [Desktop Notification](desktop-notification.md).

## Desktop File

**PyRadio** will install a Desktop File under **~/.local/share/applications**.

**Note:** The system wide Desktop File will probably be under **/usr/share/applications** or **/usr/local/share/applications**.

By default, this Desktop File will add a "**PyRadio**" entry under the "**Internet**" category (or menu), and will execute **PyRadio** no matter if the directory it resides in is the PATH or not, using the **default** terminal that the system uses.

In case of a local installation, when a system wide installation also exists, the entry will display "**PyRadio - Local**" to distinguish itself from the system wide "**PyRadio**" one.

**Note:** If the TERMINAL variable is set, the Desktop File will use that instead.

### Specifying the terminal to use

If a specific terminal has to be used, using the **--terminal** command line option is the way to go:

    pyradio --terminal kitty

This command will set the terminal in the Desktop file, so that:

    Exec=kitty -e pyradio

To have **PyRadio** try to find a suitable terminal, execute:

    pyradio --terminal auto

To restore the original functionality (specifying no terminal):

    pyradio --terminal none

#### Specifying PyRadio parameters

If a **PyRadio** parameter has to be present in the Desktop File, use the **--terminal-param** command line option:

    pyradio --terminal none --terminal-param "_p 2"

This command will use no specific terminal and will pass the "**-p 2**" (play station No 2 automatically) parameter to **PyRadio**. To pass such a parameter, substitute all hyphens with underscores.

## Session Locking

**PyRadio** uses session locking, which actually means that only the first instance executed within a given session will be able to write to the configuration file.

Subsequent instances will be "*locked*". This means that the user can still play stations, load and edit playlists, load and test themes, but any changes will **not** be recorded in the configuration file.

### Session unlocking

If for any reason **PyRadio** always starts in "*locked mode*", one can **unlock** the session, using the "*--unlock*" command line option.

## Update notification

**PyRadio** will periodically (once every 10 days) check whether a new version has been released.

If so, a notification message will be displayed, informing the user about it and asking to proceed with updating the program (provided this is not a distribution package).

**Note:** Packages coming from a distribution repository will display no notification; it's up to the distro to update / uninstall **PyRadio**, as stated in [Packaging PyRadio](docs/packaging.md).

## Remote Control Server

**PyRadio** can be controlled remotely using normal http requests either form the command line (with *curl* for example) or from a browser.

For more information, please refer to [the relevant page](server.md).

If you'd like to set up a "headless" **PyRadio** operation for your linux box, please refer to the [Headless](headless.md) page.

### Remote Control Client

**PyRadio** comes with its own client, which will make it easier to communicate with the **Remote Control Server**.

For more information, please refer to [the relevant page](client.md).

## Debug mode

Adding the "**-d**" option to the command line will instruct **PyRadio** to enter *Debug mode*, which means that it will print debug messages to a file. This file will always reside in the user's home directory and will be named *pyradio.log*.

In case of a bug or a glitch, please include this file to the issue you will [open at github](https://github.com/coderholic/pyradio/issues).

## Reporting bugs

When a bug is found, please do report it by [opening an issue at github](https://github.com/coderholic/pyradio/issues), as already stated above.

In you report you should, at the very least, state your **pyradio version**, **python version** and **method** of installation (built from source, AUR, snap, whatever).

It would be really useful to include **~/pyradio.log** in your report.

To create it, enter the following commands in a terminal:

    $ rm ~/pyradio.log
    $ pyradio -d

Then try to reproduce the bug and exit **pyradio**.

Finally, include the file produced in your report.

## Packaging PyRadio

If you are a packager and would like to produce a package for your distribution please do follow [this mini guide](packaging.md).

