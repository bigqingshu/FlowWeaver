# FlowWeaver 阶段H后置并行默认启用前置条件清单

复核日期：2026-06-28

本清单依据：

1. `00_第一阶段技术接口与验收规范.md`
2. `01_第一阶段执行方案.md`

后续讨论文档仅作为背景，不纳入当前启用门槛。

## 一、当前结论

阶段H已经完成 READY 队列、调度窗口、执行中容量边界、执行池抽象、线程执行池最小实现，以及线程池注入主循环的最小验收。

但当前不建议直接把 `ThreadedNodeTaskExecutionPool` 切为默认路径。

原因是默认主流程仍依赖 `_execute_node_task_with_supervision` 的同步监督语义。该函数内部已经为单个节点执行再启动一层 worker 线程，用于心跳、超时、取消和强制关闭判断。若直接把外层执行池默认切到线程池，会形成：

- 主循环线程
- 执行池任务线程
- 单任务监督内部 worker 线程

这会改变取消、超时、异常传播、进程退出和 executor 关闭的责任边界。因此需要先完成以下前置收口。

## 二、已具备的基础

| 项目 | 状态 | 当前证据 |
| --- | --- | --- |
| READY 候选队列 | 已具备 | `src/flowweaver/workflow_process/ready_queue.py` |
| READY 依赖输入 `input_refs` | 已具备 | `collect_ready_node_candidates` |
| 执行中容量统计 | 已具备 | `count_in_flight_node_runs` |
| 每轮先排空完成结果再分发 READY | 已具备 | `_run_workflow_process_loop` |
| READY 分发窗口 | 已具备 | `max_ready_dispatch_per_cycle` |
| 并发容量参数 | 已具备 | `max_concurrent_node_tasks` |
| 执行池协议 | 已具备 | `NodeTaskExecutionPool` |
| 同步兼容池 | 已具备 | `ImmediateNodeTaskExecutionPool` |
| 手动完成测试池 | 已具备 | `ManualNodeTaskExecutionPool` |
| 线程执行池最小实现 | 已具备 | `ThreadedNodeTaskExecutionPool` |
| 线程池注入主循环不阻塞验收 | 已具备 | `test_workflow_process_with_threaded_pool_does_not_block_after_dispatch` |

## 三、默认并行启用前必须收口的条件

### 1. 执行池生命周期边界

当前 `ThreadedNodeTaskExecutionPool` 只实现了 `submit`、`pop_completed`、`in_flight_count`。

启用默认并行前，需要补齐：

- 执行池关闭接口。
- 主循环退出前对 in-flight 任务的处理策略。
- 关闭时是否等待任务完成、等待多久、是否调用 executor.close。
- 关闭后是否拒绝新提交。
- 后台线程异常时是否仍能清理 in-flight。

建议先扩展协议为可选 close 边界，而不是立刻要求所有测试池实现复杂生命周期。

### 2. 取消请求广播边界

当前取消逻辑由 `_execute_node_task_with_supervision` 在监督循环内检测 workflow process cancel，并调用 `_request_cancel`。

默认并行后，主循环不再阻塞在单个 `_execute_node_task_with_supervision` 内，取消请求会先被主循环检测到。

启用前需要明确：

- 主循环发现 workflow process cancel 时，是否立即把取消请求广播给所有 in-flight task。
- 执行池是否需要提供 `request_cancel_all` 或按 task_id 取消接口。
- 已经处于 `CANCEL_REQUESTED` 的节点是否仍允许任务结果回收。
- 取消后是否继续 drain completion，还是立即返回。
- cancel grace period 归属于主循环、执行池，还是单任务监督函数。

建议先做最小接口：执行池暴露当前 in-flight task 快照，主循环可对其 executor 调用 `_request_cancel`。

### 3. 异常结果边界

当前同步监督路径中，executor 抛出的异常会从 `_execute_node_task_with_supervision` 继续抛出，外层主程序 `main()` 捕获后返回 1。

线程池默认启用后，后台线程中抛出的异常不能自然抛回主循环。

启用前需要明确：

- 线程池是否把异常包装为 `ExecutorTaskCompletion`。
- 异常 completion 是否转换成 `FAILED` 的 `NodeTaskResultModel`。
- 转换失败结果时 error 字段格式是否沿用 IPC executor failure result。
- 异常是否应该失败当前 node 和 workflow，还是作为 process-level fatal error。
- 后台异常是否必须写入 runtime event。

建议先实现“线程池捕获异常并返回失败 completion”的最小路径，再做默认启用。

### 4. 超时与迟到结果边界

当前超时由 `_execute_node_task_with_supervision` 内部轮询 `NodeTaskManager.mark_timed_out_task` 完成。超时后会关闭 executor、清理 staging，并尝试处理一个 late result。

默认并行后需要确认：

- 多个 in-flight task 的超时是否都由各自监督函数处理。
- 主循环退出到 workflow terminal 后，其他 in-flight task 的迟到结果是否还会被 drain。
- 迟到 completion 对终态节点是否保持 `REJECTED_NODE_TERMINAL` 并不污染 workflow。
- staging cleanup 是否只执行一次。

建议先补一个“并行线程池注入 + 一个任务超时 + 另一个任务仍 in-flight”的测试，再决定默认启用。

### 5. 多任务完成顺序边界

当前已有完成结果 drain，但默认并行前仍缺少多任务真实并发完成顺序验收。

启用前需要补：

- 两个 READY source 同时提交到线程池。
- 第二个先完成、第一個后完成时，结果均能正确 apply。
- 下游 merge 只在两个上游都 `SUCCEEDED` 后进入 READY。
- `max_concurrent_node_tasks=1` 时不会并发提交第二个任务。
- `max_ready_dispatch_per_cycle` 与 `max_concurrent_node_tasks` 同时存在时取更小值。

