# FlowWeaver 循环真实执行大白话实施方案

更新时间：2026-07-07

## 文档定位

当前 `LoopStartNode` 和 `LoopJudgeNode` 已经可以输出预览控制状态表，但还不会真的让流程回到上一段重新执行。

本文基于当前后端代码状态，按“问题是什么 -> 大白话说明 -> 当前代码分析 -> 解决方法”的方式，说明后续真实循环要怎么落。

## 总体判断

当前后端主流程仍是标准的一次性 DAG 执行模型：

```text
工作流定义 -> 普通连接 -> DAG 拓扑排序 -> 上游成功后下游 ready -> 全节点成功后工作流完成
```

所以真实循环不是简单地让 `LoopJudgeNode` 输出 `continue_loop` 就能完成。真正要做的是：让主程序知道哪里是循环区域、每一轮怎么记账、每一轮用什么输入、什么时候继续、什么时候结束。

第一版建议只支持一种清楚的循环结构：

```text
循环开始 -> 循环内容 -> 循环判断 -> 继续下一轮或结束循环
```

## 问题一：现在流程只能一路往下跑

### 大白话

现在流程更像这样：

```text
A 跑完 -> B 跑 -> C 跑
```

但真实循环需要这样：

```text
A 跑完 -> B 跑 -> 判断 -> 回到 B 再跑一轮
```

如果直接在流程图里画一条回线，主程序会把它当成“流程有环”，而不是当成合法循环。

### 当前代码分析

当前 `WorkflowDefinitionModel` 只有这些核心结构：

```text
nodes
connections
inputs
outputs
failure_policy
runtime_options
```

也就是说，定义层现在只有普通连接，没有专门的：

```text
循环区域
循环边
继续分支
结束分支
控制边
```

`WorkflowDag` 当前从 `connections` 建图，并做拓扑排序。如果发现环，会直接报：

```text
Workflow DAG contains a cycle
```

工作流校验里也会拒绝普通连接形成的 cycle。

### 解决方法

不要把循环回线塞进普通 `connections`。

后续需要单独增加一种“循环区域”描述，例如：

```text
loop_id
start_node_id
judge_node_id
body_node_ids
continue_target
end_target
max_iterations
```

普通 `connections` 继续保持无环，用来表达数据依赖。

循环的“继续下一轮”和“结束循环”走单独的控制协议，不混进普通 DAG。

## 问题二：DAG 现在只能算一次，不能天然重复跑一段节点

### 大白话

现在主程序拿到流程图后，会先排好顺序：

```text
先跑谁，后跑谁
```

这个顺序是一次性的。循环需要的是：

```text
这一段节点第 1 轮跑一次
第 2 轮再跑一次
第 3 轮再跑一次
```

这和普通 DAG 的“一次跑完”不是一回事。

### 当前代码分析

`build_workflow_dag` 会生成：

```text
nodes
topological_order
ready_node_ids
```

每个 DAG 节点记录的是：

```text
node_instance_id
node_type
node_version
config
upstream_node_ids
downstream_node_ids
```

这里没有“第几轮”的概念，也没有“循环体内节点”的概念。

`restrict_workflow_dag_to_upstream_closure` 也只是按普通上游闭包裁剪 DAG，不会解释循环区域。

### 解决方法

后续建议拆成两层：

| 层级 | 作用 |
|---|---|
| 数据 DAG | 继续负责普通数据依赖，保持无环 |
| 循环计划 | 单独描述哪些节点属于循环体，以及循环如何继续或退出 |

第一版不要让 DAG 自己支持任意环，而是让主程序识别一个结构化循环块。

这样普通流程还是普通流程，循环流程走专门的循环调度逻辑。

## 问题三：ready 逻辑现在只认“上游全部成功”

### 大白话

现在主程序判断一个节点能不能跑，规则很简单：

```text
它的上游都成功了，它就可以跑
```

循环需要多一个判断：

```text
上一轮判断说继续，才创建下一轮
上一轮判断说结束，就不再创建下一轮
```

当前 ready 逻辑还不会看这种“继续/结束”的控制结果。

### 当前代码分析

`collect_ready_node_candidates` 当前只收集状态为 `READY` 的节点。

准备输入时，逻辑是：

