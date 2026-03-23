---
name: browser-validation
description: |
  使用 browser-use CLI 对 PodcastCut webapp 做浏览器验收。始终使用 headed 模式，覆盖打开页面、登录、上传指定音频、触发生成审查稿、刷新审查稿、手动标记删除、确认剪辑、核对 workspace 产物。触发词：browser validation、浏览器验证、用 browser-use 跑流程、上传音频验收
---

# Browser Validation

> 用真实浏览器把一次完整用户路径跑完，并记录页面证据与 workspace 产物。默认始终使用 `browser-use --headed`。

## 适用场景

- 需要验证本地或线上 webapp 是否真的可用
- 需要用指定音频复现上传、审查、剪辑问题
- 需要把一次可复用的浏览器验收流程标准化

## 默认目标

- 优先使用本地 `webapp`
- 默认前端：`http://127.0.0.1:5173/`
- 默认后端：`http://127.0.0.1:8001/`
- 默认测试音频可以直接使用用户给出的绝对路径

如果用户明确指定 Fly 或其他 URL，再切到对应地址。

## 前置条件

1. `browser-use` 已安装，并且 PATH 包含：

```bash
export PATH="/Users/lincolnwang/.browser-use/bin:/Users/lincolnwang/.browser-use-env/bin:$PATH"
```

2. 前端首页能打开
3. 有一个可上传的音频文件

建议先检查：

```bash
browser-use --help
curl -I http://127.0.0.1:5173/
```

## 执行模式

- 一律使用 `browser-use --headed`
- 不要使用 headless 模式，除非用户明确要求
- 如果页面状态和你看到的不一致，优先保留当前 headed 会话继续操作，不要悄悄切回无头模式

## 标准流程

### 1. 打开页面

```bash
browser-use --headed --session browser-validation open http://127.0.0.1:5173/
browser-use --headed --session browser-validation --json state
```

### 2. 登录或注册

优先用浏览器内 `fetch()` 走后端接口，减少表单自动化不稳定：

```bash
browser-use --headed --session browser-validation eval "fetch('/api/auth/register',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'browser@test.com',password:'123456'})}).then(r=>r.json())"
browser-use --headed --session browser-validation eval "fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email:'browser@test.com',password:'123456'})}).then(r=>r.json())"
browser-use --headed --session browser-validation open http://127.0.0.1:5173/
```

### 3. 新建会话并上传音频

每一步前都重新读取页面状态，不要复用旧索引。

```bash
browser-use --headed --session browser-validation --json state
browser-use --headed --session browser-validation click <新建会话索引>
browser-use --headed --session browser-validation --json state
browser-use --headed --session browser-validation upload <上传按钮索引> /绝对路径/音频文件.m4a
```

### 4. 发送明确指令

推荐输入：

- `请分析这个音频并生成完整的 review_data.json`

发送时优先 `keys Enter`：

```bash
browser-use --headed --session browser-validation input <输入框索引> "请分析这个音频并生成完整的 review_data.json"
browser-use --headed --session browser-validation keys Enter
```

### 5. 等待并刷新审查稿

反复读取页面状态，直到出现：

- `review_data.json`
- `刷新审查稿`
- `当前会话审查稿`

然后点击 `刷新审查稿`。

### 6. 如果没有自动删除项，手动标记一条删除

必须确认：

- `确认剪辑` 变为可点击

### 7. 确认剪辑

点击 `确认剪辑`，等待页面出现：

- `剪辑成品`
- 节省时长
- 播放器或成品链接

### 8. 验证 workspace 产物

必须检查：

- `review_data.json`
- `podcast_cut.mp3`

并记录：

- session id
- `sentences` 数量
- `blocks` 数量
- `fineEdits` 数量
- 剪前/剪后时长

## 输出要求

完成后至少汇报：

- 使用的 URL
- 上传的音频绝对路径
- session id
- 页面是否成功生成审查稿
- 页面是否成功确认剪辑
- `review_data.json` 和 `podcast_cut.mp3` 是否存在
- 若失败，明确卡在第几步

## 注意事项

- 每次点击/输入前都重新跑 `state`
- 不要假设页面索引稳定
- 不要只看页面文案，最终一定要检查 workspace 文件
- 如果页面没有自动给出删除块，允许手动标记一句删除再继续验证剪辑链
