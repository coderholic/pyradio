# -*- coding: utf-8 -*-
import sys
import os
import subprocess
import re
from shutil import which
from datetime import datetime, timedelta
from glob import glob
import locale
import logging

locale.setlocale(locale.LC_ALL, "")
logger = logging.getLogger(__name__)
HAS_RICH = False
if sys.version_info.major >= 3:
    from rich.console import Console
    from rich.table import Table
    from rich.align import Align
    from rich import print
    HAS_RICH = True

class MKVToolNix:

    HAS_MKVTOOLNIX = False

    mkvmerge = None
    mkvinfo = None
    mkvpropedit = None

    _srt = False
    _chapters = False
    _cover_file = None
    _remove_file = []

    def __init__(self, stations_dir=None):
        self._stations_dir = None
        if stations_dir is not None:
            self._stations_dir = stations_dir
        self._look_for_mkvtoolnix()

    @property
    def mkv_file(self):
        return self._mkv_file

    @mkv_file.setter
    def mkv_file(self, val):
        try:
            x = int(val)
            self._mkv_file = self._get_mkv_file_from_id(x)
        except ValueError:
            self._mkv_file = self._file_valid(val)
        if self._mkv_file:
            self._command = [
                self.mkvpropedit,
                self._mkv_file
            ]

    @property
    def cover_file(self):
        return self._cover_file

    @cover_file.setter
    def cover_file(self, val):
        self._cover_file = self._file_valid(val)

    @property
    def chapters(self):
        return self._chapters

    @chapters.setter
    def chapters(self, val):
        self._chapters = val

    @property
    def srt(self):
        return self._srt

    @srt.setter
    def srt(self, val):
        self._srt = val

    def execute(self, print_messages=True):
        if print_messages:
            print('MKV file: "{}"'.format(os.path.basename(self._mkv_file)))
            folder = os.path.dirname(self._mkv_file)
            if folder:
                print('  Folder: "{}"'.format(os.path.dirname(folder)))
        if self._cover_file and self._command:
            self.update_cover()

        ret = True
        if self._command and self._cover_file:
            ret = False

        if self._command and self._chapters:
            ret = False
            self.srt_to_chapters()

        # MKV shapters to SRT
        if self._srt:
            self._srt_file = self._mkv_file.replace('.mkv', '.srt')
            self.chapters_to_srt()

        if len(self._command) > 2:
            ret = self._execute()
        return ret

    def _execute(self, print_messages=True):
        # execute command
        r = subprocess.Popen(
            self._command,
            stdout=subprocess.PIPE).stdout.read()
        if sys.version_info.major < 3:
            s = r
        else:
            s = r.decode('utf-8')
        if print_messages:
            print(s)
        # remove temporary files
        if self._remove_file:
            for n in self._remove_file:
                os.remove(n)

    def list_mkv_files(self):
        files = self._get_mkv_file_from_id(0, return_list=True)

        if files:
            if HAS_RICH:
                console = Console()

                table = Table(show_header=True, header_style="bold magenta")
                table.title = 'List of files under [bold magenta]recordings[/bold magenta]'
                table.title_justify = "left"
                table.row_styles = ['', 'plum4']
                centered_table = Align.center(table)
                table.add_column("#", justify="right")
                table.add_column("Name")
                for i, n in enumerate(files):
                    table.add_row(str(i+1), os.path.basename(n))
                console.print(centered_table)
            else:
                print('List of files under "recordings"')
                pad = len(str(len(files)))
                for i, n in enumerate(files):
                    print('{0}. {1}'.format(
                        str(i+1).rjust( pad ),
                        os.path.basename(n)
                        )
                    )
        else:
            print('No recorded files found!')

    def _get_mkv_file_from_id(self, index, return_list=False, print_messages=True):
        if index >= 0:
            index -= 1
        files = glob(os.path.join(
            self._stations_dir, 'recordings', '*.mkv'
            )
        )
        if files:
            files.sort()
        if return_list:
            return files
        try:
            return files[index]
        except IndexError:
            if print_messages:
                if HAS_RICH:
                    print('[red]Error:[/red] Index {} not found!'.format(index))
                else:
                    print('Error: Index {} not found!'.format(index))
                sys.exit(1)
            return None

    def _file_valid(self, a_file, print_messages=True):
        if not os.path.exists(a_file):
            for n in 'recordings', 'data':
                test_file = os.path.join(
                        self._stations_dir,
                        n,
                        a_file)
                if os.path.exists(test_file):
                    return test_file
            if print_messages:
                print('File not found: "{}"'.format(a_file))
                sys.exit(1)
            else:
                return None
        return a_file

    def update_cover(self, print_messages=True):
        if not self.HAS_MKVTOOLNIX:
            if print_messages:
                print('  MKVToolNix not found...')
                sys.exit(1)
            else:
                return None
        if print_messages:
            if HAS_RICH:
                print('[magenta]Setting MKV file cover image...[/magenta]')
            else:
                print('Setting MKV file cover image...')
        self._cover_file = self._file_valid(self._cover_file)
        # scan MKV file for existing cover
        r = subprocess.Popen(
            [self.mkvmerge, '-i', self._mkv_file ],
            stdout=subprocess.PIPE).stdout.read()
        if sys.version_info.major < 3:
            s = r
        else:
            s = r.decode('utf-8')
        # Validate files
        if 'container: Matroska' not in s:
            if print_messages:
                print('  File not supported: "{}"'.format(out[0]))
                sys.exit(1)
            else:
                return None
        if not self._cover_file.endswith('.png'):
            if print_messages:
                print('  File not supported: "{}"'.format(out[1]))
                sys.exit(1)
            else:
                return None
        if print_messages:
            print('  (r) PNG file: "{}"'.format(self._cover_file))
        r = re.compile(r"Attachment ID ([0-9]*): type 'image/png', size [0-9]* bytes, file name 'cover'")
        cov = re.search(r, s)
        att = cov.group(1) if cov else -1
        # build command
        self._command.append('--attachment-mime-type')
        self._command.append('image/png',)
        self._command.append('--attachment-name')
        self._command.append('cover')
        if att == -1:
            self._command.append('--add-attachment')
            self._command.append(self._cover_file)
        else:
            self._command.append('--replace-attachment')
            self._command.append(str(att) + ':' + self._cover_file)

    def chapters_to_srt(self, print_messages=True):
        if print_messages:
            if HAS_RICH:
                print('[magenta]Chapters to SRT[/magenta]')
            else:
                print('Chapters to SRT')
        chapters = self._read_chapters(self._mkv_file)
        if chapters:
            out = []
            for i, n in enumerate(chapters):
                out.append(str(i+1))
                out.append(
                        n[0].replace('.', ',') + \
                        ' --> ' +
                        self._add_seconds(n[0].replace('.', ','))
                )
                out.append(n[1])
                out.append('')
            try:
                with open(self._srt_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(out))
            except:
                if print_messages:
                    print('  Error writing file: "{}"'.format(self._srt_file))
                else:
                    return None
        else:
            if print_messages:
                print('  No chapters found...')
                sys.exit(1)
            else:
                return None
        if print_messages:
                print('  (w) SRT file: "{}"'.format(os.path.basename(self._srt_file)))
        else:
            return self._srt_file

    def _add_seconds(self, a_str, seconds=5):
        s_time, s_mili = a_str.split(',')
        t_object = datetime.strptime('2023-10-10 ' + s_time, '%Y-%m-%d %H:%M:%S')
        new_time = t_object + timedelta(seconds=seconds)
        s_time = new_time.strftime('%H:%M:%S')
        return s_time + ',' + s_mili

    def _look_for_mkvtoolnix(self):
        self.HAS_MKVTOOLNIX = False
        if sys.platform.lower().startswith('win'):
            s_path = (
                    r'C:\Program Files\MKVToolNix\mkvmerge.exe',
                    r'C:\Program Files (x86)\MKVToolNix\mkvmerge.exe',
                    os.path.join(self._stations_dir, 'mkvtoolnix', 'mkvmerge.exe')
                    )
            for n in s_path:
                if os.path.exists(n):
                    self.mkvmerge = n
                    self.HAS_MKVTOOLNIX = True
                    break
        else:
            p = subprocess.Popen(
                    'which mkvmerge',
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                    )
            r = p.communicate()
            self.HAS_MKVTOOLNIX = True if p.returncode == 0 else False
            if self.HAS_MKVTOOLNIX:
                if sys.version_info.major < 3:
                    self.mkvmerge = r[0].strip()
                else:
                    self.mkvmerge = r[0].decode('utf-8').strip()
            if not self.HAS_MKVTOOLNIX and sys.platform.lower().startswith('dar'):
                mkvmerge_file = os.path.join(stations_dir, 'data', 'mkvmerge')
                if os.path.exists(mkvmerge_file):
                    self.HAS_MKVTOOLNIX = True
                    self.mkvmerge = mkvmerge_file
        if self.HAS_MKVTOOLNIX:
            self.mkvinfo = self.mkvmerge.replace('mkvmerge', 'mkvinfo')
            self.mkvpropedit = self.mkvmerge.replace('mkvmerge', 'mkvpropedit')

    def _read_chapters(self, a_file, encoding='utf-8'):
        self.playlist = None
        try:
            r = subprocess.Popen(
                [self.mkvinfo, a_file ],
                stdout=subprocess.PIPE).stdout.read()
            if sys.version_info.major < 3:
                s = r
            else:
                s = r.decode(encoding)
        except:
            return None
        if s:
            if r'|+ Chapters' not in s:
                return None
            out = []
            search_str=('Chapter time start: ', 'Chapter string: ')
            for i, n in enumerate(search_str):
                ex = re.compile(n + r'[^\n]*')
                out.append(ex.findall(s))
                if len(out[0]) < 3:
                    return None
            out[0] = [x[:-6] for x in out[0]]
            for n in 0, 1:
                out [n] = [ x[len(search_str[n]):] for x in out[n] ]
            self.playlist = out[1][0]
            return list(zip(out[0], out[1]))
        return None

    def srt_to_chapters(self, print_messages=True):
        if print_messages:
            if HAS_RICH:
                print('[magenta]Updating MKV chapters...[/magenta]')
            else:
                print('Setting MKV file cover image...')
        srt_file = self._mkv_file[:-4] + '.srt'
        if print_messages:
            print('  (r) SRT file: "{}"'.format(os.path.basename(srt_file)))
        txt_file = self._mkv_file[:-4] + '.txt'
        if os.path.exists(srt_file):
            with open(srt_file, 'r', encoding='utf-8') as f:
                l = f.readlines()
        else:
            if print_messages:
                if HAS_RICH:
                    print('[red]Error:[/red] [bold magenta]SRT[/bold magents] file not found: "{}"'.format(srt_file))
                else:
                    print('Error: SRT file not found: "{}"'.format(srt_file))
                sys.exit(1)
            else:
                return None
        times = []
        titles = []
        for n in range(1,len(l),4):
            times.append(l[n].strip())
            titles.append(l[n+1].strip())

        ziped = list(zip([x.split()[0].replace(',', '.') for x in times],titles))

        out = []
        outs = 'CHAPTER{0:02}={1}\nCHAPTER{0:02}NAME={2}'
        for i, n in enumerate(ziped):
            out.append(outs.format(i+1, n[0], n[1]))

        try:
            with open(txt_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(out))
        except:
            if print_messages:
                if HAS_RICH:
                    print('[red]Error:[/red] Cannot write [bold magenta]Chapters[/bold magents] file "{}"'.format(txt_file))
                else:
                    print('Error: Cannot write Chapters file: "{}"'.format(txt_file))
                sys.exit(1)
            else:
                return None
        self._command.append('-c')
        self._command.append(txt_file)
        self._remove_file.append(txt_file)
        return txt_file


if __name__ == '__main__':
    x = MKVToolNix(stations_dir='/home/spiros/.config/pyradio')
    # print(x._get_mkv_file_from_id(1))
    x.list_mkv_files()