```text
遍历当前节点的上游
读取上游最新成功结果
只取 role=CURRENT 的 TableRef 作为输入
```

这说明现在 ready 队列只理解普通数据依赖。

`LoopJudgeNode` 当前虽然能输出：

```text
selected_branch=continue_loop
selected_branch=end_loop
actual_control=false
```

但 ready 队列不会读取这个结果，也不会据此创建下一轮。

### 解决方法

真实循环需要增加一个“循环调度判断”步骤：

```text
LoopJudgeNode 成功
主程序读取判断状态表
如果结果是 continue_loop，创建下一轮
如果结果是 end_loop，放行循环出口
```

这个逻辑应该放在主程序的通用控制协议里，不应该写成某个节点 handler 自己调度下游。

## 问题四：每个节点现在默认只有一条运行记录

### 大白话

循环最容易乱的地方是记录。

如果 B 节点跑了 5 轮，用户后面会问：

```text
B 第几轮失败了？
B 第 3 轮输出的是哪张表？
B 第 4 轮有没有开始？
```

如果还是只用一条 B 的运行记录，这些问题就答不上来。

### 当前代码分析

当前 `NodeRun` 记录包含：

```text
node_run_id
workflow_run_id
node_instance_id
node_type
status
attempt
started_at
finished_at
progress
current_stage
error
```

这里没有：

```text
loop_id
iteration_index
parent_iteration_id
execution_scope
```

`initialize_node_runs` 当前会按 DAG 节点初始化 NodeRun。

`get_node_run_for_instance` 当前按：

```text
workflow_run_id + node_instance_id
```

取节点运行记录。

虽然数据库表上没有明确写唯一约束，但当前运行代码大量假设一个工作流运行里，一个 `node_instance_id` 对应一条主要 NodeRun。真实循环如果直接给同一个节点实例插入多条 NodeRun，会让这些查询变得不稳定。

### 解决方法

不要直接复用当前 NodeRun 模型硬塞多轮记录。

第一版建议新增循环记录层：

```text
LoopRun：记录整个循环
LoopIterationRun：记录每一轮
```

循环体内节点有两种可选方案：

| 方案 | 说明 |
|---|---|
| 扩展 NodeRun | 给 NodeRun 增加 loop_id、iteration_index、execution_scope |
| 独立轮次节点记录 | 保持普通 NodeRun 不动，新增循环轮次节点运行表 |

从低风险角度看，建议先设计清楚查询模型，再决定是否改 NodeRun。不要直接破坏现有 `workflow_run_id + node_instance_id` 的查询假设。

## 问题五：每一轮用什么输入表还没有统一规则

### 大白话

循环每一轮都要知道“这轮处理什么数据”。

可能是：

```text
原始表的下一行
上一轮输出结果
固定列表里的下一项
外部传入的一批任务
```

如果不固定规则，节点就会自己猜数据来源，后面很难排查。

### 当前代码分析

当前 ready 队列给节点准备输入时，只会从普通上游节点的成功输出中取 `TableRole.CURRENT`。

`LoopStartNode` 当前只是预览：

```text
记录输入行数
记录最大循环次数
记录计划迭代次数
输出 loop_plan 状态表
```

它不会真的拆出“第 N 轮输入表”。

`TableRef` 记录现在能知道表来自哪个：

```text
workflow_run_id
node_run_id
logical_table_id
role
storage_kind
```

但还没有循环轮次字段。

### 解决方法

第一版需要规定一种最简单的当前轮输入来源。

建议先支持：

```text
按输入表行逐轮处理
每轮生成一个当前轮输入表
```

每轮开始时，主程序生成或登记：

```text
loop_id
iteration_index
input_table_ref_id
```

循环体节点只读当前轮输入表，不直接读取整个原始输入表。

后续再扩展上一轮输出驱动、固定列表驱动、外部任务队列驱动。

## 问题六：判断节点现在只输出计划，不控制流程

### 大白话

现在 `LoopJudgeNode` 会说：

```text
我建议继续
或者
我建议结束
```

但主程序现在不会照做。

真实循环需要主程序听懂这个结果，然后决定：

```text
继续 -> 开下一轮
结束 -> 跳出循环
异常 -> 循环失败
```

### 当前代码分析

