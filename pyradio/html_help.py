# -*- coding: utf-8 -*-
import subprocess
import logging
from sys import platform
from os import path, environ, listdir
from shutil import which
from .install import get_a_linux_resource_opener
try:
    import psutil
    HAVE_PSUTIL = True
except:
    HAVE_PSUTIL = False

logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

'''
    0 : perform detection
    1 : Graphical Environment running
    2 : Graphical Environment not running
'''
HAS_GRAPHICAL_ENV = 0

def convert_to_md(a_file):
    tmp_file = a_file[:-4] + 'md'
    return tmp_file if path.exists(tmp_file) else a_file

def is_graphical_environment_running():
    global HAS_GRAPHICAL_ENV
    if HAS_GRAPHICAL_ENV == 1:
        return True
    elif HAS_GRAPHICAL_ENV == 2:
        return False
    if which('pgrep'):
        # Check if Xorg is running
        xorg_process = subprocess.run(['pgrep', '-x', 'Xorg'], stdout=subprocess.PIPE)
        if xorg_process.returncode == 0:
            HAS_GRAPHICAL_ENV = 1
            return True
        # Check if Wayland is running
        wayland_process = subprocess.run(['pgrep', '-x', 'wayland'], stdout=subprocess.PIPE)
        if wayland_process.returncode == 0:
            HAS_GRAPHICAL_ENV = 1
            return True
    elif path.exists('/proc'):
        for pid in listdir('/proc'):
            if pid.isdigit():
                try:
                    with open(f'/proc/{pid}/cmdline', 'rb') as f:
                        cmdline = f.read().decode().split('\x00')
                        if 'Xorg' in ' '.join(cmdline) or \
                            'wayland' in ' '.join(cmdline):
                            return True
                except FileNotFoundError:
                    continue
    elif HAVE_PSUTIL:
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'] == 'Xorg' \
                    or proc.info['name'] == 'wayland':
                HAS_GRAPHICAL_ENV = 1
                return True

    # Check if DISPLAY environment variable is set
    if 'DISPLAY' in environ:
        HAS_GRAPHICAL_ENV = 1
        return True

    HAS_GRAPHICAL_ENV = 2
    return False

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
                ''' linux '''
                # if is_graphical_environment_running():
                #     return
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
                # a_file = convert_to_md(a_file)
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

