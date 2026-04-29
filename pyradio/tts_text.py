import re
import locale
import logging
from .window_stack import Window_Stack_Constants
from .keyboard import kb2str

locale.setlocale(locale.LC_ALL, '')    # set your locale

logger = logging.getLogger(__name__)

TTS_WINDOWS_TEXT = {
    Window_Stack_Constants.PLAYER_PARAMS_MODE:
        lambda it: f'''Window: Player Extra Parameters.
            Note: Changes made here will not be saved in the configuration file.
            Current item: {it}.
        '''.replace('pyradio',' p y radio'),
    Window_Stack_Constants.CONNECTION_MODE:
        lambda val: f'''Window: Connection Type.
            Current value to force http connections: {val}
        ''',
    Window_Stack_Constants.CONNECTION_HELP_MODE:
        lambda: kb2str('''Window: Connection Type Help.
            {j}, {k}, {l}, {pause}", Right Up Down: Toggle parameter.
            Enter, {s}: Accept parameter.
            Escape, {q}, {h}, Left: Cancel operation.
            Note: Changes made here will not be saved in the configuration file.
        '''),
    Window_Stack_Constants.CHANGE_PLAYER_MODE:
        lambda pl, apl: f'''Window: Switch Media Player.
            Active Media Player: {pl}.
            Current item: {apl}.
        ''',
    Window_Stack_Constants.CHANGE_PLAYER_HELP_MODE:
        lambda: kb2str('''
            Please select a Media Player to activate and press {s},
            Enter or {pause} to switch to it, or Escape to Cancel.
        '''),
    Window_Stack_Constants.REMOTE_CONTROL_SERVER_NOT_ACTIVE_MODE:
        lambda ip: f'''Window: Remote Control Server.
            The server is not active.
            IP: {ip.replace('.', ' dot ')}
        ''',
    Window_Stack_Constants.REMOTE_CONTROL_SERVER_NOT_ACTIVE_HELP_MODE:
        lambda: kb2str('''Window: Remote Control Server Help.
            {j}, {k}, Up, Down, {h}, {l}, Left, Right: Change selection.
            Enter, {pause}: Toggle IP.
            {s}: Start the server.
            Any other key will hide the window
        '''),
    Window_Stack_Constants.OPEN_DIR_MODE:
        lambda it: f'''Window: Open Directory.
            Current item: {it}.
        ''',
    Window_Stack_Constants.GROUP_SELECTION_MODE:
        lambda it: f'''Window: Available groups.
            Current item: {it}.
        ''',
}

def describe_single_key(key_string):
    """
    Convert a single key string to its spoken description.
    Handles:
      - lowercase letters
      - uppercase letters
      - control keys (^X)
      - special keys (Home, End, etc.)

    Args:
        key_string: A string representing a single key

    Returns:
        Spoken description of the key
    """
    if not key_string:
        return ""

    # Special character mappings for readability
    special_chars = {
        ' ': 'Space',
        '\t': 'Tab',
        '\n': 'Enter',
        '\r': 'Enter',
        'Esc': 'Escape',
        'Del': 'Delete',
        'Left': 'Left Arrow',
        'Right': 'Right Arrow',
        'Up': 'Up Arrow',
        'Down': 'Down Arrow',
        'Sh-Tab': 'Shift Tab',
        'PgUp': 'Page Up',
        'PgDn': 'Page Down',
        'PgDown': 'Page Down',
        '.': 'Full stop',
        '-': 'Dash',
        '?': 'Questiong mark',
        '|': 'Vertical bar',
    }

    # 1. Check for control keys (^X)
    if len(key_string) == 2 and key_string[0] == '^':
        char = key_string[1]

        # Special control character mappings
        special_controls = {
            '?': 'Question Mark',
            '[': 'Left Bracket',
            ']': 'Right Bracket',
            '{': 'Left Brace',
            '}': 'Right Brace',
            ' ': 'Space',
            '^': 'Caret',
            '\\': 'Backslash',
            '/': 'Slash',
            '|': 'Pipe',
            '-': 'Minus',
            '_': 'Underscore',
            '=': 'Equals',
            '+': 'Plus',
            '`': 'Backtick',
            '~': 'Tilde',
            '@': 'At',
            '#': 'Hash',
            '$': 'Dollar',
            '%': 'Percent',
            '&': 'Ampersand',
            '*': 'Asterisk',
            '(': 'Left Parenthesis',
            ')': 'Right Parenthesis',
            '<': 'Less Than',
            '>': 'Greater Than',
            ',': 'Comma',
            '.': 'Period',
            ';': 'Semicolon',
            ':': 'Colon',
            '"': 'Double Quote',
            "'": 'Single Quote',
        }

        if char in special_controls:
            return f"Control {special_controls[char]}"
        if char.isalpha():
            return f"Control {char.upper()}"
        if char.isdigit():
            return f"Control {char}"
        return f"Control {char}"

    # 2. Check for single character
    if len(key_string) == 1:
        if key_string.islower():
            return key_string
        if key_string.isupper():
            return f"capital {key_string}"
        if key_string in special_chars:
            return special_chars[key_string]
        return key_string

    # 3. Check for special keys
    if key_string in special_chars:
        return special_chars[key_string]

    # 4. If no match, return the original
    return key_string

