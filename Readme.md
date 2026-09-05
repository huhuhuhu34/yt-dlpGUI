<div align="center">

# yt-dlp for macOS · yt-dlpGUI

一键在 macOS 上使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) —— 命令行内核 + 原生图形界面
yt-dlp made easy on macOS — terminal kernel + native GUI

[简体中文](#中文) · [English](#english)

</div>

---

## 中文

### 🎯 项目简介

本项目为 macOS 用户提供开箱即用的视频下载方案，包含两个部分：

1. **`yt-dlp_macos` —— 命令行内核**：基于开源项目 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 编译的 **macOS 通用二进制**（Universal Binary，同时兼容 Apple Silicon 与 Intel Mac），下载即可在终端使用，无需安装 Python。
2. **yt-dlpGUI（`yt-dlp-gui/`）—— 原生图形界面**：把 `yt-dlp_macos` 内核直接打包进 `.app`，**双击即用**——自动完成内核授权（`chmod +x`）并解除隔离标记，并提供格式/画质、音频提取、字幕、输出目录、播放列表、代理/登录等完整参数表单，实时显示下载进度与日志。详见 [yt-dlp-gui/README.md](yt-dlp-gui/README.md)。

### 📁 目录结构

```text
.
├── yt-dlp_macos        # yt-dlp 的 macOS 通用二进制（可执行内核）
├── yt-dlp-gui/         # yt-dlpGUI 图形界面管理器（Swift 源码 + 构建脚本）
└── Readme.md           # 本说明文件
```

### 🚀 使用 `yt-dlp_macos`（终端）

> ⚠️ **首次使用前必须授权**：对于每一个 macOS 上的 `yt-dlp_macos`，都必须先在终端执行以下命令来赋予权限：

```bash
chmod +x ./yt-dlp_macos
```

授权后即可像普通命令行工具一样使用：

```bash
./yt-dlp_macos "视频链接"    # 下载视频（默认取最高可用画质）
./yt-dlp_macos --help       # 查看完整参数说明
./yt-dlp_macos -U           # 将内核自动更新到最新版本
```

> 💡 需要合并音视频、提取/转换音频或内嵌字幕时，请先安装 ffmpeg：`brew install ffmpeg`

### 📖 开源声明

本项目为**开源项目**，以 [MIT 许可证](LICENSE) 发布：你可以自由使用、修改与再分发，仅需保留版权与许可声明。欢迎 Star、Issue 与 PR —— [yt-dlpGUI 仓库](https://github.com/huhuhuhu34/yt-dlpGUI)。

> 上游 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 同样是开源项目，以 The Unlicense（公有领域）发布。

[English](#english)

---

## English

### 🎯 Overview

An out-of-the-box video downloading solution for macOS users, in two parts:

1. **`yt-dlp_macos` — terminal kernel**: a **macOS Universal Binary** built from the open-source [yt-dlp](https://github.com/yt-dlp/yt-dlp). It runs on both Apple Silicon and Intel Macs and works straight from the terminal — no Python installation required.
2. **yt-dlpGUI (`yt-dlp-gui/`) — native GUI**: bundles the `yt-dlp_macos` kernel inside the `.app` so it works on **double-click**. It auto-grants the kernel executable permission (`chmod +x`) and clears the quarantine flag, and provides a full download form — format/quality, audio extraction, subtitles, output directory, playlists, proxy/login, extra args and more — with live progress and logs. See [yt-dlp-gui/README.md](yt-dlp-gui/README.md).

### 📁 Layout

```text
.
├── yt-dlp_macos        # yt-dlp universal binary for macOS (executable kernel)
├── yt-dlp-gui/         # yt-dlpGUI native GUI manager (Swift source + build scripts)
└── Readme.md           # this file
```

### 🚀 Using `yt-dlp_macos` (terminal)

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

### 📖 Open Source

This project is **open source**, released under the [MIT License](LICENSE): you are free to use, modify and redistribute it, provided you retain the copyright and license notice. Stars, issues and PRs are welcome — [yt-dlpGUI repository](https://github.com/huhuhuhu34/yt-dlpGUI).

> Upstream [yt-dlp](https://github.com/yt-dlp/yt-dlp) is also open source, released under The Unlicense (public domain).

[中文](#中文)
