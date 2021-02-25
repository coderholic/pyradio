import os
from sys import platform


def RemoveWinVlcLogFiles(*args):
    ''' Removes all VLC log files within pyradio config
        directory on Windows.

        Files currently in use will not be deleted.
    '''
    if platform.startswith('win'):
        adir = args[0]
        # print('config = "{}"'.format(adir))
        files = [file for file in os.listdir(adir) if 'vlc_log.' in file]
        if files:
            for afile in files:
                #i print(afile)
                try:
                    # print('removing "{}"'.format(afile))
                    os.remove(os.path.join(adir, afile))
                except:
                    pass


if __name__ == "__main__":
    # example:
    import threading
    threading.Thread(target=RemoveWinVlcLogFiles('C:\\Users\\Spiros\\AppData\\Roaming\\pyradio')).start()
