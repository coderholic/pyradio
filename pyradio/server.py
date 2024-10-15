# -*- coding: utf-8 -*-
import locale
import socket
import logging
from os import remove
from os.path import basename, exists
from sys import platform, version_info
from time import sleep
import requests

locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

HAS_NETIFACES = True
try:
    if not platform.lower().startswith('win'):
        import netifaces
except:
    HAS_NETIFACES = False

class IPs():
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
        if not HAS_NETIFACES:
            return out
        interfaces = netifaces.interfaces()
        for n in interfaces:
            iface=netifaces.ifaddresses(n).get(netifaces.AF_INET)
            if iface:
                for entry in iface:
                    # dirty way to get real interfaces
                    if 'broadcast' in str(entry):
                        if version_info[0] > 2:
                            out.append(entry['addr'])
                        else:
                            out.append(entry['addr'].encode('utf-8'))
        return sorted(list(set(out)))

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


class IPsWithNumbers():

    def __init__(self, default_ip=None, fat=False):
        self._ips = ['localhost', 'lan']
        ips = IPs()
        if fat or len(ips.IPs) > 2:
            self._ips.extend(ips.IPs[1:])
        self._index = 0
        if default_ip:
            try:
                self._index = self._ips.index(default_ip.lower())
            except ValueError:
                pass

    def set(self, new_ip):
        try:
            self._index = self._ips.index(new_ip.lower())
        except ValueError:
            pass
        return self._ips[self._index]

    def current(self):
        return self._ips[self._index]

    def next(self):
        self._index += 1
        if self._index >= len(self._ips):
            self._index = 0
        return self._ips[self._index]

    def previous(self):
        self._index -= 1
        if self._index <0:
            self._index = len(self._ips) - 1
        return self._ips[self._index]

    def ip_exists(self, ip):
        try:
            self._ips.index(ip.lower())
            return True
        except ValueError:
            return False

    def validate_ip(self, ip):
        ''' if ip is in the list of ips, return it
            else return localhost
        '''
        return ip.lower() if self.ip_exists(ip) else 'localhost'

class PyRadioServer():
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
html {min-height: 101vh;}
body {min-height: 101vh;}
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
    #group {
        background-color: #FF71FF;
        color: white;
    }
    /* The Modal (background) */
    .modal {
        display: none; /* Hidden by default */
        position: fixed; /* Stay in place */
        z-index: 1; /* Sit on top */
        left: 0;
        top: 0;
        width: 100%; /* Full width */
        height: 100%; /* Full height */
        overflow: auto; /* Enable scroll if needed */
        background-color: rgb(0,0,0); /* Fallback color */
        background-color: rgba(0,0,0,0.4); /* Black w/ opacity */
    }

    /* Modal Content/Box */
        .modal-content {
            background-color: #fefefe;
            margin: 15% auto; /* 15% from the top and centered */
            padding: 20px;
            border: 1px solid #888;
            width: 80%; /* Could be more or less, depending on screen size */
        }

    /* The Close Button */
        .close {
            color: #aaa;
            float: right;
            font-size: 28px;
            font-weight: bold;
        }

        .close:hover,
        .close:focus {
            color: black;
            text-decoration: none;
            cursor: pointer;
        }

    #infot {
        border-collapse: collapse;
    }

    #infot tr {
        padding: 0;
        margin: 0;
    }

    #infot td {
        font-weight: bold;
        vertical-align: top;
        color: #31708F;
    }
    #infot td:first-child {
        font-weight: normal;
        text-align: right;
        padding-left: 10px;
        padding-right: 10px;
    }

