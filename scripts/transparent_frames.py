#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""攻击动作帧：去背景透明化 + 像素化 + 横排图集 + JSON 清单（纯标准库）。

流程：6 帧 PNG（frame_1..6.png）-> 去水印 -> flood-fill 去背景
      -> 六帧 alpha 包围盒并集裁剪 -> 64格/32色/深棕描边像素化
      -> 透明底单帧 + 横排图集 + JSON 清单。

用法:
    python transparent_frames.py <raw_png_dir> <out_dir> <prefix>
    python transparent_frames.py <raw_png_dir> <out_dir> <prefix> --grid 64 --colors 32 --scale 8
输入: <raw_png_dir>/frame_1.png .. frame_6.png（RGBA/RGB PNG）
输出: <out_dir>/<prefix>_1..6.png、<prefix>_sheet.png、<prefix>_sheet.json
      （type=pixel_art_batch_sprite_sheet, cols=6, rows=1, frame_ms=120, loop, alpha:true）
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pixel_core as pc

GRID_W = 64
UPSCALE = 8
PALETTE = 32
OUTLINE = (34, 24, 16, 255)
INNER = 400    # 到背景色平方距离 <= 400 (dist 20) 视为背景候选（flood 扩展）
OUTER = 10000  # 邻接背景区域的像素平方距离 <= 10000 (dist 100) 单层剥除（背景噪声带）
FRAME_MS = 120


def parse_args(args):
    out = {
        "raw_dir": args[0], "out_dir": args[1], "prefix": args[2],
        "grid_w": GRID_W, "scale": UPSCALE, "colors": PALETTE,
    }
    i = 3
    while i < len(args):
        if args[i] == "--grid" and i + 1 < len(args):
            out["grid_w"] = int(args[i + 1]); i += 2
        elif args[i] == "--colors" and i + 1 < len(args):
            out["colors"] = int(args[i + 1]); i += 2
        elif args[i] == "--scale" and i + 1 < len(args):
            out["scale"] = int(args[i + 1]); i += 2
        else:
            i += 1
    return out


def main():
    if len(sys.argv) < 4:
        print(__doc__)
        return 1
    a = parse_args(sys.argv[1:])
    raw_dir, out_dir, prefix = a["raw_dir"], a["out_dir"], a["prefix"]
    os.makedirs(out_dir, exist_ok=True)
    paths = [os.path.join(raw_dir, f"frame_{i}.png") for i in range(1, 7)]
    loaded, boxes, bgs = [], [], []
    for p in paths:
        px, w, h = pc.load_png(p)
        pc.clear_watermark(px, w, h)
        bg = pc.remove_bg(px, w, h, INNER, OUTER)
        box = pc.alpha_box(px, w, h)
        loaded.append((px, w, h))
        boxes.append(box)
        bgs.append(bg)
        print(f"  {os.path.basename(p)}: bg={bg} bbox={box}")

    x0 = min(b[0] for b in boxes)
    y0 = min(b[1] for b in boxes)
    x1 = max(b[2] for b in boxes)
    y1 = max(b[3] for b in boxes)
    uw, uh = x1 - x0, y1 - y0
    gh = max(1, round(a["grid_w"] * uh / uw))
    print(f"统一裁剪框: ({x0},{y0})-({x1},{y1}) {uw}x{uh} -> 网格 {a['grid_w']}x{gh} 放大x{a['scale']}")

    processed = []
    for (px, w, h) in loaded:
        crop = [row[x0:x1] for row in px[y0:y1]]
        img = pc.nearest_down(crop, uw, uh, a["grid_w"], gh)
        img = pc.quantize(img, a["colors"])
        img = pc.add_outline(img, OUTLINE)
        img = pc.nearest_up(img, a["grid_w"], gh, a["scale"])
        processed.append(img)

    out_w, out_h = len(processed[0][0]), len(processed[0])
    for i, img in enumerate(processed, 1):
        pc.save_png(os.path.join(out_dir, f"{prefix}_{i}.png"), img, out_w, out_h)

    sheet = []
    for y in range(out_h):
        row = []
        for img in processed:
            row.extend(img[y])
        sheet.append(row)
    pc.save_png(os.path.join(out_dir, f"{prefix}_sheet.png"), sheet, out_w * 6, out_h)

    frames = [
        {"name": f"{prefix}_{i}", "index": i - 1, "rect": [(i - 1) * out_w, 0, out_w, out_h]}
        for i in range(1, 7)
    ]
    manifest = {
        "type": "pixel_art_batch_sprite_sheet",
        "sheet": f"{prefix}_sheet.png",
        "cols": 6, "rows": 1,
        "cell_w": out_w, "cell_h": out_h,
        "frame_ms": FRAME_MS,
        "loop": True,
        "alpha": True,
        "frames": frames,
    }
    with open(os.path.join(out_dir, f"{prefix}_sheet.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent="\t")

    print(f"单帧 {out_w}x{out_h} x6 -> 图集 {out_w * 6}x{out_h}（透明底）")
    print(f"输出: {out_dir}  前缀: {prefix}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
