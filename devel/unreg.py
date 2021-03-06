import os
import winreg

hkey = winreg.HKEY_CURRENT_USER
rkey = 'Software\Microsoft\Windows\CurrentVersion\Run'

rhandle = winreg.OpenKey(hkey, rkey, 0, winreg.KEY_ALL_ACCESS)

bat = os.path.join(winreg.ExpandEnvironmentStrings('%appdata%'),
                   'pyradio',
                   'help',
                   'pyradio.bat')
if ' ' in bat:
    bat = '"' + bat + '"'

try:
    winreg.DeleteValue(rhandle, 'PyRadioLockFile')
except:
    pass
finally:
  winreg.CloseKey(rhandle)

