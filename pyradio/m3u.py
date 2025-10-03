# -*- coding: utf-8 -*-
"""
M3U playlist parsing and generation utilities for PyRadio.
Handles M3U file format with support for various metadata extensions.
"""
import re
import io
import functools
import locale
import tempfile
from html import unescape
import urllib.request
from urllib.parse import urlparse
from os.path import dirname, exists
from os import makedirs, unlink
from charset_normalizer import detect

from .common import Station

##############################################################################
#
#                               m3u functions
#
##############################################################################
HAS_IDNA = True
try:
    import idna
except ImportError:
    HAS_IDNA = False

locale.setlocale(locale.LC_ALL, "")

##############################################################################
#
#                           CENTRALIZED SUBSTITUTIONS
#
##############################################################################

# M3U CHARACTER SUBSTITUTION RULES (ORIGINAL_CHAR → REPLACEMENT_CHAR)
# USE EMPTY STRING AS REPLACEMENT TO DISABLE A SUBSTITUTION
# NOTE: FIRST MATCH WINS, PROCESS IN ORDER OF PRIORITY
# POSSIBLE COMMA OPTIONS:
#   "﹐" (SMALL COMMA U+FE50) - BEST BALANCE
#   "ʼ" (MODIFIER LETTER COMMA U+02BC) - MORE SUBTLE
#   "·" (MIDDLE DOT U+00B7)
#   ""  (GREEK ANO TELEIA U+0387)
M3U_SUBSTITUTIONS = (
    (",", "_·_"),   # MIDDLE DOT (U+00B7) - BEST FOR CSV ROUND-TRIP
    ("-", "–"),     # EN DASH (U+2013) WITH SPACES
    ('"', "”"),     # RIGHT DOUBLE QUOTATION MARK (U+201D)
)

# Reverse for CRITICAL parts when writing back to M3U-safe
CRITICAL_M3U_REPLACEMENTS = {
    '’': '&apos;',    # RIGHT SINGLE QUOTATION MARK → HTML entity
}

# Custom entity map used by html_entities_to_unicode_chars (centralized)
CUSTOM_HTML_ENTITIES = {
    # Common problematic entities in M3U files
    '&quot;': '”',      # RIGHT DOUBLE QUOTATION MARK (U+201D)
    '&#039;': "'",
    '&#39;': "'",
    '&apos;': "'",

    # Numeric entities for special characters
    '&#225;': 'á', '&#233;': 'é', '&#237;': 'í', '&#243;': 'ó', '&#250;': 'ú',
    '&#241;': 'ñ', '&#231;': 'ç',

    # German umlauts and special characters
    '&#228;': 'ä', '&#246;': 'ö', '&#252;': 'ü', '&#223;': 'ß',
    '&#196;': 'Ä', '&#214;': 'Ö', '&#220;': 'Ü',

    # Other common European characters
    '&#224;': 'à', '&#232;': 'è', '&#236;': 'ì', '&#242;': 'ò', '&#249;': 'ù',
    '&#226;': 'â', '&#234;': 'ê', '&#238;': 'î', '&#244;': 'ô', '&#251;': 'û',

    # Special symbols and punctuation
    '&#8211;': '–',  # EN DASH
    '&#8212;': '—',  # EM DASH
    '&#8216;': '‘',
    '&#8217;': '’',
    '&#8220;': '“',
    '&#8221;': '”',

    # Non-standard hex entities (common in IPTV systems)
    '&#xe1;': 'á', '&#xe9;': 'é', '&#xed;': 'í', '&#xf3;': 'ó', '&#xfa;': 'ú',
    '&#xf1;': 'ñ', '&#xe4;': 'ä', '&#xf6;': 'ö', '&#xfc;': 'ü',
    '&#xc4;': 'Ä', '&#xd6;': 'Ö', '&#xdc;': 'Ü',

    # Slash and bracket characters (avoid parsing issues)
    '&#47;': '/',
    '&#92;': '\\',
    '&#93;': ']',
    '&#91;': '[',
}

