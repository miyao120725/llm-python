# Tasks: 深度推理与深度搜索

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. Domain `LLMStreamPart`；Provider `chat` / `chat_stream` 增加 `thinking`、`search`
- [x] 2. `openai_compat` 按开关写百炼字段、解析 `reasoning_content`；mock 产出对应片段
- [x] 3. Schema + ConversationService：SSE `reasoning`/`delta`，只落 content
- [x] 4. 路由转发新字段；测试覆盖默认、只思考、思考+搜索、历史不含思考
- [x] 5. 跑 `pytest`
- [x] 6. 回写 spec 状态为「已完成」

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 业务逻辑不进 `app/api/routes`
- 厂商 SDK 只放 `app/providers`
- 基础设施只通过 `app/ports` 被上层使用
- 不提交 `.env`、密钥、`data/` 产物
