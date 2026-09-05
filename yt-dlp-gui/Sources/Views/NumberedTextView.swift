import SwiftUI
import AppKit

// MARK: - 圆数字符

/// ①～⑳ → ㉑～㉟ → ㊱～㊿ → (n)
func circledNumber(_ n: Int) -> String {
    guard n >= 1 else { return "" }
    if n <= 20 { return String(UnicodeScalar(0x2460 + n - 1)!) }
    if n <= 35 { return String(UnicodeScalar(0x3251 + n - 21)!) }
    if n <= 50 { return String(UnicodeScalar(0x32B1 + n - 36)!) }
    return "(\(n))"
}

// MARK: - 行号绘制版 NSTextView

/// 自动在行首绘制 ①②③ 的文本框：
/// - 编号只是显示层，不写入真实文本（复制/解析永远是纯净链接）
/// - 编号永远从 ① 开始、按段落自动连续
/// - 回车产生的新条目（空行）会显示下一个编号等待输入
final class NumberLineTextView: NSTextView {
    /// 编号列宽度（与 textContainerInset.left 对应）
    let gutterWidth: CGFloat = 46

    /// 自建文本三件套（强持有，否则弱引用链会被释放导致 textContainer 为 nil → 整块空白）
    private var ownedStorage: NSTextStorage?
    private var ownedLayoutManager: NSLayoutManager?
    private var ownedContainer: NSTextContainer?

    override init(frame frameRect: NSRect, textContainer container: NSTextContainer?) {
        if let provided = container {
            super.init(frame: frameRect, textContainer: provided)
        } else {
            // 显式创建 NSTextStorage + NSLayoutManager + NSTextContainer，并由本类强持有
            let storage = NSTextStorage()
            let layoutManager = NSLayoutManager()
            storage.addLayoutManager(layoutManager)
            let newContainer = NSTextContainer(size: frameRect.size)
            newContainer.widthTracksTextView = true
            layoutManager.addTextContainer(newContainer)

            super.init(frame: frameRect, textContainer: newContainer)

            ownedStorage = storage
            ownedLayoutManager = layoutManager
            ownedContainer = newContainer
        }
        commonInit()
    }

    required init?(coder: NSCoder) {
        super.init(coder: coder)
        commonInit()
    }

    private func commonInit() {
        textContainerInset = NSSize(width: gutterWidth + 2, height: 8)
        textContainer?.lineFragmentPadding = 4
    }

    override func layout() {
        super.layout()
        if let tc = textContainer, let sv = enclosingScrollView {
            tc.containerSize = NSSize(width: sv.contentSize.width, height: .greatestFiniteMagnitude)
        }
    }

    override func drawBackground(in dirtyRect: NSRect) {
        super.drawBackground(in: dirtyRect)
        drawLineNumbers()
    }
    // MARK: 行号绘制

