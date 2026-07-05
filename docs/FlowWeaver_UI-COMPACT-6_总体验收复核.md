# FlowWeaver UI-COMPACT-6 总体验收复核

> 适用范围：Avalonia 工作流页精简、统一通知浮层、最近事件面板、数据预览常驻表格与运行反馈展示。

## 1. 阶段结论

UI-COMPACT 第一轮已完成。

本轮目标不是重做工作流编辑器，而是减少主界面说明文字占比，把短反馈放入统一通知，把可追溯反馈放入最近事件，把完整 RuntimeEvent/AuditEvent 留在日志页。

当前结论：

- 工作流页主要内容仍是工作流列表、定义摘要、节点配置、连接摘要、工作流节点列表和数据预览。
- 节点编辑操作默认进入统一通知，并同步进入最近事件。
- RuntimeEvent 进入最近事件，但不默认弹通知，避免运行时高频刷屏。
- 数据预览区保持表格常驻，只把状态压缩到标题栏，错误仍保留可见行。
- 完整日志页仍保留 RuntimeEvent 和 AuditEvent 查询能力。

## 2. 完成矩阵

| 阶段 | 状态 | 内容 | 备注 |
| --- | --- | --- | --- |
| UI-COMPACT-0 | 完成 | 工作流页面精简与通知/日志浮层边界清单 | 只做边界分析 |
| UI-COMPACT-1 | 完成 | 节点操作区说明收口 | 长说明收进信息入口 |
| UI-COMPACT-2 | 完成 | 通知浮层模型与 Host 骨架 | 支持同 key 更新不重复开启动画 |
| UI-COMPACT-3 | 完成 | 工作流编辑消息接入通知浮层 | 新增、复制、删除、移动、校验、保存等已接入 |
| UI-COMPACT-3a | 完成 | 通知浮层可见性复核与样式增强 | 改善真实可见性 |
| UI-COMPACT-3b | 完成 | 连接、运行、预览、数据预览通知接入 | 运行/预览结果只做汇总通知 |
| UI-COMPACT-4 | 完成 | 最近事件面板 | 默认 1 条，展开 5 条，查看全部进入日志页 |
| UI-COMPACT-5 | 完成 | 数据预览与运行消息瘦身 | 状态进标题栏，来源进 tooltip，错误独立显示 |
| UI-COMPACT-6 | 完成 | 总体验收复核 | 本文档 |

## 3. 通知边界

默认进入统一通知的操作：

- 新增节点、复制节点、删除节点、批量删除节点。
- 上移、下移节点。
- 应用节点配置、应用节点显示名。
- 工作流定义校验、保存、revision 冲突。
- 连接检查成功/失败。
- 工作流运行启动失败、预览启动失败。
- 数据预览加载成功、失败、无可读输出表。

不默认弹通知的内容：

- 每条 RuntimeEvent。
- 每条 AuditEvent。
- 节点 heartbeat/progress 高频变化。
- 大段日志、堆栈、完整 JSON。

这些内容进入运行监控、最近事件摘要或完整日志页。

## 4. 最近事件边界

最近事件面板放在工作流页中间列连接区下方。

当前行为：

- 默认显示最近 1 条。
- 可展开显示最近 5 条。
- 内部最多保留 20 条轻量摘要。
- 通知会写入最近事件。
- RuntimeEvent 会写入最近事件，但不触发通知浮层。
- 查看全部切换到日志页。

第一轮不做：

- 复杂过滤。
- 搜索。
- 大量虚拟列表。
- 审计详情展开。

## 5. 数据预览边界

当前数据预览区：

- 表格区域常驻。
- 预览选中节点和运行按钮保留在标题栏。
- 状态消息压缩到标题栏。
- 数据来源放入 tooltip。
- 错误消息仍独立显示，避免失败被吞掉。

不改变的运行语义：

- `预览选中节点` 仍只运行到选中节点及其上游。
- `运行` 仍运行完整工作流。
- 表格数据由后端正式 TableRef / rows API 提供。

## 6. InitializeComponent 解析复核

`Avalonia_UI/Views/Components/Workflow/WorkflowRecentEventsView.axaml.cs` 已改为直接调用 `AvaloniaXamlLoader.Load(this)`。

原因：

- `dotnet build` 已确认 XAML 生成链路可用。
- 部分 IDE 对新增 `.axaml` 的生成式 `InitializeComponent()` 可能出现暂时无法解析。
- 该组件没有命名控件依赖，直接 loader 能避免 IDE 解析失败，同时保持运行时加载行为稳定。

## 7. 验收命令

已执行：

```powershell
dotnet build Avalonia_UI\Avalonia_UI.csproj -p:OutputPath=bin\Debug\net10.0-isolated\
```

已执行：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj -p:OutputPath=bin\Debug\net10.0-isolated\ --filter "FullyQualifiedName~WorkflowSummaryViewStructureTests|FullyQualifiedName~MainWindowViewModelDataTests|FullyQualifiedName~MainWindowViewModelWorkflowTests|FullyQualifiedName~MainWindowViewModelNotificationTests|FullyQualifiedName~MainWindowViewModelRuntimeEventTests"
```

## 8. 后续建议

下一阶段建议暂不继续压缩工作流页，而是进入真实使用反馈收口：

1. 运行一个实际 workflow，观察最近事件、通知、数据预览是否符合预期。
2. 若工作流页仍显拥挤，再进入第二轮局部 UI 密度调整。
3. 若数据查看需求更强，优先扩展数据预览的分页、列宽、复制单元格能力。
