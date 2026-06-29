# FlowWeaver 阶段N.0：正式路径运行闭环 Smoke

> 文档状态：阶段N.0完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M完成记录
> 适用范围：真实 EngineHost + Avalonia API 客户端的运行闭环 smoke
> 当前执行点：只做正式路径闭环验收，不新增自由画布、动态配置表单或打包能力

## 1. 目标

N.0 的目标是把 L 阶段正式后端 smoke 和 M 阶段 Avalonia 工作流定义闭环连接起来，确认以下路径可以在正式组合根下成立：

```text
启动默认 EngineHost
→ health / token 鉴权
→ Avalonia EngineHostApiClient 查询 node definitions
→ 创建 workflow
→ 读取 workflow detail
→ 校验 draft JSON
→ 使用 base_revision_id 保存新 revision
→ 查询 revisions
→ WebSocket 连接 RuntimeEvent
→ 启动 run
→ 通过 REST 观察 terminal run / node status
→ 通过 WebSocket 和 REST 恢复 RuntimeEvent
→ 查询 TableRef / SharedPublication / AuditEvent 摘要
```

## 2. 与既有阶段的区别

| 阶段 | 已覆盖 | N.0 增量 |
| --- | --- | --- |
| L.3 | 真实 uvicorn EngineHost、HTTP、WebSocket、空库/已有工作流/重启恢复 | 不覆盖 Avalonia `EngineHostApiClient` 的真实后端往返 |
| M.7 | Avalonia ViewModel 级创建、编辑、校验、保存、启动闭环 | 使用 fake API client，不启动真实 EngineHost |
| N.0 | 真实 EngineHost + Avalonia API/WebSocket 客户端 | 证明桌面端通信层可以复现 M.7 闭环 |

## 3. 本阶段修改清单

- 新增 `Avalonia_UI.Tests/EngineHostFormalSmokeTests.cs`
- 新增本阶段完成记录
- 更新 README 当前阶段与下一步建议

本阶段未修改：

- Python 后端产品代码
- Avalonia UI 交互界面
- EngineHost 运行入口
- API 契约

## 4. Smoke 验收点

| 验收点 | 断言 |
| --- | --- |
| 后端启动 | repo-local `python312` 启动真实 uvicorn `create_default_app()` |
| health | `/api/v1/health` 返回 `ok` |
| token | 从临时 `runtime/config/local_api_token` 读取 token 后访问鉴权 API |
| 节点定义 | 返回 Generate / Filter / Publish 三类内置节点 |
| 创建 workflow | 初始空 definition 创建成功，版本为 1 |
| detail | detail revision 与创建返回一致 |
| validate | 可运行 draft JSON 校验通过 |
| save | 使用当前 `base_revision_id` 保存为 version 2 |
| revisions | revision 列表包含 1 和 2 |
| WebSocket | 连接后收到 `ENGINE_READY` |
| start run | 启动 run 使用最新 revision |
| REST 状态 | run 进入 `SUCCEEDED`，三个节点均 `SUCCEEDED` |
| WebSocket 事件 | 观察到 `WORKFLOW_STARTED` 和 `WORKFLOW_FINISHED` |
| REST 事件恢复 | `/api/v1/events` 可按 workflow_run_id 查到运行事件 |
| 数据摘要 | TableRef 发布数、SharedPublication 版本和成员可查询 |
| 审计 | workflow run 相关 AuditEvent 非空 |

## 5. 当前仍不支持

N.0 完成后仍明确不支持：

- 自由画布
- 节点拖拽、连线和布局
- 动态 `config_schema` 表单
- 节点专属配置器
- workflow diff
- revision 回滚
- 真实窗口点击自动化
- UI 托管或自动启停 EngineHost
- 打包发布、安装器、后台服务和自动更新

## 6. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostFormalSmokeTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| N.0 正式路径 smoke | PASS，1 passed |
| Avalonia 全量测试 | PASS，78 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

## 7. 阶段结论

N.0 已完成正式路径运行闭环 smoke。

当前已确认：真实 Python FastAPI EngineHost、Avalonia `EngineHostApiClient`、Avalonia RuntimeEvent WebSocket 客户端和第一阶段内置节点执行路径可以组成最小定义编辑到运行观察闭环。

下一步建议进入 N.1 连接体验稳定化复核，重点处理错误提示、token 错误/轮换/失效、WebSocket 断线提示和脱敏日志边界。仍不建议直接进入自由画布或复杂节点配置表单。