`LoopJudgeNode` 当前输出统一控制状态表：

```text
signal_type=loop_decision
selected_branch=continue_loop / end_loop
action=continue_loop_preview / end_loop_preview
actual_control=false
```

当前 controller 在节点成功后做的是：

```text
标记当前节点成功
恢复满足普通依赖的节点为 READY
如果所有节点成功，则工作流成功
```

它不会读取控制状态表，也不会解释 `selected_branch`。

### 解决方法

真实循环需要新增一个控制结果解释步骤：

```text
控制节点成功后
读取它输出的控制状态表
判断 signal_type 和 selected_branch
更新循环状态
决定是否创建下一轮或放行循环出口
```

同时保持节点 handler 的边界：

```text
节点只输出判断结果
主程序统一调度
```

## 问题七：可能无限循环

### 大白话

如果判断节点每次都说“继续”，流程就可能一直跑。

所以循环必须有硬刹车。

### 当前代码分析

`LoopStartNode` schema 里已经有：

```text
max_loop_count
```

handler 当前也会计算：

```text
planned_iterations = min(total_items, max_loop_count)
```

但这只是预览状态表里的计划数字。

主程序当前不会拿 `max_loop_count` 去阻止下一轮，因为还没有真实循环调度。

另外，现有故障测试里有无限循环 fault node 的超时处理，但那是单节点执行超时，不是工作流级循环次数保护。

### 解决方法

真实循环调度必须每次创建下一轮前检查：

```text
当前轮次 < 最大次数
```

达到上限时，主程序必须写清楚退出原因：

```text
达到最大循环次数
```

第一版可以先把达到上限作为“结束循环”还是“失败循环”做成明确配置，但无论哪种都必须记录清楚，不能静默停止。

## 问题八：失败和取消要能按轮次说清楚

### 大白话

循环里失败时，不能只说“节点失败”。

要能说清楚：

```text
哪个循环失败了？
第几轮失败了？
哪个节点失败了？
失败前生成了哪些表？
后续轮次有没有继续启动？
```

取消也是一样，要知道取消发生在第几轮。

### 当前代码分析

当前节点状态已经有：

```text
FAILED
CANCELLED
SKIPPED
```

`NodeTaskManager` 也已经有失败后跳过依赖节点的相关能力。

主流程里也能汇总 failed/skipped 节点。

但这些状态都是按普通节点运行记录来看的，没有循环层级。

当前事件类型里有：

```text
NODE_STARTED
NODE_PROGRESS
NODE_FINISHED
NODE_FAILED
WORKFLOW_FINISHED
WORKFLOW_FAILED
```

还没有循环开始、循环轮次开始、循环轮次结束、循环结束这类事件。

### 解决方法

需要增加循环级记录和事件。

最少需要两类记录：

```text
循环总记录：loop_id、状态、当前轮次、最大轮次、退出原因
每轮记录：iteration_index、状态、输入表、输出表、失败节点、错误信息
```

事件可以先规划为：

```text
LOOP_STARTED
LOOP_ITERATION_STARTED
LOOP_ITERATION_FINISHED
LOOP_FINISHED
LOOP_FAILED
LOOP_CANCELLED
```

取消时，主程序不再创建后续轮次，并把当前循环总记录标记为取消。

## 问题九：工作流完成判断现在要求节点全部成功

### 大白话

普通流程里，“所有节点都成功了”，工作流就成功。

循环里会出现一些新情况：

```text
循环继续时，同一段节点会跑多轮
循环结束后，不应该再创建下一轮
未进入的循环路径不能让工作流一直等
```

如果还只按“固定节点列表全部成功”判断，真实循环很容易卡住或提前结束。

### 当前代码分析

controller 当前完成判断是：

```text
列出当前 workflow_run 的所有 NodeRun
如果全部是 SUCCEEDED，则 workflow_run 标记为 SUCCEEDED
```

这个逻辑适合一次性 DAG。

但真实循环会引入动态轮次：

```text
第 1 轮节点
第 2 轮节点
第 3 轮节点
循环出口节点
```

如果这些动态记录没有统一完成规则，工作流完成判断会不准确。

### 解决方法

后续完成判断要升级为：

