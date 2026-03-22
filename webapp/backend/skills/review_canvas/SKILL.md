---
name: review-canvas
description: |
  生成播客审查画布数据。根据当前工作区中的音频、转录、修正文稿、QA 报告和剪辑结果，
  产出固定格式的 review_data.json，供右侧审查画布直接读取。
  触发词：审查画布、review data、审查稿、生成播客审查
triggers:
  - "review canvas"
  - "审查画布"
  - "review data"
  - "审查稿"
  - "生成播客审查"
---

# 审查画布数据生成

> 目标：在当前 workspace 根目录写出一个严格合法的 `review_data.json`，并与 `PodcastCut` 审查页直接兼容。

## 必须遵守

- 输出文件固定为 `review_data.json`
- 格式必须符合 `review_data.schema.json`
- 文件必须是合法 JSON，不要加 Markdown 代码块或注释
- `sentences`、`blocks`、`fineEdits` 的数据模型与 `podcastcutai` 审查画布一致
- 即使信息不完整，也要输出一个最小可用版本，不允许因为缺字段而不写文件

## 推荐输入来源

优先读取当前 workspace 中已有文件，如果某些文件不存在就跳过：

- 原始或处理后的音频：`*.mp3`, `*.m4a`, `*.wav`
- 转录：`transcript.json`
- 修正文稿：`corrected.json`
- 质检：`qa_signal.json`, `qa_ai.json`, `qa_report.json`
- 剪辑片段：`delete_segments.json`

## 目标结构

顶层字段固定为：

```json
{
  "audio_url": "output.mp3",
  "audio_duration": 111.4,
  "sentences": [],
  "blocks": [],
  "fineEdits": []
}
```

## 字段约束

### 1. sentences

- `idx`：从 0 开始连续编号
- `speaker`：说话人名，如果未知可用 `说话人1`
- `text`：该句完整文本
- `startTime` / `endTime`：秒
- `timeStr`：`m:ss`
- `words`：字词级数组，格式 `{t, s, e}`
- `isAiDeleted`：是否建议删除
- `deleteType`：可选，例如 `off_topic`, `tech_debug`, `pre_show`
- `blockId`：如果属于某个粗剪块，则引用对应 block 的 `id`
- `fineEdit`：可选，是该句最主要的一条精剪摘要

可选字段规则：
- 如果没有值，就直接省略字段
- 不要把 `blockId` 写成空字符串、0、`null` 或 `false`
- 不要把 `deleteType` 写成空字符串
- `fineEdit` 只有在该句确实有精剪建议时才出现

### 2. blocks

- 每个 block 表示一段连续删除区间
- `range` 是句子索引区间，闭区间，例如 `[3, 5]`
- `type` / `topic` / `reason` 要可读
- `duration` 用 `m:ss`
- `durationSeconds` 用秒
- `startTime` 用块起点秒数
- `enabled` 默认写 `true`

### 3. fineEdits

- 每一条代表一句中的一个精剪点
- `sentenceIdx` 指向 `sentences[idx]`
- `type` 可用 `silence`, `stutter`, `consecutive_filler`, `repeat`
- `deleteText` / `keepText` 不确定时也要保留为空字符串，不能缺字段
- `ds` / `de` 为删除时间范围
- `enabled` 默认写 `true`

## 生成策略

1. 先尽可能从现有 transcript / corrected / QA 文件提取事实数据
2. 如果缺少完整分析结果，就先给出保守版本：
   - `blocks` 可为空
   - `fineEdits` 可为空
   - `sentences` 仍然要尽量完整
3. 如果能识别明显无效段落，例如录前测试、技术调试、长静音、连续口头停顿，可以标成删除建议
4. `audio_url` 尽量写当前 workspace 里实际存在的音频文件名，优先：
   - `output.mp3`
   - `podcast_edited.mp3`
   - `upload.mp3`
   - 其他实际存在的音频文件

## 生成后校验

写完后必须再次读取并验证 `review_data.json`：

```bash
python .claude/skills/review_canvas/validate_review_data.py review_data.json
```

如果校验失败，继续修正直到合法。