def clean_name(name):
    """Remove control characters and sanitize names, keep all Unicode characters"""
    if not name:
        return ""
    # Remove control characters
    name = re.sub(r'[\x00-\x1F\x7F]', '', name)
    # Strip leading/trailing whitespace
    return name.strip()[:255]

def clean_group_name(name):
    """
    Sanitize a group name for M3U output.
    - Remove only control characters
    - Preserve all Unicode letters (Greek, CJK, Umlauts, accented letters, etc.)
    - Apply M3U-specific substitutions (', -, ")
    - Limit length to 100 characters
    """
    if not name:
        return ""

    # Remove control characters only (0x00-0x1F, 0x7F)
    name = ''.join(c for c in name if c >= ' ' and c != '\x7f').strip()

    # Apply M3U substitutions
    for orig, sub in M3U_SUBSTITUTIONS:
        name = name.replace(orig, sub)

    return name.strip()[:100]
##############################################################################
#
#                                 URL VALIDATION
#
##############################################################################
def is_valid_url(url, check_image=False):
    """
    Universal URL validator for M3U files with mode switching.
    """
    # -------------------------------------------------------------------------
    # 1. Common checks for all URLs (security first)
    # -------------------------------------------------------------------------
    try:
        parsed = urlparse(url)
    except ValueError:
        return False

    # Basic requirements - NO AUTO-CORRECTION
    if not parsed.scheme:
        return False

    # Forbidden characters
    invalid_chars = ['"', "'", '<', '>', '{', '}', '|', '\\', '^', '`', ' ', '\n', '\r']
    if any(char in url for char in invalid_chars):
        return False

    # Length check
    if len(url) > 2048:
        return False

    # -------------------------------------------------------------------------
    # 2. Mode-specific checks
    # -------------------------------------------------------------------------
    if check_image:
        # RELAXED mode for images (http/https only)
        if parsed.scheme not in ('http', 'https'):
            return False
        return True  # Permissive for images

    # STRICT mode for streams
    if not parsed.scheme or not parsed.netloc:
        return False

    if parsed.scheme not in ('http', 'https', 'rtsp', 'udp', 'rtmp', 'mms', 'klp'):
        return False

    # Strict host validation for streams
    host = parsed.netloc.split('@')[-1].split(':')[0]

    # Allow ONLY:
    # 1. Valid domains (example.com)
    # 2. Valid IPv4 addresses (192.168.1.1)
    # 3. Valid IPv6 addresses (not shown here but could be added)

    is_valid_domain = re.match(r'^([a-zA-Z0-9-]+\.)+[a-zA-Z]{2,}$', host)
    is_valid_ipv4 = re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', host)

    if not (is_valid_domain or is_valid_ipv4):
        # Additional check for IDNA/international domains
        if HAS_IDNA:
            try:
                host.encode('idna')
                # If it encodes successfully, it's probably valid
            except (idna.core.IDNAError, UnicodeError):
                return False
        else:
            # Fallback: must be ASCII and look like a domain
            if not host.isascii() or not re.match(r'^[a-zA-Z0-9.-]+$', host):
                return False

    return True

##############################################################################
#
#                                 m3u to csv
#
##############################################################################

