@echo off
setlocal
powershell.exe -ExecutionPolicy Bypass -File "%~dp0browser_research.ps1" %*
exit /b %ERRORLEVEL%
