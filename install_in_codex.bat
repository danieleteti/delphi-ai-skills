@echo off
setlocal enabledelayedexpansion
::
:: delphi-ai-skills - install for Codex (or any agent that reads AGENTS.md)
::
::   install_in_codex.bat             installs into the current folder
::   install_in_codex.bat <path>      installs into that project folder
::
:: Copies skills\ into the project and appends a pointer section to AGENTS.md,
:: because these agents do not auto-discover skills: they must be told the files
:: exist and when to read them.
::

set "SRC=%~dp0skills"
if not exist "%SRC%" (
    echo [ERROR] Cannot find "%SRC%".
    echo         Run this script from the folder where you cloned delphi-ai-skills.
    exit /b 1
)

set "TARGET=%CD%"
if not "%~1"=="" (
    pushd "%~1" 2>nul || (echo [ERROR] No such folder: %~1 & exit /b 1)
    set "TARGET=!CD!"
    popd
)

set "DEST=!TARGET!\skills"
set "AGENTS=!TARGET!\AGENTS.md"

echo.
echo Installing delphi-ai-skills for Codex / AGENTS.md
echo   from : %SRC%
echo   to   : !DEST!
echo.

if not exist "!DEST!" mkdir "!DEST!" || (echo [ERROR] Could not create "!DEST!". & exit /b 1)
xcopy "%SRC%\*" "!DEST!\" /E /I /Y >nul || (echo [ERROR] Copy failed. & exit /b 1)
echo Skills copied.

:: --- AGENTS.md pointer -----------------------------------------------------
if exist "!AGENTS!" (
    findstr /C:"delphi-ai-skills" "!AGENTS!" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo AGENTS.md already references the skills - left untouched.
        goto :done
    )
    echo Appending a Skills section to the existing AGENTS.md ...
) else (
    echo Creating AGENTS.md ...
)

>>"!AGENTS!" echo.
>>"!AGENTS!" echo ^<^^!-- delphi-ai-skills --^>
>>"!AGENTS!" echo ## Skills
>>"!AGENTS!" echo.
>>"!AGENTS!" echo Before writing Delphi or DelphiMVCFramework code, read the relevant skill:
>>"!AGENTS!" echo.
>>"!AGENTS!" echo - `skills/delphi/SKILL.md` — the language and the RTL: version gating, lifetime, strings, generics, threading
>>"!AGENTS!" echo - `skills/delphi-code-smells/SKILL.md` — code review: compiler warnings, static analysis, memory leaks
>>"!AGENTS!" echo - `skills/dmvcframework/SKILL.md` — controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv
>>"!AGENTS!" echo - `skills/dmvcframework-minimal-api/SKILL.md` — lambda routes, route groups, filters
>>"!AGENTS!" echo - `skills/dmvcframework-webapp/SKILL.md` — TemplatePro views, fragments, ViewData
>>"!AGENTS!" echo - `skills/dmvcframework-ui/SKILL.md` — Bootstrap 5.3 layout, style.css, dark mode
>>"!AGENTS!" echo - `skills/dmvcframework-security/SKILL.md` — REQUIRED for any endpoint taking client input
>>"!AGENTS!" echo - `skills/dmvcframework-jsonrpc/SKILL.md` — JSON-RPC 2.0 services and client
>>"!AGENTS!" echo - `skills/dmvcframework-testing/SKILL.md` — DUnitX integration tests
>>"!AGENTS!" echo - `skills/htmx-skill/SKILL.md` — index of the official htmx.org docs
>>"!AGENTS!" echo.
>>"!AGENTS!" echo Do not write Delphi or DMVCFramework code from memory: the API names in these files are authoritative.

echo AGENTS.md updated.

:done
echo.
echo Done.
echo.
endlocal