def unescape_string(value):
    """
    Unescape common escape sequences in attribute values.
    Handles: \" → ", \' → ', \\ → \\ (one!), \n → newline, \t → tab, etc.
    """
    if not value:
        return value

    result = []
    i = 0
    while i < len(value):
        if value[i] == '\\' and i + 1 < len(value):
            # Handle escape sequences
            if value[i + 1] == '\\':
                result.append('\\')
                i += 2
            elif value[i + 1] == '"':
                result.append('"')
                i += 2
            elif value[i + 1] == "'":
                result.append("'")
                i += 2
            elif value[i + 1] == 'n':
                result.append('\n')
                i += 2
            elif value[i + 1] == 't':
                result.append('\t')
                i += 2
            elif value[i + 1] == 'r':
                result.append('\r')
                i += 2
            elif value[i + 1] == 'b':
                result.append('\b')
                i += 2
            elif value[i + 1] == 'f':
                result.append('\f')
                i += 2
            # Handle octal escapes (optional)
            elif value[i + 1] in '01234567':
                octal_digits = ''
                j = i + 1
                while j < len(value) and j < i + 4 and value[j] in '01234567':
                    octal_digits += value[j]
                    j += 1
                try:
                    char_code = int(octal_digits, 8)
                    result.append(chr(char_code))
                    i += 1 + len(octal_digits)
                except ValueError:
                    result.append(value[i])
                    i += 1
            # Handle hex escapes (optional)
            elif value[i + 1] == 'x' and i + 3 < len(value):
                hex_digits = value[i+2:i+4]
                if all(c in '0123456789ABCDEFabcdef' for c in hex_digits):
                    try:
                        char_code = int(hex_digits, 16)
                        result.append(chr(char_code))
                        i += 4
                    except ValueError:
                        result.append(value[i])
                        i += 1
                else:
                    result.append(value[i])
                    i += 1
            # Keep unknown escape sequences as-is
            else:
                result.append(value[i])
                i += 1
        else:
            result.append(value[i])
            i += 1

    return ''.join(result)

def is_valid_group_name(group_name):
    """
    Validate group title name.

    Args:
        group_name: Group title string to validate

    Returns:
        bool: True if valid, False if invalid
    """
    if not group_name or not isinstance(group_name, str):
        return False
    if len(group_name) > 200:
        return False
    if not re.match(r'^[\w\s\-.,!?&()/:#@+]+$', group_name):
        return False
    return True

def parse_attributes(line):
    """
    Parse attributes from EXTINF line using regex-based approach.

    Args:
        line: The EXTINF line to parse

    Returns:
        dict: Dictionary containing parsed attributes
    """
    target_attributes = {'tvg-logo', 'group-title'}  # Attributes we care about

    out = {}

    # Only process EXTINF lines with attributes
    if not line.startswith('#EXTINF:-1'):
        return out

    # Extract the attributes part (everything after EXTINF:-1 and before the comma)
    if ', ' in line:
        # Handle both formats: #EXTINF:-1 attr=value,Name and #EXTINF:-1,Name
        if line.startswith('#EXTINF:-1 '):
            parts = line.split('#EXTINF:-1', 1)
        elif line.startswith('#EXTINF:-1,'):
            # This line has no attributes, just the name
            return out
        else:
            # Handle other EXTINF formats
            return out
    else:
        return out

    attr_parts = parts[1].split(',', 1)
    attr_section = attr_parts[0].strip() if len(attr_parts) > 1 else ""
    if not attr_section:
        return out

    # Regex pattern to find all attribute=value pairs
    attr_pattern = r'(?:^|[\s,])([a-zA-Z][a-zA-Z0-9-]*)=("[^"]*"|\'[^\']*\'|[^\s]*)'
    matches = re.findall(attr_pattern, attr_section)

    for attr_name, attr_value in matches:
        # Only process target attributes
        if attr_name not in target_attributes:
            continue

        # Remove surrounding quotes if present
        if (attr_value.startswith('"') and attr_value.endswith('"')) or \
           (attr_value.startswith("'") and attr_value.endswith("'")):
            clean_value = attr_value[1:-1]
        else:
            clean_value = attr_value

        # Unescape special characters
        unescaped_value = unescape_string(clean_value)

        # Attribute-specific validation
        if attr_name == 'tvg-logo':
            # RELAXED validation for logos (per requirement)
            if not is_valid_url(unescaped_value, check_image=True):
                continue
        elif attr_name == 'group-title':
            if not is_valid_group_name(unescaped_value):
                continue

        # Store the validated value
        out[attr_name] = unescaped_value

    return out

def generate_reverse_subs():
    """
    Creates reverse mappings for M3U -> CSV round-trip.
    - Preserves "_·_" placeholders (protected commas) safely.
    - Converts normal substitutions back to their original form.
    """
    reverse = {}

    for orig, sub in reversed(M3U_SUBSTITUTIONS):
        reverse[sub.replace("_·_", " · ")] = orig

    return reverse

