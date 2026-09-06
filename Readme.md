<div align="center">

# yt-dlp for macOS · yt-dlpGUI

一键在 macOS 上使用 [yt-dlp](https://github.com/yt-dlp/yt-dlp) —— 命令行内核 + 原生图形界面

**简体中文** · [English](Readme.en.md)

</div>

---

## 🎯 项目简介

本项目为 macOS 用户提供开箱即用的视频下载方案，包含两个部分：

1. **`yt-dlp_macos` —— 命令行内核**：基于开源项目 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 编译的 **macOS 通用二进制**（Universal Binary，同时兼容 Apple Silicon 与 Intel Mac），下载即可在终端使用，无需安装 Python。
2. **yt-dlpGUI（`yt-dlp-gui/`）—— 原生图形界面**：把 `yt-dlp_macos` 内核直接打包进 `.app`，**双击即用**——自动完成内核授权（`chmod +x`）并解除隔离标记，并提供格式/画质、音频提取、字幕、输出目录、播放列表、代理/登录等完整参数表单，实时显示下载进度与日志。详见 [yt-dlp-gui/README.md](yt-dlp-gui/README.md)。

## 📁 目录结构

```text
.
├── yt-dlp_macos              # yt-dlp 的 macOS 通用二进制（可执行内核）
├── yt-dlp-gui/               # yt-dlpGUI 图形界面管理器（Swift 源码 + 构建脚本）
├── yt-dlp-gui-py/            # ★ Windows 版：同一 GUI 的 Python/tkinter 移植
│                             #   （源码本地即可跑；单文件 exe 由 GitHub Actions 构建）
├── .github/workflows/        # 自动构建 Windows 版（产出 yt-dlpGUI-windows.zip）
├── Readme.md                 # 本说明文件（简体中文）
├── Readme.en.md              # English documentation
└── LICENSE                   # MIT 许可证
```

## 🚀 使用 `yt-dlp_macos`（终端）

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

## 🪟 Windows 版本

macOS 专属的 SwiftUI 界面无法直接搬到 Windows，因此同一套 GUI 用 **Python/tkinter
重新实现**（逻辑 1:1，详见 [yt-dlp-gui-py/README.md](yt-dlp-gui-py/README.md)）：

- **开箱即用**：在仓库 GitHub Actions 页面手动运行
  「构建 Windows 版」工作流（或推送 `v*` 标签），下载
  `yt-dlpGUI-windows.zip` —— 内含 **`yt-dlpGUI.exe` + 官方 `yt-dlp.exe` 内核**，
  解压到同一文件夹双击即用，无需安装 Python。
- **源码本地跑**：`python yt-dlp-gui-py/ytdlpGUI.py`（macOS / Windows 均可，
  仅需 Python 3.9+ 与 tkinter）。
- 需要合并/转音频时 Windows 上安装 ffmpeg：`winget install Gyan.FFmpeg`。

## 📖 开源声明

本项目为**开源项目**，以 [MIT 许可证](LICENSE) 发布：你可以自由使用、修改与再分发，仅需保留版权与许可声明。欢迎 Star、Issue 与 PR —— [yt-dlpGUI 仓库](https://github.com/huhuhuhu34/yt-dlpGUI)。

> 上游 [yt-dlp](https://github.com/yt-dlp/yt-dlp) 同样是开源项目，以 The Unlicense（公有领域）发布。

[English](Readme.en.md)
