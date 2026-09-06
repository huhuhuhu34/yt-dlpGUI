# yt-dlpGUI（跨平台版 · Python/tkinter）— 面向 Windows

同一套代码可在 **macOS 开发调试、Windows 正式运行**。GUI 逻辑 1:1 移植自同仓库的
Swift 版（`../yt-dlp-gui/Sources`），Windows 分发包由 GitHub Actions 自动产出
（`yt-dlpGUI.exe` + 官方 `yt-dlp.exe` 内核，解压即用、无需安装 Python）。

## 特性（与 Swift 版对齐）

- **自包含分发**：`yt-dlp.exe`（官方自包含内核）与 GUI 同目录，双击即用；
  也支持「选择…/自动搜索/一键下载内核」指定任意新版内核。
- **完整参数表单**：格式/画质、输出目录与文件名模板、下载标记（001-前缀）、
  音频提取、字幕、缩略图/元数据内嵌、转封装、播放列表、代理/Cookies/登录、
  SponsorBlock、WAV 转换、附加自定义参数（安全解析、不经 shell）。
- **运行引擎**：直接 exec 内核（参数数组，无注入），实时日志 + 进度百分比 +
  可取消；完成后自动打开输出目录。
- **跨平台**：Windows / macOS / Linux 均可用同一源码直接运行。

## 快速开始（源码运行）

> 运行时仅依赖 **Python 3.9+ 与 tkinter**（标准库，无任何第三方包）。
> Homebrew 版 Python 需 `brew install python-tk@3.14`；python.org 安装包自带 tkinter。

```bash
cd yt-dlp-gui-py
python ytdlpGUI.py            # 启动图形界面
python ytdlpGUI.py --selftest # 自检：构建界面并自动退出（CI 冒烟用）
```

首次启动会自动查找仓库根目录的 `yt-dlp_macos`（macOS）或旁边的 `yt-dlp.exe`
（Windows），也可点「下载内核」在线获取官方最新版。

## 测试

```bash
python -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
pytest -q tests
```

- `tests/test_args.py` —— 逐条移植 Swift `tests/main.swift` 的参数拼接断言；
- `tests/test_runner.py` —— 真跑内核（`--version`）验证进程/流式输出/结束回调。
  内核路径通过环境变量指定：`YTDLP_TEST_KERNEL=/path/yt-dlp.exe`，缺省则跳过。

## 打包 Windows 单文件 exe

PyInstaller **不支持交叉编译**，必须在 Windows 上打包。两种方式任选：

1. **GitHub Actions（推荐）**：仓库已带
   [`.github/workflows/windows-build.yml`](../.github/workflows/windows-build.yml)。
   推送 `v*` tag 或在 Actions 页手动运行 → 下载 `yt-dlpGUI-windows` 工件
   （内含 `yt-dlpGUI.exe` + `yt-dlp.exe` + 说明）。
2. **本机手动**（Windows 电脑上执行）：

   ```powershell
   pip install pyinstaller
   python -m PyInstaller --noconfirm --clean yt-dlpGUI.spec
   # 再把官方内核放同一目录
   Invoke-WebRequest https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe -OutFile dist\yt-dlp.exe
   ```

## Windows 使用说明（分发包）

1. 解压 zip：**`yt-dlpGUI.exe` 与 `yt-dlp.exe` 必须放在同一文件夹**（自包含）。
2. 双击 `yt-dlpGUI.exe`，顶部显示「✅ 内核就绪」即可粘贴链接下载。
3. 需要合并音视频 / 提取音频 / 内嵌字幕 / SponsorBlock 移除时安装 ffmpeg：

   ```powershell
   winget install Gyan.FFmpeg
   ```
   或在表单「ffmpeg 位置」里指定 `ffmpeg.exe` 路径。

## 与 Swift（macOS）版的差异

| 项 | Swift 版 | 本版 |
|---|---|---|
| UI 框架 | SwiftUI / AppKit | tkinter / ttk |
| 配置存储 | UserDefaults | `~/.ytdlpgui/config.json` |
| 链接列表行号 | ①②③ 圆形字符 | 普通阿拉伯数字（Windows 字体兼容性） |
| 「行首退格删整条」 | 有 | 未移植（装饰性编辑手势） |
| 命令预览拖动杆 | 有 | 水平滚动条 |
| 授权（chmod/隔离标记） | macOS 专属 | Windows 自动跳过；macOS 保留 |

## 目录结构

```text
yt-dlp-gui-py/
├── ytdlpGUI.py            # 入口
├── ytdlp_gui/
│   ├── settings.py        # ← SettingsStore.swift（字段/JSON 持久化）
│   ├── arg_builder.py     # ← ArgBuilder.swift（参数拼接）
│   ├── runner.py          # ← DownloadRunner.swift（进程/日志/进度/取消）
│   ├── kernel.py          # ← KernelModel.swift（内核定位/授权/下载）
│   ├── platform.py        # 跨平台文件对话框/打开目录/ffmpeg 探测
│   └── ui/                # 主窗口 + 各分区表单（等价 Views/*Section.swift）
├── tests/                 # 移植 Swift 断言 + 真实内核集成测试
├── tools/make_icon.py     # 生成图标（.png/.ico，需 pillow）
├── assets/                # 应用图标
├── yt-dlpGUI.spec         # PyInstaller 配置
├── requirements-dev.txt
└── pyproject.toml
```
