# -*- coding: utf-8 -*-
"""
Playlist validation utilities with threading and host-aware throttling
"""
import sys
import locale
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from urllib.parse import urlparse
from collections import defaultdict
import requests

from .common import Station, RichColorPrinter

locale.setlocale(locale.LC_ALL, "")


def check_url(url, referer_url, semaphore, timeout=5, read_bytes=1024):
    """Check if URL provides actual playable audio stream using requests"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'audio/*, video/*, */*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Icy-MetaData': '1'
    }
    if referer_url:
        headers['Referer'] = referer_url

    try:
        with semaphore:
            # USE REQUESTS INSTEAD OF URLLIB
            response = requests.get(
                url,
                headers=headers,
                timeout=timeout,
                stream=True,  # Important for audio streams
                allow_redirects=True  # AUTO-REDIRECTS!
            )
            response.raise_for_status()  # Raise exception for bad status codes

            # 1. READ FIRST BYTES
            data = b''
            for chunk in response.iter_content(chunk_size=read_bytes):
                if chunk:
                    data = chunk
                    break

            # 2. CHECK FOR HTML RESPONSES
            is_html = (data.startswith(b'<html') or
                      b'<!DOCTYPE' in data or
                      b'<xml' in data or
                      b'<!' in data[:100])

            if is_html:
                return False  # Server returned HTML, not audio

            # 3. CHECK CONTENT-TYPE - MUST be audio/video
            content_type = response.headers.get('Content-Type', '').lower()
            is_media = any(media_type in content_type for media_type in
                         ['audio/', 'video/', 'application/ogg', 'application/vnd.apple.mpegurl'])

            if is_media:
                return True  # Content-Type confirms it's media

            # 4. CHECK FOR ICY METADATA (Shoutcast/Icecast)
            icy_headers = any(response.headers.get(h) for h in
                            ['icy-name', 'icy-genre', 'icy-url'])

            if icy_headers:
                return True  # ICY headers confirm it's a stream

            # 5. FINAL CHECK: VERIFY AUDIO SIGNATURES
            return detect_audio_signatures(data)

    except requests.exceptions.RequestException:
        return False
    except Exception:
        return False

def detect_audio_signatures(data):
    """Check for actual audio stream signatures"""
    # Common audio format headers
    audio_patterns = [
        (b'ID3', 0),           # MP3 metadata (start of data)
        (b'\xFF\xFB', 0),      # MP3 frame sync
        (b'\xFF\xF1', 0),      # AAC frame sync
        (b'OggS', 0),          # OGG container
        (b'fLaC', 0),          # FLAC
        (b'#EXTM3U', 0),       # HLS playlist
        (b'RIFF', 0),          # WAV
        (b'\x00\x00\x00\x18ftyp', 4),  # MP4
    ]

    for pattern, offset in audio_patterns:
        if len(data) > offset + len(pattern) and data[offset:offset+len(pattern)] == pattern:
            return True

    # For streams that might not have clear headers, check for non-text data
    if len(data) > 100:
        text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x100)) - {0x7f})
        is_likely_binary = bool(data.translate(None, text_chars))
        return is_likely_binary

    return False

def print_statistics(total_count, online_count, groups_count, printer):
    """
    Print validation statistics with centered alignment
    """
    # Calculate statistics
    stations_count = total_count - groups_count
    offline_count = stations_count - online_count
    success_rate = (online_count / stations_count * 100) if stations_count > 0 else 0

    # Define all labels and values
    stats_data = [
        ("Online Stations:", online_count),
        ("Offline Stations:", offline_count),
        ("Groups:", groups_count),
        ("Total Stations:", stations_count),
        ("Total Items:", total_count)
    ]

    # Find maximum widths
    max_label_width = max(len(label) for label, _ in stats_data)
    max_number_width = max(len(str(value)) for _, value in stats_data)
    max_success_width = len(f"{success_rate:.1f}%")

    # Calculate total block width and padding
    total_block_width = max_label_width + 1 + max_number_width
    left_padding = (50 - total_block_width) // 2

    # Center title
    title = "VALIDATION SUMMARY"
    title_padding = (50 - len(title)) // 2

    printer("[cyan]" + "="*50 + "[/cyan]")
    printer(" " * title_padding + f"[bold]{title}[/bold]")
    printer("[cyan]" + "="*50 + "[/cyan]")

    # Print each statistic line
    for label, value in stats_data:
        padded_label = label.rjust(max_label_width)
        line = " " * left_padding + f"[green]{padded_label}[/green] [cyan]{value}[/cyan]"
        printer(line)

    # Center separator
    printer("[cyan]" + "-"*50 + "[/cyan]")

    # Center success rate
    success_label = "Success Rate:"
    padded_label = success_label.rjust(max_label_width)
    success_line = " " * left_padding + f"[bold]{padded_label}[/bold] [cyan]{success_rate:.1f}%[/cyan]"
    printer(success_line)

    printer("[cyan]" + "="*50 + "[/cyan]")

def check_playlist(file_path, mode="mark", threads=5, timeout=5, max_per_host=2, with_date=False, no_color=False, verbose=True):
    """Validate a CSV or M3U playlist with host-aware throttling"""

    items = []
    input_type = None

    # Create printer instance
    printer = RichColorPrinter(use_color=not no_color)

    if file_path.endswith(".csv"):
        from .common import CsvReadWrite
        reader = CsvReadWrite(file_path)
        if not reader.read():
            raise RuntimeError("Error reading CSV")
        items = reader.items
        input_type = "csv"

    elif file_path.endswith(".m3u"):
        from .m3u import parse_m3u
        items, error = parse_m3u(file_path)
        if error:
            printer(f'[red]Error:[/red] {error}')
            sys.exit(1)
        input_type = "m3u"

    else:
        raise ValueError("Unsupported file type")

    # Generate timestamp if requested
    timestamp = ""
    if with_date:
        from datetime import datetime
        timestamp = datetime.now().strftime("-%Y-%m-%d-%H-%M-%S")

    printer(f"[cyan]Checking {len(items)} stations using {threads} threads...[/cyan]")

    # --- host-aware throttling setup ---
    host_map = defaultdict(list)
    for idx, st in enumerate(items):
        host = urlparse(st[Station.url]).hostname
        host_map[host].append((idx, st))

    host_semaphores = {host: threading.BoundedSemaphore(max_per_host) for host in host_map}

    # --- threaded check ---
    results_dict = {}   # idx -> (station, ok_flag)
    futures = {}

    with ThreadPoolExecutor(max_workers=threads) as executor:
        for idx, st in enumerate(items):
            # Check if it's a group header
            if st[Station.url] == '-':  # Group header
                results_dict[idx] = (st, True)  # Use None for group headers
                if verbose:
                    printer(f"[cyan]{idx+1}[/cyan]. [cyan]GROUP[/cyan] {st[Station.name]}")
                continue

            # do not check group headers
            url = st[Station.url].replace('https://', 'http://') if st[Station.http] else st[Station.url]
            semaphore = host_semaphores[urlparse(url).hostname]
            futures[executor.submit(check_url, url, st[Station.referer], semaphore, timeout, 1024)] = (idx, st)

        for future in as_completed(futures):
            idx, st = futures[future]
            ok = False
            try:
                ok = future.result()
            except Exception:
                ok = False

            # store result in dict
            results_dict[idx] = (st, ok)

            # print immediately
            if verbose:
                if ok:
                    printer(f"[green]{idx+1}[/green]. [green]OK[/green] {st[Station.name]} ({st[Station.url]})")
                else:
                    printer(f"[red]{idx+1}[/red]. [red]BROKEN[/red] {st[Station.name]} ({st[Station.url]})")

    # --- collect results in original order ---
    ok_items, bad_items = [], []
    for idx in range(len(items)):
        st, ok_flag = results_dict[idx]
        if ok_flag:
            ok_items.append(st)
        else:
            bad_items.append(st)

    # --- drop mode ---
    if mode == "drop":
        ok_file = f"{file_path}.ok{timestamp}.{input_type}"
        bad_file = f"{file_path}.bad{timestamp}.{input_type}"
        if input_type == "csv":
            from .common import CsvReadWrite
            ret = CsvReadWrite(ok_file).write(items=ok_items)
            if ret < 0:
                printer(f'[red]Error:[/red] Cannot write "{ok_file}".')
                sys.exit(1)
            printer(f'[green]Saved working stations to "{ok_file}"[/green]')
            ret = CsvReadWrite(bad_file).write(items=bad_items)
            if ret < 0:
                printer(f'[red]Error:[/red] Cannot write "{bad_file}".')
                sys.exit(1)
            printer(f'[yellow]Saved failed stations to "{bad_file}"[/yellow]')
        else:
            from .m3u import list_to_m3u
            error = list_to_m3u(ok_items, ok_file)
            if error:
                printer(f'[red]Error:[/red] Cannot write "{ok_file}"\n:  [red]{error}[/red].')
                sys.exit(1)
            printer(f'[green]Saved working stations to "{ok_file}"[/green]')
            error = list_to_m3u(bad_items, bad_file)
            if error:
                printer(f'[red]Error:[/red] Cannot write "{bad_file}"\n:  [red]{error}[/red].')
                sys.exit(1)
            printer(f'[yellow]Saved failed stations to "{bad_file}"[/yellow]')

        print_statistics(
            len(items),
            len(ok_items),
            sum(1 for st in items if st[Station.url] == '-'),
            printer
        )

        return

    # --- mark mode (default) ---
    marked_items = []
    for idx, st in enumerate(items):
        _, ok_flag = results_dict[idx]
        if not ok_flag:
            st = list(st)  # make copy
            st[Station.name] = "[X] " + st[Station.name]
        marked_items.append(st)

    out_file = f"{file_path}.validated{timestamp}.{input_type}"
    if input_type == "csv":
        from .common import CsvReadWrite
        ret = CsvReadWrite(out_file).write(items=marked_items)
        if ret < 0:
            printer(f'[red]Error:[/red] Cannot write "{out_file}".')
            sys.exit(1)
    else:
        from .m3u import list_to_m3u
        error = list_to_m3u(marked_items, out_file)
        if error:
            printer(f'[red]Error:[/red] Cannot write "{out_file}".')
            sys.exit(1)

    group_count = sum(1 for st in items if st[Station.url] == '-')
    online_count = sum(1 for st in marked_items
                  if st[Station.url] != '-' and not st[Station.name].startswith("[X]"))
    print_statistics(
        len(items),
        online_count,
        group_count,
        printer
    )

    printer(f'[cyan]Validation results written to "{out_file}"[/cyan]')
