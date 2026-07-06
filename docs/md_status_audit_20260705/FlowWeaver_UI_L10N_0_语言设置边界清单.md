# FlowWeaver UI L10N-0：语言设置边界清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：语言设置、JSON 本地化资源、语言切换、设置持久化和相关测试已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：后续新增显示文本需要继续补 en-US 与 zh-Hans key。

> 文档状态：L10N-0完成
> 适用范围：`Avalonia_UI/` 桌面端语言设置、语言资源文件、UI settings 持久化和后续界面文案替换顺序
> 当前执行点：只确认语言边界和最小实现顺序，不修改后端 API、不改变 workflow 行为、不一次性重写全部界面

## 1. 目标

本轮语言设置目标是为 Avalonia UI 增加可扩展的语言基础设施，第一批支持：

- English
- 简体中文

语言切换应作为桌面端 UI 配置，不影响 EngineHost、token、workflow definition、runtime 数据、API payload 或数据库内容。

## 2. 当前现状

当前 Avalonia UI 的可见文本主要分布在：

| 位置 | 文案类型 | 当前状态 |
| --- | --- | --- |
| `Avalonia_UI/Views/MainWindow.axaml` | 标题、Tab、按钮、标签、Watermark | 英文硬编码 |
| `Avalonia_UI/ViewModels/MainWindowViewModel.cs` | 状态消息、错误提示、加载提示 | 英文硬编码 |
| 列表项 ViewModel | 派生显示文本，例如 `node(s)`、`connection(s)`、时间、状态拼接 | 英文硬编码或协议值直显 |
| API DTO / 后端返回 | 错误码、状态、节点类型、事件类型 | 技术标识，不应翻译 |

已有连接配置保存在：

```text
%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\connection-settings.json
```

语言设置建议使用独立文件，避免和连接配置、token 语义混在一起。

## 3. 语言配置文件

新增 UI 设置文件：

```text
%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\ui-settings.json
```

建议第一版 schema：

```json
{
  "schema_version": 1,
  "language_code": "en-US",
  "updated_at_utc": "2026-06-30T00:00:00Z"
}
```

规则：

- 缺失配置时默认 `en-US`
- 损坏 JSON 时默认 `en-US`
- 非法语言码时默认 `en-US`
- 保存语言设置不保存 token、BaseUrl 或任何后端连接数据
- 后续如需系统语言自动识别，应作为独立小步，不在 L10N-1 默认开启

## 4. 语言资源文件

新增语言资源目录：

```text
Avalonia_UI/Localization/en-US.json
Avalonia_UI/Localization/zh-Hans.json
```

资源文件第一版使用扁平 key-value：

```json
{
  "app.title": "FlowWeaver",
  "connection.base_url": "Base URL"
}
```

规则：

- `en-US.json` 是 fallback 基准
- `zh-Hans.json` 缺失 key 时回退到 `en-US`
- 两个文件缺失 key 时返回 key 本身，方便开发期发现遗漏
- 语言资源随 Avalonia UI 构建输出复制
- 发布产物和便携目录后续应能包含 `Localization/` 目录

## 5. 翻译边界

第一批可以翻译：

- 菜单、Tab、按钮、标签、Watermark
- 连接状态、加载状态、用户可恢复错误提示
- 空列表提示
- 操作成功/失败提示

第一批不翻译：

- API 错误码，例如 `UNAUTHORIZED`
- workflow/node/run 状态枚举，例如 `RUNNING`、`FAILED`
- RuntimeEvent 类型，例如 `ENGINE_READY`
- 节点类型，例如 `GenerateTestTableNode`
- workflow definition JSON 内部字段
- token、BaseUrl、URL、文件路径
- 审计事件原始 payload

技术标识保留英文可以降低排障成本，也避免 UI 翻译和后端协议产生歧义。

## 6. 实施顺序

### L10N-1：语言配置和加载基础设施

本小步实现：

- `SupportedLanguage`
- `PersistedUiSettings`
- `IUiSettingsStore` / `FileUiSettingsStore`
- `ILocalizationService` / JSON 本地化服务
- `en-US.json` / `zh-Hans.json`
- 单元测试覆盖配置损坏、非法语言、fallback 和 key 缺失

本小步不改主窗口菜单，不替换全量 XAML 文案。

### L10N-2：语言菜单入口

后续实现：

- `Settings -> Language -> English`
- `Settings -> Language -> 简体中文`
- 切换后保存 `ui-settings.json`
- 主窗口最小标题/连接区域随语言刷新

### L10N-3：主窗口静态文案替换

后续实现：

- Tab、按钮、标签、Watermark 改为本地化绑定
- 保持布局不因中英文长度变化而明显错位
- 补 XAML 或 ViewModel 级 smoke

### L10N-4：ViewModel 动态消息替换

后续实现：

- 加载、刷新、保存、失败、空状态消息使用本地化模板
- 动态参数使用格式化模板
- 错误码和协议值仍保留原文

## 7. 验收标准

L10N-1 最小验收：

- 默认语言为 `en-US`
- `zh-Hans` 可加载
- 非法语言码回退 `en-US`
- 损坏 `ui-settings.json` 回退默认配置
- `zh-Hans` 缺失 key 时回退 `en-US`
- 全部 Avalonia UI 单元测试通过

L10N-2 之后再验收 UI 菜单和即时切换。
