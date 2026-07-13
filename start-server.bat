@echo off
cd /d "%~dp0web"
echo Starting PHP server on 0.0.0.0:8099...
echo Root directory: %CD%
php -S 0.0.0.0:8099
pause
