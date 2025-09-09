# PyRadio M3U Playlist Support

**PyRadio** offers seamless two-way conversion between its native CSV playlist format and the widely supported M3U format. This functionality allows you to import radio stations from external M3U sources and export your **PyRadio** stations to share with other media players.

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [What You Can Do](#what-you-can-do)
    * [Convert M3U to PyRadio CSV](#convert-m3u-to-pyradio-csv)
    * [Convert PyRadio CSV to M3U](#convert-pyradio-csv-to-m3u)
* [Character Conversions in CSV→M3U Conversion](#character-conversions-in-csv→m3u-conversion)
* [Field Correspondence](#field-correspondence)
* [Command Line Usage](#command-line-usage)

<!-- vim-markdown-toc -->

[ [Back to main doc](index.md)  ] [ Related [Playlist Validation Guide](validate_playlist.md) ]


## What You Can Do

### Convert M3U to PyRadio CSV
When you have an M3U playlist file (from another media player or online source), **PyRadio** can convert it to its CSV format while preserving important metadata like station logos and group categories. The conversion process:

- Reads standard M3U files (both local and remote URLs)
- Extracts station names, URLs, and metadata
- Preserves group/category information
- Validates URLs to ensure they're working streams
- Handles various character encodings automatically
- Converts HTML entities to readable text

The default maximum number of stations in an M3U file is 10,000.

You can perform M3U to CSV conversion in two ways:

1. **Command line conversion** using the "*--convert*" option. \
\
This is ideal for batch conversions of multiple files (or M3U URLs). \
\
It also provides a way to convert very large M3Us to CSV; the "*-lm*" / "*--limit*" parameter will help you overcome the default 10,000 stations limit; setting it to 0 will disable any such check.

2. **Automatic conversion within PyRadio** when selecting M3U playlists from the playlist browser \
\
**PyRadio** automatically detects M3U files in your playlists directory and labels them with " (m3u)" suffix. When you select an M3U playlist from within **PyRadio**, it transparently converts it to CSV format for editing and use within the application. \
\
If both M3U and CSV versions of a playlist exist, **PyRadio** prioritizes the CSV file, assuming it's your preferred edited version.

### Convert PyRadio CSV to M3U
When you want to use your **PyRadio** stations with other media players or share them with others, you can export to the universal M3U format. The conversion:

- Maintains all your station information
- Preserves PyRadio-specific settings through custom tags
- Formats the output for maximum compatibility
- Applies proper character escaping for M3U standards
- Includes both standard and extended M3U metadata

## Character Conversions in CSV→M3U Conversion

When converting from **PyRadio** CSV to M3U format, certain characters are automatically converted for better compatibility and visual presentation:

| Original Character | Converted To | Purpose |
|-------------------|--------------|---------|
| Comma (`,`) | Middle dot (`·`) with spaces | Prevents parsing issues in M3U files |
| Hyphen (`-`) | En dash (`–`) with spaces | Improved visual appearance |
| Straight quote (`"`) | Right double quotation mark (`”`) | Better typography |

These conversions help maintain data integrity while ensuring the M3U files work reliably across different media players.

## Field Correspondence

Here's how PyRadio's internal fields map to M3U attributes:

| PyRadio Field | M3U Equivalent | Description |
|---------------|----------------|-------------|
| `Station.name` | `#EXTINF` title | The display name of the radio station |
| `Station.url` | Direct URL line | The stream URL (after `#EXTINF` line) |
| `Station.encoding` | `#PYRADIO-ENCODING` | Character encoding specification |
| `Station.icon` | `tvg-logo` attribute or `#EXTIMG` | Station icon image URL |
| `Station.profile` | `#PYRADIO-PROFILE` | Audio profile setting |
| `Station.buffering` | `network-caching` + `#PYRADIO-BITRATE` | Buffer and bitrate settings |
| `Station.http` | `#PYRADIO-HTTP` | Force HTTP option (special PyRadio feature) |
| `Station.volume` | `#PYRADIO-VOLUME` | Volume preset for the station |
| `Station.referer` | `http-referrer` option | HTTP referer header for the stream |
| `Station.player` | `#PYRADIO-PLAYER` | Preferred media player for this station |

Group information is preserved through M3U's `group-title` attribute and/or `#EXTGRP` directives.

All **#PYRADIO-*** fields inserted in created M3Us are there to preserve **PyRadio** specific data; they will be ignored by all existing players but will be used if the M3U is converted back to a CSV.

## Command Line Usage

The conversion functionality is accessible through PyRadio's command line interface:

```bash
# Convert M3U to CSV
pyradio --convert playlist.m3u

# Convert online M3U to CSV
pyradio --convert https://radio-site.org/m3u/playlist.m3u

# Convert CSV to M3U
pyradio --convert radio.csv

# Specify output file for conversion
pyradio --convert radio -o my_playlist.m3u

# Force overwrite without confirmation
pyradio --convert radio -o my_playlist -y

# Limit the number of processed stations
# This one actually extends it from 10,000 to 50,000
pyradio --convert large_playlist.m3u -lm 50000

```
