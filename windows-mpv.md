# MPV Installation on Windows

**PyRadio**: Command line internet radio player.

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [MPV installation](#mpv-installation)

<!-- vim-markdown-toc -->

[[Back to Build Instructions]](windows.md) [[Back to README]](README.md)

## MPV installation

Go to [MPV's home](http://mpv.io) and open the [Installation](https://mpv.io/installation) page and click the [Windows builds by shinchiro (releases and git)](https://sourceforge.net/projects/mpv-player-windows/files) link to get to the files. Then you can choose to install either the git version ([64bit](https://sourceforge.net/projects/mpv-player-windows/files/64bit/) or [32bit](https://sourceforge.net/projects/mpv-player-windows/files/32bit/)), or the latest **stable** [release](https://sourceforge.net/projects/mpv-player-windows/files/release/) which also provides both 64 and 32 bit binaries.

**Note:** I am stating here all the links, although all one has to do is get to the last one and download the **MPV setup**. This is done so that in case any of the links change in the future, the way to go will be known, having [MPV's home page](https://mpv.io) as a starting point.

You will end up downloading a [7z archive](https://www.7-zip.org/), which contains a directory whose name is similar to **mpv-0.34.-x86_64.7z**.

Extract this archive to whatever place you like and **rename** it to **mpv**.

Here comes the tricky part...


Move the **mpv** directory to the following location (**PyRadio** will look for it there, when executed):

- **%APPDATA%\\pyradio** \
This is (or will be) "*PyRadio's configuration directory*". \
In case the "*pyradio*" directory does not exit, you just go ahead and create it.

In order to do that, open an **Explorer File Manager** window, and enter "**%APPDATA%**" at its location field and press ENTER.

If you are unsure on how to do that, please refer to the following image (you can ENTER **%APPDATA%** or any other Windows System Variable this way).

![Navigating to %APPDATA%](https://members.hellug.gr/sng/pyradio/appdata.jpg)

