# -*- coding: utf-8 -*-
import argparse
from argparse import ArgumentParser, SUPPRESS as SUPPRESS
import requests
from os import path, getenv
import sys
import re
from sys import platform
from rich import print

def format_list(a_string):
    print(a_string.replace(
    r'[', r'\[').replace(']', ']').replace(
    '/x,y', '/[green]x[/green],[blue]y[/blue]').replace(
    '/x', '/[green]x[/green]').replace(
    '[x]', '[[green]x[/green]]').replace(
    'x%', '[green]x[/green]%').replace(
    'id x', 'id [green]x[/green]').replace(
    'item x', 'item [green]x[/green]').replace(
    'if x', 'if [green]x[/green]').replace(
    'id y', 'id [blue]y[/blue]').replace(
    '(x', '([green]x[/green]').replace(
    ' (text only)', '').replace(
    'RadioBrowser', '[medium_purple]RadioBrowser[/medium_purple]').replace(
        '(headless)', '([blue]headless[/blue])'
    )
    )

class PyRadioClient(object):

    def __init__(
            self,
            host=None,
            port=None,
            server_file=None,
            alternative_server_file=None,
            timeout=1.0,
            reverse_detection=False
            ):
        self._host = None
        self._port = None
        self._file = None
        self._files = None
        self._last_command = None
        self._last_reply = None
        self._timeout = timeout
        self._type = -1
        self._discovered = True

        if host and port:
            self._host = host
            self._port = port
            ''' set self._file so that
                    server_found()
                    is_recording()
                are happy  '''
            self._file = host
            self._discovered = False
        elif server_file:
            if path.exists(server_file):
                self._file = server_file
            elif alternative_server_file is not None:
                if path.exists(alternative_server_file):
                    self._file = alternative_server_file

            if self._file:
                self._get_host_and_port_from_file()
        else:
            self._get_files()
            # search for files
            chk = (1, 0) if reverse_detection else (0, 1)
            for n in chk:
                if path.exists(self._files[n]):
                    self._file = self._files[n]
                    self._type = n
                    break
            if self._file:
                self._get_host_and_port_from_file()

    @property
    def server_ip(self):
        return self._host

    @property
    def server_port(self):
        return self._port

    @property
    def server_found(self):
        return False if self._file is None else True

    @property
    def last_command(self):
        return self._last_command

    @property
    def last_reply(self):
        if self._last_reply:
            if self._last_command == 'title':
                try:
                    return self._last_reply.split('<b>')[1][:-6]
                except IndexError:
                    return 'Error retrieving title!'
            elif self._last_command in ('i', 'info'):
                if self._discovered:
                    out = self._last_reply.splitlines()
                    out.insert(1, '  Server: ' + self._host + ':' + self._port)
                    self._last_reply = '\n'.join(out) + '\n'
                if 'Title: ' in self._last_reply:
                    self._last_reply = re.sub(r'Title: "([^"]*)"', r'Title: "[red3]\1[/red3]"', self._last_reply)
                self._last_reply = self._last_reply.replace(r'PyRadio', r'[magenta]PyRadio[/magenta]')
                self._last_reply = self._last_reply.replace(r'headless', r'[blue]headless[/blue]')
            if 'retry: ' in self._last_reply:
                self._last_reply = 'Command executed\n'
            return self._last_reply
        # empty reply
        if self._type == -1:
            return 'Command executed\n'

    def _get_files(self):
        if self._files is None:
            if platform.lower().startswith('win'):
                appdata = path.join(
                        getenv('APPDATA'),
                        'pyradio', 'data')
                self._files = (
                        path.join(appdata, 'server-headless.txt'),
                        path.join(appdata, 'server.txt')
                        )

            else:
                ''' linux et al '''
                # get XDG dirs
                data_dir = getenv(
                        'XDG_DATA_HOME',
                        path.join(path.expanduser('~'), '.local', 'share', 'pyradio')
                        )
                state_dir = getenv(
                        'XDG_STATE_HOME',
                        path.join(path.expanduser('~'), '.local', 'state', 'pyradio')
                        )
                if not path.exists(data_dir) or not path.exists(state_dir):
                    state_dir = getenv(
                        'XDG_CONFIG_HOME',
                        path.join(path.expanduser('~'), '.config')
                        )
                    state_dir = path.join(state_dir, 'pyradio', 'data')
                self._files = (
                        path.join(state_dir, 'server-headless.txt'),
                        path.join(state_dir, 'server.txt')
                        )

    def print_addresses(self):
        self._get_files()
        disp = []
        tok = ('Headless server', 'Server')
        out = '  {}: {}'
        for n in 0, 1:
            if path.exists(self._files[n]):
                try:
                    with open(self._files[n], 'r') as f:
                        addr = f.read()
                        disp.append(out.format(tok[n], addr))
                except:
                    pass
        if disp:
            print('[magenta]PyRadio Remote Control Server[/magenta]\n' +  '\n'.join(disp))
        else:
            print('No [magenta]PyRadio[/magenta] Remote Control Servers running\n')

    def is_recording(self):
        ''' Return recording to file status
            Return value:
                -2 : Error
                -1 : request timeout
                 0 : not recording
                 1 : recording a file
                 2 : No files found
        '''
        if self._file:
            ret, self._last_reply = self.send_command('srec')
            if ret == 0:
                if 'currently' in self._last_reply:
                    ''' recording to file '''
                    return 1
                ''' not recording to file '''
                return 0
            elif ret == 2:
                ''' request timeout '''
                return -1
            ''' error '''
            return -2
        ''' no server files found '''
        return 2

    def send_command(self, command):
        '''
            0 : all ok
            1 : error
        '''
        self._last_command = command
        if self._last_command is None:
            self._last_command = ''
        try:
            response = requests.get(
                    'http://' + self._host + ':' + self._port + '/' + command,
                    timeout=self._timeout)
            response.raise_for_status()  # Raise an exception for HTTP errors
            self._last_reply = response.text
            return 0, self._last_reply
        except requests.exceptions.RequestException as e:
            self._last_reply = f'{str(e)}'.split(':')[-1].strip(
                    ).replace('"', '').replace("'", '').replace(')', '')
            return 1, self._last_reply

    def _get_host_and_port_from_file(self):
        try:
            with open(self._file, 'r') as f:
                line = f.read()
        except:
            pass
        sp = line.split(':')
        try:
            self._host = sp[0]
            self._port = sp[1]
        except IndexError:
            pass



