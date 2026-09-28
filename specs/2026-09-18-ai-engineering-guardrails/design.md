# Design: AI 编程规则、Skill 与 Specs 流程

## 方案摘要

用 Cursor 的项目规则（`.cursor/rules/*.mdc`）做持久约束，用项目 Skill 教助手执行流程，用 `specs/` 存放每次大改动的方案文档。`AGENTS.md` 作为总索引。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| 业务代码 `app/` | 否 | | 本次不改运行时 |
| Tests `tests/` | 否 | | |
| Cursor 规则 | 是 | `.cursor/rules/` | 架构、规范、边界、安全 |
| Cursor Skill | 是 | `.cursor/skills/` | specs / 实现 / Provider |
| Specs | 是 | `specs/` | 流程说明、模板、本变更文档 |
| 入口文档 | 是 | `AGENTS.md`、`README.md` | 索引 |

## 规则拆分

| 文件 | 作用域 | 职责 |
| --- | --- | --- |
| `00-core.mdc` | alwaysApply | 项目是什么、分层、默认行为 |
| `10-specs.mdc` | alwaysApply | 大改动必须走 specs，先方案后实现 |
| `20-python-style.mdc` | `**/*.py` | Python 写法 |
| `30-layer-boundaries.mdc` | `app/**/*.py` | 依赖方向与落点 |
| `40-api-conventions.mdc` | `app/api/**`、`app/schemas/**` | 路由与契约 |
| `50-providers.mdc` | `app/providers/**` | 厂商适配 |
| `60-testing.mdc` | `tests/**` | 测试约束 |
| `70-security.mdc` | alwaysApply | 密钥、生产、上传 |

## Skill 拆分

1. `specs-driven-dev`：判定规模、写三份文档、等待确认、按 tasks 执行。可自动触发。
2. `implement-feature`：按分层落代码，对照 specs 实现。可自动触发。
3. `add-provider`：新增 LLM/Image/Video 厂商的固定步骤。可自动触发。

## 关键决策

1. 规则用多文件短文，而不是单文件长文，方便按 glob 加载。
2. specs 用中文撰写，目录名用英文 slug，避免路径问题。
3. 小改动允许直接实现，但必须显式声明判定结果，避免所有 typo 都走流程。
4. 用户说「直接改」时可跳过等待，不能跳过分层与安全约束。

## 接口与模型

无契约变更。

## 测试策略

文档与规则变更，无需 pytest。后续业务改动仍按现有测试策略。
