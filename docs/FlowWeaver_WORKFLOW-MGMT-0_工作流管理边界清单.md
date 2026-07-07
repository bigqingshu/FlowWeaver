# FlowWeaver WORKFLOW-MGMT-0：工作流管理边界清单

日期：2026-07-07

## 目标

补齐工作流页面左侧“工作流”区域的基础管理能力，使用户可以围绕工作流定义完成删除、导出和导入等常见操作。

本阶段只固化语义、接口边界和后续实施顺序，不直接修改代码。

## 当前基线

### 已具备能力

左侧工作流区域当前已经具备：

- 刷新工作流列表。
- 输入名称并创建模板工作流。
- 选择工作流。
- 选择后自动加载工作流定义详情。
- 选中工作流后可在其他区域继续编辑节点、保存草稿、预览和运行。

后端已经具备：

- `GET /api/v1/workflows`：列出未删除工作流。
- `POST /api/v1/workflows`：创建工作流。
- `GET /api/v1/workflows/{workflow_id}`：读取工作流详情。
- `PUT /api/v1/workflows/{workflow_id}`：保存新 revision。
- `DELETE /api/v1/workflows/{workflow_id}`：删除工作流。

`DELETE /api/v1/workflows/{workflow_id}` 当前是逻辑删除：

```text
WorkflowRecord.status = "DELETED"
```

逻辑删除后的工作流会从列表和详情读取中隐藏，不会物理删除数据库记录、历史 revision、运行记录或运行数据。

### 当前缺口

Avalonia UI 当前还没有：

- 工作流删除按钮。
- 工作流导出入口。
- 工作流导入入口。
- 对应的删除确认、导出文件格式、导入冲突策略。

Avalonia API Client 当前还没有封装：

- `DeleteWorkflowAsync`

后端当前还没有专用：

- 工作流导出 API。
- 工作流导入 API。
- 已删除工作流恢复 API。

## 管理能力职责划分

### 删除工作流

第一版删除应理解为“隐藏/停用工作流定义”，不是物理删除。

删除后：

- 当前工作流列表刷新。
- 如果删除的是当前选中工作流，则清空选中项。
- 工作流详情、节点列表、节点配置和预览状态应同步清空或进入未选择状态。
- 历史运行记录、TableRef、SharedPublication 不在本阶段级联删除。

删除必须弹出确认，因为当前没有恢复入口。

确认文案应明确：

```text
删除后该工作流将从列表隐藏；历史运行数据不会在本阶段自动清理。
```

### 导出工作流

第一版导出建议由桌面端完成，不新增后端专用接口。

流程：

```text
选中工作流
-> GET /api/v1/workflows/{workflow_id}
-> 组装导出 JSON
-> 用户选择保存位置
-> 写入本地文件
```

推荐导出格式：

```json
{
  "export_format": "flowweaver.workflow.v1",
  "exported_at": "2026-07-07T00:00:00Z",
  "workflow": {
    "workflow_id": "workflow-id",
    "name": "Workflow name",
    "revision_id": "revision-id",
    "version": 1,
    "status": "ACTIVE",
    "definition": {}
  }
}
```

导出只包含工作流定义，不包含：

- 运行历史。
- NodeRun。
- RuntimeEvent。
- TableRef。
- SharedPublication。
- 运行数据库文件。
- 外部 SQL 文件或外部资源。

原因：这些属于运行产物、数据资产或外部资源生命周期，范围明显大于工作流定义管理。

### 导入工作流

第一版导入建议“作为新工作流创建”，不覆盖已有工作流。

流程：

```text
选择导出 JSON
-> 解析 export_format
-> 读取 workflow.name 和 workflow.definition
-> POST /api/v1/workflows
-> 刷新列表
-> 选中新创建工作流
```

导入时不保留原 `workflow_id`、`revision_id` 和 `version` 作为后端身份。

这些字段只能作为导入来源信息用于提示或后续审计，不应直接写入当前 RuntimeStore。

导入失败边界：

- JSON 文件不可读。
- JSON 格式错误。
- `export_format` 不支持。
- 缺少 `workflow.definition`。
- definition 校验失败。
- EngineHost 未连接或 token 错误、轮换或失效。

## UI 放置建议

