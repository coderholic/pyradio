# -*- coding: utf-8 -*-
#
import curses
import re
import logging
from curses.ascii import ACK as KEY_ACK, STX as KEY_STX
from sys import platform
from .window_stack import Window_Stack_Constants

import locale
locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

class PyRadioMessagesSystem(object):

    _win = None
    too_small = False
    simple_dialog = False
    _same_content = False
    _same_parent = False
    _can_scroll= True
    _last_key = ''
    _columns = {}
    _max_lens = {}
    _tokens = {}
    _universal_message = None
    _station_info_message = None
    _db_info_message = None
    _delayed_message = None
    _rb_search_message = None
    _external_line_editor = None
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
r'''__Welcome to |PyRadio Main Help
__You can use the following keys to navigate: |j| (|Up|), |k| (|Down|),
|PgUp| (|^B|), |PgDn| (|^F|) to scroll up/down.
__You can also use |g| (|HOME|) / |G| (|END|) to scroll to the top / bottom.

__ You will have noticed the two |opposite arrows| at the top right
corner of this window; they indicate that the text is |scrollable| and
the keys mentioned above are |valid|; if the arrows are not there, the
text is not scrollable and pressing any key will |close the window|.

!Gerneral Help
Up|, |j|, |PgUp|,                   |*|
Down|, |k|, |PgDown                 |*|  Change station selection.
<n>g| / |<n>G                       |*|  Jump to first /last or |n|-th station.
H M L                               |*|  Go to top / middle / bottom of screen.
P                                   |*|  Go to |P|laying station.
Enter|, |Right|, |l                 |*|  Play selected station.
^N| / |^P                           |*|  Play |N|ext or |P|revious station.
i                                   |*|  Display station |i|nfo (when playing).
r                                   |*|  Select and play a random station.
Space|, |Left|, |h                  |*|  Stop / start playing selected station.
Esc|, |q                            |*|  Quit.

!Volume management
-|/|+| or |,|/|.                    |*|  Change volume.
m| / |v                             |*|  |M|ute player / Save |v|olume (not in vlc).

!Misc
o| / |s| / |R                       |*|  |O|pen / |S|ave / |R|eload playlist.
t| / |T| / | ~                      |*|  Change |t|heme / |T|ransparency / Calc. Background.
c                                   |*|  Open |C|onfiguration window.

!Searching
/| / |n| / |N                       |*|  Search, go to next / previous result.

!Stations' history
< |/| >                             |*|  Move to previous / next station.

!Moving stations
J                                   |*| Create a |J|ump tag.
<n>^U|, |<n>^D                      |*| Move station |U|p / |D|own.
                                    |*| If a |jump tag| exists, move it there.
!Group Management
a A                                 |*|  Add a |Group| (sets |URL| to "|-|").
^E |/ |^Y                           |*|  Go to next /previous |Group|.
^G                                  |*|  Open the |Group Selection| window.

!Player Customization
z                                   |*|  Toggle |Force http connections|
Z                                   |*|  Extra player parameters

!Title Logger
W                                   |*|  Toggle Logger on/off
w                                   |*|  Tag a station as liked

!Recording
Veritcal line                       |*|  Enable / disable |recording|.
Space                               |*|  Pause / resume playback.

!Change Player
\m                                  |*|  Open the |Player Selection| window.

!Remote Control Server
\s                                  |*|  Start/Stop the |Server|.

!Playlist editing
a| / |A                             |*|  Add / append new station.
e                                   |*|  Edit current station.
E                                   |*|  Change station's encoding.
p                                   |*|  Paste unnamed register.
DEL|, |x                            |*|  Delete selected station.

!Alternative modes
\                                   |*|  Enter |Extra Commands| mode.
y                                   |*|  Enter |Copy| mode.
'                                   |*|  Enter |Register| mode.
Esc|, |q                            |*|  Exit alternative mode.

!Extra Command mode (\)
\                                   |*|  Open previous playlist.
]                                   |*|  Open first opened playlist.
n                                   |*|  Create a |n|ew playlist.
p                                   |*|  Select playlist / register to |p|aste to.
r                                   |*|  |R|ename current playlist.
C                                   |*|  |C|lear all registers.
h                                   |*|  Display |H|TML help.

!Copy mode (y)
ENTER                               |*|  Copy station to unnamed register.
a-z| / |0-9                         |*|  Copy station to named register.

!Registe mode (')
'                                   |*|  Open registers list.
a-z| / |0-9                         |*|  Open named register.

!Windows Only
F8                                  |*|  Players management.
F9                                  |*|  Show |EXE| location.
F10                                 |*|  Uninstall |PyRadio|.

!Mouse Support (if enabled)
Click                               |*|  Change selection.
Double click                        |*|  Start / stop the player.
Middle click                        |*|  Toggle mute.
Wheel                               |*|  Page up / down.
Shift-Wheel                         |*|  Adjust volume.

<!--rb-->!RadioBrowser
O                                   |*|  Open |RadioBrowser|.
c                                   |*|  Open |c|onfig window.
C                                   |*|  Select server to |c|onnect to.
s                                   |*|  |S|earch for stations.
{| / |[| / |]                       |*|  Fetch first / previous / next page.
S                                   |*|  |S|ort search results.
I                                   |*|  Database Station |I|nfo (current selection).
V                                   |*|  |V|ote for station.
q Escape \\                         |*|  Close Browser (go back in history).

Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
'''),

