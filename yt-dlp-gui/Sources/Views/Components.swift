import SwiftUI
import AppKit

/// 带标题的分组卡片，用于把各类参数分区展示
struct SectionCard<Content: View>: View {
    let title: String
    @ViewBuilder var content: Content

    var body: some View {
        GroupBox {
            VStack(alignment: .leading, spacing: 10) {
                content
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.vertical, 4)
            .padding(.horizontal, 2)
        } label: {
            Text(title).font(.headline)
        }
    }
}

/// 左侧文字标签 + 右侧控件 的通用行
struct FieldRow<Content: View>: View {
    let label: String
    let help: String?
    @ViewBuilder var content: Content

    init(_ label: String, help: String? = nil, @ViewBuilder content: () -> Content) {
        self.label = label
        self.help = help
        self.content = content()
    }

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            VStack(alignment: .leading, spacing: 2) {
                Text(label).font(.callout)
                if let help {
                    Text(help)
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                        .fixedSize(horizontal: false, vertical: true)
                }
            }
            .frame(width: 160, alignment: .leading)
            .padding(.top, 4)
            content
            Spacer(minLength: 0)
        }
    }
}

/// 路径选择面板（文件或目录）
func choosePathPanel(title: String, canChooseDirectories: Bool) -> String? {
    let panel = NSOpenPanel()
    panel.title = title
    panel.prompt = "选择"
    panel.canChooseFiles = true
    panel.canChooseDirectories = canChooseDirectories
    panel.allowsMultipleSelection = false
    panel.directoryURL = URL(fileURLWithPath: NSHomeDirectory())
    if panel.runModal() == .OK, let url = panel.url {
        return url.path
    }
    return nil
}

/// 写入剪贴板
func copyToPasteboard(_ text: String) {
    let pb = NSPasteboard.general
    pb.clearContents()
    pb.setString(text, forType: .string)
}
