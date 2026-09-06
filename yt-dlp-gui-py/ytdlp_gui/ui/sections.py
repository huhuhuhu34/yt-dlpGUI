"""各分区表单构建 —— 对应 Swift 版 Sources/Views/*Section.swift。

每个函数往 container（可滚动画布里的 frame）里追加一张 SectionCard。
统一通过 app 提供的控件工厂创建；条件显隐/派生文案刷新由 App 统一驱动。
"""
from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from .numbered_text import NumberedText
from .widgets import (
    FieldRow,
    SectionCard,
    ToggleRow,
    bind_bool,
    bind_str,
    browse_dir_button,
    browse_file_button,
    check,
    combo_index,
    combo_text,
    divider,
    entry,
    info_text,
    mono_family,
    next_row,
    plain_button,
    set_store_field,
)

__all__ = [
    "build_link_section",
    "build_network_section",
    "build_format_section",
    "build_output_section",
    "build_audio_section",
    "build_subtitle_section",
    "build_metadata_section",
    "build_postprocess_section",
    "build_playlist_section",
    "build_advanced_section",
]

from ytdlp_gui.settings import Settings  # noqa: E402  仅用于类型标注

S = Settings  # noqa: F841  引用静态选项表


def _mono(app, widget):
    widget.configure(font=(mono_family(app.root), 11))
    return widget


# ------------------------------------------------------------------ 链接

def build_link_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "链接（每行一个，可粘贴多个网址）")
    body = card.body
    body.columnconfigure(0, weight=1)

    row_no = next_row(body)

    def on_links_changed():
        app.store.urlsText = numbered.get()
        app.on_field_change()

    numbered = NumberedText(body, height=8, on_change=on_links_changed)
    numbered.grid(row=row_no, column=0, sticky="nwe", padx=(0, 8), pady=(2, 4))
    if app.store.urlsText:
        numbered.set(app.store.urlsText)

    side = ttk.Frame(body)
    side.grid(row=row_no, column=1, sticky="n")

    count_label = ttk.Label(side, text="", foreground="#777777")
    count_label.pack(pady=(2, 0))

    def douyin_prefix():
        base = "https://www.douyin.com/video/"
        text = numbered.get()
        if text.strip():
            numbered.set(text + "\n" + base)
        else:
            numbered.set(base)

    def import_txt():
        import tkinter.filedialog as filedialog

        path = filedialog.askopenfilename(
            parent=app.root, title="选择包含链接的文本文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as fh:
                content = fh.read()
        except OSError as exc:
            app.set_status_text("读取文件失败：" + str(exc))
            return
        text = numbered.get()
        numbered.set(content if not text.strip() else text + "\n" + content)

    def clear_links():
        numbered.set("")

    ttk.Button(side, text="抖音", width=9, command=douyin_prefix).pack(pady=2)
    ttk.Button(side, text="导入 .txt…", width=9, command=import_txt).pack(pady=2)
    ttk.Button(side, text="清空", width=9, command=clear_links).pack(pady=2)

    def refresh_count():
        n = len(app.store.url_lines)
        count_label.configure(text="共 %d 条链接" % n)
    app.add_refresher(refresh_count)

    check(app, body, "ignoreErrors", "下载出错时忽略并继续（-i --ignore-errors）")
    check(app, body, "openOutputFolderWhenDone", "下载成功后自动打开输出文件夹")
    return card


# ------------------------------------------------------------------ 网络 / 登录

def build_network_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "网络 / 登录")
    body = card.body

    # 代理
    check(app, body, "useProxy", "使用代理服务器（--proxy）")
    proxy_row = FieldRow(body, "代理地址", "例如 http://127.0.0.1:1080 或 socks5://…；留空 = 强制直连")
    proxy_row.value(entry(app, proxy_row.value_frame, "proxy", width=44))
    app.add_condition(lambda: bool(app.store.useProxy), proxy_row)

    # Cookies
    cookie_row = FieldRow(body, "Cookies", "需要登录后才能看的视频请选择")
    cookie_mode = combo_index(
        app, cookie_row.value_frame, "cookieMode",
        ["不使用", "Cookie 文件", "从浏览器读取"], width=22)
    cookie_row.value(cookie_mode)
    # 补两个小的占位样式按钮不可行；保持一行下拉即可

    file_row = FieldRow(body, "Cookie 文件", "Netscape 格式，可用浏览器插件导出")
    file_row.value(entry(app, file_row.value_frame, "cookieFile", width=32))
    file_row.value(browse_file_button(app, file_row.value_frame, "cookieFile"))
    app.add_condition(lambda: app.store.cookieMode == 1, file_row)

    browser_row = FieldRow(body, "浏览器", "读取该浏览器已保存的登录状态")
    browser_pick = combo_text(
        app, browser_row.value_frame, "browserCookieSource",
        Settings.browser_list, width=16)
    browser_row.value(browser_pick)
    app.add_condition(lambda: app.store.cookieMode == 2, browser_row)

    divider(body)

    acct_row = FieldRow(body, "账号 / 密码", "部分站点需要登录（--username/--password/--twofactor）")
    acct_row.value(entry(app, acct_row.value_frame, "username", width=16))
    acct_row.value(entry(app, acct_row.value_frame, "password", width=16, show="•"))
    acct_row.value(entry(app, acct_row.value_frame, "twofactor", width=12))

    check(app, body, "useNetrc", "使用 .netrc 认证（--netrc）")

    divider(body)

    rate_row = FieldRow(body, "限速 / 重试 / 并发", "留空即使用 yt-dlp 默认值")
    rate_row.value(entry(app, rate_row.value_frame, "limitRate", width=13))
    rate_row.value(entry(app, rate_row.value_frame, "retries", width=13))
    rate_row.value(entry(app, rate_row.value_frame, "concurrentFragments", width=13))
    return card