@functools.lru_cache(maxsize=1)
def get_reverse_subs():
    """Create reverse substitution mappings for M3U display substitutions.

    Returns:
        dict: Reverse mapping of substitution characters
    """
    return generate_reverse_subs()

def reverse_substitutions(text):
    """Reverse the substitutions done by the
    CSV to M3U converter
    """
    if not text:
        return text
    subs = get_reverse_subs()
    for sub, orig in subs.items():
        text = text.replace(sub, orig)
    return text

def html_entities_to_unicode_chars(text: str) -> str:
    """
    Convert HTML entities to Unicode characters with special handling for M3U-specific cases.
    Focuses on non-standard entities and characters that need visual improvement for display.
    """
    # First pass: Handle custom entities (centralized)
    for entity, char in CUSTOM_HTML_ENTITIES.items():
        text = text.replace(entity, char)

    # Second pass: Use standard HTML unescape for remaining entities
    text = unescape(text)

    return text

def clean_temp_file(a_file):
    """Clean a tempfile object or file"""
    file_to_delete = None
    if not a_file:
        return
    if isinstance(a_file, str):
        file_to_delete = a_file
    else:
        try:
            file_to_delete = a_file.name
        except AttributeError:
            return
    if file_to_delete:
        try:
            unlink(file_to_delete)
        except Exception:
            pass

