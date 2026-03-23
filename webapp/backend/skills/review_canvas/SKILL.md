---
name: review-canvas
description: |
  生成播客审查画布数据。根据当前工作区中的音频、转录、QA 报告和剪辑结果，
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

- 这是生成播客审查稿的首选 skill；当用户说“分析并生成审查稿 / 审查画布 / review data / 找出该删的内容”时，应直接使用本 skill
- 输出文件固定为 `review_data.json`
- 格式必须符合 `review_data.schema.json`
- 文件必须是合法 JSON，不要加 Markdown 代码块或注释
- `sentences`、`blocks`、`fineEdits` 的数据模型与 `podcastcutai` 审查画布一致
- 优先使用本 skill 目录中的 DashScope FunASR 做真实转录；只有 DashScope 明确失败时，才允许回退到 OpenRouter Gemini 转录能力
- 不要临时探测 whisper、speech_recognition、sox 或其他随机工具
- 只要 DashScope FunASR 或 OpenRouter Gemini 中至少一个可用，就不允许只生成空壳 `review_data.json`
- 只有在你已经明确尝试过 DashScope FunASR，必要时也尝试过 OpenRouter Gemini，并拿到了可说明的失败原因时，才允许退回最小可用版本；此时必须把失败原因写给用户

## 推荐输入来源

优先读取当前 workspace 中已有文件，如果某些文件不存在就跳过：

- 原始或处理后的音频：`*.mp3`, `*.m4a`, `*.wav`
- 转录：`transcript.json`
- 质检：`qa_signal.json`, `qa_ai.json`, `qa_report.json`
- 剪辑片段：`delete_segments.json`

## 固定执行路线

生成真实审查稿时，按下面顺序执行，不要跳成“先写空稿再说”：

1. 在 workspace 中定位主音频文件，优先：`*.m4a`、`*.mp3`、`*.wav`
2. 直接执行本 skill 自带脚本生成真实审查稿，不要临时手写新脚本：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/generate_review_data.py \
  ./你的音频文件.m4a
```

如果用户已经明确告诉你说话人数，再追加参数，例如：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/generate_review_data.py \
  ./你的音频文件.m4a \
  --speakers 3
```

3. 这个脚本会自动完成：
   - 使用本 skill 目录中的 `review_asr.py`
   - DashScope FunASR 优先转录
   - 必要时回退到 OpenRouter Gemini
   - 生成 `transcript.json`
   - 生成 `review_data.json`
4. 最后验证 `review_data.json`

## DashScope / OpenRouter 约束

真实转录时，必须复用本 skill 目录中的实现：

- 转录：
  `/Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/review_asr.py`

其中：

- `review_asr.py` 已经内置了优先级：`DashScope FunASR -> OpenRouter Gemini fallback`
- 所以当你要转录时，应直接调用本 skill 里的实现，不要自己重新发明转录方式
- 对 review 任务来说，优先调用本 skill 自带的 `generate_review_data.py`；它内部只调用本 skill 目录中的模块
- 如果用户没有明确提供说话人数，不要硬编码 `--speakers 2`；优先让 DashScope 自行分离

执行 Python 时统一使用：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python
```

不要：

- 自己去找 `whisper`
- 自己安装包
- 用随机音频工具拼一个伪 transcript
- 因为懒得转录就直接写 `sentences: []`

如果需要调用这些 backend 模块，应通过项目虚拟环境显式 import 它们，然后把结果落成：

- `transcript.json`
- `review_data.json`

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

1. 先尽可能从现有 `transcript.json` / QA 文件提取事实数据
2. 如果缺少 `transcript.json`，先调用 DashScope FunASR 真实转录；若它失败，再回退 OpenRouter Gemini
3. `sentences` 必须优先来自真实转录结果；文本清理、删除建议、块和精剪判断由 Claude agent 自己完成；第一版允许 `blocks` 为空、`fineEdits` 为空，但不要让 `sentences` 为空
4. 如果能识别明显无效段落，例如录前测试、技术调试、长静音、连续口头停顿，可以标成删除建议
5. `audio_url` 尽量写当前 workspace 里实际存在的音频文件名，优先：
   - `output.mp3`
   - `podcast_edited.mp3`
   - `upload.mp3`
   - 其他实际存在的音频文件
6. 如果 DashScope FunASR 和 OpenRouter Gemini 都实际失败，允许回退最小版；但必须在回复里明确写出失败原因，例如 API key 缺失、上传公网 URL 失败、DashScope 任务失败、OpenRouter 返回非 JSON、音频格式不支持等

## 生成后校验

写完后必须再次读取并验证 `review_data.json`：

```bash
/Users/lincolnwang/podcastcut-skills/webapp/backend/.venv/bin/python \
  /Users/lincolnwang/podcastcut-skills/webapp/backend/skills/review_canvas/validate_review_data.py \
  review_data.json
```

如果校验失败，继续修正直到合法。
