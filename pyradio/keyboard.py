# -*- coding: utf-8 -*-
import curses
import curses.ascii
import platform
from collections import OrderedDict
import json
import logging
import locale
import string
from os.path import join
locale.setlocale(locale.LC_ALL, '')    # set your locale
try:
    from .cjkwrap import is_wide
except ImportError:
    pass
# from .simple_curses_widgets import SimpleCursesLineEdit

logger = logging.getLogger(__name__)

kb_letter = ''
kb_cjk = False

kbkey_orig = OrderedDict()
# ! MovementKeys
kbkey_orig['h_movement']               = ( None                   , 'Movement Keys')
kbkey_orig['j']                        = ( ord('j')               , 'Go down')
kbkey_orig['k']                        = ( ord('k')               , 'Go up')
kbkey_orig['h']                        = ( ord('h')               , 'Go left')
kbkey_orig['l']                        = ( ord('l')               , 'Go right')
kbkey_orig['g']                        = ( ord('g')               , 'Go to top of list')
kbkey_orig['G']                        = ( ord('G')               , 'Go to end of list')
kbkey_orig['screen_top']               = ( ord('H')               , 'Go to top of screen')
kbkey_orig['screen_middle']            = ( ord('M')               , 'Go to middle of screen')
kbkey_orig['screen_bottom']            = ( ord('L')               , 'Go to bottom of screen')

# ! Volume Keys')
kbkey_orig['h_volume']                 = ( None                   , 'Volume Keys')
kbkey_orig['v_up1']                    = ( ord('+')               , 'Volume up Key 1')                                # global
kbkey_orig['v_up2']                    = ( ord('.')               , 'Volume up Key 2')                                # global
kbkey_orig['v_up3']                    = ( ord('=')               , 'Volume up Key 3')                                # global
kbkey_orig['v_dn1']                    = ( ord(',')               , 'Volume down Key 1')                              # global
kbkey_orig['v_dn2']                    = ( ord('-')               , 'Volume down Key 2')                              # global
kbkey_orig['mute']                     = ( ord('m')               , 'Mute player')                                    # global
kbkey_orig['s_vol']                    = ( ord('v')               , 'Save volume')                                    # global

# ! Global / Multi Window Keys
kbkey_orig['h_global']                 = ( None                   , 'Global / Multi Window Keys')
kbkey_orig['?']                        = ( ord('?')               , 'Open help window')
kbkey_orig['s']                        = ( ord('s')               , 'Save, Accept, RadioBrowser search, etc.')
kbkey_orig['q']                        = ( ord('q')               , 'Exit or Cancel')
kbkey_orig['y']                        = ( ord('y')               , 'Answer Yes')
kbkey_orig['Y']                        = ( ord('Y')               , 'Answer Yes to All')
kbkey_orig['n']                        = ( ord('n')               , 'Answer No')
kbkey_orig['N']                        = ( ord('N')               , 'Answer No to All')
kbkey_orig['del']                      = ( ord('x')               , 'Delete an item')
kbkey_orig['paste']                    = ( ord('p')               , 'Paste')
kbkey_orig['t']                        = ( ord('t')               , 'Open themes window')
kbkey_orig['transp']                   = ( ord('T')               , 'Toggle transparency')                            # global
kbkey_orig['revert_saved']             = ( ord('r')               , 'Revert to saved values')
kbkey_orig['revert_def']               = ( ord('d')               , 'Revert to default values')
kbkey_orig['tab']                      = ( ord('L')               , 'Alternative Tab')
kbkey_orig['stab']                     = ( ord('H')               , 'Alternative Shift-Tab')
kbkey_orig['no_show']                  = ( ord('x')               , 'Do not show Info / Warning message again')
kbkey_orig['tag']                      = ( ord('w')               , 'Tag a title')                                    # global
kbkey_orig['t_tag']                    = ( ord('W')               , 'Toggle Titles Tagging')                          # global
kbkey_orig['next']                     = ( ord('n')               , 'Go to next item')
kbkey_orig['prev']                     = ( ord('p')               , 'Go to previous item')
kbkey_orig['no_buffer']                = ( ord('z')               , 'Buffering Window > Set to 0 (disable)')
kbkey_orig['repaint']                  = ( ord('#')               , 'Repaint screen')
kbkey_orig['info_rename']              = ( ord('r')               , 'Info Window > Rename station')
kbkey_orig['reload']                   = ( ord('r')               , 'Reload from disk')
kbkey_orig['watch_theme']              = ( ord('c')               , 'Themes Window > Watch theme for changes')

