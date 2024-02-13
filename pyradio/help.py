#!/usr/bin/env python
import curses
from sys import platform

import locale
locale.setlocale(locale.LC_ALL, "")

def get_txt(help_key=None):
    txt = {
        'main': ('PyRadio Help',r'''__Welcome to |PyRadio Main Help
__You can use the following keys to navigate: |j| (|Up|), |k| (|Down|),
|PgUp| (|^B|), |PgDn| (|^F|) to scroll up/down.
__You can also use |g| (|HOME|) / |G| (|END|) to scroll to the top / bottom.

__ You will have noticed the two |opposite arrows| at the top right
corner of this window; they indicate that the text is |scrollable| and
the keys mentioned above are |valid|; if the arrows are not there, the
text is not scrollable and pressing any key will |close the window|.

!Gerneral Help
Up|, |j|, |PgUp|, |*|
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

!Moving stations
J                                   |*| Create a |J|ump tag.
<n>^U|,|<n>^D                       |*| Move station |U|p / |D|own.
                                    |*| If a |jump tag| exists, move it there.

!Searching
/| / |n| / |N                       |*|  Search, go to next / previous result.

!Stations' history
< |/| >                             |*|  Move to previous / next station.

!Extra Command mode (\\)
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

!Player Customization
z                                   |*|  Toggle |Force http connections|
Z                                   |*|  Extra player parameters

!Mouse Support
Click                               |*|  Change selection.
Double click                        |*|  Start / stop the player.
Middle click                        |*|  Toggle mute.
Wheel                               |*|  Page up / down.
Shift-Wheel                         |*|  Adjust volume.

!Recording
Veritcal line                       |*|  Enable / disable |recording|.
Space                               |*|  Pause / resume playback.

!Change Player
\m                                  |*|  Open the |Player Selection| window.

!Remote Control Server
\s                                  |*|  Start/Stop the |Server|.

!Title Logger
W                                   |*|  Toggle Logger on/off
w                                   |*|  Tag a station as liked

!Group Management
a A                                 |*|  Add a |Group| (sets |URL| to "|-|").
^E |/ |^Y                           |*|  Go to next /previous |Group|.
^G                                  |*|  Open the |Group Selection| window.

!Windows Only
F8                                  |*|  Players management.
F9                                  |*|  Show |EXE| location.
F10                                 |*|  Uninstall |PyRadio|.

!RadioBrowser
O                                   |*|  Open |RadioBrowser|.
c                                   |*|  Open |c|onfig window.
C                                   |*|  Select server to |c|onnect to.
s                                   |*|  |S|earch for stations.
[| / |]                             |*|  Fetch previous / next page.
S                                   |*|  |S|ort search results.
I                                   |*|  Station |i|nfo (current selection).
V                                   |*|  |V|ote for station.
\ q Escape                          |*|  Close Browser (go back in history).

Search history navigation works with normal keys as well
__(|^N| is the same as |n| when not in a line editor).
'''),
    'page5': ('Page 5', r'''!Recording
Veritcal line    |*| Enable / disable |recording|.
Space            |*| Pause / resume playback.

!Change Player
\m               |*| Open the |Player Selection| window.

!Remote Control Server
\s               |*| Start/Stop the |Server|.

!Title Logger
W                |*| Toggle Logger on/off
w                |*| Tag a station as liked

!Group Management
a A              |*| Add a |Group| (sets |URL| to "|-|").
^E |/ |^Y        |*|  Go to next /previous |Group|.
^G               |*| Open the |Group Selection| window.

!Windows Only
F8               |*| Players management.
F9               |*| Show |EXE| location.
F10              |*| Uninstall |PyRadio|.

''')
    }
    active_help_key = help_key if help_key else 'main'
    if active_help_key == 'main' and \
            platform.startswith('win'):
        out = txt[active_help_key][1].replace(
                '|opposite ', '|upward ').replace('[| / |]', 'F2| / |F3')
    else:
        out = txt[active_help_key][1]
    return txt[active_help_key][0], out.splitlines()

class PyRadioHelp(object):

    too_small = False
    _can_scroll= True

    def __init__(self):
        self._pad_height = 32767

    def set_text(self, parent=None, help_key=None):
        self.col_txt = curses.color_pair(10)
        self.col_box = curses.color_pair(3)
        self.col_highlight = curses.color_pair(11)
        if parent is not None:
            self._parent = parent
        self._caption, l = get_txt(help_key)
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
        self._maxX = 73
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
                if platform.startswith('win'):
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
            else:
                if l:
                    self._pad.addstr(l.replace('_', ' '), col)

    def _populate_pad(self, l):
        w = 22
        self._pad.erase()
        for i, n in enumerate(l):
            out = n.strip()
            if out.startswith('!'):
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
                    self._echo_line(i, w, formated, reverse=True)
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
                if self._lines_count - self._maxY + 1 >= self._pad_pos:
                    self._pad_pos += 1
                    self._pad_refresh()
            elif char in (curses.KEY_UP, ord('k')):
                if self._pad_pos > 1:
                    self._pad_pos -= 1
                    self._pad_refresh()
            elif char in (curses.KEY_NPAGE, 6):
                if self._lines_count - self._maxY - 4 >= self._pad_pos + self._maxY + 2:
                    self._pad_pos += (self._maxY - 3)
                else:
                    self._pad_pos = self._lines_count - self._maxY + 3
                self._pad_refresh()
            elif char in (curses.KEY_PPAGE, 2):
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
