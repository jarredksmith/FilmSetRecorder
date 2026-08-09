# FilmSet Recorder - Easiest Windows Installer Build

You do **not** need Python on your Windows recording computer.

GitHub Actions will compile the program on a Windows cloud runner and give you a finished installer.

## What you will get

`FilmSetRecorder_Setup_0.1.0.exe`

## One-time setup

1. Sign in to GitHub and create a new empty repository named `FilmSetRecorder`.
2. Do not add a README, .gitignore, or license when creating the repository (this package already contains them).
3. Open the new repository and choose **Add file > Upload files**.
4. Drag the **contents of this folder** into the upload area. Make sure `.github/workflows/build-windows.yml` is included.
5. Commit the uploaded files to the `main` branch.

## Build the installer

1. Open the repository's **Actions** tab.
2. Select **Build Windows Installer** in the left sidebar.
3. Click **Run workflow**.
4. Leave the branch set to `main` and click the green **Run workflow** button.
5. Wait for the build to finish with a green check mark.
6. Open the completed workflow run.
7. In **Artifacts**, download **FilmSetRecorder-Windows-Installer**.
8. Unzip the downloaded artifact. Inside is:
   `FilmSetRecorder_Setup_0.1.0.exe`

## Install on the recording laptop

1. Install the Behringer UMC404HD driver if it is not already installed.
2. Run `FilmSetRecorder_Setup_0.1.0.exe`.
3. Windows SmartScreen may warn because this development installer is not code-signed. Choose **More info > Run anyway** only if you built the file from your own GitHub repository and trust the source.
4. Finish setup and launch FilmSet Recorder from the Start menu.

## Important

Version 0.1 is an engineering prototype. Test it thoroughly before using it for irreplaceable production audio.
