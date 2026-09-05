import SwiftUI

struct FormatSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "视频格式与画质") {
            FieldRow("清晰度方案", help: "选择后会自动生成 -f 格式表达式") {
                Picker("", selection: $store.formatPreset) {
                    ForEach(SettingsStore.formatPresets.indices, id: \.self) { i in
                        Text(SettingsStore.formatPresets[i].label).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 320)
            }
            if SettingsStore.formatPresets.indices.contains(store.formatPreset),
               SettingsStore.formatPresets[store.formatPreset].isCustom {
                FieldRow("自定义 -f", help: "例：bestvideo[height<=1080]+bestaudio/best") {
                    TextField("bestvideo*+bestaudio/best", text: $store.customFormat)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 340)
                }
            }
            FieldRow("实际生效", help: "将附加到命令中的 -f 值") {
                Text(store.effectiveFormat)
                    .font(.system(size: 12, design: .monospaced))
                    .textSelection(.enabled)
                    .foregroundStyle(.secondary)
            }
            FieldRow("合并容器", help: "需要合并视频+音频时使用的封装格式（需要 ffmpeg）") {
                Picker("", selection: $store.mergeOutputIndex) {
                    ForEach(SettingsStore.mergeFormats.indices, id: \.self) { i in
                        Text(SettingsStore.mergeFormats[i]).tag(i)
                    }
                }
                .labelsHidden()
                .pickerStyle(.menu)
                .frame(width: 220)
            }
        }
    }
}