# ! Main Window keys
kbkey_orig['h_main']                   = ( None                   , 'Main Window keys')
kbkey_orig['open_config']              = ( ord('c')               , 'Open config window')
kbkey_orig['open_playlist']            = ( ord('o')               , 'Open playlists list')
kbkey_orig['open_online']              = ( ord('O')               , 'Open online services (Radio Browser)')
kbkey_orig['open_enc']                 = ( ord('E')               , 'Open encodings window')
kbkey_orig['extra_p_pamars']           = ( ord('Z')               , 'Open "Player Extra Parameters" window')
kbkey_orig['edit']                     = ( ord('e')               , 'Edit an item')
kbkey_orig['add']                      = ( ord('a')               , 'Add item (station, group, whatever)')
kbkey_orig['append']                   = ( ord('A')               , 'Append item (add to end of current list)')
kbkey_orig['gr']                       = ( curses.ascii.BEL       , 'Open groups window')                             # default: ^G
kbkey_orig['gr_next']                  = ( curses.ascii.EM        , 'Go to next group')                               # default: ^E
kbkey_orig['gr_prev']                  = ( curses.ascii.ENQ       , 'Go to previous group')                           # default: ^Y
kbkey_orig['open_regs']                = ( ord('\'')              , 'Open registers list')
kbkey_orig['open_extra']               = ( ord('\\')              , 'Open extra commands')
kbkey_orig['add_to_reg']               = ( ord('y')               , 'Add station to register')
kbkey_orig['info']                     = ( ord('i')               , 'Display station info')
kbkey_orig['fav']                      = ( ord('*')               , 'Add station to favorites')
kbkey_orig['https']                    = ( ord('z')               , 'Toggle force use https')
kbkey_orig['pause']                    = ( ord(' ')               , 'Stop playback (Pause if recording)')
kbkey_orig['random']                   = ( ord('r')               , 'Play random station')
kbkey_orig['p_next']                   = ( curses.ascii.SO        , 'Play next station')                              # default: ^N
kbkey_orig['p_prev']                   = ( curses.ascii.DLE       , 'Play next station')                              # default: ^P
kbkey_orig['Reload']                   = ( ord('R')               , 'Reload current playlist')
kbkey_orig['t_calc_col']               = ( ord('~')               , 'Toggle calculated colors')
kbkey_orig['rec']                      = ( ord('|')               , 'Toggle recording')
kbkey_orig['jump']                     = ( ord('J')               , 'Create a Jump tag')
kbkey_orig['goto_playing']             = ( ord('P')               , 'Go to playing station')
kbkey_orig['st_up']                    = ( curses.ascii.NAK       , 'Move station up')                                # default: ^U
kbkey_orig['st_dn']                    = ( curses.ascii.EOT       , 'Move station down')                              # default: ^D
kbkey_orig['hist_next']                = ( ord('>')               , 'Play next history item')
kbkey_orig['hist_prev']                = ( ord('<')               , 'Play previous history item')
kbkey_orig['ext_player']               = ( ord('X')               , 'Launch External Player')

# ! Search function
kbkey_orig['h_search']                 = ( None                   , 'Search function')
kbkey_orig['search']                   = ( ord('/')               , 'Open search subwindow')
kbkey_orig['search_next']              = ( ord('n')               , 'Search down')
kbkey_orig['search_prev']              = ( ord('N')               , 'Search up')



