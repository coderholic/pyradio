# -*- coding: utf-8 -*-
import locale
import curses
import logging
import glob
from os import path, sep as dir_sep, access, R_OK, W_OK
from shutil import copyfile
from copy import deepcopy
from math import sqrt
import colorsys
from pathlib import Path
try:
    # Python ≥ 3.9
    from importlib.resources import files, as_file
    from importlib.resources.abc import Traversable
except ImportError:
    # Python 3.7 & 3.8 (backport)
    from importlib_resources import files, as_file
    from importlib_resources.abc import Traversable
from .common import rgb_to_curses_rgb, rgb_to_hex, hex_to_rgb
from .keyboard import kbkey, check_localized, remove_l10n_from_global_functions

logger = logging.getLogger(__name__)

locale.setlocale(locale.LC_ALL, "")

def compare_color_pairs(pair1, pair2, curses_colors):
    # Retrieve the foreground and background colors for each pair
    fg1, bg1 = curses.pair_content(pair1)
    fg2, bg2 = curses.pair_content(pair2)
    # logger.error('pair: {}, fg = {}, bg = {}'.format(pair1, fg1, bg1))
    # logger.error('pair: {}, fg = {}, bg = {}'.format(pair2, fg2, bg2))

    # Compare the foreground and background colors
    if (curses_colors[fg1] == curses_colors[fg2]) and \
            (curses_colors[bg1] == curses_colors[bg2]):
        return True  # The color pairs are identical
    return False  # The color pairs are different

def is_light_or_dark(rgb_color=None):
    if rgb_color is None:
        rgb_color = [0, 128, 255]
    [r,g,b]=rgb_color
    """
    https://stackoverflow.com/questions/22603510/is-this-possible-to-detect-a-colour-is-a-light-or-dark-colour
    """
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

    return True if hsp > 130 else False

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
        logger.debug(f'Luminance color factor = {amount}')
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f'color2: {colors[2]}')
    x = list(colorsys.rgb_to_hls(
        float(colors[2][0] / 255.0),
        float(colors[2][1] / 255.0),
        float(colors[2][2] / 255.0)
    ))
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f'hls: {x}')
    #logger.error('x = {}'.format(x))

    start_x1 = x[1]
    action = x[1] < .5

    # luma = 0.2126 * colors[2][0] + 0.7152 * colors[2][1] + 0.0722 * colors[2][2]
    # logger.error('luma = {}'.format(luma))

    action = not is_light_or_dark(colors[2])
    if logger.isEnabledFor(logging.DEBUG):
        logger.debug(f'color is dark = {action}')
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
                logger.debug(f'  luminance {count}: {x[1]}')

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
        logger.debug(f'color15: {y}')
    return tuple(y)

