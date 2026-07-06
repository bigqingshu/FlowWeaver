# FlowWeaver DATA-PREVIEW-STATE：二级数据预览状态拆分计划

## 1. 背景

当前数据预览页已经具备读取 `TableRef`、加载表格行、分页、搜索、复制、粘贴草稿和详情跳转等基础能力。

但现有 UI 状态将“候选表选择”和“当前表格实际显示的数据表”绑定在同一个 `SelectedDataPreviewTableRef` 上，导致右侧下拉菜单选择后会立即触发表格变化。

这不符合后续目标：

- 左侧选择某个处理状态；
- 右侧选择该状态下的具体表；
- 只有点击“载入选中表”后，表格才更新；
- 当前已显示的表格应保持稳定，不应被下拉选择直接清空或替换。

## 2. 当前问题

当前实现中存在三类状态耦合：

1. 左侧列表和右侧下拉使用同一份 `TableRefs`。
2. 左侧列表和右侧下拉共用 `SelectedDataPreviewTableRef`。
3. `OnSelectedDataPreviewTableRefChanged` 会重置数据预览工作台，并在数据预览页自动调用加载命令。

因此当前右侧下拉只是左侧表引用列表的另一个入口，不是“状态下的表选择器”。

## 3. 目标状态模型

后续应拆成三个独立概念。

### 3.1 SelectedDataPreviewState

含义：左侧选中的处理状态。

建议来源：

- 当前运行 `WorkflowRunId`；
- 节点运行 `NodeRunId`；
- 该节点运行产生的一组 `TableRef`；
- 后续可扩展为“处理前”“处理后”“共享输入”“内存副表”等更精确状态。

第一版最小实现可以按 `WorkflowRunId + NodeRunId` 对 `TableRef` 分组。

职责：

- 控制左侧列表选中项；
- 决定右侧下拉菜单可选表集合；
- 不直接触发表格加载；
- 切换状态时可以默认选中该状态下第一张表，但不替换当前表格。

### 3.2 SelectedDataPreviewTableOption

含义：右侧下拉菜单选中的候选表。

建议来源：

- `SelectedDataPreviewState` 下的 `TableRef` 集合。

职责：

- 控制右侧下拉菜单选中项；
- 展示当前表、SQL 映射表、内存表、节点输出副表等候选表；
- 不直接触发表格加载；
- 不清空当前表格；
- 不改变当前来源文案和保存能力判断。

### 3.3 LoadedDataPreviewTableRef

含义：当前表格真正显示的数据表。

职责：

- 作为分页、搜索、来源文案、保存能力判断的真实依据；
- 点击“载入选中表”成功后更新；
- 下拉选择变化时保持不变；
- 失败时保留上一次有效表格；
- 作为“当前显示详情”的稳定来源。

## 4. 推荐数据流

```mermaid
flowchart LR
    A["刷新表引用"] --> B["TableRefs"]
    B --> C["按 WorkflowRunId + NodeRunId 分组"]
    C --> D["DataPreviewStates"]
    D --> E["SelectedDataPreviewState"]
    E --> F["DataPreviewTableOptions"]
    F --> G["SelectedDataPreviewTableOption"]
    G --> H["点击：载入选中表"]
    H --> I["LoadedDataPreviewTableRef"]
    I --> J["读取 /api/v1/data/{table_ref_id}/rows"]
    J --> K["DataPreviewWorkbenchColumns / Rows"]
```

## 5. 最小实施阶段

### DATA-PREVIEW-STATE-1：文档与状态边界确认

目标：

- 固化三段状态命名；
- 确认短期不改后端；
- 确认右侧下拉选择不应自动加载表格。

产出：

- 本文档。

### DATA-PREVIEW-STATE-2：新增状态分组模型

目标：

- 新增 `DataPreviewStateListItemViewModel`；
- 从 `TableRefs` 按 `WorkflowRunId + NodeRunId` 分组；
- 每个状态持有该状态下的 `TableRefListItemViewModel` 集合。

建议显示字段：

- 节点运行 ID；
- 表数量；
- 存储类型摘要；
- 是否有可读表。

不做：

