# PyRadio Installation file (build_install_pyradio)

This file will help a normal user to build and install **PyRadio** using

* the system default python
* or python version 2.x (explicit)
* or python version 3.x (explicit)

From the repository directory, type
```
files/build_install_pyradio -h
```
for options.

# Develpment files for PyRadio

These files are not meant to be used by a normal user.

Use them only if you are a **PyRadio developer**.

You have been warned...

## 1. pre-commit

This is a git hook used to create *README.html*.

It requires [pandoc](https://pandoc.org).

If ***pandoc*** is not installed and you try to use
this hook, you will not be able to commit your changes.

To install it, execute
```
cp files/pre-commit .git/hooks
```

## 2. what_tag

This script will help you create a local tag (i.e.
RyRadio version) and commit it upstream.

It will not perform the actual action; just report
what you should do manually.

Check it out:
```
files/what_tag
```


