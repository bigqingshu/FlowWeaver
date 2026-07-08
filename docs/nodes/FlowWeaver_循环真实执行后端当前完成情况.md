# FlowWeaver 循环真实执行后端当前完成情况

更新时间：2026-07-08

## 当前结论

循环真实执行的后端第一版已经从方案阶段进入落地阶段。

当前已经具备这条主链路：

```text
enabled 循环定义
-> 后端校验通过
-> 工作流启动时初始化 LoopRun
-> 创建第 1 轮 LoopIterationRun
-> 绑定第 1 轮入口 / 循环体 / 判断节点
-> 节点成功后按当前轮推进
-> 判断节点输出控制表
-> continue_loop 创建下一轮
-> end_loop 或 max_iterations 结束循环
-> 放行循环出口节点
-> 出口节点完成后工作流完成
```

目前只处理后端能力，没有修改前端 UI。

## 已落实功能

### 1. 真实循环开关

后端校验已经允许：

```text
control_protocol.mode=enabled
loop_region.enabled=true
```

同时保留预览边界：

- `preview` 模式仍然不会触发真实循环执行。
- `loop_region.enabled=true` 必须配合 `control_protocol.mode=enabled`。
- 不支持的 `input_mode` 仍然会被 schema 拒绝。
- 嵌套或重叠循环区域仍然不允许。

### 2. 循环运行初始化

新增后端初始化能力：

```text
initialize_enabled_loop_runtime_state
```

它负责：

- 识别 enabled 的 loop region。
- 幂等创建 `LoopRun`。
- 启动第 1 轮 `LoopIterationRun`。
- 将第 1 轮入口节点、循环体节点、判断节点关联到当前轮次。

该初始化已经接入 workflow process 主流程。

### 3. 轮次内节点归属

已经使用最小关联表：

```text
loop_iteration_node_runs
```

用于记录：

```text
loop_iteration_id
node_run_id
node_instance_id
role
```

现在同一个 `node_instance_id` 可以在不同轮次拥有不同 `NodeRun`，不会再只能按单个节点实例理解运行结果。

### 4. 轮次内节点推进

新增轮次内调度 helper：

```text
advance_loop_iteration_after_node_success
```

当前支持：

- 入口节点成功后，按 DAG 依赖放行当前轮循环体节点。
- 循环体节点成功后，放行当前轮判断节点。
- 新轮次不会一次性创建全部未来节点。
- 只在当前轮、当前需要的节点上创建运行记录。

### 5. 按 node_run_id 派发任务

ready 队列现在可以返回具体 `NodeRun` 候选。

任务提交支持传入：

```text
node_run_id
```

这样第二轮的 `loop_start` / `body` / `loop_judge` 不会和第一轮同名节点混淆。

### 6. 控制信号解释

节点成功后会读取输出表里的通用控制字段：

```text
signal_type
selected_branch
actual_control
source_node_id
target_anchor
details
```

当前支持：

- `actual_control=false` 只作为预览，不产生调度副作用。
- `continue_loop` 创建下一轮。
- `end_loop` 结束循环。
- `target_anchor` 用于匹配目标循环。
- 不依赖具体节点类型判断。

### 7. 下一轮创建

当判断结果为 `continue_loop` 时：

- 当前轮标记为 `SUCCEEDED`。
- 创建下一轮 `LoopIterationRun`。
- 创建下一轮入口节点 `NodeRun`。
- 入口节点进入 `READY`。

达到 `max_iterations` 时：

- 不再创建下一轮。
- `LoopRun` 进入 `MAX_ITERATIONS_REACHED`。
- 后续出口节点可以按依赖判断放行。

### 8. 循环出口放行

循环出口不是直接强行 READY，而是作为 DAG 的额外依赖条件。

出口节点需要同时满足：

- 普通上游依赖完成。
- 对应循环已进入可放行终态。

当前可放行的循环终态：

```text
ENDED
MAX_ITERATIONS_REACHED
```

### 9. 工作流完成判断

已经引入独立完成判断：

```text
WorkflowCompletionEvaluator
```

工作流成功需要同时满足：

