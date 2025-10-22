import os
import time
import subprocess
import threading
import locale
import logging
import hashlib
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
from os.path import exists, join
try:
    # Python ≥ 3.9
    from importlib.resources import files, as_file
except ImportError:
    # Python 3.7–3.8 (backport)
    from importlib_resources import files, as_file
from .common import get_cached_icon_path

locale.setlocale(locale.LC_ALL, "")

logger = logging.getLogger(__name__)

class DummyIconManager:
    def __init__(self):
        self.needs_redraw = False

    def on_station_change(self, win, station, operation_mode, screen_size, icon_size, icon_duration, adjust_for_radio_browser):
        # if logger.isEnabledFor(logging.DEBUG):
        #     logger.debug('Not a graphical terminal; cannot display icon...')
        return None

class SimpleIconManager:
    """
    NO THREADS - everything happens in main thread
    """

    def __init__(self, terminal_buffer, terminal, programs, normal_mode, cache_dir="~/.cache/pyradio/logos/"):
        self._last_cleared_operation_mode = -2
        self.stdrc = terminal_buffer
        self.run = None
        self.needs_redraw = False
        self.icon_downloader = TerminalIconDownloader()
        self.icon_is_on = False
        self.terminal = terminal
        self.programs = programs
        self.normal_mode = normal_mode
        self.cache_dir = os.path.expanduser(cache_dir)
        self.last_station_id = None
        self.last_icon_check = 0
        self.Y = self.X = self.old_Y = self.old_X = 0
        self.old_icon_url = None
        self.old_station_id = None
        self.old_adjust_for_radio_browser = None

    def on_station_change(self, win, station, operation_mode, screen_size, icon_size, icon_duration, adjust_for_radio_browser):
        """
        Call this from your main keypress handler
        Returns quickly - never blocks
        """
        self.needs_redraw = False
        if self.terminal is None:
            return None
        # Skip if disabled or wrong mode
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{station = }')
        if icon_duration == 0 or \
                icon_size == 0 or \
                station is None or \
                operation_mode != self.normal_mode:
            if logger.isEnabledFor(logging.DEBUG):
                logger.error(f'{icon_duration =  }')
                logger.error(f'{icon_size =  }')
                logger.error(f'{station =  }')
                logger.error(f'{operation_mode =  }')
                logger.debug('clearing icon 1\n\n')
            self.clear_icon()
            return datetime.now()

        self._win = win
        self.Y, self.X = screen_size
        station_id = station[0].strip()
        icon_url = station[3].strip()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'Checking {icon_url = }')

        if self.Y != self.old_Y or self.X != self.old_X or \
                icon_url != self.old_icon_url or \
                adjust_for_radio_browser != self.old_adjust_for_radio_browser:
            # if any of the parameters have changed
            # clear the existing icon
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('parameters changed, clearing previous icon')
            # if icon_url and station:
            #     if logger.isEnabledFor(logging.DEBUG):
            #         logger.debug('clearing icon 2')
            #     self.clear_icon()
        if not icon_url:
            # clear previous icon
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug('no URL, clearing previous icon')
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'clearing icon 3: {self._last_cleared_operation_mode = } / {operation_mode = }')
                logger.error(f'{self.icon_is_on = }')
            # if self._last_cleared_operation_mode != operation_mode \
            #         or self.icon_is_on:
            #     self.clear_icon(force=self.terminal != 'kitty')
            if self.icon_is_on:
                self.clear_icon(force=self.terminal != 'kitty')
            # self.clear_icon(force=self.terminal != 'kitty')
            self._last_cleared_operation_mode = operation_mode
            return datetime.now()

        # Check cache first (fast)
        cached_path = get_cached_icon_path(self.cache_dir, station_id, icon_url)
        failed_path = cached_path + '.failed'  # NEW: Check for failed downloads

        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f'{cached_path = }')

        if os.path.exists(cached_path):
            self._display_icon_simple(cached_path, icon_size, adjust_for_radio_browser)
            self.old_station_id = station_id
            self.old_icon_url = icon_url
            self.old_Y = self.Y
            self.old_X = self.X
            self.old_adjust_for_radio_browser = adjust_for_radio_browser
        elif os.path.exists(failed_path):  # NEW: Display failure icon
            # Display failure icon
            failure_res = files('pyradio').joinpath('icons', 'failure.png')
            try:
                if exists(str(failure_res)):
                    failure_icon = str(failure_res)
                else:
                    cached_failure_path = join(self.cache_dir, 'failure.png')
                    if not os.path.exists(cached_failure_path):
                        with as_file(failure_res) as temp_icon:
                            import shutil
                            shutil.copy2(str(temp_icon), cached_failure_path)
                    failure_icon = cached_failure_path

                self._display_icon_simple(
                    failure_icon,
                    icon_size,
                    adjust_for_radio_browser
                )
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Could not display failure placeholder: {e}')
            self.icon_is_on = True
        else:
            # request icon downloading
            self.icon_downloader.download_icon_async(icon_url, cached_path)

            # display downloading icon
            download_token_res = files('pyradio').joinpath('icons', 'download.png')

            # First check if it's already a real file in the filesystem
            self._last_cleared_operation_mode = -2
            try:
                # Try to use it directly if it exists as a real file
                if exists(str(download_token_res)):
                    download_token_icon = str(download_token_res)
                else:
                    # It's in zip/wheel - use cached version
                    cached_download_path = join(self.cache_dir, 'download.png')
                    if not os.path.exists(cached_download_path):
                        with as_file(download_token_res) as temp_icon:
                            import shutil
                            shutil.copy2(str(temp_icon), cached_download_path)
                    download_token_icon = cached_download_path

                self._display_icon_simple(
                    download_token_icon,
                    icon_size,
                    adjust_for_radio_browser
                )
            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Could not display download placeholder: {e}')
            self.icon_is_on = True
            return datetime.now()

    def _display_icon_simple(self, icon_path, icon_size, adjust_for_radio_browser=None):
        """Display icon - main thread only, quick and safe"""
        min_icon_size = 4
        retries = 5
        cursor_saved = False

        try:
            half = icon_size // 2
            logger.error(f'====== {icon_size = }')
            logger.error(f'       {self.Y = }')
            logger.error(f'       {half = }')
            icon_Y = 3 if adjust_for_radio_browser else 2
            while half >= self.Y - icon_Y - 2:
                icon_size -= 2
                if icon_size <= min_icon_size:
                    break
                half = icon_size // 2

            icon_X = self.X - icon_size - 1
            while icon_X <= 30:
                icon_size -= 2
                if icon_size <= min_icon_size:
                    break
                icon_X = self.X - icon_size - 1
            half = icon_size // 2

            icon_X = self.X - icon_size - 1
            if icon_size < min_icon_size:
                self.clear_icon()
                return

            logger.error(f'{icon_size = }')

            # Cursor save with retry logic
            for attempt in range(retries):  # Try retries times
                try:
                    subprocess.run(['tput', 'sc'], check=True, timeout=1)
                    cursor_saved = True
                    break  # Success - exit retry loop
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    if attempt == retries-1:  # Final attempt failed
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'tput sc failed after {retries} attempts')
                        self.clear_icon()
                        return
                    time.sleep(0.1)  # Wait before retry

            # Only continue if cursor was successfully saved
            if not cursor_saved:
                self.clear_icon()
                return

            for attempt in range(retries):  # Try retries times
                try:
                    subprocess.run(['tput', 'civis'], check=True, timeout=1)
                    break  # Success - exit retry loop
                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    if attempt == retries-1:  # Final attempt failed
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'tput civis failed after {retries} attempts')
                        # Continue anyway - this is not critical

            # Attempt cursor positioning with verification
            position_success = False
            for attempt in range(retries):
                try:
                    # Set position
                    subprocess.run(['tput', 'cup', str(icon_Y), str(icon_X)],
                                 check=True, timeout=1)
                    time.sleep(0.02)

                    # Verify position (you need to implement get_cursor_position)
                    current_y, current_x = self.get_cursor_position()
                    if (current_y, current_x) == (icon_Y, icon_X):
                        position_success = True
                        break  # Success!
                    else:
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'Cursor verification failed: expected ({icon_Y},{icon_X}), got ({current_y},{current_x})')

                except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
                    if attempt == retries-1:  # Last attempt
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'Cursor positioning failed after {retries} attempts')
                        self.clear_icon()
                        return

            # Only display image if positioning was successful
            if position_success:
                params = self._build_icon_command(icon_path, icon_size, icon_X, icon_Y)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug('Executing: {}'.format(' '.join(params)))
                subprocess.run(params, stderr=subprocess.DEVNULL, timeout=5)
                self.icon_is_on = True

        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Exception in _display_icon_simple: {e}')
            self.clear_icon()
        finally:
            # Cursor management - Restore only if we saved it
            if cursor_saved:
                try:
                    subprocess.run(['tput', 'rc'], check=True)  # Restore cursor
                    subprocess.run(['tput', 'civis'], check=True)  # Keep hidden
                except Exception as e:
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Cursor restore exception: {e}')

    def get_cursor_position(self):
        """Get current cursor position (row, col) - returns 0-based coordinates"""
        try:
            import termios
            import tty
            import sys

            old_settings = termios.tcgetattr(sys.stdin)

            try:
                tty.setraw(sys.stdin.fileno())
                sys.stdout.write('\033[6n')
                sys.stdout.flush()

                response = ''
                while True:
                    char = sys.stdin.read(1)
                    response += char
                    if char == 'R':
                        break

                import re
                match = re.search(r'\033\[(\d+);(\d+)R', response)
                if match:
                    # Convert from 1-based to 0-based
                    row = int(match.group(1)) - 1
                    col = int(match.group(2)) - 1
                    return row, col

            finally:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)

        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Cursor position query failed: {e}')
        return None, None

    def _build_icon_command(self, icon_path, icon_size, icon_X, icon_Y):
        """Build timg command for ALL terminals"""
        base_params = [
            'timg',
            '-b', '#0000ff',  # Blue background
            '-W',             # Fit width
            '-U',             # Upscale
            '-I',             # Force image mode
            '-g', f'{icon_size}x{icon_size}',
            icon_path
        ]
        return base_params

        """Build the appropriate command based on terminal type and available programs"""
        terminal = self.terminal

        if terminal == 'kitty':
            return [
                'kitten', 'icat', '--scale-up', '--no-trailing-newline',
                '--place', f'{icon_size}x{icon_size}@{icon_X}x{icon_Y}',
                icon_path
            ]

        elif terminal == 'iterm2':
            program_key = self.programs['iterm2']
            if program_key == 'imgcat':
                return ['imgcat', icon_path]
            elif program_key == 'timg':
                return ['timg', icon_path]  # Auto-detects iTerm2
            elif program_key == 'viu':
                return ['viu', icon_path]   # Auto-detects iTerm2
            elif program_key == 'chafa':
                return ['chafa', '--protocol', 'iterm', icon_path]

        elif terminal in ['foot', 'mlterm', 'contour', 'xterm']:  # Sixel terminals
            program_key = self.programs['sixel']
            if program_key == 'timg':
                return ['timg', '-b', '#444444',  '-W', '-U', '-ps', '-g', f'{icon_size}x{icon_size}', icon_path]
            elif program_key == 'chafa':
                return ['chafa', '--size', f'{icon_size}x{icon_size}', icon_path]
            elif program_key == 'viu':
                return ['viu', '-s', f'{icon_size}x{icon_size}', icon_path]
            elif program_key == 'catimg':
                return ['catimg', '-w', str(icon_size), icon_path]
            elif program_key == 'img2sixel':
                return ['img2sixel', '-w', str(icon_size), icon_path]

        elif terminal == 'wezterm':
            program_key = self.programs['iterm2']  # Uses iTerm2 protocol
            if program_key == 'imgcat':
                return ['wezterm', 'imgcat', icon_path]
            elif program_key == 'timg':
                return ['timg', icon_path]
            elif program_key == 'viu':
                return ['viu', icon_path]

        elif terminal == 'terminology':
            return ['tycat', '--size', f'{icon_size}x{icon_size}', icon_path]

        return None  # No supported terminal/program

    def clear_icon(self, force=False):
        """Clear icon using terminal-specific methods"""
        if force or self.icon_is_on:
            logger.error('icon is on!')
            try:
                if self.terminal == 'kitty':
                    # For Kitty - this is the only thing that works
                    subprocess.run([
                        'kitten', 'icat', '--clear'
                    ], stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL, timeout=2)
                    self.needs_redraw = False
                    self.icon_is_on = False
                else:
                    # For all terminals - redraw
                    self.needs_redraw = True

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Icon clear for {self.terminal}')

            except Exception as e:
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Clear exception: {e}')
                # Fallback for all (except kitty)
                self.needs_redraw = True
        else:
            logger.error('icon if off!')

    def shutdown(self, wait=False):
        """Close the thread pool"""
        self.icon_downloader.shutdown(wait=wait)


