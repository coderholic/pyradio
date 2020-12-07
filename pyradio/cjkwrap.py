"""CJK wrapping and filling. Fix Python issue24665.

Copyright (C) 2015-2018, Florent Gallaire <f@gallai.re>
Copyright (C) 1999-2001, Gregory P. Ward <gward@python.net>
Copyright (C) 2002-2003, Python Software Foundation

Python2 will stay broken forever:
<https://bugs.python.org/issue24665>

Originally developed for txt2tags <http://txt2tags.org>

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as
published by the Free Software Foundation, either version 3 of the
License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with this program.  If not, see <http://www.gnu.org/licenses/>.
"""

__version__ = '2.2'

import textwrap
import unicodedata
import sys

PY3 = sys.version[0] == '3'

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


def cjkslices(text, index):
    """cjkslices(object, integer) -> object, object

    Return the two slices of a text cut to the index.
    """
    if not isinstance(text, text_type):
        return text[:index], text[index:]
    if cjklen(text) <= index:
        return text, u''
    i = 1
    # <= and i-1 to catch the last double length char of odd line
    while cjklen(text[:i]) <= index:
        i = i + 1
    return text[:i-1], text[i-1:]


class CJKWrapper(textwrap.TextWrapper):
    """CJK fix for the Greg Ward textwrap lib."""
    def _handle_long_word(self, reversed_chunks, cur_line, cur_len, width):
        if width < 1:
            space_left = 1
        else:
            space_left = width - cur_len
        if self.break_long_words:
            chunk_start, chunk_end = cjkslices(reversed_chunks[-1], space_left)
            cur_line.append(chunk_start)
            reversed_chunks[-1] = chunk_end
        elif not cur_line:
            cur_line.append(reversed_chunks.pop())

    def _wrap_chunks(self, chunks):
        lines = []
        if self.width <= 0:
            raise ValueError("invalid width %r (must be > 0)" % self.width)
        if self.width == 1 and (sum(cjklen(chunk) for chunk in chunks) >
                                sum(len(chunk) for chunk in chunks)):
            raise ValueError("invalid width 1 (must be > 1 when CJK chars)")
        chunks.reverse()
        while chunks:
            cur_line = []
            cur_len = 0

            if lines:
                indent = self.subsequent_indent
            else:
                indent = self.initial_indent
            width = self.width - len(indent)

            if self.drop_whitespace and \
                    chunks[-1].strip() == '' and \
                    lines:
                del chunks[-1]

            while chunks:
                chunk = cjklen(chunks[-1])
                if cur_len + chunk <= width:
                    cur_line.append(chunks.pop())
                    cur_len += chunk
                else:
                    break

            if chunks and cjklen(chunks[-1]) > width:
                self._handle_long_word(chunks, cur_line, cur_len, width)

            if self.drop_whitespace and \
                    cur_line and \
                    cur_line[-1].strip() == '':
                del cur_line[-1]

            if cur_line:
                lines.append(indent + ''.join(cur_line))
        return lines


# Convenience interface for CJKWrapper

def wrap(text, width=70, **kwargs):
    """Wrap a single paragraph of text, returning a list of wrapped lines.

    Reformat the single paragraph in 'text' so it fits in lines of no
    more than 'width' columns, and return a list of wrapped lines.  By
    default, tabs in 'text' are expanded with string.expandtabs(), and
    all other whitespace characters (including newline) are converted to
    space.  See CJKWrapper class for available keyword args to customize
    wrapping behaviour.
    """
    w = CJKWrapper(width=width, **kwargs)
    return w.wrap(text)


def fill(text, width=70, **kwargs):
    """Fill a single paragraph of text, returning a new string.

    Reformat the single paragraph in 'text' to fit in lines of no more
    than 'width' columns, and return a new string containing the entire
    wrapped paragraph.  As with wrap(), tabs are expanded and other
    whitespace characters converted to space.  See CJKWrapper class for
    available keyword args to customize wrapping behaviour.
    """
    w = CJKWrapper(width=width, **kwargs)
    return w.fill(text)
