# FlowWeaver 阶段M.4：最小创建入口

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：节点定义只读 API、workflow detail/revision 客户端、definition 只读视图、创建入口、JSON 草稿校验、保存 revision 与冲突保护和运行闭环验收已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：后续结构化编辑已在 WORKFLOW-EDIT / UX 系列继续推进。

> 文档状态：阶段M.4完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单、阶段M.1、M.2和M.3完成记录
> 适用范围：Avalonia UI 中从固定模板创建 workflow 的最小入口
> 当前执行点：只创建内置模板 workflow、刷新列表并选中新建项

## 1. 目标

M.4 的目标是在不进入自由画布、节点配置编辑和正式保存冲突处理的前提下，让桌面 UI 可以从一个固定内置模板创建 workflow。

本阶段只做：

- Avalonia API Client 接入已有 `POST /api/v1/workflows`
- 在 `Execution` 页 Workflows 面板加入 workflow name 输入框
- 加入 `Create` 按钮
- 使用固定 Generate + Filter 内置节点模板创建 workflow
- 创建成功后刷新 workflow 列表
- 刷新后选中新创建 workflow
- 展示创建失败时的 API envelope 错误

本阶段不做：

- 不新增后端 API
- 不实现自由画布
- 不实现节点拖拽、连线或布局
- 不实现节点配置表单
- 不实现 JSON 配置编辑
- 不实现 draft validate
- 不实现 `PUT /workflows/{workflow_id}`
- 不实现 revision 冲突保护
- 不实现删除、复制、导入或导出 workflow

## 2. 模板边界

当前内置模板固定为：

```text
GenerateTestTableNode
→ FilterRowsNode
```

模板内容：

| 节点 | node_instance_id | 作用 |
| --- | --- | --- |
| `GenerateTestTableNode` | `generate` | 生成包含 `row_id` 和 `amount` 的 3 行测试表 |
| `FilterRowsNode` | `filter` | 保留 `amount > 1.0` 的行 |

连接：

| connection_id | source | target |
| --- | --- | --- |
| `generate_to_filter` | `generate.out` | `filter.in` |

说明：

- 模板只作为 M.4 最小创建入口使用
- 模板不代表最终 UI 编辑模型
- 模板不暴露为后端固定契约
- 模板不含 SharedPublication 节点，避免 M.4 过早进入共享发布配置

## 3. UI边界

Workflows 面板新增一行：

```text
Workflow name 输入框 + Create 按钮
```

交互路径：

```text
输入 workflow name
→ Create
→ POST /api/v1/workflows
→ 刷新 workflow list
→ 选中新创建 workflow
```

约束：

- workflow name 为空时 `Create` 不可执行
- 创建中、刷新中或启动 workflow 中统一进入 workflow busy 状态
- 创建失败时不清空现有 workflow list
- 创建成功后的最终提示以刷新结果为准

## 4. API边界

新增 Avalonia 客户端方法：

```text
CreateWorkflowAsync(settings, name, definition, cancellationToken)
```

请求：

```http
POST /api/v1/workflows
Authorization: Bearer <token>
Content-Type: application/json
```

请求体：

```json
{
  "name": "<workflow name>",
  "definition": {
    "schema_version": "1.0",
    "nodes": [],
    "connections": []
  }
}
```

返回沿用 `WorkflowDefinitionDto`。

M.4 不调用：

```text
POST /api/v1/workflow-definitions/validate
PUT /api/v1/workflows/{workflow_id}
DELETE /api/v1/workflows/{workflow_id}
```

## 5. 测试覆盖

新增或补充：

- API Client 测试：`CreateWorkflowAsync` 使用 `POST /api/v1/workflows`，附带 Bearer token，并提交 `name` 和 `definition`
- ViewModel 测试：创建模板 workflow 后刷新列表并选中新建 workflow
- ViewModel 测试：空 workflow name 时 `Create` 不可执行
- ViewModel 测试：创建失败 envelope 能展示错误信息
- 既有 fake API client 补齐 `CreateWorkflowAsync` 接口实现

## 6. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter MainWindowViewModelWorkflowTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostApiClientTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| Workflow ViewModel 定向测试 | PASS，15 passed |
| API Client 定向测试 | PASS，21 passed |
| Avalonia 全量测试 | PASS，69 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

备注：

- 曾在并行执行两个 `dotnet test` 时出现一次 `CS2012` DLL 写入锁，串行重跑后通过
- 全量验收使用串行命令执行，避免测试项目 DLL 写入锁

## 7. 阶段结论

M.4 已完成最小创建入口。

当前 UI 已能从固定内置模板创建 workflow，并在创建后刷新列表、选中新建 workflow。

下一步建议进入：

```text
M.5：最小 JSON 配置编辑前置分析/小步
```

M.5 建议先分析草稿、校验和正式保存边界，再决定是否进入 JSON 文本编辑与 validate。正式保存前仍必须处理 revision 冲突保护，避免旧 revision 静默覆盖。
