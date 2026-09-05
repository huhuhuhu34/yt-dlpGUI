import SwiftUI

struct AdvancedSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "高级 / 附加参数") {
            Toggle("逐行输出日志（--newline，进度更清晰）", isOn: $store.newlineOutput)
            FieldRow("附加自定义参数", help: "界面未覆盖的任何 yt-dlp 参数都能填在这里，每行一条，支持引号。\n例：--no-mtime\n例：--exec 'echo 下载完成'") {
                TextEditor(text: $store.extraArgs)
                    .font(.system(size: 12, design: .monospaced))
                    .frame(minHeight: 52, maxHeight: 90)
                    .padding(4)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.secondary.opacity(0.35))
                    )
            }
        }
    }
}
