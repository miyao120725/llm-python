# Tasks: 最近会话列表

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. Domain `ConversationSummary` + Port `list_recent` + SQLite 聚合查询
- [x] 2. Schema 列表响应；Service `list_recent` 做标题/预览截断
- [x] 3. `GET /v1/llm/conversations`（写在 `/{id}` 之前）
- [x] 4. 测试：顺序、空会话过滤、点选 id 续聊
- [x] 5. 跑 `pytest`
- [x] 6. 回写 spec 状态为「已完成」

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 业务逻辑不进 `app/api/routes`
- 厂商 SDK 只放 `app/providers`
- 基础设施只通过 `app/ports` 被上层使用
- 不提交 `.env`、密钥、`data/` 产物
