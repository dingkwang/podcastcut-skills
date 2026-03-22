---
name: voice-clone
description: |
  语音克隆 + 播客生成完整流程。
  上传音频 → 转录 → 修正文稿 → 提取声音样本 → 克隆声音模型 → TTS 合成 → 合并成品音频。
  全自动执行，无需用户逐步操作。
  触发词：语音克隆、声音克隆、生成播客、克隆声音
triggers:
  - "voice clone"
  - "语音克隆"
  - "声音克隆"
  - "克隆声音"
  - "生成播客"
---

# 语音克隆 + 播客生成

> 从一段音频自动完成：转录 → 修正 → 提取样本 → 克隆声音 → TTS 合成 → 合并成品

## 前置条件

- `OPENROUTER_API_KEY` 环境变量（用于转录和文稿修正）
- `FISH_API_KEY` 环境变量（用于声音克隆和 TTS）
- `ffmpeg` 和 `ffprobe` 已安装

## 完整流程

用户只需提供音频文件和说话人信息，agent 自动按顺序执行以下步骤：

```
音频文件 + 说话人信息
    ↓
Step 1: 转录（Gemini 3 Flash via OpenRouter）
    ↓
Step 2: 修正文稿（LLM 清理语气词、口误、识别错误）
    ↓
Step 3: 提取声音样本（每个说话人 ~15s 最佳片段）
    ↓
Step 4: 创建声音克隆模型（Fish Audio，每个说话人一个模型）
    ↓
Step 5: TTS 批量合成（用克隆声音朗读修正后的文稿）
    ↓
Step 6: 合并音频片段 → 成品播客音频
```

## 运行方式

所有 Python 脚本都必须通过 backend 项目的虚拟环境执行，不要使用系统 `python` / `python3` / `pip`：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python <脚本路径> ...
```

例如：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/transcribe.py \
  webapp-e2e-40s.m4a --speakers 2
```

## Step 1: 转录

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/transcribe.py \
  <音频文件> [--speakers N]
```

- 使用 Gemini 3 Flash 转录，输出 `transcript.json`
- `--speakers N`：说话人数量（默认 2）

输出格式：
```json
{"sentences": [{"text": "内容", "start": 0.0, "end": 3.5, "spk": 0}, ...]}
```

## Step 2: 修正文稿

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/correct.py \
  <transcript.json> --speakers '{"0":"Alice","1":"Bob"}'
```

- 删除语气词（呃、嗯、啊）、修正口误和重复、修正 ASR 识别错误
- 输出 `corrected.json`

## Step 3: 提取声音样本

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/extract.py \
  <音频文件> <transcript.json> <输出目录> [--duration 15]
```

- 从原始音频中按说话人提取最佳片段，每人 ~15 秒
- 输出 WAV 样本文件 + `samples_manifest.json`

## Step 4: 创建声音克隆模型

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/create_model.py \
  --name "说话人名" --samples "sample1.wav,sample2.wav"
```

- 上传样本到 Fish Audio，创建克隆模型
- 输出模型 ID（后续 TTS 使用）
- 注意：Fish Audio 免费版最多 3 个模型，脚本会自动删旧模型腾位

## Step 5: TTS 批量合成

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/tts_batch.py \
  <corrected.json> <voice_models.json> <输出目录>
```

- `voice_models.json` 格式：`{"Alice": "model_id_1", "Bob": "model_id_2"}`
- 为每个文稿片段生成对应说话人的 TTS 音频
- 输出 `segment_001.mp3`, `segment_002.mp3`, ...

单条合成：
```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/tts.py \
  --text "要合成的文字" --model-id <模型ID> --output <输出.mp3>
```

## Step 6: 合并音频

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/voice_clone/merge.py \
  <片段目录> <输出.mp3> [--pattern "segment_*.mp3"]
```

- 按文件名顺序拼接所有片段
- 输出最终播客音频

## 工作目录结构

每次执行会在 workspace 下创建：
```
workspaces/<session_id>/
├── upload.mp3              # 原始音频
├── transcript.json         # Step 1 转录结果
├── corrected.json          # Step 2 修正文稿
├── samples/                # Step 3 声音样本
│   ├── speaker_0_sample_0.wav
│   ├── speaker_1_sample_0.wav
│   └── samples_manifest.json
├── voice_models.json       # Step 4 模型 ID 映射
├── tts_output/             # Step 5 TTS 片段
│   ├── segment_001.mp3
│   ├── segment_002.mp3
│   └── ...
└── output.mp3              # Step 6 最终成品
```

## 示例对话

```
用户: 帮我克隆这段音频里的声音，重新生成播客
Agent: 收到，开始处理：
  1. 转录中...（Gemini 3 Flash）
  2. 修正文稿...（删除语气词、修正口误）
  3. 提取声音样本...（Speaker 0: 3 段, Speaker 1: 2 段）
  4. 创建克隆模型...（Speaker 0 → model_abc, Speaker 1 → model_def）
  5. TTS 合成中...（32 段文稿 → 32 个音频片段）
  6. 合并成品...
  ✅ 完成！最终音频：workspaces/xxx/output.mp3
```
