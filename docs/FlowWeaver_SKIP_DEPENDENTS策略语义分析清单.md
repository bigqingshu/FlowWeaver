# FlowWeaver SKIP_DEPENDENTS 策略语义分析清单

复核日期：2026-06-28

## 一、当前结论

`SKIP_DEPENDENTS` 已明确设为“保留但不可用”的策略，不进入运行时代码实现。

原因是当前 DAG 依赖模型里，节点依赖全部是硬依赖：下游节点必须拿到所有上游成功结果引用后才能进入可执行队列。基于这个前提，`SKIP_DEPENDENTS` 如果只理解为“跳过所有依赖失败节点的下游节点”，它和已落地的 `CONTINUE_INDEPENDENT` 会高度重合。

当前处理方式是：

```text
保留 SKIP_DEPENDENTS 枚举和文档占位
用户显式配置时拒绝保存或启动
等待未来明确它与 CONTINUE_INDEPENDENT 的产品差异
再决定是实现为独立策略、别名策略，还是显式拒绝配置
```

## 二、文档语义来源

`01_第一阶段执行方案.md` 中对两个策略的描述是：

```text
CONTINUE_INDEPENDENT：失败分支停止，无关分支继续
SKIP_DEPENDENTS：跳过所有依赖失败节点的下游节点
```

`00_第一阶段技术接口与验收规范.md` 的阶段验收强调：

```text
慢分支不阻塞无关分支
依赖分支正确等待
CONTINUE_INDEPENDENT生效
```

因此，当前优先实施依据更明确要求的是 `CONTINUE_INDEPENDENT`。`SKIP_DEPENDENTS` 虽在第一阶段策略列表中出现，但没有给出完整的 workflow 终态、事件、并发、partial failure 汇总规则。

## 三、当前代码事实

当前代码状态：

- `FailurePolicyMode` 已声明 `SKIP_DEPENDENTS`。
- `NodeRunStatus.SKIPPED` 已存在。
- `WorkflowRunCompletionReason.PARTIAL_FAILURE` 已存在。
- 运行时失败策略分支目前只对 `CONTINUE_INDEPENDENT` 做特殊处理。
- `SKIP_DEPENDENTS` 目前没有独立运行时语义。
- `SKIP_DEPENDENTS` 显式配置时应被视为不可用策略，而不是悄悄映射为其他策略。

当前 `CONTINUE_INDEPENDENT` 已落地的核心行为：

```text
失败节点：FAILED
直接或间接依赖失败节点的下游：SKIPPED
与失败分支无关的节点：继续执行
所有可执行节点结束后：WorkflowRun = FAILED
completion_reason = PARTIAL_FAILURE
```

这已经覆盖了“跳过依赖失败节点下游”的主要表面语义。

## 四、两者的关键区别

### CONTINUE_INDEPENDENT

关注点是 workflow 整体调度策略。

语义重点：

- 失败分支停止。
- 失败节点的依赖下游不能继续执行。
- 与失败分支无关的 READY 或后续可 READY 分支继续执行。
- workflow 不在第一个失败节点处立刻终止。
- 最终以 `FAILED + PARTIAL_FAILURE` 汇总。

一句话：

```text
能继续的独立分支继续，不能继续的依赖分支跳过。
```

### SKIP_DEPENDENTS

从名称和文档短句看，关注点更像下游节点处理策略。

语义重点可能是：

- 某节点失败后，所有依赖它的直接或间接下游被标记为 `SKIPPED`。
- 但它没有单独说明无关分支是否继续。
- 也没有单独说明 workflow 是否立即终止。
- 也没有单独说明最终 completion_reason 是否为 `PARTIAL_FAILURE`。

一句话：

```text
明确跳过依赖失败节点的下游，但尚未明确无关分支和 workflow 终态。
```

## 五、当前模型下的重合点

在当前硬依赖模型下，只要要求无关分支继续，`SKIP_DEPENDENTS` 就会自然变成：

```text
失败节点 FAILED
依赖失败节点的下游 SKIPPED
无关分支继续
最终 FAILED + PARTIAL_FAILURE
```

这与当前 `CONTINUE_INDEPENDENT` 的可观察行为几乎一致。

因此，如果现在直接实现 `SKIP_DEPENDENTS`，要么会变成 `CONTINUE_INDEPENDENT` 的别名，要么必须额外定义新的差异点。

## 六、需要决策的差异点

实现前建议先确认以下问题：

1. `SKIP_DEPENDENTS` 是否允许无关分支继续？

如果允许，它基本等价于当前 `CONTINUE_INDEPENDENT`。

如果不允许，它会变成：

```text
失败节点 FAILED
依赖失败节点的下游 SKIPPED
无关分支不再继续调度
workflow 较早 FAILED
```

这会和 `FAIL_FAST` 接近，但多了下游 `SKIPPED` 标记。

2. `SKIP_DEPENDENTS` 跳过范围是直接下游还是传递闭包？

