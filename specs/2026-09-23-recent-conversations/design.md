# Design: 最近会话列表

## 方案摘要

在 ConversationStore 增加 `list_recent`，按最后一条消息时间倒序查出非空会话摘要。`GET /v1/llm/conversations` 返回侧边栏所需字段。客户端点选后仍用现有 id 拉历史并续聊，不新开聊天协议。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API `app/api` | 是 | `routes/llm.py` | 增加 `GET /conversations`，须写在 `/{id}` 之前 |
| Schema `app/schemas` | 是 | `llm.py` | 列表项与列表响应 |
| Service `app/services` | 是 | `conversation.py` | `list_recent` |
| Pipeline `app/pipelines` | 否 | | |
| Provider `app/providers` | 否 | | |
| Port `app/ports` | 是 | `conversations.py` | `list_recent` |
| Infra `app/infrastructure` | 是 | `conversations/sqlite.py` | SQL 聚合查询 |
| Domain `app/domain` | 是 | `models.py` | `ConversationSummary` |
| Config `app/config.py` | 否 | | `limit` 用查询参数 |
| Worker `app/worker` | 否 | | |
| Tests `tests/` | 是 | `test_conversation.py` | 列表顺序、空会话、续聊 |

## 数据流 / 调用链

```text
侧边栏：
  GET /v1/llm/conversations?limit=20
    → ConversationService.list_recent
    → ConversationStore.list_recent
    → SQLite 按最后消息时间倒序

点选续聊：
  GET /v1/llm/conversations/{id}     回填气泡
  POST /v1/llm/chat {conversation_id, messages:[{user}]}
    → 现有记忆逻辑，不改
```

## 关键决策

1. **路径**：`GET /v1/llm/conversations` 列表，`GET /v1/llm/conversations/{id}` 详情。静态路径注册在动态路径前，避免被当成 id。
2. **排序**：`updated_at` = 最后一条消息的 `created_at`，最近聊过的排最前。
3. **标题**：该会话第一条 `user` 正文，超过 40 字截断并加省略号；没有 user 则标题为空串。
4. **预览**：最后一条 `content` 截断到 80 字，带 `last_role`。
5. **空会话**：`message_count = 0` 的不返回，避免侧边栏一堆空房间。
6. **隔离**：沿用无登录模型，列出本实例全部非空会话。文档与 OpenAPI 说明仅适合单机/内网联调。
7. **不加列**：用子查询聚合，避免 SQLite 迁移。

## 接口与模型

### `GET /v1/llm/conversations`

查询：`limit` int，默认 20，范围 1～50。

```json
{
  "items": [
    {
      "conversation_id": "abc",
      "title": "我叫小明",
      "created_at": "...",
      "updated_at": "...",
      "last_role": "assistant",
      "last_content": "你叫小明。",
      "message_count": 2
    }
  ]
}
```

### Domain

```text
ConversationSummary
  conversation_id, created_at, updated_at
  title, last_role, last_content, message_count
```

### Port

```text
list_recent(limit: int) -> list[ConversationSummary]
```

## 错误处理

无新错误码。`limit` 非法由 FastAPI / Query 校验为 422。单条不存在仍是 `conversation_not_found`。

## 配置

不新增环境变量。

## 测试策略

- mock：建两个会话并聊天，列表顺序为后聊的在前，`title` 为首条 user
- 只 create 不聊天的会话不出现
- 用列表返回的 id 再聊一轮，第二轮入参含第一轮（沿用现有记忆断言）
- 禁止打真实外网

## 风险

- 无用户隔离：多客户端连同一服务会看到彼此会话。本地可接受；生产按用户拆分另开 spec。
- 长文本：列表只返回截断预览，完整正文仍走详情接口。