# ------------------------------------------------------------------ 格式

def build_format_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "视频格式与画质")
    body = card.body

    preset_row = FieldRow(body, "清晰度方案", "选择后会自动生成 -f 格式表达式")
    preset_combo = combo_index(
        app, preset_row.value_frame, "formatPreset",
        [p.label for p in Settings.format_presets], width=46)
    preset_row.value(preset_combo)

    custom_row = FieldRow(body, "自定义 -f", "例：bestvideo[height<=1080]+bestaudio/best")
    custom_row.value(_mono(app, entry(app, custom_row.value_frame, "customFormat", width=44)))
    app.add_condition(
        lambda: 0 <= app.store.formatPreset < len(Settings.format_presets)
        and Settings.format_presets[app.store.formatPreset].is_custom,
        custom_row)

    eff_row = FieldRow(body, "实际生效", "将附加到命令中的 -f 值")
    eff_label = ttk.Label(eff_row.value_frame, text="", foreground="#444444")
    eff_row.value(_mono(app, eff_label))

    def refresh_eff():
        eff_label.configure(text=app.store.effective_format)
    app.add_refresher(refresh_eff)

    merge_row = FieldRow(body, "合并容器", "需要合并视频+音频时使用的封装格式（需要 ffmpeg）")
    merge_row.value(combo_index(
        app, merge_row.value_frame, "mergeOutputIndex",
        Settings.merge_formats, width=20))
    return card


# ------------------------------------------------------------------ 输出

