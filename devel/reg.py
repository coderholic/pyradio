import os
import winreg

hkey = winreg.HKEY_CURRENT_USER
rkey = 'Software\Microsoft\Windows\CurrentVersion\Run'

rhandle = winreg.OpenKey(hkey, rkey, 0, winreg.KEY_ALL_ACCESS)
appdata = winreg.ExpandEnvironmentStrings('%appdata%')
bat = os.path.join(appdata,
                   'pyradio',
                   'help',
                   'pyradio.bat')
if ' ' in bat:
    bat = '"' + bat + '"'

try:
    winreg.SetValueEx(rhandle,
                      'PyRadioLockFile',
                      0, winreg.REG_SZ,
                      bat)
    with open(bat, "w") as f:
      f.write('echo "Windows started" > "{}"\n'.format(os.path.join(
          appdata,
          'pyradio',
          '_windows.lock')))
finally:
    winreg.CloseKey(rhandle)
                    
