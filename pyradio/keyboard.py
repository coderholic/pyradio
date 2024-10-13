import curses
import curses.ascii
import platform
import logging
import locale
locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

kbkey = {
    # Common keys
    's':                        ord('s'),               # save, accept, toggle option
    'j':                        ord('j'),               # go down
    'k':                        ord('k'),               # go up
    'h':                        ord('h'),               # go left
    'l':                        ord('l'),               # go right
    '?':                        ord('?'),               # open help
    'html_help':                ord('h'),               # open html help
    'q':                        ord('q'),               # exit or cancel (default: q)
    'g':                        ord('g'),               # goto top of list
    'G':                        ord('G'),               # goto end of list
    'y':                        ord('y'),               # answer yes
    'Y':                        ord('Y'),               # answer yes to all
    'n':                        ord('n'),               # answer no
    'N':                        ord('N'),               # answer no to all
    'del':                      ord('x'),               # delete an item
    'paste':                    ord('p'),               # paste
    'mute':                     ord('m'),               # mute player
    's_vol':                    ord('v'),               # save volume
    't_calc_col':               ord('~'),               # toggle calculated colors
    'hist_next':                ord('>'),               # go to next history item
    'hist_prev':                ord('<'),               # go to previous history item
    'tag':                      ord('w'),               # tag a title
    't_tag':                    ord('W'),               # toggle titles tagging
    'v_up1':                    ord('+'),               # volume up
    'v_up2':                    ord('.'),               # volume up
    'v_up3':                    ord('='),               # volume up
    'v_dn1':                    ord(','),               # volume down
    'v_dn2':                    ord('-'),               # volume down
    'revert_saved':             ord('r'),               # revert to saved values
    'revert_def':               ord('d'),               # revert to default values
    'tab':                      ord('L'),               # alternative TAB
    'stab':                     ord('H'),               # alternative Shift-TAB
    'next':                     ord('n'),               # go to next item
    'prev':                     ord('p'),               # go to previous item

    # main window
    'open_playlist':            ord('o'),               # open playlists list
    'open_online':              ord('O'),               # open online services (Radio Browser)
    'open_regs':                ord('\''),              # open registers list
    'open_extra':               ord('\\'),              # open extra commands
    'add_to_reg':               ord('y'),               # add station to register
    't':                        ord('t'),               # open themes window
    'search':                   ord('/'),               # open search subwindow
    'transp':                   ord('T'),               # toggle transparency
    'fav':                      ord('*'),               # add to favorites
    'rec':                      ord('|'),               # toggle recording
    'jump':                     ord('J'),               # Create a Jump tag
    'screen_top':               ord('H'),               # go to top of screen
    'screen_middle':            ord('M'),               # go to middle of screen
    'screen_bottom':            ord('L'),               # go to bottom of screen
    'goto_playing':             ord('P'),               # goto playing station
    'search_next':              ord('n'),               # search down
    'search_prev':              ord('N'),               # search up
    'info':                     ord('i'),               # display station info
    'info_rename':              ord('r'),               # rename station in info window
    'pause':                    ord(' '),               # stop or pause playback
    'open_config':              ord('c'),               # open config window
    'open_enc':                 ord('E'),               # open encodings window
    'random':                   ord('r'),               # play random station
    'Reload':                   ord('R'),               # reload current playlist, main window only
    'reload':                   ord('r'),               # reload from disk
    'https':                    ord('z'),               # toggle force use https
    'extra_p_pamars':           ord('Z'),               # open "Player Extra Parameters" window
    'add':                      ord('a'),               # add item (station, group, whatever)
    'append':                   ord('A'),               # append item (add to end of current list)
    'edit':                     ord('e'),               # edit an item
    'gr':                       curses.ascii.BEL,       # open groups window - default: ^G
    'gr_next':                  curses.ascii.EM,        # go to next group - default: ^E
    'gr_prev':                  curses.ascii.ENQ,       # go to previous group - default: ^Y
    'st_up':                    curses.ascii.NAK,       # move station up - default: ^U
    'st_dn':                    curses.ascii.EOT,       # move station down - default: ^D
    'p_next':                   curses.ascii.SO,        # play next station - default: ^N
    'p_prev':                   curses.ascii.DLE,       # play next station - default: ^P
    'resize':                   ord('#'),               # resize
    'no_show':                  ord('x'),               # do not show message again
    'watch_theme':              ord('c'),               # watch a theme for changes

    # extra
    'hist_top':                 ord(']'),               # Open first opened playlist
    'buffer':                   ord('b'),               # set buffering
    'no_buffer':                ord('z'),               # set buffering to 0 (disable)
    'open_buffer':              ord('B'),               # open buffering window
    'last_playlist':            ord('l'),               # Toggle Open last playlist
    'change_player':            ord('m'),               # Cahnge media player
    'new_playlist':             ord('n'),               # Create a new playlist
    'open_remote_control':      ord('s'),               # open "PyRadio Remote Control" window
    'rename_playlist':          ord('r'),               # Rename current playlist
    'clear_reg':                ord('c'),               # Clear current register
    'clear_all_reg':            ord('C'),               # Clear all registers
    'open_dirs':                ord('o'),               # Open dirs in file manager
    'unnamed':                  ord('u'),               # Show unnamed register

    # RadioBrowser
    'rb_vote':                  ord('V'),
    'rb_info':                  ord('I'),
    'rb_server':                ord('C'),               # Select server to connect to
    'rb_sort':                  ord('S'),               # Sort search results
    'rb_p_first':               ord('{'),               # show first result page
    'rb_p_next':                ord(']'),               # show next result page
    'rb_p_prev':                ord('['),               # show previous result page
    'rb_h_next':                curses.ascii.SO,        # go to next item - default: ^N
    'rb_h_prev':                curses.ascii.DLE,       # go to previous item - default: ^P
    'rb_h_add':                 curses.ascii.ENQ,       # add item - default: ^Y
    'rb_h_del':                 curses.ascii.CAN,       # delete item - default: ^X
    'rb_h_def':                 curses.ascii.STX,       # make item default - default: ^B
    'rb_h_0':                   curses.ascii.ACK,       # go to template (item 0) - default: ^F
    'rb_h_save':                curses.ascii.ENQ,       # save history - default: ^E
    'F7':                       curses.KEY_F7,
    'F8':                       curses.KEY_F8,          # Windows Players management
    'F9':                       curses.KEY_F9,          # Windows Show EXE location
    'F10':                      curses.KEY_F10,         # Windows Uninstall PyRadio
}


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

def to_str(akey):
    ''' convert kbkey keys to a string '''
    adict = {
    'rec':          'Verital Line (|)',
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
    if akey in adict.keys():
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
    if a_code in curses_ascii_dict.keys():
        return curses_ascii_dict[a_code]
    return ''

def ctrl_code_to_letter(a_code):
    if a_code in curses_ascii_dict.keys():
        return curses_ascii_dict[a_code][-1]
    return ''

def ctrl_code_to_simple_code(a_code):
    code = ctrl_code_to_letter(a_code)
    logger.error(f'code = {code.lower()}')
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
    ascii_value = ord(letter)

    # Check if it's a valid letter (A-Z)
    if 'A' <= letter <= 'Z':
        # Calculate the control character
        control_char = curses.ascii.NUL + (ascii_value - ord('A') + 1)

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

