---
name: deploy
description: |
  将当前 webapp 发布到 Fly.io，并在发布前后做最小健康检查。
  适用于前端或后端改动后的一键上线。触发词：deploy、发布、上线、推到 fly、fly.io
triggers:
  - "deploy"
  - "发布"
  - "上线"
  - "推到 fly"
  - "fly.io"
---

# 部署到 Fly.io

> 目标：把 `/Users/lincolnwang/podcastcut-skills/webapp` 当前代码发布到 Fly app，并确认新版本可访问。

## 当前项目约定

- 项目根目录：`/Users/lincolnwang/podcastcut-skills/webapp`
- Fly 配置：`fly.toml`
- Fly app：`podcastcut-voiceclone`
- 前端构建命令：`cd frontend && npm run build`
- 后端入口：`uvicorn app:app --host 0.0.0.0 --port 8000`

## 标准流程

### 1. 先做本地最小检查

优先执行：

```bash
cd /Users/lincolnwang/podcastcut-skills/webapp/frontend && npm run build
```

如有 Python 改动，可补充：

```bash
cd /Users/lincolnwang/podcastcut-skills/webapp/backend && ./.venv/bin/python -m py_compile app.py agent.py
```

### 2. 执行 Fly 部署

必须从项目根目录执行：

```bash
cd /Users/lincolnwang/podcastcut-skills/webapp
flyctl deploy --config fly.toml
```

### 3. 部署后确认状态

至少检查：

```bash
cd /Users/lincolnwang/podcastcut-skills/webapp
flyctl status --config fly.toml
```

期望结果：

- app 名称是 `podcastcut-voiceclone`
- machine 进入 `started`
- version 增长
- image 更新到新的 deployment tag

### 4. 线上健康检查

至少验证首页：

```bash
curl -s https://podcastcut-voiceclone.fly.dev/ | head
```

必要时也可检查响应头：

```bash
curl -I https://podcastcut-voiceclone.fly.dev/
```

## 出问题时怎么查

### 看状态

```bash
flyctl status --config /Users/lincolnwang/podcastcut-skills/webapp/fly.toml
```

### 看日志

```bash
flyctl logs --config /Users/lincolnwang/podcastcut-skills/webapp/fly.toml --no-tail
```

### 常见判断

- 如果卡在 `replacing`，先继续等 machine 切换和 smoke checks
- 如果首页能返回 HTML，通常说明静态前端已经部署成功
- 如果页面黑屏，更可能是前端运行时错误或 session/auth 问题，不一定是部署失败

## 回答用户时建议包含

- 是否部署成功
- Fly app 名称
- 新版本号
- 线上地址
- 是否通过首页健康检查
