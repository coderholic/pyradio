@echo off
set arg1=%1
set PROGRAM=python
if "%1"=="-h" goto :displayhelp

REM Check if we have admin rights
net session >nul 2>&1
if NOT %errorLevel% == 0 (
    echo.
    echo Error: You must have Administrative permissions to run this script.
    echo        Please start cmd "As Administrator"
    echo.
    goto :endofscript
)

if "%1"=="--help" goto :displayhelp
if "%1"=="-u" goto :uninstall
if "%1"=="" goto :noparam
set "PROGRAM=python%arg1%"
:noparam
cls

for /R .\... %%f in (*.pyc) do del /q "%%~ff"

REM Get mplayer
set "MPLAYER="
set "MPLAYER_SYSTEM="
if exist C:\mplayer (
    set "MPLAYER=C:\mplayer"
    set "MPLAYER_SYSTEM=yes"
)
if exist %USERPROFILE%\mplayer\mplayer.exe set "MPLAYER=%USERPROFILE%\mplayer"
if exist %APPDATA%\pyradio\mplayer\mplayer.exe set "MPLAYER=%APPDATA%\pyradio\mplayer"


set "MPLAYER_IN_PATH="
echo ;%PATH%; | find /C /I ";%MPLAYER%;" >NUL
if "%ERRORLEVEL%" == "0" set "MPLAYER_IN_PATH=yes"

%PROGRAM% setup.py build
if %ERRORLEVEL% == 0 goto :install
goto :endofscript

:install
%PROGRAM% setup.py install
if %ERRORLEVEL% == 0 goto :installhtml
echo.
echo.
echo ###############################################
echo # The installation has failed!!!              #
echo # This is probably because PyRadio is already #
echo # running, so files cannot be overwritten.    #
echo # Please terminate PyRadio and try again.     #
echo ###############################################
goto :endofscript

:installhtml
echo.
if not exist "%APPDATA%\pyradio\*" mkdir %APPDATA%\pyradio
if not exist "%APPDATA%\pyradio\help\*" mkdir %APPDATA%\pyradio\help
copy /Y *.html %APPDATA%\pyradio\help >NUL
copy /Y devel\pyradio.* %APPDATA%\pyradio\help >NUL
copy /Y devel\*.lnk %APPDATA%\pyradio\help >NUL
python devel\reg.py
echo *** HTML files copyed to "%APPDATA%\pyradio\help"

if [%MPLAYER%]==[] (
    echo.
    echo "mplayer" has not been found on your system.
    echo.
    echo Please refer to the guide in
    echo     %APPDATA%\pyradio\help\windows.html
    echo to install it.
    echo.
    echo You can execute "pyradio -ocd" and navigate to
    echo the "help" directory to find the file.
    echo.
    echo When done, execute the installation again.
    echo.
    goto :endofscript
)


REM set "MPLAYER_IN_PATH="
rem echo MPLAYER_IN_PATH is %MPLAYER_IN_PATH%
echo === Player "mplayer" found in "%MPLAYER%"
if "%MPLAYER_IN_PATH%"=="" (
    if "%MPLAYER_SYSTEM%"=="" goto :usermplayer
    REM FOR /F "tokens=2*" %%A IN ('REG QUERY "HKEY_LOCAL_MACHINE\System\CurrentControlSet\Control\Session Manager\Environment" /v PATH 2^>NUL') DO SET READ_PATH=%%B
    echo !!! Player "mplayer" not found in PATH
    echo     Add "%MPLAYER%" to PATH and log off or restart
    goto :startdesktop
)
echo === Player "mplayer" found in PATH
goto :startdesktop

:usermplayer
REM Install for user
REM FOR /F "tokens=2*" %%A IN ('REG QUERY "HKEY_CURRENT_USER\Environment" /v PATH 2^>NUL') DO SET READ_PATH=%%B
echo !!! Player "mplayer" not found in PATH
echo     Add "%MPLAYER%" to user PATH and log off or restart

REM Get Desktop
:startdesktop
CHCP 1251 >Nul
for /f "usebackq tokens=1,2,*" %%B IN (`reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop`) do set DESKTOP=%%D
CHCP 866 >Nul
for /f "delims=" %%i IN ('echo %DESKTOP%') do set DESKTOP=%%i
if exist %DESKTOP% goto :desktop


:desktop
if not exist %DESKTOP%\PyRadio.lnk goto :linkcopy
echo === Dekstop Shortcut already exists
goto :toend


:linkcopy
echo *** Installing Dekstop Shortcut
copy %APPDATA%\pyradio\help\*.lnk %DESKTOP% >NUL
goto :toend


:displayhelp
echo Build and install PyRadio
echo.
echo Execute:
echo     devel\build_install_pyradio "<PARAMETERS>"
echo.
echo Parameters are optional:
echo      2 -  use python2 to build and install
echo      3 -  use python3 to build and install
echo     -u -  uninstall PyRadio
echo     -h
echo --help -  display help
echo.
goto :endofscript

:toend
echo.
echo.
echo Installation successful!
goto :endofscript



:uninstall
echo Uninstalling PyRadio
echo ** Gathering information...
DEL pyremove.bat 2>nul
echo echo ** Removing executable ... done>>pyremove.bat
echo echo ** Removing Desktop shortcut ... done >>pyremove.bat
echo IF EXIST "%DESKTOP%\PyRadio.lnk" DEL "%DESKTOP%\PyRadio.lnk" 2>nul >>pyremove.bat
python devel\site.py exe 2>nul >>pyremove.bat
REM echo echo ** Removing Python files ... done >>pyremove.bat
python devel\site.py 2>nul >dirs
python2 devel\site.py 2>nul >>dirs
python3 devel\site.py 2>nul >>dirs
python -m site --user-site 2>nul >>dirs
python2 -m site --user-site 2>nul >>dirs
python3 -m site --user-site 2>nul >>dirs
python devel\windirs.py
python devel\unreg.py
echo DEL dirs >>pyremove.bat
echo echo PyRadio successfully uninstalled! >>pyremove.bat

echo echo. >>pyremove.bat
echo echo ********************************************************* >>pyremove.bat
echo echo. >>pyremove.bat
echo echo PyRadio has not uninstalled MPlayer, Python and/or Git. >>pyremove.bat
echo echo You will have to manually uninstall them. >>pyremove.bat
echo echo. >>pyremove.bat
echo echo PyRadio user files are left instact. You can find them at >>pyremove.bat
echo echo %APPDATA%\pyradio >>pyremove.bat
echo echo. >>pyremove.bat
echo echo ********************************************************** >>pyremove.bat
echo echo. >>pyremove.bat
REM copy pyremove.bat con
REM pause

REM IF EXIST %APPDATA%\pyradio\mplayer (
REM echo **********************************************************
REM echo *
REM echo * Directory "%APPDATA%\pyradio"
REM echo * NOT deleted since it contains the MPlayer installation
REM echo *
REM echo **********************************************************
REM echo.
REM ) ELSE (
REM echo ** Removing user files...
REM RD /S /Q %APPDATA%\pyradio
REM )
pyremove.bat

:endofscript