def parse_m3u(m3u_path, max_entries=10000):
    """Convert M3U to playlist with enhanced safety checks"""

    temp_file = None
    if m3u_path.startswith("http://") or m3u_path.startswith("https://"):
        # Download remote m3u
        try:
            response = urllib.request.urlopen(m3u_path)
            data = response.read()
            temp_file = tempfile.NamedTemporaryFile(delete=False)
            temp_file.write(data)
            temp_file.close()
            m3u_path = temp_file.name
        except Exception as e:
            return None, f"Error parsing {m3u_path}: {str(e)}"

    # READ AS BINARY FIRST - FIXED
    try:
        with open(m3u_path, 'rb') as f:
            raw_data = f.read()
    except Exception as e:
        clean_temp_file(temp_file)
        return None, f"Error reading file: {str(e)}"

    # DETECT ENCODING FROM BYTES - FIXED
    try:
        result = detect(raw_data)
        encoding = result['encoding'] if result and result['encoding'] else 'utf-8'
        # Normalize encoding names
        if encoding.lower() in ['iso-8859-1', 'cp1252', 'windows-1252']:
            encoding = 'latin-1'
    except:
        encoding = 'utf-8'

    # DECODE PROPERLY - FIXED
    try:
        content = raw_data.decode(encoding, errors='replace')
    except:
        # Fallback sequence
        for test_enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                content = raw_data.decode(test_enc, errors='replace')
                encoding = test_enc
                break
            except:
                continue
        else:
            content = raw_data.decode('latin-1', errors='replace')
            encoding = 'latin-1'

    # PROCESS LINES
    lines = content.splitlines()
    ungrouped = []
    groups = {}
    current_station = [''] * len(Station)
    current_group = None
    current_logo = ''
    entry_count = 0

    try:
        for line in lines:
            # Safety checks
            if len(line.encode('utf-8')) > 4096:
                continue
            line = line.strip()
            if not line or line.startswith("#EXTM3U"):
                continue

            if line.startswith("#EXTGRP:"):
                # Handle group headers
                current_group = clean_name(line.split(':', 1)[1].strip()[:100])
                continue

            if line.startswith("#EXTIMG:"):
                # Process EXTIMG lines
                extimg_url = line.split(':', 1)[1].strip()
                current_logo = extimg_url
                current_station[Station.icon] = extimg_url

            elif line.startswith("#EXTVLCOPT:"):
                try:
                    opt_line = line.split(':', 1)[1].strip()
                    if '=' in opt_line:
                        key, value = opt_line.split('=', 1)
                        key = key.strip()
                        value = value.strip()

                        if key == "http-referrer" and current_station and value:
                            current_station[Station.referer] = value
                        elif key == "network-caching" and current_station and value:
                            ms = int(value)
                            seconds = ms // 1000
                            current_station[Station.buffering] = f"{seconds}@128"
                except (ValueError, IndexError):
                    pass

            elif line.startswith("#PYRADIO-"):
                try:
                    field_part = line[9:].split(':', 1)
                    if len(field_part) == 2:
                        field_name = field_part[0].strip()
                        value = field_part[1].strip()

                        field_map = {
                            "PROFILE": Station.profile,
                            "HTTP": Station.http,
                            "VOLUME": Station.volume,
                            "PLAYER": Station.player,
                            "BITRATE": None,
                            "ENCODING": Station.encoding
                        }

                        if field_name in field_map and current_station:
                            if field_name == "BITRATE" and current_station[Station.buffering]:
                                seconds = current_station[Station.buffering].split('@')[0]
                                current_station[Station.buffering] = f"{seconds}@{value}"
                            else:
                                current_station[field_map[field_name]] = value
                except (ValueError, IndexError):
                    pass

            elif line.startswith("#EXTINF"):
                if entry_count >= max_entries and max_entries > 0:
                    clean_temp_file(temp_file)
                    return None, f"Maximum entries ({max_entries}) reached"

                if ',' in line:
                    name = clean_name(line.split(',', 1)[1].strip())[:255]
                    name = html_entities_to_unicode_chars(name)

                    # FIX: ENCODING RECOVERY FOR STATION NAMES
                    if '�' in name and encoding != 'utf-8':
                        try:
                            # Try to recover from encoding mismatch
                            byte_data = name.encode(encoding, errors='replace')
                            recovered_name = byte_data.decode('utf-8', errors='replace')
                            if '�' not in recovered_name:
                                name = recovered_name
                        except:
                            pass

                    current_station[Station.name] = reverse_substitutions(name)

                # Parse attributes
                attrs = parse_attributes(line)
                if "group-title" in attrs:
                    current_group = clean_name(attrs["group-title"])[:100]
                if "tvg-logo" in attrs:
                    current_station[Station.icon] = attrs["tvg-logo"][:500]
                elif current_logo:
                    current_station[Station.icon] = current_logo

            elif not line.startswith('#'):
                # Process URL line
                url = line.strip()
                if is_valid_url(url):
                    if ';' in url:  # Remove ICY metadata
                        url = url.split(';')[0]
                    current_station[Station.url] = url
                    entry_count += 1

                    # Append the completed station to appropriate group
                    if current_group:
                        groups.setdefault(current_group, []).append(current_station)
                    else:
                        ungrouped.append(current_station)

                    # Reset for next station
                    current_station = [''] * len(Station)
                    current_logo = ''

        # Build playlist
        playlist = []
        playlist.extend(ungrouped)
        for group in sorted(groups):
            playlist.append([group, "-"])
            playlist.extend(groups[group])

        clean_temp_file(temp_file)
        return playlist, None

    except Exception as e:
        clean_temp_file(temp_file)
        return None, f"Error parsing {m3u_path}: {str(e)}"

##############################################################################
#
#                                 csv to m3u
#
##############################################################################
def escape_m3u_string(text):
    """
    Prepare a station/display name for safe M3U writing.
    - Preserves explicit escaped backslashes/quotes.
    - Converts raw quotes to &quot; (central policy).
    - Encloses in quotes if contains any of: comma, quote, dash.
    """
    if not text:
        return ""

    processed = str(text)

    # Preserve already-escaped sequences during replacement
    processed = processed.replace('\\\\', '\u0002').replace('\\"', '\u0001')
    # Only replace raw quotes, not already encoded ones:
    processed = processed.replace('"', '&quot;')
    processed = processed.replace('\u0001', '\\"').replace('\u0002', '\\\\')

    # Apply VLC/m3u display substitutions (centralized)
    for orig, sub in M3U_SUBSTITUTIONS:
        processed = processed.replace(orig, sub)

    if any(c in processed for c in (',', '"', '-')):
        return f'"{processed}"'
    return ' '.join(processed.strip().split())

