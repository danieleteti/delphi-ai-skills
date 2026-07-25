@echo off
setlocal enabledelayedexpansion
::
:: delphi-ai-skills - install for Cursor
::
::   install_in_cursor.bat            installs into the current folder
::   install_in_cursor.bat <path>     installs into that project folder
::
:: Copies skills\ into the project and writes one .cursor\rules\*.mdc per skill.
:: Each rule carries a description (so Cursor knows when it is relevant) and an
:: @-reference to the SKILL.md, so the text lives in exactly one place.
:: alwaysApply is false: the rules stay out of context until they are needed.
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
set "RULES=!TARGET!\.cursor\rules"

echo.
echo Installing delphi-ai-skills for Cursor
echo   skills to : !DEST!
echo   rules  to : !RULES!
echo.

if not exist "!DEST!" mkdir "!DEST!" || (echo [ERROR] Could not create "!DEST!". & exit /b 1)
xcopy "%SRC%\*" "!DEST!\" /E /I /Y >nul || (echo [ERROR] Copy failed. & exit /b 1)
echo Skills copied.

if not exist "!RULES!" mkdir "!RULES!" || (echo [ERROR] Could not create "!RULES!". & exit /b 1)

:: NOTE: one line per skill - add a line here when a skill is added to skills\.
call :rule delphi                    "Delphi / Object Pascal language and RTL - version gating, memory and lifetime, strings, generics, RTTI, threading"
call :rule delphi-code-smells        "Delphi code review - compiler warnings and hints, static analysis, memory leak detection, code smells"
call :rule dmvcframework             "DelphiMVCFramework core - controllers, ActiveRecord, validation, DI, middleware, servers, dotEnv"
call :rule dmvcframework-minimal-api "DelphiMVCFramework Minimal API - lambda routes, route groups, endpoint and HTTP filters"
call :rule dmvcframework-webapp      "DelphiMVCFramework web app - TemplatePro views, HTMX fragments, ViewData, cookie auth"
call :rule dmvcframework-ui          "DelphiMVCFramework UI - Bootstrap 5.3 layout, style.css, dark mode, toasts"
call :rule dmvcframework-security    "DelphiMVCFramework security - access control, mass assignment, SQL injection, XSS, JWT, secrets"
call :rule dmvcframework-jsonrpc     "DelphiMVCFramework JSON-RPC 2.0 - publishing a service, requests vs notifications, params, errors, the client"
call :rule dmvcframework-testing     "DelphiMVCFramework testing - DUnitX, in-process IMVCServer, IMVCRESTClient"
call :rule htmx-skill                "htmx reference - attributes, triggers, swap modifiers, events, headers, extensions"

echo.
echo Done. Rules written to .cursor\rules\ - Cursor pulls each one in when it is relevant.
echo.
endlocal
goto :eof

:: ---------------------------------------------------------------------------
:: :rule <skill-folder> "<description>"
:rule
set "NAME=%~1"
set "DESC=%~2"
set "F=!RULES!\%NAME%.mdc"
>"!F!" echo ---
>>"!F!" echo description: %DESC%
>>"!F!" echo globs: ["**/*.pas", "**/*.dpr", "**/*.inc", "**/*.html"]
>>"!F!" echo alwaysApply: false
>>"!F!" echo ---
>>"!F!" echo.
>>"!F!" echo @skills/%NAME%/SKILL.md
echo   - %NAME%.mdc
goto :eof
