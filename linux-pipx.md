# PyRadio pipx installation on Linux

**PyRadio**: Command line internet radio player.

## Table of contents
<!-- vim-markdown-toc Marked -->

* [Preface](#preface)
* [Install a media player](#install-a-media-player)
* [Get the installation script](#get-the-installation-script)
* [Debian and derivatives](#debian-and-derivatives)
    * [Fully isolated installation - Debian](#fully-isolated-installation---debian)
    * [System dependent installation - Debian](#system-dependent-installation---debian)
* [Fedora and derivatives](#fedora-and-derivatives)
    * [Fully isolated installation - fedora](#fully-isolated-installation---fedora)
    * [System dependent installation - fedora](#system-dependent-installation---fedora)
* [openSUSE and derivatives](#opensuse-and-derivatives)
    * [Fully isolated installation - openSUSE](#fully-isolated-installation---opensuse)
    * [System dependent installation - openSUSE](#system-dependent-installation---opensuse)
* [PyRadio Cache](#pyradio-cache)

<!-- vim-markdown-toc -->

[[Return to PyRadio Build Instructions]](build.md)


## Preface

This document will help you install **PyRadio** within a **virtual environment** using [pipx](https://pypa.github.io/pipx/).

In order to install **PyRadio** to your system you will:

1. Install a media player
2. Download the installation script
3. Install the basic python system and **PyRadio** installation dependencies
4. Choose the type of **PyRadio** installation
5. Perform the installation

In order to decide which type of installation to perform, here are a couple of things you have to consider.

There are two installation types you can use for **PyRadio**:

1. **Fully isolated installation** \
This type of installation will install all **PyRadio** dependencies inside a virtual environment. \
\
The advantage is that the system's python installation is not cluttered with the package's dependencies. \
\
The disadvantage is that installing the dependencies in a virtual environment may fail.

2. **System dependent installation** \
This type of installation requires that all **PyRadio** dependencies are installed outside the virtual environment used by **PyRadio**. All dependencies must be provided by the distribution (i.e. exist in the distribution repositories).

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

or using `curl`:
```
cd
curl -L \
    https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py \
    -o install.py
```

Please follow the instructions that match/suit your distribution.

## Debian and derivatives

**Note:** The following instructions were tested on a freshly installed **Debian Testing**.

Install the requirements for the installation script:

```
sudo apt-get install \
    python3-full \
    python3-pip \
    python3-rich \
    python3-requests
```

Then install `pipx`:

```
sudo apt-get install pipx
```

If that fails, execute:

```
python3 -m pip install pipx
```

Finally, execute:

```
python3 -m pipx ensurepath
```

and exit the terminal.


### Fully isolated installation - Debian

Open a terminal and execute:
```
cd
python3 install.py -i
```

### System dependent installation - Debian

Install dependencies:
```
sudo apt-get install \
    python3-dnspython \
    python3-psutil \
    python3-netifaces \
    python3-dateutil
```

Install **PyRadio**:

```
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
    pipx
```

And
```
python3 -m pipx ensurepath
```
and exit the terminal.

### Fully isolated installation - fedora

Open a terminal and execute:
```
sudo dnf install gcc python3-devel
```

And finally:

```
cd
python install.py -i
```

### System dependent installation - fedora

Open a terminal and execute:
```
sudo dnf install \
    python3-netifaces \
    python3-psutil \
    python3-dns \
    python3-dateutil
```

Install **PyRadio**:
```
cd
python install.py
```

## openSUSE and derivatives

**Note:** The following instructions were tested on a freshly installed **openSUSE Tumbleweed 20230427**.

Execute:

```
sudo zypper install \
    python310-requests \
    python310-rich
# install pipx through pip to get the latest version (1.1.0+)
# at the time of writing this, a very old pipx version (0.14.0.0)
# was available on the openSUSE Tumbleweed repositories
python3 -m pip install --user pipx
python3 -m pipx ensurepath
```

and close the terminal.

### Fully isolated installation - openSUSE

Open a terminal and execute:

```
sudo zypper install \
    gcc \
    python310-dev
```

Install **PyRadio**:

```
cd
python3 install.py -i
```

### System dependent installation - openSUSE

Open a terminal and install **PyRadio** dependencies:

```
sudo zypper install \
    python3-psutil \
    python3-dnspython \
    python3-dateutil \
    python3-netifaces
```

Finally, install **PyRadio**:

```
cd
python3 install.py
```

## PyRadio Cache

Using **pipx** (a third party package) to deploy **PyRadio** on a system, may cause problems by itself.

**pipx** is able to correct some of these issues (according to its documentation), by executing:

```
pipx list
```

Furthermore, issues can also be resolved by reinstalling a package:

```
pipx reinstall pyradio
```

or even all pipx installed packages:

```
pipx reinstall-all
```

For these last commands to work, **PyRadio** source code must be available and present at the location it receded when the original installation took place.

**PyRadio** will keep a **cache** of ZIP files and a folder called **pyradio-source** in its data folder; all files will be kept in a folder called **.cache** (**_cache** on Windows).

Normally, just one ZIP file has to be present in the **cache**; the ZIP with the latest **PyRadio** version code. If more ZIP files are present in the cache, they can safely be deleted.

To see the contents of the cache (provided you have downloaded [the latest install.py](#get-the-installation-script)), execute:
```
python install.py -sc
```

To open the cache folder, execute:

```
python install.py -oc
```


To clear the cache (delete all ZIP files but the latest), execute:
```
python install.py -cc
```

If for some reason the cache has been lost, or got corrupted, you can just:

```
python install.py -oc
```

Delete all file and then:

```
python install.py -gc
```

This will download the latest stable ZIP file and unzip it into the **pyradio-source** folder.

And of course, if you have a working **PyRadio** installation, you can execute:

```
pyradio -sc
pyradio -oc
pyradio -cc
pyradio -gc
```
