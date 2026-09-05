import SwiftUI

struct SubtitleMetadataSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "字幕") {
            Toggle("下载普通字幕（--write-subs）", isOn: $store.writeSubs)
            Toggle("下载自动生成字幕（--write-auto-subs）", isOn: $store.writeAutoSubs)
            if store.writeSubs || store.writeAutoSubs {
                FieldRow("语言", help: "--sub-langs，如 zh-Hans,en 或 all（留空默认）") {
                    TextField("en,zh-Hans", text: $store.subLangs)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 220)
                }
                FieldRow("字幕格式", help: "--sub-format，如 srt、ass/srt/best") {
                    TextField("留空默认", text: $store.subFormat)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 220)
                }
                Toggle("内嵌字幕到视频（--embed-subs）", isOn: $store.embedSubs)
            }
        }
    }
}

struct MetadataSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "缩略图 / 元数据") {
            Toggle("保存封面缩略图（--write-thumbnail）", isOn: $store.writeThumbnail)
            Toggle("把元数据内嵌进文件（--embed-metadata，需要 ffmpeg）", isOn: $store.embedMetadata)
            Toggle("把封面内嵌进文件（--embed-thumbnail）", isOn: $store.embedThumbnail)
            Toggle("把章节信息内嵌进文件（--embed-chapters）", isOn: $store.embedChapters)
        }
    }
}
