# FlowWeaver 阶段M.5：最小JSON草稿校验

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：节点定义只读 API、workflow detail/revision 客户端、definition 只读视图、创建入口、JSON 草稿校验、保存 revision 与冲突保护和运行闭环验收已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：后续结构化编辑已在 WORKFLOW-EDIT / UX 系列继续推进。

> 文档状态：阶段M.5完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单、阶段M.1至M.4完成记录
> 适用范围：Avalonia UI 中 workflow definition draft JSON 的本地编辑和后端校验
> 当前执行点：只做本地 draft JSON 和 validate，不做正式保存

## 1. 目标

M.5 的目标是在 M.3 只读 definition 视图和 M.4 最小创建入口之后，补上最小 JSON 草稿编辑与校验能力。

本阶段只做：

- 加载 workflow detail 后生成 UI 本地 draft JSON
- 用户可在 `Definition` 页编辑 draft JSON
- `Validate` 调用 `POST /api/v1/workflows/validate`
- 展示 validate 成功、失败和 issues
- JSON 语法错误在 UI 本地拦截，不调用后端
- draft 保持在 UI 内存中，不落库

本阶段不做：

- 不实现 `PUT /api/v1/workflows/{workflow_id}`
- 不保存 workflow definition
- 不创建新 revision
- 不修改 workflow 当前 revision 指针
- 不实现 `base_revision_id` / `expected_version`
- 不处理 revision 冲突
- 不实现节点配置表单或动态 schema 表单
- 不实现自由画布、节点拖拽或连线

## 2. 分层边界

M.5 明确区分三层：

| 层级 | 当前状态 | 是否落库 | 是否创建 revision |
| --- | --- | --- | --- |
| Draft | 已实现，UI 内存中的 JSON 文本 | 否 | 否 |
| Validate | 已实现，调用后端 draft validate | 否 | 否 |
| Save | 未实现，留到 M.6 | 是 | 是 |

当前后端事实：

- `POST /api/v1/workflows/validate` 已存在，可校验未保存 definition
- `PUT /api/v1/workflows/{workflow_id}` 已存在，但请求体尚无 `base_revision_id` / `expected_version`
- 因此 M.5 不应接入 `PUT`，否则可能让旧 revision draft 静默覆盖当前 workflow

## 3. UI边界

`Definition` 页右下区域由只读 `Definition JSON` 调整为：

```text
Draft JSON
Validate
validation message
validation issues
```

交互路径：

```text
Execution tab 选中 workflow
→ Definition tab
→ Details
→ UI 生成 draft JSON
→ 用户编辑 draft JSON
→ Validate
→ 展示后端校验结果
```

约束：

- 切换 workflow 时清空旧 draft
- 只有 draft JSON 非空时 `Validate` 可执行
- JSON 语法错误只显示本地错误，不调用后端
- validate 返回 `valid=false` 时只展示 issues，不保存
- validate 返回 `valid=true` 也不保存

## 4. API边界

新增 Avalonia 客户端方法：

```text
ValidateWorkflowDraftAsync(settings, definition, cancellationToken)
```

请求：

```http
POST /api/v1/workflows/validate
Authorization: Bearer <token>
Content-Type: application/json
```

请求体：

```json
{
  "definition": {
    "schema_version": "1.0",
    "nodes": [],
    "connections": []
  }
}
```

返回 DTO：

```text
WorkflowValidationResultDto
WorkflowValidationIssueDto
```

字段：

| 字段 | 含义 |
| --- | --- |
| `valid` | draft 是否通过后端校验 |
| `errors` | 阻断保存的问题 |
| `warnings` | 非阻断提示，当前后端仍为空数组 |

## 5. 测试覆盖

新增或补充：

- API Client 测试：`ValidateWorkflowDraftAsync` 使用 `POST /api/v1/workflows/validate` 并提交 definition
- ViewModel 测试：加载 definition 后生成 draft JSON
- ViewModel 测试：validate 发送当前 draft JSON
- ViewModel 测试：本地 JSON 语法错误不调用 API
- ViewModel 测试：后端 `valid=false` issues 展示到 UI 状态
- 其它 fake API client 补齐 `ValidateWorkflowDraftAsync` 接口桩

## 6. 验收测试

执行时间：2026-06-29

已运行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostApiClientTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter MainWindowViewModelWorkflowTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| API Client 定向测试 | PASS，22 passed |
| Workflow ViewModel 定向测试 | PASS，18 passed |
| Avalonia 全量测试 | PASS，73 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

备注：

- 并行执行两个 `dotnet test` 时仍可能遇到 `CS2012` DLL 写入锁
- 串行重跑通过
- 全量验收使用串行命令执行，避免测试项目 DLL 写入锁

## 7. 阶段结论

M.5 已完成最小 JSON 草稿校验。

当前 UI 已能编辑 workflow definition draft JSON 并调用后端 validate，但不会保存，也不会创建 revision。

下一步建议进入：

```text
M.6：保存 revision 与冲突保护前置/实现
```

M.6 必须先补后端 `base_revision_id` 或 `expected_version` 检查，再接 Avalonia Save。不得直接使用当前 `PUT /api/v1/workflows/{workflow_id}` 做 UI 保存入口。
