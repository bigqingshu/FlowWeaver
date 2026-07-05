# FlowWeaver 主程序权限审计模块移除清单

更新时间：2026-07-05

## 背景说明

当前决定：默认主程序不再内置权限管理和安全审计模块。

原因是 FlowWeaver 当前定位更接近本地工作流运行与数据中转工具，主程序主要负责工作流生命周期、节点调度、运行状态、数据引用和事件中转。权限管理、审计追踪、授权句柄、字段级权限等能力会增加配置复杂度，也会让主程序持续依赖节点业务细节。

本清单用于后续移除主程序内权限/审计链路时对照执行。此前整理的“主程序与节点耦合列表”暂时保留，等权限审计模块完全移除并对接完成后，再统一更新耦合分析。

## 移除原则

1. 主程序不再做权限申请、授权、撤销和权限句柄管理。
2. 主程序不再维护独立安全审计事件表和审计查询 API。
3. 节点运行失败、进度、普通日志和状态变化继续走 RuntimeEvent 或节点结果，不再走 AuditEvent。
4. 节点内部是否访问文件、程序、网络或外部资源，由节点自身方案说明和实现，不由主程序统一授权。
5. 发布包 runtime audit 不属于本次移除范围，它是发布检查工具，不是主程序运行期权限/审计模块。

## 代码移除清单

| 模块 | 对应位置 | 移除/调整原因 | 后续处理 |
|---|---|---|---|
| 权限协议模型 | `src/flowweaver/protocols/permissions.py` | `PermissionRequestModel`、`PermissionGrantModel`、`PermissionScopeModel`、`AuditEventModel` 属于运行期权限审计协议，移除后可减少主程序契约复杂度。 | 删除或拆空该文件，并清理引用。 |
| 协议枚举 | `src/flowweaver/protocols/enums.py` | `PermissionAction`、`AuditLevel`、`AUDIT_EVENT_CREATED`、`WAITING_PERMISSION` 都服务于权限/审计链路。 | 移除相关枚举值，并同步状态机。 |
| 节点任务模型 | `src/flowweaver/protocols/node_task.py` | `permission_handle_id` 会让每个节点任务携带授权句柄，形成主程序权限依赖。 | 删除字段，任务只保留运行所需信息。 |
| 协议导出 | `src/flowweaver/protocols/__init__.py` | 继续导出权限/审计模型会保留旧接口。 | 移除权限/审计相关导出。 |
| 工作流任务提交 | `src/flowweaver/workflow_process/node_tasks.py` | 当前提交节点任务时会解析权限、创建授权、处理权限失败分支。 | 移除权限解析和授权生成，节点直接排队执行。 |
| 内置节点权限解析 | `src/flowweaver/nodes/permissions.py` | 该文件按具体内置节点解析权限，是主程序依赖节点业务的主要来源之一。 | 删除文件。 |
| 节点权限检查 | `src/flowweaver/nodes/permission_checks.py` | 执行前检查 permission grant 并写 AuditEvent，属于运行期权限审计链路。 | 删除文件。 |
| 表节点执行 | `src/flowweaver/nodes/builtin_table.py` | 当前发布输出前检查 `PermissionAction.PUBLISH`，导致内置节点依赖权限句柄。 | 移除 `ensure_task_permission_scope`，直接写运行数据。 |
| 共享表节点执行 | `src/flowweaver/nodes/builtin_shared_table.py` | 发布/读取共享表前检查权限，增加运行链路复杂度。 | 移除权限检查，保留共享表自身数据校验。 |
| 节点包导出 | `src/flowweaver/nodes/__init__.py` | 仍导出权限解析函数会保留旧能力入口。 | 移除权限解析导出。 |
| RuntimeStore 权限/审计方法 | `src/flowweaver/engine/runtime_store.py` | `create_permission_grant`、`get_permission_grant`、`list_permission_grants_by_workflow_run`、`revoke_permission_grant`、`append_audit_event`、`get_audit_event`、`list_audit_events` 都是主程序权限/审计存储接口。 | 删除方法、转换函数和相关 imports。 |
| 数据库模型 | `src/flowweaver/engine/db_models.py` | `PermissionGrantRecord`、`AuditEventRecord` 和 `NodeTaskRecord.permission_handle_id` 是数据库层权限审计结构。 | 删除对应模型/字段，并做迁移处理。 |
| 表租约审计 | `src/flowweaver/engine/table_lease_manager.py` | 表租约目前会写 `AuditEventRecord`，移除审计表后会断链。 | 移除审计写入；如需诊断，后续改普通 RuntimeEvent 或内部日志。 |
| 审计 API | `src/flowweaver/api/routes_audit_events.py` | `/api/v1/audit-events` 是独立审计查询接口。 | 删除接口文件。 |
| API 注册 | `src/flowweaver/api/app.py` | 当前注册 `audit_events_router`。 | 移除 import 和 `include_router`。 |
| API 响应序列化 | `src/flowweaver/api/responses.py` | 当前对 `AuditEventModel` 有特殊序列化。 | 删除相关 import 和分支。 |
| 配置项 | `src/flowweaver/common/config.py` | `audit_level` 不再作为主程序默认运行配置。 | 删除配置字段。 |
| 数据库迁移 | `migrations/versions/20260627_0001_create_runtime_store.py`、`migrations/versions/20260627_0008_node_task_skeleton.py`、`migrations/versions/20260629_0010_permission_grants.py` | 迁移里创建了 `audit_events`、`permission_grants` 和 `node_tasks.permission_handle_id`。 | 新增清理迁移，或在当前开发阶段重写迁移链。 |
| 桌面 API 客户端 | `Avalonia_UI/Api/EngineHostApiClient.cs`、`Avalonia_UI/Api/IEngineHostApiClient.cs`、`Avalonia_UI/Api/EngineHostDtos.cs` | 桌面端有 `ListAuditEventsAsync` 和 `AuditEventDto`。 | 删除审计 API 客户端方法和 DTO。 |
| 桌面 ViewModel | `Avalonia_UI/ViewModels/MainWindowViewModel.cs` | 当前维护 `AuditEvents`、审计刷新命令、审计 loading/error 状态。 | 删除审计状态和命令，只保留 RuntimeEvent 日志。 |
| 审计列表 ViewModel | `Avalonia_UI/ViewModels/AuditEventListItemViewModel.cs` | 只服务 AuditEvent 列表展示。 | 删除文件。 |
| 审计列表 View | `Avalonia_UI/Views/Components/Logs/AuditEventListView.axaml`、`Avalonia_UI/Views/Components/Logs/AuditEventListView.axaml.cs` | 审计列表 UI 不再需要。 | 删除文件。 |
| 日志页面 | `Avalonia_UI/Views/Pages/LogsAuditPage.axaml`、`Avalonia_UI/Views/Pages/LogsAuditPage.axaml.cs` | 当前页面同时展示 RuntimeEvent 和 AuditEvent。 | 改成单纯日志页，或重命名为 LogsPage。 |
| 日志过滤栏 | `Avalonia_UI/Views/Components/Logs/LogFilterBarView.axaml` | 当前有 Audit 刷新按钮和审计相关 loading。 | 移除 Audit 按钮，只保留 RuntimeEvent 查询。 |
| Shell 页面注册 | `Avalonia_UI/Models/BuiltinShellPages.cs`、`Avalonia_UI/Views/Components/Shell/AppShellPageHost.axaml` | 当前页面名和承载类型仍叫 LogsAuditPage。 | 后续改为 LogsPage 或只保留 RuntimeEvent 日志页。 |
| 本地化文案 | `Avalonia_UI/Localization/zh-Hans.json`、`Avalonia_UI/Localization/en-US.json` | 包含审计页、审计事件、审计刷新失败等文案。 | 删除审计文案，日志页只保留运行事件相关文本。 |

