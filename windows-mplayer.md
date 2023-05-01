# MPlayer Installation on Windows

**PyRadio**: Command line internet radio player.

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [MPlayer installation](#mplayer-installation)

<!-- vim-markdown-toc -->

[[Back to Build Instructions]](windows.md) [[Back to README]](README.md)

## MPlayer installation

Go to [MPlayer's home](http://www.mplayerhq.hu/) and open the [download](http://www.mplayerhq.hu/design7/dload.html) page. Then scroll down to the **Binaries** section and get to the [MPlayer Windows builds](http://oss.netfarm.it/mplayer/) page. Then scroll down again until you get to the **Build selection table** to select an installation bundle.

**Note:** I am stating here all the links, although all one has to do is get to the last one and download the **MPlayer setup**. This is done so that in case any of the links change in the future, the way to go will be known, having [MPlayer's home page](http://www.mplayerhq.hu/) as a starting point.

You will end up downloading a [7z archive](https://www.7-zip.org/), which contains a directory whose name is similar to **MPlayer-corei7-r38135+gb272d5b9b6**.

**Note:** *MPlayer* provides CPU type dependent builds. In case you select the wrong *mplayer* build, you will end up connecting to stations but having no sound. If this is the case, please do go back to the download page and get the right build for your system / CPU.

Extract this directory to whatever place you like and **rename** it to **mplayer**.

Here comes the tricky part...

Move the **mplayer** directory to the following location (**PyRadio** will look for it there, when executed):

- **%APPDATA%\\pyradio** \
This is (or will be) "*PyRadio's configuration directory*". \
In case the "*pyradio*" directory does not exit, you just go ahead and create it.

In order to do that, open an **Explorer File Manager** window, and enter "**%APPDATA%**" at its location field and press ENTER.

If you are unsure on how to do that, please refer to the following image (you can ENTER **%APPDATA%** or any other Windows System Variable this way).

![Navigating to %APPDATA%](https://members.hellug.gr/sng/pyradio/appdata.jpg)


