from os import path, getenv, makedirs, remove, rename, readlink, SEEK_END, SEEK_CUR, environ, getpid, listdir, rmdir, walk
from sys import platform, exit
from rich import print
from shutil import copy, copyfile, move, Error as shutil_Error, rmtree as remove_tree
import logging

from platform import system
if not system().lower() == 'windows':
    from os import getuid

data_files = [
    'INSTALLATION_TYPE',
    'pyradio.png',
    'cover.png',
    'schedule.json',
    'player-params.json',
    'radio-browser-search-terms',
]

state_files = [
    '.date',
    '.ver',
    'UPDATE_ICON',
    'asked-sync',
    'buffers',
    'last-sync',
    'last-playlist',
    'pyradio-recording.txt',
    'search-group.txt',
    'search-playlist.txt',
    'search-station.txt',
    'search-theme.txt',
    'server.txt',
    'server-headless.txt',
    'vlc.conf',
]

logger = logging.getLogger(__name__)

import locale
locale.setlocale(locale.LC_ALL, "")

class XdgMigrate(object):

    def __init__(self, config=None):
        self.home_dir = getenv('HOME', '~')
        self.other_dir = path.join(self.home_dir, 'pyradio-not-migrated')
        if config is None:
            # test values
            self.data_dir =  path.join(self.home_dir, '.local/share/pyradio')
            self.state_dir = path.join(self.home_dir, '.local/state/pyradio')
            self.path_to_scan = path.join(self.home_dir, '.config/pyradio')
        else:
            self.data_dir = config.data_dir
            self.state_dir = config.state_dir
            self.path_to_scan = config.stations_dir
        self._get_files()

    def _print_file(self, an_item, max_length):
        # l = len(self.home_dir) + 1
        # print(f'{an_item = }')
        # print(f'{max_length = }')
        # print(f'{l = }')
        # print('  {0} -> {1}'.format(
        #     an_item[0][l:].ljust(max_length-l),
        #     an_item[2]
        # ))
        print(f"  {an_item[0]:{max_length}} -> {an_item[1]}")

    def _replace_dir_in_path(self, a_file, a_path):
        return path.join(a_path, path.basename(a_file))

    def _list_files_in_path(self, a_path):
        """
        Get a path and return a list of all the files in that path.

        Args:
            path (str): The directory path to list files from.

        Returns:
            list: A list of filenames in the given path.
        """
        # Initialize an empty list to store filenames
        files_list = []

        # Iterate through all files in the specified directory
        for root, dirs, files in walk(a_path):
            # Concatenate root path with each filename to get the full path
            for file in files:
                file_path = path.join(root, file)
                files_list.append(file_path)

        return sorted([x for x in files_list if \
                       ( not x.endswith('-theme') and \
                        not x.endswith('.csv') and \
                        not x.endswith(path.sep + 'config') and \
                        not x.endswith(path.sep + 'radio-browser.conf')
                        )
                       ])

    def _get_files(self):
        files_in_path = self._list_files_in_path(self.path_to_scan)
        self.files_to_data = [[x, self._replace_dir_in_path(x, self.data_dir) ]  for x in files_in_path for y in data_files if x.endswith(y)]
        self.files_to_state = [[x, self._replace_dir_in_path(x, self.state_dir) ]  for x in files_in_path for y in state_files if x.endswith(y)]

        flag_files = [x[0] for x in self.files_to_data]
        flag_files.extend([x[0] for x in self.files_to_state])

        self.files_to_other = [[x, self._replace_dir_in_path(x, self.other_dir) ] for x in files_in_path if x not in flag_files]

    def _get_max_length(self):
        to_print = []
        max_length = 0
        for n in self.files_to_data, self.files_to_state, self.files_to_other:
            if n:
                n_max_length = max(len(internal_list[0]) for internal_list in n)
                if n_max_length > max_length:
                    max_length = n_max_length
        return max_length

    def rename_files(self, to_console=True):
        if to_console:
            caption = (
                '> Copying files to "data" dir',
                '> Copying files to "state" dir',
                '> Copying files to "pytadio-not-migrated" dir',
            )

            no_files_caption = (
                '> Nothing to copy to "data" dir',
                '> Nothing to copy to "state" dir',
                '> Nothing to copy to "pytadio-not-migrated" dir',
            )
        go_on = False
        for n in self.files_to_data, self.files_to_state, self.files_to_other:
            if n:
                go_on = True
                break
        if go_on:
            for n in self.data_dir, self.state_dir, self.other_dir:
                try:
                    makedirs(n, exist_ok=True)
                except:
                    if to_console:
                        print('[red][/red]: Cannot create dir: "{}"'.format(n))
                    exit(1)
            i = -1
            max_length = self._get_max_length()
            if to_console:
                print('[bold magenta]PyRadio[/bold magenta]: moving files to [green]XDG[/green] directories')
            for n in self.files_to_data, self.files_to_state, self.files_to_other:
                i += 1
                if to_console:
                    if n:
                        print(caption[i])
                    else:
                        print(no_files_caption[i])
                for k in n:
                    if to_console:
                        print(f"  {k[0]:{max_length}} -> {k[1]}")
                    try:
                        copyfile(k[0], k[1])
                    except OSError:
                        print('[red]Error:[/red] moving files to [green]XDG[/green] directories failed...\nCleaning up...')
                        self._remove_new_files_on_failure()
                        input('Press ENTER to exit... ')
                        exit(1)
            if to_console:
                print('Cleaning up...')
            self._remove_old_files_on_success()
            if to_console:
                input('Press ENTER to continue... ')

    def _remove_old_files_on_success(self):
        for n in self.files_to_data, self.files_to_state, self.files_to_other:
            for k in n:
                self._remove_file(k[0])
        old_data_dir = path.join(self.path_to_scan, 'data')
        if path.exists(old_data_dir):
            try:
                remove_tree(old_data_dir)
            except:
                pass

    def _remove_new_files_on_failure(self):
        for n in self.files_to_data, self.files_to_state, self.files_to_other:
            for k in n:
                self._remove_file(k[1])
        for n in self.data_dir, self.state_dir, self.other_dir:
            try:
                remove_tree(n)
            except:
                pass

    def _remove_file(self, a_file):
        if path.exists(a_file):
            try:
                remove(a_file)
            except:
                pass


