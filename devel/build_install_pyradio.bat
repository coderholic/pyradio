@ECHO OFF
IF "%1"=="--help" GOTO displayhelp
IF "%1"=="-h" GOTO displayhelp
setlocal EnableDelayedExpansion

IF EXIST DEV (SET NO_DEV=0) ELSE (SET NO_DEV=1)
REM echo(NO_DEV = %NO_DEV%
REM GOTO endnopause

::net file to test privileges, 1>NUL redirects output, 2>NUL redirects errors
:: https://gist.github.com/neremin/3a4020c172053d837ab37945d81986f6
:: https://stackoverflow.com/questions/13212033/get-windows-version-in-a-batch-file
net session >nul 2>&1
IF '%errorlevel%' == '0' ( GOTO START ) ELSE (
    for /f "tokens=4-5 delims=. " %%i in ('ver') do set VERSION=%%i.%%j
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

IF "%1"=="" (
    CLS
    ECHO Installing / Updating python modules
    pip install windows-curses --upgrade 1>NUL 2>NUL
    if %ERRORLEVEL% == 1 (
        set ERRPKG=windows-curses
        GOTO piperror
    )
    pip install pywin32 --upgrade 1>NUL 2>NUL
    if %ERRORLEVEL% == 1 (
        set ERRPKG=pywin32
        GOTO piperror
    )
    pip install requests --upgrade 1>NUL 2>NUL
    if %ERRORLEVEL% == 1 (
        set ERRPKG=requests
        GOTO piperror
    )
    pip install dnspython --upgrade 1>NUL 2>NUL
    if %ERRORLEVEL% == 1 (
        set ERRPKG=dnspython
        GOTO piperror
    )
    pip install psutil --upgrade 1>NUL 2>NUL
    if %ERRORLEVEL% == 1 (
        set ERRPKG=psutil
        GOTO piperror
    )
)

IF '%1'=='ELEV' ( GOTO START ) ELSE ( ECHO Running elevated in a different window)
ECHO >>DOPAUSE

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

CD ..
SET arg1=%1
SET PROGRAM=python


:: Get Desktop LINK FILE
:startdesktop
CHCP 1251 >NUL
FOR /f "usebackq tokens=1,2,*" %%B IN (`reg query "HKEY_CURRENT_USER\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders" /v Desktop`) DO SET DESKTOP=%%D
CHCP 866 >NUL
FOR /f "delims=" %%i IN ('ECHO %DESKTOP%') DO SET DESKTOP=%%i

SET ALL=0
IF "%1"=="-u" GOTO uninstall
IF "%1"=="-R" GOTO uninstall
IF "%1"=="-U" (
    SET ALL=1
    GOTO uninstall
)
IF "%1"=="" GOTO noparam
SET "PROGRAM=python%arg1%"

:noparam
CLS
FOR /R .\... %%f in (*.pyc) DO DEL /q "%%~ff"


IF "%NO_DEV%" == "1" (
    CD pyradio
    %PROGRAM% -c "from install import windows_put_devel_version; windows_put_devel_version()"
    cd ..
)
%PROGRAM% setup.py build
IF %ERRORLEVEL% == 0 GOTO install
ECHO.
ECHO.
ECHO ###############################################
ECHO # The installation has failed!                #
ECHO #                                             #
ECHO # Please make sure your internet connection   #
ECHO # is working and try again.                   #
ECHO ###############################################
GOTO endofscript

:install
%PROGRAM% setup.py install
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
GOTO endofscript

:installhtml
IF "%NO_DEV%"=="1" (
    DEL DEV
    CD pyradio
    DEL config.py
    RENAME config.py.dev config.py
    CD ..
)
ECHO.
IF NOT EXIST "%APPDATA%\pyradio\*" MKDIR %APPDATA%\pyradio
IF NOT EXIST "%APPDATA%\pyradio\help\*" MKDIR %APPDATA%\pyradio\help
COPY /Y *.html %APPDATA%\pyradio\help >NUL
COPY /Y devel\pyradio.* %APPDATA%\pyradio\help >NUL
COPY /Y devel\*.lnk %APPDATA%\pyradio\help >NUL
python devel\reg.py
ECHO *** HTML files copyed to "%APPDATA%\pyradio\help"


:: Install lnk file
IF NOT EXIST %DESKTOP%\PyRadio.lnk GOTO linkcopy
ECHO === Dekstop Shortcut already exists
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

:linkcopy
ECHO *** Installing Dekstop Shortcut
COPY %APPDATA%\pyradio\help\*.lnk %DESKTOP% >NUL
GOTO toend


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
ECHO PyRadio will NOT uninstall NPV, MPlayer, Python and/or Git.
ECHO You will have to manually uninstall them.
ECHO.
ECHO PyRadio user files will be left instact.
ECHO You can find them at
ECHO     %APPDATA%\pyradio
ECHO.
ECHO ***********************************************************
ECHO.
DEL pyremove.bat 2>NUL
ECHO ECHO Uninstalling PyRadio>>pyremove.bat
ECHO ECHO ** Gathering information...>>pyremove.bat
ECHO ECHO ** Removing executable ... done>>pyremove.bat
ECHO ECHO ** Removing Desktop shortcut ... done >>pyremove.bat
ECHO IF EXIST "%DESKTOP%\PyRadio.lnk" DEL "%DESKTOP%\PyRadio.lnk" 2>NUL >>pyremove.bat
python devel\site.py exe 2>NUL >>pyremove.bat
python devel\site.py 2>NUL >dirs
python -m site --user-site 2>NUL >>dirs
python devel\windirs.py
python devel\unreg.py
ECHO DEL dirs >>pyremove.bat
ECHO ECHO. >>pyremove.bat
ECHO ECHO. >>pyremove.bat
ECHO ECHO PyRadio successfully uninstalled! >>pyremove.bat
ECHO ECHO. >>pyremove.bat
:: IF EXIST "DOPAUSE" ( ECHO PAUSE >>pyremove.bat )
:: PAUSE
CALL pyremove.bat
IF %ALL% == 1 ( GOTO noparam )

:endofscript
ECHO.
DEL DOPAUSE 2>NUL
PAUSE

:endnopause