```text
普通 DAG 节点满足完成条件
循环总记录处于结束状态
所有已创建的循环轮次都处于终态
没有 ready/running/queued 的节点或轮次任务
```

第一版先不要支持复杂嵌套循环，避免完成判断过早复杂化。

## 问题十：UI 查询如果没有结构化记录会很难看

### 大白话

如果 UI 只看到一堆节点记录，用户会很难理解循环跑了几轮。

更自然的展示应该是：

```text
循环 orders_loop
  第 1 轮：成功
  第 2 轮：成功
  第 3 轮：失败
```

点开一轮，再看这一轮里的节点、输入表、输出表和错误。

### 当前代码分析

当前 API 和运行记录主要按 workflow run、node run、table refs 查询。

`TableRef` 能按 workflow_run 或 node_run 查询，但没有 loop_id / iteration_index。

如果不增加循环记录，UI 只能靠命名规则或日志内容猜测轮次，这会非常脆弱。

### 解决方法

后续记录层要给 UI 留明确查询入口：

```text
查询某个 workflow_run 下有哪些 LoopRun
查询某个 LoopRun 下有哪些 Iteration
查询某个 Iteration 下有哪些 NodeRun 和 TableRef
```

第一版 UI 可以先只做只读展示，不急着做复杂的循环编辑器。

## 问题十一：数据库怎么存循环记录

### 大白话

如果循环真的跑起来，就不能只靠普通节点记录。

需要有地方专门存：

```text
这个循环是谁
跑到第几轮
每一轮是什么状态
每一轮用了哪张输入表
每一轮最后输出了什么
```

否则后面 UI、恢复、失败排查都会没有稳定依据。

### 当前代码分析

当前数据库模型里有：

```text
workflow_runs
node_runs
node_tasks
node_task_results
data_refs
runtime_event_logs
```

但还没有：

```text
loop_runs
loop_iteration_runs
```

`NodeRunRecord` 里也没有 `loop_id`、`iteration_index`、`loop_run_id` 这类字段。

当前迁移文件已经有多轮历史迁移，后续如果加循环记录，需要走正式 migration，而不是临时塞 JSON。

### 解决方法

建议第一版新增两张运行记录表：

```text
loop_runs
loop_iteration_runs
```

`loop_runs` 记录整个循环：

```text
loop_run_id
workflow_run_id
loop_id
start_node_instance_id
judge_node_instance_id
status
current_iteration
max_iterations
exit_reason
started_at
finished_at
error
```

`loop_iteration_runs` 记录每一轮：

```text
loop_iteration_id
loop_run_id
iteration_index
status
input_table_ref_id
output_table_ref_id
started_at
finished_at
failed_node_run_id
error
```

后续再决定 NodeRun 是增加 loop 字段，还是通过关联表挂到某一轮。

## 问题十二：API 怎么给 UI 查

### 大白话

后端记录好了，还要让 UI 查得到。

UI 不应该自己去一堆节点日志里猜循环结构，而应该直接问后端：

```text
这个工作流有哪些循环？
这个循环跑了几轮？
这一轮里面有哪些节点？
这一轮用了哪些表？
```

### 当前代码分析

当前 API 已经能查：

```text
workflow run
node runs
table refs
data rows
runtime events
```

但还没有专门的循环查询接口。

如果后续只把循环信息塞进事件 payload，UI 会很难稳定分页、筛选、定位某一轮。

### 解决方法

建议后续增加只读 API：

```text
GET /runs/{run_id}/loops
GET /runs/{run_id}/loops/{loop_run_id}/iterations
GET /runs/{run_id}/loops/{loop_run_id}/iterations/{iteration_id}/nodes
GET /runs/{run_id}/loops/{loop_run_id}/iterations/{iteration_id}/table-refs
```

第一版 API 只做查询，不做编辑。

这样 UI 先能稳定展示循环运行情况，再考虑循环编辑体验。

## 问题十三：主程序崩溃后怎么恢复

### 大白话

真实运行时，程序可能跑到第 4 轮突然崩溃。

重启后要能知道：

```text
第 4 轮有没有开始？
第 4 轮有没有结束？
判断节点有没有给出结果？
要不要继续第 5 轮？
还是把循环标记为失败？
```

如果没有恢复规则，循环很容易重复跑一轮，或者漏跑一轮。