class XdgDirs(object):
    ''' A class to provide PyRadio directories compliant
        to the XDG XDG Base Directory Specification (or not)

        Links:
            https://specifications.freedesktop.org/basedir-spec/basedir-spec-latest.html
            https://wiki.archlinux.org/title/XDG_Base_Directory
        '''

    HOME = 0
    STATIONS = 1
    REGISTERS = 2
    DATA = 3
    STATE = 4
    CACHE = 5
    RECORDINGS = 6

    _old_dirs = [None, None, None, None, None, None, None]
    _new_dirs = [None, None, None, None, None, None, None]

    ''' function to execute when the directory has been
        moved inside the target directory, instead of
        renaming it (because it's not empty)
    '''
    dir_fixed_function = None

    titles_log_file = None

    def __init__(self, config_dir=None, xdg_compliant=False, a_dir_fix_function=None):
        ''' Parameters
            ==========
            config_dir
                Use this Configuration directory instead of the default one
                If provided, xdg_compliant is False (all subsequent
                directories will be under the one provided)
            xdg_compliant
                If False (default), all subsequent directories will be
                    under the Configuration directory
                If True, follow the Specification
        '''
        if config_dir is not None:
            self._xdg_compliant = False
            self._new_dirs[self.STATIONS] = self._old_dirs[self.STATIONS] = config_dir
        else:
            self._xdg_compliant = xdg_compliant
        self.build_paths()
        self.dir_fixed_function = a_dir_fix_function

    def migrate(self, locked):
        if not locked:
            if not platform.startswith('win'):
                self.migrate_cache()
            self.migrate_recordings()
            self.migrate_titles()

    @property
    def xdg_compliant(self):
        return self._xdg_compliant

    @xdg_compliant.setter
    def xdg_compliant(self, val):
        self._xdg_compliant = val
        self.build_paths()

    def build_paths(self):
        # print(f'{self._xdg_compliant = }')
        if platform.startswith('win'):
            if self._new_dirs[self.HOME] is None:
                self._old_dirs[self.HOME] = getenv('APPDATA')
            self._old_dirs[self.STATIONS] = path.join(self._old_dirs[self.HOME], 'pyradio')
            self._old_dirs[self.REGISTERS] = path.join(self._old_dirs[self.STATIONS], '_registers')
            self._old_dirs[self.DATA] = self._old_dirs[self.STATE] = path.join(self._old_dirs[self.STATIONS], 'data')
            self._old_dirs[self.CACHE] = path.join(self._old_dirs[self.DATA], '_cache')
            self._new_dirs = self._old_dirs[:]
        else:
            self._new_dirs[self.HOME] = self._old_dirs[self.HOME] = self._old_dirs[self.HOME] = getenv('HOME', '~')
            if self._new_dirs[self.STATIONS] is None:
                self._new_dirs[self.STATIONS] = self._old_dirs[self.STATIONS] = path.join(self._new_dirs[self.HOME], '.config', 'pyradio')
            self._old_dirs[self.REGISTERS] = self._new_dirs[self.REGISTERS] = path.join(self._new_dirs[self.STATIONS], '.registers')
            self._old_dirs[self.DATA] = path.join(self._old_dirs[self.STATIONS], 'data')
            self._old_dirs[self.STATE] = path.join(self._old_dirs[self.STATIONS], 'data')
            self._old_dirs[self.CACHE] = path.join(self._old_dirs[self.DATA], '.cache')
            if self._xdg_compliant:
                self._new_dirs[self.DATA] = path.join(self._get_xdg_dir('XDG_DATA_HOME'), 'pyradio')
                self._new_dirs[self.STATE] = path.join(self._get_xdg_dir('XDG_STATE_HOME'), 'pyradio')
            else:
                self._new_dirs[self.DATA] = self._old_dirs[self.DATA]
                self._new_dirs[self.STATE] = self._old_dirs[self.STATE]
            self._new_dirs[self.CACHE] = path.join(path.expanduser('~'), '.cache', 'pyradio')
        if self._old_dirs[self.RECORDINGS] is None:
            self._old_dirs[self.RECORDINGS] = path.join(self._old_dirs[self.STATIONS], 'recordings')
        if self._new_dirs[self.RECORDINGS] is None:
            self._new_dirs[self.RECORDINGS] = path.join(path.expanduser('~'), 'pyradio-recordings')
        # for n in range(len(self._old_dirs)):
        #     print('Item {}\n{}\n{}'.format(n, self._old_dirs[n], self._new_dirs[n]))
        # print('\n\n')

    def _get_xdg_dir(self, xdg_var):
        xdg = getenv(xdg_var)
        if xdg:
            return xdg
        else:
            # build dirs
            not_set = {}
            not_set['HOME'] = getenv('HOME', '~')
            not_set['XDG_CONFIG_HOME'] = path.join(not_set['HOME'], '.config')
            not_set['XDG_DATA_HOME'] = path.join(not_set['HOME'], '.local', 'share')
            not_set['XDG_STATE_HOME'] = path.join(not_set['HOME'], '.local', 'state')
            not_set['XDG_CACHE_HOME'] = path.join(not_set['HOME'], '.cache')
            not_set['XDG_RUNTIME_DIR'] = path.join('/run/user', str(getuid()))
            try:
                return not_set[xdg_var]
            except KeyError:
                return None

    def ensure_paths_exist(self):
        ''' Make sure config dirs exists '''
        for a_dir in (self.stations_dir,
                      self.registers_dir,
                      self.data_dir,
                      self.state_dir,
                      ):
            if not path.exists(a_dir):
                try:
                    makedirs(a_dir)
                except:
                    print('Error: Cannot create directory: "{}"'.format(a_dir))
                    sys.exit(1)

        # getenv('XDG_RUNTIME_DIR', '/run/user/1000')

    @property
    def need_to_migrate(self):
        ''' If True, it should trigger a migration process to the new scheme '''
        for n in self.DATA, self.STATE:
            if self._new_dirs[n] != self._old_dirs[n]:
                return True
        return False

    @property
    def home_dir(self):
        if platform.startswith('win'):
            return path.expanduser('~')
        else:
            return self._new_dirs[self.HOME]

    @property
    def stations_dir(self):
        if self._xdg_compliant:
            return self._new_dirs[self.STATIONS]
        else:
            return self._old_dirs[self.STATIONS]

    @property
    def data_dir(self):
        if self._xdg_compliant:
            return self._new_dirs[self.DATA]
        else:
            return self._old_dirs[self.DATA]

    @property
    def cache_dir(self):
        return self._new_dirs[self.CACHE]

    @property
    def state_dir(self):
        if self._xdg_compliant:
            return self._new_dirs[self.STATE]
        else:
            return self._old_dirs[self.STATE]

    @property
    def registers_dir(self):
        if self._xdg_compliant:
            return self._new_dirs[self.REGISTERS]
        else:
            return self._old_dirs[self.REGISTERS]

    @property
    def recording_dir(self):
        return self._new_dirs[self.RECORDINGS]

    @recording_dir.setter
    def recording_dir(self, val):
        self.set_recording_dir(new_dir=val, print_to_console=False)

    def set_recording_dir(self, new_dir=None, print_to_console=True, migrate=True, first_read=None):
        ret = True
        # logger.error('@recording_dir.setter: migrate = "{}"'.format(migrate))
        # logger.error('@recording_dir.setter: new_dir = "{}"'.format(new_dir))
        # logger.error('@recording_dir.setter: self._new_dirs[self.RECORDINGS] = "{}"'.format(self._new_dirs[self.RECORDINGS]))
        # logger.error('@recording_dir.setter: self._old_dirs[self.RECORDINGS] = "{}"'.format(self._old_dirs[self.RECORDINGS]))
        if first_read:
            old_dir = self._old_dirs[self.RECORDINGS]
            self._old_dirs[self.RECORDINGS] = first_read
            self._new_dirs[self.RECORDINGS] = new_dir
            # logger.error('@ after recording_dir.setter: self._new_dirs[self.RECORDINGS] = "{}"'.format(self._new_dirs[self.RECORDINGS]))
            # logger.error('@ after recording_dir.setter: self._old_dirs[self.RECORDINGS] = "{}"'.format(self._old_dirs[self.RECORDINGS]))
            # logger.error('self.migrate_recordings 2')
            ret = self.migrate_recordings(silent=not print_to_console)
            self._old_dirs[self.RECORDINGS] = old_dir
            self._set_last_rec_dirs(ret)
        elif new_dir is None:
            ''' coming form save condfig
                self._new_dirs[self.RECORDINGS]
                is already set and checked
            '''
            if migrate:
                ret = self.migrate_recordings(silent=not print_to_console)
                self._set_last_rec_dirs(ret)
        elif new_dir != self._new_dirs[self.RECORDINGS]:
            if new_dir != path.join(self.stations_dir, 'recordings'):
                self._new_dirs[self.RECORDINGS] = new_dir
            if migrate:
                ret = self.migrate_recordings(silent=not print_to_console)
                self._set_last_rec_dirs(ret)
        return ret

    def _set_last_rec_dirs(self, val):
        if val:
            self.last_rec_dirs = ()
        else:
            self.last_rec_dirs = (
                self._old_dirs[self.RECORDINGS],
                self._new_dirs[self.RECORDINGS]
            )

    def migrate_cache(self):
        ''' cache dir '''
        if path.exists(self._old_dirs[self.CACHE]):
            print('Migrating cache...')
            if path.exists(self._new_dirs[self.CACHE]):
                try:
                    remove_tree(self._new_dirs[self.CACHE])
                except:
                    pass
            try:
                move(self._old_dirs[self.CACHE], self._new_dirs[self.CACHE])
            except:
                print('Cannot move cache\nfrom: "{0}"\nto: "{1}"'.format(self._old_dirs[self.CACHE], self._new_dirs[self.CACHE]))
                exit(1)
        else:
            if not path.exists(self._new_dirs[self.CACHE]):
                try:
                    makedirs(self._new_dirs[self.CACHE])
                except:
                    print('\nCannot create cache dir: "{}"'.format(self._new_dirs[self.CACHE]))
                    exit(1)

    def migrate_recordings(self, silent=False):
        ''' recordings dir '''
        dir_is_fixed = False
        if self._old_dirs[self.RECORDINGS] == self._new_dirs[self.RECORDINGS]:
            return True
        if path.exists(self._old_dirs[self.RECORDINGS]):
            files = [path.join(self._old_dirs[self.RECORDINGS], f) for f in listdir(self._old_dirs[self.RECORDINGS])]
            if files:
                if not silent:
                    print('Migrating recordings...')
                parent_dir = path.dirname(self._new_dirs[self.RECORDINGS])
                if path.exists(parent_dir):
                    if path.exists(self._new_dirs[self.RECORDINGS]):
                        if len(listdir(self._new_dirs[self.RECORDINGS])) == 0:
                            try:
                                rmdir(self._new_dirs[self.RECORDINGS])
                            except:
                                if silent:
                                    return False
                                else:
                                    print("\nCannot remove empty target dir: {}".format(self._new_dirs[self.RECORDINGS]))
                                    exit(1)
                        else:
                            self._new_dirs[self.RECORDINGS] = path.join(self._new_dirs[self.RECORDINGS], 'pyradio-recordings')
                            dir_is_fixed = True
                else:
                    try:
                        makedirs(parent_dir)
                    except:
                        if silent:
                            return False
                        else:
                            print("\nCannot create target's parent dir: {}".format(parent_dir))
                            exit(1)
                try:
                    move(self._old_dirs[self.RECORDINGS], self._new_dirs[self.RECORDINGS])
                except:
                    if silent:
                        return False
                    else:
                        print('\nCannot copy files\nfrom: "{0}"\nto: {1}'.format(self._old_dirs[self.RECORDINGS], self._new_dirs[self.RECORDINGS]))
                        exit(1)
                if dir_is_fixed and self.dir_fixed_function is not None:
                    # save config if dir is "fixed"
                    self.dir_fixed_function(self._new_dirs[self.RECORDINGS])
                if path.exists(self._old_dirs[self.RECORDINGS]):
                    try:
                        remove_tree(self._old_dirs[self.RECORDINGS])
                    except:
                        pass
                # self._old_dirs[self.RECORDINGS] = self._new_dirs[self.RECORDINGS]
                # return True
            else:
                try:
                    rmdir(self._old_dirs[self.RECORDINGS])
                except:
                    pass
        #
        # I do not need to do this here, the dir will be created as needed elsewhere
        #
        # if not path.exists(self._new_dirs[self.RECORDINGS]):
        #     try:
        #         makedirs(self._new_dirs[self.RECORDINGS])
        #     except:
        #         if silent:
        #             return False
        #         else:
        #             print('\nCannot create dir: "{}"'.format(self._new_dirs[self.RECORDINGS]))
        #             exit(1)
        self._old_dirs[self.RECORDINGS] = self._new_dirs[self.RECORDINGS]
        return True

    def migrate_titles(self):
        # Create the destination directory if it doesn't exist
        if not path.exists(self.recording_dir):
            makedirs(self.recording_dir, exist_ok=True)
        if not path.exists(self.recording_dir):
            # if I cannot create the new dir (and file),use the old file
            self.titles_log_file = old_title_file

        # Construct the path to the pyradio-titles.log file
        old_title_path = path.join(path.expanduser('~'), '.config', 'pyradio')
        old_title_file = path.join(old_title_path, 'pyradio-titles.log')
        # Check if titles.log exists
        if path.exists(old_title_file):
            # Find all "pyradio-titles.*" files
            titles_files = [f for f in listdir(old_title_path) if f.startswith('pyradio-titles.')]
            try:
                # Copy titles files to recording_dir
                for title_file in titles_files:
                    copy(path.join(old_title_path, title_file), self.recording_dir)
                # Delete the original titles files
                for title_file in titles_files:
                    remove(path.join(old_title_path, title_file))
            except Exception as e:
                # If an error occurs during copying, delete all pyradio-titles.* files from recording_dir
                for title_file in titles_files:
                    try:
                        remove(path.join(self.recording_dir, title_file))
                    except Exception as ex:
                        pass
                self.titles_log_file = old_title_file
                return

        self.titles_log_file = path.join(self.recording_dir, 'pyradio-titles.log')


