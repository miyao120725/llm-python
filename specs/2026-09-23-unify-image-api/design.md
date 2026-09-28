# Design: 文生图 / 图生图合并为一个接口

## 方案摘要

只保留 `POST /v1/generate/image`，一律 multipart。有参考图走 `image_to_image`，没有走 `text_to_image`。删除 `/text-to-image`、`/image-to-image`。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API | 是 | `routes/generate.py` | 统一路由，删除旧路径 |
| Schema | 是 | `generate.py` | `ImageGenerateForm` 替换两套请求模型 |
| Service / Pipeline / Provider | 否 | | 复用现有方法 |
| Tests | 是 | `test_generate.py`、`test_runtime.py` | 改打新路径 |
| Docs | 是 | `README.md` | 接口列表与示例 |

## 数据流

```text
POST /v1/generate/image  multipart
  → 有 image 且文件名非空
      → 校验类型/大小 → GenerationService.image_to_image
  → 否则
      → GenerationService.text_to_image
  → GenerationResult（kind 区分）
```

## 关键决策

1. **一个路径、一种编码**：统一 `FormData`。
2. **有无文件分流**：不传 `image` 或空文件名，当文生图。
3. **删除旧路径**：不再兼容 JSON 文生图。
4. **strength**：仅图生图有意义；文生图忽略。

## 接口

### `POST /v1/generate/image`

`multipart/form-data`

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| prompt | string | 必填 | 提示词 |
| image | file | 可选 | 有则图生图 |
| enhance_prompt | bool | false | LLM 扩写 |
| size | string | 空 | `1024x1024` 或 `1024*1024` |
| strength | float | 0.6 | 仅图生图；百炼忽略 |
| async_mode | bool | false | 异步则查任务 |

## 错误处理

沿用 `invalid_upload`、`upload_too_large`、`provider_error`。

## 测试策略

- mock：无图成功、有 png 成功、txt 失败、旧路径 404
- 回归图生视频
- 不打真实外网
