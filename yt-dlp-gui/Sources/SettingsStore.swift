import Foundation
import Combine

struct FormatPreset {
    let label: String
    let value: String
    let isCustom: Bool
}

/// 全部表单参数与持久化
final class SettingsStore: ObservableObject {
    // ---- 链接 ----
    @Published var urlsText = ""
    @Published var ignoreErrors = false
    @Published var openOutputFolderWhenDone = true

    // ---- 网络 / 登录 ----
    @Published var useProxy = false
    @Published var proxy = ""
    @Published var cookieMode = 0            // 0 不使用  1 文件  2 浏览器
    @Published var cookieFile = ""
    @Published var browserCookieSource = "safari"
    @Published var username = ""
    @Published var password = ""
    @Published var twofactor = ""
    @Published var useNetrc = false
    @Published var limitRate = ""
    @Published var retries = ""
    @Published var concurrentFragments = ""

    // ---- 视频格式 ----
    @Published var formatPreset = 1          // 默认：最佳视频+最佳音频（合并）
    @Published var customFormat = ""

    // ---- 输出 ----
    @Published var outputDir = ""
    @Published var outputTemplateIndex = 0
    @Published var customOutputTemplate = ""
    @Published var overwriteMode = 0         // 0 续传  1 不覆盖(-w)  2 强制覆盖

    // ---- 音频 ----
    @Published var extractAudio = false
    @Published var audioFormatIndex = 0      // 0 默认(best)
    @Published var audioQuality = ""

    // ---- 字幕 ----
    @Published var writeSubs = false
    @Published var writeAutoSubs = false
    @Published var subLangs = ""
    @Published var subFormat = ""

    // ---- 元数据 / 缩略图 ----
    @Published var writeThumbnail = false
    @Published var embedMetadata = false
    @Published var embedThumbnail = false
    @Published var embedChapters = false
    @Published var embedSubs = false

    // ---- 后期处理 ----
    @Published var remuxIndex = 0            // 0 不转封装
    @Published var ffmpegLocation = ""
    @Published var splitChapters = false
    @Published var sponsorMark = ""
    @Published var sponsorRemove = ""

    // ---- 播放列表 ----
    @Published var playlistMode = 0          // 0 自动  1 仅当前视频  2 强制整个列表
    @Published var playlistItems = ""
    @Published var downloadArchive = ""

    // ---- 行为 / 高级 ----
    @Published var newlineOutput = true
    @Published var extraArgs = ""

    // ====== 静态选项数据 ======
    static let formatPresets: [FormatPreset] = [
        FormatPreset(label: "最佳质量（单文件 best）", value: "best", isCustom: false),
        FormatPreset(label: "最佳视频+最佳音频（合并，推荐）", value: "bestvideo*+bestaudio/best", isCustom: false),
        FormatPreset(label: "≤ 1080p（合并）", value: "bestvideo[height<=1080]+bestaudio/best[height<=1080]", isCustom: false),
        FormatPreset(label: "≤ 720p（合并）", value: "bestvideo[height<=720]+bestaudio/best[height<=720]", isCustom: false),
        FormatPreset(label: "≤ 480p（合并）", value: "bestvideo[height<=480]+bestaudio/best[height<=480]", isCustom: false),
        FormatPreset(label: "仅音频（ba/best）", value: "ba/best", isCustom: false),
        FormatPreset(label: "自定义格式表达式…", value: "", isCustom: true)
    ]
    static let audioFormats = ["默认 (best)", "mp3", "m4a", "aac", "flac", "opus", "vorbis", "wav", "alac"]
    static let mergeFormats = ["不指定容器", "mp4", "mkv", "webm"]
    static let remuxFormats = ["不转封装", "mp4", "mkv", "webm", "mov"]
    static let outputTemplateNames = ["标题", "标题 + ID", "上传日期 + 标题", "按播放列表分目录", "自定义…"]
    static let outputTemplateValues = [
        "%(title)s.%(ext)s",
        "%(title)s [%(id)s].%(ext)s",
        "%(upload_date>%Y-%m-%d)s %(title)s.%(ext)s",
        "%(playlist_title)s/%(playlist_index)02d %(title)s.%(ext)s",
        ""
    ]
    static let browserList = ["safari", "chrome", "chromium", "edge", "firefox", "brave", "opera", "vivaldi", "whale"]
    static let overwriteModes = ["续传（默认 -c）", "不覆盖已有文件 (-w)", "强制覆盖 (--force-overwrites)"]
    static let playlistModes = ["自动判断", "仅下载当前视频 (--no-playlist)", "强制下载整个列表 (--yes-playlist)"]

