# FlowWeaver 表数据流解耦阶段验收复核

日期：2026-07-06

## 验收范围

本次复核对应 `FlowWeaver_表数据流与节点资源解耦边界清单.md` 的最小落地阶段。

目标是让主程序继续保持“编排表数据流”的角色：

- 工作流连接只表达节点依赖，不复制表。
- 节点结果继续通过 `TableRef` 传递。
- 数据预览入口按 `provider_id` 路由读取表。
- SQL 资源细节由 SQL 节点和 provider 解释，主程序不解释 SQL 语义。
- 新节点通过后端节点注册表和通用 `config_schema` 暴露给 UI。

## 小阶段完成矩阵

| 阶段 | 完成内容 | 结果 |
| --- | --- | --- |
| DF-0 | 固化表数据流与节点资源解耦边界清单 | 已提交 |
| DF-1 | 新增 `TableProviderRegistry`，数据 API 从硬编码 SQLite 读取改为 provider 路由 | 已提交 |
| DF-2 | 补充 TableRef 读取边界测试：未知 provider、不支持 storage kind、缺少 READ capability、生命周期不可用 | 已提交 |
| DF-3 | 在协议层新增 `EXTERNAL_SQL` 表存储类型，并补充序列化测试 | 已提交 |
| DF-4 | 新增外部 SQLite SQL 表读取 provider，支持只读 table/query 映射 | 已提交 |
| DF-5 | 新增 `SqlMappingNode` 骨架，执行后输出外部 SQL `TableRef`，不复制表数据 | 已提交 |
| DF-6 | 补充 SQL 映射节点正式工作流闭环 smoke：创建、运行、读取数据预览 | 已提交 |
| DF-7 | 复核 SQL 映射节点通用 API 契约，确认 UI 可通过通用节点定义和配置 Schema 获取能力 | 已提交 |
| DF-8 | 本文档总体验收复核 | 当前收口 |

## 当前代码事实

### 主程序边界

主程序仍只保存和调度以下通用结构：

- `WorkflowDefinition` 的节点、连接和节点 `config`。
- `NodeTaskResult.output_refs`。
- `TableRef` 及其 `provider_id`、`storage_kind`、`opaque_handle`、schema、capabilities。

主程序不解释：

- SQL 文本的业务含义。
- 物理数据库路径、物理表名或查询来源。
- SQL 节点配置中的资源语义。
- 外部资源的鉴权、连接池、profile 生命周期。

### 数据预览读取

数据预览 API 已改为通过 `TableProviderRegistry` 读取 `TableRef`。

最小读取边界为：

- `provider_id` 必须能找到 provider。
- `storage_kind` 必须被 provider 支持。
- `TableRef` 必须具备 READ capability。
- `TableRef` lifecycle 必须可读。
- provider 返回 schema、行数和分页样例数据。

### 外部 SQL 映射

当前 `SqlMappingNode` 的落地语义是：

```text
SQL 节点配置
-> 节点执行
-> 输出 EXTERNAL_SQL TableRef
-> 数据 API 通过 external SQL provider 读取
```

这满足“SQL 节点映射外部表时不复制表”的最小目标。

### UI/API 契约

SQL 映射节点已通过通用节点定义 API 暴露：

- 节点类型。
- 显示名称和描述。
- 通用配置 Schema。
- 输入输出说明。

因此 UI 不需要为 SQL 映射节点单独修改主结构；后续只需要在通用节点配置渲染、文案和表单体验上逐步增强。

## 已明确不支持

以下能力未在本阶段实现，属于后续阶段：

- 外部 SQL provider 目前只覆盖 SQLite。
- SQL 查询限制为只读查询；不支持多语句、写入语句或任意脚本执行。
- 尚未实现数据库 profile、凭据管理、连接池和资源生命周期管理。
- 尚未实现内存表 provider。
- 尚未实现 SQL 下推筛选、排序、选择列或懒执行链。
- 尚未实现保存、导出、发布节点的物化策略。
- 下游通用表处理节点读取外部 SQL 后，仍可能在自身处理边界内产出新的 runtime 表。
- 未新增多端口 UI，也未把连接作为主要用户操作入口。
- 未做 SQL 节点专用 UI 美化、本地化和高级配置控件。

## 后续建议顺序

1. 先稳定通用节点配置 Schema 的 UI 渲染能力。
2. 再补 SQL 节点的用户可读文案、默认值和错误提示。
3. 再做内存表 provider 或保存/导出节点，不与 SQL provider 混在一个阶段。
4. 需要性能优化时，优先从 provider 分页、schema 缓存和可下推查询开始。
5. 只有通用配置控件无法表达时，再考虑某类节点的专用 UI。

## 验收命令

```powershell
.\python312\python.exe -m pytest `
  tests\integration\test_data_api_provider_routing.py `
  tests\integration\test_external_sql_table_provider.py `
  tests\integration\test_builtin_sql_mapping_node.py `
  tests\integration\test_sql_mapping_workflow_smoke.py `
  tests\unit\test_protocol_serialization.py
```

结果：`20 passed, 1 warning`。

警告来自 FastAPI/Starlette TestClient 对当前 httpx 用法的弃用提示，不影响本阶段功能验收。
