# yt-dlp 管理器（yt-dlpGUI）

macOS 原生图形界面，把 yt-dlp 在终端里的用法搬进窗口，并解决 Readme 里
"每个 yt-dlp_macos 都要在终端 `chmod +x`" 的授权痛点。

## 特性

- **自包含打包**：`yt-dlp_macos` 内核直接打进 App（`Contents/Resources`）。
  双击即自动选用并授权（`chmod +x` + 解除隔离标记），App 可以随意移动/拷贝，
  无需再手动找内核文件。
- **内核管理**：内置内核之外，也支持「选择…」改用外部新版内核；切回内置只需一键。
- **完整 GUI 参数表单**：格式/画质、输出目录与文件名模板、音频提取、
  字幕、缩略图/元数据内嵌、转封装、播放列表、代理/Cookies/登录、SponsorBlock 等。
- **附加参数框**：未覆盖的任意 yt-dlp 参数逐行填写（安全解析，不经 shell）。
- **运行引擎**：直接 exec 内核，实时输出日志、进度百分比、可取消，
  完成后自动打开输出目录。

## 构建（无需 Xcode）

```bash
cd yt-dlp-gui
chmod +x build.sh
./build.sh                     # 产出 dist/yt-dlpGUI.app（自包含版，约 37MB）
./build.sh --smoke             # 额外运行参数拼接自检
open dist/yt-dlpGUI.app        # 启动
```

> 内核源默认取上一级目录的 `yt-dlp_macos`；
> 也可以指定：`YTDLP_KERNEL=/某个/yt-dlp_macos ./build.sh`

## 使用方法

1. 打开 App 后顶部自动显示 `✅ 内置内核就绪`（绿点 + 「内置」徽标），直接可用。
2. 在「链接」框粘贴网址（每行一个），按需设置格式/输出，点「开始下载」。
3. 想换更新版本的内核：下载新的 `yt-dlp_macos` → 点「选择…」定位它；
   或点「更新内核 (-U)」让内置内核自我更新。
4. 需要合并/转音频/内嵌元数据时请安装 ffmpeg：`brew install ffmpeg`。

## 说明

- 应用不做沙盒，仅本地使用；二进制为 ad-hoc 签名，双击即可运行。
- 下载文件默认保存到你设置的目录；目录留空则保存到用户主目录。
- 若要把 App 拷给别的 Mac：整个 `yt-dlpGUI.app` 直接复制即可（内含内核）；<br>
  从网络下载的 App 首次打开若被 Gatekeeper 拦截，右键 →「打开」一次即可。
