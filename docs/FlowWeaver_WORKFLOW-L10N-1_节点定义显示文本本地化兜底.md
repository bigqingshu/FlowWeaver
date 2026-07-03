# FlowWeaver WORKFLOW-L10N-1：节点定义显示文本本地化兜底

## 阶段目标

本阶段只处理 Avalonia 前端显示层的节点信息本地化兜底，让内置节点目录、节点类型下拉项、节点配置字段标题和字段类型能跟随当前界面语言显示。

本阶段不修改后端 `NodeDefinition` API，不修改 workflow definition JSON，不翻译真实 `node_type`、`node_version`、端口名或 config 字段名。

## 完成内容

```text
DisplayTextFormatter 增加节点定义显示名格式化
DisplayTextFormatter 增加节点配置字段标题格式化
DisplayTextFormatter 增加节点配置字段类型格式化
NodeDefinitionListItemViewModel.DisplayNameText 使用当前语言显示内置节点名
NodeDefinitionListItemViewModel.ConfigSchemaSummaryText 使用当前语言显示字段标题
NodeConfigEditableFieldInputViewModel.DisplayLabel / TypeText 使用当前语言显示
WorkflowDefinitionDraftNode.NodeTypeDisplayName 使用当前语言显示草稿节点类型
MainWindowViewModel 重建节点配置输入字段时传入当前 DisplayTextFormatter
语言切换后通知已加载节点定义刷新显示文本
```

## 当前翻译范围

第一版只覆盖内置可见节点：

```text
GenerateTestTableNode
FilterRowsNode
PublishSharedTablesNode
ReadSharedTablesNode
```

以及这些节点当前声明的静态 `config_schema` 字段标题。

## 保留英文的稳定标识

以下内容仍保留原始协议文本：

```text
node_type@node_version
input/output port name，例如 in / out
workflow definition JSON 中的 config 字段名
enum 值，例如 EQ / GT / LATEST
```

这些字段属于执行、连接和保存语义的一部分，不应作为显示语言切换的副作用被改写。

补充说明：

```text
新增连接里的源节点 / 目标节点下拉菜单：
主标题仍显示 node_instance_id，例如 generate / filter
副标题改为本地化后的 NodeTypeDisplayName
真实 NodeType 保持 GenerateTestTableNode / FilterRowsNode 等机器标识
```

## 回退策略

```text
优先使用当前语言 key
缺少当前语言 key 时回退 English key
缺少所有 key 时回退后端 display_name / schema title / 字段名
```

这样未来插件节点即使没有本地化资源，也仍能稳定显示后端提供的原始英文或插件自带名称。

## 验证结果

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore /p:UseAppHost=false
通过，0 warning，0 error

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeDefinitionListItemViewModelTests|NodeConfigEditableFieldInputViewModelTests|JsonLocalizationServiceTests" /p:UseAppHost=false
通过，14 passed

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore /p:UseAppHost=false
通过，270 passed

补充验证：

dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore /p:UseAppHost=false
通过，0 warning，0 error

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftStructureBuilderTests|WorkflowSummaryViewStructureTests|NodeDefinitionListItemViewModelTests" /p:UseAppHost=false
通过，17 passed

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore /p:UseAppHost=false
通过，271 passed
```
