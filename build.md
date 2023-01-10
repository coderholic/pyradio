# PyRadio Build Instructions

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Current state of the project](#current-state-of-the-project)
    * [What does it all mean and why should you care](#what-does-it-all-mean-and-why-should-you-care)
* [Preparing for the installation](#preparing-for-the-installation)
    * [Linux](#linux)
        * [Notice for Python 2 users](#notice-for-python-2-users)
        * [Installation on the BSDs](#installation-on-the-bsds)
        * [Rasberry Pi installation](#rasberry-pi-installation)
    * [macOS](#macos)
    * [Windows](#windows)
* [Performing the installation](#performing-the-installation)
    * [Note for macOS users](#note-for-macos-users)
    * [Updating a pre 0.8.9 installation](#updating-a-pre-0.8.9-installation)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md)

## Current state of the project

Starting with version **0.8.9.15**, **PyRadio** has changed its installation method from invoking *setup.py* directly to *pip* (i.e. from "*python setup.py install*" to "*python -m pip .*"). This is a must for all **Python** projects in order to keep up with the latest developments. For more info, please refer to "[Why you shouldn't invoke setup.py directly](https://blog.ganssle.io/articles/2021/10/setup-py-deprecated.html)".

### What does it all mean and why should you care

Moving to the **pip** way of doing things has its implications:

1. **PyRadio** will be installed as a pip package.

2. **PyRadio** will no longer be installed as a system-wide package. \
\
This means that after installing **PyRadio**, it will only be available to the current user. If another user wants to use it as well, he would have to install it again. \
\
In other words, in order to have a **Pyradio system-wide installation**, your distribution has to provide a package for it.

3. As I'm starting the procedure to move away from *Python 2*, **PyRadio** will not be compatible with it on *macOs* and *Windows* (but will still be on *Linux*, at least for the time being).


## Preparing for the installation

Before installing **PyRadio** you have to prepare your system, so that you end up with a working installation. The process depends on the OS you are on.


### Linux

Use your distribution method to install

1. *python-pip*
2. *python-setuptools*
3. *python-wheel*
4. *python-requests*
5. *python-dnspython*
6. *python-psutil*
6. *python-netifaces*
7. *sed*
8. any one of *MPV*, *MPlayer* and/or *VLC*.

#### Notice for Python 2 users

If you are still using **Python 2**, plase make sure "**pip**" is installed. Execute the following command to verify its existance:

    python[2] -m pip list

If you get a response, you are good to go. Otherwise, use your distro package manager to install it.

If your distro does not provide it (some do not anymore), use the following commands to get it:

    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py --output get-pip.py
    sudo python[2] get-pip.py

or

    wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
    sudo python[2] get-pip.py

When you are done, proceed to  "[Performing the installation](#performing-the-installation)".

#### Installation on the BSDs

If you are on any of the BSDs, please do install **bash** beforehand.


#### Rasberry Pi installation

If installing on a Rasberry Pi, there are a couple of things you should be aware of:

1. The default player will be **MPlayer**
3. If you still want to use **MPV**, please make sure you increase the *Connection timeout* value to at least 20 (sometimes even 30 for some machines). Even then, your machine may eventually crash, if it's on the lower end of things and **PyRadio** is left running for hours.


### macOS

First thing you do is install python dependencies (assuming python 3 is installed):

    python3 -m pip install --upgrade pip wheel setuptools requests dnspython psutil netifaces

Everything else you need to install and run **pyradio** is available on [Homebrew](https://github.com/Homebrew/homebrew). If you haven't already downloaded its client, go ahead and do it.

Open a **terminal** and type:

    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

Depending on your macOS version, you may have to install **sed** too:

    brew install gnu-sed --default-names

Now it's time to install a media player. You are free to install any one of them or even more than one...

1\. ***MPV***

    brew install mpv

2\. ***MPlayer***

    brew install mplayer

3\. ***VLC***

You  can get VLC from the official site or from [Homebrew](https://github.com/Homebrew/homebrew).

a\. ***Oficial package***

You just go to [videolan.org](http://www.videolan.org/vlc/download-macos.html),  download and install the program as you usually do with any other application.

Finally, add a symbolic link to the executable as follows:

    sudo ln -s /Applications/VLC.app/Contents/MacOS/VLC /usr/local/bin/cvlc

b\. ***Homebrew package***

    brew cask install vlc
    sudo ln -s /usr/local/bin/vlc /usr/local/bin/cvlc

Your system is ready now for **pyradio** to be installed. You can follow the instructions given at "[Performing the installation](#performing-the-installation)".

### Windows

Windows installation is presented in its [own page](windows.md).

## Performing the installation

First thing you do is get the installation script. Open a **terminal** and type:

    cd
    wget https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py

or using curl:

    cd
    curl -L https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py -o install.py

**Note**: If you have neither *wget* or *curl* installed, just right click on [this link](https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py) and use your browser "**Save link as**" menu entry to save the file in your home folder.

Finally, execute the command:

    python install.py

On **Debian** based systems you will have to execute:

    python3 install.py

If for some reason you want a **python 2** installation, execute:

    python2 install.py


### Note for macOS users

This release of **PyRadio** has been tested on **Catalina** and **Big Sur**.

On **Catalina** the executable has been placed on a location which is not directly accessible (not in the PATH). **PyRadio** will try to link it to your **bin** folder (creating *~/bin/pyradio*), and **PyRadio** will be ready yo be executed, provided that this folder is in your PATH and that **Homebrew** default installation folders have been used during the installation of **Python 3**.

In case a different **Homebrew** location has been used (or a different package manager, for this matter), you can just point the installation to the correct path, using the following command (post installation):

    python3 install.py --brew /path/to/homebrew/installation

so that **PyRadio** can find and link the executable to your **bin** folder.

### Updating a pre 0.8.9 installation

If you are on a pre 0.8.9 release and want to update **PyRadio**, just follow the instructions above, but add the "*--force*" command line parameter to the installation command.

So, instead of

    python install.py

do a

    python install.py --force