# ! Extra Commands Keys:)
kbkey_orig['h_extra']                  = ( None                   , 'Extra Commands Keys')
kbkey_orig['new_playlist']             = ( ord('n')               , 'Create a new playlist')
kbkey_orig['rename_playlist']          = ( ord('r')               , 'Rename current playlist')
kbkey_orig['open_remote_control']      = ( ord('s')               , 'Open "PyRadio Remote Control" window')
kbkey_orig['open_dirs']                = ( ord('o')               , 'Open dirs in file manager')
kbkey_orig['change_player']            = ( ord('m')               , 'Cahnge media player')
kbkey_orig['hist_top']                 = ( ord(']')               , 'Open first opened playlist')
kbkey_orig['buffer']                   = ( ord('b')               , 'Toggle buffering')
kbkey_orig['open_buffer']              = ( ord('B')               , 'Open buffering window')
kbkey_orig['last_playlist']            = ( ord('l')               , 'Toggle Open last playlist')
kbkey_orig['clear_reg']                = ( ord('c')               , 'Clear current register')
kbkey_orig['clear_all_reg']            = ( ord('C')               , 'Clear all registers')
kbkey_orig['unnamed']                  = ( ord('u')               , 'Show unnamed register')
kbkey_orig['html_help']                = ( ord('h')               , 'Open html help')


# ! RadioBrowser Keys:
kbkey_orig['h_rb']                     = ( None                   , 'RadioBrowser Keys')
kbkey_orig['rb_vote']                  = ( ord('V')               , 'Vote for station')
kbkey_orig['rb_info']                  = ( ord('I')               , 'Station DB info')
kbkey_orig['rb_server']                = ( ord('C')               , 'Select server to connect to')
kbkey_orig['rb_sort']                  = ( ord('S')               , 'Sort search results')
kbkey_orig['rb_p_first']               = ( ord('{')               , 'Go to first search results page')
kbkey_orig['rb_p_next']                = ( ord(']')               , 'Go to next search results page')
kbkey_orig['rb_p_prev']                = ( ord('[')               , 'Go to previous search results page')

# ! RadioBrowser Search Keys
kbkey_orig['h_rb_s']                   = ( None                   , 'RadioBrowser Search Window Keys')
kbkey_orig['rb_h_next']                = ( curses.ascii.SO        , 'Go to next item')                     # default: ^N
kbkey_orig['rb_h_prev']                = ( curses.ascii.DLE       , 'Go to previous item')                 # default: ^P
kbkey_orig['rb_h_add']                 = ( curses.ascii.EM        , 'Add item')                            # default: ^Y
kbkey_orig['rb_h_del']                 = ( curses.ascii.CAN       , 'Delete item')                         # default: ^X
kbkey_orig['rb_h_def']                 = ( curses.ascii.STX       , 'Make item default')                   # default: ^B
kbkey_orig['rb_h_0']                   = ( curses.ascii.ACK       , 'Go to template (item 0)')             # default: ^F
kbkey_orig['rb_h_save']                = ( curses.ascii.ENQ       , 'Save items')                          # default: ^E

# ! Window Keys:
kbkey_orig['h_windows']                = ( None                   , 'Windows keys')
kbkey_orig['F7']                       = ( curses.KEY_F7          , 'Remove old istallation files')
kbkey_orig['F8']                       = ( curses.KEY_F8          , 'Media Players management')
kbkey_orig['F9']                       = ( curses.KEY_F9          , 'Show EXE location')
kbkey_orig['F10']                      = ( curses.KEY_F10         , 'Uninstall PyRadio')

if platform.system().lower().startswith('win'):
    kbkey_orig['rb_p_first']           = ( curses.KEY_F1          , 'Go to first search results page')
    kbkey_orig['rb_p_next']            = ( curses.KEY_F3          , 'Go to next search results page')
    kbkey_orig['rb_p_prev']            = ( curses.KEY_F2          , 'Go to previous search results page')

