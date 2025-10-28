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
from .common import M_STRINGS

logger = logging.getLogger(__name__)

class Priority(Enum):
    """Priority levels for speech requests"""
    NORMAL = 1    # Interruptible - navigation, titles
    HIGH = 2      # Non-interruptible - critical alerts, playback status

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

    def __init__(self, config):
        self.config = config
        self.system = platform.system()
        self.state = TTSState.IDLE
        self._current_process = None
        self._lock = threading.RLock()
        self.speech_delay = 0.3  # Anti-stutter delay

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute the speech command - to be implemented by platform-specific classes"""
        raise NotImplementedError

    def stop(self):
        """Stop current speech"""
        raise NotImplementedError

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        raise NotImplementedError

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        raise NotImplementedError

class TTSLinux(TTSBase):
    """Linux TTS implementation using user-configured command"""

    def __init__(self, config):
        super().__init__(config)
        self.retry_count = 0
        self.max_retries = 2

    def _execute_speech(self, text, priority=Priority.NORMAL):
        logger.error('\n\npriority = {}\n\n'.format(priority.name))
        """Execute speech with priority-based blocking behavior"""
        try:
            if priority == Priority.HIGH:
                # HIGH priority: blocking execution with -w flag
                cmd = ['spd-say', '-w', text]  # -w for wait
            else:
                # NORMAL priority: non-blocking execution
                cmd = ['spd-say', text]

            # Execute the command
            logger.error(f'===> waiting... "{cmd}" with {priority.name = }')
            result = subprocess.run(
                cmd,
                timeout=30,  # Safety timeout
                capture_output=True,
                text=True
            )
            logger.error(f'===> done waiting... "{cmd}" with {priority.name = }')

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
    """Windows TTS implementation"""

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute speech on Windows"""
        try:
            cmd = self.config.get_command(self.system, text)
            if isinstance(cmd, str):
                cmd = shlex.split(cmd)

            # Use Popen for process control
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                shell=True  # Needed for PowerShell on Windows
            )

            # Wait for completion
            self._current_process.wait(timeout=30)
            return True

        except subprocess.TimeoutExpired:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("Windows TTS timeout")
            if self._current_process:
                self._current_process.terminate()
            return False
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Windows TTS error: {e}")
            return False

    def stop(self):
        """Stop current speech"""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
                try:
                    self._current_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._current_process.kill()
            time.sleep(self.speech_delay)

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self.stop()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
            self._current_process = None
            self.state = TTSState.IDLE
            return True

class TTSMacOS(TTSBase):
    """macOS TTS implementation"""

    def _execute_speech(self, text, priority=Priority.NORMAL):
        """Execute speech on macOS"""
        try:
            cmd = self.config.get_command(self.system, text)
            if isinstance(cmd, str):
                cmd = shlex.split(cmd)

            # Use Popen for process control
            self._current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

            # Wait for completion
            self._current_process.wait(timeout=30)
            return True

        except subprocess.TimeoutExpired:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning("macOS TTS timeout")
            if self._current_process:
                self._current_process.terminate()
            return False
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"macOS TTS error: {e}")
            return False

    def stop(self):
        """Stop current speech"""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
                try:
                    self._current_process.wait(timeout=1)
                except subprocess.TimeoutExpired:
                    self._current_process.kill()
            # Kill any say processes that might be stuck
            subprocess.run(
                ['pkill', '-9', 'say'],
                capture_output=True
            )
            time.sleep(self.speech_delay)

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self.stop()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
            self._current_process = None
            self.state = TTSState.IDLE
            return True

