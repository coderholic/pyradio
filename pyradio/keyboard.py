# -*- coding: utf-8 -*-
import curses
import curses.ascii
import platform
from collections import OrderedDict
import json
import logging
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

kbkey_orig = OrderedDict()
# ! MovementKeys
kbkey_orig['h0']                       = ( None                   , 'Movement Keys')
kbkey_orig['j']                        = ( ord('j')               , 'Go down: ')
kbkey_orig['k']                        = ( ord('k')               , 'Go up: ')
kbkey_orig['h']                        = ( ord('h')               , 'Go left: ')
kbkey_orig['l']                        = ( ord('l')               , 'Go right: ')
kbkey_orig['g']                        = ( ord('g')               , 'Go to top of list: ')
kbkey_orig['G']                        = ( ord('G')               , 'Go to end of list: ')
kbkey_orig['screen_top']               = ( ord('H')               , 'Go to top of screen: ')
kbkey_orig['screen_middle']            = ( ord('M')               , 'Go to middle of screen: ')
kbkey_orig['screen_bottom']            = ( ord('L')               , 'Go to bottom of screen: ')
kbkey_orig['goto_playing']             = ( ord('P')               , 'Go to playing station: ')
kbkey_orig['jump']                     = ( ord('J')               , 'Create a Jump tag: ')
kbkey_orig['st_up']                    = ( curses.ascii.NAK       , 'Move station up')                  # default: ^U
kbkey_orig['st_dn']                    = ( curses.ascii.EOT       , 'Move station down')                # default: ^D
kbkey_orig['hist_next']                = ( ord('>')               , 'Play next history item: ')
kbkey_orig['hist_prev']                = ( ord('<')               , 'Play previous history item: ')

# ! Volume Keys: ')
kbkey_orig['h1']                       = ( None                   , 'Volume Keys')
kbkey_orig['v_up1']                    = ( ord('+')               , 'Volume up Key 1: ')
kbkey_orig['v_up2']                    = ( ord('.')               , 'Volume up Key 2: ')
kbkey_orig['v_up3']                    = ( ord('=')               , 'Volume up Key 3: ')
kbkey_orig['v_dn1']                    = ( ord(',')               , 'Volume down Key 1: ')
kbkey_orig['v_dn2']                    = ( ord('-')               , 'Volume down Key 2: ')
kbkey_orig['mute']                     = ( ord('m')               , 'Mute player: ')
kbkey_orig['s_vol']                    = ( ord('v')               , 'Save volume: ')

# ! Global / Multi Window Keys
kbkey_orig['h2']                       = ( None                   , 'Global / Multi Window Keys')
kbkey_orig['?']                        = ( ord('?')               , 'open help window: ')
kbkey_orig['s']                        = ( ord('s')               , 'Save, Accept, RadioBrowser search: ')
kbkey_orig['q']                        = ( ord('q')               , 'Exit or Cancel: ')
kbkey_orig['y']                        = ( ord('y')               , 'Answer Yes: ')
kbkey_orig['Y']                        = ( ord('Y')               , 'Answer Yes to All: ')
kbkey_orig['n']                        = ( ord('n')               , 'Answer No: ')
kbkey_orig['N']                        = ( ord('N')               , 'Answer No to All: ')
kbkey_orig['del']                      = ( ord('x')               , 'Delete an item: ')
kbkey_orig['paste']                    = ( ord('p')               , 'Paste: ')
kbkey_orig['t']                        = ( ord('t')               , 'open themes window: ')
kbkey_orig['transp']                   = ( ord('T')               , 'Toggle transparency: ')
kbkey_orig['revert_saved']             = ( ord('r')               , 'Revert to saved values: ')
kbkey_orig['revert_def']               = ( ord('d')               , 'Revert to default values: ')
kbkey_orig['tab']                      = ( ord('L')               , 'Alternative TAB: ')
kbkey_orig['stab']                     = ( ord('H')               , 'Alternative Shift-TAB: ')
kbkey_orig['no_show']                  = ( ord('x')               , 'Do not show Info / Warning message again: ')
kbkey_orig['tag']                      = ( ord('w')               , 'Tag a title: ')
kbkey_orig['t_tag']                    = ( ord('W')               , 'Toggle Titles Tagging: ')
kbkey_orig['next']                     = ( ord('n')               , 'Go to next item: ')
kbkey_orig['prev']                     = ( ord('p')               , 'Go to previous item: ')
kbkey_orig['no_buffer']                = ( ord('z')               , 'Buffering Window: set to 0 (disable): ')

