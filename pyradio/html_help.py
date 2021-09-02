import subprocess
from sys import platform
from os import path

class HtmlHelp(object):

    _files = ('README.html', 'radio-browser.html')

    if platform.lower().startswith('win'):
        _paths = (path.join(path.expandvars('%APPDATA%'), 'pyradio', 'help'), )
    else:
        _paths = (
            '/usr/share/doc/pyradio',
            '/usr/local/share/doc/pyradio',
            path.join(path.expanduser('~'), '.local/share/doc')
        )

    def __init__(self):
        for a_path in self._paths:
            if path.exists(a_path):
                self._path = a_path
                break

    def open_file(self, browser=False):
        a_file = self._files[1] if browser else self._files[0]
        this_platform = platform.lower()
        if this_platform.startswith('win'):
            os.startfile(path.join(self._path, a_file))
        else:
            if this_platform.startswith('darwin'):
                cmd = 'open ' + path.join(self._path, a_file)
            else:
                cmd = 'xdg-open ' + path.join(self._path, a_file)
            p = subprocess.Popen(cmd,
                                 shell=True,
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE, close_fds=True)

