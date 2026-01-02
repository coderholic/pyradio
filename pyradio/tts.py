#!/usr/bin/env python3
"""
TTSManager - Cross-platform Text-to-Speech with Smart Queue Management
Advanced TTS manager with priority-based queue, title preservation,
volume debouncing and cross-platform support.
"""

import platform
import subprocess
import threading
import time
import logging
import os
import shlex
import queue
from enum import Enum
if platform.system().lower().startswith('win'):
    try:
        import win32com.client
    except:
        pass
from .common import M_STRINGS
from .tts_text import tts_transform_to_string

logger = logging.getLogger(__name__)

class Priority(Enum):
    """Priority levels for speech requests"""
    NORMAL = 1          # Interruptible - navigation, titles
    HIGH = 2            # Non-interruptible - critical alerts, playback status
    NAVIGATION = 3      # HIGH-like but self-interruptible
    HELP = 4            # Help messages
    DIALOG = 5          # Interruptible HIGH - dialog messages

class Context(Enum):
    """Context setting for speech requests"""
    LIMITED = 1
    WINDOW = 2
    ALL = 3

class TTSState(Enum):
    """TTS system states"""
    IDLE = 0
    SPEAKING = 1
    SHUTTING_DOWN = 2

class TTSConfig:
    """Configuration manager for TTS commands"""

    def __init__(self):
        self.config_file = self._get_config_path()
        self.config = self._load_config()

    def _get_config_path(self):
        """Get config file path for current platform"""
        if platform.system() == "Windows":
            return os.path.expanduser("~\\AppData\\Local\\pyradio\\tts.conf")
        else:
            return os.path.expanduser("~/.config/pyradio/tts.conf")

    def _load_config(self):
        """Load configuration from file with cross-platform support"""
        # Default configurations
        defaults = {
            'COMMAND_LINUX': 'spd-say',
            'COMMAND_WINDOWS': 'powershell -Command "Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\\\"{}\\\")"',
            'COMMAND_MACOS': 'say',
            'RESTART_LINUX': 'systemctl --user restart speech-dispatcher',
            'TITLE_TOKEN': M_STRINGS['title_'],
            'RESET_TOKENS': 'Playing,Initializing,Connecting,Error:'
        }

        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # Skip comments and empty lines
                    if not line or line.startswith('#'):
                        continue
                    # Parse key=value
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        if key in defaults:
                            defaults[key] = value
            if logger.isEnabledFor(logging.INFO):
                logger.info(f"Loaded TTS config from {self.config_file}")
        except FileNotFoundError:
            if logger.isEnabledFor(logging.INFO):
                logger.info("No TTS config file found, using defaults")
        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"Error reading TTS config: {e}")

        return defaults

    def get_command(self, system, text):
        """Get the appropriate command for the current system and text"""
        if system == "Linux":
            cmd_template = self.config['COMMAND_LINUX']
        elif system == "Windows":
            cmd_template = self.config['COMMAND_WINDOWS']
        elif system == "Darwin":
            cmd_template = self.config['COMMAND_MACOS']
        else:
            return None

        # Replace placeholder or append text
        if '{}' in cmd_template:
            return cmd_template.replace('{}', text)
        else:
            # Use shlex.split to properly handle quoted arguments
            base_cmd = shlex.split(cmd_template)
            base_cmd.append(text)
            return base_cmd

    def get_linux_restart_commands(self):
        """Get Linux restart commands as a list of command lists"""
        restart_str = self.config['RESTART_LINUX']
        commands = []

        if '&&' in restart_str:
            # Multiple commands separated with a &&
            for cmd in restart_str.split('&&'):
                cmd = cmd.strip()
                if cmd:
                    commands.append(shlex.split(cmd))
        else:
            # Single command
            commands.append(shlex.split(restart_str))

        return commands

    def get_title_token(self):
        """Get the title token for identifying title messages"""
        return self.config['TITLE_TOKEN']

    def get_reset_tokens(self):
        """Get the reset tokens that trigger title reset"""
        return [token.strip() for token in self.config['RESET_TOKENS'].split(',')]

class TTSRequest:
    """Represents a TTS speech request"""

    def __init__(self, text, priority=Priority.NORMAL):
        self.text = text
        self.priority = priority
        self.timestamp = time.time()

