# -*- coding: utf-8 -*-

from sys import version
import unicodedata
PY3 = version[0] == '3'

if PY3:
    text_type = str
else:
    text_type = unicode

def is_wide(char):
    """is_wide(unicode_char) -> boolean

    Return True if unicode_char is Fullwidth or Wide, False otherwise.
    Fullwidth and Wide CJK chars are double-width.
    """
    return unicodedata.east_asian_width(char) in ('F', 'W')

def cjklen(text):
    """cjklen(object) -> integer

    Return the real width of an unicode text, the len of any other type.
    """
    if not isinstance(text, text_type):
        return len(text)
    return sum(2 if is_wide(char) else 1 for char in text)

def fix_cjk_string_width(self, a_string, width):
    if PY3 or isinstance(a_string, unicode):
        is_unicode = True
    else:
        is_unicode = False

    if is_unicode:
        while cjklen(a_string) > width:
            a_string = a_string[:-1]
        return a_string
    else:
        while cjklen(a_string.decode('utf-8', 'replace')) > width:
            a_string = a_string[:-1]
        return a_string


