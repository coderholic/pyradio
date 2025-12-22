# PyRadio Text-to-Speech Support

## Overview

**PyRadio** features comprehensive Text-to-Speech (TTS) support, providing intelligent auditory feedback for an enhanced radio streaming experience. This advanced system delivers contextual information with priority-based management, supporting multiple platforms and extensive configuration options.

## Table of Contents

<!-- vim-markdown-toc Marked -->

* [Features](#features)
* [Activation](#activation)
    * [Permanent Activation](#permanent-activation)
    * [Temporary Activation](#temporary-activation)
* [Platform Implementation](#platform-implementation)
    * [Linux](#linux)
    * [Windows](#windows)
    * [macOS](#macos)
* [Speech Control](#speech-control)
    * [Speech Context](#speech-context)
    * [Speech Priorities](#speech-priorities)
* [Language Support](#language-support)
    * [Voice Characteristics](#voice-characteristics)
    * [Platform-Specific Strategy](#platform-specific-strategy)
* [Technical Features](#technical-features)
    * [Smart Queue Management](#smart-queue-management)
    * [Intelligent Behavior](#intelligent-behavior)
* [Usage Guidelines](#usage-guidelines)
    * [For English-Dominant Users](#for-english-dominant-users)
    * [For Multi-Language Content](#for-multi-language-content)
* [Configuration Options](#configuration-options)
    * [Basic Settings](#basic-settings)
    * [Speech Characteristics](#speech-characteristics)
* [Current Status & Roadmap](#current-status-&-roadmap)
    * [Current Implementation](#current-implementation)
    * [Configuration Window Behavior](#configuration-window-behavior)
    * [Planned Enhancements for Future Versions](#planned-enhancements-for-future-versions)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#text-to-speech-support) ]

## Features

The TTS system provides spoken feedback for:

- **Station Navigation**: Station names and numbers during browsing
- **Playback Status**: Connection establishment, playback start/stop
- **Media Metadata**: Song titles and artist information from stream metadata
- **System Events**: Connection errors, volume changes, status alerts
- **Dialog Interaction**: Menu items, help text, configuration options

## Activation

### Permanent Activation
Enable TTS permanently through the configuration menu:
**Config → TTS → Enable TTS**

This setting is saved in your configuration file and persists across sessions.

### Temporary Activation
Toggle TTS during runtime by pressing **\\T** (backslash + T). This setting is session-only and resets when restarting PyRadio.

## Platform Implementation

### Linux
Utilizes [speech-dispatcher](https://freebsoft.org/speechd) configured for English language by default. Provides robust, interruptible speech synthesis with priority-based queue management.

### Windows
Leverages **Windows SAPI (Speech API)** with automatic selection of English voices when available. Features immediate speech interruption and consistent volume control.

### macOS
Employs the native **`say` command** using the system's default voice. Most macOS voices support multiple languages natively, handling mixed-language content seamlessly.

## Speech Control

### Speech Context
Control how much speech feedback you receive:

- **limited**: Essential information only (system messages, errors, station data)
- **window**: Extended feedback (includes window text and interface elements)
- **all**: Comprehensive feedback (speaks all available text and information)

### Speech Priorities
The system intelligently manages speech priorities:

- **Critical information** (errors, alerts) receives immediate attention
- **Navigation feedback** can be interrupted for rapid browsing
- **Song titles** are preserved and spoken after important announcements

## Language Support

### Voice Characteristics

TTS voices generally fall into two categories:

**Monolingual Voices** (typical on Linux/Windows):

- Specialized in one language
- System messages sound clear in English
- **Non-English characters may be mispronounced or skipped entirely**

**Multilingual Voices** (common on macOS):

- Automatic language detection and switching
- Handle mixed-language content naturally
- Provide authentic pronunciation for both system messages and station names

### Platform-Specific Strategy

- **Linux**: English-configured for consistent system messaging
- **Windows**: Auto-selects English voices while respecting system preferences
- **macOS**: Uses default system voice - typically multilingual by design

## Technical Features

### Smart Queue Management
- Priority-based processing
- Pending title queuing after high-priority interruptions
- Volume adjustment debouncing
- Platform-optimized anti-stutter protection

### Intelligent Behavior
- Critical alerts receive immediate priority
- Song titles are queued and spoken after high-priority interruptions
- Rapid navigation triggers queue optimization

## Usage Guidelines

### For English-Dominant Users
- Default configuration works optimally
- System messages and international station names sound natural

### For Multi-Language Content
- **macOS**: Handles mixed content seamlessly with multilingual voices
- **Windows/Linux**: **Non-English characters in station names may not be pronounced correctly**
- Consider using English names for frequently-accessed stations

## Configuration Options

### Basic Settings

| Setting | Values | Default | Description |
|---------|--------|---------|-------------|
| **enable_tts** | True/False | False | Master switch for TTS functionality |
| **tts_context** | limited/window/all | all | Controls how much information is spoken |
| **tts_volume** | 0-100 | 50 | Speech volume (Linux/Windows only) |
| **tts_rate** | -100 to 100 | 0 | Speech speed (negative=slower, positive=faster) |
| **tts_pitch** | -100 to 100 | 0 | Voice pitch adjustment |
| **tts_verbosity** | default/punctuation | default | Controls how punctuation is spoken |

### Speech Characteristics

- **Volume**: Adjustable on Linux and Windows (macOS uses system volume)
- **Rate**: Controls speech speed across all platforms
- **Pitch**: Alters voice pitch (platform-dependent implementation)
- **Verbosity**:
  - `default`: Punctuation is interpreted naturally
  - `punctuation`: Punctuation is spoken literally (e.g., "read-only" becomes "read dash only")

## Current Status & Roadmap

### Current Implementation

The TTS support in PyRadio is continuously evolving. Currently, TTS is available for:

- Main station selection window
- Playback status and notifications
- Station navigation and browsing
- Volume adjustment feedback
- Basic configuration menus

### Configuration Window Behavior

To assist users in configuring the program, **special rules apply when using the Configuration windows**:

1. **Full TTS Access**: When navigating through the Configuration menus and windows (including all sub-windows), the TTS system operates at its fullest capacity, temporarily overriding the `tts_context` setting to provide complete auditory feedback about all interface elements.

2. **Voice Sample**: While in the main TTS configuration screen, pressing **T** (uppercase) will speak a voice sample using the current TTS settings, allowing you to preview how your configuration sounds.

3. **Detailed Help**: In all configuration windows (currently implemented in the "Keyboard Shortcuts" window), pressing **t** (lowercase) provides additional spoken information about the current setting being configured.

*This special behavior ensures that all users can effectively configure the program to their preferences, regardless of their current TTS context settings.*

### Planned Enhancements for Future Versions

- Extended TTS support for all program windows and dialogs
- Enhanced context-aware speech patterns
- More granular control over speech feedback
- Implementation of the detailed help feature (lowercase **t**) across all configuration windows

*Note: The TTS system is designed to be unobtrusive yet informative. If you encounter issues with speech feedback or have suggestions for improvement, please report them via the PyRadio issue tracker.*
