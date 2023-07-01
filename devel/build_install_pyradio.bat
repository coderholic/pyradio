@ECHO OFF
SET PROGRAM=python
IF "%1"=="--help" GOTO displayhelp
IF "%1"=="-h" GOTO displayhelp
SETLOCAL EnableDelayedExpansion

IF EXIST DEV (SET NO_DEV=0) ELSE (SET NO_DEV=1)
REM echo(NO_DEV = %NO_DEV%
REM GOTO endnopause

REM CLS
ECHO Installing / Updating wheel
%PROGRAM% -m pip install --upgrade wheel 1>NUL 2>NUL
IF %ERRORLEVEL% == 1 (
    SET ERRPKG=wheel
    GOTO piperror
)
ECHO Installing / Updating setuptools
%PROGRAM% -m pip install --upgrade setuptools 1>NUL 2>NUL
IF %ERRORLEVEL% == 1 (
    SET ERRPKG=setuptools
    GOTO piperror
)
ECHO Installing / Updating pip
%PROGRAM% -m pip install --upgrade pip 1>NUL 2>NUL
IF %ERRORLEVEL% == 1 (
    SET ERRPKG=pip
    GOTO piperror
)
REM ECHO Installing / Updating windows-curses
REM %PROGRAM% -m pip install --upgrade windows-curses 1>NUL 2>NUL
REM IF %ERRORLEVEL% == 1 (
REM     SET ERRPKG=windows-curses
REM     GOTO piperror
REM )
ECHO Installing / Updating rich
%PROGRAM% -m pip install --upgrade rich 1>NUL 2>NUL
IF %ERRORLEVEL% == 1 (
    SET ERRPKG=rich
    GOTO piperror
)
ECHO Installing / Updating requests
%PROGRAM% -m pip install --upgrade requests 1>NUL 2>NUL
IF %ERRORLEVEL% == 1 (
    SET ERRPKG=requests
    GOTO piperror
)

echo pywin32 > requirements.txt
echo windows-curses >> requirements.txt
echo requests >> requirements.txt
echo rich >> requirements.txt
echo dnspython >> requirements.txt
echo psutil >> requirements.txt
echo wheel >> requirements.txt
echo pylnk >> requirements.txt
echo win10toast >> requirements.txt
echo python-dateutil >> requirements.txt

::Remove the elevation tag and SET the correct working directory
IF '%1'=='ELEV' ( SHIFT /1 )
CD /d %~dp0

::Do your adminy thing here...

CD ..
SET arg1=%1


:: Get Desktop LINK FILE
:startdesktop
CHCP 1251 >NUL
FOR /f "usebackq tokens=1,2,*" %%B IN (`reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop`) DO SET DESKTOP=%%D
CHCP 866 >NUL
FOR /f "delims=" %%i IN ('ECHO %DESKTOP%') DO SET DESKTOP=%%i

SET ALL=0
IF "%1"=="-u" GOTO uninstall
IF "%1"=="-R" GOTO uninstall
REM Do not run uninstall while installing
IF "%1"=="-U" (
    SET ALL=1
    REM     GOTO uninstall
)
IF "%1"=="" GOTO noparam
IF "%arg1%" == "2" SET "PROGRAM=python%arg1%"
IF "%arg1%" == "3" SET "PROGRAM=python%arg1%"

:noparam
REM CLS
FOR /R .\... %%f in (*.pyc) DO DEL /q "%%~ff"


IF "%NO_DEV%" == "1" (
    CD pyradio
    %PROGRAM% -c "from install import windows_put_devel_version; windows_put_devel_version()"
    cd ..
)

:install
%PROGRAM% -m pip install -r requirements.txt .
IF %ERRORLEVEL% == 0 GOTO installhtml
:installationerror
ECHO.
ECHO.
ECHO ###############################################
ECHO # The installation has failed!                #
ECHO #                                             #
ECHO # This is probably because PyRadio is already #
ECHO # running, so files cannot be overwritten.    #
ECHO # Please terminate PyRadio and try again.     #
ECHO ###############################################
IF EXIST "DOPAUSE" ( GOTO endofscript )
GOTO endnopause

:installhtml
IF "%NO_DEV%"=="1" (
    DEL DEV 1>NUL 2>NUL
    CD pyradio
    IF EXIST config.py.dev (
        DEL config.py
        RENAME config.py.dev config.py
    )
    CD ..
)
ECHO.

SET INSTALL_PLAYER=no
IF NOT EXIST "%APPDATA%\pyradio\*" (
    MKDIR %APPDATA%\pyradio
    SET INSTALL_PLAYER=yes
)
IF NOT EXIST "%APPDATA%\pyradio\help\*" MKDIR %APPDATA%\pyradio\help
COPY /Y *.html %APPDATA%\pyradio\help >NUL
COPY /Y devel\pyradio.* %APPDATA%\pyradio\help >NUL
COPY /Y devel\*.lnk %APPDATA%\pyradio\help >NUL
python devel\reg.py
ECHO *** HTML files copyed to "%APPDATA%\pyradio\help"


:: Update lnk file
CD pyradio
%PROGRAM% -c "from win import create_pyradio_link; create_pyradio_link()"
CD ..

:: Install lnk file
ECHO *** Installing Dekstop Shortcut
REM DEL %USERPROFILE%\desktop\PyRadio.lnk >NUL
REM DEL "%APPDATA%\Microsoft\Windows\Start Menu\Programs\PyRadio.lnk" >NUL
REM REM COPY /Y %APPDATA%\pyradio\help\PyRadio.lnk %DESKTOP% >NUL
REM COPY /Y %APPDATA%\pyradio\help\PyRadio.lnk %USERPROFILE%\desktop >NUL
REM IF EXIST "%APPDATA%\Microsoft\Windows\Start Menu\Programs" (
REM     ECHO *** Installing Start Menu Shortcut
REM     COPY /Y %APPDATA%\pyradio\help\PyRadio.lnk "%APPDATA%\Microsoft\Windows\Start Menu\Programs" >NUL
REM )
CD pyradio
%PROGRAM% -c "from win import install_pyradio_link; install_pyradio_link()"
CD ..

:: Clean up
CD pyradio
%PROGRAM% -c "from win import clean_up; clean_up()"
CD ..
GOTO toend

:piperror
CLS
ECHO  The installation has failed
ECHO.
ECHO This means that either you internet connection has failed
ECHO (in which case you should fix it and try again), or that
ECHO.
ECHO one of PyRadio's dependencies has not been found
ECHO(     package: !ERRPKG!
ECHO.
ECHO  If this is the case, packagers have not yet produced
ECHO  a package for this version of python (it was probably
ECHO  released recently).
ECHO.
ECHO  What can you do?
ECHO  1. Wait for the package to be updated (which means you
ECHO     will not be able to use PyRadio until then), or
ECHO  2. Uninstall python and then go to
ECHO           https://www.python.org/downloads/
ECHO     and download and install the second to last version.
ECHO .
ECHO     Then try installing PyRadio again
ECHO.
ECHO.
GOTO endnopause

:displayhelp
ECHO Build and install PyRadio
ECHO.
ECHO Execute:
ECHO     devel\build_install_pyradio "<PARAMETERS>"
ECHO.
ECHO Parameters are optional:
ECHO           -U   -   update PyRadio
ECHO       -u, -R   -   uninstall PyRadio
ECHO   -h, --help   -   display this help
ECHO.
GOTO endnopause

:toend
ECHO.
ECHO.
ECHO Installation successful!
IF EXIST "DOPAUSE" ( GOTO endofscript )
GOTO endnopause


:uninstall
ECHO This may take some time...
ECHO ***********************************************************
ECHO.
ECHO PyRadio will NOT uninstall Python and/or Git.
ECHO You will have to manually uninstall them (IF desired).
ECHO.
ECHO ***********************************************************
ECHO.
DEL pyremove.bat 2>NUL
ECHO ECHO Uninstalling PyRadio>>pyremove.bat
:: ECHO ECHO ** Gathering information>>pyremove.bat
:: ECHO ECHO ** Removing executable>>pyremove.bat
ECHO ECHO ** Removing Desktop shortcut>>pyremove.bat
ECHO IF EXIST "%DESKTOP%\PyRadio.lnk" DEL "%DESKTOP%\PyRadio.lnk">>pyremove.bat
ECHO IF EXIST "%APPDATA%\Microsoft\Windows\Start Menu\Programs"\PyRadio.lnk DEL "%APPDATA%\Microsoft\Windows\Start Menu\Programs"\PyRadio.lnk>>pyremove.bat
:: python devel\site.py exe 2>NUL >>pyremove.bat
:: python devel\site.py 2>NUL >dirs
:: python -m site --user-site 2>NUL >>dirs
:: python devel\windirs.py
python devel\unreg.py

SET ANS=""
:readit
ECHO User files are under "%APPDATA%\pyradio"
SET /p ANS="Do you want to remove them (y/n)?: "
:: ECHO %ANS%
IF "%ANS%" == "y" GOTO :addtobat
IF "%ANS%" == "n" (
    IF EXIST "DOPAUSE" ( GOTO endofscript )
    GOTO endnopause
)
GOTO :readit
:addtobat

IF "%ANS%" == "y" (
    ECHO ECHO ** Removing user files>>pyremove.bat
    ECHO RD /Q /S "%APPDATA%\pyradio">>pyremove.bat
) else (
    ECHO ECHO ** Removing stations.csv>>pyremove.bat
    ECHO DEL "%APPDATA%\pyradio\stations.csv">>pyremove.bat
    IF EXIST %APPDATA%\pyradio\mpv (
        ECHO ECHO ** Removing MPV>>pyremove.bat
        ECHO RD /Q /S "%APPDATA%\pyradio\mpv">>pyremove.bat
    )
    IF EXIST %APPDATA%\pyradio\mplayer (
        ECHO ECHO ** Removing MPlayer>>pyremove.bat
        ECHO RD /Q /S "%APPDATA%\pyradio\mplayer">>pyremove.bat
    )
)

ECHO IF EXIST dirs DEL dirs >>pyremove.bat
ECHO %PROGRAM% -m pip uninstall -y pyradio>>pyremove.bat
ECHO ECHO.>>pyremove.bat
ECHO ECHO.>>pyremove.bat
:: ECHO ECHO PyRadio successfully uninstalled! >>pyremove.bat
::ECHO ECHO. >>pyremove.bat
IF EXIST "DOPAUSE" ( ECHO PAUSE>>pyremove.bat )
:: PAUSE
CALL pyremove.bat
IF %ALL% == 1 ( GOTO noparam )

:endofscript
ECHO.
DEL DOPAUSE 2>NUL
PAUSE

:endnopause

REM IF "%INSTALL_PLAYER%" == "yes" (
REM    %PROGRAM% pyradio\win.py
REM )
