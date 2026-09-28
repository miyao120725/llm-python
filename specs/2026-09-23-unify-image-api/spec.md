# Spec: 文生图 / 图生图合并为一个接口

- 状态: 已完成
- 日期: 2026-09-23
- 提出者: 用户

## 背景

客户端现在要记两条路径：文生图走 JSON `POST /v1/generate/text-to-image`，图生图走 multipart `POST /v1/generate/image-to-image`。前端希望一个入口，有参考图就改图，没有就按提示词生图。用户确认后要求去掉旧路径。

## 目标

完成后必须满足：

- [x] 单一入口 `POST /v1/generate/image`：有 `image` 文件则图生图，否则文生图
- [x] 响应仍是 `GenerationResult`，`kind` 分别为 `text_to_image` / `image_to_image`
- [x] 删除 `/text-to-image`、`/image-to-image`
- [x] 上传限制与现有图生图相同；无文件时不走上传校验
- [x] mock 与真实 Provider 行为不变；测试不打外网

## 非目标

- 不合并图生视频 / 视频生视频
- 不改聊天、任务查询、媒体下载
- 不改百炼 Provider 协议
- 不改任务 `kind` 取值（仍区分文生图 / 图生图）

## 用户场景

1. 作为前端，我只用一个 `fetch` + `FormData`，有文件就带上 `image`，以便少记一条路径。
2. 作为用户，我不传图只写提示词，仍然能出图。

## 需求

### 必须

- `POST /v1/generate/image`，`multipart/form-data`
- 字段：`prompt`（必填）、`image`（选填文件）、`enhance_prompt`、`size`、`strength`、`async_mode`
- 无文件或空文件 → `text_to_image`（忽略 `strength`）
- 有文件 → 现有图生图校验（png/jpeg/webp + 大小上限）
- 默认同步，`async_mode=true` 仍查 `GET /v1/tasks/{id}`
- 旧路径返回 404

### 可选

- 无

## 约束与边界

- 架构：路由只判断有没有图，再调现有 Service
- API：删除两条旧路径，只保留 `/image`
- 安全：有图时白名单与 `MAX_UPLOAD_MB` 不放宽
- 兼容：已对接旧路径的客户端必须改到 `/image`

## 验收标准

- [x] 只传 prompt，同步返回 `kind=text_to_image` 且有 `media.url`
- [x] 传 png + prompt，同步返回 `kind=image_to_image` 且有 `media.url`
- [x] 传 txt 仍是 `invalid_upload`
- [x] 旧路径 404
- [x] `pytest` 全绿

## 开放问题

- 无
