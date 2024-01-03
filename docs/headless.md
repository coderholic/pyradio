# PyRadio Headless Operation

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Goal](#goal)
    * [Usage](#usage)
    * [How it works](#how-it-works)
* [Installation](#installation)
    * [Notice](#notice)
    * [Using tmux](#using-tmux)
        * [systemd](#systemd)
    * [Using screen](#using-screen)
        * [systemd](#systemd)
    * [systemd service file](#systemd-service-file)
    * [Notice for systemd installation](#notice-for-systemd-installation)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#installation) ]


## Goal

This is a document that provides info on running **PyRadio** in *headless* mode (well, kind of), on a Linux, BSD, or Pi system.

Now, **PyRadio** is a **terminal application**; it actually **needs** a terminal to run. But there is a way to make it run on a "terminal" and at the same time run in the background, being "invisible" so to speak, or run as a weird kind of a daemon; the way to do that is run it in a **tmux detached session** or a **screen detached session**.

**tmux** man page reads:

"**tmux**  is  a  terminal  multiplexer: it enables a number of terminals to be created, accessed, and controlled from a single screen.  tmux may be **detached from a screen** and continue running in the background, then later reattached."

**screen** man page reads:

"**Screen** is a full-screen window manager that multiplexes a physical terminal  between  several processes (typically interactive shells)... Programs continue to run when their window is currently not visible and even when the whole screen session **is detached from the user's terminal**."


**PyRadio** users [Wikinaut](https://github.com/Wikinaut) and [aleksandr-sabitov](https://github.com/aleksandr-sabitov) on [github](https://github.com/coderholic/pyradio/issues/184) have come up with the idea to use this approach to run the application on their headless Raspberry Pi, so kudos to them!

### Usage

After the program is started, the only way to interact with it is through its integrated web server. Please refref to the relevant document for more info on the [remote control server](server.md).

The web server can be accessed either through a terminal (address **http://ip:port**) using `wget` or `curl`, or through a web browser (address **http://ip:port/html**).

The `ip` and `port` will be set using the **--headless** command line option.

The `ip` can either be:

1. **localhost** \
The server will be accessible only by programs running in the system. The `ip` is 127.0.0.1.
2. **lan** \
The server will be accessible by any system on the LAN. The `ip` is the one assigned to the network interface of the system.

For example:

- using **--headless lan:12345** \
will make the web server listen to the network interface IP address, port 12345.

- using **--headless localhost:23456** \
will make the web server listen to 127.0.0.1, port 23456

- using **--headless auto** \
will make the web server listen to 127.0.0.1, port 11111; this is the default and fallback configuration.

To get the server `ip` and `port`, execute on a terminal

```
pyradio --addr
```

Which will return something like:

```
PyRadio Remote Control Server
  Headless server
    Text address: http://127.0.0.1:11111
    HTML address: http://127.0.0.1:11111/html
```

If both a "headless" and a normal instance of **PyRadio** is running, you will get something like this:

```
PyRadio Remote Control Server
  Headless server
    Text address: http://127.0.0.1:11111
    HTML address: http://127.0.0.1:11111/html
  Server
    Text address: http://127.0.0.1:9998
    HTML address: http://127.0.0.1:9998/html
```

### How it works

When **PyRadio** is executed with the **--headles** command line option, it will basically start the web server and wait for connections.

To make it less memory hungry, the default (aka "*dark*" theme) will be loaded, and access to themes and the configuration window will be restricted.

Additionally, it will not create a "*session lock file*", so that other instances of the program can be executed normally (in a terminal), and be able to function properly.

It will create a "headless server lock file", though, so that

- we cannot start a second headless server, and

- we can get info about the server running.

## Installation

By the term "installation", we mean that we set up things in such a way, that after we log into the system, we find **PyRadio** ready to accept connections.

So, the installation can be as easy as adding a line in a configuration file (or the startup section of the *desktop environment*) or as hard as adding a system service.

### Notice

The commands that follow use the following conventions:

1. The username is **spiros**. \
Please replace it with your username.

2. **PyRadio** is installed from source; this means that its executable is **~/.local/bin/pyradio**. If this is not the case (using a distribution package, for example), please replace it with the correct one.

3. Both **tmux** and **screen** are executed using their *absolute path* (**/usr/bin/tmux** and **/usr/bin/screen** respectively). If they are installed at a different location, please use the correct one instead.

### Using tmux

If **bash** is the default shell, this would do the trick:
```
echo "/usr/bin/tmux new-session \
        -dA -s pyradio-session /home/spiros/.local/bin/pyradio \
        --headless auto" >> ~/.profile
```

In case a *Window manager* is used, adding a line in its **autostart** file would be enough. For example, this would work for **openbox**:

```
echo "(sleep 10; /usr/bin/tmux new-session -dA -s pyradio-session /home/spiros/.local/bin/pyradio --headless auto)" >> ~/.config/openbox/autostart
```

And so on, and so forth...

#### systemd

The first thing you do is create the log file:

    touch ~/pyradio.log

Then create the start file. Write this to **~/.local/bin/start-headless-pyradio.sh**

```
#!/bin/bash
/usr/bin/tmux new-session -dA -s pyradio-session /home/spiros/.local/bin/pyradio --headless auto
```

Then create the stop file. Writhe this to **~/.local/bin/stop-headless-pyradio.sh**

```
#!/bin/bash
[ -z "$(/usr/bin/tmux ls | grep pyradio-session)" ] || /usr/bin/tmux send-keys -t pyradio-session q
sleep 2
[ -z "$(/usr/bin/tmux ls | grep pyradio-session)" ] || /usr/bin/tmux send-keys -t pyradio-session q
[ -e /home/spiros/.config/pyradio/data/server-headless.txt ] && rm /home/spiros/.config/pyradio/data/server-headless.txt
```

Make both files executable:

    chmod +x ~/.local/bin/start-headless-pyradio.sh
    chmod +x ~/.local/bin/stop-headless-pyradio.sh

Now you are ready to create the [service file](#systemd-service-file).

### Using screen

If **bash** is the default shell, this would do the trick:
```
echo "/usr/bin/screen -U -S pyradio-session -d -m \
        /home/spiros/.local/bin/pyradio \
        --headless auto" >> ~/.profile
```

In case a *Window manager* is used, adding a line in its **autostart** file would be enough. For example, this would work for **openbox**:

```
echo "(sleep 10; /usr/bin/screen -U -S pyradio-session -d -m /home/spiros/.local/bin/pyradio --headless auto)" >> ~/.config/openbox/autostart
```

And so on, and so forth...

#### systemd

The first thing you do is create the log file:

    touch ~/pyradio.log

Then create the start file. Write this to **~/.local/bin/start-headless-pyradio.sh**

```
#!/bin/bash
/usr/bin/screen -U -S pyradio-session -d -m /home/spiros/.local/bin/pyradio --headless auto
```

Then create the stop file. Writhe this to **~/.local/bin/stop-headless-pyradio.sh**

```
#!/bin/bash
[ -z "$(/usr/bin/screen -ls | grep pyradio-session)" ] || /usr/bin/screen -S pyradio-session -p 0 -X stuff q
sleep 2
[ -z "$(/usr/bin/screen -ls | grep pyradio-session)" ] || /usr/bin/screen -S pyradio-session -p 0 -X stuff q
[ -e /home/spiros/.config/pyradio/data/server-headless.txt ] && rm /home/spiros/.config/pyradio/data/server-headless.txt

```

Make both files executable:

    chmod +x ~/.local/bin/start-headless-pyradio.sh
    chmod +x ~/.local/bin/stop-headless-pyradio.sh

Now you are ready to create the service file

### systemd service file

Create the file **/lib/systemd/system/pyradio.service**

```
[Unit]
Description=PyRadio Service
After=multi-user.target

[Service]
Type=forking
User=spiros
Environment="XDG_RUNTIME_DIR=/run/user/1000"
Environment="PULSE_RUNTIME_PATH=/run/user/1000/pulse/"
StandardOutput=append:/home/spiros/pyradio.log
StandardError=append:/home/spiros/pyradio.log
ExecStart=/home/spiros/.local/bin/start-headless-pyradio.sh
ExecStop=/home/spiros/.local/bin/stop-headless-pyradio.sh

[Install]
WantedBy=multi-user.target
```

Then execute:
```
sudo chmod 644 /lib/systemd/system/pyradio.service
sudo systemctl daemon-reload
sudo systemctl enable pyradio # enabling the autostart on every boot
```

### Notice for systemd installation

The service file has two lines starting with "*Environment=*"

These two lines provide an environment for *systemd*; I've found out that on Arch Linux, for example, **PyRadio** would produce no sound at all without them (it would not be able to connect to the sound server).

On other systems, on Raspberry Pi for example, they can be omitted altogether.

