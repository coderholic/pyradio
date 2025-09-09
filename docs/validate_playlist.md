# PyRadio Playlist Validation Guide

**PyRadio** provides a powerful playlist validation system, with multi-threading support and host-aware throttling.


## Table of Contents

<!-- vim-markdown-toc Marked -->

* [Overview](#overview)
* [Features](#features)
* [Usage](#usage)
    * [Basic Syntax](#basic-syntax)
    * [Validation Options](#validation-options)
    * [Validation Modes](#validation-modes)
        * [mark mode (default)](#mark-mode-(default))
        * [drop mode](#drop-mode)
    * [Usage Examples](#usage-examples)
* [Technical Details](#technical-details)
    * [Validation Algorithm](#validation-algorithm)
    * [Host-Aware Throttling](#host-aware-throttling)
    * [Supported Formats](#supported-formats)
* [Output Files](#output-files)
    * [mark mode](#mark-mode)
    * [drop mode](#drop-mode)
* [Results Summary](#results-summary)
* [Usage Tips](#usage-tips)
* [Troubleshooting](#troubleshooting)
* [Contributing](#contributing)

<!-- vim-markdown-toc -->

[ [Back to main doc](index.md#playlist-validation-support)  ] [ Related: [M3U Playlist Support](m3u.md) ]

## Overview

This tool allows validation of radio stations in playlist files (CSV or M3U) to ensure all links are functional and provide actual playable audio content.

## Features

- **Multi-threaded validation**: Validate multiple stations simultaneously
- **Host-aware throttling**: Limit requests per host to prevent server banning
- **Smart audio detection**: Detect actual audio streams through multiple methods
- **Flexible output options**: Mark non-functional stations or save to separate files
- **Colorized output**: Readable results with color coding


## Usage

### Basic Syntax

    pyradio [options] --validate <mode> --convert <playlist_file>

### Validation Options

| Option | Default | Description |
|--------|---------|-------------|
| --validate | mark | Validation mode (**mark** or **drop**) |
| --threads | 5 | Number of threads for parallel processing |
| --timeout | 5 | Timeout in seconds per request |
| --max-per-host | 2 | Maximum concurrent requests per host |
| --with-date | False | Add timestamp to output filenames |
| --no-color | False | Disable color output |
| --quiet | False | Reduce verbosity (hide per-station output) |

### Validation Modes

#### mark mode (default)
Marks non-functional stations with "*[X]*" in the name and saves all results to one file.

    pyradio --validate --convert my_playlist.csv

#### drop mode
Creates two separate files:
- **.ok**: Working stations
- **.bad**: Non-working stations

Example:

    pyradio --validate drop my_playlist.m3u

### Usage Examples

**Basic validation:**

    pyradio --validate mark --convert playlist.csv


**Validation with 10 threads and stricter timeout:**

    pyradio --validate drop --threads 10 --timeout 3 --convert playlist.m3u

**Validation with timestamp and without colors:**

    pyradio --validate mark --with-date --no-color --convert playlist.csv

**Quiet validation (summary only):**

    pyradio --validate mark --quiet --convert playlist.m3u

## Technical Details

### Validation Algorithm

The tool uses multiple techniques to determine if a URL provides actual audio stream:

1. **Content-Type check**: Verifies content type is audio/video
2. **ICY headers detection**: Checks for Shoutcast/Icecast headers
3. **Audio signature analysis**: Detects patterns of common audio formats (MP3, AAC, OGG, FLAC, etc.)
4. **HTML exclusion**: Rejects HTML responses indicating errors or pages

### Host-Aware Throttling

To prevent server banning, the tool:
- Groups requests by hostname
- Applies separate semaphore for each host
- Limits concurrent requests per host (default: 2)

### Supported Formats

- **CSV**: Files with **PyRadio** CSV formatting
- **M3U**: Standard M3U playlist files

**Note:** If you provide a URL instead of a file path, **PyRadio** will treat it as a link to an online M3U file and attempt to download and validate it.

## Output Files

### mark mode
- "*playlist.validated.[timestamp].csv/m3u*": File with marked non-functional stations

### drop mode
- "*playlist.ok.[timestamp].csv/m3u*": Working stations
- "*playlist.bad.[timestamp].csv/m3u*": Non-working stations

## Results Summary

The tool displays a detailed summary including:

- Number of online/offline stations
- Number of groups (group headers)
- Success rate
- Total counts

## Usage Tips

1. **For large playlists**: Use more threads ("*--threads*") for faster processing
2. **For sensitive servers**: Reduce "*--max-per-host*" to avoid banning
3. **For scheduled validations**: Use "*--with-date*" for history
4. **For scripting**: Use "*--no-color --quiet*" for machine-readable output

## Troubleshooting

**Error: "Cannot write file"**
- Ensure you have write permissions in the directory

**Error: "Unsupported file type"**
- Ensure the file has **.csv** or **.m3u** extension

**Many non-functional stations**
- Check your network connection
- Increase "*--timeout*" for slow servers
- Check if stations require specific headers/referrer

## Contributing

Any improvements to the validation algorithm or new detection techniques are welcome.
