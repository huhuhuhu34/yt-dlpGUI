"""下载执行引擎 —— 1:1 移植自 Swift 版 yt-dlp-gui/Sources/DownloadRunner.swift。

把收到的字节流切成完整行、实时追加日志、解析进度百分比、支持取消。
纯逻辑层，不依赖 tkinter：UI 通过轮询 drain_log_delta() 取走新增日志，
on_finished 回调在结束监测线程触发（UI 需自行派发回主线程）。

取消语义差异（与 Swift 对齐）：
  - POSIX（macOS/Linux）：SIGINT（yt-dlp 优雅收尾）→ 4 秒后 SIGTERM 兜底
  - Windows：以 CREATE_NEW_PROCESS_GROUP 启动，先发 CTRL_BREAK_EVENT，
    4 秒后 taskkill /T /F（PyInstaller onefile 有子进程，必须杀进程树）
"""
from __future__ import annotations

import os
import re
import signal
import subprocess
import sys
import threading

_LOG_LIMIT = 350_000   # 超过后裁掉（对应 Swift logText.count > 350_000）
_LOG_KEEP = 250_000    # 保留末尾这么多字符

_PROGRESS_RE = re.compile(r"\[download\]\s+([\d.]+)%")


class LineAccumulator:
    """把收到的字节流切成完整行（避免跨块截断 UTF-8）。"""

    def __init__(self) -> None:
        self._pending = bytearray()

    def append(self, data: bytes, on_line) -> None:
        self._pending.extend(data)
        while True:
            idx = self._pending.find(b"\n")
            if idx < 0:
                break
            line_data = bytes(self._pending[:idx])
            del self._pending[:idx + 1]
            if line_data.endswith(b"\r"):
                line_data = line_data[:-1]
            on_line(line_data.decode("utf-8", errors="replace"))

    def flush(self, on_line) -> None:
        if not self._pending:
            return
        if self._pending.endswith(b"\r"):
            self._pending.pop()
        on_line(bytes(self._pending).decode("utf-8", errors="replace"))
        self._pending.clear()

