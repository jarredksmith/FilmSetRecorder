# Building the Windows installer

This project is prepared to produce a normal Windows installer named:

`FilmSetRecorder_Setup_0.1.0.exe`

The installer contains Python and the application dependencies, so the target recording computer does **not** need Python installed.

## Fastest local build

Use a 64-bit Windows 10 or Windows 11 PC.

1. Install Python 3.12 (64-bit).
2. Install Inno Setup 6. A convenient command is:
   `winget install JRSoftware.InnoSetup`
3. Open PowerShell in the project folder.
4. Run:
   `powershell -ExecutionPolicy Bypass -File .\build-windows.ps1`
5. The finished installer will be:
   `release\FilmSetRecorder_Setup_0.1.0.exe`

The build script creates an isolated build environment, installs the runtime requirements and PyInstaller, creates the self-contained application folder, then wraps it in an Inno Setup installer.

## GitHub Actions build

A workflow is included at `.github/workflows/build-windows.yml`. If the project is pushed to GitHub, run **Build Windows Installer** from the Actions tab. The workflow builds on a real Windows runner and uploads the installer as an artifact.

## Audio driver note

The FilmSet Recorder installer does not install Behringer hardware drivers. Install the correct UMC404HD Windows driver separately before using the recorder.

## Prototype warning

Version 0.1 is still an engineering prototype. Test it extensively before using it for irreplaceable production audio. In particular, verify long recordings, interface reconnect behavior, sample-rate selection, disk-full behavior, sleep/power settings, and recovery after forced termination.