'D_STATION_DELETE_ASK': ('Station Deletion',
r'''
Are you sure you want to delete station:
"|{}|"?

Press "|y|" to confirm, "|Y|" to confirm and not
be asked again, or any other key to cancel

'''
),

'D_STATION_DELETE_ASK_LOCKED': ('Station Deletion',
r'''
Are you sure you want to delete station:
"|{}|"?

Press "|y|" to confirm, or any other key to cancel

'''
),

    'M_STATION_INFO_ERROR': ('Station Info Error',
r'''
Station info not available at this time,
since it comes from the data provided by
the station when connecting to it.

Please play a station to get its info, (or
wait until one actually starts playing).

'''
),

    'M_STATION_INFO': ('',),

    'M_DB_INFO': ('',),

    'D_WITH_DELAY': ('',),

    'H_PLAYLIST': ('Playlist Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                 |*|Change playlist selection.
<n>g| / |<n>G                       |*|Jump to first / last or n-th item.
M| / |P                             |*|Jump to |M|iddle / loaded playlist.
Enter|, |Right|, |l                 |*|Open selected playlist.
x                                   |*|Delete current playlist.
r                                   |*|Re-read playlists from disk.
'                                   |*|Toggle between playlists.
/| / |n| / |N                       |*|Search, go to next / previous result.
\                                   |*|Enter |Extra Commands| mode.
Esc|, |q|, |Left|, |h               |*|Cancel.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*|Change volume.
m| / |v                             |*||M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*|Toggle title log / like a station.'''
),


    'M_PLAYLIST_READ': ('',
r'''
___Reading playlists.___
____Please wait...

'''
),

    'D_PLAYLIST_RELOAD_CONFIRM': ('Playlist Reload',
r'''
This playlist has not been modified within
PyRadio. Do you still want to reload it?

Press "|y|" to confirm, "|Y|" to confirm and not
be asked again, or any other key to cancel

'''
),

    'D_PLAYLIST_RELOAD_CONFIRM_LOCKED': ('Playlist Reload',
r'''
This playlist has not been modified within
PyRadio. Do you still want to reload it?

Press "|y|" to confirm, or any other key to cancel

'''
),

    'M_PLAYLIST_LOAD_ERROR': ('Error',
),

    'D_PLAYLIST_DIRTY_CONFIRM_LOCKED': ('Playlist Reload',
r'''
This playlist has been modified within PyRadio.
If you reload it now, all modifications will be
lost. Do you still want to reload it?

Press "|y|" to confirm, or "|n|" to cancel

'''
),

    'D_PLAYLIST_DIRTY_CONFIRM': ('Playlist Reload',
r'''
This playlist has been modified within PyRadio.
If you reload it now, all modifications will be
lost. Do you still want to reload it?

Press "|y|" to confirm, "|Y|" to confirm and not be
asked again, or "|n|" to cancel

'''
),

    'D_PLAYLIST_MODIFIED': ('Playlist Modified',
r'''
This playlist has been modified within
PyRadio. Do you want to save it?

If you choose not to save it now, all
modifications will be lost.

Press "|y|" to confirm, "|Y|" to confirm and not
be asked again, "|n|" to reject, or "|q|" or
"|ESCAPE|" to cancel

'''
),

    'D_PLAYLIST_MODIFIED_LOCKED': ('Playlist Modified',
r'''
This playlist has been modified within
PyRadio. Do you want to save it?

If you choose not to save it now, all
modifications will be lost.

Press "|y|" to confirm, "|n|" to reject,
or "|q|" or "|ESCAPE|" to cancel

'''
),

    'M_PLAYLIST_SAVE_ERR_1': ('Error'
r'''
Saving current playlist |failed|!

Could not open file for writing
"|{}|"

'''
),

    'M_PLAYLIST_SAVE_ERR_2': ('Error'
r'''
Saving current playlist |failed|!

You will find a copy of the saved playlist in
"|{}|"

PyRadio will open this file when the playlist
is opened in the future.

'''
),

    'M_PLAYLIST_NOT_FOUND_ERROR': ('Error',
r'''
Playlist |not| found!

This means that the playlist file was deleted
(or renamed) some time after you opened the
Playlist Selection window.

'''
),

    'M_PLAYLIST_RECOVERY_ERROR_1': ('Error',
r'''
Both a playlist file (|CSV|) and a playlist backup
file (|TXT|) exist for the selected playlist. In
this case, |PyRadio| would try to delete the |CSV|
file, and then rename the |TXT| file to |CSV|.

Unfortunately, deleting the |CSV| file has failed,
so you have to manually address the issue.

'''
),

    'M_PLAYLIST_RECOVERY_ERROR_2': ('Error',
r'''
A playlist backup file (|TXT|) has been found for
the selected playlist. In this case, PyRadio would
try to rename this file to |CSV|.

Unfortunately, renaming this file has failed, so
you have to manually address the issue.

'''
),

    'M_PLAYLIST_NOT_SAVED': ('Playlist Modified',
r'''
Current playlist is modified and cannot be renamed.

Please save the playlist and try again.

'''
),

        'D_PLAYLIST_DELETE_ASK': ('Playlist Deletion',
r'''
Are you sure you want to delete the playlist:
"|{}|"?
Please keep in mind that once it is deleted, there
is no way to get it back.

Press "|y|" to confirm, or any other key to cancel

'''
),

        'M_PLAYLIST_DELETE_ERROR': ('Playlist Deletion Error',
r'''
Cannot delete the playlist:
"|{}|"

Please close all other porgrams and try again...

'''
),

    'M_PLAYLIST_RELOAD_ERROR': ('Error',
r'''
Playlist reloading |failed|!

You have probably edited the playlist with an
external program. Please re-edit it and make
sure that you save a valid |CSV| file.

'''
),

        'H_THEME': ('Theme Help',
r'''Up| ,|j|, |PgUp|,              |*|
Down|, |k|, |PgDown                |*| Change theme selection.
g| / |<n>G                         |*| Jump to first or n-th / last theme.
Enter|, |Right|, |l                |*| Apply selected theme.
Space                              |*| Apply theme and make it default.
c                                  |*| Make theme default and watch it for
|                                  |*| changes (|User Themes| only).
T                                  |*| Toggle theme transparency.
r                                  |*| Rescan disk for user themes.
/| / |n| / |N                      |*| Search, go to next / previous result.
Esc|, |q|, |Left|, |h              |*| Close window.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.|                  |*| Change volume.
m| / |v                            |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                            |*| Toggle title log / like a station.'''

),

    'D_THEME_CREATE_NEW_ASK': ('Read-only Theme',
r'''
You have requested to edit a |read-only| theme,
which is not possible. Do you want to create a
new theme instead?

Press "|y|" to accept or any other key to cancel.

'''
),

        'H_GROUP': ('Group Selection Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                 |*| Change Group Header selection.
g G                                 |*| Go to first / last Group Header.
H M L                               |*| Go to top / middle / bottom of screen.
/ n N                               |*| Perform search.
Space|, |Left|, |Enter              |*| Select a Group Header.
Esc|, |q                             |*| Cancel.
%Global functions
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'D_GROUP_DELETE_ASK': ('Group Deletion',
r'''
Are you sure you want to delete this group header:
"|{}|"?

Press "|y|" to confirm, or any other key to cancel

'''
),

    'H_YANK': ('Copy Mode Help',
r'''ENTER                           |*| Copy station to unnamed register.
a-z| / |0-9                         |*| Copy station to named register.

Any other key exits current mode.

'''
),

    'H_REGISTERS': ('Registers Mode Help',
r'''ENTER                           |*| Open registers list.
a-z| / |0-9                         |*| Open named register.

Any other key exits current mode.

'''
),

    'D_REGISTER_CLEAR': ('Clear register',
r'''
Are you sure you want to clear the contents
of this register?

This action is not recoverable!

Press "|y|" to confirm, or "|n|" to cancel

'''
),

    'D_REGISTERS_CLEAR_ALL': ('Clear All Registers',
r'''
Are you sure you want to clear the contents
of all the registers?

This action is not recoverable!

Press "|y|" to confirm, or "|n|" to cancel

'''
),

    'M_REGISTER_SAVE_ERROR': ('Error',
r'''
Error saving register file:
__"|{}|"

'''
),

    'H_EXTRA': ('Extra Commands Help',
r'''\                               |*| Open previous playlist.
]                                   |*| Open first opened playlist.
b B                                 |*| Set player |b|uffering.
l                                   |*| Toggle |Open last playlist|.
m                                   |*| Cahnge |m|edia player.
n                                   |*| Create a |n|ew playlist.
p                                   |*| Select playlist / register to |p|aste to.
r                                   |*| |R|ename current playlist.
C                                   |*| |C|lear all registers.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

