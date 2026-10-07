# Aural for Windows

Target: Windows 10/11 x64. A Windows build includes the existing music library, YouTube Music pane, playlists, themes, listening history, drag-and-drop, and desktop icon. Ads and donations have not been added.

## Running the source version now

1. Install Python 3.12 x64 from https://www.python.org/downloads/windows/ (with the Python launcher).
2. Extract the Aural source kit to a permanent folder.
3. Double-click **Setup-Windows.cmd**. It installs Python dependencies into `.venv-win`, downloads checksum-verified FFmpeg/ffprobe and Deno, and adds an Aural Start-menu shortcut. Internet access is needed for setup.
4. Search **Aural** in Start, or double-click **Start-Aural.cmd**.

The source kit is not a precompiled Windows app. Keep the extracted directory in place. You do not need Linux commands or administrator rights for the app setup. Tool downloads can be substantial.

## Building a standalone Windows app

On a Windows x64 build machine with Python 3.12, run PowerShell from the Aural directory:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\windows\build.ps1
```

This creates `dist\Aural\Aural.exe` and `dist\Aural-Windows-x64.zip`. Send the **entire** portable ZIP, not only the executable. End users of this built package do not need Python, FFmpeg or yt-dlp installed separately.

To also create a normal per-user installer, install Inno Setup 6, then run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File packaging\windows\build.ps1 -Installer
```

The result is `dist\Aural-Windows-x64-Installer.exe`, with a Start-menu shortcut, optional desktop shortcut, app icon and uninstaller. Uninstalling the application leaves your music and preferences intact.

`-SkipTools` reuses previously prepared binaries. The build script runs tests, writes a third-party license inventory, packages Qt WebEngine and site assets, and checks the frozen download worker. It builds with PyInstaller in directory mode; Qt and Chromium resources are bundled by PyInstaller's PySide6 hooks.

## Windows-specific behavior

- Data is stored in `%LOCALAPPDATA%\Aural`, independent of the installation directory. `AURAL_DATA` can override it.
- FFmpeg and Deno are discovered in the package before PATH. The source version runs yt-dlp as a Python module; packaged downloads use a worker mode in Aural.exe without starting another app window.
- Download subprocesses use UTF-8 output and do not open command-prompt windows.
- An `.ico` is supplied for the window, shortcuts and installer, with an explicit Windows app identity.
- Missing download dependencies show an error dialog. Logs are in `%LOCALAPPDATA%\Aural\aural.log`.
- Download engine updates currently require rebuilding/updating the Windows package. Automatic updates are not implemented.

## Verification status

The source app, portable Windows executable, and installed Windows app passed all 17 desktop smoke checks on a GitHub-hosted Windows runner. The installer, Start-menu shortcut, and data-preserving uninstall passed too. The 17 backend/platform tests passed on Windows and Linux. Linux desktop checks passed locally on CachyOS and on an Ubuntu GitHub runner.

See [verification details](../../docs/TESTING.md). These automated checks cover the listed behavior; they do not certify every hardware configuration or guarantee continued access to YouTube.

For additional manual coverage, try live YouTube Music browsing, physical cross-pane dragging, and upgrades on your Windows machine. Code signing has not been configured, so Windows may show an unsigned-app warning.

The package carries bundled icon and tool notices plus a Python dependency license inventory. FFmpeg binaries from Gyan are GPLv3; public binary distribution must also satisfy the corresponding-source requirements for the selected build and dependencies. Preserve the tool manifest and arrange the matching source distribution before a public release.

## Build references

- PyInstaller requires a build on the target operating system: https://pyinstaller.org/en/stable/
- Windows FFmpeg release archives and SHA-256 checksums: https://www.gyan.dev/ffmpeg/builds/
- Deno releases and asset digests: https://github.com/denoland/deno/releases
- yt-dlp JavaScript runtime setup: https://github.com/yt-dlp/yt-dlp/wiki/EJS
- Inno Setup: https://jrsoftware.org/isinfo.php
