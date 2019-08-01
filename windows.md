# PyRadio

Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of contents

* [Running PyRadio on Windows](#running-pyradio-on-windows)
* [How it all works](#how-it-all-works)
* [Installation](#installation)
    * [1. Python installation](#python-installation)
        * [1.1 Installing Python](#installing-python)
        * [1.2 Verifying the installation](#verifying-the-installation)
    * [2. MPlayer installation](#mplayer-installation)
        * [2.1 Adding MPlayer to the PATH](#adding-mplayer-to-the-path)
    * [3. Git installation (optional)](#git-installation-optional)
    * [4. PyRadio installation](#pyradio-installation)
        * [4.1 Using Git](#using-git)
        * [4.2 Not using Git](#not-using-git)
        * [4.3 Final steps](#final-steps)
    * [5. Updating PyRadio](#updating-pyradio)
        * [5.1 Updating with Git](#updating-with-git)
        * [5.2 Updating without Git](#updating-without-git)
* [Back](build.md)
* [Back to README](README.md)

## Running PyRadio on Windows

What? A linux console application on Windows?

Yes, sure. Why not?

**PyRadio** is a *python* script after all, and *python* does run on Windows. So, with a little bit of tweaking of the code, it is possible.

This page will guide you through the process of installing, updating and running **PyRadio** on Windows.

## How it all works

First of all, let me tell you that if you are still running Windows XP, you can just stop reading right now; it won't happen...

Then, due to reasons that are of no importance right now, [MPlayer](http://www.mplayerhq.hu/design7/news.html) is the only player that can be used. Furthermore, special care has to be taken in order to be able to save the volume of the player.

Other than that, you will have a fully functional **PyRadio** installation.

Having said that, let us proceed with the installation.

## Installation

The installation consists of three (optionally four) steps:

1. **Python** installation
2. **MPlayer** installation
3. **Git** installation (optional)
4. **PyRadio** installation

### 1. Python installation

#### 1.1 Installing Python

If you don't already have **Pyhton**, just get to its [Windows Downloads](https://www.python.org/downloads/windows/) page and download the latest **3.x** release.

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

If the command could not be found, you have to run the installation again, select "*Modify*" and set the "*Add Python to environment varaibles*" option. You can refer to the following image to see the relevant setting.

[Python Installation Modification](https://members.hellug.gr/sng/pyradio/python2.jpg)


**Note:** If you don't have the setup file of the original **Python** installation, you will have to **download** it from [Python's Windows Downloads](https://www.python.org/downloads/windows/). In case you want to upgrade to the latest version, you **must uninstall** the one currently installed, beforehand.

### 2. MPlayer installation

Go to [MPlayer's home](http://www.mplayerhq.hu/) and open the [download](http://www.mplayerhq.hu/design7/dload.html) page. Then scroll down to the **Binaries** section and get to the [MPlayer Windows builds](http://oss.netfarm.it/mplayer/) page. Then scroll down again until you get to the **Build selection table** to select an installation bundle.

**Note:** I am stating here all the links, although all one has to do is get to the last one and download the **MPlayer setup**. This is done so that in case any of the links change in the future, the way to go will be known, having [MPlayer's home page](http://www.mplayerhq.hu/) as a starting point.

You will end up downloading a **7z archive**, which contains a directory whose name is similar to **MPlayer-corei7-r38135+gb272d5b9b6**.

Extract this directory to whatever place you like and **rename** it to **mplayer**.

Here comes the tricky part...

In case you:

a. are the Administrator of the PC, or

b. have administrative rights

move (cut) the **mplayer** directory to **C:\\** (paste).

Make a note that you will add "**C:\\mplayer**" to PATH.

In any other case, move the **mplayer** directory to either on of the following locations:

a. **%USERPROFILE%**

    This is actually your "*Home*" directory.

    Please make a note that you will add "**%USERPROFILE%\\mplayer** to PATH.

b. **%APPDATA%\\pyradio**

    This is (or will be) "*PyRadio's configuration directory*".

    In case the **pyradio** directory does not exit, you just go ahead and create it.

    (Make a note that you will add "**%APPDATA%\\pyradio\\mplayer** to PATH)

In either case, in order to do that, open an **Explorer File Manager** window, and enter at its location field **%USERPROFILE%** or **%APPDATA%**.

If you are unsure on how to do that, please refer to the following image (you can ENTER **%USERPROFILE%** or **%APPDATA%** or any other Windows System Variable this way).

[Navigating to %APPDATA%](https://members.hellug.gr/sng/pyradio/appdata.jpg)


#### 2.1 Adding MPlayer to the PATH

The final step is to add MPlayer to the PATH System Variable.

Now, you already know the string that has to be added (you have made a note of it in the previous step).

There's just one thing to say here: Windows provide a "*User variable for User*" and a "*System variables*" section in the "*Environment Variables*" window.

If the string to add is "**C:\\mplayer**", you add it to the "*System variables*" section, otherwise to the "*User variables for User*" section.

In order to make the actual addition, please refer to the following image.

[Adding MPlayer to the PATH](https://members.hellug.gr/sng/pyradio/path.jpg)

After applying the changes you should **log off and back on** or **restart the system**, because changes done to the PATH variable will take effect the next time you log into the system.

When you are back on, verify that you can run **MPlayer**; open a console (press the **Win** key, type **cmd** and press **ENTER**) and type "**mplayer**".

If you get something similar to the following snippet, you are all good.

```
MPlayer Redxii-SVN-r38119-6.2.0 (x86_64) (C) 2000-2018 MPlayer Team
Using FFmpeg N-92801-g7efe84aebd (2018-12-25 00:44:17 +0100)
Compiled on 2018-12-25 13:55:17 EST (rev. 1)
Usage:   mplayer [options] [url|path/]filename
```

If **mplayer** was not found, you just have to go through the PATH modification procedure again.


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

If you have Git installed, you open a console (press the **Win** key, type **cmd** and press **ENTER**) and type:

```
git clone https://github.com/coderholic/pyradio.git
cd pyradio
devel\build_install_pyradio
```

#### 4.2 Not using Git

Go to [PyRadio's Releases page](https://github.com/coderholic/pyradio/releases) and download the latest release (either a zip or a tar.gz file).

Extract this file to your "*Home*" directory ("**C:\\Users\\[Your User Name]**" or "**%USERPROFILE%**) - you will get a directory whose name is similar to  "**pyradio-0.7.9**".

I will use this name for the following examples; you will have to use the actual name of directory you got from the extraction.

Then open a console (press the **Win** key, type **cmd** and press **ENTER**) and type:

```
cd pyradio-0.7.9
cd pyradio
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


### 5. Updating PyRadio

**PyRadio** will inform you when a new release is available. 

To start the update procedure, close **Pyradio** if it's still running.

Then do one of the following depending on whether you have **Git** installed or not:

#### 5.1 Updating with Git


Open a console (press the **Win** key, type **cmd** and press **ENTER**) and execute the commands:

```
cd pyradio
git pull
devel\build_install_pyradio
```


#### 5.2 Updating without Git

The procedure is the same as installing, so please follow the [relevant instructions](#not-using-git).