class TTSBase:
    """Base class for TTS implementations"""

    def __init__(self, config, volume, rate, pitch, verbosity):
        self.config = config
        self.volume = volume
        self.rate = rate
        self.pitch = pitch
        self.verbosity = verbosity
        self.system = platform.system()
        self.state = TTSState.IDLE
        self._current_process = None
        self._lock = threading.RLock()
        self.speech_delay = 0.3  # Anti-stutter delay

        # External stop mechanism for DIALOG and NAVIGATION interruption
        self._external_stop_requested = threading.Event()
        self._external_stop_lock = threading.RLock()
        self._navigation_stop_requested = threading.Event()  # NEW: Specific for NAVIGATION

    def request_external_stop(self, priority=Priority.DIALOG):
        """Request external stop - to be checked during DIALOG or NAVIGATION execution"""
        logger.error('priority  = {}'.format(priority.name))
        with self._external_stop_lock:
            if priority == Priority.NAVIGATION:
                logger.error('setting navigation stop request')
                self._navigation_stop_requested.set()
            else:
                logger.error('setting external stop request')
                self._external_stop_requested.set()

    def _clear_external_stop(self, priority=None):
        """Clear external stop flag for specific priority"""
        with self._external_stop_lock:
            if priority == Priority.NAVIGATION:
                self._navigation_stop_requested.clear()
            elif priority in (Priority.DIALOG, Priority.HIGH):
                self._external_stop_requested.clear()
            else:
                self._external_stop_requested.clear()
                self._navigation_stop_requested.clear()

    def _should_stop_externally(self, priority):
        """Check if external stop was requested"""
        result = False
        if priority in (Priority.DIALOG, Priority.HIGH):
            with self._external_stop_lock:
                result = self._external_stop_requested.is_set()
                if result:
                    logger.error(f"macOS DEBUG: _should_stop_externally returning TRUE for {priority.name}")
        elif priority == Priority.NAVIGATION:
            with self._external_stop_lock:
                result = self._navigation_stop_requested.is_set()

        return result

