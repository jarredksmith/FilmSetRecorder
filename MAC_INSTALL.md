# FilmSet Recorder 0.6.4 - macOS install guide

FilmSet Recorder can be built for both Apple Silicon and Intel Macs with GitHub Actions. The recording engine uses the same project/session format as Windows, while macOS audio devices are exposed through the system audio stack.

## Which build do I need?

- **Apple Silicon:** M1, M2, M3, M4, M5, etc. Download the artifact ending in `arm64`.
- **Intel:** Older Intel-based Macs. Download the artifact ending in `x86_64`.

You can check your Mac at **Apple menu > About This Mac**.

## Build the DMG in GitHub

1. Upload/commit this project to your GitHub repository.
2. Open **Actions**.
3. Select **Build macOS App**.
4. Choose **Run workflow**.
5. The workflow builds two jobs, one for Apple Silicon and one for Intel.
6. When the run completes, download the appropriate artifact:
   - `FilmSetRecorder-macOS-v0.6.4-arm64`
   - `FilmSetRecorder-macOS-v0.6.4-x86_64`
7. Unzip the artifact to get the `.dmg`.
8. Open the DMG and drag **FilmSetRecorder.app** into **Applications**.

## First launch of this development build

This build is ad-hoc signed but is not yet Apple Developer ID signed or notarized. If macOS blocks the first launch:

1. Try opening FilmSetRecorder once.
2. Open **System Settings > Privacy & Security**.
3. Scroll to the security message about FilmSetRecorder.
4. Choose **Open Anyway** and confirm.

Do this only for a build you created from your own repository/source.

## Permissions

On first use, macOS may request:

- **Microphone** access - required for recording from the selected audio input/interface.
- **Local Network** access - required for the QR web remote, phone/tablet remote, and ESP32 controller.

Allow both if you want all FilmSet Recorder features.

If you accidentally deny them, go to **System Settings > Privacy & Security** and enable FilmSet Recorder under the relevant permission.

## Audio interface

Connect the interface before opening FilmSet Recorder, then select it in the Audio tab and start the audio engine. Run a disposable test take before using the system for production audio.

## Important production note

The macOS build still needs hardware stress testing on the exact Mac, interface, storage device, sample rate, and remote-network setup that will be used on set. Do not rely on this engineering build as the only recorder for irreplaceable production audio until those tests pass.
