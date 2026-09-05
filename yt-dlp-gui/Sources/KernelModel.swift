import Foundation
import AppKit
import Combine
import Darwin

/// 管理 yt-dlp 内核程序：定位、状态检测、授权（chmod +x、移除隔离标记）
final class KernelModel: ObservableObject {
    @Published var kernelPath = ""
    @Published var exists = false
    @Published var executable = false
    @Published var quarantined = false
    @Published var message = ""
    @Published var versionText = ""
    @Published var isSearching = false

    private static let pathKey = "ytdlpgui.kernelPath"
    private static let overrideKey = "ytdlpgui.kernelOverride"
    private static let quarantineName = "com.apple.quarantine"
    private let ud = UserDefaults.standard

    /// 是否正在使用“打进 App 的内置内核”
    @Published var usesBundled = false

    /// 内置内核路径（随 App 一起移动，放进 Contents/Resources）
    var bundledKernelPath: String? {
        guard let res = Bundle.main.resourceURL else { return nil }
        let p = res.appendingPathComponent("yt-dlp_macos").path
        return FileManager.default.fileExists(atPath: p) ? p : nil
    }

    init() {
        let override = ud.bool(forKey: KernelModel.overrideKey)
        let saved = ud.string(forKey: KernelModel.pathKey) ?? ""
        if let bundled = bundledKernelPath {
            // 内置内核存在：
            //  · 没有“手动改用外部内核”的记录 → 始终优先内置（App 随便移动都有效）
            //  · 有记录且外部文件还在 → 尊重用户手动选择
            //  · 有记录但文件已失效 → 自动回退内置
            if !override {
                select(path: bundled, markOverride: false)
            } else if FileManager.default.fileExists(atPath: saved) {
                select(path: saved, markOverride: true)
            } else {
                select(path: bundled, markOverride: false)
            }
        } else if !saved.isEmpty, FileManager.default.fileExists(atPath: saved) {
            select(path: saved, markOverride: override)
        } else if let first = quickCandidate() {
            select(path: first, markOverride: false)
        } else {
            searchForKernel()
        }
    }

    /// 无需递归的快速探测（常见位置），避免首启等待
    private func quickCandidate() -> String? {
        let home = NSHomeDirectory()
        var list: [String] = []
        if let bundleDir = Bundle.main.resourceURL?.deletingLastPathComponent().deletingLastPathComponent() {
            list.append(bundleDir.path + "/yt-dlp_macos")
        }
        list += [
            home + "/Documents/Products/yt-dlp/yt-dlp_macos",
            home + "/Documents/yt-dlp_macos",
            home + "/Downloads/yt-dlp_macos",
            home + "/Desktop/yt-dlp_macos"
        ]
        for p in list where FileManager.default.fileExists(atPath: p) {
            return p
        }
        return nil
    }

    var isUsable: Bool {
        exists && executable && !quarantined
    }

    // MARK: 检测状态

    func refresh() {
        let fm = FileManager.default
        exists = !kernelPath.isEmpty && fm.fileExists(atPath: kernelPath)
        executable = false
        quarantined = false
        if exists {
            if let attrs = try? fm.attributesOfItem(atPath: kernelPath),
               let perms = attrs[.posixPermissions] as? NSNumber {
                executable = (perms.intValue & 0o111) != 0
            }
            quarantined = hasQuarantine(kernelPath)
        }
        updateMessage()
    }

    private func updateMessage() {
        if kernelPath.isEmpty {
            message = "尚未选择内核。点击「选择…」定位 yt-dlp_macos，或点「自动搜索」。"
        } else if !exists {
            message = "⚠️ 路径不存在，请重新选择内核程序。"
        } else if quarantined {
            message = usesBundled
                ? "⚠️ 内置内核带隔离标记，点击「一键授权」解除。"
                : "⚠️ 文件带 macOS 隔离标记（Gatekeeper），点击「一键授权」解除。"
        } else if !executable {
            message = usesBundled
                ? "⚠️ 内置内核缺少执行权限，点击「一键授权」（等价于 chmod +x）。"
                : "⚠️ 缺少执行权限，点击「一键授权」（等价于终端 chmod +x）。"
        } else {
            message = usesBundled ? "✅ 内置内核就绪，可直接下载。" : "✅ 内核就绪，可以直接下载。"
        }
    }

    // MARK: 选择内核

    func chooseKernel() {
        guard let path = choosePathPanel(title: "选择 yt-dlp 内核程序（yt-dlp_macos）", canChooseDirectories: false),
              !path.isEmpty else { return }
        select(path: path, markOverride: true)
    }

    /// 切回 App 内置内核
    func useBundledKernel() {
        guard let bundled = bundledKernelPath else {
            message = "此版本未内置内核，请用「选择…」指定外部 yt-dlp_macos。"
            return
        }
        select(path: bundled, markOverride: false)
    }

