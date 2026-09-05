import Foundation

/// 把 GUI 表单翻译成 yt-dlp 参数数组（不经过 shell，杜绝转义/注入问题）
enum ArgBuilder {

    /// 输出模板（启用“下载标记”时在文件名的最后一段前注入批次前缀）
    static func outputTemplate(withMark s: SettingsStore) -> String {
        let base = s.effectiveOutputTemplate
        guard s.markEnabled else { return base }
        let mark = String(format: "%03d", s.markCounter + 1)
        let parts = base.split(separator: "/", omittingEmptySubsequences: false).map(String.init)
        if let last = parts.last, !last.isEmpty {
            var newParts = parts
            newParts[newParts.count - 1] = "\(mark) - \(last)"
            return newParts.joined(separator: "/")
        }
        return "\(mark) - \(base)"
    }

    /// 从抖音分享链接中提取 modal_id，换算成标准视频链接：
    /// https://www.douyin.com/user/xxx?...&modal_id=7680222044810744293
    ///   → https://www.douyin.com/video/7680222044810744293
    /// 非 douyin.com 或没有 modal_id 的链接原样返回。
    static func douyinVideoURL(from urlString: String) -> String {
        let raw = urlString.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let comps = URLComponents(string: raw),
              let host = comps.host?.lowercased(),
              host.contains("douyin.com"),
              let items = comps.queryItems,
              let modalID = items.first(where: { $0.name.lowercased() == "modal_id" })?.value,
              !modalID.isEmpty else {
            return urlString
        }
        return "https://www.douyin.com/video/" + modalID
    }

    /// 把一行字符串按空白拆成 token，支持单双引号
    static func tokenizeLine(_ line: String) -> [String] {
        var tokens: [String] = []
        var current = ""
        var quote: Character?
        var started = false
        for ch in line {
            if let q = quote {
                if ch == q {
                    quote = nil
                } else {
                    current.append(ch)
                }
            } else if ch == "'" || ch == "\"" {
                quote = ch
                started = true
            } else if ch.isWhitespace {
                if started {
                    tokens.append(current)
                    current = ""
                    started = false
                }
            } else {
                current.append(ch)
                started = true
            }
        }
        if started { tokens.append(current) }
        return tokens
    }

    /// 组装正式参数（不含末尾的 URL）
    static func buildArgs(_ s: SettingsStore) -> [String] {
        var a: [String] = []
        func add(_ arr: [String]) { a.append(contentsOf: arr) }
        func trimmed(_ x: String) -> String {
            x.trimmingCharacters(in: .whitespaces)
        }

        // ---- 通用 ----
        if s.ignoreErrors { a.append("-i") }
        if s.newlineOutput { a.append("--newline") }

        // ---- 网络 / 登录 ----
        if s.useProxy {
            let p = trimmed(s.proxy)
            add(["--proxy", p])   // 空字符串 = 强制直连
        }
        switch s.cookieMode {
        case 1:
            if !trimmed(s.cookieFile).isEmpty {
                add(["--cookies", trimmed(s.cookieFile)])
            }
        case 2:
            add(["--cookies-from-browser", trimmed(s.browserCookieSource)])
        default:
            break
        }
        if !trimmed(s.username).isEmpty { add(["--username", trimmed(s.username)]) }
        if !s.password.isEmpty { add(["--password", s.password]) }
        if !trimmed(s.twofactor).isEmpty { add(["--twofactor", trimmed(s.twofactor)]) }
        if s.useNetrc { a.append("--netrc") }
        if !trimmed(s.limitRate).isEmpty { add(["--limit-rate", trimmed(s.limitRate)]) }
        if !trimmed(s.retries).isEmpty { add(["--retries", trimmed(s.retries)]) }
        if !trimmed(s.concurrentFragments).isEmpty {
            add(["--concurrent-fragments", trimmed(s.concurrentFragments)])
        }

        // ---- 格式 ----
        add(["-f", s.effectiveFormat])
        if let m = s.effectiveMergeFormat { add(["--merge-output-format", m]) }

        // ---- 输出 ----
        if !trimmed(s.outputDir).isEmpty { add(["-P", s.resolvedOutputDir]) }
        add(["-o", outputTemplate(withMark: s)])
        if s.overwriteMode == 1 { a.append("-w") }
        if s.overwriteMode == 2 { a.append("--force-overwrites") }

        // ---- 音频 ----
        if s.extractAudio {
            a.append("-x")
            let fmt = s.effectiveAudioFormat
            if fmt != "默认 (best)" && fmt != "best" {
                add(["--audio-format", fmt])
            }
            if !trimmed(s.audioQuality).isEmpty {
                add(["--audio-quality", trimmed(s.audioQuality)])
            }
        }

        // ---- 字幕 ----
        if s.writeSubs { a.append("--write-subs") }
        if s.writeAutoSubs { a.append("--write-auto-subs") }
        if !trimmed(s.subLangs).isEmpty { add(["--sub-langs", trimmed(s.subLangs)]) }
        if !trimmed(s.subFormat).isEmpty { add(["--sub-format", trimmed(s.subFormat)]) }

        // ---- 元数据 / 缩略图 ----
        if s.writeThumbnail { a.append("--write-thumbnail") }
        if s.embedMetadata { a.append("--embed-metadata") }
        if s.embedThumbnail { a.append("--embed-thumbnail") }
        if s.embedChapters { a.append("--embed-chapters") }
        if s.embedSubs { a.append("--embed-subs") }

        // ---- 后期处理 ----
        if let r = s.effectiveRemux { add(["--remux-video", r]) }
        if !trimmed(s.ffmpegLocation).isEmpty { add(["--ffmpeg-location", trimmed(s.ffmpegLocation)]) }
        if s.splitChapters { a.append("--split-chapters") }
        if !trimmed(s.sponsorMark).isEmpty { add(["--sponsorblock-mark", trimmed(s.sponsorMark)]) }
        if !trimmed(s.sponsorRemove).isEmpty { add(["--sponsorblock-remove", trimmed(s.sponsorRemove)]) }

        // ---- 播放列表 ----
        if s.playlistMode == 1 { a.append("--no-playlist") }
        if s.playlistMode == 2 { a.append("--yes-playlist") }
        if !trimmed(s.playlistItems).isEmpty { add(["--playlist-items", trimmed(s.playlistItems)]) }
        if !trimmed(s.downloadArchive).isEmpty {
            add(["--download-archive", (trimmed(s.downloadArchive) as NSString).expandingTildeInPath])
        }

        // ---- 附加自定义参数（每行解析） ----
        for line in s.extraArgs.split(whereSeparator: \.isNewline) {
            let tokens = tokenizeLine(String(line))
            a.append(contentsOf: tokens)
        }

        return a
    }

    /// 供预览/复制用的 shell 风格字符串
    static func commandPreview(exe: String, args: [String]) -> String {
        ([exe] + args).map(shellQuote).joined(separator: " ")
    }

    static func shellQuote(_ s: String) -> String {
        if s.isEmpty { return "''" }
        let special = CharacterSet.whitespacesAndNewlines
            .union(CharacterSet(charactersIn: "\\'\"&|;<>()$`!*?[]{}#~"))
        if s.rangeOfCharacter(from: special) == nil {
            return s
        }
        return "'" + s.replacingOccurrences(of: "'", with: "'\\''") + "'"
    }
}
