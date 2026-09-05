import SwiftUI
import AppKit

struct ContentView: View {
    @EnvironmentObject var store: SettingsStore
    @EnvironmentObject var kernel: KernelModel
    @EnvironmentObject var runner: DownloadRunner

    var body: some View {
        VSplitView {
            ScrollView {
                VStack(alignment: .leading, spacing: 14) {
                    kernelBar
                    LinkSection()
                    NetworkAuthSection()
                    FormatSection()
                    OutputSection()
                    AudioSection()
                    SubtitleMetadataSection()
                    MetadataSection()
                    PostProcessSection()
                    PlaylistSection()
                    AdvancedSection()
                }
                .padding(14)
            }
            .frame(minHeight: 430)

            bottomPane
                .frame(minHeight: 210, maxHeight: 400)
        }
        .onAppear {
            runner.onFinished = { code in
                if code == 0, store.openOutputFolderWhenDone {
                    openOutputFolder()
                }
            }
        }
        .onChange(of: kernel.kernelPath) { _ in
            kernel.refresh()
        }
    }

    // MARK: 内核管理栏

    private var kernelBar: some View {
        SectionCard(title: "内核 · yt-dlp 程序（自包含版：内置内核随 App 打包）") {
            HStack(spacing: 8) {
                TextField("未选择内核程序，请点右侧按钮", text: $kernel.kernelPath)
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12, design: .monospaced))
                    .onSubmit { kernel.refresh() }
                Button("选择…") { kernel.chooseKernel() }
                if kernel.bundledKernelPath != nil, !kernel.usesBundled {
                    Button("使用内置内核") { kernel.useBundledKernel() }
                        .help("切回随 App 一起打包的内核")
                }
                Button("自动搜索") { kernel.searchForKernel() }
                    .disabled(kernel.isSearching)
                Button("一键授权") { kernel.authorize() }
                    .disabled(!kernel.exists)
                    .help("等价于终端：chmod +x 并解除 Gatekeeper 隔离标记")
                Button("检测版本") { kernel.detectVersion() }
                    .disabled(!kernel.exists)
                Button("更新内核 (-U)") { updateKernel() }
                    .disabled(!kernel.isUsable)
                    .help("让内核自我更新到最新版（需要联网）")
            }
            HStack(spacing: 10) {
                Circle()
                    .fill(statusColor)
                    .frame(width: 10, height: 10)
                if kernel.usesBundled {
                    Text("内置")
                        .font(.caption2)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 1)
                        .background(Capsule().fill(Color.accentColor.opacity(0.15)))
                        .foregroundStyle(.secondary)
                }
                Text(kernel.message).font(.callout)
                if !kernel.versionText.isEmpty {
                    Text(kernel.versionText)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.top, 2)
        }
    }

    private var statusColor: Color {
        if kernel.kernelPath.isEmpty { return .gray }
        if !kernel.exists { return .red }
        if kernel.quarantined || !kernel.executable { return .orange }
        return .green
    }

    // MARK: 底部面板（命令预览 + 操作 + 日志）

    private var bottomPane: some View {
        VStack(spacing: 8) {
            HStack(spacing: 8) {
                Text("命令").font(.callout).foregroundStyle(.secondary)
                VStack(alignment: .leading, spacing: 2) {
                    if previewCommand.isEmpty {
                        Text("（请先选择并授权内核、填入网址）")
                            .font(.system(size: 11, design: .monospaced))
                            .foregroundStyle(.secondary)
                            .padding(.vertical, 6)
                    } else {
                        CommandScrubView(text: previewCommand)
                            .id(previewCommand)   // 命令变化时滑块自动归零
                    }
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(6)
                .background(Color.black.opacity(0.06), in: RoundedRectangle(cornerRadius: 6))
                Button("复制") { copyToPasteboard(previewCommand) }
                    .disabled(previewCommand.isEmpty)
            }

            HStack(spacing: 10) {
                Button {
                    startDownload()
                } label: {
                    Label("开始下载", systemImage: "arrow.down.circle.fill")
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
                .disabled(!kernel.isUsable || runner.isRunning)

                Button("取消") { runner.cancel() }
                    .disabled(!runner.isRunning)

                Button("查看可用格式") { listFormats() }
                    .disabled(!kernel.isUsable || runner.isRunning || store.urlLines.isEmpty)

                Button("打开输出目录") { openOutputFolder() }

                Button("清空日志") { runner.clearLog() }

                Spacer()

                if runner.isRunning {
                    ProgressView().controlSize(.small)
                }
                if let percent = runner.percent {
                    ProgressView(value: percent, total: 100)
                        .frame(width: 150)
                }
                Text(runner.statusText).font(.callout)
            }

            LogPanel()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    private var previewCommand: String {
        guard kernel.isUsable, !store.urlLines.isEmpty else { return "" }
        var args = ArgBuilder.buildArgs(store)
        args.append(contentsOf: store.urlLines)
        return ArgBuilder.commandPreview(exe: kernel.kernelPath, args: args)
    }

    // MARK: 动作

    private func startDownload() {
        guard !runner.isRunning else { return }
        guard kernel.isUsable else {
            runner.statusText = "请先选择并授权 yt-dlp 内核"
            return
        }
        guard !store.urlLines.isEmpty else {
            runner.statusText = "请输入至少一个网址"
            return
        }
        var args = ArgBuilder.buildArgs(store)
        args.append(contentsOf: store.urlLines)
        if store.markEnabled {
            _ = store.consumeMarkNumber()   // 真正开始下载才消耗批次号
        }
        let dir = store.resolvedOutputDir
        runner.run(
            executable: kernel.kernelPath,
            arguments: args,
            directory: dir,
            taskTitle: "开始下载"
        )
    }

    private func listFormats() {
        guard kernel.isUsable, !store.urlLines.isEmpty else { return }
        var args = ["-F"]
        args.append(contentsOf: store.urlLines)
        runner.run(
            executable: kernel.kernelPath,
            arguments: args,
            directory: store.resolvedOutputDir,
            taskTitle: "查询可用格式"
        )
    }

    private func updateKernel() {
        guard kernel.isUsable else { return }
        runner.run(
            executable: kernel.kernelPath,
            arguments: ["-U"],
            directory: store.resolvedOutputDir,
            taskTitle: "更新内核（yt-dlp -U）"
        )
    }

    private func openOutputFolder() {
        let dir = store.resolvedOutputDir
        NSWorkspace.shared.open(URL(fileURLWithPath: dir, isDirectory: true))
    }
}

/// 日志显示面板
struct LogPanel: View {
    @EnvironmentObject var runner: DownloadRunner

    var body: some View {
        VStack(spacing: 0) {
            HStack {
                Text("运行输出")
                    .font(.callout)
                    .foregroundStyle(.secondary)
                Spacer()
                Text("进度 %：\(runner.percent.map { String(format: "%.1f", $0) } ?? "-")")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            .padding(.vertical, 3)
            Divider()
            ScrollViewReader { proxy in
                ScrollView {
                    Text(runner.logText.isEmpty ? "（在这里查看实时输出…）" : runner.logText)
                        .font(.system(size: 11, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .id("logEnd")
                }
                .onReceive(runner.$logText) { _ in
                    withAnimation(.linear(duration: 0.1)) {
                        proxy.scrollTo("logEnd", anchor: .bottom)
                    }
                }
            }
        }
        .background(Color.black.opacity(0.03))
        .clipShape(RoundedRectangle(cornerRadius: 6))
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(Color.secondary.opacity(0.25))
        )
    }
}
