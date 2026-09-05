#!/usr/bin/env bash
# 生成 App 图标：渲染 PNG → iconutil 合成 Resources/AppIcon.icns
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$(pwd)"

ICONSET="$ROOT/build/AppIcon.iconset"
mkdir -p "$ICONSET"
rm -f "$ICONSET"/*.png

echo "==> 渲染图标 PNG（Swift + AppKit）"
swift "$ROOT/tools/make_icon.swift" "$ICONSET"

echo "==> 合成 AppIcon.icns"
rm -f "$ROOT/Resources/AppIcon.icns"
iconutil -c icns "$ICONSET" -o "$ROOT/Resources/AppIcon.icns"

echo "==> 完成"
ls -lh "$ROOT/Resources/AppIcon.icns"