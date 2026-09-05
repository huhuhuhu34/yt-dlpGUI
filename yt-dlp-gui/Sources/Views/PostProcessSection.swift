import SwiftUI
import AppKit

struct PostProcessSection: View {
    @EnvironmentObject var store: SettingsStore
    @EnvironmentObject var runner: DownloadRunner

    var body: some View {
        SectionCard(title: "后期处理（转封装 / ffmpeg / 章节 / SponsorBlock）") {
            FieldRow("转封装格式", help: "--remux-video；若目标容器不支持编码会失败") {
                Picker("", selection: $store.remuxIndex) {
                    ForEach(SettingsStore.remuxFormats.indices, id: \.self) { i in
                        Text(SettingsStore.remuxFormats[i]).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 220)
            }
            FieldRow("ffmpeg 位置", help: "默认自动搜索；如装在非标准位置可手动指定") {
                HStack(spacing: 6) {
                    TextField("/opt/homebrew/bin/ffmpeg", text: $store.ffmpegLocation)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 300)
                    Button("浏览…") { chooseFFmpeg() }
                    Button("清空") { store.ffmpegLocation = "" }
                }
            }

            Divider().padding(.vertical, 2)

            HStack(spacing: 8) {
                Button {
                    convertFileToWav()
                } label: {
                    Label("选择文件并转 WAV", systemImage: "waveform")
                }
                .disabled(runner.isRunning)
                .help("ffmpeg -i 输入文件 -ar 16000 -ac 1 -c:a pcm_s16le 同名.wav")
                Text("16kHz / 单声道 / PCM16；输出在输入文件同目录、同名 .wav")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Toggle("按章节拆分视频（--split-chapters）", isOn: $store.splitChapters)

            Divider().padding(.vertical, 2)

            FieldRow("SponsorBlock 标记类别", help: "赞助/intro/outro/selfpromo/preview/filler/interaction/…；例 sponsor,intro") {
                TextField("留空关闭", text: $store.sponsorMark)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 280)
            }
            FieldRow("SponsorBlock 移除类别", help: "移除指定片段；例 sponsor,intro,outro（需要 ffmpeg）") {
                TextField("留空关闭", text: $store.sponsorRemove)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 280)
            }
        }
    }

    private func chooseFFmpeg() {
        if let p = choosePathPanel(title: "选择 ffmpeg 可执行文件", canChooseDirectories: false) {
            store.ffmpegLocation = p
        }
    }

    // MARK: 音频转换（WAV）

    private func convertFileToWav() {
        guard !runner.isRunning else { return }
        guard let ffmpeg = resolveFFmpeg() else {
            runner.statusText = "未找到 ffmpeg，请安装（brew install ffmpeg）或在「ffmpeg 位置」里指定。"
            return
        }
        guard let inputPath = choosePathPanel(title: "选择要转换成音频的文件", canChooseDirectories: false) else {
            return
        }
        let inputURL = URL(fileURLWithPath: inputPath)
        guard inputURL.pathExtension.lowercased() != "wav" else {
            runner.statusText = "输入文件已是 WAV，无需转换。"
            return
        }

        let outputURL = inputURL
            .deletingLastPathComponent()
            .appendingPathComponent(inputURL.deletingPathExtension().lastPathComponent + ".wav")

        var args: [String] = []
        if FileManager.default.fileExists(atPath: outputURL.path) {
            guard confirmOverwrite(outputURL.path) else { return }
            args.append("-y")
        }
        args += [
            "-i", inputURL.path,
            "-ar", "16000",
            "-ac", "1",
            "-c:a", "pcm_s16le",
            outputURL.path
        ]

        runner.statusText = "音频转换中…"
        runner.run(
            executable: ffmpeg,
            arguments: args,
            directory: inputURL.deletingLastPathComponent().path,
            taskTitle: "音频转换 WAV"
        )
    }

    /// 探测 ffmpeg：优先用户指定，其次常见路径
    private func resolveFFmpeg() -> String? {
        let fm = FileManager.default
        var candidates: [String] = []
        let override = store.ffmpegLocation.trimmingCharacters(in: .whitespaces)
        if !override.isEmpty {
            let expanded = (override as NSString).expandingTildeInPath
            var isDir: ObjCBool = false
            if fm.fileExists(atPath: expanded, isDirectory: &isDir), isDir.boolValue {
                candidates.append(expanded + "/ffmpeg")
            } else {
                candidates.append(expanded)
            }
        }
        candidates += [
            "/opt/homebrew/bin/ffmpeg",
            "/usr/local/bin/ffmpeg",
            "/usr/bin/ffmpeg"
        ]
        for c in candidates where fm.isExecutableFile(atPath: c) {
            return c
        }
        return nil
    }

    private func confirmOverwrite(_ path: String) -> Bool {
        let alert = NSAlert()
        alert.messageText = "文件已存在"
        alert.informativeText = "「\(URL(fileURLWithPath: path).lastPathComponent)」已存在，是否覆盖？"
        alert.alertStyle = .warning
        alert.addButton(withTitle: "覆盖")
        alert.addButton(withTitle: "取消")
        return alert.runModal() == .alertFirstButtonReturn
    }
}
