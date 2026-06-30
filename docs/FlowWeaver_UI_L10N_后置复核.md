# FlowWeaver UI L10N 后置复核

> 文档状态：L10N 后置复核完成
> 适用范围：`Avalonia_UI/` 语言设置、静态文案、动态消息完成后的剩余 UI 文案边界
> 当前执行点：只做复核与后续小步建议，不直接改列表项 ViewModel 构造、不改变 API DTO、不翻译协议值

## 1. 已完成范围

当前 Avalonia UI 已完成：

- `Settings -> Language` 菜单入口
- `en-US` / `zh-Hans` JSON 资源文件
- UI language 持久化到独立 `ui-settings.json`
- 主窗口静态文本本地化
- `MainWindowViewModel` 中加载、刷新、成功、失败、校验、事件流和数据区动态消息本地化

测试已覆盖：

- 默认语言与非法语言回退
- 资源 key fallback
- UI settings 读取和保存
- 主窗口静态文本切换
- 简体中文动态消息路径

## 2. 本次复核对象

复核命令聚焦 `Avalonia_UI/ViewModels/*.cs` 中仍存在的派生显示文本。

主要文件：

| 文件 | 观察点 | 判断 |
| --- | --- | --- |
| `WorkflowDefinitionDetailViewModel.cs` | `node(s)`、`connection(s)`、`enabled`、`disabled` | 用户可读，应后续本地化 |
| `NodeRunListItemViewModel.cs` | `attempt {n}` | 用户可读，应后续本地化 |
| `SharedPublicationListItemViewModel.cs` | `member(s)` | 用户可读，应后续本地化 |
| `WorkflowListItemViewModel.cs` | `v{n}`、时间格式 | 技术/紧凑格式，暂保留 |
| `WorkflowRunListItemViewModel.cs` | `v{n}`、`-`、时间格式、状态和 completion_reason | 协议/紧凑格式，暂保留 |
| `RuntimeEventListItemViewModel.cs` | `#{sequence}`、事件类型、run/node id、`-` | 协议/技术标识，保留原文 |
| `AuditEventListItemViewModel.cs` | event type、decision、run/node id、`-` | 协议/审计标识，保留原文 |
| `TableRefListItemViewModel.cs` | role、storage_kind、capabilities、lifecycle_status、`v{n}` | 协议/能力标识，保留原文 |
| `SharedPublicationMemberListItemViewModel.cs` | `v{n}` | 技术版本格式，暂保留 |

## 3. 不建议立即翻译的内容

以下内容继续保留原文：

- API/数据库状态枚举，例如 `RUNNING`、`FAILED`、`PUBLISHED`
- RuntimeEvent 和 AuditEvent 类型
- table role、storage kind、capability、lifecycle status
- node type、node version、workflow id、run id、node run id
- `v{n}`、`#{sequence}`、`yyyy-MM-dd HH:mm:ss`
- JSON 字段名和 workflow definition 内部文本

原因：

- 这些值主要用于排障和与后端协议对齐
- 翻译后容易和 API payload、日志、审计记录产生歧义
- 部分文本来自用户或 workflow definition，桌面端不应擅自翻译

## 4. 后续最小实现建议

如果继续做 L10N 后续小步，建议只做 `L10N-5：列表项用户可读派生文本`。

最小范围：

- `WorkflowDefinitionDetailViewModel.NodeCountText`
- `WorkflowDefinitionDetailViewModel.ConnectionCountText`
- `WorkflowDefinitionNodeListItemViewModel.EnabledText`
- `NodeRunListItemViewModel.AttemptText`
- `SharedPublicationListItemViewModel.MemberCountText`

实现注意：

- 不把 `ILocalizationService` 直接散落到每个 DTO 类里
- 优先引入一个很薄的 `DisplayTextFormatter` 或 `UiTextFormatter`
- 由 `MainWindowViewModel` 构造列表项时传入 formatter
- 保持协议值字段继续原文显示
- 语言切换后，已有列表项如果不重建，需明确是否刷新；第一版可在语言切换后重建可见集合或只对新加载数据生效

## 5. L10N-5 风险点

L10N-5 看似小，但会触及多个列表项构造链：

- workflow definition detail 会嵌套 node、connection、revision item
- shared publication 会嵌套 member item
- runtime event stream 会持续插入 item
- 语言切换时是否刷新已存在 item，需要明确策略

因此不建议在本次后置复核里直接实现。

## 6. 建议结论

当前 L10N 阶段可以视为完成“主窗口可操作文本”的最小闭环。

下一步若继续语言体验，建议进入 `L10N-5`，只处理少量用户可读派生文本；若暂不继续，当前状态已经可用于简体中文/英文切换的基础使用。
