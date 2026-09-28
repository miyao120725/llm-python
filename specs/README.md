# Specs 流程

改动较大时，先写方案文档，经确认后再按任务清单实现。不要直接大范围改代码。

## 何时必须走 specs

满足任一条件即视为**大改动**：

- 跨 2 个以上分层（API / Service / Pipeline / Provider / Infrastructure）
- 变更 API 契约（路径、字段、状态码语义、鉴权）
- 新增 Provider 或 storage / queue / task backend
- 调整异步任务、队列、Worker 行为
- 调整生产安全、配置模型或运行时约束
- 预估改动 ≥ 4 个文件，或净变更较大
- 用户明确要求「方案」「设计」「规划」

小改动（单文件 bug、测试、注释、局部文案）可直接实现，但须在回复里说明判定为小改动。

## 目录约定

```text
specs/
  templates/                 模板，复制后填写
  YYYY-MM-DD-short-slug/     一次变更一个目录
    spec.md                  要做什么、为什么、边界
    design.md                怎么做、触及哪些层
    tasks.md                 可勾选的实现清单
```

slug 只用小写英文、数字和连字符，例如 `2026-09-18-ai-engineering-guardrails`。

## 执行顺序

1. 判定规模，大改动先读 `.cursor/skills/specs-driven-dev/SKILL.md`。
2. 复制模板到新目录，写完 `spec.md` → `design.md` → `tasks.md`。
3. 向用户给出方案摘要，**等待明确同意**后再改业务代码。
4. 按 `tasks.md` 逐项实现，完成一项勾一项。
5. 中途发现设计不对：先改 spec/design，再改代码。

用户说「直接改 / 不用方案 / 小改」时，可跳过等待，但仍建议留下简短说明。
