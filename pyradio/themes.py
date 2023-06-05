# -*- coding: utf-8 -*-
import curses
import sys
import logging
import glob
from sys import version_info
from os import path, getenv, makedirs, remove, sep as dir_sep, access, R_OK
from shutil import copyfile, move
from copy import deepcopy
from math import sqrt
import colorsys
from .log import Log
from .common import *

logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

PY3 = sys.version[0] == '3'

def isLightOrDark(rgbColor=[0,128,255]):
    [r,g,b]=rgbColor
    '''
    https://stackoverflow.com/questions/22603510/is-this-possible-to-detect-a-colour-is-a-light-or-dark-colour
    '''
    #hsp = sqrt(0.299 * (r * r) + 0.587 * (g * g) + 0.114 * (b * b))
    #if (hsp>127.5):
    #    return True
    #    return 'light'
    #else:
    #    return False
    #    return 'dark'

    '''
    https://stackoverflow.com/questions/12043187/how-to-check-if-hex-color-is-too-black
    '''
    hsp = sqrt(0.241 * (r * r) + 0.691 * (g * g) + 0.068 * (b * b))
    # logger.error('hsp = {}'.format(hsp))

    if (hsp>130):
        return True
        return 'light'
    else:
        return False
        return 'dark'

def calculate_fifteenth_color(colors, an_amount, inhibit_if_color15_exists=True):
    if an_amount == '0' or \
            (15 in colors.keys() and \
             inhibit_if_color15_exists
            ):
        if logger.isEnabledFor(logging.INFO):
            logger.info('Cannot calculating color15...')
        return colors[2]

    if logger.isEnabledFor(logging.INFO):
        logger.info('Calculating color15...')
    amount = round(float(an_amount) ,2)
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('Luminance color factor = {}'.format(amount))
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('color2: {}'.format(colors[2]))
    x = list(colorsys.rgb_to_hls(
        float(colors[2][0] / 255.0),
        float(colors[2][1] / 255.0),
        float(colors[2][2] / 255.0)
    ))
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('hls: {}'.format(x))
    #logger.error('x = {}'.format(x))

    start_x1 = x[1]
    action = x[1] < .5

    # luma = 0.2126 * colors[2][0] + 0.7152 * colors[2][1] + 0.0722 * colors[2][2]
    # logger.error('luma = {}'.format(luma))

    action = not isLightOrDark(colors[2])
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('color is dark = {}'.format(action))
    count = 0

    y = list(x)
    if action:
        y = list(colorsys.hls_to_rgb(x[0], x[1] + amount, x[2]))
    else:
        y = list(colorsys.hls_to_rgb(x[0], x[1] - amount, x[2]))

    for count in range(0, 15):
        if action:
            x[1] += amount
        else:
            x[1] -= amount

        if 0 < x[1] < 1:
            # x[1] = amount * (1 - x[1])

            y = list(colorsys.hls_to_rgb(x[0], x[1], x[2]))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('  luminance {0}: {1}'.format(count, x[1]))

            if abs(y[0] - colors[10][0]) > 15 and \
                    abs(y[1] - colors[11][1]) > 15 and \
                    abs(y[2] - colors[12][2]) > 15 :
                break

            if count == 8:
                action = not action
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('flipping algorithm...')
                x[1] = start_x1
        else:
            break

    #logger.error('y = {}'.format(y))
    for n in range(0,3):
        y[n] = round(y[n] * 255)

    if logger.isEnabledFor(logging.DEBUG):
        logger.debug('color15: {}'.format(y))
    return tuple(y)

