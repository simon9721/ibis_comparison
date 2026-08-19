@echo off
setlocal
cd /d "%~dp0\.."
py -3.14 tools\figure_editor\figure_editor.py %*
