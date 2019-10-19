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
THEME_ITEMS = ( ('PyRadio URL', 2, 0, 3),
        ('Messages Border', 3, 0 ,3),
        ('Status Bar', 7, 0, 0),
        ('Stations', 5, 0 ,0),
        ('Active Station', 4, 0, 3),
        ('Normal Cursor', 6, 0, 0),
        ('Active Cursor', 9, 0, 0),
        ('Edit Cursor', 8, 0, 0 ) )
