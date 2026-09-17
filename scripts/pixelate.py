#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""角色立绘/单图批量像素化 CLI（纯标准库）。

流程：解码 PNG -> 去水印 -> 角落色裁剪 -> 最近邻缩格 -> 中位切分量化
      -> 亮度差深棕描边 -> 最近邻放大，保留 RGBA 透明通道。

用法:
    python pixelate.py <输入图...> <输出目录>
    python pixelate.py <输入图...> <输出目录> --grid 64 --colors 32 --scale 8
参数:
    --grid N    横向网格数（默认 64）
    --colors N  调色板色数（默认 32）
    --scale N   放大倍数（默认 8）
    --no-outline  不描边
输出: <输出目录>/<原名>_像素化.png
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_core as pc

OUTLINE = (34, 24, 16, 255)  # 深棕描边


def process(src, outdir, grid_w=64, upscale=8, palette=32, outline=True):
    px, w, h = pc.load_png(src)
    pc.clear_watermark(px, w, h)
    box = pc.crop_content(px, w, h)
    x0, y0, x1, y1 = box
    cropped = [row[x0:x1] for row in px[y0:y1]]
    cw, chh = len(cropped[0]), len(cropped)
    gh = max(1, round(grid_w * chh / cw))
    img = pc.nearest_down(cropped, cw, chh, grid_w, gh)
    img = pc.quantize(img, palette)
    if outline:
        img = pc.add_outline(img, OUTLINE)
    img = pc.nearest_up(img, grid_w, gh, upscale)
    base = os.path.splitext(os.path.basename(src))[0]
    out = os.path.join(outdir, base + "_像素化.png")
    pc.save_png(out, img, len(img[0]), len(img))
    print(f"  {base}: 原图 {w}x{h} -> 裁剪 {cw}x{chh} -> 像素画 {len(img[0])}x{len(img)} -> {out}")
    return out


def main():
    args = sys.argv[1:]
    grid_w, upscale, palette = 64, 8, 32
    outline = True
    files = []
    i = 0
    while i < len(args):
        a = args[i]
        if a == "--grid" and i + 1 < len(args):
            grid_w = int(args[i + 1]); i += 2
        elif a == "--colors" and i + 1 < len(args):
            palette = int(args[i + 1]); i += 2
        elif a == "--scale" and i + 1 < len(args):
            upscale = int(args[i + 1]); i += 2
        elif a == "--no-outline":
            outline = False; i += 1
        else:
            files.append(a); i += 1
    if len(files) < 2:
        print(__doc__)
        return 1
    outdir = files[-1]
    os.makedirs(outdir, exist_ok=True)
    outs = []
    for src in files[:-1]:
        if not os.path.exists(src):
            print("跳过不存在:", src)
            continue
        outs.append(process(src, outdir, grid_w, upscale, palette, outline))
    print(f"完成，共 {len(outs)} 张（{grid_w}格/{palette}色/放大{upscale}）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
