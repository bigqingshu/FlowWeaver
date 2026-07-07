# FlowWeaver 控制流节点最小语义分析

更新时间：2026-07-07

## 结论

当前可以进入控制流节点的前置收口，但不应直接实现跳转、循环或子工作流调度。

最小可落地顺序建议为：

1. 先实现 `ConditionFlagNode` 为普通后端节点，只输出条件结果状态表。
2. 再定义通用控制信号/条件结果协议。
3. 再评估 `ConditionalJumpNode`、`UnconditionalJumpNode`、`JumpAnchorNode` 是否接入调度层。
4. 最后单独处理 `LoopStartNode`、`LoopJudgeNode` 和 `SubWorkflowNode`。

## 当前主程序状态

当前工作流执行模型仍是 DAG：

| 模块 | 当前能力 | 对控制流的影响 |
|---|---|---|
| `WorkflowDefinitionModel` | 节点列表 + 连接列表 | 没有条件边、跳转边、循环边字段 |
| `WorkflowDag` | 拓扑排序，检测环 | 不允许回跳或循环 |
| `ready_queue` | 上游全部成功后下游 ready | 不支持按条件选择下游 |
| `controller` | 节点成功后恢复依赖满足的节点 | 不解释节点输出里的控制信号 |
| `NodeTaskModel` | 承载业务 config 和输入表引用 | 没有控制流输出协议 |

因此，当前如果直接实现跳转节点，需要让调度层对特定节点做 program counter 特判，会增加主程序和节点耦合。

## 节点分层

| 节点 | 最小阶段 | 原因 |
|---|---|---|
| `ConditionFlagNode` | 可先实现为普通结果节点 | 只读取输入表并输出状态表，不改变执行路径 |
| `ConditionalJumpNode` | 后置 | 需要条件结果协议和条件边 / 动态调度 |
| `UnconditionalJumpNode` | 后置 | 需要跳转目标解析和执行路径改写 |
| `JumpAnchorNode` | 后置 | 当前 DAG 没有锚点语义，单独实现价值有限 |
| `LoopStartNode` | 后置 | 需要循环状态、最大次数和动态调度 |
| `LoopJudgeNode` | 后置 | 依赖循环状态和回跳语义 |
| `SubWorkflowNode` | 后置 | 需要父子 run、子流程输入输出映射和取消传播 |

## `ConditionFlagNode` 第一版边界

第一版目标不是驱动调度，而是把条件判断结果变成普通表数据：

```text
输入：一个 TableRef
输出：一个 status TableRef
不透传业务表，或后续如需要再增加透传端口
不改变下游 ready 逻辑
不写 RuntimeStore 私有状态
不引入条件边
```

建议输出字段：

| 字段 | 含义 |
|---|---|
| `flag_name` | 条件标志名 |
| `condition_type` | 条件类型 |
| `aggregation` | 聚合方式，例如 any / all / first / count |
| `result` | true / false |
| `true_value` | 成立输出值 |
| `false_value` | 不成立输出值 |
| `output_value` | 最终输出值 |
| `matched_count` | 命中行数 |
| `total_rows` | 总行数 |
| `details` | 简短说明 |

## 第一版配置建议

| 字段 | 建议 |
|---|---|
| `flag_name` | 必填，默认 `condition` |
| `condition_type` | `row_count`、`field_exists`、`field_value` |
| `field` | 字段条件需要 |
| `operator` | `EQ`、`NE`、`GT`、`GE`、`LT`、`LE`、`CONTAINS`、`IS_NULL`、`IS_EMPTY` |
| `value` | 固定比较值 |
| `value_source` | 第一版支持 `literal`、`field` |
| `value_field` | `value_source=field` 时使用 |
| `aggregation` | 第一版支持 `any`、`all`、`first`、`count` |
| `case_sensitive` | 文本比较使用 |
| `true_value` / `false_value` | 默认 `true` / `false` |

## 不进入第一版

- 不修改 `WorkflowDag`。
- 不新增条件边、跳转边或动态 ready 规则。
- 不实现锚点解析。
- 不实现循环回跳。
- 不实现父子 workflow run。
- 不让 `WorkflowRunProcess` 对某个节点类型写专用分支。

## 验收方式

第一版 `ConditionFlagNode` 验收只看普通节点行为：

1. 节点定义 API 能返回配置 schema 和端口。
2. 行数条件可输出 true / false。
3. 字段存在条件可输出 true / false。
4. 字段值条件支持固定值和同一行字段值来源。
5. 聚合方式 `any`、`all`、`first`、`count` 有测试覆盖。
6. 字段缺失、配置缺失和非法操作符返回验证错误。
7. 下游仍按普通 DAG 依赖执行，不因条件结果改变路径。

## 后续进入调度层的前置

在实现真实跳转前，需要先补统一协议：

```text
ControlSignal / ConditionResult
条件边或动态调度规则
跳转目标校验
被跳过节点的运行记录表达
路径预览
跳过高风险节点时的解释记录
```

这些能力应作为工作流调度能力建设，不放进单个节点 handler。