class MyArgParser(ArgumentParser):

    def __init(self):
        super(MyArgParser, self).__init__(
            description = description
        )

    def print_usage(self, file=None):
        if file is None:
            file = sys.stdout
        usage = self.format_usage()
        print(self._add_colors(self.format_usage()))

    def print_help(self, file=None):
        if file is None:
            file = sys.stdout
        print(self._add_colors(self.format_help()))

    def _add_colors(self, txt):
        t = txt.replace('show this help', 'Show this help').replace('usage:', '• Usage:').replace('options:', '• General options:').replace('[', '|').replace(']', '||')
        x = re.sub(r'([^a-zZ-Z0-9])(--*[^ ,\t|]*)', r'\1[red]\2[/red]', t)
        t = re.sub(r'([A-Z_][A-Z_]+)', r'[green]\1[/green]', x)
        x = re.sub('([^"]pyradio)', r'[magenta]\1[/magenta]', t, flags=re.I)
        t = re.sub(r'(player_name:[a-z:_]+)', r'[plum2]\1[/plum2]', x)
        x = re.sub(r'(•.*:)', r'[orange_red1]\1[/orange_red1]', t)
        t = x.replace('mpv', '[green]mpv[/green]').replace(
        'mplayer', '[green]mplayer[/green]').replace(
        'vlc', '[green]vlc[/green]').replace(
        'command', '[green]command[/green]').replace(
        '[green]command[/green]s', 'commands').replace(
        '[magenta] pyradio[/magenta]-client',
        ' [magenta]pyradio-client[/magenta]').replace(
        'PyRadio[/magenta] Remote Control Client',
        'PyRadio Remote Control Client[/magenta]')
        # with open('/home/spiros/pyradio-client.txt', 'w') as f:
        #     f.write(t + '\n')
        return '[bold]' + t.replace('||', r']').replace('|', r'\[').replace('• ', '') + '[/bold]'


def client():

    parser = MyArgParser(
        description='PyRadio Remote Control Client'
    )

    parser.add_argument('--address', action='store_true',
                        help='List available servers')

    server_opts = parser.add_argument_group('• Server Parameters')
    server_opts.add_argument('-s', '--server_and_port', default='',
                             help="Set the servers's IP and PORT (format: IP:PORT)")
    server_opts.add_argument('-r', '--reverse-detection', action='store_true', default=False,
                             help='Reverse server detection (when no server IP and PORT specified);'
                             ' detect headless server last, instead of headless server first')
    server_opts.add_argument('-t', '--timeout', default='1.0',
                             help='Set the timeout (default = 1.0)')
    server_opts.add_argument('command', nargs='?', type=str, default=None,
                             help='The command to send to the server')
    args = parser.parse_args()
    # sys.stdout.flush()

    timeout = float(args.timeout)

    if args.address:
        x = PyRadioClient()
        x.print_addresses()
        sys.exit()

    host = None
    port = None
    if args.server_and_port:
        try:
            host, port = args.server_and_port.split(':')
        except ValueError:
            print('[red]Error[/red]: Invalid server IP and PORT specified\n')
            sys.exit()
    x = PyRadioClient(host=host, port=port, reverse_detection=args.reverse_detection)

    if x.server_ip is None or x.server_port is None:
        print('No [magenta]PyRadio[/magenta] Remote Control Servers running\n')
    else:
        x.send_command(args.command)
        if x.last_command:
            print(x.last_reply)
        else:
            format_list(x.last_reply)

if __name__ == '__main__':
    client()