# keys are the same as the headers of kbkey_orig
conflicts = {}
for a_key in kbkey_orig:
    if kbkey_orig[a_key][0] is None:
        header = a_key
        conflicts[header] = []
    else:
        conflicts[header].append(a_key)

''' this is the working dict
    it is a  deep copy of the original
    done this way for qick access
'''
def populate_dict():
    for key, value in kbkey_orig.items():
        if value[0]:
            kbkey[key] = value[0]
    return kbkey

kbkey = {}
kbkey = populate_dict()

# localized keys
lkbkey = {}

def set_kbkey(a_key, value):
    ''' update kbkey dict from other modules '''
    global kbkey  # This line comes after using kbkey
    kbkey[a_key] = value  # Attempting to use kbkey before declaring it as global

curses_function_keys_dict = {
    curses.KEY_F1: 'F1',
    curses.KEY_F2: 'F2',
    curses.KEY_F3: 'F3',
    curses.KEY_F4: 'F4',
    curses.KEY_F5: 'F5',
    curses.KEY_F6: 'F6',
    curses.KEY_F7: 'F7',
    curses.KEY_F8: 'F8',
    curses.KEY_F9: 'F9',
    curses.KEY_F10: 'F10',
}

curses_ascii_dict = {
    curses.ascii.NUL: '^@',
    curses.ascii.SOH: '^A',
    curses.ascii.STX: '^B',
    curses.ascii.ETX: '^C',
    curses.ascii.EOT: '^D',
    curses.ascii.ENQ: '^E',
    curses.ascii.ACK: '^F',
    curses.ascii.BEL: '^G',
    curses.ascii.BS:  '^H',
    curses.ascii.TAB: '^I',
    curses.ascii.LF:  '^J',
    curses.ascii.VT:  '^K',
    curses.ascii.FF:  '^L',
    curses.ascii.CR:  '^M',
    curses.ascii.SO:  '^N',
    curses.ascii.SI:  '^O',
    curses.ascii.DLE: '^P',
    curses.ascii.DC1: '^Q',
    curses.ascii.DC2: '^R',
    curses.ascii.DC3: '^S',
    curses.ascii.DC4: '^T',
    curses.ascii.NAK: '^U',
    curses.ascii.SYN: '^V',
    curses.ascii.ETB: '^W',
    curses.ascii.CAN: '^X',
    curses.ascii.EM:  '^Y',
    curses.ascii.SUB: '^Z',
    curses.ascii.ESC: '^[',
    curses.KEY_F1: 'F1',
    curses.KEY_F2: 'F2',
    curses.KEY_F3: 'F3',
    curses.KEY_F4: 'F4',
    curses.KEY_F5: 'F5',
    curses.KEY_F6: 'F6',
    curses.KEY_F7: 'F7',
    curses.KEY_F8: 'F8',
    curses.KEY_F9: 'F9',
    curses.KEY_F10: 'F10',
}

def read_keyboard_shortcuts(file_path, reset=False):
    global kbkey  # Declare kbkey as global since we're reassigning it
    if reset:
        kbkey = populate_dict()  # Reassign kbkey with a new OrderedDict
    data = None
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as json_file:
            data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, IOError):
        pass
    if data is not None:
        for n in data.keys():
            kbkey[n] = data[n]  # Modify the existing kbkey

def read_localized_keyboard(file_path, keyboard_path):
    ''' read file_path which is {'keyboard': 'name of country'},
            file_path is in "datya dir"
        if that succeeds, read "keyboard_path"/"name of country".jason
            and put result in data dict
            keyboard_path is in the code directory
        if any of the above steps fails, populate data dict
            with default values
        Finally populate global lbkey from data dict using ord()
            of both key and value
    '''
    global lkbkey
    error = False
    data = {}
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as json_file:
            data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError, TypeError, IOError):
        error = True
    if 'keyboard' in data:
        # read the actual keyboard file
        k_file = join(keyboard_path, data['keyboard'] + '.json')
        try:
            with open(k_file, 'r', encoding='utf-8', errors='ignore') as k_json_file:
                data = json.load(k_json_file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError, IOError):
            error = True
    else:
        error = True

    if error:
        keys = list(string.ascii_lowercase) + list(string.ascii_uppercase)
        values = list(string.ascii_lowercase) + list(string.ascii_uppercase)
        data = {keys[i]: values[i] for i in range(len(keys))}

    for key in data:
        lkbkey[ord(key)] = ord(data[key])

