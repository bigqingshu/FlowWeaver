# 阶段Q：后端大文件解耦方案

> 文档状态：历史执行规划，当前状态已校正
> 当前用途：梳理后端偏大文件的当前职责、耦合风险和后续拆分顺序
> 原执行边界：只分析和规划后端；前端 UI 正在重构，本文不安排 UI 代码改动

## 0. 2026-07-12 状态校正

本文原始大文件行数和拆分建议保留为历史依据。当前源码已经完成主要低风险拆分：

- 表节点 runner、纯表处理、保存、写入、控制、文件和配置 helper 已拆为独立模块，`builtin_table.py` 不再承载原先全部实现。
- 默认节点 definitions 已按表处理、写入、控制和资源类别拆分，`default_registry.py` 保持聚合入口。
- `runtime_record_mappers.py` 已拆出；RuntimeStore 事务边界仍保持集中。
- workflow process 已拆出 process loop、runtime initialization、dispatch、supervision、IPC 和 finalization 等职责。
- runs API 已拆出 `run_review.py` 和 `run_table_cleanup.py`，有界清理不再堆在路由函数中。

原第 6 节列出的三个契约缺口也已独立解决：结果 binding 已由输入解析和目录消费；WriteSelected/WriteBack 已有稳定 `target` binding；SaveRun 已声明 `in` 和 `out/transit` 表槽位。后续解耦应继续保持“移动职责”和“修改行为”分批提交。

## 1. 当前结论

后端当前最大的耦合点不是 API 层，而是节点实现层和运行存储层。

第一轮低风险解耦已经完成：

| 已完成项 | 说明 | 影响 |
| --- | --- | --- |
| 拆出 `runtime_models.py` | 将 `WorkflowRun`、`NodeRun`、`RuntimeEventLog`、`SharedPublication` 等运行数据模型从 `runtime_store.py` 拆出 | API、共享表读取等模块可依赖轻量模型，不必隐式依赖完整存储实现 |
| 拆出 `builtin_table_node_types.py` | 将表节点类型常量从 `builtin_table.py` 拆出 | 节点定义注册层不再为了拿常量导入完整表节点实现 |

后续建议继续按“先解除导入耦合，再拆实现职责，再整理测试”的路线推进。

## 2. 大文件扫描结果

| 文件 | 当前行数约 | 当前职责 | 主要问题 | 优先级 |
| --- | ---: | --- | --- | --- |
| `src/flowweaver/nodes/builtin_table.py` | 7683 | 普通表节点、控制节点、写入节点、文件节点、插件节点、表节点 runner、配置解析 helper、schema helper | 单文件职责过多，新增节点容易互相影响；测试定位成本高 | 最高 |
| `src/flowweaver/nodes/default_registry.py` | 2642 | 所有默认节点定义、端口、表槽位、配置 schema | 节点定义和配置 schema 堆在一起，任何节点 schema 改动都触碰大文件 | 高 |
| `src/flowweaver/engine/runtime_store.py` | 2540 | RuntimeStore 存储操作、状态迁移、记录转换、TableRef、共享表、事件记录 | 已拆出模型，但记录转换和多领域存储操作仍集中 | 高 |
| `src/flowweaver/workflow_process/main.py` | 1375 | 工作流进程入口、主循环、调度、取消、超时、IPC 事件、资源清理 | 主循环过长，调度和执行监督边界不够清楚 | 中高 |
| `src/flowweaver/workflow_process/node_tasks.py` | 674 | 节点任务创建、结果应用、失败传播 | 仍可接受，但后续控制/循环增强后可能继续变大 | 中 |
| `src/flowweaver/api/routes_runs.py` | 513 | run 查询、后台运行列表、回看、取消、重试、表目录、清理 | API 路由和 review/cleanup 业务 helper 混合 | 中 |
| `src/flowweaver/nodes/table_node_handlers.py` | 484 | 表节点上下文、读写表 helper、输出目标写入 | 当前体量可接受；后续节点拆分后可作为稳定底座 | 中 |
| `src/flowweaver/workflow_process/loop_control.py` | 472 | 循环控制状态处理 | 体量尚可，后续循环真实调度增强时再评估 | 低 |
| `src/flowweaver/workflow/runtime_options.py` | 404 | 配置字解析、合并、过滤 | 当前边界清楚，暂不优先拆 | 低 |
| `src/flowweaver/engine/supervisor.py` | 394 | 工作流进程 supervisor | 当前体量可接受，暂不优先拆 | 低 |

## 3. 核心问题与解法

### 3.1 `builtin_table.py` 太大

大白话问题：

现在所有表节点都挤在一个文件里。加一个普通表节点、写入节点、控制节点或文件节点，都要打开同一个 7000 多行文件，查找、审查、合并冲突都会变慢。

代码分析：