class CheckDir(object):

    def __init__(self, a_path, default=None, remove_after_validation=False):
        self._remove_after_validation = remove_after_validation
        # logger.error('++ remove_after_validation = {}'.format(remove_after_validation))
        self._is_writable = False
        self.dir_path = self._replace_tilde(a_path)
        if default:
            # logger.error('++ default not None')
            if not self._validate_path():
                expanded_default = self._replace_tilde(default)
                self.dir_path = self._replace_tilde(expanded_default)

    @property
    def is_writable(self):
        return self._is_writable

    @property
    def is_dir(self):
        return path.isdir(self.dir_path)

    @property
    def is_valid(self):
        return self._validate_path(self.dir_path)

    def _replace_tilde(self, a_path):
        if a_path.startswith('~/'):
            self.dir_path = a_path.replace('~', path.expanduser('~'))
        else:
            self.dir_path = a_path
        return self.dir_path

    def _validate_path(self, a_path=None):
        created = False
        if a_path is None:
            a_path = self.dir_path
        # make sure path exists and is writable
        self._is_writable = False
        if not path.exists(self.dir_path):
            if system().lower() == 'windows':
                splited_path = self.dir_path.split(path.sep)
                existing = splited_path[0]
                for n in splited_path[1:]:
                    existing = existing + path.sep + n
                    if not path.exists(existing):
                        break
            else:
                splited_path = self.dir_path.split(path.sep)[1:]
                existing = path.sep
                for n in splited_path:
                    existing = path.join(existing, n)
                    if not path.exists(existing):
                        break
            # it does not exist, try to create it
            try:
                makedirs(self.dir_path)
                created = True
            except:
                return False
        ret = False
        if path.isdir(self.dir_path):
            # Can i write in it?
            test_file = path.join(self.dir_path, r'TEST_IF_WRITABLE')
            try:
                with open(test_file, 'w') as f:
                    pass
                remove(test_file)
                self._is_writable = True
                ret = True
            except:
                pass
        else:
            pass
        # asked to remove the dir i created?
        if created and self._remove_after_validation:
            try:
                remove_tree(existing)
            except:
                pass
        return ret



if __name__ == '__main__':
    x = XdgMigrate()
    # x.print_files()
    x.rename_files()
