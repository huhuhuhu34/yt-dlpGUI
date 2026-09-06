"""通用 ttk 控件与绑定辅助 —— 对应 Swift Components.swift（SectionCard /
FieldRow）与各 Section 的共用控件工厂。

设计：每个“表单行”占据 grid 的一行。行号不依赖 grid_size（否则 grid_remove
隐藏行后会把计数弄乱），而是由 next_row() 在 Python 侧单调递增。

所有控件改动都写回 app.store 并触发 app.on_field_change()（联动显隐 /
命令预览 / 防抖保存 / 下拉框同步）。
"""
from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from tkinter import ttk

_MONO_CANDIDATES = ("Menlo", "Consolas", "Courier New", "monospace")


def mono_family(root: tk.Misc) -> str:
    for name in _MONO_CANDIDATES:
        try:
            tkfont.Font(root=root, family=name, size=11)
            return name
        except tk.TclError:
            continue
    return "TkFixedFont"


def next_row(widget: tk.Widget) -> int:
    """给 grid 容器的下一个行号（Python 侧单调递增，删除不影响）。"""
    row = getattr(widget, "_row_counter", 0)
    setattr(widget, "_row_counter", row + 1)
    return row


# ---------------------------------------------------------------- 布局块

class SectionCard(ttk.LabelFrame):
    """带标题的分组卡片（对应 Swift SectionCard/GroupBox）。"""

    def __init__(self, master, title: str, padding: int = 12):
        super().__init__(master, text="  " + title + "  ", padding=padding)
        self.body = ttk.Frame(self)
        self.body.pack(fill="x", expand=True)
        self.body.columnconfigure(1, weight=1)


class FieldRow:
    """左侧标签(+帮助) + 右侧控件。row.set_visible(bool) 支持条件显隐。"""

    def __init__(self, parent: tk.Widget, label: str, help_text: str = "", width: int = 170):
        self._grid = parent
        self._row = next_row(parent)
        bg = FieldRow._theme_bg(parent)
        self._label_frame = tk.Frame(parent, bg=bg)
        self._label_frame.grid(row=self._row, column=0, sticky="nw", padx=(0, 10), pady=(5, 2))
        self.label = ttk.Label(self._label_frame, text=label, width=width, anchor="w")
        self.label.pack(anchor="w")
        if help_text:
            note = ttk.Label(
                self._label_frame, text=help_text, foreground="#777777",
                width=width, wraplength=width * 5, justify="left",
            )
            note.pack(anchor="w")
        self.value_frame = ttk.Frame(parent)
        self.value_frame.grid(row=self._row, column=1, sticky="w", pady=(3, 2))
        self._visible = True

    def value(self, widget: tk.Widget) -> tk.Widget:
        widget.pack(side="left", anchor="w", padx=(0, 6))
        return widget

    def set_visible(self, visible: bool) -> None:
        if visible == self._visible:
            return
        self._visible = visible
        if visible:
            self._label_frame.grid()
            self.value_frame.grid()
        else:
            self._label_frame.grid_remove()
            self.value_frame.grid_remove()

    @staticmethod
    def _theme_bg(widget: tk.Widget) -> str:
        try:
            style = widget.cget("style") or "TFrame"
            bg = widget.tk.call("ttk::style", "lookup", style, "background")
            return bg if bg else "#f0f0f0"
        except tk.TclError:
            return "#f0f0f0"


class ToggleRow:
    """整行复选项（对应 Swift 的 Toggle）。"""

    def __init__(self, parent: tk.Widget, text: str, var: tk.BooleanVar):
        self._grid = parent
        self._row = next_row(parent)
        self.ck = ttk.Checkbutton(parent, text=text, variable=var)
        self.ck.grid(row=self._row, column=0, columnspan=2, sticky="w", pady=(3, 2))

    def set_visible(self, visible: bool) -> None:
        self.ck.grid() if visible else self.ck.grid_remove()


def info_text(parent: tk.Widget, text: str, wrap: int = 720) -> ttk.Label:
    """次要说明文字（占满两列，可换行）。"""
    row = next_row(parent)
    note = ttk.Label(parent, text=text, foreground="#777777", wraplength=wrap, justify="left")
    note.grid(row=row, column=0, columnspan=2, sticky="w", pady=(2, 4))
    return note


def divider(parent: tk.Widget) -> ttk.Separator:
    row = next_row(parent)
    sep = ttk.Separator(parent, orient="horizontal")
    sep.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(6, 4))
    return sep


# ---------------------------------------------------------------- 变量绑定

