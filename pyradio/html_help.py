# -*- coding: utf-8 -*-
import subprocess
import logging
from sys import platform
from os import path
from shutil import which
from .install import get_a_linux_resource_opener

logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

class HtmlHelp(object):

    _files = ('index.html', 'radio-browser.html')

    if platform.lower().startswith('win'):
        _paths = (path.join(path.expandvars('%APPDATA%'), 'pyradio', 'help'), )
    else:
        _paths = (
            '/usr/share/doc/pyradio',
            '/usr/local/share/doc/pyradio',
            path.join(path.expanduser('~'), '.local/share/doc/pyradio')
        )

    def __init__(self):
        for a_path in self._paths:
            if path.exists(a_path):
                self._path = a_path
                break

    def open_file(self, linux_resource_opener=None, browser=False):
        a_file = self._files[1] if browser else self._files[0]
        self._open_file(a_file, linux_resource_opener=linux_resource_opener)

    def open_filename(self,a_file, linux_resource_opener=None):
        self._open_file(a_file, linux_resource_opener=linux_resource_opener)

    def _open_file(self, a_file, linux_resource_opener=None):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('HtmlHelp: opening "{}"'.format(path.join(self._path, a_file)))
        this_platform = platform.lower()
        if this_platform.startswith('win'):
            from os import startfile
            startfile(path.join(self._path, a_file))
        else:
            if this_platform.startswith('darwin'):
                cmd = [which('open'),  path.join(self._path, a_file)]
            else:
                if linux_resource_opener is None:
                    tool = get_a_linux_resource_opener()
                else:
                    tool = linux_resource_opener
                if tool is None:
                    if logger.isEnabledFor(logging.INFO):
                        logger.info('HtmlHelp: Cannot find a run tool for Linux!')
                    return
                if isinstance(tool, str):
                    tool = tool.split(' ')
                cmd = [*tool , path.join(self._path, a_file)]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('HtmlHelp: executing: "{}"'.format(cmd))
            try:
                p = subprocess.Popen(
                        cmd,
                        shell=False,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE, close_fds=True)
            except (FileNotFoundError, PermissionError):
                pass