def to_str(akey):
    ''' convert kbkey keys to a string '''
    # Handle function keys explicitly
    if kbkey[akey] == ord(' '):
        return 'Space'
    elif kbkey[akey] == curses.KEY_F1:
        return "F1"
    elif kbkey[akey] == curses.KEY_F2:
        return "F2"
    elif kbkey[akey] == curses.KEY_F3:
        return "F3"
    elif kbkey[akey] == curses.KEY_F4:
        return "F4"
    elif kbkey[akey] == curses.KEY_F5:
        return "F5"
    elif kbkey[akey] == curses.KEY_F6:
        return "F6"
    elif kbkey[akey] == curses.KEY_F7:
        return "F7"
    elif kbkey[akey] == curses.KEY_F8:
        return "F8"
    elif kbkey[akey] == curses.KEY_F9:
        return "F9"
    elif kbkey[akey] == curses.KEY_F10:
        return "F10"
    adict = {
    'rec':          'Verital Line',
    'pause':        'Space',
    'gr':           '^G',
    'gr_next':      '^E',
    'gr_prev':      '^Y',
    'st_up':        '^U',
    'st_dn':        '^D',
    'p_next':       '^N',
    'p_prev':       '^P',
    }
    if akey in adict:
        return adict[akey]
    return chr(kbkey[akey])


def kb2str(msg):
    ''' convert a string to an appropriate
        form to be displayed to the user

        All keys in kbkey will be replaced with to_str result
        provided they are enclosed to {}
    '''
    for n in kbkey.keys():
        chk = '{' + n + '}'
        if chk in msg:
            msg = msg.replace(chk, to_str(n))
    if msg == ' ':
        msg = 'Space'

    return msg

def kb2strL(msg):
    ''' convert a string to an appropriate
        form to be displayed to the user

        msg can contain {X}, X is y, Y, n, N, q
    '''
    for n in ('y', 'Y', 'n', 'N', 'q'):
        msg = msg.replace('{' + n +  '}', chr(kbkey[n]))
    return msg

def kb2chr(akey):
    ''' convert a kbkey key to a string (result of to_str) '''
    if akey in kbkey.keys():
        return to_str(akey)
    return ''

def ctrl_code_to_string(a_code):
    if a_code:
        if a_code in curses_ascii_dict:
            return curses_ascii_dict[a_code]
        char = chr(a_code)
        return char
    return ''

def ctrl_code_to_letter(a_code):
    if a_code in curses_ascii_dict:
        return curses_ascii_dict[a_code][-1]
    return ''

def ctrl_code_to_simple_code(a_code):
    code = ctrl_code_to_letter(a_code)
    if code:
        return ord(code.lower())
    return None

def letter_to_ctrl_code(letter):
    ''' gets a letter (for example "a")
        returns the key of "^{letter}" (for example "^A")
        in curses_ascii_dict, or None for "^S", "^Z", and "^C" on Linux/macOS
        but accepts them on Windows.
    '''

    # Normalize to uppercase
    letter = letter.upper()

    # Calculate the ASCII value of the letter
    # ascii_value = ord(letter)

    # Check if it's a valid letter (A-Z)
    if 'A' <= letter <= 'Z':
        # Calculate the control character
        # control_char = curses.ascii.NUL + (ascii_value - ord('A') + 1)

        # Check for "^S", "^Z", and "^C" based on OS
        if platform.system() in ['Linux', 'Darwin']:  # Darwin is macOS
            if value := f'^{letter}' in ['^S', '^Z', '^C']:
                return None

        # Find and return the key corresponding to the control character
        for key, value in curses_ascii_dict.items():
            if value == f'^{letter}':
                return key

    # Return None if not a valid letter or not found
    return None

