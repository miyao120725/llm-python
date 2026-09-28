# Tasks: <标题>

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [ ] 1. 按 design 创建/修改模块 A
- [ ] 2. 接线（router / container / registry / factory）
- [ ] 3. 更新 schema / 错误码 / `.env.example`
- [ ] 4. 补充或更新测试
- [ ] 5. 跑 `pytest`，必要时手动验证 `/v1/health` 与相关接口
- [ ] 6. 回写 spec 状态为「已完成」，核对验收标准

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 业务逻辑不进 `app/api/routes`
- 厂商 SDK 只放 `app/providers`
- 基础设施只通过 `app/ports` 被上层使用
- 不提交 `.env`、密钥、`data/` 产物
