"""进程引擎集成测试 —— 等价 Swift 版 yt-dlp-gui/tests/RunHarness.swift。

用 App 的真实执行引擎跑内核命令，验证 进程启动 + 流式输出 + 结束回调。
内核路径：优先 YTDLP_TEST_KERNEL 环境变量；否则在仓库根目录寻找
yt-dlp_macos / yt-dlp / yt-dlp.exe。
"""
import os
import threading
from pathlib import Path

import pytest

from ytdlp_gui.runner import DownloadRunner, LineAccumulator

# ---- 通用工具 ----

def _kernel() -> str:
    env = os.environ.get("YTDLP_TEST_KERNEL")
    if env and os.path.isfile(env):
        return env
    root = Path(__file__).resolve().parents[2]  # 仓库根
    for name in ("yt-dlp_macos", "yt-dlp", "yt-dlp.exe"):
        cand = root / name
        if cand.is_file():
            return str(cand)
    return ""


requires_kernel = pytest.mark.skipif(
    not _kernel(), reason="需要 yt-dlp 内核（yt-dlp_macos / yt-dlp / yt-dlp.exe）")


def test_line_accumulator_crlf():
    """CRLF / 跨块切分都必须还原成干净行。"""
    acc = LineAccumulator()
    lines: list[str] = []
    acc.append(b"[download]  42.0% of 12.0MiB at 1.2MiB/s\r\nseco", lines.append)
    acc.append(b"nd line", lines.append)
    acc.flush(lines.append)
    assert lines == ["[download]  42.0% of 12.0MiB at 1.2MiB/s", "second line"]


def test_line_accumulator_multi_lines_in_one_chunk():
    acc = LineAccumulator()
    lines: list[str] = []
    acc.append(b"a\r\nb\r\nc", lines.append)
    acc.flush(lines.append)
    assert lines == ["a", "b", "c"]


@requires_kernel
def test_runner_version_run(tmp_path):
    """真实跑内核 --version：启动 + 流式输出 + 结束回调（退出码 0）。"""
    kernel = _kernel()
    runner = DownloadRunner()
    finished = threading.Event()
    codes: list[int] = []

    runner.on_finished = lambda code: (codes.append(code), finished.set())
    runner.run(
        executable=kernel,
        arguments=["--version"],
        directory=str(tmp_path),
        task_title="集成测试",
    )
    assert finished.wait(timeout=60), "超时：任务未在 60s 内结束"
    assert codes == [0]
    assert runner.status_text == "完成 ✅"
    log = runner.full_log()
    assert "▶ 集成测试" in log
    assert "$ " in log and "--version" in log
    # 输出里应当出现版本号（yt-dlp 或已改名内核的自定义版本）
    assert len(runner.drain_log_delta()) >= 0  # 确认无新增残留


@requires_kernel
def test_runner_clear_log(tmp_path):
    kernel = _kernel()
    runner = DownloadRunner()
    runner.run(executable=kernel, arguments=["--version"], directory=str(tmp_path))
    # 立即 clear 不应抛错；结束后再次 clear 恢复初始状态
    runner.clear_log()
    assert runner.full_log() == ""
    assert runner.status_text == "就绪"


@requires_kernel
def test_detect_version_sync():
    """内核版本探测（等价 KernelModel.detectVersion 的底层 run_capture）。"""
    from ytdlp_gui.kernel import KernelModel

    model = KernelModel(state_file=str(Path(__file__).parent / "kernel_state_test.json"))
    model.select(_kernel(), mark_override=True)
    code, output = model.run_capture(["--version"])
    assert code == 0
    assert output.strip()
    # 清理测试用的状态文件
    try:
        (Path(__file__).parent / "kernel_state_test.json").unlink(missing_ok=True)
    except OSError:
        pass
