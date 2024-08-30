# PyRadio Recordings Directory

**PyRadio** will record stations to files (when [recording](recording.md) is enabled) and save the resulting files in a dedicated directory.

This directory used to be inside the "**configuration directory**", but since **v. 0.9.2.26** it will be located in the user's home directory and will be named "**pyradio-recordings**", by default.

Also, since **v. 0.9.3**, the directory is user selectable, providing this way maximum flexibility.

When the new directory is selected (actually typed or pasted in the relevant dialog), and saved, **PyRadio** will try to **move** the existing directory to the new location.

This is a case table of how this will work.

|  | If the new directory                   | PyRadio will
|--|----------------------------------------|-------------------------------------------------------------------------------------------------------|
|1.| does not exist                         | move the original directory to the new location and optionally rename it                              |
|2.| already exists and it is **empty**     | delete the new directory and move the original directory to the new location and optionally rename it |
|3.| already exists and it is **not empty** | move the original directory **inside** the new directory and optionally rename it                     |

### 1. New directory does not exist

There's nothing more to say about this case; the old directory will be moved/renamed and will be available to the program immediately.

### 2. New directory exists and it is empty

The user experience will be the same as the previous case, though the directory will actually be removed before moving/renaming the old directory.

Please make sure you do not specify a commonly OS used folder here, such as "*Downloads*", "*Documents*" or "*Pictures*", as it may be **overwritten**.

### 3. New directory exists but it is not empty

This is when it gets tricky; the original directory will be renamed to "**pyradio-recordings**" and will be moved inside the user specified folder. **PyRadio** will use this moved directory to save recorded files instead of the one specified by the user (which will actually be the parent directory of the "*pyradio-recordings*" directory.)


## Pre 0.9.3 installation behavior

Pre 0.9.3 installations will use ~/.config/pyradio/data/recordings as the recording directory, by default.

After updating to v. 0.9.3 (and newer), **PyRadio** will move this directory to the user's home folder and rename it to "**pyradio-recordings**".

Then the user can change the folder's location from *Config / General options / Recording dir*.

## Post 0.9.3.10 behavior

Up until **v. 0.9.3.10, Ryradio** would create the "*recording directory*" upon startup, no matter where it would be located, making it available for the recording and titles' log function.

This eventually creates the following problem:

A user who never wants to use the recording or the titles' log function, ends up with an empty directory in his home folder, which will be recreated every time **PyRadio** is executed (even if deleted before that), as described in [issue No. 253](https://github.com/coderholic/pyradio/issues/253).

The solution is that **PyRadio** will remove the "*recording directory*" upon execution, if

1. the default location is used
2. the directory is empty

As a consequence, both the recording and the titles' log function will make sure the directory actually exists (and create it if it does not), before trying to save any data to it.
