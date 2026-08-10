# Start Here - GitHub Builds

## Windows

1. Upload the **contents of this folder** to the root of your GitHub repository.
2. Open the repository's **Actions** tab.
3. Select **Build Windows Installer**.
4. Click **Run workflow**.
5. Download `FilmSetRecorder-Windows-Installer-v0.7.0` from **Artifacts**.
6. Unzip it and install `FilmSetRecorder_Setup_0.7.0.exe`.

The recording computer does not need Python installed.

## macOS

1. Open the repository's **Actions** tab.
2. Select **Build macOS App**.
3. Click **Run workflow**.
4. Wait for both Mac build jobs to complete.
5. Download the artifact matching the Mac:
   - `FilmSetRecorder-macOS-v0.7.0-arm64` for Apple Silicon (M-series)
   - `FilmSetRecorder-macOS-v0.7.0-x86_64` for Intel
6. Unzip the artifact, open the `.dmg`, and drag **FilmSetRecorder.app** to **Applications**.
7. See `MAC_INSTALL.md` for first-launch and permissions instructions.

The Mac does not need Python installed.
