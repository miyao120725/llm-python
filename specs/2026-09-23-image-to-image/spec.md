# Spec: 百炼千问图像（文生图 + 图生图）

- 状态: 已完成
- 日期: 2026-09-23
- 提出者: 用户

## 背景

聊天已接百炼 `qwen3.8-max`。文生图仍走 OpenAI 兼容 `dall-e-3`，本机 `IMAGE_API_KEY` 为空，实际是 mock 占位图。客户端还要把「参考图 + 提示词」改成新图，目前没有这条链路。

用户先点名 `qwen-mt-image-2.0`（官方是图内翻译，不是生图），后确认用 **`qwen-image-3.0`**。该模型同时支持文生图与图生图，协议是 DashScope `multimodal-generation`。`IMAGE_MODEL` 可改成同系列 `qwen-image-3.0-pro`。

## 目标

完成后必须满足：

- [x] 文生图 `POST /v1/generate/text-to-image` 在配置百炼 Key 时走 DashScope `qwen-image-3.0`，不再默认 DALL·E
- [x] `POST /v1/generate/image-to-image` 上传一张图和提示词，返回新图
- [x] 可选先用 LLM 按 image 模式扩写提示词
- [x] 默认同步等结果；`async_mode=true` 时走现有任务查询
- [x] 无图像 Key（且不能复用 LLM Key）时 mock 仍能跑通；测试不打真实外网
- [x] 图生视频、视频生视频行为不变

## 非目标

- 不接 `qwen-mt-image-2.0` 图像翻译（协议是 `image2image/image-synthesis`，字段是 `source_lang` / `target_lang`）
- 不接万相专用协议
- 不做多参考图、局部重绘蒙版、ControlNet
- 不改聊天、搜索、思考
- 不删 OpenAI 兼容图像 Provider（`IMAGE_PROVIDER=openai_compat` 仍可用）
- 不放宽上传大小和类型白名单
- 不把 Key 写入仓库或 `.env.example` 实值

## 用户场景

1. 作为用户，我写「一只赛博朋克橘猫」，以便得到真实生成图而不是占位 PNG。
2. 作为用户，我上传一张猫的照片并写「改成赛博朋克」，以便得到改风格后的图。
3. 作为前端，我用 JSON / multipart 提交，拿到 `/v1/media/{id}` 展示。
4. 作为开发，没配图像 Key 时接口仍返回占位图，链路能通。

## 需求

### 必须

- 新增 `IMAGE_PROVIDER=dashscope`，HTTP 调百炼同步接口：
  - `POST {IMAGE_BASE_URL}/services/aigc/multimodal-generation/generation`
  - 默认 `IMAGE_BASE_URL=https://dashscope.aliyuncs.com/api/v1`
  - 默认 `IMAGE_MODEL=qwen-image-3.0`
- 文生图：`content` 仅 `{"text": prompt}`
- 图生图：`content` 为 `{"image": data URI}` + `{"text": prompt}`（参考图走 Base64，不要求公网 URL）
- 厂商返回的图像 URL 有效期 24 小时，Provider 必须下载后交给现有落盘
- 新接口：multipart，字段 `image`（必填）、`prompt`（必填）、`enhance_prompt`、`size`、`strength`、`async_mode`
- 上传限制与图生视频相同：`IMAGE_TYPES` + `MAX_UPLOAD_MB`
- 任务 `kind=image_to_image`
- ImageProvider 增加 `edit(prompt, image, size, strength)`；mock 返回现有占位 PNG
- `IMAGE_API_KEY` 为空时，dashscope 可复用 `LLM_API_KEY`（同一把百炼 Key）；两者都空才 mock
- `.env.example` 只改空值和注释，不写密钥

### 可选

- `strength` 默认 0.6；百炼该接口无对应字段则忽略
- 客户端 `size` 仍可用 `1024x1024`，Provider 转成百炼的 `1024*1024`
- 厂商侧 `prompt_extend` 默认关，避免与本服务 `enhance_prompt` 双重改写

## 约束与边界

- 架构：API 只收 JSON/表单；Service 入队；Pipeline 扩写 → Provider → 落盘；厂商协议只进 `app/providers/image`
- API：文生图 JSON 契约不变；仅新增图生图路径
- 安全：类型白名单与大小上限不放宽；密钥不进日志；不输出完整 Authorization
- 兼容：旧客户端不调新路径即可；显式 `IMAGE_PROVIDER=openai_compat` 仍走 DALL·E

## 验收标准

- [x] 配置 `IMAGE_PROVIDER=dashscope` 且有 Key 时，文生图 Provider 名为 `dashscope`（健康检查可见）
- [x] mock：合法 png + prompt 同步返回 `succeeded` 和 `media.url`
- [x] 非法类型（如 txt）仍是 `invalid_upload`
- [x] 文生图、图生视频测试仍通过
- [x] DashScope Provider 单测用 httpx mock，不打真实外网
- [x] `pytest` 全绿

## 开放问题

- 无。默认模型用 `qwen-image-3.0`。图内翻译另开 spec。