# ! Main Window keys
kbkey_orig['h3']                       = ( None                   , 'Main Window keys')
kbkey_orig['open_config']              = ( ord('c')               , 'Open config window: ')
kbkey_orig['open_playlist']            = ( ord('o')               , 'Open playlists list: ')
kbkey_orig['open_online']              = ( ord('O')               , 'Open online services (Radio Browser): ')
kbkey_orig['open_enc']                 = ( ord('E')               , 'Open encodings window: ')
kbkey_orig['extra_p_pamars']           = ( ord('Z')               , 'Open "Player Extra Parameters" window: ')
kbkey_orig['edit']                     = ( ord('e')               , 'Edit an item: ')
kbkey_orig['add']                      = ( ord('a')               , 'Add item (station, group, whatever): ')
kbkey_orig['append']                   = ( ord('A')               , 'Append item (add to end of current list): ')
kbkey_orig['gr']                       = ( curses.ascii.BEL       , 'Open groups window: ')                             # default: ^G
kbkey_orig['gr_next']                  = ( curses.ascii.EM        , 'Go to next group: ')                               # default: ^E
kbkey_orig['gr_prev']                  = ( curses.ascii.ENQ       , 'Go to previous group: ')                           # default: ^Y
kbkey_orig['open_regs']                = ( ord('\'')              , 'Open registers list: ')
kbkey_orig['open_extra']               = ( ord('\\')              , 'Open extra commands: ')
kbkey_orig['add_to_reg']               = ( ord('y')               , 'Add station to register: ')
kbkey_orig['info']                     = ( ord('i')               , 'Display station info: ')
kbkey_orig['fav']                      = ( ord('*')               , 'Add to favorites: ')
kbkey_orig['https']                    = ( ord('z')               , 'Toggle force use https: ')
kbkey_orig['pause']                    = ( ord(' ')               , 'Stop playback (Pause if recording): ')
kbkey_orig['random']                   = ( ord('r')               , 'Play random station: ')
kbkey_orig['p_next']                   = ( curses.ascii.SO        , 'Play next station: ')                              # default: ^N
kbkey_orig['p_prev']                   = ( curses.ascii.DLE       , 'Play next station: ')                              # default: ^P
kbkey_orig['Reload']                   = ( ord('R')               , 'Reload current playlist: ')
kbkey_orig['t_calc_col']               = ( ord('~')               , 'Toggle calculated colors: ')
kbkey_orig['rec']                      = ( ord('|')               , 'Toggle recording: ')

# ! Search function
kbkey_orig['h4']                       = ( None                   , 'Search function: ')
kbkey_orig['search']                   = ( ord('/')               , 'Open search subwindow: ')
kbkey_orig['search_next']              = ( ord('n')               , 'Search down: ')
kbkey_orig['search_prev']              = ( ord('N')               , 'Search up: ')


# main window:)
kbkey_orig['info_rename']              = ( ord('r')               , 'Rename station in info window')
kbkey_orig['reload']                   = ( ord('r')               , 'Reload from disk: ')
kbkey_orig['resize']                   = ( ord('#')               , 'Resize: ')
kbkey_orig['watch_theme']              = ( ord('c')               , 'Themes Window: Watch a theme for changes: ')

