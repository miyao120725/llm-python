---
name: implement-feature
description: Implements features along existing FastAPI layers (API, service, pipeline, provider, ports). Use when adding endpoints, generation flows, config, or infrastructure, or when executing an approved spec.
---

# 按分层实现功能

先确认是否大改动。大改动且尚未批准 spec 时，先走 `specs-driven-dev`，不要编码。

## 落点

| 你要做的事 | 改这些 |
| --- | --- |
| 新 HTTP 接口 | `app/schemas/*` → `app/api/routes/*` → `app/api/router.py` |
| 生成任务编排 | `app/services/generation.py`（或新 service），不要放进路由 |
| 扩写/调用模型/落盘 | `app/pipelines/` |
| 新厂商 | 停，改走 `add-provider` |
| 新存储/队列/任务库 | `app/ports/` 接口 → `app/infrastructure/` 实现 → `factory.py` → `config.py` |
| 新领域字段 | `app/domain/models.py`，再映射 schema |
| 新错误 | `app.core.exceptions` 子类，API 不 catch 后重新发明 JSON |
| 配置 | `Settings` + `.env.example`，生产约束放 `validate_runtime` |

装配入口：`app/container.py`。不要在 `main.py` 里 new 依赖。

## 调用链（生成类功能）

```text
route 校验入参/上传
  → GenerationService 建任务、入队、可选 wait
    → Worker 取 Job
      → Pipeline 扩写 + Provider.generate + storage.save
        → TaskStore 更新状态与 MediaObject
```

视频类默认异步；文生图默认同步。不要偷偷改默认。

## 实现检查

- [ ] 路由薄，无厂商 SDK、无直接读写 `data/`
- [ ] 上层不 import `app.infrastructure.*`
- [ ] 有 `AppError` 子类而不是裸 500
- [ ] 上传有大小/类型检查
- [ ] mock 仍可跑通；测试不打真实外网
- [ ] 若改契约：同步 OpenAPI 语义与 `tests/`

## 反例

```python
# ❌ 路由里 httpx.post(settings.video_base_url, ...)
# ✅ VideoProvider 实现 + registry 注册 + pipeline 调用
```