class TTSLinux(TTSBase):
    """Linux TTS implementation using user-configured command"""

    def __init__(self, config, volume, rate, pitch, verbosity):
        super().__init__(config, volume, rate, pitch, verbosity)
        self.retry_count = 0
        self.max_retries = 2

    def _calculate_volume(self):
        volume = int(self.volume())
        return str(2 * volume - 100)

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute speech with priority-based blocking behavior"""
        try:
            # Clear external stop flag for the given priority
            self._clear_external_stop(priority)

            # Calculate volume for spd-say (-100 to 100)
            volume = self._calculate_volume()

            # Determine command based on priority
            if priority in (Priority.HIGH, Priority.DIALOG, Priority.NAVIGATION):
                # HIGH/DIALOG/NAVIGATION priority: blocking execution with -w flag
                cmd = ['spd-say', '-l', 'en', '-i', volume,
                       '-r', self.rate(), '-p', self.pitch(), '-w', text]
                logger.error(f'Linux: Blocking speech with -w flag for {priority.name}')
            else:
                # NORMAL priority: non-blocking execution
                cmd = ['spd-say', '-l', 'en', '-i', volume,
                       '-r', self.rate(), '-p', self.pitch(), text]
                logger.error(f'Linux: Non-blocking speech for {priority.name}')

            # Execute the command
            logger.error(f'===> executing: "{cmd}" with {priority.name = }')

            # For blocking priorities (HIGH/DIALOG/NAVIGATION), we need to handle interruption
            if priority in (Priority.HIGH, Priority.DIALOG, Priority.NAVIGATION):
                # Start the process
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True
                )

                # Monitor the process for completion or interruption
                while process.poll() is None:
                    # Small sleep to avoid busy waiting
                    time.sleep(0.05)

                    # Check for external stop (for DIALOG or NAVIGATION)
                    if self._should_stop_externally(priority):
                        logger.error(f"External stop requested for {priority.name}, terminating")
                        process.terminate()
                        try:
                            process.wait(timeout=0.5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        return False

                    # Check for shutdown
                    if self.state == TTSState.SHUTTING_DOWN:
                        logger.error("Shutting down, terminating speech process")
                        process.terminate()
                        try:
                            process.wait(timeout=0.5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()
                        return False

                # Process completed normally
                result = process
            else:
                # For NORMAL priority, just run without monitoring
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True
                )

            logger.error(f'===> done: "{cmd}" with {priority.name = }')

            if result.returncode == 0:
                return True
            else:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(f"spd-say failed with return code {result.returncode}")
                return False

        except subprocess.TimeoutExpired:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("TTS command timeout - stopping speech")
            subprocess.run(['spd-say', '-S'], capture_output=True)  # Emergency stop
            return False
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"TTS execution error: {e}")
            return False

    def _restart_speech_dispatcher(self):
        """Restart speech-dispatcher service with support for multiple commands"""
        try:
            restart_command = self.config['RESTART_LINUX']

            # Separate commands if a && exists
            if '&&' in restart_command:
                commands = [cmd.strip() for cmd in restart_command.split('&&')]
            else:
                commands = [restart_command]

            for cmd in commands:
                cmd_list = shlex.split(cmd)
                result = subprocess.run(
                    cmd_list,
                    timeout=30,
                    capture_output=True
                )

                if result.returncode != 0:
                    if logger.isEnabledFor(logging.WARNING):
                        logger.warning(f"Restart command failed: {cmd}")
                    # We go no to next command even if it fails

            if logger.isEnabledFor(logging.WARNING):
                logger.info("All restart commands executed")
            return True

        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Failed to restart speech-dispatcher: {e}")

            # Fallback to standard restart methods
            try:
                # Try systemctl first
                subprocess.run(
                    ['systemctl', '--user', 'restart', 'speech-dispatcher'],
                    timeout=30,
                    capture_output=True
                )
                # Then pkill as backup
                subprocess.run(
                    ['pkill', '-f', 'speech-dispatcher'],
                    timeout=10,
                    capture_output=True
                )
                subprocess.run(
                    ['speech-dispatcher', '-d'],
                    timeout=10,
                    capture_output=True
                )
                if logger.isEnabledFor(logging.WARNING):
                    logger.info("Used fallback method to restart speech-dispatcher")
                return True
            except Exception as fallback_error:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"Fallback restart also failed: {fallback_error}")
                return False

    def stop(self):
        """Stop current speech - only used for emergency stops"""
        with self._lock:
            # Clear all external stop flags
            self._clear_external_stop()

            # Stop all speech using -S flag
            subprocess.run(['spd-say', '-S'], capture_output=True)
            # Anti-stutter delay
            time.sleep(self.speech_delay)

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            # Linux: Stop all speech immediately
            subprocess.run(['spd-say', '-S'], capture_output=True)

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            # Linux: No process to wait for, just cleanup state
            self._current_process = None
            self.state = TTSState.IDLE
            return True

class TTSWindows(TTSBase):
    """Windows TTS implementation using win32com and SAPI"""

    def __init__(self, config, volume, rate, pitch, verbosity):
        super().__init__(config, volume, rate, pitch, verbosity)
        self.speaker = win32com.client.Dispatch("SAPI.SpVoice")

        # Try to set an English voice
        english_voice = self._get_english_voice()
        if english_voice:
            self.speaker.Voice = english_voice
            if logger.isEnabledFor(logging.INFO):
                logger.info("Windows TTS initialized with English voice")
        else:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("No English voice found, using system default")

        self.speaker.Volume = self.volume()
        self.current_stream = None
        self._lock = threading.RLock()

    def _get_english_voice(self):
        """Find and return an English voice from available voices"""
        try:
            voices = self.speaker.GetVoices()

            # Priority 1: Look for voices with English indicators in description
            for i in range(voices.Count):
                voice = voices.Item(i)
                voice_description = voice.GetDescription().lower()

                # Check for English language indicators
                english_indicators = [
                    'en-', 'english', ' united states',
                    ' us ', ' uk ', 'british', 'american'
                ]

                if any(indicator in voice_description for indicator in english_indicators):
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Found English voice: {voice_description}")
                    return voice

            # Priority 2: If no specific English voice found, use first available
            if voices.Count > 0:
                first_voice = voices.Item(0)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Using first available voice: {first_voice.GetDescription()}")
                return first_voice

        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Error finding English voice: {e}")

        return None

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute speech with proper priority handling"""
        with self._lock:
            try:
                # Clear external stop flag for the given priority
                if priority in (Priority.HIGH, Priority.DIALOG, Priority.NAVIGATION):
                    self._clear_external_stop(priority)

                # For ALL priorities, stop any ongoing speech first
                self.stop()

                # Set voice properties
                self.speaker.Volume = int(self.volume())
                self.speaker.Rate = int(self.rate())

                logger.error(f'Windows: executing: "{text[:50]}..." with {priority.name}')

                # HIGH and DIALOG: async execution with interruption checking
                if priority in (Priority.HIGH, Priority.DIALOG):
                    # Using async speech (flags=1) and a waiting loop
                    self.current_stream = self.speaker.Speak(text, 1)  # flags=1 for async
                    self.state = TTSState.SPEAKING

                    while self.current_stream and not self.speaker.WaitUntilDone(50):  # 50ms chunks
                        # Check for external stop (for HIGH and DIALOG)
                        if self._should_stop_externally(priority):
                            self.stop()
                            return False
                        # Check for shutdown
                        if self.state == TTSState.SHUTTING_DOWN:
                            self.stop()
                            return False

                    self.current_stream = None
                    self.state = TTSState.IDLE
                    return True
                else:
                    # NAVIGATION and NORMAL: async execution without waiting
                    self.speaker.Speak(text, 1)  # flags=1 for async
                    self.state = TTSState.SPEAKING
                    return True

            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"Windows TTS error: {e}")
                return False

    def stop(self):
        """Stop current speech - optimized for Windows"""
        with self._lock:
            try:
                # Stop immediately
                self.speaker.Speak("", 2)  # flags=2 for immediate stop
                time.sleep(0.1)  # shorter delay
                self.current_stream = None
            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"Windows TTS stop error: {e}")

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self.stop()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            self.stop()
            return True

