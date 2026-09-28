# Design: 深度推理与深度搜索

## 方案摘要

在 chat 契约上增加 `thinking` / `search`。Provider 的流式产出改为带类型的片段（思考 / 正文）。Service 只把正文拼进历史和 `delta`，思考走 `reasoning` 事件且不落库。百炼在 OpenAI 兼容 payload 里开关 `enable_thinking` 与 `enable_search`；非百炼 URL 不传这些扩展字段。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API `app/api` | 是 | `routes/llm.py` | 把 thinking/search 传给 service |
| Schema `app/schemas` | 是 | `llm.py` | 请求字段；JSON 响应可选 `reasoning` |
| Service `app/services` | 是 | `conversation.py` | 分流 SSE；只持久化 content |
| Pipeline `app/pipelines` | 否 | | |
| Provider `app/providers` | 是 | `llm/base.py`、`openai_compat.py`、`mock.py` | 流片段类型与厂商参数 |
| Port `app/ports` | 否 | | |
| Infra `app/infrastructure` | 否 | | |
| Domain `app/domain` | 是 | `models.py` | `LLMStreamPart` |
| Config `app/config.py` | 否 | | 超时按次覆盖，不新环境变量 |
| Worker `app/worker` | 否 | | |
| Tests `tests/` | 是 | `test_conversation.py` 等 | mock 覆盖开关与落库 |

## 数据流 / 调用链

```text
POST /v1/llm/chat {thinking, search, stream?}
  → ConversationService
    → LLMProvider.chat_stream(..., thinking, search)
         yield LLMStreamPart(kind=reasoning|content, text)
    → stream=true:
         reasoning → SSE type=reasoning（不落库）
         content   → SSE type=delta，结束后落 assistant
    → stream=false:
         拼 content / reasoning 后返回 JSON，只落 content
```

## 关键决策

1. **两个独立开关**：可只开思考、只开搜索、或两个都开。都关 = 现状。
2. **搜索枚举**：`off` / `agent` / `agent_max`。深度搜索用 `agent_max`（多轮检索 + 抓页）。
3. **流式类型**：`chat_stream` 不再只 yield `str`，改为 `LLMStreamPart`，避免思考被误写入历史。
4. **默认关思考**：百炼 URL 仅在 `thinking=true` 时传 `enable_thinking=true`，否则仍传 `false`。
5. **非百炼**：不附加 `enable_*`，避免 OpenAI 官方接口 400。
6. **历史**：只存最终 `content`。思考不进下一轮上下文。
7. **超时**：`thinking` 或 `search!=off` 时该次 stream 超时 300s。
8. **JSON 不强制改 SSE**：深度模式建议客户端 `stream=true`；JSON 仍聚合完整结果。
9. **来源**：本期不解析、不转发 `search_info`。
10. **mock**：`thinking` 先吐两段 reasoning；`search!=off` 在正文加 `[mock-search:agent_max]` 之类标记。

## 接口与模型

### `POST /v1/llm/chat` 请求新增

```text
thinking: bool = false
search: "off" | "agent" | "agent_max" = "off"
```

占位符 `string` 视为默认关。

### SSE

```text
data: {"type":"reasoning","content":"先检索再比较…"}

data: {"type":"delta","content":"结论是…"}

data: {"type":"done","conversation_id":"...","model":"...","thinking":true,"search":"agent_max"}

data: [DONE]
```

### JSON 响应新增

```text
reasoning: str | null
thinking: bool
search: str
```

`content` 仍是给用户看的最终回复。

### Domain

```text
LLMStreamPart
  kind: "reasoning" | "content"
  text: str
```

### Provider

```text
chat(..., thinking=False, search="off") -> str          # 只拼 content
chat_stream(...) -> AsyncIterator[LLMStreamPart]
```

`enhance_prompt` 不传思考/搜索。

### 百炼 payload（仅 dashscope URL）

```text
enable_thinking: <thinking>
enable_search: true                 # 仅 search != off
search_options.search_strategy: agent | agent_max
```

## 错误处理

无新错误码。上游失败仍 `provider_error`。流中途失败：已有正文则落 assistant；思考稿丢弃。

## 配置

不新增环境变量。深度模式单次超时 300s，写在 Provider 调用处。

## 测试策略

- 默认 chat：无 reasoning 事件，历史不变
- `thinking=true` + stream：有 reasoning 行；GET 历史 assistant 不含思考文案
- `search=agent_max` + `thinking=true`：mock 记录到的开关正确
- 回归：无会话 JSON、两轮记忆、最近会话列表
- 禁止打真实外网

## 风险

- 深度模式耗时与费用上升：默认关闭，由客户端点选
- 兼容协议搜不到完整出处：前端不要依赖角标
- 旧进程不热更新：改完需重启服务
