# PyRadio Installation file (build_install_pyradio)

This file will help a normal user to build and install **PyRadio** using

* the system default python
* or python version 2.x (explicit)
* or python version 3.x (explicit)

From the repository directory, type

    devel/build_install_pyradio -h

for options.

# Development files for PyRadio

These files are not meant to be used by a normal user.

Use them only if you are a **PyRadio developer**.

You have been warned...

## 1. pre-commit

This is a git hook used to create *README.html*.

It requires [pandoc](https://pandoc.org).

If ***pandoc*** is not installed and you try to use
this hook, you will not be able to commit your changes.

To install it, execute

    ln -s devel/pre-commit .git/hooks/pre-commit


## 2. what_tag

This script will help you create a local tag (i.e.
RyRadio version) and commit it upstream.

It will not perform the actual action; just report
what you should do manually.

Check it out:

    devel/what_tag

### How this works
1. set package version in ***pyradio/\_\_init\_\_.py***.
2. run this script to get help. This script will read the version from said file, and help you create the corresponding tag.
3. commit your changes, both local and remote.

When this is done, you will have a tag on the remote repository denoting the release of a new package version.

**Why go in all this trouble?**

Well, when the package is built against the tagged commit, the tag/version will be displayed. So far, so good.

When the package is built against an adjunct commit, the tag/version will be followed by the revision number (i.e. number of commits ahead of the tagged commit).

