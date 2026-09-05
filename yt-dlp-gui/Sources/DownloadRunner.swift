import Foundation
import Combine

/// 把收到的字节流切成完整行（避免跨块截断 UTF-8）
struct LineAccumulator {
    private var pending = Data()

    mutating func append(_ data: Data, onLine: (String) -> Void) {
        pending.append(data)
        while let idx = pending.firstIndex(of: 0x0A) {
            var lineData = Data(pending[..<idx])
            pending.removeSubrange(0...idx)
            if lineData.last == 0x0D { lineData.removeLast() }
            if let s = String(data: lineData, encoding: .utf8) {
                onLine(s)
            }
        }
    }

    mutating func flush(_ onLine: (String) -> Void) {
        guard !pending.isEmpty else { return }
        if pending.last == 0x0D { pending.removeLast() }
        if let s = String(data: pending, encoding: .utf8) {
            onLine(s)
        }
        pending.removeAll()
    }
}

/// 真正执行 yt-dlp 内核的进程管理器：实时输出、进度解析、取消
final class DownloadRunner: ObservableObject {
    @Published var isRunning = false
    @Published var logText = ""
    @Published var percent: Double?
    @Published var statusText = "就绪"
    @Published var lastExitCode: Int32?

    /// 结束后回调（主线程）：退出码 0 表示成功
    var onFinished: ((Int32) -> Void)?

    private var process: Process?
    private var drainCount = 0
    private var exited = false
    private var finalizing = false
    private var lastPercentValue: Double?
    private let progressPattern = try! NSRegularExpression(pattern: #"\[download\]\s+([\d.]+)%"#)
    private var forceKillWorkItem: DispatchWorkItem?

    func clearLog() {
        logText = ""
        percent = nil
        statusText = "就绪"
        lastExitCode = nil
    }

    // MARK: 启动

    func run(executable: String, arguments: [String], directory: String? = nil, taskTitle: String? = nil) {
        guard !isRunning else { return }
        resetForRun()

        let exe = URL(fileURLWithPath: executable)
        logText = ""
        if let title = taskTitle {
            logText += "▶ \(title)\n"
        }
        logText += "$ " + ArgBuilder.commandPreview(exe: executable, args: arguments) + "\n\n"
        statusText = "运行中…"
        percent = nil
        isRunning = true

        let p = Process()
        p.executableURL = exe
        p.arguments = arguments

        var env = ProcessInfo.processInfo.environment
        let extraPath = "/opt/homebrew/bin:/usr/local/bin"
        env["PATH"] = (env["PATH"].map { extraPath + ":" + $0 }) ?? extraPath
        p.environment = env

        if let directory, !directory.isEmpty {
            p.currentDirectoryURL = URL(fileURLWithPath: directory, isDirectory: true)
        }

        let outPipe = Pipe()
        let errPipe = Pipe()
        p.standardOutput = outPipe
        p.standardError = errPipe

        process = p
        p.terminationHandler = { [weak self] proc in
            DispatchQueue.main.async {
                guard let self else { return }
                self.exited = true
                self.lastExitCode = proc.terminationStatus
                self.tryFinalize()
            }
        }

        do {
            try p.run()
            startDrain(outPipe.fileHandleForReading)
            startDrain(errPipe.fileHandleForReading)
        } catch {
            logText += "⚠️ 启动失败：\(error.localizedDescription)\n"
            isRunning = false
            statusText = "启动失败"
        }
    }

    private func resetForRun() {
        exited = false
        finalizing = false
        drainCount = 0
        process = nil
        forceKillWorkItem?.cancel()
        forceKillWorkItem = nil
    }

    // MARK: 输出读取

    private func startDrain(_ fh: FileHandle) {
        drainCount += 1
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            var acc = LineAccumulator()
            while true {
                do {
                    let data = try fh.read(upToCount: 16384)
                    if let data, !data.isEmpty {
                        acc.append(data) { line in
                            self?.emitLine(line)
                        }
                    } else {
                        break
                    }
                } catch {
                    break
                }
            }
            acc.flush { line in self?.emitLine(line) }
            try? fh.close()
            DispatchQueue.main.async {
                self?.drainFinished()
            }
        }
    }

    private func emitLine(_ line: String) {
        DispatchQueue.main.async { [weak self] in
            guard let self else { return }
            if self.logText.count > 350_000 {
                self.logText = String(self.logText.suffix(250_000))
            }
            self.logText += line + "\n"
            self.parseProgress(line)
        }
    }

    private func parseProgress(_ line: String) {
        let ns = line as NSString
        let range = NSRange(location: 0, length: ns.length)
        guard let m = progressPattern.firstMatch(in: line, options: [], range: range) else {
            return
        }
        let numRange = m.range(at: 1)
        guard numRange.location != NSNotFound,
              let v = Double(ns.substring(with: numRange)) else { return }
        percent = min(v, 100)
    }

    // MARK: 结束处理

    private func drainFinished() {
        drainCount -= 1
        tryFinalize()
    }

    private func tryFinalize() {
        guard exited, drainCount <= 0, !finalizing else { return }
        finalizing = true
        let code = lastExitCode ?? -1
        process = nil
        isRunning = false
        if code == 0 {
            statusText = "完成 ✅"
            if percent == nil { percent = 100 }
            logText += "\n✅ 任务结束（退出码 0）。\n"
        } else {
            statusText = "已结束（退出码 \(code)）"
            logText += "\n⚠️ 任务结束（退出码 \(code)）。\n"
        }
        let handler = onFinished
        handler?(code)
    }

    // MARK: 取消

    func cancel() {
        guard let p = process, p.isRunning else { return }
        statusText = "正在取消…"
        p.interrupt()   // SIGINT：yt-dlp 会尽量收尾
        let item = DispatchWorkItem { [weak self, weak p] in
            if let p, p.isRunning {
                p.terminate()   // 4 秒后仍不退则强制结束
            }
            self?.forceKillWorkItem = nil
        }
        forceKillWorkItem = item
        DispatchQueue.main.asyncAfter(deadline: .now() + 4, execute: item)
    }
}
