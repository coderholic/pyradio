#!/usr/bin/env python
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

    too_small = False
    simple_dialog = False
    _same_content = False
    _same_parent = False
    _can_scroll= True
    _last_key = ''
    _columns = {}
    _max_lens = {}
    _tokens = {}

    ''' reset _columns and _tokens
        These keys will have non static content,
        so widths will have to be calculated every time
    '''
    _reset_metrics = (
            'm-playlist-delete-error',
            'd-playlist-delete-ask',
            'd-group-delete-ask',
            'd-station-delete-ask',
            'd-station-delete-ask-locked',
            'h-config-player',
            'm-show-unnamed-register',
            )

    def set_text(self, parent, *args):
        self._txt = {
        'h-main': ('PyRadio Help',
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
[| / |]                             |*|  Fetch previous / next page.
S                                   |*|  |S|ort search results.
I                                   |*|  Database Station |I|nfo (current selection).
V                                   |*|  |V|ote for station.
q Escape \\                         |*|  Close Browser (go back in history).

Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
'''),

'd-station-delete-ask': ('Station Deletion',
r'''
Are you sure you want to delete station:
"|{}|"?

Press "|y|" to confirm, "|Y|" to confirm and not
be asked again, or any other key to cancel

'''
),

'd-station-delete-ask-locked': ('Station Deletion',
r'''
Are you sure you want to delete station:
"|{}|"?

Press "|y|" to confirm, or any other key to cancel

'''
),

        'h-playlist': ('Playlist Help',
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

        'd-playlist-delete-ask': ('Playlist Deletion',
r'''
Are you sure you want to delete the playlist:
"|{}|"?
Please keep in mind that once it is deleted, there
is no way to get it back.

Press "|y|" to confirm, or any other key to cancel

'''
),

        'm-playlist-delete-error': ('Playlist Deletion Error',
r'''
Cannot delete the playlist:
"|{}|"

Please close all other porgrams and try again...

'''
),

        'h-theme': ('Theme Help',
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

        'h-group': ('Group Selection Help',
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

    'd-group-delete-ask': ('Group Deletion',
r'''
Are you sure you want to delete this group header:
"|{}|"?

Press "|y|" to confirm, or any other key to cancel

'''
),

    'h-yank': ('Copy Mode Help',
r'''ENTER                           |*| Copy station to unnamed register.
a-z| / |0-9                         |*| Copy station to named register.

Any other key exits current mode.

'''
),

    'h-registers': ('Registers Mode Help',
r'''ENTER                           |*| Open registers list.
a-z| / |0-9                         |*| Open named register.

Any other key exits current mode.

'''
),

    'd-register-clear': ('Clear register',
r'''
Are you sure you want to clear the contents
of this register?

This action is not recoverable!

Press "|y|" to confirm, or "|n|" to cancel

'''
),

    'd-registers-clear-all': ('Clear All Registers',
r'''
Are you sure you want to clear the contents
of all the registers?

This action is not recoverable!

Press "|y|" to confirm, or "|n|" to cancel

'''
),

    'h-extra': ('Extra Commands Help',
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

    'h-extra-registers-list': ('Extra Commands Help',
r'''r                               |*| |R|ename current register.
p                                   |*| |P|aste to current register.
c                                   |*| Clear |c|urrent register.
C                                   |*| |C|lear all registers.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

Any other key exits current mode.
'''
),

    'h-extra-playlist': ('Extra Commands Help',
r'''n                               |*| Create a |n|ew playlist.
p                                   |*| |P|aste to current playlist.
r                                   |*| |R|ename current playlist.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

|Any other key exits current mode.
'''
),

    'h-rb-search': ('RadioBrowser Search Help',
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

    'h-rb-config': ('RadioBrowser Config Help',
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

    'd-rb-ask-to-save-config': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'd-rb-ask-to-save-config-from-config': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'd-rb-ask-to-save-config-to-exit': ('Online Browser Config not Saved!',
r'''
|{}|'s configuration has been altered
but not saved. Do you want to save it now?

Press |y| to save it or |n| to disregard it.
'''
),

    'm-rb-config-save-error': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure there is enought free space in___
___the file system and try again.___

'''
),

    'm-rb-config-save-error-win': ('Config Saving Error',
r'''
___Saving your configuration has failed!!!___

___Please make sure that the configuration file___
___is not opened in another application and that___
___there is enough free space in the drive and ___
___try again.___

'''
),

    'm-rb-vote-result': ('Station Vote Result',
r'''
You have just voted for the following station:
____|{0}|

Voting result:
____|{1}|
'''
),

    'd-ask-to-update-stations-csv': ('Stations update',
r'''
|PyRadio| default stations (file "|stations.csv|") has been
updated upstream.

Do you want to update your "|stations.csv|" file with the
upstream changes?

Press |y| to update, |n| to decline and not be asked again
for this version, or any other key to close this window and
be asked next time you execute |PyRadio|.

'''
),

    'h-config': ('Configuration Help',
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

    'h-config-station': ('Station Selection Help',
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

    'h-config-playlist': ('Playlist Selection Help',
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

    'h-config-encoding': ('Encoding Selection Help',
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

    'm-config-save-error': ('Error Saving Config',
r'''An error occured while saving the configuration file!

|PyRadio| will try to |restore| your previous settings,
but in order to do so, it has to |terminate now!

'''
),

    'h-dir': ('Open Directory Help',
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

    'h-search': ('Search Help',
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

    'h-search-darwin': ('Search Help',
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

    'h-line-editor': ('Line Editor Help',
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

    'h-line-editor-darwin': ('Line Editor Help',
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

    'm-session-locked': ('Session Locked',
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

    'm-mouse-restart': ('Program Restart required',
r'''
You have just changed the |mouse support| config
option.

|PyRadio| must be |restarted| for this change to
take effect.

'''
),

    'm-no-playlist': ('Error',
r'''
|No playlists found!!!

This should |never| have happened; |PyRadio| is missing its
default playlist. Therefore, it has to |terminate| now.
It will re-create it the next time it is lounched.
'''
),

    'd-rc-active': ('Remote Control Enabled',
r'''
|PyRadio Remote Control Server| is active!

Text Address: |http://{0}
_Web Address: |http://{0}/html____

Press "|s|" to stop the server, or'''
),

    'm-rc-start-error': ('Server Error',
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

    'm-rc-dead-error': ('Server Error',
r'''
The Remote Control Server |terminated| with
message:
__|{}

'''
),

    'm-rc-locked': ('Not Available',
r'''
______This session is |locked|, so the
__|Remote Control Server| cannot be started!__

'''
),

    'd-update-notification': ('',
r'''
A new |PyRadio| release (|{0}|) is available!

You are strongly encouraged to update now, so that
you enjoy new features and bug fixes.

Press |y| to update or any other key to cancel.
'''
),

    'm-update-notification-ok': ('Update Notification',
r'''
|PyRadio| will now be updated!

The program will now terminate so that the update_
procedure can start.

Press any key to exit |PyRadio|.

'''
),

    'm-update-notification-ok-win': ('Update Notification',
r'''
|PyRadio| will now terminate and the update script
 will be created.

When Explorer opens please double click on
"|update.bat|" to start the update procedure.

Press any key to exit |PyRadio|.

'''
),

    'm-update-notification-nok': ('',
r'''
You have chosen not to update |PyRadio| at this time!

Please keep in mind that you are able to update
at any time using the command:

___________________|pyradio -U|

'''
),

    'm-rec-enabled': ('Recording Enable',
r''' _____Next time you play a station,
_____it will be |written to a file|!

A |[r]| at the right top corner of the window
indicates that recording is |enabled|.
A |[R]| indicates that a station is actually
|being recorded| to a file.

Press |x| to not show this message again, or'''
),

    'm-rec-disabled': ('Recording Disabled',
r'''
Recording will actually continue until
you stop the playback of the station!

'''
),

    'm-rec-not-supported': ('Recording not supported!',
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

    'm-rec-dir-move': ('',
r'''
______Moving |Recordings Directory______
____________Please wait...

'''
),

    'm-rec-dir-move-error': ('Error',
r'''
______Moving |Recordings Directory| has |failed!!|______
Moving from
|{}|
to
|{}|

Press any key to open the directories in file explorer...

'''
),

    'm-manage-players-win': ('Players Management',
r'''
Players management |enabled|!

|PyRadio| will now terminate so that you can
|manage| installed players.

'''
),

    'm-uninstall-win': ('Uninstall PyRadio',
r'''
Are you sure you want to uninstall |PyRadio|?

Please press |y| to confirm or any other key to decline.

'''
),

    'm-remove-old-installation': ('PyRadio',
r'''
|PyRadio| will now try to remove any files found on your
system belonging to a pre |0.8.9.15| installation.

'''
),

    'm-show-unnamed-register': ('Unnamed Register',
r'''
___{}___

'''
),

    'm-change-player-one-error': ('PyRadio',
r'''
You have requested to change the |Media Player| but
there's only one player detected.

If you have already installed any other player
(|{0}| or |{1}|), please make sure its executable
is in your PATH.

'''
),

    'm-change-player-the-same-error': ('PyRadio',
r'''
|{}|: Media Player already active.

You have requested to change the |Media Player| to
the one that's already active.

Please try selecting a different |Media Player|.

'''
),

    'm-not-implemented': ('PyRadio',
r'''
___This feature has not been implemented yet...___

'''
),

        }
        # INSERT NEW ITEMS ABOVE
        logger.error('args = "{}"'.format(args))
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
        logger.info('self.active_message_key = {} '.format(self.active_message_key))
        logger.info('self._last_key = {} '.format(self._last_key))
        logger.info('self._same_content = {} '.format(self._same_content))
        if  self._same_content:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('Redisplaying last Messaging System Active key...')
        else:
            self._caption, l, max_len = self._get_txt(*args)
            if l is None:
                return
            if max_len < self._main_win_width:
                self._maxX = max_len
            else:
                self._maxX = self._main_win_width
            logger.error('self._caption = "{}"'.format(self._caption))
            logger.error('max_len = {0}, self._maxY = {1}'.format(max_len, self._maxX))
            for n in l:
                logger.info(n)
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
            self._populate_pad(l)
        self.simple_dialog = False
        self._txt = {}

    def __init__(self, config, op_mode, prev_op_mode):
        self._main_win_width = 73
        self._columnX = 22
        self._cnf = config
        self._pad_height = 32767
        self._operation_mode = op_mode
        self._previous_operation_mode = prev_op_mode

    def set_token(self, token):
        self._active_token = None
        logger.error('senf_tokens = {}'.format(self._tokens))
        if token in self._tokens.keys():
            self._active_token = self._tokens[token]
            logger.info('setting self._pad_pos to {}'.format(self._pad_pos))

    def _get_txt(self, *args):
        '''
            args[0] = message_key

            Format is:
                (
                    Help Window Caption,
                    r text (string)
                )
        '''
        logger.error('args = "{}"'.format(args))
        cap, out = self._txt[self.active_message_key]
        if out is None:
            return None, None, 0

        ''' apply per item customization / variables '''
        if self.active_message_key == 'h-main' and \
                platform.startswith('win'):
            out = self._txt[self.active_message_key][1].replace(
                    '|opposite ', '|upward ').replace('[| / |]', 'F2| / |F3')
        elif self.active_message_key == 'h-main' and \
                platform.lower().startswith('darwin'):
            out = self._txt[self.active_message_key][1].replace(
                    '|opposite ', '|upward ')
        elif self.active_message_key == 'h-playlist':
            if self._cnf.open_register_list:
                out = self._txt[self.active_message_key][1].replace(
                        'playlist', 'register')
                cap=' Registers List Help '
        elif self.active_message_key == 'h-dir':
            out = self._txt[self.active_message_key][1].format(args[1])
        elif (self.active_message_key == 'h-search' or self.active_message_key == 'h-line-editor') and \
                platform.startswith('win'):
            out = self._txt[self.active_message_key][1].replace('M-', 'A-')
        elif self.active_message_key == 'h-config-encoding':
            if self._operation_mode() == Window_Stack_Constants.SELECT_ENCODING_MODE:
                out = out.replace('r c  ', 'r    ').replace('Revert to station / |c|onfig value.', 'Revert to saved value.')
        elif self.active_message_key in (
                'd-rc-active',
                'm-rc-start-error',
                'd-rb-ask-to-save-config',
                'd-rb-ask-to-save-config-to-exit',
                'm-rc-dead-error',
                'd-update-notification',
                'm-playlist-delete-error',
                'd-playlist-delete-ask',
                'd-group-delete-ask',
                'd-station-delete-ask',
                'd-station-delete-ask-locked',
                'm-show-unnamed-register',
                'm-change-player-the-same-error',
                ):
            out = self._txt[self.active_message_key][1].format(args[1])
        elif self.active_message_key in (
                'm-rb-vote-result',
                'm-rec-dir-move-error',
                'm-change-player-one-error',
                ):
            out = self._txt[self.active_message_key][1].format(args[1], args[2])

        self._tokens, l = self._parse_strings_for_tokens(out.splitlines())
        logger.error('\n\nself._tokens = {}'.format(self._tokens))
        # get max len
        if logger.isEnabledFor(logging.INFO):
            logger.info('>>> Message System: setting key to "{}"'.format(self.active_message_key))
            self._last_key = self.active_message_key
        if self.active_message_key == 'h-main':
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
                            first_column.append(x[0].strip().replace('%', '').replace('!', '').replace('|', ''))
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
                for n in l:
                    x = n.split('|*|')
                    if len(x) == 2:
                        first_column.append(x[0].strip().replace('%', '').replace('!', '').replace('|', ''))
                        x[-1] = '-' * (column + 2) + x[-1]
                    last_column.append(x[-1].strip().replace('%', '').replace('!', '').replace('|', ''))
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
        logger.error('self._max_lens\n{}'.format(self._max_lens))
        if mmax < len(cap) + 6:
            mmax = len(cap) + 6
        return cap, l, mmax

    def _get_active_message_key(self, *args):
        if args:
            self.active_message_key = args[0] if args[0] else 'h-main'
            logger.error('\n\n\n')
            logger.error('args[0]'.format(args[0]))
            try:
                logger.error('args[1]'.format(args[1]))
            except:
                logger.error('args[1] = N/A')
            logger.error('\n\n\n')
        ''' self.active_message_key transformation '''
        if self.active_message_key == 'h-search' and \
                platform.startswith('darwin'):
            self.active_message_key = 'h-search-darwin'
        elif self.active_message_key == 'h-extra':
            if self._operation_mode() == Window_Stack_Constants.NORMAL_MODE or \
                        (self._operation_mode() == Window_Stack_Constants.HELP_MODE and \
                        self._previous_operation_mode() == Window_Stack_Constants.NORMAL_MODE):
                if self._cnf.is_register:
                    out = out.replace('C   ', 'c  ').replace(
                            'current playlist', 'current register').replace(
                                '|C|lear all registers.', 'Clear |c|urrent register.')
            else:
                if self._cnf.open_register_list:
                    self.active_message_key = 'h-extra-registers-list'
                else:
                    self.active_message_key = 'h-extra-playlist'
        elif self.active_message_key == 'h-lines-editor':
            if platform.lower().startswith('dar'):
                self.active_message_key = 'h-line-editor-darwin'
        elif self.active_message_key == 'h-external-line-editor':
            self._txt['h-external-line-editor'] = (
                    'Line Editor Help',
                    args[1]()
            )
        elif self.active_message_key == 'h-config-player':
            self._txt['h-config-player'] = (
                    'Player Extra Parameters Help',
                    args[1]()
            )
        elif self.active_message_key == 'm-update-notification-ok' and \
                platform.startswith('win'):
            self.active_message_key = 'm-update-notification-ok-win'
        elif self.active_message_key == 'm-rb-config-save-error' and \
                platform.startswith('win'):
            self.active_message_key = 'm-rb-config-save-error-win'

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

    def _get_win(self):
        p_height, p_width = self._parent.getmaxyx()
        self._maxY = p_height - 2
        # self._maxX = self._main_win_width
        if p_width < self._maxX or self._maxY < 10:
            self.too_small = True
            self._can_scroll = False
            txt = ' Window too small '
            self._maxY = 3
            self._maxX = len(txt) + 2
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
            return
        else:
            self.too_small = False
            pY, pX = self._parent.getbegyx()
            if self._lines_count + 2 < self._maxY:
                self._can_scroll = False
                self._maxY = self._lines_count + 2
                self._winY = int((p_height - self._maxY) / 2) + pY
            else:
                self._can_scroll = True
                self._winY = int((p_height - self._maxY) / 2) + pY
            # if not ( p_height % 2 ):
            #     self._winY += 1
            self._winX = int((p_width - self._maxX) / 2) + pX
            logger.error('newwin maxX = {}'.format(self._maxX))
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

    def _echo_line(self, Y, X, formated, reverse=False):
        for k, l in enumerate(formated):
            if reverse:
                col = self.col_highlight if k % 2 else self.col_txt
            else:
                col = self.col_txt if k % 2 else self.col_highlight
            if k == 0:
                self._pad.addstr(Y, X, l.replace('_', ' '), col)
                logger.error('printing: {0} - "{1}"'.format(X, l))
            else:
                if l:
                    self._pad.addstr(l.replace('_', ' '), col)

    def _populate_pad(self, l):
        self._pad.erase()
        for i, n in enumerate(l):
            out = n.strip()
            if out.strip().startswith('%'):
                logger.info('striped out = "{}"'.format(out))
                self._pad.addstr(i, 1, '─' * (self._maxX-4), self.col_box)
                logger.error('Y = {}'.format(i))
                logger.error('Y = {}'.format(self._maxX - len(n) - 5))
                logger.error('text   n: " {} "'.format(n[1:]))
                logger.error('text out: " {} "'.format(out[1:]))
                logger.error('len = {}'.format(len(out[1:])+2))
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
            logger.info('self._pad_pos = {}'.format(self._pad_pos))
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
            x.set_text('h-main')
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
