# 多模态生成服务

面向「提示词生成图片」「图片 + 提示词生成视频」「视频生成视频」三条链路，并把大模型作为可插拔能力接入。

开发环境未配置真实 Key 时会回退 mock。`APP_ENV=production` 必须配置真实凭证、API Key、Redis 队列，并独立启动 Worker。

## 架构

```text
客户端
  │  X-API-Key / X-Request-ID
  ▼
API 进程（FastAPI）
  ├── /health/live  /health/ready
  ├── /v1/llm
  ├── /v1/generate   校验后入队
  ├── /v1/tasks/{id}
  └── /v1/media/{id}
          │
          ▼
     JobQueue（memory / Redis）
          │
          ▼
Worker 进程
  └── Pipeline → Provider → ObjectStorage
          │
          ▼
   TaskStore（SQLite） + Storage（本地 / S3）
```

| 层 | 目录 | 作用 |
| --- | --- | --- |
| API | `app/api` | HTTP、鉴权、request_id |
| Service | `app/services` | 建任务、存上传、入队 |
| Worker | `app/worker` | 消费队列并执行生成 |
| Pipeline | `app/pipelines` | 扩写 → 调模型 → 落盘 |
| Provider | `app/providers` | 厂商适配 |
| Ports / Infra | `app/ports`, `app/infrastructure` | 存储、任务库、队列实现 |

本地默认 `QUEUE_BACKEND=memory` 且内嵌 Worker，一条命令即可联调。生产必须 `QUEUE_BACKEND=redis` 且 `python -m app.worker` 单独跑。

## 快速开始

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
python -m app.main
```

文档：`http://127.0.0.1:8000/docs`。探针：`/health/live`、`/health/ready`。

拆开 API 与 Worker（需要 Redis）：

```bash
docker compose up --build
```

请求头加 `X-API-Key: dev-key`。本机不走 Docker 时：

```bash
# 终端 1
set QUEUE_BACKEND=redis
set EMBEDDED_WORKER=false
python -m app.main

# 终端 2
python -m app.worker
```

## 接口

- `GET /health/live` / `GET /health/ready`：存活与就绪
- `GET /v1/health`：当前 provider 与是否 mock
- `POST /v1/llm/chat`、`POST /v1/llm/enhance-prompt`
- `POST /v1/generate/image`（multipart；可选上传参考图）
- `POST /v1/generate/video`（multipart；可选上传参考图/参考视频）
- `GET /v1/tasks/{task_id}`
- `GET /v1/media/{file_id}`

```bash
curl -X POST http://127.0.0.1:8000/v1/generate/image ^
  -F "prompt=雨夜霓虹街头的猫" ^
  -F "enhance_prompt=true" ^
  -F "async_mode=false"
```

视频接口默认 `async_mode=true`，成片 2～10 秒，用 `GET /v1/tasks/{task_id}` 轮询。

## 生产约束

`APP_ENV=production` 启动时会校验：

- 必须配置 `API_KEYS`
- 禁止 mock，必须有 LLM / 图片 / 视频真实凭证
- `QUEUE_BACKEND=redis`，且 `EMBEDDED_WORKER` 不能为 true
- 使用 S3 时必须配置 `S3_BUCKET`

对象存储切 S3：

```env
STORAGE_BACKEND=s3
S3_BUCKET=your-bucket
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
S3_ENDPOINT_URL=https://oss-example.com
```

并安装 `pip install .[s3]`。

## 接入真实模型

复制 `.env.example` 后填写 `LLM_*` / `IMAGE_*` / `VIDEO_*`。视频 HTTP 适配器约定：

1. `POST` 使用 multipart：图生视频为 `prompt` + `image`，视频生视频为 `prompt` + `video`
2. 同步返回 `video_url` 或 `video_b64`
3. 异步返回 `task_id`，按 `VIDEO_TASK_PATH` 轮询

新厂商：在 `app/providers/` 实现并到 `registry.py` 注册。
