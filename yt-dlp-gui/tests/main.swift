import Foundation

var failures = 0
func check(_ cond: Bool, _ name: String) {
    print((cond ? "PASS" : "FAIL") + "  " + name)
    if !cond { failures += 1 }
}

// 1. 多行 URL
let s = SettingsStore()
s.markEnabled = false   // 防止读取到历史持久化的标记配置影响断言
s.urlsText = "https://example.com/watch?v=abc123\nhttps://a/b"
var args = ArgBuilder.buildArgs(s)
args.append(contentsOf: s.urlLines)
check(args.contains("https://example.com/watch?v=abc123"), "多行 URL 按行拆分并保留")
check(args.contains("https://a/b"), "第二行 URL 保留")

// 1b. 抖音 modal_id 提取
let douyinSample = "https://www.douyin.com/user/MS4wLjABAAAA0l_9-4Qdks_mRt4AmCVJCiydf-TDzQlQ0CkELB66I-8?from_tab_name=main&modal_id=7680222044810744293"
check(ArgBuilder.douyinVideoURL(from: douyinSample) == "https://www.douyin.com/video/7680222044810744293", "modal_id 提取为标准视频链接")
let douyinOrder2 = "https://www.douyin.com/user/abc?modal_id=123456789&from=main"
check(ArgBuilder.douyinVideoURL(from: douyinOrder2) == "https://www.douyin.com/video/123456789", "modal_id 参数乱序也能提取")
check(ArgBuilder.douyinVideoURL(from: "https://www.douyin.com/video/123456789") == "https://www.douyin.com/video/123456789", "已是视频链接保持不变")
check(ArgBuilder.douyinVideoURL(from: "https://example.com/x?modal_id=1") == "https://example.com/x?modal_id=1", "非抖音链接保持不变")
check(ArgBuilder.douyinVideoURL(from: "https://www.douyin.com/user/xyz") == "https://www.douyin.com/user/xyz", "无 modal_id 保持不变")

// 2. 默认格式 preset=1
if let i = args.firstIndex(of: "-f") {
    check(i + 1 < args.count && args[i + 1] == "bestvideo*+bestaudio/best", "默认 -f = 合并最佳视频+音频")
} else {
    check(false, "-f 应出现")
}

// 3. 音频提取
s.extractAudio = true
s.audioFormatIndex = 1
args = ArgBuilder.buildArgs(s)
check(args.contains("-x"), "-x 应出现")
if let i = args.firstIndex(of: "--audio-format") {
    check(i + 1 < args.count && args[i + 1] == "mp3", "--audio-format mp3")
} else {
    check(false, "--audio-format 应出现")
}

// 4. 代理
s.extractAudio = false
s.useProxy = true
s.proxy = "http://127.0.0.1:1080"
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "--proxy") {
    check(i + 1 < args.count && args[i + 1] == "http://127.0.0.1:1080", "--proxy 值正确")
} else {
    check(false, "--proxy 应出现")
}

// 5. 从浏览器读 cookies
s.useProxy = false
s.cookieMode = 2
s.browserCookieSource = "safari"
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "--cookies-from-browser") {
    check(i + 1 < args.count && args[i + 1] == "safari", "--cookies-from-browser 值正确")
} else {
    check(false, "--cookies-from-browser 应出现")
}

// 6. 附加参数解析（含引号）
s.extraArgs = "--no-mtime\n--exec \"echo done\""
args = ArgBuilder.buildArgs(s)
check(args.contains("--no-mtime"), "附加参数整行参数")
if let i = args.firstIndex(of: "--exec") {
    check(i + 1 < args.count && args[i + 1] == "echo done", "带引号的参数保留内部空格")
} else {
    check(false, "--exec 应出现")
}

// 7. 自定义输出模板
s.extraArgs = ""
s.outputTemplateIndex = 4
s.customOutputTemplate = "VID %(id)s.%(ext)s"
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "-o") {
    check(i + 1 < args.count && args[i + 1] == "VID %(id)s.%(ext)s", "自定义 -o 模板")
} else {
    check(false, "-o 应出现")
}

// 7b. 下载标记：文件名前缀
s.outputTemplateIndex = 0
s.markEnabled = true
s.markCounter = 0
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "-o") {
    check(i + 1 < args.count && args[i + 1] == "001 - %(title)s.%(ext)s", "标记注入 001 前缀")
} else {
    check(false, "-o 应出现")
}
s.markCounter = 3
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "-o") {
    check(i + 1 < args.count && args[i + 1] == "004 - %(title)s.%(ext)s", "批次递增到 004")
} else {
    check(false, "-o 应出现")
}
s.resetMark()
check(s.nextMarkNumber == 1, "重置后下一个批次号为 001")
// 带目录模板时，前缀只注入文件名段（不改变文件夹名）
s.outputTemplateIndex = 3
s.markCounter = 2
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "-o") {
    check(args[i + 1] == "%(playlist_title)s/003 - %(playlist_index)02d %(title)s.%(ext)s", "带目录模板时前缀只加在文件名段")
} else {
    check(false, "-o 应出现")
}
s.markEnabled = false

// 8. 输出目录展开 ~
s.outputTemplateIndex = 0
s.outputDir = "~/yt-dlp Test"
args = ArgBuilder.buildArgs(s)
if let i = args.firstIndex(of: "-P") {
    let expanded = (args[i + 1] as NSString).expandingTildeInPath
    check(expanded.hasSuffix("/yt-dlp Test"), "-P 输出目录展开含空格")
} else {
    check(false, "-P 应出现")
}

// 9. 播放列表 / 覆盖策略
s.outputDir = ""
s.playlistMode = 1
args = ArgBuilder.buildArgs(s)
check(args.contains("--no-playlist"), "--no-playlist")
s.overwriteMode = 1
args = ArgBuilder.buildArgs(s)
check(args.contains("-w"), "不覆盖 -w")
s.overwriteMode = 2
args = ArgBuilder.buildArgs(s)
check(args.contains("--force-overwrites"), "强制覆盖 --force-overwrites")

// 10. shell 引号
check(ArgBuilder.shellQuote("hello") == "hello", "无特殊字符不加引号")
check(ArgBuilder.shellQuote("a b") == "'a b'", "含空格加单引号")
check(ArgBuilder.shellQuote("it's") == "'it'\\''s'", "含单引号正确转义")

print(failures == 0 ? "\n✅ 全部通过" : "\n❌ 有 \(failures) 项失败")
exit(failures == 0 ? 0 : 1)
