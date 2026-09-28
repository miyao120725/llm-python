# Spec: AI 编程规则、Skill 与 Specs 流程

- 状态: 已完成
- 日期: 2026-09-18
- 提出者: 项目维护者

## 背景

本仓库是 FastAPI 多模态生成服务，分层已经成型（API / Service / Pipeline / Provider / Ports / Infrastructure）。目前没有给 AI 助手的持久规则、编写规范、约束边界，也没有「大改动先方案后实现」的流程。助手容易直接改代码、打穿分层、或在未确认时做大范围重构。

## 目标

- [x] 增加 Cursor 项目规则：架构、编码规范、分层边界、API/Provider/测试、安全约束
- [x] 增加对应 Skill：specs 流程、功能实现、新增 Provider
- [x] 建立 specs 目录、模板和判定标准：大改动先写 `spec.md` / `design.md` / `tasks.md`，确认后再实现
- [x] 用 `AGENTS.md` 作为入口，README 增加简短索引

## 非目标

- 不改业务代码、API 契约、依赖或运行时行为
- 不引入 linter/formatter 强制配置（可后续单独 spec）
- 不把规则写成大而全的论文；规则保持短、可执行

## 用户场景

1. 作为开发者，我希望 AI 在大改动前先给方案和文档，确认后再动手。
2. 作为开发者，我希望 AI 按现有分层改代码，而不是在路由里调厂商 SDK。
3. 作为开发者，我希望新增可灵/Runway 等厂商时有固定步骤可循。

## 需求

### 必须

- `.cursor/rules/` 下按主题拆分 `.mdc` 规则（alwaysApply 与 glob 结合）
- `.cursor/skills/` 下提供 specs / 实现 / Provider 三个 skill
- `specs/` 提供 README、模板、以及本变更自身的示例 spec
- 大改动必须等待用户同意后再改业务代码（本变更已由用户明确提出，可直接落地）

### 可选

- README 增加「AI 协作」一小节

## 约束与边界

- 只新增文档与 Cursor 配置，不碰 `app/` 运行时代码
- 规则内容必须对齐当前仓库：mock 回退、`AppError`、container、ports、生产禁 mock
- 规则单文件尽量短，一条规则只盯一类问题

## 验收标准

- [x] 打开项目后，助手能读到 alwaysApply 规则和 AGENTS.md
- [x] 大改动判定标准写进规则与 skill，流程为：写 spec → 等人确认 → 按 tasks 实现
- [x] 新增 Provider / 新功能的落点在 skill 里写清
- [x] 不包含真实密钥，不改 `.gitignore` 已忽略的 `.env`

## 开放问题

- 无。用户已要求同时落地规则、规范和 specs 流程。