def build_output_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "输出设置")
    body = card.body

    dir_row = FieldRow(body, "保存到目录", "留空则使用用户主目录；目录不存在时 yt-dlp 会自动创建")
    dir_row.value(entry(app, dir_row.value_frame, "outputDir", width=38))
    dir_row.value(browse_dir_button(app, dir_row.value_frame, "outputDir"))
    dir_row.value(plain_button(app, dir_row.value_frame, "恢复默认",
                               lambda: set_store_field(app, "outputDir", "")))

    resolved_label = ttk.Label(body, text="", foreground="#777777")
    resolved_label.grid(row=next_row(body), column=1, sticky="w", padx=(0, 10))

    def refresh_resolved():
        resolved_label.configure(text="实际路径：" + app.store.resolved_output_dir)
    app.add_refresher(refresh_resolved)

    tmpl_row = FieldRow(body, "文件名模板", "-o 输出模板，yt-dlp 支持 %(title)s 等字段")
    tmpl_row.value(combo_index(
        app, tmpl_row.value_frame, "outputTemplateIndex",
        Settings.output_template_names, width=24))

    custom_tmpl_row = FieldRow(body, "自定义模板")
    custom_tmpl_row.value(_mono(app, entry(
        app, custom_tmpl_row.value_frame, "customOutputTemplate", width=44)))
    app.add_condition(
        lambda: app.store.outputTemplateIndex == len(Settings.output_template_names) - 1,
        custom_tmpl_row)

    overwrite_row = FieldRow(body, "已有文件处理")
    overwrite_row.value(combo_index(
        app, overwrite_row.value_frame, "overwriteMode",
        Settings.overwrite_modes, width=40))

    divider(body)

    mark_toggle = check(app, body, "markEnabled",
                        "下载标记：文件名加批次前缀（001、002…）")

    mark_row = FieldRow(body, "下一个批次号", "每点一次「开始下载」自动 +1")
    mark_no = ttk.Label(mark_row.value_frame, text="000", font=("Helvetica", 15, "bold"),
                        foreground="#007aff")
    mark_row.value(mark_no)
    reset_btn = plain_button(app, mark_row.value_frame, "重置标记",
                             lambda: (set_store_field(app, "markCounter", 0), app.on_field_change()))
    reset_btn.configure(state="disabled")
    mark_row.value(reset_btn)
    app.add_condition(lambda: app.store.markEnabled, mark_row)

    def refresh_mark():
        mark_no.configure(text="%03d" % app.store.next_mark_number)
        reset_btn.configure(state="normal" if app.store.markCounter > 0 else "disabled")
    app.add_refresher(refresh_mark)

    info_text(
        body,
        "效果：文件名变成「001 - 视频标题.mp4」。同一次下载里，同一个网址产生的视频/图片"
        "共用同一前缀；按名称升序 = 下载先后顺序（倒着看用排序降序）。",
        wrap=700)
    return card



# ------------------------------------------------------------------ 音频

def build_audio_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "音频提取（把视频转成纯音频）")
    body = card.body

    check(app, body, "extractAudio", "提取音频（-x --extract-audio，需要 ffmpeg）")

    fmt_row = FieldRow(body, "音频格式", "--audio-format")
    fmt_row.value(combo_index(
        app, fmt_row.value_frame, "audioFormatIndex",
        Settings.audio_formats, width=18))
    app.add_condition(lambda: app.store.extractAudio, fmt_row)

    q_row = FieldRow(body, "音质", "0(最佳)～10(最差)，或直接写码率如 192K")
    q_row.value(entry(app, q_row.value_frame, "audioQuality", width=16))
    app.add_condition(lambda: app.store.extractAudio, q_row)

    hint = ("提示：若选择「合并」画质方案或提取音频，请确保已安装 ffmpeg。"
            "Windows 可 winget install Gyan.FFmpeg；macOS 可 brew install ffmpeg。")
    info_text(body, hint, wrap=700)
    return card


# ------------------------------------------------------------------ 字幕

def build_subtitle_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "字幕")
    body = card.body

    check(app, body, "writeSubs", "下载普通字幕（--write-subs）")
    check(app, body, "writeAutoSubs", "下载自动生成字幕（--write-auto-subs）")

    def subs_visible():
        return app.store.writeSubs or app.store.writeAutoSubs

    lang_row = FieldRow(body, "语言", "--sub-langs，如 zh-Hans,en 或 all（留空默认）")
    lang_row.value(entry(app, lang_row.value_frame, "subLangs", width=26))
    app.add_condition(subs_visible, lang_row)

    fmt_row = FieldRow(body, "字幕格式", "--sub-format，如 srt、ass/srt/best")
    fmt_row.value(entry(app, fmt_row.value_frame, "subFormat", width=26))
    app.add_condition(subs_visible, fmt_row)

    embed_row = ToggleRow(body, "内嵌字幕到视频（--embed-subs）", bind_bool(app, "embedSubs"))
    app.add_condition(subs_visible, embed_row)
    return card


# ------------------------------------------------------------------ 缩略图 / 元数据

def build_metadata_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "缩略图 / 元数据")
    body = card.body
    check(app, body, "writeThumbnail", "保存封面缩略图（--write-thumbnail）")
    check(app, body, "embedMetadata", "把元数据内嵌进文件（--embed-metadata，需要 ffmpeg）")
    check(app, body, "embedThumbnail", "把封面内嵌进文件（--embed-thumbnail）")
    check(app, body, "embedChapters", "把章节信息内嵌进文件（--embed-chapters）")
    return card



