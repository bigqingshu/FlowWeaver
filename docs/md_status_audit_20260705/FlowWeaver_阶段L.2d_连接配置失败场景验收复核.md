# FlowWeaver 阶段L.2d：连接配置失败场景验收复核

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L.2d验收复核完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口和阶段L.2连接配置持久化边界
> 适用范围：Avalonia UI 连接配置的损坏配置、非法 URL、保存失败和敏感信息不落盘验收
> 当前执行点：只补失败场景验收，不扩展 UI 功能

## 1. 目标

L.2d只做连接配置失败场景的验收复核，确认 L.2a 到 L.2c 的实现满足以下边界：

- 配置文件不存在时使用默认 BaseUrl
- 配置文件损坏时使用默认 BaseUrl
- 配置文件内容是合法 JSON 但 BaseUrl 非法时使用默认 BaseUrl
- 保存失败不阻断 health 成功
- token、Authorization header 和完整 WebSocket URL 不写入配置 JSON

L.2d不做：

- 不保存 token
- 不新增 recent BaseUrl 下拉 UI
- 不新增配置页面
- 不引入系统凭据存储
- 不修改 EngineHost 后端
- 不修改 RuntimeEvent WebSocket 鉴权方式

## 2. 已有覆盖

L.2a/L.2c 已经覆盖：

| 场景 | 覆盖位置 | 结论 |
| --- | --- | --- |
| 配置文件不存在 | `FileConnectionSettingsStoreReturnsDefaultWhenMissing` | 回退默认 BaseUrl |
| 配置文件损坏 | `FileConnectionSettingsStoreReturnsDefaultForCorruptJson` | 回退默认 BaseUrl |
| 模型层非法 URL | `PersistedConnectionSettingsFallsBackWhenAllUrlsAreInvalid` | 回退默认 BaseUrl |
| 保存内容不含 token/authorization | `PersistedConnectionSettingsJsonDoesNotContainToken` | 不落敏感字段 |
| 启动加载不恢复 token | `LoadConnectionSettingsDoesNotRestoreToken` | token 仍为空 |
| 启动加载异常 | `LoadConnectionSettingsFailureKeepsDefaultBaseUrl` | UI 不崩溃，回退默认 BaseUrl |
| health 失败 | `CheckConnectionDoesNotSaveWhenHealthFails` | 不保存 BaseUrl |
| 保存失败 | `SaveFailureDoesNotTurnHealthyConnectionIntoError` | 保持 Connected，只显示非阻断错误 |
| 业务 API | `BusinessApiDoesNotReadOrSaveConnectionSettings` | 不触发 Store 读写 |

## 3. 本次补齐

本次 L.2d 只补一个缺口：

```text
FileConnectionSettingsStoreReturnsDefaultForInvalidStoredBaseUrls
```

覆盖场景：

- 配置文件是合法 JSON
- `last_successful_base_url` 不是 URL
- `recent_base_urls` 只有非 HTTP/HTTPS URL
- `LoadAsync()` 返回默认 BaseUrl
- recent 列表也回退为默认 BaseUrl

该测试确认 Store 层不会把非法但可反序列化的配置继续传给 UI。

## 4. 失败处理结论

L.2d 复核后，连接配置失败处理边界如下：

| 场景 | 行为 |
| --- | --- |
| 文件不存在 | 默认 BaseUrl |
| JSON 损坏 | 默认 BaseUrl |
| JSON 可读但 URL 非法 | 默认 BaseUrl |
| Store 读取异常 | ViewModel 保持默认 BaseUrl 并显示非阻断错误 |
| health 成功但保存失败 | 保持 `Connected`，显示非阻断错误 |
| health 失败 | 不保存配置，连接状态为 `Error` |
| token 错误、轮换或失效 | 用户重新输入，不从配置恢复 |
| RuntimeEvent WebSocket URL | 不写入配置，不写入文档示例中的真实 token |

## 5. 验收命令

L.2d 验收应至少运行：

```powershell
dotnet build Avalonia_UI\Avalonia_UI.sln
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-build
```

同时执行：

```powershell
git diff --check -- README.md "FlowWeaver_阶段L.2_UI连接配置持久化边界.md" "FlowWeaver_阶段L.2d_连接配置失败场景验收复核.md" Avalonia_UI Avalonia_UI.Tests
```

## 6. 下一步建议

L.2d 完成后，L.2 连接配置持久化边界可以视为第一轮闭环。下一步建议进入 L.3：正式路径烟雾清单，覆盖空数据库、已有工作流和 EngineHost 重启三类验收。
