import Foundation

// 集成测试：用 App 的真实引擎执行内核命令，验证 进程启动 + 流式输出 + 结束回调
// 编译：swiftc -swift-version 5 Sources/SettingsStore.swift Sources/ArgBuilder.swift Sources/DownloadRunner.swift tests/RunHarness.swift -o build/runharness
// 运行：./build/runharness /path/to/yt-dlp_macos --version

@main
struct RunHarness {
    static func main() {
        let args = CommandLine.arguments
        guard args.count >= 3 else {
            print("用法: runharness <内核路径> <参数...>")
            exit(2)
        }
        let exe = args[1]
        let cmdArgs = Array(args.dropFirst(2))

        let runner = DownloadRunner()
        var finished = false
        runner.onFinished = { code in
            print("__EXIT_CODE=\(code)")
            finished = true
        }
        runner.run(executable: exe, arguments: cmdArgs, directory: NSHomeDirectory(), taskTitle: "集成测试")

        let deadline = Date().addingTimeInterval(40)
        while !finished && Date() < deadline {
            RunLoop.current.run(mode: .default, before: Date().addingTimeInterval(0.1))
        }

        print("__STATUS=\(runner.statusText)")
        let logHead = String(runner.logText.prefix(800))
        print("__LOG_HEAD>>\n\(logHead)\n<<__LOG_HEAD")
        print(finished ? "__RESULT=PASS" : "__RESULT=TIMEOUT")
        exit(finished ? 0 : 1)
    }
}
