# What happened?

Well, things are always evolving and changing when it comes to computers, this is what happened :)

In a word, `pip` is not allowed to install packages anymore, unless they are installed in a virtual environment.

For more info, please refer to this [section](build.md#current-state-of-the-project).

## Solution

1. Uninstall **PyRadio**:
```
pyradio -R
```
2. Install `pipx`. Since your distro has moved to this python installation change, it will probably have `pipx` in its repos. \
\
For Debian, Ubuntu 23.04, etc, this would be the way to go:

```
sudo apt-get install python3-full python3-pip python3-venv pipx

```

After `pipx` is installed, execute the follwoing command:

```
python3 -m pipx ensurepath
```

and exit the terminal.

Open a new terminal (so that the new PATH is read) and...

3. Download [install.py](https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py) and execute:

```
cd
curl -L \
    https://raw.githubusercontent.com/coderholic/pyradio/master/pyradio/install.py \
    -o install.py
python3 install.py
```

This should get you up and running.

**Note:** If you are updating a **0.9.2.5 PyRadio installation**, please do execute:

```
sudo apt-get install python3-dateutil
```


