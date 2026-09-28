# Design: 百炼 wan3.0-video 统一生视频

## 方案摘要

视频默认改接百炼 DashScope 异步 `video-synthesis`，模型 `wan3.0-video`。对外只保留 `POST /v1/generate/video`，按有无图/视频映射四种万相用法。删除旧 `/image-to-video`、`/video-to-video`。图可用 Base64；视频必须先传到百炼临时 OSS。下载结果不带 Bearer。

## 触及的层

| 层 | 是否改动 | 文件 | 说明 |
| --- | --- | --- | --- |
| API | 是 | `routes/generate.py` | 新 `/video`；删除旧路径 |
| Schema | 是 | `generate.py` | `VideoGenerateForm` |
| Service | 是 | `generation.py` | 统一 `generate_video` |
| Pipeline | 是 | 新 `video_generate.py`（或扩展现有） | 一种 run，图/视频可选 |
| Provider | 是 | 新 `video/dashscope.py`、`base.py`、`mock.py`、`registry.py` | `synthesize` |
| Domain | 是 | `GenerationJob` | 分开记录 image / video 输入 |
| Config | 是 | `config.py`、`.env.example` | dashscope / wan3.0-video / Key 复用 |
| Worker | 是 | `runner.py` | 分发四种 kind |
| Tests | 是 | `test_generate.py`、新 `test_dashscope_video.py` | mock + HTTP mock |

## 数据流

```text
POST /v1/generate/video  multipart
  → 校验已上传文件的类型/大小
  → GenerationService 建 task(kind=按组合) 入队
    → Pipeline：可选 enhance_prompt(mode=video)
      → VideoProvider.synthesize(prompt, image=, video=, duration, resolution, ratio)
        → 有视频：getPolicy + OSS 上传 → oss://...
        → POST video-synthesis（Header: Async + 必要时 OssResourceResolve）
        → GET /tasks/{id} 直到 SUCCEEDED
        → 无鉴权下载 video_url
      → storage.save → media.url
```

## 关键决策

1. **一个路径**：对齐出图 `/generate/image`，客户端只记 `/generate/video`。
2. **仅图用 first_frame**：像素级当首帧；图+视频必须改用 `reference_*`，否则万相 400（互斥）。
3. **本服务默认同 async**：厂商本身只能异步；`async_mode` 默认 `true`。同步等结果时超时跟 `VIDEO_POLL_TIMEOUT_SECONDS`（默认 600）。
4. **轮询 15s**：跟官方建议一致，避免打满查询 RPS。
5. **Key**：dashscope 时 `VIDEO_API_KEY` 空则复用 `LLM_API_KEY`；`use_mock_video` 看解析后的 Key，不再要求单独 `VIDEO_BASE_URL` 才不算 mock。
6. **下载**：独立无 Bearer 客户端（与出图 OSS 403 同类问题）。
7. **保留 HttpVideoProvider**：`VIDEO_PROVIDER=http` 仍可用。
8. **旧路径删除**：不再兼容 `/image-to-video`、`/video-to-video`。

## 接口

### `POST /v1/generate/video`

`multipart/form-data`

| 字段 | 类型 | 默认 | 说明 |
| --- | --- | --- | --- |
| prompt | string | 必填 | 提示词 |
| image | file | 可选 | png/jpeg/webp |
| video | file | 可选 | mp4/mov（webm 仅 mock；真机万相可能拒） |
| enhance_prompt | bool | false | 本服务 LLM 扩写 |
| duration_seconds | float | 5 | 2～10 |
| resolution | string | 720P | 480P / 720P / 1080P |
| ratio | string | adaptive | 万相 ratio |
| async_mode | bool | true | false 则阻塞等到成片或超时 |

响应仍是 `GenerationResult`。

客户端：

```js
const form = new FormData();
form.append("prompt", prompt);
if (imageFile) form.append("image", imageFile);
if (videoFile) form.append("video", videoFile);
const { task_id, status, media } = await fetch("/v1/generate/video", { method: "POST", body: form }).then(r => r.json());
if (status !== "succeeded") {
  // 轮询 GET /v1/tasks/{task_id}
}
videoEl.src = API + media.url;
```

### 万相请求要点

```json
{
  "model": "wan3.0-video",
  "input": {
    "prompt": "...",
    "media": [
      {"type": "reference_image", "url": "data:image/png;base64,..."},
      {"type": "reference_video", "url": "oss://dashscope-instant/..."}
    ]
  },
  "parameters": {
    "resolution": "720P",
    "ratio": "adaptive",
    "duration": 5,
    "prompt_extend": false,
    "watermark": false
  }
}
```

文生视频去掉 `media`。仅图时 `media` 只有 `first_frame`。

## Provider

```text
synthesize(prompt, *, image=None, video=None, duration_seconds=5, resolution="720P", ratio="adaptive") -> VideoResult
```

base 上 `image_to_video` / `video_to_video` 转调 `synthesize`，避免旧 Pipeline 立刻全拆。

## 错误处理

沿用 `invalid_upload`、`upload_too_large`、`provider_error`。厂商 `FAILED` 只回 `code` + 截断 message，不带 URL 查询串。

## 测试策略

- mock 四种组合 + 非法上传
- dashscope：mock getPolicy/OSS/synthesis/poll/download
- 回归旧两条路径
- 禁止打外网

## 风险

- 万相 3.0 可能仍是邀测，Key 无权限会 `provider_error`
- 成片远长于 180s；客户端必须按异步轮询，不要当出图那样默认同步死等
- 参考视频要 mp4/mov、1～15 秒；不符由厂商失败
- 临时 OSS 上传凭证接口有 QPS 限制；本期单请求内传 1 段视频可接受