# ------------------------------------------------------------------ 后期处理

def build_postprocess_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "后期处理（转封装 / ffmpeg / 章节 / SponsorBlock）")
    body = card.body

    remux_row = FieldRow(body, "转封装格式", "--remux-video；若目标容器不支持编码会失败")
    remux_row.value(combo_index(
        app, remux_row.value_frame, "remuxIndex", Settings.remux_formats, width=20))

    ff_row = FieldRow(body, "ffmpeg 位置", "默认自动搜索 PATH；装在非标准位置可手动指定")
    ff_row.value(entry(app, ff_row.value_frame, "ffmpegLocation", width=36))
    ff_row.value(browse_file_button(app, ff_row.value_frame, "ffmpegLocation"))
    ff_row.value(plain_button(app, ff_row.value_frame, "清空",
                              lambda: set_store_field(app, "ffmpegLocation", "")))

    divider(body)

    wav_row = next_row(body)
    wav_btn = ttk.Button(body, text="🎵 选择文件并转 WAV", command=app.convert_to_wav)
    wav_btn.grid(row=wav_row, column=0, sticky="w", pady=(4, 2))
    info_text(body, "ffmpeg -i 输入文件 -ar 16000 -ac 1 -c:a pcm_s16le 同名.wav（输出在输入同目录）", wrap=700)

    check(app, body, "splitChapters", "按章节拆分视频（--split-chapters）")

    divider(body)

    sb1 = FieldRow(body, "SponsorBlock 标记类别",
                   "赞助/intro/outro/selfpromo/preview/filler/interaction/…；例 sponsor,intro")
    sb1.value(entry(app, sb1.value_frame, "sponsorMark", width=34))

    sb2 = FieldRow(body, "SponsorBlock 移除类别",
                   "移除指定片段；例 sponsor,intro,outro（需要 ffmpeg）")
    sb2.value(entry(app, sb2.value_frame, "sponsorRemove", width=34))
    return card


# ------------------------------------------------------------------ 播放列表

def build_playlist_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "播放列表")
    body = card.body

    mode_row = FieldRow(body, "下载范围", "适用于 YouTube/B站 等含播放列表的链接")
    mode_row.value(combo_index(
        app, mode_row.value_frame, "playlistMode",
        Settings.playlist_modes, width=36))

    item_row = FieldRow(body, "指定条目", "--playlist-items，例：1-5,8,10-")
    item_row.value(entry(app, item_row.value_frame, "playlistItems", width=26))

    arch_row = FieldRow(body, "下载记录", "--download-archive，只下载新增，避免重复（断点记忆）")
    arch_row.value(entry(app, arch_row.value_frame, "downloadArchive", width=34))
    arch_row.value(browse_file_button(app, arch_row.value_frame, "downloadArchive"))
    arch_row.value(plain_button(app, arch_row.value_frame, "清空",
                                lambda: set_store_field(app, "downloadArchive", "")))
    return card


# ------------------------------------------------------------------ 高级

def build_advanced_section(app, container: tk.Widget) -> SectionCard:
    card = SectionCard(container, "高级 / 附加参数")
    body = card.body

    check(app, body, "newlineOutput", "逐行输出日志（--newline，进度更清晰）")

    extra_row = FieldRow(body, "附加自定义参数",
                         "界面未覆盖的任何 yt-dlp 参数都能填在这里，每行一条，支持引号。\n"
                         "例：--no-mtime\n例：--exec 'echo 下载完成'")
    text_box = tk.Text(extra_row.value_frame, height=4, width=52, font=(mono_family(app.root), 11),
                        padx=4, pady=4, undo=True, wrap="word")
    extra_row.value(text_box)
    text_box.insert("1.0", app.store.extraArgs)

    def sync_extra(_event=None):
        new_value = text_box.get("1.0", "end-1c")
        if app.store.extraArgs != new_value:
            app.store.extraArgs = new_value
            app.on_field_change()

    text_box.bind("<<Modified>>", lambda _e: text_box.edit_modified(False) or sync_extra())
    return card

