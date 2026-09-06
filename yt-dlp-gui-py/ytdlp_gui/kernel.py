"""内核管理 —— 移植自 Swift 版 yt-dlp-gui/Sources/KernelModel.swift。

macOS 专属能力（chmod +x、Gatekeeper 隔离标记 xattr、Bundle.main 内置内核）
在非 macOS 上自动降级：
  - Windows：没有执行位/隔离标记概念，exists 即可用；「内置内核」= 与 GUI
    程序同目录（或运行时源目录旁的 yt-dlp.exe / yt-dlp_macos）。
  - 持久化用独立 JSON（~/.ytdlpgui/kernel.json），与表单配置分离。
"""
from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
import threading
import urllib.request
from pathlib import Path

from .settings import Settings

# 官方 Windows 自包含内核下载地址（latest 重定向到最新 Release）
YTDLP_WINDOWS_URL = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"


def _kernel_names() -> list[str]:
    """当前平台 yt-dlp 内核文件名候选。"""
    if os.name == "nt":
        return ["yt-dlp.exe"]
    return ["yt-dlp_macos", "yt-dlp"]


def _is_quarantined(path: str) -> bool:
    """仅 macOS：com.apple.quarantine xattr 是否存在。"""
    if sys.platform != "darwin":
        return False
    try:
        import xattr  # 可能不可用；失败视为无隔离标记
        return "com.apple.quarantine" in xattr.listxattr(path)
    except Exception:  # noqa: BLE001
        return False


def _remove_quarantine(path: str) -> bool:
    if sys.platform != "darwin":
        return True
    try:
        import xattr
        xattr.removexattr(path, "com.apple.quarantine")
        return True
    except Exception:  # noqa: BLE001
        return False


