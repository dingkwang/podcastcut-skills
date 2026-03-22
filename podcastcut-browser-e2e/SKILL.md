---
name: podcastcut-browser-e2e
description: 使用 browser-use CLI 对 webapp 做端到端验证。覆盖登录、上传音频、生成 review_data.json、刷新审查稿、手动标记删除、确认剪辑、验证 podcast_cut.mp3。触发词：browser e2e、端到端验证、验证网页剪辑、用浏览器跑流程
---

<!--
input: 本地运行中的 webapp + 可上传的音频文件
output: 一次真实 E2E 验证结果（页面证据 + workspace 产物 + 失败点）
pos: 面向浏览器验收，不修改业务逻辑
-->

# Browser E2E 验证

> 用 `browser-use` 真实打开页面，像用户一样完成上传、生成审查稿、手动删句和确认剪辑。

## 适用场景

- 需要确认本地 `webapp` 是否真的可用
- 需要复现“页面上看起来不对”的前端问题
- 需要验证 `review_data.json` 和 `podcast_cut.mp3` 是否真的生成

## 默认目标

默认验证本地环境：

- 前端：`http://127.0.0.1:5173/`
- 后端：`http://127.0.0.1:8001/`

如果用户给了其他地址，按用户地址执行。

## 前置条件

1. 本地服务已经启动：
   - 前端能打开首页
   - 后端 API 正常
2. `browser-use` 已安装
3. 当前机器可访问 Chromium
4. 有一个可上传的音频文件

推荐先检查：

```bash
export PATH="/Users/lincolnwang/.browser-use/bin:/Users/lincolnwang/.browser-use-env/bin:$PATH"
browser-use --help
browser-use sessions
curl -I http://127.0.0.1:5173/
curl -I http://127.0.0.1:8001/api/debug/skills
```

## 核心原则

1. 必须走真实浏览器，不要只测 HTTP API
2. 优先验证完整用户路径，不要只验证局部控件
3. 每次页面状态变化后，重新执行 `state`
4. 不要假设元素索引稳定；`browser-use` 的索引会变
5. 最终必须验证 workspace 产物，而不只是页面文案

## 标准流程

### 1. 打开页面并确认首页可见

```bash
browser-use --session codexverify open http://127.0.0.1:5173/
browser-use --session codexverify --json state
```

检查页面中是否出现：

- `PodcastCut`
- 登录表单，或
- 已登录后的主页面

### 2. 登录

如果未登录，优先使用后端登录接口，避免表单自动化不稳定：

```bash
browser-use --session codexverify eval "fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'local@test.com',password:'123456'})}).then(r=>r.json())"
browser-use --session codexverify open http://127.0.0.1:5173/
browser-use --session codexverify --json state
```

检查是否进入主页面，并能看到：

- `Projects`
- `新建会话`

### 3. 新建会话

重新读取页面状态，找到 `新建会话` 对应索引并点击：

```bash
browser-use --session codexverify --json state
browser-use --session codexverify click <新建会话的索引>
browser-use --session codexverify --json state
```

### 4. 上传音频

重新读取页面状态，找到上传按钮索引并执行：

```bash
browser-use --session codexverify upload <上传按钮索引> /绝对路径/音频文件.m4a
browser-use --session codexverify --json state
```

检查聊天区是否出现：

- `Uploaded file: ...`
- 或 `上传了 ...`

### 5. 触发生成审查稿

在输入框中输入明确指令，例如：

- `请分析这个音频并生成完整的 review_data.json`
- `分析并生成审查稿`

推荐做法：

```bash
browser-use --session codexverify click <输入框索引>
browser-use --session codexverify input <输入框索引> "请分析这个音频并生成完整的 review_data.json"
browser-use --session codexverify keys Enter
```

说明：

- 某些页面上点击“发送”按钮不如 `Enter` 稳定
- 如果发送后无变化，先重新跑 `state` 再重试

### 6. 等待 Claude 生成审查稿

循环读取页面状态，直到页面出现以下任一信号：

- `review_data.json`
- `审查稿生成完成`
- `刷新审查稿`

必要时截图留证：

```bash
browser-use --session codexverify screenshot /tmp/codexverify-progress.png
```

### 7. 刷新审查稿

重新读取页面状态，找到 `刷新审查稿` 按钮并点击：

```bash
browser-use --session codexverify --json state
browser-use --session codexverify click <刷新审查稿索引>
browser-use --session codexverify --json state
```

验收条件：

- 右侧出现 `当前会话审查稿`
- 能看到句子列表
- 不是只显示“还没有可审查的句子”

### 8. 手动标记一条删除

如果审查稿中没有现成的 `blocks` 或 `fineEdits`，必须手动点一条句子的 `标记删除`：

```bash
browser-use --session codexverify --json state
browser-use --session codexverify click <标记删除索引>
browser-use --session codexverify --json state
```

验收条件：

- `确认剪辑` 从禁用变成可点击

### 9. 确认剪辑

```bash
browser-use --session codexverify click <确认剪辑索引>
browser-use --session codexverify --json state
```

验收条件：

- 页面出现 `剪辑成品`
- 页面出现节省时长/成品时长
- 页面出现播放器或 `打开成品音频`

### 10. 验证 workspace 产物

必须到后端 workspace 检查真实文件：

1. 从当前会话拿到 `session_id`
2. 检查：
   - `review_data.json`
   - `podcast_cut.mp3`
   - 如有需要也检查 `transcript.json`

示例：

```bash
ls -lah /Users/lincolnwang/podcastcut-skills/webapp/backend/workspaces/<session_id>/
ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1 /Users/lincolnwang/podcastcut-skills/webapp/backend/workspaces/<session_id>/podcast_cut.mp3
```

## 推荐验证输出

完成后应记录这些信息：

- 使用的 URL
- 使用的音频文件绝对路径
- session id
- 页面上是否出现 `review_data.json` 生成完成提示
- `review_data.json` 是否存在
- `review_data.json` 中的：
  - `sentences` 数量
  - `blocks` 数量
  - `fineEdits` 数量
- 是否成功点击 `确认剪辑`
- `podcast_cut.mp3` 是否存在
- 剪前/剪后时长
- 若失败，明确失败在第几步

## 常见问题

### 1. 页面元素索引变了

解决：

- 不要复用旧索引
- 每一步前都重新执行 `browser-use --json state`

### 2. 发送消息后没有真的提交

解决：

- 先点输入框
- 再 `input`
- 最后用 `keys Enter`

### 3. 刷新审查稿后仍是空白

先检查 workspace 中的 `review_data.json`：

- 文件不存在：说明 Claude 还没生成
- 文件存在但 `sentences` 为空：说明生成的是空壳审查稿

### 4. 确认剪辑不可点

通常是因为：

- 还没切到真实 `Workspace Review`
- `blocks` 和 `fineEdits` 都为空
- 还没有手动对句子执行 `标记删除`

### 5. 页面显示成功，但没有真实成品

必须回到 workspace 验证：

- `podcast_cut.mp3` 是否真的存在
- 时长是否变化

## 完成标准

满足以下条件才算 E2E 通过：

1. 页面真实上传了音频
2. Claude 在当前会话生成了 `review_data.json`
3. 右侧成功渲染真实审查稿
4. 用户可在右侧手动标记删除
5. 点击 `确认剪辑` 后页面出现成品提示
6. workspace 中真实生成 `podcast_cut.mp3`
