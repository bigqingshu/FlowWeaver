# FlowWeaver MEM-0 内存表 Provider 与辅助表边界清单

日期：2026-07-06

## 目标

在 FlowWeaver 中引入最小内存表 provider 能力，用于承载类似 DataFlowKit “中转副表/内存副表”的使用体验，但底层仍保持 `TableRef + provider` 边界。

第一轮只覆盖 MEM-0 到 MEM-4：

- 内存表 provider 最小读取能力。
- 数据 API 可通过 provider 路由读取内存表。
- 保存内存表节点最小实现。
- 节点可输出“当前主表 + 辅助内存表”。
- 后续节点默认继续沿当前主表执行，不因为辅助表存在而改变主流程。

## 核心语义

内存表不是主程序里的全局业务数据库，也不是工作流定义的一部分。它是运行期表数据的一种 provider 实现。

推荐模型：

```text
节点输出数据
-> MemoryTableProvider 保存 rows
-> RuntimeStore 注册 TableRef
-> NodeTaskResult.output_refs 记录 TableRef ID
-> 数据预览 API 按 provider_id 读取
```

## 主表与辅助表

当前阶段只定义两类角色：

- `TableRole.CURRENT`：主流程当前表。
- `TableRole.AUXILIARY`：辅助表，也就是用户视角里的“内存副表/中转副表”。

保存内存表节点的第一版语义：

```text
输入 CURRENT 表
-> 写入 AUXILIARY 内存表
-> CURRENT 表原样透传
-> NodeTaskResult.output_refs = [current_ref_id, memory_ref_id]
```

这样可以支持“不干预当前工作表”的需求：

- 后续普通表处理节点继续处理当前主表。
- 数据预览仍能看到新生成的内存副表。
- 内存副表后续可作为多表节点、插件节点、循环节点、节点组的输入基础。

## 与 DataFlowKit 的差异

DataFlowKit 的中转副表大致是：

```text
context["transit_tables"][name] = {"headers": headers, "rows": rows}
```

FlowWeaver 不建议把整张表直接塞进 workflow context。当前方向是：

```text
logical_table_id/name
-> TableRef(provider_id="memory", storage_kind="MEMORY")
-> MemoryTableProvider 私有句柄
```

这能保留用户理解上的“中转副表”，同时让主程序继续只编排 `TableRef`。

## 第一版明确不做

以下能力不进入 MEM-0 到 MEM-4：

- append 追加写入。
- 表头并集对齐。
- TTL、内存上限和自动释放策略。
- 跨进程共享内存、mmap、Arrow IPC 或 spill。
- UI 专项展示和交互优化。
- 插件、循环、节点组对内存表的专门适配。
- 保存到 SQLite、xlsx、CSV 或共享发布。

## 跨进程边界

第一版内存 provider 是最小内存读取边界，主要用于固化协议、节点输出和测试闭环。

真实正式路径中，WorkflowProcess 可能独立于 EngineHost 运行。普通 Python 进程内存不能天然跨进程共享，因此跨进程可预览需要后续单独收口：

- 共享内存。
- 内存映射文件。
- Arrow IPC。
- 临时 SQLite / DuckDB spill。
- EngineHost 托管的内存表服务。

在这些方案确定前，不把第一版内存 provider 承诺为可跨 EngineHost/WorkflowProcess 重启恢复的能力。

## MEM-0 到 MEM-4 验收点

MEM-1/MEM-2：

- `MemoryTableProvider` 可以保存 rows 并返回 `TableRef`。
- 支持 schema、row_count、分页 rows。
- 数据 API 可以通过 provider registry 读取内存表。

MEM-3：

- 新增保存内存表节点。
- 输入必须有且只有一张当前表。
- 当前表透传。
- 额外输出辅助内存表。

MEM-4：

- `NodeTaskResult.output_refs` 可同时记录主表和辅助表。
- 下游普通节点默认只沿 `TableRole.CURRENT` 表继续执行。
- 辅助表不提前进入连接 UI 主概念。
