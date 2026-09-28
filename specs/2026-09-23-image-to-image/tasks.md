# Tasks: 百炼千问图像（文生图 + 图生图）

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. `Settings`：默认 `IMAGE_PROVIDER=dashscope`、`IMAGE_BASE_URL`、`IMAGE_MODEL=qwen-image-3.0`；`IMAGE_API_KEY` 可回退 `LLM_API_KEY`；`use_mock_image` / 生产校验对齐
- [x] 2. `.env.example` 只改注释与空值默认（不写密钥）
- [x] 3. `ImageProvider.edit` + mock / openai_compat
- [x] 4. 新 `DashScopeImageProvider`（generate + edit + 下载结果 URL）并在 `registry` 注册
- [x] 5. Pipeline `image_to_image` + Worker 分发 + `GenerationJob.kind`
- [x] 6. Schema 表单 + `POST /v1/generate/image-to-image` + Service
- [x] 7. 测试：mock 出图、非法上传、dashscope HTTP mock、回归文生图
- [x] 8. 跑 `pytest`
- [x] 9. 回写 spec 状态为「已完成」

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 业务逻辑不进 `app/api/routes`
- 厂商 SDK 只放 `app/providers`
- 基础设施只通过 `app/ports` 被上层使用
- 不提交 `.env`、密钥、`data/` 产物
- 不接 `qwen-mt-image-2.0` 翻译协议
