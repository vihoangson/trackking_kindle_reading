@echo off
cd /d "%~dp0"
echo Starting PHP server on 0.0.0.0:8099...
echo Root directory: %CD%
php -S 0.0.0.0:8099 server.php
pause