def list_to_m3u(stations, out_file):
    """Write PyRadio stations to M3U file with error handling"""
    if not stations:
        return '[red]Error:[/red] No stations to write'

    try:
        # Create directory if it doesn't exist
        out_dir = dirname(out_file)
        if out_dir and not exists(out_dir):
            makedirs(out_dir)

        with io.open(out_file, 'w', encoding='utf-8') as f:
            f.write("#EXTM3U\n")
            current_group = None

            for entry in stations:
                # Handle group headers
                # Skip empty group names entirely
                if len(entry) >= 2 and entry[1] == "-":
                    if entry[0].strip():  # Only process non-empty names
                        current_group = clean_group_name(entry[0])
                    continue  # Skip regardless to avoid empty groups

                # Skip invalid stations
                if not entry[Station.url] or not is_valid_url(
                        entry[Station.url], check_image=False
                ):
                    continue

                # Write group header if exists
                if current_group:
                    f.write(f"#EXTGRP:{current_group}\n")

                # Make sure icon is a string
                # Ensure icon is valid and extract URL from dict if needed
                logo = ''
                if len(entry) > Station.icon and entry[Station.icon]:
                    icon_value = entry[Station.icon]
                    logo = icon_value

                    # RELAXED validation for logos (per requirement)
                    if not is_valid_url(logo, check_image=True):
                        logo = ''

                # Write icon if exists
                if logo:
                    f.write(f"#EXTIMG:{logo}\n")

                # Add this in list_to_m3u after group writing but before EXTIMG
                if entry[Station.referer]:
                    f.write(f"#EXTVLCOPT:http-referrer={entry[Station.referer]}\n")

                if entry[Station.buffering]:
                    if '@' in entry[Station.buffering]:
                        seconds, bitrate = entry[Station.buffering].split('@')
                    else:
                        seconds = entry[Station.buffering]
                        bitrate = "128"
                    try:
                        int_seconds = int(seconds) * 1000
                        f.write(f"#EXTVLCOPT:network-caching={int_seconds}\n")
                    except ValueError:
                        pass

                # PyRadio custom comments
                pyradio_fields = [
                    (Station.profile, "PROFILE"),
                    (Station.http, "HTTP"),
                    (Station.volume, "VOLUME"),
                    (Station.player, "PLAYER"),
                    (Station.encoding, "ENCODING")
                ]

                for field, tag in pyradio_fields:
                    if len(entry) > field and entry[field]:
                        f.write(f"#PYRADIO-{tag}: {entry[field]}\n")

                # Special handling for bitrate
                if entry[Station.buffering] and '@' in entry[Station.buffering]:
                    seconds, bitrate = entry[Station.buffering].split('@')
                    if bitrate != "128":  # Only write if not default
                        f.write(f"#PYRADIO-BITRATE: {bitrate}\n")

                # Build EXTINF line
                name = entry[Station.name] if entry[Station.name] else 'Station {}'.format(len(stations))
                # Apply display substitutions (centralized)
                for n in M3U_SUBSTITUTIONS:
                    name = name.replace(*n)

                attrs = []
                if logo:
                    attrs.append(f'tvg-logo="{logo}"')
                if current_group:
                    attrs.append('group-title="{}"'.format(current_group.replace('_·_', ' · ')))

                escaped_m3u_string = escape_m3u_string(name).replace('_·_', ' · ')
                if attrs:
                    joined_attrs = ' '.join(attrs)
                    string = (f"#EXTINF:-1 {joined_attrs}, "
                              f"{escaped_m3u_string}")
                else:
                    string = f"#EXTINF:-1,{escaped_m3u_string}"

                f.write(f"{string}\n{entry[Station.url]}\n")

            return None

    except (IOError, OSError) as e:
        return f"[red]File error: {e}[/red]"

    except Exception as e:
        return f"[red]Error writing M3U: {e}[/red]"
