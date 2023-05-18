# PyRadio pip installation on Linux

**PyRadio**: Command line internet radio player.

## Table of contents
<!-- vim-markdown-toc Marked -->

* [Preface](#preface)
* [Take care of your PATH](#take-care-of-your-path)
* [Install a media player](#install-a-media-player)
* [Get the installation script](#get-the-installation-script)
* [Debian and derivatives](#debian-and-derivatives)
* [Fedora and derivatives](#fedora-and-derivatives)
* [openSUSE and derivatives](#opensuse-and-derivatives)

<!-- vim-markdown-toc -->

[[Return to PyRadio Build Instructions]](build.md)

## Preface

This document will help you install **PyRadio** within your **.local** directory, using `pip`.

In order to install **PyRadio** to your system you will:

1. Take care of your PATH
2. Install a media player
1. Download the installation script
2. Install the basic python system and **PyRadio** dependencies
3. Perform the installation


## Take care of your PATH

**PyRadio** will be installed in the **~/.local/bin** directory.

Please make sure this directory is in your PATH shell variable. The way to do this depends on the default shell you are using; please refer to its documentation on how to edit your PATH.

## Install a media player

**PyRadio** relies on the existence of at least one of the following media players: **mpv**, **mplayer** or **vlc**.

Please install at least one of them beforehand:

```
# on Debian
sudo apt-get install [ mpv / mplayer / vlc ]

# on Fedora
sudo dnf install [ mpv / mplayer / vlc ]

# on openSUSE
sudo zypper install [ mpv / mplayer / vlc ]
```

## Get the installation script

Open a terminal and execute:

```
cd
wget https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py
```

or using curl:
```
cd
curl -L \
    https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py \
    -o install.py
```

If you are going to use **Python 2**, please execute:

```
sed -i.orig 's/from rich import print/pass/' install.py
```

This will fix the instllation script for **Python 2**; the original script will be renamed to *install.py.orig*.

Please follow the instructions that match/suit your distribution.

## Debian and derivatives

**Note:** The following instructions were tested on a freshly installed **Debian Testing**.

Install the requirements for the installation script:

```
sudo apt-get install \
    python3-full \
    python3-pip \
    python3-rich \
    python3-requests \
    python3-dnspython \
    python3-psutil \
    python3-netifaces \
    python3-dateutil
cd
python3 install.py
```

## Fedora and derivatives

**Note:** The following instructions were tested on a freshly installed **Fedora 38 Workstation**.

Execute:
```
sudo dnf install \
    python3-pip \
    python3-wheel \
    python3-rich \
    python3-requests \
    python3-netifaces \
    python3-psutil \
    python3-dns \
    python3-dateutil
cd
python install.py
```

## openSUSE and derivatives

**Note:** The following instructions were tested on a freshly installed **openSUSE Tumbleweed 20230427**.

Execute:

```
sudo zypper install \
    python310-requests \
    python310-rich \
    python3-psutil \
    python3-dnspython \
    python3-dateutil \
    python3-netifaces
cd
python3 install.py
```

