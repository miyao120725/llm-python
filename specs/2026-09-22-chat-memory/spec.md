# Spec: 对话记忆与流式输出

- 状态: 已完成
- 日期: 2026-09-22
- 提出者: 用户

## 背景

当前 `POST /v1/llm/chat` 无状态，且整段生成完才返回。连续提问看不到上文；长回复要等很久。需要服务端记住同一会话，并支持边生成边输出。

## 目标

完成后必须满足：

- [x] 同一 `conversation_id` 下的后续提问能带上此前的 user / assistant 消息
- [x] 可以查询某次会话的完整历史
- [x] 不传会话 ID 时，现有无状态 `/v1/llm/chat` JSON 行为保持不变
- [x] 历史有长度上限，避免把整个上下文塞爆模型窗口
- [x] `stream=true` 时以 SSE 逐段返回 `content`，结束后再落库完整助手回复

## 非目标

- 不做跨会话的长期画像 / 向量检索 RAG
- 不做登录用户体系；本期用 `conversation_id` 标识会话
- 不改文生图 / 视频链路
- 不向前端展示模型思考过程（`reasoning_content` 丢弃，只流式输出最终 `content`）
- 不做 WebSocket

## 用户场景

1. 作为调用方，我连续问「我叫小明」再问「我叫什么」，以便模型能答出小明。
2. 作为调用方，我希望拿到 `conversation_id` 并稍后拉取历史，以便核对说过什么。
3. 作为调用方，我仍可以一次传入完整 `messages` 做单轮问答，不必建会话。
4. 作为调用方，我设置 `stream=true`，一边收字一边展示，不必等整段结束。

## 需求

### 必须

- 创建会话，返回 `conversation_id`
- 在会话中追加一条用户输入，服务加载历史 → 调 LLM → 落库回复
- 查询会话消息列表（按时间正序）
- 历史截断：默认只把最近 N 条送给模型（N 可配置）
- `stream=true`：SSE 推送 `delta`，最后 `done`；有会话时流结束后写入完整 assistant
- `stream=false`（默认）：仍返回现在的 JSON

### 可选

- 删除会话
- 可选 `title`（首条用户消息截断）

## 约束与边界

- 架构：API → Service → ConversationStore Port + LLMProvider；路由不直连存储/厂商
- Provider 增加流式方法，OpenAI 兼容与 mock 都要实现
- API：扩展 chat 契约；无 `conversation_id` 且 `stream=false` 时保持旧行为
- 安全：不把密钥写入历史；日志不打印完整长对话
- 兼容：旧客户端不传新字段仍可用

## 验收标准

- [x] 两轮对话：「我叫小明」→「我叫什么」，第二轮能用到第一轮（mock 断言拼进 provider 的 messages）
- [x] `GET` 历史条数与落库一致
- [x] 不传 `conversation_id` 的 JSON chat 测试仍通过
- [x] `stream=true` 时响应 `text/event-stream`，能拼出完整回复；有会话时历史里有完整 assistant
- [x] `pytest` 全绿，测试不打真实百炼

## 开放问题

- 无（默认最近 20 条进模型；流式默认关闭，需显式 `stream=true`）
