# PyRadio Remote Control Client

## Table of Contents
<!-- vim-markdown-toc Marked -->

* [Remote Control Client](#remote-control-client)
    * [Command line parameters](#command-line-parameters)
    * [How it works](#how-it-works)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#remote-control-server) ]

## Remote Control Client

**PyRadio** comes with a client to be used in conjunction with the **Remote Control Server** provided by the program, using the server's text command set.

The **client** is created with maximum ease in mind; the user does not even have to provide the IP and PORT.

### Command line parameters

The following is the output of the "**pyradio -h**" command:

```
Usage: pyradio-client [-h] [--address] [-s SERVER_AND_PORT] [-r] [-t TIMEOUT]
                      [command]

PyRadio Remote Control Client

General options:
  -h, --help            Show this help message and exit
  --address             List available servers

Server Parameters:
  -s SERVER_AND_PORT, --server_and_port SERVER_AND_PORT
                        Set the servers's IP and PORT (format: IP:PORT)
  -r, --reverse-detection
                        Reverse server detection (when no server IP and PORT
                        specified); detect headless server last, instead of
                        headless server first
  -t TIMEOUT, --timeout TIMEOUT
                        Set the timeout (default = 1.0)
  command               The command to send to the server

```

### How it works

The client will auto-detect the **PyRadio Servers** running on the system, when the "*-s*" command line parameter is not used.

The auto-detection functionality is based on parsing the "*server files*" (residing in the STATE directory).

If both a **headless** and a **normal** instance of **PyRadio** are detected, the **headless** server will be used to send the requested command, unless the "*-r*" ("*--reverse-detection*") command line parameter is used.

**Note:** A **normal** server is a server started by a **PyRadio** instance which is executed on a real terminal, without the "*--headless*" command line parameter.

A list of available commands will be displayed when no command has been specified.

A list of detected servers (and their address) can be obtained using the command:

```
$ pyradio-client --addr

PyRadio Remote Control Server
  Headless server: 127.0.0.1:11111
  Server: 127.0.0.1:9998
```
Then, the **address** reported can be used to contact a specific server:

    pyradio-client -s 127.0.0.1:9998 i

The previous command will get the info page of the **normal** instance of a server.


