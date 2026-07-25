@echo off
setlocal enabledelayedexpansion
::
:: delphi-ai-skills - install for Gemini CLI
::
::   install_in_gemini.bat            installs into the current folder
::   install_in_gemini.bat <path>     installs into that project folder
::
:: Copies skills\ into the project and appends a pointer section to GEMINI.md,
:: which Gemini reads at startup.
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
set "GEM=!TARGET!\GEMINI.md"

echo.
echo Installing delphi-ai-skills for Gemini CLI
echo   from : %SRC%
echo   to   : !DEST!
echo.

if not exist "!DEST!" mkdir "!DEST!" || (echo [ERROR] Could not create "!DEST!". & exit /b 1)
xcopy "%SRC%\*" "!DEST!\" /E /I /Y >nul || (echo [ERROR] Copy failed. & exit /b 1)
echo Skills copied.

if exist "!GEM!" (
    findstr /C:"delphi-ai-skills" "!GEM!" >nul 2>&1
    if !ERRORLEVEL! EQU 0 (
        echo GEMINI.md already references the skills - left untouched.
        goto :done
    )
    echo Appending a Skills section to the existing GEMINI.md ...
) else (
    echo Creating GEMINI.md ...
)

>>"!GEM!" echo.
>>"!GEM!" echo ^<^^!-- delphi-ai-skills --^>
>>"!GEM!" echo ## Skills
>>"!GEM!" echo.
>>"!GEM!" echo Before writing Delphi or DelphiMVCFramework code, read the relevant skill:
>>"!GEM!" echo.
>>"!GEM!" echo - `skills/delphi/SKILL.md` — the language and the RTL: version gating, lifetime, strings, generics, threading
>>"!GEM!" echo - `skills/delphi-code-smells/SKILL.md` — code review: compiler warnings, static analysis, memory leaks
>>"!GEM!" echo - `skills/dmvcframework/SKILL.md` — controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv
>>"!GEM!" echo - `skills/dmvcframework-minimal-api/SKILL.md` — lambda routes, route groups, filters
>>"!GEM!" echo - `skills/dmvcframework-webapp/SKILL.md` — TemplatePro views, fragments, ViewData
>>"!GEM!" echo - `skills/dmvcframework-ui/SKILL.md` — Bootstrap 5.3 layout, style.css, dark mode
>>"!GEM!" echo - `skills/dmvcframework-security/SKILL.md` — REQUIRED for any endpoint taking client input
>>"!GEM!" echo - `skills/dmvcframework-jsonrpc/SKILL.md` — JSON-RPC 2.0 services and client
>>"!GEM!" echo - `skills/dmvcframework-testing/SKILL.md` — DUnitX integration tests
>>"!GEM!" echo - `skills/htmx-skill/SKILL.md` — index of the official htmx.org docs
>>"!GEM!" echo.
>>"!GEM!" echo Do not write Delphi or DMVCFramework code from memory: the API names in these files are authoritative.

echo GEMINI.md updated.

:done
echo.
echo Done.
echo.
endlocal