    // ====== 供参数拼接使用的解析结果 ======
    var urlLines: [String] {
        urlsText.split(whereSeparator: \.isNewline)
            .map { $0.trimmingCharacters(in: .whitespaces) }
            .filter { !$0.isEmpty }
            .map { ArgBuilder.douyinVideoURL(from: $0) }
    }

    var effectiveFormat: String {
        let i = formatPreset
        if i >= 0, i < SettingsStore.formatPresets.count {
            let p = SettingsStore.formatPresets[i]
            if p.isCustom {
                let c = customFormat.trimmingCharacters(in: .whitespaces)
                return c.isEmpty ? "bestvideo*+bestaudio/best" : c
            }
            return p.value
        }
        return "bestvideo*+bestaudio/best"
    }

    var effectiveAudioFormat: String {
        let i = audioFormatIndex
        if i >= 0, i < SettingsStore.audioFormats.count {
            return SettingsStore.audioFormats[i]
        }
        return "best"
    }

    var effectiveMergeFormat: String? {
        let i = mergeOutputIndex
        if i > 0, i < SettingsStore.mergeFormats.count { return SettingsStore.mergeFormats[i] }
        return nil
    }

    var effectiveRemux: String? {
        let i = remuxIndex
        if i > 0, i < SettingsStore.remuxFormats.count { return SettingsStore.remuxFormats[i] }
        return nil
    }

    var effectiveOutputTemplate: String {
        let i = outputTemplateIndex
        if i == SettingsStore.outputTemplateNames.count - 1 {
            let c = customOutputTemplate.trimmingCharacters(in: .whitespaces)
            return c.isEmpty ? "%(title)s.%(ext)s" : c
        }
        if i >= 0, i < SettingsStore.outputTemplateValues.count { return SettingsStore.outputTemplateValues[i] }
        return "%(title)s.%(ext)s"
    }

    /// 输出目录（空则退回用户主目录），展开 ~
    var resolvedOutputDir: String {
        let t = outputDir.trimmingCharacters(in: .whitespaces)
        if t.isEmpty { return NSHomeDirectory() }
        return (t as NSString).expandingTildeInPath
    }

    // 合并容器由 UI 单独维护；此处仅为占位以保持字段集中（由 mergeOutputIndex 映射）
    @Published var mergeOutputIndex = 0

    // ---- 下载标记（文件名批次前缀） ----
    @Published var markEnabled = false
    @Published var markCounter = 0       // 已使用的最大批次号

    var nextMarkNumber: Int { markCounter + 1 }

    /// 「开始下载」真正运行时消费一个批次号
    @discardableResult
    func consumeMarkNumber() -> Int {
        markCounter += 1
        return markCounter
    }

    /// 重置标记：清零，下次从 001 开始
    func resetMark() {
        markCounter = 0
    }

    private var saveCancellable: AnyCancellable?
    private static let prefix = "ytdlpgui."
    private let ud = UserDefaults.standard

    init() {
        load()
        saveCancellable = objectWillChange
            .debounce(for: .seconds(0.8), scheduler: RunLoop.main)
            .sink { [weak self] _ in self?.save() }
    }

    private func key(_ k: String) -> String { SettingsStore.prefix + k }

    // MARK: 读取

