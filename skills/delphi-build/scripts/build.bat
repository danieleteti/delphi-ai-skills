@echo off
rem build.bat <project.dproj> [Config] [Platform] [Target] [extra msbuild args, max 5]
rem   Config   Debug (default) | Release | any configuration named in the .dproj
rem   Platform Win32 (default) | Win64
rem   Target   Build (default, rebuilds every unit) | Make (only changed units) | Clean
rem Extra args pass straight to msbuild; quote each one, cmd splits on "=": "/p:DCC_NO_RETVAL=error"
rem Environment: DELPHI_BDS=23.0 picks that Studio folder; the default is the newest installed.
rem Exit code: msbuild's (0 = built, 1 = failed), 2 = bad arguments or no Studio found.
rem No delayed expansion on purpose: nothing here needs it, and "!" in a path would break it.
setlocal

if "%~1"=="" goto :usage
if not exist "%~1" echo build.bat: project not found: %~1& exit /b 2
set "PROJ=%~1"
set "CFG=%~2"
set "PLAT=%~3"
set "TARGET=%~4"
if not defined CFG set "CFG=Debug"
if not defined PLAT set "PLAT=Win32"
if not defined TARGET set "TARGET=Build"

set "ROOT=%ProgramFiles(x86)%\Embarcadero\Studio"
set "BDSVER=%DELPHI_BDS%"
if not defined BDSVER call :newest
if not defined BDSVER echo build.bat: no Studio with bin\rsvars.bat under %ROOT%& exit /b 2
if not exist "%ROOT%\%BDSVER%\bin\rsvars.bat" echo build.bat: no rsvars.bat in %ROOT%\%BDSVER%\bin& exit /b 2

rem rsvars sets BDS, puts MSBuild and the compiler on PATH and blanks PLATFORM.
call "%ROOT%\%BDSVER%\bin\rsvars.bat"

echo build.bat: Studio %BDSVER%, %PROJ%, Config=%CFG% Platform=%PLAT% Target=%TARGET%
msbuild "%PROJ%" /t:%TARGET% /p:Config=%CFG% /p:Platform=%PLAT% /v:m /nologo %5 %6 %7 %8 %9
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" echo build.bat: FAILED, exit code %RC%
exit /b %RC%

:usage
echo usage: build.bat project.dproj [Debug^|Release] [Win32^|Win64] [Build^|Make^|Clean]
exit /b 2

:newest
rem Highest numeric folder name under Studio that holds rsvars.bat (37.0 beats 9.0 and 23.0).
set /a BEST=-1
for /d %%D in ("%ROOT%\*") do call :consider "%%~nxD"
goto :eof

:consider
if not exist "%ROOT%\%~1\bin\rsvars.bat" goto :eof
for /f "delims=." %%M in ("%~1") do set /a N=%%M
if %N% GTR %BEST% set /a BEST=%N% & set "BDSVER=%~1"
goto :eof
