# Recording stations

**PyRadio**: Command line internet radio player.

___


**Berfore you continue, read this!**

Generally, recording a radio streaming broadcast is considered legit, if the recording is to be used for personal use only (i.e. to listen to the broadcast at a later time).

Distributing such a recording, is illegal. Broadcasting it is also illegal. Its reproduction before an audience is also illegal. In some countries/regions, it is also illegal to split or tag the songs in the recording.

Please make sure you are informed about this topic, about what the law considers illegal at your country/region, **before using this feature!**

**You have been warned!**

**PyRadio**, its creator and maintainers do not condone any behavior that involves online piracy or copyright violation. This feature is provided strictly for personal use, and to utilize another requested feature: **pausing and resuming** playback.

___

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Intro](#intro)
    * [MPV](#mpv)
    * [MPlayer](#mplayer)
    * [VLC](#vlc)
    * [VLC recording on Windows](#vlc-recording-on-windows)
* [Recording implementation](#recording-implementation)
    * [Starting recording from the command line](#starting-recording-from-the-command-line)
    * [File location](#file-location)
    * [File type](#file-type)
    * [Chapters](#chapters)
        * [MKVToolNix installation](#mkvtoolnix-installation)
            * [Linux](#linux)
            * [MacOS](#macos)
            * [Windows](#windows)
    * [Files location](#files-location)
    * [Pausing playback](#pausing-playback)

<!-- vim-markdown-toc -->

[[Return to main doc]](README.md#recording-stations)

## Intro

**PyRadio v. 0.9.2.8** introduces the ability to record stations, a feature used mainly to facilitate another feature: the ability to *pause and resume playback*.

All supported media players (**MPV**, **MPlayer** and **VLC**) support stream recording, each implementing it in a different way, which pose a challenge for the front end implementation.

Before we see the differences, let us talk about some things that will make the whole thing easier to understand.

When it comes to recording a stream the program has to provide two things:

1. a **recorder**, which is the component that will connect to the stream (in our case the station), receive its data, and write them in a file that media players can recognize and reproduce. \
\
Since this is the program receiving data from the station, it will also receive song titles, or other stations data, but will not save them to the recorded file.

2. a **monitor**, which is the component that will reproduce the saved stream so that the user can monitor what is being downloaded. \
\
The **monitor** will just reproduce what's written to the file by the **recorder**, so it knows nothing about a station, it's data and song titles transmitted by it.

Now, let's see how **PyRadio**'s supported players behave.

### MPV

**MPV** stream recording has the following characteristics:

- it is considered an **experimental feature** by the **MPV** developers. \
Radio streaming uses well known and established codecs (mainly mp3 and aac) and I have had no broken recording while testing the feature (even with flac stations).

- **MPV** has the ability to play and record a stream at the same time (both the **recorder** and the **monitor** components are active simultaneously). \
This is very convenient, since all one has to do is add a command line parameter and start recording, while listening to what's being recorded.

- adjusting the volume or muting the player will not affect what's being recorded.

- when paused, the player will pause the playback but will keep recording the stream. Furthermore, song titles will stop being updated, but will be correctly displayed and updated when playback is resumed.

### MPlayer

**MPlayer** stream recording has the following characteristics:

- it does not have the ability to record and play a stream at the same time. \
This means that the front end (**PyRadio**) will have to use two *mplayer* instances (run *mplayer* twice): one as a **recorder** and one as a **monitor**.

- the **recorder** will display the song titles in addition to saving the output file.

- the **monitor** will be started after the output file gets to a certain size, set to 12000 bytes by trial and error.

- pausing and resuming the **monitor** for long will lead to song titles being out of sync, since the **recorder** will keep receiving data (and song titles) even when the playback if off.

### VLC

**VLC** stream recording has the following characteristics:

- it does not have the ability to record and play a stream at the same time. \
This means that the front end (**PyRadio**) will have to use two *vlc* instances (run *vlc* twice): one as a **recorder** and one as a **monitor**.

- the **recorder** will display the song titles in addition to saving the output file.

- the **monitor** will be started after the output file gets to a certain size, set to 120000 bytes by trial and error.

- pausing and resuming the **monitor** for long will lead to song titles being out of sync, since the **recorder** will keep receiving data (and song titles) even when the playback if off.

### VLC recording on Windows

**VLC** recording in **not** supported on **Windows**.

The **VLC** implementation on **Window** is a bit clumsy as it is as a radio player, and duplicating all this clumsiness in order to support recording as well, is just too much.

Trying to enable recording while **VLC** is the active player will lead to displaying a message informing the user of the situation and ways to proceed.

Consequently, this restriction has been applied to the "*Switch Media Player*" window (opened with "**\\m**"); when recording a station and trying to change the player in use on **Windows**, selecting **VLC** is not supported.

## Recording implementation

The following keys are used for this feature:

| Key                    | Description                 |
|------------------------|-----------------------------|
| \|<br>(pipe symbol)    | Toggle recording on and off |
| Space                  | Pause and resume playback   |

In order to record a station, recording has to be enabled **beforehand**, by pressing the *"pipe symbol*" or "*vetical line*" ("**|**"). Then the following message appears:

![Enable recording](https://members.hellug.gr/sng/pyradio/pyradio-recording1.jpg)

When this is done an "**[r]**" will be displayed at the top left corner of the window. This means that recording is enabled, but **PyRadio** is not currently recording to a file.

When playback is started (i.e. start playing a station), an "**[R]**" will be displayed at the top left corner of the window (replacing the "**[r]**" that was already there), which means that **PyRadio** is actually recording the station to a file.

The following image is a mockup presenting the difference.

![Recording mockup](https://members.hellug.gr/sng/pyradio/pyradio-recording2.jpg)

Pressing the *"pipe symbol*" or "*vetical line*" ("**|**") again will disable recording and nothing will be displayed at the top left corner of the window. The actual recording of the station will still be active, until the station is stopped.

It must be made clear that toggling the recording status for **PyRadio** will actually take effect after a station has been started or stopped. This is because of the way the players get the recording command; through command line arguments, which can only be passed when the player is executed.

### Starting recording from the command line

One can use the "**--record**" command line parameter to start the program in recording mode.

This would be extra useful to start playback and recording, for example:

```
pyradio -p 3 --record
```

This command would open the default playlist (or the one last used, if set in the config), using the default player, and start playing and recording station No 3.

**Note:** If the default player is **VLC** on Windows, and the "**--record**" command line parameter is used, a message informing the user that recording is not supported, will be displayed.

### File location

Files created by the recording feature will be saved under the "**recordings**" folder inside **PyRadio**'s configuration directory.

The file will be named:

```
[date] [Station Name].mkv
```

### File type

**PyRadio** will produce a **mkv** file when recording a station.

This is just a measure of convenience since the type of audio (mp3, aac, aac+, flac, etc.) the station will broadcast cannot be known beforehand (before starting the recording, that is).

Although a **mkv** file is a video/audio/subs etc. container, it's perfectly fine to contain just a sound stream, as is the case of the files produced by **PyRadio**.

The file can be (hopefully) reproduced using any video media player.

### Chapters

As a convenience, **PyRadio** will write chapter markers to the file produced, provided that:

1. [MKVToolNix](https://mkvtoolnix.download/) is installed. \
MKVToolNix is a set of tools to create, alter and inspect [Matroska](http://www.matroska.org/) files under Linux, other Unices and Windows. \
**PyRadio** uses *mkvmerge* (*mkvmerge.exe* on Windows) to add chapters to the MKV file.

2. The stations will provide *ICY Titles* (the titles will be used as **chapter titles**).

Things to consider:

- The first chaprer will always be at 00:00 and will be the name of the station.

- Chapters markers timing depends on the time the *ICY Titles* are received, plus any overhead added by **PyRadio**. \
\
This means that, for whatever reason, a chapter marker may not exactly point to the beginning of the song associated with it.

The image below shows how a chapter aware player will display and handle chapter markers found in a MKV file. This is the [Media Player Classic](https://sourceforge.net/projects/mpc-hc/) on Windows 7.

![PyRadio Chapters](https://members.hellug.gr/sng/pyradio/pyradio-chapters.gif)

#### MKVToolNix installation

Why would I want to install yet another package / program, you may ask.

Here's why:

1. Through **MKVToolNix** it is possible to have the songs titles embedded in the recorded file itself.

2. If the player used to reproduce the recorded file is chapters aware (most are), you can also navigate to the songs; their titles will be availabe at the **Chapters** menu (wherever the application chooses to place it).

3. If your player of choice for **PyRadio** is **MPlayer**, you really should take the time to install **MKVToolNix**. \
\
The reason is that **MPlayer** will dump the audio data it receives to the file without any alteration. This means that even though the saved file will have the *mkv* extension, the file will not be a valid Mastroka file; it will be an MP3, a FLAC, a AAC or whatever encoding is used by the station. \
\
Using **MKVToolNix** to add chapters to the file will actually create a valid **mkv** file.

Having said that, let's see how to install **MKVToolNix**.

##### Linux

On **Linux** you will have no problem installing the package; all distros will include it, either as *mkvtoolnix*, or *mkvtoolnix-cli* or whatever.

Just make sure that after the installation you can execute **mkvmerge** from a terminal.

##### MacOS

On **MacOS**, it all depends on your System Version, i guess.

First try to use [HomeBrew](https://brew.sh/):

    brew install mkvtoolnix

I do not know if using [HomeBrew](https://brew.sh/) for the installation will place **mkvmerge** into your PATH, but if it does, you are done.

I was not able to install it on *Catalina* using [HomeBrew](), so I ended up using the AppImage from [MKVToolNix](https://mkvtoolnix.download/downloads.html#macosx). Just make sure you download the right version for your system.

Then, since the installed application was not in the PATH (so that **PyRadio** finds **mkvmerge**), I just executed (in a terminal):

```
sudo find / -name mkvmerge
```

and ended up with

```
/System/Volumes/Data/Applications/MKVToolNix-54.0.0.app/Contents/MacOS/mkvmerge
/Applications/MKVToolNix-54.0.0.app/Contents/MacOS/mkvmerge
```

Since I do not know the difference between the first and second result, I will just use the second one, just because it is shorter :)

So, finally:

```
mkdir -p ~/.config/pyradio/data
echo '#!/bin/bash' > ~/.config/pyradio/data/mkvmerge
echo '/Applications/MKVToolNix-54.0.0.app/Contents/MacOS/mkvmerge "$@"' >> ~/.config/pyradio/data/mkvmerge
chmod +x ~/.config/pyradio/data/mkvmerge
```

##### Windows

For **Windows 10** and **11** you have two options; either install the package provided by [MKVToolNix](https://mkvtoolnix.download/), or use the portable version.

If you decide to go with the later option, please read on.

For **Window 7** (or **Windows 10** and **11** portable installation), this is what you do:

1. Download the **7z** file provided by [MKVToolNix for Windows 7](https://github.com/jpsdr/MKVToolnix-QT5-Windows-7/releases). \
\
If you have decided to use one of the **portable** versions of [MKVToolNix](https://mkvtoolnix.download/) on **Windows 10** or **11**, download that **7z** file instead.

2. "Install" it in **PyRadio Configuration Folder**. \
\
To do that, open **PyRadio** and press "*\\o*" to open the configuradio folder in the File Explorer. \

3. Create a folder named "**mkvtoolnix**"

4. Extract the **7z** file you previously downloaded, in the "**mkvtoolnix**" folder.

### Files location

The file produced by the recording function will be placed in the **recordings** directory, inside the *configuration directory*.

If **MKVToolNix** is not installed, the file will be downloaded in this directory and will not be altered by **PyRadio**.

If **MKVToolNix** is installed, the file will initially be downloaded in the "*data*" directory; the final file, after chapters addition, will be placed in the **recordings** directory and the downloaded file will be deleted.


**Note:** On **Windows**, if **MKVToolNix** is installed, a dedicated routine will be executed at program's startup to remove all recording related files from the "*data*" folder.

### Pausing playback

After you have started recording a station, **PyRadio** will connect to it and start downloading the station data and at the same time will produce sound for you to hear what's downloaded.

You can then press "**Space**" to pause the playback, but still continue downloading the station's data.

Pressing "**Space**" again will resume playback from where it left off.

As a consequence, listening to the end of a show that you have paused for say 10 minutes, and then stopping the station (both playback and recording), the file recorded will have an excess of 10 minutes of data, past the end of the actual show.

Finally, please keep in mind that all other keys relevant to starting, stopping and restarting a station's playback remain the same; only the behavior of the "**Space**" key has changed when recording is on.