## 测试调整清单

| 测试位置 | 移除/调整原因 | 后续处理 |
|---|---|---|
| `tests/unit/test_node_permission_resolution.py` | 专门测试内置节点权限解析。 | 删除。 |
| `tests/unit/test_protocol_serialization.py` | 包含权限/审计模型序列化用例。 | 移除对应用例。 |
| `tests/integration/test_runtime_store.py` | 测试 permission grant 和 audit event 存储。 | 删除相关断言和用例。 |
| `tests/integration/test_api.py` | 包含 `/api/v1/audit-events` 接口测试。 | 删除审计 API 用例。 |
| `tests/integration/test_builtin_table_nodes.py` | 当前手动创建 permission grant，并断言权限审计事件。 | 改为验证节点直接运行和输出数据。 |
| `tests/integration/test_builtin_shared_table_nodes.py` | 当前共享表节点依赖权限句柄和审计断言。 | 改为验证共享表发布/读取本身。 |
| `tests/integration/test_workflow_process_main.py` | 当前断言任务 permission handle、grant、permission audit。 | 删除权限相关断言，保留工作流执行和输出验证。 |
| `tests/integration/test_k0b_formal_path_smoke.py` | 当前断言存在审计事件。 | 移除 `list_audit_events()` 断言。 |

## 文档修改清单

