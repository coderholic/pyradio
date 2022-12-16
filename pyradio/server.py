# https://stackoverflow.com/questions/10114224/how-to-properly-send-http-response-with-python-using-socket-library-only
import socket
import logging
from os.path import basename
from sys import platform, version_info
import requests

PY2 = version_info[0] == 2
logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

if not platform.lower().startswith('win'):
    import netifaces

class IPs(object):
    def __init__(self, fetch_public_ip=False):
        self._fetch_public_ip = fetch_public_ip
        self._IPs = []

    @property
    def fetch_public_ip(self):
        return self._fetch_public_ip

    @fetch_public_ip.setter
    def fetch_public_ip(self, value):
        old_value = self._fetch_public_ip
        self._fetch_public_ip = value
        if old_value != self._fetch_public_ip:
            self._IPs = self._get_all_ips()

    @property
    def IPs(self):
        if not self._IPs or not self._fetch_public_ip:
            self._get_all_ips()
        return self._IPs

    def _get_all_ips(self):
        ''' get local IPs '''
        if not platform.lower().startswith('win'):
            self._IPs = self._get_linux_ips()
        else:
            self._IPs = self._get_win_ips()
        ''' get public IP '''
        if self._fetch_public_ip:
            ip = self._get_public_ip()
            if ip:
                self._IPs.append(ip)

    def _get_public_ip(self):
        try:
            ip = requests.get('https://api.ipify.org').text
        except requests.exceptions.RequestException:
            return None
        if version_info[0] < 3:
            ip = ip.encode('utf-8')
        return ip

    def _get_linux_ips(self):
        out = ['127.0.0.1']
        interfaces = netifaces.interfaces()
        for n in interfaces:
            iface=netifaces.ifaddresses(n).get(netifaces.AF_INET)
            if iface:
                # dirty way to get real interfaces
                if 'broadcast' in str(iface):
                    if version_info[0] > 2:
                        out.append(iface[0]['addr'])
                    else:
                        out.append(iface[0]['addr'].encode('utf-8'))
        return out

    def _get_win_ips(self):
        out = ['127.0.0.1']
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0)
        try:
            # doesn't even have to be reachable
            s.connect(('10.254.254.254', 1))
            out.append(s.getsockname()[0])
        except Exception:
            pass
        finally:
            s.close()
        return out


