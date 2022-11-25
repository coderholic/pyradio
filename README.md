# PyRadio

Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

![Pyradio](https://members.hellug.gr/sng/pyradio/pyradio.png)


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
* [About Playlist files](#about-playlist-files)
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
    * [Extra Player Parameters](#extra-player-parameters)
        * [Using the command line](#using-the-command-line)
        * [Using the Configuration Window](#using-the-configuration-window)
    * [Changing parameters set](#changing-parameters-set)
* [Player connection protocol](#player-connection-protocol)
* [Player default volume level](#player-default-volume-level)
    * [MPV](#mpv)
    * [MPlayer](#mplayer)
* [Displaying Station Info](#displaying-station-info)
* [Copying and pasting - Registers](#copying-and-pasting---registers)
* [PyRadio Themes](#pyradio-themes)
    * [Virtual terminal restrictions](#virtual-terminal-restrictions)
    * [CSS color themes restrictions](#css-color-themes-restrictions)
    * [Secondary windows background](#secondary-windows-background)
        * [Theme defined secondary windows color](#theme-defined-secondary-windows-color)
        * [Calculated secondary windows color](#calculated-secondary-windows-color)
    * [User themes](#user-themes)
        * [Converting old themes](#converting-old-themes)
    * [Using transparency](#using-transparency)
    * [Updating themes automatically](#updating-themes-automatically)
    * [Using Project Themes](#using-project-themes)
        * [base16](#base16)
            * [Using the themes without base16](#using-the-themes-without-base16)
        * [pywal](#pywal)
        * [theme.sh](#theme.sh)
            * [Using the themes without theme.sh](#using-the-themes-without-theme.sh)
* [Mouse support](#mouse-support)
* [Titles logging](#titles-logging)
    * [Tagging a title](#tagging-a-title)
* [Online radio directory services](#online-radio-directory-services)
* [Desktop Notifications](#desktop-notifications)
* [Desktop File](#desktop-file)
    * [Specifying the terminal to use](#specifying-the-terminal-to-use)
        * [Specifying PyRadio parameters](#specifying-pyradio-parameters)
* [Session Locking](#session-locking)
    * [Session unlocking](#session-unlocking)
* [Update notification](#update-notification)
    * [Updating a pre 0.8.9 installation](#updating-a-pre-0.8.9-installation)
* [Cleaning up](#cleaning-up)
* [Debug mode](#debug-mode)
* [Reporting bugs](#reporting-bugs)
* [Packaging PyRadio](#packaging-pyradio)
* [TODO](#todo)
* [Acknowledgment](#acknowledgment)
* [Special thanks](#special-thanks)

<!-- vim-markdown-toc -->

## Features

**PyRadio** provides the following features:

 - vi like keys in addition to arrows and special keys
 - Station editor (add/edit) with [CJK characters support](#cjk-characters-support)
 - Configuration editor
 - Multiple playlist support
 - vi like station registers
 - Search function
 - Theming support
 - [RadioBrowser](radio-browser.md) support
 - Easy installation / updating
 - Runs on Linux, macOS and Windows

and much more...

## Requirements
* python 2.7/3.5+
    - setuptools
    - wheel
    - requests
    - dnspython
    - psutil
* MPV, MPlayer or VLC installed and in your path

<!-- Changelog -->

## Installation

The best way to install **PyRadio** is via a distribution package, if one exists (e.g. *Arch Linux* and derivatives can install [any of these packages](https://aur.archlinux.org/packages/?K=pyradio) from the AUR).

In any other case, and since **PyRadio** is currently not available via pip, you will have to [build it from source](build.md).

## Command line options

```
$ pyradio -h

usage: pyradio [-h] [-s STATIONS] [-p [PLAY]] [-u USE_PLAYER] [-a] [-ls] [-l]
               [-t THEME] [--show-themes] [--no-themes]
               [--write-theme IN_THEME OUT_THEME,] [--terminal TERMINAL]
               [--terminal-param TERMINAL_PARAM] [-tlp] [-scd] [-ocd]
               [-ep EXTRA_PLAYER_PARAMETERS] [-ap ACTIVE_PLAYER_PARAM_ID]
               [-lp] [-U] [--user] [-R] [--unlock] [-lt] [-d] [-V]

Curses based Internet radio player

options:
  -h, --help            show this help message and exit
  -s STATIONS, --stations STATIONS
                        Use specified station CSV file.
  -p [PLAY], --play [PLAY]
                        Start and play.The value is num station or empty for
                        random.
  -u USE_PLAYER, --use-player USE_PLAYER
                        Use specified player. A comma-separated list can be
                        used to specify detection order. Supported players:
                        mpv, mplayer, vlc.
  -a, --add             Add station to list.
  -ls, --list-playlists
                        List of available playlists in config dir.
  -l, --list            List of available stations in a playlist.
  -t THEME, --theme THEME
                        Use specified theme.
  --show-themes         Show Internal and System Themes names.
  --no-themes           Disable themes (use default theme).
  --write-theme IN_THEME OUT_THEME,
                        Write an Internal or System Theme to themes directory.
  --terminal TERMINAL   Use this terminal for Desktop file instead of the
                        auto-detected one. Use "none" to reset to the default
                        terminal or "auto" to reset to the auto-detected one.
  --terminal-param TERMINAL_PARAM
                        Use this as PyRadio parameter in the Desktop File.
                        Please replace hyphens with underscores when passing
                        the parameter, for example: --terminal-param "_p 3 _t
                        light" (which will result to "pyradio -p 3 -t light").
  -tlp, --toggle-load-last-playlist
                        Toggle autoload last opened playlist.
  -scd, --show-config-dir
                        Print config directory [CONFIG DIR] location and exit.
  -ocd, --open-config-dir
                        Open config directory [CONFIG DIR] with default file
                        manager.
  -ep EXTRA_PLAYER_PARAMETERS, --extra-player_parameters EXTRA_PLAYER_PARAMETERS
                        Provide extra player parameters as a string. The
                        parameter is saved in the configuration file and is
                        activated for the current session. The string's format
                        is [player_name:parameters]. player_name can be 'mpv',
                        'mplayer' or 'vlc'. Alternative format to pass a
                        profile: [player_name:profile:profile_name]. In this
                        case, the profile_name must be a valid profile defined
                        in the player's config file (not for VLC).
  -ap ACTIVE_PLAYER_PARAM_ID, --active-player-param-id ACTIVE_PLAYER_PARAM_ID
                        Specify the extra player parameter set to be used with
                        the default player. ACTIVE_PLAYER_PARAM_ID is 1-11
                        (refer to the output of the -lp option)
  -lp, --list-player-parameters
                        List extra players parameters.
  -U, --update          Update PyRadio.
  --user                Install only for current user (not on Windows).
  -R, --uninstall       Uninstall PyRadio.
  --unlock              Remove sessions' lock file.
  -lt, --log-titles     Log titles to file.
  -d, --debug           Start pyradio in debug mode.
  -V, --version         Display version information.
```

The following options can also be set in **PyRadio**'s [configuration file](#config-file):

* **-s** - parameter **default_playlist** (default value: **stations**)
* **-p** - parameter **default_station** (default value: **-1**)
* **-u** - parameter **player** (default value: **mpv, mplayer, vlc**)
* **-t** - parameter **theme** (default value: **dark**)

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
| **\+** / **\-** and **,** / **\.** | adjust volume         |**W**                          | toggle titles logging |
| **m**                          | mute player           |**w**                          | like a station        |
| **v**                          | save volume           |**^N** / **^P** [1] [2]|play next / previous station|
| **T**                          | toggle transparency   |**<** / **>** [1]             | play next / previous station history entry|

Every window in **PyRadio** will respect these shortcuts, even the ones with a "*Press any key to...*" message.

When focus is on a "*Line editor*", all shortcuts will work when preceded by a "**\\**".

**Notes**

[1] Function not available when in **Playlist** and **Registers** mode. More info on *PyRadio's modes* below.

[2] Function not available in the **Radio Browser** Search window.

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

2. The **Limited Width** mode, which is automatically enabled when the window width get bellow certain limits:

    - When the width gets bellow 40 columns, all windows will be closed and the main window will be the only visible one (either displaying stations, playlists or registers).

    - When the width gets bellow 20 columns, the **Limited display** will be activated.

![Pyradio reduced to the "Limited display"](https://members.hellug.gr/sng/pyradio/pyradio-limited-display.jpg)

**Note:** These two modes do not work on Windows, either 7 or 10. The "*Console*"window will shrink as desired, but will not always notify **PyRadio** about it, so results will vary.

## Config file

**PyRadio** upon its execution tries to read its configuration file (i.e. *~/.config/pyradio/config*). If this file is not found, it will be created. If an error occurs while parsing it, an error message will be displayed and **PyRadio** will terminate.

The file contains parameters such as the player to use, the playlist to load etc. It is heavily commented (as you can see [here](pyradio/config)), so that manual editing is really easy. The best practice to manually edit this file is executing **PyRadio** with the **-ocd** command line option, which will open the configuration directory in your file manager, and then edit it using your preferable text editor.

The file can also be altered while **PyRadio** is running by pressing "**c**", which will open the "**Configuration window**". This window presents all **PyRadio** options and provide the way to change them and finally save them by pressing "**s**".

In any case, **PyRadio** will save the file before exiting (or in case Ctrl-C is pressed) if needed (e.g. if a config parameter has been changed during its execution).

If saving the configuration file fails, **PyRadio** will create a back up file and terminate. When restarted, **PyRadio** will try to restore previously used settings from the said back up file.

## About Playlist files

**PyRadio** reads the stations to use from a CSV file, where each line contains two columns, the first being the station name and the second being the stream URL.

Optionally, a third column can be inserted, stating the encoding used by the station (more on this at [Specifying stations' encoding](#specifying-stations-encoding)).

**PyRadio** will by default load the user's stations file (e.g. *~/.config/pyradio/stations.csv*) to read the stations from. If this file is not found, it will be created and populated with a default set of stations.

**Note:** Older versions used to use **~/.pyradio** as default stations file. If this file is found, it will be copied to use's config directory (e.g. **~/.config/pyradio**) and renamed to **stations.csv** or if this file exists, to **pyradio.csv**. In this case, this file will be the default one.


### Integrating new stations

When the package's "*stations.csv*" files is updated, the changes it has will not automatically appear in the user's stations file.

What **PyRadio** will do is inform the user that these changes do exist and give him a chance to **integrate** these changes to his stations file, by appending the new stations to the file.

When this is done, the first added station will be selected so that the user can inspect the changes and decide to keep or delete the new stations.

**PyRadio** will only add stations to the user's stations file; no station will be deleted as a result of this procedure.

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
      1. hip-hop
      2. party
      3. stations
      4. huge
      5. blues
      6. rock
      7. pop
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

The list is not saved between sessions (restarting the program will lead to an empty list). When an "**online service** is used (e.g. **Radio Browser**) the list is reseted with every search that is performed.

## Search function

On any window presenting a list of items (stations, playlists, themes) a **search function** is available by pressing "**/**".

The *Search Window* supports normal and extend editing and in session history.

One can always get help by pressing the "**?**" key.

After a search term has been successfully found (search is case insensitive), next occurrence can be obtained using the "**n**" key and previous occurrence can be obtained using the "**N**" key.

## Line editor

**PyRadio** "*Search function*" and "*Station editor*" use a *Line editor* to permit typing and editing stations' data.

The *Line editor* works both on **Python 2** and **Python 3**, but does not provide the same functionality for both versions:


* In **Python 2**, only ASCII characters can be inserted.
* In **Python 3**, no such restriction exists. Furthermore, using CJK characters is also supported.

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

### Extra Player Parameters

All three supported players can accept a significant number of "*command line options*", which are well documented and accessible through man pages (on linux and macOs) or the documentation (on Windows).

**PyRadio** uses some of these parameters in order to execute and communicate with the players. In particular, the following parameters are in use **by default**:

| Player  | Parameters                                                                                    |
|---------|-----------------------------------------------------------------------------------------------|
| mpv     | --no-video, --quiet, --input-ipc-server, --input-unix-socket, --playlist, --profile           |
| mplayer | -vo, -quiet, -playlist, -profile                                  |
| vlc     | -Irc, -vv<br>**Windows only:** --rc-host, --file-logging, --logmode, --log-verbose, --logfile |

**Note:** The user should not use or change the above player parameters. Failing to do so, may render the player ***unusable***.

**PyRadio** provides a way for the user to add extra parameters to the player, either by a command line option, or the "*Configuration Window*" (under "*Player:*").

This way, 10 sets of parameters can be inserted and made available for selection.

#### Using the command line

When the command line option (**-ep** or **--extra_player_parameters**) is used, the parameters specified must be of a specific format, and will be added to the list of parameters and made default for the player for the current session.

The format of the parameter is the following: **[player_name:parameters]**

Where:

- **player_name**: the name of the player
- **parameters**: the actual player parameters

Example:

    pyradio -ep "vlc:--force-dolby-surround 2"

**Note:** When a parameter is passed to "*mpv*" or "*mplayer*", **PyRadio**" will use the default player profile (called "**pyradio**").

For "*mpv*" and "*mplayer*" a profile can be specified ("*vlc*" does not support profiles). In this case the format of the **parameters** part of the command line is: **profile:profile_name**.

Where:

- **profile**: the word "*profile*"
- **profile_name**: the name of a profile. The profile must be already defined in the player's configuration file.

Example:

    pyradio -ep "mpv:profile:second_sound_card"

#### Using the Configuration Window

When the user uses the configuration window (shown in the following image), he is presented with an interface which will permit him to select the player to use with **PyRadio** and edit its extra parameters.

![PyRadio Player Selectio Window](https://members.hellug.gr/sng/pyradio/pyradio-player-selection.jpg)

Each of the supported players can have up to 11 sets of extra parameters (the first one is the default).

The user can add ("**a**") a new parameter, edit ("**e**") an existing set and delete ("**x**" or "**DEL**") one.

### Changing parameters set

When all desired parameter sets are already defined, using the **-ap** (**--active-player-param-id**) command line option can activate the set that corresponds to the number specified. The number to use for any given set can be retrieved using the **-lp** (**--list-player-parameters**) command line option.

While **PyRadio** is running, the user can change the parameters set used by the player using the "*Player Extra Parameters*" window, by pressing "**Z**".

If playback is on, changing the player's parameters will make the player restart the playback so that the new parameters get used.

**Note:** Any changes made this way will not be saved but will be in effect until **PyRadio** terminates.

## Player connection protocol

Most radio stations use plain old http protocol to broadcast, but some of them use https.

Experience has shown that playing a **https** radio station depends on the combination of the station's configuration and the player used.

If such a station fails to play, one might as well try to use **http** protocol to connect to it.

**PyRadio** provides a way to instruct the player used to do so; the "*Force http connections*" configuration parameter. If it is *False* (the default), the player will use whatever protocol the station proposes (either **http** or **https**). When changed to **True**, all connections will use the **http** protocol.

When the selected player is initialized (at program startup), it reads this configuration parameter and acts accordingly.

If the parameter has to be changed mid-session (without restarting the program), one would press "**z**" to display the "*Connection Type*" window, where the parameter's value can be set as desired.

**Note:** Changes made using the "*Connection Type*" window are not stored; next time the program is executed, it will use whatever value the configuration parameter holds. Furthermore, changing the configuration stored value, will not affect the "working" value of the parameter.

## Player default volume level

MPV and MPlayer, when started, use their saved (or default) volume level to play any multimedia content. Fortunately, this is not the case with VLC.

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

**Note:** Starting with **PyRadio v. 0.8.9**, *mplayer*'s default profile will use its internal mixer to adjust its volume; this is accompliced using the "*softvol=1*" and "*softvol-max=300*" lines above. The user may choose to remove these lines from the config (to activate system-wide volume adjustment) or add them to the config (in case the profile was created by an older **PyRadio** version).

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

**PyRadio** comes with 6 preconfigured (hard coded) themes:

1. **dark** (8 color theme). \
This is the appearance **PyRadio** has always had. Enabled by default.
2. **light** \
A theme for light terminal background settings.
3. **dark_16_colors** \
"**dark**" theme alternative.
4. **light_16_colors** \
"**light**" them alternative.
5. **white_on_black** or **wob** (b&w theme). \
A theme for dark terminal background settings.
6. **black_on_white** or **bow** (b&w theme). \
A theme for light terminal background settings.

Furthermore, a number of themes (these are actual files saved in the **themes** installation directory) are also available:

- **classic_by_obsdg** \
A clasic theme by [The OpenBSD Guy](https://github.com/OpenBSDGuy), originally created on [OpenBSD](https://www.openbsd.org/).
- **cupcake_by_edunfelt** and  **fairyflossy_by_edunfelt** \
Two themes by [edunfelt](https://github.com/edunfelt) inspired by the [base16](https://github.com/base16-project) project.
- **gruvbox_dark_by_sng** and **gruvbox_light_by_sng** \
Two themes based on the [gruvbox](https://github.com/morhetz/gruvbox) theme.
- **minima_by_ben_chile** \
A theme by user [ben_chile](https://forum.maboxlinux.org/u/ben_chile) created on the [Mabox Linux](https://maboxlinux.org) Forum.
- **pastel_based_by_sng** \
A dim but colorful theme.

Contrary to the old styling method, which was terminal and palette dependent, a new styling method has been implemented; actual CSS colors can now be defined.

Theme sample / template:

```
# Main foreground and background
Stations            #8b8198 #fbf1f2

# Playing station text color
# (background color will come from Stations)
Active Station      #d57e85

# Status bar foreground and background
Status Bar          #fbf1f2 #d57e85

# Normal cursor foreground and background
Normal Cursor       #fbf1f2 #dcb16c

# Cursor foreground and background
# when cursor on playing station
Active Cursor       #fbf1f2 #d57e85

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         #fbf1f2 #bfb9c6

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          #69a9a7

# Text color for URL
# (background color will come from Stations)
PyRadio URL         #a3b367

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     #a3b367

# Theme Transparency
# Values are:
#   0: No transparency (default)
#   1: Theme is transparent
#   2: Obey config setting
transparency        0
```

Pressing "**t**" will bring up the *Theme selection window*, which can be used to activate a theme and set the default one.

**Note:** If the theme selected in the "*Theme selection window*", (or requested using the "**-t**" command line option), is in any way invalid, or is of the old format, **PyRadio** will fall-back to the "**dark**" theme and will display a relevant message.

The "*Theme selection window*" will remain open after activating a theme, so that the user can inspect the visual result and easily change it, if desired. Then, when he is satisfied with the activated theme, the window will have to be manually closed (by pressing "**q**" or any other relevant key - pressing "**?**" will bring up its help).

Pressing "**SPACE**", will apply the theme and make it default, and pressing "**c**" will apply the theme and make it default and start a file watch function on the file, so that if the file changes, **PyRadio** will automatically update itself.

### Virtual terminal restrictions

After introducing CSS color themes, it has come to my attention that **PyRadio** will not display colors correctly when executed within specific terminals, *konsole*, *yakuake*, *deepin-teminal*, *qterminal* and *terminology*, just to name a few.

Now, I do not know whether this is because of the terminals themselves, python curses implementation or whatever, but that's that.

**PyRadio** will try to detect these terminals and disable themes (after displaying a relative message). Then the default theme will be used.

Some of the terminals that work ok, are: *gnome-terminal*, *mate-terminal*, *xfce4-terminal*, *lxterminal*, *terminator*, *termite*, *kitty*, *alacritty*, *sakura*, *roxterm*, *tilix*, *lilyterm*, *st*, *xst*, *rxvt*, *urxvt*, *uxterm*, *xterm*.

If you want to make **PyRadio** start in one of these terminal, just follow the instructions given at [Desktop File: Specifying the terminal to use](#specifying-the-terminal-to-use).

### CSS color themes restrictions

Using CSS colors imposes a couple of restrictions on the type of terminals **PyRadio** will be able to run:

1. The TERM variable must be set *(Linux and MacOs only)*. \
\
**PyRadio** will set it to "*xterm-256color*" if not set. \
\
Furthermore, if TERM is set to anything like "**xterm**", "**screen**" or "**tmux**", **PyRadio** will set it to "*xterm-256color*" as well.

2. Terminals that do not support at least 16 colors will not be able to display any of the new themes. The same goes for terminals that do not support changing their colors (through the **curses** library). \
\
These terminal will default to the old "**dark**" theme, displaying whatever colors the active palette dictates.

3. There are a couple of terminals (that I know of) which will permit changing their colors but will not be able to present the changed color on the fly. \
\
This means that, in order for a theme change to take full effect, **PyRadio** will have to be restarted.

### Secondary windows background

Secondary windows (such as messages, questions, the "*Theme Selection window*" the "*Encoding Selection window*", etc.) originally use the same background color as the "*Main window*".

It is now possible to use a different background color for these windows, to get better visual result.

There are two way to do that:

1. Defined in a theme

2. Using a calculated color

#### Theme defined secondary windows color

Themes have the following entry

```
# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#secondary-windows-background
#
Messages Border     #a3b367
```

It is possible to define a background color as well, like so


```
Messages Border     #a3b367 #F5DBDE
```

In this case, this color will be used as the Secondary Windows background color.

Although one can use any color here, it is recommended to follow these guidelines for best visual result:

1. The color should be 1-20% lighter or darker than the "*Stations Background*" color setting of the theme. \
\
One can use [this page](http://www.workwithcolor.com/hsl-color-picker-01.htm) (or a similar one) to insert the base color and adjust the "*L*" component as needed. \
\
A terminal alternative is [pastel](https://github.com/sharkdp/pastel), which can be used like so:

```
pastel color '#fbf1f2'              # show color info
pastel lighten .1 '#fbf1f2'         # color lightened by 10%
pastel darken .1 '#fbf1f2'          # color darkened by 10%
```


2. If the "*Stations Background*" color is dark, create a lighter version of it; if it's light, create a darker version of it. \
\
This is just a recomenration, though; just get a color that combines well with existing ones (border foreground, stations foreground and active station).

This information is actually relevant to creating a new **PyRadio** theme, but it's very important in order to understand how the calculated background color works.

#### Calculated secondary windows color

**PyRadio** will use the same background color for all windows by default, provided that the theme used does not define a "*Messages Border*" background color.

In order to use a "*Messages Border*" background color different than the "*Stations background*" color, when "*Messages Border*" background color is not defined in the selected theme, a config option is available; "**Calculated color**".

This config option takes a value that's between 0 and 0.2.

If it is 0, no color change will occur.

Otherwise, the value acts as a percentage (a **factor**), which indicates how much the luminance of the "*Stations background*" color will change to produce the new background color.

This is how this works: **PyRadio** will calculate the "*Stations background*" color perceived brightness, which will indicate whether the color is dark or light. Then depending on that, will add or subtract **factor** percent from its luminance value.

Finally, a check will be made to see if this color is close to "*Messages Border*" foreground color, and re-adjusted as possible.

**Note:** When a calculated background color is used, pressing "**~**" (**tilde**) will toggle it on and off. This setting will be valid until **PyRadio** terminates, or a new theme is loaded.

### User themes

Users can easiliy create their own themes, using for example [CSS color names](https://www.cssportal.com/css3-color-names/) as a resource, and

1. Save the theme provided as a template above in their themes folder using any (short) file name and a "**.pyradio-theme**" file extension. \
\
For this reason, a folder called "**themes**" will probably have to be created in **PyRadio** config directory (**~/.config/pyradio** or **%APPDATA%\\pyradio** on Windows)


2. Customize it as desired

3. Load it from the "*Theme selection window*" (it will be found under "**User Themes**").


#### Converting old themes

An old theme (using the old format) can be asily converted to the new format, using the script found at [this gist](https://gist.github.com/s-n-g/65aa6ae12e135481bf3a503ece4e92d2).

**Note:** In order to get the color intended to be used, the same palette as the one used when the original theme was created, must be used.

### Using transparency

For **PyRadio**, transparency means that a theme's background actually disappears, effectively making it to display whatever is on the terminal (color/picture/transparency).  The visual result depends on terminal settings and whether a compositor is running.

Not all themes look good when transparency is ON, so themes can now declare whether they want to use transparency or not. This is the "**transparency**" variable of the theme, which can have these values:

- 0 means that the theme looks better with no transparency (default)
- 1 means that the theme looks better when transparency in ON
- 2 means that the theme looks good either way, and the global transparency setting (defined in **PyRadio** config file) can be used.

Please notice that this is just a hint; themes will obey the rules above, but transparency can still be toggled using "**T**" (capital "**t**").

When the "*Theme selection window*" is visible, a "**[T]**" string displayed  at  its  bottom right corner will indicate that transparency is *on*.

### Updating themes automatically

Terminal users have been using all kind of software to change / update / adapt their terminal colors and palettes, such as [bASE16](https://github.com/chriskempson/base16), [pywal](https://github.com/dylanaraps/pywal), [wpgtk](https://github.com/deviantfero/wpgtk), [theme.sh](https://github.com/lemnos/theme.sh), to name a few.

**PyRadio** is now able to "watch" a given theme for changes and update its colors whenever the theme changes.

To set up a theme for auto update, one would just open the "*Theme Selection*" window, navigate to a theme under "**User Themes**" and press "**c**". To create a **user theme** just follow the procedure described in section [User themes](#user-themes).

Consecuently, the default theme name will be preceded by:

- "**\***" if the theme is the default one (the way it has always been).
- "**+**" if the theme is the default one, and **PyRadio** will watch it for changes.

### Using Project Themes

**PyRadio** is able to use (and watch) the output of certain projects that modify terminal colors.

**PyRadio** will detect theses projects (programs installed and initialized), and will add them under the "**Ext. Themes Projects**" section of the "*Themes Selection Window*."

If loading any of these themes fails, the default **dark** theme will be loaded, but contrary to a local theme being invalid, the selection will persist (so that the theme gets loaded wheneve it is available).

Currently, the following projects are supported:

#### base16

Thanks to the wonderful work by user [edunfelt](https://github.com/edunfelt), there is now a **PyRadio** [base16](https://github.com/base16-project) template in place, and themes have been produced based on the project (there are more than 900 themes available).

This implementation will add four entries in the theme selection menu (with alternative and variant forms of the main theme).

Then, any of the themes can either be activated or watched; in which case **PyRadio** will download and apply the corresponding theme.

##### Using the themes without base16

In case one wants to use any of these themes, but not install or use [base16](https://github.com/base16-project), one can get them [from this repo](https://github.com/edunfelt/base16-pyradio), and use the "*cycle_themes.py*" and "*install_themes.py*" scripts to inspect and install them.

For Windows users, this is the only way to use any of these "*Project Themes*", since their generation works on non-windows platforms only.

#### pywal

When detected, two themes will be added to the menu; the main and the alternative form.

Since these themes are generated on the fly, as the wallpaper changes, there is no way to use them if [pywal](https://github.com/dylanaraps/pywal) is not in use.

**Note:** If [pywal](https://github.com/dylanaraps/pywal) themes are activated but not watched, the theme will be corrupted when the wallpaper changes, and will have to be manually reloaded. So, it's better to just always watch these themes.

#### theme.sh

When detected, four themes will be added to the menu; the main and the alternative forms (there are 400 plus themes available, which makes a stuggering number of around 1800 themes for **PyRadio**!)

##### Using the themes without theme.sh

In case one wants to use any of these themes, but not install or use [theme.sh](https://github.com/lemnos/theme.sh), one can download [this repo](https://github.com/s-n-g/theme-sh-pyradio), and use the "*create_themes.py*" script to create the themes, and "*cycle_themes.py*" and "*install_themes.py*" scripts to inspect and install them.

For Windows users, this is the only way to use any of these "*Project Themes*", since their generation works on non-windows platforms only.

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

## Titles logging

Version **0.8.9.17** adds to **PyRadio** the ability to log the titles displayed at the bottom of its window, in a log file, for refference.

The logger, which works independantly from the "*degub*" function, is actually a [Rotating File Handler](https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler), configured to write up to 5 files of around 50KB each (parameters **maxBytes=50000** and **backupCount=5**).

The way this works, according to the documenataion, is that one "can use the **maxBytes** and **backupCount** values to allow the file to rollover at a predetermined size. When the size is about to be exceeded, the file is closed and a new file is silently opened for output. Rollover occurs whenever the current log file is nearly **maxBytes** in length… When **backupCount** is non-zero, the system will save old log files by appending the extensions ‘.1’, ‘.2’ etc., to the filename. For example, with a backupCount of 5 and a base file name of **app.log**, you would get *app.log*, *app.log.1*, *app.log.2*, up to *app.log.5*. The file being written to is always **app.log**. When this file is filled, it is closed and renamed to *app.log.1*, and if files *app.log.1*, *app.log.2*, etc. exist, then they are renamed to *app.log.2*, *app.log.3* etc. respectively.

The function can be enabled:

1. using the `-lt` (`--log-titles`) command line option, or
2. by pressing "**W**" while in the **Main**, the **Playlist** or the **Register** mode.

The titles are written in a file called `pyradio-titles.log` which is saved at **PyRadio** configuration directory.

Log file sample:

```
Apr 18 (Mon) 13:12 | >>> Station: Lounge (Illinois Street Lounge - SomaFM)
Apr 18 (Mon) 13:12 |     Jack Costanzo - La Cumparsa, Harlem Nocturne
Apr 18 (Mon) 13:14 |     Don Baker Trio - Third Man Theme
Apr 18 (Mon) 13:16 |     Gillian Hills - Un Petit Baiser
```

### Tagging a title

An extra functionality is made possible because of "*titles's logging*": tagging a title (something like liking a song).

The idea is that the user plays a station and hears a song he likes and want to look it up later. With this functionality, he can tag the song (make a note in the log file), so he can refer to it at a later time.

To tag a title, one has to press the "**w**" key.

Then, if titles's logging is already enabled, the log file will have an entry similar to the one shown below:

    Apr 18 (Mon) 13:39 |     Tom Russell - Bus Station
    Apr 18 (Mon) 13:40 |     Tom Russell - Bus Station (LIKED)

If title's logging is not enabled, it will be turned on, the song will be tagged and logging will be turned off again:

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

**PyRadio** can provide Desktop Notifications when a notification daemon is already present (on Linux and BSD), or throught **Windows Notification Service** (**WNS**).

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

    pyraio --terminal auto

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

### Updating a pre 0.8.9 installation

First thing you do is get the installation script. Open a **terminal** and type:

    cd
    wget https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py

or using curl:

    cd
    curl -L https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py -o install.py

**Note**: If you have neither *wget* or *curl* installed, or you are on Windows, just right click on [this link](https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py) and use your browser "**Save link as**" menu entry to save the file in your home folder.

Finally, execute the command:

    python install.py --force

## Cleaning up

**PyRadio** will uninstall all previously installed versions when updated (using the **-U** command line option), so no extra steps are needed any more to house keep your system.

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

If you are a packager and would like to produce a package for your distribution please do follow this mini guide.

First of all, make sure you declare the pacakges's requirements to the relevant section of your manifest (or whatever) file. These are:

1. setuptools
2. wheel
3. requests
4. dnspython
5. psutil

After that, you will have to modify some files, because **PyRadio** is able to update and uninstall itself, when installed from source. This is something you do not want to be happening when your package is used; **PyRadio** should be updated and uninstalled using the distro package manager.

In order to accomplice that, you just have to change the **distro** configuration parameter in the **config** file. **PyRadio** will read this parameter and will disable updating and uninstalling, when set to anything other than "**None**". So, here's how you do that:

Once you are in the sources top level directory (typically "*pyradio*"), you execute the command:

    sed -i 's/distro = None/distro = YOUR DISTRO NAME/' pyradio/config

Then you go on to produce the package as you would normally do.

For example, an **Arch Linux** packager would use this command:

    sed -i 's/distro = None/distro = Arch Linux/' pyradio/config

The distro name you insert here will appear in **PyRadio**'s "*Configuration Window*". In addition to that it will appear in the log file, so that I know where the package came from while debugging.

Having said that, if you are not packaging for a specific distribution, please do use something meaningful (for example, using "*xxx*" will do the job, but provides no useful information).

## TODO

- [ ] Any user request I find interesting :)
- [ ] Use Radio Browser service ([#80](https://github.com/coderholic/pyradio/issues/80) [#93](https://github.com/coderholic/pyradio/issues/93) [#112](https://github.com/coderholic/pyradio/issues/112))
- [ ] Use some OPML service, [https://opml.radiotime.com](https://opml.radiotime.com) for example
- [x] Notify the user that the package's stations.csv has changed -v 0.8.9
- [x] Update / uninstall using command line options (-U / -R) - v. 0.8.9
- [x] Basic mouse support ([#119](https://github.com/coderholic/pyradio/issues/119)) - v. 0.8.8.3
- [x] Players extra parameters ([#118](https://github.com/coderholic/pyradio/issues/118)) - v. 0.8.8.3
- [x] New player selection configuration window ([#118](https://github.com/coderholic/pyradio/issues/118)) - v. 0.8.8.3

## Acknowledgment

**PyRadio** uses code from the following projects:

1. [CJKwrap](https://gitlab.com/fgallaire/cjkwrap) by Florent Gallaire - A library for wrapping and filling UTF-8 CJK text.

2. [ranger](https://ranger.github.io/) - A console file manager with VI key bindings.

3. [Vifm](https://vifm.info/) -  A file manager with curses interface, which provides a Vi[m]-like environment.

## Special thanks

1. [edunfelt](https://github.com/edunfelt), for her wonderful work on [base16 themes](https://github.com/edunfelt/base16-pyradio), and ideas regarding theming and such.
