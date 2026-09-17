# 示例产物

## characters/ — 角色像素化

4 个 Q 版角色的像素化输出（64 格 / 32 色 / 深棕描边 / 放大 8，透明底）：

| 文件 | 角色 | 原图来源 |
|---|---|---|
| `orbs.png` | 捧珠少女（深蓝汉服黑羽翼） | TapTap 发布素材 |
| `bone.png` | 持骨少年（米色和服黑短发） | TapTap 发布素材 |
| `palm.png` | 触角少女（绿紫渐变发） | TapTap 发布素材 |
| `ghost.png` | 黑焰幽灵（白瞳短剑） | TapTap 发布素材 |

复现：`python scripts/pixelate.py <原始图> examples/characters/`

## orbs/ — 攻击动作帧完整资产

捧珠少女「灵力球」6 帧攻击序列的完整输出（透明底）：

| 文件 | 说明 |
|---|---|
| `orbs_sheet.png` | 横排 6 帧图集（3072×504） |
| `orbs_sheet.json` | 帧清单（cols=6, cell=512×504, 120ms/帧, loop, alpha） |
| `orbs_sheet.gif` | 透明循环动画（120ms/帧，无残影叠加） |

复现：`python scripts/transparent_frames.py <6帧PNG目录> examples/orbs/ orbs` 后接 `python scripts/build_gif.py examples/orbs/ orbs`

> 示例角色图与动作帧为 AI 生成内容，仅供演示；实际游戏资产请替换为自有素材。