- 节点类型常量已拆出，导入耦合已降低。
- 文件内仍混有：
  - 纯表转换节点。
  - 控制信号预览节点。
  - 写入类节点。
  - 文件资源类节点。
  - 插件节点占位执行。
  - 表节点 runner。
  - 大量配置解析和数据处理 helper。

解决方案：

第一批建议按节点类别拆，不先追求极细：

| 新模块建议 | 放置内容 |
| --- | --- |
| `nodes/builtin_table_runner.py` | `BuiltinTableNodeRunner`、节点 handler registry 装配 |
| `nodes/table_transform_nodes.py` | 筛选、增删列、复制列、重命名、填充、替换、去重、提取、合并、数值、日期等纯表转换节点 |
| `nodes/table_control_nodes.py` | `ConditionFlagNode`、跳转、循环预览、子工作流预览等控制状态节点 |
| `nodes/table_write_nodes.py` | `SaveMemoryTableNode`、`SaveRunTableNode`、`WriteSelectedColumnsNode`、`WriteBackTableNode` |
| `nodes/file_table_nodes.py` | `ListFilesNode`、`BatchRenameFilesNode` |
| `nodes/plugin_table_node.py` | `PluginNode` 相关占位执行和 manifest 校验 |
| `nodes/table_node_config.py` | 通用 `_int_config`、`_bool_config`、`_enum_config`、字段列表解析等配置 helper |

验收标准：

- `is_table_node_type()` 和 `BuiltinTableNodeRunner` 的外部导入路径保持兼容，必要时在旧模块 re-export。
- 每次拆分只移动一类节点，不混入行为修改。
- 原有节点测试先保持通过，再进入下一类拆分。

### 3.2 `default_registry.py` 节点定义过集中

大白话问题：

节点怎么显示、有哪些端口、有哪些配置字段，全写在一个大文件。后续节点越来越多后，改一个节点配置也容易碰到不相关内容。

代码分析：

- `default_registry.py` 现在仍负责所有默认节点定义和全部 schema。
- `builtin_table_node_types.py` 已让它不再依赖完整表节点实现，这是继续拆分的前置条件。

解决方案：

建议按节点类别拆 schema 和 definitions：

| 新模块建议 | 放置内容 |
| --- | --- |
| `nodes/definitions/table_transform_definitions.py` | 纯表转换节点定义和 schema |
| `nodes/definitions/table_write_definitions.py` | 保存、写入、写回节点定义和 schema |
| `nodes/definitions/control_definitions.py` | 条件、跳转、循环、子工作流预览节点定义 |
| `nodes/definitions/resource_definitions.py` | 文件、插件、SQL、共享表节点定义 |
| `nodes/default_registry.py` | 只保留聚合注册入口 |

验收标准：

- `/api/v1/nodes` 返回字段不变。
- 节点定义顺序保持稳定，避免 UI 下拉顺序无意义变化。
- 每个 definition 模块有定向测试覆盖关键节点的端口、表槽位和默认配置。

### 3.3 `runtime_store.py` 仍承担太多存储职责

大白话问题：

RuntimeStore 负责工作流、进程、节点、循环、表引用、共享表、事件等所有数据库操作。现在模型已经拆出，但存储操作仍然比较集中。

代码分析：

- `runtime_models.py` 已完成，降低了“只需要模型也要导入 RuntimeStore”的问题。
- 记录转换函数仍在 `runtime_store.py` 尾部。
- 共享表、read lease、input snapshot、loop runtime、TableRef 操作仍由同一个类承载。

解决方案：

先拆无状态转换，再拆领域 helper，不建议马上把 RuntimeStore 类拆成很多仓储类。

| 阶段 | 动作 | 原因 |
| --- | --- | --- |
| 1 | 拆 `runtime_record_mappers.py` | 记录到模型的转换没有业务状态，最容易安全移动 |
| 2 | 拆 `runtime_status_guards.py` | 终态集合、状态来源校验、状态值转换可独立 |
| 3 | 拆 `shared_table_store_helpers.py` | 共享表 publication、snapshot、lease 逻辑相对独立 |
| 4 | 再评估是否拆 repository 类 | 过早拆类会增加事务和 session 传递复杂度 |

验收标准：

- RuntimeStore 对外方法名保持不变。
- 事务边界不跨模块变复杂。
- Alembic 和 RuntimeStore integration 测试通过。

### 3.4 `workflow_process/main.py` 主循环过重

大白话问题：

工作流运行主循环同时管启动、调度、执行、取消、超时、IPC 事件和清理。以后后台运行和循环真实执行继续增强时，这个文件会越来越难读。

代码分析：

- 工作流 DAG、ready queue、node task manager 已经拆出一部分。
- `main.py` 仍有 executor owner、调度、取消、结果应用、IPC event 记录等多类职责。

解决方案：

建议不动主循环语义，先把辅助职责移走：

