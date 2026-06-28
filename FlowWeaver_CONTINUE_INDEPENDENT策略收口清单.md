# FlowWeaver CONTINUE_INDEPENDENT 策略收口清单

复核日期：2026-06-28

## 一、当前结论

`CONTINUE_INDEPENDENT` 需要单独收口，不应混入阶段 H 的执行模式、线程池或默认并发配置小步。

当前代码已经在 `WorkflowDefinitionModel.failure_policy` 中声明了三种模式：

```text
FAIL_FAST
CONTINUE_INDEPENDENT
SKIP_DEPENDENTS
```

但执行层实际只具备 `FAIL_FAST` 语义：任一节点任务返回失败结果时，`NodeTaskManager._apply_terminal_failure()` 会将当前节点标记为 `FAILED`，并将 WorkflowRun 标记为 `FAILED`，主循环随后因 workflow 终态退出。

因此，`CONTINUE_INDEPENDENT` 目前只是协议字段，还不是可执行策略。

## 二、必须先明确的语义

### 1. Workflow 终态

`CONTINUE_INDEPENDENT` 下，单个节点失败后不应立即让 WorkflowRun 进入终态 `FAILED`。

已确认最终状态表达：

- 运行期间，单个节点失败不会立即结束 WorkflowRun。
- 所有可执行节点结束后，WorkflowRun 最终状态为 `FAILED`。
- 最终完成原因为 `completion_reason=PARTIAL_FAILURE`。

确认策略：

```text
运行期间：WorkflowRun 保持 RUNNING
所有可运行分支结束后：WorkflowRun 最终 FAILED
完成原因：completion_reason = PARTIAL_FAILURE
```

### 2. 失败节点的下游

失败节点的直接或间接依赖节点不能继续执行，因为缺少成功输出。

已确认节点状态表达：

- 失败节点：`FAILED`。
- 直接或间接依赖失败节点，且无法继续执行的节点：`SKIPPED`。
- 与失败分支无关的节点：继续执行。

当前 `NodeRunStatus` 还没有 `SKIPPED`。因此实现前需要先扩展节点状态、状态迁移和事件/响应序列化边界。

确认策略：

```text
失败节点：FAILED
受失败分支阻断的下游节点：SKIPPED
无关分支：继续执行
```

### 3. 独立分支继续执行

无依赖失败节点的 READY 分支应继续调度。

这要求失败结果应用时：

- 不能立即更新 WorkflowRun 为终态；
- 主循环不能因为单个失败节点退出；
- READY 队列仍能继续收集独立 READY 节点；
- 并发 threaded 模式下，失败 completion 不应关闭执行池或拒绝其他 in-flight completion。

这与当前 H+5 的“并行失败隔离，workflow 立即 FAILED，迟到成功不污染终态”语义不同，需要单独测试。

### 4. 事件语义

最小事件顺序需要明确：

- 节点失败时仍发 `NODE_FAILED`；
- Workflow 最终失败时再发 `WORKFLOW_FAILED`；
- 不应在第一个节点失败时提前发 `WORKFLOW_FAILED`；
- `SKIPPED` 节点应增加对应事件，或至少在 workflow failure summary 中表达。
- `WORKFLOW_FAILED` payload 应携带 `completion_reason="PARTIAL_FAILURE"`。

## 三、当前代码冲突点

| 位置 | 当前行为 | 与 CONTINUE_INDEPENDENT 的冲突 |
| --- | --- | --- |
| `NodeTaskManager._apply_terminal_failure()` | 节点失败后立刻更新 WorkflowRun 为 `FAILED` | 应允许 WorkflowRun 继续 `RUNNING` |
| `_run_workflow_process_loop()` | workflow 终态后立即 return | 若失败不立即终态，主循环才能继续调度独立分支 |
| `_drain_executor_task_completions()` | completion 后发现终态即停止 drain | CONTINUE_INDEPENDENT 下不能因单个失败停止 |
| H+5 失败隔离验收 | 失败后迟到成功不污染终态 | CONTINUE_INDEPENDENT 需要允许其他独立成功继续落地 |
| `NodeRunStatus` | 没有 `SKIPPED` 状态 | 无法清晰表达失败节点下游不可运行 |
| WorkflowRun 记录 | 当前没有 `completion_reason` 字段 | 无法表达 `PARTIAL_FAILURE` 完成原因 |

