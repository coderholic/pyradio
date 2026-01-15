# Packaging PyRadio

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Packaging status](#packaging-status)
* [Dependencies](#dependencies)
* [Files to change](#files-to-change)
    * [distro name (must do)](#distro-name-(must-do))
    * [XDG Base Directory Specification Compliance](#xdg-base-directory-specification-compliance)
    * [Desktop Notifications (optional)](#desktop-notifications-(optional))
        * [Desktop Notification Icons (optional)](#desktop-notification-icons-(optional))
    * [Desktop File location](#desktop-file-location)
    * [importlib_resources](#importlib_resources)
    * [pyradio/\_\_pycache\_\_](#pyradio/\_\_pycache\_\_)
* [Recordings Directory](#recordings-directory)
* [MKVToolNix cli installation](#mkvtoolnix-cli-installation)
* [Resource opener (Linux only)](#resource-opener-(linux-only))

<!-- vim-markdown-toc -->

[ [Back to main doc](index.md#packaging-pyradio)  ]

## Packaging status

The following data is provided by [Repology, the packaging hub](https://repology.org/).

<!-- [![Packaging status](https://repology.org/badge/vertical-allrepos/pyradio.svg)](https://repology.org/project/pyradio/versions) -->

<a href="https://repology.org/project/pyradio/versions">
    <img style="width: 35%" src="https://repology.org/badge/vertical-allrepos/pyradio.svg" alt="Packaging status">
</a>


## Dependencies

First of all, you have to decide on the player that's going to be used. Three players are supported:

1. mpv
2. plmayer
3. vlc

Make sure one of them is included in the dependencies.

Then you have to add the following python modules to the relevant section of your manifest (or whatever) file:

1. requests
2. dnspython
3. psutil
5. rich
5. netifaces
6. dateutil
7. charset-normalizer
8. importlib_resources (depending on python version)

## Files to change

You will have to modify a couple of files to tailor **PyRadio**' to your needs and liking.

### distro name (must do)

**PyRadio** is able to update and uninstall itself, when installed from source. This is something you do not want to be happening when your package is used; **PyRadio** should be updated and uninstalled using the distro package manager.

In order to accomplice that, you just have to change the **distro** configuration parameter in the **config** file. **PyRadio** will read this parameter and will disable updating and uninstalling, when set to anything other than "**None**". So, here's how you do that:

Once you are in the sources top level directory (typically "*pyradio*"), you execute the command:

```
sed -i 's/distro = None/distro = YOUR DISTRO NAME/' pyradio/config
```

Then you go on to produce the package as you would normally do.

For example, an **Arch Linux** packager would use this command:

```
sed -i 's/distro = None/distro = Arch Linux/' pyradio/config
```

The distro name you insert here will appear in **PyRadio**'s "*Configuration Window*". In addition to that it will appear in the log file, so that I know where the package came from while debugging.

Having said that, if you are not packaging for a specific distribution, please do use something meaningful (for example, using "*xxx*" will do the job, but provides no useful information).

### XDG Base Directory Specification Compliance

By default, all **PyRadio** configuration, operational and state files are stored under "*~/.config/pyradio*".

[XDG Base Directory Specification](https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html) proposes a different arrangement, though. More info (and examples) can also be found at Arch's [XDG Base Directory](https://wiki.archlinux.org/title/XDG_Base_Directory).

If you want to comply to this specification, just execute the following command from the sources top level directory (typically "*pyradio*"):

```
sed -i 's/xdg_compliant = False/xdg_compliant = True/' pyradio/config
```

### Desktop Notifications (optional)

If you want to enable [Desktop Notifications](index.md#desktop-notifications), do a

```
sed -i 's/enable_notifications = -1/enable_notifications = 0/' pyradio/config
```

to display titles whenever they are received, or

```
sed -i 's/enable_notifications = -1/enable_notifications = 60/' pyradio/config
```
to have notifications every 60 seconds, for example. You can use any value here, starting from 30 to 300 (meaning every 30 seconds up to 5 minutes), using a step of 30.

#### Desktop Notification Icons (optional)

**PyRadio** will download stations logos (icons) in the "*logos*" cache directory.

This directory will be deleted at program exit, by default.

If you want to keep the downloaded icons, do a

```
sed -i 's/remove_station_icons  = True/remove_station_icons   = False/' pyradio/config
```

### Desktop File location

If the Desktop File is not installed in */usr/share/applications* or */usr/local/share/applications*, it will have to be passed as a parameter to the script that will handle it, like so:

```
sed -i "s,' -t ',' -d /path/to/desktop_file' + &," pyradio/main.py
```

### importlib_resources

Depending on the Python version used by your distro, you may also have to add **importlib_resources** to your dependencies.

Experience says Python 3.8 and 3.10 will probably need this package installed.

### pyradio/\_\_pycache\_\_

This is a directory that is needed for some build systems to succesfully build **PyRadio**.

Depending on the build system:

1. It may be needed (in the case of Gentoo, MacOS and Windows). \
In this case, you have nothing to do. \
\
Please keep in mind that there is a REDME file in the directory; in case this file causes any problems, just remove the file before the build command.

2. It may not be needed (for example on Arch Linux). \
In this case, just delete it before the build command.

## Recordings Directory

Parameter **recording_dir** in the config will point to the directory to save recorded files.

It may seem like a good idea to change it to something meaningful but there is a catch.

**PyRadio 0.9.3** (and newer) will nornaly use the *default* location, which is *~/pyradio-recordings*. Furthermore, it will move the pre-0.9.3 default recordings dir, i.e. *~/.config/pyradio/recordings* and titles log(from *~/.config/pyradio*, to this new default location.

If you, the packager, provide a different default **recording_dir** in the package config file, your users will probably end up in the following situation:

1. Pro existing recordings and titles logs will end up in *~/pyradio-recordings*.

2. New recordings and titles logs will be saved in the new default location you have provided.

This means that your users will eventaually have to **manually** move the files from *~/pyradio-recordings* to the new location.

If this is acceptable for you, and you have a way to inform your users about it, go no and

```
sed -i 's|recording_dir = default|recording_dir = ~/whatever|' config
```

In any other case, I would suggest you leave this parameter as is and let the user select customize their setup.

## MKVToolNix cli installation

Another thing to consider is whether you should mark **MKVToolNix** command line utilities as a dependency for **PyRadio**.

I would suggest to do so, in order to provide your users the best experience possible. If unsure, please refer to section [Chapters](recording.md#chapters) in the relevant document.

In case you decide to do so, please make sure you mark as a dependency the **command line utilities**, not the GUI program, if that's on a different package on your distro. For examle, Arch Linux provides both a *mkvtoolnix-cli* and a *mkvtoolnix-gui* package; the first one should be used. Same thing with Debian Linux; it provides both a *mkvtoolnix* and a *mkvtoolnix-gui* package; in which case you'd use the later.

## Resource opener (Linux only)

A [resource opener](https://wiki.archlinux.org/title/default_applications#Resource_openers) is a utility to open directories, html pages, etc.

**PyRadio** running on Linux will look for *xdg-open*, *gio*, *mimeopen*, *mimeo* or *handlr*, in that order of detection.

If none of the above if found, the requested file will simply not open.

Most Linux distros will probably have *xdg-open* (from *xdg-utils* package) installed or available (or any of the ones in the list above), so no action will be nesesary.

In case a different *resource opener* is to be used, one can declare it like so:

```
sed -i 's/resource_opener = auto/resource_opener = MY_RESOURCE_OPENER/' config
```

This will instruct **PyRadio** to use the file **MY_RESOURCE_OPENER** as a *resource opener*.

**MY_RESOURCE_OPENER** can be just the name of the file (if it is in the *PATH*), or an absolute path to a file, it it's not.
