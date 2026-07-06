# FlowWeaver 阶段M.3：Workflow定义只读视图

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：节点定义只读 API、workflow detail/revision 客户端、definition 只读视图、创建入口、JSON 草稿校验、保存 revision 与冲突保护和运行闭环验收已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：后续结构化编辑已在 WORKFLOW-EDIT / UX 系列继续推进。

> 文档状态：阶段M.3完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单、阶段M.1和M.2完成记录
> 适用范围：Avalonia UI 中 workflow definition 的只读查看能力
> 当前执行点：只展示 workflow detail、revision、节点、连接和原始 definition JSON

## 1. 目标

M.3 的目标是在 Avalonia UI 中提供 workflow definition 的只读视图，让用户能从已选 workflow 查看当前 definition 和 revision 历史，为后续最小创建、配置编辑和保存前置。

本阶段只做：

- 新增 `Definition` tab
- 读取已选 workflow detail
- 读取 workflow revisions
- 展示 workflow name、version、revision、definition hash、status、updated time
- 展示 revision 列表
- 展示 definition 中的 nodes
- 展示 definition 中的 connections
- 展示格式化后的原始 definition JSON

本阶段不做：

- 不新增后端 API
- 不新增 workflow 创建、更新、保存或删除
- 不实现 draft validate
- 不实现 `base_revision_id` / revision 冲突保存
- 不实现节点配置编辑
- 不实现画布、拖拽、连线或布局算法
- 不把 revision 列表变成可编辑历史回滚入口

## 2. UI边界

新增 `Definition` tab，采用两列只读布局：

| 区域 | 内容 |
| --- | --- |
| 左侧 | Load Details 按钮、workflow 摘要、revision 列表、加载/错误状态 |
| 右侧上 | nodes 列表 |
| 右侧中 | connections 列表 |
| 右侧下 | 原始 definition JSON |

用户路径：

```text
Execution tab 选中 workflow
→ Definition tab
→ Details
→ 查看当前 workflow definition
```

说明：

- `Details` 只读取数据，不修改 workflow
- 切换 selected workflow 时会清空旧 definition detail，避免误读
- 原始 JSON 为只读 `TextBox`
- nodes / connections 从当前 workflow detail 的 `definition` JSON 解析

## 3. ViewModel边界

新增：

```text
WorkflowDefinitionDetailViewModel
WorkflowDefinitionNodeListItemViewModel
WorkflowDefinitionConnectionListItemViewModel
WorkflowRevisionListItemViewModel
```

`MainWindowViewModel` 新增状态：

- `WorkflowDefinitionDetail`
- `WorkflowDefinitionMessage`
- `WorkflowDefinitionErrorMessage`
- `IsLoadingWorkflowDefinition`
- `HasWorkflowDefinition`
- `HasWorkflowDefinitionError`

新增命令：

```text
LoadSelectedWorkflowDefinitionCommand
```

该命令调用：

```text
GetWorkflowAsync()
ListWorkflowRevisionsAsync()
```

M.3 不调用：

```text
GetWorkflowRevisionAsync()
POST /validate
PUT /workflows/{workflow_id}
POST /workflows
```

## 4. 验收测试

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
| Workflow ViewModel 定向测试 | PASS，12 passed |
| Avalonia 全量测试 | PASS，65 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

备注：

- 测试覆盖成功加载 definition、nodes、connections、revisions
- 测试覆盖 detail API 失败时的错误状态
- 测试覆盖未选择 workflow 时加载按钮不可用

## 5. 阶段结论

M.3 已完成。

当前 UI 已能只读查看 workflow definition。下一步建议进入：

```text
M.4：最小创建入口
```

M.4 建议只从内置模板创建 workflow 并刷新列表，不进入自由画布、节点配置编辑或保存冲突处理。