| 文档位置 | 当前问题 | 后续处理 |
|---|---|---|
| `docs/00_第一阶段技术接口与验收规范.md` | 把日志与审计、权限能力写成第一阶段接口。 | 删除或标记废弃，改为 RuntimeEvent/运行日志。 |
| `docs/01_第一阶段执行方案.md` | 包含 PermissionManager、AuditEvent、权限句柄相关执行计划。 | 移除主程序权限审计计划。 |
| `docs/02_数据库共享表与节点故障隔离_讨论方案.md` | 共享表方案仍围绕权限句柄和审计控制。 | 改成共享表数据校验和运行引用，不走权限句柄。 |
| `docs/03_架构讨论阶段总结.md` | 大量章节将权限/审计作为平台核心能力。 | 统一标记为已废弃或重写为“主程序不做权限审计”。 |
| `docs/FlowWeaver_NODE-CONFIG-SCHEMA-0_后端配置Schema边界清单.md` | `secret`、路径权限、运行时权限校验仍指向主程序权限体系。 | 调整为后置能力，由节点方案单独讨论。 |
| `docs/FlowWeaver_Gemini_UI界面设计_MainWindow拆分与接口规划任务说明.md` | UI 规划包含 AuditEvent、LogsAuditPage、审计列表。 | 移除审计页面要求，日志页只保留 RuntimeEvent。 |
| `docs/FlowWeaver_UI-COMPACT-0_工作流页面精简与通知日志浮层边界清单.md` | 完整日志页仍描述 RuntimeEvent/AuditEvent 双列表。 | 改为 RuntimeEvent 和最近运行事件。 |
| `docs/FlowWeaver_UI-ACTION_总体验收复核.md` | 复核范围包含 Logs/Audit 双刷新状态。 | 改为 RuntimeEvent 刷新状态。 |
| `docs/nodes/FlowWeaver_节点规划核心模板.md` | 节点模板包含权限句柄、AuditEvent、需要权限栏目。 | 移除权限句柄和审计，改为“副作用/外部资源说明”。 |
| `docs/nodes/FlowWeaver_节点模板减法建议.md` | 仍保留简单权限声明和默认审计讨论。 | 改为后置或移除。 |
| `docs/nodes/FlowWeaver_节点核心模板_当前主程序框架支持分析.md` | 当前把权限审计作为主程序支持能力/缺口分析。 | 更新为“权限审计将从默认主程序移除”。 |
| `docs/nodes/00_FlowWeaver_防止主程序与节点耦合方案.md` | 仍把权限入口、授权、权限句柄写入主程序边界。 | 暂时保留，等代码移除完成后再统一更新耦合列表。 |

## 不纳入本次移除范围

| 内容 | 位置 | 保留原因 |
|---|---|---|
| 发布 runtime audit | `tools/portable_runtime_audit.py`、`tests/unit/test_portable_runtime_audit.py`、P 阶段发布文档 | 这是发布包运行时检查，不是主程序运行期权限/审计模块。 |
| RuntimeEvent | `src/flowweaver/protocols/events.py`、`src/flowweaver/api/routes_events.py`、桌面 RuntimeEvent 日志页面 | 这是工作流运行状态和调试显示所需能力，应保留。 |
| 节点运行状态 | `NodeRunStatus` 中除 `WAITING_PERMISSION` 之外的状态 | 这是工作流运行所需状态机，应保留。 |
| 数据引用和表格读取 | `TableRef`、`DataRef`、`SQLiteRuntimeTableProvider` | 这是当前数据中转核心能力，不属于权限审计模块。 |

## 建议执行顺序

1. 先移除节点运行路径上的权限检查：`NodeTask.permission_handle_id`、`NodeTaskManager` 权限生成、内置节点 `ensure_task_permission_scope`。
2. 再清理存储层：`permission_grants`、`audit_events`、RuntimeStore 对应 CRUD。
3. 再清理 API 和桌面 UI：删除 `/api/v1/audit-events`、AuditEvent DTO、AuditEvent 列表和刷新命令。
4. 最后清理测试和历史文档，把“主程序权限审计”统一标记为已移除或后置。

## 预期结果

移除完成后，主程序只保留：

- 工作流定义和结构校验。
- 工作流运行生命周期。
- 节点调度和状态记录。
- RuntimeEvent 运行事件。
- 数据引用、表格中转和共享表基础能力。

主程序不再负责：

- 权限申请。
- 权限授权。
- 权限句柄。
- 权限撤销。
- 安全审计事件。
- 字段级/表级权限追踪。

这样可以减少默认主程序复杂度，也能降低节点体系对主程序的耦合。
