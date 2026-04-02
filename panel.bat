@echo off
setlocal
set SCRIPT_DIR=%~dp0
set ACTION=%~1

if "%ACTION%"=="" set ACTION=start

powershell -NoProfile -ExecutionPolicy Bypass -File "%SCRIPT_DIR%panel.ps1" %ACTION%
