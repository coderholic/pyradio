@echo off
cls
set arg1=%1
set PROGRAM=python
if "%1"=="-h" goto :displayhelp
if "%1"=="--help" goto :displayhelp
if "%1"=="" goto :noparam
set "PROGRAM=python%arg1%"
:noparam

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
echo     -h
echo --help -  display help
echo.


:toend
echo.
echo.
echo Installation successful!
goto :endofscript

:endofscript




REM *** HTML files copyed to "C:\Users\spiros\AppData\Roaming\pyradio\help"
REM === Player "mplayer" found in "C:\Users\spiros\mplayer"
REM === Player "mplayer" found in PATH
REM === Dekstop Shortcut already exists



REM *** HTML files copyed to "C:\Users\spiros\AppData\Roaming\pyradio\help"
REM === Player "mplayer" found in "C:\Users\spiros\mplayer"
REM !!! Player "mplayer" not found in PATH
REM     Add "C:\Users\spiros\mplayer" to user PATH and log off or restart
REM === Dekstop Shortcut already exists
