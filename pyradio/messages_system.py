# -*- coding: utf-8 -*-
#
import curses
import re
import logging
import locale
from curses.ascii import ACK as KEY_ACK, STX as KEY_STX
from sys import platform
from .window_stack import Window_Stack_Constants
from .keyboard import kbkey, kb2str, kb2strL, check_localized
from .common import M_STRINGS
from .tts import Priority, Context

locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

class PyRadioMessagesSystem():

    ''' reset _columns and _tokens
        These keys will have non static content,
        so widths will have to be calculated every time
    '''
    _reset_metrics = (
            'M_PLAYLIST_DELETE_ERROR',
            'D_PLAYLIST_DELETE_ASK',
            'D_GROUP_DELETE_ASK',
            'D_STATION_DELETE_ASK',
            'D_STATION_DELETE_ASK_LOCKED',
            'H_CONFIG_PLAYER',
            'M_SHOW_UNNAMED_REGISTER',
            'M_STATION_INFO',
            'M_DB_INFO',
            'M_UPDATE_STATIONS_RESULT',
            'D_WITH_DELAY',
            'UNIVERSAL',
            )

    _one_arg_list = (
            'D_RC_ACTIVE',
            'M_RC_START_ERROR',
            'D_RB_ASK_TO_SAVE_CONFIG',
            'D_RB_ASK_TO_SAVE_CONFIG_FROM_CONFIG',
            'D_RB_ASK_TO_SAVE_CONFIG_TO_EXIT',
            'M_RC_DEAD_ERROR',
            'D_UPDATE_NOTIFICATION',
            'M_PLAYLIST_DELETE_ERROR',
            'D_PLAYLIST_DELETE_ASK',
            'D_GROUP_DELETE_ASK',
            'D_STATION_DELETE_ASK',
            'D_STATION_DELETE_ASK_LOCKED',
            'M_SHOW_UNNAMED_REGISTER',
            'M_CHANGE_PLAYER_THE_SAME_ERROR',
            'M_DNSPYTHON_ERROR',
            'M_NETIFACES_ERROR',
            'M_REQUESTS_ERROR',
            'M_REGISTER_SAVE_ERROR',
            'M_PLAYLIST_SAVE_ERR_1'
            'M_PLAYLIST_SAVE_ERR_2'
            'M_SCHEDULE_INFO',
            'M_SCHEDULE_ERROR',
            'M_REC_IS_ON_NO_DIR_HEADLESS',
            'M_SCHEDULE_INFO',
            'M_KEYBOARD_FILE_SAVE_ERROR',
            )

    _two_arg_list = (
            'M_RB_VOTE_RESULT',
            'M_REC_DIR_MOVE_ERROR',
            'M_CHANGE_PLAYER_ONE_ERROR',
            'M_FOREIGN',
            'M_PARAMETER_ERROR',
            'M_RB_UNKNOWN_SERVICE',
            'X_PLAYER_CHANGED',
            )

    _second_arg_is_a_function = (
            'SCHEDULE_ERROR_MODE',
            'SCHEDULE_ERROR_MODE',
            'M_UPDATE_STATIONS_RESULT',
            )

    def set_text(self, parent, *args):
        self._args = args
        self._txt = {
        'UNIVERSAL': (),

        'H_MAIN': ('PyRadio Help',
kb2str(r'''__Welcome to |PyRadio Main Help
__You can use the following keys to navigate: |{j}| or |Up|, |{k}| or |Down|,
|PgUp| or |^B|, |PgDn| or |^F| to scroll up/down.
__You can also use |Home| or |{g}| and |End| or |{G}| to scroll to the top / bottom.

__You will have noticed an |upward arrow| at the top right corner of
this window; it indicates that the text is |scrollable| and the keys
mentioned above are |valid|; if the arrow is not there, the text is
not scrollable and pressing any key will |close the window|.

!Gerneral Notes
|Note 1:| |Home| (and |{g}|) and |End| (and |{G}|) may be used to move to the first
____and last item or field, respectively. In several of these windows
____(excluding the main window), |0| and |^| can be used to go to the
____first item or field, and |$| can be used to go to the last one.

|Note 2:| In several windows, |Tab| may be used to move to next item or
____field (and |Sh-Tab| to the previous one). In these cases, |{tab}| and |{stab}|
____can also be used, respectively.

!Gerneral Help
Up|, |{j}|, |PgUp|,                                     <*>
Down|, |{k}|, |PgDown                                   <*>  Change station selection.
<n>{g}| / |<n>{G}                                       <*>  Jump to first /last or |n|-th station.
{screen_top} {screen_middle} {screen_bottom}            <*>  Go to top / middle / bottom of screen.
{goto_playing}                                          <*>  Go to |P|laying station.
Enter|, |Right|, |{l}                                   <*>  Play selected station.
{ext_player}                                            <*>  E|x|ternal player playback.
{p_next}| / |{p_prev}                                   <*>  Play |N|ext or |P|revious station.
{info}                                                  <*>  Display station |i|nfo (when playing).
{random}                                                <*>  Select and play a random station.
{pause}|, |Left|, |{h}                                  <*>  Stop / start playing selected station.
{fav}                                                   <*>  Add station to favorites.
Esc|, |{q}                                              <*>  Quit.

!Volume management
{v_dn2}| / |{v_up1} or |{v_dn1}| / |{v_up2}     <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.

!Misc
{open_playlist}| / |{s}| / |{reload}            <*>  |O|pen / |S|ave / |R|eload playlist.
{t}| / |{transp}| / | {t_calc_col}              <*>  Change |t|heme / |T|ransparency / Calc. Background.
{open_config}                                   <*>  Open |C|onfiguration window.

!Searching
{search} |/ |{search_next}| / |{search_prev}    <*>  Search, go to next / previous result.

!Stations' history
{hist_prev} |/| {hist_next}                     <*>  Move to previous / next station.

!Moving stations
{jump}                                          <*> Create a |J|ump tag.
<n>{st_up}|, |<n>{st_dn}                        <*> Move station |U|p / |D|own.
                                                <*> If a |jump tag| exists, move it there.
!Group Management
{add} {append}                                  <*>  Add a |Group| (sets |URL| to "|-|").
{gr_prev} |/ |{gr_next}                         <*>  Go to previous / next |Group|.
{gr}                                            <*>  Open the |Group Selection| window.

!Player Customization
{https}                                         <*>  Toggle |Force http connections|
{extra_p_pamars}                                <*>  Extra player parameters

!Title Logger
{t_tag}                                         <*>  Toggle Logger on/off
{tag}                                           <*>  Tag a station as liked

!Recording
{rec}                                           <*>  Enable / disable |recording|.
{pause}                                         <*>  Pause / resume playback.

!Change Player
{open_extra}{change_player}                     <*>  Open the |Player Selection| window.

!Remote Control Server
{open_extra}{s}                                 <*>  Start/Stop the |Server|.

!Playlist editing
{add}| / |{append}                              <*>  Add / append new station.
{edit}                                          <*>  Edit current station.
{open_enc}                                      <*>  Change station's encoding.
{paste}                                         <*>  Paste unnamed register.
DEL|, |{del}                                    <*>  Delete selected station.

!Alternative modes
{open_extra}                                    <*>  Enter |Extra Commands| mode.
{add_to_reg}                                    <*>  Enter |Copy| mode.
{open_regs}                                     <*>  Enter |Register| mode.
Esc|, |{q}                                      <*>  Exit alternative mode.

!Extra Command mode ({open_extra})
{open_extra}                                    <*>  Open previous playlist.
{hist_top}                                      <*>  Open first opened playlist.
{change_player}                                 <*>  Change |m|edia player.
{new_playlist}                                  <*>  Create a |n|ew playlist.
{paste}                                         <*>  Select playlist / register to |p|aste to.
{rename_playlist}                               <*>  |R|ename current playlist.
{clear_all_reg}                                 <*>  |C|lear all registers.
{html_help}                                     <*>  Display |H|TML help.
{station_volume}                                <*>  Save station |v|olume.
{toggle_station_volume}                         <*>  Toggle use of station |V|olume.
{toggle_time}                                   <*>  Toggle time display.
{toggle_tts}                                    <*>  Toggle Text-to-Speech.
{open_remote_control}                           <*>  Open "PyRadio Remote Control" window.
{open_dirs}                                     <*>  Open dirs in file manager
{buffer}                                        <*>  Toggle buffering.
{open_buffer}                                   <*>  Open buffering window.
{unnamed}                                       <*>  Show unnamed register.
{last_playlist}                                 <*> Toggle Open last playlist.
{toggle_time}                                   <*> Toggle displaying time.
{clear_reg}                                     <*> Clear current register.

!Copy mode ({add_to_reg})
Enter                                           <*>  Copy station to unnamed register.
a-z| / |0-9                                     <*>  Copy station to named register.

!Registe mode ({open_regs})
{open_regs}                                     <*>  Open registers list.
a-z| / |0-9                                     <*>  Open named register.

!Windows Only
{F8}                                            <*>  Players management.
{F9}                                            <*>  Show |EXE| location.
{F10}                                           <*>  Uninstall |PyRadio|.

!Mouse Support (if enabled)
Click                                           <*>  Change selection.
Double click                                    <*>  Start / stop the player.
Middle click                                    <*>  Toggle mute.
Wheel                                           <*>  Page up / down.
Shift-Wheel                                     <*>  Adjust volume.

<!--rb-->!RadioBrowser
{open_online}                                       <*>  Open |RadioBrowser|.
{open_config}                                       <*>  Open |c|onfig window.
{rb_server}                                         <*>  Select server to |c|onnect to.
{s}                                                 <*>  |S|earch for stations.
{rb_p_first}| / |{rb_p_prev}| / |{rb_p_next}        <*>  Fetch first / previous / next page.
{rb_sort}                                           <*>  |S|ort search results.
{rb_info}                                           <*>  Database Station |I|nfo (current selection).
{rb_vote}                                           <*>  |V|ote for station.
{q} Escape {open_extra}{open_extra}                 <*>  Close Browser (go back in history).

Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
'''), Priority.HELP),

'D_STATION_DELETE_ASK': ('Station Deletion',
kb2strL(r'''
Are you sure you want to delete station:
"|{}|"?

Press "|{y}|" to confirm, "|{Y}|" to confirm and not
be asked again, or any other key to cancel

'''), Priority.HIGH),

'D_ASK_TO_SAVE_CONFIG': ('Config Modified',
kb2strL(r'''
The configuration has been modified!

Press "|{y}|" to save it, or "|{q}|" or "|ESC|" to
disregard the changes, or any other key to
 remain in the |Configuration Editor|.

'''.replace('{s}', chr(kbkey['s']))
), Priority.HIGH),

'D_STATION_DELETE_ASK_LOCKED': ('Station Deletion',
kb2strL(r'''
Are you sure you want to delete station:
"|{}|"?

Press "|{y}|" to confirm, or any other key to cancel

'''), Priority.HIGH),

    'M_STATION_INFO_ERROR': ('Station Info Error',
r'''
Station info not available at this time,
since it comes from the data provided by
the station when connecting to it.

Please play a station to get its info, (or
wait until one actually starts playing).

''', Priority.HIGH
),

'M_PLAYING_STATION_CHANGE_MODE': ('Station not available',
r'''
The station playing does not exist
_____in the current playlist.

''', Priority.HIGH
),

    'M_STATION_INFO': ('', Priority.DIALOG),

    'M_DB_INFO': ('', Priority.DIALOG),

    'D_WITH_DELAY': ('', Priority.DIALOG),

    'H_PLAYLIST': ('Playlist Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                  <*>
Down|, |{k}|, |PgDown                           <*>Change playlist selection.
<n>{g}| / |<n>{G}                               <*>Jump to first / last or n-th item.
{screen_middle}| / |{goto_playing}              <*>Jump to |M|iddle / loaded playlist.
Enter|, |Right|, |{l}                           <*>Open selected playlist.
{del}                                           <*>Delete current playlist.
{reload}                                        <*>Re-read playlists from disk.
{open_regs}                                     <*>Toggle between playlists / registers.
{search} |/ |{search_next}| / |{search_prev}    <*>  Search, go to next / previous result.
{open_extra}                                    <*>Enter |Extra Commands| mode.
Esc|, |{q}|, |Left|, |{h}                       <*>Cancel.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),


    'M_PLAYLIST_READ': ('',
r'''
___Reading playlists.___
____Please wait...

''', Priority.HIGH
),

    'D_PLAYLIST_RELOAD_CONFIRM': ('Playlist Reload',
kb2strL(r'''
This playlist has not been modified within
PyRadio. Do you still want to reload it?

Press "|{y}|" to confirm, "|{Y}|" to confirm and not
be asked again, or any other key to cancel

'''
), Priority.HIGH),

    'D_PLAYLIST_RELOAD_CONFIRM_LOCKED': ('Playlist Reload',
kb2strL(r'''
This playlist has not been modified within
PyRadio. Do you still want to reload it?

Press "|{y}|" to confirm, or any other key to cancel

'''
), Priority.HIGH),

    'M_PLAYLIST_LOAD_ERROR': ('Error',
),

    'D_PLAYLIST_DIRTY_CONFIRM_LOCKED': ('Playlist Reload',
kb2strL(r'''
This playlist has been modified within PyRadio.
If you reload it now, all modifications will be
lost. Do you still want to reload it?

Press "|{y}|" to confirm, or "|{n}|" to cancel

'''
), Priority.HIGH),

    'D_PLAYLIST_DIRTY_CONFIRM': ('Playlist Reload',
kb2strL(r'''
This playlist has been modified within PyRadio.
If you reload it now, all modifications will be
lost. Do you still want to reload it?

Press "|{y}|" to confirm, "|{Y}|" to confirm and not be
asked again, or "|{n}|" to cancel

'''
), Priority.HIGH),

    'D_PLAYLIST_MODIFIED': ('Playlist Modified',
kb2strL(r'''
This playlist has been modified within
PyRadio. Do you want to save it?

If you choose not to save it now, all
modifications will be lost.

Press "|{y}|" to confirm, "|{Y}|" to confirm and not
be asked again, "|{n}|" to reject, or "|{q}|" or
"|ESCAPE|" to cancel

'''
), Priority.HIGH),

    'D_PLAYLIST_MODIFIED_LOCKED': ('Playlist Modified',
kb2strL(r'''
This playlist has been modified within
PyRadio. Do you want to save it?

If you choose not to save it now, all
modifications will be lost.

Press "|{y}|" to confirm, "|{n}|" to reject,
or "|{q}|" or "|ESCAPE|" to cancel

'''
), Priority.HIGH),

    'M_PLAYLIST_SAVE_ERR_1': ('Error'
r'''
Saving current playlist |failed|!

Could not open file for writing
"|{}|"

''', Priority.HIGH
),

    'M_PLAYLIST_SAVE_ERR_2': ('Error'
r'''
Saving current playlist |failed|!

You will find a copy of the saved playlist in
"|{}|"

PyRadio will open this file when the playlist
is opened in the future.

''', Priority.HIGH
),

    'M_PLAYLIST_NOT_FOUND_ERROR': ('Error',
r'''
Playlist |not| found!

This means that the playlist file was deleted
(or renamed) some time after you opened the
Playlist Selection window.

''', Priority.HIGH
),

    'M_PLAYLIST_RECOVERY_ERROR_1': ('Error',
r'''
Both a playlist file (|CSV|) and a playlist backup
file (|TXT|) exist for the selected playlist. In
this case, |PyRadio| would try to delete the |CSV|
file, and then rename the |TXT| file to |CSV|.

Unfortunately, deleting the |CSV| file has failed,
so you have to manually address the issue.

''', Priority.HIGH
),

    'M_PLAYLIST_RECOVERY_ERROR_2': ('Error',
r'''
A playlist backup file (|TXT|) has been found for
the selected playlist. In this case, PyRadio would
try to rename this file to |CSV|.

Unfortunately, renaming this file has failed, so
you have to manually address the issue.

''', Priority.HIGH
),

    'M_PLAYLIST_NOT_SAVED': ('Playlist Modified',
r'''
Current playlist is modified and cannot be renamed.

Please save the playlist and try again.

''', Priority.HIGH
),

        'D_PLAYLIST_DELETE_ASK': ('Playlist Deletion',
kb2strL(r'''
Are you sure you want to delete the playlist:
"|{}|"?
Please keep in mind that once it is deleted, there
is no way to get it back.

Press "|{y}|" to confirm, or any other key to cancel

'''
), Priority.HIGH),

        'M_PLAYLIST_DELETE_ERROR': ('Playlist Deletion Error',
r'''
Cannot delete the playlist:
"|{}|"

Please close all other porgrams and try again...

''', Priority.HIGH
),

    'M_PLAYLIST_RELOAD_ERROR': ('Error',
r'''
Playlist reloading |failed|!

You have probably edited the playlist with an
external program. Please re-edit it and make
sure that you save a valid |CSV| file.

''', Priority.HIGH
),

        'H_THEME': ('Theme Help',
kb2str(r'''Up| ,|{j}|, |PgUp|,                  <*>
Down|, |{k}|, |PgDown                           <*> Change theme selection.
{g}| / |<n>{G}                                  <*> Jump to first or n-th / last theme.
Enter|, |Right|, |{l}                           <*> Apply selected theme.
{pause}                                         <*> Apply theme and make it default.
{watch_theme}                                   <*> Make theme default and watch it for
|                                               <*> changes (|User Themes| only).
{transp}                                        <*> Toggle theme transparency.
{reload}                                        <*> Rescan disk for user themes.
{search} |/ |{search_next}| / |{search_prev}    <*> Search, go to next / previous result.
Esc|, |{q}|, |Left|, |{h}                       <*> Close window.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*> Change volume.
{mute}| / |{s_vol}                              <*> |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*> Toggle title log / like a station.'''
), Priority.HELP),

    'D_THEME_CREATE_NEW_ASK': ('Read-only Theme',
kb2strL(r'''
You have requested to edit a |read-only| theme,
which is not possible. Do you want to create a
new theme instead?

Press "|{y}|" to accept or any other key to cancel.

'''
), Priority.HIGH),

        'H_GROUP': ('Group Selection Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                      <*>
Down|, |{k}|, |PgDown                               <*> Change Group Header selection.
{g} {G}                                             <*> Go to first / last Group Header.
{screen_top} {screen_middle} {screen_bottom}        <*> Go to top / middle / bottom of screen.
{search} {search_next} {search_prev}                <*> Perform search.
{pause}|, |Left|, |Enter                            <*> Select a Group Header.
Esc|, |{q}                                          <*> Cancel.
%Global functions
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}             <*> Change volume.
{mute}| / |{s_vol}                                  <*> |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                                   <*> Toggle title log / like a station.'''
), Priority.HELP),

    'D_GROUP_DELETE_ASK': ('Group Deletion',
kb2strL(r'''
Are you sure you want to delete this group header:
"|{}|"?

Press "|{y}|" to confirm, or any other key to cancel

'''
), Priority.HIGH),

    'H_YANK': ('Copy Mode Help',
r'''Enter                           <*> Copy station to unnamed register.
a-z| / |0-9                         <*> Copy station to named register.

Any other key exits current mode.

''', Priority.HELP
),

    'H_REGISTERS': ('Registers Mode Help',
r'''Enter                           <*> Open registers list.
a-z| / |0-9                         <*> Open named register.

Any other key exits current mode.

''', Priority.HELP
),

    'D_REGISTER_CLEAR': ('Clear register',
kb2strL(r'''
Are you sure you want to clear the contents
of this register?

This action is not recoverable!

Press "|{y}|" to confirm, or "|{n}|" to cancel

'''
), Priority.HIGH),

    'D_REGISTERS_CLEAR_ALL': ('Clear All Registers',
kb2strL(r'''
Are you sure you want to clear the contents
of all the registers?

This action is not recoverable!

Press "|{y}|" to confirm, or "|{n}|" to cancel

'''
), Priority.HIGH),

    'M_REGISTER_SAVE_ERROR': ('Error',
r'''
Error saving register file:
__"|{}|"

''', Priority.HIGH
),

    'H_EXTRA': ('Extra Commands Help',
kb2str(r'''{open_extra}       <*> Open previous playlist.
{hist_top}                    <*> Open first opened playlist.
{buffer} {open_buffer}        <*> Set player |b|uffering.
{toggle_time}                 <*> Toggle |t|ime display.
{toggle_tts}                  <*>  Toggle TTS.
{last_playlist}               <*> Toggle |Open last playlist|.
{change_player}               <*> Cahnge |m|edia player.
{new_playlist}                <*> Create a |n|ew playlist.
{paste}                       <*> Select playlist / register to |p|aste to.
{rename_playlist}             <*> |R|ename current playlist.
{clear_all_reg}               <*> |C|lear all registers.
{unnamed}                     <*> Show |U|nnamed Register.
{open_dirs}                   <*> |O|pen dirs in file manager.
{station_volume}              <*>  Save station |v|olume.
{toggle_station_volume}       <*>  Toggle use of station |V|olume.

Any other key exits current mode.
'''
), Priority.HELP),

    'H_EXTRA_REG': ('Extra Commands Help',
kb2str(r'''{open_extra}       <*> Open previous playlist.
{hist_top}                    <*> Open first opened playlist.
{buffer} {open_buffer}        <*> Set player |b|uffering.
{toggle_time}                 <*> Toggle |t|ime display.
{toggle_tts}                  <*>  Toggle TTS.
{last_playlist}               <*> Toggle |Open last playlist|.
{change_player}               <*> Cahnge |m|edia player.
{new_playlist}                <*> Create a |n|ew playlist.
{paste}                       <*> Select playlist / register to |p|aste to.
{rename_playlist}             <*> |R|ename current playlist.
{clear_reg}                   <*> Clear |c|urrent register.
{unnamed}                     <*> Show |U|nnamed Register.
{open_dirs}                   <*> |O|pen dirs in file manager.
{station_volume}              <*>  Save station |v|olume.
{toggle_station_volume}       <*>  Toggle use of station |V|olume.

Any other key exits current mode.
'''
), Priority.HELP),

    'H_EXTRA_REGISTERS_LIST': ('Extra Commands Help',
kb2str(r'''{rename_playlist}  <*> |R|ename current register.
{paste}                       <*> |P|aste to current register.
{clear_reg}                   <*> Clear |c|urrent register.
{clear_all_reg}               <*> |C|lear all registers.
{unnamed}                     <*> Show |U|nnamed Register.
{open_dirs}                   <*> |O|pen dirs in file manager.
{station_volume}              <*>  Save station |v|olume.
{toggle_station_volume}       <*>  Toggle use of station |V|olume.
{toggle_time}                 <*> Toggle |t|ime display.
{toggle_tts}                  <*>  Toggle TTS.

Any other key exits current mode.
'''
), Priority.HELP),

    'H_EXTRA_PLAYLIST': ('Extra Commands Help',
kb2str(r'''{new_playlist}     <*> Create a |n|ew playlist.
{paste}                       <*> |P|aste to current playlist.
{rename_playlist}             <*> |R|ename current playlist.
{unnamed}                     <*> Show |U|nnamed Register.
{open_dirs}                   <*> |O|pen dirs in file manager.

|Any other key exits current mode.
'''
), Priority.HELP),

    'D_RB_OPEN': ('',
r'''Connecting to service.
____Please wait...''', Priority.NORMAL
),

    'D_RB_SEARCH': ('',
r'''__Performing search.__
 ____Please wait...''', Priority.NORMAL
),

    'M_RB_UNKNOWN_SERVICE': ('Unknown Service',
r'''
The service you are trying to use is not supported.

The service "|{0}|"
(url: "|{1}|")
is not implemented (yet?)

If you want to help implementing it, please open an
issue at "|https://github.com/coderholic/pyradio/issues|".

''', Priority.HIGH
),

    'H_RB_NO_PING': ('Servers Unreachable',
r'''No server responds to ping.

You will be able to edit the config file, but
you will not be able to select a default server.

''', Priority.HIGH
),

    'H_RB_SEARCH': ('RadioBrowser Search Help',
kb2str(r'''Tab| / |Sh-Tab           <*> Go to next / previous field.
{j}|, |Up| / |{k}|, |Down           <*> Go to next / previous field vertivally.
{h}|, |Left| / |{l}|, |Right        <*>
                                    <*> Go to next / previous field (when
                                    <*> applicable). Also, change counter value.
{pause}                             <*> Toggle check buttons.
                                    <*> Toggle multiple selection.
Enter                               <*> Perform search / cancel (on push buttons).
{s}                                 <*> Perform search (not on Line editor).
Esc                                 <*> Cancel operation.
_
Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_RB_CONFIG': ('RadioBrowser Config Help',
kb2str(r'''Tab| / |Sh-Tab|,                <*>
{j}|, |Up| / |{k}|, |Down                  <*> Go to next / previous field.
{h}|, |Left| / |{l}|, |Right               <*> Change |auto save| and |counters| value.
                                           <*> Navigate through |Search Terms|.
{g}|, |{G}|, |Home|, |End|,                <*>
PgUp|, |PgDn                               <*> Navigate through |Search Terms|.
{pause}|, |Enter                           <*> Toggle |auto save|  value.
                                           <*> Open |Server Selection| window.
{revert_saved}| / |{revert_def}                             <*> Revert to |saved| / |default| values.
{s}                                        <*> Save config.
Esc                                        <*> Exit without saving.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}    <*>  Change volume.
{mute}| / |{s_vol}                         <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                          <*>Toggle title log / like a station.'''
), Priority.HELP),

    'D_RB_ASK_TO_SAVE_CONFIG': ('Online Browser Config not Saved!',
kb2strL(r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |{y}| to save it or |n| to disregard it.
'''
), Priority.HIGH),

    'D_RB_ASK_TO_SAVE_CONFIG_FROM_CONFIG': ('Online Browser Config not Saved!',
kb2strL(r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |{y}| to save it or |{n}| to disregard it.
'''
), Priority.HIGH),

    'D_RB_ASK_TO_SAVE_CONFIG_TO_EXIT': ('Online Browser Config not Saved!',
kb2strL(r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |{y}| to save it or |{n}| to disregard it.
'''
), Priority.HIGH),

    'M_RB_CONFIG_SAVE_ERROR': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure there is enought free space in___
___the file system and try again.___

''', Priority.HIGH
),

    'M_RB_CONFIG_SAVE_ERROR_WIN': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure that the configuration file___
___is not opened in another application and that___
___there is enough free space in the drive and ___
___try again.___

''', Priority.HIGH
),

    'M_RB_VOTE_RESULT': ('Station Vote Result',
r'''
You have just voted for the following station:
____|{0}|

Voting result:
____|{1}|

''', Priority.HIGH
),

    'M_RB_VOTE': ('',
r'''
___Voting for station._____
_____Please wait...'

''', Priority.HIGH
),

    'M_RB_EDIT_URL_ERROR': ('Error',
r'''
____Errorenous Station Data provided!___

_________Station URL is invalid!___
___Please provide a valid Station URL.___

''', Priority.HIGH
),

    'M_RB_EDIT_INCOMPLETE_ERROR': ('Error',
r'''
____Incomplete Station Data provided!___

_________Station URL is empty!___
___Please provide a valid Station URL.___

''', Priority.HIGH
),

    'M_RB_EDIT_NAME_ERROR': ('Error',
r'''
___Incomplete Station Data provided!___

____Please provide a Station Name.___

''', Priority.HIGH
),

    'M_RB_EDIT_ICON_ERROR': ('Error',
r'''
______Errorenous Station Data provided!___

________Station Icon URL is invalid!___
___Please provide a valid Station Icon URL.___

''', Priority.HIGH
),

    'M_RB_EDIT_ICON_FORMAT_ERROR': ('Error',
r'''
______Errorenous Station Data provided!___

________Station Icon URL is invalid!___
____It must point to a JPG or a PNG file.__
___Please provide a valid Station Icon URL.___

''', Priority.HIGH
),

    'M_RB_EDIT_REF_ERROR': ('Error',
r'''
______Errorenous Referrer Data provided!___

________Referrer URL is invalid!___
___Please provide a valid Referrer URL.___

''', Priority.HIGH
),

    'D_ASK_TO_UPDATE_STATIONS_CSV': ('Stations update',
kb2strL(r'''
|PyRadio| default stations (file "|stations.csv|") has been
updated upstream.

Do you want to update your "|stations.csv|" file with the
upstream changes?

Press |{y}| to update, |{n}| to decline and not be asked again
for this version, or any other key to close this window
and be asked next time you execute |PyRadio|.

'''
), Priority.HIGH),

    'M_UPDATE_STATIONS_RESULT': ('', ''),

    'H_CONFIG': ('Configuration Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                  <*>
Down|, |{k}|, |PgDown                           <*> Change option selection.
{g}|, |Home| / |{G}|, |End                      <*> Jump to first / last option.
Enter|, |{pause}|, |Right|, |{l}                <*> Change option value.
{revert_saved}                                  <*> Revert to saved values.
{search} |/ |{search_next}| / |{search_prev}    <*> Search, go to next / previous result.
t                                               <*> TTS test.
{revert_def}                                    <*> Load default values.
{s}                                             <*> Save config.
Esc|, |{q}|, |Left|, |{h}                       <*> Cancel.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_CONFIG_STATION': ('Station Selection Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                   <*>
Down|, |{k}|, |PgDown                            <*> Change station selection.
{g}| / |<n>G                                     <*> Jump to first or n-th / last station.
{screen_middle}                                  <*> Jump to the middle of the list.
Enter|, |{pause}|,                               <*>
Right|, |{l}                                     <*> Select default station.
{search} |/ |{search_next}| / |{search_prev}     <*>  Search, go to next / previous result.
{revert_saved}                                   <*> Revert to saved value.
Esc|, |{q}|, |Left|, |{h}                        <*> Canel.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}          <*>  Change volume.
{mute}| / |{s_vol}                               <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                                <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_CONFIG_PLAYER': ('Player Selection Help',
kb2str(r'''TAB|                                 <*> Move selection to |Extra Parameters| column.
Up|, |{j}|, |Down|, |{k}|                       <*> Change player selection.
Enter|, |{pause}|,                              <*>
Right|, |{l}                                    <*> Enable / disable player.
^U| / |^D|                                      <*> Move player |u|p or |d|own.
{revert_saved}|                                 <*> Revert to saved values.
{s}|                                            <*> Accept changes (player and parameters).
|                                               <*> |Notice|: Changes will be saved only after pressing
|                                               <*> ________"|{s}|" in the main |Configurationw Window|.
Esc|, |{q}|, |Left|, |{h}                       <*> Canel.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_CONFIG_PLAYLIST': ('Playlist Selection Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                  <*>
Down|, |{k}|, |PgDown                           <*> Change playlist selection.
{g}| / |<n>[G}                                  <*> Jump to first or n-th / last playlist.
Enter|, |{pause}|,                              <*>
Right|, |{l}                                    <*> Select default playlist.
{search} |/ |{search_next}| / |{search_prev}    <*>  Search, go to next / previous result.
{revert_saved}                                  <*> Revert to saved value.
Esc|, |{q}|, |Left|, |{h}                       <*> Canel.
%Global functions (with \ on Line editor)
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_CONFIG_ENCODING': ('Encoding Selection Help',
kb2str(r'''Arrows|, |{h}|, |{j}|, |{k}|,        <*>
{l}|, |PgUp|, |,PgDn                            <*>
{g}|, |Home|, |{G}|, |End                       <*> Change encoding selection.
Enter|, |{pause}|, |{s}                         <*> Save encoding.
{revert_saved} {revert_def}                     <*> Revert to station / config value.
Esc|, |{q}                                      <*> Cancel.
%Global functions
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'M_CONFIG_SAVE_ERROR': ('Error Saving Config',
r'''An error occured while saving the configuration file!

|PyRadio| will try to |restore| your previous settings,
but in order to do so, it has to |terminate now!

''', Priority.HIGH
),

    'H_DIR': ('Open Directory Help',
kb2str(r'''Up|, |{j}|, |PgUp|,                  <*>
Down|, |{k}|, |PgDown                           <*> Change Directory selection.
{g} {G}                                         <*> Go to first / last Directory.
{pause}|, |Right|,                              <*>
{l}|, |Enter                                    <*> Open a Directory.
1| - |{}                                        <*> Open corresponding Directory.
Esc|, |{q}                                      <*> Cancel.
%Global functions
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*>  Change volume.
{mute}| / |{s_vol}                              <*>  |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'H_SEARCH': ('Search Help',
kb2str(r'''Left| / |Right           <*> Move to next / previous character.
Up| / |Down                         <*> Cycle within history.
M-F| / |M-B                         <*> Move to next / previous word.
Home|, |^A| / |End|, |^E            <*> Move to start / end of line.
^W| / |M-D|, |^K                    <*> Clear to start / end of line.
^U                                  <*> Clear line.
^X                                  <*> Remove history item.
Del|, |^D                           <*> Delete character.
Backspace|, |^H                     <*> Backspace (delete previous character).
Up|, |^P| / |Down|, |^N             <*> Get previous / next history item.
\?| / |\\                           <*> Insert a "|?|" or a "|\|", respectively.
Enter| / |Esc                       <*> Perform / cancel search.

Global functions work when preceded with a "|\|".
'''
), Priority.HELP),

    'H_SEARCH_DARWIN': ('Search Help',
kb2str(r'''Left| / |Right           <*> Move to next / previous character.
Home|, |^A| / |End|, |^E            <*> Move to start / end of line.
^W| / |^K                           <*> Clear to start / end of line.
^U                                  <*> Clear line.
Del|, |^D                           <*> Delete character.
Backspace|, |^H                     <*> Backspace (delete previous character).
Up|, |^P| / |Down|, |^N             <*> Get previous / next history item.
\?| / |\\                           <*> Insert a "|?|" or a "|\|", respectively.
Enter| / |Esc                       <*> Perform / cancel search.

Global functions work when preceded with a "|\|".
'''
), Priority.HELP),

    'H_EXTERNAL_LINE_EDITOR': ('', Priority.HELP),

    'H_LINE_EDITOR': ('Line Editor Help',
kb2str(r'''Left| / |Right           <*> Move to next / previous character.
Home|, |^A| / |End|, |^E            <*> Move to start / end of line.
^W| / |^K                           <*> Clear to start / end of line.
^U                                  <*> Clear line.
Del|, |^D                           <*> Delete character.
Backspace|, |^H                     <*> Backspace (delete previous character).
Up| / |Down                         <*> Go to previous / next field.
\?| / |\\                           <*> Insert a "|?|" or a "|\\|", respectively.
Esc                                 <*> Cancel operation.

Global functions work when preceded with a "|\|".

'''
), Priority.HELP),

    'H_LINE_EDITOR_DARWIN': ('Line Editor Help',
kb2str(r'''Left| / |Right           <*> Move to next / previous character.
M-F| / |M-B                         <*> Move to next / previous word.
Home|, |^A| / |END|, |^E            <*> Move to start / end of line.
^W| / |M-D|,|^K                     <*> Clear to start / end of line.
^U                                  <*> Clear line.
Del|, |^D                           <*> Delete character.
Backspace|, |^H                     <*> Backspace (delete previous character).
Up| / |Down                         <*> Go to previous / next field.
\?| / |\\                           <*> Insert a "|?|" or a "|\\|", respectively.
Esc                                 <*> Cancel operation.

Global functions work when preceded with a "|\|".

'''
), Priority.HELP),

    'M_SESSION_LOCKED': (M_STRINGS['session-locked-title'],
'''
This session is |locked| by another |PyRadio instance|.

You can still play stations, load and edit playlists,
load and test themes, but any changes will |not| be
recorded in the configuration file.

If you are sure this is the |only| active |PyRadio|
instance, exit |PyRadio| now and execute the following
command: |pyradio --unlock|

''', Priority.HIGH
),

    'M_NO_PLAYLIST': ('Error',
r'''
|No playlists found!!!

This should |never| have happened; |PyRadio| is missing its
default playlist. Therefore, it has to |terminate| now.
It will re-create it the next time it is lounched.
''', Priority.HIGH
),

    'D_RC_ACTIVE': ('Remote Control Enabled',
r'''
|PyRadio Remote Control Server| is active!

Text Address: |http://{0}
_Web Address: |http://{0}/html____

Press "|{s}|" to stop the server, or'''.replace('{s}', chr(kbkey['s']))
, Priority.DIALOG),

    'M_RC_START_ERROR': ('Server Error',
r'''
The Remote Control Server |failed| to start!
The error message is:
__|{}

This is probably because another (|PyRadio?|) process
is already using the requested |Server Port|.

Close this window, press "|\s|", select a |different
|port| and try to start the |Server| again.

''', Priority.HIGH
),

    'M_RC_DEAD_ERROR': ('Server Error',
r'''
The Remote Control Server |terminated| with
message:
__|{}

''', Priority.HIGH
),

    'M_RC_LOCKED': ('Not Available',
r'''
______This session is |locked|, so the
__|Remote Control Server| cannot be started!__

''', Priority.HIGH
),

    'D_UPDATE_NOTIFICATION': ('New Release!',
kb2strL(r'''
|PyRadio| release |{0}| is available!

You are strongly encouraged to update now, so that
you enjoy new features and bug fixes.

Press |{y}| to update or any other key to cancel.
'''
), Priority.HIGH),

    'M_UPDATE_NOTIFICATION_OK': ('Update Notification',
r'''
|PyRadio| will now be updated!

The program will now terminate so that the update_
procedure can start.

Press any key to exit |PyRadio|.

''', Priority.HIGH
),

    'M_UPDATE_NOTIFICATION_OK_WIN': ('Update Notification',
r'''
|PyRadio| will now terminate and the update script
 will be created.

When Explorer opens please double click on
"|update.bat|" to start the update procedure.

Press any key to exit |PyRadio|.

''', Priority.HIGH
),

    'M_REC_ENABLED': ('Recording Enable',
r''' _____Next time you play a station,
_____it will be |written to a file|!

A |[r]| at the right top corner of the window
indicates that recording is |enabled|.
A |[R]| indicates that a station is actually
|being recorded| to a file.

Press |{x}| to not show this message again, or'''.replace('{x}', chr(kbkey['no_show']))
, Priority.HIGH),

    'M_REC_DISABLED': ('Recording Disabled',
r'''
Recording will actually continue until
you stop the playback of the station!

''', Priority.HIGH
),

    'M_REC_NOT_SUPPORTED': ('Recording not supported!',
r'''
|VLC| on |Windows| does not support recording.

If you really need to record a station, please use one
of the other two supported players, preferably |MPV|.

To use one of them (|MPV| or |MPlayer|), close this window
and press |\m| to activate it.

If none of them is installed, close this window and
press |F8| to get to the player installation window.

'''.replace('|F8|', chr(kbkey['F8']))
, Priority.HIGH),

    'M_REC_IS_ON_NO_DIR': ('Recording is active',
r'''
|PyRadio| is currently recording a station!

Changing the |Recording Directory| while recording a
station is not allowed.

Please stop the playback of the station (effectively
stopping the recording) and try again.

''', Priority.HIGH
),

    'M_REC_IS_ON_NO_DIR_HEADLESS': ('Recording is active',
r'''
A |headless PyRadio| instance at |{}| is
currently recording a station!

Changing the |Recording Directory| while recording a
station is not allowed.

Please stop the playback of the station (effectively
stopping the recording) and try again.

''', Priority.HIGH
),

    'M_RESOURCE_OPENER': ('Resource Opener Help',
r'''A |Resource Opener| is a program used to open files passed to it
as arguments.

|PyRadio| will use it to open either directories or HTML files.

Default value is "|auto|", in which case, |PyRadio| will try to use
|xdg-open|, |gio|, |mimeopen|, |mimeo| or |handlr|, in that order of
detection. If none if found, the requested file will simply not
open.

To set a |Custom Opener|, insert its name (either absolute path
to its executable or its name, if it is in your |PATH|), followed
by any parameter required, for example: "|/usr/bin/gio open|",
"|mimeopen -n|", "|xdg-open|".
''', Priority.HELP
),

    'M_REC_DIR_HELP': ('Recordings Dir Help',
r'''|PyRadio| will record stations to files and save them in the
directory specified here.

When a new directory is specified, |PyRadio| will try to |move| the
existing directory to the new location.

If the new directory...
1. |does not exist|
___|PyRadio| will move the original directory to the new location
___and optionally rename it.
2. |already exists and is empty|
___|PyRadio| will |delete| the new directory and |move| the original
___directory to the new location and optionally rename it.
3. |already exists and is not empty|
___|PyRadio| will |move| the original directory |inside| the new
___directory and optionally rename it.
''', Priority.HELP
),

    'M_REC_DIR_MOVE': ('',
r'''
______Moving |Recordings Directory______
____________Please wait...

''', Priority.HIGH
),

    'M_REC_DIR_MOVE_ERROR': ('Error',
r'''
______Moving |Recordings Directory| has |failed!!|______
Moving from
|{}|
to
|{}|

Press any key to open the directories in file explorer...

''', Priority.HIGH
),

    'M_MANAGE_PLAYERS_WIN': ('Players Management',
r'''
Players management |enabled|!

|PyRadio| will now terminate so that you can
|manage| installed players.

''', Priority.HIGH
),

    'D_UNINSTALL_WIN': ('Uninstall PyRadio',
kb2strL(r'''
Are you sure you want to uninstall |PyRadio|?

Please press |{y}| to confirm or any other key
to decline.

'''
), Priority.HIGH),

    'M_REMOVE_OLD_INSTALLATION': ('PyRadio',
r'''
|PyRadio| will now try to remove any files found on your
system belonging to a pre |0.8.9.15| installation.

''', Priority.HIGH
),

    'M_SHOW_UNNAMED_REGISTER': ('Unnamed Register',
r'''
___{}___

''', Priority.DIALOG
),

    'M_CHANGE_PLAYER_ONE_ERROR': ('PyRadio',
r'''
You have requested to change the |Media Player| but
there's only one player detected.

If you have already installed any other player
(|{0}| or |{1}|), please make sure its executable
is in your PATH.

''', Priority.HIGH
),

    'M_CHANGE_PLAYER_THE_SAME_ERROR': ('PyRadio',
r'''
|{}|: Media Player already active.

You have requested to change the |Media Player| to
the one that's already active.

Please try selecting a different |Media Player|.

''', Priority.HIGH
),

    'M_NOT_IMPLEMENTED': ('PyRadio',
r'''
___This feature has not been implemented yet...___

''', Priority.HIGH
),

    'M_FOREIGN': ('Foreign playlist',
r'''
A playlist by this name:
__"|{0}|"
already exists in the config directory.

This playlist was saved as:
__"|{1}|"

''', Priority.HIGH
),

    'M_FOREIGN_ERROR': ('Error',
r'''
Foreign playlist copying |failed|!

Make sure the file is not open with another
application and try to load it again

''', Priority.HIGH
),

    'D_FOREIGN_ASK': ('Foreign playlist',
kb2strL(r'''
This is a "|foreign|" playlist (i.e. it does not
reside in PyRadio's config directory). If you
want to be able to easily load it again in the
future, it should be copied there.

Do you want to copy it in the config directory?

Press "|{y}|" to confirm or "|{n}|" to reject

'''), Priority.HIGH
),

    'M_NO_THEMES': ('Themes Disabled',
r'''|Curses| (the library this program is based on), will not display
colors |correctly| in this terminal, (after they have been |changed by
PyRadio.

Therefore, using |themes is disabled| and the |default theme| is used.

For more info, please refer to:
|https://github.com/coderholic/pyradio/#virtual-terminal-restrictions

Press "|{x}|" to never display this message in the future, or
'''.replace('{x}', chr(kbkey['no_show'])), Priority.HIGH
),

    'M_REQUESTS_ERROR':('Module Error',
r'''
Module "|requests|" not found!

In order to use |RadioBrowser| stations directory
service, the "|requests|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-requests| or |python{}-requests|) and try
executing |PyRadio| again.

''', Priority.HIGH
),

    'M_NETIFACES_ERROR':('Module Error',
r'''
Module "|netifaces|" not found!

In order to use |RadioBrowser| stations directory
service, the "|netifaces|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-netifaces| or |python{}-netifaces|) and try
executing |PyRadio| again.

''', Priority.HIGH
),

    'M_DNSPYTHON_ERROR':('Module Error',
r'''
Module "|dnspython|" not found!

In order to use |RadioBrowser| stations directory
service, the "|dnspython|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-dnspython| or |python{}-dnspython|) and try
executing |PyRadio| again.

''', Priority.HIGH
),

    'X_THEME_DOWN_FAIL': ('',
r'''
____|Theme download failed!!!|____
_____Loading |default| theme..._____

''', Priority.HIGH
),

    'M_PARAMETER_ERROR': ('Parameter Set Error',
r'''
The player parameter set you specified does
not exist!

|{0}| currently has |{1}| sets of parameters.
You can press "|{Z}|" to access them, after you
close this window.

'''.replace('{Z}', chr(kbkey['extra_p_pamars']))
, Priority.HIGH),

    'X_PLAYER_CHANGED':('',
r'''
|PyRadio| default player has changed from
__"|{0}|"
to
__"|{1}|".

This change may lead to changing the player used,
and will take effect next time you open |PyRadio|.

''', Priority.HIGH
),

    'M_SCHEDULE_INFO': ('Schedule Entry Info',
r'''{}
''', Priority.HIGH
),

    'M_SCHEDULE_ERROR': ('Schedule Error',
r'''
___|{}___

''', Priority.HIGH
),

    'M_SCHEDULE_EDIT_HELP': ('Schedule Editor Help',
kb2str(r'''Tab|, |L| / |Sh-Tab|, |H             <*>Go to next / previous field.
{j}|, |Up| / |{k}|, |Down                       <*>Go to next / previous field vertivally.
                                                <*>Go to next / previous field (when
                                                <*>applicable). Also, change counter value.
{pause}                                         <*>Toggle check buttons.
n                                               <*>Set current date and time to section.
0|-|9                                           <*>Add hours to |Start| or |Stop| section.
t| / |f                                         <*>Copy date/time |t|o/|f|rom complementary field.
i                                               <*>Validate entry and show dates.
Enter                                           <*>Perform search / cancel (on push buttons).
s                                               <*>Perform search (not on Line editor).
Esc                                             <*>Cancel operation.

%Global functions
{v_dn2}|/|{v_up1} or |{v_dn1}|/|{v_up2}         <*> Change volume.
{mute}| / |{s_vol}                              <*> |M|ute player / Save |v|olume.
{t_tag}| / |{tag}                               <*>Toggle title log / like a station.'''
), Priority.HELP),

    'M_KEYBOARD_HELP':('Keyboard Shortcuts Help',
r'''
The |Keyboard Shortcuts| window will display a list of shortcuts in
four columns:
__|Actions|  Available actions.
__|Default|  The default key for the item.
__|User|___  User custom key for the item (saved value).
__|New|____  Latest change (not saved yet).

The following action are available:
''' + self._format_columns(kb2str(
r'''
__|Arrow Keys|, |{j}|, |{k}|,            <*>
__|PgUp|, |PgDown|                       <*> Move up, down, etc.
__|Tab|, |{tab}| / |Sh-Tab|, |{stab}|    <*> Move to next / previous field.
__|{g}| / |{G}|                          <*> Go to top / bottom of the list.
__|[| / |]|                              <*> Move between sections.
__{search} |/ |{search_next}| / |{search_prev}    <*>  Search, go to next / previous result.
__|{revert_def}| / |{revert_saved}|      <*> Revert to default / saved shortcuts.
__|x|                                    <*> Revert current item to saved value.
__|f|                                    <*> Show |free| keys.
__|t|                                    <*> |T|alk the current item.
__|Enter|, |{pause}|,                    <*>
__|Right|, |{l}|                         <*> Enter |editing mode| (insert new shortcut).
__|Esc|                                  <*>Exit |editing mode|.
__|0|                                    <*> Switch between |c|ocnflicting items.
                                         <*>Available in |editing mode| as well.
__|{?}|                                  <*>Display this help screen.
''')) + r'''

To change a |Keyboard Shortcut|, just enter the |editing mode|. This will
be indicated by a "|[edit]|" appearing at the right of the line. Press
any key to change the shortcut, or |Esc| to cancel the operation.

After you have finished customizing the shortcuts, navigate to the |OK|
button to save and activate your new shortcuts.

Keep in mind that this is the only window in |PyRadio| that will not be
closed when "|Esc|" is pressed; you will have to navigate to the |Cancel|
button and press it, instead.

|Important Notice on Shortcut Customization

As you customize your shortcuts, please be aware that adding a new
shortcut triggers a |validation| procedure.

The system is designed to be |context-aware|; if the new key you choose
is already in use, it will check whether it conflicts within the same
context. In such cases, an error message will be displayed, and the
change will be rejected.

However, we recognize that there may be instances where conflicting
keys go undetected by the system. We kindly ask you to keep an eye
out for any such conflicts. If you encounter a situation where a
shortcut |seems to be causing issues| without triggering a validation
error, please |report| this incident to us, at this URL:

____|https://github.com/coderholic/pyradio/issues

Thank you for your cooperation.
''', Priority.HELP
),

    'M_INVALID_KEY_ERROR':('Invalid Key',
r'''
The key pressed is |invalid|!

Please do not use any keys like |Home|, |End|,
|PgUp|, |PgDown|, |Arrow Keys|, etc. here.

''', Priority.DIALOG
),

    'M_INVALID_TYPE_KEY_ERROR':('Invalid Key',
r'''
The key pressed is |invalid|!

Please use ASCII characters, punctuation and
Control characters |only| for |PyRadio Shortcuts|.

''', Priority.DIALOG
),

    'M_NOT_CTRL_KEY_ERROR':('Invalid Key',
r'''
The key pressed is |invalid|!

Please use only |Control Characters| here, (|Ctrl+A|
to |Ctrl+Z|, excluding |Ctrl-C|, |Ctrl-S| and |Ctrl-Z| on
Linux and macOS).

Keep in mind that the shortcut's equivalent key
will also work on non-line editor widgets (|n| will
work for |Ctrl-N|, for example).

''', Priority.DIALOG
),

    'M_KEYBOARD_FILE_SAVE_ERROR':('Error Saving File',
r'''
The configuration file could not be saved!
|{0}|

|PyRadio| will open the directory in your file manager
so you can resolve the issue and try again.

''', Priority.HIGH
),

    'M_LOC_HELP': ('Localized Shortcuts Help',
r'''This window allows you to define or edit a keyboard layout that maps
your local language characters to their English equivalents.

__The purpose of this mapping is to ensure that PyRadio responds
correctly to keyboard shortcuts even when your system keyboard layout
is not English. For example, if your layout is Greek and you press
the key corresponding to '|α|', the program will recognize it as the
English '|a|' and trigger the appropriate action.

To create or edit a layout:

__• Select an existing layout to edit (press |{edit}|), or choose "|Define
____|New Layout|" (or press |{add}|) to create one.
__• Use the input grid to map each English letter (lowercase and
____uppercase) to the corresponding character in your local language.
__• When you type a lowercase character, its uppercase version is
____auto-filled, but you can change it manually.

__The |Display| option affects only the visual ordering of keys in the
table (e.g., QWERTY, AZERTY) to help you locate them according to
your physical keyboard. It does |not| affect the functionality or
saved layout.

|Note:|
__• If you attempt to edit a default layout provided with the
____program, you will be asked to use a new name.
__• Your personalized layout will take priority during runtime.

To set the default layout to use, just press |space|, |Enter|, |{l}| or
the |Left Arror| while you are in the "|Available Layouts|" field.
'''.replace('{add}', chr(kbkey['add'])).replace('{edit}', chr(kbkey['edit'])).replace('{l}', chr(kbkey['l']))
, Priority.HELP),

    'M_LOC_READ_ONLY': ('Read-Only Warning',
r'''You are attempting to edit a |read-only| layout.

While it is perfectly fine to customize a layout provided
by |PyRadio|, please note the following:

__1. This is a |read-only| layout file provided by the package.
__2. Your changes will be saved as a new local file.
__3. The local file will override the original layout provided
_____by the package.

Proceed with caution to ensure your customizations do not
unintentionally disrupt functionality.

''', Priority.HIGH
),

        }
        # INSERT NEW ITEMS ABOVE
        if self._db_info_message is not None:
            self._txt['M_DB_INFO'] = self._db_info_message
            self._db_info_message = None
        if self._station_info_message is not None:
            self._txt['M_STATION_INFO'] = self._station_info_message
            self._station_info_message = None
        if self._universal_message is not None:
            self._txt['UNIVERSAL'] = self._universal_message
            self._universal_message = None
        if self._delayed_message is not None:
            self._txt['D_WITH_DELAY'] = self._delayed_message
            self._delayed_message = None
        if self._rb_search_message is not None:
            self._txt['D_RB_SEARCH'] = self._rb_search_message
            self._rb_search_message = None
        if self._external_line_editor is not None:
            self._txt['H_EXTERNAL_LINE_EDITOR'] = self._external_line_editor
            self._external_line_editor = None
        # logger.error('args = "{}"'.format(args))
        '''
            args[0] = message_key
        '''
        self._active_token = None
        self.col_txt = curses.color_pair(10)
        self.col_box = curses.color_pair(3)
        self.col_highlight = curses.color_pair(11)
        if parent is not None:
            self._parent = parent
        if args:
            self.active_message_key = args[0]
        self._get_active_message_key(*args)

        # self._same_content = self.active_message_key == self._last_key
        self._same_content  = False
        # logger.info('self.active_message_key = {} '.format(self.active_message_key))
        # logger.info('self._last_key = {} '.format(self._last_key))
        # logger.info('self._same_content = {} '.format(self._same_content))
        if  self._same_content:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Redisplaying last Messaging System Active key...')
        else:
            self._caption, text, max_len, priority, context = self._get_txt(*args)
            if text is None:
                return None, 0
            if max_len < self._main_win_width or \
                    self.active_message_key in ('M_STATION_INFO', 'M_DB_INFO'):
                self._maxX = max_len
            else:
                self._maxX = self._main_win_width
            # # logger.error('self._caption = "{}"'.format(self._caption))
            # # logger.error('max_len = {0}, self._maxY = {1}'.format(max_len, self._maxX))
            # for n in text:
            #     logger.info(n)
            self._lines_count = len(text)

        self._get_win()

        if not self._same_content:
            self._pad = curses.newpad(self._pad_height, self._maxX - 2)
            self._pad.scrollok(True)
            self._pad_pos = 0
            self._pad_refresh = lambda: self._pad.refresh(
                    self._pad_pos, 0,
                    self._winY+1, self._winX+1,
                    self._maxY+self._winY-2, self._maxX+self._winX-2
            )
            self._pad.bkgd(' ', self.col_txt)
            try:
                self._populate_pad(text)
            except curses.error:
                pass
        self.simple_dialog = False
        self._txt = {}
        return self._caption.strip(), text, priority

    def __init__(self, config, op_mode, prev_op_mode, speak_high):
        self._speak_high = speak_high
        self._args = None
        self._txt = None
        self._active_token = None
        self.col_txt = None
        self.col_box = None
        self.col_highlight = None
        self._parent = None
        self.active_message_key = None
        self.active_message_key = None
        self._caption = None
        self._maxY = 0
        self._maxX = 0
        self._winY = 0
        self._winX = 0
        self._lines_count = 0
        self._pad_pos = 0
        self._pad_refresh = None

        self._win = None
        self._pad = None
        self.too_small = False
        self.simple_dialog = False
        self._same_content = False
        self._same_parent = False
        self._can_scroll= True
        self._last_key = ''
        self._columns = {}
        self._max_lens = {}
        self._tokens = {}
        self._universal_message = None
        self._station_info_message = None
        self._db_info_message = None
        self._delayed_message = None
        self._rb_search_message = None
        self._external_line_editor = None
        self._main_win_width = 73
        self._columnX = 22
        self._cnf = config
        self._pad_height = 32767
        self._operation_mode = op_mode
        self._previous_operation_mode = prev_op_mode

    def set_a_message(self, index, msg):
        if index == 'D_RB_SEARCH':
            self._rb_search_message = msg
        elif index == 'D_WITH_DELAY':
            self._delayed_message = msg
        elif index == 'M_STATION_INFO':
            self._station_info_message = msg
        elif index == 'M_DB_INFO':
            self._db_info_message = msg
        elif index == 'UNIVERSAL':
            self._universal_message = msg
        elif index == 'H_EXTERNAL_LINE_EDITOR':
            self._external_line_editor = msg

    def set_token(self, token):
        self._active_token = None
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('tokens = {}'.format(self._tokens))
        if token in self._tokens:
            self._active_token = self._tokens[token]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('setting self._pad_pos to {}'.format(self._pad_pos))

    def _remove_start_char(self, txt, char):
        if txt.startswith(char):
            return txt[1:]
        return txt

    def _get_txt(self, *args):
        '''
            args[0] = message_key

            Format is:
                (
                    Help Window Caption,
                    r text (string),
                    priority
                )
        '''
        logger.error(f'{args = }')
        # try:
        #     cap, out = self._txt[self.active_message_key]
        # except ValueError:
        #     cap, out, priority = self._txt[self.active_message_key]

        logger.error('\n\nself._txt[self.active_message_key] = {}\n\n'.format(self._txt[self.active_message_key]))

        try:
            cap, out, priority = self._txt[self.active_message_key]
            context = Context.LIMITED
        except ValueError:
            cap, out, priority, context = self._txt[self.active_message_key]
        # logger.info('--> out\n{}'.format(out))
        if out is None:
            logger.error('return None, None, 0, 0, 0')
            return None, None, 0, 0, 0

        ''' apply per item customization / variables '''
        if self.active_message_key == 'H_MAIN' and \
                platform.startswith('win'):
            out = self._txt[self.active_message_key][1].replace(
                    '|opposite ', '|upward ').replace('{| / |[| / |]', 'Sh-F2| / |F2| / |F3')
        elif self.active_message_key == 'H_MAIN' and \
                platform.lower().startswith('darwin'):
            out = self._txt[self.active_message_key][1].replace(
                    '|opposite ', '|upward ')
        elif self.active_message_key == 'H_PLAYLIST':
            if self._cnf.open_register_list:
                out = self._txt[self.active_message_key][1].replace(
                        'playlist', 'register')
                cap=' Registers List Help '
        elif self.active_message_key == 'H_DIR':
            out = self._txt[self.active_message_key][1].format(args[1])
        elif self.active_message_key in ('H_SEARCH', 'H_LINE_EDITOR') and \
                platform.startswith('win'):
            out = self._txt[self.active_message_key][1].replace('M-', 'A-')
        elif self.active_message_key == 'H_CONFIG_ENCODING':
            if self._operation_mode() == Window_Stack_Constants.SELECT_ENCODING_MODE:
                out = out.replace('r c  ', 'r    ').replace(
                        'Revert to station / |c|onfig value.',
                        'Revert to saved value.'
                        )
        elif self.active_message_key in self._one_arg_list:
            out = self._txt[self.active_message_key][1].format(args[1])
        elif self.active_message_key in self._two_arg_list:
            out = self._txt[self.active_message_key][1].format(args[1], args[2])
        elif self.active_message_key in self._second_arg_is_a_function:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('setting {} text to result of {}'.format(self.active_message_key, args[1]))
            self._txt[self.active_message_key] = args[1]()
            out = self._txt[self.active_message_key][1]

        self._tokens, cleaned_text = self._parse_strings_for_tokens(out.splitlines())
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('tokens = {}'.format(self._tokens))
        # get max len
        if logger.isEnabledFor(logging.INFO):
            logger.info('>>> Message System: setting key to "{}"'.format(self.active_message_key))
            self._last_key = self.active_message_key
        if self.active_message_key == 'H_MAIN':
            mmax = self._main_win_width
            column = 22
        else:
            first_column = []
            last_column = []
            if self.simple_dialog:
                column = 0
            else:
                if self.active_message_key in self._columns:
                    column =  self._columns[self.active_message_key]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('column from self._columns = {}'.format(column))
                else:
                    for n in cleaned_text:
                        x = n.split('<*>')
                        if len(x) == 2:
                            first_column.append(x[0].strip().replace('%', '').replace('|', ''))
                            first_column[-1] = self._remove_start_char(first_column[-1], '!')
                    if first_column:
                        column = max(len(x) for x in first_column) + 5
                    else:
                        column = 0
                    self._columns[self.active_message_key] = column
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('column from calculation = {}'.format(column))
            if self.active_message_key in self._max_lens:
                mmax =  self._max_lens[self.active_message_key]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('max len from self._max_lens = {}'.format(mmax))
            else:
                # logger.error(f'{cleaned_text = }')
                for n in cleaned_text:
                    x = n.split('<*>')
                    if len(x) == 2:
                        first_column.append(x[0].strip().replace('|', ''))
                        first_column[-1] = self._remove_start_char(first_column[-1], '!')
                        first_column[-1] = self._remove_start_char(first_column[-1], '%')
                        x[-1] = '-' * (column + 2) + x[-1]
                    last_column.append(x[-1].strip().replace('|', ''))
                    last_column[-1] = self._remove_start_char(last_column[-1], '!')
                    last_column[-1] = self._remove_start_char(last_column[-1], '%')
                    if len(x) == 1 and last_column[-1]:
                        last_column[-1] += 4 * ' '
                    mmax = max(len(x) for x in last_column)
                    mmax += mmax % 2
                self._max_lens[self.active_message_key] = mmax
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('max len from calculation = {}'.format(mmax))
        self._columnX = column
        if self.active_message_key in self._reset_metrics:
            self._columns.pop(self.active_message_key, None)
            self._max_lens.pop(self.active_message_key, None)
        # logger.error('self._max_lens\n{}'.format(self._max_lens))
        mmax = max(mmax, len(cap) + 6)
        ''' replaced by pylint prompt
        if mmax < len(cap) + 6:
            mmax = len(cap) + 6
        '''
        # logger.error('\n\n===> mmax = {}\n\n'.format(mmax))
        logger.error('cap = {}'.format(cap))
        logger.error('mmax = {}'.format(mmax))
        logger.error('cleaned_text = {}'.format(cleaned_text))
        logger.error('priority = {}'.format(priority))
        logger.error('context = {}'.format(context))
        return cap, cleaned_text, mmax, priority, context

    def _get_active_message_key(self, *args):
        if args:
            self.active_message_key = args[0] if args[0] else 'H_MAIN'
            # logger.error('args[0] = {}'.format(args[0]))
            # try:
            #     logger.error('args[1] = {}'.format(args[1]))
            # except:
            #     logger.error('args[1] = N/A')
        ''' self.active_message_key transformation '''
        if self.active_message_key == 'H_SEARCH' and \
                platform.startswith('darwin'):
            self.active_message_key = 'H_SEARCH_DARWIN'
        elif self.active_message_key == 'H_EXTRA':
            # if self._operation_mode() == Window_Stack_Constants.NORMAL_MODE or \
            #             (self._operation_mode() == Window_Stack_Constants.HELP_MODE and \
            #             self._previous_operation_mode() == Window_Stack_Constants.NORMAL_MODE):
            #     if self._cnf.is_register:
            #         out = self._txt[self.active_message_key][1].replace('C   ', 'c  ').replace(
            #                 'current playlist', 'current register').replace(
            #                     '|C|lear all registers.', 'Clear |c|urrent register.')
            if self._operation_mode() == Window_Stack_Constants.NORMAL_MODE:
                if self._cnf.is_register:
                    self.active_message_key='H_EXTRA_REG'
            else:
                if self._cnf.open_register_list:
                    self.active_message_key = 'H_EXTRA_REGISTERS_LIST'
                else:
                    self.active_message_key = 'H_EXTRA_PLAYLIST'
        elif self.active_message_key == 'H_LINES_EDITOR':
            if platform.lower().startswith('dar'):
                self.active_message_key = 'H_LINE_EDITOR_DARWIN'
        elif self.active_message_key == 'M_UPDATE_NOTIFICATION_OK' and \
                platform.startswith('win'):
            self.active_message_key = 'M_UPDATE_NOTIFICATION_OK_WIN'
        elif self.active_message_key == 'M_RB_CONFIG_SAVE_ERROR' and \
                platform.startswith('win'):
            self.active_message_key = 'M_RB_CONFIG_SAVE_ERROR_WIN'

    def _parse_strings_for_tokens(self, text):
        token_dict = {}
        if self.simple_dialog:
            cleaned_text = text
        else:
            cleaned_text = []
            pattern = re.compile(r'<!--(.*?)-->')
            for i, line in enumerate(text):
                match = pattern.search(line)
                while match:
                    token = match.group(1)
                    token_dict[token] = i
                    # Remove "<!--" + token + "-->" from the line
                    line = line[:match.start()] + line[match.end():]
                    match = pattern.search(line)
                cleaned_text.append(line)
        return token_dict, cleaned_text

    def _show_too_small(self):
        p_height, p_width = self._parent.getmaxyx()
        self.too_small = True
        self._can_scroll = False
        txt = ' Window too small '
        self._maxY = 3
        self._maxX = len(txt) + 2
        # logger.error(f'too small maxX = {self._maxX}')
        self._winY = int((p_height - 3) / 2) + self._parent.getbegyx()[0]
        self._winX = int((p_width - self._maxX) / 2)
        if p_height > self._winY and p_width > self._winX:
            self._win = curses.newwin(
                    self._maxY,
                    self._maxX,
                    self._winY,
                    self._winX
                )
            self._win.bkgd(' ', self.col_box)
            self._win.box()
            self._win.addstr(1, 1, txt, self.col_txt)
        else:
            self._win = None

    def _get_win(self):
        p_height, p_width = self._parent.getmaxyx()
        self._maxY = p_height - 2
        # self._maxX = self._main_win_width
        if p_width < self._maxX or self._maxY < 10:
            self._show_too_small()
            return

        self.too_small = False
        pY, pX = self._parent.getbegyx()
        p_height, p_width = self._parent.getmaxyx()
        if self._lines_count + 2 <= self._maxY:
            self._can_scroll = False
            self._maxY = self._lines_count + 2
            self._winY = int((p_height - self._maxY) / 2) + pY
        else:
            if self.active_message_key in(
                    'M_STATION_INFO',
                    'M_DB_INFO'):
                self._show_too_small()
                return
            self._can_scroll = True
            self._winY = int((p_height - self._maxY) / 2) + pY
        # if not ( p_height % 2 ):
        #     self._winY += 1
        self._winX = int((p_width - self._maxX) / 2) + pX
        # logger.error('newwin maxX = {}'.format(self._maxX))
        self._win = curses.newwin(
                self._maxY,
                self._maxX,
                self._winY,
                self._winX
            )
        self._win.bkgd(' ', self.col_box)
        self._win.erase()
        self._win.box()
        if self._can_scroll:
            # if platform.startswith('win') or \
            #         platform.lower().startswith('darwin'):
            #     self._win.addstr(0, self._maxX-1, '^', self.col_box)
            #     self._win.addstr(1, self._maxX-1, '^', self.col_box)
            # else:
            #     self._win.addstr(0, self._maxX-1, '⮝', self.col_box)
            #     self._win.addstr(1, self._maxX-1, '⮟', self.col_box)
            self._win.addstr(0, self._maxX-1, '^', self.col_box)
            # self._win.addstr(1, self._maxX-1, '^', self.col_box)
        if self._caption:
            self._win.addstr(
                    0, int((self._maxX - len(self._caption)) / 2) - 2,
                    ' ' + self._caption + ' ',
                    self.col_highlight
            )
        if not (self.active_message_key.startswith('D') or \
                self.active_message_key.startswith('X') or \
                self._can_scroll
                ):
            prompt = ' Press any key... '
            self._win.addstr(
                    self._maxY-1,
                    self._maxX - len(prompt) - 1,
                    prompt,
                    self.col_box
                    )

    def _echo_line(self, Y, X, formated, reverse=False):
        for k, a_string in enumerate(formated):
            if reverse:
                col = self.col_highlight if k % 2 else self.col_txt
            else:
                col = self.col_txt if k % 2 else self.col_highlight
            if k == 0:
                self._pad.addstr(Y, X, a_string.replace('_', ' '), col)
                # logger.error('printing: {0} - "{1}"'.format(X, a_string))
            else:
                if a_string:
                    self._pad.addstr(a_string.replace('_', ' '), col)
                # logger.error('adding: "{}"'.format(a_string))

    def _populate_pad(self, a_list):
        self._pad.erase()
        for i, n in enumerate(a_list):
            out = n.strip()
            if out.strip().startswith('%'):
                self._pad.addstr(i, 1, '─' * (self._maxX-4), self.col_box)
                self._pad.addstr(i, self._maxX - len(out) - 5, ' ' + out[1:] + ' ', self.col_highlight)
            elif out.strip().startswith('!'):
                self._pad.addstr(i, 1, '─── ', self.col_box)
                self._pad.addstr(out[1:] + ' ', self.col_highlight)
                self._pad.addstr('─' * (self._maxX - len(out[1:]) - 9), self.col_box)
            else:
                lines = out.split('<*>')
                lines = [x.strip() for x in lines]
                if len(lines) == 2:
                    # keys list
                    formated =  lines[0].split('|')
                    self._echo_line(i, 1, formated)
                    # print item description
                    formated = lines[1].split('|')
                    self._echo_line(i, self._columnX, formated, reverse=True)
                else:
                    self._echo_line(i, 1, [''] + lines[0].split('|'))
            self._pad_refresh()

    def show_args(self, parent):
        if self._args:
            if self._args[0] == 'H_EXTERNAL_LINE_EDITOR' and \
                    len(self._args) > 1:
                self.set_text(parent, *self._args)
        self.show(parent)

    def erase(self):
        if self._win:
            self._win.bkgdset(' ', curses.color_pair(13))
            self._win.erase()
            self._win.refresh()

    def _format_columns(self, help_text):
        # Step 1: Use the original help text
        # help_text = self.help_text

        # Step 2: Split lines and process each line
        lines = help_text.strip().split('\n')
        formatted_lines = []
        max_left_length = 0

        for line in lines:
            # Split by '<*>' and strip whitespace
            parts = [part.strip() for part in line.split('<*>')]
            if len(parts) != 2:
                continue  # Skip lines that don't conform to expected format

            left_part = parts[0].strip()  # Keep '|' in left part
            right_part = parts[1].strip()  # Right part remains as is

            # Calculate lengths
            left_length_no_pipe = len(left_part.replace('|', '').strip())
            left_length_with_pipe = len(left_part.strip())

            # Update max length of left part without pipes
            max_left_length = max(max_left_length, left_length_no_pipe)

            # Prepare formatted line with original left part
            formatted_lines.append((left_part, right_part))

        # Total width (max_left_length + 4)
        total_width = max_left_length + 4

        # Step 3: Create formatted output with proper spacing
        output_lines = []
        for left_part, right_part in formatted_lines:
            # Calculate lengths again for formatting
            left_length_no_pipe = len(left_part.replace('|', '').strip())
            left_length_with_pipe = len(left_part.strip())

            # Calculate number of spaces needed for padding after removing '|'
            padding_spaces = total_width - left_length_no_pipe

            if left_part == "":
                # If left_part is empty, pad right_part with underscores
                right_part = '_' * total_width + right_part

            # Create a formatted line with calculated padding
            formatted_line = left_part.ljust(len(left_part) + padding_spaces) + right_part
            output_lines.append(formatted_line)

        return '\n'.join(output_lines)

    def get_formatted_help(self):
        return self._format_columns()

    def show(self, parent=None):
        if logger.isEnabledFor(logging.INFO):
            logger.info('>>> Message System: displaying key "{}"'.format(self._last_key))
        if parent is not None:
            self._parent = parent
            self._get_win()
        if self.too_small:
            if self._win is not None:
                self._win.refresh()
        else:
            self._win.refresh()
            if self._active_token is not None:
                self._pad_pos = self._active_token
            self._pad_pos = min(self._pad_pos, self._lines_count - self._maxY + 3)
            self._pad_refresh()

    def keypress(self, char):
        ''' PyRadioMessagesSystem keypress '''
        l_char = None
        if not self.too_small and self._can_scroll:
            if char in (kbkey['g'], curses.KEY_HOME) or \
                check_localized(char, (kbkey['g'], )):
                self._pad_pos = 0
                self._pad_refresh()
            elif char in (kbkey['G'], curses.KEY_END) or \
                check_localized(char, (kbkey['G'], )):
                self._pad_pos = self._lines_count - self._maxY + 3
                self._pad_refresh()
            elif char in (curses.KEY_DOWN, kbkey['j']) or \
                check_localized(char, (kbkey['j'], )):
                if self._lines_count - self._maxY + 2 >= self._pad_pos:
                    self._pad_pos += 1
                    self._pad_refresh()
            elif char in (curses.KEY_UP, kbkey['k']) or \
                check_localized(char, (kbkey['k'], )):
                if self._pad_pos > 0:
                    self._pad_pos -= 1
                    self._pad_refresh()
            elif char in (curses.KEY_NPAGE, KEY_ACK):
                if self._lines_count - self._maxY - 4 >= self._pad_pos + self._maxY + 2:
                    self._pad_pos += (self._maxY - 3)
                else:
                    self._pad_pos = self._lines_count - self._maxY + 3
                self._pad_refresh()
            elif char in (curses.KEY_PPAGE, KEY_STX):
                if self._pad_pos - self._maxY - 3 >= 0:
                    self._pad_pos -= (self._maxY - 3)
                else:
                    self._pad_pos = 0
                self._pad_refresh()
            else:
                return True
        else:
            return True
        return False

