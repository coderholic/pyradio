# PyRadio on Windows

**PyRadio**: Command line internet radio player.

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [Running PyRadio on Windows](#running-pyradio-on-windows)
* [How it all works](#how-it-all-works)
* [Installation](#installation)
    * [Python installation](#python-installation)
        * [Installing Python](#installing-python)
        * [Verifying the installation](#verifying-the-installation)
    * [7-Zip installation](#7-zip-installation)
    * [Player installation](#player-installation)
        * [MPV or MPlayer installation](#mpv-or-mplayer-installation)
        * [VLC installation](#vlc-installation)
    * [PyRadio installation](#pyradio-installation)
        * [Fresh python installation?](#fresh-python-installation?)
        * [Final steps](#final-steps)
        * [Getting the path to pyradio.exe](#getting-the-path-to-pyradio.exe)
        * [Using the Title Logging feature](#using-the-title-logging-feature)
        * [Cleaning up](#cleaning-up)
* [Updating PyRadio](#updating-pyradio)
    * [Updating a pre 0.8.9 installation](#updating-a-pre-0.8.9-installation)
* [Removing an old-style installation](#removing-an-old-style-installation)
* [Uninstalling PyRadio](#uninstalling-pyradio)
* [Reporting bugs](#reporting-bugs)

<!-- vim-markdown-toc -->

[[Back to Build Instructions](build.md)] | [[Back to README](README.md)]

## Running PyRadio on Windows

What? A linux console application on Windows?

Yes, sure. Why not?

**PyRadio** is a *python* script after all, and *python* does run on Windows. So, with a little bit of tweaking of the code, it is possible.

This page will guide you through the process of installing, updating and running **PyRadio** on Windows.

## How it all works

First of all, let me tell you that if you are still running Windows XP, you can just stop reading right now; it won't happen...

**PyRadio** on *Linux* (its main target platform) can use any of three players [MPV](https://mpv.io/), [MPlayer](http://www.mplayerhq.hu/design7/news.html) and [VLC](https://www.videolan.org/vlc/); and this is also the case on *Windows*!

[MPV](https://mpv.io/) is the preferred player for *Windows* and will be automatically installed on a fresh **PyRadio** installation.

Installing [MPlayer](http://www.mplayerhq.hu/) takes a couple of extra steps, and you may find that some streams (e.g. m3u8) may not be playable. Furthermore, special care has to be taken in order to be able to save the volume of the player.

If you are on **Windows 7** and using **MPlayer**, you will not be able to use profiles; it seems the use of profiles is not supported.

[VLC](https://www.videolan.org/vlc/) is much easier to install, but song titles' updating may not be 100% consistent (if any). If this is not a deal breaker for you, then just go on and use [VLC](https://www.videolan.org/vlc/) as **PyRadio**'s player.

Other than that, you will have a fully functional **PyRadio** installation.

Having said that, let us proceed with the installation.

## Installation

The installation consists of three steps:

1. **Python** installation
2. **7Zip** installation
3. **Player** installation
4. **PyRadio** installation

### Python installation

#### Installing Python

If you don't already have **Python** installed, just get to its [Windows Downloads](https://www.python.org/downloads/windows/) page and download one of the **3.x** releases.

A tip as to which **Python** version to choose is to go to [zephyrproject-rtos
/windows-curses github page](https://github.com/zephyrproject-rtos/windows-curses) and check the latest supported version.

Here's how you do that: the page contains some folders named py*XY* (*XY* is the python version the folder corresponds to). Make a note of the largest *XY* number; this is the latest **Python** version supported, and this is the one you should download. At the time of writing this, version **3.9** was the latest supported one (folder py*39*), even though Python 3.10 had already been released.

When the download is done, run its setup and select "*Custom Installation*" so that you can "*Add Python to environment variables*". You can refer to the following image to see the relevant setting.

![Python Installation](https://members.hellug.gr/sng/pyradio/python1.jpg)


#### Verifying the installation

Either if you have just installed **Python** or you already have it installed, you need to verify that its executable is in the **PATH** (i.e. **Python** can be executed from a console by typing"*python*").

So, go ahead and open a console (the command is **cmd**) and type **python**.

If you get something similar to the following snippet, you are good to go.

    Python 3.6.4 (v3.6.4:d48eceb, Dec 19 2017, 06:54:40) [MSC v.1900 64 bit (AMD64)] on win
    Type "help", "copyright", "credits" or "license" for more information.
    >>>

If the command could not be found, you have to run the installation again, select "*Modify*" and set the "*Add Python to environment variables*" option. You can refer to the following image to see the relevant setting.

![Python Installation Modification](https://members.hellug.gr/sng/pyradio/python2.jpg)

**Note:** If you don't have the setup file of the original **Python** installation, you will have to **download** it from [Python's Windows Downloads](https://www.python.org/downloads/windows/). In case you want to upgrade to the latest version, you **must uninstall** the one currently installed, beforehand.

### 7-Zip installation

[7-Zip](https://www.7-zip.org/) Windows archiver is needed for MPV's installation. **PyRadio** will try to download and run the installation, if [7-Zip](https://www.7-zip.org/) is not already installed.

### Player installation

As already stated [MPV](https://mpv.io) will be automatically installed on a fresh installation.

If the user decides to install a different player, he should have the following in mind:


|          |MPV                               | MPlayer                                                        | VLC                                           |
|----------|----------------------------------|----------------------------------------------------------------|-----------------------------------------------|
| **Pros** | Fully functional | Fully functional                                               | Plays almost all streams |
| **Cons** | - | May not play all streams (e.g. m3u8) | Titles update is not consistent (if any)    |

#### MPV or MPlayer installation

**PyRadio** provides a helper function to install, update and uninstall [MPV](https://mpv.io) and [MPlayer](http://www.mplayerhq.hu/design7/news.html).

This function will be part of the installation procedure, when **PyRadio** detects that this is a fresh installation.

After you have installed or updated **PyRadio**, you cas still enable this function, by executing **PyRadio** and pressing "**F8**". Then **PyRadio** will terminate and you will be presented with a screen similar to the following one:

```
Reading config...
Reading playlist...

Please select an action:
    1. Update MPV
    2. Install MPlayer

    3. Uninstall MPV

    Note:
      VLC media player is already installed

Press 1, 2, 3 or q to Cancel:
```

Press any of the numbers presented to you to execute an action, or press "**q**" to exit.

**Note:** If you already have installed any of these players for a pre **0.8.9.15** installation, you should:

- delete the installed player(s)
- remove the corresponding entry from your **PATH** variable
- use only the above function to manage players

**Note:** If at some point and for whatever reason you want to perform a manual player installation, just refer to the [relevant instructions for MPV](windows-mpv.md), or the [relevant instructions for MPlayer](windows-mplayer.md).

#### VLC installation

If [VLC](https://www.videolan.org/vlc/) is your selection, just go and get it and install it as any other Windows program.

As long as you install it to its default location (e.g "*C:\\Program Files\\VideoLAN\\VLC*" or "*C:\\Program Files (x86)\\VideoLAN\\VLC*") **Pyradio** will be able to detect and use it.

### PyRadio installation

At last!

You are ready to install **PyRadio**!

So here's how you do it: Right click on [this link](https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py) and use your browser "**Save as**" menu entry to save the file in your home folder as **install.py**.

Finally, open a console (press the **Win** key, type **cmd** and press **ENTER**).

Then type:

    cd %USERPROFILE%
    python install.py


#### Fresh python installation?

If you have just installed **Python**, you will probably end up with the following message and the installation script will terminate.


```
PyRadio has installed all required python modules.
In order for them to be properly loaded, the installation script
has to be executed afresh.

Please execute the installation script again, like so:

    python install.py

```

This is perfectly normal; some **Python** modules have been installed, but in order to be used by the installation script, it has to be executed one more time. So you just type (again):

    python install.py

in order to complete the installation.

#### Final steps

If the installation is successful, you will get something similar to the following image:

![Installation image](https://members.hellug.gr/sng/pyradio/win-install.jpg)

**PyRadio** has been installed preforming a "*user installation*", which means that the program is available to your current user only.

Furthermore, if the WARNING shown in the previous image has been shown to you, the executable of the program is not in your PATH (you cannot just open a console and type "*pyradio*" to execute it; you have to use the Icon/Shortcut created on your Desktop to do that).

Now, you can just call it a day; you can run **PyRadio** from its Desktop Shortcut.

If you want to be able to run it from a terminal, you have to add the path shown to you to your [PATH variable](https://www.computerhope.com/issues/ch000549.htm).

**Note:** If you are having a problem finding the path to add to your PATH variable, just copy the one found after right-clicking on the **PyRadio** icon on your Desktop and selection "**Properties**", or follow the instructions shown at [Getting the path to pyradio.exe](#getting-the-path-to-pyradio.exe).

Finally, please keep in mind that, if you upgrade your **Python** version, you will have to update **PyRadio**'s path in your PATH variable (since you will have to reinstall **PyRadio** anyway).


#### Getting the path to pyradio.exe

In case one has not added the "*Scripts*" path to the **PATH** variable, but has to have the path to the executable of the program (in order to execute it from a console, for example), one can just execute **PyRadio** and press "*F9*". Then the following info will be displayed:

![Pressing F9](https:/members.hellug.gr/sng/pyradio/win-f9.jpg)

After **PyRadio** terminates, the following will be displayed:

```
Reading config...
Reading playlist...

PyRadio EXE files:
  System:
    %PROGRAMFILES%\Python310\Scripts\pyradio.exe
  User:
    %APPDATA%\Python\Python310\Scripts\pyradio.exe

Press any key to exit...
```

In this example, both a "**System**" and a "**User**" path to **PyRadio** executable is displayed.

This would be the case after installing a version newer than **0.8.9.14** while a version older than **0.8.9.14** is already installed.

If this is your case, please follow the instructions found in "[Removing an old-style installation](#removing-an-old-style-installation)".

#### Using the Title Logging feature

If you want to use the [Title Logging](README.md#title-logging) feature, and your Country/Region is anything different than **English**, chances are you will have to correctly set your locale for non-unicode applications, which is something you should be doing regardless. Otherwise, the titles' log file may contain unreadable characters.

If you want to go on and set your locale for non-unicode applications, just refer to the following image.

![INTL.CPL](https://members.hellug.gr/sng/pyradio/intl.jpg)

The instructions work for Windows 7 up to 11.

#### Cleaning up

After the installation is completed, there will be some files left on your system, which you may want to remove. These are:

1. **install.py**: The script you originally downloaded. It should be in your home folder.
2. **tmp-pyradio**: A folder containing **PyRadio**'s sources and intermediate installation scripts. It should be in your home folder.

You can safely delete these files.

If you need to have **PyRadio**'s sources, you can just get them from the "*tmp-pyradio*" folder.

## Updating PyRadio

**PyRadio** will inform you when a new release is available and ask you to go on with the update.

If you answer "*y*" to the question asked, **PyRadio** will terminate after creating an update batch file and opening Windows Explorer to its location.

You just double click on the batch file (called **update.bat**) to go on with the update.

In any case, you can perform the update at any time, using the command:

    pyradio -U

**Note:** If **PyRadio** is not in your PATH, you will have to use the full path to it to execute the previous command. Just right-click **Pyradio**'s icon on your Desktop and copy the command found there, or follow the instructions shown at [Getting the path to pyradio.exe](#getting-the-path-to-pyradio.exe). Once you have it, paste it on a console, add a "*-U*" and you are good to go.

### Updating a pre 0.8.9 installation

If you are on a pre 0.8.9 release and want to update **PyRadio**, just follow the [installation instructions](#pyradio-installation), but add the "*--force*" command line parameter to the installation command.

So, instead of

    python install.py

do a

    python install.py --force

## Removing an old-style installation

If you have an old-style installation (an installation done with a version up to **0.8.9.14**), you should remove the installed files which are not used anymore, they just clutter your system.

Just execute **PyRadio** and press "**F7**".

**PyRadio** will search you system and put all the files that should be removed in a BAT file, which it will execute. Just make sure no other apps are open at the time.

## Uninstalling PyRadio

To uninstall **PyRadio** you just press "**F10**" and confirm the action.

Then **PyRadio** will terminate and an "**Explorer Window**" will open containing a BAT file called **uninstall.bat**.

Just double-click on it to complete the procedure.


## Reporting bugs

When a bug is found, please do report it by [opening an issue at github](https://github.com/coderholic/pyradio/issues).

In you report you should, at the very least, state your **pyradio version** and **python version**.

It would be really useful to include **%USERPROFILE%/pyradio.log** in your report.

To create it, enter the following commands in a terminal:

    cd %USERPROFILE%
    del pyradio.log
    pyradio -d

**Note:** If **PyRadio** is not in your PATH, you will have to use the full path to it to execute the previous command. Just right-click **Pyradio**'s icon on your Desktop and copy the command found there, or follow the instructions shown at [Getting the path to pyradio.exe](#getting-the-path-to-pyradio.exe). Once you have it, paste it on a console, add a "*-d*" and you are good to go.


Then try to reproduce the bug and exit **PyRadio**.

Finally, include the file produced in your report.