Any other key exits current mode.
'''
),

    'H_EXTRA_REGISTERS_LIST': ('Extra Commands Help',
r'''r                               |*| |R|ename current register.
p                                   |*| |P|aste to current register.
c                                   |*| Clear |c|urrent register.
C                                   |*| |C|lear all registers.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

Any other key exits current mode.
'''
),

    'H_EXTRA_PLAYLIST': ('Extra Commands Help',
r'''n                               |*| Create a |n|ew playlist.
p                                   |*| |P|aste to current playlist.
r                                   |*| |R|ename current playlist.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

|Any other key exits current mode.
'''
),

    'D_RB_OPEN': ('',
r'''Connecting to service.
____Please wait...'''
),

    'D_RB_SEARCH': ('',
r'''__Performing search.__
 ____Please wait...'''
),

    'M_RB_UNKNOWN_SERVICE': ('Unknown Service',
r'''
The service you are trying to use is not supported.

The service "|{0}|"
(url: "|{1}|")
is not implemented (yet?)

If you want to help implementing it, please open an
issue at "|https://github.com/coderholic/pyradio/issues|".

'''
),

    'H_RB_NO_PING': ('Servers Unreachable',
r'''No server responds to ping.

You will be able to edit the config file, but
you will not be able to select a default server.

'''
),

    'H_RB_SEARCH': ('RadioBrowser Search Help',
r'''Tab| / |Sh-Tab                  |*| Go to next / previous field.
j|, |Up| / |k|, |Down               |*| Go to next / previous field vertivally.
h|, |Left| / |l|, |Right            |*|
                                    |*| Go to next / previous field (when
                                    |*| applicable). Also, change counter value.
