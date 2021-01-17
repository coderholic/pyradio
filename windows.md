# PyRadio on Windows

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of contents

* [Running PyRadio on Windows](#running-pyradio-on-windows)
* [How it all works](#how-it-all-works)
* [Installation](#installation)
    * [1. Python installation](#python-installation)
        * [1.1 Installing Python](#installing-python)
        * [1.2 Verifying the installation](#verifying-the-installation)
    * [2. Player installation](#player-installation)
        * [2.1 MPlayer installation](#mplayer-installation)
        * [2.2 VLC installation](#vlc-installation)
    * [3. Git installation (optional)](#git-installation-optional)
    * [4. PyRadio installation](#pyradio-installation)
        * [4.1 Using Git](#using-git)
        * [4.2 Not using Git](#not-using-git)
        * [4.3 Final steps](#final-steps)
* [Updating PyRadio](#updating-pyradio)
    * [Updating with Git](#updating-with-git)
    * [Updating without Git](#updating-without-git)
* [Uninstalling PyRadio (or Cleaning up)](#uninstalling-pyradio-or-cleaning-up)
* [Reporing bugs](#reporting-bugs)

[[Back to Build Instructions]](build.md) | [[Back to README]](README.md)

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

The installation consists of three (optionally four) steps:

1. **Python** installation
2. **Player** installation
3. **Git** installation (optional)
4. **PyRadio** installation

### 1. Python installation

#### 1.1 Installing Python

If you don't already have **Python**, just get to its [Windows Downloads](https://www.python.org/downloads/windows/) page and download the latest **3.x** release.

When the download is done, run its setup and select "*Custom Installation*" so that you can "*Add Python to environment varaibles*". You can refer to the following image to see the relevant setting.

[Python Installation](https://members.hellug.gr/sng/pyradio/python1.jpg)


#### 1.2 Verifying the installation

Either if you have just installed **Python** or you already have it installed, you need to verify that its executable is in the **PATH** (i.e. **Python** can be executed from a console by typing"*python*").

So, go ahead and open a console (the command is **cmd**) and type **python**.

If you get something similar to the following snippet, you are good to go.

```
Python 3.6.4 (v3.6.4:d48eceb, Dec 19 2017, 06:54:40) [MSC v.1900 64 bit (AMD64)] on win
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

If the command could not be found, you have to run the installation again, select "*Modify*" and set the "*Add Python to environment variables*" option. You can refer to the following image to see the relevant setting.

[Python Installation Modification](https://members.hellug.gr/sng/pyradio/python2.jpg)

**Note:** If you don't have the setup file of the original **Python** installation, you will have to **download** it from [Python's Windows Downloads](https://www.python.org/downloads/windows/). In case you want to upgrade to the latest version, you **must uninstall** the one currently installed, beforehand.

### 2. Player installation

It's time to decide which player you want to use, either [MPlayer](http://www.mplayerhq.hu/design7/news.html) or [VLC](https://www.videolan.org/vlc/), or even both of them.

This is what you should know before making your decision:

|          | MPlayer                                                        | VLC                                           |
|----------|----------------------------------------------------------------|-----------------------------------------------|
| **Pros** | Fully functional                                               | Easy installation<br>Plays almost all streams |
| **Cons** | Extra steps to install<br>May not play all streams (e.g. m3u8) | Titles update is not consistent (if any)    |


#### 2.1 MPlayer installation

If [MPlayer](http://www.mplayerhq.hu/) is your selection, please refer to the [relevant instructions](windows-mplayer.md).

#### 2.2 VLC installation

If [VLC](https://www.videolan.org/vlc/) is your selection, just go and get it and install it as any other Windows program.

As long as you install it to its default location (e.g "*C:\\Program Files\\VideoLAN\\VLC*" or "*C:\\Program Files (x86)\\VideoLAN\\VLC*") **Pyradio** will be able to detect and use it.
    

### 3. Git installation (optional)

This is an optional step, so if you do not want to install yet another program to your PC, you are free to skip it.

Having said that, why would you install **Git**?

Well, it makes installing and updating **PyRadio** much easier and faster. That's all.

If you decide to install it, this is how you do it:

1. Download the latest [Git for Windows](https://gitforwindows.org) installer.

2. When you've successfully started the installer, you should see the **Git Setup wizard** screen. Follow the **Next** and **Finish** prompts to complete the installation. The default options are pretty sensible for most users.

3. Open a console (press the **Win** key, type **cmd** and press **ENTER**).

4. Run the following commands to configure your Git username and email using the following commands, using you name and email at the appropriate places:

```
git config --global user.name "FirstName LastName"
git config --global user.email "my@email.com"
```

You are done!!!


### 4. PyRadio installation

At last!

You are ready to install **PyRadio**!

So here's how you do it:

#### 4.1 Using Git

If you have Git installed, you open a console (press the **Win** key, type **cmd** and press **ENTER** or if you are on Windows 10, use **Run it as Administrator** as you can see in the following image).

[Run as Administrator](https://members.hellug.gr/sng/pyradio/run-as-admin.jpg)

Then type:

```
git clone https://github.com/coderholic/pyradio.git
cd pyradio
devel\build_install_pyradio
```

#### 4.2 Not using Git

Go to [PyRadio's Releases page](https://github.com/coderholic/pyradio/releases) and download the latest release (either a zip or a tar.gz file).

Extract this file to your "*Home*" directory ("**C:\\Users\\[Your User Name]**" or "**%USERPROFILE%**) - you will get a directory whose name is similar to  "**pyradio-0.7.9**".

I will use this name for the following examples; you will have to use the actual name of directory you got from the extraction.

Finally, open a console (press the **Win** key, type **cmd** and press **ENTER** or if you are on Windows 10, use **Run it as Administrator** as you can see in the following image).

[Run as Administrator](https://members.hellug.gr/sng/pyradio/run-as-admin.jpg)

Then type:

```
cd pyradio-0.7.9
devel\build_install_pyradio
```

#### 4.3 Final steps

If the installation is successful, you will get something similar to the following snippet:

```
...
Installing pyradio-script.py script to C:\Users\spiros\AppData\Local\Programs\Python\Python37\Scripts
Installing pyradio.exe script to C:\Users\spiros\AppData\Local\Programs\Python\Python37\Scripts

Installed c:\users\spiros\appdata\local\programs\python\python37\lib\site-packages\pyradio-0.7.9-py3.7.egg
Processing dependencies for pyradio==0.7.9
Finished processing dependencies for pyradio==0.7.9

*** HTML files copyed to "C:\Users\spiros\AppData\Roaming\pyradio\help"
=== Player "mplayer" found in "C:\Users\spiros\mplayer"
=== Player "mplayer" found in PATH
*** Installing Dekstop Shortcut


Installation successful!

```

Finally, install **PyRadio's Python packages** requirements:

```
pip install windows-curses
pip install pywin32
```

And you are done!

If you are not using Git, you can safely delete the **pyradio-0.7.9** directory.

Finally, you can type **pyradio** and enjoy!

**Note:** For your convenience, the installation batch file has tried to installed a shortcut on your Desktop. You can use it to launch **PyRadio** and optionally modify it (change font size, window dimensions, etc). If it's not there, you can just copy it from the "*help*" directory of the **Explorer File Manager** which will open after executing **pyradio -ocd**.


## Updating PyRadio

**PyRadio** will inform you when a new release is available.

To start the update procedure, close **PyRadio** if it's still running.

Then do one of the following depending on whether you have **Git** installed or not:

### Updating with Git


Open a console (press the **Win** key, type **cmd** and press **ENTER**) and execute the commands:

```
cd pyradio
git pull
devel\build_install_pyradio
```


### Updating without Git

The procedure is the same as installing, so please follow the [relevant instructions](#not-using-git).


## Uninstalling PyRadio (or Cleaning up)

To uninstall **PyRadio** you will have to use the "**-u**" (uninstall) parameter.

This procedure will remove any **PyRadio** files installed in your system, but will leave instact **PyRadio** configuration files and python, mplayer and git (if installed).

To uninstall **PyRadio** open a console (press the **Win** key, type **cmd** and press **ENTER** or if you are on Windows 10, use **Run it as Administrator** as you can see in the following image).

[Run as Administrator](https://members.hellug.gr/sng/pyradio/run-as-admin.jpg)

Then navigate to the previously downloaded **PyRadio** setup folder, and execute *devel\\build_install_pyradio -u*.

Example:

    C:\Users\spiros\pyradio>devel\build_install_pyradio -u
    Uninstalling PyRadio
    ** Gathering information...
    ** Removing executable ... done
    ** Removing Desktop shortcut ... done
    Looking for python installed files...
    ** Removing "pyradio-0.8.8-py3.7.egg" ... done
    ** Removing "pyradio-0.7.9-py3.7.egg" ... done
    ** Removing "pyradio-0.6.3-py3.7.egg" ... done
    PyRadio successfully uninstalled!

    *********************************************************

    PyRadio has not uninstalled MPlayer, Python and/or Git.
    You will have to manually uninstall them.

    PyRadio user files are left instact. You can find them at
    C:\Users\spiros\AppData\Roaming\pyradio

    **********************************************************

In this example, running *devel\\build_install_pyradio -u* has removed **PyRadio** python 3.7 installation files.

The script has detected (and removed) version *0.8.8* (probably the current or previous version), along with verisons *0.7.9* and *0.6.3* (older versions previously installed).

I would recommend to execute *devel\\build_install_pyradio -u* from time to time, and reinstall **PyRadio** right after its completion.

### Reporting bugs

When a bug is found, please do report it by [opening an issue at github](https://github.com/coderholic/pyradio/issues).

In you report you should, at the very least, state your **pyradio version** and **python version**.

It would be really useful to include **%USERPROFILE%/pyradio.log** in your report.

To create it, enter the following commands in a terminal:

    cd %USERPROFILE%
    del pyradio.log
    pyradio -d

Then try to reproduce the bug and exit **PyRadio**.

Finally, include the file produced in your report.