class PyRadioTheme():

    applied_theme_name = 'dark'

    def __init__(self, cnf):
        self._cnf = cnf
        # self._terminals_colors = tuple(curses.color_content(x) for x in range(0, 16))
        self._colors = {}
        self._active_colors = {}
        self._curses_colors = {}
        self._temp_colors = None
        self._read_colors = {}
        self._temp_colors = {}
        self.config_dir = ''
        self._theme_name = ''

    def __del__(self):
        self._colors = None
        self._active_colors = None
        self._read_colors = None
        self._temp_colors = None

    def calculate_transparency(self):
        transp = False
        theme_transp = self._active_colors['transparency']
        if logger.isEnabledFor(logging.DEBUG):
            if theme_transp == 0:
                logger.debug('Theme says: Do not use transparency (0)')
            elif theme_transp == 1:
                logger.debug('Theme says: Use transparency (1)')
            else:
                logger.debug('Theme says: I work both with and without transparency (2)')
            if self._cnf.use_transparency:
                logger.debug('Config says: Transparency is ON')
            else:
                logger.debug('Config says: Transparency is OFF')
            if self._cnf.force_transparency:
                logger.debug('Config says: Force transparency')
            else:
                logger.debug('Config says: Do not force transparency')

        if self._cnf.force_transparency:
            theme_transp = 2
        if logger.isEnabledFor(logging.DEBUG):
            if theme_transp == 2:
                logger.debug('Using config transparency setting!')
            else:
                logger.debug('Using theme transparency setting!')
        if theme_transp == 0:
            transp = False
        elif theme_transp == 1:
            transp = True
        else:
            transp = self._cnf.use_transparency
        if logger.isEnabledFor(logging.INFO):
            logger.info('*** Active transparency is {}'.format('ON' if transp else 'OFF'))
        return transp

    def _do_init_pairs(
            self,
            transparency=None,
            calculate_transparency_function=None
            ):
        self._cnf.time_color = 6
        if self._cnf.use_themes:
            if calculate_transparency_function is None:
                transp = self.calculate_transparency()
            else:
                transp = calculate_transparency_function()

            border_color = 16  if curses.COLORS > 16 else 1
            if not self._cnf.use_calculated_colors and \
                    self._colors['color_factor'] > 0:
                if logger.isEnabledFor(logging.INFO):
                    logger.debug('Theme has a color_factor, setting use_calculated_colors = True')
                self._cnf.use_calculated_colors = True
            # if not self._cnf.enable_calculated_colors and \
            #         self._cnf.use_calculated_colors:
            #     if logger.isEnabledFor(logging.INFO):
            #         logger.debug('Theme has a color_factor, setting use_calculated_colors = True')
            #     self._cnf.use_calculated_colors = False
            if self._cnf.use_calculated_colors:
                self._cnf.use_calculated_colors = self._cnf.enable_calculated_colors
                if not self._cnf.enable_calculated_colors:
                    if logger.isEnabledFor(logging.INFO):
                        logger.debug('Setting use_calculated_colors = False due to enable_calculated_colors')

            if self._cnf.use_calculated_colors or \
                   self._cnf.has_border_background:
                if transp:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'--> 1 transparency: ON (use_calculated_colors: {self._cnf.use_calculated_colors}, has_border_background: {self._cnf.has_border_background})')
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
                        logger.debug(f'--> 1 transparency: OFF (use_calculated_colors: {self._cnf.use_calculated_colors}, has_border_background: {self._cnf.has_border_background})')
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
                        logger.debug(f'--> 2 transparency: ON (use_calculated_colors: {self._cnf.use_calculated_colors}, has_border_background: {self._cnf.has_border_background})')
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
                        logger.debug(f'--> 2 transparency: OFF (use_calculated_colors: {self._cnf.use_calculated_colors}, has_border_background: {self._cnf.has_border_background})')
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
            for k, (fg, bg) in colors.items():
                curses.init_pair(k, fg, bg)
                # logger.error('pair {}: {}'.format(k, colors[k]))
            if compare_color_pairs(6, 7, self._curses_colors):
                if compare_color_pairs(9, 7, self._curses_colors):
                    self._cnf.time_color = 8
                else:
                    self._cnf.time_color = 9
            # else:
            #     self._cnf.time_color = 6

    def restoreActiveTheme(self, calculate_transparency_function=None):
        self._active_colors = deepcopy(self._read_colors)
        self._do_init_pairs(
                calculate_transparency_function=calculate_transparency_function
                )
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
        logger.error(f'{a_theme  = }')
        logger.error(f'{theme_path  = }')
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
        self._cnf.last_theme_s_transparency_setting = self._colors['transparency']
        self._read_colors = deepcopy(self._colors)
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
            logger.info(f'Applying fallback theme: "{self.applied_theme_name}" instead of: "{a_theme}"')
        self.open_theme(self.applied_theme_name)
        self._update_colors()
        self._cnf.last_theme_s_transparency_setting = self._colors['transparency']
        try:
            self.outerBodyWin.refresh()
            self.bodyWin.refresh()
            self.footerWin.refresh()
        except AttributeError:
            pass

    def _update_colors(self):
        self._curses_colors = {}
        if self._cnf.use_themes:
            for k in self._colors['data'].keys():
                curse_rgb = rgb_to_curses_rgb(self._colors['data'][k])
                self._curses_colors[int(k) + self._cnf.start_colors_at] = (
                    curse_rgb[0],
                    curse_rgb[1],
                    curse_rgb[2]
                )
                curses.init_color(
                    int(k) + self._cnf.start_colors_at,
                    curse_rgb[0],
                    curse_rgb[1],
                    curse_rgb[2],
                )
                # logger.error('color {}, rgb: {}, curses_rgb: {}'.format(
                #     k + self._cnf.start_colors_at,
                #     self._colors['data'][k],
                #     curse_rgb
                #     ))

    def recalculate_theme(self, inhibit_if_color15_exists=True):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Recalculating color15...')
            logger.debug(f"Stations background color: {self._colors['css'][2]}")
        self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
        # logger.error('\n\nself._colors before recalculate\n{}\n\n'.format(self._colors))
        if self._colors['color_factor'] == 0:
            fact = self._cnf.opts['calculated_color_factor'][1]
        else:
            fact = self._colors['color_factor']
        self._colors['data'][15] = calculate_fifteenth_color(
            self._colors['data'],
            fact,
            inhibit_if_color15_exists
            )
        self._colors['css'][15] = rgb_to_hex(tuple(self._colors['data'][15]))
        # logger.error('\n\nself._colors after recalculate\n{}\n\n'.format(self._colors))
        self._do_init_pairs()
        self._update_colors()

    def create_theme_from_theme(self, theme_name, out_theme_name):
        ''' Create a theme in theme's directory
            based on an internal or system theme
        '''
        out_file = path.join(self._cnf.themes_dir, out_theme_name + '.pyradio-theme')
        if path.exists(out_file):
            return False, f'Theme "{out_theme_name}" already exists...'
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
                return True, f'Theme created: "{out_theme_name}"'
            elif ret == -2:
                return False, f'Error writing theme file: "{out_theme_name}"'
        else:
            ''' copy theme file '''
            in_resource = files("pyradio.themes").joinpath(f"{theme_name}.pyradio-theme")
            try:
                with as_file(in_resource) as real_path:
                    copyfile(real_path, out_file)
                return True, f'Theme created: "{out_theme_name}"'
            except Exception:
                return False, f'Error creating file for theme: "{out_theme_name}"'

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

        if a_theme in {'dark', 'default'}:
            self._colors['transparency'] = 2
            self._colors['color_factor'] = 0
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
            self._colors['color_factor'] = 0
            self._colors['Name'] = 'dark_16_colors'
            self._colors['Path'] = ''
            self.applied_theme_name = 'dark_16_colors'
            self._colors['data'] = {1: (255, 255, 255), 2: (128, 128, 128), 3: (0, 255, 0), 8: (0, 0, 0), 9: (0, 255, 0), 4: (0, 0, 0), 5: (255, 0, 255), 6: (0, 0, 0), 7: (0, 255, 0), 12: (0, 255, 255), 11: (0, 0, 255), 10: (255, 255, 0), 13: (255, 255, 255), 14: (128, 128, 128), 15: (154, 154, 154)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (255, 255, 255)
            self._cnf.has_border_background = True

        elif a_theme == 'light':
            ''' info '''
            self._colors['Name'] = 'light'
            self._colors['transparency'] = 0
            self._colors['color_factor'] = 0
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
            self._colors['color_factor'] = 0
            self._colors['Path'] = ''
            self.applied_theme_name = 'light_16_colors'
            self._colors['data'] = {1: (128, 128, 128), 2: (255, 255, 255), 3: (255, 0, 0), 8: (255, 255, 255), 9: (0, 0, 255), 4: (255, 255, 255), 5: (255, 0, 255), 6: (255, 255, 255), 7: (0, 0, 255), 12: (0, 0, 255), 11: (0, 0, 255), 10: (255, 0, 255), 13: (255, 255,255), 14: (255, 0, 0), 15: (230, 230, 230)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (128, 128, 128)
            self._cnf.has_border_background = True

        elif a_theme in {'black_on_white', 'bow'}:
            ''' info '''
            self._colors['Name'] = 'black_on_white'
            self._colors['transparency'] = 0
            self._colors['color_factor'] = 0.2
            self._colors['Path'] = ''
            self.applied_theme_name = 'black_on_white'
            self._colors['data'] = {1: (128, 128, 128), 2: (255, 255, 255), 3: (0, 0, 0), 8: (255, 255, 255), 9: (138, 138, 138), 4: (255, 255, 255), 5: (128, 128, 128), 6: (0, 0, 0), 7: (128, 128, 128), 12: (0, 255, 255), 11: (138, 138, 138), 10: (138, 138, 138), 14: (0, 0, 0), 13: (255, 255, 255), 15: (229, 229, 229)}
            if curses.COLORS > 16:
                self._colors['data'][16] = (128, 128, 128)
            self._cnf.has_border_background = True

        elif a_theme in {'white_on_black', 'wob'}:
            ''' info '''
            self._colors['Name'] = 'white_on_black'
            self._colors['transparency'] = 2
            self._colors['color_factor'] = 0.2
            self._colors['Path'] = ''
            self.applied_theme_name = 'white_on_black'
            self._colors['data'] = {1: (158, 158, 158), 2: (38, 38, 38), 3: (238, 238, 238), 8: (28, 28, 28), 9: (218, 218, 218), 4: (38, 38, 38), 5: (158, 158, 158), 6: (38, 38, 38), 7: (218, 218, 218), 12: (218, 218, 218), 11: (138, 138, 138), 10: (158, 158, 158), 13: (0, 0, 0), 14: (169, 169, 169), 15: (52, 52, 52)}
            if not no_curses:
                if curses.COLORS > 16:
                    self._colors['data'][16] = (158, 158, 158)
            self._cnf.has_border_background = True

        else:
            ret, ret_ind = self._cnf.is_project_theme(a_theme)
            logger.error(f'{ret = }')
            logger.error(f'{ret_ind = }')
            if ret is not None:
                ''' this is a project theme! '''
                a_path = ret.default_theme_path
                ret.theme_id = ret_ind
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Project theme file name: {a_path}')
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
            # logger.error('colors\n{}'.format(self._colors))

        self.applied_theme_name = self._colors['Name']
        return ret

    def _get_theme_path(self, a_theme):
        """
        Locate a theme file by name, searching both user and package directories.

        1. First search the user themes directory (real filesystem path).
        2. Then search the package's internal themes directory (may be inside a zip/egg).
        3. If found inside the package resources, extract it to the cache directory and return the real path.

        Parameters
        ----------
        a_theme : str
            The name of the theme (without extension).

        Returns
        -------
        str
            Absolute path to the located theme file, or an empty string if not found.
        """
        # logger.error(f'{a_theme = }')
        try:
            # Python ≥ 3.9
            from importlib.resources import files, as_file
            from importlib.resources.abc import Traversable
        except ImportError:
            # Python 3.7 & 3.8 (backport)
            from importlib_resources import files, as_file
            from importlib_resources.abc import Traversable

        user_theme_dir = Path(self._cnf.stations_dir) / 'themes'
        package_theme_dir = files("pyradio") / "themes"
        cache_dir = Path(self._cnf.cache_dir) / 'themes'

        # List of theme directories: user path first, package resources second
        theme_dirs_to_search = [
            (user_theme_dir, False),    # (dir, is_package_resource)
            (package_theme_dir, True)
        ]
        # logger.error(f'{theme_dirs = }')


        # Search in user dir firts
        for theme_dir, is_package_resource in theme_dirs_to_search:
            # Case 1: It is Traversable (package source)
            if is_package_resource and isinstance(theme_dir, Traversable):
                for res in theme_dir.iterdir():
                    if res.name == f"{a_theme}.pyradio-theme":
                        # Copy to cache if a package source
                        cache_dir.mkdir(parents=True, exist_ok=True)
                        cached_theme_path = cache_dir / res.name
                        with as_file(res) as tmp_path:
                            copyfile(tmp_path, cached_theme_path)
                        return str(cached_theme_path)
            # Case 2: It is a normal system path
            elif isinstance(theme_dir, Path) and theme_dir.is_dir():
                theme_path = theme_dir / f"{a_theme}.pyradio-theme"
                if theme_path.is_file():
                    return str(theme_path)

        # If we got this far, nothing found
        return None


class PyRadioThemeReadWrite():

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
        self._theme_name = ''
        self._theme_path = ''
        self._temp_colors = None

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
                logger.error(f'read_theme(): file not found: {theme_path}')
            return 1, None
        if not access(theme_path, R_OK):
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'read_theme(): file not readable: {theme_path}')
            return 2, None

        try:
            with open(theme_path, 'r', encoding='utf-8') as thmfile:
                lines = [line.strip() for line in thmfile if line.strip() and not line.startswith('#')]

        except:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'read_theme(): read error on: {theme_path}')
            return 3, None

        names = {}
        for line in lines:
            if ',' in line:
                ''' old theme format '''
                # return 5, None
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f'read_theme(): old format theme: {theme_path}')
                return 4, None
            raw = line.split(' ')
            if raw[-1].startswith('#') and len(raw[-1]) != 7:
                ''' corrupt: not valid color '''
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f'read_theme(): {theme_path} - invalid color in line: ""{line}: - value: {raw[-1]}')
                return 4, None
            sp = [raw[-1]]
            raw.pop()
            try:
                if raw[-1]:
                    if raw[-1].startswith('#') and len(raw[-1]) != 7:
                        ''' corrupt: not valid color '''
                        if logger.isEnabledFor(logging.ERROR):
                            logger.error(f'read_theme(): {theme_path} - invalid color in line: ""{line}: - value: {raw[-1]}')
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
                    logger.error(f'read_theme(): file is corrupt: {theme_path}')
                return 4, None
            # logger.error('sp = {}'.format(sp))
            # logger.error('names = {}'.format(names))
            names[sp[0].strip()] = sp[1:]
            for _, v in names.items():
                for n in (0, 1):
                    try:
                        v[n] = v[n].strip()
                    except IndexError:
                        pass

        if curses.COLORS > 16 and \
                'Border' not in names:
            names['Border'] = [names['Stations'][0]]

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'theme names = {names}')
        self._temp_colors = { 'data': {}, 'css': {}, 'transparency': 2, 'color_factor': 0}
        for name in names:
            if name == 'transparency':
                self._temp_colors['transparency'] = 2
                try:
                    self._temp_colors['transparency'] = int(names[name][0])
                except (ValueError, TypeError):
                    self._temp_colors['transparency'] = 2
                if self._temp_colors['transparency'] not in range(0,3):
                    self._temp_colors['transparency'] = 2
                # logger.error('\n\nset transparency: {}\n\n'.format(self._temp_colors['transparency']))
            elif name == 'Color Factor':
                try:
                    num = float(names[name][0])
                    if 0.00 <= num <= 0.20:
                        self._temp_colors['color_factor'] = num
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'Theme Color Factor is off-limits: 0.0 <= {num} <= 0.20; reseting to 0.0')
                        self._temp_colors['color_factor'] = 0.0
                except ValueError:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Theme Color Factor is invalid: {names[name][0]}; reseting to 0.0')
                    self._temp_colors['color_factor'] = 0.0
            else:
                try:
                    self._temp_colors['css'][self._param_to_color_id[name][0]] = names[name][0]
                except KeyError:
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error(f'read_theme(): file is corrupt: {theme_path}')
                    return 4, None
                self._temp_colors['data'][self._param_to_color_id[name][0]] = hex_to_rgb(names[name][0])
                if len(self._param_to_color_id[name]) == 2:
                    self._temp_colors['css'][self._param_to_color_id[name][1]] = names[name][1]
                    self._temp_colors['data'][self._param_to_color_id[name][1]] = hex_to_rgb(names[name][1])

        if self._theme_is_incomplete():
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f'read_theme(): file is incomplete: {theme_path}')
            return 4, None
            return 5, None

        if len(names['Messages Border']) == 2:
            self._temp_colors['css'][15] = names['Messages Border'][-1]
            self._temp_colors['data'][15] = hex_to_rgb(self._temp_colors['css'][15])
            self._temp_colors['color_factor'] = 0
            self._cnf.has_border_background = True
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"read_theme(): color15 = {self._temp_colors['css'][15]}")
        else:
            self._cnf.has_border_background = False
            self._calculate_fifteenth_color()
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"read_theme(): calculated color15 = {self._temp_colors['css'][15]}")

        self._theme_name = theme_name
        self._theme_path = theme_path
        self._temp_colors['Name'] = theme_name
        self._temp_colors['Path'] = theme_path
        self._cnf.active_transparency = self._temp_colors['transparency']
        if logger.isEnabledFor(logging.INFO):
            logger.info(f'self._temp_colors\n{self._temp_colors}')
        return 0, self._temp_colors

    def _calculate_fifteenth_color(self):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"Stations background color: {self._temp_colors['css'][2]}")
        # logger.error('tmp_colors\n{}'.format(self._temp_colors))
        if self._temp_colors['color_factor'] == 0:
            fact = self._cnf.opts['calculated_color_factor'][1]
        else:
            fact = self._temp_colors['color_factor']
        self._temp_colors['data'][15] = calculate_fifteenth_color(
                self._temp_colors['data'],
                fact
                )
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
        if path.exists(out_theme):
            return -4
        if colors is None:
            if base_theme is not None:
                if not path.exists(base_theme):
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



