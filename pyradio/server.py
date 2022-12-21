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

    _html = '''<!DOCTYPE html>
<html lang="en">
    <head>
        <title>PyRadio Remote Control</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link rel="stylesheet" href="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/css/bootstrap.min.css">
        <script src="https://ajax.googleapis.com/ajax/libs/jquery/3.6.1/jquery.min.js"></script>
        <script src="https://maxcdn.bootstrapcdn.com/bootstrap/3.4.1/js/bootstrap.min.js"></script>
        <style>
html, body, td, a, a:hover, a:visited{color: #333333;}
.btn {margin: 1px; width: 80px;}
        </style>
    <link rel="shortcut icon" href="https://raw.githubusercontent.com/coderholic/pyradio/master/devel/pyradio.ico"
    </head>
    <body class="container-fluid">


        <div class="row text-center" style="background: green; color: white; padding-bottom: 15px; display: none;">
            <h2>PyRadio Remote Control</h2>
        </div>
        <div id="title_container" class="row" style="margin-top: 40px;">
            <div class="col-lg-2">
            </div>
            <div class="col-lg-8 col-xs-12">
                <div id="song_title" class="alert alert-info text-center">
                </div>
                <div>
                </div>
            </div>
            <div class="col-lg-2">
            </div>
        </div>
        <div class="row" style="margin-top: 20px;">
            <div class="col-xs-4 col-lg-3">
                <div class="text-center">
                    <button onclick="window.location.href='http://|IP|/html/vu';" type="button" class="btn btn-primary">Volume<br>Up</button>
                    <button onclick="window.location.href='http://|IP|/html/vd';" type="button" class="btn btn-primary">Vulume<br>Down</button>
                    <button onclick="window.location.href='http://|IP|/html/m';" type="button" class="btn btn-danger">Mute<br>Player</button>
                    <!--<button onclick="title_on_off();" type="button" class="btn btn-default">Title<br>On / Off</button>-->
                </div>
            </div>
            <div class="col-xs-4 col-lg-5">
                <div class="text-center">
                    <button onclick="window.location.href='http://|IP|/html/n';" type="button" class="btn btn-warning">Play<br>Next</button>
                    <button onclick="window.location.href='http://|IP|/html/p';" type="button" class="btn btn-warning">Play<br>Previous</button>
                    <button onclick="window.location.href='http://|IP|/html/hn';" type="button" class="btn btn-success">Play Hist.<br> Next</button>
                    <button onclick="window.location.href='http://|IP|/html/hp';" type="button" class="btn btn-success">Play Hist.<br>Previous</button>
                    <button onclick="window.location.href='http://|IP|/html/t';" type="button" class="btn btn-danger">Toggle<br>Playback</button>
                </div>
            </div>
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button onclick="window.location.href='http://|IP|/html/st';" type="button" class="btn btn-success">Stations<br>List</button>
                    <button onclick="window.location.href='http://|IP|/html/pl';" type="button" class="btn btn-primary">Show<br>Playlists</button>
                    <button onclick="window.location.href='http://|IP|/html/i';" type="button" class="btn btn-danger">System<br>Info</button>
                    <button onclick="window.location.href='http://|IP|/html/g';" type="button" class="btn btn-warning">Toggle<br>Titles Log</button>
                    <button onclick="window.location.href='http://|IP|/html/l';" type="button" class="btn btn-info">Like<br>Title</button>
                </div>
            </div>
        </div>


        <div id="message" class="row" style="margin-top: 40px;">
            <div class="col-lg-2">
            </div>
            <div class="col-lg-8 col-xs-12">

                <div class="alert |ALERT_TYPE|">
                    |ALERT|
                </div>
                <div>
                    |CONTENT|
                </div>
            </div>
            <div class="col-lg-2">
            </div>
        </div>


    <script>
    var tit_counter = 0;
    function title_on_off() {
        var element = document.getElementById("title_container");
        if ( element.style.display == "none"){
            refresh();
            tit_counter = setInterval(refresh, 1000);
            element.style.display = "block";
        } else {
            element.style.display = "none";
            clearInterval(tit_counter);
        }
    }

    function refresh() {
        $.get('/html/title', function(result) {
        $("#song_title").html(result);
    });
    }

    function refresh_handler() {
        refresh();
        tit_counter = setInterval(refresh, 1000);
    }

    // $(document).ready(refresh_handler);
    </script>
    </body>
</html>
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
        '/like': 'Station tagged (liked)',
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
        self._html_data = {
            '|ALERT|': '',
            '|ALERT_TYPE|': '',
            '|CONTENT|': '',
            '|IP|': '{0}:{1}'.format(self._bind_ip, self._bind_port)
        }

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
            muted,
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
        self.muted = muted
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((self._bind_ip, self._bind_port))
        except (OSError, socket.error) as e:
            if logger.isEnabledFor(logger.ERROR):
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
            if logger.isEnabledFor(logger.ERROR):
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
                if logger.isEnabledFor(logger.ERROR):
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

        self._is_html = True if self._path.startswith('/html') else False
        logger.error('path = {}'.format(self._path))
        if self._path.startswith('/html'):
            self._is_html = True
            self._path = self._path[5:]
        else:
            self._is_html = False
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('URL path = {}'.format(self._path))
        if self._path == '/title':
            title = self._commands['/title']()
            self._send_raw(client_socket, title)
        elif self._path == '/favicon.ico':
            pass
            #self._html_data['|ALERT|'] = ''
            #self._html_data['|ALERT_TYPE|'] = ''
            #self._html_data['|CONTENT|'] = ''
            #logger.error('html_data = {}'.format(self._html_data))
            #self._send_html(client_socket)
        elif self._path in ('/like', '/g'):
            self._commands['/like']()
            self._send_text(client_socket, self._text['/like'], alert_type='alert-success')
        elif self._path in ('/like', '/l'):
            if self.sel()[1] > -1:
                self._commands['/like']()
                self._send_text(client_socket, self._text['/like'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/mute', '/m'):
            if self.sel()[1] > -1:
                self._commands['/mute']()
                if self.muted():
                    self._send_text(client_socket, 'Player muted!', alert_type='alert-success')
                else:
                    self._send_text(client_socket, 'Player unmuted!', alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/volumeup', '/vu'):
            if self.sel()[1] > -1:
                if self.muted():
                    self._send_text(client_socket, 'Player is muted!', alert_type='alert-danger')
                else:
                    self._commands['/volumeup']()
                    self._send_text(client_socket, self._text['/volumeup'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path in ('/volumedown', '/vd'):
            if self.sel()[1] > -1:
                if self.muted():
                    self._send_text(client_socket, 'Player is muted!', alert_type='alert-danger')
                else:
                    self._commands['/volumedown']()
                    self._send_text(client_socket, self._text['/volumedown'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/idle'])
        elif self._path == '/quit':
            self._send_text(client_socket, self._text['/quit'])
        elif self._path in  ('', '/'):
            if self._is_html:
                self._send_text(client_socket, '', alert_type='')
            else:
                self._send_text(client_socket, self._text['/'], alert_type='')
        elif self._path in ('/i', '/info'):
            if self.can_send_command():
                self._send_text(client_socket, self._info())
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/next', '/n'):
            if self.can_send_command():
                self._commands['/next']()
                self._send_text(client_socket, self._text['/next'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/previous', '/p'):
            if self.can_send_command():
                self._commands['/previous']()
                self._send_text(client_socket, self._text['/previous'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/histnext', '/hn'):
            if self.can_send_command():
                go_on = False
                llen = len(self.config().stations_history.items)
                l_item = self.config().stations_history.item
                if l_item == -1 or llen == 0:
                    self._send_text(client_socket, 'No items in history!', alert_type='alert-danger')
                elif l_item + 1 < llen:
                    go_on = True
                if go_on:
                    self._commands['/histnext']()
                    self._send_text(client_socket, self._text['/histnext'], alert_type='alert-success')
                else:
                    self._send_text(client_socket, 'Already at last history item!')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path in ('/histprev', '/hp'):
            if self.can_send_command():
                go_on = True
                llen = len(self.config().stations_history.items)
                l_item = self.config().stations_history.item
                if l_item == -1 or llen == 0:
                    self._send_text(client_socket, 'No items in history!', alert_type='alert-danger')
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
                    self._send_text(client_socket, self._text['/stop'], alert_type='alert-success')
                else:
                    self._commands['/start']()
                    self._send_text(client_socket, self._text['/start'], alert_type='alert-success')
            else:
                self._send_text(client_socket, self._text['/perm'])
        elif self._path.startswith('/st/') or \
                self._path.startswith('/stations/'):
            if self.can_send_command():
                ret = self._parse()
                if ret is None:
                    self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
                else:
                    has_error = False
                    if ret == '/stations':
                        if self._is_html:
                            self._send_text(
                                client_socket,
                                msg='',
                                alert_type='',
                                content=self._format_html_table(
                                    self._list_stations(html=True), 0,
                                    sel=self.sel()[1]
                                ),
                                put_script=True
                            )
                        else:
                            self._send_text(client_socket, self._list_stations())
                    else:
                        try:
                            ret = int(ret)
                        except (ValueError, TypeError):
                            self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
                            has_error = True
                        if not has_error:
                            # ret = ret -1 if ret > 0 else 0
                            if ret < 0:
                                ret = 0
                            self._commands['/jump'](ret)
                            if self._is_html:
                                self._send_text(client_socket, ' Playing station: <b>{}</b>'.format(self.lists()[0][-1][ret-1][0]))
                            else:
                                self._send_text(client_socket, ' Playing station: {}'.format(self.lists()[0][-1][ret-1][0]))
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
                    self._send_text(client_socket, self._text['/error'], alert-danger)
                else:
                    if sp[1] not in ('playlists', 'pl'):
                        self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
                    else:
                        # get the numbers
                        pl, st = self._get_numbers(sp[-1])
                        if pl is None:
                            self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
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
                                    if self._is_html:
                                        self._send_text(
                                            client_socket,
                                            'Playing station <b>{0}</b> from playlist <i>{1}</i>'.format(
                                                self.lists()[0][-1][st][0],
                                                p_name
                                            )
                                        )
                                    else:
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
                                                if self._is_html:
                                                    self._send_text(
                                                        client_socket,
                                                        'Playing station <b>{0}</b> from playlist <i>{1}</i>'.format(
                                                            playlist_stations[st],
                                                            playlist_name
                                                        )
                                                    )
                                                else:
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
                    self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
                elif ret.startswith('/'):
                    if ret == '/stations':
                        if self._is_html:
                            self._send_text(
                                client_socket,
                                msg='',
                                alert_type='',
                                content=self._format_html_table(
                                    self._list_stations(html=True), 0,
                                    sel=self.sel()[1]
                                ),
                                put_script=True
                            )
                        else:
                            self._send_text(client_socket, self._list_stations())
                    elif ret == '/playlists':
                        if self._is_html:
                            self._send_text(
                                client_socket,
                                msg='',
                                alert_type='',
                                content=self._format_html_table(
                                    self._list_playlists(html=True), 1,
                                    sel=self._get_playlist_id(basename(self.playlist_in_editor()[:-4]))
                                ),
                                put_script=True
                            )
                        else:
                            self._send_text(client_socket, self._list_playlists())
                    else:
                        self._send_text(client_socket, self._text[ret])

                else:
                    go_on = True
                    try:
                        ret = int(ret) - 1
                    except (ValueError, TypeError):
                        go_on = False
                        self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')
                    if go_on:
                        try:
                            playlist_name = self.lists()[2][-1][ret][0]
                        except IndexError:
                            self._send_text(client_socket, 'Error: Playlist not found (id={})'.format(ret+1), alert_type='alert-danger')
                            go_on = False
                        if go_on:
                            in_file, out = self.config().read_playlist_for_server(
                                playlist_name
                            )
                            if out:
                                if self._is_html:
                                    self._send_text(
                                        client_socket,
                                        msg='',
                                        alert_type='',
                                        content=self._format_html_table(
                                            self._list_stations(stations=out, html=True),
                                            index=2,
                                            playlist_index=ret,
                                        ),
                                        put_script=True
                                    )
                                else:
                                    self._send_text(
                                        client_socket,
                                        self._list_stations(playlist_name, out)
                                    )
                            else:
                                if self._is_html:
                                    self._send_text(client_socket, 'Error reading playlist: <b>{}</b>'.format(playlist_name), alert_type='alert-danger')
                                else:
                                    self._send_text(client_socket, 'Error reading playlist: "{}"'.format(playlist_name), alert_type='alert-danger')
        else:
            self._send_text(client_socket, self._text['/error'], alert_type='alert-danger')

        # if self._path == '/quit':
        #     _send_html(client_socket, 'Server has shut down!!!')
        # else:
        #     _send_html(client_socket, 'path: {}\n\nYES!!!'.format(self._path))
        client_socket.close()
        return True

    def _send_raw(self, client_socket, msg):
        f_msg = msg + '\n'
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=utf-8
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

    def _send_text(self, client_socket,
                   msg, alert_type='alert-info',
                   content='', put_script=False
    ):
        if self._is_html:
            self._html_data['|ALERT|'] = msg
            self._html_data['|ALERT_TYPE|'] = alert_type
            self._html_data['|CONTENT|'] = content
            self._send_html(client_socket, put_script=put_script)
            return
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

    def _send_html(self, client_socket, msg=None, put_script=False):
        f_msg = self._html + '\n'
        for n in self._html_data.keys():
            f_msg = f_msg.replace(n, self._html_data[n])
        if put_script:
            f_msg = self._insert_html_script(f_msg)
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Content-Length: {}
Server: PyRadio

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Content-Length: {}
Server: PyRadio

'''.format(len(b_msg)).encode('utf-8')
        try:
            client_socket.sendall(txt + b_msg)
        except socket.error as e:
            self.error = e

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

    def _get_playlist_id(self, a_playlist):
        try:
            return [x[0] for x in self.lists()[1][-1]].index(a_playlist)
        except ValueError:
            return -1

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
        stations=None,
        html=False
    ):
        out = []
        if stations is None:
            for n in self.lists()[0][-1]:
                out.append(n[0])
            p_name = basename(self.playlist_in_editor()[:-4])
        else:
            out = stations
            p_name = playlist_name
        if html:
            return out

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

    def _list_playlists(self, html=False):
        # logger.error('playlist_in_editor = "{}"'.format(self.playlist_in_editor()))
        pl = basename(self.playlist_in_editor()[:-4])
        out = []
        for n in self.lists()[1][-1]:
            out.append(n[0])
        if html:
            return out

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
        if self._is_html:
            out.append('<b>Playlist:</b> ' + basename(self.playlist_in_editor()[:-4]) + '')
        else:
            out.append('Playlist: "' + basename(self.playlist_in_editor()[:-4]) + '"')
        selection = self.sel()[0]
        playing = self.sel()[1]
        if playing == -1:
            if self._is_html:
                out.append('<b>Player:</b> ' + 'Idle')
            else:
                out.append('Player: ' + 'Idle')
        else:
            mut = ' (muted)' if self.muted() else ''
            if self._is_html:
                out.append('<b>Player:</b> ' + 'In playback' + mut)
                out.append('<span style="padding-left: 1em; font-weight: bold;">  Station:</span> {}'.format(self.lists()[0][-1][playing][0]))
            else:
                out.append('Player: ' + 'In playback' + mut)
                out.append('  Station (id={0}): "{1}"'.format(playing+1, self.lists()[0][-1][playing][0]))
        if self._is_html:
            out.append('<b>Selection:</b> {}'.format(self.lists()[0][-1][selection][0]))
            for i in range(0, len(out)):
                out[i] += '<br>'
        else:
            out.append('Selection (id={0}): "{1}"'.format(selection, self.lists()[0][-1][selection][0]))

        return '\n'.join(out)

    def _insert_html_script(self, msg):
        script = '''        <script>
            $(document).ready(function(){
                $("#myInput").on("keyup", function() {
                    var value = $(this).val().toLowerCase();
                    $("#myTable tr").filter(function() {
                        $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
                    });
                });
            });
        </script>
    </body>'''
        return msg.replace('</body>', script)

    def _format_html_table(
            self, in_list, index,
            playlist_index=None, sel=-1
        ):
        '''
        format html table for |CONTENT|

        Parameters
        ==========
        in_list         list of items
        self            selected item
        index           type of output (stations / playlist) and URL formatter
        playlist_index  playist index (only valid if index == 2)
        '''
        head_captions = (
            'Stations (current playlist)',
            'List of Playlists',
            'Stations from Playlist: "{}"'.format(self.lists()[1][-1][playlist_index][0]) if playlist_index else ''
        )
        url = ['/html/st/{}', '/html/pl/{}', '/html/pl/{0},{1}']
        head = '''                    <h5>Search field</h5>
                    <input class="form-control" id="myInput" type="text" placeholder="Type to search for a station...">
                    <br>
                    <table class="table table-bordered table-hover">
                        <thead>
                            <tr class="btn-success">
                                <td colspan="2" style="color: white; font-weight: bolder;">{}</td>
                            </tr>
                        </thead>
                        <tbody id="myTable">
'''.format(head_captions[index])
        out = []
        for i, n in enumerate(in_list):
            if sel == i:
                out.append('                            <tr class="btn-warning">')
            else:
                out.append('                            <tr>')
            out.append('                                <td class="text-right">{}</td>'.format(i+1))
            if index < 2:
                t_url = 'http://|IP|' + url[index].format(i+1)
            else:
                t_url = 'http://|IP|' + url[2].format(playlist_index+1, i+1)
            out.append('                           <td id="' + str(i+1) + '"><a href="' + t_url + '">' + n + '</a>')
            out.append('                                </td>')
            out.append('                            </tr>')
        out.append('                        </tbody>')
        out.append('                    </table>')
        return head + '\n' + '\n'.join(out)

    def _read_playlist(self, a_playlist):
        pass
