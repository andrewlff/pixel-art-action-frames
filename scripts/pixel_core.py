#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""pixel-art-action-frames 核心算法库（纯标准库，零依赖）。

合并自 Godot/Unity 像素化工具的 Python 等价实现与攻击动作帧透明化管线：
- PNG 解码/编码（8bit，gray/RGB/RGBA/gray-alpha）
- 去水印 / 内容裁剪 / flood-fill 去背景
- 最近邻缩小、中位切分量化、亮度差描边、最近邻放大（保留 RGBA 透明通道）
"""
import os
import struct
import zlib
from collections import deque

# ---------------------------------------------------------------- PNG 编解码
def _png_chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(
        ">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def save_png(path: str, pixels, w: int, h: int) -> None:
    """pixels: list[list[(r,g,b,a)]]，各通道 0-255，输出 RGBA8 PNG。"""
    raw = bytearray()
    for row in pixels:
        raw.append(0)  # filter: None
        for r, g, b, a in row:
            raw += bytes((r, g, b, a))
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 6, 0, 0, 0)
    png = (b"\x89PNG\r\n\x1a\n" + _png_chunk(b"IHDR", ihdr)
           + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 9))
           + _png_chunk(b"IEND", b""))
    with open(path, "wb") as f:
        f.write(png)


def load_png(path):
    """纯 Python 解码 PNG（8bit，color type 0/2/3/4/6），返回 (pixels, w, h)。
    pixels 统一为 RGBA 元组列表。"""
    data = open(path, "rb").read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "不是 PNG: " + path
    pos = 8
    w = h = bit = ct = interlace = 0
    idat = b""
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        tag = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + ln]
        if tag == b"IHDR":
            w, h, bit, ct, _, _, interlace = struct.unpack(">IIBBBBB", body)
        elif tag == b"IDAT":
            idat += body
        pos += 12 + ln
    if interlace != 0:
        raise ValueError("暂不支持 interlaced PNG: " + path)
    if bit != 8:
        raise ValueError("暂不支持非 8bit PNG: " + path)
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[ct]
    raw = zlib.decompress(idat)
    stride = w * channels
    px = []
    prev = bytearray(stride)
    p = 0
    for _ in range(h):
        f = raw[p]; p += 1
        line = bytearray(raw[p:p + stride]); p += stride
        if f == 1:
            for x in range(channels, stride):
                line[x] = (line[x] + line[x - channels]) & 0xFF
        elif f == 2:
            for x in range(stride):
                line[x] = (line[x] + prev[x]) & 0xFF
        elif f == 3:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                line[x] = (line[x] + ((left + prev[x]) >> 1)) & 0xFF
        elif f == 4:
            for x in range(stride):
                left = line[x - channels] if x >= channels else 0
                ul = prev[x - channels] if x >= channels else 0
                a, b, c = left, prev[x], ul
                pv = a + b - c
                pa, pb, pc = abs(pv - a), abs(pv - b), abs(pv - c)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else c)
                line[x] = (line[x] + pr) & 0xFF
        row = [tuple(line[x * channels:(x + 1) * channels]) for x in range(w)]
        if channels == 3:
            row = [(r, g, b, 255) for (r, g, b) in row]
        elif channels == 1:
            row = [(v, v, v, 255) for (v,) in row]
        elif channels == 2:
            row = [(v, v, v, a) for (v, a) in row]
        px.append(row)
        prev = line
    return px, w, h


# ---------------------------------------------------------------- 去水印与裁剪
def clear_watermark(px, w, h, x0f=0.78, y0f=0.90):
    """把右下角水印区的浅灰文字像素替换为背景色。
    规则：亮色（luma>=120）且低饱和（max-min<=60）的像素视为水印文字。"""
    bg = px[0][0][:3]
    x0, y0 = int(w * x0f), int(h * y0f)
    for y in range(y0, h):
        for x in range(x0, w):
            c = px[y][x]
            luma = sum(c[:3]) / 3
            sat = max(c[:3]) - min(c[:3])
            if luma >= 120 and sat <= 60:
                px[y][x] = (bg[0], bg[1], bg[2], 255)


def crop_content(px, w, h, skip_watermark=True):
    """以角落像素为背景色，返回内容包围盒（排除右下角水印区），留 4% 边距。"""
    bg = px[0][0][:3]
    thresh = 40
    x0, y0, x1, y1 = w, h, -1, -1
    wm_x = int(w * 0.76)
    wm_y = int(h * 0.89)
    for y in range(h):
        for x in range(w):
            if skip_watermark and x >= wm_x and y >= wm_y:
                continue
            c = px[y][x]
            d = sum((c[i] - bg[i]) ** 2 for i in range(3))
            if d > thresh * thresh:
                x0 = min(x0, x); y0 = min(y0, y)
                x1 = max(x1, x); y1 = max(y1, y)
    if x1 < x0:
        return 0, 0, w, h
    margin = int(0.04 * max(1, min(w, h)))
    x0 = max(0, x0 - margin); y0 = max(0, y0 - margin)
    x1 = min(w, x1 + 1 + margin); y1 = min(h, y1 + 1 + margin)
    return x0, y0, x1, y1


# ---------------------------------------------------------------- flood-fill 去背景
def top_color(px, w, h):
    """背景色估计：按 32 级量化格子统计众数簇（JPEG 噪声分散单色，聚簇后背景面积最大），
    再取簇内平均色。黑色角色块不与浅色背景同簇。"""
    cells = {}
    sums = {}
    for row in px:
        for c in row:
            q = (c[0] >> 5, c[1] >> 5, c[2] >> 5)
            cells[q] = cells.get(q, 0) + 1
            s = sums.get(q)
            if s is None:
                s = sums[q] = [0, 0, 0]
            s[0] += c[0]
            s[1] += c[1]
            s[2] += c[2]
    q = max(cells, key=cells.get)
    n = cells[q]
    s = sums[q]
    return (s[0] // n, s[1] // n, s[2] // n)


def remove_bg(px, w, h, inner=400, outer=10000):
    """flood-fill 去背景：
    1) 从四边开始，扩展"距离背景色 <= sqrt(inner)"的连通区域 -> alpha=0；
    2) 与背景区域 4-邻接、且距离 <= sqrt(outer) 的像素单层剥除（清 JPEG 噪声带）；
    3) 角色内部浅色（眼睛/刀光等）不与边缘连通，天然保留。
    返回估计的背景色。"""
    bg = top_color(px, w, h)
    visited = [bytearray(w) for _ in range(h)]
    q = deque()

    def seed(x, y):
        c = px[y][x]
        d = sum((c[i] - bg[i]) ** 2 for i in range(3))
        if d <= inner and not visited[y][x]:
            visited[y][x] = 1
            q.append((x, y))

    for x in range(w):
        seed(x, 0)
        seed(x, h - 1)
    for y in range(h):
        seed(0, y)
        seed(w - 1, y)

    while q:
        x, y = q.popleft()
        px[y][x] = (0, 0, 0, 0)
        for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nx, ny = x + dx, y + dy
            if 0 <= nx < w and 0 <= ny < h and not visited[ny][nx]:
                c = px[ny][nx]
                d = sum((c[i] - bg[i]) ** 2 for i in range(3))
                if d <= inner:
                    visited[ny][nx] = 1
                    q.append((nx, ny))

    # 单层剥除：邻接背景区域的背景噪声带
    for y in range(h):
        for x in range(w):
            if visited[y][x]:
                continue
            c = px[y][x]
            d = sum((c[i] - bg[i]) ** 2 for i in range(3))
            if d > outer:
                continue
            touch = False
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx, ny = x + dx, y + dy
                if 0 <= nx < w and 0 <= ny < h and visited[ny][nx]:
                    touch = True
                    break
            if touch:
                px[y][x] = (0, 0, 0, 0)
    return bg


def alpha_box(px, w, h):
    """非透明像素包围盒（含 2% 边距）。"""
    x0, y0, x1, y1 = w, h, -1, -1
    for y in range(h):
        row = px[y]
        for x in range(w):
            if row[x][3] > 0:
                if x < x0: x0 = x
                if x > x1: x1 = x
                if y < y0: y0 = y
                if y > y1: y1 = y
    if x1 < x0:
        return 0, 0, w, h
    m = max(2, int(0.02 * min(w, h)))
    return max(0, x0 - m), max(0, y0 - m), min(w, x1 + 1 + m), min(h, y1 + 1 + m)


# ---------------------------------------------------------------- 像素化算法
def nearest_down(pixels, w, h, gw, gh):
    out = [[(0, 0, 0, 0)] * gw for _ in range(gh)]
    for y in range(gh):
        sy = min(h - 1, int(y * h / gh))
        for x in range(gw):
            sx = min(w - 1, int(x * w / gw))
            out[y][x] = pixels[sy][sx]
    return out


def nearest_up(pixels, gw, gh, up):
    out_w, out_h = gw * up, gh * up
    out = [[(0, 0, 0, 0)] * out_w for _ in range(out_h)]
    for y in range(out_h):
        sy = y // up
        for x in range(out_w):
            out[y][x] = pixels[sy][x // up]
    return out


def _channel(c, i):
    return c[i] / 255.0


def luma(c):
    return 0.299 * c[0] / 255.0 + 0.587 * c[1] / 255.0 + 0.114 * c[2] / 255.0


def _box_ranges(box):
    mn = [1.0, 1.0, 1.0]
    mx = [0.0, 0.0, 0.0]
    for c in box:
        for i in range(3):
            v = _channel(c, i)
            mn[i] = min(mn[i], v)
            mx[i] = max(mx[i], v)
    return [mx[i] - mn[i] for i in range(3)]


def _split_box(box):
    ranges = _box_ranges(box)
    ch = ranges.index(max(ranges))
    sbox = sorted(box, key=lambda c: _channel(c, ch))
    mid = len(sbox) // 2
    return sbox[:mid], sbox[mid:]


def _box_average(box):
    n = len(box)
    return (round(sum(c[0] for c in box) / n),
            round(sum(c[1] for c in box) / n),
            round(sum(c[2] for c in box) / n),
            round(sum(c[3] for c in box) / n))


def quantize(pixels, max_colors):
    """中位切分量化：把不透明像素聚成 <= max_colors 个盒子，取盒均值作调色板。"""
    h, w = len(pixels), len(pixels[0])
    opaque = [pixels[y][x] for y in range(h) for x in range(w) if pixels[y][x][3] > 127]
    if len(opaque) < 2:
        return pixels
    boxes = [opaque]
    while len(boxes) < max_colors:
        widest, widest_i, widest_r = None, -1, -1.0
        for i, b in enumerate(boxes):
            r = max(_box_ranges(b))
            if r > widest_r:
                widest_r, widest_i, widest = r, i, b
        if widest_i < 0 or len(widest) < 2:
            break
        left, right = _split_box(widest)
        boxes[widest_i:widest_i + 1] = [left, right]
    palette = [_box_average(b) for b in boxes]
    out = [[(0, 0, 0, 0)] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            c = pixels[y][x]
            if c[3] <= 127:
                continue
            best, best_d = palette[0], sum((c[i] - palette[0][i]) ** 2 for i in range(3))
            for p in palette[1:]:
                d = sum((c[i] - p[i]) ** 2 for i in range(3))
                if d < best_d:
                    best_d, best = d, p
            out[y][x] = (best[0], best[1], best[2], c[3])
    return out


def add_outline(pixels, line_color=(34, 24, 16, 255), threshold=0.30):
    """亮度差描边：像素与其右/下/右下邻接亮度差超过阈值时描深棕色。"""
    h, w = len(pixels), len(pixels[0])
    src = [row[:] for row in pixels]
    for y in range(h):
        for x in range(w):
            c = src[y][x]
            if c[3] <= 127:
                continue
            l = luma(c)
            edge = False
            if x + 1 < w and abs(luma(src[y][x + 1]) - l) > threshold:
                edge = True
            elif y + 1 < h and abs(luma(src[y + 1][x]) - l) > threshold:
                edge = True
            elif x + 1 < w and y + 1 < h and abs(luma(src[y + 1][x + 1]) - l) > threshold:
                edge = True
            if edge:
                pixels[y][x] = (line_color[0], line_color[1], line_color[2], max(c[3], line_color[3]))
    return pixels


# ---------------------------------------------------------------- 色键去背
def chroma_key(px, w, h, key_color=(0, 255, 0), tolerance=25, spill_suppress=True):
    """绿幕/色键去背：绿通道明显大于红蓝的像素变透明，可选溢色抑制。
    key_color: (r,g,b) 要去除的背景色。tolerance: 容差。"""
    kr, kg, kb = key_color
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[y][x]
            if a == 0:
                continue
            d = ((r - kr) ** 2 + (g - kg) ** 2 + (b - kb) ** 2) ** 0.5
            if d < tolerance * 4:
                px[y][x] = (r, g, b, 0)
            elif spill_suppress and g > r + 10 and g > b + 10:
                # 溢色抑制：把绿色压到红蓝的最大值
                m = max(r, b)
                px[y][x] = (r, m, b, a)
    return px


def remove_flat_bg(px, w, h, mode="white", threshold=200):
    """纯色背景去除：mode='white' 白地，'black' 黑地。"""
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[y][x]
            if a == 0:
                continue
            if mode == "white" and r > threshold and g > threshold and b > threshold:
                px[y][x] = (r, g, b, 0)
            elif mode == "black" and r < (255 - threshold) and g < (255 - threshold) and b < (255 - threshold):
                px[y][x] = (r, g, b, 0)
    return px


# ---------------------------------------------------------------- 色板锁定
def extract_palette(px, w, h):
    """从像素中提取唯一色板（不透明像素）。返回 [(r,g,b), ...]。"""
    seen = set()
    palette = []
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[y][x]
            if a <= 127:
                continue
            key = (r, g, b)
            if key not in seen:
                seen.add(key)
                palette.append((r, g, b))
    return palette


def quantize_to_palette(px, w, h, palette):
    """把像素量化到指定色板（最近色匹配），不透明像素保留 alpha。"""
    out = [[(0, 0, 0, 0)] * w for _ in range(h)]
    for y in range(h):
        for x in range(w):
            r, g, b, a = px[y][x]
            if a <= 127:
                continue
            best, best_d = palette[0], float("inf")
            for p in palette:
                d = (r - p[0]) ** 2 + (g - p[1]) ** 2 + (b - p[2]) ** 2
                if d < best_d:
                    best_d, best = d, p
            out[y][x] = (best[0], best[1], best[2], a)
    return out


def save_gpl(path, palette, name="Pixelizer Palette"):
    """导出 GIMP .gpl 调色板文件。"""
    lines = ["GIMP Palette", f"Name: {name}", "#"]
    for r, g, b in palette:
        lines.append(f"  {r:3d}   {g:3d}   {b:3d}")
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ---------------------------------------------------------------- Sprite Sheet 拆分
def split_sheet(path, cols, rows, out_dir, prefix="frame"):
    """把一张 sprite sheet 大图按 cols×rows 切成单帧 PNG。"""
    px, w, h = load_png(path)
    fw, fh = w // cols, h // rows
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    idx = 0
    for r in range(rows):
        for c in range(cols):
            frame = [[px[y][x] for x in range(c * fw, (c + 1) * fw)]
                     for y in range(r * fh, (r + 1) * fh)]
            out_path = os.path.join(out_dir, f"{prefix}_{idx:03d}.png")
            save_png(out_path, frame, fw, fh)
            paths.append(out_path)
            idx += 1
    return paths, fw, fh