class TerminalIconDownloader:
    def __init__(self):
        self.executor = ThreadPoolExecutor()
        self.downloaded_icons = set()  # Track what we've downloaded
        self.lock = threading.Lock()

    def download_icon_async(self, icon_url, icon_path):
        """Add download to the thread pool"""
        # NEW: Skip if already failed
        if os.path.exists(icon_path + '.failed'):
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Skipping download - previously failed: {icon_url}')
            return

        # Check if already downloaded or downloading
        with self.lock:
            if (icon_url, icon_path) in self.downloaded_icons:
                return
            self.downloaded_icons.add((icon_url, icon_path))

        # Submit task to the thread pool
        self.executor.submit(self._download_icon, icon_url, icon_path)

    def _download_icon(self, icon_url, icon_path):
        """Real download (runs in a background thread)"""
        try:
            if not os.path.exists(icon_path):
                # Use the existing download logic
                success = self._download_station_image(icon_url, icon_path)

                # NEW: If successful, remove any .failed file
                if success:
                    failed_path = icon_path + '.failed'
                    if os.path.exists(failed_path):
                        os.remove(failed_path)
                        if logger.isEnabledFor(logging.DEBUG):
                            logger.debug(f'Removed failed marker: {failed_path}')

                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Background download: {icon_url} - {success}')
        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Background download failed: {e}')

    def _download_station_image(self, url, file_to_write):
        """
        Copy of your existing download logic from _thread_download_station_image
        but simplified for this use case
        """
        try:
            import requests
            from os import rename, remove
            from tempfile import NamedTemporaryFile

            # Skip if already exists (double-check)
            if exists(file_to_write):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'File already exists: {file_to_write}')
                return True

            # NEW: Check if this URL has previously failed
            failed_path = file_to_write + '.failed'
            if exists(failed_path):
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'URL previously failed: {url}')
                return False

            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Starting download: {url} -> {file_to_write}')

            # Download the image
            response = requests.get(url, timeout=10)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Response status: {response.status_code}')

            if response.status_code == 200:
                # Determine file extension from path
                ext = os.path.splitext(file_to_write)[1]

                # Get the target directory for the temporary file
                target_dir = os.path.dirname(file_to_write)

                # Use temporary file in the SAME directory to avoid cross-filesystem issues
                with NamedTemporaryFile(delete=False, suffix=ext, dir=target_dir) as temp_file:
                    for chunk in response.iter_content(chunk_size=128):
                        temp_file.write(chunk)
                    temp_path = temp_file.name
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Temporary file created: {temp_path}')

                # Rename to final name - now it should work since they're on same filesystem
                rename(temp_path, file_to_write)
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'File successfully saved: {file_to_write}')
                return True
            else:
                # NEW: Create .failed file for HTTP errors
                if logger.isEnabledFor(logging.DEBUG):
                    logger.debug(f'Download failed with status: {response.status_code}')
                open(failed_path, 'w').close()  # Create empty .failed file
                return False

        except Exception as e:
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Download failed for {url}: {e}')
            # NEW: Create .failed file for any exception
            try:
                failed_path = file_to_write + '.failed'
                open(failed_path, 'w').close()
            except:
                pass
            # Clean up temporary file if it exists
            try:
                if 'temp_path' in locals() and exists(temp_path):
                    remove(temp_path)
                    if logger.isEnabledFor(logging.DEBUG):
                        logger.debug(f'Cleaned up temp file: {temp_path}')
            except:
                pass
        return False

    def shutdown(self, wait=False):
        """Close the thread pool"""
        self.executor.shutdown(wait=wait)

    def clear_failed_downloads(self, station_id, icon_url):
        """Clear failed download marker to allow retry"""
        cached_path = get_cached_icon_path(self.cache_dir, station_id, icon_url)
        failed_path = cached_path + '.failed'
        if os.path.exists(failed_path):
            os.remove(failed_path)
            if logger.isEnabledFor(logging.DEBUG):
                logger.debug(f'Cleared failed marker for retry: {failed_path}')