def handle_formatting_underscores(text):
    """
    Handle formatting underscores used for indentation.

    Args:
        text: Input text containing underscores for formatting

    Returns:
        Text with formatting underscores converted to spaces
    """
    # Replace multiple underscores used for indentation with spaces
    text = re.sub(r'^_{2,}', '', text)  # Remove leading underscores
    text = re.sub(r'_{2,}', ' ', text)   # Replace internal multiple underscores with single space
    return text


def convert_pipe_content(text):
    """
    Find all |...| patterns and:
      - If content is a single uppercase English letter, replace with "capital X"
      - Otherwise, remove the pipes and keep the content

    Args:
        text: Input text containing |...| patterns

    Returns:
        Text with converted pipe content
    """
    pattern = r'\|([^|]+)\|'

    def replace_match(match):
        content = match.group(1)
        # Check if it's a single uppercase English letter
        if len(content) == 1 and content.isalpha() and content.isupper():
            return f"capital {content.lower()}"
        return content

    return re.sub(pattern, replace_match, text)


def handle_parentheses(text, verbosity):
    """
    Handle parentheses based on verbosity setting.

    Args:
        text: Input text containing parentheses
        verbosity: 'default' or 'punctuation'

    Returns:
        Text with parentheses handled appropriately
    """
    if verbosity == 'punctuation':
        text = text.replace('(', ' open parenthesis ')
        text = text.replace(')', ' close parenthesis ')
        text = text.replace('[', ' open bracket ')
        text = text.replace(']', ' close bracket ')
        text = text.replace('{', ' open brace ')
        text = text.replace('}', ' close brace ')
        text = text.replace(':', ' colon ')
        text = text.replace(',', ' comma, ')
        # text = text.replace('.', ' full stop. ')
        text = text.replace('!', ' exclamation mark ')
    else:
        # Default behavior - replace with commas
        text = text.replace('(', ', ')
        text = text.replace(')', ', ')
        text = text.replace('[', ', ')
        text = text.replace(']', ', ')
        text = text.replace('{', ', ')
        text = text.replace('}', ', ')
        text = text.replace('!', ', ')

    return text

def replace_control_keys_in_text(text, verbosity):
    """
    Replace control key notations (^X) within text with descriptive names.
    Uses regex to catch all ^X patterns in the text.
    """
    # Special control character mappings
    special_controls = {
        '?': 'Question Mark',
        '[': 'Left Bracket',
        ']': 'Right Bracket',
        '{': 'Left Brace',
        '}': 'Right Brace',
        ' ': 'Space',
        '^': 'Caret',
        '\\': 'Backslash',
        '/': 'Slash',
        '|': 'Pipe',
        '-': 'Minus',
        '_': 'Underscore',
        '=': 'Equals',
        '+': 'Plus',
        '`': 'Backtick',
        '~': 'Tilde',
        '@': 'At',
        '#': 'Hash',
        '$': 'Dollar',
        '%': 'Percent',
        '&': 'Ampersand',
        '*': 'Asterisk',
        '(': 'Left Parenthesis',
        ')': 'Right Parenthesis',
        '<': 'Less Than',
        '>': 'Greater Than',
        ',': 'Comma',
        '.': 'Period',
        ';': 'Semicolon',
        ':': 'Colon',
        '"': 'Double Quote',
        "'": 'Single Quote',
    }

    # Regex to catch ^ followed by any single character
    pattern = r'\^(\?|[^\w\s]|[A-Za-z0-9])'

    def replace_match(match):
        char = match.group(1)
        if char in special_controls:
            return f' Control {special_controls[char]} '
        if char.isalpha():
            return f' Control {char.upper()} '
        if char.isdigit():
            return f' Control {char} '
        return f' Control {char} '

    return re.sub(pattern, replace_match, text)


