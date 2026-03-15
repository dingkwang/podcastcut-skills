---
name: cut-audio
description: 音频剪辑。根据 delete_segments.json 删除指定片段，自适应淡入淡出，可选说话人音量对齐。触发词：剪辑、cut、编辑音频
triggers:
  - "cut audio"
  - "剪辑音频"
  - "剪辑"
  - "编辑音频"
---

# 音频剪辑

> 根据删除片段列表一键剪辑，自适应淡入淡出 + 可选说话人音量对齐

## 前置条件

- `ffmpeg` 和 `ffprobe` 已安装
- 音频文件（mp3, wav, m4a）
- `delete_segments.json` — 包含 `{start, end}` 的数组

## 用法

```bash
python .claude/skills/cut_audio/cut_audio.py <输出文件名.mp3> <音频文件> <delete_segments.json> [--speakers-json subtitles_words.json] [--no-fade]
```

### 参数

- `输出文件名` (可选): 输出文件名（默认: `播客_精剪版_v1.mp3`）
- `音频文件` (可选): 输入音频路径
- `delete_segments.json` (可选): 要删除的片段列表
- `--speakers-json` (可选): 字级转录 JSON，用于说话人音量对齐
- `--no-fade` (可选): 禁用自适应淡入淡出，仅用 3ms 微 fade

### 特性

- 先解码为 WAV 再切割，确保采样级精确（MP3 `-c copy` 只有帧级精度 ~26ms）
- 每个切点根据片段时长自动加淡入淡出
- 可选：检测各说话人平均响度，补偿音量差异（最大 +6dB）

### delete_segments.json 格式

```json
[
  {"start": 10.5, "end": 15.2},
  {"start": 30.0, "end": 45.8}
]
```

也支持包装格式：`{"segments": [...], "editState": {...}}`

### 示例

```bash
python .claude/skills/cut_audio/cut_audio.py \
  workspaces/abc123/podcast_edited.mp3 \
  workspaces/abc123/upload.mp3 \
  workspaces/abc123/delete_segments.json
```