- 普通节点完成。
- 所有 `LoopRun` 进入终态。
- 已创建的 `LoopIterationRun` 进入终态。
- 没有 READY / QUEUED / RUNNING / LONG_RUNNING 等未完成节点。

循环未结束时，工作流不会提前成功。

### 10. 失败与取消收口

当前规则：

- 循环体节点失败会关闭当前轮。
- 当前轮失败会关闭循环。
- 记录失败节点运行 ID。
- 工作流取消会关闭活跃循环和当前轮。
- 取消后不会继续创建下一轮。

### 11. 恢复幂等

已经接入循环恢复：

```text
recover_serial_loop_runtime_state
```

当前支持：

- 判断节点成功但尚未推进时，恢复后补推进。
- 已经推进过的判断结果不会重复创建下一轮。
- 终态循环不会被恢复成运行中。
- 失败轮次可以收口为循环失败。

### 12. 测试覆盖

已补充或覆盖的关键场景：

- enabled 循环初始化。
- preview 不初始化真实循环。
- 第 1 轮节点绑定。
- 两轮循环：第 1 轮 continue，第 2 轮 end。
- 达到 `max_iterations` 后放行出口。
- 控制信号 `actual_control=false` 无副作用。
- 控制信号重复解释幂等。
- 循环出口依赖放行。
- 工作流完成等待循环终态。
- 循环失败和取消收口。
- 恢复后不重复创建轮次。

## 性能方向判断

### 已控制住的性能点

#### 1. 不预创建全部未来轮次

当前只在需要时创建下一轮：

```text
第 N 轮判断 continue -> 创建第 N+1 轮
```

没有在循环开始时按 `max_iterations` 一次性创建大量轮次。

这个方向是正确的，能避免：

- 大量无效 `LoopIterationRun`。
- 中途失败或取消后留下大量未来记录。
- 恢复时扫描无意义的未来轮次。

#### 2. 不预创建未来轮次节点

当前只创建当前轮需要执行的节点。

已经避免：

```text
100 轮 * 循环体节点数
```

这种提前膨胀。

#### 3. 控制表读取很轻

控制解释只读取输出表首行。

对于判断节点输出控制状态表来说，这个读取成本较低，不会按整张表扫描。

#### 4. 恢复逻辑保持幂等

恢复时如果某个判断结果已经推进过，不会重复创建下一轮。

这对后台运行很重要，可以避免重启后重复膨胀记录。

#### 5. 事件没有额外放大

本轮没有引入大量逐行或逐节点详细事件。

后台快速运行时，事件量仍主要来自原有节点队列、开始、完成等基础事件。

### 当前性能风险

#### 1. ready 队列开始面对多条同名 NodeRun

为了支持循环多轮，ready 队列现在不再简单按：

```text
node_instance_id -> NodeRun
```

理解运行记录，而是会遍历当前 workflow_run 下的所有 `NodeRun`。

这对小中型工作流没有问题，但如果循环轮次很多，后续可能需要优化：

- 按状态查询 READY 节点。
- 批量预取 loop_iteration_node_runs。
- 批量预取最新成功 task result。
- 避免每个 candidate 触发多次 store 查询。

#### 2. 轮次内依赖判断仍有多次查询

当前轮次内推进会根据当前节点查 loop link、iteration、loop、region，再判断下游依赖。

第一版清晰可靠，但大量轮次下可以继续优化：

- 在单个调度周期内缓存 `dag.nodes` 映射。
- 缓存当前轮的 linked node runs。
- 对同一轮的上游结果做批量读取。

#### 3. 恢复仍需要按 loop_run 扫描

恢复逻辑会遍历当前 workflow_run 下的 loop runs。

当前第一版可接受，但如果一个工作流运行包含大量循环记录，后续应继续保证这些查询走索引：

```text
loop_runs(workflow_run_id)
loop_iteration_runs(loop_run_id, iteration_index)
loop_iteration_runs(loop_run_id, status)
loop_iteration_node_runs(node_run_id)
loop_iteration_node_runs(loop_iteration_id, node_instance_id)
```

#### 4. 出口输入取值仍需继续观察

循环出口节点的普通上游可能是循环判断节点。

