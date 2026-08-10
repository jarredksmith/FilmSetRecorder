# Build the Windows installer

## Easiest method: GitHub Actions

You do **not** need Python on the recording PC.

1. Upload this repository to GitHub with the `.github` folder at the repository root.
2. Open the repository's **Actions** tab.
3. Select **Build Windows Installer**.
4. Click **Run workflow**.
5. Wait for the Windows build to finish with a green check mark.
6. Open the completed run.
7. Under **Artifacts**, download `FilmSetRecorder-Windows-Installer-v0.2.0`.
8. Unzip the artifact.
9. Run `FilmSetRecorder_Setup_0.2.0.exe`.

The workflow runs unit tests, compiles the Python source, builds the application with PyInstaller, creates the installer with Inno Setup, and uploads both installer and portable artifacts.

## Local developer build

A local Windows build requires Python 3.12 and Inno Setup 6. From PowerShell in the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build-windows.ps1
```

The completed installer is placed in:

```text
release\FilmSetRecorder_Setup_0.2.0.exe
```