def _var(app, kind: str, key: str, default):
    """创建并注册 tk 变量，变化时写回 store[key] 并触发联动刷新。"""
    if kind == "str":
        var = tk.StringVar(master=app.root, value=str(getattr(app.store, key)))
    elif kind == "bool":
        var = tk.BooleanVar(master=app.root, value=bool(getattr(app.store, key)))
    else:
        var = tk.IntVar(master=app.root, value=int(getattr(app.store, key)))

    def write(*_):
        try:
            new_value = var.get() if kind != "int" else int(var.get())
        except (tk.TclError, ValueError):
            return
        new_value = bool(new_value) if kind == "bool" else new_value
        if getattr(app.store, key) != new_value:
            setattr(app.store, key, new_value)
            app.on_field_change()

    var.trace_add("write", write)
    app.tk_vars[key] = var
    return var


def bind_str(app, key: str) -> tk.StringVar:
    return _var(app, "str", key, "")


def bind_bool(app, key: str) -> tk.BooleanVar:
    return _var(app, "bool", key, False)


def bind_int(app, key: str) -> tk.IntVar:
    return _var(app, "int", key, 0)


def set_store_field(app, key: str, value) -> None:
    """程序化修改表单值（如「抖音」按钮插入链接），并同步已绑定的控件。"""
    setattr(app.store, key, value)
    var = app.tk_vars.get(key)
    if var is not None:
        var.set(value)
    app.on_field_change()


# ---------------------------------------------------------------- 控件工厂

def entry(app, parent: tk.Widget, key: str, width: int = 30, show: str | None = None,
          mono: bool = False) -> ttk.Entry:
    var = bind_str(app, key)
    e = ttk.Entry(parent, textvariable=var, width=width, show=show)
    if mono:
        e.configure(font=(mono_family(app.root), 11))
    return e


def check(app, parent: tk.Widget, key: str, text: str) -> ToggleRow:
    """复选项：一行占两列。"""
    var = bind_bool(app, key)
    row = ToggleRow(parent, text, var)
    return row


def combo_index(app, parent: tk.Widget, key: str, options: list[str],
                width: int = 32, mono: bool = False) -> ttk.Combobox:
    """只读下拉框，选中项下标写入 store[key]（等价 Swift Picker.tag）。"""
    cb = ttk.Combobox(parent, state="readonly", values=options, width=width)
    idx = max(0, min(int(getattr(app.store, key)), len(options) - 1))
    cb.current(idx)

    def on_select(_event=None):
        new_idx = cb.current()
        if new_idx >= 0 and getattr(app.store, key) != new_idx:
            setattr(app.store, key, new_idx)
            app.on_field_change()

    cb.bind("<<ComboboxSelected>>", on_select)
    if mono:
        cb.configure(font=(mono_family(app.root), 11))
    app.combo_syncs.append((key, cb))
    return cb


def combo_text(app, parent: tk.Widget, key: str, options: list[str],
               width: int = 32) -> ttk.Combobox:
    """只读下拉框，选中项文本写入 store[key]（字符串字段用）。"""
    var = bind_str(app, key)
    value = str(getattr(app.store, key))
    cb = ttk.Combobox(parent, state="readonly", values=options, width=width, textvariable=var)
    if value in options:
        cb.current(options.index(value))
    else:
        cb.set(value)

    def on_select(_event=None):
        var.set(cb.get())
        # bind_str 的 trace 已写回 store 并触发 on_field_change

    cb.bind("<<ComboboxSelected>>", on_select)
    return cb


def browse_file_button(app, parent: tk.Widget, target_key: str,
                       filetypes=None, text: str = "浏览…") -> ttk.Button:
    import tkinter.filedialog as filedialog

    if filetypes is None:
        filetypes = [("所有文件", "*.*")]

    def on_click():
        path = filedialog.askopenfilename(parent=app.root, title="选择文件", filetypes=filetypes)
        if path:
            set_store_field(app, target_key, path)

    return ttk.Button(parent, text=text, command=on_click)


def browse_dir_button(app, parent: tk.Widget, target_key: str, text: str = "浏览…") -> ttk.Button:
    import tkinter.filedialog as filedialog

    def on_click():
        path = filedialog.askdirectory(parent=app.root, title="选择目录")
        if path:
            set_store_field(app, target_key, path)

    return ttk.Button(parent, text=text, command=on_click)


def plain_button(app, parent: tk.Widget, text: str, command, width: int | None = None) -> ttk.Button:
    return ttk.Button(parent, text=text, command=command, width=width)


def copy_to_clipboard(app, text: str) -> None:
    if text:
        app.root.clipboard_clear()
        app.root.clipboard_append(text)

