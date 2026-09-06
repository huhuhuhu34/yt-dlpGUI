"""参数拼接 —— 1:1 移植自 Swift 版 yt-dlp-gui/Sources/ArgBuilder.swift。

把 GUI 表单翻译成 yt-dlp 参数数组（不经过 shell，杜绝转义/注入问题）。
真实执行永远走参数数组；command_preview()/shell_quote() 仅用于展示与复制。
"""
from __future__ import annotations

import os
from urllib.parse import unquote

from .settings import Settings

_WHITESPACE = " \t\n\r\v\f"
_SHELL_SPECIAL = set(_WHITESPACE + "\\'\"&|;<>()$`!*?[]{}#~")


def output_template_with_mark(s: Settings) -> str:
    """输出模板（启用“下载标记”时在文件名的最后一段前注入批次前缀）。"""
    base = s.effective_output_template
    if not s.markEnabled:
        return base
    mark = "%03d" % (s.markCounter + 1)
    parts = base.split("/")  # Swift: split(separator: "/", omittingEmptySubsequences: false)
    if parts and parts[-1]:
        new_parts = parts[:-1] + ["%s - %s" % (mark, parts[-1])]
        return "/".join(new_parts)
    return "%s - %s" % (mark, base)


def douyin_video_url(url_string: str) -> str:
    """从抖音分享链接中提取 modal_id，换算成标准视频链接：
    https://www.douyin.com/user/xxx?...&modal_id=7680222044810744293
      → https://www.douyin.com/video/7680222044810744293
    非 douyin.com 或没有 modal_id 的链接原样返回。
    """
    raw = url_string.strip()
    scheme, sep, rest = raw.partition("://")
    if not sep:
        return url_string
    host, _, _ = rest.partition("/")
    # host 可能带端口；与 Swift 一致仅比较 contains
    if "douyin.com" not in host.lower():
        return url_string
    # 取 query 段（第一个 # 之前）
    path_and_query = rest[len(host):]
    query_part = path_and_query.partition("?")[2]
    query_part = query_part.partition("#")[0]
    for item in query_part.split("&"):
        if not item:
            continue
        k, _, v = item.partition("=")
        if k.lower() == "modal_id" and v:
            return "https://www.douyin.com/video/" + unquote(v)
    return url_string


def tokenize_line(line: str) -> list[str]:
    """把一行字符串按空白拆成 token，支持单双引号（= Swift tokenizeLine）。"""
    tokens: list[str] = []
    current = ""
    quote: str | None = None
    started = False
    for ch in line:
        if quote is not None:
            if ch == quote:
                quote = None
            else:
                current += ch
        elif ch in ("'", '"'):
            quote = ch
            started = True
        elif ch in _WHITESPACE:
            if started:
                tokens.append(current)
                current = ""
                started = False
        else:
            current += ch
            started = True
    if started:
        tokens.append(current)
    return tokens


def _trimmed(x: str) -> str:
    return x.strip()


def build_args(s: Settings) -> list[str]:
    """组装正式参数（不含末尾的 URL），顺序与 Swift 版一致。"""
    a: list[str] = []
    add = a.extend

    # ---- 通用 ----
    if s.ignoreErrors:
        a.append("-i")
    if s.newlineOutput:
        a.append("--newline")

    # ---- 网络 / 登录 ----
    if s.useProxy:
        p = _trimmed(s.proxy)
        add(["--proxy", p])  # 空字符串 = 强制直连
    if s.cookieMode == 1:
        if _trimmed(s.cookieFile):
            add(["--cookies", _trimmed(s.cookieFile)])
    elif s.cookieMode == 2:
        add(["--cookies-from-browser", _trimmed(s.browserCookieSource)])
    if _trimmed(s.username):
        add(["--username", _trimmed(s.username)])
    if s.password:
        add(["--password", s.password])
    if _trimmed(s.twofactor):
        add(["--twofactor", _trimmed(s.twofactor)])
    if s.useNetrc:
        a.append("--netrc")
    if _trimmed(s.limitRate):
        add(["--limit-rate", _trimmed(s.limitRate)])
    if _trimmed(s.retries):
        add(["--retries", _trimmed(s.retries)])
    if _trimmed(s.concurrentFragments):
        add(["--concurrent-fragments", _trimmed(s.concurrentFragments)])

    # ---- 格式 ----
    add(["-f", s.effective_format])
    if s.effective_merge_format is not None:
        add(["--merge-output-format", s.effective_merge_format])

    # ---- 输出 ----
    if _trimmed(s.outputDir):
        add(["-P", s.resolved_output_dir])
    add(["-o", output_template_with_mark(s)])
    if s.overwriteMode == 1:
        a.append("-w")
    elif s.overwriteMode == 2:
        a.append("--force-overwrites")

    # ---- 音频 ----
    if s.extractAudio:
        a.append("-x")
        fmt = s.effective_audio_format
        if fmt != "默认 (best)" and fmt != "best":
            add(["--audio-format", fmt])
        if _trimmed(s.audioQuality):
            add(["--audio-quality", _trimmed(s.audioQuality)])

    # ---- 字幕 ----
    if s.writeSubs:
        a.append("--write-subs")
    if s.writeAutoSubs:
        a.append("--write-auto-subs")
    if _trimmed(s.subLangs):
        add(["--sub-langs", _trimmed(s.subLangs)])
    if _trimmed(s.subFormat):
        add(["--sub-format", _trimmed(s.subFormat)])

    # ---- 元数据 / 缩略图 ----
    if s.writeThumbnail:
        a.append("--write-thumbnail")
    if s.embedMetadata:
        a.append("--embed-metadata")
    if s.embedThumbnail:
        a.append("--embed-thumbnail")
    if s.embedChapters:
        a.append("--embed-chapters")
    if s.embedSubs:
        a.append("--embed-subs")

    # ---- 后期处理 ----
    if s.effective_remux is not None:
        add(["--remux-video", s.effective_remux])
    if _trimmed(s.ffmpegLocation):
        add(["--ffmpeg-location", _trimmed(s.ffmpegLocation)])
    if s.splitChapters:
        a.append("--split-chapters")
    if _trimmed(s.sponsorMark):
        add(["--sponsorblock-mark", _trimmed(s.sponsorMark)])
    if _trimmed(s.sponsorRemove):
        add(["--sponsorblock-remove", _trimmed(s.sponsorRemove)])

    # ---- 播放列表 ----
    if s.playlistMode == 1:
        a.append("--no-playlist")
    elif s.playlistMode == 2:
        a.append("--yes-playlist")
    if _trimmed(s.playlistItems):
        add(["--playlist-items", _trimmed(s.playlistItems)])
    if _trimmed(s.downloadArchive):
        add(["--download-archive", os.path.expanduser(_trimmed(s.downloadArchive))])

    # ---- 附加自定义参数（每行解析） ----
    for line in s.extraArgs.splitlines():
        add(tokenize_line(line))

    return a


def command_preview(exe: str, args: list[str]) -> str:
    """供预览/复制用的 shell 风格字符串。"""
    return " ".join(shell_quote(x) for x in ([exe] + args))


def shell_quote(s: str) -> str:
    """bash 风格引号（仅展示/复制用，执行不经 shell）。"""
    if not s:
        return "''"
    if not any(c in _SHELL_SPECIAL for c in s):
        return s
    return "'" + s.replace("'", "'\\''") + "'"