class TTSMacOS(TTSBase):
    """macOS TTS implementation with improved interruption handling"""

    def __init__(self, config, volume, rate, pitch, verbosity):
        super().__init__(config, volume, rate, pitch, verbosity)
        self._current_process = None
        self._lock = threading.RLock()
        self._speech_start_delay = 0.15
        # Faster interruption check interval for better responsiveness
        self._interrupt_check_interval = 0.02  # 20ms instead of 100ms

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute speech on macOS with optimized interruption handling"""
        with self._lock:
            try:
                # ALWAYS stop any current speech first - CRITICAL for macOS
                self._stop_current_speech()

                # Clear external stop flag for the given priority
                self._clear_external_stop(priority)

                # Small delay to avoid race conditions
                time.sleep(0.01)

                cmd = ['say', '-r', self.rate(), text]

                logger.error(f'macOS: executing: "{cmd}" with {priority.name}')

                # Use Popen with stdout/stderr redirection for better performance
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True  # New session for easier kill
                )
                self.state = TTSState.SPEAKING

                # For NORMAL: wait a bit to let speech start then return
                if priority == Priority.NORMAL:
                    time.sleep(self._speech_start_delay)
                    return True

                # For NAVIGATION, HIGH, DIALOG: wait for completion with interruption checks
                elif priority in (Priority.NAVIGATION, Priority.HIGH, Priority.DIALOG):
                    return self._wait_for_completion_with_interrupt(priority)

                return True

            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"macOS TTS error: {e}")
                return False

    def _stop_current_speech(self):
        """Stop any currently running speech process"""
        if self._current_process:
            try:
                # Try graceful termination first
                if self._current_process.poll() is None:
                    self._current_process.terminate()
                    try:
                        self._current_process.wait(timeout=0.2)
                    except subprocess.TimeoutExpired:
                        # Force kill if not terminated
                        self._current_process.kill()
                        self._current_process.wait()
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Error stopping speech process: {e}")
            finally:
                self._current_process = None

        # Clean up any stray say processes
        try:
            subprocess.run(['pkill', '-9', 'say'],
                          stdout=subprocess.DEVNULL,
                          stderr=subprocess.DEVNULL,
                          timeout=0.5)
        except Exception:
            pass

    def _wait_for_completion_with_interrupt(self, priority):
        """Wait for current process to complete with frequent interruption checking"""
        try:
            # Enhanced check for interruption
            while self._current_process and self._current_process.poll() is None:
                # Check for external stop (for DIALOG or NAVIGATION)
                if self._should_stop_externally(priority):
                    logger.error(f"macOS: External stop requested for {priority.name}")
                    self._stop_current_speech()
                    return False
                # Check for shutdown
                if self.state == TTSState.SHUTTING_DOWN:
                    self._stop_current_speech()
                    return False

                # Using a very short sleep for better responsiveness
                # but long enough to not load the PU
                time.sleep(0.01)  # 10ms instead of 20ms

            return self._current_process.returncode == 0 if self._current_process else False

        except Exception as e:
            logger.error(f"Error waiting for speech completion: {e}")
            return False

    def stop(self):
        """Stop current speech"""
        with self._lock:
            self._stop_current_speech()
            time.sleep(self.speech_delay)
            self.state = TTSState.IDLE

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self._stop_current_speech()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        start_time = time.time()
        with self._lock:
            while (self._current_process and
                   self._current_process.poll() is None and
                   (time.time() - start_time) < timeout):
                time.sleep(0.1)

            self._stop_current_speech()
            self._current_process = None
            self.state = TTSState.IDLE
            return True

class TTSManagerDummy:

    def __init__(self):
        self.enabled = False

    def can_i_use_tts(self, priority=Priority.HIGH):
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug('Speech request rejected: TTS disabled')
        return False

    def queue_speech(self, text, priority=Priority.NORMAL, context=Context.LIMITED, mode=0):
        return

    def stop(self):
        return

    def set_enabled(self, enable):
        return

    def shutdown(self):
        return

    def wait_for_shutdown(self, timeout):
        return

    def stop_dialog_speech(self):
        return

class TTSManager:
    """
    Main TTS manager with priority-based queue and title preservation
    """

    def __init__(self, volume, rate, pitch, verbosity, context, tts_in_config, enabled=True):
        self.stop_after_high = False
        self.enabled = enabled
        self.volume = volume
        self.rate = rate
        self.pitch = pitch
        self.verbosity = verbosity
        self.context = context
        self.config = TTSConfig()
        self.system = platform.system()
        self.available = False
        self.engine = None
        self.tts_in_config = tts_in_config

        # Queue management
        self.high_priority_queue = queue.Queue()
        self.normal_priority_queue = queue.Queue()
        self.pending_title = None
        self._last_spoken_title = None
        self.title_token = self.config.get_title_token()
        self.reset_tokens = self.config.get_reset_tokens()

        # NEW: Track current navigation for self-interruption
        self._current_navigation = None
        self._navigation_lock = threading.RLock()

        # Threading
        self._lock = threading.RLock()
        self._current_request = None
        self._worker_thread = None
        self._shutdown_flag = False

        # Statistics for rapid navigation detection
        self._last_navigation_time = 0
        self._consecutive_requests = 0

        if self.enabled:
            self._initialize_tts()
            self._start_worker()

        # Volume debouncing
        self._pending_volume_request = None
        self._volume_timer = None
        # New lock for volume operations
        self._volume_lock = threading.RLock()

    def _clean_navigation_queue(self):
        """Remove all pending NAVIGATION requests except the last one"""
        with self._navigation_lock:
            if self.high_priority_queue.qsize() == 0:
                return

            # Create a temporary list to hold all requests
            temp_requests = []
            last_navigation = None

            # Extract all requests from queue
            while not self.high_priority_queue.empty():
                try:
                    req = self.high_priority_queue.get_nowait()
                    if req.priority == Priority.NAVIGATION:
                        last_navigation = req  # Keep only the last one
                    else:
                        temp_requests.append(req)  # Keep non-NAVIGATION
                except queue.Empty:
                    break

            # Put back non-NAVIGATION requests
            for req in temp_requests:
                self.high_priority_queue.put(req)

            # Put back the last NAVIGATION request (if any)
            if last_navigation:
                self.high_priority_queue.put(last_navigation)

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Cleaned navigation queue, kept {1 if last_navigation else 0} NAVIGATION requests")

    def stop_navigation_speech(self):
        """Stop currently speaking NAVIGATION priority speech"""
        if self.engine:
            self.engine.request_external_stop(Priority.NAVIGATION)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Requested stop for NAVIGATION speech")

    def _process_pending_title(self):
        """Process pending title after HIGH or NAVIGATION priority completes"""
        if self.pending_title and not self._shutdown_flag:
            # Check if we should actually speak the title
            # Don't speak if another HIGH/NAVIGATION is queued
            if self.high_priority_queue.empty():
                # Add pending title to normal queue
                self.normal_priority_queue.put(TTSRequest(
                    self.pending_title,
                    Priority.NORMAL
                ))
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Queued pending title: {self.pending_title[:50]}...")
            self.pending_title = None

    def can_i_use_tts(self, priority=Priority.NORMAL):
        """ return True if TTS is available and enabled
            and the context is allowed to be spoken
        """
        if self.available and self.enabled:
            if self.tts_in_config():
                return True
            context = self.context()
            if context == 'all':
                return True
            elif context == 'window':
                if priority.value <= Priority.DIALOG.value:
                    return True
            elif context == 'limited':
                if priority.value <= Priority.HIGH.value:
                    return True
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Speech request rejected: priority is "{priority.name}" but context is "{context}"')
        return False

    def _initialize_tts(self):
        """Initialize TTS with proper availability checking"""
        try:
            if self.system == "Windows":
                self.available = self._check_windows_availability()
            elif self.system == "Darwin":
                self.available = self._check_macos_availability()
            else:
                self.available = self._check_linux_availability()

            if self.available:
                self.engine = self._create_engine()
                if logger.isEnabledFor(logging.INFO):
                    logger.info(f"TTS initialized successfully for {self.system}")
            else:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(f"TTS not available on {self.system}")

        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"TTS initialization failed: {e}")
            self.available = False

    def _create_engine(self):
        """Create the appropriate TTS engine for the current platform"""
        if self.system == "Windows":
            return TTSWindows(self.config, self.volume, self.rate, self.pitch, self.verbosity)
        elif self.system == "Darwin":
            return TTSMacOS(self.config, self.volume, self.rate, self.pitch, self.verbosity)
        else:
            return TTSLinux(self.config, self.volume, self.rate, self.pitch, self.verbosity)

    def _check_linux_availability(self):
        """Check if spd-say is available on Linux"""
        try:
            # Check if spd-say command exists and works
            result = subprocess.run(
                ['which', 'spd-say'],
                capture_output=True,
                timeout=5
            )
            if result.returncode != 0:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("spd-say not found in PATH")
                return False

            # Test that it actually works
            test_result = subprocess.run(
                ['spd-say', '--version'],
                capture_output=True,
                timeout=5
            )
            return test_result.returncode == 0

        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"Linux TTS check failed: {e}")
            return False

    def _check_windows_availability(self):
        """Check if Windows TTS is available via SAPI"""
        try:
            speaker = win32com.client.Dispatch("SAPI.SpVoice")
            # Test with empty speech
            speaker.Speak("", 1)
            return True
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Windows TTS availability check failed: {e}")
            return False

    def _check_macos_availability(self):
        """Check if say command is available on macOS"""
        try:
            result = subprocess.run(
                ['which', 'say'],
                capture_output=True,
                timeout=5
            )
            # say is almost always available on macOS
            return result.returncode == 0

        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"macOS TTS check failed: {e}")
            return False

    def _start_worker(self):
        """Start the queue processing worker thread"""
        if not self.available or not self.engine:
            return

        self._worker_thread = threading.Thread(
            target=self._process_queues,
            daemon=True,
            name="TTS-Worker"
        )
        self._worker_thread.start()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("TTS worker thread started")

    def stop_dialog_speech(self):
        """Stop currently speaking DIALOG priority speech"""
        if self.engine:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Requesting stop for DIALOG speech")
            if platform.system() == 'Linux':
                self.stop()
            elif platform.system() == 'Darwin':
                self.engine.request_external_stop(Priority.HIGH)
            else:
                self.engine.request_external_stop()

    def _process_queues(self):
        """Process speech queues with optimized handling for NAVIGATION"""
        while not self._shutdown_flag:
            try:
                # Use shorter timeouts for better responsiveness
                request = None

                # 1. Check for HIGH/DIALOG/NAVIGATION/HELP first (non-blocking)
                try:
                    request = self.high_priority_queue.get_nowait()
                except queue.Empty:
                    pass

                # 2. If no HIGH priority, check NORMAL queue with short timeout
                if not request:
                    try:
                        request = self.normal_priority_queue.get(timeout=0.01)
                    except queue.Empty:
                        time.sleep(0.005)  # Very small sleep for CPU efficiency
                        continue

                # Execute the request if it has actual text
                if request and request.text:
                    self._execute_request(request)

            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"Queue processing error: {e}")
                time.sleep(0.01)

    def _stop_normal_speech(self):
        """Stop currently speaking NORMAL priority speech"""
        with self._lock:
            # ALWAYS stop NORMAL when HIGH/DIALOG/NAVIGATION/HELP arrives
            if (self._current_request and
                self._current_request.priority == Priority.NORMAL):
                logger.error(f'**** Stopping NORMAL speech for {self.system}')
                self.engine.stop()
                return True

            # ADDITION: Also stop if engine is speaking and we don't know the request
            if (self.engine and
                self.engine.state == TTSState.SPEAKING and
                not self._current_request):
                logger.error(f'**** Stopping unknown speech (assumed NORMAL) for {self.system}')
                self.engine.stop()
                return True

            return False

    def _execute_request(self, request):
        """Execute a TTS request"""
        if not self.engine or self._shutdown_flag:
            return

        with self._lock:
            self._current_request = request
            self.engine.state = TTSState.SPEAKING

        try:
            prefix = ''
            pitch = self.pitch()
            logger.error(f'{pitch = }')
            if pitch != '0':
                if platform.system().lower().startswith('darwin'):
                    prefix = f'[[pbas {pitch}]]'
                elif platform.system().lower().startswith('win'):
                    prefix = f'<pitch absmiddle="{pitch}"/>'
            logger.error(f'{prefix = }')
            transformed_text = tts_transform_to_string([request.text], self.verbosity())
            success = self.engine._execute_speech(
                prefix+transformed_text,
                request.priority
            )
            if not success:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(f"Failed to speak: {request.text[:50]}...")
            else:
                if self._is_title(request.text):
                    self._last_spoken_title = request.text
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Speech execution error: {e}")
        finally:
            with self._lock:
                # Process pending title after HIGH or NAVIGATION completes
                if request.priority in (Priority.HIGH, Priority.NAVIGATION):
                    self._process_pending_title()

                # Clear current request BEFORE changing state
                self._current_request = None

                if self.engine.state != TTSState.SHUTTING_DOWN:
                    self.engine.state = TTSState.IDLE

        if self.stop_after_high and request.priority == Priority.HIGH:
            self.set_enabled(False)
            self.stop_after_high = False

    def _wait_with_interruption(self, delay):
        """Wait with interruption checks for anti-stutter"""
        chunk_size = 0.01  # 10ms chunks
        remaining = delay

        while remaining > 0 and not self._shutdown_flag:
            time.sleep(min(chunk_size, remaining))
            remaining -= chunk_size

            # Check if we should interrupt
            with self._lock:
                if (self.engine and
                    self.engine.state == TTSState.SHUTTING_DOWN):
                    return False

        return not self._shutdown_flag

    def _should_reset_title(self, text):
        """Check if this message should reset pending titles"""
        return any(reset_token in text for reset_token in self.reset_tokens)

    def _is_title(self, text):
        """Check if text is a title message"""
        return text.startswith(self.title_token)

    def _clean_normal_queue(self):
        """Clean normal priority queue - always clear for new NORMAL"""
        # Drain the queue completely
        while not self.normal_priority_queue.empty():
            try:
                self.normal_priority_queue.get_nowait()
            except queue.Empty:
                break
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug("Cleaned normal priority queue completely")

    def _get_context_value(self):
        context = self.context()
        if context == 'all':
            return Context.ALL.value
        elif context == 'window':
            return Context.WINDOW.value
        return Context.LIMITED.value

    def _wake_worker(self):
        """Wake up worker thread for faster processing"""
        # Add an empty request to wake up the worker thread
        try:
            # This will make the worker thread's queue.get() return immediately
            if self.high_priority_queue.qsize() < 10:  # Prevent queue flooding
                self.high_priority_queue.put(TTSRequest("", Priority.NORMAL), block=False)
        except queue.Full:
            pass
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Could not wake worker: {e}")

    def _clean_all_queues(self):
        """Clean all queues completely - for rapid navigation scenarios"""
        with self._lock:
            # Clean high priority queue
            while not self.high_priority_queue.empty():
                try:
                    self.high_priority_queue.get_nowait()
                except queue.Empty:
                    break

            # Clean normal priority queue
            while not self.normal_priority_queue.empty():
                try:
                    self.normal_priority_queue.get_nowait()
                except queue.Empty:
                    break

            # Reset state
            self.pending_title = None
            self._current_request = None

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Cleaned all queues completely")

    def queue_speech(self, text, priority=Priority.NORMAL, context=Context.LIMITED, mode=0):
        if priority == Priority.HELP:
            return

        logger.error(f'{mode = }')
        if not self.enabled or not self.available or not self.engine:
            return False

        logger.error('config says: {}'.format(self._get_context_value()))
        if context.value > self._get_context_value():
            logger.error('refusing {} = {}'.format(context.name, context.value))
            return False

        if not text or not text.strip():
            return False
        if '%' in text:
            text = text.replace('%', ' percent')
        if priority == Priority.HIGH and ' (error ' in text:
            text = text.split(' (error ')[0]

        # Volume debouncing logic - applies to HIGH and NAVIGATION
        if (priority in (Priority.HIGH, Priority.NAVIGATION) and
            text.startswith(M_STRINGS['volume_set'])):

            with self._volume_lock:
                # Cancel previous timer
                if self._volume_timer:
                    self._volume_timer.cancel()

                # Save the new volume request
                self._pending_volume_request = TTSRequest(text, priority)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Holding volume request: {text[:30]}...")

                # Start new timer for 500ms
                self._volume_timer = threading.Timer(0.5, self._process_pending_volume)
                self._volume_timer.daemon = True
                self._volume_timer.start()
            return True

        # If it's not volume, process any pending volume first
        with self._volume_lock:
            if self._pending_volume_request:
                self._process_pending_volume_immediately()

        if self._is_title(text) and text == self._last_spoken_title:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Ignoring repeated title: {text[:50]}...")
            return True

        if self._is_title(text):
            self._last_spoken_title = text

        request = TTSRequest(text, priority)

        try:
            if priority in (Priority.HIGH, Priority.DIALOG, Priority.NAVIGATION, Priority.HELP):
                # HIGH/DIALOG/NAVIGATION/HELP priority handling
                if self._should_reset_title(text):
                    self.pending_title = None
                    # Reset if changing title
                    self._last_spoken_title = None
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Reset pending title due to: {text[:50]}...")

                # ALWAYS stop NORMAL when HIGH/DIALOG/NAVIGATION/HELP arrives
                self._stop_normal_speech()

                # NAVIGATION-specific: Self-interruption logic
                if priority == Priority.NAVIGATION:
                    with self._navigation_lock:
                        # Rapid navigation detection
                        current_time = time.time()
                        if current_time - self._last_navigation_time < 0.1:  # 100ms
                            self._consecutive_requests += 1
                            if self._consecutive_requests > 3:
                                self._clean_all_queues()
                                self._consecutive_requests = 0
                        else:
                            self._consecutive_requests = 0

                        self._last_navigation_time = current_time

                        # If current request is also NAVIGATION, stop it
                        if (self._current_request and
                                self._current_request.priority == Priority.NAVIGATION):
                            logger.error('**** stopping previous NAVIGATION')
                            self.engine.request_external_stop(Priority.NAVIGATION)

                        # Clean up any pending NAVIGATION requests
                        self._clean_navigation_queue()

                    # For macOS: Ensure immediate stop before new speech
                    if self.system == "Darwin":
                        self.engine.stop()
                        time.sleep(0.01)  # Small delay to avoid race conditions

                    # Platform-specific: Wake up worker thread for faster processing on non-Linux
                    if self.system != "Linux":
                        self._wake_worker()

                self.high_priority_queue.put(request)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Queued {priority.name} priority: {text[:50]}...")
                return True

            else:
                # NORMAL priority request
                # Clean normal queue to avoid accumulation
                self._clean_normal_queue()

                # Stop any currently speaking NORMAL for new NORMAL
                self._stop_normal_speech()

                # Check if HIGH/DIALOG/NAVIGATION/HELP is playing or queued
                if not self.high_priority_queue.empty() or (
                    self._current_request and
                    self._current_request.priority in (Priority.HIGH, Priority.DIALOG, Priority.NAVIGATION, Priority.HELP)
                ):
                    # HIGH/DIALOG/NAVIGATION/HELP is playing or queued
                    if self._is_title(text):
                        # Title during HIGH/NAVIGATION/HELP: save as pending
                        self.pending_title = text
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f"Title saved as pending: {text[:50]}...")
                        return True
                    else:
                        # Non-title NORMAL during HIGH/DLG/NAV/HELP: reject
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug("Rejected NORMAL request during HIGH/DLG/NAV/HELP playback")
                        return False
                else:
                    self.normal_priority_queue.put(request)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Queued NORMAL: {text[:50]}...")
                    return True

        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Error queuing speech request: {e}")
            return False

    def _process_pending_volume(self):
        """Speak pending volume request after debounce period"""
        with self._volume_lock:
            if self._pending_volume_request:
                volume_request = self._pending_volume_request
                self._pending_volume_request = None
                self._volume_timer = None

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Processing debounced volume: {volume_request.text[:30]}...")
                # Insert it in the HIGH queue to be spoken
                self.high_priority_queue.put(volume_request)

    def _process_pending_volume_immediately(self):
        """Forced speech for pending volume SR before any other request"""
        with self._volume_lock:
            if self._pending_volume_request:
                volume_request = self._pending_volume_request
                self._pending_volume_request = None
                if self._volume_timer:
                    self._volume_timer.cancel()
                    self._volume_timer = None

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Processing pending volume immediately: {volume_request.text[:30]}...")
                self.high_priority_queue.put(volume_request)

    def stop(self):
        """Stop current speech"""
        if self.engine:
            self.engine.stop()

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        self._shutdown_flag = True
        if self.engine:
            self.engine.shutdown()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=timeout)

        if self.engine:
            return self.engine.wait_for_shutdown(timeout)
        return True

    def set_enabled(self, enabled):
        """Enable/disable TTS globally"""
        old_state = self.enabled
        self.enabled = enabled

        if enabled and not old_state:
            # Completely reinitialize TTS
            self.shutdown()
            self.wait_for_shutdown()

            # Clear queues for restart
            while not self.high_priority_queue.empty():
                try:
                    self.high_priority_queue.get_nowait()
                except queue.Empty:
                    break
            while not self.normal_priority_queue.empty():
                try:
                    self.normal_priority_queue.get_nowait()
                except queue.Empty:
                    break

            # Reset all state
            self._shutdown_flag = False
            self.engine = None
            self.available = False

            self._initialize_tts()
            self._start_worker()
            logger.error(f'TTS reinitialized - {self.engine = }')

        elif not enabled and old_state:
            # Turning OFF - shutdown gracefully
            self.shutdown()
            self.wait_for_shutdown()
            self.engine = None

    def is_available(self):
        """Check if TTS is available and enabled"""
        return self.enabled and self.available

    def get_status(self):
        """Get detailed status information"""
        engine_state = self.engine.state.name if self.engine else 'NO_ENGINE'
        return {
            'system': self.system,
            'enabled': self.enabled,
            'available': self.available,
            'engine_initialized': self.engine is not None,
            'state': engine_state,
            'high_queue_size': self.high_priority_queue.qsize(),
            'normal_queue_size': self.normal_priority_queue.qsize(),
            'pending_title': self.pending_title is not None
        }

# Demo and test code
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    tts = TTSManager()
    print("=== TTS Manager Demo ===")
    print(f"Status: {tts.get_status()}")

    # Test basic speech
    if tts.queue_speech("Hello, this is a test of the TTS system"):
        time.sleep(3)

    # Test title preservation
    print("Testing title preservation...")
    tts.queue_speech("Playing: Test Station", Priority.HIGH)
    tts.queue_speech("Title: First Song", Priority.NORMAL)  # Should be preserved
    time.sleep(2)

    # The title should play after the HIGH priority
    time.sleep(3)

    # Test rapid navigation
    print("Testing rapid navigation...")
    for i in range(5):
        tts.queue_speech(f"Station {i}", Priority.NORMAL)
        time.sleep(0.1)

    time.sleep(2)

    tts.shutdown()
    tts.wait_for_shutdown()
    print("Demo completed")
