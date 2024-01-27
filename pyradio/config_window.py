# -*- coding: utf-8 -*-
import curses
from copy import deepcopy
from textwrap import wrap
import glob
import csv
from os import path, sep, remove
from sys import platform, version_info

from .common import *
from .window_stack import Window_Stack_Constants
from .cjkwrap import cjklen
from .encodings import *
from .themes import *
from .server import IPsWithNumbers
from .simple_curses_widgets import SimpleCursesLineEdit, SimpleCursesHorizontalPushButtons, SimpleCursesMenu
import logging
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

def set_global_functions(global_functions):
    ret = {}
    if global_functions is not None:
        ret = dict(global_functions)
        if ord('t') in ret.keys():
            del ret[ord('t')]
    return ret

class PyRadioConfigWindow(object):
    n_u = Window_Stack_Constants

    parent = None
    _win = None

    _title = 'PyRadio Configuration'

    selection = __selection = 1

    ''' Keep a copy of saved values for theme and transparency
        Work-around for 'T' auto save (trasnsparency), and
        's'/Space them saving
    '''
    _old_use_transparency = False
    _old_theme = ''

    _headers = []

    _num_of_help_lines = 0
    _help_text = []
    _help_text.append(None)
    _help_text.append(['Specify the player to use with PyRadio, or the player detection order.', '|',
    'This is the eqivelant to the -u , --use-player command line option.', '|',
    'Example:', '  player = vlc', 'or', '  player = vlc,mpv, mplayer', '|',
    'Default value: mpv,mplayer,vlc'])
    _help_text.append(['If this option is enabled, the last local playlist loaded before terminating, will be automatically opened the next time PyRadio is executed. Furthermore, playback will resume, if it was on when PyRadio exited. Otherwise, station selection will be restored.', '|', 'This option will take precedence over the "Def. playlist" configuration option and the "-s" command line option.', '|', 'It can also be toggled on the fly by perssing \\l while on Main mode.', '|', 'Default value: False'])
    _help_text.append(['This is the playlist to open at start up, if none is specified and "Open last playlist" is not set.', '|',
    'This is the equivalent to the -s, --stations command line option.', '|',
    'Default value: stations'])
    _help_text.append(['The station number within the default playlist to play.', '|',
    'This is the equivalent to the -p, --play command line option.', '|',
    'Value is 1..number of stations, "False" means no auto play, "Random" means play a random station.', '|', 'Default value: False'])
    _help_text.append(['This is the encoding used by default when reading data provided by a station such as song title, etc. If reading said data ends up in an error, "utf-8" will be used instead.', '|',
    'If changed, playback must be restarted so that changes take effect.',
    '|', 'Default value: utf-8'])
    _help_text.append(['If this options is enabled, the mouse can be used to scroll the playlist, start, stop and mute the player, adjust its volume etc.', '|', 'Mouse support is highly terminal dependent, that\'s why it is disabled by default.', '|', 'Default value: False'])
    _help_text.append(['If this options is enabled, a Desktop Notification will be displayed using the notification daemon / service.', '|', 'If enabled but no notification is displayed, please refer to', 'https://github.com/coderholic/pyradio/desktop-notification.md', '|', 'Valid values are:', '   -1: disabled ', '    0: enabled (no repetition) ', '    x: repeat every x seconds ', '|', 'Default value: -1'])
    _help_text.append(['Notice: Not applicable on Windows!', '|',  'Online Radio Directory Services (like Radio Browser) will usually provide an icon for the stations they advertise.', '|', 'PyRadio can use this icon (provided that one exists and is of JPG or PNG format) while displaying Desktop Notifications.', '|', 'Setting this option to True, will enable the behavior above.', '|', 'If this option is False, the default icon will be used.', '|', 'Default value: True'])
    _help_text.append([ 'This is the folder where recorded files will be saved', '|', 'Default value: "recordings" in config dir' ])
    _help_text.append(None)
    _help_text.append(['PyRadio will wait for this number of seconds to get a station/server message indicating that playback has actually started.', '|',
    'If this does not happen within this number of seconds after the connection is initiated, PyRadio will consider the station unreachable, and display the "Failed to connect to: station" message.', '|', 'Press "h"/Left or "l"/Right to change value.',
    '|', 'Valid values: 5 - 60, 0 disables check', 'Default value: 10'])
    _help_text.append(['Most radio stations use plain old http protocol to broadcast, but some of them use https.', '|', 'If this parameter is enabled, all connections will use http; results depend on the combination of station/player.', '|', 'This value is read at program startup, use "z" to change its effect while mid-session.',
    '|', 'Default value: False'])
    _help_text.append(None)
    _help_text.append(['The theme to be used by default.', '|',
    'This is the equivalent to the -t , --theme command line option.', '|',
    'If a theme uses more colors than those supported by the terminal in use, the "dark" theme will be used instead (but the "light" theme will be used, if the "light_16colors" theme was requested but not supported).',
    '|', 'Default value = dark'])
    _help_text.append(['This option will work when a theme\'s transparency value is set to 2 (Obey config setting), the default. Otherwise, it\'s up to the theme to handle transparency.', '|', 'If False, theme colors will be used.', '|',
    "If True and a compositor is running, the stations' window background will be transparent.", '|', "If True and a compositor is not running, the terminal's background color will be used.", '|', 'Default value: False'])
    _help_text.append(['This option, when enabled, will make all themes behave as if their transparency setting was set to 2 (Obey config setting), in which case the windows\'s transparency will depend entirely on the value of the "Use transparency" setting (the one above this one).', '|', 'Default value: False'])
    _help_text.append(['Pyradio can calculate and use an alternative color for secondary windows.', '|', 'This option will determine if this color will be used (value > 0) or not (value = 0), provided that the theme used does not already provide it.', '|', 'The value of this option is actually the factor to darken or lighten the main (stations) background color.', '|', 'You can get more info on this at https://github.com/coderholic/pyradio#secondary-windows-background', '|', 'Valid Values: 0-0.2', 'Default value: 0'])
    _help_text.append(None)
    _help_text.append(['Specify whether you will be asked to confirm every station deletion action.',
    '|', 'Default value: True'])
    _help_text.append(['Specify whether you will be asked to confirm playlist reloading, when the playlist has not been modified within PyRadio.',
    '|', 'Default value: True'])
    _help_text.append(['Specify whether you will be asked to save a modified playlist whenever it needs saving.', '|', 'Default value: False'])
    _help_text.append(None)
    _help_text.append(['This is the IP for the Remote Control Server.', '|', 'Available options:', '- localhost : PyRadio will be accessible from within the current system only.', '- lan : PyRadio will be accessible from any computer in the local network.', '- IP : In case the system has more than one interfaces.', '|', 'Use "Space", "Enter", "l/Right" to change the value.','|', 'Default value: localhost'])
    _help_text.append(
        ['This is the port used by the Remote Control Server (the port the server is listening to).', '|', 'Please make sure that a "free" port is specified here, to avoid any conflicts with existing services and daemons.', '|', 'If an invalid port number is inserted, the cursor will not move to another field.', '|', 'Valid values: 1025-65535', 'Default value: 9998'])
    _help_text.append(['If set to True, the Server wiil be automatically started when PyRadio starts.', r'If set to False, one can start the Server using the "\s" command from the Main program window.', '|', 'Default value: False'])
    _help_text.append(None)
    _help_text.append(['This options will open the configuration window for the RadioBrowser Online Stations Directory.', '|', "In order to use RadioBrowser, python's requests module must be installed."])

    _config_options = None

    def __init__(self, parent, config,
                 toggle_transparency_function,
                 update_transparency_function,
                 show_theme_selector_function,
                 save_parameters_function,
                 reset_parameters_function,
                 show_port_number_invalid,
                 parameters_editing_error=None,
                 global_functions=None
        ):
        self.parameters_editing_error = parameters_editing_error
        self._local_functions = {
            ord('j'): self._go_down,
            curses.KEY_DOWN: self._go_down,
            ord('k'): self._go_up,
            curses.KEY_UP: self._go_up,
            curses.KEY_PPAGE: self._go_pgup,
            curses.KEY_NPAGE: self._go_pgdown,
            ord('g'): self._go_home,
            curses.KEY_HOME: self._go_home,
            ord('G'): self._go_end,
            curses.KEY_END: self._go_end,
            ord('d'): self._go_default,
            ord('r'): self._go_saved,
            curses.KEY_EXIT: self._go_exit,
            27: self._go_exit,
            ord('q'): self._go_exit,
            ord('h'): self._go_exit,
            curses.KEY_LEFT: self._go_exit,
            ord('s'): self._go_save,
        }

        self._global_functions = set_global_functions(global_functions)
        self._port_line_editor = SimpleCursesLineEdit(
            parent=self._win,
            width=6,
            begin_y=6,
            begin_x=16,
            boxed=False,
            has_history=False,
            caption='',
            box_color=curses.color_pair(6),
            edit_color=curses.color_pair(6),
            cursor_color=curses.color_pair(8),
            unfocused_color=curses.color_pair(4),
            key_up_function_handler=self._go_up,
            key_down_function_handler=self._go_down,
            key_pgup_function_handler=self._go_pgup,
            key_pgdown_function_handler=self._go_pgdown,
        )
        self._port_line_editor.visible = False
        self._port_line_editor.bracket = False
        self._port_line_editor._use_paste_mode = False
        self._port_line_editor.set_global_functions(self._global_functions)
        self._port_line_editor._paste_mode = False
        self._port_line_editor.chars_to_accept = [str(x) for x in range(0, 10)]
        self._port_line_editor.set_local_functions(self._fix_local_functions_for_editor())

        self._start = 0
        self.parent = parent
        self._cnf = config
        self._show_port_number_invalid = show_port_number_invalid
        self._toggle_transparency_function = toggle_transparency_function
        self._update_transparency_function = update_transparency_function
        self._show_theme_selector_function = show_theme_selector_function
        self._save_parameters_function = save_parameters_function
        self._reset_parameters_function = reset_parameters_function
        self._saved_config_options = deepcopy(config.opts)
        self._config_options = deepcopy(config.opts)
        self._old_theme = self._config_options['theme'][1]
        if logger.isEnabledFor(logging.INFO):
            if self._saved_config_options == self._config_options:
                logger.info('Saved options loaded')
            else:
                logger.info('Altered options loaded')
        self.number_of_items = len(self._config_options) - 3
        for i, n in enumerate(list(self._config_options.values())):
            if n[1] == '':
                self._headers.append(i)
        # logger.error('{}'.format(self._config_options))
        # logger.error('self._headers = {}'.format(self._headers))
        self._port_line_editor.string = self._config_options['remote_control_server_port'][1]
        self.init_config_win()
        self.refresh_config_win()
        self._old_use_transparency = self._config_options['use_transparency'][1]

        self._cnf.get_player_params_from_backup()

        ''' Config window parameters check '''
        # logger.error('DE \n\ncheck params\n{0}\n{1}'.format(self._cnf.saved_params, self._cnf.params))
        for a_key in self._cnf.saved_params.keys():
            if self._cnf.saved_params[a_key] != self._cnf.params[a_key]:
                self._cnf.dirty_config = True
        self.nip = IPsWithNumbers(
                default_ip=self._config_options['remote_control_server_ip'][1]
        )

    def __del__(self):
        self._toggle_transparency_function = None

    def calculate_transparency(self):
        transp = False
        theme_transp = self._cnf.last_theme_s_transparency_setting
        if logger.isEnabledFor(logging.DEBUG):
            if theme_transp == 0:
                logger.debug('Theme says: Do not use transparency (0)')
            elif theme_transp == 1:
                logger.debug('Theme says: Use transparency (1)')
            else:
                logger.debug('Theme says: I work both with and without transparency (2)')
            if self._config_options['use_transparency'][1]:
                logger.debug('Config says: Transparency is ON')
            else:
                logger.debug('Config says: Transparency is OFF')
            if self._config_options['force_transparency'][1]:
                logger.debug('Config says: Force transparency')
            else:
                logger.debug('Config says: Do not force transparency')

        if self._config_options['force_transparency'][1]:
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
            transp = self._config_options['use_transparency'][1]
        if logger.isEnabledFor(logging.INFO):
            logger.info('*** Active transparency is {}'.format('ON' if transp else 'OFF'))
        return transp

    def _fix_local_functions_for_editor(self):
        chk = (
            curses.KEY_HOME,
            curses.KEY_END,
            curses.KEY_LEFT,
            curses.KEY_RIGHT,
        )
        local_f = {}
        for n in self._local_functions.keys():
            local_f[n] = self._local_functions[n]
        for n in chk:
            if n in local_f.keys():
                local_f.pop(n)
        return local_f

    @property
    def parent(self):
        return self.__parent

    @parent.setter
    def parent(self, val):
        self.__parent = val
        self.init_config_win()

    @property
    def selection(self):
        return self.__selection

    @selection.setter
    def selection(self, val):
        if val < 1:
            val = len(self._headers) - 1
        elif val >= self.number_of_items:
            val = 1
        if val in self._headers:
            self.__selection = val + 1
        else:
            self.__selection = val
        #self.refresh_config_win()

    def init_config_win(self):
        self._win = None
        self.maxY, self.maxX = self.__parent.getmaxyx()
        # logger.error('\n\nmaxY = {}\n\n'.format(self.maxY))
        self._second_column = int(self.maxX / 2)
        self._win = curses.newwin(self.maxY, self.maxX, 1, 0)
        self._populate_help_lines()

        if self._config_options:
            self._max_start =  len(self._config_options) - 1 - self.maxY
            # logger.error('max_start = {}'.format(self._max_start))
            if self._max_start < 0:
                self._start = 0
            else:
                self._put_cursor(0)

    def refresh_config_win(self):
        self._win.bkgdset(' ', curses.color_pair(12))
        self._win.erase()
        self._win.box()
        self._print_title()
        #self._win.addstr(0,
        #    int((self.maxX - len(self._title)) / 2),
        #    self._title,
        #    curses.color_pair(4))
        min_lines = len(self._config_options)
        if min_lines < self._max_number_of_help_lines:
            min_lines = self._max_number_of_help_lines
        # if self.maxX < 80 or self.maxY < min_lines + 3:
        if self.maxX < 80 or self.maxY < 22:
            self.too_small = True
        else:
            self.too_small = False
        if self.too_small:
            self._port_line_editor.visible = False
            # self._port_line_editor.visible = False
            msg = 'Window too small to display content!'
            if self.maxX < len(msg) + 2:
                msg = 'Window too small!'
            try:
                self._win.addstr(
                    int(self.maxY / 2),
                    int((self.maxX - len(msg)) / 2),
                    msg, curses.color_pair(5))
            except:
                pass
        else:
            self._win.addstr(1, self._second_column, 'Option Help', curses.color_pair(4))
            ''' print distro name '''
            ''' TODO: make sure it does not overwrite an option name '''
        self.refresh_selection()

    def _print_title(self):
        if self._config_options == self._saved_config_options and \
            self._old_theme == self._saved_config_options['theme'][1] and \
                self._old_use_transparency == self._saved_config_options['use_transparency'][1] and not self._cnf.params_changed:
            dirty_title = '─ '
            self._cnf.dirty_config = False
            col = 12
        else:
            dirty_title = ' *'
            # logger.error('config_options = {}'.format(self._config_options))
            # logger.error('saved_config_options = {}'.format(self._saved_config_options))
            # logger.error('old_theme = "{0}", theme = "{1}"'.format(self._old_theme, self._saved_config_options['theme'][1]))
            # logger.error('old transparency = {0}, transparency = {1}'.format(self._old_use_transparency, self._saved_config_options['use_transparency'][1]))
            # logger.error('params_changed = {}'.format(self._cnf.params_changed))
            # logger.error('>>>')
            self._cnf.dirty_config = True
            col = 12
        X = int((self.maxX - len(self._title) - 1) / 2)
        try:
            self._win.addstr(0, X, dirty_title, curses.color_pair(col))
        except:
            self._win.addstr(0, X, dirty_title.encode('utf-8'), curses.color_pair(col))
        self._win.addstr(self._title + ' ', curses.color_pair(4))

        if self._cnf.distro != 'None':
            try:
                X = int((self.maxX - 20 - len(self._cnf.distro) - 1) / 2)
                self._win.addstr(self.maxY - 1, X, ' Package provided by ', curses.color_pair(5))
                # self._win.addstr(min_lines + 2, 3 + int(abs(8 - len(self._cnf.distro)) / 2), self._cnf.distro, curses.color_pair(4))
                self._win.addstr(self._cnf.distro + ' ', curses.color_pair(4))
            except:
                pass

    def refresh_selection(self):
        self._print_title()
        if not self.too_small:
            # logger.error('\n\n================\nself._start = {}'.format(self._start))
            # logger.error(self._config_options)
            it_list = list(self._config_options.values())
            for i in range(len(it_list)-1, 0, -1):
                if it_list[i][0] == '':
                    it_list.pop()
            # logger.error(it_list)
            # if self.__selection < self.maxY -2:
            #     self._start = 0
            # else:
            #     self._start += 1
            # logger.error('self._start = {}'.format(self._start))
            # for i in range(self._start, len(it_list)):
            self._port_line_editor.visible = False
            for i in range(self._start, self._start + self.maxY - 2):
                try:
                    it = it_list[i]
                except IndexError:
                    break
                # logger.error('selection = {0}, i = {1}, max = {2}'.format(self.selection, i, self.maxY))
                if i == self.__selection:
                    col = hcol = curses.color_pair(6)
                    self._print_options_help()
                else:
                    col = curses.color_pair(5)
                    hcol = curses.color_pair(4)
                hline_width = self._second_column - 2
                try:
                    self._win.hline(i+1-self._start, 1, ' ', hline_width, col)
                except:
                    logger.error('===== ERROR: {}'.format(i+1))
                if it[0] == 'Server Port: ':
                    logger.error('\n\ni = {0}, y = {1}, it[0] = "{2}"'.format(i, i+1-self._start, it[0]))
                if i in self._headers:
                    self._win.addstr(i+1-self._start, 1, it[0], curses.color_pair(4))
                else:
                    on_editor = i+1-self._start if it[0] == 'Server Port: ' else -1
                    self._win.addstr(i+1-self._start, 1, '  ' + it[0], col)
                    if on_editor > -1:
                        ''' move port editor to line '''
                        self._port_line_editor.visible = True
                        self._port_line_editor.move(self._win, on_editor + 1, 16, update=False)
                        logger.error('{0}: moving to: {1},{2}'.format(on_editor+1, on_editor, 16))
                        if i == self.__selection:
                            self._port_line_editor.focused = True
                            logger.error('line editor focused = True')
                        else:
                            self._port_line_editor.focused = False
                            logger.error('line editor focused = False')
                        logger.error('line editor string = "{}"'.format(self._port_line_editor.string))
                    elif isinstance(it[1], bool):
                        self._win.addstr('{}'.format(it[1]), hcol)
                    else:
                        if it[1] is None:
                            ''' random station '''
                            self._win.addstr('{}'.format('Random'), hcol)
                        else:
                            if it[1] != '-':
                                self._win.addstr('{}'.format(it[1][:self._second_column - len(it[0]) - 6]), hcol)
        self._win.refresh()
        if self._port_line_editor.visible:
            self._port_line_editor.keep_restore_data()
            self._port_line_editor.show(self._win)

    def _get_col_line(self, ind):
        if ind < self._headers:
            self._column = 3
            self._line = ind + 2
        else:
            self._column = self._second_column + 2
            self._line = ind - self._headers + 2

    def _put_cursor(self, jump):
        if self.__selection == self.number_of_items - 1 and jump > 0:
            self.__selection = 1
            self._start = 0
            return
        visible_items = self.maxY - 3
        last_item = self._start + visible_items
        old_selection = self.__selection
        old_start = self._start
        self.__selection += jump
        if jump >= 0:
            if self.__selection in self._headers:
                self.__selection += 1
            if self.__selection >= self.number_of_items:
                self.__selection = self.number_of_items -1
                if self.number_of_items > visible_items:
                    self._start = self.number_of_items - visible_items - 1
            else:
                if self.__selection <= 1:
                    self._start = 0
                elif self.__selection > last_item:
                    self._start += 1
                    if self._start + visible_items in self._headers:
                        self._start += 1
                    if self.__selection - self._start > visible_items:
                        self._start = self.__selection - self._start - visible_items + 1
        else:
            if self.__selection in self._headers:
                self.__selection -= 1
            if self.__selection < 1:
                self.__selection = self.number_of_items - 1
                if self.number_of_items > visible_items:
                    self._start = self.__selection - visible_items
            else:
                if self.__selection < self._start:
                    self._start = self.__selection

    def _populate_help_lines(self):
        self._help_lines = []
        self._max_number_of_help_lines = 0
        for z in self._help_text:
            if z is None:
                self._help_lines.append(None)
            else:
                all_lines = []
                for k in z:
                    lines = []
                    lines = wrap(k, self.maxX - self._second_column - 2)
                    all_lines.extend(lines)
                self._help_lines.append(all_lines)
                if len(all_lines) > self._max_number_of_help_lines:
                    self._max_number_of_help_lines = len(all_lines)

    def _print_options_help(self):
        for i, x in enumerate(self._help_lines[self.selection]):
            if i + 2 == self.maxY:
                break
            self._win.addstr(i+2, self._second_column, ' ' * (self._second_column - 1), curses.color_pair(5))
            self._win.addstr(i+2, self._second_column, x.replace('|',''), curses.color_pair(5))
        if len(self._help_lines[self.selection]) < self._num_of_help_lines:
            for i in range(len(self._help_lines[self.selection]), self._num_of_help_lines):
                try:
                    self._win.addstr(i+2, self._second_column, ' ' * (self._second_column - 1), curses.color_pair(5))
                except:
                    pass
        self._num_of_help_lines = len(self._help_lines[self.selection])
        '''
        Uncomment if trouble with help lines
        '''
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('self._num_of_help_lines = {}'.format(self._num_of_help_lines))

    def _load_default_values(self):
        self._config_options['general_title'][1] = ''
        self._config_options['player'][1] = 'mpv,mplayer,vlc'
        self._config_options['open_last_playlist'][1] = 'False'
        self._config_options['default_playlist'][1] = 'stations'
        self._config_options['default_station'][1] = 'False'
        self._config_options['default_encoding'][1] = 'utf-8'
        self._config_options['enable_mouse'][1] = 'False'
        self._config_options['enable_notifications'][1] = '-1'
        self._config_options['use_station_icon'][1] = 'True'
        self._config_options['recording_dir'][1] = path.join(self._cnf.stations_dir, 'recordings')
        self._config_options['connection_timeout'][1] = '10'
        self._config_options['theme_title'][1] = ''
        ''' Transparency '''
        #self._old_use_transparency = self._config_options['use_transparency'][1]
        self._config_options['use_transparency'][1] = False
        self._config_options['force_transparency'][1] = False
        self._config_options['calculated_color_factor'][1] = '0'
        self._config_options['force_http'][1] = False
        self._toggle_transparency_function(changed_from_config_window=True, force_value=False)
        self._config_options['playlist_manngement_title'][1] = ''
        self._config_options['confirm_station_deletion'][1] = True
        self._config_options['confirm_playlist_reload'][1] = True
        self._config_options['auto_save_playlist'][1] = False
        self._config_options['requested_player'][1] = ''
        self._config_options['remote_control_server_ip'][1] = 'localhost'
        self._config_options['remote_control_server_port'][1] = '9998'
        self._port_line_editor.string = '9998'
        self._config_options['remote_control_server_auto_start'][1] = False
        ''' Theme
            Put this AFTER applying transparency, so that _do_init_pairs in
            _toggle_transparency does not overwrite pairs with applied theme values
        '''
        self._config_options['theme'][1] = 'dark'
        self._apply_a_theme('dark', False)
        self._check_if_config_is_dirty()

    def _check_if_config_is_dirty(self):
        if self._config_options == self._saved_config_options:
            self._config_options['dirty_config'] = ['', False]
        else:
            self._config_options['dirty_config'] = ['', True]

    def _apply_a_theme(self, a_theme, use_transparency=None):
        theme = PyRadioTheme(self._cnf)
        theme.readAndApplyTheme(a_theme, use_transparency=use_transparency)
        self._cnf.use_calculated_colors = False if self._cnf.opts['calculated_color_factor'][1] == '0' else True
        self._cnf.update_calculated_colors()
        theme = None
        curses.doupdate()

    def _is_port_invalid(self):
        if 1025 <= int(self._port_line_editor.string) <= 65535:
            self._config_options['remote_control_server_port'][1] = self._port_line_editor.string
            return False
        self._show_port_number_invalid()
        return True

    def _go_up(self):
        if self._is_port_invalid():
            return
        self._put_cursor(-1)
        self.refresh_selection()

    def _go_down(self):
        if self._is_port_invalid():
            return
        self._put_cursor(1)
        self.refresh_selection()

    def _go_pgup(self):
        if self._is_port_invalid():
            return
        self._put_cursor(-5)
        self.refresh_selection()

    def _go_pgdown(self):
        if self._is_port_invalid():
            return
        self._put_cursor(5)
        self.refresh_selection()

    def _go_home(self):
        if self._is_port_invalid():
            return
        self._start = 0
        self.__selection = 1
        self.refresh_selection()

    def _go_end(self):
        if self._is_port_invalid():
            return
        # logger.error('self._start = {}'.format(self._start))
        # logger.error('self.__selection = {}'.format(self.__selection))
        # logger.error('self.number_of_items = {}'.format(self.number_of_items))
        self.__selection = self.number_of_items - 1
        # fixing #215
        if self.number_of_items > self.maxY:
            self._start = self.__selection - self.maxY + 2
        # logger.error('self.maxY = {}'.format(self.maxY))
        # logger.error('self._start = {}'.format(self._start))
        # logger.error('self.__selection = {}'.format(self.__selection))
        self._put_cursor(0)
        self.refresh_selection()

    def _go_default(self):
        self._load_default_values()
        self.refresh_selection()
        if logger.isEnabledFor(logging.INFO):
            logger.info('Default options loaded')

    def _go_saved(self):
        if self._cnf.use_themes:
            old_theme = self._config_options['theme'][1]
            old_transparency = self._config_options['use_transparency'][1]
            self._config_options = deepcopy(self._saved_config_options)
            self._port_line_editor.string = self._config_options['remote_control_server_port'][1]
            ''' Transparency '''
            self._config_options['use_transparency'][1] = self._old_use_transparency
            self._toggle_transparency_function(
                changed_from_config_window=True,
                force_value=self._old_use_transparency)
            ''' Theme
                Put it after applying transparency, so that saved color_pairs
                do not get loaded instead of active ones
            '''
            self._config_options['theme'][1] = self._old_theme
            self._saved_config_options['theme'][1] = self._old_theme
            self._apply_a_theme(self._config_options['theme'][1], self._old_use_transparency)
        self._reset_parameters_function()
        self.refresh_selection()
        if logger.isEnabledFor(logging.INFO):
            logger.info('Saved options loaded')

    def _go_exit(self):
        self._win.nodelay(True)
        char = self._win.getch()
        self._win.nodelay(False)
        if char == -1:
            ''' ESCAPE '''
            logger.error('dirty config is {}, and ESC pressed'.format(self._cnf.dirty_config))
            self._saved_config_options['theme'][1] = self._old_theme
            self._cnf.opts['theme'][1] = self._old_theme
            self._cnf.theme = self._old_theme

    def _go_save(self):
        if self._is_port_invalid():
            return
        ''' save and exit '''
        self._old_theme = self._config_options['theme'][1]
        if self._saved_config_options['enable_mouse'][1] == self._config_options['enable_mouse'][1]:
            self.mouse_support_option_changed = False
        else:
            self.mouse_support_option_changed = True
        if self._saved_config_options['calculated_color_factor'][1] == self._config_options['calculated_color_factor'][1]:
            self.need_to_update_theme = False
        else:
            self.need_to_update_theme = True
        self._cnf.rec_dirs = (self._config_options['recording_dir'][1], self._saved_config_options['recording_dir'][1])
        logger.error('rec_dirs\n{}'.format(self._cnf.rec_dirs))
        self._saved_config_options = deepcopy(self._config_options)
        if self._cnf.opts != self._saved_config_options:
            ''' check if player has changed '''
            if self._cnf.opts['player'][1] != self._saved_config_options['player'][1]:
                self._cnf.player_changed = True
                self._cnf.player_values = [self._cnf.opts['player'][1], self._saved_config_options['player'][1]]
            self._cnf.opts = deepcopy(self._saved_config_options)
            self._old_theme == self._saved_config_options['theme'][1]
            self._config_options = deepcopy(self._cnf.opts)
            self._cnf.dirty_config = True
        else:
            self._cnf.dirty_config = False
        self._save_parameters_function()
        return True

    def keypress(self, char):
        ''' Config Window key press
            Returns:
                -1  continue
                 0  save config
                 1  cancel saving config
                 2  cancel a dirty config (not active currently)
                 3  open online browser config
                 4 open recording dir selection window
        '''
        if self.too_small:
            return 1, []
        # logger.error('max = {0}, len = {1}'.format(self.maxY, len(self._config_options)))
        self._max_start =  len(self._config_options) -1 - self.maxY
        # logger.error('mas_start = {}'.format(self._max_start))
        val = list(self._config_options.items())[self.selection]
        Y = self.selection - self._start + 1

        if char in self._local_functions.keys():
            if not (val[0] in (
                'remote_control_server_port',
                'enable_notifications',
                'connection_timeout',
                'calculated_color_factor',
            ) and char in (
                curses.KEY_LEFT,
                curses.KEY_RIGHT,
                ord('h'), ord('l'),
            )):
                    ret = self._local_functions[char]()
                    if self._local_functions[char] == self._go_exit:
                        return 1, []
                    elif self._local_functions[char] == self._go_save and ret:
                        return 0, []
                    return -1, []

        if char in self._global_functions.keys():
            self._global_functions[char]()

        elif val[0] == 'recording_dir':
            return self.n_u.INSERT_RECORDINGS_DIR_MODE, []

        elif val[0] == 'radiobrowser':
            if char in (curses.KEY_RIGHT, ord('l'),
                        ord(' '), curses.KEY_ENTER, ord('\n')):
                return 3, []

        elif val[0] == 'remote_control_server_port':
            ret = self._port_line_editor.keypress(self._win, char)
            if ret == 1:
                return -1, []

        elif val[0] == 'enable_notifications':
            if char in (curses.KEY_RIGHT, ord('l')):
                t = int(val[1][1])
                if t == -1:
                    t = 0
                elif t == 0:
                    t = 30
                else:
                    t += 30
                    if t > 300:
                        t =300
                val[1][1] = str(t)
                self._win.addstr(
                    Y, 3 + len(val[1][0]),
                    val[1][1] + '     ', curses.color_pair(6))
                self._print_title()
                self._win.refresh()
                return -1, []
            elif char in (curses.KEY_LEFT, ord('h')):
                t = int(val[1][1])
                if t == -1:
                    t = -1
                elif t == 0:
                    t = -1
                else:
                    t -= 30
                val[1][1] = str(t)
                self._win.addstr(
                    Y, 3 + len(val[1][0]),
                    val[1][1] + '     ', curses.color_pair(6))
                self._print_title()
                self._win.refresh()
                return -1, []

        elif val[0] == 'calculated_color_factor':
            if char in (curses.KEY_RIGHT, ord('l')):
                if self._cnf.use_themes:
                    t = float(val[1][1])
                    if t < .2:
                        t = round(t + .01, 2)
                        logger.error('t = {}'.format(t))
                        s_t = str(t)[:4]
                        if s_t == '0.0':
                            s_t = '0'
                        logger.error('s_t = ' + s_t)
                        self._config_options[val[0]][1] = s_t
                        self._win.addstr(
                            Y, 3 + len(val[1][0]),
                            s_t + '     ', curses.color_pair(6))
                        self._print_title()
                        self._win.refresh()
                        # att = PyRadioThemeReadWrite(self._cnf)
                        # att._calculate_fifteenth_color()
                else:
                    self._cnf._show_colors_cannot_change()
                return -1, []

            elif char in (curses.KEY_LEFT, ord('h')):
                if self._cnf.use_themes:
                    t = float(val[1][1])
                    if t > 0:
                        t = round(t - .01, 2)
                        logger.error('t = {}'.format(t))
                        s_t = str(t)[:4]
                        if s_t == '0.0':
                            s_t = '0'
                        logger.error('s_t = ' + s_t)
                        self._config_options[val[0]][1] = s_t
                        self._win.addstr(
                            Y, 3 + len(val[1][0]),
                            s_t + '     ', curses.color_pair(6))
                        self._print_title()
                        self._win.refresh()
                        # att = PyRadioThemeReadWrite(self._cnf)
                        # att._calculate_fifteenth_color()
                else:
                    self._cnf._show_colors_cannot_change()
                return -1, []

        elif val[0] == 'remote_control_server_ip':
            if char in (curses.KEY_RIGHT, ord('l'), ord(' '), ord('\n'), curses.KEY_ENTER):
                self._config_options[val[0]][1] = self.nip.next()
                disp = self._config_options[val[0]][1].ljust(15)
                # if self._config_options[val[0]][1] == 'localhost':
                #     self._config_options[val[0]][1] = 'LAN'
                #     disp = 'LAN      '
                # else:
                #     self._config_options[val[0]][1] = 'localhost'
                #     disp = 'localhost'
                self._win.addstr(
                    Y, 3 + len(val[1][0]),
                    disp, curses.color_pair(6)
                )
                self._print_title()
                self._win.refresh()
                return -1, []
            elif char in (curses.KEY_LEFT, ord('h')):
                if self._config_options[val[0]][1] == 'localhost':
                    self._config_options[val[0]][1] = 'LAN'
                    disp = 'LAN      '
                else:
                    self._config_options[val[0]][1] = 'localhost'
                    disp = 'localhost'
                self._win.addstr(
                    Y, 3 + len(val[1][0]),
                    disp, curses.color_pair(6)
                )
                self._print_title()
                self._win.refresh()
                return -1, []

        elif val[0] == 'connection_timeout':
            if char in (curses.KEY_RIGHT, ord('l')):
                t = int(val[1][1])
                if t == 0:
                    t = 4
                if t < 60:
                    t += 1
                    self._config_options[val[0]][1] = str(t)
                    self._win.addstr(
                        Y, 3 + len(val[1][0]),
                        str(t) + ' ', curses.color_pair(6))
                    self._print_title()
                    self._win.refresh()
                return -1, []

            elif char in (curses.KEY_LEFT, ord('h')):
                t = int(val[1][1])
                if t > 5:
                    t -= 1
                else:
                    t = 0
                self._config_options[val[0]][1] = str(t)
                self._win.addstr(
                    Y, 3 + len(val[1][0]),
                    str(t) + ' ', curses.color_pair(6))
                self._print_title()
                self._win.refresh()
                return -1, []

        if char in (
                curses.KEY_ENTER, ord('\n'),
                ord('\r'), ord(' '), ord('l'), curses.KEY_RIGHT):
            ''' alter option value '''
            vals = list(self._config_options.items())
            sel = vals[self.selection][0]
            if sel == 'player':
                return self.n_u.SELECT_PLAYER_MODE, []
            elif sel == 'default_encoding':
                return self.n_u.SELECT_ENCODING_MODE, []
            elif sel == 'theme':
                if self._cnf.use_themes:
                    self._cnf.theme = self._old_theme
                    if logger.isEnabledFor(logging.ERROR):
                        logger.error('DE\n\nshowing theme self._cnf.theme = {}\n\n'.format(self._cnf.theme))
                self._show_theme_selector_function()
            elif sel == 'default_playlist':
                return self.n_u.SELECT_PLAYLIST_MODE, []
            elif sel == 'default_station':
                return self.n_u.SELECT_STATION_MODE, []
            elif sel == 'confirm_station_deletion' or \
                    sel == 'open_last_playlist' or \
                    sel == 'confirm_playlist_reload' or \
                    sel == 'enable_mouse' or \
                    sel == 'auto_save_playlist' or \
                    sel == 'force_http' or \
                    sel == 'remote_control_server_auto_start' or \
                    sel == 'use_station_icon':
                self._config_options[sel][1] = not self._config_options[sel][1]
                # # if sel == 'open_last_playlist':
                # #     if self._config_options[sel][1]:
                # #         ''' became True, save last playlist '''
                # #         self._cnf.save_last_playlist()
                self.refresh_selection()
            elif sel == 'force_transparency':
                #self._old_use_transparency = not self._config_options[ 'use_transparency' ][1]
                self._config_options['force_transparency'][1] = not self._config_options['force_transparency'][1]
                self._update_transparency_function(
                    changed_from_config_window=True,
                    calculate_transparency_function=self.calculate_transparency
                )
                self.refresh_selection()
            elif sel == 'use_transparency':
                self._old_use_transparency = not self._config_options[ 'use_transparency' ][1]
                self._cnf.use_transparency = not self._cnf.use_transparency
                self._config_options[ 'use_transparency' ][1] = self._old_use_transparency
                self._update_transparency_function(
                    changed_from_config_window=True,
                    calculate_transparency_function=self.calculate_transparency
                )
                self.refresh_selection()
                # self._toggle_transparency_function(
                #     changed_from_config_window=True,
                #     force_value = not self._config_options['use_transparency'][1]
                # )
                # self.refresh_selection()

        return -1, []


