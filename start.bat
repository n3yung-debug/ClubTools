@echo off
rem Starts ClubTools with no console window, in its own app window (or the browser if pywebview is missing).
rem Closing the app window quits it. (Browser fallback: it stops ~30 s after the tab closes.)
rem If the app is already running, this just opens it again.
rem Problems? Run start_console.bat instead to see error messages, or read clubtools.log.
cd /d "%~dp0"
where pythonw >nul 2>nul && (start "" pythonw chem_builder.py --app & exit /b 0)
where pyw >nul 2>nul && (start "" pyw chem_builder.py --app & exit /b 0)
rem No windowless Python found: fall back to a console window.
call "%~dp0start_console.bat"
