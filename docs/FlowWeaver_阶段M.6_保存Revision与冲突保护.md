# FlowWeaver 阶段M.6：保存Revision与冲突保护

> 文档状态：阶段M.6完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单、阶段M.1至M.5完成记录
> 适用范围：workflow definition draft 的正式保存与 revision 并发保护
> 当前执行点：先补后端冲突保护，再接 Avalonia Save

## 1. 目标

M.6 的目标是在 M.5 本地 draft JSON + validate 的基础上，补齐正式保存的最小闭环，并防止旧 revision draft 静默覆盖当前 workflow。

本阶段只做：

- `PUT /api/v1/workflows/{workflow_id}` 请求体新增 `base_revision_id`
- 缺少 `base_revision_id` 时拒绝保存
- 当前 workflow revision 已变化时返回 `WORKFLOW_REVISION_CONFLICT`
- Avalonia API Client 新增 `UpdateWorkflowAsync`
- Definition 页新增 `Save`
- UI 保存时使用当前 detail 的 `RevisionId` 作为 `base_revision_id`
- 保存成功后刷新 workflow 列表并重新加载 detail

本阶段不做：

- 不实现自由画布
- 不实现节点拖拽、连线或布局
- 不实现复杂表单或动态 schema 表单
- 不实现多人协同合并
- 不实现 workflow diff
- 不实现历史 revision 回滚
- 不实现批量编辑

## 2. 后端保存边界

请求：

```http
PUT /api/v1/workflows/{workflow_id}
Authorization: Bearer <token>
Content-Type: application/json
```

请求体：

```json
{
  "base_revision_id": "rev-current",
  "name": "Workflow name",
  "definition": {
    "schema_version": "1.0",
    "nodes": [],
    "connections": []
  }
}
```

处理规则：

| 场景 | 结果 |
| --- | --- |
| `base_revision_id` 缺失 | `400 BASE_REVISION_REQUIRED` |
| workflow 不存在 | `404 WORKFLOW_NOT_FOUND` |
| definition 不合法 | `422 WORKFLOW_VALIDATION_FAILED` |
| 当前 revision 与 `base_revision_id` 不一致 | `409 WORKFLOW_REVISION_CONFLICT` |
| 校验通过且 revision 未变化 | 创建新 revision，更新 current revision |

冲突响应 details：

```json
{
  "workflow_id": "wf",
  "expected_revision_id": "rev-old",
  "current_revision_id": "rev-new"
}
```

## 3. Store边界

`RuntimeStore.update_workflow_definition()` 新增：

```text
base_revision_id: str | None
```

当 `base_revision_id` 与 `workflow.current_revision_id` 不一致时返回：

```text
WorkflowRevisionConflict
```

说明：

- workflow revision 仍不可变
- 保存 definition 时仍创建新 revision
- legacy `workflow_definitions` 表继续同步当前版本
- workflow run 仍绑定保存时明确的 revision

## 4. UI边界

`Definition` 页 Draft JSON 区域新增：

```text
Validate
Save
```

保存路径：

```text
Load Details
→ 生成 draft JSON
→ 用户编辑 draft JSON
→ Save
→ 解析 JSON
→ PUT /api/v1/workflows/{workflow_id}
   base_revision_id = 当前 WorkflowDefinitionDetail.RevisionId
→ 成功后刷新 workflow list
→ 重新加载 definition detail
```

失败处理：

- JSON 语法错误：本地拒绝，不调用 API
- `WORKFLOW_REVISION_CONFLICT`：显示错误，不清空 draft
- 其它 envelope 错误：显示错误，不清空 draft

## 5. 测试覆盖

新增或补充：

- 后端 API：更新 workflow 必须携带 `base_revision_id`
- 后端 API：旧 `base_revision_id` 保存返回 `WORKFLOW_REVISION_CONFLICT`
- API Client：`UpdateWorkflowAsync` 使用 `PUT` 并提交 `base_revision_id`
- ViewModel：保存使用加载时的 `RevisionId`
- ViewModel：保存成功后刷新 list 并重载 detail
- ViewModel：保存冲突 envelope 显示到 UI

## 6. 验收测试

执行时间：2026-06-29

已运行：

```powershell
.\python312\python.exe -m pytest tests\integration\test_api.py -q
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostApiClientTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter MainWindowViewModelWorkflowTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
.\python312\python.exe -m ruff check src tests
```

结果：

| 命令 | 结果 |
| --- | --- |
| 后端 API 定向测试 | PASS，21 passed |
| API Client 定向测试 | PASS，23 passed |
| Workflow ViewModel 定向测试 | PASS，20 passed |
| Avalonia 全量测试 | PASS，76 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |
| ruff `src tests` | PASS |

备注：

- `pytest` 有一条 Starlette `httpx` deprecation warning，非本阶段新增失败
- 全量验收使用串行命令执行，避免测试项目 DLL 写入锁

## 7. 阶段结论

M.6 已完成保存 revision 与冲突保护的最小闭环。

当前 UI 可以保存 draft JSON，并且保存请求必须携带读取时的 `base_revision_id`。后端发现当前 revision 已变化时会拒绝保存，避免旧 draft 静默覆盖。

下一步建议进入：

```text
M.7：工作流定义与运行闭环验收
```

M.7 建议覆盖从 UI 创建、加载、编辑 draft、validate、save、启动 run、观察运行状态的闭环；仍不进入自由画布和动态表单。