Space                               |*| Toggle check buttons.
                                    |*| Toggle multiple selection.
Enter                               |*| Perform search / cancel (on push buttons).
s                                   |*| Perform search (not on Line editor).
Esc                                 |*| Cancel operation.
_
Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station'''
),

    'H_RB_CONFIG': ('RadioBrowser Config Help',
r'''Tab| / |Sh-Tab,                 |*|
j|, |Up| / |k|, |Down               |*| Go to next / previous field.
h|, |Left| / |l|, |Right            |*| Change |auto save| and |counters| value.
                                    |*| Navigate through |Search Terms|.
g|, |G|, |Home|, |End|,             |*|
PgUp|, |PgDn                        |*| Navigate through |Search Terms|.
Space|, |Enter                      |*| Toggle |auto save|  value.
                                    |*| Open |Server Selection| window.
r| / |d                             |*| Revert to |saved| / |default| values.
s                                   |*| Save config.
Esc                                 |*| Exit without saving.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'D_RB_ASK_TO_SAVE_CONFIG': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'D_RB_ASK_TO_SAVE_CONFIG_FROM_CONFIG': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'D_RB_ASK_TO_SAVE_CONFIG_TO_EXIT': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'M_RB_CONFIG_SAVE_ERROR': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure there is enought free space in___
___the file system and try again.___

