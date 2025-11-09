# PyRadio Text-to-Speech Support

## Overview

**PyRadio** now features comprehensive Text-to-Speech (TTS) support, providing auditory feedback for an enhanced radio streaming experience. This intelligent system delivers contextual information about station navigation, playback status, and system events.

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
* [Language Support](#language-support)
    * [Voice Characteristics](#voice-characteristics)
    * [Platform-Specific Strategy](#platform-specific-strategy)
* [Technical Features](#technical-features)
    * [Smart Queue Management](#smart-queue-management)
    * [Intelligent Behavior](#intelligent-behavior)
* [Usage Guidelines](#usage-guidelines)
    * [For English-Dominant Users](#for-english-dominant-users)
    * [For Multi-Language Content](#for-multi-language-content)
* [Configuration Philosophy](#configuration-philosophy)
* [Configuration Options](#configuration-options)
    * [Volume](#volume)
* [Current Status & Roadmap](#current-status-&-roadmap)

<!-- vim-markdown-toc -->

[ [Return to main doc](index.md#text-to-speech-support) ]

## Features

The TTS system provides spoken feedback for:

- **Station Information**: Station names and numbers during navigation
- **Playback Status**: Start of playback and connection establishment  
- **Media Context**: Song titles when available in stream metadata
- **System Events**: Connection errors and important status changes
- **Audio Control**: Volume adjustment feedback

## Activation

### Permanent Activation
Enable TTS permanently through the configuration menu:
**Config → TTS → Enable TTS**

### Temporary Activation
Toggle TTS during runtime by pressing **\\T** (backslash + T). This setting is session-only and resets when restarting PyRadio.

## Platform Implementation

### Linux
Utilizes [speech-dispatcher](https://freebsoft.org/speechd) configured for English language by default. Provides robust, interruptible speech synthesis with priority-based queue management.

### Windows  
Leverages **Windows SAPI (Speech API)** with automatic selection of English voices when available. Features immediate speech interruption and consistent volume control.

### macOS
Employs the native **`say` command** using the system's default voice. Most macOS voices support multiple languages natively, handling mixed-language content seamlessly.

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
- Priority-based processing (HIGH for alerts, NORMAL for navigation)
- Pending title queuing after high-priority interruptions
- Volume adjustment debouncing
- Platform-optimized anti-stutter protection

### Intelligent Behavior
- Critical alerts receive immediate priority
- Song titles are queued and spoken after high-priority interruptions
- Rapid navigation triggers queue optimization
- Volume changes are consolidated to prevent speech spam

## Usage Guidelines

### For English-Dominant Users
- Default configuration works optimally
- System messages and international station names sound natural

### For Multi-Language Content
- **macOS**: Handles mixed content seamlessly with multilingual voices
- **Windows/Linux**: **Non-English characters in station names may not be pronounced correctly**
- Consider using English names for frequently-accessed stations

## Configuration Philosophy

The system is optimized for English while respecting platform conventions:

- **English-optimized voice selection on Linux and Windows**
- **Multilingual voice support on macOS**
- Maintains your preferred speech rate and volume
- Platform-native experience throughout

## Configuration Options

### Volume

The TTS volume can be adjusted independently of audio playback volume:

- **Linux**: Uses `spd-say` with volume range from **-100 to +100** (relative to base volume)
- **Windows**: Uses SAPI with volume range from **0 to 100** (absolute)
- **macOS**: Volume control is not supported - uses system speech volume

This option can be found in the configuration menu under **Config → TTS → Volume**.

## Current Status & Roadmap

This TTS implementation is actively developed. Planned enhancements include:

- Comprehensive help system narration
- Detailed interface element descriptions
- Enhanced context-aware speech patterns
- Extended configuration options