# ! Extra Commands Keys:)
kbkey_orig['h5']                       = ( None                   , 'Extra Commands Keys')
kbkey_orig['new_playlist']             = ( ord('n')               , 'Create a new playlist: ')
kbkey_orig['rename_playlist']          = ( ord('r')               , 'Rename current playlist: ')
kbkey_orig['open_remote_control']      = ( ord('s')               , 'open "PyRadio Remote Control" window: ')
kbkey_orig['open_dirs']                = ( ord('o')               , 'Open dirs in file manager: ')
kbkey_orig['change_player']            = ( ord('m')               , 'Cahnge media player: ')
kbkey_orig['hist_top']                 = ( ord(']')               , 'Open first opened playlist: ')
kbkey_orig['buffer']                   = ( ord('b')               , 'Toggle buffering: ')
kbkey_orig['open_buffer']              = ( ord('B')               , 'Open buffering window: ')
kbkey_orig['last_playlist']            = ( ord('l')               , 'Toggle Open last playlist: ')
kbkey_orig['clear_reg']                = ( ord('c')               , 'Clear current register: ')
kbkey_orig['clear_all_reg']            = ( ord('C')               , 'Clear all registers: ')
kbkey_orig['unnamed']                  = ( ord('u')               , 'Show unnamed register: ')
kbkey_orig['html_help']                = ( ord('h')               , 'Open html help: ')


# ! RadioBrowser Keys:
kbkey_orig['h5']                       = ( None                   , 'RadioBrowser Keys')
kbkey_orig['rb_vote']                  = ( ord('V')               , 'Vote for station: ')
kbkey_orig['rb_info']                  = ( ord('I')               , 'Station DB info: ')
kbkey_orig['rb_server']                = ( ord('C')               , 'Select server to connect to: ')
kbkey_orig['rb_sort']                  = ( ord('S')               , 'Sort search results: ')
kbkey_orig['rb_p_first']               = ( ord('{')               , 'Go to first search results page: ')
kbkey_orig['rb_p_next']                = ( ord(']')               , 'Go to next search results page: ')
kbkey_orig['rb_p_prev']                = ( ord('[')               , 'Go to previous search results page: ')
kbkey_orig['rb_h_next']                = ( curses.ascii.SO        , 'Go to next search item: ')                     # default: ^N
kbkey_orig['rb_h_prev']                = ( curses.ascii.DLE       , 'Go to previous search item: ')                 # default: ^P
kbkey_orig['rb_h_add']                 = ( curses.ascii.ENQ       , 'Add search item: ')                            # default: ^Y
kbkey_orig['rb_h_del']                 = ( curses.ascii.CAN       , 'Delete search item: ')                         # default: ^X
kbkey_orig['rb_h_def']                 = ( curses.ascii.STX       , 'Make item default: ')                          # default: ^B
kbkey_orig['rb_h_0']                   = ( curses.ascii.ACK       , 'Go to template (item 0): ')                    # default: ^F
kbkey_orig['rb_h_save']                = ( curses.ascii.ENQ       , 'Save search items: ')                          # default: ^E

# ! Window Keys:
kbkey_orig['h6']                       = ( None                   , 'Windows keys')
kbkey_orig['F7']                       = ( curses.KEY_F7          , ': ')
kbkey_orig['F8']                       = ( curses.KEY_F8          , 'Media Players management: ')
kbkey_orig['F9']                       = ( curses.KEY_F9          , 'Show EXE location: ')
kbkey_orig['F10']                      = ( curses.KEY_F10         , 'Uninstall PyRadio: ')

''' this is the working dict
    it is a  deep copy of the original
    done this way for qick access
'''
def populate_dict():
    for key, value in kbkey_orig.items():
        kbkey[key] = value[0]
    return kbkey

kbkey = OrderedDict()
kbkey = populate_dict()

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
    else:
        data = None
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as json_file:
                data = json.load(json_file)
        except (FileNotFoundError, json.JSONDecodeError, TypeError, IOError):
            pass
        if data is not None:
            print('========')
            for n in data.keys():
                print(f'{n} : {data[n]}')
                kbkey[n] = data[n]  # Modify the existing kbkey

def to_str(akey):
    ''' convert kbkey keys to a string '''
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
    'F7':           'F7',
    'F8':           'F8',
    'F9':           'F9',
    'F10':          'F10',
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
    if a_code in curses_ascii_dict:
        return curses_ascii_dict[a_code]
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


if __name__ == '__main__':
    F_PATH="/home/spiros/keyboard.json"
    with open(F_PATH, 'w', encoding='utf-8', errors='ignore') as j_file:
        json.dump(kbkey, j_file, ensure_ascii=False)
