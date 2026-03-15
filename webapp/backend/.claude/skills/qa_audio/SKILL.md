---
name: qa-audio
description: |
  播客剪辑质检：三层自动检测。
  Layer 1（信号层）：纯本地信号分析，无需 API Key。
  Layer 2（AI 听感）：Gemini Audio API 评估，可选。
  Layer 3（综合报告）：合并两层结果，生成评分和摘要。
  触发词：质检、QA、检查音频质量、审查剪辑
triggers:
  - "quality check"
  - "质检"
  - "QA"
  - "检查音频质量"
  - "审查剪辑"
---

# 播客剪辑质检

> 三层自动检测：信号分析 → AI 听感评估 → 综合报告

## 前置条件

- `ffmpeg` 和 `ffprobe` 已安装
- Python 包：`librosa`、`numpy`、`soundfile`
- （可选）`google-genai` 包 + `GEMINI_API_KEY` 环境变量

## Layer 1：信号分析（纯本地，无需 API Key）

```bash
python .claude/skills/qa_audio/signal_analysis.py \
  --input <音频文件> \
  --output <报告.json>
```

自动检测剪切点，运行 5 项检测：
1. 能量突变（RMS energy ratio）
2. 不自然静音（silence duration）
3. 波形不连续（ZCR jump）
4. 频谱跳变（MFCC cosine similarity）
5. 呼吸音截断（energy envelope pattern）

### 播客模式优化

播客场景下以下检测项误报太多，在报告生成时自动过滤：
- `energy_jump`：自然语气/说话人切换导致，全是假阳性
- `zcr_discontinuity`：误报太多
- `breath_truncation`：误报太多

只保留 `spectral_jump` 和 `unnatural_silence`。

## Layer 2：AI 听感评估（可选）

```bash
python .claude/skills/qa_audio/ai_listen.py \
  --input <音频文件> \
  --signal-report <layer1报告.json> \
  --output <ai报告.json>
```

需要 `GEMINI_API_KEY`（环境变量或 `.env` 文件）。

两种采样策略：
- **全局采样**：等间隔抽取 6 个 30s 片段，评估整体节奏和风格一致性
- **可疑复查**：对 Layer 1 标记的 HIGH 问题做 AI 二次确认（减少误报）

## Layer 3：综合报告

```bash
python .claude/skills/qa_audio/report_generator.py \
  --signal <layer1报告.json> \
  [--ai <layer2报告.json>] \
  --output <综合报告.json> \
  --summary <摘要.md>
```

合并两层结果，生成 10 分制评分和 Markdown 摘要，列出需要人工复听的片段。

## 完整流程示例

```bash
# Layer 1（必须）
python .claude/skills/qa_audio/signal_analysis.py \
  -i workspaces/abc123/podcast_edited.mp3 \
  -o workspaces/abc123/qa_signal.json

# Layer 2（可选，需要 GEMINI_API_KEY）
python .claude/skills/qa_audio/ai_listen.py \
  -i workspaces/abc123/podcast_edited.mp3 \
  -s workspaces/abc123/qa_signal.json \
  -o workspaces/abc123/qa_ai.json

# Layer 3（合并）
python .claude/skills/qa_audio/report_generator.py \
  -s workspaces/abc123/qa_signal.json \
  -a workspaces/abc123/qa_ai.json \
  -o workspaces/abc123/qa_report.json \
  --summary workspaces/abc123/qa_summary.md
```