class KernelModel:
    """管理 yt-dlp 内核程序：定位、状态检测、授权、版本检测、下载。"""

    def __init__(self, state_file: str | os.PathLike | None = None) -> None:
        self.kernel_path = ""
        self.exists = False
        self.executable = False
        self.quarantined = False
        self.message = "尚未选择内核。点击「选择…」定位内核，或点「自动搜索」。"
        self.version_text = ""
        self.is_searching = False
        self.uses_bundled = False
        self._lock = threading.RLock()
        self.on_changed = None  # 状态变化回调（UI 需派发回主线程）
        self._state_file = Path(state_file) if state_file else (Settings.CONFIG_DIR / "kernel.json")
        self._load_state()
        self.refresh()

    # ---- 内置内核路径 ----

    @property
    def bundled_kernel_path(self) -> str | None:
        """内置内核路径：
        - PyInstaller 单文件 → 与 yt-dlpGUI.exe 同目录的 yt-dlp.exe
        - 源码运行（macOS 调试） → 仓库根目录 yt-dlp_macos
        """
        base: Path | None = None
        if getattr(sys, "frozen", False):
            base = Path(sys.executable).parent
        else:
            # kernel.py 位于 yt-dlp-gui-py/ytdlp_gui/ → 仓库根
            base = Path(__file__).resolve().parent.parent.parent
        for name in _kernel_names():
            cand = base / name
            if cand.is_file():
                return str(cand)
        return None

    # ---- 状态检测 ----

    def refresh(self) -> None:
        with self._lock:
            path = self.kernel_path
            exists = bool(path) and os.path.isfile(path)
            self.exists = exists
            self.executable = False
            self.quarantined = False
            if exists:
                if os.name != "nt":
                    self.executable = os.access(path, os.X_OK)
                else:
                    self.executable = True
                self.quarantined = _is_quarantined(path)
            self._update_message()

    @property
    def is_usable(self) -> bool:
        with self._lock:
            return self.exists and self.executable and not self.quarantined

    def _update_message(self) -> None:
        if not self.kernel_path:
            self.message = "尚未选择内核。点击「选择…」定位内核，或点「自动搜索」。"
        elif not self.exists:
            self.message = "内核文件不存在，请重新选择或下载。"
        elif self.quarantined:
            self.message = "⚠️ 内核带隔离标记，请点「一键授权」解除（仅 macOS）。"
        elif not self.executable:
            self.message = "⚠️ 内核没有执行权限，请点「一键授权」（等价 chmod +x）。"
        else:
            self.message = "✅ 内核就绪，可直接使用。"

    # ---- 选择 / 授权 ----

    def select(self, path: str, mark_override: bool) -> None:
        with self._lock:
            self.kernel_path = path
            self.uses_bundled = not mark_override and self.bundled_kernel_path == path
            self._persist()
        self.refresh()
        self._notify()

    def use_bundled_kernel(self) -> None:
        bundled = self.bundled_kernel_path
        if bundled:
            self.select(bundled, mark_override=False)

    def authorize(self) -> None:
        with self._lock:
            path = self.kernel_path
            if not path or not self.exists:
                self.message = "请先选择内核程序。"
                self._notify()
                return
        if os.name == "nt":
            # Windows 无执行位概念
            self.executable = True
            self.quarantined = False
            self.message = "✅ 已就绪（Windows 无需 chmod）。"
            self._notify()
            return
        try:
            os.chmod(path, stat.S_IRWXU | stat.S_IRGRP | stat.S_IXGRP | stat.S_IROTH | stat.S_IXOTH)
            self.executable = True
        except OSError as exc:
            self.message = "设置执行权限失败：%s" % exc
            self.refresh()
            self._notify()
            return
        if self.quarantined:
            _remove_quarantine(path)
        self.refresh()
        self.message = "✅ 已授权：chmod +x 完成，隔离标记已解除。" if self.is_usable \
            else "授权未完全生效，请重试；或检查文件归属（Owner）。"
        self._notify()

    # ---- 自动搜索 ----

    def search_for_kernel(self) -> None:
        with self._lock:
            if self.is_searching:
                return
            self.is_searching = True
            self.message = "正在自动搜索内核…"
            self._notify()
        threading.Thread(target=self._search_worker, daemon=True).start()

    def _search_worker(self) -> None:
        home = str(Path.home())
        roots: list[str] = []
        if self.bundled_kernel_path:
            roots.append(str(Path(self.bundled_kernel_path).parent))
        roots += [home, os.path.join(home, "Downloads"), os.path.join(home, "Desktop")]
        if not getattr(sys, "frozen", False):
            roots.append(str(Path(__file__).resolve().parent.parent.parent))
        # 去重且只保留存在的目录
        seen: set[str] = set()
        dirs = []
        for r in roots:
            r = os.path.abspath(r)
            if r not in seen and os.path.isdir(r):
                seen.add(r)
                dirs.append(r)

        found: str | None = None
        names = _kernel_names()
        for root in dirs:
            found = self._walk(root, names, depth=0, max_depth=4)
            if found:
                break
        with self._lock:
            self.is_searching = False
        if found:
            self.select(found, mark_override=False)
        else:
            self.refresh()
            self.message = "未找到内核。请点「下载内核」或手动「选择…」。"
        self._notify()

    def _walk(self, root: str, names: list[str], depth: int, max_depth: int) -> str | None:
        if depth > max_depth:
            return None
        try:
            entries = sorted(os.listdir(root))
        except OSError:
            return None
        for item in entries:
            if item.startswith("."):
                continue
            full = os.path.join(root, item)
            if os.path.isdir(full):
                if depth < max_depth:
                    res = self._walk(full, names, depth + 1, max_depth)
                    if res:
                        return res
            elif item in names:
                return full
        return None


    # ---- 检测版本 / 快速执行 ----

    def detect_version(self) -> None:
        if not self.exists:
            return
        threading.Thread(target=self._version_worker, daemon=True).start()

    def _version_worker(self) -> None:
        code, output = self.run_capture(["--version"])
        text = output.strip()
        if code == 0 and text:
            self.version_text = "版本：" + text
            self._notify()
        else:
            self.version_text = ""
            self.message = "检测版本失败（退出码 %s）：%s" % (code, text)
            self._notify()

    def run_capture(self, args: list[str], timeout: float = 25) -> tuple[int, str]:
        """快速同步执行并抓取输出（用于 --version 等短命令）。"""
        if not self.kernel_path:
            return (1, "尚未选择内核")
        try:
            proc = subprocess.run(
                [self.kernel_path, *args],
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return (proc.returncode, proc.stdout + proc.stderr)
        except subprocess.TimeoutExpired as exc:
            return (1, "执行超时：" + str(exc))
        except Exception as exc:  # noqa: BLE001
            return (1, "启动失败：%s" % exc)

    # ---- 下载内核（Windows 兜底入口） ----

    def download_kernel(self, url: str, target_dir: str | os.PathLike,
                        progress_cb=None, done_cb=None) -> None:
        """后台线程下载官方 yt-dlp 内核。progress_cb(done_bytes, total_bytes)，
        done_cb(path|None, error|None) 在完成/失败时回调（非主线程，UI 需派发）。"""
        def worker() -> None:
            dest = Path(target_dir) / "yt-dlp.exe"
            tmp = dest.with_suffix(".exe.part")
            error: str | None = None
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "yt-dlpGUI/1.0"})
                with urllib.request.urlopen(req, timeout=60) as resp:
                    total = int(resp.headers.get("Content-Length") or 0)
                    done = 0
                    with open(tmp, "wb") as fh:
                        while True:
                            chunk = resp.read(65536)
                            if not chunk:
                                break
                            fh.write(chunk)
                            done += len(chunk)
                            if progress_cb:
                                progress_cb(done, total)
                os.replace(tmp, dest)
            except Exception as exc:  # noqa: BLE001
                error = str(exc)
                try:
                    tmp.unlink(missing_ok=True)
                except OSError:
                    pass
            if done_cb:
                done_cb(str(dest) if error is None else None, error)

        threading.Thread(target=worker, daemon=True).start()

    # ---- 持久化（~/.ytdlpgui/kernel.json） ----

    def _load_state(self) -> None:
        override = False
        saved = ""
        try:
            data = json.loads(self._state_file.read_text(encoding="utf-8"))
            override = bool(data.get("override", False))
            saved = data.get("kernelPath", "") or ""
        except (OSError, ValueError):
            data = {}
        bundled = self.bundled_kernel_path
        if bundled and not override:
            self.select(bundled, mark_override=False)
        elif saved and os.path.isfile(saved):
            self.select(saved, mark_override=override)
        elif bundled:
            self.select(bundled, mark_override=False)
        elif saved:
            self.kernel_path = saved
            self.refresh()

    def _persist(self) -> None:
        try:
            self._state_file.parent.mkdir(parents=True, exist_ok=True)
            payload = {
                "kernelPath": self.kernel_path,
                "override": not self.uses_bundled,
            }
            self._state_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def _notify(self) -> None:
        if self.on_changed:
            try:
                self.on_changed()
            except Exception:  # noqa: BLE001
                pass