建议这是下一小步的最稳测试范围。

### 6. 数据库并发写入边界

`RuntimeStore` 当前每次操作创建独立 SQLAlchemy session，并对 SQLite 设置 busy_timeout，文件库启用 WAL。

默认并行后，多个任务线程可能同时：

- 记录 heartbeat/progress。
- apply result。
- 更新 node_run/workflow_run 状态。
- 记录 runtime event。

启用前需要补：

- 两个并发任务同时完成时，节点状态与 runtime event 顺序可接受。
- 一个任务失败导致 workflow terminal 后，另一个任务成功 completion 不会重新推进 workflow。
- executor event handler 在后台线程调用 store 时不共享 session。

建议先以 SQLite 文件库集成测试覆盖，不引入新数据库抽象。

### 7. 默认开关与回退策略

即使前置条件满足，也不建议一次性无条件切默认。

建议默认启用采用两步：

1. 新增显式参数或配置开关，例如 `execution_mode="immediate" | "threaded"`，默认仍为 immediate。
2. 完成验收后，再评估是否把默认值改为 threaded。

这样可以保留同步路径作为回退，也便于定位并行问题。

### 8. 最小配置决策清单

下一步只建议引入显式、保守的运行模式配置，不直接改变现有默认行为。

配置字段：

```text
execution_mode = "immediate" | "threaded"
max_concurrent_node_tasks = 1 | 2
```

决策：

- 当配置字段缺省时，自动使用安全默认值：`execution_mode="immediate"` 且 `max_concurrent_node_tasks=1`。
- 默认 `execution_mode` 固定为 `"immediate"`。
- 可选 `execution_mode` 为 `"threaded"`，必须显式配置后才启用。
- 默认并发数固定为 `1`。
- 当前阶段只允许把并发数配置为 `2`，不开放更大的并发值。
- `execution_mode="immediate"` 时，即使配置并发数为 `2`，运行效果仍应保持单任务同步执行。
- `execution_mode="threaded"` 且 `max_concurrent_node_tasks=2` 时，才允许最多两个 READY 节点并发执行。
- 用户显式填写非法 `execution_mode` 或非法并发数时，启动即拒绝，不自动回退。

进入实现前置条件：

- 配置来源明确，优先使用已有 `EngineConfig` 或 workflow process 入参，不新增独立配置系统。
- API、CLI、测试 helper 对默认值的行为保持兼容。
- threaded 模式必须继续通过 H+1 到 H+6 已覆盖的异常、取消、失败隔离、终态 close 验收。
- 本轮不把 threaded 设为默认，不扩大到多进程池或节点隔离方案。

## 四、建议执行顺序

### H+1：线程池异常 completion 最小边界

范围：

- `ThreadedNodeTaskExecutionPool` 捕获后台异常。
- completion 携带异常信息或转换为失败结果的最小结构。
- 单元测试覆盖 in-flight 清理和 pop completion。

不做：

- 默认启用线程池。
- 主循环失败策略重写。

### H+2：执行池生命周期 close 边界

范围：

- 为线程池增加 close / closed 行为。
- close 后拒绝 submit。
- close 可等待已有线程在短时间内退出。
- 单元测试覆盖 close 后提交拒绝和 in-flight 清理。

不做：

- 强杀线程。
- 进程池管理。

### H+3：主循环取消时 in-flight 快照与取消请求

范围：

- 线程池暴露 in-flight dispatched task 快照。
- 主循环收到取消请求时，对 in-flight executor 发出取消请求。
- 测试覆盖注入线程池下的协作取消。

不做：

- 默认线程池启用。
- 多进程取消广播。

### H+4：多 READY 并发完成顺序验收

范围：

- 两个 source 同时 READY。
- 注入线程池。
- 两个任务按反序完成。
- 验证 merge 只在两个上游完成后执行。

不做：

- 更换调度算法。
- 工作窃取或优先级队列。

### H+5：并行失败隔离验收

范围：

- 一个任务失败，另一个任务迟到成功。
- workflow 保持 FAILED。
- 迟到成功不推进下游，不污染终态。

不做：

- 复杂重试。
- 节点故障隔离扩展方案。

### H+6：显式 threaded 模式开关

范围：

- 新增显式 execution mode。
- 默认仍保持 immediate。
- 测试 threaded 模式可通过参数启用。

不做：

- 将 threaded 设为默认。

## 五、本阶段不建议做的事

- 不要直接把 `run_workflow_process(..., execution_pool=None)` 时的默认池改成 `ThreadedNodeTaskExecutionPool`。
- 不要引入新的节点进程池架构。
- 不要改写 `RuntimeStore` 事务模型。
- 不要把讨论文档中的共享表、节点隔离备选方案并入 H 后置收口。
- 不要扩大到 UI、API 或 supervisor 策略。

## 六、验收门槛

完成以上前置条件后，才可评估默认 threaded 启用。

最低验收应包括：

```text
.\python312\python.exe -m ruff check src tests migrations
.\python312\python.exe -m mypy
.\python312\python.exe -m pytest tests\unit\test_executor_pool.py tests\integration\test_workflow_process_main.py -q
.\python312\python.exe -m pytest -q
```

允许保留既有 `StarletteDeprecationWarning`，但不允许新增并行相关不稳定测试。

## 七、结论

阶段H后置的主线方向应是：先把线程执行池从“能跑”补到“可关闭、可取消、可表达异常、可验证多任务完成顺序”，再通过显式 threaded 模式启用。

在这些前置条件完成之前，默认路径继续保持 `ImmediateNodeTaskExecutionPool` 是当前最稳选择。