## 四、建议最小实现顺序

### CI-1：只读策略识别

范围：

- 在 `NodeTaskManager` 或主循环上下文中可读取 workflow `failure_policy.mode`。
- 保持所有行为不变。
- 测试确认默认仍为 `FAIL_FAST`。

不做：

- 不改变失败结果应用行为。
- 不新增状态。

### CI-2：状态与完成原因前置结构

范围：

- 新增 `NodeRunStatus.SKIPPED`。
- 为 WorkflowRun 增加 `completion_reason` 或等价可序列化字段。
- 定义 `PARTIAL_FAILURE` 常量。
- 补序列化/API response/状态迁移测试。

不做：

- 不改变默认 `FAIL_FAST` 行为。
- 不开始调度独立分支。

### CI-3：CONTINUE_INDEPENDENT 失败不终止 workflow

范围：

- 节点失败后仅标记该节点 `FAILED` 并发 `NODE_FAILED`。
- WorkflowRun 保持 `RUNNING`。
- 直接或间接依赖失败节点的不可执行下游标记为 `SKIPPED`。
- 独立 READY 分支继续执行。

不做：

- 不实现 `SKIP_DEPENDENTS` 的完整独立策略。

### CI-4：完成判定与最终失败

范围：

- 当没有可继续运行的 READY/RUNNING/LONG_RUNNING 节点时，若存在 failed node，则 WorkflowRun 最终 `FAILED`。
- 此时再发 `WORKFLOW_FAILED`。
- WorkflowRun 写入 `completion_reason=PARTIAL_FAILURE`。
- `WORKFLOW_FAILED` 事件 payload 携带 `completion_reason="PARTIAL_FAILURE"`。

不做：

- 不新增 `PARTIAL_FAILED` workflow 状态。

### CI-5：下游阻断验收

范围：

- 失败节点的依赖下游进入 `SKIPPED`。
- workflow failure summary 记录 failed/skipped/blocked 节点。

不做：

- 不实现 `SKIP_DEPENDENTS` 的完整策略，除非明确进入该策略阶段。

## 五、最小验收场景

### 场景 1：默认 FAIL_FAST 不变

```text
source_a failed
source_b independent ready
expected:
  workflow FAILED immediately
  source_b not继续执行
```

### 场景 2：CONTINUE_INDEPENDENT 独立分支继续

```text
source_a failed
source_b independent ready
merge depends on source_a + source_b
expected:
  source_a FAILED
  source_b SUCCEEDED
  merge SKIPPED
  workflow 最终 FAILED
  completion_reason PARTIAL_FAILURE
  WORKFLOW_FAILED 在 source_b 完成和 merge SKIPPED 后出现
```

### 场景 3：threaded/2 下失败不关闭独立分支

```text
source_a failed first
source_b late success
expected:
  source_b success 可落地
  workflow 最终 FAILED
  completion_reason PARTIAL_FAILURE
  不触发 H+5 的终态拒绝路径
```

## 六、本阶段不建议做的事

- 不在阶段 H 执行模式配置小步中实现 `CONTINUE_INDEPENDENT`。
- 不直接新增复杂 workflow 终态枚举。
- 不混入 `SKIP_DEPENDENTS`。
- 不改变默认 `FAIL_FAST`。
- 不改变 H+5/H+6 的既有 fail-fast 验收语义。

## 七、建议结论

`CONTINUE_INDEPENDENT` 应作为独立后续小阶段处理。

已确认产品语义：

1. 失败节点为 `FAILED`。
2. 直接或间接依赖失败节点且无法继续执行的节点为 `SKIPPED`。
3. 与失败分支无关的节点继续执行。
4. 所有可执行节点结束后，WorkflowRun 为 `FAILED`。
5. WorkflowRun 完成原因为 `completion_reason=PARTIAL_FAILURE`。
