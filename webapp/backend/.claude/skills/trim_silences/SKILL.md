---
name: trim-silences
description: 静音裁剪。将音频中超过阈值的停顿裁剪到目标时长。触发词：裁剪静音、trim、去停顿
triggers:
  - "trim silences"
  - "裁剪静音"
  - "去停顿"
  - "去掉长停顿"
---

# 静音裁剪

> 检测并缩短所有超过阈值的静音段，适合在 cut_audio 之后使用

## 前置条件

- `ffmpeg` 和 `ffprobe` 已安装
- 音频文件（mp3, wav, m4a）

## 用法

```bash
python .claude/skills/trim_silences/trim_silences.py <输入.mp3> [输出.mp3] [--threshold 0.8] [--target 0.6] [--noise -30]
```

### 参数

- `输入.mp3` (必需): 输入音频文件
- `输出.mp3` (可选): 输出路径（默认: `<输入>_trimmed.<扩展名>`）
- `--threshold T` (可选): 检测阈值，超过 T 秒的静音会被裁剪（默认: 0.8）
- `--target T` (可选): 目标时长，每段静音裁剪到 T 秒（默认: 0.6）
- `--noise N` (可选): 静音检测噪声阈值 dB（默认: -30）

### 原理

1. FFmpeg `silencedetect` 扫描所有超过阈值的静音段
2. 每段静音保留 target 秒（前后各 target/2 秒），裁掉多余部分
3. 用 `atrim` + `concat` 拼接所有保留段
4. 编码为 MP3

### 典型场景

- `cut_audio` 出成品后，删除内容前后的短静音合并成长停顿
- 直接用成品音频扫一遍比反推 delete_segments 更简单可靠

### 示例

```bash
python .claude/skills/trim_silences/trim_silences.py \
  workspaces/abc123/podcast_edited.mp3 \
  workspaces/abc123/podcast_final.mp3 \
  --threshold 1.0 --target 0.5
```