import curses

def is_valid_char(char, win):
    """
    Checks if the character c is a valid ASCII character or a control combination.
    If c is invalid, it will read from the window to clear the input buffer.

    Parameters:
        c (int): The character code obtained from getch().
        win (curses.window): The curses window object for further input if needed.

    Returns:
        bool: True if c is valid, False otherwise.
    """
    if char in (9, ord('\t')):
        return False
    # if char <= 127:
    if (65 <= char <= 90) or (97 <= char <= 122) or (1 <= char <= 47):
        ''' 1 byte '''
        return True
    #elif 194 <= char <= 223:
    elif 192 <= char <= 223:
        ''' 2 bytes '''
        win.getch()
    elif 224 <= char <= 239:
        ''' 3 bytes '''
        win.getch()
        win.getch()
    elif 240 <= char <= 244:
        ''' 4 bytes '''
        win.getch()
        win.getch()
        win.getch()
    elif char in (
        ord('='), ord('.'), ord('+'),
        ord('`'), ord('-'),
        ord('1'), ord('2'), ord('3'),
        ord('4'), ord('5'), ord('6'),
        ord('7'), ord('8'), ord('9'),
        curses.KEY_F1,
        curses.KEY_F2,
        curses.KEY_F3,
        curses.KEY_F4,
        curses.KEY_F5,
        curses.KEY_F6,
        curses.KEY_F7,
        curses.KEY_F8,
        curses.KEY_F9,
        curses.KEY_F10,
    ):
        return True
    return False

def is_invalid_key(key):
    """
    Check if the pressed key is a special key (like HOME, END, PgUp, etc.).

    Args:
        key (int): The key code returned by curses.getch().

    Returns:
        bool: True if it's a special key, False otherwise.
    """
    # Check for special keys defined in curses
    special_keys = [
        curses.KEY_HOME,
        curses.KEY_END,
        curses.KEY_PPAGE,  # Page Up
        curses.KEY_NPAGE,  # Page Down
        curses.KEY_LEFT,
        curses.KEY_RIGHT,
        curses.KEY_UP,
        curses.KEY_DOWN,
        curses.KEY_IC,     # Insert
        curses.KEY_DC,     # Delete
        curses.KEY_BACKSPACE,
        # Add more keys as necessary
    ]
    if key in (
        curses.KEY_F1,
        curses.KEY_F2,
        curses.KEY_F3,
        curses.KEY_F4,
        curses.KEY_F5,
        curses.KEY_F6,
        curses.KEY_F7,
        curses.KEY_F8,
        curses.KEY_F9,
        curses.KEY_F10,
    ):
        logger.error('Key is F-[1-10]')
        return False

    # Check if the key is in the list of special keys or is greater than 255
    return key in special_keys or key > 255

def is_ctrl_key(key):
    """
    Check if the pressed key is a Ctrl-* key.

    Args:
        key (int): The key code returned by curses.getch().

    Returns:
        bool: True if it's a Ctrl-* key, False otherwise.
    """
    # Ctrl+A to Ctrl+Z correspond to ASCII values 1 to 26
    return 0 <= key <= 26

def chk_key(char, key, win):
    logger.error(f'{lkbkey = }')
    for n in lkbkey:
        logger.error(f'{n} ({chr(n)}) : {lkbkey[n]} ({chr(lkbkey[n])})')
    logger.error(f'{key = }')
    logger.error(f'{chr(key) = }')
    logger.error(f'{char = }')
    logger.error(f'{chr(char) = }')
    if char == key:
        return True
    '''
    try:
        letter = get_unicode_and_cjk_char(None, char)
        logger.error(f'{letter = }')
        this_char = ord(letter)
        logger.error(f'{char(letter) = }')
    except:
        this_char = None
    '''
    letter = get_unicode_and_cjk_char(win, char)
    if letter is not None:
        logger.error(f'{letter = }')
        this_char = ord(letter)
        logger.error(f'{chr(this_char) = }')
        try:
            if this_char == lkbkey[key]:
                return True
        except IndexError:
            pass
    else:
        logger.error('letter is None')
    return False


