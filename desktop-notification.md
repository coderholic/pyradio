# PyRadio Desktop Notification

**PyRadio**: Command line internet radio player.

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Introduction](#introduction)
    * [Configuration](#configuration)
    * [Notification Icon](#notification-icon)
* [On Linux](#on-linux)
* [On MacOS](#on-macos)
* [On Windows](#on-windows)
    * [Configuring notifications](#configuring-notifications)
* [On Windows 7](#on-windows-7)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md)

## Introduction

**PyRadio** can provide Desktop Notifications when a notification daemon is already present (on Linux and BSD), or through **Windows Notification Service** (**WNS**).

The behavior and presentation of notifications greatly depends on the daemon/service and command line utility used to trigger a notification.

If enabled, **PyRadio** will display:

1. The playlist name, when playback starts.
2. Song info (as provided by the radio station).
3. Connection failure messages.
4. Player crash messages.

Desktop Notifications are disabled by default.


### Configuration

Desktop Notifications are disabled by default. To enable them, go to **PyRadio** config window and customize the "*Enable notifications*" option.

Available values are:
```
   -1: disabled (deault)
    0: enabled (no repetition)
    x: enabled and repeat every x seconds
```

**PyRadio** supports notifications repetition, so that even when used with `quake` or `yakuake` and the like, you still have some info on what's going on with it.

Notifications can be set to repeat every "*x*" seconds, with "*x*" ranging from 30 to 300 (30 seconds to 5 minutes), in 30 seconds steps.

### Notification Icon

The icon that is displayed in the notification message is by default **PyRadio**'s icon.

**PyRadio** will search for this icon, named *pyradio.png*  (or *pyradio.ico* on Windows) in the following locations:

1. In the *configuration directory*, under **data** (or **Help** folder on Windows).
2. In the distribution directory (under the **icons** folder).

As a consequence, one could replace the icon found in the *configuration directory* (under **data** or **Help**) with a custom icon, preserving the icon name as appropriate (*pyradio.png*, or *pyradio.ico* on Windows).

If the station defines a "*Station Icon URL*" (either on a local playlist or an online service; **Radio Browser** includes an icon for many stations, for example), **PyRadio** will used this one instead, provided that it is of *JPG* or *PNG* format. This does not apply to Windows; an *ICO* file is used instead for **Desktop Notifications**.

## On Linux

![Linux notification](https://members.hellug.gr/sng/pyradio/pyradio-notif.jpg)

On Linux (and the BSDs), **PyRadio** uses the *notification daemon* that's already present and whatever command line helper program it provides to send notifications to the daemon.

By default, **PyRadio** uses the following command to issue notifications:

```
notify-send -i ICON TITLE MSG
```

This command will:

- display the title "**TITLE**" and message "**MSG**".
- display an icon (**-i**).

The "**ICON**", "**TITLE**" and "**MSG**" tokens are just placeholders; **PyRadio** will replace them with real data when issuing the notification.

If that does not work for you, or you want to customize the output, this is what to do:

1. put together a valid command that can be executed on a terminal and produce the desired notification.
2. create a file called **notification** in **PyRadio** configuration directory.
3. write the above command in that file and put each field in a different line.

**Example:**

I have this custom command:

```
notify-send -i ICON -t 6000 TITLE MSG
```

The file I wrote is **~/.config/pyradio/notification**:

```
notify-send
-i
ICON
-t
6000
TITLE
MSG
```

## On MacOS

![MacOS notification](https://members.hellug.gr/sng/pyradio/mac-notif.jpg)

MacOS Maverick (and later) provides a scripting service to issue notifications from the command line.

The command **PyRadio** uses is:

```
osascript -e 'display notification "MSG" with title "TITLE"'

```

If that does not work for you, or you want to display the icon as well, just install `terminal-notifier`:

```
brew install terminal-notifier
```
After it is installed, write the following in **~/.config/pyradio/notification**:

```
terminal-notifier
-message
MSG
-title
TITLE
-appIcon
ICON
```

and you are done!

## On Windows

![Windows notification](https://members.hellug.gr/sng/pyradio/win-notif.jpg)

As already stated **PyRadio** will display notifications throught **Windows Notification Service** (**WNS**).

All that you have to do is enable the notifications in the config window.

### Configuring notifications

Window will display the program the notification comes from, which in this case is **Python**, not **PyRadio**.

By default, a sound is played when a notification is displayed, which is very annoying when using **PyRadio** to listen to music and such.

To change the setting, just hover your mouse over a notification and click on the three dots displayed next to the "*X*".

Then you will get the menu that's shown in the next image.

![Windows notification edit](https://members.hellug.gr/sng/pyradio/win-notif-edit.jpg)

Click on "*Go to notification settings*" to open the window that's shown below.

**Note:** Please be careful not to click on "*Turn off all notifications for Python"; if you do, it won't be easy to get notifications back, especially on Window 10 and 11.

![Windows notification properties](https://members.hellug.gr/sng/pyradio/win-python-props.jpg)

Please replicate the settings you see in the image above, and enjoy!

## On Windows 7

![Windows 7 notification](https://members.hellug.gr/sng/pyradio/win7-notif.jpg)

If you are on **Windows 7**, you will have a differently looking notification (shown above).

If you click on the little tool-like "icon" next to the "X", you get to the "**Notification Area Icons**", the notifications configuration window. A couple of options are available, and again, I do not know how easy it will be to enable the notification if disabled once.

![Windows 7 Nontification Icons](https://members.hellug.gr/sng/pyradio/win7-icons.jpg)

Again, Window considers that the program sending the notifications is **Python**, not **PyRadio**, so that's what you will be changing.

