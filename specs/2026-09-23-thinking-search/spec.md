# Spec: 深度推理与深度搜索

- 状态: 已完成
- 日期: 2026-09-23
- 提出者: 用户

## 背景

当前聊天为了稳定落库，百炼侧强制 `enable_thinking=false`，也不联网。客户端无法按需打开深度推理或深度搜索。两件事都要接到现有 `/v1/llm/chat` 与 SSE 上，默认行为保持不变。

## 目标

完成后必须满足：

- [x] 请求可打开思考（`thinking`）和搜索策略（`search`），默认都关
- [x] 打开后 SSE 能区分思考过程与最终正文；历史只落最终 `assistant` 正文
- [x] 两开关可同时开（调研场景：先搜再想再答）
- [x] 不传新字段时，现有 JSON / SSE / 会话记忆行为不变
- [x] mock 能覆盖思考与搜索路径，测试不打真实外网

## 非目标

- 不新增 DashScope 专用 Provider；继续 OpenAI 兼容协议加厂商扩展字段
- 不保证角标、完整 `search_info` 来源列表（兼容协议能力有限）
- 不把思考过程写入会话记忆
- 不改文生图 / 视频 / enhance-prompt
- 不做自建爬虫或自建搜索后端
- 不强制 `stream=true`（JSON 仍可用，但文档建议深度模式走 SSE）

## 用户场景

1. 作为用户，我打开思考，以便看到推理过程再看到结论。
2. 作为用户，我打开深度搜索，以便回答带上网后的信息。
3. 作为用户，我两个都开，以便做需要查资料再推理的问题。
4. 作为旧客户端，我不传新字段，行为与现在一致。

## 需求

### 必须

- `POST /v1/llm/chat` 增加：
  - `thinking: bool`，默认 `false`
  - `search: "off" | "agent" | "agent_max"`，默认 `"off"`
- `thinking=true`：上游 `enable_thinking=true`；SSE 推 `type=reasoning`，再推 `type=delta`
- `search!=off`：上游 `enable_search=true`，`search_options.search_strategy` 为对应值
- 会话历史只追加最终 `content`，不含 `reasoning`
- JSON 模式返回 `content`，可选带 `reasoning`（不落库）
- mock：按开关产出假思考 / 假搜索痕迹，并记录本次开关供测试断言

### 可选

- `done` 事件回传本次实际使用的 `thinking` / `search`

## 约束与边界

- 架构：路由只校验；Service 转发开关；只有 Provider 认识百炼字段
- API：扩展 chat 契约，旧字段语义不变
- 安全：不把 Key 写入思考/搜索日志；生产仍禁止 mock
- 兼容：未识别 `search` / `thinking` 占位符时按默认关处理
- 超时：思考或搜索时单次请求超时不低于 300s（仅该次调用）

## 验收标准

- [x] 默认请求无 `reasoning` 事件，历史只有 user/assistant 正文
- [x] `thinking=true` 的 SSE 含 `reasoning` 与 `delta`；GET 历史无思考稿
- [x] `search=agent_max` 且 `thinking=true` 时，mock/真实 Provider 收到两个开关
- [x] 旧 JSON chat、会话记忆、最近会话列表测试仍通过
- [x] `pytest` 全绿，不打真实百炼

## 开放问题

- 无（默认双关；深度搜索用 `agent_max`；来源列表本期不做）
