# -*- coding: utf-8 -*-
import io
from os.path import exists

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
_param_to_color_id = {
    'Extra Func': (12, ),
    'PyRadio URL': (11, ),
    'Messages Border': (10, ),
    'Status Bar': (8, 9),
    'Stations': (1, 2),
    'Active Station': (3, ),
    'Active Cursor': (6, 7),
    'Normal Cursor': (4, 5),
}

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
player_start_stop_token = ('Initialization: ',
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

def is_rasberrypi():
    ''' Try to detest rasberry pi '''
    try:
        with io.open('/sys/firmware/devicetree/base/model', 'r') as m:
            if 'raspberry pi' in m.read().lower():
                return True
    except Exception:
        pass
    return False

    # if exists('/usr/bin/raspi-config'):
    #     return True
    # return False

def hex_to_rgb(hexadecimal):
    n = hexadecimal.lstrip('#')
    return tuple(int(n[i:i+2], 16) for i in (0, 2, 4))

def rgb_to_hex(rgb):
    return '#%02x%02x%02x' % rgb

def curses_rgb_to_hex(rgb):
    return rgb_to_hex(tuple(int(y * 255 / 1000) for y in rgb))

def rgb_to_curses_rgb(rgb):
    return tuple(int(y / 255 * 1000) for y in rgb)