现在 ready 队列已经支持多条同名 `NodeRun`，并会尽量选择可用的成功结果。

后续如果出口节点需要明确使用“最后一轮输出”或“汇总输出”，建议把这件事变成明确协议，而不是长期依赖普通上游查找。

## 耦合方向判断

### 已控制住的耦合点

#### 1. 主流程没有写死具体节点类型

当前主流程没有写成：

```text
if node_type == LoopJudgeNode
```

而是通过通用控制协议解释控制表。

这符合低耦合方向。

#### 2. 循环回跳没有塞进普通 connections

循环仍然通过：

```text
control_protocol.loop_regions
```

描述区域，不把回线伪造成普通 DAG 边。

普通 DAG 仍保持无环结构。

#### 3. TableRef 没有被塞入循环字段

没有把：

```text
loop_id
iteration_index
loop_iteration_id
```

直接塞进 `TableRef`。

循环归属仍由专门的运行态关联表管理。

#### 4. 没有一次性引入 execution_scope 大改

当前采用最小关联表：

```text
loop_iteration_node_runs
```

避免同时大改：

- NodeRun 模型。
- RuntimeStore 查询模型。
- API。
- UI。
- 主流程调度。

这个落点比较稳，适合第一版真实循环。

#### 5. 循环能力被拆在独立 helper 中

当前主要职责拆分为：

```text
loop_control.py                 状态推进
control_signal_interpreter.py   控制表解释
loop_runtime_initialization.py  真实循环初始化
loop_iteration_scheduling.py    轮次内节点推进
loop_recovery.py                恢复补偿
loop_terminal_state.py          失败取消收口
workflow_completion.py          完成判断
```

主流程只做少量编排调用，没有把所有循环逻辑堆进一个大函数。

### 当前耦合风险

#### 1. ready_queue 已经感知 loop_iteration_node_runs

为了让多轮同名节点正确派发，ready 队列现在需要理解轮次关联。

这是必要耦合，属于调度层对运行态的理解，不是节点类型耦合。

但后续要控制边界：

- ready_queue 可以知道“某个 NodeRun 属于某轮”。
- ready_queue 不应该知道具体 LoopJudgeNode 的业务配置。
- ready_queue 不应该解析控制表。

#### 2. NodeTaskManager 开始调用轮次推进 helper

节点成功后需要推进当前轮下游节点，因此 `NodeTaskManager` 调用了：

```text
advance_loop_iteration_after_node_success
```

这属于调度层耦合，当前可以接受。

后续如果控制结构继续增多，可以考虑抽一个更通用的：

```text
runtime scheduling coordinator
```

但现在不需要提前大改。

#### 3. get_node_run_for_instance 仍然存在歧义

循环真实执行后，同一个 `node_instance_id` 可以有多条 `NodeRun`。

因此后续新增调度代码时要注意：

- 根作用域普通节点可以继续用 `get_node_run_for_instance`。
- 循环轮次内节点应优先使用 `node_run_id` 或 `loop_iteration_node_runs`。
- 不要在循环上下文里只靠 `node_instance_id` 查运行记录。

这是后续最需要守住的边界之一。

## 当前边界

当前版本仍然是保守第一版：

- 只支持串行循环。
- 不支持嵌套循环。
- 不支持循环体内真实子工作流。
- 不支持并行轮次。
- 当前输入模式以 row selector 为核心。
- 还没有完整 `execution_scope` 抽象。
- 前端 UI 展示、交互和调试面板不在本轮范围内。

## 当前总体判断

从性能方向看，当前实现没有明显的大规模提前创建问题，核心路径保持了按需创建和幂等恢复。

从耦合方向看，当前实现没有把循环节点类型写死进主流程，也没有污染 `TableRef` 或普通 DAG connections。耦合主要集中在调度层对运行态关联表的理解，这属于真实循环第一版必须承担的耦合，当前范围可控。

后续最值得继续加固的是：

1. 大轮次下 ready 队列和轮次依赖判断的批量查询优化。
2. 循环出口输出语义明确化。
3. 循环上下文中避免继续使用单纯 `node_instance_id` 查询。
4. 如果控制结构继续增多，再评估是否抽象更统一的调度协调层。
