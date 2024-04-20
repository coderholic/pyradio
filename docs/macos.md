# PyRadio macOS installation

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Preface](#preface)
* [Preparation](#preparation)
    * [Homebrew installation](#homebrew-installation)
    * [Python Installation](#python-installation)
    * [Media player installation](#media-player-installation)
    * [Get the installation script](#get-the-installation-script)
* [PyRadio installation](#pyradio-installation)
    * [Dependencies installation](#dependencies-installation)
    * [Performing the installation](#performing-the-installation)

<!-- vim-markdown-toc -->

[ [Return to PyRadio Build Instructions](build.md#installation-guides) ]

## Preface

**PyRadio** on macOS can only be installed on **Python 3** through **pipx**.

Furtermore, the pipx installation will be a fully isolated one, which means that all dependencies will be installed along with **PyRadio** in a virtual environment.

That is a one-way street to follow since the combination of macOS versions, python installation methods and player installation methods is too complex to provide a complete installation guide for **PyRadio**.

[pipx](https://pypa.github.io/pipx/) provides a standardization of the whole procedure which leads to an acceptable (enjoyable even) user experience.

## Preparation

These are the steps required before actually installing **PyRadio**.

**Note:** The following installation instructions were performed on a freshly installed **Ventura** (macOS 13) system. Things may be a bit different for older macOs versions, but it will be the same for **Sonoma** (macOS 14).

### Homebrew installation

This is the method [Homebrew](https://brew.sh) recommends, so we just go with it.

Open a terminal and execute:

<!-- START OF BREW LINK-->
```
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```
<!-- END OF BREW LINK-->

### Python Installation

Your system comes with a pre-installed version of Python, but it would be better to install the one provided by **Homebrew**.

    brew install python3

This will also install "*Apple's Command Line Developer Tools*" (if they are not already installed).


Then, adjust your **PATH**, so that the newly installed Python will be the default one.

```
cat << END >> ~/.zshrc
export PATH=/usr/local/bin:"$PATH"
END
source ~/.zshrc
```

### Media player installation

The next step is to install a supported media player (**MPV**, **MPLayer** or **VLC**). You are free to install any one of them or even more than one. The steps to follow from now on depends entirely on you, meaning depends entirely on the media player(s) you want to install and use with **PyRadio**.

**1\. VLC**

**VLC** provides a macOS package, so you can just go get it from [its site](https://www.videolan.org/vlc/). This is the cleaner way and I would recommend it.

If this is the player you prefer, you will have to take one more step before it can be used with **PyRadio**.

Open a terminal and type:

    ln -s /Applications/VLC.app/Contents/MacOS/VLC ~/.local/bin/cvlc


**2\. MPV or MPlayer**

**MPV** and **MPlayer** can be installed using [Homebrew](https://brew.sh).

***a)  MPV***

    brew install mpv

***b) MPlayer***

    brew install mplayer

### Get the installation script

Open a terminal and execute:

```
cd
curl -L \
    https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py \
    -o install.py
```

## PyRadio installation

Your system is ready now for **PyRadio** to be installed.

### Dependencies installation

Open a terminal and type:

    python3 -m pip install requests rich pipx --break-system-packages

Finally, type:

    python3 -m pipx ensurepath
    source ~/.zshrc

### Performing the installation

Execute the following command:

    python3 install.py

Enjoy!

