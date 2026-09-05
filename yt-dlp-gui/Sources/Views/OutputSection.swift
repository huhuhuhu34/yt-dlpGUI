import SwiftUI
import AppKit

struct OutputSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "输出设置") {
            FieldRow("保存到目录", help: "留空则使用用户主目录；目录不存在时 yt-dlp 会自动创建") {
                HStack(spacing: 6) {
                    TextField("~/Movies 等", text: $store.outputDir)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 300)
                    Button("浏览…") { chooseOutputDir() }
                    Button("恢复默认") { store.outputDir = "" }
                }
                Text("实际路径：\(store.resolvedOutputDir)")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            FieldRow("文件名模板", help: "-o 输出模板，yt-dlp 支持 %(title)s 等字段") {
                Picker("", selection: $store.outputTemplateIndex) {
                    ForEach(SettingsStore.outputTemplateNames.indices, id: \.self) { i in
                        Text(SettingsStore.outputTemplateNames[i]).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 220)
            }
            if store.outputTemplateIndex == SettingsStore.outputTemplateNames.count - 1 {
                FieldRow("自定义模板") {
                    TextField("%(title)s.%(ext)s", text: $store.customOutputTemplate)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 340)
                }
            }
            FieldRow("已有文件处理") {
                Picker("", selection: $store.overwriteMode) {
                    ForEach(SettingsStore.overwriteModes.indices, id: \.self) { i in
                        Text(SettingsStore.overwriteModes[i]).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .frame(width: 500)
            }

            Divider().padding(.vertical, 2)

            Toggle("下载标记：文件名加批次前缀（001、002…）", isOn: $store.markEnabled)
            if store.markEnabled {
                FieldRow("下一个批次号", help: "每点一次「开始下载」自动 +1") {
                    Text(String(format: "%03d", store.nextMarkNumber))
                        .font(.system(size: 16, design: .monospaced))
                        .foregroundStyle(.tint)
                    Button("重置标记") { store.resetMark() }
                        .disabled(store.markCounter == 0)
                        .help("清零后下次下载重新从 001 开始")
                }
                Text("效果：文件名变成「001 - 视频标题.mp4」。同一次下载里，同一个网址产生的视频/图片共用同一前缀；按名称升序 = 下载先后顺序（倒着看用 Finder 降序）。")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
    }

    private func chooseOutputDir() {
        if let p = choosePathPanel(title: "选择输出目录", canChooseDirectories: true) {
            store.outputDir = p
        }
    }
}
