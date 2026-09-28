# Tasks: 对话记忆与流式输出

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. Domain + `ConversationStore` Port + SQLite，并接入 factory / container
- [x] 2. LLMProvider 增加 `chat_stream`；openai_compat 解析上游 SSE；mock 分片输出
- [x] 3. `ConversationService`：无状态 / 有会话、JSON / 流式聚合落库
- [x] 4. Schema + 会话接口；`POST /v1/llm/chat` 按 `stream` 返回 JSON 或 SSE
- [x] 5. `CHAT_HISTORY_LIMIT` 写入 Settings 与 `.env.example`
- [x] 6. mock 测试：两轮记忆、无状态 JSON、SSE 分片、会话 404
- [x] 7. 跑 `pytest`；spec 状态改为已完成

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 业务逻辑不进 `app/api/routes`
- 厂商 SDK 只放 `app/providers`
- 基础设施只通过 `app/ports` 被上层使用
- 不提交 `.env`、密钥、`data/` 产物
