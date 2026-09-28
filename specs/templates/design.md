# Design: <标题>

## 方案摘要

用一段话说明怎么做。优先最小改动，复用现有端口与工厂，而不是新开平行架构。

## 触及的层

| 层 | 是否改动 | 文件/模块 | 说明 |
| --- | --- | --- | --- |
| API `app/api` | 否 | | |
| Schema `app/schemas` | 否 | | |
| Service `app/services` | 否 | | |
| Pipeline `app/pipelines` | 否 | | |
| Provider `app/providers` | 否 | | |
| Port `app/ports` | 否 | | |
| Infra `app/infrastructure` | 否 | | |
| Domain `app/domain` | 否 | | |
| Config `app/config.py` | 否 | | |
| Worker `app/worker` | 否 | | |
| Tests `tests/` | 否 | | |

## 数据流 / 调用链

```text
客户端
  → API
  → Service
  → Pipeline / Queue
  → Provider / Storage
```

需要时补充序列说明：同步还是异步、任务状态如何变化。

## 关键决策

1. 决策 A：选项、选择、原因
2. 决策 B：

## 接口与模型

新增或变更的 Pydantic / dataclass / Port 方法。没有则写「无契约变更」。

## 错误处理

沿用 `app.core.exceptions.AppError` 子类。列出新错误码、HTTP 状态、用户可见文案。

## 配置

新增环境变量（同步到 `.env.example`）。生产约束写清楚。

## 测试策略

- 单测：覆盖哪条路径
- 必须用 mock provider，禁止测试打真实外网
- 回归：现有 `tests/test_health.py`、`tests/test_generate.py`

## 风险

- 风险与缓解
