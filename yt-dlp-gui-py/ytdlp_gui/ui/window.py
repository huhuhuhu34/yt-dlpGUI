"""主窗口 —— 对应 Swift 版 App.swift + ContentView.swift。

布局：上=可滚动的分区表单（内核栏 + 各 Section），下=命令预览 + 操作按钮 +
日志面板。启动后每 100ms 轮询 runner/kernel 状态刷新界面（tkinter 无观察者，
用轮询最稳妥），所有控件写回 store 由 on_field_change 统一联动刷新。
"""
from __future__ import annotations

import os
import sys
import tkinter as tk
from tkinter import messagebox, ttk

from .. import platform as pf
from ..kernel import YTDLP_WINDOWS_URL, KernelModel
from ..runner import DownloadRunner
from ..settings import Settings
from . import sections as sec
from .numbered_text import NumberedText
from .widgets import SectionCard, copy_to_clipboard, mono_family

POLL_MS = 100


class App:
    """yt-dlpGUI 主控制器。"""

    def __init__(self, root: tk.Tk, store: Settings | None = None,
                 kernel: KernelModel | None = None, runner: DownloadRunner | None = None):
        self.root = root
        self.store = store if store is not None else Settings()
        self.kernel = kernel if kernel is not None else KernelModel()
        self.runner = runner if runner is not None else DownloadRunner()

        # 表单联动注册表
        self.tk_vars: dict[str, tk.Variable] = {}
        self.combo_syncs: list[tuple[str, ttk.Combobox]] = []
        self._conditions: list[tuple] = []      # (fn, row)
        self._refreshers: list = []             # 派生文案刷新
        self._save_after = None
        self._ui_dirty = False

        # 下载内核进度状态（后台线程写，主线程轮询读）
        self._dl = {"active": False, "last_pct": -1, "phase": ""}

        root.title("yt-dlp 管理器 · yt-dlpGUI")
        root.geometry("1080x840")
        root.minsize(920, 720)
        self._build_ui()
        self._bind_finish()
        self._poll()
        root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ================= 布局 =================

    def _build_ui(self) -> None:
        pane = ttk.Panedwindow(self.root, orient="vertical")
        pane.pack(fill="both", expand=True)
        top = ttk.Frame(pane)
        bottom = ttk.Frame(pane)
        pane.add(top, weight=4)
        pane.add(bottom, weight=2)

        # ---- 上：可滚动表单 ----
        wrap = ttk.Frame(top)
        wrap.pack(fill="both", expand=True)
        canvas = tk.Canvas(wrap, highlightthickness=0)
        vsb = ttk.Scrollbar(wrap, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner.bind("<Configure>", lambda _e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>", lambda e: canvas.itemconfigure(inner_id, width=e.width))

        def _wheel(event):
            if event.num == 4:
                delta = -1
            elif event.num == 5:
                delta = 1
            else:
                delta = -1 if event.delta > 0 else 1
            canvas.yview_scroll(delta, "units")
        canvas.bind_all("<MouseWheel>", _wheel)
        canvas.bind_all("<Button-4>", _wheel)
        canvas.bind_all("<Button-5>", _wheel)

        # 依 Swift ContentView 顺序堆叠
        self._build_kernel_bar(inner)
        sec.build_link_section(self, inner).pack(fill="x", padx=6, pady=(2, 4))
        sec.build_network_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_format_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_output_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_audio_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_subtitle_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_metadata_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_postprocess_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_playlist_section(self, inner).pack(fill="x", padx=6, pady=4)
        sec.build_advanced_section(self, inner).pack(fill="x", padx=6, pady=(4, 6))

        self._canvas = canvas
        self._build_bottom(bottom)

        self.refresh_conditions()
        for fn in self._refreshers:
            fn()
        self.refresh_preview()

    # ---------- 内核管理栏 ----------

    def _build_kernel_bar(self, parent: tk.Widget) -> None:
        card = SectionCard(parent, "内核 · yt-dlp 程序")
        body = card.body
        card.pack(fill="x", padx=6, pady=(2, 4))

        self.path_var = tk.StringVar(value=self.kernel.kernel_path)
        path_entry = ttk.Entry(body, textvariable=self.path_var, width=80)
        path_entry.pack(fill="x", pady=(0, 4))
        path_entry.bind("<Return>", lambda _e: self._commit_path())

        btns = ttk.Frame(body)
        btns.pack(fill="x", pady=(0, 4))
        self.btn_choose = ttk.Button(btns, text="选择…", command=self.choose_kernel)
        self.btn_choose.pack(side="left", padx=(0, 6))
        self.btn_bundled = ttk.Button(btns, text="使用内置内核",
                                      command=self.kernel.use_bundled_kernel)
        self.btn_search = ttk.Button(btns, text="自动搜索",
                                     command=self.kernel.search_for_kernel)
        self.btn_search.pack(side="left", padx=(0, 6))
        self.btn_authorize = ttk.Button(btns, text="一键授权",
                                        command=self.kernel.authorize)
        self.btn_version = ttk.Button(btns, text="检测版本",
                                      command=self.kernel.detect_version)
        self.btn_update = ttk.Button(btns, text="更新内核 (-U)",
                                     command=self.update_kernel)
        self.btn_download = ttk.Button(btns, text="下载内核",
                                       command=self.download_kernel_action)
        for b in (self.btn_authorize, self.btn_version, self.btn_update, self.btn_download):
            b.pack(side="left", padx=(0, 6))
        if sys.platform != "darwin":
            self.btn_authorize.pack_forget()

        status = ttk.Frame(body)
        status.pack(fill="x")
        self.dot = tk.Canvas(status, width=12, height=12, highlightthickness=0)
        self.dot.pack(side="left", padx=(0, 6))
        self.dot_id = self.dot.create_oval(1, 1, 11, 11, fill="gray", outline="")
        self.msg_label = ttk.Label(status, text=self.kernel.message, anchor="w")
        self.msg_label.pack(side="left", fill="x", expand=True)
        self.version_label = ttk.Label(status, text="", foreground="#777777")
        self.version_label.pack(side="left", padx=(8, 0))


    # ---------- 底部：命令预览 + 操作 + 日志 ----------

    def _build_bottom(self, parent: tk.Widget) -> None:
        frame = ttk.Frame(parent, padding=(10, 6))
        frame.pack(fill="both", expand=True)

        # 命令预览行
        cmd_row = ttk.Frame(frame)
        cmd_row.pack(fill="x")
        ttk.Label(cmd_row, text="命令").pack(side="left", padx=(0, 8))
        self.preview_box = tk.Text(
            cmd_row, height=1, wrap="none", font=(mono_family(self.root), 11),
            background="#f0f0f0", relief="flat", padx=6, pady=3, state="disabled")
        self.preview_box.pack(side="left", fill="x", expand=True)
        self.btn_copy = ttk.Button(cmd_row, text="复制", command=self.copy_command,
                                   state="disabled")
        self.btn_copy.pack(side="left", padx=(8, 0))
        # 长命令水平滚动
        xs = ttk.Scrollbar(cmd_row, orient="horizontal", command=self.preview_box.xview)
        self.preview_box.configure(xscrollcommand=xs.set)
        xs.pack(side="bottom", fill="x", padx=(46, 0))

        # 操作行
        actions = ttk.Frame(frame)
        actions.pack(fill="x", pady=(8, 4))
        self.btn_start = ttk.Button(actions, text="开始下载", command=self.start_download)
        self.btn_start.pack(side="left", padx=(0, 6))
        self.btn_cancel = ttk.Button(actions, text="取消", command=self.cancel_download,
                                     state="disabled")
        self.btn_cancel.pack(side="left", padx=(0, 6))
        self.btn_formats = ttk.Button(actions, text="查看可用格式", command=self.list_formats,
                                      state="disabled")
        self.btn_formats.pack(side="left", padx=(0, 6))
        self.btn_open = ttk.Button(actions, text="打开输出目录", command=self.open_output_folder)
        self.btn_open.pack(side="left", padx=(0, 6))
        self.btn_clear_log = ttk.Button(actions, text="清空日志", command=self.clear_log)
        self.btn_clear_log.pack(side="left")

        self.progress = ttk.Progressbar(actions, maximum=100, length=160)
        self.progress.pack(side="right", padx=(10, 8))
        self.percent_label = ttk.Label(actions, text="", foreground="#444444")
        self.percent_label.pack(side="right", padx=(0, 6))
        self.status_label = ttk.Label(actions, text=self.runner.status_text)
        self.status_label.pack(side="right")

        # 日志面板
        log_header = ttk.Frame(frame)
        log_header.pack(fill="x")
        ttk.Label(log_header, text="运行输出", foreground="#555555").pack(side="left")
        self.log_header_pct = ttk.Label(log_header, text="", foreground="#555555")
        self.log_header_pct.pack(side="right")

        log_frame = ttk.Frame(frame)
        log_frame.pack(fill="both", expand=True)
        self.log_text = tk.Text(
            log_frame, height=9, wrap="word", font=(mono_family(self.root), 11),
            state="disabled", padx=6, pady=4, relief="flat", background="#fafafa")
        log_sb = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_sb.set)
        log_sb.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True)
        self._log_follow = True
        self._append_log_text("（在这里查看实时输出…）\n")

        # 日志滚动：用户上滚则暂停自动跟随
        self.log_text.bind("<MouseWheel>", self._on_log_wheel)
        self.log_text.bind("<Button-4>", lambda _e: setattr(self, "_log_follow", False))
        self.log_text.bind("<Button-5>", lambda _e: setattr(self, "_log_follow", False))



    # ================= 命令预览 =================

    def preview_command(self) -> str:
        if not self.kernel.is_usable or not self.store.url_lines:
            return ""
        from ..arg_builder import build_args, command_preview

        args = build_args(self.store) + self.store.url_lines
        return command_preview(self.kernel.kernel_path, args)

    def refresh_preview(self) -> None:
        if not self._ui_dirty and hasattr(self, "_last_preview"):
            return
        text = self.preview_command()
        placeholder = ""
        if not text:
            placeholder = "（请先选择并授权内核、填入网址）"
            self.btn_copy.configure(state="disabled")
        else:
            self.btn_copy.configure(state="normal")
        if not hasattr(self, "_last_preview") or self._last_preview != text:
            self.preview_box.configure(state="normal")
            self.preview_box.delete("1.0", "end")
            self.preview_box.insert("1.0", text or placeholder)
            self.preview_box.configure(state="disabled")
            self._last_preview = text
        self._ui_dirty = False

    # ================= 日志区 =================

    def _append_log_text(self, chunk: str, prefix: bool = False) -> None:
        """chunk 追加到日志；如需去占位符前缀请 prefix=True。"""
        self.log_text.configure(state="normal")
        if prefix and self.log_text.get("1.0", "end").strip() == "（在这里查看实时输出…）":
            self.log_text.delete("1.0", "end")
        self.log_text.insert("end", chunk)
        self.log_text.configure(state="disabled")
        # 自动跟随（默认在最底部；用户上滚后暂停，回到底部恢复）
        if not self._log_follow:
            try:
                self._log_follow = self.log_text.yview()[1] >= 0.999
            except tk.TclError:
                pass
        if self._log_follow:
            self.log_text.see("end")

    def _on_log_wheel(self, event):
        self._log_follow = False

    def _bind_finish(self) -> None:
        def on_finished(code):
            self.root.after(0, lambda: self._runner_finished(code))

        self.runner.on_finished = on_finished

    def _runner_finished(self, code: int) -> None:
        if code == 0 and self.store.openOutputFolderWhenDone:
            self.open_output_folder()

    # ================= 动作 =================

    def _commit_path(self) -> None:
        p = self.path_var.get().strip()
        if p:
            self.kernel.select(p, mark_override=True)

    def choose_kernel(self) -> None:
        import tkinter.filedialog as filedialog

        name = "yt-dlp.exe" if os.name == "nt" else "yt-dlp_macos"
        path = filedialog.askopenfilename(
            parent=self.root, title="选择 yt-dlp 内核",
            filetypes=[("yt-dlp 内核", "yt-dlp*"), ("所有文件", "*.*")],
            initialfile=name)
        if path:
            self.kernel.select(path, mark_override=True)

    def start_download(self) -> None:
        if self.runner.is_running:
            return
        if not self.kernel.is_usable:
            self.runner.set_status_text("请先选择并授权 yt-dlp 内核")
            return
        if not self.store.url_lines:
            self.runner.set_status_text("请输入至少一个网址")
            return
        from ..arg_builder import build_args

        args = build_args(self.store)
        args += self.store.url_lines
        if self.store.markEnabled:
            self.store.consume_mark_number()
        self._ui_dirty = True
        self.runner.run(
            executable=self.kernel.kernel_path,
            arguments=args,
            directory=self.store.resolved_output_dir,
            task_title="开始下载",
        )

    def list_formats(self) -> None:
        if not self.kernel.is_usable or not self.store.url_lines:
            return
        self.runner.run(
            executable=self.kernel.kernel_path,
            arguments=["-F"] + self.store.url_lines,
            directory=self.store.resolved_output_dir,
            task_title="查询可用格式",
        )

    def update_kernel(self) -> None:
        if not self.kernel.is_usable:
            return
        self.runner.run(
            executable=self.kernel.kernel_path,
            arguments=["-U"],
            directory=self.store.resolved_output_dir,
            task_title="更新内核（yt-dlp -U）",
        )

    def cancel_download(self) -> None:
        self.runner.cancel()

    def clear_log(self) -> None:
        self.runner.clear_log()
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self._append_log_text("（在这里查看实时输出…）\n")
        self._log_follow = True

    def copy_command(self) -> None:
        copy_to_clipboard(self, self.preview_command())

    def open_output_folder(self) -> None:
        ok = pf.open_in_file_manager(self.store.resolved_output_dir)
        if not ok:
            self.runner.set_status_text("无法打开输出目录：" + self.store.resolved_output_dir)

    # ================= 表单联动 =================

    def add_condition(self, fn, row) -> None:
        """fn() 为真时显示该行。"""
        self._conditions.append((fn, row))

    def add_refresher(self, fn) -> None:
        """派生文案刷新器（任何字段变化后调用）。"""
        self._refreshers.append(fn)

    def on_field_change(self) -> None:
        """任意控件写回 store 后的统一联动入口。"""
        self.schedule_save()
        self._ui_dirty = True
        self.refresh_conditions()
        self._sync_combos()
        for fn in self._refreshers:
            fn()
        self.refresh_preview()

    def refresh_conditions(self) -> None:
        for fn, row in self._conditions:
            try:
                row.set_visible(bool(fn()))
            except Exception:  # noqa: BLE001
                pass

    def _sync_combos(self) -> None:
        for key, cb in self.combo_syncs:
            idx = int(getattr(self.store, key))
            if idx != cb.current():
                if 0 <= idx < len(cb.cget("values")):
                    cb.current(idx)

    def schedule_save(self) -> None:
        if self._save_after is not None:
            try:
                self.root.after_cancel(self._save_after)
            except tk.TclError:
                pass
        self._save_after = self.root.after(800, self._do_save)

    def _do_save(self) -> None:
        self._save_after = None
        self.store.save()

    # ================= 状态轮询 =================

    def _poll(self) -> None:
        try:
            self._refresh_from_state()
        except tk.TclError:
            return
        self.root.after(POLL_MS, self._poll)

    def _refresh_from_state(self) -> None:
        k, r = self.kernel, self.runner

        # 路径框回显（自动搜索/下载内核后更新）
        if self.path_var.get() != k.kernel_path:
            self.path_var.set(k.kernel_path)
        # 状态点颜色
        if not k.kernel_path:
            color = "#999999"
        elif not k.exists:
            color = "#e74c3c"
        elif not k.is_usable:
            color = "#f39c12"
        else:
            color = "#2ecc71"
        self.dot.itemconfigure(self.dot_id, fill=color)
        self.msg_label.configure(text=k.message)
        self.version_label.configure(text=k.version_text)

        # 内核栏按钮可用性
        usable = k.is_usable
        self.btn_search.configure(state="disabled" if k.is_searching else "normal")
        self.btn_version.configure(state="normal" if k.exists else "disabled")
        self.btn_update.configure(state="normal" if usable else "disabled")
        self.btn_download.configure(state="disabled" if self._dl["active"] else "normal")
        if sys.platform == "darwin":
            self.btn_authorize.configure(state="normal" if k.exists else "disabled")
        if self.btn_bundled.winfo_ismapped() != bool(k.bundled_kernel_path and not k.uses_bundled):
            if k.bundled_kernel_path and not k.uses_bundled:
                self.btn_bundled.pack(side="left", padx=(0, 6))
            else:
                self.btn_bundled.pack_forget()

        # 运行状态
        running = r.is_running
        self.btn_start.configure(state="normal" if usable and not running else "disabled")
        self.btn_cancel.configure(state="normal" if running else "disabled")
        urls = self.store.url_lines
        self.btn_formats.configure(
            state="normal" if usable and urls and not running else "disabled")
        self.status_label.configure(text=r.status_text)
        pct = r.percent
        if pct is None:
            self.progress.configure(value=0)
            self.percent_label.configure(text="")
        else:
            self.progress.configure(value=pct)
            self.percent_label.configure(text="%.1f%%" % pct)
        self.log_header_pct.configure(
            text=f"进度 %：{'-' if pct is None else '%.1f' % pct}")

        # 日志增量
        delta = r.drain_log_delta()
        if delta:
            self._append_log_text(delta, prefix=True)

        # 内核下载进度（来自后台线程）
        if self._dl["active"]:
            self._update_download_progress()


    # ================= 内核下载 =================

    def download_kernel_action(self) -> None:
        if self._dl["active"]:
            return
        target_dir = pf.default_kernel_dir()
        if not os.path.isdir(target_dir):
            target_dir = str(Settings.CONFIG_DIR)
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as exc:
            self.runner.set_status_text("无法创建下载目录：" + str(exc))
            return
        self._dl = {"active": True, "last_pct": -1, "phase": "starting", "done": 0, "total": 0}
        self.runner.set_status_text("正在下载 yt-dlp 内核…")
        self.runner.log_line("▶ 下载官方 yt-dlp.exe → " + target_dir)

        def progress(done: int, total: int):
            self._dl["phase"] = "downloading"
            self._dl["done"] = done
            self._dl["total"] = total

        def done(path, error):
            self.root.after(0, self._on_kernel_downloaded, path, error)

        self.kernel.download_kernel(YTDLP_WINDOWS_URL, target_dir, progress_cb=progress, done_cb=done)

    def _update_download_progress(self) -> None:
        if not self._dl.get("active"):
            return
        phase = self._dl.get("phase")
        if phase == "downloading":
            done, total = self._dl.get("done", 0), self._dl.get("total", 0)
            pct = int(done * 100 // total) if total else -1
            last = self._dl.get("last_pct", -1)
            if pct != last and (pct % 5 == 0 or pct >= 0 and last < 0):
                self._dl["last_pct"] = pct
                self.runner.log_line("  下载中：%s / %s（%d%%）"
                                     % (pf.readable_size(done), pf.readable_size(total) or "?", max(pct, 0)))

    def _on_kernel_downloaded(self, path, error) -> None:
        self._dl["active"] = False
        if error:
            self.runner.set_status_text("内核下载失败")
            self.runner.log_line("⚠️ 下载失败：" + error)
            return
        self.runner.log_line("✅ 内核已下载：" + str(path))
        self.kernel.select(path, mark_override=False)
        self.kernel.detect_version()

    # ================= 转 WAV（对应 Swift PostProcessSection） =================

    def convert_to_wav(self) -> None:
        if self.runner.is_running:
            self.runner.set_status_text("已有任务在运行，请先完成或取消。")
            return
        ffmpeg = pf.find_ffmpeg(self.store.ffmpegLocation)
        if not ffmpeg:
            self.runner.set_status_text("未找到 ffmpeg，请安装或在「ffmpeg 位置」里指定。")
            return
        import tkinter.filedialog as filedialog
        import os.path as op

        src = filedialog.askopenfilename(
            parent=self.root, title="选择要转换成音频的文件",
            filetypes=[("媒体文件", "*.mp4 *.mkv *.webm *.mov *.flv *.avi *.mp3 *.m4a *.aac"),
                       ("所有文件", "*.*")])
        if not src:
            return
        if op.splitext(src)[1].lower() == ".wav":
            self.runner.set_status_text("输入文件已是 WAV，无需转换。")
            return
        out_dir = op.dirname(src)
        out_path = op.join(out_dir, op.splitext(op.basename(src))[0] + ".wav")
        args: list[str] = []
        if os.path.exists(out_path):
            if not messagebox.askyesno("文件已存在", "「%s」已存在，是否覆盖？"
                                       % op.basename(out_path)):
                return
            args.append("-y")
        args += ["-i", src, "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", out_path]
        self.runner.set_status_text("音频转换中…")
        self.runner.run(executable=ffmpeg, arguments=args,
                        directory=out_dir, task_title="音频转换 WAV")

    # ================= 退出 =================

    def _on_close(self) -> None:
        try:
            if self._save_after is not None:
                self.root.after_cancel(self._save_after)
            if self.runner.is_running:
                self.runner.cancel()
        except Exception:  # noqa: BLE001
            pass
        self.store.save()
        self.root.destroy()

