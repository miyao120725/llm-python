---
name: add-provider
description: Adds a pluggable LLM, image, or video provider with mock fallback and registry wiring. Use when integrating a vendor such as Kling, Runway, Tongyi, OpenAI, or when the user mentions 厂商, provider, registry.
---

# 新增模型厂商

只加 Provider 适配，不改 API 形状，除非 spec 明确要新字段。

大改动：先完成 `specs-driven-dev` 并获得确认。

## 步骤

复制并勾选：

```
- [ ] 1. 选定类型：llm | image | video
- [ ] 2. 在 app/providers/<kind>/ 新增实现，继承对应 base
- [ ] 3. 补 mock（若行为与现有 mock 不同）或确认现有 mock 仍可用
- [ ] 4. Settings 增加必要项（base_url/api_key/model/path），写入 .env.example
- [ ] 5. 在 registry.build_providers 增加分支
- [ ] 6. 无 Key 时仍回退 mock（allow_mock_providers）
- [ ] 7. 生产 validate_runtime 仍禁止 mock
- [ ] 8. 测试用 mock 覆盖原链路，不打真实厂商
```

## 实现要点

- 类放 `app/providers/llm/`、`image/` 或 `video/`
- 构造参数来自 `Settings`，不要在类里写死密钥
- 把厂商 JSON 转成管道需要的结果：`str` / 图片字节 / 视频字节或 URL
- HTTP 视频协议优先扩展 `HttpVideoProvider`；协议差再新开类
- `aclose()` 关闭 httpx client
- `name`、`model`、`mocked` 供 `/v1/health` 展示

## 注册示例

```python
elif settings.video_provider == "kling":
    video = KlingVideoProvider(...)
else:
    raise ValueError(f"不支持的 Video provider: {settings.video_provider}")
```

未知名字要失败，不要静默落到错误厂商。

## 不要做

- 不要在 `routes` / `services` 里 `if settings.video_provider ==`
- 不要为了接厂商改 `/v1/generate/*` 的表单字段，除非 spec 批准
- 不要删除 mock 回退
- 不要把厂商错误原文（含密钥）返回给客户端；包装为 `ProviderError`
