<div align="center">

# yt-dlp for macOS · yt-dlpGUI

yt-dlp made easy on macOS — terminal kernel + native GUI

[简体中文](Readme.md) · **English**

</div>

---

## 🎯 Overview

An out-of-the-box video downloading solution for macOS users, in two parts:

1. **`yt-dlp_macos` — terminal kernel**: a **macOS Universal Binary** built from the open-source [yt-dlp](https://github.com/yt-dlp/yt-dlp). It runs on both Apple Silicon and Intel Macs and works straight from the terminal — no Python installation required.
2. **yt-dlpGUI (`yt-dlp-gui/`) — native GUI**: bundles the `yt-dlp_macos` kernel inside the `.app` so it works on **double-click**. It auto-grants the kernel executable permission (`chmod +x`) and clears the quarantine flag, and provides a full download form — format/quality, audio extraction, subtitles, output directory, playlists, proxy/login, extra args and more — with live progress and logs. See [yt-dlp-gui/README.md](yt-dlp-gui/README.md).

## 📁 Layout

```text
.
├── yt-dlp_macos            # yt-dlp universal binary for macOS (executable kernel)
├── yt-dlp-gui/             # yt-dlpGUI native GUI manager (Swift source + build scripts)
├── yt-dlp-gui-py/          # ★ Windows edition: same GUI ported to Python/tkinter
│                           #   (runs from source anywhere; one-file .exe built via GitHub Actions)
├── .github/workflows/      # builds the Windows release (yt-dlpGUI-windows.zip)
├── Readme.md               # docs in Simplified Chinese
├── Readme.en.md            # this file (English)
└── LICENSE                 # MIT License
```

## 🚀 Using `yt-dlp_macos` (terminal)

> ⚠️ **Grant permission before first use**: every `yt-dlp_macos` on macOS must first be made executable in the terminal:

```bash
chmod +x ./yt-dlp_macos
```

After that, use it like any CLI tool:

```bash
./yt-dlp_macos "video-url"   # download video (best available quality by default)
./yt-dlp_macos --help        # full option reference
./yt-dlp_macos -U            # self-update to the latest kernel
```

> 💡 Install ffmpeg if you need to merge, convert audio or embed subtitles: `brew install ffmpeg`

## 🪟 Windows edition

The macOS-only SwiftUI shell cannot be rebuilt for Windows, so the same GUI was
**ported 1:1 to Python/tkinter** (see [yt-dlp-gui-py/README.md](yt-dlp-gui-py/README.md)):

- **Out of the box**: run the “构建 Windows 版” workflow from the Actions page (or push a
  `v*` tag) and download `yt-dlpGUI-windows.zip` — it contains **`yt-dlpGUI.exe` plus the
  official self-contained `yt-dlp.exe` kernel**. Unzip both into the same folder and
  double-click; no Python installation needed.
- **From source**: `python yt-dlp-gui-py/ytdlpGUI.py` (macOS / Windows, Python 3.9+ with tkinter).
- Install ffmpeg on Windows when merging/remuxing: `winget install Gyan.FFmpeg`.

## 📖 Open Source

This project is **open source**, released under the [MIT License](LICENSE): you are free to use, modify and redistribute it, provided you retain the copyright and license notice. Stars, issues and PRs are welcome — [yt-dlpGUI repository](https://github.com/huhuhuhu34/yt-dlpGUI).

> Upstream [yt-dlp](https://github.com/yt-dlp/yt-dlp) is also open source, released under The Unlicense (public domain).

[简体中文](Readme.md)