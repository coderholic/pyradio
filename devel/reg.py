import os
import winreg

hkey = winreg.HKEY_CURRENT_USER
rkey = r'Software\Microsoft\Windows\CurrentVersion\Run'

rhandle = winreg.OpenKey(hkey, rkey, 0, winreg.KEY_ALL_ACCESS)
bat = os.path.join('%APPDATA%',
                   'pyradio',
                   'data',
                   'pyradio.lock')
bat = '"' + bat + '"'

try:
    winreg.SetValueEx(
        rhandle,
        'PyRadioLockFile',
        0, winreg.REG_SZ,
        'cmd.exe /C DEL ' + bat
    )
except FileNotFoundError:
    print("Error: The specified registry key could not be found.")
except PermissionError:
    print("Error: You do not have sufficient permissions to modify the registry.")
except OSError as e:
    print(f"OS Error: An operating system error occurred: {e}")
except Exception as e:
    print(f"An unexpected error occurred: {e}")
finally:
    winreg.CloseKey(rhandle)