class TTSManager:
    """
    Main TTS manager with priority-based queue and title preservation
    """

    def __init__(self, enabled=True):
        self.enabled = enabled
        self.config = TTSConfig()
        self.system = platform.system()
        self.available = False
        self.engine = None

        # Queue management
        self.high_priority_queue = queue.Queue()
        self.normal_priority_queue = queue.Queue()
        self.pending_title = None
        self.title_token = self.config.get_title_token()
        self.reset_tokens = self.config.get_reset_tokens()

        # Threading
        self._lock = threading.RLock()
        self._current_request = None
        self._worker_thread = None
        self._shutdown_flag = False

        # Statistics
        self._last_navigation_time = 0
        self._consecutive_requests = 0

        if self.enabled:
            self._initialize_tts()
            self._start_worker()

        # Volume
        self._pending_volume_request = None
        self._volume_timer = None
        # New lock for volume operations
        self._volume_lock = threading.RLock()

    def _initialize_tts(self):
        """Initialize TTS with proper availability checking"""
        try:
            if self.system == "Linux":
                self.available = self._check_linux_availability()
            elif self.system == "Windows":
                self.available = self._check_windows_availability()
            elif self.system == "Darwin":
                self.available = self._check_macos_availability()

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
        if self.system == "Linux":
            return TTSLinux(self.config)
        elif self.system == "Windows":
            return TTSWindows(self.config)
        elif self.system == "Darwin":
            return TTSMacOS(self.config)
        else:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"Unsupported platform: {self.system}")
            return None

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
        """Check if PowerShell TTS is available on Windows"""
        try:
            # Check PowerShell version and TTS capabilities
            ps_test = subprocess.run([
                'powershell', '-Command',
                'Get-Host | Select-Object Version'
            ], capture_output=True, timeout=10, shell=True)

            if ps_test.returncode != 0:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning("PowerShell not available or not working")
                return False

            # Test TTS functionality
            tts_test = subprocess.run([
                'powershell', '-Command',
                'Add-Type -AssemblyName System.Speech; exit 0'
            ], capture_output=True, timeout=10, shell=True)

            return tts_test.returncode == 0

        except Exception as e:
            if logger.isEnabledFor(logging.WARNING):
                logger.warning(f"Windows TTS check failed: {e}")
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

    def _process_queues(self):
        """Process speech queues with platform-specific behavior"""
        while not self._shutdown_flag:
            try:
                # 1. Process HIGH priority queue first
                try:
                    high_request = self.high_priority_queue.get(timeout=0.1)
                    logger.error('\n\n******* high_request = {}\n\n'.format(high_request))
                    self._execute_request(high_request)

                    # After HIGH completes, check for pending title
                    self._process_pending_title()
                    continue
                except queue.Empty:
                    pass

                # 2. Process NORMAL priority queue
                try:
                    normal_request = self.normal_priority_queue.get(timeout=0.1)
                    logger.error('\n\n*******  normal_request= {}\n\n'.format(normal_request))

                    # PLATFORM-SPECIFIC: Anti-stutter delay
                    if self.system == "Linux":
                        # Linux: No delay needed - speech-dispatcher handles interruptions
                        self._execute_request(normal_request)
                    else:
                        # Windows/macOS: Apply anti-stutter delay with interruption check
                        if self._wait_with_interruption(0.3):
                            self._execute_request(normal_request)

                except queue.Empty:
                    time.sleep(0.01)  # Small sleep to prevent busy waiting

            except Exception as e:
                if logger.isEnabledFor(logging.ERROR):
                    logger.error(f"Queue processing error: {e}")
                time.sleep(0.1)

    def _execute_request(self, request):
        """Execute a TTS request"""
        if not self.engine or self._shutdown_flag:
            return

        with self._lock:
            self._current_request = request
            self.engine.state = TTSState.SPEAKING

        try:
            success = self.engine._execute_speech(request.text, request.priority)
            if not success:
                if logger.isEnabledFor(logging.WARNING):
                    logger.warning(f"Failed to speak: {request.text[:50]}...")
        except Exception as e:
            if logger.isEnabledFor(logging.ERROR):
                logger.error(f"Speech execution error: {e}")
        finally:
            with self._lock:
                if self.engine.state != TTSState.SHUTTING_DOWN:
                    self.engine.state = TTSState.IDLE
                self._current_request = None

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

    def _process_pending_title(self):
        """Process pending title after HIGH priority completes"""
        if self.pending_title and not self._shutdown_flag:
            # Add pending title to normal queue
            self.normal_priority_queue.put(TTSRequest(
                self.pending_title,
                Priority.NORMAL
            ))
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f"Queued pending title: {self.pending_title[:50]}...")
            self.pending_title = None

    def _clean_normal_queue(self):
        """Clean normal priority queue during rapid navigation"""
        # Keep only the most recent request if we have too many
        if self.normal_priority_queue.qsize() > 2:
            # Drain the queue
            while not self.normal_priority_queue.empty():
                try:
                    self.normal_priority_queue.get_nowait()
                except queue.Empty:
                    break
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug("Cleaned normal priority queue due to rapid navigation")

    def queue_speech(self, text, priority=Priority.NORMAL):
        if not self.enabled or not self.available or not self.engine:
            return False

        if not text or not text.strip():
            return False

        # Volume debouncing logic
        if (priority == Priority.HIGH and
            text.startswith(M_STRINGS['volume_set'])):

            with self._volume_lock:
                # Cabcel previous timer
                if self._volume_timer:
                    self._volume_timer.cancel()

                # Save the new volume request
                self._pending_volume_request = TTSRequest(text, priority)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f"Holding volume request: {text[:30]}...")

                # Start noew timer for 500ms
                self._volume_timer = threading.Timer(0.5, self._process_pending_volume)
                self._volume_timer.daemon = True
                self._volume_timer.start()
            return True

        # If it's not volume, process any pending volume first
        with self._volume_lock:
            if self._pending_volume_request:
                self._process_pending_volume_immediately()

        request = TTSRequest(text, priority)

        try:
            if priority == Priority.HIGH:
                # HIGH priority handling
                if self._should_reset_title(text):
                    self.pending_title = None
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f"Reset pending title due to: {text[:50]}...")

                # PLATFORM-SPECIFIC: Interrupt logic
                if self.system != "Linux":  # Windows/macOS
                    # Manual interruption for non-Linux platforms
                    with self._lock:
                        if (self._current_request and
                            self._current_request.priority == Priority.NORMAL):
                            self.engine.stop()
                # Linux: No manual stop - speech-dispatcher handles it automatically

                self.high_priority_queue.put(request)
                if logger.isEnabledFor(logging.WARNING):
                    logger.debug(f"Queued HIGH priority: {text[:50]}...")
                return True

            else:  # NORMAL priority
                current_time = time.time()

                # Rate limiting for rapid navigation
                if current_time - self._last_navigation_time < 0.2:
                    self._consecutive_requests += 1
                    if self._consecutive_requests > 3:
                        self._clean_normal_queue()
                else:
                    self._consecutive_requests = 0

                self._last_navigation_time = current_time

                if self._is_title(text):
                    # Title handling - always preserve the latest title
                    self.pending_title = text
                    if logger.isEnabledFor(logging.WARNING):
                        logger.debug(f"Preserved title: {text[:50]}...")

                    # If no HIGH is playing, queue it immediately
                    if self.high_priority_queue.empty() and not self._current_request:
                        self.normal_priority_queue.put(request)
                        return True
                    return True  # Title preserved, considered successful

                else:
                    # Regular NORMAL request
                    if not self.high_priority_queue.empty() or (
                        self._current_request and
                        self._current_request.priority == Priority.HIGH
                    ):
                        # HIGH is playing or queued, reject regular NORMAL
                        if logger.isEnabledFor(logging.WARNING):
                            logger.debug("Rejected NORMAL request during HIGH playback")
                        return False
                    else:
                        self.normal_priority_queue.put(request)
                        if logger.isEnabledFor(logging.WARNING):
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
        """Forced skeep for pending volume SR before any other request"""
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
            # Turning ON - initialize if needed
            if not self.engine:
                self._initialize_tts()
                self._start_worker()
        elif not enabled and old_state:
            # Turning OFF - shutdown gracefully
            self.shutdown()
            self.wait_for_shutdown()

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