def replace_special_keys(text, verbosity):
    """
    Replace special key notations with their descriptive names.

    Args:
        text: Input text containing special key notations
        verbosity: 'default' or 'punctuation'

    Returns:
        Text with special keys replaced by descriptive names
    """
    # Only include keys that need transformation
    special_keys_map = {
        'Esc': 'Escape',
        'Del': 'Delete',
        'Space': 'Space',
        'Sh-Tab': 'Shift Tab',
        'PgUp': 'Page Up',
        'PgDn': 'Page Down',
        'PgDown': 'Page Down',
        'Left': 'Left Arrow',
        'Right': 'Right Arrow',
        'Up': 'Up Arrow',
        'Down': 'Down Arrow',
    }

    # 1. First replace control keys with regex
    text = replace_control_keys_in_text(text, verbosity)
    # logger.error(f'a) {text = }')

    # 2. Then replace other special keys
    for key, replacement in special_keys_map.items():
        text = text.replace(key, f" {replacement} ")
    # logger.error(f'b) {text = }')


    # Clean up extra spaces
    text = re.sub(r'\s+', ' ', text).strip()
    # logger.error(f'c) {text = }')
    return text

def handle_punctuation_marks(text, verbosity):
    """
    Handle punctuation marks based on verbosity setting.

    Args:
        text: Input text containing punctuation marks
        verbosity: 'default' or 'punctuation'

    Returns:
        Text with punctuation marks handled appropriately
    """

    text = text.replace(r'\"', '"')
    text = text.replace(r"\'", "'")

    if verbosity == 'punctuation':
        # Handle dashes and hyphens
        if any(c in text for c in ['-', '–', '—', '‒']):
            text = re.sub(r'(\s)--(\s)', r'\1double dash\2', text)
            text = re.sub(r'(\s)-(\s)', r'\1dash\2', text)
            text = re.sub(r'(\w)-(\w)', r'\1 dash \2', text)
            text = re.sub(r'(\s)–(\s)', r'\1long dash\2', text)
            text = re.sub(r'(\w)–(\w)', r'\1 long dash \2', text)
            text = re.sub(r'(\s)—(\s)', r'\1long dash\2', text)
            text = re.sub(r'(\w)—(\w)', r'\1 long dash \2', text)
            text = re.sub(r'(\s)‒(\s)', r'\1figure dash\2', text)
            text = re.sub(r'(\w)‒(\w)', r'\1 figure dash \2', text)

        # Handle quotes
        text = text.replace('"', ' quote ')
        text = text.replace("'", ' single quote ')

        # Handle ellipsis
        text = text.replace('...', ' dot dot dot ')

        # Handle other symbols with descriptive names
        symbol_map = {
            '\\': 'backslash',
            '/': 'slash',
            '<': 'less than',
            '>': 'greater than',
            '~': 'tilde',
            '`': 'backtick',
            '@': 'at',
            '#': 'hash',
            '$': 'dollar',
            '%': 'percent',
            '&': 'and',
            '*': 'star',
            '+': 'plus',
            '=': 'equals',
        }

        for symbol, replacement in symbol_map.items():
            text = text.replace(symbol, f" {replacement} ")
    else:
        # Default behavior - minimal symbol replacement
        symbol_map = {
            '\\': 'backslash',
            '/': 'slash',
            '<': 'less than',
            '>': 'greater than',
            '~': 'tilde',
            '`': 'backtick',
            '@': 'at',
            '#': 'hash',
            '$': 'dollar',
            '%': 'percent',
            '&': 'and',
            '*': 'star',
            '+': 'plus',
            '=': 'equals',
        }

        for symbol, replacement in symbol_map.items():
            if symbol.isalnum():
                text = re.sub(r'\b' + re.escape(symbol) + r'\b', replacement, text)
            else:
                text = text.replace(symbol, f" {replacement} ")

    return text


def convert_file_extensions(text):
    """
    Convert dots in file extensions to "dot" for better TTS clarity.

    Args:
        text: Input text that may contain file extensions

    Returns:
        Text with file extension dots converted to "dot"
    """
    # Pattern to match common file extensions
    extension_pattern = r'\.(\w{2,4})'

    def replace_extension(match):
        extension = match.group(1)
        return f" dot {extension}"

    text = re.sub(extension_pattern, replace_extension, text)
    return text


def tts_transform_to_string(text_lines, verbosity):
    """
    Transform text lines to a single TTS-ready string.
    Optimized for dialog messages and help texts.
    """
    for i, n in enumerate(text_lines):
        if n == '___----==== Empty ====----___':
            text_lines[i] = 'Empty'
    transformed_lines = tts_transform_final(text_lines, verbosity)
    non_empty_lines = [line.strip() for line in transformed_lines if line.strip()]
    return ' '.join(non_empty_lines)


