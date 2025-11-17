import re

def tts_transform_final(text_lines):
    """
    Transform a list of text lines for TTS output with simplified rules.

    Args:
        text_lines: List of text lines to transform

    Returns:
        List of transformed text lines suitable for TTS
    """
    transformed_lines = []
    for line in text_lines:
        # Step 0: Handle formatting underscores
        line = handle_formatting_underscores(line)

        # Step 1: Convert pipe content |...|
        line = convert_pipe_content(line)

        # Step 2: Remove any remaining | characters
        line = line.replace('|', '')

        # Step 3: Replace parentheses with commas
        line = replace_parentheses_with_commas(line)

        # Step 4: Replace special keys and symbols
        line = replace_special_keys(line)

        # Step 5: Convert file extensions (dots to "dot")
        line = convert_file_extensions(line)

        # Step 6: Clean up extra spaces
        line = re.sub(r'\s+', ' ', line).strip()

        transformed_lines.append(line)

    return transformed_lines


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
        else:
            return content

    return re.sub(pattern, replace_match, text)


def replace_parentheses_with_commas(text):
    """
    Replace parentheses with commas for better TTS flow.

    Args:
        text: Input text containing parentheses

    Returns:
        Text with parentheses replaced by commas
    """
    text = text.replace('(', ', ')
    text = text.replace(')', ', ')
    return text


def replace_special_keys(text):
    """
    Replace special key notations with their descriptive names.

    Args:
        text: Input text containing special key notations

    Returns:
        Text with special keys replaced by descriptive names
    """
    special_keys_map = {
        'PgUp': 'Page Up',
        'PgDn': 'Page Down',
        'PgDown': 'Page Down',
        'Home': 'Home',
        'End': 'End',
        'Esc': 'Escape',
        'Del': 'Delete',
        'Enter': 'Enter',
        'Tab': 'Tab',
        'Space': 'Space',
        'Backspace': 'Backspace',
        'Left': 'Left Arrow',
        'Right': 'Right Arrow',
        'Up': 'Up Arrow',
        'Down': 'Down Arrow',
        'Sh-Tab': 'Shift Tab',
        '^B': 'Control B',
        '^F': 'Control F',
        '^N': 'Control N',
        '^P': 'Control P',
        '^U': 'Control U',
        '^D': 'Control D',
        '^Y': 'Control Y',
        '^E': 'Control E',
        '^G': 'Control G',
        '^A': 'Control A',
        '^W': 'Control W',
        '^K': 'Control K',
        '^X': 'Control X',
        '^H': 'Control H',
        '^?': 'Control Question Mark',
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

    for key, replacement in special_keys_map.items():
        if key.isalnum():
            text = re.sub(r'\b' + re.escape(key) + r'\b', replacement, text)
        else:
            text = text.replace(key, f" {replacement} ")

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


def tts_transform_to_string(text_lines):
    """
    Transform text lines to a single TTS-ready string.
    Optimized for dialog messages and help texts.
    """
    for i, n in enumerate(text_lines):
        if n == '___----==== Empty ====----___':
            text_lines[i] = 'Empty'
    transformed_lines = tts_transform_final(text_lines)
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
        ]
    ]

    for i, test_lines in enumerate(test_cases, 1):
        print(f"=== Test Case {i} ===")
        print("Original:")
        for line in test_lines:
            print(f"  {line}")

        print("\nTTS Ready String:")
        tts_output = tts_transform_to_string(test_lines)
        print(f"  '{tts_output}'")
        print()

if __name__ == "__main__":
    test_tts_transformation()

if __name__ == "__main__":
    test_tts_transformation()
