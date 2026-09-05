import SwiftUI

@main
struct YTDLPApp: App {
    @StateObject private var store = SettingsStore()
    @StateObject private var kernel = KernelModel()
    @StateObject private var runner = DownloadRunner()

    var body: some Scene {
        WindowGroup {
            ContentView()
                .environmentObject(store)
                .environmentObject(kernel)
                .environmentObject(runner)
                .frame(minWidth: 1000, minHeight: 760)
        }
    }
}
