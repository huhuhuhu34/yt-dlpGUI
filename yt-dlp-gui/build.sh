#!/usr/bin/env bash
# yt-dlp 管理器 —— 无需 Xcode，用 swiftc 直接编译并打包 .app
set -euo pipefail
cd "$(dirname "$0")"
ROOT="$(pwd)"
APP_NAME="yt-dlpGUI"
DEPLOY="13.0"
BUILD="$ROOT/build"
OUT_DIR="$ROOT/dist"
# 要嵌入 App 的内核源文件：默认取上一级目录的 yt-dlp_macos，可用 YTDLP_KERNEL 覆盖
KERNEL_SRC="${YTDLP_KERNEL:-$ROOT/../yt-dlp_macos}"
if [[ -n "${1:-}" && "$1" != -* ]]; then
    OUT_DIR="$1"
fi
OUT="$OUT_DIR/$APP_NAME.app"

BIN_ARM="$BUILD/${APP_NAME}_arm64"
BIN_X86="$BUILD/${APP_NAME}_x86_64"
BIN_UNI="$BUILD/$APP_NAME"

mkdir -p "$BUILD" "$OUT_DIR"
rm -rf -- "$OUT"
mkdir -p "$OUT/Contents/MacOS" "$OUT/Contents/Resources"

SOURCES=()
while IFS= read -r line; do
    SOURCES+=("$line")
done < <(find "$ROOT/Sources" -name '*.swift' | sort)

echo "==> 编译 arm64"
swiftc -parse-as-library -swift-version 5 -O \
    -target "arm64-apple-macosx$DEPLOY" \
    "${SOURCES[@]}" -o "$BIN_ARM"

echo "==> 编译 x86_64"
swiftc -parse-as-library -swift-version 5 -O \
    -target "x86_64-apple-macosx$DEPLOY" \
    "${SOURCES[@]}" -o "$BIN_X86"

echo "==> 合成通用二进制 (Universal)"
lipo -create -output "$BIN_UNI" "$BIN_ARM" "$BIN_X86"

echo "==> 组装 .app"
cp "$BIN_UNI" "$OUT/Contents/MacOS/$APP_NAME"
chmod +x "$OUT/Contents/MacOS/$APP_NAME"
cp "$ROOT/Resources/Info.plist" "$OUT/Contents/Info.plist"
plutil -lint "$OUT/Contents/Info.plist" >/dev/null

echo "==> 嵌入内核"
if [[ ! -f "$KERNEL_SRC" ]]; then
    echo "错误：找不到内核 $KERNEL_SRC" >&2
    echo "      可用 YTDLP_KERNEL=/路径/yt-dlp_macos ./build.sh 指定" >&2
    exit 1
fi
cp "$KERNEL_SRC" "$OUT/Contents/Resources/yt-dlp_macos"
chmod +x "$OUT/Contents/Resources/yt-dlp_macos"
xattr -d com.apple.quarantine "$OUT/Contents/Resources/yt-dlp_macos" 2>/dev/null || true
KERNEL_SIZE=$(ls -lh "$OUT/Contents/Resources/yt-dlp_macos" | awk '{print $5}')
echo "    → 已嵌入内核：$KERNEL_SIZE (Resources/yt-dlp_macos)"

echo "==> 复制应用图标"
if [[ -f "$ROOT/Resources/AppIcon.icns" ]]; then
    cp "$ROOT/Resources/AppIcon.icns" "$OUT/Contents/Resources/AppIcon.icns"
    echo "    → AppIcon.icns"
else
    echo "    → 未找到 AppIcon.icns（可先运行 tools/build_icon.sh 生成）"
fi

echo "==> ad-hoc 签名"
codesign --force --deep --sign - "$OUT"
codesign --verify --deep --strict "$OUT" 2>/dev/null && echo "==> 签名校验通过"

echo ""
echo "✔ 构建完成：$OUT"
echo "   启动命令：open \"$OUT\""
if [[ "${2:-}" == "--open" ]]; then
    open "$OUT"
fi

# 可选的参数拼接自检：bash build.sh --smoke
if [[ " $* " == *" --smoke "* ]]; then
    echo ""
    echo "==> 运行参数自检"
    swiftc -swift-version 5 \
        "$ROOT/Sources/SettingsStore.swift" \
        "$ROOT/Sources/ArgBuilder.swift" \
        "$ROOT/tests/main.swift" \
        -o "$BUILD/smoke"
    "$BUILD/smoke"
fi
