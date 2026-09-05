import SwiftUI
import AppKit

struct LinkSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "链接（每行一个，可粘贴多个网址）") {
            HStack(alignment: .top, spacing: 10) {
                NumberedTextView(text: $store.urlsText)
                    .frame(maxWidth: .infinity, minHeight: 72, maxHeight: 130)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.secondary.opacity(0.35))
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 6))
                VStack(alignment: .leading, spacing: 8) {
                    Button("抖音") {
                        if store.urlsText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                            store.urlsText = "https://www.douyin.com/video/"
                        } else {
                            store.urlsText += "\nhttps://www.douyin.com/video/"
                        }
                    }
                    .help("在列表末尾新增一行抖音链接前缀，不覆盖已有内容")
                    Button("导入 .txt…") { importURLs() }
                    Button("清空") { store.urlsText = "" }
                    Spacer()
                    Text("共 \(store.urlLines.count) 条链接")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(width: 100)
            }
            Toggle("下载出错时忽略并继续（-i --ignore-errors）", isOn: $store.ignoreErrors)
            Toggle("下载成功后自动打开输出文件夹", isOn: $store.openOutputFolderWhenDone)
        }
    }

    private func importURLs() {
        guard let path = choosePathPanel(title: "选择包含链接的文本文件", canChooseDirectories: false),
              let content = try? String(contentsOfFile: path, encoding: .utf8) else { return }
        if store.urlsText.isEmpty {
            store.urlsText = content
        } else {
            store.urlsText += "\n" + content
        }
    }
}
