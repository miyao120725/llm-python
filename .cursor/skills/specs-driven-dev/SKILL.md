---
name: specs-driven-dev
description: Gates large changes behind spec.md, design.md, and tasks.md. Use when the change spans layers, alters API contracts, adds providers or backends, touches workers/queues, or the user asks for a plan, design, spec, or 方案.
---

# Specs 驱动开发

大改动先写方案文档，等用户确认，再按任务清单改代码。

完整约定见 [specs/README.md](../../../specs/README.md)。模板在 `specs/templates/`。

## 立即判定

先输出一行：`规模: 小改动 | 大改动` 以及判定原因。

**大改动**（任一即是）：跨 2+ 分层；改 API 契约/鉴权；新 Provider 或 storage/queue/task backend；改任务/队列/Worker；改生产配置模型；≥4 个文件或较大净变更；用户要方案/设计。

**小改动：** 单文件修复、测试、注释。直接实现，不必等确认。

## 大改动流程

复制本清单并勾选：

```
- [ ] 1. 建目录 specs/YYYY-MM-DD-short-slug/
- [ ] 2. 从 templates 复制 spec.md / design.md / tasks.md 并填空
- [ ] 3. 向用户给方案摘要（目标、非目标、触及层、风险）
- [ ] 4. 等待明确同意（同意 / 按方案执行 / LGTM）
- [ ] 5. 按 tasks.md 逐项实现并勾选
- [ ] 6. 对照 spec 验收；跑相关测试
```

未到第 4 步，**不要改 `app/` 业务代码**。可以写 spec 文档。

slug：小写英文+数字+连字符，例如 `add-kling-video-provider`。

## 方案摘要格式

```markdown
规模: 大改动
目录: specs/<date>-<slug>/

目标: ...
非目标: ...
触及层: API / Service / ...
风险: ...

请确认后我再按 tasks.md 实现。
```

## 执行约束

- 只做 `tasks.md` 里的项；范围外先改 spec
- 实现时读取 `implement-feature` skill；加厂商时再读 `add-provider`
- 用户说「直接改 / 不用方案 / 小改」可跳过等待，仍须遵守分层与安全规则
- 中途发现设计错误：停下来改 design，再继续编码
