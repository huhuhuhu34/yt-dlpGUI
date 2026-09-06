#!/usr/bin/env python3
"""生成应用图标（.png + .ico，Windows 打包用）。

用法：python tools/make_icon.py
依赖：pillow（仅本工具需要，运行时无第三方依赖）
"""
import os
from PIL import Image, ImageDraw


def build(size: int = 512) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    radius = int(size * 0.19)
    d.rounded_rectangle([0, 0, size - 1, size - 1], radius=radius, fill=(38, 132, 255, 255))
    # 播放三角
    cx, cy, r = size * 0.44, size * 0.5, size * 0.26
    d.polygon([(cx + r * 0.4, cy - r * 0.95), (cx + r * 0.4, cy + r * 0.95), (cx + r * 1.1, cy)],
              fill=(255, 255, 255, 255))
    # 下载箭头（右侧）
    aw = size * 0.15
    ux = size * 0.74
    uy = size * 0.22
    d.rounded_rectangle([ux - aw / 2, uy, ux + aw / 2, uy + aw * 1.7], radius=aw * 0.2,
                        fill=(255, 255, 255, 255))
    d.polygon([(ux - aw * 0.75, uy + aw * 0.9), (ux + aw * 0.75, uy + aw * 0.9), (ux, uy + aw * 1.9)],
              fill=(255, 255, 255, 255))
    return img


def main() -> None:
    here = os.path.dirname(os.path.abspath(__file__))
    out = os.path.join(here, "..", "assets")
    os.makedirs(out, exist_ok=True)
    img = build(512)
    img.save(os.path.join(out, "yt-dlpGUI.png"))
    img.resize((256, 256), Image.LANCZOS).save(
        os.path.join(out, "yt-dlpGUI.ico"), sizes=[(s, s) for s in (16, 32, 48, 64, 128, 256)])
    print("图标已生成：", os.path.abspath(out))


if __name__ == "__main__":
    main()
