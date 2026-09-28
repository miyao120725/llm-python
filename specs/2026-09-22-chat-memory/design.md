# Design: 对话记忆与流式输出

## 方案摘要

新增会话存储（SQLite）和 `ConversationService`。`POST /v1/llm/chat` 增加可选 `conversation_id` 与 `stream`。有会话时只收本轮 user，拼最近 N 条再调 LLM。`stream=false` 返回 JSON；`stream=true` 走 SSE，Provider 产出 token，API 原样写出，流结束后把完整 assistant 落库。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API `app/api` | 是 | `routes/llm.py` | JSON 或 `StreamingResponse`；会话路由 |
| Schema `app/schemas` | 是 | `llm.py` | `conversation_id`、`stream` |
| Service `app/services` | 是 | `conversation.py` | 历史、截断、流式聚合落库 |
| Pipeline `app/pipelines` | 否 | | |
| Provider `app/providers` | 是 | `llm/base.py`、`openai_compat.py`、`mock.py` | `chat_stream` |
| Port `app/ports` | 是 | `conversations.py` | |
| Infra `app/infrastructure` | 是 | `conversations/sqlite.py` | |
| Domain `app/domain` | 是 | Conversation / 消息 |
| Config `app/config.py` | 是 | `CHAT_HISTORY_LIMIT` |
| Worker `app/worker` | 否 | | |
| Tests `tests/` | 是 | mock 覆盖记忆、无状态、SSE |

## 数据流 / 调用链

```text
JSON（stream=false）：
  POST /v1/llm/chat
    → 拼 messages（可选历史）
    → LLMProvider.chat
    → 有会话则 add_message(assistant)
    → ChatResponse

SSE（stream=true）：
  POST /v1/llm/chat {stream:true, conversation_id?}
    → 有会话则先落 user
    → async for token in LLMProvider.chat_stream(...)
         yield data: {"type":"delta","content":"..."}
    → 有会话则落完整 assistant
    → yield data: {"type":"done","conversation_id":"...","model":"..."}
    → yield data: [DONE]
```

## 关键决策

1. **会话 ID**：无登录，用 `conversation_id`。
2. **截断**：最近 `CHAT_HISTORY_LIMIT` 条（默认 20）。
3. **SSE 而不是 WebSocket**：实现简单，fetch ReadableStream 即可。
4. **默认不流式**：文档页和旧客户端仍拿 JSON。
5. **只流 `content`**：百炼思考内容不往外推，避免半截 reasoning。
6. **兼容 OpenAI 兼容协议**：上游 `stream: true`，解析 `choices[0].delta.content`。
7. **有会话时本轮只收一条 user**。

## 接口与模型

### `POST /v1/llm/chat`

请求增加：`conversation_id`、`stream`（默认 false）。

有会话：`messages` 必须恰好 1 条 user。

`stream=false` 响应增加 `conversation_id`。

`stream=true`：`Content-Type: text/event-stream`

```text
data: {"type":"delta","content":"你"}

data: {"type":"delta","content":"好"}

data: {"type":"done","conversation_id":"abc","model":"qwen3.8-max"}

data: [DONE]
```

### `POST /v1/llm/conversations` / `GET /v1/llm/conversations/{id}`

与原方案相同。

### Provider

```text
chat(...) -> str
chat_stream(...) -> AsyncIterator[str]   # 只 yield content 增量
```

`chat()` 可内部消费 `chat_stream` 再拼接，避免两套协议。

## 错误处理

- `conversation_not_found` → 404
- `invalid_conversation_turn` → 400
- 流式中途失败：发一条 `{"type":"error","message":"..."}` 后结束；已落库的 user 保留，不写半截 assistant

## 配置

- `CHAT_HISTORY_LIMIT=20`
- 写入 `.env.example`

## 测试策略

- mock `chat_stream` 产出固定分片，断言 SSE 行与拼接文本
- 两轮记忆：第二次入参含第一轮
- JSON 无会话路径回归
- 会话 404
- 禁止打真实外网

## 风险

- 文档页对 SSE 展示不友好：保留默认 JSON
- 流中断：不落半截回复，客户端可重问
- 思考模型耗时：只等 `content`；超时沿用现有 HTTP timeout