div[id^='a_']:hover { underline: none;}
        </style>
    <link rel="shortcut icon" href="https://raw.githubusercontent.com/coderholic/pyradio/master/devel/pyradio.ico"
    </head>
    <body class="container-fluid">
        <!--
        <div id="the_blocking_box">
        </div>
        -->

        <!-- The Modal -->
        <div id="myModal" class="modal modal-dialog">
            <!-- Modal content -->
            <div class="modal-content">
              <p>
                  <span class="close">&times;</span>
              </p>
              <div id="mod-cont">
                  No Groups found!
              </div>
            </div>
        </div>
        <div id="a_head" class="row text-center" onclick="js_refresh_page();" style="background: green; color: white; padding-bottom: 15px;">
            <h2>PyRadio Remote Control</h2>
        </div>
        <div id="a_title" onclick="js_send_simple_command('/html/title', 0);">
            <div id="title_container" class="row" style="margin: 3px; margin-top: 15px;>
                <div class="col-xs-12">
                    <div id="song_title" class="alert alert-info text-center">
                    <b>No data!</b>
                    </div>
                </div>
            </div>
        </a>
        <div id="all_buttons" class="row">
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button id="rb" onclick="js_toggle_radio_browser();" type="button" class="btn btn-info">Radio<br>Browser</button>
                    <button id="next" onclick="js_play_next();" type="button" class="btn btn-warning">Play<br>Next</button>
                    <button id="prev" onclick="js_play_previous();" type="button" class="btn btn-warning">Play<br>Previous</button>
                    <button id="hnext" onclick="js_send_simple_command_with_stop('/html/histnext', 1500);" type="button" class="btn btn-success">Play Hist.<br> Next</button>
                    <button id="hprev" onclick="js_send_simple_command_with_stop('/html/histprev', 1500);" type="button" class="btn btn-success">Play Hist.<br>Previous</button>
                    <button id="tplay" onclick="js_send_simple_command_with_stop('/html/toggle', 1500);" type="button" class="btn btn-danger">Toggle<br>Playback</button>
                </div>
            </div>
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button id="vu" onclick="js_send_simple_command('/html/volumeup', 1500);" type="button" class="btn btn-primary">Volume<br>Up</button>
                    <button id="vd" onclick="js_send_simple_command('/html/volumedown', 1500);" type="button" class="btn btn-primary">Volume<br>Down</button>
                    <button id="vs" onclick="js_send_simple_command('/html/volumesave', 1500);" type="button" class="btn btn-success">Save<br>Volume</button>
                    <button id="mute" onclick="js_send_simple_command('/html/mute', 1500);" type="button" class="btn btn-warning">Mute<br>Player</button>
                    <button id="recording" onclick="js_send_simple_command('/html/trec', 1500);" type="button" class="btn btn-danger">REC<br>Disabled</button>
                    <!-- <button id="recondig" onclick="js_send_simple_command('/html/reconfig', 1500);" type="button" class="btn btn-success">Re-read<br>Config</button> -->
                </div>
            </div>
            <div class="col-xs-4 col-lg-4">
                <div class="text-center">
                    <button id="st" onclick="js_send_simple_command('/html/st', 0);" type="button" class="btn btn-success">Show<br>Stations</button>
                    <button id="group" type="button" class="btn">Show<br>Groups</button>
                    <button id="pl" onclick="js_list_playlists_or_searches();" type="button" class="btn btn-primary">Show<br>Playlists</button>
                    <button id="logging" onclick="js_toggle_titles_logging();" type="button" class="btn btn-warning">Enable<br>Title Log</button>
                    <button id="like" onclick="js_send_simple_command('/html/like', 1500);" type="button" class="btn btn-info">Like<br>Title</button>
                    <button id="info" onclick="js_send_simple_command('/html/info', 0);" type="button" class="btn btn-danger">System<br>Info</button>
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
    ////////////////////////////////////////////////////////////////////
    //                     Group Modal Popup                          //
    ////////////////////////////////////////////////////////////////////

    // Get the modal
    var modal = document.getElementById("myModal");

    // Get the button that opens the modal
    var btn = document.getElementById("group");

    // Get the <span> element that closes the modal
    var span = document.getElementsByClassName("close")[0];

    // When the user clicks on the button, open the modal
    btn.onclick = function() {
      $('#mod-cont').html = "Nothing found!";
      var elements = document.getElementsByClassName('group-header');
      if (elements.length == 0){
          document.getElementById('mod-cont').innerHTML = "No Groups found!";
      } else {
        var my_out_str = `<table class="table table-bordered">
                        <thead>
                            <tr class="btn-success">
                                <td style="font-size:150%; color: white; font-weight: bolder;">Groups</td>
                            </tr>
                        </thead>
                        <tbody id="myGroupTable">`;


        for (i = 0; i < elements.length ; i++){
            var the_id = "";
            var the_text = "";
            var final_text = "";
            the_id = elements[i].getAttribute('id');
            the_text = elements[i].innerText;
            final_text = `<a onclick="js_hide_modal();" href="#` + the_id + `">` + the_text + "</a>";
            my_out_str += "<tr><td>" + final_text + "</td></tr>";
        }
        my_out_str += "</tbody></table>";
        document.getElementById('mod-cont').innerHTML =  my_out_str;
      }
      modal.style.display = "block";
    }

    function js_hide_modal(){
      modal.style.display = "none";
    }

    // When the user clicks on <span> (x), close the modal
    span.onclick = function() {
      modal.style.display = "none";
    }

    // When the user clicks anywhere outside of the modal, close it
    window.onclick = function(event) {
      if (event.target == modal) {
          modal.style.display = "none";
        }
    }
    ////////////////////////////////////////////////////////////////////
    //                   Group Modal Popup End                        //
    ////////////////////////////////////////////////////////////////////

    var error_count = 0;
    var msg_timeout = 0;
    var url_to_reload = "";
    var last_title = "";
    var get_rb_status = 0;
    var radio_browser = 0;

    var selection = -1;

    function js_refresh_page(){
        window.location.href = url_to_reload.replace("#", "");
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
        // console.log("get_rb_status", get_rb_status)
        if ( get_rb_status == 1 ){
            js_fix_radio_browser();
            window.get_rb_status = 0;
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

    function js_send_simple_command_with_stop(the_command, the_timeout){
            js_set_title("#song_title", "<b>Player is stopped!</b>", the_command);
            js_disable_buttons_on_stopped(true);
            js_send_simple_command(the_command, the_timeout);
        }

    function js_send_simple_command(the_command, the_timeout){
        // js_disable_all_buttons(true);
        // console.log("the_command =", the_command);
        if ( ( the_command == "/html/open_rb" ) || ( the_command == "/html/close_rb" ) ) {
            clearTimeout(msg_timeout);
            if ( window.radio_browser == 0 ){
                rb_msg = '<div class="alert alert-info">Connecting to <b>RadioBrowser</b>...</div>';
            }else{
                rb_msg = '<div class="alert alert-info">Disconnecting from <b>RadioBrowser</b>...</div>';
            }
            js_set_title("#msg_text", rb_msg, the_command);
            js_show_element("msg");
            // if (the_timeout > 0){
            //     msg_timeout = setTimeout(js_hide_msg, the_timeout);
            // }

           ////// Trigger to read radio_browser
           window.get_rb_status = 1;
           // console.log("* get_rb_status", window.get_rb_status);
        }
        if ( ( the_command.startsWith("/html/search_rb") ) || ( the_command.startsWith("/html/srb") ) ) {
            // console.log("RadioBrowser Search!")
            js_hide_msg();
            clearTimeout(msg_timeout);
            srb_msg = '<div class="alert alert-info">Performing <b>RadioBrowser</b> search...</div>';
            js_set_title("#msg_text", srb_msg, the_command);
            js_show_element("msg");
        }

        // console.log("get_rb_status", window.get_rb_status);
        // console.log("startsWith /html/pl/ :", the_command.startsWith("/html/pl/"));
        // console.log("length =:", the_command.length);
        if ( the_command == '/html/st' || ( ( the_command.startsWith("/html/pl/" ) && ( the_command.length > 9 )) )){
            js_disable_group_button(false);
        }
        else
        {
            js_disable_group_button(true);
        }
        // if ( ( the_command == '/html/st' ) || ( the_command == '/html/pl' ) || ( ( the_command.startsWith("/html/pl/" ) && ( the_command.length > 9 )) )){
        //     js_get_selection();
        // }
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
                } else if ( the_command == "/html/open_rb"  ) {
                    result = '<div class="alert alert-success">Connection to <b>RadioBrowser</b> established!</div>'
                    js_fix_radio_browser();
                } else if ( the_command == "/html/close_rb"  ) {
                    result = '<div class="alert alert-success"><b>Local</b> Playlist restored</div>'
                } else if ( ( the_command.startsWith("/html/search_rb") ) || ( the_command.startsWith("/html/srb") ) ) {
                    // console.log("RadioBrowser Search result!")
                    result = '<div class="alert alert-success">Search performed!</div>'
                //     //// js_hide_msg();
                //     // js_hide_msg();
                //     // clearTimeout(msg_timeout);
                //     // srb_msg = '<div class="alert alert-info">Performing <b>RadioBrowser</b> search...</div>';
                //     // js_set_title("#msg_text", srb_msg, the_command);
                //     // js_show_element("msg");
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
            if ( ( the_command == '/html/st' ) || ( the_command == '/html/pl' ) || ( ( the_command.startsWith("/html/pl/" ) && ( the_command.length > 9 )) )){
                // console.log("-- selection =", selection);
                let the_counter = 0;
                //if (selection > 0){
                //    the_counter = 2 * selection;
                //    console.log("the_counter =", the_counter);
                //}
                td = document.getElementsByTagName('td');
                for (i=the_counter; i<td.length; i++){
                    try{
                        var x = td[i].getAttribute('style');
                        // console.log("x =", x);
                        if (i>0){
                            if (x == "color: white;"){
                                // console.log("found at", i, "id =", td[i].getAttribute('id'));
                                var this_id = td[i+1].getAttribute('id');
                                if (i>6){
                                  this_id = "n" + (this_id-2);
                                }else{
                                    this_id = "myInput";
                                }
                                // console.log("this_id =", this_id);
                                document.getElementById(this_id).scrollIntoView();
                                break;
                            }
                        }
                    }catch{
                        // do not care about it!
                    }
                }
        }
        js_fix_recording();
        // js_fix_muted();
        // console.log("--------");
        js_disable_all_buttons(false);
        });
    }

    function js_play_next(){
        // js_disable_all_buttons(true);
        js_send_simple_command_with_stop('/html/next', 1500)
    }

    function js_play_previous(){
        // js_disable_all_buttons(true);
        js_send_simple_command_with_stop('/html/previous', 1500)
    }

    function js_set_title(a_tag, a_title, the_command=''){
        var b_title = a_title.replaceAll(String.fromCharCode(92), "");
        // console.log("b_title = ", b_title)
        // console.log("    ", last_title);
        // console.log("b_title.length < last_title.length :", b_title.length < last_title.length);
        // console.log("last_title.includes(b_title) :", last_title.includes(b_title));
        if ( a_tag === "#song_title" ){
            if ( b_title.length < last_title.length && last_title.includes(b_title.substring(0, b_title.length - 4)) ){
                // console.log("----", b_title)
                return;
            }
        } else if ( a_tag === "#msg_text" ){
            if ( the_command !== "" && the_command != "/html/info" ) {
                b_title = b_title.replace("alert ", "text-center alert ");
            }
        }

        // console.log("++++", b_title)
        $(a_tag).html(b_title);
        if ( a_tag === "#song_title" ){
            last_title = b_title;
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
                    $("#song_title").html("<b>Player is stopped!</b>");
                } else {
                    js_disable_buttons_on_stopped(false);
                    setTimeout(js_init_title, 1500);
                }
            }
        }
        getStopped();
    }

    function js_list_playlists_or_searches(){
        if ( window.radio_browser == 0 ){
            js_send_simple_command('/html/pl', 0);
        }else{
            js_send_simple_command('/html/lrb', 0);
        }
    }

    function js_get_selection(){
        const getSelection = async () => {
            const response = await fetch("/html/get_selection");
            const data = await response.text();
            // console.log("async selection:", data);
            if ( data > -1 ){
                selection = data;
            }else{
                selection = -1;
            }
        }
        getSelection();
        // console.log("==> selection =", selection);
    }

    function js_disable_group_button(enable){
        var element = document.getElementById("group");
        // DIS element.disabled = enable;
    }

    function js_disable_buttons_on_stopped(enable){
        let b_id = ["vu", "vd", "vs", "mute", "like" ];
        for (let i in b_id) {
            var element = document.getElementById(b_id[i]);
            // console.log("async:", data);
            // DIS element.disabled = enable;
        }
    }

    function js_disable_all_buttons(enable){
        if (enable){
            // disable all buttons
            let b_id = ["rb", "next", "prev", "hnext", "hprev", "tplay", "vu", "vd", "vs", "mute", "st", "group", "pl", "info", "logging", "like", "recording"];
            for (let i in b_id) {
                var element = document.getElementById(b_id[i]);
                // console.log("async:", data);
                element.disabled = true;
            }
        }else{
            let b_id = ["rb", "next", "prev", "hnext", "hprev", "tplay", "vu", "vd", "vs", "mute", "st", "group", "pl", "info", "logging", "like", "recording"];
            for (let i in b_id) {
                var element = document.getElementById(b_id[i]);
                // console.log("async:", data);
                element.disabled = false;
            }
            // enable / disable button based on state
            // js_fix_muted();
            // js_fix_recording();
            // js_fix_logging_titles();
        }
    }

    function js_fix_history_buttons(){
        var el_n = document.getElementById("hnext");
        var el_p = document.getElementById("hprev");
        var s = document.getElementById("pl");
        if ( window.radio_browser == 0 ){
            // DIS el_n.disabled = false;
            // DIS el_p.disabled = false;
            //s.disabled = true
            s.innerHTML = "Show<br>Playlists";
            // s.className = "btn btn-primary";
        }else{
            // DIS el_n.disabled = true;
            // DIS el_p.disabled = true;
            //s.disabled = false
            s.innerHTML = "Show<br>Searches";
            // s.className = "btn btn-danger";
        }
    }

    function js_toggle_radio_browser(){
        js_hide_msg();
        js_disable_all_buttons(true);
        var element = document.getElementById("rb");
        // DIS element.disabled = true;
        if ( window.radio_browser == 0 ){
            js_send_simple_command('/html/open_rb', 1500)
        }else{
            js_send_simple_command('/html/close_rb', 1500)
        }
        // DIS element.disabled = true;
        //js_disable_all_buttons(false);
        //js_fix_logging_titles();
        //js_fix_muted();
        //js_fix_history_buttons();
    }

    function js_toggle_titles_logging(){
        js_send_simple_command('/html/log', 1500);
        js_fix_logging_titles();
    }

    function js_fix_logging_titles(){
        const getTitlesLogging = async () => {
            const response = await fetch("/html/is_logging_titles");
            const data = await response.text();

            // console.log("async:", data);
            var element = document.getElementById("logging");
            if ( data == 0 ){
                element.className = "btn btn-warning";
                element.innerHTML = "Enable<br>Title Log"
            } else {
                element.className = "btn btn-success";
                element.innerHTML = "Disable<br>Title Log"
            }
        }
        getTitlesLogging();
    }

    function js_fix_recording(){
        const getRecordingStatus = async () => {
            const response = await fetch("/html/rec_status");
            const data = await response.text();

            // console.log("async recording:", data);
            var element = document.getElementById("recording");
            if ( data == 0 ){
                element.className = "btn btn-danger";
                element.innerHTML = "REC<br>Disabled";
                element.disabled = false;
            }else if (data == 1 ){
                element.className = "btn btn-danger";
                element.innerHTML = "REC<br>Enabled";
                element.disabled = false;
            }else if (data == 2 ){
                element.className = "btn btn-success";
                element.innerHTML = "REC<br>Disabled";
                element.disabled = false;
            }else if (data == 3 ){
                element.className = "btn btn-success";
                element.innerHTML = "REC<br>Enabled";
                element.disabled = false;
            }else if (data == 4 ){
                element.className = "btn btn-danger";
                element.innerHTML = "REC<br>Disabled";
                element.disabled = true;
            }
        }
        getRecordingStatus();
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

    function js_fix_radio_browser(){
        const getRadioBrowser = async () => {
            const response = await fetch("/html/is_radio_browser");
            const data = await response.text();

            // console.log("js_fix_radio_browser async:", data);
            var element = document.getElementById("rb");
            var pl = document.getElementById("pl");
            if ( data == 0 ){
                element.className = "btn btn-info";
                element.innerHTML = "Local<br>Playlist";
                pl.innerHTML = "Show<br>Playlists";
                window.radio_browser = 0
            } else {
                element.className = "btn btn-danger";
                element.innerHTML = "Radio<br>Browser";
                pl.innerHTML = "Show<br>Searchs";
                window.radio_browser = 1
            }
            // console.log("set radio_browser: ", radio_browser);
            js_disable_all_buttons(false);
            // js_fix_muted();
            // js_fix_recording();
            // js_fix_history_buttons();
            // js_fix_logging_titles();
            // DIS element.disabled = false;
        }
        getRadioBrowser();
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
        js_fix_recording();
        js_fix_radio_browser();
        js_fix_logging_titles();
        js_fix_stopped();
        js_disable_group_button(true);
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
Long                  Short        Description
---------------------------------------------------------------------------
/info                 /i           display PyRadio info
/volume               /v           show volume (text only)
/set_volume/x         /sv/x        set volume to x% (text only)
/volumeup             /vu          increase volume
/volumedown           /vd          decrease volume
/volumesave           /vs          save volume
/mute                 /m           toggle mute
/log                  /g           toggle stations logging
/like                 /l           tag (like) station
/title                             get title (HTML format)

Restricted Commands (Main mode only)
---------------------------------------------------------------------------
/toggle               /t           toggle playback
/playlists            /pl          get playlists list
/playlists/x          /pl/x        get stations list from playlist id x
                                     (x comes from command /pl)
/playlists/x,y        /pl/x,y      play station id y from playlist id x
/stations             /st          get stations list from current playlist
/stations/x           /st/x        play station id x from current playlist
/next                 /n           play next station
/previous             /p           play previous station
/histnext             /hn          play next station from history
/histprev             /hp          play previous station from history
/rec_status           /srec        get recording status
/toggle_rec           /trec        toggle recording
/open_rb              /orb         open RadioBrowser
/close_rb             /crb         close RadioBrowser
/list_rb              /lrb         list RadioBrowser search items
/search_rb/[x]        /srb/[x]     execute RadioBrowser search item x
                                     (x comes from /lrb - execute default
                                      search item if x not specified)
/rb_page              /grb         get RadioBrowser searh results page number
/rb_first_page        /frb         load RadioBrowser first results page
/rb_next_page         /nrb         load RadioBrowser next results page
/rb_previous_page     /prb         load RadioBrowser previous results page
/reconfig                          force a headless instance to read config''',
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
        '/perm': 'Operation not permitted (not in Main Mode)',
        '/perm_html': '<div class="alert alert-danger">Operation not permitted (not in <b>Main Mode</b>)</div>',
    }

    def __init__(self, bind_ip, bind_port, config, player, commands):
        self.has_netifaces = HAS_NETIFACES
        if not self.has_netifaces:
            return
        self._bind_ip = bind_ip
        if bind_ip.lower() == 'localhost':
            self._bind_ip = '127.0.0.1'
        elif bind_ip.lower() == 'lan':
            sys_ip = IPs()
            self._bind_ip = sys_ip.IPs[1]
        self._bind_port = bind_port
        self._commands = commands
        self._cnf = config
        self._player = player

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
            rb_html_search_strings,
            error_func,
            dead_func,
            song_title,
            lock
    ):
        self._path = ''
        self.config = config
        self.report_file = config().remote_control_server_report_file
        self.lists = lists
        self.playlist_in_editor = playlist_in_editor
        self.can_send_command = can_send_command
        self.rb_html_search_strings = rb_html_search_strings
        self.song_title = song_title
        '''
        sel = (self.selection, self.playing)
        '''
        self.sel = sel
        ''' the item to scroll to when displaying list of stations / playlists '''
        self._selected = -1
        self.muted = muted
        self.lock = lock
        self._remove_report_file()
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
            server.listen()  # max backlog of connections
        except (OSError, socket.error) as e:
            logger.error('Remote Control Server error: "{}"'.format(e))
            server.close()
            error_func(e)
            return
        if logger.isEnabledFor(logging.INFO):
            logger.info('Remote Control Server listening on {}:{}'.format(self._bind_ip, self._bind_port))

        self._create_report_file()
        while True:
            try:
                self.client_socket, address = server.accept()
                request = self.client_socket.recv(1024)
            except socket.error as e:
                self._remove_report_file()
                dead_func(e)
                break
            self.error = None
            self._handle_client_connection(address, request)
            if self.error is not None:
                # self.client_socket.close()
                self._remove_report_file()
                dead_func(self.error)
                break
            if self._path == '/quit':
                self.client_socket.close()
                self._remove_report_file()
                break
        server.close()
        if logger.isEnabledFor(logging.INFO):
            logger.info('Remote Control Server exiting...')
        # just in case...
        self._remove_report_file()

    def _create_report_file(self):
        try:
            with open(self.report_file, 'w', encoding='utf-8') as f:
                f.write('{0}:{1}'.format(self._bind_ip, self._bind_port))
        except:
            pass

    def _remove_report_file(self):
        if exists(self.report_file):
            try:
                remove(self.report_file)
            except:
                pass

    def _handle_client_connection(self, address, request):
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


        try:
            self._path = sp[1]
        except IndexError:
            self._path = ''
        if logger.isEnabledFor(logging.INFO):
            logger.info('Accepted connection from {0}:{1} -> {2}'.format(address[0], address[1], self._path))

        # self._is_html = True if self._path.startswith('/html') else False
        if self._path.startswith('/html'):
            self._is_html = True
            self._path = self._path[5:]
        else:
            self._is_html = False
        if self._path == '/init':
            self._commands['/html_init']()

        elif self._path == '/title':
            self.send_song_title(self.song_title())

        elif self._path == '/favicon.ico':
            pass

        elif self._path == '/get_selection' and self._is_html:
            self._send_raw(str(self._selected))

        elif self._path == '/is_radio_browser' and self._is_html:
            received = self._commands['/html_is_radio_browser']()
            self._send_raw(received)

        elif self._path == '/is_stopped' and self._is_html:
            received = self._commands['/html_is_stopped']()
            self._send_raw(received)

        elif self._path == '/toggle_rec' or self._path == '/trec':
            if self._is_html:
                received = self._commands['/html_toggle_rec']()
                self._send_raw(received)
            else:
                received = self._commands['/toggle_rec']()
                self._send_text(received)

        elif self._path == '/rec_status' or self._path == '/srec':
            if platform.lower().startswith('win') and \
                    self._player().PLAYER_NAME == 'vlc':
                if self._is_html:
                    self._send_raw('4')
                else:
                    self._send_text('Recording not supported')
            if self._is_html:
                ''' 0: rec disabled, not recording
                    1: rec enabled, not recording
                    2: rec disabled, recording
                    3: rec enabled, recording
                '''
                if self._player().recording == 0:
                    if self._player().currently_recording:
                        self._send_raw('2')
                    else:
                        self._send_raw('0')
                else:
                    if self._player().currently_recording:
                        self._send_raw('3')
                    else:
                        self._send_raw('1')
            else:
                rec = ', currently recording' if self._player().currently_recording else ''
                if self._player().recording == 0:
                    self._send_text('Redording is disabled' + rec)
                else:
                    self._send_text('Redording is enabled' + rec)

        elif self._path == '/is_muted' and self._is_html:
            if self.muted():
                self._send_raw('0')
            else:
                self._send_raw('1')

        elif self._path == '/is_logging_titles' and self._is_html:
            if self.config().titles_log.titles_handler is None:
                self._send_raw('0')
            else:
                self._send_raw('1')

        elif self._path in ('/log', '/g'):
            if self._is_html:
                received = self._commands['/html_log']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                received = self._commands['/log']()
                self._send_text(received)

        elif self._path in ('/like', '/l'):
            if self._is_html:
                received = self._commands['/html_like']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                received = self._commands['/like']()
                # logger.error('received = "{}"'.format(received))
                self._send_text(received)

        elif self._path in ('/mute', '/m'):
            if self._is_html:
                received = self._commands['/html_mute']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    # self._send_text('Player mute toggled!')
                    self._commands['/mute']()
                else:
                    self._send_text(self._text['/idle'])

        elif self._path in ('/volumesave', '/vs'):
            if self._is_html:
                received = self._commands['/html_volumesave']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!')
                    else:
                        out = self._commands['/volumesave']()
                        # if out:
                        #     self._send_text('Volume saved!')
                        # else:
                        #     self._send_text('Volume not saved!')
                else:
                    self._send_text(self._text['/idle'])

        elif self._path in ('/volumeup', '/vu'):
            if self._is_html:
                received = self._commands['/html_volumeup']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!')
                    else:
                        # self._send_text(self._text['/volumeup'])
                        self._commands['/volumeup']()
                else:
                    self._send_text(self._text['/idle'])

        elif self._path in ('/volumedown', '/vd'):
            if self._is_html:
                received = self._commands['/html_volumedown']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                if self.sel()[1] > -1:
                    if self.muted():
                        self._send_text('Player is muted!')
                    else:
                        # self._send_text(self._text['/volumedown'])
                        self._commands['/volumedown']()
                else:
                    self._send_text(self._text['/idle'])

        elif self._path == '/quit':
            if not self._is_html:
                self._send_text(self._text['/quit'])

        elif self._path in  ('', '/'):
            if self._is_html:
                self._send_text('')
                self.send_song_title(self.song_title())
            else:
                self._send_text(self._text['/'])

        elif self._path in ('/reconfig', ):
            ''' no html command '''
            if not self._is_html:
                if self._cnf.headless:
                    if self.can_send_command():
                        received = self._commands['/text_reconfig']()
                        # logger.error('received = "{}"'.format(received))
                        self._send_text(received)
                    else:
                        self._send_text(self._text['/perm'])
                else:
                    self._send_text('Command not applicable in non-headless operation!')
            else:
                self._send_raw('')

        elif self._path in ('/i', '/info'):
            if self._is_html:
                received = self._commands['/html_info']()
                # logger.error('received = "{}"'.format(received))
                self._send_raw(received)
            else:
                received = self._commands['/text_info']()
                self._send_text(received)

        elif self._path in ('/next', '/n'):
            if self._is_html:
                if self.can_send_command():
                    received = self._commands['/html_next']()
                    # logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    self._send_text(self._text['/next'])
                    self._commands['/next']()
                else:
                    self._send_text(self._text['/perm'])

        elif self._path in ('/previous', '/p'):
            if self._is_html:
                if self.can_send_command():
                    received = self._commands['/html_previous']()
                    # logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    self._send_text(self._text['/previous'])
                    self._commands['/previous']()
                else:
                    self._send_text(self._text['/perm'])

        elif self._path in ('/histnext', '/hn'):
            if self._is_html:
                if self.can_send_command():
                    received = self._commands['/html_histnext']()
                    # logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    go_on = False
                    llen = len(self.config().stations_history.items)
                    l_item = self.config().stations_history.item
                    if l_item == -1 or llen == 0:
                        self._send_text('No items in history!')
                    elif l_item + 1 < llen:
                        go_on = True
                    if go_on:
                        self._send_text(self._text['/histnext'])
                        self._commands['/histnext']()
                    else:
                        self._send_text('Already at last history item!')
                else:
                    self._send_text(self._text['/perm'])

        elif self._path in ('/histprev', '/hp'):
            if self._is_html:
                if self.can_send_command():
                    received = self._commands['/html_histprev']()
                    # logger.error('received = "{}"'.format(received))
                    self._send_raw(received)
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    go_on = True
                    llen = len(self.config().stations_history.items)
                    l_item = self.config().stations_history.item
                    if l_item == -1 or llen == 0:
                        self._send_text('No items in history!')
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
                if self.can_send_command():
                    if self.sel()[1] > -1:
                        received = self._commands['/html_stop']()
                        # logger.error('received = "{}"'.format(received))
                        self._send_raw(received)
                    else:
                        received = self._commands['/html_start']()
                        # logger.error('received = "{}"'.format(received))
                        self._send_raw(received)
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    if self.sel()[1] > -1:
                        self._send_text(self._text['/stop'])
                        self._commands['/stop']()
                    else:
                        self._send_text(self._text['/start'])
                        self._commands['/start']()
                else:
                    self._send_text(self._text['/perm'])

        elif self._path.startswith('/st/') or \
                self._path.startswith('/stations/'):
            if self.can_send_command():
                ret = self._parse()
                if ret is None:
                    self._send_text(self._text['/error'])
                else:
                    has_error = False
                    if ret == '/stations':
                        if self._is_html:
                            self._selected = self.sel()[1]
                            self._send_raw(
                                self._format_html_table(
                                self._list_stations(html=True), 0,
                                sel=self._selected,
                                show_page_navigation=self._cnf._online_browser is not None
                                )
                            )
                        else:
                            self._send_text(self._list_stations())
                    else:
                        try:
                            ret = int(ret)
                        except (ValueError, TypeError):
                            self._send_text(self._text['/error'])
                            has_error = True
                        if not has_error:
                            # ret = ret -1 if ret > 0 else 0
                            if ret < 0:
                                ret = 0
                            if self._is_html:
                                self._commands['/jump'](ret)
                                self._send_raw('<div class="alert alert-success">Playing <b>{}</b></div>'.format(self.lists()[0][-1][ret-1][0]))
                            else:
                                self._send_text(' Playing station: "{}"'.format(self.lists()[0][-1][ret-1][0]))
                                self._commands['/jump'](ret)
                    has_error = False
            else:
                if self._is_html:
                    self._send_raw(self._text['/perm_html'])
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/open_rb' or self._path == '/orb':
            if self._is_html:
                received = self._commands['/html_open_radio_browser']()
                self._send_raw(received)
            else:
                if not self.can_send_command():
                    self._send_text(self._text['/perm'])
                elif self._cnf.browsing_station_service:
                    self._send_text('RadioBrowser already active!')
                else:
                    received = self._commands['/open_radio_browser']()
                # self._send_text(received)

        elif self._path == '/close_rb' or self._path == '/crb':
            if self._is_html:
                if not self.can_send_command():
                    self._send_raw(self._text['/perm_html'])
                else:
                    received = self._commands['/html_close_radio_browser']()
            else:
                if not self.can_send_command():
                    self._send_text(self._text['/perm'])
                elif self._cnf.browsing_station_service:
                    received = self._commands['/close_radio_browser']()
                else:
                    self._send_text('Local playlist already opened!')
                # self._send_text('Local playlist opened!')

        elif self._path.startswith('/search_rb') or \
                self._path.startswith('/srb'):
            if not self.can_send_command():
                if self._is_html:
                    self._send_raw(self._text['/perm_html'])
                else:
                    self._send_text(self._text['/perm'])
                return
            if self._path.endswith('srb') or \
                    self._path.endswith('srb/') or \
                    self._path.endswith('search_radio_browser') or \
                    self._path.endswith('search_radio_browser/'):
                x = None
            else:
                p = self._path.replace(
                        '/search_radio_browser/', ''
                    ).replace(
                        '/srb/', ''
                    )
                # logger.error('p = "{}"'.format(p))
                try:
                    x = int(p)
                    # logger.error('x = {}'.format(x))
                except ValueError:
                    if self._is_html:
                        # logger.error('HTML ERROR')
                        self._send_raw('<div class="alert txt-center alert-danger">Error in parameter</div>')
                    else:
                        # logger.error('TEXT ERROR')
                        self._send_text('Error in command\n')
                    return
            if self._is_html:
                ret = self._commands['/html_search_radio_browser'](x)
            else:
                ret = self._commands['/search_radio_browser'](x)
                if ret != '':
                    self._send_text(ret)

        elif self._path == '/rb_page' or self._path == '/grb':
            if self._is_html:
                pass
            else:
                if self.can_send_command():
                    received = self._commands['/radio_browser_page']()
                    self._send_text(received)
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/rb_first_page' or self._path == '/frb':
            if self._is_html:
                if self.can_send_command():
                    ret = self._commands['/radio_browser_first_page']()
                    self._selected = self.sel()[1]
                    self._send_raw(
                        self._format_html_table(
                        self._list_stations(html=True), 0,
                        sel=self._selected,
                        show_page_navigation=self._cnf._online_browser is not None
                        )
                    )
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    received = self._commands['/radio_browser_first_page']()
                    self._send_text(received)
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/rb_next_page' or self._path == '/nrb':
            if self._is_html:
                if self.can_send_command():
                    ret = self._commands['/radio_browser_next_page']()
                    self._selected = self.sel()[1]
                    self._send_raw(
                        self._format_html_table(
                        self._list_stations(html=True), 0,
                        sel=self._selected,
                        show_page_navigation=self._cnf._online_browser is not None
                        )
                    )
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    received = self._commands['/radio_browser_next_page']()
                    self._send_text(received)
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/rb_previous_page' or self._path == '/prb':
            if self._is_html:
                if self.can_send_command():
                    ret = self._commands['/radio_browser_previous_page']()
                    self._selected = self.sel()[1]
                    self._send_raw(
                        self._format_html_table(
                        self._list_stations(html=True), 0,
                        sel=self._selected,
                        show_page_navigation=self._cnf._online_browser is not None
                        )
                    )
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    received = self._commands['/radio_browser_previous_page']()
                    self._send_text(received)
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/list_rb' or self._path == '/lrb':
            if self._is_html:
                if self.can_send_command():
                    sel, a_list = self.rb_html_search_strings()
                    if a_list:
                        self._send_raw(
                            self._format_html_table(
                                a_list, 3,
                                sel=sel-1
                            )
                        )
                    else:
                        out = []
                        out.append('<div class="alert alert-danger">')
                        out.append('No <b>Search Items</b> found!')
                        out.append('</div>')
                        self._send_raw('\n'.join(out))
                else:
                    self._send_raw(self._text['/perm_html'])
            else:
                if self.can_send_command():
                    received = self._commands['/list_radio_browser']()
                    self._send_text(received)
                else:
                    self._send_text(self._text['/perm'])

        elif self._path == '/volume' or self._path == '/v':
            ''' get volume '''
            if self._is_html:
                pass
            else:
                received = self._commands['/volume']()
                self._send_raw(received)
        elif self._path.startswith('/set_volume/') or \
                    self._path.startswith('/sv/'):
            ''' set volume '''
            go_on = True
            sp = self._path.split('/')
            if len(sp) != 3:
                self._send_text(self._text['/error'])
            else:
                try:
                    vol = int(sp[-1])
                except (ValueError, TypeError):
                    if self._is_html:
                        self._send_raw(self._text['/error'])
                    else:
                        self._send_text(self._text['/error'])
                    go_on = False
            if self._is_html:
                pass
            else:
                if go_on:
                    if 0 <= vol <= 100:
                        received = self._commands['/set_volume'](vol)
                        self._send_raw(received)
                    else:
                        self._send_raw('Error: Volume must be 0-100')

        elif self._path.startswith('/playlists') or \
                self._path.startswith('/pl') or \
                self._path == '/stations' or \
                self._path == '/st':
            if  ',' in self._path:
                if not self.can_send_command():
                    if self._is_html:
                        self._send_raw(self._text['/perm_html'])
                    else:
                        self._send_text(self._text['/perm'])
                else:
                    sp = self._path.split('/')
                    if ',' not in sp [-1]:
                        self._send_text(self._text['/error'], alert-danger)
                    else:
                        if sp[1] not in ('playlists', 'pl'):
                            self._send_text(self._text['/error'])
                        else:
                            # get the numbers
                            pl, st = self._get_numbers(sp[-1])
                            if pl is None:
                                self._send_text(self._text['/error'])
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
                        self._send_raw(self._text['/perm_html'])
                    else:
                        self._send_text(self._text['/perm'])
                else:
                    ret = self._parse()
                    if ret is None:
                        self._send_text(self._text['/error'])

                    elif ret.startswith('/'):
                        if ret == '/stations':
                            if self._is_html:
                                self._selected = self.sel()[1]
                                self._send_raw(
                                    self._format_html_table(
                                        self._list_stations(html=True), 0,
                                        sel=self._selected,
                                        show_page_navigation=self._cnf._online_browser is not None
                                    )
                                )
                            else:
                                self._send_text(self._list_stations())
                        elif ret == '/playlists':
                            if self._is_html:
                                self._selected = self._get_playlist_id(basename(self.playlist_in_editor()[:-4]))
                                self._send_raw(
                                    self._format_html_table(
                                        self._list_playlists(html=True), 1,
                                        sel=self._selected
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
                            self._send_text(self._text['/error'])
                        if go_on:
                            try:
                                playlist_name = self.lists()[2][-1][ret][0]
                            except IndexError:
                                self._send_text('Error: Playlist not found (id={})'.format(ret+1))
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
                                            self._list_stations(playlist_name, out).replace(r'<b>', '').replace(r'</b>', '')
                                        )
                                else:
                                    if self._is_html:
                                        self._send_raw('<div class="alert txt-center alert-danger">Error reading playlist: <b>{}</b></div>'.format(playlist_name))
                                    else:
                                        self._send_text('Error reading playlist: "{}"'.format(playlist_name))
        else:
            self._send_text(self._text['/error'])

        return True

    def send_song_title(self, msg=None):
        if not msg:
            return
        f_msg = 'retry: 150\nevent: /html/title\ndata: <b>' + msg + '</b>\n\n'
        b_msg = f_msg.encode('utf-8')
        txt = '''HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=UTF-8
Cache-Control: no-cache
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=1, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        with self.lock:
            try:
                self.client_socket.sendall(txt + b_msg)
            except socket.error as e:
                self.error = e
            except AttributeError:
                pass

    def _send_raw(self, msg):
        # logger.error('msg = "{}"'.format(msg))
        if msg is None:
            msg = 'Unknown reply...'
        if msg.startswith('retry: '):
            return
        f_msg = msg + '\n'
        b_msg = f_msg.encode('utf-8')
        txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=1, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        with self.lock:
            try:
                self.client_socket.sendall(txt + b_msg)
            except socket.error as e:
                self.error = e

    def _send_text(
        self, msg,
        put_script=False
    ):
        if msg.startswith('retry: '):
            return
        # logger.error('_send_text(): "{}"'.format(msg))
        if self._is_html:
            self._send_html(put_script=put_script)
            return
        f_msg = msg + '\n'
        b_msg = f_msg.encode('utf-8')
        txt = '''HTTP/1.1 200 OK
Content-Type: text/txt; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=1, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        with self.lock:
            try:
                self.client_socket.sendall(txt + b_msg)
            except socket.error as e:
                self.error = e

    def _send_html(self, msg=None, put_script=False):
        f_msg = self._html + '\n'
        if put_script:
            f_msg = self._insert_html_script(f_msg)
        b_msg = f_msg.encode('utf-8')
        txt = '''HTTP/1.1 200 OK
Content-Type: text/html; charset=UTF-8
Connection: keep-alive, Keep-Alive
Keep-Alive: timeout=1, max=1000
Content-Length: {}

'''.format(len(b_msg)).encode('utf-8')
        with self.lock:
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
                        int(sp[1])
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


        with self.lock:
            try:
                s.connect((self._bind_ip, self._bind_port))
                request = "GET /quit HTTP/1.0\n\n".encode('utf-8')
                s.sendall(request)
            except socket.error as e:
                s.close()
                return False, e

        # Receive data
        try:
            s.recv(4096)
            # reply = s.recv(4096)
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
                if html:
                    if n[1] == '-':
                        out.append('<b>' + n[0] + '</b>')
                    else:
                        out.append(n[0])
                else:
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
            return 'Stations List for Playlist: "' + p_name + '"\n' +  '\n'.join(out) + '\n\nFirst column\n  [> ]: Selected, [+ ]: Playing, [+>]: Both'
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

        return 'Available Playlists\n' + '\n'.join(out) + '\n\nFirst column\n  [>]: Playlist loaded'

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
            playlist_index=None, sel=-1,
            show_page_navigation=False
        ):
        '''
        format html table for |CONTENT|

        Parameters
        ==========
        in_list         list of items
        sel             selected item
        index           type of output (stations / playlist) and URL formatter
        playlist_index  playist index (only valid if index == 2)
        '''
        if show_page_navigation:
            out = []
            show_prev_button = self._cnf._online_browser.page > 0
            show_first_button = self._cnf._online_browser.page > 1
            show_next_button = len(in_list) == self._cnf._online_browser.current_search_limit
            if show_next_button or show_prev_button:
                out.append(r'''
<div id="page" class="row" style="margin-top: 40px;">
        <div class="text-center">
            <div id="gpage" style="margin-bottom: 2px;">Results page: <span style="color: red; font-weight: bold;">{}</span></div>
'''.format(self._cnf._online_browser.page+1))
                if show_first_button:
                    out.append(r'''<button id="fpage" onclick="js_send_simple_command('/html/rb_first_page', 1500); js_send_simple_command('/html/st', 0);" type="button" class="btn btn-warning">First<br>Page</button>''')
                if show_prev_button:
                    out.append(r'''<button id="npage" onclick="js_send_simple_command('/html/rb_previous_page', 1500); js_send_simple_command('/html/st', 0);" type="button" class="btn btn-primary">Previous<br>Page</button>''')
                if show_next_button:
                    out.append(r'''<button id="ppage" onclick="js_send_simple_command('/html/rb_next_page', 1500); js_send_simple_command('/html/st', 0);" type="button" class="btn btn-primary">Next<br>Page</button>''')
                out.append(r'''
        </div>
</div>''')
                nav = ''.join(out)
                out = []
            else:
                nav = ''
        else:
            nav = ''
        head_captions = [
            'Stations (current playlist)',
            'Playlists',
            'Stations from Playlist: "{}"'.format(self.lists()[1][-1][playlist_index][0]) if playlist_index is not None else '',
            'RadioBrowser Search Items'
        ]
        url = ['/html/st/{}', '/html/pl/{}', '/html/pl/{0},{1}', '/html/srb/{}']
        search_term = ('station', 'playlist', 'station', 'term')
        timeout = ('1500', '0', '1500', '1500')
        head = '''                    <h5>Search field</h5>
                    <input class="form-control" id="myInput" type="text" placeholder="Type to search for a {0}...">
                    <br>
                    <table class="table table-bordered">
                        <thead>
                            <tr class="btn-success">
                                <td colspan="2" style="color: white; font-weight: bolder;">{1}</td>
                            </tr>
                        </thead>
                        <tbody id="myTable">
'''.format(search_term[index], head_captions[index])
        out = []
        for i, n in enumerate(in_list):
            header = False
            if n.startswith('<b>') or \
                    n.startswith('<B>'):
                header = True
                out.append('                            <tr>')
            else:
                if sel == i:
                    out.append('                            <tr class="btn-success">')
                else:
                    out.append('                            <tr>')
                if sel == i:
                    out.append('                                <td id="n{0}" class="text-right" style="color: white;">{1}</td>'.format(i+1, i+1))
                else:
                    out.append('                                <td id="n{0}" class="text-right">{1}</td>'.format(i+1, i+1))
            if header:
                out.append('                               <td id="n' + str(i+1) + '" class="text-center group-header" colspan="2">' + n + '</td>')
            else:
                if index in (0, 1, 3):
                    t_url = url[index].format(i+1)
                else:
                    t_url = url[2].format(playlist_index+1, i+1)
                if sel == i:
                    out.append('                               <td id="' + str(i+1) + '"><a style="color: white;" href="#" onclick="js_send_simple_command_with_stop(\'' + t_url + '\', ' + timeout[index] + ');">' + n + '</a></td>')
                else:
                    out.append('                               <td id="' + str(i+1) + '"><a href="#" onclick="js_send_simple_command_with_stop(\'' + t_url + '\', ' + timeout[index] + ');">' + n + '</a></td>')
            out.append('                            </tr>')
        out.append('                        </tbody>')
        out.append('                    </table>')
        return nav + head + '\n' + '\n'.join(out) + self._filter_string

    def _read_playlist(self, a_playlist):
        pass