左侧工作流区域保持当前主结构：

```text
工作流标题 + 刷新
新建名称 + 创建
工作流列表
底部状态消息
```

建议在底部状态消息上方或列表下方新增一行紧凑管理按钮：

```text
导入  导出  删除
```

按钮启用条件：

| 按钮 | 启用条件 |
| --- | --- |
| 导入 | EngineHost 已连接、当前没有工作流忙碌操作 |
| 导出 | EngineHost 已连接、已选择工作流、当前没有工作流忙碌操作 |
| 删除 | EngineHost 已连接、已选择工作流、当前没有工作流忙碌操作 |

删除按钮应使用危险操作样式或确认弹窗，不建议和普通刷新/创建按钮混在同一视觉层级。

## 与现有阶段的关系

本阶段补的是阶段 M.4 当时明确未做的工作流删除、导入和导出能力。

它不改变：

- 工作流定义 revision 保存机制。
- 草稿 JSON 保存机制。
- 节点结构化编辑机制。
- 运行到选中节点语义。
- TableRef / SharedPublication 数据流。
- 数据预览工作台计划。

因此 WORKFLOW-MGMT 可以作为 UI 工作流管理增强阶段独立推进。

## 不进入本阶段的能力

以下能力后置：

- 物理删除工作流和历史记录。
- 恢复已删除工作流。
- 批量删除工作流。
- 重命名工作流独立入口。
- 复制工作流。
- 覆盖导入到已有工作流。
- 导出运行历史。
- 导出运行数据表。
- 导出 SharedPublication。
- 导出完整项目包。
- 从导入文件恢复原 workflow_id。
- 导入时自动重连外部 SQL、文件或其他外部资源。

## 建议实施顺序

### WORKFLOW-MGMT-1：删除工作流

目标：

- Avalonia API Client 增加 `DeleteWorkflowAsync`。
- ViewModel 增加删除命令和删除中状态。
- 左侧工作流区域增加删除按钮。
- 删除前弹确认。
- 删除成功后刷新列表并清空已删除选中项。

测试：

- API Client 使用 `DELETE /api/v1/workflows/{workflow_id}`。
- 未选中工作流时删除按钮不可用。
- 删除成功后不会保留已删除工作流为选中项。
- 删除失败时保留原列表和错误提示。

### WORKFLOW-MGMT-2：导出工作流

目标：

- 读取当前工作流详情。
- 生成 `flowweaver.workflow.v1` JSON。
- 通过桌面保存文件入口写出。
- 导出成功后显示通知。

测试：

- 导出 JSON 包含 `export_format`、`exported_at`、`workflow`。
- 导出 JSON 包含 definition。
- 未选择工作流时导出不可用。
- 读取详情失败时不写出无效文件。

### WORKFLOW-MGMT-3：导入为新工作流

目标：

- 通过桌面打开文件入口读取 JSON。
- 校验 `export_format`。
- 解析 `workflow.name` 和 `workflow.definition`。
- 使用现有 `CreateWorkflowAsync` 创建新工作流。
- 导入成功后刷新列表并选中新工作流。

测试：

- 支持导入 `flowweaver.workflow.v1`。
- 不复用原 `workflow_id`。
- 非法 JSON、缺字段和不支持格式能给出用户可读错误。
- 后端校验失败时不清空当前工作流列表。

### WORKFLOW-MGMT-4：阶段验收复核

目标：

- 复核删除、导出、导入的按钮状态、错误提示和本地化文本。
- 复核与工作流详情自动加载、草稿 dirty 状态、revision 冲突状态的交互。
- 更新阶段完成记录。

验收：

- 删除、导出、导入互不影响当前节点编辑能力。
- 删除当前选中工作流后，中间和右侧区域不会继续显示旧工作流内容。
- 导出的文件可重新导入为新工作流。
- 导入的新工作流可以加载详情、编辑、保存、预览和运行。

## 推荐下一步

进入 `WORKFLOW-MGMT-1：删除工作流`。

理由：

- 后端删除 API 已存在。
- 删除是当前左侧管理区最明显缺口。
- 可以先补最小 API Client、ViewModel 命令、按钮状态和确认弹窗。
- 不需要引入文件选择器，也不需要定义额外导入导出格式。
