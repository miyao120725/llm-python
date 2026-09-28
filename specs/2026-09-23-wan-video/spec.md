# Spec: 百炼 wan3.0-video 统一生视频

- 状态: 已完成
- 日期: 2026-09-23
- 提出者: 用户

## 背景

出图已走百炼 `qwen-image-3.0`。视频仍是通用 HTTP Provider，本机无视频 Key，实际是 mock。用户要四条能力，模型都是百炼 **`wan3.0-video`**：

1. 文生视频
2. 文 + 图生视频
3. 文 + 视频生视频
4. 文 + 图 + 视频生视频

万相 3.0 是 All-in-One：同一模型、同一异步接口，靠 `input.media[].type` 区分。官方 HTTP **只支持异步**（必须 `X-DashScope-Async: enable`），成片约 1～5 分钟。

## 目标

完成后必须满足：

- [x] 单一入口 `POST /v1/generate/video`：按是否上传图/视频分流上述四种
- [x] 配置后走 DashScope `wan3.0-video`；无 Key 时 mock 仍通
- [x] 默认同本服务任务异步（`async_mode=true`），用 `GET /v1/tasks/{id}` 查
- [x] 厂商结果 URL 立刻下载落盘；错误不带回签名 URL / 密钥
- [x] 删除 `/image-to-video`、`/video-to-video`
- [x] 测试不打真实外网

## 非目标

- 不接音频参考、文档/网页生视频、首尾帧两张图、视频延长专用字段
- 不合并进 `/v1/generate/image`
- 不保留旧 `/image-to-video`、`/video-to-video`
- 不放宽 `MAX_UPLOAD_MB`；不把 Key 写入仓库

## 用户场景

1. 作为前端，我只用一个 `FormData` 打 `/v1/generate/video`，按有无 `image`/`video` 组合四种能力。
2. 作为用户，我先拿到 `task_id`，再轮询直到 `media.url` 可播。
3. 作为开发，没配视频 Key 时仍返回占位 mp4，链路能通。

## 需求

### 必须

- `POST /v1/generate/video`，multipart
- 字段：`prompt`（必填）、`image`（可选）、`video`（可选）、`enhance_prompt`、`duration_seconds`、`resolution`、`ratio`、`async_mode`
- 分流与万相 `media.type`：

| 客户端上传 | 任务 kind | 万相 media |
| --- | --- | --- |
| 仅 prompt | `text_to_video` | 不传 media |
| prompt + 图 | `image_to_video` | `first_frame`（图用 data URI） |
| prompt + 视频 | `video_to_video` | `reference_video`（先上传临时 oss://） |
| prompt + 图 + 视频 | `image_and_video_to_video` | `reference_image` + `reference_video`（不可与 first_frame 混用） |

- 新 `VIDEO_PROVIDER=dashscope`，默认 `VIDEO_MODEL=wan3.0-video`，`VIDEO_BASE_URL=https://dashscope.aliyuncs.com/api/v1`
- `VIDEO_API_KEY` 可空，dashscope 复用 `LLM_API_KEY`
- 创建任务：`POST .../services/aigc/video-generation/video-synthesis` + `X-DashScope-Async: enable`
- 轮询：`GET .../tasks/{task_id}`，间隔默认 15s，超时默认 600s
- 成功后的 `output.video_url` 用不带 Bearer 的客户端下载再落盘
- 参考视频走百炼临时上传（`GET /api/v1/uploads?action=getPolicy`），调用时带 `X-DashScope-OssResourceResolve: enable`
- 厂商 `prompt_extend=false`；本服务 `enhance_prompt` 仍走 LLM
- mock：四种组合都返回现有占位 mp4

### 可选

- `duration_seconds` 默认 5，范围 **2～10**（超出由本服务校验拒绝）
- `resolution` 默认 `720P`（官方默认 1080P 更慢更贵）
- `ratio` 默认 `adaptive`

## 约束与边界

- 架构：API 只收表单；Service 入队；Pipeline 扩写 → Provider → 落盘
- 厂商协议只进 `app/providers/video`
- 上传：图走现有 `IMAGE_TYPES`；视频走 `VIDEO_TYPES`（增加 `video/quicktime` / `.mov`，万相要 mp4/mov）
- 生产：`resolved_video_api_key` 必须有；禁止 mock
- 兼容：旧视频路径返回 404，客户端改打 `/video`

## 验收标准

- [x] mock：四种组合都能 `succeeded` 且有 `media.url`；`kind` 正确
- [x] 非法类型仍 `invalid_upload`
- [x] 旧路径 404
- [x] DashScope Provider 单测 mock HTTP（建任务、轮询、下载、上传策略），不打外网
- [x] `pytest` 全绿

## 开放问题

- 无。统一入口 `/v1/generate/video`；旧视频路径删除。
