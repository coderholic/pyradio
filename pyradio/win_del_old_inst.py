# -*- coding: utf-8 -*-
import glob
import os
from sys import platform

import locale
locale.setlocale(locale.LC_ALL, "")

def win_del_old_inst():
    if not platform.startswith('win'):
        return False

    path = os.getenv('PROGRAMFILES')

    out = []
    pdirs = [f for f in glob.glob(path + "**/Python*", recursive=False)]

    for f in pdirs:
        # print('Searching in "' + f + '"')
        exe = os.path.join(f, 'Scripts', 'pyradio.exe')
        # # print("  EXE: {0} - {1}".format(exe, 'exists' if os.path.exists(exe) else 'not found'))
        if os.path.exists(exe):
            # print('  Found "' + exe + '"')
            out.append('DEL "' + exe + '"\n')
        site_packages = os.path.join(f, 'Lib', 'site-packages')
        if os.path.exists(site_packages):
            # # print('site-packages: "{}"'.format(site_packages))
            pydir = [f for f in glob.glob(site_packages + "**/pyradio*.egg", recursive=False)]
            for n in pydir:
                # print('  Found "' + n + '"')
                out.append('RD /Q /S "' + n + '"\n')
            # print(pydir)
    # print('')
    if out:
        TARGET = os.path.join(os.getenv('USERPROFILE'), 'tmp-pyradio')
        if not os.path.exists(TARGET):
            os.makedirs(TARGET)

        msg = '''@ECHO OFF
SETLOCAL EnableDelayedExpansion

IF EXIST DEV (SET NO_DEV=0) ELSE (SET NO_DEV=1)

::net file to test privileges, 1>NUL redirects output, 2>NUL redirects errors
:: https://gist.github.com/neremin/3a4020c172053d837ab37945d81986f6
:: https://stackoverflow.com/questions/13212033/get-windows-version-in-a-batch-file
net session >nul 2>&1
IF "%errorlevel%" == "0" ( GOTO START ) ELSE (
    FOR /f "tokens=4-5 delims=. " %%i in ('ver') do SET VERSION=%%i.%%j
    IF "%version%" == "6.1" ( GOTO win7exit )
    IF "%version%" == "6.0" ( GOTO win7exit )
    GOTO getPrivileges
)

:win7exit
ECHO.
ECHO Error: You must have Administrative permissions to run this script.
ECHO        Please start cmd "As Administrator".
ECHO.
ECHO        If that does not work, ask the system administrator to
ECHO        install PyRadio for you.
ECHO.
GOTO endnopause

:getPrivileges
IF "%version%" == "6.1" ( GOTO win7exit )
IF "%version%" == "6.0" ( GOTO win7exit )

IF '%1'=='ELEV' ( GOTO START ) ELSE ( ECHO Running elevated in a different window)

SET "batchPath=%~f0"
SET "batchArgs=ELEV"

::Add quotes to the batch path, IF needed
SET "script=%0"
SET script=%script:"=%
IF '%0'=='!script!' ( GOTO PathQuotesDone )
    SET "batchPath=""%batchPath%"""
:PathQuotesDone

::Add quotes to the arguments, IF needed.
:ArgLoop
IF '%1'=='' ( GOTO EndArgLoop ) ELSE ( GOTO AddArg )
    :AddArg
    SET "arg=%1"
    SET arg=%arg:"=%
    IF '%1'=='!arg!' ( GOTO NoQuotes )
        SET "batchArgs=%batchArgs% "%1""
        GOTO QuotesDone
        :NoQuotes
        SET "batchArgs=%batchArgs% %1"
    :QuotesDone
    SHIFT
    GOTO ArgLoop
:EndArgLoop

::Create and run the vb script to elevate the batch file
ECHO SET UAC = CreateObject^("Shell.Application"^) > "%temp%\OEgetPrivileges.vbs"
ECHO UAC.ShellExecute "cmd", "/c ""!batchPath! !batchArgs!""", "", "runas", 1 >> "%temp%\OEgetPrivileges.vbs"
"%temp%\OEgetPrivileges.vbs"
EXIT /B

:START
::Remove the elevation tag and SET the correct working directory
IF '%1'=='ELEV' ( SHIFT /1 )
CD /d %~dp0

::Do your adminy thing here...

:: RD /Q /S %USERPROFILE%\tmp-pyradio
:: MKDIR %USERPROFILE%\tmp-pyradio
:: START %USERPROFILE%\tmp-pyradio


'''
        TARGET_FILE = os.path.join(TARGET, 'RunMe.bat')
        with open(TARGET_FILE, 'w', encoding='utf-8') as ofile:
            ofile.write(msg)
            ofile.write('\nECHO Looking for old style installation files\n')
            for n in out:
                ofile.write('ECHO   found ' + n.replace('RD /Q /S ', '').replace('DEL ', '').replace('\n', '') + ' - removing it...\n')
                # enable this one to not delete any files
                # ofile.write(':: ' + n)
                # enable this one to actually delete files
                ofile.write(n)
            ofile.write('ECHO.\n')
            ofile.write('ECHO Old style installation files removed...\n')
            ofile.write('ECHO.\n')
            ofile.write('PAUSE\n')

        os.startfile(TARGET_FILE)
    return True

if __name__ == '__main__':
    if not win_del_old_inst():
        print('This is a Windows only program!')

