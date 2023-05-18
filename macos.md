# PyRadio macOS installation

**PyRadio**: Command line internet radio player.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Preface](#preface)
* [Install a media player](#install-a-media-player)
* [Get the installation script](#get-the-installation-script)
* [Python3 installation](#python3-installation)
    * [Dependencies installation](#dependencies-installation)
    * [PyRadio installation](#pyradio-installation)
* [Installation of Additional Package Managers](#installation-of-additional-package-managers)
    * [Homebrew](#homebrew)
    * [MacPorts](#macports)

<!-- vim-markdown-toc -->

[[Return to PyRadio Build Instructions]](build.md)

## Preface

**PyRadio** on macOS can only be installed on **Python 3** through **pipx**.

Furtermore, the pipx installation will be a fully isolated one, which means that all dependencies will be installed along with **PyRadio** in a virtual environment.

That is a one-way street to follow since the combination of macOS versions, python installation methods and player installation methods is too complex to provide a complete installation guide for **PyRadio**.

[pipx](https://pypa.github.io/pipx/) provides a standardization of the whole procedure which leads to an acceptable (enjoyable even) user experience.


## Install a media player

First of all you will install a supported media player (**MPV**, **MPLayer** or **VLC**). You are free to install any one of them or even more than one. The steps to follow from now on depends entirely on you, meaning depends entirely on the media player(s) you want to install and use with **PyRadio**.

**1\. VLC**

**VLC** provides a MacOS package, so you can just go get it from [its site](https://www.videolan.org/vlc/). This is the cleaner way and I would recommend it.

If this is the player you prefer, you will have to take one more step before it can be used with **PyRadio**.

Open a terminal and type:

    ln -s /Applications/VLC.app/Contents/MacOS/VLC ~/.local/bin


**2\. MPV or MPlayer**

**MPV** and **MPlayer** can be installed using either [Homebrew](https://github.com/Homebrew/homebrew) or [MacPorts](https://www.macports.org/). Installation info can be found at the [end of this page](#installation-of-additional-package-managers).

After you have installed [Homebrew](https://github.com/Homebrew/homebrew) or [MacPorts](https://www.macports.org/), you can install the player of your choice.

***a)  MPV***

    brew install mpv

or

    sudo port install mpv

***b) MPlayer***

    brew install mplayer

or

    sudo port install MPlayer

## Get the installation script

Open a terminal and execute:

```
cd
curl -L \
    https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py \
    -o install.py
```

## Python3 installation

Execute:

    python3

If this is the first time python3 is executed you will be prompted to allow the installation of "*Apple's Command Line Developer Tools*". Accept the installation, wait for it to complete, and reboot.

When the system is up again, please check for updates (open **App Store** and click on **Updates**). Install any pending update and reboot.

Your system is ready now for **PyRadio** to be installed.


### Dependencies installation

Open a terminal and type:

```
python3 -m pip install requests rich pipx
python3 -m pipx ensurepath
```

Log out and log in again for the changes to take effect.

### PyRadio installation

Once you are logged in again, open a terminal and type:

```
cd
python3 install.py
```

Enjoy!

## Installation of Additional Package Managers

These instructions must be followed only in case you want to use **MPV** or **MPlayer** with **PyRadio**.

It goes without saying that it's enough to install only one of these package managers.

### Homebrew

To install [Homebrew](https://github.com/Homebrew/homebrew) open a **terminal** and type:

    /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

### MacPorts

[MacPorts](https://www.macports.org/) provide installation packages for each MacOS version, so just get to their [site](https://www.macports.org/install.php) and get the one suitable for you.