def set_kb_letter(letter):
    global kb_letter
    kb_letter = letter

def set_kb_cjk(value):
    global kb_cjk
    kb_cjk = value

def get_unicode_and_cjk_char(win, char):
    def _decode_string(data):
        encodings = ['utf-8', locale.getpreferredencoding(False), 'latin1']
        for enc in encodings:
            try:
                data = data.decode(enc)
            except:
                continue
            break

        assert type(data) != bytes  # Latin1 should have worked.
        return data

    def get_check_next_byte(win):
        logger.error(f'{win = }')
        char = win.getch()
        if 128 <= char <= 191:
            return char
        else:
            return None
            raise UnicodeError


    set_kb_cjk(False)
    set_kb_letter('')
    logger.error(f'all {win = }')
    bytes = []
    if char <= 127:
        ''' 1 byte '''
        bytes.append(char)
    #elif 194 <= char <= 223:
    elif 192 <= char <= 223:
        ''' 2 bytes '''
        bytes.append(char)
        bytes.append(get_check_next_byte(win))
    elif 224 <= char <= 239:
        ''' 3 bytes '''
        bytes.append(char)
        bytes.append(get_check_next_byte(win))
        bytes.append(get_check_next_byte(win))
    elif 240 <= char <= 244:
        ''' 4 bytes '''
        bytes.append(char)
        bytes.append(get_check_next_byte(win))
        bytes.append(get_check_next_byte(win))
        bytes.append(get_check_next_byte(win))
    ''' no zero byte allowed '''
    while 0 in bytes:
        bytes.remove(0)

    try:
        buf = bytearray(bytes)
    except TypeError:
        return None
    out = _decode_string(buf)
    if out:
        set_kb_letter(out)
        if is_wide(out) and not kb_cjk:
            set_kb_cjk(True)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('=== CJK editing is ON ===')
    else:
        out = None
        set_kb_letter('')
        set_kb_cjk(False)
    return out







if __name__ == '__main__':
    import json
    with open('/home/spiros/projects/my-gits/pyradio/pyradio/keyboard/classes.json', 'r', encoding='utf-8') as f:
        res = json.load(f)
    print('===> classes.py')
    print(res)
    out = []
    for n in res:
        out += res[n]

    print('\n\n===> In list')
    out = list(set(out))
    print(out)

    missing = []

    for n in kbkey_orig:
        if n not in out and kbkey_orig[n][0]:
            missing.append(n)

    print('\n\n===> missing')
    print(missing)
    global_functions = {
        'tag',
        't_tag',
        'transp',
        'v_up1',
        'v_up2',
        'v_up3',
        'v_dn1',
        'v_dn2',
        'mute',
        's_vol',
        't_calc_col',
        'repaint',
        # ord('b'): None,
    }

    missing_after_global_functions = []
    for n in missing:
        if n not in global_functions:
            missing_after_global_functions.append(n)

    print('\n\n===> missing after removing global_functions')
    print(missing_after_global_functions)


    extra = [
    'new_playlist',
    'rename_playlist',
    'open_remote_control',
    'open_dirs',
    'change_player',
    'hist_top',
    'buffer',
    'open_buffer',
    'last_playlist',
    'clear_reg',
    'clear_all_reg',
    'unnamed',
    'html_help',
    ]

    miss = []
    for n in missing_after_global_functions:
        if n not in extra:
            miss.append(n)

    print('\n\n===> missing after removing h_extra section')
    print(miss)
