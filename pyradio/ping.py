# -*- coding: utf-8 -*-
import subprocess
from sys import platform

import locale
locale.setlocale(locale.LC_ALL, "")

def ping(server, count=10, timeout_in_seconds=1):
    ''' ping a server on any platform
        Returns:
             1: server is alive (True)
             0: server is not alive (False)
            -1: error
    '''
    if platform.lower().startswith('win'):
        return windows_ping(server, count=count, timeout_in_miliseconds=timeout_in_seconds * 1000)
    return linux_ping(server, count=count, timeout_in_seconds=timeout_in_seconds)

def windows_ping(server, count=1, timeout_in_miliseconds=1000):
    ''' ping a server on windows
    Returns:
             1: server is alive (True)
             0: server is not alive (False)
            -1: error
    '''
    try:
        r=subprocess.Popen(
            ['ping', '-n', str(count), '-w',
             str(timeout_in_miliseconds), server ],
            stdout=subprocess.PIPE).stdout.read()
        return 0 if '100%' in str(r) else 1
    except:
        return -1

def linux_ping(server, count=1, timeout_in_seconds=1):
    ''' ping a server on linux
    Returns:
             1: server is alive (True)
             0: server is not alive (False)
            -1: error
    '''
    try:
        r = subprocess.Popen(
            ['ping', '-c', str(count), '-w',
             str(timeout_in_seconds), server],
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE
        ).stdout.read()
        return 0 if '100%' in str(r) else 1
    except:
        return -1

if __name__ == "__main__":
    msg= ''' ping a server on any platform
    Returns:
         1: server is alive (True)
         0: server is not alive (False)
        -1: error
    '''
    print(msg)
    ping_result = ping('www.google.com', count=20, timeout_in_seconds=3)
    print(f'Ping response: {ping_result}')
