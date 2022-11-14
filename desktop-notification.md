# PyRadio Desktop Notification

Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Introduction](#introduction)
* [On Linux](#on-linux)
    * [Packagers info](#packagers-info)
* [On MacOS](#on-macos)
* [On Windows](#on-windows)
    * [Configuring notifications](#configuring-notifications)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md)

## Introduction

**PyRadio** can provide Desktop Notifications when a notification daemon is already present (on Linux and BSD), or throught **Windows Notification Service** (**WNS**).

If enabled, **PyRadio** will display:

1. Song info (as provided by the radio station) \
That means that if the radio station does not provide any info, no notification will be issued.
2. Connection failure messages.
3. Player crash messages.

**Note:** If Desktop Notification is enabled by default (in the case of a distro package) users can disable it by creating an empty **~/.config/pyradio/notification** file (Linux only).

## On Linux

On Linux (and the BSDs), **PyRadio** uses the *notification daemon* that's already present, using whatever command it provides to send notifications to the daemon.

![Linux notification](https://members.hellug.gr/sng/pyradio/pyradio-notif.jpg)

On my linux box, this is done using the **notify-send** command (as it would be with most distros).

This is its help screen.

```
# notify-send --help

Usage:
  notify-send [OPTION…] <SUMMARY> [BODY] - create a notification

Help Options:
  -?, --help                        Show help options

Application Options:
  -u, --urgency=LEVEL               Specifies the urgency level (low, normal, critical).
  -t, --expire-time=TIME            Specifies the timeout in milliseconds at which to expire the notification.
  -a, --app-name=APP_NAME           Specifies the app name for the icon
  -i, --icon=ICON                   Specifies an icon filename or stock icon to display.
  -c, --category=TYPE[,TYPE...]     Specifies the notification category.
  -e, --transient                   Create a transient notification
  -h, --hint=TYPE:NAME:VALUE        Specifies basic extra data to pass. Valid types are boolean, int, double, string, byte and variant.
  -p, --print-id                    Print the notification ID.
  -r, --replace-id=REPLACE_ID       The ID of the notification to replace.
  -w, --wait                        Wait for the notification to be closed before exiting.
  -A, --action=[NAME=]Text...       Specifies the actions to display to the user. Implies --wait to wait for user input. May be set multiple times. The name of the action is output to stdout. If NAME is not specified, the numerical index of the option is used (starting with 0).
  -v, --version                     Version of the package.
```

In order to make **PyRadio** use it, we wil use this help screen to create a valid command, for example:

```
notify-send -i ~/.config/pyradio/pyradio.png -t 6000 TITLE MSG
```

This command will:

- display an icon (-i) \
The icon is already in **PyRadio** config folder; just use the full path to it.
- display the notification for 6 seconds (-t)

The **TITLE** and **MSG** tokens are just placeholders; **PyRadio** will replace them with real data when issuing the notification.

When the command is ready, we just write it to **~/.config/pyradio/notification**, like so:

```
echo "notify-send -i ~/.config/pyradio/pyradio.png -t 6000 TITLE MSG" > ~/.config/pyradio/notification
```

Next time **PyRadio** is executed, it will read the above file, and start issuing notifications.

That was just an example to demonstrate the procedure one would follow to enable **PyRadio** Desktop Notifications.

Users can populate the **~/.config/pyradio/notification** files as needed and in accordance with their notification daemon / command.

### Packagers info

Since Desktop Notifications are not enabled by default, packages will have to populate the **notification** file manually (which is originally an empty file in the **pyradio** directory), using the procedure described above.

**Note:** The icon will probable by in **/usr/share/icons**.

**Note:** Individual users can disable the Desktop Notifications enabled by the installed packaged, by creating an empty **~/.config/pyradio/notification** file.

## On MacOS

MacOS Maverick (and later) provides a standardized way to display notifications, so it's much more easier to enable them for **PyRadio**.

Just create a non-empty **~/.config/pyradio/notification** file:

```
echo YES > ~/.config/pyradio/notification
```

To disable notifications, just make it empty:

```
echo > ~/.config/pyradio/notification
```

## On Windows

As already stated **PyRadio** will display notifications throught **Windows Notification Service** (**WNS**).

![Windows notification](https://members.hellug.gr/sng/pyradio/win-notif.jpg)

All that you have to do in install one package, and you are done.

```
python -m pip install win10toast
```


If you wanto to disable Desktop Notification, just uninstall the package.

```
python -m pip uninstall win10toast
```

That's all.

### Configuring notifications

Window will display the program the notification comes from, which in this case is **Python**, not .

By default, a sound is played when a notification is displayed, which is very annoying when using **PyRadio** to listen to music and such.

To change the setting, just hover your mouse over a notification and click on the three dots displayed next to the "*X*".

Then you will get the menu that's shown in the next image.

![Windows notification edit](https://members.hellug.gr/sng/pyradio/win-notif-edit.jpg)

Click on "*Go to notification settings*" to open the window that's shown below.

**Note:** Please be careful not to click on "*Turn off all notifications for Python"; if you do, it won't be easy to get notifications back, especially on Window 10 and 11.

![Windows notification properties](https://members.hellug.gr/sng/pyradio/win-python-props.jpg)

Please replicate the settings you see in the image above, and enjoy!
