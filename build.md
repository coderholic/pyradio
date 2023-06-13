# PyRadio Build Instructions

**PyRadio**: Command line internet radio player.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Current state of the project](#current-state-of-the-project)
    * [What does it all mean and why should you care](#what-does-it-all-mean-and-why-should-you-care)
    * [When do I need to install pipx?](#when-do-i-need-to-install-pipx?)
        * [More info](#more-info)
    * [Notice for Python 2 users](#notice-for-python-2-users)
    * [Installation on the BSDs](#installation-on-the-bsds)
    * [Rasberry Pi installation](#rasberry-pi-installation)
* [Installation guides](#installation-guides)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md)

## Current state of the project

Starting with version **0.9.2.6**, **PyRadio** has changed (yet again) its installation method, forced by the emergance of Ubuntu 23.04.

After abandoning invoking *setup.py* directly, now it's time to start using **virtual environments** (through a program called `pipx`) along with the pure `pip` method.

This is not a **PyRadio** thing; distributions are starting to embrace this behaviour.

The rationale behind this move it this: since `pip` can be used to install packages **system wide**, it can easily "destroy" the whole python installation. This would be the equivalent of forcing the installation of an Ubuntu package in a Debian system or a Debian 11 package on a Debian 8 system.

At the same time, python scripts and packages are already used by distributions to provide system tools and breaking a system's python installation may lead to breaking the whole system.

The solution is forcing the use of **virtual environments** for any python script or program or package that is **not provided** by the distribution itself, effectively isolating the program's installation from the rest of the system. Any program, package or module installed within the **virtual environment** exists and lives within that environment only, it does not interfere with the distribution's Python installation and cannot "destroy" it.

Python **virtual environments** have existed for a long time, but their use was not always that straight forward. Fortunately, a program called [pipx](https://pypa.github.io/pipx/) will help with the installation and execution of python programs from within a virtual environment while taking care of the overhead required.

### What does it all mean and why should you care

Moving to the **pipx** means:

1. **PyRadio** will be installed by default through `pipx` on Linux, if pipx is already installed.

2. If a Linux distribution does not provide a pipx package, you can still use the `pip` installation method.

3. Python 2 is still supported on a Linux system, in which case a `pip` installation will be performed.

4. **PyRadio** on **Windows** will still use the `pip` installation method. *Python 2* is not supported anymore.

5. **PyRadio** will only be installed using `pipx` on **Python 3** on **MacOS**. *Python 2* is not supported anymore.


### When do I need to install pipx?

If you already have **PyRadio** installed, a subsequent update notification may lead to an installation failure. The same goes if you try to install **PyRadio** on a freshly installed Ubuntu 23.04 (or Debian or any other distribution that ships its python "externally managed" in the future).

This is what you get on Ubuntu 23.04 (and probably Debian and any distribution based on them):

```
error: externally-managed-environment

× This environment is externally managed
╰─> To install Python packages system-wide, try apt install
    python3-xyz, where xyz is the package you are trying to
    install.

    If you wish to install a non-Debian-packaged Python package,
    create a virtual environment using python3 -m venv path/to/venv.
    Then use path/to/venv/bin/python and path/to/venv/bin/pip. Make
    sure you have python3-full installed.

    If you wish to install a non-Debian packaged Python application,
    it may be easiest to use pipx install xyz, which will manage a
    virtual environment for you. Make sure you have pipx installed.

    See /usr/share/doc/python3.11/README.venv [1] for more information.

--
[1] https://sources.debian.org/src/python3.11/3.11.2-6/debian/README.venv
```

If you get that message, or a similar one, it is time to install `pipx`.

#### More info

- [Externally Managed Environments @ PyPA](https://packaging.python.org/en/latest/specifications/externally-managed-environments/)

- [PEP 668 – Marking Python base environments as “externally managed”](https://peps.python.org/pep-0668/)


### Notice for Python 2 users

If you are still using **Python 2** in a linux system, plase make sure "**pip**" is installed. Execute the following command to verify its existance:

```
python[2] -m pip list
```

If you get a response, you are good to go. Otherwise, use your distro package manager to install it.

If your distro does not provide it (some do not anymore), use the following commands to get it:

```
    curl https://bootstrap.pypa.io/pip/2.7/get-pip.py \
        --output get-pip.py
    sudo python[2] get-pip.py
```

or

```
    wget https://bootstrap.pypa.io/pip/2.7/get-pip.py
    sudo python[2] get-pip.py
```

When you are done, proceed to  "[pip installation](linux.md) (the old way)", adapting the commands to python2.

### Installation on the BSDs

If you are on any of the BSDs, please do install **bash** beforehand and try to follow the [pip installation guide](linux-pip.md).

Please be aware that **PyRadio** is provided as a **port** on [FreeBSB](https://www.freshports.org/audio/py-pyradio/).


### Rasberry Pi installation

If installing on a Rasberry Pi, there are a couple of things you should be aware of:

1. The default player will be **MPlayer**
3. If you still want to use **MPV**, please make sure you increase the *Connection timeout* value to at least 20 (sometimes even 30 for some machines). Even then, your machine may eventually crash, if it's on the lower end of things and **PyRadio** is left running for hours.

## Installation guides

Please follow the installation guides for your OS.

1. Linux
    - [pip installation](linux.md) (the old way) \
Not valid for **Debian** and **Ubuntu 23.04**
    - [pipx installation](linux-pipx.md) (the new way) \
Valid for **Debian** and **Ubuntu 23.04**
2. MacOS \
Follow the instructions on [this page](macos.md).
3. Windows \
Follow the instructions on [this page](windows.md).


