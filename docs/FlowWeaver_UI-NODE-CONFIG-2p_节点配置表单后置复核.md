# FlowWeaver UI-NODE-CONFIG-2p：节点配置表单后置复核

> 文档状态：UI-NODE-CONFIG-2p 后置复核完成
> 当前阶段：复核节点配置表单、Apply 可用性和 XAML 绑定边界
> 不适用范围：新的 workflow 编辑能力、后端 API 修改、发布打包、外部模块

## 1. 复核目标

本阶段复核 `UI-NODE-CONFIG-2o` 后的最小链路：

```text
节点选择
→ schema 派生输入字段
→ UI 显示字段
→ 用户修改字段
→ Apply patch 到 WorkflowDefinitionDraftJson
```

## 2. 已补充验证

补充 `MainWindowViewModelWorkflowTests`：

* schema 未加载时 `ApplySelectedNodeConfigDraftCommand` 不可用。
* node definitions 加载后，输入字段存在且 Apply 可用。

补充 `WorkflowSummaryViewStructureTests`：

* 节点配置区域绑定 `HasSelectedNodeConfigEditableInputFields`。
* 字段标签绑定 `DisplayLabel`。
* 类型、必填、warning 绑定 `TypeText` / `RequiredText` / `WarningText`。
* text / enum / boolean 控件分别绑定 `IsTextInput` / `IsEnumInput` / `IsBooleanInput`。
* boolean 候选绑定 `BooleanValues`。
* XAML 不引入 `Converter=`。

## 3. 当前证据

构建：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，警告：0，错误：0
```

定向测试：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests"
通过：46，失败：0，跳过：0
```

完整测试：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：216，失败：0，跳过：0
```

## 4. 已满足边界

当前满足：

* 节点配置表单只接入 `WorkflowSummaryView.axaml`。
* 没有新增 converter。
* 没有新增 code-behind。
* Apply 不调用后端。
* Apply 不调用 Validate / Save。
* revision conflict 下 Apply 不可用。
* schema 未加载时 Apply 不可用。
* 当前字段输入可以 patch 到 `WorkflowDefinitionDraftJson`。

## 5. 未完成/保留项

仍未完成：

* 未做真实桌面截图核验。
* 未做节点配置区域滚动高度的真实窗口复核。
* 未做字段级错误的高质量可视化回填。
* 未做 array / object JSON fallback 编辑器。
* 未做 WORKFLOW-EDIT-1/2 的完整工作流结构编辑能力。

这些不阻塞当前最小节点配置主线，但进入更大的 workflow 编辑阶段前应在验收清单中继续跟踪。

## 6. 下一小步建议

下一步建议先做一个阶段转场复核：

```text
UI-NODE-CONFIG-2q：
节点配置阶段总体验收与进入 WORKFLOW-EDIT 前复核。
```

该复核应明确：

* 当前节点配置主线已经覆盖哪些能力。
* 哪些能力属于 WORKFLOW-EDIT-1/2。
* 是否还需要真实桌面截图/手动 smoke 后再进入 WORKFLOW-EDIT。