### 当前代码分析

当前主程序已有 workflow process、process_generation、owner_process_id 等运行归属信息。

NodeTask 结果应用时也有 stale attempt、stale generation、executor mismatch 这类保护。

但这些保护目前是围绕普通节点任务设计的，没有循环轮次状态机。

循环如果引入“动态创建下一轮”，恢复时必须知道上一轮处在哪个状态。

### 解决方法

循环记录需要可恢复。

建议每一轮有明确状态：

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
SKIPPED
```

恢复时按状态处理：

| 状态 | 恢复策略 |
|---|---|
| 循环总记录运行中，但没有运行中轮次 | 根据最后一轮判断结果决定继续或结束 |
| 某一轮运行中，但节点任务已丢失 | 按现有进程丢失策略标记失败或重新派发 |
| 判断节点已成功但还没创建下一轮 | 幂等地补创建下一轮或结束循环 |
| 已达到终态 | 不再创建新轮次 |

关键点是：创建下一轮必须幂等，不能恢复一次就多创建一轮。

## 问题十四：循环是串行还是并行

### 大白话

循环有两种玩法：

```text
第 1 轮跑完，再跑第 2 轮
或者
很多轮同时跑
```

第一种简单稳定，第二种性能高但记录和失败处理复杂。

### 当前代码分析

当前 ready queue 支持多个 ready 节点派发，也有每轮 dispatch 数量限制。

但现有调度并不知道“第几轮”的依赖关系。

如果第一版就允许循环轮次并行，会立刻遇到：

```text
多轮输出顺序怎么定
上一轮结果是否会影响下一轮
取消时哪些轮次已经启动
达到最大次数时是否还有已派发轮次
```

### 解决方法

第一版循环建议强制串行：

```text
第 N 轮结束并判断后，才允许创建第 N+1 轮
```

先把记录、恢复、失败、取消做稳。

并行循环可以作为后续能力，单独设计：

```text
parallelism
batch_size
result_order
partial_failure_policy
```

## 问题十五：嵌套循环和子工作流先不要混进来

### 大白话

循环里面再放循环，或者循环里面启动子工作流，会让问题翻倍。

第一版如果直接支持这些，记录会变成：

```text
外层第 3 轮
  内层第 5 轮
    子工作流第 2 个节点
