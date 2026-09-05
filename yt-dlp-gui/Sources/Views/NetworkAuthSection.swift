import SwiftUI
import AppKit

struct NetworkAuthSection: View {
    @EnvironmentObject var store: SettingsStore

    var body: some View {
        SectionCard(title: "网络 / 登录") {
            Toggle("使用代理服务器（--proxy）", isOn: $store.useProxy)
            if store.useProxy {
                FieldRow("代理地址", help: "例如 http://127.0.0.1:1080 或 socks5://…；留空 = 强制直连") {
                    TextField("http://127.0.0.1:1080", text: $store.proxy)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 340)
                }
            }

            FieldRow("Cookies", help: "需要登录后才能看的视频请选择") {
                Picker("", selection: $store.cookieMode) {
                    Text("不使用").tag(0)
                    Text("Cookie 文件").tag(1)
                    Text("从浏览器读取").tag(2)
                }
                .labelsHidden()
                .pickerStyle(.segmented)
                .frame(width: 360)
            }
            if store.cookieMode == 1 {
                FieldRow("Cookie 文件", help: "Netscape 格式，可用浏览器插件导出") {
                    HStack(spacing: 6) {
                        TextField("", text: $store.cookieFile)
                            .textFieldStyle(.roundedBorder)
                            .frame(width: 260)
                        Button("浏览…") { chooseCookieFile() }
                    }
                }
            }
            if store.cookieMode == 2 {
                FieldRow("浏览器", help: "读取该浏览器已保存的登录状态") {
                    Picker("", selection: $store.browserCookieSource) {
                        ForEach(SettingsStore.browserList, id: \.self) { name in
                            Text(name).tag(name)
                        }
                    }
                    .labelsHidden()
                    .pickerStyle(.menu)
                    .frame(width: 180)
                }
            }

            Divider().padding(.vertical, 2)

            FieldRow("账号 / 密码", help: "部分站点需要登录（--username/--password/--twofactor）") {
                HStack(spacing: 6) {
                    TextField("用户名", text: $store.username)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 120)
                    SecureField("密码", text: $store.password)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 120)
                    TextField("两步验证", text: $store.twofactor)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 100)
                }
            }
            Toggle("使用 .netrc 认证（--netrc）", isOn: $store.useNetrc)

            Divider().padding(.vertical, 2)

            FieldRow("限速 / 重试 / 并发", help: "留空即使用 yt-dlp 默认值") {
                HStack(spacing: 6) {
                    TextField("限速 如 2M", text: $store.limitRate)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 110)
                    TextField("重试 如 10", text: $store.retries)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 110)
                    TextField("并发片段 -N", text: $store.concurrentFragments)
                        .textFieldStyle(.roundedBorder)
                        .frame(width: 110)
                }
            }
        }
    }

    private func chooseCookieFile() {
        if let p = choosePathPanel(title: "选择 Cookie 文件", canChooseDirectories: false) {
            store.cookieFile = p
        }
    }
}
