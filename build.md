# PyRadio Build Instructions

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [Building from source](#building-from-source)
* [Preparing for the installation](#preparing-for-the-installation)
    * [Linux](#linux)
    * [macOS](#macos)
    * [Windows](#windows)
* [Performing the installation](#performing-the-installation)

<!-- vim-markdown-toc -->
[[Return to main doc](README.md)]

## Building from source

Reasons to build from source

* A pre-built package is not available to you.
* You want to use a particular python version. For example, most pre-built packages nowadays are built using python 3.x. If for any reason you have to use python 2.x, this is the way to go.

For the installation you will need:

1.  ***setuptools*** (e.g. *python-setuptools*, *python3-setuptools* or *python2-setuptools*)
 2. ***requests*** (e.g. *python-requests*, *python3-requests* or *python2-requests*) to be already installed.

The procedure presented here will not provide you with the sources; it will download and install them and then delete them.  If you have to have **PyRadio**'s sources, you can just:

```
git clone https://github.com/coderholic/pyradio.git
```

or download a zip from **PyRadio**'s [main page](https://github.com/coderholic/pyradio).

## Preparing for the installation

Before installing **PyRadio** you have to prepare your system, so that you end up with a working installation. The process depends on the OS you are on.

### Linux

Use your distribution method to install *python-setuptools*, *python-requests*, *sed* and any one of *MPV*, *MPlayer* and/or *VLC*.

When you are done, proceed to  "[Performing the installation](#performing-the-installation)".


### macOS

Everything you need to install, run and keep **pyradio** up-to-date is available on [Homebrew](https://github.com/Homebrew/homebrew). If you haven't already downloaded its client, go ahead and do it.

Open a **terminal** and type:

```
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Depending on your Mac OS version, you may have to install **sed** too:

```
brew install gnu-sed --default-names
```

Now it's time to install a media player. You are free to install any one of them or even more than one...

1\. ***MPV***

```
brew install mpv
```

2\. ***MPlayer***

```
brew install mplayer
```

3\. ***VLC***

You  can get VLC from the official site or from [Homebrew](https://github.com/Homebrew/homebrew).

a\. ***Oficial package***

You just go to [videolan.org](http://www.videolan.org/vlc/download-macos.html),  download and install the program as you usually do with any other application.

Finally, add a symbolic link to the executable as follows:

```
sudo ln -s /Applications/VLC.app/Contents/MacOS/VLC /usr/bin/cvlc
```

b\. ***Homebrew package***

```
brew cask install vlc
sudo ln -s /usr/local/bin/vlc /usr/local/bin/cvlc
```

Your system is ready now for **pyradio** to be installed. You can follow the instructions given at "[Performing the installation](#performing-the-installation)".

### Windows

Windows installation is presented in its [own page](windows.md).

## Performing the installation

First thing you do is get the installation script. Open a **terminal** and type:

```
cd
wget https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py
```

or using curl:

```
cd
curl -L https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py -o install.py
```

**Note**: If you have neither *wget* or *curl* installed, just right click on [this link](https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py) and use your browser "**Save link as**" menu entry to save the file in your home folder.

Finally, execute the command:

```
python install.py
```

On **Debian** based systems you will have to execute:

```
python3 install.py
```

If for some reason you want a **python 2** installation, execute:

```
python2 install.py
```

