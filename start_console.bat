@echo off
rem Same as start.bat but keeps a console window open, so error messages stay visible.
cd /d "%~dp0"
echo Starting Chem Builder... this window shows its messages. Closing the app window stops it.
where python >nul 2>nul && (python chem_builder.py --app) || (py chem_builder.py --app)
echo.
echo The app stopped. If there is an error above, send it to Claude.
pause
