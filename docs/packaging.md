# Packaging PyRadio

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Dependencies](#dependencies)
* [Files to change](#files-to-change)
    * [distro name (must do)](#distro-name-(must-do))
    * [Desktop Notifications (optional)](#desktop-notifications-(optional))
    * [Desktop File location](#desktop-file-location)
    * [pyradio/\_\_pycache\_\_](#pyradio/\_\_pycache\_\_)
* [MKVToolNix cli installation](#mkvtoolnix-cli-installation)

<!-- vim-markdown-toc -->

[ [Back to main doc](index.md#packaging-pyradio)  ]

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


## Files to change

You will have to modify a couple of files to tailor **PyRadio**' to your needs and liking.

### distro name (must do)

**PyRadio** is able to update and uninstall itself, when installed from source. This is something you do not want to be happening when your package is used; **PyRadio** should be updated and uninstalled using the distro package manager.

In order to accomplice that, you just have to change the **distro** configuration parameter in the **config** file. **PyRadio** will read this parameter and will disable updating and uninstalling, when set to anything other than "**None**". So, here's how you do that:

Once you are in the sources top level directory (typically "*pyradio*"), you execute the command:

    sed -i 's/distro = None/distro = YOUR DISTRO NAME/' pyradio/config

Then you go on to produce the package as you would normally do.

For example, an **Arch Linux** packager would use this command:

    sed -i 's/distro = None/distro = Arch Linux/' pyradio/config

The distro name you insert here will appear in **PyRadio**'s "*Configuration Window*". In addition to that it will appear in the log file, so that I know where the package came from while debugging.

Having said that, if you are not packaging for a specific distribution, please do use something meaningful (for example, using "*xxx*" will do the job, but provides no useful information).

### Desktop Notifications (optional)

If you want to enable [Desktop Notifications](index.md#desktop-notifications), do a

    sed -i 's/enable_notifications = -1/enable_notifications = 0/' pyradio/config

to display titles whenever they are received, or

    sed -i 's/enable_notifications = -1/enable_notifications = 60/' pyradio/config

to have notifications every 60 seconds, for example. You can use any value here, starting from 30 to 300 (meaning every 30 seconds up to 5 minutes), using a step of 30.

### Desktop File location

If the Desktop File is not installed in */usr/share/applications* or */usr/local/share/applications*, it will have to be passed as a parameter to the script that will handle it, like so:

```
sed -i "s,' -t ',' -d /path/to/desktop_file' + &," pyradio/main.py
```

### pyradio/\_\_pycache\_\_

This is a directory that is needed for some build systems to succesfully build **PyRadio**.

Depending on the build system:

1. It may be needed (in the case of Gentoo, MacOS and Windows). \
In this case, you have nothing to do. \
\
Please keep in mind that there is a REDME file in the directory; in case this file causes any problems, just remove the file before the build command.

2. It may not be needed (for example on Arch Linux). \
In this case, just delete it before the build command.

## MKVToolNix cli installation

Another thing to consider is whether you should mark **MKVToolNix** command line utilities as a dependency for **PyRadio**.

I would suggest to do so, in order to provide your users the best experience possible. If unsure, please refer to section [Chapters](recording.md#chapters) in the relevant document.

In case you decide to do so, please make sure you mark as a dependency the **command line utilities**, not the GUI program, if that's on a different package on your distro. For examle, Arch Linux provides both a *mkvtoolnix-cli* and a *mkvtoolnix-gui* package; the first one should be used. Same thing with Debian Linux; it provides both a *mkvtoolnix* and a *mkvtoolnix-gui* package; in which case you'd use the later.


