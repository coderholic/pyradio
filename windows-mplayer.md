# MPlayer Installation on Windows

**PyRadio**: Command line internet radio player.

Ben Dowling - [https://github.com/coderholic](https://github.com/coderholic)

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [MPlayer installation](#mplayer-installation)
* [Adding MPlayer to the PATH](#adding-mplayer-to-the-path)

<!-- vim-markdown-toc -->

[[Back to Build Instructions]](windows.md) [[Back to README]](README.md)

## MPlayer installation

Go to [MPlayer's home](http://www.mplayerhq.hu/) and open the [download](http://www.mplayerhq.hu/design7/dload.html) page. Then scroll down to the **Binaries** section and get to the [MPlayer Windows builds](http://oss.netfarm.it/mplayer/) page. Then scroll down again until you get to the **Build selection table** to select an installation bundle.

**Note:** I am stating here all the links, although all one has to do is get to the last one and download the **MPlayer setup**. This is done so that in case any of the links change in the future, the way to go will be known, having [MPlayer's home page](http://www.mplayerhq.hu/) as a starting point.

You will end up downloading a [7z archive](https://www.7-zip.org/), which contains a directory whose name is similar to **MPlayer-corei7-r38135+gb272d5b9b6**.

**Note:** *MPlayer* provides CPU type dependent builds. In case you select the wrong *mplayer* build, you will end up connecting to stations but having no sound. If this is the case, please do go back to the download page and get the right build for your system / CPU.

Extract this directory to whatever place you like and **rename** it to **mplayer**.

Here comes the tricky part...

Move the **mplayer** directory to either on of the following locations:

a. **%USERPROFILE%**

    This is actually your "*Home*" directory.

    Please make a note that you will add "**%USERPROFILE%\\mplayer** to PATH.

b. **%APPDATA%\\pyradio**

    This is (or will be) "*PyRadio's configuration directory*".

    In case the **pyradio** directory does not exit, you just go ahead and create it.

    (Make a note that you will add "**%APPDATA%\\pyradio\\mplayer** to PATH)

In either case, in order to do that, open an **Explorer File Manager** window, and enter at its location field **%USERPROFILE%** or **%APPDATA%**.

If you are unsure on how to do that, please refer to the following image (you can ENTER **%USERPROFILE%** or **%APPDATA%** or any other Windows System Variable this way).

[Navigating to %APPDATA%](https://members.hellug.gr/sng/pyradio/appdata.jpg)


## Adding MPlayer to the PATH

The final step is to add MPlayer to the PATH System Variable.

Now, you already know the **path string** that has to be added (you have made a note of it in the previous step).

There's just one thing to say here: Windows provide a "*User variable for User*" and a "*System variables*" section in the "*Environment Variables*" window.

Add the **path string** to the "*User variables for User*" section.

In order to make the actual addition, please refer to the following image.

[Adding MPlayer to the PATH](https://members.hellug.gr/sng/pyradio/path.jpg)

After applying the changes you should **log off and back on** or **restart the system**, because changes done to the PATH variable will take effect the next time you log into the system.

When you are back on, verify that you can run **MPlayer**; open a console (press the **Win** key, type **cmd** and press **ENTER**) and type "**mplayer**".

If you get something similar to the following snippet, you are all good.

    MPlayer Redxii-SVN-r38119-6.2.0 (x86_64) (C) 2000-2018 MPlayer Team
    Using FFmpeg N-92801-g7efe84aebd (2018-12-25 00:44:17 +0100)
    Compiled on 2018-12-25 13:55:17 EST (rev. 1)
    Usage:   mplayer [options] [url|path/]filename

If **mplayer** was not found, you just have to go through the PATH modification procedure again.
