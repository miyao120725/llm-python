# Tasks: 文生图 / 图生图合并为一个接口

按依赖顺序排列。未完成的项不要提前改无关文件。

## 实现清单

- [x] 1. Schema：`ImageGenerateForm`，删除旧请求模型
- [x] 2. `POST /v1/generate/image`；删除 `/text-to-image`、`/image-to-image`
- [x] 3. 测试改打新路径；旧路径 404；更新 README 示例
- [x] 4. 跑 `pytest`
- [x] 5. 回写 spec 状态为「已完成」

## 实现中的规则

- 只做 tasks 列出的事；范围外先更新 spec
- 路由只分流，仍调 Service
- 不提交 `.env`、密钥、`data/` 产物
