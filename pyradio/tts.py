#!/usr/bin/env python3
"""
TTSManager - Cross-platform Text-to-Speech with User Configuration
Simplified TTS manager that uses user-configured commands for each platform.
"""

import platform
import subprocess
import threading
import time
import logging
import os
import shlex
from enum import Enum

logger = logging.getLogger(__name__)

class Priority(Enum):
    """Priority levels for speech requests"""
    NORMAL = 1    # Interruptible - navigation, feedback
    HIGH = 2      # Non-interruptible - critical alerts

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
            'RESTART_LINUX': 'systemctl --user restart speech-dispatcher'
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
            logger.info(f"Loaded TTS config from {self.config_file}")
        except FileNotFoundError:
            logger.info("No TTS config file found, using defaults")
        except Exception as e:
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

    def get_linux_restart_command(self):
        """Get the Linux restart command"""
        return shlex.split(self.config['RESTART_LINUX'])

class TTSBase:
    """Base class for TTS implementations"""

    def __init__(self, config):
        self.config = config
        self.system = platform.system()
        self.state = TTSState.IDLE
        self._current_process = None  # Will store Popen object for active process
        self._lock = threading.RLock()
        self._current_thread = None
        self.speech_delay = 0.5  # Anti-stutter delay

    def speak(self, text, priority=Priority.NORMAL):
        """Speak text with specified priority"""
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

    def speak(self, text, priority=Priority.NORMAL):
        if not text or not text.strip():
            return False

        with self._lock:
            # HIGH priority always speaks, NORMAL can be interrupted
            if priority == Priority.NORMAL and self.state == TTSState.SPEAKING:
                self.stop()

            # Start speech in a thread
            self._current_thread = threading.Thread(
                target=self._speak_thread,
                args=(text, priority),
                daemon=True
            )
            self._current_thread.start()
            return True

    def _speak_thread(self, text, priority):
        """Thread function for speech execution"""
        self.state = TTSState.SPEAKING

        try:
            # Anti-stutter delay
            delay_remaining = self.speech_delay
            while delay_remaining > 0:
                time.sleep(0.05)
                delay_remaining -= 0.05
                with self._lock:
                    if self.state == TTSState.SHUTTING_DOWN:
                        return

            # Execute speech command
            success = self._execute_speech(text)

        except Exception as e:
            logger.error(f"Speech thread error: {e}")
            success = False
        finally:
            with self._lock:
                if self.state != TTSState.SHUTTING_DOWN:
                    self.state = TTSState.IDLE
                self._current_thread = None

    def _execute_speech(self, text):
        """Execute the speech command with retry logic"""
        for attempt in range(self.max_retries + 1):
            try:
                cmd = self.config.get_command(self.system, text)
                if not cmd:
                    return False

                # Convert to list if it's a string
                if isinstance(cmd, str):
                    cmd = shlex.split(cmd)

                # Use Popen instead of run to get a process we can control
                self._current_process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                # Wait for process to complete with timeout
                try:
                    returncode = self._current_process.wait(timeout=30)
                    if returncode == 0:
                        self.retry_count = 0
                        return True
                    else:
                        logger.warning(f"TTS command failed with return code {returncode}")
                except subprocess.TimeoutExpired:
                    logger.warning("TTS command timeout")
                    self._current_process.terminate()

            except Exception as e:
                logger.error(f"TTS command error: {e}")

            # Retry logic
            if attempt < self.max_retries:
                if self._restart_speech_dispatcher():
                    time.sleep(1)  # Wait for restart
                    continue

        # All retries failed
        return False

    def _restart_speech_dispatcher(self):
        """Restart speech-dispatcher service"""
        try:
            restart_cmd = self.config.get_linux_restart_command()
            result = subprocess.run(restart_cmd, timeout=30, capture_output=True)
            if result.returncode == 0:
                logger.info("Successfully restarted speech-dispatcher")
                return True
            else:
                # Fallback to pkill for non-systemd systems
                subprocess.run(['pkill', '-9', 'speech-dispatcher'], timeout=10)
                subprocess.run(['speech-dispatcher', '-d'], timeout=10)
                logger.info("Used fallback method to restart speech-dispatcher")
                return True
        except Exception as e:
            logger.error(f"Failed to restart speech-dispatcher: {e}")
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
            # Anti-stutter delay
            time.sleep(self.speech_delay)

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self.stop()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            if self._current_thread and self._current_thread.is_alive():
                self._current_thread.join(timeout=timeout)

            # Cleanup resources
            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
            self._current_process = None
            self._current_thread = None
            self.state = TTSState.IDLE

            return True

