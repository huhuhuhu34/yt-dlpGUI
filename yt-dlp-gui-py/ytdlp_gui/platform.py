"""跨平台系统能力 —— 替代 Swift 版里的 AppKit / Foundation 调用。

| Swift 用法                    | 这里等价实现                       |
|------------------------------|----------------------------------|
| NSOpenPanel（选文件/目录）     | tkinter.filedialog.askopenfilename / askdirectory |
| NSWorkspace.shared.open      | os.startfile (Windows) / open (macOS) |
| NSPasteboard.general         | 由 UI 层用 tk.clipboard_append     |
| NSAlert 确认                  | tkinter.messagebox.askyesno       |
| expandingTildeInPath         | os.path.expanduser                |
| 常见 ffmpeg 路径 / PATH 探测   | shutil.which + 用户指定目录         |
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def open_in_file_manager(path: str) -> bool:
    """打开资源管理器/Finder（目录不存在时先尝试创建）。"""
    p = Path(path)
    if not p.exists():
        try:
            p.mkdir(parents=True, exist_ok=True)
        except OSError:
            return False
    try:
        if os.name == "nt":
            os.startfile(str(p))  # type: ignore[attr-defined]
        elif sys.platform == "darwin":
            subprocess.Popen(["open", str(p)])
        else:
            subprocess.Popen(["xdg-open", str(p)])
        return True
    except Exception:  # noqa: BLE001
        return False


def find_ffmpeg(override: str) -> str | None:
    """探测 ffmpeg：优先用户指定（文件或目录），其次 PATH。"""
    candidates: list[str] = []
    override = override.strip()
    if override:
        expanded = os.path.expanduser(override)
        if os.path.isdir(expanded):
            candidates.append(os.path.join(expanded, "ffmpeg" + (".exe" if os.name == "nt" else "")))
        else:
            candidates.append(expanded)
    for c in candidates:
        if os.path.isfile(c):
            return c
    # PATH
    found = shutil.which("ffmpeg")
    return found


def default_kernel_dir() -> str:
    """内核默认放置目录：
    - 打包（PyInstaller）→ 与 exe 同目录（sidecar，随包分发）
    - 源码运行 → 仓库根目录
    """
    if getattr(sys, "frozen", False):
        return str(Path(sys.executable).parent)
    # platform.py 位于 yt-dlp-gui-py/ytdlp_gui/ → 仓库根
    return str(Path(__file__).resolve().parent.parent.parent)


def readable_size(num: float) -> str:
    """字节数 → 人类可读（进度显示用）。"""
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return "%.1f %s" % (num, unit) if unit != "B" else "%d %s" % (num, unit)
        num /= 1024.0
    return "%d B" % num
