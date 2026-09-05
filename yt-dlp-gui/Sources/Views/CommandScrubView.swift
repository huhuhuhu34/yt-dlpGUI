import SwiftUI
import AppKit

/// 长命令"横向滑块"预览：命令单行不换行，拖动滑块前后平移查看完整内容
struct CommandScrubView: View {
    let text: String
    @State private var frac: Double = 0

    private let font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            GeometryReader { geo in
                let overflow = max(0, measuredWidth - geo.size.width)
                ZStack(alignment: .leading) {
                    Text(text.isEmpty ? " " : text)
                        .font(.system(size: 11, design: .monospaced))
                        .lineLimit(1)
                        .fixedSize(horizontal: true, vertical: false)
                        .offset(x: -overflow * CGFloat(frac))
                }
                .frame(width: geo.size.width, alignment: .leading)
                .clipped()
            }
            .frame(height: 16)

            Slider(value: $frac, in: 0...1)
                .controlSize(.small)
        }
    }

    private var measuredWidth: CGFloat {
        (text as NSString).size(withAttributes: [.font: font]).width
    }
}