class PyRadioExtraParams(object):
    ''' Class to display extra player parameters on
        main window. No editing allowed!
    '''

    def __init__(self,
                 config,
                 parent,
                 global_functions=None):
        ''' setting editing to 0 so that help functions work '''
        self.editing = 0
        self._max_lines = 16
        self._note_text = ' Note '
        self._note_line1 = 'Changes made here wil not be'
        self._note_line2 = 'saved in the configuration file'
        self._extra = None
        self._cnf = config
        self._parent = parent
        self._win = None
        self._title = ' Player Extra Parameters '
        self._too_small_str = 'Window too small'
        self._cnf.get_player_params_from_backup(param_type=1)
        self._global_functions = global_functions
        ''' list is list of player profiles / parameters '''
        self._list = None
        self._redisplay()

    @property
    def params(self):
        return self._extra._working_params

    @params.setter
    def params(self, val):
        raise ValueError('property is read only')

    def set_parrent(self, window):
        self._parent = window
        self._redisplay()

    def _redisplay(self):
        pY, pX = self._parent.getmaxyx()
        logger.error('pY = {0}, pX = {1}'.format(pY, pX))
        if pY < self._max_lines + 2 or pX < 30:
            self._too_small = True
            self._win = curses.newwin(
                3, len(self._too_small_str) + 4,
                int((pY - 3) / 2) + 2,
                int((pX - len(self._too_small_str)) / 2)
            )
            self.show()
            return
        else:
            self._too_small = False
            self.maxX = pX - 2 if pX < 40 else 40
            logger.error('maxX = {}'.format(self.maxX))
            logger.error('max_lines = {}'.format(self._max_lines))
            self._Y = int((pY - self._max_lines) / 2) + 2
            self._X = int((pX - self.maxX) / 2)
            self._win = curses.newwin(
                self._max_lines, self.maxX,
                self._Y, self._X
            )
        if self._extra:
            self._extra.set_window(self._win, do_show=False)
            self.show()
        else:
            ''' No editing allowed '''
            self._extra = ExtraParameters(
                self._cnf,
                self._cnf.PLAYER_NAME,
                self._win,
                lambda: True,
                from_config=False,
                global_functions=self._global_functions
            )
            self._extra.enabled = self._extra.focused = True

    def show(self):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        if self._too_small:
            self._win.addstr(1, 1, self._too_small_str,
                             curses.color_pair(10))
            self._win.refresh()
        else:
            ''' show title '''
            self._win.addstr(
                0, int((self.maxX - len(self._title)) / 2),
                self._title,
                curses.color_pair(11))
            ''' show note '''
            try:
                self._win.addstr(12, 2, '─' * (self.maxX - 4), curses.color_pair(3))
            except:
                self._win.addstr(12, 2, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
            self._win.addstr(12, int((self.maxX - len(self._note_text))/2), self._note_text, curses.color_pair(3))

            self._win.addstr(13, int((self.maxX - len(self._note_line1)) / 2), self._note_line1, curses.color_pair(10))
            self._win.addstr(14, int((self.maxX - len(self._note_line2)) / 2), self._note_line2, curses.color_pair(10))

            self._move_in_config_win_Y = self._Y
            self._move_in_config_win_Y = self._X
            self._extra.refresh_win()

    def keypress(self, char):
        return self._extra.keypress(char)


class ExtraParametersEditor(object):
    ''' Class to edit or add parameters
    '''

    def __init__(self,
                 parent,
                 config,
                 string='',
                 global_functions=None):
        self._parent = parent
        self._cnf = config
        self.edit_string = string
        self._caption = ' Parameter value '
        self._string = self._orig_string = string

        self._global_functions = set_global_functions(global_functions)
        self.Y, self.X = self._parent.getbegyx()
        self.Y += 1
        self.X += 1
        self.maxY, self.maxX = self._parent.getmaxyx()
        self.maxY -= 2
        self.maxX -= 2
        self._win = curses.newwin(
            self.maxY, self.maxX,
            self.Y, self.X)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()

        self._focus = 0
        self._widgets = [None, None, None]

        self._too_small = False

        ''' add line editor '''
        self._widgets[0] = SimpleCursesLineEdit(
            parent=self._win,
            width=self.maxX - 2,
            begin_y=self.Y + 1,
            begin_x=self.X + 1,
            boxed=False,
            has_history=False,
            caption='',
            box_color=curses.color_pair(9),
            caption_color=curses.color_pair(11),
            edit_color=curses.color_pair(9),
            cursor_color=curses.color_pair(8),
            unfocused_color=curses.color_pair(10),
            string_changed_handler=self._string_changed
        )
        self._widgets[0].string = string
        self._widgets[0].bracket = False
        self._widgets[0]._use_paste_mode = True
        self._widgets[0]._mode_changed = self._show_alternative_modes
        self._widgets[0].set_global_functions(self._global_functions)
        ''' enables direct insersion of ? and \\ '''
        self._widgets[0]._paste_mode = False
        self._line_editor = self._widgets[0]

        ''' add horizontal push buttons '''
        self._h_buttons = SimpleCursesHorizontalPushButtons(
                Y=3, captions=('OK', 'Cancel'),
                color_focused=curses.color_pair(9),
                color=curses.color_pair(11),
                bracket_color=curses.color_pair(10),
                parent=self._win)
        self._h_buttons.calculate_buttons_position()
        self._widgets[1], self._widgets[2] = self._h_buttons.buttons
        self._widgets[1]._focused = self._widgets[2].focused = False

        if not self._orig_string:
            self._widgets[1].enabled = False

    def _show_alternative_modes(self):
        if self._line_editor._paste_mode:
            """ print paste mode is on on editor """
            self._win.addstr(0, 18, '[', curses.color_pair(10))
            self._win.addstr('Paste mode', curses.color_pair(11))
            self._win.addstr(']    ', curses.color_pair(10))
        else:
            if self._line_editor.backslash_pressed:
                """ print editor's flag """
                # fix for python 2
                #self._win.addstr(*lin[i], '[', curses.color_pair(10))
                self._win.addstr(0, 18, '[', curses.color_pair(10))
                self._win.addstr('Extra mode', curses.color_pair(11))
                self._win.addstr(']', curses.color_pair(10))
            else:
                """ print cleared editor's flag """
                # fix for python 2
                #self._win.addstr(*lin[i], 15 * ' ', curses.color_pair(10))
                self._win.addstr(0, 18, 15 * ' ', curses.color_pair(10))
        self._win.refresh()

    def _string_changed(self):
        pass

    def resize(self, parent):
        self._parent = parent
        self.Y, self.X = self._parent.getbegyx()
        self.Y += 1
        self.X += 1
        self._win.mvwin(self.Y, self.X)

        self._h_buttons.calculate_buttons_position(parent=self._win)
        self._win.refresh()
        self.refresh_win()

    def show(self):
        self._win.addstr(0, 0, self._caption, curses.color_pair(10))
        try:
            self._win.addstr(5, 3, '─' * (self.maxX - 6), curses.color_pair(3))
        except:
            self._win.addstr(5, 3, '─'.encode('utf-8') * (self.maxX - 6), curses.color_pair(3))
        self._win.addstr(5, int((self.maxX - 6) / 2), ' Help ', curses.color_pair(11))


        self._win.addstr(6, 5, 'TAB', curses.color_pair(11))
        self._win.addstr(', ', curses.color_pair(10))
        self._win.addstr('Down', curses.color_pair(11))
        self._win.addstr(' / ', curses.color_pair(10))
        self._win.addstr('Up', curses.color_pair(11))
        self._win.addstr('    Go to next / previous field.', curses.color_pair(10))
        self._win.addstr(7, 5, 'ENTER', curses.color_pair(11))
        self._win.addstr('             When in Line Editor, go to next field.', curses.color_pair(10))
        step = 0
        if self._orig_string:
            self._win.addstr(8, 5, 'r', curses.color_pair(11))
            self._win.addstr(', ', curses.color_pair(10))
            self._win.addstr('^R', curses.color_pair(11))
            self._win.addstr(8, 23, 'Revert to saved values (', curses.color_pair(10))
            self._win.addstr('^R', curses.color_pair(11))
            self._win.addstr(' in Line Editor).', curses.color_pair(10))
            step = 1
        self._win.addstr(8 + step, 5, 'Esc', curses.color_pair(11))
        self._win.addstr(8 + step, 23, 'Cancel operation.', curses.color_pair(10))

        self._win.addstr(9 + step, 5, 's', curses.color_pair(11))
        self._win.addstr(' / ', curses.color_pair(10))
        self._win.addstr('q', curses.color_pair(11))
        self._win.addstr(9 + step , 23, 'Save / Cancel (not in Line Editor).', curses.color_pair(10))

        self._win.addstr(10 + step, 5, '?', curses.color_pair(11))
        self._win.addstr(10 + step, 23, 'Line editor help (in Line Editor).', curses.color_pair(10))
        self._show_alternative_modes()
        self._win.refresh()
        self.refresh_win()

    def refresh_win(self):
        if not self._too_small:
            self._line_editor.show(
                self._win, opening=False,
                new_y=self.Y + 1,
                new_x=self.X + 1)
            self._widgets[1].show()
            self._widgets[2].show()

    def _update_focus(self):
        ''' use _focused here to avoid triggering
            widgets' refresh
        '''
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

    def _focus_next(self):
        if self._focus == len(self._widgets) - 1:
            self._focus = 0
        else:
            focus = self._focus + 1
            while not self._widgets[focus].enabled:
                focus += 1
            self._focus = focus

    def _focus_previous(self):
        if self._focus == 0:
            self._focus = len(self._widgets) - 1
        else:
            focus = self._focus - 1
            while not self._widgets[focus].enabled:
                focus -= 1
            self._focus = focus

    def keypress(self, char):
        ''' Extra parameter editor keypress
            Returns:
                0: Response ready (in edit_string)
                1: Continue
                2: Display line editor help
        '''
        ret = 1
        if char == ord('?') and self._focus > 0:
            return 2
        elif char in (curses.KEY_EXIT, 27, ord('q')) and \
                self._focus > 0:
            self.edit_string = ''
            ret = 0
        elif char in (ord('\t'), 9, curses.KEY_DOWN):
            self._focus_next()
        elif char == curses.KEY_UP:
            self._focus_previous()
        elif char in (curses.KEY_ENTER, ord('\n'), ord('\r')):
            if self._focus == 0:
                ''' go to next field '''
                self._focus_next()
            elif self._focus == 1:
                ''' save string '''
                self.edit_string = self._line_editor.string.strip()
                ret = 0
            else:
                ''' cancel '''
                self.edit_string = ''
                ret = 0
        elif char == ord('s') and self._focus > 0:
            ''' s, execute '''
            if self._widgets[1].enabled:
                self.edit_string = self._line_editor.string.strip()
                ret = 0
        elif self._focus == 0:
            '''
             Returns:
                2: display help
                1: get next char
                0: exit edit mode, string isvalid
               -1: cancel
            '''
            ret = self._line_editor.keypress(self._win, char)
            if ret == 2:
                self._win.touchwin()
            elif ret == 1:
                ''' get next char '''
                if self._line_editor.string.strip():
                    self._widgets[1].enabled = True
                else:
                    self._widgets[1].enabled = False
                ret = 1
            elif ret == 0:
                ''' exit, string is valid '''
                self.edit_string = self._line_editor.string.strip()
                ret = 0
            elif ret == -1:
                ''' cancel '''
                self.edit_string = ''
                ret = 0
        elif char in self._global_functions.keys():
            self._global_functions[char]()
            return 1

        if ret == 1:
            self._update_focus()
            self.refresh_win()
        ''' Continue '''
        return ret

        try:
            self._count += 1
        except:
            self._count = 1
        if self._count > 2:
            return 0
        else:
            return 1

    def _update_focus(self):
        ''' use _focused here to avoid triggering
            widgets' refresh
        '''
        for i, x in enumerate(self._widgets):
            if x:
                if self._focus == i:
                    x._focused = True
                else:
                    x._focused = False

class ExtraParameters(object):
    ''' display player's extra parameters
        in a foreign curses window ('Z')
    '''

    def __init__(self,
                 config,
                 player,
                 win,
                 focus,
                 startY=1,
                 startX=1,
                 max_lines=11,
                 from_config=True,
                 can_add_items=False,
                 can_delete_items=False,
                 can_edit_items=False,
                 entry_cannot_be_added_function=None,
                 entry_cannot_be_edited_function=None,
                 entry_cannot_be_deleted_function=None,
                 global_functions=None):
        self._list = None
        self._cnf = config
        self._orig_params = deepcopy(self._cnf.params)
        self._global_functions = set_global_functions(global_functions)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('original parameters = {}'.format(self._orig_params))
        self._player = player
        self._orig_player = player
        # logger.error('DE orig player = {}'.format(self._orig_player))
        self._win = win
        self._focus = focus
        self.from_config = from_config

        ''' editing functions '''
        self._can_add_items = can_add_items
        self._can_delete_items = can_delete_items
        self._can_edit_items = can_edit_items

        self._entry_cannot_be_added_function = entry_cannot_be_added_function
        self._entry_cannot_be_edited_function = entry_cannot_be_edited_function
        self._entry_cannot_be_deleted_function = entry_cannot_be_deleted_function
        ''' end editing functions '''

        ''' start Y, X '''
        self.startY = startY
        self.startX = startX
        # logger.error('start self.startY = {}'.format(self.startY))
        # logger.error('start self.startX = {}'.format(self.startX))
        self._parentY, self._parentX = self._win.getbegyx()
        # logger.error('start self._parentY = {}'.format(self._parentY))
        # logger.error('start self._parentX = {}'.format(self._parentX))

        ''' maximum number of lines to display '''
        self.max_lines = max_lines

        if from_config:
            self._working_params = deepcopy(self._cnf.saved_params)
        else:
            self._working_params = deepcopy(self._cnf.params)
        self._profiles_from_files = self._extract_all_profiles()
        # logger.error('\n\nself._profiles_from_files\n{}\n\n'.format(self._profiles_from_files))

        self.reset(saved=False)
        ''' set cursor to active item '''
        for a_key in self._selections.keys():
            self._selections[a_key][0] = self._selections[a_key][2]
        # logger.error('self._selections\n{}'.format(self._selections))
        self._get_width()

    @property
    def focused(self):
        return self._focus

    @focused.setter
    def focused(self, val):
        self._focus = val
        if self._list is not None:
            self._list.focused = val

    @property
    def player(self):
        return self._player

    @player.setter
    def player(self, a_player):
        if a_player in self._cnf.SUPPORTED_PLAYERS:
            logger.info('==== new player: {}'.format(a_player))
            self._player = a_player
            self._items = self._items_dict[a_player]
            self.refresh_win()

    @property
    def selection(self):
        if self._list:
            return self._list.selection
        return(self._selections[self._player][0])

    @selection.setter
    def selection(self, val):
        if self._list:
            self._list.selection = val
        self._selections[self._player][0] = val

    @property
    def startPos(self):
        if self._list:
            return self._list.startPos
        return(self._selections[self._player][1])

    @startPos.setter
    def startPos(self, val):
        self._selections[self._player][1] = val

    @property
    def active(self):
        ''' this is the parameter to be used by the player '''
        if self._list:
            return self._list.active
        return(self._selections[self._player][2])

    @active.setter
    def active(self, val):
        if self._list:
            self._list.active = val
        self._selections[self._player][2] = val

    @property
    def original_active(self):
        if self._player == self._cnf.PLAYER_NAME:
            return self._original_active
        else:
            return self.selection

    @original_active.setter
    def original_active(self, val):
        raise ValueError('property is read only')

    @property
    def params(self):
        ''' Returns the parameters as changed by the user '''
        return self._orig_params

    @params.setter
    def params(self, val):
        raise ValueError('parameter is read only')

    def edit_item(self, an_item_id, an_item, select=False):
        if self._list:
            self._list.edit_item(an_item_id, an_item, select)

    def add_item(self, an_item, select=False):
        if self._list:
            self._list.add_item(an_item, select)

    def _validate_add_entry(self, index, item):
        return False if item.startswith('profile:') else True

    def _validate_delete_entry(self, index, item):
        if item.startswith('Do not use'):
            return False
        return False if item.startswith('profile:') else True

    def _validate_edit_entry(self, index, item):
        if item.startswith('Do not use'):
            return False
        return False if item.startswith('profile:') else True

    def _reposition_list(self):
        Y, X = self._win.getbegyx()
        if self.from_config:
            self._offsetY = Y + 2
            self._offsetX = X + 24
        else:
            self._offsetY = Y + 1
            self._offsetX = X + 2
        if self._list:
            self._list.get_new_win(self._offsetY, self._offsetX)

    def _add_params_to_all_profiles(self):
        for n in self._cnf.SUPPORTED_PLAYERS:
            self._add_params_to_profiles(n)

    def _add_params_to_profiles(self, a_player_name=None):
        if a_player_name is None:
            a_player_name = self._player
        # logger.error('\n=============================\n============================')
        # logger.error('self._working_params = {}'.format(self._working_params))
        # logger.error('a_player_name = {}'.format(a_player_name))
        default_id = self._working_params[a_player_name][0]
        # logger.error('default_id = {}'.format(default_id))
        default = self._working_params[a_player_name][default_id].strip()
        # logger.error('default = {}'.format(default))
        for n in self._working_params[a_player_name][1:]:
            stripped = n.strip()
            if not stripped.startswith('profile:'):
                if not stripped.startswith('Do not use any extra'):
                    if stripped not in self._profiles_from_files[a_player_name]:
                        self._profiles_from_files[a_player_name].append(stripped)
        # logger.error('self._profiles_from_files[a_player_name] = {}'.format(self._profiles_from_files[a_player_name]))
        if default in self._profiles_from_files[a_player_name]:
            default_id = self._profiles_from_files[a_player_name].index(default)
        else:
            try:
                default_id = self._profiles_from_files[a_player_name].index('profile:pyradio')
            except ValueError:
                default_id = 0
        # logger.error('default_id = {}'.format(default_id))
        if self.from_config or (a_player_name=='vlc'):
            self._selections[a_player_name][2] = default_id
        else:
            self._selections[a_player_name][2] = default_id - 1
        # logger.error('self._selections[a_player_name][2] = {}'.format( self._selections[a_player_name][2] ))

    def _extract_profile(self, a_file):
        ''' extract profiles from a file '''
        from sys import version as l_py_version
        PY3 = l_py_version[0] == 3
        try:
            out = []
            with open(a_file, 'r') as f:
                r = f.readlines()
                for n in r:
                    k = n.strip()
                    if k.startswith('[') and \
                            k.endswith(']'):
                        out.append(k[1:-1])
            return out
        except (FileNotFoundError, PermissionError) if PY3 else IOError:
            return []

    def _extract_profiles(self, config_files, a_player_name=None):
        if a_player_name is None:
            a_player_name = self._player
        if a_player_name == 'vlc':
            return ['Do not use any extra player parameters']
        ''' extract profiles for a player '''
        result = []
        for n in config_files:
            result.extend(self._extract_profile(n))

        ''' convert to set and remove pyradio '''
        result = list(set(result))
        if result:
            if 'pyradio' not in result:
                result.append('pyradio')
        else:
            result = ['pyradio']
        result.sort()
        return ['profile:' + x for x in result]

    def _extract_all_profiles(self):
        ''' extract profiles for all players '''
        out = {}
        if self.from_config:
            for n in self._cnf.SUPPORTED_PLAYERS:
                if n == 'vlc':
                    out[n] = ['Do not use any extra player parameters']
                else:
                    out[n] = self._extract_profiles(
                            self._cnf.player_instance().all_config_files[n],
                            a_player_name=n
                            )
        else:
            if self._player == 'vlc':
                out['vlc'] = ['Do not use any extra player parameters']
                out['mpv'] = []
                out['mplayer'] = []
            else:
                out['vlc'] = []
                if self._player == 'mplayer':
                    out['mpv'] = []
                else:
                    out['mplayer'] = []
                out[self._player] = self._extract_profiles(
                        self._cnf.player_instance().all_config_files[self._player],
                        a_player_name=self._player
                        )
        return out

    def _on_default_parameter_change(self):
        logger.error('selected!!!')
        self._defaults[self._player] = self._list.active_item

    def check_parameters(self):
        ''' Exrta Parameters check '''
        for a_key in self._orig_params.keys():
            if self._orig_params[a_key] != self._working_params[a_key]:
                self._cnf.dirty_config = self._cnf.params_changed = True
                return True
        return False

    def reset(self, saved=True, from_reset=False):
        ''' reset Player Selection Options

            Parameter
            ========
            saved:
                False - load params from config (default)
                True  - load saved params from config
        '''
        self._player = self._orig_player
        # logger.error('saved = {}'.format(saved))
        if saved:
            self._working_params = deepcopy(self._cnf.saved_params)
        else:
            self._working_params = deepcopy(self._cnf.params)
        ''' selections
                0: selection
                1: startPos
                2: active
        '''
        self._selections = {
            'mpv': [0, 0, 0],
            'mplayer': [0, 0, 0],
            'vlc': [0, 0, 0]
        }
        self._items_dict = {
            'mpv': [],
            'mplayer': [],
            'vlc': []
        }
        logger.exception('\n\n1 Extraparameters.reset\nself._items.dict\n{}\n\n'.format(self._items_dict))
        if self.from_config:
            self._add_params_to_all_profiles()
        else:
            self._add_params_to_profiles(self._player)
        logger.error('self._working_params\n{}'.format(self._working_params))
        self._defaults = {
            'mpv': self._working_params['mpv'][self._working_params['mpv'][0]],
            'mplayer': self._working_params['mplayer'][self._working_params['mplayer'][0]],
            'vlc': self._working_params['vlc'][self._working_params['vlc'][0]],
        }
        # logger.error('\n\nself._defaults\n{}'.format(self._defaults))
        self._dict_to_list()
        # default_id = self._working_params[a_player_name][0]
        # default = self._working_params[a_player_name][default_id].strip()
        for a_player in self._cnf.SUPPORTED_PLAYERS:
            if self._items_dict[a_player]:
                if isinstance(self._items_dict[a_player][0], int):
                    self._items_dict[a_player].pop(0)
        self._items = self._items_dict[self._player]
        logger.error('\n\n*****************************')
        logger.error('self._selections\n{}'.format(self._selections))
        logger.error('self._items_dict\n{}'.format(self._items_dict))
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('parameter items: {}'.format(self._items))
        if self._defaults[self._player] in self._items:
            logger.error('\n\nself._defaults\n{}'.format(self._defaults))
            logger.error('setting to players default: {}'.format(self._player))
            self.active = self._items.index(self._defaults[self._player])
        else:
            lgger.error('setting to profile:pyradio')
            self.active = self._items.index('profile:pyradio')
        logger.error('\n*****************************\n\n')
        if not saved:
            self._original_active = self.active
        logger.exception('\n\n2 Extraparameters.reset\nself._items.dict\n{}\n\n'.format(self._items_dict))

    def list_widget_to_selections(self):
        ''' pass Menu selection, startPos, active
            to self._selections
        '''
        logger.error('setting to player: {}'.format(self._player))
        self._selections[self._player] = [
                self._list.selection,
                self._list.startPos,
                self._list.active
                ]

    def _dict_to_list(self):
        ''' convert self._working_params dict
            to self._items dict, and set self.active
        '''
        # logger.error('DE\n')
        # logger.error('DE working params = {}'.format(self._working_params))
        for a_param_set in self._profiles_from_files.keys():
            for a_param in self._profiles_from_files[a_param_set]:
                self._items_dict[a_param_set].append(a_param)

    def _list_to_dict(self):
        ''' convert self._items_dict to self._working_params '''
        for a_params_set in self._items_dict.keys():
            the_list = [self._selections[a_params_set][2] + 1]
            the_list.extend(self._items_dict[a_params_set])
            self._working_params[a_params_set] = the_list[:]

    def _get_width(self):
        Y, X = self._win.getmaxyx()
        self._width = X - self.startX - 2

    def refresh_win(self, do_show=True):
        self._reposition_list()
        if self._list is None:
            # logger.error('self._parentY = {}'.format(self._parentY))
            # logger.error('self._parentX = {}'.format(self._parentX))
            # logger.error('self.startY = {}'.format(self.startY))
            # logger.error('self.startX = {}'.format(self.startX))
            # logger.error('self._offsetY = {}'.format(self._offsetY))
            # logger.error('self._offsetX = {}'.format(self._offsetX))
            # logger.error('max_lines = {}'.format(self.max_lines))
            # logger.error('max_width = {}'.format(self._width))
            if self.from_config:
                self._can_add_items = self._can_edit_items = self._can_delete_items = True
            else:
                self._can_add_items = self._can_edit_items = self._can_delete_items = False
            self._list = SimpleCursesMenu(
                    self._offsetY, self._offsetX,
                    parent=self._win,
                    selection=self.selection,
                    active=self.active,
                    items=self._items,
                    display_count=True,
                    max_height=self.max_lines,
                    max_width=self._width,
                    title='',
                    window_type=2,
                    bordered=False,
                    color=curses.color_pair(10),
                    color_title=curses.color_pair(11),
                    color_border=curses.color_pair(3),
                    color_active=curses.color_pair(11),
                    color_cursor_selection=curses.color_pair(6),
                    color_cursor_active=curses.color_pair(9),
                    can_add_items=self._can_add_items,
                    can_edit_items=self._can_edit_items,
                    can_delete_items=self._can_delete_items,
                    validate_add_entry=self._validate_add_entry,
                    validate_edit_entry=self._validate_edit_entry,
                    validate_delete_entry=self._validate_delete_entry,
                    entry_cannot_be_added_function=self._entry_cannot_be_added_function,
                    entry_cannot_be_edited_function=self._entry_cannot_be_edited_function,
                    entry_cannot_be_deleted_function=self._entry_cannot_be_deleted_function,
                    on_select_callback_function=self._on_default_parameter_change,
                    items_changed_function=self._update_items_dict,
                    )
            self._list.focused = not self.from_config
        self._win.refresh()
        if do_show:
            self._list.show(parent=self._win)

    def _get_color(self, a_line):
        col = curses.color_pair(10)
        if self._focus():
            if a_line == self.active:
                if a_line == self.selection:
                    col = curses.color_pair(9)
                else:
                    col = curses.color_pair(11)
            elif a_line == self.selection:
                col = curses.color_pair(6)
        else:
            if a_line == self.active:
                col = curses.color_pair(11)
        return col

    def set_player(self, a_player, from_keypress=False):
        if a_player in self._cnf.SUPPORTED_PLAYERS:
            # logger.error('\n>>>==========')
            # # logger.error('self._selections = {}'.format(self._selections))
            if self._list and from_keypress:
                self._update_items_dict()
            self._orig_player = self._player
            self._player = a_player
            self._items = self._items_dict[a_player]
            if self._list:
                self._list.set_items(items=self._items)
                self._list.selection = self._selections[self._player][0]
                self._list._start_pos = self._selections[self._player][1]
                self._list.active = self._selections[self._player][2]
            # logger.error('self._items_dict = {}'.format(self._items_dict))
            # logger.error('a_player = {}'.format(a_player))
            # # logger.error('self._items = {}'.format(self._items))
            # # logger.error('self._selections = {}'.format(self._selections))
            # logger.error('\n<<<==========')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('changing player to "{0}", loading times items: {1}'.format(self._player, self._items))
            self.refresh_win()

    def resize(self, window, startY=None, startX=None, do_show=True):
        self._win = window
        if startY is not None:
            self.startY = startY
        if startX is not None:
            self.startX = startX
        self._get_width()

        ''' erase params window
            done by containing window
        '''
        self.refresh_win(do_show=do_show)

    def set_window(self, window, do_show=True):
        self.resize(window=window, do_show=do_show)

    def _go_up(self, how_much=1):
        old_selection = self.selection
        self.selection -= how_much
        if old_selection == 0:
            self.selection = len(self._items) - 1
        else:
            if self.selection < 0:
                if how_much == 1:
                    self.selection = len(self._items) - 1
                else:
                    self.selection = 0
        self.refresh_win()

    def _go_down(self, how_much=1):
        old_selection = self.selection
        self.selection += how_much
        if old_selection == len(self._items) - 1:
            self.selection = 0
        else:
            if self.selection >= self.max_lines or \
                    self.selection >= len(self._items):
                if how_much == 1:
                    self.selection = 0
                else:
                    self.selection = len(self._items) - 1
        self.refresh_win()

    def _update_items_dict(self):
        ''' pass _list content to self._items_dict '''
        if self._list is not None:
            self._selections[self._player] = [
                    self._list.selection,
                    self._list.startPos,
                    self._list.active
                    ]
            self._items_dict[self._player] = self._list.items[:]
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('self._selections\n{0}\nself._items_dic\n{1}'.format(self._selections, self._items_dict))

    def save_results(self):
        ''' pass working parameters to original parameters
            effectively saving any changes.
        '''
        if self._list:
            self._update_items_dict()
        # logger.error('\n\n')
        # logger.error('DE save_results')
        # logger.error('DE self._player = {}'.format(self._player))
        # logger.error('DE 1 working_params = {}'.format(self._working_params))
        self._list_to_dict()
        # logger.error('DE 2 working_params = {}'.format(self._working_params))
        self.check_parameters()
        # logger.error('DE 3 working_params = {}'.format(self._working_params))
        self._orig_params = deepcopy(self._working_params)
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('new parameters (not saved) = {}'.format(self._orig_params))

    def keypress(self, char):
        ''' Extra parameters keypress
            Returns:
                -2 - cancel
                -1 - continue
                 0 - activate selection
                 1 - display help
                 2 - error, number of max lines reached
                 3 - error, cannot edit or delete first item
                 4 - edit parameter
                 5 - add parameter
                 6 - line editor help
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()
            return -1
        elif char in (
            curses.KEY_ENTER, ord('\n'),
            ord('\r'), ord(' '), ord('l'),
                curses.KEY_RIGHT, ord('s')):
            ''' activate selection '''
            self._list.keypress(char)
            # logger.error('DE active ={}, selection={}'.format(self.active, self.selection))
            self.active = self.selection = self._list.selection
            # logger.error('DE active ={}, selection={}'.format(self.active, self.selection))

            if self.from_config:
                self.refresh_win()
            else:
                self.save_results()
            return 0

        elif char in (
            curses.KEY_EXIT, 27,
            ord('q'), curses.KEY_LEFT,
            ord('h')
        ):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
                self.reset()
                return -2

        elif char == ord('?'):
            ''' display help '''
            return 1
        ret = self._list.keypress(char)
        if ret == 1:
            ret = -1
        return ret


class PyRadioSelectPlayer(object):

    maxY = 14
    maxX = 72
    selection = 0

    _title = ' Player Selection '

    _win = None
    _extra = None

    _working_players = [[], []]

    ''' mlength is the length of the longest item in the
        players list, which is '[ ] mplayer ' = 14
    '''
    mlength = 13

    def __init__(
            self,
            config,
            parent,
            player,
            parameters_editing_error_function=None,
            global_functions=None
            ):
        self._parameters_editing_error_function=parameters_editing_error_function
        self._char = ' [X] ' if platform.lower().startswith('win') else ' [✔] '
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('current players = {}'.format(player))
        self._cnf = config
        self._parent = parent
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        self.player = player
        self._orig_player = player
        self._global_functions = set_global_functions(global_functions)
        self.focus = True

        ''' Is editor active?
                0 - Not active
                1 - Adding a parameter
                2 - Editing a parameter
        '''
        self.editing = 0
        ''' result of parameter editing'''
        self.edit_string = None
        ''' parameter editor window '''
        self._parameter_editor = None

        ''' players contain supported players
            it is a list of lists
            each list contains three items
            0 - player name
            1 - True if enabled for detection
            2 - True if usable on platform
        '''
        self._players = []
        self._populate_players()
        self.init_window()
        self.refresh_win(do_params=True)

    def refresh_list(self):
        if self._extra is not None:
            self._extra.refresh_win()

    @property
    def from_config(self):
        if self._extra:
            return self._extra.from_config
        else:
            return True

    @from_config.setter
    def from_config(self, val):
        raise ValueError('property is read only')

    @property
    def is_dirty(self):
        if self._extra is not None:
            return self._extra.is_dirty
        return False

    @is_dirty.setter
    def is_dirty(self, val):
        raise ValueError('property is read only')

    def init_window(self):
        self._win = None
        Y = int((self._parent_maxY - self.maxY) / 2)
        if Y % 2 == 1:
            Y += 1
        self._win = curses.newwin(
            self.maxY, self.maxX,
            Y,
            int((self._parent_maxX - self.maxX) / 2)
        )
        if self._extra is None:
            ''' Editing allowed '''
            self._extra = ExtraParameters(
                self._cnf,
                self.selected_player_name(),
                self._win,
                lambda: not self.focus,
                startY=2,
                startX=self.mlength + 11,
                entry_cannot_be_added_function=self._parameters_editing_error_function,
                entry_cannot_be_edited_function=self._parameters_editing_error_function,
                entry_cannot_be_deleted_function=self._parameters_editing_error_function,
            )
            self._extra.enabled = True
            self._extra.focused = False
        else:
            self._extra.set_window(self._win)

    def selected_player_name(self):
        return self._players[self.selection][0]

    def _populate_players(self):
        self._players = []
        parts = self.player.replace(' ', '').split(',')
        for ap in parts:
            self._players.append([ap, True, True])

        if len(parts) < len(self._cnf.SUPPORTED_PLAYERS):
            ''' add missing player '''
            for ap in self._cnf.SUPPORTED_PLAYERS:
                if ap not in parts:
                    self._players.append([ap, False, True])

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('all players parameters = {}'.format(self._players))

    def refresh_win(self, do_params=False):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        if self.editing == 0:
            self._win.addstr(
                0, int((self.maxX - len(self._title)) / 2),
                self._title,
                curses.color_pair(11))
            self._win.addstr(1, 2, 'Supported Players', curses.color_pair(11))
            self._win.addstr(1, self.mlength + 11, 'Extra Player Parameters', curses.color_pair(11))
            #self._win.addstr(1, int(self.maxX / 2 + 2), 'Active' , curses.color_pair(11))
            self.refresh_selection()
            if do_params:
                self._extra.set_player(self.selected_player_name())
        else:
            if self.editing == 1:
                title = ' Add player paremeter '
            else:
                title = ' Edit player paremeter '
            self._win.addstr(
                0, int((self.maxX - len(title)) / 2),
                title, curses.color_pair(11))
            self._win.refresh()
            self._parameter_editor.show()

    def refresh_selection(self):
        for i in range(0, len(self._players)):
            token = self._char if self._players[i][1] else ' [ ] '
            first_char = last_char = ' '
            if self.focus:
                if self.selection == i:
                    col = curses.color_pair(6)
                else:
                    col = curses.color_pair(10)
            else:
                col = curses.color_pair(10)
                if self.selection == i:
                    col = curses.color_pair(11)
                    '''
                        first_char = '>'
                        last_char = '<'
                    '''
            pad = self.mlength - (len(token) + len(self._players[i][0])) + 3
            self._win.addstr(
                i+2, 1,
                first_char + token + self._players[i][0] +
                pad * ' ' + last_char,
                col
            )
            # self._win.hline(i+2, 1, ' ', self.maxX - 2, curses.color_pair(10))
        self._win.refresh()
        return

        if self._working_players[0]:
            if self.selection[0] >= len(self._working_players[0]):
                self.selection[0] = 0

    def refresh_and_resize(self, maxY, maxX):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.init_window()
        self._extra.set_window(self._win)
        if self._parameter_editor:
            self._parameter_editor.resize(self._win)
        self.refresh_win(True)

    def reset(self):
        self._extra.reset(from_reset=True)
        self._populate_players()
        self.refresh_win(do_params=True)
        self._cnf.params_changed = False

    def keypress(self, char):
        ''' Player selection keypress
            Returns:
              -2 - error, number of max lines reached
              -3 - error, cannot edit or delete first item
              -1 - Continue
               0 - Accept changes
               1 - Cancel
               2 - Display editor help
               3 - Editor is visible
               4 - Editor exited
        '''
        if self.editing == 0:
            ''' focus on players '''
            if char in self._global_functions.keys():
                self._global_functions[char]()
            elif char in (9, ):
                if self.from_config  and self._players[self.selection][1]:
                    self._switch_column()

            elif char in (
                curses.KEY_EXIT, 27,
                ord('q'), curses.KEY_LEFT,
                ord('h')
            ):
                self._win.nodelay(True)
                char = self._win.getch()
                self._win.nodelay(False)
                if char == -1:
                    ''' ESCAPE '''
                    return 1

            elif char == ord('r'):
                self.reset()

            elif char == ord('s'):
                working_players = []
                for a_player in self._players:
                    if a_player[1]:
                        working_players.append(a_player[0])

                if working_players:
                    self.player = ','.join(working_players)
                else:
                    self.player = ','.join(self._cnf.SUPPORTED_PLAYERS)
                self._extra.save_results()
                return 0

            if self.focus:
                ''' focus on players '''
                if char in (
                    curses.KEY_ENTER, ord('\n'), ord('\r'),
                    ord(' '), ord('l'), curses.KEY_RIGHT
                ):
                    self._players[self.selection][1] = not self._players[self.selection][1]
                    self.refresh_selection()

                elif char in (curses.ascii.NAK, 21):
                    ''' ^U, move player Up '''
                    x = self._players.pop(self.selection)
                    if self.selection == 0:
                        self._players.append(x)
                        self.selection = len(self._players) - 1
                    else:
                        self.selection -= 1
                        self._players.insert(self.selection, x)
                    self.refresh_selection()

                elif char in (curses.ascii.EOT, 4):
                    ''' ^D, move player Down '''
                    if self.selection == len(self._players) - 1:
                        x = self._players.pop(self.selection)
                        self._players.insert(0, x)
                        self.selection = 0
                    else:
                        x = self._players.pop(self.selection)
                        self.selection += 1
                        self._players.insert(self.selection, x)
                    self.refresh_selection()

                elif char in (curses.KEY_UP, ord('k')):
                    self.selection -= 1
                    if self.selection < 0:
                        self.selection = len(self._players) - 1
                    self.refresh_selection()
                    self._extra.set_player(self.selected_player_name(), True)

                elif char in (curses.KEY_DOWN, ord('j')):
                    self.selection += 1
                    if self.selection == len(self._players):
                        self.selection = 0
                    self.refresh_selection()
                    self._extra.set_player(self.selected_player_name(), True)

            else:
                ''' focus on parameters '''
                ret = self._extra.keypress(char)
                if ret == 2:
                    ''' error, number of max lines reached '''
                    return -2
                elif ret == 3:
                    ''' error, cannot edit or delete first item '''
                    return -3
                elif ret == 4:
                    ''' edit parameter '''
                    self.editing = 2
                    self._parameter_editor = ExtraParametersEditor(
                        self._win,
                        self._cnf,
                        string=self._extra._items[self._extra.selection],
                        global_functions=self._global_functions
                    )
                    self.refresh_win()
                    return 3
                elif ret == 5:
                    ''' add parameter '''
                    self._parameter_editor = ExtraParametersEditor(
                        self._win,
                        self._cnf,
                        global_functions=self._global_functions
                    )
                    self.editing = 1
                    self.refresh_win()
                    return 3

        else:
            ''' return from parameter editor
                adding or editing a parameter
            '''
            ret = self._parameter_editor.keypress(char)
            if ret == 0:
                ''' accept parameter or cancel '''
                if self._parameter_editor.edit_string:
                    if self.editing == 1:
                        ''' add parameter  '''
                        self._extra.add_item(self._parameter_editor.edit_string, select=True)
                        # self._extra._items.append(self._parameter_editor.edit_string)
                        # self._extra.selection = len(self._extra._items) - 1
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('New parameter: ' + self._extra._items[-1])
                    else:
                        ''' change parameter '''
                        self._extra.edit_item(self._extra.selection, self._parameter_editor.edit_string)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug('New parameter value: ' + self._parameter_editor.edit_string)

                self.editing = 0
                self.refresh_win(True)
                self._parameter_editor = None
                return 4
            elif ret == 2:
                ''' show editor help '''
                return ret

        return -1

    def _switch_column(self):
        self.focus = not self.focus
        self._extra.focused = not self.focus
        self.refresh_selection()
        self._extra.refresh_win()

    def setPlayers(self, these_players):
        self.player = these_players
        self._players = []
        self._populate_players()


class PyRadioSelectEncodings(object):
    max_enc_len = 15

    _win = None

    _title = ' Encoding Selection '

    _num_of_columns = 4
    maxY = maxX = 10
    _column = _row = 0

    _encodings = []
    list_maxY = 0
    startPos = 0
    selection = 0

    _invalid = []

    def __init__(self, maxY, maxX, encoding, config_encoding,
                 global_functions=None):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.encoding = encoding
        self._orig_encoding = encoding
        self._config_encoding = config_encoding
        self._orig_encoding = encoding
        self._encodings = get_encodings()
        self._num_of_rows = int(len(self._encodings) / self._num_of_columns)
        self.init_window()

    def set_global_functions(self, global_functions):
        self._global_functions = global_functions

    def set_reduced_global_functions(self, global_functions):
        self._global_functions = set_global_functions(global_functions)

    def init_window(self, set_encoding=True):
        self._win = None
        self._win = curses.newwin(
            self.maxY, self.maxX,
            int((self._parent_maxY - self.maxY) / 2) + 1,
            int((self._parent_maxX - self.maxX) / 2))
        if set_encoding:
            self.setEncoding(self.encoding, init=True)

    def _fix_geometry(self):
        self._num_of_columns = int((self._parent_maxX - 2) / (self.max_enc_len + 2))
        if self._num_of_columns > 8:
            self._num_of_columns = 8
        elif self._num_of_columns > 4:
            self._num_of_columns = 4

        self.maxY = int(len(self._encodings) / self._num_of_columns) + 5
        if len(self._encodings) % self._num_of_columns > 0:
            self.maxY += 1
        if self._num_of_columns == 8:
            maxY = int(len(self._encodings) / 6) + 5
            if len(self._encodings) % 6 > 0:
                maxY += 1
            if maxY < self._parent_maxY:
                self.maxY = maxY
                self._num_of_columns = 6
        while self.maxY > self._parent_maxY - 2:
            self.maxY -= 1
        self.list_maxY = self.maxY - 5
        self.maxX = self._num_of_columns * (self.max_enc_len + 2) + 2
        ''' Enable this to see geometry '''
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('maxY,maxX = {0},{1}'.format(self.maxY, self.maxX))
        #    logger.debug('Number of columns = {}'.format(self._num_of_columns))
        #    logger.debug('Number of rows = {}'.format(self._num_of_rows))
        #    logger.debug('Number of visible rows = {}'.format(self.list_maxY))

    def refresh_win(self, set_encoding=True):
        ''' set_encoding is False when resizing '''
        self._fix_geometry()
        self.init_window(set_encoding)
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self._title)) / 2),
            self._title,
            curses.color_pair(11))
        for i in range(1, self.maxX - 1):
            try:
                self._win.addch(self.maxY - 4,  i, '─', curses.color_pair(3))
            except:
                self._win.addstr(self.maxY - 4, i, u'─'.encode('utf-8'), curses.color_pair(3))
        try:
            self._win.addch(self.maxY - 4, 0, '├', curses.color_pair(3))
            self._win.addch(self.maxY - 4, self.maxX - 1, '┤', curses.color_pair(3))
        except:
            self._win.addstr(self.maxY - 4,  0, u'├'.encode('utf-8'), curses.color_pair(3))
            self._win.addstr(self.maxY - 4,  self.maxX - 1, u'┤'.encode('utf-8'), curses.color_pair(3))

        self._num_of_rows = int(len(self._encodings) / self._num_of_columns)
        self._get_invalids()
        self.refresh_selection()

    def refresh_selection(self):
        if self._parent_maxX < 4 * (self.max_enc_len + 2) + 2 or self.maxY < 10:
            self._too_small = True
        else:
            self._too_small = False
        if self._too_small:
            msg = 'Window too small to display content!'
            if self.maxX - 2 < len(msg):
                msg = 'Window too small!'
            self._win.hline(self.maxY - 4, 1, ' ', self.maxX - 2, curses.color_pair(10))
            try:
                self._win.addch(self.maxY - 4, 0, '│', curses.color_pair(3))
                self._win.addch(self.maxY - 4, self.maxX - 1, '│', curses.color_pair(3))
            except:
                self._win.addstr(self.maxY - 4,  0, u'│'.encode('utf-8'), curses.color_pair(3))
                self._win.addstr(self.maxY - 4,  self.maxX - 1, u'│'.encode('utf-8'), curses.color_pair(3))
            self._win.addstr(
                int(self.maxY / 2),
                int((self.maxX - len(msg)) / 2),
                msg, curses.color_pair(10))

        else:
            self._win.hline(self.maxY - 3, 1, ' ', self.maxX - 2, curses.color_pair(10))
            self._win.hline(self.maxY - 2, 1, ' ', self.maxX - 2, curses.color_pair(10))

            self._set_startPos()
            for i in range(0, self._num_of_columns):
                for y in range(0, self.list_maxY):
                    xx = i * self.max_enc_len + 2 + i * 2
                    yy = y + 1
                    pos = self.startPos + i * self._num_of_rows + y
                    if i > 0:
                        pos += i
                    if pos == self.selection:
                        if self._encodings[self.selection][0] == self._orig_encoding:
                            col = curses.color_pair(9)
                        else:
                            col = curses.color_pair(6)
                        self._win.addstr(self.maxY - 3, 1, ' ' * (self.maxX - 2), curses.color_pair(11))
                        self._win.addstr(self.maxY - 3, 2, '   Alias: ', curses.color_pair(11))
                        self._win.addstr(self._encodings[pos][1][:self.maxX - 14], curses.color_pair(10))
                        self._win.addstr(self.maxY - 2, 1, ' ' * (self.maxX - 2), curses.color_pair(11))
                        self._win.addstr(self.maxY - 2, 2, 'Language: ', curses.color_pair(11))
                        self._win.addstr(self._encodings[pos][2][:self.maxX - 14], curses.color_pair(10))
                    else:
                        col = curses.color_pair(10)
                        if pos < len(self._encodings):
                            if self._encodings[pos][0] == self._orig_encoding:
                                col = curses.color_pair(11)
                    self._win.addstr(yy, xx - 1,
                                     ' ' * (self.max_enc_len + 2),
                                     col)
                    if pos < len(self._encodings):
                        self._win.addstr(yy, xx, self._encodings[pos][0], col)

        self._win.refresh()

    def refresh_and_resize(self, maxY, maxX):
        self._parent_maxY = maxY
        self._parent_maxX = maxX
        self.refresh_win(set_encoding=False)
        self._resize()

    def _get_invalids(self):
        self._invalid = []
        col = self._num_of_columns - 1
        row = self._num_of_rows
        b = self._col_row_to_selection(col, row)
        while b >= len(self._encodings):
            self._invalid.append((col, row))
            row -= 1
            b = self._col_row_to_selection(col, row)

    def _set_startPos(self):
        try:
            if self.list_maxY == self._num_of_rows + 1:
                self.startPos = 0
        except:
            pass
        if self.startPos < 0:
            self.startPos = 0

    def _resize(self, init=False):
        col, row = self._selection_to_col_row(self.selection)
        if not (self.startPos <= row <= self.startPos + self.list_maxY - 1):
            while row > self.startPos:
                self.startPos += 1
            while row < self.startPos + self.list_maxY - 1:
                self.startPos -= 1
        ''' if the selection at the end of the list,
            try to scroll down '''
        if init and row > self.list_maxY:
            new_startPos = self._num_of_rows - self.list_maxY + 1
            if row > new_startPos:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('setting startPos at {}'.format(new_startPos))
                self.startPos = new_startPos
        self.refresh_selection()

    def setEncoding(self, this_encoding, init=False):
        ret = self._is_encoding(this_encoding)
        if ret == -1:
            if logger.isEnabledFor(logging.ERROR):
                logger.error('encoding "{}" not found, reverting to "utf-8"'.format(this_encoding))
            self.encoding = 'utf-8'
            self.selection = self._is_encoding(self.encoding)
        else:
            self.selection = ret
            self.encoding = this_encoding
        self._resize(init)

    def _is_encoding(self, a_string):
        def in_alias(a_list, a_string):
            splited = a_list.split(',')
            for n in splited:
                if n.strip() == a_string:
                    return True
            return False
        for i, an_encoding in enumerate(self._encodings):
            if a_string == an_encoding[0] or in_alias(an_encoding[1], a_string):
                return i
        return -1

    def _fix_startPos(self, direction=1):
        col, row = self._selection_to_col_row(self.selection)
        startRow = self.startPos
        endRow = self.startPos + self.list_maxY - 1
        if not (startRow <= row <= endRow):
            self.startPos = self.startPos + direction
            if direction > 0:
                #if self.startPos >= self.list_maxY or row == 0:
                if row == 0:
                    self.startPos = 0
                else:
                    self._resize()
            elif direction < 0:
                if row == self._num_of_rows - 2 or row == self._num_of_rows:
                    self.startPos = self._num_of_rows - self.list_maxY + 1
                elif self.startPos < 0:
                    self._resize(init=True)
            if self.startPos < 0:
                self.startPos = 0

    def _selection_to_col_row(self, sel):
        x = int(sel / (self._num_of_rows+1))
        y = sel % (self._num_of_rows + 1)
        return x, y

    def _col_row_to_selection(self, a_column, a_row):
        return (self._num_of_rows + 1) * a_column + a_row

    def keypress(self, char):
        ''' Encoding key press
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()

        elif char in (ord('c'), ):
            self.encoding = self._config_encoding
            self.setEncoding(self.encoding, init=True)

        elif char in (ord('r'), ):
            self.encoding = self._orig_encoding
            self.setEncoding(self.encoding, init=True)

        elif char in (curses.KEY_UP, ord('k')):
            self.selection -= 1
            if self.selection < 0:
                self.selection = len(self._encodings) - 1
            self._fix_startPos(-1)
            self.refresh_selection()

        elif char in (curses.KEY_DOWN, ord('j')):
            self.selection += 1
            if self.selection == len(self._encodings):
                self.selection = 0
            self._fix_startPos(1)
            self.refresh_selection()

        elif char in (curses.KEY_RIGHT, ord('l')):
            self._column, self._row = self._selection_to_col_row(self.selection)
            self._column += 1
            if self._column == self._num_of_columns:
                self._column = 0
                self._row += 1
                if self._row == self._num_of_rows:
                    self._row = 0
            if (self._column, self._row) in self._invalid:
                self._column = 0
                self._row += 1
                if self._row > self._num_of_rows:
                    self._row = 0
            self.selection = self._col_row_to_selection(self._column, self._row)
            self._fix_startPos(1)
            self.refresh_selection()

        elif char in (curses.KEY_LEFT, ord('h')):
            self._column, self._row = self._selection_to_col_row(self.selection)
            self._column -= 1
            if self._column == -1:
                self._column = self._num_of_columns - 1
                self._row -= 1
            if (self._column, self._row) in self._invalid:
                self._column -= 1
            self.selection = self._col_row_to_selection(self._column, self._row)
            self._fix_startPos(-1)
            self.refresh_selection()

        elif char in (curses.KEY_NPAGE, ):
            if self.selection == len(self._encodings) - 1:
                self.selection = 0
            else:
                self.selection += 5
                if self.selection > len(self._encodings) - 1:
                    self.selection = len(self._encodings) - 1
            self._fix_startPos(5)
            self.refresh_selection()

        elif char in (curses.KEY_PPAGE, ):
            if self.selection == 0:
                self.selection = len(self._encodings) - 1
            else:
                self.selection -= 5
                if self.selection < 0:
                    self.selection = 0
            self._fix_startPos(-5)
            self.refresh_selection()

        elif char in (curses.KEY_HOME, ord('g')):
            self.selection = 0
            self.startPos = 0
            self.refresh_selection()

        elif char in (curses.KEY_END, ord('G')):
            self.selection = len(self._encodings) - 1
            self.startPos = self._num_of_rows - self.list_maxY + 1
            self.refresh_selection()

        elif char in (curses.KEY_EXIT, 27,
                      ord('q'), curses.KEY_LEFT,
                      ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
                return 1, ''

        elif char in (curses.KEY_ENTER, ord('\n'),
                      ord('\r'), ord(' '), ord('s')):
            return 0, self._encodings[self.selection][0]

        return -1, ''


class PyRadioSelectPlaylist(object):
    _win = None

    _title = ' Playlist Selection '

    maxY = maxX = _parent_maxY = _parent_maxX = 0

    _items = []
    _registers_path = None

    startPos = 0
    selection = 0
    _selected_playlist_id = 0

    _select_playlist_error = -2

    pageChange = 5
    jumpnr = ''

    ''' offset to current item for padding calculation '''
    pad_adjustment = 0

    def __init__(self,
                 parent,
                 config_path,
                 default_playlist,
                 include_registers=False,
                 global_functions=None):
        ''' Select a playlist from a list

        include_registers changes its behavior

        If it is False (default), it is used by config window
        and permit playlist only selection.
        Returns: state, playlist title

        if it is True, it is used in \\p (paste) function and
        permits playlist and register selection.
        default_playlist is removed from the list.
        Returns: state, playlist/register path
        '''
        self._parent_maxY, self._parent_maxX = parent.getmaxyx()
        try:
            self._parent_Y, _ = parent.getbegyx()
        except:
            ''' revert to old behavior '''
            self._parent_Y = 1
        self._config_path = config_path
        self.playlist = default_playlist
        self._orig_playlist = default_playlist
        self._selected_playlist = default_playlist
        self._include_registers = include_registers
        #self._include_registers = True
        if self._include_registers:
            self._title = ' Paste: Select target '
            self._playlist_in_editor = self._selected_playlist
        self._global_functions = set_global_functions(global_functions)
        self.init_window()

    def __del__(self):
        self._error_win = None
        self._items = None

    def init_window(self, read_items=True):
        if read_items:
            self._read_items()
        self.maxY = self._num_of_items + 2
        if self.maxY > self._parent_maxY - 2:
            self.maxY = self._parent_maxY - 2
        self._calculate_width()
        self._win = None
        Y = int((self._parent_maxY - self.maxY) / 2) + self._parent_Y
        X = int((self._parent_maxX - self.maxX) / 2)
        self._win = curses.newwin(self.maxY, self.maxX, Y, X)

    def refresh_and_resize(self, parent_maxYX):
        self._parent_maxY = parent_maxYX[0]
        self._parent_maxX = parent_maxYX[1]
        self.init_window()
        self.refresh_win(resizing=True)

    def _calculate_width(self):
        self.maxX = self._max_len + 5 + len(str(self._num_of_items))
        max_title = len(self._title) + 8
        if self.maxX < max_title:
            self.maxX = max_title
        if self.maxX > self._parent_maxX - 4:
            self.maxX = self._parent_maxX - 4

    def refresh_win(self, resizing=False):
        self._win.bkgdset(' ', curses.color_pair(3))
        self._win.erase()
        self._win.box()
        self._win.addstr(
            0, int((self.maxX - len(self._title)) / 2),
            self._title,
            curses.color_pair(11)
        )
        if resizing:
            self._resize()
        self.refresh_selection(resizing)

    def refresh_selection(self, resizing=False):
        pad = len(str(self.startPos + self.maxY - 2 - self.pad_adjustment))
        # logger.error('DE \n\npos = {0}, pad = {1}\n\n'.format(self.startPos + self.maxY - 2 - self.pad_adjustment, pad))
        for i in range(0, self.maxY - 2):
            # logger.error('DE i = {0}, startPos = {1}'.format(i, self.startPos))
            if i + self.startPos < self._num_of_items:
                line, pad = self._format_line(i, pad)
                colour = self._get_color(i)
                self._win.hline(i + 1, 1, ' ', self.maxX - 2, colour)
                self._win.addstr(i + 1, 1, line[:self.maxX - 3], colour)
            else:
                break
        self._win.refresh()
        if not resizing:
            if self._select_playlist_error > -2:
                self.print_select_playlist_error()

    def _resize(self):
        if self.maxY - 2 == self._num_of_items:
            self.startPos = 0
        else:
            self._fix_startPos()

    def _get_color(self, i):
        col = curses.color_pair(10)
        if self._items[i + self.startPos] == self._orig_playlist:
            if i + self.startPos == self._selected_playlist_id:
                col = curses.color_pair(9)
            else:
                col = curses.color_pair(11)
        elif i + self.startPos == self._selected_playlist_id:
            col = curses.color_pair(6)
        return col

    def _format_line(self, i, pad):
        ''' PyRadioSelectPlaylist format line '''
        line = '{0}. {1}'.format(
            str(i + self.startPos + 1).rjust(pad),
            self._items[i + self.startPos]
        )
        return line, pad

    def _read_items(self):
        self._items = []
        self._items = glob.glob(path.join(self._config_path, '*.csv'))
        if len(self._items) > 0:
            self._items.sort()
        if self._include_registers:
            self._registers_path = path.join(self._config_path, '.registers')
            if platform == 'win32':
                self._registers_path.replace('.reg', '_reg')
            r_items = glob.glob(path.join(self._registers_path, '*.csv'))
            if r_items:
                r_items.sort()
                self._items.extend(r_items)
        if len(self._items) == 0:
            return 0, -1
        for i, an_item in enumerate(self._items):
            if self._include_registers:
                self._items[i] = an_item.replace(self._registers_path + sep, '').replace('.csv', '').replace('register_', 'Register: ')
                self._items[i] = self._items[i].replace(self._config_path + sep, '')
            else:
                self._items[i] = an_item.replace(self._config_path + sep, '').replace('.csv', '')
        if self._include_registers:
            ''' Remove playlist in editor '''
            try:
                self._items.remove(self._playlist_in_editor)
            except ValueError:
                pass
        else:
            ''' get already loaded playlist id '''
            for i, a_playlist in enumerate(self._items):
                if a_playlist ==self._selected_playlist:
                    self._selected_playlist_id = i
                    break
        self._max_len = cjklen(max(self._items, key=cjklen))
        self._num_of_items = len(self._items)

    def setPlaylist(self, a_playlist, adjust=True):
        self._selected_playlist = a_playlist
        if a_playlist == 'False':
            self._selected_playlist_id = 0
        elif a_playlist == 'random' or \
            a_playlist == 'Random' or \
                a_playlist is None:
            self._selected_playlist_id = 1
        for i, a_playlist in enumerate(self._items):
            if a_playlist == self._selected_playlist:
                self._selected_playlist_id = i
                break
        else:
            self.setPlaylistById(0, adjust)
            self.startPos = 0
            self._selected_playlist = self._items[self._selected_playlist_id]
            return
        if adjust:
            self._fix_startPos()
        self.refresh_selection()

    def setPlaylistById(self, an_id, adjust=True):
        self._selected_playlist_id = an_id
        if self._selected_playlist_id == self._num_of_items:
            self._selected_playlist_id = 0
        elif self._selected_playlist_id < 0:
            self._selected_playlist_id = self._num_of_items - 1
            #self._selected_playlist = self._items[self._selected_playlist_id]
        if adjust:
            self._fix_startPos()
        self._selected_playlist = self._items[self._selected_playlist_id]
        self.refresh_selection()

    def _get_result(self):
        if self._include_registers:
            if self._items[self._selected_playlist_id].startswith('Register: '):
                ret = self._items[self._selected_playlist_id].replace('Register: ', 'register_')
                ret = path.join(self._config_path, '.registers', ret + '.csv')
            else:
                ret = path.join(self._config_path, self._items[self._selected_playlist_id] + '.csv')
            if platform == 'win32':
                ret.replace('.registers', '_registers')
            return 0, ret

        stationFile = path.join(self._config_path, self._items[self._selected_playlist_id] + '.csv')
        self._select_playlist_error = 0
        with open(stationFile, 'r', encoding='utf-8') as cfgfile:
            try:
                for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
                    if not row:
                        continue
                    try:
                        name, url = [s.strip() for s in row]
                        self._select_playlist_error = 1
                    except ValueError:
                        try:
                            name, url, enc = [s.strip() for s in row]
                            self._select_playlist_error = 1
                        except ValueError:
                            try:
                                name, url, enc, br = [s.strip() for s in row]
                                self._select_playlist_error = 1
                            except ValueError:
                                self._select_playlist_error = -1
                                break
            except:
                self._select_playlist_error = -1
        if self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            self.print_select_playlist_error()
            return -1, ''
        else:
            return 0, self._items[self._selected_playlist_id]

    def print_select_playlist_error(self):
        if self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            if self._select_playlist_error == 0:
                msg = 'This playlist is empty!'
            else:
                msg = 'This playlist is corrupt!'
            self._error_win = curses.newwin(
                5, 38,
                int((self._parent_maxY - 5) / 2) + 1,
                int((self._parent_maxX - 38) / 2))
            self._error_win.bkgdset(' ', curses.color_pair(12))
            self._error_win.erase()
            self._error_win.box()
            self._error_win.addstr(0, 16, ' Error ', curses.color_pair(11))
            self._error_win.addstr(1, 2, msg, curses.color_pair(10))
            self._error_win.addstr(2, 2, 'Please select another playlist...', curses.color_pair(10))
            self._error_win.addstr(4, 14, ' Press any key to hide ', curses.color_pair(12))
            self._error_win.refresh()

    def _fix_startPos(self):
        if self._num_of_items < self.maxY - 2:
            self.startPos = 0
            return
        if self._selected_playlist_id < self.maxY - 2:
            if self._selected_playlist_id < 0:
                self._selected_playlist_id = 0
            self.startPos = 0
        elif self._selected_playlist_id >= self._num_of_items:
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
        elif self._selected_playlist_id > self._num_of_items - self.maxY + 2:
            self.startPos = self._num_of_items - self.maxY + 2
        else:
            self.startPos = self._selected_playlist_id - int((self.maxY - 2) / 2)

    def keypress(self, char):
        ''' Return restlt from playlist selection window

        Results are:
        -1, ''              - Continue in window
         0, station title   - selected station title (for config window)
         0, station path    - selected station path (for paste window)
         1, ''              - Cancel
        '''
        if char in self._global_functions.keys():
            self._global_functions[char]()

        elif self._select_playlist_error == -1 or \
                self._select_playlist_error == 0:
            self._error_win = None
            self._select_playlist_error = -2
            self.refresh_selection()

        elif char == ord('M'):
            if self._num_of_items > 0:
                self.setPlaylistById(int(self._num_of_items / 2) - 1)
                #self._put_selection_in_the_middle(force=True)
                self.refresh_selection()

        elif char in (ord('r'), ):
            self.setPlaylist(self._orig_playlist)

        elif char in (curses.KEY_EXIT, 27, ord('q'), curses.KEY_LEFT, ord('h')):
            self._win.nodelay(True)
            char = self._win.getch()
            self._win.nodelay(False)
            if char == -1:
                ''' ESCAPE '''
                self._select_playlist_error = -2
                return 1, ''

        elif char in (curses.KEY_ENTER, ord('\n'),
                      ord('\r'), ord(' '), ord('l'),
                      curses.KEY_RIGHT):
            if type(self) is PyRadioSelectStation:
                if self._selected_playlist_id in self._groups_ids:
                    return -1, ''
            return self._get_result()

        elif char in (curses.KEY_DOWN, ord('j')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id + 1,
                                     adjust=False)
                if self._selected_playlist_id == 0:
                    self.startPos = 0
                elif self.startPos + self.maxY - 2 == self._selected_playlist_id:
                    self.startPos += 1
                self.refresh_selection()

        elif char in (curses.KEY_UP, ord('k')):
            self.jumpnr = ''
            if self._num_of_items > 0:
                self.setPlaylistById(self._selected_playlist_id - 1,
                                     adjust=False)
                if self._selected_playlist_id == self._num_of_items - 1:
                    self.startPos = self._num_of_items - self.maxY + 2
                    if self.startPos < 0:
                        self.startPos = 0
                elif self.startPos > self._selected_playlist_id:
                    self.startPos = self._selected_playlist_id
                self.refresh_selection()

        elif char in (curses.KEY_PPAGE, ):
            self.jumpnr = ''
            if self._num_of_items > 0:
                old_id = self._selected_playlist_id
                self._selected_playlist_id -= self.pageChange
                if old_id == 0:
                    self._selected_playlist_id = self._num_of_items - 1
                    self.startPos = self._num_of_items - self.maxY + 2
                elif self._selected_playlist_id < 0:
                    self._selected_playlist_id = 0
                    self.startPos = 0
                else:
                    if not (self.startPos < self._selected_playlist_id < self.startPos + self.maxY - 2):
                        self.startPos = old_id - self.pageChange
                        if self.startPos > self._num_of_items - self.maxY + 2:
                            self.startPos = self._num_of_items - self.maxY + 2
                self.refresh_selection()

        elif char in (curses.KEY_NPAGE, ):
            self.jumpnr = ''
            old_id = self._selected_playlist_id
            self._selected_playlist_id += self.pageChange
            if old_id == self._num_of_items - 1:
                self._selected_playlist_id = 0
                self.startPos = 0
            elif self._selected_playlist_id >= self._num_of_items:
                self._selected_playlist_id = self._num_of_items - 1
                self.startPos = self._num_of_items - self.maxY + 2
            else:
                if not (self.startPos < self._selected_playlist_id < self.startPos + self.maxY - 2):
                    self.startPos = old_id + self.pageChange
                    if self.startPos > self._num_of_items - self.maxY + 2:
                        self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in (curses.KEY_HOME, ord('g')):
            self.jumpnr = ''
            self._selected_playlist_id = 0
            self.startPos = 0
            self.refresh_selection()

        elif char in (curses.KEY_END, ):
            self.jumpnr = ''
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in (ord('G'), ):
            if self.jumpnr:
                try:
                    if type(self) is PyRadioSelectStation:
                        jump = int(self.jumpnr) + 1
                    else:
                        jump = int(self.jumpnr) - 1
                    self.setPlaylistById(jump)
                    self.jumpnr = ''
                    return -1, ''
                except:
                    pass
            self._selected_playlist_id = self._num_of_items - 1
            self.startPos = self._num_of_items - self.maxY + 2
            self.refresh_selection()

        elif char in map(ord, map(str, range(0, 10))):
            if self._num_of_items > 0:
                self.jumpnr += chr(char)
        else:
            self.jumpnr = ""

        return -1, ''


class PyRadioSelectStation(PyRadioSelectPlaylist):

    _default_playlist = ''

    def __init__(self, parent, config_path, default_playlist, default_station,
                 global_functions=None, is_from_schedule=False):
        self._default_playlist = default_playlist
        self._orig_default_playlist = default_playlist
        if logger.isEnabledFor(logging.INFO):
            logger.info('displaying stations from: "{}"'.format(default_playlist))
        # if self._is_from_schedule is True, we need to read the playlist here
        # so that default_station goes from str -> int (index)
        self._is_from_schedule = is_from_schedule
        if self._is_from_schedule:
            self._config_path = config_path
            default_station = self._read_items(a_station=default_station)
        PyRadioSelectPlaylist.__init__(self, parent, config_path, default_station)
        self._global_functions = set_global_functions(global_functions)
        self._title = ' Station Selection '
        ''' adding 2 to padding calculation
            (i.e. no selection and random selection
        '''
        self.pad_adjustment = 2

    def update_playlist_and_station(self, a_playlist, a_station):
        #if logger.isEnabledFor(logging.DEBUG):
        #    logger.debug('default_playlist = {0}\norig_playlist = {1}\nselected_playlist = {2}\nplaylist = {3}'.format(self._default_playlist, self._orig_playlist, self._selected_playlist, self.playlist))
        self._default_playlist = a_playlist
        self._orig_playlist = a_station
        self._selected_playlist = a_station
        self.playlist = a_station
        self._read_items()

    def setStation(self, a_station):
        if a_station == 'False':
            self._selected_playlist_id = 0
            self.startPos = 0
            self.refresh_selection()
        elif a_station == 'random' or a_station == 'Random' or a_station is None:
            self._selected_playlist_id = 1
            self.startPos = 0
            self.refresh_selection()
        else:
            try:
                pl = int(a_station) + 1
                self.setPlaylistById(pl)
                return
            except:
                self.setPlaylist(a_station)

    def _get_result(self):
        if not self._is_from_schedule:
            if self._selected_playlist_id == 0:
                return 0, 'False'
            elif self._selected_playlist_id == 1:
                return 0, 'Random'
            else:
                return 0, str(self._selected_playlist_id - 1)
        return 0, self._items[self._selected_playlist_id]

    def _read_items(self, a_station=None):
        self._items = []
        self._groups_ids = []
        stationFile = path.join(self._config_path, self._default_playlist + '.csv')
        if path.exists(stationFile):
            with open(stationFile, 'r', encoding='utf-8') as cfgfile:
                try:
                    for row in csv.reader(filter(lambda row: row[0] != '#', cfgfile), skipinitialspace=True):
                        if not row:
                            continue
                        try:
                            name, url = [s.strip() for s in row]
                        except ValueError:
                            try:
                                name, url, _ = [s.strip() for s in row]
                            except ValueError:
                                name, url, _, _ = [s.strip() for s in row]
                        self._items.append(name)
                        if url == '-':
                            self._groups_ids.append(name)
                except:
                    pass
            if self._groups_ids:
                for i, n in enumerate(self._groups_ids):
                    self._groups_ids[i] = self._items.index(n)
                    if not self._is_from_schedule:
                        self._groups_ids[i] += 2
            if not self._is_from_schedule:
                self._items.reverse()
        index = 0
        if self._is_from_schedule:
            if a_station:
                try:
                    index = self._items.index(a_station)
                except IndexError:
                    pass
        else:
            self._items.append('Play a Random station on startup')
            self._items.append('Do not play a station on startup')
            self._items.reverse()
        self._num_of_items = len(self._items)
        self._max_len = cjklen(max(self._items, key=cjklen))
        return index

    def _get_color(self, i):
        or_pl = self._orig_playlist
        if self._orig_playlist == 'False':
            or_pl = -1
        elif self._orig_playlist == 'random' or \
                self._orig_playlist == 'Random' or \
                self._orig_playlist is None:
            or_pl = 0
        if i in self._groups_ids:
            col = curses.color_pair(3)
        else:
            col = curses.color_pair(10)
        displ = 0 if self._is_from_schedule else 1
        if i + self.startPos == int(or_pl) + displ:
            if i + self.startPos == self._selected_playlist_id:
                col = curses.color_pair(9)
            else:
                col = curses.color_pair(11)
        elif i + self.startPos == self._selected_playlist_id:
            if i in self._groups_ids:
                col = curses.color_pair(9)
            else:
                col = curses.color_pair(6)
        return col

    def _format_line(self, i, pad):
        ''' PyRadioSelectStation format line '''
        fixed_pad = pad
        if self._is_from_schedule:
            if i + self.startPos in self._groups_ids:
                line = self._format_group_line(i,fixed_pad)
            else:
                line = '{0}. {1}'.format(str(i + self.startPos + 1).rjust(fixed_pad),
                        self._items[i + self.startPos])
        else:
            if i + self.startPos < 2:
                line = '{0}  {1}'.format(' '.rjust(fixed_pad),
                    self._items[i + self.startPos])
            else:
                if i + self.startPos in self._groups_ids:
                    line = self._format_group_line(i,fixed_pad)
                else:
                    line = '{0}. {1}'.format(str(i + self.startPos - 1).rjust(fixed_pad),
                            self._items[i + self.startPos])
        return line, pad

    def _format_group_line(self, i, pad):
        if self._is_from_schedule:
            pad_string = str(i + self.startPos + 1).rjust(pad)
        else:
            pad_string = str(i + self.startPos - 1).rjust(pad)
        length = self.maxX - 2 - len(pad_string) - 6
        pad_char = '_' if version_info.major == 2 else '─'
        return '{0}. {1}'.format(pad_string,
                (' ' + self._items[i + self.startPos] + ' ').center(length, pad_char) + 6 * pad_char
                                 )

    def keypress(self, char):
        if char in (ord('r'), ):
            self.setStation(self._orig_playlist)
            return -1, ''

        elif char in self._global_functions.keys():
            self._global_functions[char]()
            return -1, ''

        return PyRadioSelectPlaylist.keypress(self, char)

class PyRadioServerConfig(object):

    def __init__(self):
        pass

    def show(self):
        pass

    def keypress(self, char):
        pass

# pymode:lint_ignore=W901
