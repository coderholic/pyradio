# PyRadio Packagers' Info

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Packaging PyRadio](#packaging-pyradio)
    * [Distro Specific Files](#distro-specific-files)
    * [MKVToolNix cli installation](#mkvtoolnix-cli-installation)

<!-- vim-markdown-toc -->

[ [Back to main doc](index.md#packaging-pyradio)  ]

## Packaging PyRadio

If you are a packager and would like to produce a package for your distribution please do follow this mini guide.

First of all, make sure you declare the pacakges's requirements to the relevant section of your manifest (or whatever) file. These are:

1. setuptools
2. wheel
3. requests
4. dnspython
5. psutil
6. rich
7. netifaces
8. dateutils

After that, you will have to modify some files, because **PyRadio** is able to update and uninstall itself, when installed from source. This is something you do not want to be happening when your package is used; **PyRadio** should be updated and uninstalled using the distro package manager.

In order to accomplice that, you just have to change the **distro** configuration parameter in the **config** file. **PyRadio** will read this parameter and will disable updating and uninstalling, when set to anything other than "**None**". So, here's how you do that:

Once you are in the sources top level directory (typically "*pyradio*"), you execute the command:

    sed -i 's/distro = None/distro = YOUR DISTRO NAME/' pyradio/config

Then you go on to produce the package as you would normally do.

For example, an **Arch Linux** packager would use this command:

    sed -i 's/distro = None/distro = Arch Linux/' pyradio/config

The distro name you insert here will appear in **PyRadio**'s "*Configuration Window*". In addition to that it will appear in the log file, so that I know where the package came from while debugging.

Having said that, if you are not packaging for a specific distribution, please do use something meaningful (for example, using "*xxx*" will do the job, but provides no useful information).

Then, if you want to enable **Desktop Notifications**, do a

    sed -i 's/enable_notifications = -1/enable_notifications = 0/' pyradio/config

or

    sed -i 's/enable_notifications = -1/enable_notifications = 60/' pyradio/config

to have notifications every 60 seconds, for example. You can use any value here, starting from 30 to 300 (meaning every 30 seconds up to 5 minutes), using a step of 30.

### Distro Specific Files

**1. Desktop File**

If the Desktop File is not installed in */usr/share/applications* or */usr/local/share/applications*, it will have to be passed as a parameter to the script that will handle it, like so:

```
sed -i "s,' -t ',' -d /path/to/desktop_file' + &," pyradio/main.py
```

**2. Package Icon**

As of **v. 0.9.1**, **PyRadio** includes the icon in its distribution files, so no further action is necessary.

### MKVToolNix cli installation

Another thing to consider is whether you should mark **MKVToolNix** command line utilities as a dependency for **PyRadio**.

I would suggest to do so, in order to provide your users the best experience possible. If unsure, please refer to section [Chapters](recording.md#chapters) in the relevant document.

In case you decide to do so, please make sure you mark as a dependency the **command line utilities**, not the GUI program, if that's on a different package on your distro. For examle, Arch Linux provides both a *mkvtoolnix-cli* and a *mkvtoolnix-gui* package; the first one should be used. Same thing with Debian Linux; it provides a *mkvtoolnix* and a *mkvtoolnix-gui* package.


