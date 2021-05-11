# -*- coding: utf-8 -*-

""" Theming constants """
def FOREGROUND(): return 0
def BACKGROUND(): return 1

# for pop up window
CAPTION = 2
BORDER = 3

"""
Format of theme configuration
    Name, color_pair, foreground, background
If foreground == 0, color can be edited
If > 0, get color from list item referred to by number
Same for the background
"""
THEME_ITEMS = (
    ('PyRadio URL', 2, 0, 3),
    ('Messages Border', 3, 0, 3),
    ('Status Bar', 7, 0, 0),
    ('Stations', 5, 0, 0),
    ('Active Station', 4, 0, 3),
    ('Normal Cursor', 6, 0, 0),
    ('Active Cursor', 9, 0, 0),
    ('Edit Cursor', 8, 0, 0)
)

""" Messages to display when player starts / stops
    Used in log to stop runaway threads from printing
    messages after playback is stopped """
player_start_stop_token = ('Initialization: "',
                           ': Playback stopped',
                           ': Player terminated abnormally!')

def erase_curses_win(self, Y, X, beginY, beginX, char=' ', color=5):
    ''' empty a part of the screen
    '''
    empty_win = curses.newwin(
        Y - 2, X - 2,
        beginY + 1, beginX + 1
    )
    empty_win.bkgdset(char, curses.color_pair(color))
    empty_win.erase()
    empty_win.refresh()