```

这个复杂度不适合第一步。

### 当前代码分析

当前 `SubWorkflowNode` 也是预览控制节点，不创建子 `WorkflowRun`。

`SubWorkflowNode` 的预览 handler 里已经有 `allow_loop_nodes` 这类边界配置。

循环真实执行还没有落地前，如果同时打开子工作流真实执行，会让父子运行、循环轮次、表引用归属交织在一起。

### 解决方法

第一版真实循环明确限制：

```text
不支持嵌套循环
不支持循环体内真实子工作流
不支持子工作流内真实循环
```

如果配置里检测到这些结构，先返回清晰校验错误。

后续等单层循环稳定后，再扩展：

```text
parent_loop_run_id
parent_iteration_id
child_workflow_run_id
```

## 问题十六：每轮产生的表怎么清理

### 大白话

循环每跑一轮，都可能生成一批表。

如果跑 100 轮，就可能生成很多中间表。

这些表什么时候保留、什么时候清理、UI 能不能看历史轮次，都要提前想清楚。

### 当前代码分析

当前表引用有生命周期：

```text
STAGING
PUBLISHED
ACTIVE
RELEASED
RETIRED
ORPHANED
```

主程序在工作流结束时会释放未释放的 read leases。

但循环每轮输出表没有轮次归属字段，也没有循环级保留策略。

如果只按 node_run 查表，循环多轮后会很难按轮次清理。

### 解决方法

第一版先制定保守策略：

```text
每轮输入表和关键输出表保留到工作流结束
每轮临时 staging 表按现有清理机制释放
LoopIterationRun 记录关键 input/output table_ref_id
```

后续再增加可配置保留策略：

```text
保留全部轮次
只保留最后一轮
保留失败轮次
保留摘要不保留数据
```

但第一版不要默认删除调试所需的关键轮次表。

## 问题十七：预览节点怎么升级到真实循环

### 大白话

现在循环节点只是预览。

以后不能突然让所有旧流程里的循环节点都开始真实回跳，否则用户原来只是想看计划，结果流程突然开始重复执行。

### 当前代码分析

当前控制状态表里 `actual_control=false`。

`LoopStartNode` 和 `LoopJudgeNode` 的 handler 没有真实调度副作用。

主程序也没有读取这些状态表来改变执行路径。

### 解决方法

真实循环必须显式开启。

可以考虑两层开关：

```text
工作流定义声明启用真实控制协议
循环区域声明启用真实循环
```

旧流程默认继续走预览语义：

```text
actual_control=false
```

新真实循环执行时，状态表仍可输出，但需要清楚记录：

```text
actual_control=true
```

并且只在新协议工作流里生效。

## 问题十八：重复提交和重复结果要防住

### 大白话

真实循环会动态创建下一轮。

如果同一个判断结果被处理两次，就可能多创建一轮。

如果同一个节点结果重复上报，也可能让循环状态被推进两次。

### 当前代码分析

当前 NodeTask 结果已有一些防重复机制：

```text
task_id + result_id 唯一
attempt 校验
process_generation 校验
executor mismatch 拒绝
```

这些对普通节点足够有帮助。

但循环调度还需要额外保证：

```text
同一个 loop_run_id + iteration_index 只能创建一次
同一个判断结果只能推进一次循环状态
```

### 解决方法

循环记录要有唯一约束或幂等键：

```text
loop_run_id + iteration_index
loop_run_id + source_judge_node_run_id
```

推进循环状态时要用状态版本或事务保护：

```text
只有当前轮处于等待判断结果时，才能推进到下一轮或结束
```

这样即使主程序重试，也不会多创建轮次。

## 问题十九：失败策略和跳过策略要重新定义

### 大白话

普通流程失败时，可以直接失败，也可以跳过依赖节点。

循环里失败时要更细：

```text
失败的是当前轮
还是整个循环
还是整个工作流
```

如果不定义清楚，用户会不知道为什么后续节点没跑。

### 当前代码分析

当前失败策略有：

```text
FAIL_FAST
CONTINUE_INDEPENDENT
SKIP_DEPENDENTS
```

其中 `SKIP_DEPENDENTS` 还处于 reserved/unavailable 状态。

NodeRun 已有 `SKIPPED`，NodeTaskManager 里也有失败后跳过节点的相关逻辑。

但循环里的“跳过后续轮次”和普通 DAG 的“跳过下游节点”不是一回事。

### 解决方法

第一版先采用简单规则：

```text
循环体任一节点失败 -> 当前轮失败
当前轮失败 -> 循环失败
循环失败 -> 按工作流失败策略处理
```

不要第一版就支持“失败一轮但继续下一轮”。

后续再扩展：

```text
continue_on_iteration_failure
max_failed_iterations
failed_iteration_output_policy
```

## 问题二十：测试矩阵要提前列清楚

### 大白话

循环不是只测“能跑起来”就够了。

要测：

```text
成功结束
继续多轮
达到最大次数
中途失败
中途取消
空输入
恢复后不重复创建轮次
```

### 当前代码分析

当前已经有很多普通 DAG、节点执行、runtime store、workflow process 的测试。

控制节点也已经有预览状态表测试。

但真实循环需要新的测试层：

```text
循环协议校验测试
循环记录存储测试
循环调度集成测试
恢复和幂等测试
API 查询测试
```

### 解决方法

执行前先把测试矩阵列入目标：

| 类型 | 必测场景 |
|---|---|
| 定义校验 | 缺少循环开始、缺少判断、普通连接成环、嵌套循环 |
| 存储 | 创建 LoopRun、创建 Iteration、重复轮次拒绝 |
| 调度 | 继续一轮、结束循环、达到最大次数 |
| 失败 | 循环体失败、判断节点失败、判断结果非法 |
| 取消 | 当前轮取消、后续轮次不再创建 |
| 恢复 | 判断成功后崩溃、创建下一轮前崩溃、重复结果上报 |
| API | 查询循环、查询轮次、查询轮次节点、查询轮次表 |

这样后续执行目标时，不会只实现开心路径。

## 性能与耦合优化约束

本节是后续执行目标时必须遵守的硬边界。真实循环可以增加主程序调度能力，但不能把主程序改成对某几个节点类型写死逻辑，也不能让每轮运行产生不可控的数据和事件膨胀。

### 约束一：当前轮输入不要默认复制整张表

每一轮都需要明确输入，但不能默认每轮复制一整张原始表。

优先记录：

```text
source_table_ref_id
row_index / row_range / selector
materialized_input_table_ref_id
```

只有真正执行当前轮节点时，才按需物化当前轮输入表。

这样可以避免：

```text
1 万行输入 -> 1 万份整表副本
```

第一版可以先支持“按行物化小表”，但要保留 selector 字段，避免后续只能靠复制表扩展。

### 约束二：循环记录必须有查询索引

循环记录后续会被调度器、恢复逻辑和 UI 高频查询。

新增表时必须提前设计索引，至少包括：

```text
loop_runs(workflow_run_id, status)
loop_runs(workflow_run_id, loop_id)
loop_iteration_runs(loop_run_id, iteration_index)
loop_iteration_runs(loop_run_id, status)
```

如果后续有轮次和节点运行的关联表，也要能按：

```text
loop_iteration_id
node_run_id
```

快速查询。

不允许先只建表不建索引，再让 UI 或恢复流程靠全表扫描查轮次。

### 约束三：事件输出要分档，不能每轮刷太多日志

循环可能跑几十轮、几百轮，事件量会快速放大。

默认只记录关键摘要：

```text
循环开始
每轮开始
每轮结束
循环结束
失败
取消
达到上限
```

详细事件只在诊断模式开启：

```text
每轮节点详细进度
每轮表摘要
每轮判断详情
```

后台快速模式下，只保留低频摘要和最终结果，避免循环变成事件风暴。

### 约束四：表保留策略必须分档

循环每轮都可能生成表，不能默认永久保留所有中间表。

建议第一版支持三档：

| 模式 | 保留内容 |
|---|---|
| 普通模式 | 最后一轮、失败轮次、循环摘要 |
| 诊断模式 | 全部轮次关键输入输出 |
| 后台快速模式 | 最终结果和必要摘要 |

调试所需的关键表不能提前删除，但也不能无条件保留全部轮次的所有中间表。

如果某些表被清理，循环记录里仍要保留摘要：

```text
table_ref_id
logical_table_id
row_count
schema_fingerprint
released_at
```

### 约束五：主程序只解释控制协议，不写死具体节点类型

真实循环不能写成：

```text
if node_type == "LoopJudgeNode":
    创建下一轮
