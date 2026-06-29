# FlowWeaver 阶段M.7：工作流定义与运行闭环验收

> 文档状态：阶段M.7完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单、阶段M.1至M.6完成记录
> 适用范围：Avalonia UI 工作流定义入口到运行观察的闭环验收
> 当前执行点：只做闭环验收与文档复核，不新增自由画布、动态表单或节点能力

## 1. 目标

M.7 的目标是确认阶段M已经形成一个最小可用闭环：

```text
创建 workflow
→ 加载 definition
→ 编辑 draft JSON
→ validate
→ save 新 revision
→ 启动 run
→ 查询 run / node status
```

本阶段只做：

- 补充 ViewModel 级闭环验收测试
- 固化阶段M.1至M.7完成矩阵
- 明确当前仍不支持的 UI 能力
- 更新 README 当前阶段与下一步建议

本阶段不做：

- 不实现自由画布
- 不实现节点拖拽、连线或布局
- 不实现动态 `config_schema` 表单
- 不实现专属节点配置器
- 不实现 workflow diff
- 不实现 revision 回滚
- 不实现真实窗口自动化脚本
- 不新增后端 API

## 2. M阶段完成矩阵

| 小步 | 状态 | 主要产出 |
| --- | --- | --- |
| M.0 | 完成 | 工作流定义与节点配置入口边界清单 |
| M.1 | 完成 | `GET /api/v1/node-definitions` 和 Avalonia 客户端 DTO |
| M.2 | 完成 | workflow detail / revisions / revision detail 客户端接入 |
| M.3 | 完成 | Definition 页只读展示 nodes、connections、revisions、raw JSON |
| M.4 | 完成 | 固定模板创建 workflow，并刷新选中新建项 |
| M.5 | 完成 | Draft JSON 编辑与 `POST /api/v1/workflows/validate` |
| M.6 | 完成 | 带 `base_revision_id` 保存 revision 与冲突保护 |
| M.7 | 完成 | 创建、编辑、校验、保存、启动、状态观察闭环验收 |

## 3. 闭环验收路径

M.7 新增 ViewModel 测试覆盖以下路径：

```text
CreateTemplateWorkflowCommand
→ LoadSelectedWorkflowDefinitionCommand
→ 编辑 WorkflowDefinitionDraftJson
→ ValidateWorkflowDefinitionDraftCommand
→ SaveWorkflowDefinitionDraftCommand
→ StartSelectedWorkflowCommand
→ RefreshNodeRunsCommand
```

验收点：

| 验收点 | 断言 |
| --- | --- |
| 创建 | API 收到 workflow name 和模板 definition |
| 加载 | UI 持有当前 workflow detail 和 draft JSON |
| 校验 | API 收到用户编辑后的 draft JSON |
| 保存 | API 收到 `base_revision_id = 当前 detail revision` |
| 刷新 | 保存后 detail 更新到新 revision |
| 启动 | workflow run 启动并选中新 run |
| 状态观察 | node run 列表可刷新并展示节点状态 |

## 4. 当前明确不支持

阶段M完成后仍明确不支持：

- 自由画布
- 节点拖拽和连线
- 动态配置表单
- `config_schema`
- 节点专属配置器
- workflow diff
- revision 回滚
- 多人协同编辑
- 批量编辑
- 打包发布

这些能力应作为后续阶段单独拆分，不应混入 M.7 验收。

## 5. 下一阶段建议

M阶段后，建议先做一个进入下一阶段前的边界分析，而不是立刻进入大 UI 功能。

较稳方向：

| 候选方向 | 说明 |
| --- | --- |
| N.0 运行闭环 smoke | 用正式后端路径验证 UI 创建、保存、启动、事件/REST恢复 |
| N.1 连接体验稳定化 | 错误提示、token失效、WebSocket断线提示和脱敏复核 |
| N.2 打包发布前置清单 | 后端启动方式、runtime目录、token、日志、配置迁移 |
| N.3 配置编辑体验小步 | 在 JSON 基础上为少数内置节点提供轻量表单 |

当前最建议先做：

```text
N.0：正式路径运行闭环 smoke 清单与执行
```

原因：

- M阶段已经具备最小定义编辑闭环
- 下一步应该确认真实 EngineHost + Avalonia API 路径是否能复现闭环
- 若真实路径发现后端组合根、API、事件恢复或 UI 状态问题，应先修基础链路

## 6. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter MainWindowViewModelWorkflowTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| Workflow ViewModel 定向测试 | PASS，21 passed |
| Avalonia 全量测试 | PASS，77 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

备注：

- 新增闭环验收测试不依赖真实窗口自动化
- 本阶段未修改 Python 源码，仍执行 ruff 保持第一阶段验收基线

## 7. 阶段结论

M.7 已完成工作流定义与运行闭环验收。

阶段M现在已经从“只读观察已有 workflow”推进到“创建、查看、编辑 draft、校验、保存、启动并观察运行状态”的最小可用闭环。下一阶段建议先做正式路径 smoke，而不是直接进入自由画布或复杂配置表单。