    private func select(path: String, markOverride: Bool) {
        kernelPath = path
        ud.set(path, forKey: KernelModel.pathKey)
        ud.set(markOverride, forKey: KernelModel.overrideKey)
        refresh()
        usesBundled = (path == bundledKernelPath)
        if exists, quarantined || !executable {
            authorize()
        }
    }

    // MARK: 自动搜索

    func searchForKernel() {
        let roots = defaultCandidateRoots()
        isSearching = true
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            let found = self.findIn(roots: roots)
            DispatchQueue.main.async {
                self.isSearching = false
                if let found {
                    self.select(path: found, markOverride: false)
                } else {
                    self.message = "未找到 yt-dlp_macos，请点击「选择…」手动定位。"
                }
            }
        }
    }

    private func defaultCandidateRoots() -> [String] {
        let home = NSHomeDirectory()
        var roots = [home + "/Documents", home + "/Downloads", home + "/Desktop"]
        if let bundleDir = Bundle.main.resourceURL?.deletingLastPathComponent().deletingLastPathComponent() {
            roots.insert(bundleDir.path, at: 0)
        }
        return roots
    }

    private func findIn(roots: [String]) -> String? {
        let fm = FileManager.default
        var scanned = 0
        let limit = 30000
        func walk(_ dir: String, depth: Int) -> String? {
            guard depth <= 4, scanned < limit else { return nil }
            guard let items = try? fm.contentsOfDirectory(atPath: dir) else { return nil }
            for item in items {
                scanned += 1
                if scanned > limit { return nil }
                let full = dir + "/" + item
                var isDir: ObjCBool = false
                guard fm.fileExists(atPath: full, isDirectory: &isDir) else { continue }
                if isDir.boolValue {
                    if !item.hasPrefix("."), depth < 4 {
                        if let r = walk(full, depth: depth + 1) { return r }
                    }
                } else if item == "yt-dlp_macos" {
                    return full
                }
            }
            return nil
        }
        for root in roots {
            if let r = walk(root, depth: 0) { return r }
        }
        return nil
    }

    // MARK: 授权

    func authorize() {
        guard !kernelPath.isEmpty, exists else {
            message = "请先选择内核程序。"
            return
        }
        do {
            try FileManager.default.setAttributes([.posixPermissions: 0o755], ofItemAtPath: kernelPath)
            executable = true
        } catch {
            message = "设置执行权限失败：\(error.localizedDescription)"
            refresh()
            return
        }
        if quarantined {
            _ = removeQuarantine(kernelPath)
        }
        refresh()
        message = exists && executable && !quarantined
            ? "✅ 已授权：chmod +x 完成，隔离标记已解除。"
            : "授权未完全生效，请重试；或检查文件归属（Owner）。"
    }

    // MARK: 检测版本 / 快速执行

    func detectVersion() {
        guard exists else { return }
        DispatchQueue.global(qos: .userInitiated).async { [weak self] in
            guard let self else { return }
            let (code, output) = self.runCapture(args: ["--version"])
            let text = output.trimmingCharacters(in: .whitespacesAndNewlines)
            DispatchQueue.main.async {
                if code == 0, !text.isEmpty {
                    self.versionText = "版本：\(text)"
                } else {
                    self.versionText = ""
                    self.message = "检测版本失败（退出码 \(code)）：\(text)"
                }
            }
        }
    }

    /// 快速同步执行并抓取输出（用于 --version 等短命令）
    func runCapture(args: [String], timeout: TimeInterval = 25) -> (Int32, String) {
        let p = Process()
        p.executableURL = URL(fileURLWithPath: kernelPath)
        p.arguments = args
        p.standardOutput = Pipe()
        p.standardError = Pipe()
        let outPipe = p.standardOutput as! Pipe
        let errPipe = p.standardError as! Pipe
        do {
            try p.run()
        } catch {
            return (1, "启动失败：\(error.localizedDescription)")
        }
        let deadline = Date().addingTimeInterval(timeout)
        while p.isRunning, Date() < deadline {
            Thread.sleep(forTimeInterval: 0.05)
        }
        if p.isRunning { p.terminate() }
        p.waitUntilExit()
        let out = String(data: outPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        let err = String(data: errPipe.fileHandleForReading.readDataToEndOfFile(), encoding: .utf8) ?? ""
        return (p.terminationStatus, out + err)
    }

    // MARK: xattr

    private func hasQuarantine(_ path: String) -> Bool {
        let result = path.withCString { p in
            KernelModel.quarantineName.withCString { n in
                getxattr(p, n, nil, 0, 0, 0)
            }
        }
        return result >= 0
    }

    private func removeQuarantine(_ path: String) -> Bool {
        let result = path.withCString { p in
            KernelModel.quarantineName.withCString { n in
                removexattr(p, n, 0)
            }
        }
        return result == 0
    }
}
