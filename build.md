# Building PyRadio from source

Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of contents

* [Building from source](#building-from-source)
    * [Preparing for the installation](#preparing-for-the-installation)
        * [Linux](#linux)
        * [macOS](#macos)
        * [Windows](windows.md)
    * [Performing the installation](#performing-the-installation)
        * [Development version](#development-version)
        * [Stable version](#stable-version)
* [Return to main doc](README.md)

## Building from source

Reasons to build from source

* A pre-built package is not available to you.
* You want to use a particular python version. For example, most pre-built packages nowadays are built using python 3.x. If for any reason you have to use python 2.x, this is the way to go.

For the installation you will need ***git*** and ***setuptools*** (e.g. *python-setuptools*, *python3-setuptools* or *python2-setuptools*) to be already installed.

Finally, you will use the ***build_install_pyradio*** script, located int the ***devel*** directory.

To see your options, execute:

```
devel/build_install_pyradio -h
```

## Preparing for the installation

Before installing **PyRadio** you have to prepare your system, so that you end up with a working installation. The process depends on the OS you are on.

### Linux

Use your distribution method to install *python-setuptools*, *git*, *sed* and any one of *MPV*, *MPlayer* and/or *VLC*.

When you are done, proceed to  "[Performing the installation](#performing-the-installation)".


### macOS 

Everything you need to install, run and keep **pyradio** up-to-date is available on [Homebrew](https://github.com/Homebrew/homebrew). If you haven't already downloaded its client, go ahead and do it.

Open a **terminal** and type:

```
/usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

Then just install **git**:

```
brew install git
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



## Performing the installation

First thing you do is get the source. Open a **terminal** and type:

```
git clone https://github.com/coderholic/pyradio.git
cd pyradio
```

Then you have to decide to either build the development version or one of the available stable versions.

### Development version

```
devel/build_install_pyradio
```

### Stable version

Get tag information.

```
git fetch --all --tags --prune
git tag
```

This will report to you something similar to:

```
0.1
0.4
0.6.0
```

Now is the time to pick a version.

For this example we will go with v. **0.6.0**.

```
git checkout tags/0.6.0 -b 0.6.0
```

Finally, build and install

```
devel/build_install_pyradio
```