class DownloadRunner:
    """真正执行 yt-dlp 内核的进程管理器：实时输出、进度解析、取消。"""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._log = ""
        self._read_pos = 0
        self._is_running = False
        self._percent = None          # type: float | None
        self._status_text = "就绪"
        self._last_exit_code = None   # type: int | None
        self._process = None          # type: subprocess.Popen | None
        self._drain_count = 0
        self._exited = False
        self._finalizing = False
        self._cancel_timer = None     # type: threading.Thread | None
        self.on_finished = None       # 结束后回调 callable(code)；在结束监测线程中触发

    # ---- 线程安全的状态读取 ----

    @property
    def is_running(self) -> bool:
        with self._lock:
            return self._is_running

    @property
    def percent(self) -> float | None:
        with self._lock:
            return self._percent

    @property
    def status_text(self) -> str:
        with self._lock:
            return self._status_text

    @property
    def last_exit_code(self) -> int | None:
        with self._lock:
            return self._last_exit_code

    def full_log(self) -> str:
        with self._lock:
            return self._log

    def drain_log_delta(self) -> str:
        """返回上次读取以来新增的日志（UI 每帧调用一次并追加到文本框）。"""
        with self._lock:
            delta = self._log[self._read_pos:]
            self._read_pos = len(self._log)
            return delta

    def set_status_text(self, text: str) -> None:
        """供 UI 在运行前/期间改写状态行（如「请先选择内核」）。"""
        self._set_status(text)

    def log_line(self, text: str) -> None:
        """供 UI 追加外部信息到当前日志区（如内核下载进度）。"""
        self._append_log(text + "\n")

    def clear_log(self) -> None:
        with self._lock:
            self._log = ""
            self._read_pos = 0
            self._percent = None
            self._status_text = "就绪"
            self._last_exit_code = None

    # ---- 内部写入 ----

    def _append_log(self, text: str) -> None:
        with self._lock:
            if len(self._log) + len(text) > _LOG_LIMIT:
                drop = len(self._log) + len(text) - _LOG_KEEP
                self._log = self._log[drop:]
                self._read_pos = max(0, self._read_pos - drop)
            self._log += text

    def _set_status(self, text: str) -> None:
        with self._lock:
            self._status_text = text

    def _set_percent(self, value: float) -> None:
        with self._lock:
            self._percent = value

    # MARK: 启动

    def run(self, executable: str, arguments: list[str],
            directory: str | None = None, task_title: str | None = None) -> None:
        if self.is_running:
            return
        self._reset_for_run()

        if task_title:
            self._append_log("▶ " + task_title + "\n")
        from .arg_builder import command_preview  # 仅展示用
        self._append_log("$ " + command_preview(executable, arguments) + "\n\n")
        self._set_status("运行中…")
        self._set_percent(None)
        with self._lock:
            self._is_running = True

        env = os.environ.copy()
        extra_path: list[str] = []
        if sys.platform == "darwin":
            extra_path = ["/opt/homebrew/bin", "/usr/local/bin"]
        if extra_path:
            base = env.get("PATH")
            env["PATH"] = ":".join(extra_path + [base]) if base else ":".join(extra_path)

        creationflags = 0
        if os.name == "nt":
            # 允许向整个进程组发送 CTRL_BREAK_EVENT（等价 SIGINT）取消
            creationflags = getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0)

        try:
            proc = subprocess.Popen(
                [executable, *arguments],
                cwd=directory or None,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.DEVNULL,
                creationflags=creationflags,
            )
        except Exception as exc:  # noqa: BLE001
            self._append_log("⚠️ 启动失败：" + str(exc) + "\n")
            self._set_status("启动失败")
            with self._lock:
                self._is_running = False
            return

        with self._lock:
            self._process = proc
            self._drain_count = 2
        threading.Thread(target=self._drain, args=(proc.stdout,), daemon=True).start()
        threading.Thread(target=self._drain, args=(proc.stderr,), daemon=True).start()
        threading.Thread(target=self._monitor, args=(proc,), daemon=True).start()

    def _reset_for_run(self) -> None:
        with self._lock:
            self._exited = False
            self._finalizing = False
            self._drain_count = 0
            self._process = None
            self._cancel_timer = None


    # MARK: 输出读取

    def _drain(self, fh) -> None:
        acc = LineAccumulator()
        while True:
            chunk = fh.read(16384)
            if not chunk:
                break
            acc.append(chunk, self._emit_line)
        acc.flush(self._emit_line)
        try:
            fh.close()
        except OSError:
            pass
        with self._lock:
            self._drain_count -= 1
        self._try_finalize()

    def _emit_line(self, line: str) -> None:
        self._append_log(line + "\n")
        self._parse_progress(line)

    def _parse_progress(self, line: str) -> None:
        m = _PROGRESS_RE.search(line)
        if not m:
            return
        try:
            v = float(m.group(1))
        except ValueError:
            return
        self._set_percent(min(v, 100))

    # MARK: 结束处理

    def _monitor(self, proc: subprocess.Popen) -> None:
        try:
            code = proc.wait()
        except Exception:  # noqa: BLE001
            code = -1
        with self._lock:
            self._exited = True
            self._last_exit_code = code
        self._try_finalize()

    def _try_finalize(self) -> None:
        with self._lock:
            if not (self._exited and self._drain_count <= 0 and not self._finalizing):
                return
            self._finalizing = True
            code = self._last_exit_code if self._last_exit_code is not None else -1
            self._process = None
            self._is_running = False
            handler = self.on_finished
        if code == 0:
            self._set_status("完成 ✅")
            if self.percent is None:
                self._set_percent(100)
            self._append_log("\n✅ 任务结束（退出码 0）。\n")
        else:
            self._set_status("已结束（退出码 %s）" % code)
            self._append_log("\n⚠️ 任务结束（退出码 %s）。\n" % code)
        if handler:
            try:
                handler(code)
            except Exception:  # noqa: BLE001
                pass

    # MARK: 取消

    def cancel(self) -> None:
        with self._lock:
            proc = self._process
            if proc is None or self._cancel_timer is not None:
                return
            running = proc.poll() is None
            self._cancel_timer = threading.Thread(target=self._force_kill_later, args=(proc,), daemon=True)
        if not running:
            return
        self._set_status("正在取消…")
        try:
            if os.name == "nt":
                proc.send_signal(signal.CTRL_BREAK_EVENT)
            else:
                proc.send_signal(signal.SIGINT)   # 等价 Swift p.interrupt()
        except (OSError, ValueError):
            pass
        self._cancel_timer.start()

    def _force_kill_later(self, proc: subprocess.Popen) -> None:
        import time

        time.sleep(4)
        with self._lock:
            self._cancel_timer = None
        if proc.poll() is not None:
            return
        try:
            if os.name == "nt":
                # PyInstaller onefile 会派生子进程：按树强制结束
                subprocess.run(
                    ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                    capture_output=True,
                    timeout=10,
                )
            else:
                proc.terminate()   # SIGTERM，等价 Swift p.terminate()
        except Exception:  # noqa: BLE001
            try:
                proc.kill()
            except OSError:
                pass