class PyRadioServer(object):

    _html = '''HTTP/1.1 200 OK
Content-Type: text/html

<!DOCTYPE html><html lang="en"><head><title>PyRadio Web Service</title><meta charset="utf-8"><title></title></head><body><pre>

{}

</pre></body></html>
'''

    _text = {
        '/': '''PyRadio Remote Service

Global Commands
Long             Short      Description
--------------------------------------------------------------------
/info            /i         display PyRadio info
/volumeup        /vu        increase volume
/volumedown      /vd        decrease volume
/mute            /m         toggle mute
/log             /g         toggle stations logging
/like            /l         tag (like) station

Restricted Commands
--------------------------------------------------------------------
/toggle          /t         toggle playback
/playlists       /pl        get playlists list
/playlists/x     /pl/x      get stations list from playlist id x
                            (x comes from command /pl)
/playlists/x,y   /pl/x,y    play station id y (-1 = random) from
                            playlist id x
/stations        /st        get stations list from current playlist
/stations/x      /st/x      play station id x from current playlist
/next            /n         play next station
/previous        /p         play previous station
/histnext        /hn        play next station from history
/histprev        /hp        play previous station from history''',
        '/quit': 'PyRadio Remote Service exiting!\nCheers!',
        '/volumeup': 'Volume increased!',
        '/volumedown': 'Volume decreased!',
        '/start': 'Playback started!',
        '/stop': 'Playback stopped!',
        '/mute': 'Player mute toggled!',
        '/stations' : 'Listing stations!',
        '/next': 'Playing next station',
        '/histnext': 'Playing next station from history',
        '/previous': 'Playing previous station',
        '/histprev': 'Playing previous station from history',
        '/playlists': 'Listing playlists!',
        '/numbers': 'Playing specified station',
        '/number': 'Listing specified playlist',
        '/plst': 'Playing station from playlist',
        '/list': 'Listing stations from playlist',
        '/idle': 'Player is idle; operation not applicable...',
        '/error': 'Error in parameter',
        '/perm': 'Operation not permited (not in normal mode)',
        '/log': 'Stations logging toggled',
        '/tag': 'Station tagged (liked)',
    }

    def __init__(self, bind_ip, bind_port, commands):
        self._bind_ip = bind_ip
        if bind_ip.lower() == 'localhost':
            self._bind_ip = '127.0.0.1'
        elif bind_ip.lower() == 'lan':
            sys_ip = IPs()
            self._bind_ip = sys_ip.IPs[1]
        self._bind_port = bind_port
        self._commands = commands

    @property
    def ip(self):
        return self._bind_ip

    @property
    def port(self):
        return self._bind_port

    def start_remote_control_server(
            self,
            config,
            lists,
            sel,
            playlist_in_editor,
            can_send_command,
            error_func,
            dead_func,
    ):
        self._path = ''
        self.config = config
        self.lists = lists
        self.playlist_in_editor = playlist_in_editor
        self.can_send_command = can_send_command
        '''
        sel = (self.selection, self.playing)
        '''
        self.sel = sel
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self._bind_ip, self._bind_port))
        except (OSError, socket.error) as e:
            logger.error('Remote Control Server start error: "{}"'.format(e))
            server.close()
            error_func(e)
            return
        try:
            if PY2:
                server.listen(5)  # max backlog of connections
            else:
                server.listen()  # max backlog of connections
        except (OSError, socket.error) as e:
            logger.error('Remote Control Server error: "{}"'.format(e))
            server.close()
            error_func(e)
            return
        if logger.isEnabledFor(logging.INFO):
            logger.info('Remote Control Server listening on {}:{}'.format(self._bind_ip, self._bind_port))

        while True:
            try:
                client_sock, address = server.accept()
                request = client_sock.recv(1024)
            except socket.error as e:
                logger.error('Server accept error: "{}"'.format(e))
                dead_func(e)
                break
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Accepted connection from {}:{}'.format(address[0], address[1]))
            self.error = None
            self._handle_client_connection(client_sock, request)
            if self.error is not None:
                client_sock.close()
                dead_func(self.error)
                break
            if self._path == '/quit':
                client_sock.close()
                break
        server.close()
        if logger.isEnabledFor(logging.INFO):
            logger.info('Remote Control Server exiting...')

    def _handle_client_connection(self, client_socket, request):
        # logger.error ('Received {}'.format(request))
        # logger.error ('\n\nReceived {}'.format(request.decode('utf-8', 'replace')))
        try:
            rcv = request.decode('utf-8')
        except (OSError, socket.error) as e:
            client_socket.close()
            self.error = e
            return False
        except:
            rcv = 'Unicode Error'
        sp = rcv.split(' ')
        self._path = sp[1]

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Remote command: "{}"'.format(self._path))

        if self._path in ('/tag', '/g'):
            self._commands['/tag']()
            self._send_text(client_socket, self._text['/tag'])
        elif self._path in ('/like', '/l'):
            if self.sel()[1] > -1:
                self._commands['/like']()
                self._send_text(client_socket, self._text['/like'])
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/mute', '/m'):
            if self.sel()[1] > -1:
                self._commands['/mute']()
                self._send_text(client_socket, self._text['/mute'])
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/volumeup', '/vu'):
            if self.sel()[1] > -1:
                self._commands['/volumeup']()
                self._send_text(client_socket, self._text['/volumeup'])
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/volumedown', '/vd'):
            if self.sel()[1] > -1:
                self._commands['/volumedown']()
                self._send_text(client_socket, self._text['/volumedown'])
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path == '/quit':
            self._send_text(client_socket, self._text['/quit'])
        elif self._path == '/':
            self._send_text(client_socket, self._text['/'])
        elif self._path in ('/i', '/info'):
            if self.can_send_command():
                self._send_text(client_socket, self._info())
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/next', '/n'):
            if self.can_send_command():
                self._commands['/next']()
                self._send_text(client_socket, self._text['/next'])
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/previous', '/p'):
            if self.can_send_command():
                self._commands['/previous']()
                self._send_text(client_socket, self._text['/previous'])
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/histnext', '/hn'):
            if self.can_send_command():
                go_on = False
                llen = len(self.config().stations_history.items)
                l_item = self.config().stations_history.item
                if l_item == -1 or llen == 0:
                    self._send_text(client_socket, 'No items in history!')
                elif l_item + 1 < llen:
                    go_on = True
                if go_on:
                    self._commands['/histnext']()
                    self._send_text(client_socket, self._text['/histnext'])
                else:
                    self._send_text(client_socket, 'Already at last history item!')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/histprev', '/hp'):
            if self.can_send_command():
                go_on = True
                llen = len(self.config().stations_history.items)
                l_item = self.config().stations_history.item
                logger.error('\n\nitems = {0}, item = {1}\n\n'.format(llen, l_item))
                if l_item == -1 or llen == 0:
                    self._send_text(client_socket, 'No items in history!')
                    go_on = False
                elif l_item == 0:
                    go_on = False
                if go_on:
                    self._commands['/histprev']()
                    self._send_text(client_socket, self._text['/histprev'])
                else:
                    self._send_text(client_socket, 'Already at first history item!')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/toggle', '/t'):
            if self.can_send_command():
                if self.sel()[1] > -1:
                    self._commands['/stop']()
                    self._send_text(client_socket, self._text['/stop'])
                else:
                    self._commands['/start']()
                    self._send_text(client_socket, self._text['/start'])
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path.startswith('/st/') or \
                self._path.startswith('/stations/'):
            if self.can_send_command():
                ret = self._parse()
                if ret is None:
                    self._send_text(client_socket, self._text['/error'])
                else:
                    has_error = False
                    if ret == '/stations':
                        self._send_text(client_socket, self._list_stations())
                    else:
                        try:
                            ret = int(ret)
                        except (ValueError, TypeError):
                            self._send_text(client_socket, self._text['/error'])
                            has_error = True
                        if not has_error:
                            # ret = ret -1 if ret > 0 else 0
                            if ret < 0:
                                ret = 0
                            self._commands['/jump'](ret)
                            self._send_text(client_socket, ' Playing station Id: {}'.format(ret))
                    has_error = False
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path.startswith('/playlists') or \
                self._path.startswith('/pl') or \
                self._path == '/stations' or \
                self._path == '/st':
            if  ',' in self._path:
                sp = self._path.split('/')
                if ',' not in sp [-1]:
                    self._send_text(client_socket, self._text['/error'])
                else:
                    if sp[1] not in ('playlists', 'pl'):
                        self._send_text(client_socket, self._text['/error'])
                    else:
                        # get the numbers
                        pl, st = self._get_numbers(sp[-1])
                        if pl is None:
                            self._send_text(client_socket, self._text['/error'])
                        else:
                            go_on = True
                            try:
                                playlist_name = self.lists()[1][-1][pl][0]
                            except IndexError:
                                self._send_text(client_socket, 'Error: Playlist not found (id={})'.format(pl+1))
                                go_on = False
                            if go_on:
                                p_name = basename(self.playlist_in_editor()[:-4])
                                if p_name == playlist_name:
                                    # play station from current playlist
                                    self._commands['/jump'](st+1)
                                    self._send_text(
                                        client_socket,
                                        'Playing station "{0}" (id={1}) from playlist "{2}" (id={3})'.format(
                                            self.lists()[0][-1][st][0],
                                            st+1,
                                            p_name,
                                            pl+1
                                        )
                                    )
                                else:
                                    # need to load a new playlist
                                    if self.config().dirty_playlist:
                                        self._send_text(
                                            client_socket,
                                            'Current playlist not saved; cannot load other playlist...'
                                        )
                                    else:
                                        in_file, playlist_stations = self.config().read_playlist_for_server(playlist_name)
                                        if playlist_stations:
                                            if st < len(playlist_stations):
                                                item = [playlist_name, playlist_stations[st], st]
                                                if logger.isEnabledFor(logging.DEBUG):
                                                    logger.debug('item = {}'.format(item))
                                                # radio.py 8762
                                                self._commands['open_history'](in_file, item)
                                                self._send_text(
                                                    client_socket,
                                                    'Playing station "{0}" (id={1}) from playlist "{2}" (id={3})'.format(
                                                        playlist_stations[st],
                                                        st+1,
                                                        playlist_name,
                                                        pl+1
                                                    )
                                                )
                                            else:
                                                self._send_text(
                                                    client_socket,
                                                    'Error: Requested station (id={0}) not found in playlist "{1}" (id={2})'.format(
                                                        st+1, playlist_name, pl+1,
                                                    )
                                                )
                                        else:
                                            self._send_text(
                                                client_socket,
                                                'Error opening playlist "{0}" (id={1})'.format(
                                                    playlist_name, pl+1
                                                )
                                            )

            else:
                ret = self._parse()
                if ret is None:
                    self._send_text(client_socket, self._text['/error'])
                elif ret.startswith('/'):
                    if ret == '/stations':
                        self._send_text(client_socket, self._list_stations())
                    elif ret == '/playlists':
                        self._send_text(client_socket, self._list_playlists())
                    else:
                        self._send_text(client_socket, self._text[ret])

                else:
                    go_on = True
                    try:
                        ret = int(ret) - 1
                    except (ValueError, TypeError):
                        go_on = False
                        self._send_text(client_socket, self._text['/error'])
                    if go_on:
                        try:
                            playlist_name = self.lists()[2][-1][ret][0]
                        except IndexError:
                            self._send_text(client_socket, 'Error: Playlist not found (id={})'.format(ret+1))
                            go_on = False
                        if go_on:
                            in_file, out = self.config().read_playlist_for_server(
                                playlist_name
                            )
                            if out:
                                self._send_text(
                                    client_socket,
                                    self._list_stations(playlist_name, out)
                                )

                            else:
                                self._send_text(client_socket, 'Error reading playlist: "{}"'.format(playlist_name))
        else:
            self._send_text(client_socket, self._text['/error'])

        # if self._path == '/quit':
        #     _send_html(client_socket, 'Server has shut down!!!')
        # else:
        #     _send_html(client_socket, 'path: {}\n\nYES!!!'.format(self._path))
        client_socket.close()
        return True

    def _send_text(self, client_socket, msg):
        f_msg = msg + '\n'
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Content-Length: {}
Server: PyRadio

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Content-Length: {}
Server: PyRadio

