# MPV Installation on Windows

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [MPV installation](#mpv-installation)
* [Adding MPV to the PATH](#adding-mpv-to-the-path)

<!-- vim-markdown-toc -->

[[Back to Build Instructions]](windows.md) [[Back to README]](README.md)

## MPV installation

Go to [MPV's home](http://mpv.io) and open the [Installation](https://mpv.io/installation) page and click the [Windows builds by shinchiro (releases and git)](https://sourceforge.net/projects/mpv-player-windows/files) link to get to the files. Then you can choose to install either the git version ([64bit](https://sourceforge.net/projects/mpv-player-windows/files/64bit/) or [32bit](https://sourceforge.net/projects/mpv-player-windows/files/32bit/)), or the latest **stable** [release](https://sourceforge.net/projects/mpv-player-windows/files/release/) which also provides both 64 and 32 bit binaries.

**Note:** I am stating here all the links, although all one has to do is get to the last one and download the **MPV setup**. This is done so that in case any of the links change in the future, the way to go will be known, having [MPV's home page](https://mpv.io) as a starting point.

You will end up downloading a [7z archive](https://www.7-zip.org/), which contains a directory whose name is similar to **mpv-0.34.-x86_64.7z**.

Extract this archive to whatever place you like and **rename** it to **mpv**.

Here comes the tricky part...

Move the **mpv** directory to either on of the following locations:

a. **%USERPROFILE%**

    This is actually your "*Home*" directory.

    Please make a note that you will add "**%USERPROFILE%\\mpv** to PATH.

b. **%APPDATA%\\pyradio**

    This is (or will be) "*PyRadio's configuration directory*".

    In case the **pyradio** directory does not exit, you just go ahead and create it.

    (Make a note that you will add "**%APPDATA%\\pyradio\\mpv** to PATH)

In either case, in order to do that, open an **Explorer File Manager** window, and enter at its location field **%USERPROFILE%** or **%APPDATA%**.

If you are unsure on how to do that, please refer to the following image (you can ENTER **%USERPROFILE%** or **%APPDATA%** or any other Windows System Variable this way).

![Navigating to %APPDATA%](https://members.hellug.gr/sng/pyradio/appdata.jpg)


## Adding MPV to the PATH

The final step is to add MPV to the PATH System Variable.

Now, you already know the **path string** that has to be added (you have made a note of it in the previous step).

There's just one thing to say here: Windows provide a "*User variable for User*" and a "*System variables*" section in the "*Environment Variables*" window.

Add the **path string** to the "*User variables for User*" section.

In order to make the actual addition, please refer to the following image.

![Adding MPV to the PATH](https://members.hellug.gr/sng/pyradio/path.jpg)

**Note**: This image is the one used in the relevant **mplayer** page; in this case you just replace **mplayer** with **mpv**.

After applying the changes you should **log off and back on** or **restart the system**, because changes done to the PATH variable will take effect the next time you log into the system.

When you are back on, verify that you can run **MPV**; open a console (press the **Win** key, type **cmd** and press **ENTER**) and type "**mpv**".

If you get something similar to the following snippet, you are all good.


    mpv 0.34.0 Copyright © 2000-2021 mpv/MPlayer/mplayer2 projects
     built on Sun Nov  7 20:16:38 +08 2021
    FFmpeg library versions:
       libavutil       57.7.100
       libavcodec      59.12.100
       libavformat     59.8.100
       libswscale      6.1.100
       libavfilter     8.16.101
       libswresample   4.0.100
    FFmpeg version: git-2021-11-06-1728127e

    Usage:   mpv [options] [url|path/]filename

    Basic options:
     --start=<time>    seek to given (percent, seconds, or hh:mm:ss) position
     --no-audio        do not play sound
     --no-video        do not play video
     --fs              fullscreen playback
     --sub-file=<file> specify subtitle file to use
     --playlist=<file> specify playlist file

     --list-options    list all mpv options
     --h=<string>      print options which contain the given string in their name

If **mpv** was not found, you just have to go through the PATH modification procedure again.
