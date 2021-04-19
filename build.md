# PyRadio Build Instructions

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Preparing for the installation](#preparing-for-the-installation)
    * [Linux](#linux)
    * [macOS](#macos)
    * [Windows](#windows)
* [Performing the installation](#performing-the-installation)
    * [Updating a pre 0.8.9 installation](#updating-a-pre-0.8.9-installation)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md)


## Preparing for the installation

Before installing **PyRadio** you have to prepare your system, so that you end up with a working installation. The process depends on the OS you are on.

### Linux

Use your distribution method to install 
1. *python-setuptools*
2. *python-requests*
3. *python-dnspython*
4. *sed*
5. any one of *MPV*, *MPlayer* and/or *VLC*.

When you are done, proceed to  "[Performing the installation](#performing-the-installation)".


### macOS

Everything you need to install, run and keep **pyradio** up-to-date is available on [Homebrew](https://github.com/Homebrew/homebrew). If you haven't already downloaded its client, go ahead and do it.

Open a **terminal** and type:

    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

Depending on your Mac OS version, you may have to install **sed** too:

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

    sudo ln -s /Applications/VLC.app/Contents/MacOS/VLC /usr/bin/cvlc

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

### Updating a pre 0.8.9 installation

If you are on a pre 0.8.9 release and want to update **PyRadio**, just follow the instructions above, but add the "*--force*" command line parameter to the installation command.

So, instead of

    python install.py

do a

    python install.py --force