class PyRadioTheme(object):
    _colors = {}
    _active_colors = {}
    _read_colors = {}
    _temp_colors = {}

    applied_theme_name = 'dark'

    config_dir = ''


    def __init__(self, cnf):
        self._cnf = cnf
        # self._terminals_colors = tuple(curses.color_content(x) for x in range(0, 16))

    def __del__(self):
        self._colors = None
        self._active_colors = None
        self._read_colors = None
        self._temp_colors = None

    def calculate_transparency(self, transparency=None):
        transp = False
        if transparency is None:
            if self._active_colors['transparency'] == 0:
                transp = False
            elif self._active_colors['transparency'] == 1:
                transp = True
            else:
                transp = self._cnf.use_transparency
        else:
            if transparency == 0:
                transp = False
            elif transparency == 1:
                transp = True
            else:
                transp = self._cnf.use_transparency
        return transp

    def _do_init_pairs(self, transparency=None):
        if self._cnf.use_themes:
            transp = self.calculate_transparency(transparency)
            logger.info('=============')
            logger.info('transp = {}'.format(transp))

            border_color = 16  if curses.COLORS > 16 else 1
            if self._cnf.use_calculated_colors or \
                   self._cnf.has_border_background:
                if transp:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('--> 1 transparency: ON (use_calculated_colors: {0}, has_border_background: {1})'.format(self._cnf.use_calculated_colors, self._cnf.has_border_background))
                    colors = {
                        1: (12 + self._cnf.start_colors_at, -1),
                        2: (11 + self._cnf.start_colors_at, -1),
                        3: (10 + self._cnf.start_colors_at, -1),
                        4: (3 + self._cnf.start_colors_at, -1),
                        5: (1 + self._cnf.start_colors_at, -1),
                        6: (4 + self._cnf.start_colors_at, 5 + self._cnf.start_colors_at),
                        7: (8 + self._cnf.start_colors_at, 9 + self._cnf.start_colors_at),
                        8: (13 + self._cnf.start_colors_at, 14 + self._cnf.start_colors_at),
                        9: (6 + self._cnf.start_colors_at, 7 + self._cnf.start_colors_at),
                        10: (1 + self._cnf.start_colors_at, -1),
                        11: (3 + self._cnf.start_colors_at, -1),
                        12: (10 + self._cnf.start_colors_at, -1),
                        13: (border_color + self._cnf.start_colors_at, -1),
                        14: (9 + self._cnf.start_colors_at, -1)
                    }
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('--> 1 transparency: OFF (use_calculated_colors: {0}, has_border_background: {1})'.format(self._cnf.use_calculated_colors, self._cnf.has_border_background))
                    colors = {
                        1: (12 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        2: (11 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        3: (10 + self._cnf.start_colors_at, 15 + self._cnf.start_colors_at),
                        4: (3 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        5: (1 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        6: (4 + self._cnf.start_colors_at, 5 + self._cnf.start_colors_at),
                        7: (8 + self._cnf.start_colors_at, 9 + self._cnf.start_colors_at),
                        8: (13 + self._cnf.start_colors_at, 14 + self._cnf.start_colors_at),
                        9: (6 + self._cnf.start_colors_at, 7 + self._cnf.start_colors_at),
                        10: (1 + self._cnf.start_colors_at, 15 + self._cnf.start_colors_at),
                        11: (3 + self._cnf.start_colors_at, 15 + self._cnf.start_colors_at),
                        12: (10 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        13: (border_color + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        14: (9 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at)
                    }
            else:
                if transp:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('--> 2 transparency: ON (use_calculated_colors: {0}, has_border_background: {1})'.format(self._cnf.use_calculated_colors, self._cnf.has_border_background))
                    colors = {
                        1: (12 + self._cnf.start_colors_at, -1),
                        2: (11 + self._cnf.start_colors_at, -1),
                        3: (10 + self._cnf.start_colors_at, -1),
                        4: (3 + self._cnf.start_colors_at, -1),
                        5: (1 + self._cnf.start_colors_at, -1),
                        6: (4 + self._cnf.start_colors_at, 5 + self._cnf.start_colors_at),
                        7: (8 + self._cnf.start_colors_at, 9 + self._cnf.start_colors_at),
                        8: (13 + self._cnf.start_colors_at, 14 + self._cnf.start_colors_at),
                        9: (6 + self._cnf.start_colors_at, 7 + self._cnf.start_colors_at),
                        10: (1 + self._cnf.start_colors_at, -1),
                        11: (3 + self._cnf.start_colors_at, -1),
                        12: (10 + self._cnf.start_colors_at, -1),
                        13: (border_color + self._cnf.start_colors_at, -1),
                        14: (9 + self._cnf.start_colors_at, -1),
                    }
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('--> 2 transparency: OFF (use_calculated_colors: {0}, has_border_background: {1})'.format(self._cnf.use_calculated_colors, self._cnf.has_border_background))
                    colors = {
                        1: (12 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        2: (11 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        3: (10 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        4: (3 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        5: (1 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        6: (4 + self._cnf.start_colors_at, 5 + self._cnf.start_colors_at),
                        7: (8 + self._cnf.start_colors_at, 9 + self._cnf.start_colors_at),
                        8: (13 + self._cnf.start_colors_at, 14 + self._cnf.start_colors_at),
                        9: (6 + self._cnf.start_colors_at, 7 + self._cnf.start_colors_at),
                        10: (1 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        11: (3 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        12: (10 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        13: (border_color + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at),
                        14: (9 + self._cnf.start_colors_at, 2 + self._cnf.start_colors_at)
                    }
            for k in colors.keys():
                curses.init_pair(k, colors[k][0], colors[k][1])
            # curses.start_color()

    def restoreActiveTheme(self):
        self._active_colors = deepcopy(self._read_colors)
        self._do_init_pairs()
        self._update_colors()
        # curses.start_color()

    def readAndApplyTheme(self, a_theme, print_errors=None, **kwargs):
        """ Read a theme and apply it

            Returns:
              -2: theme not supported (default theme loaded)
              -1: theme has error (default theme loaded)
               0: all ok
        """
        self._cnf.theme_download_failed = False
        self._cnf.theme_has_error = False
        self._cnf.theme_not_supported = False
        self._cnf.theme_not_supported_notification_shown = False
        result = 0
        use_transparency = None
        theme_path = ''
        for name, value in kwargs.items():
            if name == 'use_transparency':
                use_transparency = value
            elif name == 'theme_path':
                theme_path = value
        ret = self.open_theme(a_theme, theme_path, print_errors)
        if ret < 0:
            self._load_default_theme(self.applied_theme_name)
            result = -1, self.applied_theme_name
        # elif self._applied_theme_max_colors > curses.COLORS:
        #     self._load_default_theme(self.applied_theme_name)
        #     result = -2, self.applied_theme_name
        else:
            result = ret, self.applied_theme_name
            self._update_colors()
            self.applied_theme_name = a_theme

        self._active_colors = None
        self._active_colors = deepcopy(self._colors)
        self._do_init_pairs(transparency=self._colors['transparency'])

        self._read_colors = deepcopy(self._colors)
        # logger.error('colors\n{}'.format(self._read_colors))
        return result

    def _load_default_theme(self, a_theme):
        if self._cnf.fallback_theme:
            self.applied_theme_name = self._cnf.fallback_theme
        else:
            self.applied_theme_name = 'dark'
            if a_theme.startswith('light'):
                    self.applied_theme_name = 'light'
            self._cnf.fallback_theme = self.applied_theme_name
        if logger.isEnabledFor(logging.INFO):
            logger.info('Applying fallback theme: "{0}" instead of: "{1}"'.format(self.applied_theme_name, a_theme))
        self.open_theme(self.applied_theme_name)
        self._update_colors()
        try:
            self.outerBodyWin.refresh()
            self.bodyWin.refresh()
            self.footerWin.refresh()
        except AttributeError:
            pass

    def _update_colors(self):
        if self._cnf.use_themes:
            for k in self._colors['data'].keys():
                curse_rgb = rgb_to_curses_rgb(self._colors['data'][k])
                curses.init_color(
                    int(k) + self._cnf.start_colors_at,
                    curse_rgb[0],
                    curse_rgb[1],
                    curse_rgb[2],
                )

    def recalculate_theme(self, inhibit_if_color15_exists=True):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Recalculating color15...')
            logger.debug('Stations background color: {}'.format(self._colors['css'][2]))
        self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
        self._colors['data'][15] = calculate_fifteenth_color(
            self._colors['data'],
            self._cnf.opts['calculated_color_factor'][1],
            inhibit_if_color15_exists
        )
        self._colors['css'][15] = rgb_to_hex(tuple(self._colors['data'][15]))
        self._do_init_pairs()
        self._update_colors()

    def create_theme_from_theme(self, theme_name, out_theme_name):
        ''' Create a theme in theme's directory
            based on an internal or system theme
        '''
        out_file = path.join(self._cnf.themes_dir, out_theme_name + '.pyradio-theme')
        if exists(out_file):
                return False, 'Theme "{}" already exists...'.format(out_theme_name)
        th_name = theme_name if theme_name else 'dark'
        if theme_name not in self._cnf.internal_themes and \
                theme_name not in self._cnf.system_themes:
            th_name = 'dark'
        if th_name in self._cnf.internal_themes:
            ''' create theme file '''
            ret = self.open_theme(th_name, no_curses=True)
            if ret < 0:
                self.open_theme('dark')
            self._active_colors = None
            self._active_colors = deepcopy(self._colors)
            save_theme = PyRadioThemeReadWrite(self._cnf)
            ret = save_theme.write_theme(out_file, colors=self._colors)
            # print(self._colors)
            if ret == 0:
                return True, 'Theme created: "{}"'.format(out_theme_name)
            elif ret == -2:
                return False, 'Error writing theme file: "{}"'.format(out_theme_name)
        else:
            ''' copy theme file '''
            in_file = path.join(path.dirname(__file__), 'themes', theme_name + '.pyradio-theme')
            try:
                copyfile(in_file, out_file)
                return True, 'Theme created: "{}"'.format(out_theme_name)
            except:
                return False, 'Error creating file for theme: "{}"'.format(out_theme_name)

    def open_theme(self, a_theme='', a_path='', print_errors=None, no_curses=False):
        """ Read a theme and place it in _colors
            a_theme: theme name
            a_path:  theme path (enpty if internal theme)

            Returns:
                0: all ok
                """
        ret = 0
        is_internal = True
        if not a_theme.strip():
            a_theme = 'dark'

        if a_theme == 'dark' or a_theme == 'default':
            self._colors['transparency'] = 2
            self._colors['data'] = {1: (192, 192, 192), 2: (0, 0, 0), 3: (0, 128, 0), 4: (0, 0, 0), 5: (135, 0, 135), 6: (0, 0, 0), 7: (0, 128, 0), 8: (0, 0, 0), 9: (0, 128, 0), 10: (128, 128, 0), 11: (95, 135, 255), 12: (0, 255, 255), 14: (192, 192, 192), 13: (0, 0, 0), 15: (26, 26, 26)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (192, 192, 192)
            self._cnf.has_border_background = True

            ''' info '''
            self._colors['Name'] = 'dark'
            self._colors['Path'] = ''
            self.applied_theme_name = 'dark'

        elif a_theme == 'dark_16_colors':
            ''' info '''
            self._colors['transparency'] = 2
            self._colors['Name'] = 'dark_16_colors'
            self._colors['Path'] = ''
            self.applied_theme_name = 'dark_16_colors'
            self._colors['data'] = {1: (255, 255, 255), 2: (128, 128, 128), 3: (0, 255, 0), 8: (0, 0, 0), 9: (0, 255, 0), 4: (0, 0, 0), 5: (255, 0, 255), 6: (0, 0, 0), 7: (0, 255, 0), 12: (0, 255, 255), 11: (0, 0, 255), 10: (255, 255, 0), 13: (255, 255, 255), 13: (128, 128, 128), 15: (154, 154, 154)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (255, 255, 255)
            self._cnf.has_border_background = True

        elif a_theme == 'light':
            ''' info '''
            self._colors['Name'] = 'light'
            self._colors['transparency'] = 0
            self._colors['Path'] = ''
            self.applied_theme_name = 'light'
            self._colors['data'] = {1: (0, 0, 0), 2: (255,255, 255), 3: (128, 0, 0), 8: (192, 192, 192), 9: (0, 0, 128), 4: (192, 192, 192), 5: (128, 0, 128), 6: (192, 192, 192), 7: (0, 0, 128), 12: (0, 0, 128), 11: (0, 0, 128), 10: (128, 0, 128), 13: (255, 255, 255), 14: (128, 0, 0), 15: (230, 230, 230)}
            if curses.COLORS > 16:
                self._colors['data'][16] = (0, 0, 0)
            self._cnf.has_border_background = True

        elif a_theme == 'light_16_colors':
            ''' info '''
            self._colors['Name'] = 'light_16_colors'
            self._colors['transparency'] = 0
            self._colors['Path'] = ''
            self.applied_theme_name = 'light_16_colors'
            self._colors['data'] = {1: (128, 128, 128), 2: (255, 255, 255), 3: (255, 0, 0), 8: (255, 255, 255), 9: (0, 0, 255), 4: (255, 255, 255), 5: (255, 0, 255), 6: (255, 255, 255), 7: (0, 0, 255), 12: (0, 0, 255), 11: (0, 0, 255), 10: (255, 0, 255), 13: (255, 255,255), 14: (255, 0, 0), 15: (230, 230, 230)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (128, 128, 128)
            self._cnf.has_border_background = True

        elif a_theme == 'black_on_white' or a_theme == 'bow':
            ''' info '''
            self._colors['Name'] = 'black_on_white'
            self._colors['transparency'] = 0
            self._colors['Path'] = ''
            self.applied_theme_name = 'black_on_white'
            self._colors['data'] = {1: (128, 128, 128), 2: (255, 255, 255), 3: (0, 0, 0), 8: (255, 255, 255), 9: (138, 138, 138), 4: (255, 255, 255), 5: (128, 128, 128), 6: (0, 0, 0), 7: (128, 128, 128), 12: (0, 255, 255), 11: (138, 138, 138), 10: (138, 138, 138), 14: (0, 0, 0), 13: (255, 255, 255), 15: (229, 229, 229)}
            if curses.COLORS > 16:
                self._colors['data'][16] = (128, 128, 128)
            self._cnf.has_border_background = True

        elif a_theme == 'white_on_black' or a_theme == 'wob':
            ''' info '''
            self._colors['Name'] = 'white_on_black'
            self._colors['transparency'] = 2
            self._colors['Path'] = ''
            self.applied_theme_name = 'white_on_black'
            self._colors['data'] = {1: (158, 158, 158), 2: (38, 38, 38), 3: (238, 238, 238), 8: (28, 28, 28), 9: (218, 218, 218), 4: (38, 38, 38), 5: (158, 158, 158), 6: (38, 38, 38), 7: (218, 218, 218), 12: (218, 218, 218), 11: (138, 138, 138), 10: (158, 158, 158), 13: (0, 0, 0), 14: (169, 169, 169), 15: (52, 52, 52)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (158, 158, 158)
            self._cnf.has_border_background = True

        else:
            ret, ret_ind = self._cnf.is_project_theme(a_theme)
            if ret is not None:
                ''' this is a project theme! '''
                a_path = ret.default_theme_path
                ret.theme_id = ret_ind
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Project theme file name: {}'.format(a_path))
                if not self._cnf.locked:
                    if ret.download(print_errors=print_errors)[0]:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Theme downloaded successfully!')
                    else:
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('Theme download failed!')
                        self._cnf.theme_download_failed = True
                else:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Theme downloaded by main instance!')
                    self._cnf.theme_download_failed = False
            is_internal = False
            if a_path == '':
                a_path = self._get_theme_path(a_theme)
            if a_path == '':
                '''load default theme '''
                #self._load_default_theme(self.applied_theme_name)
                ret = -1
            else:
                ''' read theme from disk '''
                att = PyRadioThemeReadWrite(self._cnf)
                ret, self._temp_colors = att.read_theme(a_theme, a_path)
                if ret == 0:
                    self._colors = deepcopy(self._temp_colors)
                else:
                    #self._load_default_theme(self.applied_theme_name)
                    return -1
            self._colors['Name'] = a_theme

        if is_internal:
            self._colors['css'] = {}
            for k in self._colors['data'].keys():
                self._colors['css'][k] = rgb_to_hex(self._colors['data'][k])

        self.applied_theme_name = self._colors['Name']
        return ret

    def _get_theme_path(self, a_theme):
        #self.root_path = path.join(path.dirname(__file__), 'stations.csv')
        theme_dirs = [path.join(self._cnf.stations_dir, 'themes'),
                      path.join(path.dirname(__file__), 'themes')]
        for theme_dir in theme_dirs:
            files = glob.glob(path.join(theme_dir, '*.pyradio-theme'))
            if files:
                for a_file in files:
                     a_theme_name = a_file.split(dir_sep)[-1].replace('.pyradio-theme', '')
                     if a_theme_name == a_theme:
                         return a_file
        return ''


class PyRadioThemeReadWrite(object):

    _tmeme_name = ''
    _theme_path = ''

    _param_to_color_id = {
        'Extra Func': (12, ),
        'PyRadio URL': (11, ),
        'Messages Border': (10, ),
        'Status Bar': (8, 9),
        'Stations': (1, 2),
        'Active Station': (3, ),
        'Active Cursor': (6, 7),
        'Normal Cursor': (4, 5),
        'Edit Cursor': (13, 14),
        'Border': (16, )
    }

    def __init__(self, config):
        self._cnf = config

    def read_theme(self, theme_name, theme_path):
        """ Opens a theme file and return its contents in self._temp_colors

        Returns:
            0: success
            1: file not found
            2: file not readable
            3: read error
            4: file corrupt
            5: file incomplete
            6: old file format
        """
        # logger.error('read_theme(): theme_name = "{0}", theme_path = "{1}"'.format(theme_name, theme_path))
        self._temp_colors = None
        if not path.isfile(theme_path):
            if logger.isEnabledFor(logging.ERROR):
                logger.error('read_theme(): file not found: {}'.format(theme_path))
            return 1, None
        if not access(theme_path, R_OK):
            if logger.isEnabledFor(logging.ERROR):
                logger.error('read_theme(): file not readable: {}'.format(theme_path))
            return 2, None

        try:
            with open(theme_path, 'r', encoding='utf-8') as thmfile:
                lines = [line.strip() for line in thmfile if line.strip() and not line.startswith('#')]

        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('read_theme(): read error on: {}'.format(theme_path))
            return 3, None

        names = {}
        for line in lines:
            if ',' in line:
                ''' old theme format '''
                # return 5, None
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('read_theme(): old format theme: {}'.format(theme_path))
                return 4, None
            raw = line.split(' ')
            if raw[-1].startswith('#') and len(raw[-1]) != 7:
                ''' corrupt: not valid color '''
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('read_theme(): {0} - invalid color in line: ""{1}: - value: {2}'.format(theme_path, line, raw[-1]))
                return 4, None
            sp = [raw[-1]]
            raw.pop()
            try:
                if raw[-1]:
                    if raw[-1].startswith('#') and len(raw[-1]) != 7:
                        ''' corrupt: not valid color '''
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error('read_theme(): {0} - invalid color in line: ""{1}: - value: {2}'.format(theme_path, line, raw[-1]))
                        return 4, None
                    sp.append(raw[-1])
                    raw.pop()
                sp.append(' '.join(raw).strip())
                if len(sp) > 3:
                    ''' corrupt '''
                    return 4, None
                sp.reverse()
            except IndexError:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error('read_theme(): file is corrupt: {}'.format(theme_path))
                return 4, None
            # logger.error('sp = {}'.format(sp))
            # logger.error('names = {}'.format(names))
            names[sp[0].strip()] = sp[1:]
            for k in names.keys():
                for n in (0, 1):
                    try:
                        names[k][n] = names[k][n].strip()
                    except IndexError:
                        pass

        if curses.COLORS > 16 and \
                'Border' not in names.keys():
            names['Border'] = [names['Stations'][0]]

        logger.error('\n\nnames = {}\n\n'.format(names))
        self._temp_colors = { 'data': {}, 'css': {}, 'transparency': 2}
        for name in names.keys():
            if name != 'transparency':
                try:
                    self._temp_colors['css'][self._param_to_color_id[name][0]] = names[name][0]
                except KeyError:
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error('read_theme(): file is corrupt: {}'.format(theme_path))
                    return 4, None
                self._temp_colors['data'][self._param_to_color_id[name][0]] = hex_to_rgb(names[name][0])
                if len(self._param_to_color_id[name]) == 2:
                    self._temp_colors['css'][self._param_to_color_id[name][1]] = names[name][1]
                    self._temp_colors['data'][self._param_to_color_id[name][1]] = hex_to_rgb(names[name][1])
            elif name == 'transparency':
                self._temp_colors['transparency'] = 2
                try:
                    self._temp_colors['transparency'] = int(names[name][0])
                except (ValueError, TypeError):
                    self._temp_colors['transparency'] = 2
                if not self._temp_colors['transparency'] in range(0,3):
                    self._temp_colors['transparency'] = 2
                logger.error('\n\nset transparency: {}\n\n'.format(self._temp_colors['transparency']))

        if self._theme_is_incomplete():
            if logger.isEnabledFor(logging.ERROR):
                logger.error('read_theme(): file is incomplete: {}'.format(theme_path))
            return 4, None
            return 5, None

        if len(names['Messages Border']) == 2:
            self._temp_colors['css'][15] = names['Messages Border'][-1]
            self._temp_colors['data'][15] = hex_to_rgb(self._temp_colors['css'][15])
            self._cnf.has_border_background = True
            if logger.isEnabledFor(logging.INFO):
                logger.info('read_theme(): color15 = {}'.format(self._temp_colors['css'][15]))
        else:
            self._cnf.has_border_background = False
            self._calculate_fifteenth_color()
            if logger.isEnabledFor(logging.INFO):
                logger.info('read_theme(): calculated color15 = {}'.format(self._temp_colors['css'][15]))

        self._theme_name = theme_name
        self._theme_path = theme_path
        self._temp_colors['Name'] = theme_name
        self._temp_colors['Path'] = theme_path
        self._cnf.active_transparency = self._temp_colors['transparency']
        logger.error('\n\nself._temp_colors\n{}\n\n'.format(self._temp_colors))
        return 0, self._temp_colors

    def _calculate_fifteenth_color(self):
        logger.debug('Stations background color: {}'.format(self._temp_colors['css'][2]))
        self._temp_colors['data'][15] = calculate_fifteenth_color(self._temp_colors['data'], self._cnf.opts['calculated_color_factor'][1])
        self._temp_colors['css'][15] = rgb_to_hex(tuple(self._temp_colors['data'][15]))

    def _theme_is_incomplete(self, some_colors=None):
        colors = self._temp_colors if some_colors is None else some_colors
        for i in range(1, 15):
            if i not in colors['data'].keys():
                return True
        return False

    def write_theme(self, out_theme, base_theme=None, colors=None):
        ''' write a theme

            Parameters
            ==========
            out_theme
                output theme file name
            base_theme
                read colors from this theme file name
            colors
                colors to write

            Return
            ======
               -4   output file already exists
               -3   input file does not exist
               -2   error writing file
               -1   colors are incomplete
                0   all ok
        '''
        if exists(out_theme):
            return -4
        if colors is None:
            if base_theme is not None:
                if not exists(base_theme):
                    return -3
                try:
                    copyfile(base_theme, out_theme)
                    return 0
                except:
                    return -2
            else:
                return -1
        else:
            if self._theme_is_incomplete(colors):
                return -1
            msg = '''# Main foreground and background
Stations            {0} {1}

# Playing station text color
# (background color will come from Stations)
Active Station      {2}

# Status bar foreground and background
Status Bar          {3} {4}

# Normal cursor foreground and background
Normal Cursor       {5} {6}

# Cursor foreground and background
# when cursor on playing station
Active Cursor       {7} {8}

# Cursor foreground and background
# This is the Line Editor cursor
Edit Cursor         {9} {10}

# Text color for extra function indication
# and jump numbers within the status bar
# (background color will come from Stations)
Extra Func          {11}

# Text color for URL
# (background color will come from Stations)
PyRadio URL         {12}

# Message window border foreground and background.
# The background color can be left unset.
# Please refer to the following link for more info
# https://github.com/coderholic/pyradio#calculated_colors
#
Messages Border     {13}

# Theme Transparency
# Values are:
#   0: No transparency
#   1: Theme is transparent
#   2: Obey config setting (default)
transparency        0
'''
            with open(out_theme, 'w', encoding='utf-8') as f:
                f.write(
                   msg.format(
                       colors['css'][1],
                       colors['css'][2],
                       colors['css'][3],
                       colors['css'][8],
                       colors['css'][9],
                       colors['css'][4],
                       colors['css'][5],
                       colors['css'][6],
                       colors['css'][7],
                       colors['css'][13],
                       colors['css'][14],
                       colors['css'][12],
                       colors['css'][11],
                       colors['css'][10]
                   )
                )
            return 0



class PyRadioThemeSelector(object):
    """ Theme Selector Window """
    TITLE = ' Available Themes '
    parent = None
    _win = None
    _width = _height = X = Y = 0
    selection = _selection = _start_pos = _items = 0

    _themes = []
    _title_ids = []

    ''' display the 2 internal 8 color themes '''
    _items = 2

    ''' window background '''
    _bg_pair = 0

    ''' page up, down
        when zero it will be _items / 2
    '''
    _page_jump = 0

    jumpnr = ''

    log = None
    _log_file = ''

    _max_title_width = 20
    _categories = 1

    _showed = False

    changed_from_config = False

    def __init__(self, parent, config, theme,
                 applied_theme_name,
                 config_theme_name,
                 title_color_pair, box_color_pair,
                 applied_color_pair, normal_color_pair,
                 cursor_color_pair, applied_cursor_color_pair,
                 is_watched, a_lock, log_file=''):
        self.parent = parent
        self._cnf = config
        self._theme = theme
        self._applied_theme_name = applied_theme_name
        self._config_theme_name = config_theme_name
        self._title_color_pair = title_color_pair
        self._box_color_pair = box_color_pair
        self._cursor_color_pair = cursor_color_pair
        self._applied_cursor_color_pair = applied_cursor_color_pair
        self._applied_color_pair = applied_color_pair
        self._normal_color_pair = normal_color_pair
        self._theme_is_watched = is_watched
        self._watch_theme_lock = a_lock
        self._watch_theme_lock.acquire()
        if log_file:
            self._log_file = log_file
            self.log = self._log

        self._themes = []
        # logger.error('\n\n========== Theme Window')
        # logger.error('theme = {}'.format(theme))
        # logger.error('is_watched = {}'.format(is_watched))
        # logger.error('applied_theme_name = {}'.format(applied_theme_name))
        # logger.error('config_theme_name = {}'.format(config_theme_name))
        # logger.error('========== Theme Window End\n\n')
        # for n in self._cnf.opts.keys():
        #     logger.error('{0}: {1}'.format(n, self._cnf.opts[n]))

    @property
    def theme_is_watched(self):
        return self._theme_is_watched

    def set_global_functions(self, global_functions):
        self._global_functions = {}
        if global_functions is not None:
            self._global_functions = dict(global_functions)
            if ord('t') in self._global_functions.keys():
                del self._global_functions[ord('t')]
            if ord('T') in self._global_functions.keys():
                del self._global_functions[ord('T')]

    def show(self, touch_selection=True):
        if self._cnf.locked:
            self._too_small = False
            self._get_metrics()
            return
        self._themes = [['dark', '']]
        self._themes.append(['dark_16_colors', ''])
        self._items += 1
        self._themes.append(['light', ''])
        self._themes.append(['light_16_colors', ''])
        self._items += 1
        self._themes.append(['black_on_white', ''])
        self._themes.append(['white_on_black', ''])
        self._items += 2
        ''' scan for package and user themes '''
        themes_to_add = self._scan_for_theme_files(self._cnf.stations_dir)
        if themes_to_add:
            self._themes.extend(themes_to_add)
            self._items = len(self._themes)
            self._get_titles_ids()
        self._first_theme_to_watch = 0
        for i, n in enumerate(self._themes):
            if n[0] in ('User Themes', 'Ext. Themes Projects'):
                self._first_theme_to_watch = i
                break
        if self._first_theme_to_watch == 0:
            self._first_theme_to_watch = len(self._themes)

        for a_theme in self._themes:
            if len(a_theme[0]) > self._max_title_width:
                self._max_title_width = len(a_theme[0])

        if self.log:
            self.log('max_title_width = {}\n'.format(self._max_title_width))
        self._get_config_and_applied_theme(touch_selection)
        self._get_metrics()

    def _scan_for_theme_files(self, cnf_path, user_themes_first=False):
        out_themes = []
        #self.root_path = path.join(path.dirname(__file__), 'stations.csv')
        theme_dirs = [path.join(path.dirname(__file__), 'themes'),
                      path.join(cnf_path, 'themes')]
        if user_themes_first:
            theme_dirs.reverse()
        for i, theme_dir in enumerate(theme_dirs):
            files = glob.glob(path.join(theme_dir, '*.pyradio-theme'))
            if files:
                tmp_themes = []
                for a_file in files:
                     theme_name = a_file.split(dir_sep)[-1].replace('.pyradio-theme', '')

                     ret, _ = self._cnf.is_project_theme(theme_name)
                     if ret is None:
                         if not self._cnf.is_default_file(theme_name):
                             tmp_themes.append([theme_name, a_file])
                if tmp_themes:
                    tmp_themes.sort()
                    tmp_themes.reverse()
                    if i == 0:
                        tmp_themes.append(['System Themes', '-'])
                    else:
                        tmp_themes.append(['User Themes', '-'])
                    tmp_themes.reverse()
                    out_themes.extend(tmp_themes)

        ''' add auto update themes, if not already there '''
        tmp_themes = []
        for n in self._cnf.auto_update_frameworks:
            if n.can_auto_update:
                for k in n.THEME:
                    tmp_themes.append([k, n.default_theme_path])
        if tmp_themes:
            tmp_themes.reverse()
            tmp_themes.append(['Ext. Themes Projects', '-'])
            tmp_themes.reverse()
            out_themes.extend(tmp_themes)
        return out_themes

    def _theme_name_in_themes(self, themes_list, theme_name):
        for i, x in enumerate(themes_list):
            if x[0] == theme_name:
                return i
        return -1

    def _get_titles_ids(self):
        self._title_ids = []
        for i, a_theme in enumerate(self._themes):
            if a_theme[1] == '-':
                self._title_ids.append(i)

    def theme_name(self, val):
        if val < len(self._themes):
            return self._themes[val][0]
        return ''

    def theme_path(self, val):
        if val < len(self._themes):
            return self._themes[val][1]
        return ''

    def _short_to_normal_theme_name(self, a_theme_name):
        if a_theme_name == 'bow':
            return 'black_on_white'
        elif a_theme_name == 'wob':
            return 'white_on_black'
        return a_theme_name

    def _get_config_and_applied_theme(self, touch_selection=True):
        self._config_theme_name = self._short_to_normal_theme_name(self._config_theme_name)
        self._applied_theme_name = self._short_to_normal_theme_name(self._applied_theme_name)
        if self.log:
            self.log('config theme name = "{0}", applied theme name = "{1}"\n'.format(self._config_theme_name, self._applied_theme_name))
        self._config_theme = -1
        self._applied_theme = -1
        found = 0
        for i, a_theme in enumerate(self._themes):
            if a_theme[0] == self._config_theme_name:
                self._config_theme = i
                found += 1
            if a_theme[0] == self._applied_theme_name:
                self._applied_theme = i
                found += 1
            if found == 2:
                break

        if self.log:
            self.log('config theme = {0}, applied theme = {1}\n'.format(self._config_theme, self._applied_theme))
        if touch_selection:
            if self._applied_theme == -1 or \
                    self._selection >= len(self._themes):
                self._selection = 0
            else:
                self._selection = self._applied_theme
        ''' make sure selection is valid
            for example when a user theme is selected
            and user themes are deleted and 'r' pressed
        '''
        if self._selection >= len(self._themes):
            self._selection = 0

    def _get_metrics(self):
        maxY, maxX = self.parent.getmaxyx()
        maxY -= 2
        maxX -= 2
        num_of_themes = len(self._themes)
        if num_of_themes > 4:
            if num_of_themes + 2 < maxY - 2:
                self._items = num_of_themes
                self.Y = int((maxY - self._items + 2) / 2)
            else:
                self._items = maxY - 4
                self.Y = 2
        else:
            self.Y = int((maxY - self._items + 2) / 2)
        if self.Y <= 2:
            self.Y = 3
        self._height = self._items + 2

        if self.log:
            self.log('max_title_width = {}\n'.format(self._max_title_width))
        self._width = self._max_title_width + 4

        """ check if too small """
        maxY, maxX = self.parent.getmaxyx()
        if self._height < 5 or self._width >= maxX - 2 or self._cnf.locked:
            txt = ' Window too small '
            self._win = curses.newwin(3, len(txt) + 2, int(maxY / 2), int((maxX - len(txt)) / 2))
            self._too_small = True
            self._win.bkgdset(' ', curses.color_pair(3))
            self._win.erase()
            self._win.box()
            self._win.addstr(1, 1, txt, curses.color_pair(4))
            self._win.refresh()
        else:
            self._too_small = False

            if self.log:
                self.log('width = {}\n'.format(self._width))
            self.X = int((maxX - self._width) / 2)

            self._page_jump = int(self._items / 2)
            self._win = None
            self._win = curses.newwin(self._height, self._width, self.Y, self.X)
            self._win.bkgdset(' ', curses.color_pair(self._box_color_pair))
            #self._win.erase()
            self._draw_box()
            self.refresh()


    def getmaxyx(self):
        return self._width, self._height

    @property
    def transparent(self):
        return self._cnf.use_transparency

    @transparent.setter
    def transparent(self, val):
        return

    @property
    def selection(self):
        return self._selection

    @selection.setter
    def selection(self, val):
        old_selection = self._selection
        if val < 0:
            self._selection = 0
            self._start_pos = 0
        elif val >= len(self._themes):
            self._selection = len(self._themes) - 1
            self._start_pos = len(self._themes) - self._items
        else:
            self._selection = val
            if self._selection >= len(self._themes):
                self._selection = len(self._themes) - 1
                self._start_pos = len(self._themes) - self._items

            if self._selection > old_selection:
                while self._selection >= self._start_pos + self._items:
                    self._start_pos += self._items
                if self._start_pos >= len(self._themes) - self._items:
                    self._start_pos = len(self._themes) - self._items
            else:
                while self._selection < self._start_pos:
                    self._start_pos -= self._items
                if self._start_pos < 0:
                    self._start_pos = 0
        self.refresh()

    def set_theme(self, a_theme):
        for i, ex_theme in enumerate(self._themes):
            if ex_theme == a_theme:
                if self._selection != i:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug('Setting theme: "{}"'.format(a_theme))
                    self.selection = i
                break

    def refresh(self):
        if self._too_small:
            return
        if self.log:
            self.log('======================\n')
            self.log('{}\n'.format(self._themes))
        self._draw_box()
        if not self._showed:
            number_of_items = len(self._themes)
            if self._items < number_of_items:
                if self._selection >= self._items:
                    if self._selection >= number_of_items - self._items:
                        self._start_pos = number_of_items - self._items
                    else:
                        self._start_pos = self._selection - int(self._items / 2)

        for i in range(0, self._height - 2):
            an_item = i + self._start_pos
            token = ' '
            if an_item in self._title_ids:
                col = curses.color_pair(self._title_color_pair)
            elif an_item == self.selection:
                ''' on selection, display cursor '''
                if self._selection == self._applied_theme:
                    col = curses.color_pair(self._applied_cursor_color_pair)
                else:
                    col = curses.color_pair(self._cursor_color_pair)
            else:
                if an_item == self._applied_theme:
                    col = curses.color_pair(self._applied_color_pair)
                else:
                    col = curses.color_pair(self._normal_color_pair)
            self._win.hline(i + 1, 1, ' ', self._max_title_width + 2, col)
            if an_item == self._config_theme:
                if self._theme_is_watched:
                    token = '+'
                else:
                    token = '*'
            if an_item in self._title_ids:
                self._win.move(i + 1, 0)
                try:
                    self._win.addstr('├', curses.color_pair(3))
                    self._win.move(i + 1, len(self._themes[an_item][0]) + 3)
                    self._win.addstr('─' * (self._width - 2 - len(self._themes[an_item][0]) - 2), curses.color_pair(3))
                    try:
                        self._win.addstr('┤', curses.color_pair(3))
                    except:
                        pass
                except:
                    self._win.addstr('├'.encode('utf-8'), curses.color_pair(3))
                    self._win.move(i + 1, len(self._themes[an_item][0]) + 2)
                    self._win.addstr('─'.encode('utf-8') * (self._width - 2 - len(self._themes[an_item][0]) - 2), curses.color_pair(3))
                    try:
                        self._win.addstr('┤'.encode('utf-8'), curses.color_pair(3))
                    except:
                        pass
                self._win.addstr(i+1, 1, token + self._themes[an_item][0], col)
            else:
                self._win.addstr(i+1, 1, token + self._themes[an_item][0], col)

        try:
            self._win.move(sel, self._width - 2)
        except:
            pass
        ''' display transparency indicator '''
        if self._cnf.use_transparency:
            self._win.addstr(self._height-1, self._width - 4, '[T]', curses.color_pair(self._box_color_pair))
        else:
            try:
                self._win.addstr(self._height-1, self._width - 4, '───', curses.color_pair(self._box_color_pair))
            except:
                self._win.addstr(self._height-1, self._width - 4, '───'.encode('utf-8'), curses.color_pair(self._box_color_pair))
        self._win.refresh()
        curses.doupdate()
        self._showed = True

    def _draw_box(self):
        self._win.box()
        self._win.move(0, 1)
        self._win.addstr(self.TITLE, curses.color_pair(self._title_color_pair))

    def _go_up(self):
        self._selection -= 1
        if self._selection in self._title_ids:
            self._selection -= 1
        if self._selection < 0:
            self.selection = len(self._themes) - 1
            self._start_pos = len(self._themes) - self._items
        if self._selection < self._start_pos:
            self._start_pos = self.selection
        self.refresh()

    def _go_down(self):
        self._selection += 1
        if self._selection in self._title_ids:
            self._selection += 1
        if self._selection == len(self._themes):
            self.selection = 0
            self._start_pos = 0
        while self._start_pos + self._items <= self._selection:
            self._start_pos += 1
        self.refresh()

    def _go_home(self):
        self._selection = 0
        self._start_pos = 0
        self.refresh()

    def _go_end(self):
        self.selection = len(self._themes)

    def _is_theme_read_only(self, theme_path):
        if theme_path:
            themes_path = path.join(path.dirname(__file__), 'themes')
            if themes_path == path.dirname(theme_path):
                return True
            else:
                if access(theme_path, R_OK):
                    return False
                else:
                    return True
        else:
            return True

    def keypress(self, char):
        """ returns theme_id, save_theme
            return_id
              0-..  : id in self._theme
              -1    : end or canel
              -2    : ask to create a new theme
              -3    : go no
              -4    : redisplay (scan for themes)
            save_them
              True  : theme is to be saved in config
              False : theme is not to be saved in config
        """
        if  self._too_small or self._cnf.locked:
            return -1, False
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return -3, False
        if char in (ord('e'), ):
            ''' edit theme '''
            pass
            # if self._themes[self._selection][1] == '' or \
            #         self._is_theme_read_only(self._themes[self._selection][1]):
            #     ''' display question to create theme instead '''
            #     return -2, False
            # else:
            #     pass
        elif char in (ord('a'), ):
            ''' new theme '''
            pass
        elif char in (ord('r'), ):
            return -4, False
        elif char in (curses.KEY_ENTER, ord('\n'),
                      ord('\r'), ord('l'),
                      curses.KEY_RIGHT):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            #if self.changed_from_config:
            #    self._config_theme = self._selection
            #    self._config_theme_name = self._themes[self._selection][0]
            self.refresh()
            return self._selection, False
        elif char in (ord(' '), ord('s'), ord('c'), ord('C')):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            if not self.changed_from_config:
                self._config_theme = self._selection
                self._config_theme_name = self._themes[self._selection][0]
            self._theme_is_watched = False
            if char == ord('c'):
                if self._selection > self._first_theme_to_watch and \
                        self._themes[self._selection][1]:
                    ''' we are at "User Themes" '''
                    is_project_theme, _ = self._cnf.is_project_theme(self._applied_theme_name)
                    if is_project_theme is not None:
                        if is_project_theme.can_auto_update:
                            self._theme_is_watched = True
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Theme set to auto update: "{}"'.format(self._applied_theme_name))
                        else:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug('Theme cannot auto update: "{}"'.format(self._applied_theme_name))
                    else:
                        self._theme_is_watched = True
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('Theme set to auto update: "{}"'.format(self._applied_theme_name))
            self.refresh()
            return self._selection, True
        elif char in (curses.KEY_UP, ord('k')):
            self.jumpnr = ''
            self._go_up()
        elif char in (curses.KEY_DOWN, ord('j')):
            self.jumpnr = ''
            self._go_down()
        elif char in (curses.KEY_HOME, ord('g')):
            self.jumpnr = ''
            self._go_home()
        elif char in (curses.KEY_END, ord('G')):
            if self.jumpnr == '':
                self._go_end()
            else:
                num = int(self.jumpnr) - 1
                if num in self._title_ids:
                    num += 1
                if num >= 0:
                    self.selection = num
                    self.jumpnr = ''
        elif char in (curses.KEY_NPAGE, ):
            self.jumpnr = ''
            sel = self._selection + self._page_jump
            if sel in self._title_ids:
                sel += 1
            if self._selection == len(self._themes) - 1:
                sel = 0
            elif sel >= len(self._themes):
                sel = len(self._themes) - 1
            self.selection = sel
        elif char in (curses.KEY_PPAGE, ):
            self.jumpnr = ''
            sel = self._selection - self._page_jump
            if sel in self._title_ids:
                sel -= 1
            if self._selection == 0:
                sel = len(self._themes) - 1
            elif sel < 0:
                sel = 0
            self.selection = sel
        elif char in map(ord,map(str,range(0, 10))):
            self.jumpnr += chr(char)
        elif char in (curses.KEY_EXIT, 27, ord('q'), ord('h'), curses.KEY_LEFT):
            self.jumpnr = ''
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                if not self.changed_from_config:
                    if self._applied_theme_name != self._config_theme_name:
                        if logger.isEnabledFor(logging.INFO):
                            logger.info('Restoring saved theme: {}'.format(self._config_theme_name))
                        ret, ret_theme_name = self._theme.readAndApplyTheme(self._config_theme_name)
                        self._applied_theme = self._config_theme
                        if ret == 0:
                            self._applied_theme_name = self._config_theme_name
                            self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
                            self._cnf.update_calculated_colors()
                        else:
                            self._applied_theme_name = ret_theme_name
                            self._cnf.theme_not_supported = True
                            self._cnf.theme_has_error = True if ret == -1 else False
                            ''' avoid showing extra notification when exiting theme selector '''
                            self._cnf.theme_not_supported_notification_shown = True
                self.selection = -1
                return -1, False
        return -3, False

    def _log(self, msg):
        with open(self._log_file, 'a', encoding='utf-8') as log_file:
            log_file.write(msg)


class PyRadioThemeEditor(object):

    theme_name = theme_path = ''
    editing = False
    _cnf = None
    maxX = maxY = 0

    def __init__(self, theme_name, theme_path, editing, config, maxX, maxY):
        self.theme_name = theme_name
        self.theme_path = theme_path
        self.editing = editing
        self._cnf = config
        self.maxY = maxX
        self.maxY = maxY

    def keypress(self, char):
        pass

