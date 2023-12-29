# PyRadio Headless Operation

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Goal](#goal)
    * [Usage](#usage)
    * [How it works](#how-it-works)
* [Installation](#installation)
    * [systemd](#systemd)
* [Using screen instead of tmux](#using-screen-instead-of-tmux)

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

After the program is started, the only way (well, not really, more on this below) to interact with it is through its integrated web server.

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

It will create a "headless server lock file", though, so that a) we cannot start a second headless server, and b) we can get info about the server running.

To get access to the program, execute:

```
tmux attach-session -t pyradio-session
```

To detach the session press **C-b d** (default key binding).

## Installation

**Note:** the instructions in this section focus on using **tmux**; differences regarding using **screen** will follow.

By the term "installation", we mean that we set up things in such a way, that after we log into the system, we find **PyRadio** ready to accept connections.

So, the installation can be as easy as adding a line in a configuration file (or the startup section of the *desktop environment*) or as hard as adding a system service.

**Note:** All commands start by removing the "headless server lock file", just in case **PyRadio** was not able to remove it itself the last time it terminated... this should be acceptable, since these commands are supposed to be running once, at system boot.

For example, if **bash** is the default shell, this would do the trick:
```
echo "rm /home/spiros/.config/pyradio/data/server-headless.txt 2>/dev/null
      /usr/bin/tmux new-session \
        -dA -s pyradio-session /home/spiros/.local/bin/pyradio \
        --headless auto" >> ~/.profile
```

In case a *Window manager* is used, adding a line in its **autostart** file would be enough. For example, this would work for **openbox**:

```
echo "(sleep 10; rm /home/spiros/.config/pyradio/data/server-headless.txt 2>/dev/null; /usr/bin/tmux new-session -dA -s pyradio-session /home/spiros/.local/bin/pyradio --headless auto)" >> ~/.config/openbox/autostart
```

And so on, and so forth...


### systemd

The first thing you do is create the log file:

    touch ~/pyradio.log

Then create the start file:

    mkdir ~/.local/bin
    echo "#!/bin/bash" > ~/.local/bin/start-headless-pyradio.sh
    echo "rm /home/spiros/.config/pyradio/data/server-headless.txt 2>/dev/null" >> ~/.local/bin/start-headless-pyradio.sh
    echo "/usr/bin/tmux new-session -dA -s pyradio-session /home/spiros/.local/bin/pyradio --headless auto" >> ~/.local/bin/start-headless-pyradio.sh
    chmod +x ~/.local/bin/start-headless-pyradio.sh

Finally create the service:

File `/lib/systemd/system/pyradio.service`

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
ExecStop=/usr/bin/tmux kill-session -t pyradio-session

[Install]
WantedBy=multi-user.target
```

Then execute:
```
$ sudo chmod 644 /lib/systemd/system/pyradio.service
$ sudo systemctl daemon-reload
$ sudo systemctl enable pyradio # enabling the autostart on every boot
```

And get the status:
```
$ sudo systemctl status pyradio
● pyradio.service - PyRadio Service
     Loaded: loaded (/usr/lib/systemd/system/pyradio.service; enabled; preset: disabled)
     Active: active (running) since Fri 2023-12-01 11:33:02 EET; 2min 47s ago
    Process: 10829 ExecStart=/home/spiros/.local/bin/start-headless-pyradio.sh (code=exited, status=0/SUCCESS)
   Main PID: 10831 (tmux: server)
      Tasks: 23 (limit: 9395)
     Memory: 103.3M
        CPU: 2.629s
     CGroup: /system.slice/pyradio.service
             ├─10831 /usr/bin/tmux new-session -dA -s pyradio-session /home/spiros/.local/bin/pyradio --headless auto
             ├─10941 /home/spiros/.local/pipx/venvs/pyradio/bin/python /home/spiros/.local/bin/pyradio --headless auto
             └─11126 mpv --no-video --quiet https://icecast.walmradio.com:8443/christmas --input-ipc-server=/tmp/mpvsocket.10941 --profile=pyradio

Dec 01 11:33:02 py systemd[1]: Starting PyRadio Service...
Dec 01 11:33:02 py systemd[1]: Started PyRadio Service.
```

The service can be stopped:
```
sudo systemctl stop pyradio
```

And this is its state:
```
$ sudo systemctl status pyradio
○ pyradio.service - PyRadio Service
     Loaded: loaded (/usr/lib/systemd/system/pyradio.service; enabled; preset: disabled)
     Active: inactive (dead) since Fri 2023-12-01 11:37:51 EET; 21s ago
   Duration: 4min 49.355s
    Process: 10829 ExecStart=/home/spiros/.local/bin/start-headless-pyradio.sh (code=exited, status=0/SUCCESS)
    Process: 11353 ExecStop=/usr/bin/tmux kill-session -t pyradio-session (code=exited, status=0/SUCCESS)
   Main PID: 10831 (code=exited, status=0/SUCCESS)
        CPU: 4.097s

Dec 01 11:33:02 py systemd[1]: Starting PyRadio Service...
Dec 01 11:33:02 py systemd[1]: Started PyRadio Service.
Dec 01 11:37:51 py systemd[1]: Stopping PyRadio Service...
Dec 01 11:37:51 py systemd[1]: pyradio.service: Deactivated successfully.
Dec 01 11:37:51 py systemd[1]: Stopped PyRadio Service.
Dec 01 11:37:51 py systemd[1]: pyradio.service: Consumed 4.097s CPU time.
```

## Using screen instead of tmux

The difference is actually the command to start the detached session.

This means that you just have to replace the

    /usr/bin/tmux new-session -dA -s pyradio-session

part, with

    /usr/bin/screen -U -S pyradio-session -d -m

in the commands above.

To get access to the program, you'd execute:

    screen -r pyradio-session

and press "**C-a d**" to detach it again.

Other than that, the behavior should be the same.
