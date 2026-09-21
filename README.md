# Pixel Art Action Frames

游戏像素美术资产管线：把角色立绘一键转成复古像素画，或把攻击动作序列帧做成**透明底像素图集 + JSON 帧清单 + 循环动画 GIF**，开箱即用、零依赖（纯 Python 标准库），可直接导入 Godot / Unity 等引擎。

## 特性

- 🎨 **角色像素化**：去水印 → 自动裁剪 → 最近邻缩格 → 中位切分量化（32 色）→ 深棕描边 → 放大输出，保留 RGBA 透明通道
- ⚔️ **攻击动作帧管线**：6 帧动作序列 → flood-fill 去背景透明化 → 统一裁剪 → 像素化 → 透明单帧 + 横排图集 + JSON 帧清单
- 🎞️ **透明动画 GIF**：自研纯标准库 GIF89a 编码器（全局色表 + 专用透明索引 + 每帧 disposal=2），**播放无残影叠加**
- 📦 **引擎友好**：输出 `pixel_art_batch_sprite_sheet` 清单（`cols/rows/cell_w/cell_h/frame_ms/loop/alpha/frames[i].rect`），按 rect 直接切图
- 🧩 **零依赖**：全部脚本只用 Python 标准库，任何机器可直接运行

## 2026-09-21 更新

新增 4 个工具脚本，和 Web 版 Pixelizer 对齐：

| 脚本 | 功能 |
|---|---|
| `split_sheet.py` | 把一张 sprite sheet 大图按 cols×rows 自动切成单帧 PNG |
| `video_to_frames.py` | 视频抽帧（依赖 ffmpeg），按采样帧率导出 PNG 序列 |
| `palette_lock.py` | 色板提取/导出 .gpl/批量锁定色板（多帧色调统一） |
| `chroma_key.py` | 绿幕/白地/黑地一键去背（含溢色抑制） |

## 快速开始

```bash
# 1. 角色像素化：输入图... + 输出目录
python scripts/pixelate.py assets/hero.png out/ --grid 64 --colors 32 --scale 8

# 2. 攻击动作帧：6 张 PNG（frame_1.png..frame_6.png）→ 去背景+像素化+图集+JSON
python scripts/transparent_frames.py raw_frames/ out/ attack

# 3. 透明动画 GIF：读 out/attack_1..6.png → out/attack_sheet.gif
python scripts/build_gif.py out/ attack

# 4. 拆分 sprite sheet
python scripts/split_sheet.py walk_sheet.png --cols 4 --rows 4 --out frames/

# 5. 视频抽帧
python scripts/video_to_frames.py walk.mp4 --fps 8 --out frames/

# 6. 色板锁定
python scripts/palette_lock.py extract frame_000.png --palette palette.gpl
python scripts/palette_lock.py batch frames/ --out frames_q/

# 7. 绿幕去背
python scripts/chroma_key.py green_screen.png --mode green --out transparent.png
```

## 目录结构

```
pixel-art-action-frames/
├── scripts/
│   ├── pixel_core.py            # 核心算法库（PNG 编解码/去水印/flood-fill去背景/量化/描边/色键/色板）
│   ├── pixelate.py              # 角色/单图批量像素化 CLI
│   ├── transparent_frames.py    # 6帧动作序列 → 去背景+像素化+图集+JSON
│   ├── build_gif.py             # 透明动画 GIF 编码器（disposal=2 + 全局色表）
│   ├── split_sheet.py           # Sprite Sheet 拆分器（cols×rows → 单帧）
│   ├── video_to_frames.py       # 视频抽帧（ffmpeg）
│   ├── palette_lock.py          # 色板提取/导出/批量锁定
│   └── chroma_key.py            # 绿幕/白地/黑地去背
└── examples/
    ├── characters/              # 4 个角色的像素化示例（orbs/bone/palm/ghost）
    └── orbs/                    # 攻击动作帧示例：图集 + JSON 清单 + 动画 GIF
```

## 动作帧流程

| 步骤 | 说明 | 输出 |
|---|---|---|
| 1 | 用图像生成工具按角色原图生成 6 帧（起手→蓄力→挥击→命中→收势→归位） | frame_1..6.png |
| 2 | `transparent_frames.py`：flood-fill 去背景 + 像素化 + 打包 | 单帧 + 图集 + JSON |
| 3 | `build_gif.py`：合成透明循环动画 | GIF（120ms/帧） |

## 引擎对接

清单格式（`*_sheet.json`）：

```json
{
  "type": "pixel_art_batch_sprite_sheet",
  "sheet": "orbs_sheet.png",
  "cols": 6, "rows": 1,
  "cell_w": 512, "cell_h": 504,
  "frame_ms": 120, "loop": true, "alpha": true,
  "frames": [{ "name": "orbs_1", "index": 0, "rect": [0, 0, 512, 504] }, ...]
}
```

- **Godot**：`AtlasTexture` + `SpriteFrames` 按 `rect` 建帧，`frame_ms` 设帧时长
- **Unity**：`SpriteEditor` 按 `cell_w/cell_h` 切片，`AnimationClip` 设采样率

## 示例

`examples/characters/` 四个 Q 版角色的像素化效果，`examples/orbs/` 完整动作帧资产（图集/清单/GIF 可预览播放）。

## 许可

MIT License。生成内容（示例角色图、动作帧）仅供演示。