class TTSWindows(TTSBase):
    """Windows TTS implementation"""

    def speak(self, text, priority=Priority.NORMAL):
        if not text or not text.strip():
            return False

        with self._lock:
            if priority == Priority.NORMAL and self.state == TTSState.SPEAKING:
                self.stop()

            self._current_thread = threading.Thread(
                target=self._speak_thread,
                args=(text,),
                daemon=True
            )
            self._current_thread.start()
            return True

    def _speak_thread(self, text):
        """Thread function for speech execution"""
        self.state = TTSState.SPEAKING

        try:
            # Anti-stutter delay
            time.sleep(self.speech_delay)

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

        except subprocess.TimeoutExpired:
            logger.warning("Windows TTS timeout")
            if self._current_process:
                self._current_process.terminate()
        except Exception as e:
            logger.error(f"Windows TTS error: {e}")
        finally:
            with self._lock:
                if self.state != TTSState.SHUTTING_DOWN:
                    self.state = TTSState.IDLE
                self._current_thread = None

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
            if self._current_thread and self._current_thread.is_alive():
                self._current_thread.join(timeout=timeout)

            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
            self._current_process = None
            self._current_thread = None
            self.state = TTSState.IDLE

            return True

class TTSMacOS(TTSBase):
    """macOS TTS implementation"""

    def speak(self, text, priority=Priority.NORMAL):
        if not text or not text.strip():
            return False

        with self._lock:
            if priority == Priority.NORMAL and self.state == TTSState.SPEAKING:
                self.stop()

            self._current_thread = threading.Thread(
                target=self._speak_thread,
                args=(text,),
                daemon=True
            )
            self._current_thread.start()
            return True

    def _speak_thread(self, text):
        """Thread function for speech execution"""
        self.state = TTSState.SPEAKING

        try:
            # Anti-stutter delay
            time.sleep(self.speech_delay)

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

        except subprocess.TimeoutExpired:
            logger.warning("macOS TTS timeout")
            if self._current_process:
                self._current_process.terminate()
        except Exception as e:
            logger.error(f"macOS TTS error: {e}")
        finally:
            with self._lock:
                if self.state != TTSState.SHUTTING_DOWN:
                    self.state = TTSState.IDLE
                self._current_thread = None

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
            subprocess.run(['pkill', '-9', 'say'], capture_output=True)
            time.sleep(self.speech_delay)

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        with self._lock:
            self.state = TTSState.SHUTTING_DOWN
            self.stop()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
        with self._lock:
            if self._current_thread and self._current_thread.is_alive():
                self._current_thread.join(timeout=timeout)

            if self._current_process and self._current_process.poll() is None:
                self._current_process.terminate()
            self._current_process = None
            self._current_thread = None
            self.state = TTSState.IDLE

            return True

class TTSManager:
    def __init__(self, enabled=True):
        self.enabled = enabled  # Global on/off switch
        self.config = TTSConfig()
        self.system = platform.system()
        self.available = False
        self.engine = None

        if self.enabled:
            self._initialize_tts()

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
                logger.info(f"TTS initialized successfully for {self.system}")
            else:
                logger.warning(f"TTS not available on {self.system}")

        except Exception as e:
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
                logger.warning("PowerShell not available or not working")
                return False

            # Test TTS functionality
            tts_test = subprocess.run([
                'powershell', '-Command',
                'Add-Type -AssemblyName System.Speech; exit 0'
            ], capture_output=True, timeout=10, shell=True)

            return tts_test.returncode == 0

        except Exception as e:
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
            logger.warning(f"macOS TTS check failed: {e}")
            return False

    def speak(self, text, priority=Priority.NORMAL):
        """Speak text only if TTS is enabled and available"""
        if not self.enabled:
            logger.debug("TTS speak skipped - disabled")
            return False
        if not self.available:
            logger.debug("TTS speak skipped - not available")
            return False
        if not self.engine:
            logger.debug("TTS speak skipped - no engine")
            return False

        return self.engine.speak(text, priority)

    def stop(self):
        """Stop current speech"""
        if self.engine:
            self.engine.stop()

    def shutdown(self):
        """Phase 1: Immediate shutdown (non-blocking)"""
        if self.engine:
            self.engine.shutdown()

    def wait_for_shutdown(self, timeout=2.0):
        """Phase 2: Wait for complete shutdown (blocking)"""
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
            'state': engine_state
        }

# Demo and test code
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    tts = TTSManager()
    print("=== TTS Manager Demo ===")
    print(f"Status: {tts.get_status()}")

    # Test speech
    if tts.speak("Hello, this is a test of the TTS system"):
        time.sleep(3)

    # Test interruption
    if tts.speak("This is normal priority speech"):
        time.sleep(1)
        tts.speak("This interrupts the previous speech")
        time.sleep(3)

    # Test high priority (non-interruptible)
    if tts.speak("High priority message", priority=Priority.HIGH):
        time.sleep(2)

    tts.shutdown()
    tts.wait_for_shutdown()
    print("Demo completed")