class PyRadioThemeSelector():
    """ Theme Selector Window """
    TITLE = ' Available Themes '

    def __init__(self, parent, config, theme,
                 applied_theme_name,
                 config_theme_name,
                 title_color_pair, box_color_pair,
                 applied_color_pair, normal_color_pair,
                 cursor_color_pair, applied_cursor_color_pair,
                 is_watched, a_lock, log_file=''):
        self._win = None
        self._global_functions = None
        self._width = self._height = self.X = self.Y = 0
        self._selection = self._start_pos = self._items = 0
        self._start_pos = 0
        self._first_theme_to_watch = 0
        self._applied_theme = -1

        self._themes = []
        self._title_ids = []
        self._too_small = False
        self._config_theme = -1

        ''' display the 2 internal 8 color themes '''
        self._items = 2

        ''' window background '''
        self._bg_pair = 0

        ''' page up, down
            when zero it will be _items / 2
        '''
        self._page_jump = 0

        self.jumpnr = ''

        self.log = None
        self._log_file = ''

        self._max_title_width = 20
        self._categories = 1

        self._showed = False

        self.changed_from_config = False

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
        self._global_functions = remove_l10n_from_global_functions(
            global_functions,
            ('t', 'transp')
        )

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

        self._max_title_width = max(len(theme[0]) for theme in self._themes)

        if self.log:
            self.log(f'max_title_width = {self._max_title_width}\n')
        self._get_config_and_applied_theme(touch_selection)
        self._get_metrics()

    def _scan_for_theme_files(self, cnf_path, user_themes_first: bool = False):
        """
        Scan for available theme files.

        This function collects theme names and their corresponding paths from:
          1. User themes directory (real filesystem path).
          2. Package internal themes directory (may be zipped).

        If a theme comes from the package, its path is set to an empty string (''),
        signaling that it must be extracted/resolved later by _get_theme_path().

        Parameters
        ----------
        cnf_path : str
            Path to the user's configuration directory.
        user_themes_first : bool, optional
            If True, list user themes first.

        Returns
        -------
        list[list[str, str]]
            A list of [theme_name, theme_path] pairs. Some entries are headers
            of the form [header_text, '-'].
        """
        out_themes = []

        # User and package theme directories
        user_dir = path.join(cnf_path, 'themes')
        package_dir = files("pyradio").joinpath("themes")

        # Build directory list depending on priority
        theme_dirs = [(user_dir, 'User Themes'), (package_dir, 'System Themes')]
        if user_themes_first:
            theme_dirs.reverse()

        for theme_dir, header in theme_dirs:
            tmp_themes = []

            # Case 1: user directory (real path)
            if isinstance(theme_dir, str) and path.isdir(theme_dir):
                theme_files = glob.glob(path.join(theme_dir, '*.pyradio-theme'))
                for a_file in theme_files:
                    theme_name = path.basename(a_file).replace('.pyradio-theme', '')
                    ret, _ = self._cnf.is_project_theme(theme_name)
                    if ret is None and not self._cnf.is_default_file(theme_name):
                        tmp_themes.append([theme_name, a_file])

            # Case 2: package directory (Traversable, may be zipped)
            elif isinstance(theme_dir, Traversable):
                for res in theme_dir.iterdir():
                    if res.name.endswith('.pyradio-theme'):
                        theme_name = res.name[:-14]
                        ret, _ = self._cnf.is_project_theme(theme_name)
                        if ret is None and not self._cnf.is_default_file(theme_name):
                            # '' indicates package resource, to be resolved later
                            tmp_themes.append([theme_name, ''])

            if tmp_themes:
                tmp_themes.sort()
                tmp_themes.reverse()
                tmp_themes.append([header, '-'])
                tmp_themes.reverse()
                out_themes.extend(tmp_themes)

        # Add auto update themes, if not already there
        tmp_themes = []
        for n in self._cnf.auto_update_frameworks:
            if n.can_auto_update:
                for k in n.THEME:
                    tmp_themes.append([k, n.default_theme_path])
        logger.error(f'\n\nthemes\n{tmp_themes}\n\n')
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
            self.log(f'config theme name = "{self._config_theme_name}", applied theme name = "{self._applied_theme_name}\"\n')
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
            self.log(f'config theme = {self._config_theme}, applied theme = {self._applied_theme}\n')
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
            self.log(f'max_title_width = {self._max_title_width}\n')
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
                self.log(f'width = {self._width}\n')
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
                self._start_pos = min(self._start_pos, len(self._themes) - self._items)
            else:
                while self._selection < self._start_pos:
                    self._start_pos -= self._items
                self._start_pos = max(self._start_pos, 0)
        self.refresh()

    def set_theme(self, a_theme):
        for i, ex_theme in enumerate(self._themes):
            if ex_theme == a_theme:
                if self._selection != i:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Setting theme: "{a_theme}"')
                    self.selection = i
                break

    def refresh(self):
        if self._too_small:
            return
        if self.log:
            self.log('======================\n')
            self.log(f'{self._themes}\n')
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

        # Leftover from a bad copy/paste?
        # try:
        #     self._win.move(sel, self._width - 2)
        # except:
        #     pass
        ''' display transparency indicator '''
        if not self.changed_from_config:
            self._win.addstr(self._height-1, self._width - 4, '[T]', curses.color_pair(self._box_color_pair))
            try:
                self._win.addstr(self._height-1, self._width - 5, '────', curses.color_pair(self._box_color_pair))
            except:
                self._win.addstr(self._height-1, self._width - 5, '────'.encode('utf-8'), curses.color_pair(self._box_color_pair))
            if self._cnf.use_transparency and self._cnf.force_transparency:
                self._win.addstr(self._height-1, self._width - 5, '[TF]', curses.color_pair(self._box_color_pair))
            elif self._cnf.use_transparency:
                self._win.addstr(self._height-1, self._width - 4, '[T]', curses.color_pair(self._box_color_pair))
            elif self._cnf.force_transparency:
                self._win.addstr(self._height-1, self._width - 4, '[F]', curses.color_pair(self._box_color_pair))
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
        """
        Determine if a theme is read-only.

        Read-only if:
          1. No real path ('' or inside zip/wheel)
          2. Located in cache_dir (even if writable)
          3. Located in system dir and not writable
        """
        # Case 1: zip/wheel resource (no real file)
        if not theme_path:
            return True

        # Normalize
        theme_dir = path.dirname(theme_path)

        # Case 2: cache_dir copy (always read-only)
        if theme_dir.startswith(self._cnf.cache_dir):
            return True

        # Case 3: system dir (package installed themes)
        # it is ok, zip/wheel taken care of
        system_themes_path = path.join(path.dirname(__file__), 'themes')
        if theme_dir == system_themes_path:
            return True

        # Otherwise, check real FS permissions (user themes)
        return not access(theme_path, R_OK | W_OK)

    def keypress(self, char):
        """ PyRadioThemeSelector keypress
            returns theme_id, save_theme
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
        l_char = None
        if  self._too_small or self._cnf.locked:
            return -1, False
        if char in self._global_functions or \
                (l_char := check_localized(char, self._global_functions.keys(), True)) is not None:
            if l_char is None:
                l_char = char
            self._global_functions[l_char]()
            return -3, False
        if char in (kbkey['edit'], ) or \
                check_localized(char, (kbkey['edit'], )):
            ''' edit theme '''
            pass
            # if self._themes[self._selection][1] == '' or \
            #         self._is_theme_read_only(self._themes[self._selection][1]):
            #     ''' display question to create theme instead '''
            #     return -2, False
            # else:
            #     pass
        elif char in (kbkey['add'], ) or \
                check_localized(char, (kbkey['add'], )):
            ''' new theme '''
            pass
        elif char == kbkey['reload'] or \
                check_localized(char, (kbkey['reload'], )):
            return -4, False
        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r'),
                      kbkey['l'], curses.KEY_RIGHT) or \
                check_localized(char, (kbkey['l'], )):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            #if self.changed_from_config:
            #    self._config_theme = self._selection
            #    self._config_theme_name = self._themes[self._selection][0]
            self.refresh()
            return self._selection, False
        elif char in (kbkey['pause'], kbkey['s'], kbkey['watch_theme']) or \
                check_localized(char, (kbkey['pause'], kbkey['s'])):
            self._applied_theme = self._selection
            self._applied_theme_name = self._themes[self._selection][0]
            if not self.changed_from_config:
                self._config_theme = self._selection
                self._config_theme_name = self._themes[self._selection][0]
            self._theme_is_watched = False
            if char == kbkey['watch_theme'] or \
                check_localized(char, (kbkey['watch_theme'], )):
                if self._selection > self._first_theme_to_watch and \
                        self._themes[self._selection][1]:
                    ''' we are at "User Themes" '''
                    is_project_theme, _ = self._cnf.is_project_theme(self._applied_theme_name)
                    if is_project_theme is not None:
                        if is_project_theme.can_auto_update:
                            self._theme_is_watched = True
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f'Theme set to auto update: "{self._applied_theme_name}"')
                        else:
                            if logger.isEnabledFor(logging.DEBUG):
                                logger.debug(f'Theme cannot auto update: "{self._applied_theme_name}"')
                    else:
                        self._theme_is_watched = True
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'Theme set to auto update: "{self._applied_theme_name}"')
            self.refresh()
            return self._selection, True
        elif char in (curses.KEY_UP, kbkey['k']) or \
                check_localized(char, (kbkey['k'], )):
            self.jumpnr = ''
            self._go_up()
        elif char in (curses.KEY_DOWN, kbkey['j']) or \
                check_localized(char, (kbkey['j'], )):
            self.jumpnr = ''
            self._go_down()
        elif char in (curses.KEY_HOME, kbkey['g']) or \
                check_localized(char, (kbkey['g'], )):
            self.jumpnr = ''
            self._go_home()
        elif char in (curses.KEY_END, kbkey['G']) or \
                check_localized(char, (kbkey['G'], )):
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
        elif char in (curses.KEY_EXIT, 27, kbkey['q'], kbkey['h'], curses.KEY_LEFT) or \
                check_localized(char, (kbkey['q'], kbkey['h'])):
            self.jumpnr = ''
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                """ ESCAPE """
                if not self.changed_from_config:
                    if self._applied_theme_name != self._config_theme_name:
                        if logger.isEnabledFor(logging.INFO):
                            logger.info(f'Restoring saved theme: {self._config_theme_name}')
                        ret, ret_theme_name = self._theme.readAndApplyTheme(self._config_theme_name)
                        self._applied_theme = self._config_theme
                        if ret == 0:
                            self._applied_theme_name = self._config_theme_name
                            self._cnf.use_calculated_colors = self._cnf.opts['calculated_color_factor'][1] == '0'
                            self._cnf.update_calculated_colors()
                        else:
                            self._applied_theme_name = ret_theme_name
                            self._cnf.theme_not_supported = True
                            self._cnf.theme_has_error = ret == -1
                            ''' avoid showing extra notification when exiting theme selector '''
                            self._cnf.theme_not_supported_notification_shown = True
                self.selection = -1
                return -1, False
        return -3, False

    def _log(self, msg):
        with open(self._log_file, 'a', encoding='utf-8') as log_file:
            log_file.write(msg)


class PyRadioThemeEditor():

    def __init__(self, *, theme_name, theme_path, editing, config, maxX, maxY):
        self.theme_name = theme_name
        self.theme_path = theme_path
        self.editing = editing
        self._cnf = config
        self.maxY = maxX
        self.maxY = maxY

    def keypress(self, char):
        ''' PyRadioThemeEditor keypress '''
        l_char = None