# Test function
def test_tts_transformation():
    """
    Test the TTS transformation with dialog examples.
    """
    test_cases = [
        [
            "|PyRadio|'s configuration has been altered",
            "but not saved. Do you want to save it now?",
            "",
            "Press |y| to save it or |Y| to disregard it.",
        ],
        [
            "Are you sure you want to delete station:",
            "\"|Best Radio Station|\"?",
            "",
            "Press |y| to confirm or any other key to cancel."
        ],
        [
            "Artist - Song",
            "Album (Remix) [2024]",
            "read-only file...",
            "Email: user@domain.com"
        ]
    ]

    for i, test_lines in enumerate(test_cases, 1):
        print(f"=== Test Case {i} ===")
        print("Original:")
        for line in test_lines:
            print(f"  {line}")

        for verbosity in ['default', 'punctuation']:
            print(f"\nTTS Ready String ({verbosity}):")
            tts_output = tts_transform_to_string(test_lines, verbosity)
            print(f"  '{tts_output}'")
        print()

def normalize_text(text: str) -> str:
    # Rule 1: remove "capital" before words (not single letter)
    text = re.sub(
        r'\bcapital\s+([A-Za-z]{2,})\b',
        r'\1',
        text,
        flags=re.IGNORECASE,
    )

    # Rule 2: add "capital" to single uppercase letters if not already present
    def replace_single_upper(match: re.Match) -> str:
        start = match.start()
        prefix = text[:start]

        if re.search(r'(?i)\bcapital\s+$', prefix):
            return match.group(1)

        return f'capital {match.group(1)}'

    text = re.sub(r'\b([A-Z])\b', replace_single_upper, text)

    # Rule 3: collapse comma chains
    # "comma ... comma" (with any mix of spaces/commas in between) -> "comma"
    text = re.sub(
        r'(?i)\bcomma\b(?:\s*,\s*|\s+)+\bcomma\b',
        'comma',
        text,
    )

    # Cleanup spaces
    text = re.sub(r'[ \t]+', ' ', text).strip()

    return text

def tts_transform_final(text_lines, verbosity='default'):
    """
    Transform a list of text lines for TTS output with simplified rules.

    Args:
        text_lines: List of text lines to transform
        verbosity: 'default' or 'punctuation'

    Returns:
        List of transformed text lines suitable for TTS
    """
    transformed_lines = []
    logger.error(f'\n\n\n8-8-8-8-8-8-8-8-8-8-8-8-8\n{text_lines = }\n8-8-8-8-8-8-8-8-8-8-8-8-8\n\n\n')
    for line in text_lines:
        # Step 0: Handle formatting underscores
        line = line.replace('!!!', '!')
        line = line.replace(', ,', ', ')
        line = handle_formatting_underscores(line)

        # Step 1: Convert pipe content |...|
        line = convert_pipe_content(line)

        # Step 2: Remove any remaining | characters
        line = line.replace('|', '')

        # logger.error(f'2 *** {line = }')
        # Step 3: Handle parentheses based on verbosity
        line = handle_parentheses(line, verbosity)

        # logger.error(f'3 *** {line = }')
        # Step 4: Replace special keys and symbols
        line = replace_special_keys(line, verbosity)

        # logger.error(f'4 *** {line = }')
        # Step 5: Convert file extensions (dots to "dot")
        line = convert_file_extensions(line)

        # logger.error(f'5 *** {line = }')
        # Step 6: Handle punctuation marks based on verbosity
        line = handle_punctuation_marks(line, verbosity)

        # logger.error(f'6 *** {line = }')
        # Step 7: Clean up extra spaces
        line = re.sub(r'\s+', ' ', line).strip()

        # step 8: Clean duplicates
        line = line.replace(' full stop full stop.', ' full stop.')
        line = line.replace('Page Up Arrow', 'Page Up')
        line = line.replace('Page Down Arrow', 'Page Down')
        line = line.replace('Arrow Arrow', 'Arrow')
        line = line.replace('percent Global', 'Global')
        line = line.replace('percent Note', 'Note')
        line = line.replace('Escape ape', 'Escape')
        line = line.replace('Delete ete ete', 'Delete')
        line = normalize_text(line)
        # logger.error(f'7 *** {line = }')
        transformed_lines.append(line)

    logger.error(f'\n\n\n8-8-8-8-8-8-8-8-8-8-8-8-8\n{transformed_lines = }\n8-8-8-8-8-8-8-8-8-8-8-8-8\n\n\n')

    return transformed_lines

if __name__ == "__main__":
    test_tts_transformation()