    private func load() {
        func s(_ k: String, _ def: String) -> String {
            ud.string(forKey: key(k)) ?? def
        }
        func b(_ k: String, _ def: Bool) -> Bool {
            ud.object(forKey: key(k)) as? Bool ?? def
        }
        func i(_ k: String, _ def: Int) -> Int {
            ud.object(forKey: key(k)) as? Int ?? def
        }

        urlsText = s("urlsText", "")
        ignoreErrors = b("ignoreErrors", false)
        openOutputFolderWhenDone = b("openOutputFolderWhenDone", true)
        useProxy = b("useProxy", false)
        proxy = s("proxy", "")
        cookieMode = i("cookieMode", 0)
        cookieFile = s("cookieFile", "")
        browserCookieSource = s("browserCookieSource", "safari")
        username = s("username", "")
        password = s("password", "")
        twofactor = s("twofactor", "")
        useNetrc = b("useNetrc", false)
        limitRate = s("limitRate", "")
        retries = s("retries", "")
        concurrentFragments = s("concurrentFragments", "")
        formatPreset = i("formatPreset", 1)
        customFormat = s("customFormat", "")
        outputDir = s("outputDir", "")
        outputTemplateIndex = i("outputTemplateIndex", 0)
        customOutputTemplate = s("customOutputTemplate", "")
        overwriteMode = i("overwriteMode", 0)
        extractAudio = b("extractAudio", false)
        audioFormatIndex = i("audioFormatIndex", 0)
        audioQuality = s("audioQuality", "")
        writeSubs = b("writeSubs", false)
        writeAutoSubs = b("writeAutoSubs", false)
        subLangs = s("subLangs", "")
        subFormat = s("subFormat", "")
        writeThumbnail = b("writeThumbnail", false)
        embedMetadata = b("embedMetadata", false)
        embedThumbnail = b("embedThumbnail", false)
        embedChapters = b("embedChapters", false)
        embedSubs = b("embedSubs", false)
        remuxIndex = i("remuxIndex", 0)
        ffmpegLocation = s("ffmpegLocation", "")
        splitChapters = b("splitChapters", false)
        sponsorMark = s("sponsorMark", "")
        sponsorRemove = s("sponsorRemove", "")
        playlistMode = i("playlistMode", 0)
        playlistItems = s("playlistItems", "")
        downloadArchive = s("downloadArchive", "")
        newlineOutput = b("newlineOutput", true)
        extraArgs = s("extraArgs", "")
        mergeOutputIndex = i("mergeOutputIndex", 0)
        markEnabled = b("markEnabled", false)
        markCounter = i("markCounter", 0)
    }

    // MARK: 保存

    private func save() {
        ud.set(urlsText, forKey: key("urlsText"))
        ud.set(ignoreErrors, forKey: key("ignoreErrors"))
        ud.set(openOutputFolderWhenDone, forKey: key("openOutputFolderWhenDone"))
        ud.set(useProxy, forKey: key("useProxy"))
        ud.set(proxy, forKey: key("proxy"))
        ud.set(cookieMode, forKey: key("cookieMode"))
        ud.set(cookieFile, forKey: key("cookieFile"))
        ud.set(browserCookieSource, forKey: key("browserCookieSource"))
        ud.set(username, forKey: key("username"))
        ud.set(password, forKey: key("password"))
        ud.set(twofactor, forKey: key("twofactor"))
        ud.set(useNetrc, forKey: key("useNetrc"))
        ud.set(limitRate, forKey: key("limitRate"))
        ud.set(retries, forKey: key("retries"))
        ud.set(concurrentFragments, forKey: key("concurrentFragments"))
        ud.set(formatPreset, forKey: key("formatPreset"))
        ud.set(customFormat, forKey: key("customFormat"))
        ud.set(outputDir, forKey: key("outputDir"))
        ud.set(outputTemplateIndex, forKey: key("outputTemplateIndex"))
        ud.set(customOutputTemplate, forKey: key("customOutputTemplate"))
        ud.set(overwriteMode, forKey: key("overwriteMode"))
        ud.set(extractAudio, forKey: key("extractAudio"))
        ud.set(audioFormatIndex, forKey: key("audioFormatIndex"))
        ud.set(audioQuality, forKey: key("audioQuality"))
        ud.set(writeSubs, forKey: key("writeSubs"))
        ud.set(writeAutoSubs, forKey: key("writeAutoSubs"))
        ud.set(subLangs, forKey: key("subLangs"))
        ud.set(subFormat, forKey: key("subFormat"))
        ud.set(writeThumbnail, forKey: key("writeThumbnail"))
        ud.set(embedMetadata, forKey: key("embedMetadata"))
        ud.set(embedThumbnail, forKey: key("embedThumbnail"))
        ud.set(embedChapters, forKey: key("embedChapters"))
        ud.set(embedSubs, forKey: key("embedSubs"))
        ud.set(remuxIndex, forKey: key("remuxIndex"))
        ud.set(ffmpegLocation, forKey: key("ffmpegLocation"))
        ud.set(splitChapters, forKey: key("splitChapters"))
        ud.set(sponsorMark, forKey: key("sponsorMark"))
        ud.set(sponsorRemove, forKey: key("sponsorRemove"))
        ud.set(playlistMode, forKey: key("playlistMode"))
        ud.set(playlistItems, forKey: key("playlistItems"))
        ud.set(downloadArchive, forKey: key("downloadArchive"))
        ud.set(newlineOutput, forKey: key("newlineOutput"))
        ud.set(extraArgs, forKey: key("extraArgs"))
        ud.set(mergeOutputIndex, forKey: key("mergeOutputIndex"))
        ud.set(markEnabled, forKey: key("markEnabled"))
        ud.set(markCounter, forKey: key("markCounter"))
    }
}