- 不改后端 API；
- 不做处理前/处理后精准语义；
- 不引入 SQL 专用 UI。

### DATA-PREVIEW-STATE-3：拆分 ViewModel 选择状态

目标：

- 新增 `SelectedDataPreviewState`；
- 新增 `DataPreviewTableOptions`；
- 新增 `SelectedDataPreviewTableOption`；
- 新增 `LoadedDataPreviewTableRef`。

关键要求：

- 切换 `SelectedDataPreviewState` 只刷新右侧表选项；
- 切换 `SelectedDataPreviewTableOption` 不加载表格；
- `LoadedDataPreviewTableRef` 只在载入成功后变化。

### DATA-PREVIEW-STATE-4：调整加载命令

目标：

- `LoadSelectedDataPreviewTableCommand` 改为读取 `SelectedDataPreviewTableOption`；
- 载入成功后设置 `LoadedDataPreviewTableRef`；
- 分页加载使用 `LoadedDataPreviewTableRef`；
- 来源文案和保存能力判断使用 `LoadedDataPreviewTableRef`。

关键要求：

- 加载失败保留上一次有效表格；
- 下拉选择变化不清空表格；
- 分页时不被候选表变化误伤。

### DATA-PREVIEW-STATE-5：调整 View 层

目标：

- 左侧列表改为绑定 `DataPreviewStates`；
- 左侧选中绑定 `SelectedDataPreviewState`；
- 右侧下拉绑定 `DataPreviewTableOptions`；
- 右侧下拉选中绑定 `SelectedDataPreviewTableOption`；
- “载入选中表”按钮绑定现有加载命令。

建议文案：

- 左侧标题：处理状态；
- 右侧标签：数据表；
- 按钮：载入选中表。

### DATA-PREVIEW-STATE-6：详情跳转兼容

目标：

- “显示详情”从工作流预览跳转到数据预览页时，能够定位对应状态和对应表；
- 必要时刷新 `TableRefs`；
- 找到目标表后设置：
  - `SelectedDataPreviewState`
  - `SelectedDataPreviewTableOption`
  - `LoadedDataPreviewTableRef`
- 然后载入目标表。

### DATA-PREVIEW-STATE-7：测试与验收

建议补充测试：

- 刷新表引用后能生成处理状态列表；
- 同一 `NodeRunId` 下多张表会显示在右侧下拉；
- 切换右侧下拉不会调用 `GetTableDataRowsAsync`；
- 点击“载入选中表”才会读取 rows；
- 切换左侧状态不会清空当前已显示表格；
- 加载失败保留上一张有效表格；
- “显示详情”能定位状态和表，并加载目标表。

验收命令：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -c CodexRestore
```

## 6. 与后端边界

第一版不需要修改后端。

当前 `TableRef` 已提供最小可用分组字段：

- `workflow_run_id`
- `node_run_id`
- `role`
- `storage_kind`
- `logical_table_id`
- `capabilities`
- `lifecycle_status`

后续如果需要严格表达“处理前”“处理后”“输入表”“输出表”，再考虑新增后端只读摘要接口，例如：

- `GET /api/v1/runs/{run_id}/data-states`
- `GET /api/v1/runs/{run_id}/data-states/{state_id}/table-refs`

在此之前，UI 只按已有 `TableRef` 做分组，不扩大后端范围。

## 7. 明确不做

本阶段不做：

- 不实现 SQL 表保存；
- 不实现 xlsx 直接解析入口；
- 不实现多表编辑事务；
- 不改 TableRef 协议；
- 不改变内存表、SQL 表、运行时表的 provider 实现；
- 不把下拉选择作为自动加载行为。

## 8. 当前待处理提醒

当前工作区中右侧下拉已经存在一版临时实现，但它仍绑定 `TableRefs` 和 `SelectedDataPreviewTableRef`。

正式进入本计划时，应将该临时绑定替换为：

- `ItemsSource="{Binding DataPreviewTableOptions}"`
- `SelectedItem="{Binding SelectedDataPreviewTableOption, Mode=TwoWay}"`

并移除下拉变化触发表格自动加载的行为。
