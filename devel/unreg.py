import os
import winreg

hkey = winreg.HKEY_CURRENT_USER
rkey = r'Software\Microsoft\Windows\CurrentVersion\Run'

rhandle = winreg.OpenKey(hkey, rkey, 0, winreg.KEY_ALL_ACCESS)

try:
    winreg.DeleteValue(rhandle, 'PyRadioLockFile')
except:
    pass
finally:
  winreg.CloseKey(rhandle)

