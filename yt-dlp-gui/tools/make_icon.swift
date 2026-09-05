import AppKit

// ===== yt-dlpGUI App 图标生成器 =====
// 绘制：深蓝→紫渐变圆角方块 + 白色下载箭头
// 用法：swift tools/make_icon.swift <输出iconset目录>
// 产出：icon_16x16.png ~ icon_512x512@2x.png 共 10 张

let CANVAS: CGFloat = 1024

// MARK: - 颜色

func color(_ r: CGFloat, _ g: CGFloat, _ b: CGFloat, _ a: CGFloat = 1) -> NSColor {
    NSColor(calibratedRed: r / 255, green: g / 255, blue: b / 255, alpha: a)
}

let blueTop = color(59, 130, 246)        // #3B82F6
let indigoMid = color(79, 70, 229)       // #4F46E5
let violetBottom = color(124, 58, 237)   // #7C3AED
let white = NSColor.white

// MARK: - 绘制 1024 主图

func makeMasterImage() -> NSImage {
    let image = NSImage(size: NSSize(width: CANVAS, height: CANVAS))
    image.lockFocus()
    defer { image.unlockFocus() }

    let canvasRect = NSRect(x: 0, y: 0, width: CANVAS, height: CANVAS)
    let cornerRadius: CGFloat = 185
    let basePath = NSBezierPath(roundedRect: canvasRect, xRadius: cornerRadius, yRadius: cornerRadius)

    // 1) 渐变背景
    guard let gradient = NSGradient(colorsAndLocations:
        (blueTop, 0.0),
        (indigoMid, 0.55),
        (violetBottom, 1.0)
    ) else { return image }
    gradient.draw(in: basePath, angle: 135)

    // 2) 顶部柔和高光
    NSGraphicsContext.saveGraphicsState()
    basePath.addClip()
    let sheenRect = NSRect(x: 0, y: CANVAS * 0.62, width: CANVAS, height: CANVAS * 0.38)
    if let sheen = NSGradient(colorsAndLocations:
        (color(255, 255, 255, 0.16), 0.0),
        (color(255, 255, 255, 0.0), 1.0)
    ) {
        sheen.draw(in: sheenRect, angle: 90)
    }
    // 边缘高光描边（微妙的玻璃感）
    let edge = NSBezierPath(roundedRect: canvasRect.insetBy(dx: 5, dy: 5),
                            xRadius: cornerRadius - 4, yRadius: cornerRadius - 4)
    color(255, 255, 255, 0.10).setStroke()
    edge.lineWidth = 9
    edge.stroke()
    NSGraphicsContext.restoreGraphicsState()

    // 3) 白色下载箭头（带柔和投影）
    NSGraphicsContext.saveGraphicsState()
    let shadow = NSShadow()
    shadow.shadowColor = color(0, 0, 0, 0.28)
    shadow.shadowBlurRadius = 34
    shadow.shadowOffset = NSSize(width: 0, height: -10)
    shadow.set()

    let silhouette = NSBezierPath()
    // 箭头杆（上：AppKit 坐标系 y 向上，杆放在画面中上部）
    silhouette.appendRoundedRect(
        NSRect(x: 464, y: 464, width: 96, height: 390),
        xRadius: 48, yRadius: 48
    )
    // 箭头头部：尖端朝下（下载方向 ↓）
    let head = NSBezierPath()
    head.move(to: NSPoint(x: 352, y: 464))
    head.line(to: NSPoint(x: 672, y: 464))
    head.line(to: NSPoint(x: 512, y: 270))
    head.close()
    silhouette.append(head)
    // 托盘（底部）
    silhouette.appendRoundedRect(
        NSRect(x: 252, y: 156, width: 520, height: 112),
        xRadius: 56, yRadius: 56
    )

    white.setFill()
    silhouette.fill()
    NSGraphicsContext.restoreGraphicsState()

    return image
}

// MARK: - 导出 PNG

func pngData(of master: NSImage, pixelSize: Int) -> Data? {
    let rep = NSBitmapImageRep(
        bitmapDataPlanes: nil,
        pixelsWide: pixelSize,
        pixelsHigh: pixelSize,
        bitsPerSample: 8,
        samplesPerPixel: 4,
        hasAlpha: true,
        isPlanar: false,
        colorSpaceName: .deviceRGB,
        bytesPerRow: 0,
        bitsPerPixel: 0
    )
    guard let rep else { return nil }
    rep.size = NSSize(width: pixelSize, height: pixelSize)

    NSGraphicsContext.saveGraphicsState()
    NSGraphicsContext.current = NSGraphicsContext(bitmapImageRep: rep)
    let rect = NSRect(x: 0, y: 0, width: pixelSize, height: pixelSize)
    master.draw(in: rect, from: NSRect(x: 0, y: 0, width: CANVAS, height: CANVAS),
                operation: .copy, fraction: 1)
    NSGraphicsContext.restoreGraphicsState()

    return rep.representation(using: .png, properties: [:])
}

// MARK: - 主流程

let outDir = CommandLine.arguments.count > 1
    ? CommandLine.arguments[1]
    : "build/AppIcon.iconset"

try? FileManager.default.createDirectory(
    atPath: outDir, withIntermediateDirectories: true
)

let specs: [(name: String, size: Int)] = [
    ("icon_16x16.png", 16),
    ("icon_16x16@2x.png", 32),
    ("icon_32x32.png", 32),
    ("icon_32x32@2x.png", 64),
    ("icon_128x128.png", 128),
    ("icon_128x128@2x.png", 256),
    ("icon_256x256.png", 256),
    ("icon_256x256@2x.png", 512),
    ("icon_512x512.png", 512),
    ("icon_512x512@2x.png", 1024)
]

let master = makeMasterImage()
var written = 0
for spec in specs {
    guard let data = pngData(of: master, pixelSize: spec.size) else {
        FileHandle.standardError.write("生成失败：\(spec.name)\n".data(using: .utf8)!)
        exit(1)
    }
    let path = outDir + "/" + spec.name
    do {
        try data.write(to: URL(fileURLWithPath: path))
        written += 1
    } catch {
        FileHandle.standardError.write("写入失败：\(path) \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}
print("✔ 已生成 \(written) 张图标 PNG → \(outDir)")
