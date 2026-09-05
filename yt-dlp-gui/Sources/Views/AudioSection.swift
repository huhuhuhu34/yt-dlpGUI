import SwiftUI

struct AudioSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "音频提取（把视频转成纯音频）") {
            Toggle("提取音频（-x --extract-audio，需要 ffmpeg）", isOn: $store.extractAudio)
            if store.extractAudio {
                FieldRow("音频格式", help: "--audio-format") {
                    Picker("", selection: $store.audioFormatIndex) {
                        ForEach(SettingsStore.audioFormats.indices, id: \.self) { i in
                            Text(SettingsStore.audioFormats[i]).tag(i)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.menu)
                    .frame(width: 200)
                }
                FieldRow("音质", help: "0(最佳)～10(最差)，或直接写码率如 192K") {
                    TextField("留空使用默认 5", text: $store.audioQuality)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 160)
                }
            }
            Text("提示：若选择「合并」画质方案或提取音频，请确保已安装 ffmpeg（brew install ffmpeg）。应用会自动把 /opt/homebrew/bin 加入搜索路径。")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}