```

主程序应该只理解通用控制协议：

```text
signal_type
selected_branch
control_region
actual_control
```

`LoopStartNode` 和 `LoopJudgeNode` 只是产生控制信号的内置节点。

后续如果出现别的循环判断节点，只要输出相同协议，主程序就不应该再新增节点类型分支。

### 约束六：优先设计通用 execution_scope，不要只给 NodeRun 加 loop 字段

如果直接给 `NodeRun` 加：

```text
loop_id
iteration_index
```

会让 `NodeRun` 和循环强绑定。

更推荐设计通用执行作用域：

```text
execution_scope_id
scope_type: root / loop_iteration / subworkflow
parent_scope_id
```

这样后续可以同时支撑：

```text
循环轮次
子工作流
批处理
预览局部运行
```

第一版如果暂时不实现完整 execution_scope，也不能把字段命名和结构设计死成只服务循环。

### 约束七：TableRef 不直接塞循环字段，优先用关联表

`TableRef` 是通用表引用，不建议直接加：

```text
loop_id
iteration_index
```

更低耦合的方式是新增关联表：

```text
loop_iteration_table_refs
```

记录：

```text
loop_iteration_id
table_ref_id
role: input / output / summary / failed_snapshot
```

这样普通表引用模型保持干净，循环只是通过关联关系解释这些表属于哪一轮。

### 约束八：不要靠改 node_instance_id 拼接轮次

不能用这种方式解决多轮节点记录：

```text
nodeA__loop1__iter3
```

这种做法看起来简单，但会破坏：

```text
节点定义查询
节点配置覆盖
前端定位节点
运行记录归类
错误定位
```

轮次应该放在运行作用域或关联记录里，节点实例 ID 仍保持工作流定义里的原始 ID。

### 约束九：循环调度逻辑要集中成层

循环逻辑不能散落在多个地方：

```text
ready_queue 一点
controller 一点
node_tasks 一点
RuntimeStore 一点
```

建议后续集中成几个明确职责：

| 层 | 职责 |
|---|---|
| 控制协议解释层 | 读取控制状态，判断 continue/end |
| 循环状态推进层 | 创建轮次、结束循环、处理上限 |
| 完成状态评估层 | 判断工作流是否可以完成 |
| 循环记录存储层 | 写入 LoopRun、Iteration 和关联表 |

主流程只调用这些通用层，避免核心文件里出现大量循环专用细节。

### 约束十：第一版必须串行，不能同时打开并行轮次

第一版真实循环只支持：

```text
第 N 轮完成并判断后，才创建第 N+1 轮
```

不支持：

```text
多个轮次同时执行
循环体内部动态并行轮次
失败一轮但继续跑其他轮
```

并行循环会引入输出顺序、取消、失败聚合和资源占用问题，应作为后续独立目标。

### 约束十一：预览语义默认不变，真实循环必须显式启用

当前循环节点已经作为预览控制节点存在。

后续不能因为实现真实循环，就让旧工作流自动变成真实回跳。

必须显式满足：

```text
工作流启用真实控制协议
循环区域启用真实循环
控制状态 actual_control=true
```

旧流程默认继续：

```text
actual_control=false
```

这样可以避免已有预览流程突然变成真实循环。

## 最小实施顺序

| 阶段 | 要做什么 | 目标 |
|---:|---|---|
| 1 | 定义标准循环区域协议 | 主程序能认出哪里是循环开始、循环内容、循环判断和循环出口 |
| 2 | 设计数据库迁移 | 明确 LoopRun、Iteration、唯一约束和状态字段 |
| 3 | 增加循环总记录 | 能知道某个循环整体跑到哪里 |
| 4 | 增加每轮记录 | 能知道每一轮开始、结束、失败或取消情况 |
| 5 | 明确当前轮输入表规则 | 每一轮的数据来源清楚 |
| 6 | 增加控制结果解释逻辑 | `continue_loop` 和 `end_loop` 能真正影响调度 |
| 7 | 加最大次数保护 | 避免无限循环 |
| 8 | 增加幂等和恢复保护 | 崩溃或重复结果不会重复创建轮次 |
| 9 | 改造完成判断 | 循环结束后工作流能正确完成，不会卡住 |
| 10 | 加失败和取消收口 | 出错或取消时记录清楚，不继续乱跑 |
| 11 | 补 API 查询入口 | UI 能按循环和轮次查看运行过程 |
| 12 | 补完整测试矩阵 | 覆盖成功、失败、取消、恢复、达到上限等场景 |
| 13 | 再考虑 UI 编辑 | 在后端记录和调度稳定后，再做更完整的循环编辑体验 |

## 第一版验收标准

第一版只要能完成以下场景，就算循环真实执行基础打通：

```text
识别一个标准循环区域
创建循环总记录
创建第 1 轮记录
准备第 1 轮输入表
执行循环体
读取判断结果
继续时创建下一轮
结束时跳出循环
执行循环后续节点
```

同时需要能查到：

```text
循环一共跑了几轮
每一轮是否成功
每一轮用了哪张输入表
每一轮生成了哪些输出表
如果失败，失败在第几轮哪个节点
如果取消，取消发生在第几轮
如果达到上限，是正常结束还是失败
恢复后不会重复创建同一轮
API 能按循环和轮次查记录
第一版明确拒绝嵌套循环和真实子工作流混用
```

## 当前结论

当前后端已经具备普通 DAG 执行、节点状态、跳过状态、表引用记录、事件日志和预览控制状态表。

但真实循环还缺这些核心能力：

```text
循环区域协议
循环轮次记录
当前轮输入表规则
主程序控制结果解释
数据库迁移和唯一约束
恢复和幂等保护
API 查询入口
表保留和清理策略
完整测试矩阵
```

因此后续不要直接把循环回线塞进普通连接，也不要让节点 handler 自己调度下一轮。

最稳路线是先补循环协议和记录模型，再接入主程序调度。
