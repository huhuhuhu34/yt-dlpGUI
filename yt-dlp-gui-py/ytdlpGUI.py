#!/usr/bin/env python3
"""yt-dlpGUI 跨平台版启动入口。

直接运行（macOS 开发调试 / Windows 装有 Python 时均可）：
    python ytdlpGUI.py

打包成单文件 exe：见 README.md（PyInstaller 必须在 Windows 上执行，
项目内置 GitHub Actions workflow）。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tkinter as tk  # noqa: E402


def main() -> int:
    from ytdlp_gui.ui.window import App  # 延迟导入：让 --help 等路径不依赖 GUI

    root = tk.Tk()
    App(root)
    if "--selftest" in sys.argv:
        # CI 冒烟：构建界面后 600ms 自动退出；退出码 0 表示打包产物可启动
        root.after(600, root.destroy)
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