文档写的是“所有依赖失败节点的下游节点”，更接近传递闭包。

建议默认理解为：

```text
直接和间接下游都 SKIPPED
```

3. 已经在运行中的下游或相关节点如何处理？

当前 `CONTINUE_INDEPENDENT` 只跳过尚未运行的阻断下游，不强杀已运行节点。

`SKIP_DEPENDENTS` 如需更强语义，需要额外定义：

```text
RUNNING / LONG_RUNNING / CANCEL_REQUESTED 是否取消
是否发取消请求
是否等待宽限期
是否清理 STAGING
```

这会扩大到取消协议和执行器生命周期，不建议在小步内混入。

4. workflow 最终 completion_reason 是什么？

如果 `SKIP_DEPENDENTS` 允许无关分支继续，建议沿用：

```text
completion_reason = PARTIAL_FAILURE
```

如果它表示“失败后跳过依赖并尽快结束”，可能需要另一个原因，例如：

```text
UPSTREAM_FAILED
DEPENDENTS_SKIPPED
```

但当前没有必要新增原因。

5. 未来 optional edge / optional input 出现后如何区分？

如果未来支持可选输入或可容忍缺失上游结果，两个策略可以自然分化：

- `CONTINUE_INDEPENDENT`：尽可能继续，允许满足可选输入规则的下游继续。
- `SKIP_DEPENDENTS`：只要依赖链上出现失败，就跳过依赖失败节点的下游。

但当前没有 optional edge，因此暂时无法体现这个差异。

## 七、建议的策略定位

当前建议把三种策略定位为：

| 策略 | 当前定位 | 行为摘要 |
| --- | --- | --- |
| `FAIL_FAST` | 已实现默认策略 | 任一节点失败后 workflow 立即失败 |
| `CONTINUE_INDEPENDENT` | 已实现部分失败策略 | 失败分支 SKIPPED，无关分支继续，最终 PARTIAL_FAILURE |
| `SKIP_DEPENDENTS` | 保留但不可用，待语义确认 | 显式配置时拒绝，不映射为 CONTINUE_INDEPENDENT |

## 八、可选实现路线

### 路线 A：显式预留，非法配置即拒绝

语义：

```text
SKIP_DEPENDENTS 当前不启用
用户显式配置时启动即拒绝
```

优点：

- 避免用户误以为它已有独立语义。
- 不制造两个名字同一行为的维护负担。
- 后续可在语义明确后再开启。

代价：

- 与枚举已声明但运行时不可用之间需要补清晰错误。

### 路线 B：作为 CONTINUE_INDEPENDENT 的别名

语义：

```text
SKIP_DEPENDENTS 与 CONTINUE_INDEPENDENT 当前行为一致
```

优点：

- 实现小。
- 能满足“跳过依赖失败下游”的表面要求。

代价：

- 两个策略名称表达不同，但行为相同，后续容易形成兼容包袱。
- 未来想把两者分开时可能破坏已有用户预期。

### 路线 C：定义成 FAIL_FAST + 下游 SKIPPED

语义：

```text
失败节点 FAILED
依赖失败节点的下游 SKIPPED
无关分支不继续调度
workflow 尽快 FAILED
```

优点：

- 与 `CONTINUE_INDEPENDENT` 有明显差异。
- 比 `FAIL_FAST` 多保留依赖阻断信息。

代价：

- 文档没有明确说无关分支应停止。
- 并发场景下已运行的无关节点如何处理会牵涉取消和迟到结果边界。

## 九、最稳建议

本小步采用以下决策：

```text
SKIP_DEPENDENTS 设为保留但不可用策略
当前不作为 CONTINUE_INDEPENDENT 的别名
当前不改变 FAIL_FAST 和 CONTINUE_INDEPENDENT 行为
显式配置时拒绝并给出清晰错误
```

理由：

- 当前验收主线已经要求 `CONTINUE_INDEPENDENT` 生效。
- 当前实现已经覆盖失败分支跳过和无关分支继续。
- `SKIP_DEPENDENTS` 缺少独立终态、事件和并发语义。
- 过早别名会增加未来兼容压力。

## 十、后续最小验收清单

若下一步进入 `SKIP_DEPENDENTS` 收口，建议只做一个很小的前置验收：

```text
当 workflow definition 显式配置 failure_policy.mode = SKIP_DEPENDENTS
启动 workflow process 时返回失败
WorkflowRun = FAILED
错误信息明确：SKIP_DEPENDENTS is reserved / unsupported
默认未配置时仍自动使用 FAIL_FAST
CONTINUE_INDEPENDENT 既有测试不受影响
```

暂不做：

- 不把 `SKIP_DEPENDENTS` 映射成 `CONTINUE_INDEPENDENT`。
- 不新增 workflow completion reason。
- 不新增取消协议。
- 不改变 READY 队列。
- 不改变并发执行池生命周期。
