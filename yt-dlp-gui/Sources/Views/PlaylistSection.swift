import SwiftUI
import AppKit

struct PlaylistSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "播放列表") {
            FieldRow("下载范围", help: "适用于 YouTube/B站 等含播放列表的链接") {
                Picker("", selection: $store.playlistMode) {
                    ForEach(SettingsStore.playlistModes.indices, id: \.self) { i in
                        Text(SettingsStore.playlistModes[i]).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 320)
            }
            FieldRow("指定条目", help: "--playlist-items，例：1-5,8,10-") {
                TextField("留空下载全部", text: $store.playlistItems)
                    .textFieldStyle(.roundedBorder)
                    .frame(width: 220)
            }
            FieldRow("下载记录", help: "--download-archive，只下载新增，避免重复（断点记忆）") {
                HStack(spacing: 6) {
                    TextField("记录文件路径，留空不使用", text: $store.downloadArchive)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 300)
                    Button("浏览…") { chooseArchive() }
                    Button("清空") { store.downloadArchive = "" }
                }
            }
        }
    }

    private func chooseArchive() {
        if let p = choosePathPanel(title: "选择存档文件（可新建）", canChooseDirectories: false) {
            store.downloadArchive = p
        }
    }
}
