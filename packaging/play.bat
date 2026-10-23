@echo off
rem Start the game with the configuration file shipped next to it.
cd /d "%~dp0"
pac-man.exe config.json
