@echo off
setlocal enabledelayedexpansion
::
:: delphi-ai-skills - install for Claude Code
::
::   install_in_claude.bat            installs for your user (every project)
::   install_in_claude.bat .          installs into the current project (.claude\skills)
::   install_in_claude.bat <path>     installs into that project
::
:: Claude Code discovers skills automatically - there is nothing else to configure.
::

set "SRC=%~dp0skills"
if not exist "%SRC%" (
    echo [ERROR] Cannot find "%SRC%".
    echo         Run this script from the folder where you cloned delphi-ai-skills.
    exit /b 1
)

if "%~1"=="" (
    set "DEST=%USERPROFILE%\.claude\skills"
    set "SCOPE=your user account ^(available in every project^)"
) else (
    pushd "%~1" 2>nul || (echo [ERROR] No such folder: %~1 & exit /b 1)
    set "DEST=!CD!\.claude\skills"
    set "SCOPE=the project at !CD!"
    popd
)

echo.
echo Installing delphi-ai-skills for Claude Code
echo   from : %SRC%
echo   to   : !DEST!
echo   scope: !SCOPE!
echo.

if not exist "!DEST!" mkdir "!DEST!" || (echo [ERROR] Could not create "!DEST!". & exit /b 1)

:: /E copy subdirs incl. empty, /I assume dir, /Y overwrite without asking
xcopy "%SRC%\*" "!DEST!\" /E /I /Y >nul || (echo [ERROR] Copy failed. & exit /b 1)

echo Installed:
for /d %%S in ("%SRC%\*") do echo   - %%~nxS
echo.
echo Done. Start Claude Code in any Delphi project and ask, for example:
echo   "Find the memory leak in this Delphi unit"
echo   "Review this unit and tell me what is actually wrong with it"
echo.
echo The two Delphi skills ^(delphi, delphi-code-smells^) assume nothing:
echo any .pas, any project, no framework and no particular layout.
echo.
echo The DMVCFramework skills are the ones with a prerequisite. They add
echo features to an existing project, so create it with the IDE wizard
echo first, then start the agent from that project folder:
echo   "Create a DMVCFramework REST controller for Customers with full CRUD"
echo.
endlocal
