# Tasks: 百炼 wan3.0-video 统一生视频

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. Settings：默认 `VIDEO_PROVIDER=dashscope`、`VIDEO_MODEL=wan3.0-video`、Key 可复用 LLM；轮询默认 15s / 600s；`.env.example` 只改注释与空值
- [x] 2. `VIDEO_TYPES` 增加 mov；`GenerationJob` 分开 image / video 输入
- [x] 3. `VideoProvider.synthesize` + mock / http 转调
- [x] 4. `DashScopeVideoProvider`（上传策略、建任务、轮询、无鉴权下载）并注册
- [x] 5. Pipeline + Service + Worker 支持四种 kind
- [x] 6. `POST /v1/generate/video`；删除旧两条路径
- [x] 7. 测试：四种 mock、非法上传、dashscope HTTP mock、旧路径 404
- [x] 8. 跑 `pytest`
- [x] 9. 回写 spec 状态为「已完成」

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 厂商协议只放 `app/providers`
- 不提交 `.env`、密钥、`data/` 产物
- 不接音频 / 文档 / 首尾帧双图