    private func drawLineNumbers() {
        guard let lm = layoutManager, let container = textContainer else { return }
        let text = string as NSString

        // 收集行片段：rect 以内容区顶部为 0（y 向下）；视图已翻转，叠加 containerOrigin 即视图坐标
        var fragments: [(start: Int, rect: NSRect)] = []
        var firstRowHeight: CGFloat = 15
        let fullGlyphRange = lm.glyphRange(for: container)
        lm.enumerateLineFragments(forGlyphRange: fullGlyphRange) { rect, _, _, glyphRange, _ in
            let charRange = lm.characterRange(forGlyphRange: glyphRange, actualGlyphRange: nil)
            fragments.append((start: charRange.location, rect: rect))
            if fragments.count == 1 { firstRowHeight = rect.height }
        }
        let origin = textContainerOrigin

        var lastDrawnRow = 0
        var cursor = 0
        var nlCount = 0
        var maxBottom: CGFloat = 0

        func countNewlines(from: Int, to: Int) -> Int {
            guard to > from else { return 0 }
            var count = 0
            var i = from
            while i < to {
                if text.character(at: i) == 10 { count += 1 }
                i += 1
            }
            return count
        }

        for f in fragments {
            if f.start >= cursor {
                nlCount += countNewlines(from: cursor, to: f.start)
                let row = nlCount + 1
                if row != lastDrawnRow {
                    drawNumber(row, topY: origin.y + f.rect.minY, rowHeight: f.rect.height)
                    lastDrawnRow = row
                }
                cursor = f.start
            }
            maxBottom = max(maxBottom, f.rect.maxY)
        }

        // 文本以换行结尾时的“待输入空条目”：没有独立 fragment，画在末尾下一行
        let endsWithNewline = text.length > 0 && text.character(at: text.length - 1) == 10
        if endsWithNewline {
            drawNumber(nlCount + 1, topY: origin.y + maxBottom, rowHeight: firstRowHeight)
        }

        // 完全空白的编辑器：显示 ① 等待输入
        if text.length == 0 {
            drawNumber(1, topY: origin.y, rowHeight: firstRowHeight)
        }

        // 编号列与文本区之间的分隔线
        var dividerBottom = origin.y + maxBottom
        if endsWithNewline || text.length == 0 {
            dividerBottom = origin.y + maxBottom + firstRowHeight
        }
        if dividerBottom > origin.y {
            NSColor.separatorColor.withAlphaComponent(0.5).setStroke()
            let line = NSBezierPath()
            line.move(to: NSPoint(x: gutterWidth - 1, y: origin.y - 6))
            line.line(to: NSPoint(x: gutterWidth - 1, y: dividerBottom + 2))
            line.lineWidth = 1
            line.stroke()
        }
    }

    private func drawNumber(_ n: Int, topY: CGFloat, rowHeight: CGFloat) {
        let number = circledNumber(n)
        guard !number.isEmpty else { return }
        let font = NSFont.monospacedSystemFont(ofSize: 11, weight: .regular)
        let style = NSMutableParagraphStyle()
        style.alignment = .right
        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.secondaryLabelColor,
            .paragraphStyle: style
        ]
        let size = (number as NSString).size(withAttributes: attrs)
        let rect = NSRect(
            x: 0,
            y: topY + max(0, (rowHeight - size.height) / 2),
            width: gutterWidth - 10,
            height: size.height
        )
        (number as NSString).draw(with: rect, options: [.usesLineFragmentOrigin], attributes: attrs)
    }
}
// MARK: - SwiftUI 包装

/// 带强制连续编号 ①②③… 的多行链接编辑器
struct NumberedTextView: NSViewRepresentable {
    @Binding var text: String

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeNSView(context: Context) -> NSScrollView {
        let scroll = NSScrollView()
        scroll.hasVerticalScroller = true
        scroll.hasHorizontalScroller = false
        scroll.autohidesScrollers = true
        scroll.borderType = .noBorder
        scroll.drawsBackground = true

        let tv = NumberLineTextView(frame: NSRect(x: 0, y: 0, width: 200, height: 100),
                                    textContainer: nil)
        tv.isRichText = false
        tv.allowsUndo = true
        tv.font = NSFont.monospacedSystemFont(ofSize: 12, weight: .regular)
        tv.textColor = .textColor
        tv.backgroundColor = .textBackgroundColor
        tv.drawsBackground = true   // 必须开启，否则 drawBackground 不回调 → 编号画不出来
        tv.isEditable = true
        tv.isSelectable = true
        tv.delegate = context.coordinator

        tv.minSize = NSSize(width: 0, height: 0)
        tv.maxSize = NSSize(width: CGFloat.greatestFiniteMagnitude,
                            height: CGFloat.greatestFiniteMagnitude)
        tv.isVerticallyResizable = true
        tv.isHorizontallyResizable = false
        tv.autoresizingMask = [.width]
        tv.textContainer?.widthTracksTextView = true

        context.coordinator.textView = tv
        tv.string = text

        scroll.documentView = tv
        return scroll
    }

