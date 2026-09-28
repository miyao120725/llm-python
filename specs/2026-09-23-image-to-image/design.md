# Design: 百炼千问图像（文生图 + 图生图）

## 方案摘要

图像默认改接百炼 DashScope 原生 multimodal-generation，模型 `qwen-image-3.0`（文生图与图生图同一接口，有无 `image` 字段区分）。新增图生图任务，形状对齐图生视频（multipart），默认同步对齐文生图。`qwen-mt-image-2.0` 是翻译模型，本期不接。OpenAI 兼容 Provider 保留。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API `app/api` | 是 | `routes/generate.py` | `POST /image-to-image` |
| Schema `app/schemas` | 是 | `generate.py` | 图生图表单 |
| Service `app/services` | 是 | `generation.py` | 建任务入队 |
| Pipeline `app/pipelines` | 是 | 新 `image_to_image.py` | 扩写 + edit + 落盘 |
| Provider `app/providers` | 是 | `image/dashscope.py`（新）、`base.py`、`mock.py`、`openai_compat.py`、`registry.py` | dashscope + `edit` |
| Config | 是 | `config.py`、`.env.example` | 默认 dashscope / qwen-image-3.0；Key 可复用 LLM |
| Port / Infra | 否 | | 复用存储与任务 |
| Domain | 是 | `GenerationJob.kind` | 增加 `image_to_image` |
| Worker | 是 | `runner.py` | 分发 `image_to_image` |
| Tests | 是 | `test_generate.py`、新 `test_dashscope_image.py` | mock 上传 + HTTP mock |

## 数据流 / 调用链

```text
POST /v1/generate/text-to-image  JSON
  → GenerationService 建 task(kind=text_to_image)
    → Pipeline：可选 enhance_prompt
      → ImageProvider.generate(prompt, size)
      → 若 dashscope：POST multimodal-generation（仅 text）
      → 下载 output.choices[0].message.content[].image
      → storage.save → media.url

POST /v1/generate/image-to-image  multipart
  → 校验类型/大小
  → GenerationService 建 task(kind=image_to_image)
    → Pipeline：可选 enhance_prompt(mode=image)
      → ImageProvider.edit(prompt, image_blob, size, strength)
      → 若 dashscope：content = [data URI image, text]
      → 同上落盘
```

## 关键决策

1. **模型名**：默认 `qwen-image-3.0`（用户确认）。`IMAGE_MODEL` 可换成 `qwen-image-3.0-pro`。不接 `qwen-mt-image-2.0`。
2. **协议**：不用 OpenAI `/images/generations`。百炼图像是 `POST /api/v1/services/aigc/multimodal-generation/generation`，`Authorization: Bearer`。
3. **地域**：默认国内站 `https://dashscope.aliyuncs.com/api/v1`，与现有 LLM 国内站一致。国际站改 `IMAGE_BASE_URL`。不在代码里写 Workspace 专属域名。
4. **参考图**：本地上传转 `data:{content_type};base64,...`，不先传到公网。
5. **结果图**：响应只有 24h URL，Provider 立刻 GET 成字节再落盘。
6. **size**：对外仍接受 `1024x1024`；发往百炼时把 `x`/`X` 换成 `*`。空则用 `IMAGE_SIZE`。
7. **strength**：百炼无此参数，dashscope 忽略；openai_compat edits 同样可忽略。
8. **双重改写 / 思考**：3.0 默认 `prompt_extend=true` 且 `enable_thinking=true`（思考依赖改写，耗时更长）。本期固定 `prompt_extend=false`、`enable_thinking=false`、`watermark=false`，避免和本服务 `enhance_prompt` 叠两层，也避免同步接口超时。本服务 `enhance_prompt` 仍走 LLM。
9. **Key**：`use_mock_image()` 在 `image_provider==dashscope` 时，无 `IMAGE_API_KEY` 则看 `LLM_API_KEY`。生产校验仍要求最终能解析出真实图像 Key（复用后的值）。
10. **路径**：图生图 `/v1/generate/image-to-image`，不和文生图挤同一个 JSON。
11. **默认同步**：与文生图一致。
12. **openai_compat**：保留；`edit` 走 `/images/edits`。默认不再指向它。

## 接口与模型

### 配置（`.env.example` 注释 + 空值）

```text
IMAGE_PROVIDER=dashscope
IMAGE_BASE_URL=https://dashscope.aliyuncs.com/api/v1
IMAGE_API_KEY=
IMAGE_MODEL=qwen-image-3.0
IMAGE_SIZE=1024*1024
```

`IMAGE_API_KEY` 可留空，本地与 `LLM_API_KEY` 共用一把百炼 Key。

### 已有 `POST /v1/generate/text-to-image`

契约不变。换默认 Provider 后，有 Key 时出真实图。

### 新增 `POST /v1/generate/image-to-image`

`multipart/form-data`

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| image | file | 必填 | png/jpeg/webp |
| prompt | string | 必填 | 如何改图 |
| enhance_prompt | bool | false | 本服务 LLM 扩写 |
| size | string | 空 | `1024x1024` 或 `1024*1024` |
| strength | float | 0.6 | 0～1；百炼忽略 |
| async_mode | bool | false | 异步则查任务 |

响应复用 `GenerationResult`，`kind=image_to_image`。

### Provider

```text
generate(prompt, size=) -> ImageResult
edit(prompt, image: MediaBlob, *, size=None, strength=0.6) -> ImageResult
```

base 默认 `edit` 可转调 `generate`（忽略参考图）。mock / dashscope / openai_compat 显式实现。

dashscope 请求体要点：

```json
{
  "model": "qwen-image-3.0",
  "input": {
    "messages": [
      {
        "role": "user",
        "content": [
          {"image": "data:image/png;base64,..."},
          {"text": "改成赛博朋克"}
        ]
      }
    ]
  },
  "parameters": {
    "prompt_extend": false,
    "enable_thinking": false,
    "watermark": false,
    "size": "1024*1024"
  }
}
```

文生图去掉 `content` 里的 `image`。从 `output.choices[0].message.content` 取第一项 `image` URL。

HTTP 非 2xx 或 body 带 `code` 时包装为 `ProviderError`，不回传 Authorization。

## 错误处理

沿用 `invalid_upload`、`upload_too_large`、`provider_error`。无新错误码。

## 测试策略

- mock：合法 png 同步成功，有 `media.url`
- 上传 txt → 400 `invalid_upload`
- dashscope：httpx mock 固定 JSON + 假图像 URL，再 mock 下载字节
- 回归文生图、图生视频
- 禁止打真实外网

## 风险

- 未配任何百炼 Key 时仍是占位图（与现在一致）
- `qwen-image-3.0` 默认同步可能超过 30s（尤其厂商思考开启时）；本期关掉厂商思考，超时仍用 `SYNC_WAIT_TIMEOUT_SECONDS=180`
- 若改成 `qwen-mt-image-2.0`，调用会失败（缺源/目标语种）；翻译另开 spec
