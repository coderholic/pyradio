# https://stackoverflow.com/questions/10114224/how-to-properly-send-http-response-with-python-using-socket-library-only
import socket
import logging
from os.path import basename
from sys import platform, version_info
import requests
from time import sleep

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
    _filter_string = '''
                    <script>
                    $(document).ready(function(){
                      $("#myInput").on("keyup", function() {
                          var value = $(this).val().toLowerCase();
                          $("#myTable tr").filter(function() {
                                $(this).toggle($(this).text().toLowerCase().indexOf(value) > -1)
                              });
                        });
                    });
                    </script>
'''

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
.btn {margin: 1px; width: 80px; border-radius: 6px;}
#the_blocking_box {
    position: absolute;
    top: 0;
    left:0;
    z-index: 9998;
    width: 100%;
    height: 100%;
    overflow: hiddden;
    display: none;
    }
        </style>
    <link rel="shortcut icon" href="https://raw.githubusercontent.com/coderholic/pyradio/master/devel/pyradio.ico"
    </head>
    <body class="container-fluid">
        <!--
        <div id="the_blocking_box">
        </div>
        -->
        <div class="row text-center" onclick="js_refresh_page();" style="background: green; color: white; padding-bottom: 15px;">
            <h2>PyRadio Remote Control</h2>
        </div>
        <div id="title_container" class="row" style="margin: 3px; margin-top: 15px;>
            <div class="col-xs-12">
                <div id="song_title" class="alert alert-info text-center">
                <b>No data!</b>
                </div>
            </div>
        </div>
        <div id="all_buttons" class="row">
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button onclick="js_send_simple_command('/html/next', 1500);" type="button" class="btn btn-warning">Play<br>Next</button>
                    <button onclick="js_send_simple_command('/html/previous', 1500);" type="button" class="btn btn-warning">Play<br>Previous</button>
                    <button onclick="js_send_simple_command('/html/histnext', 1500);" type="button" class="btn btn-success">Play Hist.<br> Next</button>
                    <button onclick="js_send_simple_command('/html/histprev', 1500);" type="button" class="btn btn-success">Play Hist.<br>Previous</button>
                    <button onclick="js_send_simple_command('/html/toggle', 1500);" type="button" class="btn btn-danger">Toggle<br>Playback</button>
                </div>
            </div>
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button id="vu" onclick="js_send_simple_command('/html/volumeup', 500);" type="button" class="btn btn-primary">Volume<br>Up</button>
                    <button id="vd" onclick="js_send_simple_command('/html/volumedown', 500);" type="button" class="btn btn-primary">Vulume<br>Down</button>
                    <button id="vs" onclick="js_send_simple_command('/html/volumesave', 1500);" type="button" class="btn btn-success">Save<br>Volume</button>
                    <button id="mute" onclick="js_send_simple_command('/html/mute', 500);" type="button" class="btn btn-warning">Mute<br>Player</button>
                </div>
            </div>
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button onclick="js_send_simple_command('/html/st', 0);" type="button" class="btn btn-success">Stations<br>List</button>
                    <button onclick="js_send_simple_command('/html/pl', 0);" type="button" class="btn btn-primary">Show<br>Playlists</button>
                    <button onclick="js_send_simple_command('/html/info', 0);" type="button" class="btn btn-danger">System<br>Info</button>
                    <button onclick="js_send_simple_command('/html/log', 1500);" type="button" class="btn btn-warning">Toggle<br>Titles Log</button>
                    <button id="like" onclick="js_send_simple_command('/html/like', 1500);" type="button" class="btn btn-info">Like<br>Title</button>
                </div>
            </div>
        </div>


        <div id="msg" class="row" style="margin-top: 40px;">
            <div class="col-lg-4">
            </div>
            <div id="msg_text" class="col-lg-4 col-xs-12">
            </div>
            <div class="col-lg-4">
            </div>
        </div>

    <script>
    var error_count = 0;
    var msg_timeout = 0;
    var url_to_reload = "";
    var last_title = "";

    function js_refresh_page(){
        window.location.href = url_to_reload;
    }

    ////////////////////////////////////////////////////////////////////
    //                     SSE implementation                         //
    ////////////////////////////////////////////////////////////////////

    let eventSource = new EventSource("/html/title");

    eventSource.addEventListener("/html/title", (event) => {
        // console.log("event.data:", event.data);
        js_set_title("#song_title", event.data);
        error_count = 0;
        if ( event.data.includes("Player is stopped!") || event.data.includes("Connecting to: ") || event.data.includes("Failed to connect to: ") || event.data.includes("Player terminated abnormally") ){
            js_disable_buttons_on_stopped(true);
        } else {
            js_disable_buttons_on_stopped(false);
        }
    });

    eventSource.onerror = function(m) {
        error_count++;
        if ( error_count > 5 ) {
            js_close_sse();
        }
    };

    function js_close_sse(){
        $("#song_title").html("<b>Connection to Server lost!</b>");
        js_hide_element("all_buttons");
        js_hide_element("msg");
        eventSource.close();
    }

    ////////////////////////////////////////////////////////////////////

    function js_send_simple_command(the_command, the_timeout){
        $.get(the_command, function(result){
            // console.log(the_command, result, typeof result);
            //
            //  Check for html to display
            //
            // console.log("result:", result);
            if ( result.length < 5 ) {
                // console.log("Rejected: " + result)
                return;
            }
            if ( result.startsWith("retry: ") ) {
                // if a title reply gets here,
                // I have to see where it came from
                if ( the_command == "/html/init" ) {
                    var x = result.indexOf("<b>");
                    var title = result.slice(x, result.length-1);
                    js_set_title("#song_title", title);
                    return;
                } else if ( the_command == "/html/toggle" ) {
                    result = '<div class="alert alert-success">Playback <b>toggled!</b></div>'
                } else if ( the_command == "/html/mute"  ) {
                    result = '<div class="alert alert-success">Player mute state <b>toggled!</b></div>'
                } else {
                    //console.log("next or previous command!");
                    var x = result.indexOf("Connecting");
                    //console.log("x:", x);
                    if ( x > -1 ){
                        var st = result.slice(x, result.length-1);
                        result = st.replace("Connecting to:", '<div class="alert alert-success">Playing <b>') + "</div>";
                        //console.log("st:", st);
                        //console.log("result:", result);
                    } else {
                        return;
                    }
                }
                // console.log("Rejected: " + result)
            }
            // console.log('Accepted: ' + result)
            clearTimeout(msg_timeout);
            js_set_title("#msg_text", result, the_command);
            js_show_element("msg");
            if (the_timeout > 0){
                msg_timeout = setTimeout(js_hide_msg, the_timeout);
            }
            if ( the_command == "/html/mute" ) {
                js_fix_muted();
            }
            // console.log("the_command:", the_command)
        });
    }

    function js_set_title(a_tag, a_title, the_command=''){
        // console.log("    ", last_title);
        // console.log("a_title.length < last_title.length :", a_title.length < last_title.length);
        // console.log("last_title.includes(a_title) :", last_title.includes(a_title));
        if ( a_tag === "#song_title" ){
            if ( a_title.length < last_title.length && last_title.includes(a_title.substring(0, a_title.length - 4)) ){
                // console.log("----", a_title)
                return;
            }
        } else if ( a_tag === "#msg_text" ){
            if ( the_command !== "" && the_command != "/html/info" ) {
                a_title = a_title.replace("alert ", "text-center alert ");
            }
        }

        // console.log("++++", a_title)
        $(a_tag).html(a_title);
        if ( a_tag === "#song_title" ){
            last_title = a_title;
            // console.log("set ", last_title)
        }
    }

    function js_fix_stopped(){
        const getStopped = async () => {
            const response = await fetch("/html/is_stopped");
            const data = await response.text();


            let b_id = ["vu", "vd", "vs", "mute", "like"];
            for (let i in b_id) {
                // console.log("async:", data);
                if ( data == 0 ){
                    js_disable_buttons_on_stopped(true);
                } else {
                    js_disable_buttons_on_stopped(false);
                }
            }
        }
        getStopped();
    }

    function js_disable_buttons_on_stopped(enable){
        let b_id = ["vu", "vd", "vs", "mute", "like"];
        for (let i in b_id) {
            var element = document.getElementById(b_id[i]);
            // console.log("async:", data);
            element.disabled = enable;
        }
    }

    function js_fix_muted(){
        const getMuted = async () => {
            const response = await fetch("/html/is_muted");
            const data = await response.text();

            // console.log("async:", data);
            var element = document.getElementById("mute");
            if ( data == 0 ){
                element.className = "btn btn-danger";
                element.innerHTML = "Unmute<br>Player"
            } else {
                element.className = "btn btn-warning";
                element.innerHTML = "Mute<br>Player"
            }
        }
        getMuted();
    }

    function js_hide_msg(){
        var element = document.getElementById("msg");
        element.style.display = "none";
    }

    function js_show_element(the_element){
        var element = document.getElementById(the_element);
        element.style.display = "block";
    }

    function js_hide_element(the_element){
        var element = document.getElementById(the_element);
        element.style.display = "none";
    }

    function js_init(){
        url_to_reload = window.location.href;
        js_fix_muted();
        js_fix_stopped();
        setTimeout(js_init_title, 2000);
    }

    function js_init_title(){
        js_send_simple_command("/html/init",0);
    }

    $(document).ready(js_init);
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
/vulumesave      /vs        save volume
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
        '/perm': 'Operation not permitted (not in normal mode)',
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
            song_title,
    ):
        self._path = ''
        self.config = config
        self.lists = lists
        self.playlist_in_editor = playlist_in_editor
        self.can_send_command = can_send_command
        self.song_title = song_title
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
                self.client_socket, address = server.accept()
                request = self.client_socket.recv(1024)
            except socket.error as e:
                if logger.isEnabledFor(logger.ERROR):
                    logger.error('Server accept error: "{}"'.format(e))
                dead_func(e)
                break
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Accepted connection from {}:{}'.format(address[0], address[1]))
            self.error = None
            self._handle_client_connection(request)
            if self.error is not None:
                self.client_socket.close()
                dead_func(self.error)
                break
            if self._path == '/quit':
                self.client_socket.close()
                break
        server.close()
        if logger.isEnabledFor(logging.INFO):
            logger.info('Remote Control Server exiting...')

    def _handle_client_connection(self, request):
        # logger.error ('Received {}'.format(request))
        # logger.error ('\n\nReceived {}'.format(request.decode('utf-8', 'replace')))
        try:
            rcv = request.decode('utf-8')
        except (OSError, socket.error) as e:
            # self.client_socket.close()
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
        if self._path == '/init':
            self._commands['/html_init']()
        elif self._path == '/title':
            self.send_song_title(self.song_title())
        elif self._path == '/favicon.ico':
            pass
        elif self._path == '/is_stopped' and self._is_html:
            received = self._commands['/html_is_stopped']()
            logger.error('received = "{}"'.format(received))
            self._send_raw(received)
        elif self._path == '/is_muted' and self._is_html:
            if self.muted():
                self._send_raw('0')
            else:
                self._send_raw('1')
        elif self._path in ('/log', '/g'):
            if self._is_html:
                received = self._commands['/html_log']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                self._commands['/log']()
                self._send_text(self._text['/log'], alert_type='alert-success')
        elif self._path in ('/like', '/l'):
            if self._is_html:
                received = self._commands['/html_like']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    self._commands['/like']()
                    self._send_text(self._text['/like'], alert_type='alert-success')
                else:
                    self._send_text(self._text['/idle'])
        elif self._path in ('/mute', '/m'):
            if self._is_html:
                received = self._commands['/html_mute']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    self._send_text('Player mute toggled!', alert_type='alert-success')
                    self._commands['/mute']()
                else:
                    self._send_text(self._text['/idle'])
        elif self._path in ('/volumesave', '/vs'):
            if self._is_html:
                received = self._commands['/html_volumesave']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!', alert_type='alert-danger')
                    else:
                        out = self._commands['/volumesave']()
                        if out:
                            self._send_text('Volume saved', alert_type='alert-success')
                        else:
                            self._send_text('Volume not saved', alert_type='alert-success')
                else:
                    self._send_text(self._text['/idle'])
        elif self._path in ('/volumeup', '/vu'):
            if self._is_html:
                received = self._commands['/html_volumeup']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!', alert_type='alert-danger')
                    else:
                        self._commands['/volumeup']()
                        self._send_text(self._text['/volumeup'], alert_type='alert-success')
                else:
                    self._send_text(self._text['/idle'])
        elif self._path in ('/volumedown', '/vd'):
            if self._is_html:
                received = self._commands['/html_volumedown']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!', alert_type='alert-danger')
                    else:
                        self._commands['/volumedown']()
                        self._send_text(self._text['/volumedown'], alert_type='alert-success')
                else:
                    self._send_text(self._text['/idle'])
        elif self._path == '/quit':
            if not self._is_html:
                self._send_text(self._text['/quit'])
        elif self._path in  ('', '/'):
            if self._is_html:
                self._send_text('', alert_type='')
                self.send_song_title(self.song_title())
            else:
                self._send_text(self._text['/'], alert_type='')
        elif self._path in ('/i', '/info'):
            if self._is_html:
                received = self._commands['/html_info']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.can_send_command():
                    self._send_text(self._info())
                else:
                    self._send_text(self._text['/perm'])
        elif self._path in ('/next', '/n'):
            if self._is_html:
                received = self._commands['/html_next']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.can_send_command():
                    self._send_text(self._text['/next'], alert_type='alert-success')
                    self._commands['/next']()
                else:
                    self._send_text(self._text['/perm'])
        elif self._path in ('/previous', '/p'):
            if self._is_html:
                received = self._commands['/html_previous']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.can_send_command():
                    self._send_text(self._text['/previous'], alert_type='alert-success')
                    self._commands['/previous']()
                else:
                    self._send_text(self._text['/perm'])
        elif self._path in ('/histnext', '/hn'):
            if self._is_html:
                received = self._commands['/html_histnext']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.can_send_command():
                    go_on = False
                    llen = len(self.config().stations_history.items)
                    l_item = self.config().stations_history.item
                    if l_item == -1 or llen == 0:
                        self._send_text('No items in history!', alert_type='alert-danger')
                    elif l_item + 1 < llen:
                        go_on = True
                    if go_on:
                        self._send_text(self._text['/histnext'], alert_type='alert-success')
                        self._commands['/histnext']()
                    else:
                        self._send_text('Already at last history item!')
                else:
                    self._send_text(self._text['/perm'])
        elif self._path in ('/histprev', '/hp'):
            if self._is_html:
                received = self._commands['/html_histprev']()
                logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.can_send_command():
                    go_on = True
                    llen = len(self.config().stations_history.items)
                    l_item = self.config().stations_history.item
                    if l_item == -1 or llen == 0:
                        self._send_text('No items in history!', alert_type='alert-danger')
                        go_on = False
                    elif l_item == 0:
                        go_on = False
                    if go_on:
                        self._send_text(self._text['/histprev'])
                        self._commands['/histprev']()
                    else:
                        self._send_text('Already at first history item!')
                else:
                    self._send_text(self._text['/perm'])
        elif self._path in ('/toggle', '/t'):
            if self._is_html:
                if self.sel()[1] > -1:
                    received = self._commands['/html_stop']()
                    logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
                else:
                    received = self._commands['/html_start']()
                    logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
            else:
                if self.can_send_command():
                    if self.sel()[1] > -1:
                        self._send_text(self._text['/stop'], alert_type='alert-success')
                        self._commands['/stop']()
                    else:
                        self._send_text(self._text['/start'], alert_type='alert-success')
                        self._commands['/start']()
                else:
                    self._send_text(self._text['/perm'])
        elif self._path.startswith('/st/') or \
                self._path.startswith('/stations/'):
            if self.can_send_command():
                ret = self._parse()
                if ret is None:
                    self._send_text(self._text['/error'], alert_type='alert-danger')
                else:
                    has_error = False
                    if ret == '/stations':
                        if self._is_html:
                            self._send_raw(
                                self._format_html_table(
                                self._list_stations(html=True), 0,
                                sel=self.sel()[1]
                                )
                            )
                        else:
                            self._send_text(self._list_stations())
                    else:
                        try:
                            ret = int(ret)
                        except (ValueError, TypeError):
                            self._send_text(self._text['/error'], alert_type='alert-danger')
                            has_error = True
                        if not has_error:
                            # ret = ret -1 if ret > 0 else 0
                            if ret < 0:
                                ret = 0
                            if self._is_html:
                                self._commands['/jump'](ret)
                                self._send_raw('<div class="alert alert-success">Playing <b>{}</b></div>'.format(self.lists()[0][-1][ret-1][0]))
                            else:
                                self._send_text(' Playing station: {}'.format(self.lists()[0][-1][ret-1][0]))
                                self._commands['/jump'](ret)
                    has_error = False
            else:
                if self._is_html:
                    self._send_raw('<div class="alert alert-danger">' + self._text['/perm'] + '</div>')
                else:
                    self._send_text(self._text['/perm'])
        elif self._path.startswith('/playlists') or \
                self._path.startswith('/pl') or \
                self._path == '/stations' or \
                self._path == '/st':
            if  ',' in self._path:
                if not self.can_send_command():
                    if self._is_html:
                        self._send_raw('<div class="alert alert-danger">' + self._text['/perm'] + '</div>')
                    else:
                        self._send_text(self._text['/perm'])
                else:
                    sp = self._path.split('/')
                    if ',' not in sp [-1]:
                        self._send_text(self._text['/error'], alert-danger)
                    else:
                        if sp[1] not in ('playlists', 'pl'):
                            self._send_text(self._text['/error'], alert_type='alert-danger')
                        else:
                            # get the numbers
                            pl, st = self._get_numbers(sp[-1])
                            if pl is None:
                                self._send_text(self._text['/error'], alert_type='alert-danger')
                            else:
                                go_on = True
                                try:
                                    playlist_name = self.lists()[1][-1][pl][0]
                                except IndexError:
                                    self._send_text('Error: Playlist not found (id={})'.format(pl+1))
                                    go_on = False
                                if go_on:
                                    p_name = basename(self.playlist_in_editor()[:-4])
                                    if p_name == playlist_name:
                                        # play station from current playlist
                                        self._commands['/jump'](st+1)
                                        if self._is_html:
                                            self._send_raw(
                                                '<div class="alert alert-success">Playing station <b>{0}</b> from playlist <i>{1}</i></b>'.format(
                                                    self.lists()[0][-1][st][0],
                                                    p_name
                                                )
                                            )
                                        else:
                                            self._send_text(
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
                                                    if self._is_html:
                                                        self._commands['open_history'](in_file, item)
                                                        self._send_raw(
                                                            '<div class="alert alert-success">Playing station <b>{0}</b> from playlist <i>{1}</i></div>'.format(
                                                                playlist_stations[st],
                                                                playlist_name
                                                            )
                                                        )
                                                    else:
                                                        self._send_text(
                                                            'Playing station "{0}" (id={1}) from playlist "{2}" (id={3})'.format(
                                                                playlist_stations[st],
                                                                st+1,
                                                                playlist_name,
                                                                pl+1
                                                            )
                                                        )
                                                        sleep(1)
                                                        self._commands['open_history'](in_file, item)
                                                else:
                                                    self._send_text(
                                                        'Error: Requested station (id={0}) not found in playlist "{1}" (id={2})'.format(
                                                            st+1, playlist_name, pl+1,
                                                        )
                                                    )
                                            else:
                                                self._send_text(
                                                    'Error opening playlist "{0}" (id={1})'.format(
                                                        playlist_name, pl+1
                                                    )
                                                )

            else:
                if not self.can_send_command():
                    if self._is_html:
                        self._send_raw('<div class="alert alert-danger">' + self._text['/perm'] + '</div>')
                    else:
                        self._send_text(self._text['/perm'])
                else:
                    ret = self._parse()
                    if ret is None:
                        self._send_text(self._text['/error'], alert_type='alert-danger')
                    elif ret.startswith('/'):
                        if ret == '/stations':
                            if self._is_html:
                                self._send_raw(
                                    self._format_html_table(
                                        self._list_stations(html=True), 0,
                                        sel=self.sel()[1]
                                    )
                                )
                            else:
                                self._send_text(self._list_stations())
                        elif ret == '/playlists':
                            if self._is_html:
                                self._send_raw(
                                    self._format_html_table(
                                        self._list_playlists(html=True), 1,
                                        sel=self._get_playlist_id(basename(self.playlist_in_editor()[:-4]))
                                    )
                                )
                            else:
                                self._send_text(self._list_playlists())
                        else:
                            self._send_text(self._text[ret])

                    else:
                        go_on = True
                        try:
                            ret = int(ret) - 1
                        except (ValueError, TypeError):
                            go_on = False
                            self._send_text(self._text['/error'], alert_type='alert-danger')
                        if go_on:
                            try:
                                playlist_name = self.lists()[2][-1][ret][0]
                            except IndexError:
                                self._send_text('Error: Playlist not found (id={})'.format(ret+1), alert_type='alert-danger')
                                go_on = False
                            if go_on:
                                in_file, out = self.config().read_playlist_for_server(
                                    playlist_name
                                )
                                if out:
                                    if self._is_html:
                                        self._send_raw(
                                            self._format_html_table(
                                                self._list_stations(stations=out, html=True),
                                                index=2,
                                                playlist_index=ret
                                            )
                                        )
                                    else:
                                        self._send_text(
                                            self._list_stations(playlist_name, out)
                                        )
                                else:
                                    if self._is_html:
                                        self._send_text('Error reading playlist: <b>{}</b>'.format(playlist_name), alert_type='alert-danger')
                                    else:
                                        self._send_text('Error reading playlist: "{}"'.format(playlist_name), alert_type='alert-danger')
        else:
            self._send_text(self._text['/error'], alert_type='alert-danger')

        return True

    def send_song_title(self, msg=None):
        if not msg:
            return
        f_msg = 'retry: 150\nevent: /html/title\ndata: <b>' + msg + '</b>\n\n'
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=UTF-8
Cache-Control: no-cache
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        try:
            self.client_socket.sendall(txt + b_msg)
        except socket.error as e:
            self.error = e
        except AttributeError:
            pass

    def _send_raw(self, msg):
        if msg.startswith('retry: '):
            return
        f_msg = msg + '\n'
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=utf-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        try:
            self.client_socket.sendall(txt + b_msg)
        except socket.error as e:
            self.error = e

    def _send_text(self,
                   msg, alert_type='alert-info',
                   content='', put_script=False
    ):
        if msg.startswith('retry: '):
            return
        if self._is_html:
            self._html_data['|ALERT|'] = msg
            self._html_data['|ALERT_TYPE|'] = alert_type
            self._html_data['|CONTENT|'] = content
            self._send_html(put_script=put_script)
            return
        f_msg = msg + '\n'
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        try:
            self.client_socket.sendall(txt + b_msg)
        except socket.error as e:
            self.error = e

    def _send_html(self, msg=None, put_script=False):
        f_msg = self._html + '\n'
        for n in self._html_data.keys():
            f_msg = f_msg.replace(n, self._html_data[n])
        if put_script:
            f_msg = self._insert_html_script(f_msg)
        if PY2:
            b_msg = f_msg
            txt = '''HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg))
        else:
            b_msg = f_msg.encode('utf-8')
            txt = '''HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=9000, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        try:
            self.client_socket.sendall(txt + b_msg)
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
        head_captions = [
            'Stations (current playlist)',
            'List of Playlists',
            'Stations from Playlist: "{}"'.format(self.lists()[1][-1][playlist_index][0]) if playlist_index is not None else ''
        ]
        url = ['/html/st/{}', '/html/pl/{}', '/html/pl/{0},{1}']
        timeout = ('1500', '0', '1500')
        head = '''                    <h5>Search field</h5>
                    <input class="form-control" id="myInput" type="text" placeholder="Type to search for a station...">
                    <br>
                    <table class="table table-bordered">
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
                out.append('                            <tr class="btn-success">')
            else:
                out.append('                            <tr>')
            if sel == i:
                out.append('                                <td class="text-right" style="color: white;">{}</td>'.format(i+1))
            else:
                out.append('                                <td class="text-right">{}</td>'.format(i+1))
            if index < 2:
                t_url = url[index].format(i+1)
            else:
                t_url = url[2].format(playlist_index+1, i+1)
            if sel == i:
                out.append('                               <td id="' + str(i+1) + '"><a style="color: white;" href="#" onclick="js_send_simple_command(\'' + t_url + '\', ' + timeout[index] + ');">' + n + '</a></td>')
            else:
                out.append('                               <td id="' + str(i+1) + '"><a href="#" onclick="js_send_simple_command(\'' + t_url + '\', ' + timeout[index] + ');">' + n + '</a></td>')
            out.append('                            </tr>')
        out.append('                        </tbody>')
        out.append('                    </table>')
        return head + '\n' + '\n'.join(out) + self._filter_string

    def _read_playlist(self, a_playlist):
        pass

