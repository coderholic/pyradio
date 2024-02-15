#!/usr/bin/env python
import curses
import logging
from curses.ascii import ACK as KEY_ACK, STX as KEY_STX
from sys import platform
from .window_stack import Window_Stack_Constants

import locale
locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

class PyRadioHelp(object):

    too_small = False
    _can_scroll= True
    _columns = {}
    _max_lens = {}

    def __init__(self, config, op_mode, prev_op_mode):
        self._main_win_width = 73
        self._columnX = 22
        self._cnf = config
        self._pad_height = 32767
        self._operation_mode = op_mode
        self._previous_operation_mode = prev_op_mode

    def _get_txt(self, *args):
        '''
            args[0] = help_key

            Format is:
                (
                    Help Window Caption,
                    r text (string)
                )
        '''
        txt = {
        'main': ('PyRadio Help',
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

!RadioBrowser
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

        'playlist': ('Playlist Help',
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

        'theme': ('Theme Help',
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

        'group': ('Group Selection Help',
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

    'yank': ('Copy Mode Help',
r'''ENTER                           |*| Copy station to unnamed register.
a-z| / |0-9                         |*| Copy station to named register.

Any other key exits current mode.

'''
),

    'registers': ('Registers Mode Help',
r'''ENTER                           |*| Open registers list.
a-z| / |0-9                         |*| Open named register.

Any other key exits current mode.

'''
),

    'extra': ('Extra Commands Help',
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

    'extra-registers-list': ('Extra Commands Help',
r'''r                               |*| |R|ename current register.
p                                   |*| |P|aste to current register.
c                                   |*| Clear |c|urrent register.
C                                   |*| |C|lear all registers.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

Any other key exits current mode.
'''
),

    'extra-playlist': ('Extra Commands Help',
r'''n                               |*| Create a |n|ew playlist.
p                                   |*| |P|aste to current playlist.
r                                   |*| |R|ename current playlist.
u                                   |*| Show |U|nnamed Register.
o                                   |*| |O|pen dirs in file manager.

|Any other key exits current mode.
'''
),

    'rb-search': ('RadioBrowser Search Help',
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

    'rb-config': ('RadioBrowser Config Help',
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

    'config': ('Configuration Help',
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

    'config-station': ('Station Selection Help',
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

    'config-playlist': ('Playlist Selection Help',
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

    'config-encoding': ('Encoding Selection Help',
r'''Arrows|, |h|, |j|, |k|,         |*|
l|, |PgUp|, |,PgDn                 |*|
g|, |Home|, |G|, |End               |*| Change encoding selection.
Enter|, |Space|, |s                 |*| Save encoding.
r c                                 |*| Revert to station / |c|onfig value.
Esc|, |q                            |*| Cancel.
%Global functions
-|/|+| or |,|/|.                    |*| Change volume.
m| / |v                             |*| |M|ute player / Save |v|olume (not in vlc).
W| / |w                             |*| Toggle title log / like a station.'''
),

    'dir': ('Open Directory Help',
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

    'search': ('Search Help',
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

    'search-darwin': ('Search Help',
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

    'line-editor': ('Line Editor Help',
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

    'line-editor-darwin': ('Line Editor Help',
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

    'session-locked': ('Session Locked',
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

    'mouse-restart': ('Program Restart required',
r'''
You have just changed the |mouse support| config
option.

|PyRadio| must be |restarted| for this change to
take effect.

'''
),
        }
        active_help_key = args[0] if args[0] else 'main'
        ''' active_help_key transformation '''
        if active_help_key == 'search' and \
                platform.startswith('darwin'):
            active_help_key = 'search-darwin'
        elif active_help_key == 'extra':
            if self._operation_mode() == Window_Stack_Constants.NORMAL_MODE or \
                        (self._operation_mode() == Window_Stack_Constants.HELP_MODE and \
                        self._previous_operation_mode() == Window_Stack_Constants.NORMAL_MODE):
                if self._cnf.is_register:
                    out = out.replace('C   ', 'c  ').replace(
                            'current playlist', 'current register').replace(
                                '|C|lear all registers.', 'Clear |c|urrent register.')
            else:
                if self._cnf.open_register_list:
                    active_help_key = 'extra-registers-list'
                else:
                    active_help_key = 'extra-playlist'
        elif active_help_key == 'lines-editor':
            if platform.lower().startswith('dar'):
                active_help_key = 'line-editor-darwin'
        elif active_help_key == 'external-line-editor':
            txt['external-line-editor'] = (
                    'Line Editor Help',
                    args[1]()
            )
        elif active_help_key == 'config-player':
            txt['config-player'] = (
                    'Player Extra Parameters Help',
                    args[1]()
            )

        cap, out = txt[active_help_key]
        if out is None:
            return None, None, 0

        ''' apply per item customization / variables '''
        if active_help_key == 'main' and \
                platform.startswith('win'):
            out = txt[active_help_key][1].replace(
                    '|opposite ', '|upward ').replace('[| / |]', 'F2| / |F3')
        elif active_help_key == 'main' and \
                platform.lower().startswith('darwin'):
            out = txt[active_help_key][1].replace(
                    '|opposite ', '|upward ')
        elif active_help_key == 'playlist':
            if self._cnf.open_register_list:
                out = txt[active_help_key][1].replace(
                        'playlist', 'register')
                cap=' Registers List Help '
        elif active_help_key == 'dir':
            out = txt[active_help_key][1].format(args[1])
        elif (active_help_key == 'search' or active_help_key == 'line-editor') and \
                platform.startswith('win'):
            out = txt[active_help_key][1].replace('M-', 'A-')
        elif active_help_key == 'config-encoding':
            if self._operation_mode() == Window_Stack_Constants.SELECT_ENCODING_MODE:
                out = out.replace('r c  ', 'r    ').replace('Revert to station / |c|onfig value.', 'Revert to saved value.')

        l = out.splitlines()
        # get max len
        if logger.isEnabledFor(logging.INFO):
            logger.info('help active key = "{}"'.format(active_help_key))
        if active_help_key == 'main':
            mmax = self._main_win_width
            column = 22
        else:
            first_column = []
            last_column = []
            if active_help_key in self._columns.keys():
                column =  self._columns[active_help_key]
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
                self._columns[active_help_key] = column
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('column from calculation = {}'.format(column))
            if active_help_key in self._max_lens.keys():
                mmax =  self._max_lens[active_help_key]
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
                self._max_lens[active_help_key] = mmax
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('max len from calculation = {}'.format(mmax))
        self._columnX = column
        if active_help_key == 'config-player':
            self._columns.pop(active_help_key)
            self._max_lens.pop(active_help_key)
        return cap, l, mmax

    def set_text(self, parent, *args):
        '''
            args[0] = help_key
        '''
        self.col_txt = curses.color_pair(10)
        self.col_box = curses.color_pair(3)
        self.col_highlight = curses.color_pair(11)
        if parent is not None:
            self._parent = parent
        if args:
            help_key = args[0]
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
            self._win.addstr(0, int((self._maxX - len(self._caption)) / 2) - 2, ' ' + self._caption + ' ', self.col_highlight)

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
                    # print help description
                    formated = lines[1].split('|')
                    self._echo_line(i, self._columnX, formated, reverse=True)
                else:
                    self._echo_line(i, 1, [''] + lines[0].split('|'))
            self._pad_refresh()

    def show(self, parent=None):
        if parent is not None:
            self._parent = parent
            self._get_win()
        if self.too_small:
            if self._win is not None:
                self._win.refresh()
        else:
            self._win.refresh()
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

    x = PyRadioHelp()
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
            x.set_text('main')
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
