# AI 协作入口

本仓库是 FastAPI 多模态生成服务。助手必须遵守分层、安全边界，并在**大改动时先写 specs 再实现**。

## 先读

| 文档 | 用途 |
| --- | --- |
| [specs/README.md](specs/README.md) | 何时写方案、目录与确认流程 |
| `.cursor/rules/` | 架构、Python、分层、API、Provider、测试、安全 |
| `.cursor/skills/specs-driven-dev/SKILL.md` | 大改动执行流程 |
| `.cursor/skills/implement-feature/SKILL.md` | 代码落点 |
| `.cursor/skills/add-provider/SKILL.md` | 新厂商 |

## 硬性约束

1. 大改动：先 `spec.md` + `design.md` + `tasks.md`，等确认再改 `app/`。
2. 路由不调厂商、不碰基础设施实现；厂商只放 `app/providers`。
3. 禁止提交密钥与 `.env`；测试禁止打真实外网。
4. 生产禁止 mock，必须 Redis 队列与独立 Worker。
5. 回复使用简体中文。

## 小改动

单文件 bug、测试、注释可直接改，并声明「判定为小改动」。
