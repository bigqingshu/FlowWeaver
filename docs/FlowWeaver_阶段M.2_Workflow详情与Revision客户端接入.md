# FlowWeaver 阶段M.2：Workflow详情与Revision客户端接入

> 文档状态：阶段M.2完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单和阶段M.1完成记录
> 适用范围：Avalonia UI 进入 workflow 定义只读视图前的客户端 API 边界
> 当前执行点：只补 Avalonia API Client 对已有 workflow detail / revision 只读端点的接入

## 1. 目标

M.2 的目标是让 Avalonia UI 客户端具备读取 workflow detail 和 revision 历史的 API 能力，为后续 M.3 定义只读视图做准备。

本阶段只做：

- `GetWorkflowAsync()`
- `ListWorkflowRevisionsAsync()`
- `GetWorkflowRevisionAsync()`
- `WorkflowRevisionDto`
- API Client 单元测试
- 既有 ViewModel fake client 接口补齐

本阶段不做：

- 不接 UI 页面或 ViewModel 行为
- 不新增后端 API
- 不实现 workflow 创建、更新、保存或删除
- 不实现 draft validate 客户端入口
- 不实现 revision 冲突保存、防覆盖或 `base_revision_id`
- 不进入节点配置编辑、JSON 编辑器、画布、拖拽或连线

## 2. 客户端接口

新增 Avalonia API Client 方法：

```text
GetWorkflowAsync(settings, workflowId)
ListWorkflowRevisionsAsync(settings, workflowId)
GetWorkflowRevisionAsync(settings, workflowId, revisionId)
```

对应后端现有端点：

```text
GET /api/v1/workflows/{workflow_id}
GET /api/v1/workflows/{workflow_id}/revisions
GET /api/v1/workflows/{workflow_id}/revisions/{revision_id}
```

接口特征：

- 继续使用统一 API envelope
- 继续使用 Bearer token
- `workflowId` 和 `revisionId` 均由客户端 URL escape
- workflow definition 仍以 `JsonElement` 承载
- revision detail 返回独立 `WorkflowRevisionDto`

## 3. DTO边界

新增 DTO：

```text
WorkflowRevisionDto
```

字段：

- `revision_id`
- `workflow_id`
- `version`
- `definition_hash`
- `definition`
- `created_at`
- `created_by`

保留现状：

- `WorkflowDefinitionDto` 继续承载当前 workflow detail
- `definition` 仍保持原始 JSON 结构，不在 M.2 内拆成 UI 编辑模型
- 不新增 validation DTO

## 4. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostApiClientTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| Avalonia API Client 定向测试 | PASS，20 passed |
| Avalonia 全量测试 | PASS，62 passed |
| ruff `src tests` | PASS |

备注：

- 曾并行运行两个 `dotnet test` 导致 `Avalonia_UI.dll` 输出文件被 `VBCSCompiler` 短暂锁定；顺序重跑后通过，不属于代码失败。

## 5. 阶段结论

M.2 已完成。

当前 Avalonia API Client 已具备读取 workflow detail 和 revision 历史的能力，但 UI 尚未展示这些数据。下一步建议进入：

```text
M.3：Workflow definition 只读视图
```

M.3 建议只把已选 workflow 的 definition、revision、definition hash、节点和 connections 以只读方式展示出来，不进入创建、保存或编辑。