    func updateNSView(_ scroll: NSScrollView, context: Context) {
        guard let tv = scroll.documentView as? NumberLineTextView else { return }
        if tv.string != text {
            tv.string = text
            tv.needsDisplay = true
        }

        // 让文档视图与文本容器跟随滚动区真实尺寸（防止 SwiftUI 首次布局宽度为 0 → 整块空白）
        scroll.layoutSubtreeIfNeeded()
        let width = scroll.contentSize.width > 1 ? scroll.contentSize.width : scroll.bounds.width
        if tv.frame.width != width {
            tv.frame.size.width = width
        }
        if let tc = tv.textContainer {
            if tc.containerSize.width != width {
                tc.containerSize = NSSize(width: width, height: CGFloat.greatestFiniteMagnitude)
            }
            tv.layoutManager?.ensureLayout(for: tc)
            let insetY = tv.textContainerInset.height * 2
            let usedH = (tv.layoutManager?.usedRect(for: tc) ?? .zero).height + insetY
            let targetH = max(scroll.contentSize.height, max(usedH, 100))
            if abs(tv.frame.height - targetH) > 1 {
                tv.frame.size.height = targetH
            }
        }
        tv.needsDisplay = true
    }

    /// 让 SwiftUI 按提案尺寸布局（NSScrollView 没有内在尺寸，必须显式返回提案宽度）
    func sizeThatFits(_ proposal: ProposedViewSize, nsView: NSScrollView, context: Context) -> CGSize? {
        CGSize(width: proposal.width ?? 300, height: proposal.height ?? 100)
    }

    // MARK: Coordinator

    final class Coordinator: NSObject, NSTextViewDelegate {
        var parent: NumberedTextView
        weak var textView: NumberLineTextView?

        init(_ parent: NumberedTextView) {
            self.parent = parent
        }

        func textDidChange(_ notification: Notification) {
            if let tv = textView {
                parent.text = tv.string
            }
        }

        /// 拦截：位于某条行首按 Backspace/Delete → 删除整条（编号随条目消失并自动重排）
        func textView(_ textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            guard commandSelector == #selector(NSResponder.deleteBackward(_:)) else {
                return false
            }
            let sel = textView.selectedRange()
            guard sel.length == 0 else { return false }   // 有选区时交给默认删除
            let ns = textView.string as NSString
            guard ns.length > 0 else { return false }

            let items = itemRanges(ns)
            guard !items.isEmpty else { return false }
            let loc = sel.location
            let idx = itemIndex(at: loc, in: items)
            let r = items[idx]
            let col = loc - r.location
            guard col == 0 else { return false }

            var removal = NSRange(location: NSNotFound, length: 0)
            if r.length == 0 {
                // 空条目：删除它自己的换行（若存在）
                if r.location < ns.length, ns.character(at: r.location) == 10 {
                    removal = NSRange(location: r.location, length: 1)
                } else if r.location == ns.length, idx > 0 {
                    removal = NSRange(location: ns.length - 1, length: 1) // 末尾空行
                }
            } else {
                let end = idx + 1 < items.count ? items[idx + 1].location : ns.length
                removal = NSRange(location: r.location, length: end - r.location)
            }

            guard removal.location != NSNotFound else { return false }
            textView.insertText("", replacementRange: removal)
            textView.setSelectedRange(NSRange(location: removal.location, length: 0))
            return true
        }

        // MARK: 行模型（按 \n 拆分；item 不含其结尾换行符）

        private func itemRanges(_ ns: NSString) -> [NSRange] {
            var items: [NSRange] = []
            var start = 0
            var i = 0
            let count = ns.length
            while i < count {
                if ns.character(at: i) == 10 {
                    items.append(NSRange(location: start, length: i - start))
                    start = i + 1
                }
                i += 1
            }
            items.append(NSRange(location: start, length: count - start))
            return items
        }

        private func itemIndex(at loc: Int, in items: [NSRange]) -> Int {
            for (i, r) in items.enumerated() {
                if loc >= r.location && loc <= r.location + r.length {
                    return i
                }
            }
            return items.count - 1
        }
    }
}
