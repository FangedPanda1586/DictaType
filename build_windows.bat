@echo off
setlocal
cd /d "%~dp0"

echo [1/4] Creating build environment...
if not exist .venv py -3.12 -m venv .venv
call .venv\Scripts\activate.bat

 echo [2/4] Installing dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
if errorlevel 1 goto :error

 echo [3/4] Building portable executable...
python -m PyInstaller --noconfirm --clean DictaType.spec
if errorlevel 1 goto :error

 echo [4/4] Build complete.
echo Portable executable: %CD%\dist\DictaType.exe
if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
  echo Inno Setup detected. Building installer...
  "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
  echo Installer: %CD%\installer_output\DictaType-Setup.exe
)
exit /b 0

:error
echo Build failed. Review the message above.
exit /b 1