'''.format(len(b_msg)).encode('utf-8')
        try:
            client_socket.sendall(txt + b_msg)
        except socket.error as e:
            self.error = e

    def _send_html(self, client_socket, msg):
        client_socket.send(
            self._html.format(msg).encode('utf-8')
        )

    def _get_numbers(self, comma):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('parsing: "{}"'.format(comma))
        sp = comma.split(',')
        for i in (0,1):
            try:
                num = int(sp[i])
                sp[i] = num
            except (IndexError, ValueError, TypeError):
                return None, None
        for i in (0,1):
            sp[i] -= 1
            if sp[i] < 0:
                return None, None
        return sp

    def _parse(self):
        sp = self._path.split('/')
        sp = [i for i in sp if i]
        if len(sp) == 1:
            if sp[0] in ('stations', 'st'):
                return '/stations'
            elif sp[0] in ('playlists', 'pl'):
                return '/playlists'
            else:
                return None
        elif len(sp) == 2:
            if sp[0] in ('stations', 'st'):
                if sp[1] in ('next', 'n'):
                    return '/next'
                elif sp[1] in ('previous', 'p'):
                    return '/previous'
                elif sp[1] in ('histnext', 'hn'):
                    return '/histnext'
                elif sp[1] in ('histprev', 'hp'):
                    return '/histprev'
                else:
                    ''' do i have a number? '''
                    try:
                        x = int(sp[1])
                    except ValueError:
                        return None
                    return sp[1]
            elif sp[0] in ('playlists', 'pl'):
                ''' do i have a number? '''
                nsp = sp[1].split(',')
                if len(nsp) == 1:
                    try:
                        x = int(nsp[0])
                    except ValueError:
                        return None
                    return sp[1]
                else:
                    return None
            else:
                return None
        else:
            return None

    def close_server(self):
        # create socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        except socket.error as e:
            s.close()
            return False, e

        try:
            s.connect((self._bind_ip, self._bind_port))
            request = "GET /quit HTTP/1.0\n\n".encode('utf-8')
            s.sendall(request)
        except socket.error as e:
            s.close()
            return False, e

        # Receive data
        try:
            reply = s.recv(4096)
        except socket.error as e:
            s.close()
            return False, e
        s.close()
        return True, None

    def _list_stations(
        self,
        playlist_name=None,
        stations=None
    ):
        out = []
        if stations is None:
            for n in self.lists()[0][-1]:
                out.append(n[0])
            p_name = basename(self.playlist_in_editor()[:-4])
        else:
            out = stations
            p_name = playlist_name
        pad = len(str(len(out)))
        pad_str = '{:' + str(pad) + '}. '

        for i in range(0, len(out)):
            tok = '  '
            if stations is None:
                if i == self.sel()[0] and i == self.sel()[1]:
                    ''' selected and playing '''
                    tok = '+>'
                elif i == self.sel()[0]:
                    ''' selected '''
                    tok = '> '
                elif i == self.sel()[1]:
                    ''' playing '''
                    tok = '+ '
                out[i] = tok + pad_str.format(i+1) + out[i]
            else:
                out[i] = tok + pad_str.format(i+1) + out[i]
        if stations is None:
            return 'Stations List for Playlist: "' + p_name + '"\n' +  '\n'.join(out) + '\nFirst column\n  [> ]: Selected, [+ ]: Playing, [+>]: Both'
        else:
            return 'Stations List for Playlist: "' + p_name + '"\n' +  '\n'.join(out)

    def _list_playlists(self):
        # logger.error('playlist_in_editor = "{}"'.format(self.playlist_in_editor()))
        pl = basename(self.playlist_in_editor()[:-4])
        out = []
        for n in self.lists()[1][-1]:
            out.append(n[0])
        pad = len(str(len(out)))
        pad_str = '{:' + str(pad) + '}. '

        for i in range(0, len(out)):
            tok = '  '
            if out[i] == pl:
                tok = '> '
            out[i] = tok + pad_str.format(i+1) + out[i]

        return 'Available Playlists\n' + '\n'.join(out) + '\nFirst column:\n  [>]: Playlist loaded'

    def _info(self):
        out = []
        out.append('Playlist: "' + basename(self.playlist_in_editor()[:-4]) + '"')
        selection = self.sel()[0]
        playing = self.sel()[1]
        if playing == -1:
            out.append('Player: ' + 'Idle')
        else:
            out.append('Player: ' + 'In playback')
            out.append('  Station (id={0}): "{1}"'.format(playing+1, self.lists()[0][-1][playing][0]))
        out.append('Selection (id={0}): "{1}"'.format(selection, self.lists()[0][-1][selection][0]))

        return '\n'.join(out)

    def _read_playlist(self, a_playlist):
        pass

if __name__ == '__main__':
    x = PyRadioServer('192.168.122.4', 9998)
    x.start_remote_control_server(lambda: False)
