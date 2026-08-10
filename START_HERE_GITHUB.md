# Start here - build FilmSet Recorder without installing Python

This repository is ready for GitHub Actions.

## Windows

1. Make sure `.github/workflows/build-windows.yml` exists at the repository root.
2. Open **Actions**.
3. Choose **Build Windows Installer**.
4. Click **Run workflow**.
5. When the run finishes, download `FilmSetRecorder-Windows-Installer-v0.3.2` from **Artifacts**.
6. Unzip it and install `FilmSetRecorder_Setup_0.3.2.exe`.

## macOS

1. Open **Actions**.
2. Choose **Build macOS App**.
3. Click **Run workflow**.
4. Download `FilmSetRecorder-macOS-v0.3.2` from **Artifacts**.
5. Unzip the artifact and open the DMG.

Development builds are not digitally signed or notarized, so OS security warnings are expected until code signing is added.
