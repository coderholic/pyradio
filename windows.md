# PyRadio on Windows

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [Running PyRadio on Windows](#running-pyradio-on-windows)
* [How it all works](#how-it-all-works)
* [Installation](#installation)
    * [Python installation](#python-installation)
        * [Installing Python](#installing-python)
        * [Verifying the installation](#verifying-the-installation)
    * [Player installation](#player-installation)
        * [MPV installation](#mpv-installation)
        * [MPlayer installation](#mplayer-installation)
        * [VLC installation](#vlc-installation)
    * [PyRadio installation](#pyradio-installation)
        * [Fresh python installation?](#fresh-python-installation?)
        * [Final steps](#final-steps)
        * [Cleaning up](#cleaning-up)
* [Updating PyRadio](#updating-pyradio)
    * [Updating a pre 0.8.9 installation](#updating-a-pre-0.8.9-installation)
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

[MPV](https://mpv.io/) is the preferred player for *Windows*. Its installation takes a few extra steps, but once installed, it's super reliable due to its using "*Named Pipes*" (in a client-server paradigm) for its communication with the client application (in this case **PyRadio**.)

Installing [MPlayer](http://www.mplayerhq.hu/) also takes a couple of extra steps, and you may find that some streams (e.g. m3u8) may not be playable. Furthermore, special care has to be taken in order to be able to save the volume of the player.

[VLC](https://www.videolan.org/vlc/) is much easier to install, but song titles' updating may not be 100% consistent (if any). If this is not a deal breaker for you, then just go on and use [VLC](https://www.videolan.org/vlc/) as **PyRadio**'s player.

Other than that, you will have a fully functional **PyRadio** installation.

Having said that, let us proceed with the installation.

## Installation

The installation consists of three steps:

1. **Python** installation
2. **Player** installation
3. **PyRadio** installation

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

### Player installation

It's time to decide which player you want to use, either [MPlayer](http://www.mplayerhq.hu/design7/news.html) or [VLC](https://www.videolan.org/vlc/), or even both of them.

This is what you should know before making your decision:

|          |MPV                               | MPlayer                                                        | VLC                                           |
|----------|----------------------------------|----------------------------------------------------------------|-----------------------------------------------|
| **Pros** | Fully functional | Fully functional                                               | Plays almost all streams |
| **Cons** | - | May not play all streams (e.g. m3u8) | Titles update is not consistent (if any)    |


#### MPV installation

If [MPV](https://mpv.io) is your selection, please refer to the [relevant instructions](windows-mpv.md).

#### MPlayer installation

If [MPlayer](http://www.mplayerhq.hu/) is your selection, please refer to the [relevant instructions](windows-mplayer.md).

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

If you have just installed **Pyhon**, you will probably end up with the following message and the installation script will terminate.


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

Furthermore, if the WARNING shown in the previous image has been shown to you, the executable of the program is not in your PATH (you cannot just open a console and type "*pyradio*" to execute it; you have to use the Ison/Shortcut created on your Desktop to do that).

Now, you can just call it a day; you can run **PyRadio** from its Desktop Shortcut.

If you want to be able to run it from a console, you have to add the path shown to you to your PATH variable. To do that, just have a look at the following image:

![aaa](https:/members.hellug.gr/sng/pyradio/path.jpg)

**Note:** If you are having a problem finding the path to add to your PATH variable, just copy the one found after right-clicking on the **PyRadio** icon on your Desktop and selection "**Properties**".

Finally, please keep in mind that, if you upgrade your **Python** version, you will have to update **PyRadio**'s path in your PATH variable (since you will have to reinstall **PyRadio** anyway).

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

**Note:** If **PyRadio** is not in your PATH, you will have to use the full path to it to execute the previous command. Just right-click **Pyradio**'s icon on your Desktop and copy the command found there. Paste it on a console, add a "*-U*" and you are good to go.

### Updating a pre 0.8.9 installation

If you are on a pre 0.8.9 release and want to update **PyRadio**, just follow the [installation instructions](#pyradio-installation), but add the "*--force*" command line parameter to the installation command.

So, instead of

    python install.py

do a

    python install.py --force

## Uninstalling PyRadio

To uninstall **PyRadio** you just have to open a console window and execute the command:

    pyradio -R

**PyRadio** create an uninstall batch file and open Windows Explorer to its location.

You just double click on the batch file (called **uninstall.bat**) to complete the procedure.

**Note:** If **PyRadio** is not in your PATH, you will have to use the full path to it to execute the previous command. Just right-click **Pyradio**'s icon on your Desktop and copy the command found there. Paste it on a console, add a "*-R*" and you are good to go.

## Reporting bugs

When a bug is found, please do report it by [opening an issue at github](https://github.com/coderholic/pyradio/issues).

In you report you should, at the very least, state your **pyradio version** and **python version**.

It would be really useful to include **%USERPROFILE%/pyradio.log** in your report.

To create it, enter the following commands in a terminal:

    cd %USERPROFILE%
    del pyradio.log
    pyradio -d

Then try to reproduce the bug and exit **PyRadio**.

Finally, include the file produced in your report.

**Note:** If **PyRadio** is not in your PATH, you will have to use the full path to it to execute the previous command. Just right-click **Pyradio**'s icon on your Desktop and copy the command found there. Paste it on a console, add a "*-d*" and you are good to go.