| 新模块建议 | 放置内容 |
| --- | --- |
| `workflow_process/executor_owner.py` | `_DefaultWorkflowProcessExecutorOwner` 和 executor 关闭逻辑 |
| `workflow_process/task_dispatch.py` | ready node dispatch、dispatch slot 计算 |
| `workflow_process/task_supervision.py` | 节点执行监督、超时、取消请求 |
| `workflow_process/ipc_events.py` | IPC event handler 和 runtime event 记录 |
| `workflow_process/process_finalization.py` | terminal 判断、lease 释放、空工作流完成 |

验收标准：

- `run_workflow_process()` 对外入口不变。
- 主循环文件明显变薄，但状态机行为不变。
- 工作流进程主路径和取消/超时测试通过。

### 3.5 `routes_runs.py` 路由和业务 helper 混合

大白话问题：

运行相关 API 现在既有路由，也有后台运行列表、回看 payload、表清理逻辑。文件还不算特别大，但后续后台运行管理会继续增加。

代码分析：

- 表清理逻辑已经有明确边界：只清内部 `MEMORY` / `RUNTIME_SQL`。
- review payload 是轻量表目录，不携带 rows。
- 当前可以继续工作，但后续批量清理、保留策略、后台 run 管理会让文件增长。

解决方案：

| 新模块建议 | 放置内容 |
| --- | --- |
| `api/run_review.py` | `_run_review_payload`、表目录 summary |
| `api/run_table_cleanup.py` | 清理内部 TableRef 的 helper |
| `api/run_pagination.py` | pagination 校验小工具 |

验收标准：

- 路由函数只负责参数、依赖、错误响应拼装。
- 清理内部表的规则集中，不能散落在多个 API 文件。
- API 集成测试通过。

## 4. 推荐执行顺序

| 顺序 | 阶段 | 说明 | 建议提交信息 |
| ---: | --- | --- | --- |
| 1 | 已完成：拆运行模型与节点类型常量 | 当前已完成并验证 | `后端: 拆分运行模型与节点类型常量` |
| 2 | 拆 `builtin_table.py` 的 runner 和配置 helper | 先把通用支撑层移走，降低后续节点拆分冲突 | `后端: 拆分表节点运行器与配置辅助函数` |
| 3 | 拆纯表转换节点模块 | 普通节点最多，收益最大；保持行为不变 | `后端: 拆分纯表转换节点实现` |
| 4 | 拆写入类和控制类节点模块 | 写入、控制语义更敏感，放在纯表节点之后 | `后端: 拆分写入与控制类表节点` |
| 5 | 拆 `default_registry.py` definitions | 节点实现拆完后，再同步整理定义层 | `后端: 拆分默认节点定义模块` |
| 6 | 拆 RuntimeStore record mappers | 无状态转换拆分，低风险瘦身 | `后端: 拆分运行存储记录转换` |
| 7 | 拆 workflow process 辅助职责 | 保持主入口不变，拆 executor owner / dispatch / IPC | `后端: 拆分工作流进程辅助模块` |
| 8 | 拆 runs API helper | 后台运行管理继续增强前收口 API 文件 | `后端: 拆分运行接口辅助逻辑` |

## 5. 性能与耦合约束

| 约束 | 说明 |
| --- | --- |
| 不改变运行语义 | 第一轮解耦只移动代码，不改节点结果、TableRef、RuntimeEvent、状态机语义 |
| 不增加运行时反射 | 节点注册继续显式导入和显式装配，避免字符串反射查找 |
| 保持兼容导入 | 外部已使用的 `BuiltinTableNodeRunner`、`is_table_node_type()` 等路径暂时保留 |
| 不跨事务拆 Store | RuntimeStore 的事务边界不能因为拆文件而变得隐蔽 |
| 不把 UI 逻辑带入后端 | 表槽位和节点定义只提供契约，不在后端判断 UI 展示细节 |
| 每阶段可独立回滚 | 每次只拆一类职责，提交粒度小，便于定位回归 |
| 测试先行验证 | 每阶段至少跑对应模块的 ruff、mypy、定向 pytest |

## 6. 契约缺口状态校正

当前审查还发现几个和解耦相关的契约缺口，建议和拆分同步处理，但不要混在纯移动代码提交里：

| 原问题 | 当前状态 |
| --- | --- |
| `output_slot_bindings` 已保存，但输入解析和表目录没有完全消费 | 已解决；resolver 优先结果 binding，目录使用可重建关系投影 |
| 写入类节点有第二张产物表，但槽位绑定只标 `status` | 已解决；真实目标表同时登记 `target` |
| `SaveRunTableNode` 缺少 `output_table_slots` 定义 | 已解决；声明 `in` 与 `out/transit`，并按批读取输入 |

这些问题均通过独立行为提交完成，没有混入单纯代码搬迁批次。
