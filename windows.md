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
        * [MPlayer installation](#mplayer-installation)
        * [VLC installation](#vlc-installation)
    * [PyRadio installation](#pyradio-installation)
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

Then, due to reasons that are of no importance right now, [mpv](https://mpv.io/) is not (yet?) supported. That leaves us with [MPlayer](http://www.mplayerhq.hu/design7/news.html) and [VLC](https://www.videolan.org/vlc/).

Installing [MPlayer](http://www.mplayerhq.hu/) takes a couple of extra steps, and you may find that some streams (e.g. m3u8) may not be playable. Furthermore, special care has to be taken in order to be able to save the volume of the player.

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

If you don't already have **Python**, just get to its [Windows Downloads](https://www.python.org/downloads/windows/) page and download the latest **3.x** release.

When the download is done, run its setup and select "*Custom Installation*" so that you can "*Add Python to environment varaibles*". You can refer to the following image to see the relevant setting.

[Python Installation](https://members.hellug.gr/sng/pyradio/python1.jpg)


#### Verifying the installation

Either if you have just installed **Python** or you already have it installed, you need to verify that its executable is in the **PATH** (i.e. **Python** can be executed from a console by typing"*python*").

So, go ahead and open a console (the command is **cmd**) and type **python**.

If you get something similar to the following snippet, you are good to go.

    Python 3.6.4 (v3.6.4:d48eceb, Dec 19 2017, 06:54:40) [MSC v.1900 64 bit (AMD64)] on win
    Type "help", "copyright", "credits" or "license" for more information.
    >>>

If the command could not be found, you have to run the installation again, select "*Modify*" and set the "*Add Python to environment variables*" option. You can refer to the following image to see the relevant setting.

[Python Installation Modification](https://members.hellug.gr/sng/pyradio/python2.jpg)

**Note:** If you don't have the setup file of the original **Python** installation, you will have to **download** it from [Python's Windows Downloads](https://www.python.org/downloads/windows/). In case you want to upgrade to the latest version, you **must uninstall** the one currently installed, beforehand.

### Player installation

It's time to decide which player you want to use, either [MPlayer](http://www.mplayerhq.hu/design7/news.html) or [VLC](https://www.videolan.org/vlc/), or even both of them.

This is what you should know before making your decision:

|          | MPlayer                                                        | VLC                                           |
|----------|----------------------------------------------------------------|-----------------------------------------------|
| **Pros** | Fully functional                                               | Easy installation<br>Plays almost all streams |
| **Cons** | Extra steps to install<br>May not play all streams (e.g. m3u8) | Titles update is not consistent (if any)    |


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

#### Final steps

If the installation is successful, you will get something similar to the following snippet:

    ...
    Installing pyradio-script.py script to C:\Users\spiros\AppData\Local\Programs\Python\Python37\Scripts
    Installing pyradio.exe script to C:\Users\spiros\AppData\Local\Programs\Python\Python37\Scripts

    Installed c:\users\spiros\appdata\local\programs\python\python37\lib\site-packages\pyradio-0.8.9-py3.7.egg
    Processing dependencies for pyradio==0.8.9
    Finished processing dependencies for pyradio==0.8.9

    *** HTML files copyed to "C:\Users\spiros\AppData\Roaming\pyradio\help"
    === Player "mplayer" found in "C:\Users\spiros\mplayer"
    === Player "mplayer" found in PATH
    *** Installing Dekstop Shortcut


    Installation successful!


Finally, you can type **pyradio** and enjoy!

**Note:** For your convenience, the installation batch file has tried to installed a shortcut on your Desktop. You can use it to launch **PyRadio** and optionally modify it (change font size, window dimensions, etc). If it's not there, you can just copy it from the "*help*" directory of the **Explorer File Manager** which will open after executing **pyradio -ocd**.


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


