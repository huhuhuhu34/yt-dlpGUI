"""参数拼接自检 —— 逐条移植自 Swift 版 yt-dlp-gui/tests/main.swift。

运行：python -m pytest yt-dlp-gui-py/tests -q
"""
import os

import pytest

from ytdlp_gui import arg_builder as A
from ytdlp_gui.settings import Settings

failures = []  # noqa  (等价 main.swift 的 failures 计数，改用 pytest 报告)


@pytest.fixture
def s(tmp_path):
    """每个用例独立配置路径，避免读到本机真实配置影响断言（等价 main.swift 用全新 store）。"""
    store = Settings(config_file=tmp_path / "config.json")
    store.markEnabled = False  # 防止读取到历史持久化的标记配置影响断言
    return store


def test_多行_url_按行拆分并保留(s):
    s.urlsText = "https://example.com/watch?v=abc123\nhttps://a/b"
    args = A.build_args(s)
    args += s.url_lines
    assert "https://example.com/watch?v=abc123" in args
    assert "https://a/b" in args


def test_modal_id_提取为标准视频链接(s):
    sample = ("https://www.douyin.com/user/MS4wLjABAAAA0l_9-4Qdks_mRt4AmCVJCiydf-"
              "TDzQlQ0CkELB66I-8?from_tab_name=main&modal_id=7680222044810744293")
    assert A.douyin_video_url(sample) == "https://www.douyin.com/video/7680222044810744293"


def test_modal_id_参数乱序也能提取(s):
    assert (A.douyin_video_url("https://www.douyin.com/user/abc?modal_id=123456789&from=main")
            == "https://www.douyin.com/video/123456789")


def test_已是视频链接保持不变(s):
    assert (A.douyin_video_url("https://www.douyin.com/video/123456789")
            == "https://www.douyin.com/video/123456789")


def test_非抖音链接保持不变(s):
    assert A.douyin_video_url("https://example.com/x?modal_id=1") == "https://example.com/x?modal_id=1"


def test_无_modal_id_保持不变(s):
    assert (A.douyin_video_url("https://www.douyin.com/user/xyz")
            == "https://www.douyin.com/user/xyz")


def test_默认_f_为合并最佳视频_音频(s):
    s.urlsText = "https://example.com/watch?v=abc123\nhttps://a/b"
    args = A.build_args(s) + s.url_lines
    i = args.index("-f")
    assert args[i + 1] == "bestvideo*+bestaudio/best"


def test_音频提取(s):
    s.extractAudio = True
    s.audioFormatIndex = 1
    args = A.build_args(s)
    assert "-x" in args
    i = args.index("--audio-format")
    assert args[i + 1] == "mp3"


def test_代理(s):
    s.useProxy = True
    s.proxy = "http://127.0.0.1:1080"
    args = A.build_args(s)
    i = args.index("--proxy")
    assert args[i + 1] == "http://127.0.0.1:1080"


def test_从浏览器读_cookies(s):
    s.cookieMode = 2
    s.browserCookieSource = "safari"
    args = A.build_args(s)
    i = args.index("--cookies-from-browser")
    assert args[i + 1] == "safari"


def test_附加参数解析_含引号(s):
    s.extraArgs = '--no-mtime\n--exec "echo done"'
    args = A.build_args(s)
    assert "--no-mtime" in args
    i = args.index("--exec")
    assert args[i + 1] == "echo done"


def test_自定义输出模板(s):
    s.extraArgs = ""
    s.outputTemplateIndex = 4
    s.customOutputTemplate = "VID %(id)s.%(ext)s"
    args = A.build_args(s)
    i = args.index("-o")
    assert args[i + 1] == "VID %(id)s.%(ext)s"


def test_标记注入_001_前缀(s):
    s.outputTemplateIndex = 0
    s.markEnabled = True
    s.markCounter = 0
    args = A.build_args(s)
    i = args.index("-o")
    assert args[i + 1] == "001 - %(title)s.%(ext)s"


def test_批次递增到_004(s):
    s.outputTemplateIndex = 0
    s.markEnabled = True
    s.markCounter = 3
    args = A.build_args(s)
    i = args.index("-o")
    assert args[i + 1] == "004 - %(title)s.%(ext)s"


def test_重置后下一个批次号为_001(s):
    s.reset_mark()
    assert s.next_mark_number == 1


def test_带目录模板时前缀只加在文件名段(s):
    s.outputTemplateIndex = 3
    s.markEnabled = True
    s.markCounter = 2
    args = A.build_args(s)
    i = args.index("-o")
    assert args[i + 1] == "%(playlist_title)s/003 - %(playlist_index)02d %(title)s.%(ext)s"


def test_P_输出目录展开含空格(s):
    s.outputTemplateIndex = 0
    s.markEnabled = False
    s.outputDir = "~/yt-dlp Test"
    args = A.build_args(s)
    i = args.index("-P")
    assert args[i + 1] == os.path.expanduser("~/yt-dlp Test")
    assert args[i + 1].endswith("yt-dlp Test")


def test_播放列表_覆盖策略(s):
    s.outputDir = ""
    s.playlistMode = 1
    args = A.build_args(s)
    assert "--no-playlist" in args
    s.overwriteMode = 1
    args = A.build_args(s)
    assert "-w" in args
    s.overwriteMode = 2
    args = A.build_args(s)
    assert "--force-overwrites" in args


def test_shell_引号(s):
    assert A.shell_quote("hello") == "hello"
    assert A.shell_quote("a b") == "'a b'"
    assert A.shell_quote("it's") == "'it'\\''s'"


# ---- 补充：Swift 版未覆盖但 Python 版新增的等价性断言 ----

def test_consume_mark_number(s):
    s.markEnabled = True
    s.markCounter = 0
    assert s.next_mark_number == 1
    assert s.consume_mark_number() == 1
    assert s.consume_mark_number() == 2
    assert s.next_mark_number == 3