'''
),

    'M_RB_CONFIG_SAVE_ERROR_WIN': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure that the configuration file___
___is not opened in another application and that___
___there is enough free space in the drive and ___
___try again.___

'''
),

    'M_RB_VOTE_RESULT': ('Station Vote Result',
r'''
You have just voted for the following station:
____|{0}|

Voting result:
____|{1}|

'''
),

    'M_RB_VOTE': ('',
r'''
___Voting for station._____
_____Please wait...'

'''
),

    'M_RB_EDIT_URL_ERROR': ('Error',
r'''
____Errorenous Station Data provided!___

_________Station URL is invalid!___
___Please provide a valid Station URL.___

'''
),

    'M_RB_EDIT_INCOMPLETE_ERROR': ('Error',
r'''
____Incomplete Station Data provided!___

_________Station URL is empty!___
___Please provide a valid Station URL.___

'''
),

    'M_RB_EDIT_NAME_ERROR': ('Error',
r'''
___Incomplete Station Data provided!___

____Please provide a Station Name.___

'''
),

    'M_RB_EDIT_ICON_ERROR': ('Error',
r'''
______Errorenous Station Data provided!___

________Station Icon URL is invalid!___
___Please provide a valid Station Icon URL.___

'''
),

    'M_RB_EDIT_ICON_GORMAT_ERROR': ('Error',
r'''
______Errorenous Station Data provided!___

________Station Icon URL is invalid!___
____It must point to a JPG or a PNG file.__
___Please provide a valid Station Icon URL.___

'''
),

    'D_ASK_TO_UPDATE_STATIONS_CSV': ('Stations update',
r'''
|PyRadio| default stations (file "|stations.csv|") has been
updated upstream.

Do you want to update your "|stations.csv|" file with the
upstream changes?

Press |y| to update, |n| to decline and not be asked again
for this version, or any other key to close this window
and be asked next time you execute |PyRadio|.

'''
),

    'M_UPDATE_STATIONS_RESULT': ('', ''),

    'H_CONFIG': ('Configuration Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                 |*| Change option selection.
g|, |Home| / |G|, |End              |*| Jump to first / last option.
Enter|, |Space|, |Right|, |l        |*| Change option value.
r                                   |*| Revert to saved values.
d                                   |*| Load default values.
s                                   |*| Save config.
Esc|, |q|, |Left|, |h               |*| Cancel.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''

),

    'H_CONFIG_STATION': ('Station Selection Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                 |*| Change station selection.
g| / |<n>G                          |*| Jump to first or n-th / last station.
M                                   |*| Jump to the middle of the list.
Enter|, |Space|,                    |*|
Right|, |l                          |*| Select default station.
/| / |n| / |N                       |*| Search, go to next / previous result.
r                                   |*| Revert to saved value.
Esc|, |q|, |Left|, |h                  |*| Canel.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'H_CONFIG_PLAYLIST': ('Playlist Selection Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                 |*| Change playlist selection.
g| / |<n>G                          |*| Jump to first or n-th / last playlist.
Enter|, |Space|,                    |*|
Right|, |l                          |*| Select default playlist.
/| / |n| / |N                       |*| Search, go to next / previous result.
r                                   |*| Revert to saved value.
Esc|, |q|, |Left|, |h               |*| Canel.
%Global functions (with \ on Line editor)
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'H_CONFIG_ENCODING': ('Encoding Selection Help',
r'''Arrows|, |h|, |j|, |k|,         |*|
l|, |PgUp|, |,PgDn                  |*|
g|, |Home|, |G|, |End               |*| Change encoding selection.
Enter|, |Space|, |s                 |*| Save encoding.
r c                                 |*| Revert to station / |c|onfig value.
Esc|, |q                            |*| Cancel.
%Global functions
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'M_CONFIG_SAVE_ERROR': ('Error Saving Config',
r'''An error occured while saving the configuration file!

|PyRadio| will try to |restore| your previous settings,
but in order to do so, it has to |terminate now!

'''
),

    'H_DIR': ('Open Directory Help',
r'''Up|, |j|, |PgUp|,               |*|
Down|, |k|, |PgDown                  |*| Change Directory selection.
g G                                 |*| Go to first / last Directory.
Space|, |Right|,                    |*|
l|, |Enter                          |*| Open a Directory.
1| - |{}                            |*| Open corresponding Directory.
Esc|, |q                            |*| Cancel.
%Global functions
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'H_SEARCH': ('Search Help',
r'''Left| / |Right                  |*| Move to next / previous character.
Up| / |Down                         |*| Cycle within history.
M-F| / |M-B                         |*| Move to next / previous word.
HOME|, |^A| / |END|, |^E            |*| Move to start / end of line.
^W| / |M-D|, |^K                    |*| Clear to start / end of line.
^U                                  |*| Clear line.
^X                                  |*| Remove history item.
DEL|, |^D                           |*| Delete character.
Backspace|, |^H                     |*| Backspace (delete previous character).
Up|, |^P| / |Down|, |^N             |*| Get previous / next history item.
\?| / |\\                           |*| Insert a "|?|" or a "|\|", respectively.
Enter| / |Esc                       |*| Perform / cancel search.

Global functions work when preceded with a "|\|".
'''
),

    'H_SEARCH_DARWIN': ('Search Help',
r'''Left| / |Right                  |*| Move to next / previous character.
HOME|, |^A| / |END|, |^E            |*| Move to start / end of line.
^W| / |^K                           |*| Clear to start / end of line.
^U                                  |*| Clear line.
DEL|, |^D                           |*| Delete character.
Backspace|, |^H                     |*| Backspace (delete previous character).
Up|, |^P| / |Down|, |^N             |*| Get previous / next history item.
\?| / |\\                           |*| Insert a "|?|" or a "|\|", respectively.
Enter| / |Esc                       |*| Perform / cancel search.

Global functions work when preceded with a "|\|".
'''
),

    'H_EXTERNAL_LINE_EDITOR': ('',),

    'H_LINE_EDITOR': ('Line Editor Help',
r'''Left| / |Right                  |*| Move to next / previous character.
HOME|, |^A| / |END|, |^E            |*| Move to start / end of line.
^W| / |^K                           |*| Clear to start / end of line.
^U                                  |*| Clear line.
DEL|, |^D                           |*| Delete character.
Backspace|, |^H                     |*| Backspace (delete previous character).
Up| / |Down                         |*| Go to previous / next field.
\?| / |\\                           |*| Insert a "|?|" or a "|\\|", respectively.
Esc                                 |*| Cancel operation.

Global functions work when preceded with a "|\|".

'''
),

    'H_LINE_EDITOR_DARWIN': ('Line Editor Help',
r'''Left| / |Right                  |*| Move to next / previous character.
M-F| / |M-B                         |*| Move to next / previous word.
HOME|, |^A| / |END|, |^E            |*| Move to start / end of line.
^W| / |M-D|,|^K                     |*| Clear to start / end of line.
^U                                  |*| Clear line.
DEL|, |^D                           |*| Delete character.
Backspace|, |^H                     |*| Backspace (delete previous character).
Up| / |Down                         |*| Go to previous / next field.
\?| / |\\                           |*| Insert a "|?|" or a "|\\|", respectively.
Esc                                 |*| Cancel operation.

Global functions work when preceded with a "|\|".

'''
),

    'M_SESSION_LOCKED': ('Session Locked',
'''
This session is |locked| by another |PyRadio instance|.

You can still play stations, load and edit playlists,
load and test themes, but any changes will |not| be
recorded in the configuration file.

If you are sure this is the |only| active |PyRadio|
instance, exit |PyRadio| now and execute the following
command: |pyradio --unlock|

'''
),

    'M_MOUSE_RESTART': ('Program Restart required',
r'''
You have just changed the |mouse support| config
option.

|PyRadio| must be |restarted| for this change to
take effect.

'''
),

    'M_NO_PLAYLIST': ('Error',
r'''
|No playlists found!!!

This should |never| have happened; |PyRadio| is missing its
default playlist. Therefore, it has to |terminate| now.
It will re-create it the next time it is lounched.
'''
),

    'D_RC_ACTIVE': ('Remote Control Enabled',
r'''
|PyRadio Remote Control Server| is active!

Text Address: |http://{0}
_Web Address: |http://{0}/html____

Press "|s|" to stop the server, or'''
),

    'M_RC_START_ERROR': ('Server Error',
r'''
The Remote Control Server |failed| to start!
The error message is:
__|{}

This is probably because another (|PyRadio?|) process
is already using the requested |Server Port|.

Close this window, press "|\s|", select a |different
|port| and try to start the |Server| again.

'''
),

    'M_RC_DEAD_ERROR': ('Server Error',
r'''
The Remote Control Server |terminated| with
message:
__|{}

'''
),

    'M_RC_LOCKED': ('Not Available',
r'''
______This session is |locked|, so the
__|Remote Control Server| cannot be started!__

'''
),

    'D_UPDATE_NOTIFICATION': ('',
r'''
A new |PyRadio| release (|{0}|) is available!

You are strongly encouraged to update now, so that
you enjoy new features and bug fixes.

Press |y| to update or any other key to cancel.
'''
),

    'M_UPDATE_NOTIFICATION_OK': ('Update Notification',
r'''
|PyRadio| will now be updated!

The program will now terminate so that the update_
procedure can start.

Press any key to exit |PyRadio|.

'''
),

    'M_UPDATE_NOTIFICATION_OK_WIN': ('Update Notification',
r'''
|PyRadio| will now terminate and the update script
 will be created.

When Explorer opens please double click on
"|update.bat|" to start the update procedure.

Press any key to exit |PyRadio|.

'''
),

    'M_REC_ENABLED': ('Recording Enable',
r''' _____Next time you play a station,
_____it will be |written to a file|!

A |[r]| at the right top corner of the window
indicates that recording is |enabled|.
A |[R]| indicates that a station is actually
|being recorded| to a file.

Press |x| to not show this message again, or'''
),

    'M_REC_DISABLED': ('Recording Disabled',
r'''
Recording will actually continue until
you stop the playback of the station!

'''
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

'''
),

    'M_REC_DIR_MOVE': ('',
r'''
______Moving |Recordings Directory______
____________Please wait...

'''
),

    'M_REC_DIR_MOVE_ERROR': ('Error',
r'''
______Moving |Recordings Directory| has |failed!!|______
Moving from
|{}|
to
|{}|

Press any key to open the directories in file explorer...

'''
),

    'M_MANAGE_PLAYERS_WIN': ('Players Management',
r'''
Players management |enabled|!

|PyRadio| will now terminate so that you can
|manage| installed players.

'''
),

    'D_UNINSTALL_WIN': ('Uninstall PyRadio',
r'''
Are you sure you want to uninstall |PyRadio|?

Please press |y| to confirm or any other key
to decline.

'''
),

    'M_REMOVE_OLD_INSTALLATION': ('PyRadio',
r'''
|PyRadio| will now try to remove any files found on your
system belonging to a pre |0.8.9.15| installation.

'''
),

    'M_SHOW_UNNAMED_REGISTER': ('Unnamed Register',
r'''
___{}___

'''
),

    'M_CHANGE_PLAYER_ONE_ERROR': ('PyRadio',
r'''
You have requested to change the |Media Player| but
there's only one player detected.

If you have already installed any other player
(|{0}| or |{1}|), please make sure its executable
is in your PATH.

'''
),

    'M_CHANGE_PLAYER_THE_SAME_ERROR': ('PyRadio',
r'''
|{}|: Media Player already active.

You have requested to change the |Media Player| to
the one that's already active.

Please try selecting a different |Media Player|.

'''
),

    'M_NOT_IMPLEMENTED': ('PyRadio',
r'''
___This feature has not been implemented yet...___

'''
),

    'M_FOREIGN': ('Foreign playlist',
r'''
A playlist by this name:
__"|{0}|"
already exists in the config directory.

This playlist was saved as:
__"|{1}|"

'''
),

    'M_FOREIGN_ERROR': ('Error',
r'''
Foreign playlist copying |failed|!

Make sure the file is not open with another
application and try to load it again

'''
),

    'D_FOREIGN_ASK': ('Foreign playlist',
r'''
This is a "|foreign|" playlist (i.e. it does not
reside in PyRadio's config directory). If you
want to be able to easily load it again in the
future, it should be copied there.

Do you want to copy it in the config directory?

Press "|y|" to confirm or "|n|" to reject

'''
),

    'M_NO_THEMES': ('Themes Disabled',
r'''|Curses| (the library this program is based on), will not display
colors |correctly| in this terminal, (after they have been |changed by
PyRadio.

Therefore, using |themes is disabled| and the |default theme| is used.

For more info, please refer to:
|https://github.com/coderholic/pyradio/#virtual-terminal-restrictions

Press "|x|" to never display this message in the future, or
'''
),

    'M_REQUESTS_ERROR':('Module Error',
r'''
Module "|requests|" not found!

In order to use |RadioBrowser| stations directory
service, the "|requests|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-requests| or |python{}-requests|) and try
executing |PyRadio| again.

'''
),

    'M_NETIFACES_ERROR':('Module Error',
r'''
Module "|netifaces|" not found!

In order to use |RadioBrowser| stations directory
service, the "|netifaces|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-netifaces| or |python{}-netifaces|) and try
executing |PyRadio| again.

'''
),

    'M_DNSPYTHON_ERROR':('Module Error',
r'''
Module "|dnspython|" not found!

In order to use |RadioBrowser| stations directory
service, the "|dnspython|" module must be installed.

Exit |PyRadio| now, install the module (named
|python-dnspython| or |python{}-dnspython|) and try
executing |PyRadio| again.

'''
),

    'M_PYTHON2_ASCII_ERROR': ('Error',
r'''
Non-ASCII characters editing is |not supported!|

You are running |PyRadio| on |Python 2|. As a result,
the station editor only supports |ASCII characters|,
but the station name you are trying to edit contains
|non-ASCII| characters.

To edit this station, either run |PyRadio| on |Python 3|,
or edit the playlist with an external editor and then
reload the playlist.

'''
),

    'X_THEME_DOWN_FAIL': ('',
r'''
____|Theme download failed!!!|____
_____Loading |default| theme..._____

'''
),

    'M_PARAMETER_ERROR': ('Parameter Set Error',
r'''
The player parameter set you specified does
not exist!

|{0}| currently has |{1}| sets of parameters.
You can press "|Z|" to access them, after you
close this window.

'''
),

    'X_PLAYER_CHANGED':('',
r'''
|PyRadio| default player has changed from
__"|{0}|"
to
__"|{1}|".

This change may lead to changing the player used,
and will take effect next time you open |PyRadio|.

'''
),

    'M_SCHEDULE_INFO': ('Schedule Entry Info',
r'''{}
'''
),

    'M_SCHEDULE_ERROR': ('Schedule Error',
r'''
___|{}___

'''
),

    'M_SCHEDULE_EDIT_HELP': ('Schedule Editor Help',
r'''Tab|, |L| / |Sh-Tab|, |H        |*| Go to next / previous field.
j|, |Up| / |k|, |Down               |*| Go to next / previous field vertivally.
                                    |*| Go to next / previous field (when
                                    |*| applicable). Also, change counter value.
Space                               |*| Toggle check buttons.
n                                   |*| Set current date and time to section.
0|-|9                               |*| Add hours to |Start| or |Stop| section.
t| / |f                             |*| Copy date/time |t|o/|f|rom complementary field.
i                                   |*| Validate entry and show dates.
Enter                               |*| Perform search / cancel (on push buttons).
s                                   |*| Perform search (not on Line editor).
Esc                                 |*| Cancel operation.

%Global functions
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station'''
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
            self._caption, l, max_len = self._get_txt(*args)
            if l is None:
                return
            if max_len < self._main_win_width or \
                    self.active_message_key in ('M_STATION_INFO', 'M_DB_INFO'):
                self._maxX = max_len
            else:
                self._maxX = self._main_win_width
            # # logger.error('self._caption = "{}"'.format(self._caption))
            # # logger.error('max_len = {0}, self._maxY = {1}'.format(max_len, self._maxX))
            # for n in l:
            #     logger.info(n)
            self._lines_count = len(l)

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
                self._populate_pad(l)
            except curses.error:
                pass
        self.simple_dialog = False
        self._txt = {}

    def __init__(self, config, op_mode, prev_op_mode):
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
        if token in self._tokens.keys():
            self._active_token = self._tokens[token]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('setting self._pad_pos to {}'.format(self._pad_pos))

    def _remove_start_char(self, txt, char):
        if txt.startswith(char):
            return txt[1:]
        else:
            return txt

    def _get_txt(self, *args):
        '''
            args[0] = message_key

            Format is:
                (
                    Help Window Caption,
                    r text (string)
                )
        '''
        cap, out = self._txt[self.active_message_key]
        # logger.info('--> out\n{}'.format(out))
        if out is None:
            return None, None, 0

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
        elif (self.active_message_key == 'H_SEARCH' or self.active_message_key == 'H_LINE_EDITOR') and \
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

        self._tokens, l = self._parse_strings_for_tokens(out.splitlines())
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
                if self.active_message_key in self._columns.keys():
                    column =  self._columns[self.active_message_key]
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('column from self._columns = {}'.format(column))
                else:
                    for n in l:
                        x = n.split('|*|')
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
            if self.active_message_key in self._max_lens.keys():
                mmax =  self._max_lens[self.active_message_key]
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('max len from self._max_lens = {}'.format(mmax))
            else:
                # logger.error(f'{l = }')
                for n in l:
                    x = n.split('|*|')
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
        if mmax < len(cap) + 6:
            mmax = len(cap) + 6
        # logger.error('\n\n===> mmax = {}\n\n'.format(mmax))
        return cap, l, mmax

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
            if self._operation_mode() == Window_Stack_Constants.NORMAL_MODE or \
                        (self._operation_mode() == Window_Stack_Constants.HELP_MODE and \
                        self._previous_operation_mode() == Window_Stack_Constants.NORMAL_MODE):
                if self._cnf.is_register:
                    out = out.replace('C   ', 'c  ').replace(
                            'current playlist', 'current register').replace(
                                '|C|lear all registers.', 'Clear |c|urrent register.')
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
        else:
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
                if platform.startswith('win') or \
                        platform.lower().startswith('darwin'):
                    self._win.addstr(0, self._maxX-1, '^', self.col_box)
                    self._win.addstr(1, self._maxX-1, '^', self.col_box)
                else:
                    self._win.addstr(0, self._maxX-1, '⮝', self.col_box)
                    self._win.addstr(1, self._maxX-1, '⮟', self.col_box)
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
        for k, l in enumerate(formated):
            if reverse:
                col = self.col_highlight if k % 2 else self.col_txt
            else:
                col = self.col_txt if k % 2 else self.col_highlight
            if k == 0:
                self._pad.addstr(Y, X, l.replace('_', ' '), col)
                # logger.error('printing: {0} - "{1}"'.format(X, l))
            else:
                if l:
                    self._pad.addstr(l.replace('_', ' '), col)

    def _populate_pad(self, l):
        self._pad.erase()
        for i, n in enumerate(l):
            out = n.strip()
            if out.strip().startswith('%'):
                self._pad.addstr(i, 1, '─' * (self._maxX-4), self.col_box)
                self._pad.addstr(i, self._maxX - len(out) - 5, ' ' + out[1:] + ' ', self.col_highlight)
            elif out.strip().startswith('!'):
                self._pad.addstr(i, 1, '─── ', self.col_box)
                self._pad.addstr(out[1:] + ' ', self.col_highlight)
                self._pad.addstr('─' * (self._maxX - len(out[1:]) - 9), self.col_box)
            else:
                lines = out.split('|*|')
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
            if self._pad_pos > self._lines_count - self._maxY + 3:
                #if self._lines_count - self._maxY - 4 >= self._pad_pos + self._maxY + 2:
                self._pad_pos = self._lines_count - self._maxY + 3
            self._pad_refresh()

    def keypress(self, char):
        if not self.too_small and self._can_scroll:
            if char in (ord('g'), curses.KEY_HOME):
                self._pad_pos = 0
                self._pad_refresh()
            elif char in (ord('G'), curses.KEY_END):
                self._pad_pos = self._lines_count - self._maxY + 3
                self._pad_refresh()
            elif char in (curses.KEY_DOWN, ord('j')):
                if self._lines_count - self._maxY + 2 >= self._pad_pos:
                    self._pad_pos += 1
                    self._pad_refresh()
            elif char in (curses.KEY_UP, ord('k')):
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

def main(scr):
    # Create curses screen
    scr.keypad(True)
    curses.use_default_colors()
    curses.noecho()
    curses.start_color()
    curses.use_default_colors()

    # Clear the screen
    scr.clear()
    scr.refresh()

    # Get the dimensions of the terminal window
    curses.init_pair(1, curses.COLOR_RED, curses.COLOR_WHITE)
    curses.init_pair(3, curses.COLOR_BLUE, curses.COLOR_WHITE)
    curses.init_pair(10, curses.COLOR_BLACK, curses.COLOR_WHITE)
    curses.init_pair(11, curses.COLOR_MAGENTA, curses.COLOR_WHITE)

    height, width = scr.getmaxyx()
    window = curses.newwin(height-2, width, 1, 0)
    window.bkgd(' ', curses.color_pair(1))
    window.box()
    window.refresh()

    x = PyRadioMessagesSystem()
    x.set_text(parent=window)

    x.show()

    # Wait for user to scroll or quit
    running = True
    while running:
        ch = scr.getch()
        if ch in (curses.KEY_RESIZE, ord('#')):

            height, width = scr.getmaxyx()
            window = curses.newwin(height-2, width, 1, 0)
            window.bkgd(' ', curses.color_pair(1))
            window.box()
            window.refresh()
            x.show(parent=window)
        elif ch == ord('1'):
            x.set_text('H_MAIN')
            window.refresh()
            x.show()
        elif ch == ord('2'):
            x.set_text('page5')
            window.refresh()
            x.show()
        else:
            ret = x.keypress(ch)
            if ret:
                running = False
    # # Store the current contents of pad
    # for i in range(0, mypad.getyx()[0]):
    #     mypad_contents.append(mypad.instr(i, 0))



if __name__ == "__main__":
    curses.wrapper(main)
    # Write the old contents of pad to console
    # print '\n'.join(mypad_contents)
