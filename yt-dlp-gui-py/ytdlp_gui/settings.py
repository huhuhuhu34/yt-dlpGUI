"""设置存储 —— 1:1 移植自 Swift 版 yt-dlp-gui/Sources/SettingsStore.swift。

持久化差异说明：Swift 用 UserDefaults（key 前缀 ytdlpgui.），Python 版改为
JSON 文件（默认 ~/.ytdlpgui/config.json，可用 config_file 覆盖以便测试隔离）。
key 名与 Swift 完全一致，字段/默认值与源码一一对应。

本模块不依赖 tkinter，逻辑层与 UI 分离，可直接单测。
"""
from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class FormatPreset:
    """对应 Swift SettingsStore.FormatPreset。"""

    __slots__ = ("label", "value", "is_custom")

    def __init__(self, label: str, value: str, is_custom: bool = False):
        self.label = label
        self.value = value
        self.is_custom = is_custom


class Settings:
    """全部表单参数与持久化（= SettingsStore）。"""

    # ---- 默认配置路径（Windows: %USERPROFILE%\\.ytdlpgui\\config.json）----
    CONFIG_DIR: Path = Path.home() / ".ytdlpgui"
    CONFIG_FILE: Path = CONFIG_DIR / "config.json"

    # ====== 静态选项表（与 Swift 一一对应） ======
    format_presets: list[FormatPreset] = [
        FormatPreset("最佳质量（单文件 best）", "best"),
        FormatPreset("最佳视频+最佳音频（合并，推荐）", "bestvideo*+bestaudio/best"),
        FormatPreset("≤ 1080p（合并）", "bestvideo[height<=1080]+bestaudio/best[height<=1080]"),
        FormatPreset("≤ 720p（合并）", "bestvideo[height<=720]+bestaudio/best[height<=720]"),
        FormatPreset("≤ 480p（合并）", "bestvideo[height<=480]+bestaudio/best[height<=480]"),
        FormatPreset("仅音频（ba/best）", "ba/best"),
        FormatPreset("自定义格式表达式…", "", is_custom=True),
    ]
    audio_formats: list[str] = ["默认 (best)", "mp3", "m4a", "aac", "flac", "opus", "vorbis", "wav", "alac"]
    merge_formats: list[str] = ["不指定容器", "mp4", "mkv", "webm"]
    remux_formats: list[str] = ["不转封装", "mp4", "mkv", "webm", "mov"]
    output_template_names: list[str] = ["标题", "标题 + ID", "上传日期 + 标题", "按播放列表分目录", "自定义…"]
    output_template_values: list[str] = [
        "%(title)s.%(ext)s",
        "%(title)s [%(id)s].%(ext)s",
        "%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s",
        "%(playlist_title)s/%(playlist_index)02d %(title)s.%(ext)s",
        "",
    ]
    browser_list: list[str] = ["safari", "chrome", "chromium", "edge", "firefox", "brave", "opera", "vivaldi", "whale"]
    overwrite_modes: list[str] = ["续传（默认 -c）", "不覆盖已有文件 (-w)", "强制覆盖 (--force-overwrites)"]
    playlist_modes: list[str] = ["自动判断", "仅下载当前视频 (--no-playlist)", "强制下载整个列表 (--yes-playlist)"]

    # ====== 默认值表（属性名 = Swift 持久化 key） ======
    _DEFAULTS: dict[str, Any] = {
        # 链接
        "urlsText": "", "ignoreErrors": False, "openOutputFolderWhenDone": True,
        # 网络 / 登录
        "useProxy": False, "proxy": "", "cookieMode": 0, "cookieFile": "",
        "browserCookieSource": "safari", "username": "", "password": "",
        "twofactor": "", "useNetrc": False, "limitRate": "", "retries": "",
        "concurrentFragments": "",
        # 视频格式
        "formatPreset": 1, "customFormat": "", "mergeOutputIndex": 0,
        # 输出
        "outputDir": "", "outputTemplateIndex": 0, "customOutputTemplate": "",
        "overwriteMode": 0,
        # 音频
        "extractAudio": False, "audioFormatIndex": 0, "audioQuality": "",
        # 字幕
        "writeSubs": False, "writeAutoSubs": False, "subLangs": "", "subFormat": "",
        # 元数据 / 缩略图
        "writeThumbnail": False, "embedMetadata": False, "embedThumbnail": False,
        "embedChapters": False, "embedSubs": False,
        # 后期处理
        "remuxIndex": 0, "ffmpegLocation": "", "splitChapters": False,
        "sponsorMark": "", "sponsorRemove": "",
        # 播放列表
        "playlistMode": 0, "playlistItems": "", "downloadArchive": "",
        # 行为 / 高级
        "newlineOutput": True, "extraArgs": "",
        # 下载标记
        "markEnabled": False, "markCounter": 0,
    }

    def __init__(self, config_file: str | os.PathLike | None = None):
        self._config_file = Path(config_file) if config_file else self.CONFIG_FILE
        self.reset_to_defaults()
        self.load()

    # ---- 序列化范围 ----
    @property
    def persisted_keys(self) -> list[str]:
        return list(self._DEFAULTS.keys())

    def reset_to_defaults(self) -> None:
        for key, default in self._DEFAULTS.items():
            setattr(self, key, default)

    # MARK: 读取 / 保存

    def load(self) -> None:
        """从 JSON 读取；文件缺失或损坏时静默保持默认值。"""
        if not self._config_file.exists():
            return
        try:
            data = json.loads(self._config_file.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return
        if not isinstance(data, dict):
            return
        for key, default in self._DEFAULTS.items():
            if key not in data:
                continue
            value = data[key]
            # 类型不符（旧版本/手改坏）时丢弃该项
            if isinstance(default, bool):
                if isinstance(value, bool):
                    setattr(self, key, value)
            elif isinstance(default, int):
                if isinstance(value, int) and not isinstance(value, bool):
                    setattr(self, key, value)
            elif isinstance(default, str):
                if isinstance(value, str):
                    setattr(self, key, value)

    def save(self) -> None:
        """立即把全部字段写回 JSON（原子写，避免进程中断损坏配置）。"""
        data = {key: getattr(self, key) for key in self._DEFAULTS}
        try:
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._config_file.with_suffix(".json.tmp")
            tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            tmp.replace(self._config_file)
        except OSError:
            pass  # 无法写配置不应阻塞使用

    # ====== 供参数拼接使用的解析结果（= Swift computed） ======

    @property
    def url_lines(self) -> list[str]:
        from .arg_builder import douyin_video_url  # 延迟导入避免循环依赖

        out: list[str] = []
        for raw in self.urlsText.splitlines():
            line = raw.strip()
            if line:
                out.append(douyin_video_url(line))
        return out

    @property
    def effective_format(self) -> str:
        i = self.formatPreset
        if 0 <= i < len(self.format_presets):
            p = self.format_presets[i]
            if p.is_custom:
                c = self.customFormat.strip()
                return c if c else "bestvideo*+bestaudio/best"
            return p.value
        return "bestvideo*+bestaudio/best"

    @property
    def effective_audio_format(self) -> str:
        i = self.audioFormatIndex
        if 0 <= i < len(self.audio_formats):
            return self.audio_formats[i]
        return "best"

    @property
    def effective_merge_format(self) -> str | None:
        i = self.mergeOutputIndex
        if i > 0 and i < len(self.merge_formats):
            return self.merge_formats[i]
        return None

    @property
    def effective_remux(self) -> str | None:
        i = self.remuxIndex
        if i > 0 and i < len(self.remux_formats):
            return self.remux_formats[i]
        return None

    @property
    def effective_output_template(self) -> str:
        i = self.outputTemplateIndex
        if i == len(self.output_template_names) - 1:
            c = self.customOutputTemplate.strip()
            return c if c else "%(title)s.%(ext)s"
        if 0 <= i < len(self.output_template_values):
            return self.output_template_values[i]
        return "%(title)s.%(ext)s"

    @property
    def resolved_output_dir(self) -> str:
        """输出目录（空则退回用户主目录），展开 ~。"""
        t = self.outputDir.strip()
        if not t:
            return str(Path.home())
        return os.path.expanduser(t)

    # ---- 下载标记（文件名批次前缀） ----

    @property
    def next_mark_number(self) -> int:
        return self.markCounter + 1

    def consume_mark_number(self) -> int:
        """「开始下载」真正运行时消费一个批次号。"""
        self.markCounter += 1
        return self.markCounter

    def reset_mark(self) -> None:
        """重置标记：清零，下次从 001 开始。"""
        self.markCounter = 0

