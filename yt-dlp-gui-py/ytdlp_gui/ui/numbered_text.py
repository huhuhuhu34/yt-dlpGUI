"""行号链接编辑器 —— 移植自 Swift 版 NumberedTextView.swift。

要点（与 Swift 一致）：
  - 编号只是展示层（左侧画布），不写入真实文本 —— 复制/解析永远是纯净链接
  - 每个逻辑条目（\n 分隔）显示一个编号，画在条目首个可视行；
    长 URL 自动换行时续行不显示编号
  - 文本末尾“待输入的空条目”显示下一个编号
编号用阿拉伯数字（Swift 用 ①②③ 装饰；Windows 字体对后者支持不佳，
这是纯展示差异）。
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

from .widgets import mono_family


class NumberedText(tk.Frame):
    """带行号 gutter 与滚动条的多行文本框。用 get()/set() 操作真实内容。"""

    GUTTER_WIDTH = 46

    def __init__(self, master: tk.Widget, height: int = 6, on_change=None):
        super().__init__(master)
        self.on_change = on_change
        self._font = (mono_family(master), 12)
        self._line_h = tkfont.Font(master, font=self._font).metrics("linespace")

        # gutter 画布 + 文本框 + 垂直滚动条
        self.gutter = tk.Canvas(self, width=self.GUTTER_WIDTH, highlightthickness=0)
        self.gutter.pack(side="left", fill="y")
        self.text = tk.Text(
            self, height=height, wrap="word", undo=True, font=self._font,
            padx=6, pady=4, borderwidth=0, highlightthickness=0, relief="flat",
        )
        self.text.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(self, orient="vertical", command=self.text.yview)
        scroll.pack(side="right", fill="y")
        self.text.configure(yscrollcommand=self._on_text_scroll)

        # 刷新时机
        self.text.bind("<<Modified>>", self._on_modified)
        self.text.bind("<KeyRelease>", lambda _e: self._schedule_redraw())
        self.text.bind("<MouseWheel>", lambda _e: self._schedule_redraw())
        self.text.bind("<ButtonRelease-4>", lambda _e: self._schedule_redraw())  # 向上滚
        self.text.bind("<ButtonRelease-5>", lambda _e: self._schedule_redraw())  # 向下滚
        self.text.bind("<<Paste>>", lambda _e: self._schedule_redraw())
        self._after_id = None

    # ---- 对外接口 ----

    def get(self) -> str:
        return self.text.get("1.0", "end-1c")

    def set(self, value: str) -> None:
        self.text.delete("1.0", "end")
        self.text.insert("1.0", value)
        self.text.edit_modified(False)
        self._redraw()
        if self.on_change:
            self.on_change()

    def focus_input(self) -> None:
        self.text.focus_set()

    # ---- 刷新 ----

    def _on_modified(self, _event=None):
        if self.text.edit_modified():
            self.text.edit_modified(False)
            self._redraw()
            if self.on_change:
                self.on_change()

    def _on_text_scroll(self, *args):
        # 滚动条拖动也重绘行号
        self._schedule_redraw()

    def _schedule_redraw(self):
        if self._after_id:
            return
        self._after_id = self.after(20, self._do_redraw)

    def _do_redraw(self):
        self._after_id = None
        self._redraw()

    # ---- 行号绘制 ----

    def _redraw(self):
        canvas = self.gutter
        text = self.text
        canvas.delete("num")
        content = text.get("1.0", "end")  # 与输入完全一致（含末尾换行）
        paragraphs = content.split("\n")
        has_trailing_newline = content.endswith("\n") or content == ""
        n = len(paragraphs)
        last_y = None
        last_h = self._line_h
        visible_last = False
        for i in range(1, n + 1):
            info = text.dlineinfo(f"{i}.0")
            if not info:
                continue
            _x, y, _w, h, _b = info
            self._draw_number(i, y, h)
            last_y, last_h, visible_last = y, h, True
        # 待输入的空条目（内容为空，或文本以换行结尾）
        if content == "":
            self._draw_number(1, 4, self._line_h)
        elif has_trailing_newline and visible_last and self._is_at_bottom():
            self._draw_number(n, last_y + last_h, self._line_h)

    def _is_at_bottom(self) -> bool:
        """末尾空行是否可见（近似：滚动条在最底部）。"""
        try:
            frac = float(self.text.yview()[1])
            return frac >= 0.999
        except (tk.TclError, ValueError):
            return True

    def _draw_number(self, num: int, y: float, h: float):
        self.gutter.create_text(
            self.GUTTER_WIDTH - 10,
            y + h / 2,
            text=str(num),
            anchor="e",
            font=(mono_family(self.gutter), 11),
            fill="#8a8a8e",
            tags="num",
        )
