---
name: mix-highlights
description: 金句混音。将高亮片段叠加在连续背景音乐上，人声出现时音乐自动降低。触发词：混音、片头音乐、金句背景音乐
triggers:
  - "mix highlights"
  - "混合高亮"
  - "片头音乐"
  - "金句背景音乐"
---

# 金句片段 + 背景音乐混合

> 将高亮片段叠加在连续背景音乐上，人声出现时音乐自动降低

## 前置条件

- `ffmpeg` 和 `ffprobe` 已安装
- 主题曲/背景音乐文件（mp3/wav）
- 一个或多个高亮片段文件（mp3/wav）

## 用法

```bash
python .claude/skills/mix_highlights/mix_highlights.py \
  --theme <音乐文件> \
  --clips <片段1> <片段2> <片段3> \
  --output <输出.wav> \
  [选项]
```

### 参数

- `--theme` (必需): 背景音乐文件路径
- `--clips` (必需): 高亮片段文件路径列表
- `--output` (可选): 输出文件路径（默认: `intro_complete.wav`）
- `--intro-dur` (可选): 片头纯音乐时长，秒（默认: 10）
- `--gap-dur` (可选): 片段间过渡时长，秒（默认: 5）
- `--outro-dur` (可选): 尾声过渡到正文时长，秒（默认: 9）
- `--music-vol` (可选): 人声时背景音乐音量 0-1（默认: 0.08）
- `--gap-vol` (可选): 过渡段音乐音量 0-1（默认: 1.0）
- `--voice-gain` (可选): 人声增益倍数（默认: 2.0）
- `--fade-transition` (可选): 音乐升降渐变时长，秒（默认: 1.5）
- `--theme-start` (可选): 主题曲截取起点，秒（默认: 0）

### 关键设计

- 使用 `amerge+pan` 混合（**禁止用 `amix`**，它会归一化导致人声听不见）
- 一条连续音乐轨道 + `volume=eval=frame` 动态控制音量
- 1.5s 平滑渐变，人声区域音乐降到 8%

### 输出

- 混合后的 WAV 文件
- 时间线 JSON 文件（`*_timeline.json`），用于时间戳偏移计算

### 示例

```bash
python .claude/skills/mix_highlights/mix_highlights.py \
  --theme workspaces/abc123/theme_song.mp3 \
  --clips workspaces/abc123/clip1.mp3 workspaces/abc123/clip2.mp3 \
  --output workspaces/abc123/intro_complete.wav \
  --music-vol 0.08 --voice-gain 2.0
```
