# FlowWeaver 控制信号协议与预览控制节点实施计划

更新时间：2026-07-07

## 文档定位

本文件用于规划下一批复杂控制类节点的后端最小实现入口。

当前目标不是实现真实跳转、循环或子工作流调度，而是先建立统一的控制状态表协议，并让控制类节点以普通后端节点形式输出可验证、可读取、可后续解释的控制计划。

## 当前主程序边界

当前工作流执行仍是严格 DAG：

| 模块 | 当前状态 | 对控制节点的影响 |
|---|---|---|
| `WorkflowDefinitionModel` | 节点列表 + 连接列表 | 还没有条件边、跳转边、锚点边或循环边字段 |
| `WorkflowDag` | 拓扑排序并拒绝环 | 不支持回跳、循环或动态执行路径 |
| `ready_queue` | 上游全部成功后下游进入 ready | 不支持按条件选择下游 |
| `controller` | 节点成功后恢复依赖满足的节点 | 不解释节点输出里的控制信号 |
| `NodeTaskModel` | 承载节点业务配置和输入表引用 | 当前没有调度级控制输出字段 |

因此，复杂控制节点第一阶段应保持普通节点行为：读取输入表或配置，输出标准状态表，不改变下游 ready 逻辑。

## 已完成前置

`ConditionFlagNode` 第一版已实现：

```text
输入：一个 TableRef
输出：条件状态 TableRef
能力：row_count / field_exists / field_value
聚合：any / all / first / count
边界：不改变 DAG，不驱动跳转，不写调度私有状态
```

这为后续 `ConditionalJumpNode` 提供了可读取的条件结果来源。

## 第一阶段目标

第一阶段只做后端低耦合能力：

1. 定义统一控制状态表字段。
2. 让预览型控制节点输出控制计划。
3. 保持节点注册、config schema、handler、测试覆盖完整。
4. 不改 `WorkflowDag`、`ready_queue`、`controller` 的调度语义。
5. 不让主程序为某个控制节点写专用分支。

## 不进入第一阶段

- 不真实跳转。
- 不真实回跳。
- 不跳过未选中分支节点。
- 不改 workflow 完成判断。
- 不新增循环执行语义。
- 不创建父子 workflow run。
- 不改前端 UI 结构。

## 统一控制状态表协议

建议所有预览型控制节点输出同一类状态表，字段保持稳定。

| 字段 | 类型 | 含义 |
|---|---|---|
| `signal_type` | TEXT | 控制信号类型，例如 `anchor`、`jump`、`conditional_jump`、`loop_plan` |
| `signal_status` | TEXT | `planned`、`matched`、`not_matched`、`invalid`、`skipped` |
| `source_node_id` | TEXT | 当前节点实例 ID |
| `target_node_id` | TEXT | 目标节点实例 ID，没有则为空 |
| `target_anchor` | TEXT | 目标锚点名，没有则为空 |
| `condition_result` | TEXT | 条件结果，`true` / `false` / 空 |
| `selected_branch` | TEXT | 选择的分支名，例如 `true`、`false`、`default` |
| `action` | TEXT | 计划动作，例如 `declare_anchor`、`jump_to_anchor`、`jump_to_node` |
| `actual_control` | TEXT | 第一阶段固定为 `false` |
| `reason` | TEXT | 选择、跳过或失败原因 |
| `details` | TEXT | JSON 摘要，用于保存配置快照和解析结果 |

第一阶段所有控制计划表都应使用 `TableRole.CURRENT`，这样后续节点可以按普通输入读取。

## 节点一：JumpAnchorNode

### 定位

锚点声明节点，用于在工作流中声明可被跳转计划引用的位置。

### 第一版行为

```text
输入：无输入或可选输入
输出：控制状态表
不改变执行路径
不解析全图
不校验是否被引用
```

### 配置草案

| 字段 | 含义 |
|---|---|
| `anchor_name` | 锚点名，必填 |
| `description` | 可选说明 |
| `allow_multiple_hits` | 后续真实调度使用；第一版仅记录 |

### 输出示例

```text
signal_type=anchor
signal_status=planned
target_anchor=<anchor_name>
action=declare_anchor
actual_control=false
```

### 价值

先让锚点成为可注册、可测试、可被后续计划节点引用的普通节点。

## 节点二：UnconditionalJumpNode

### 定位

无条件跳转计划节点。

### 第一版行为

```text
输入：可选输入
输出：控制状态表
不执行真实跳转
不修改 ready 队列
```

### 配置草案

| 字段 | 含义 |
|---|---|
| `target_mode` | `anchor` 或 `node` |
| `target_anchor` | 目标锚点名 |
| `target_node_id` | 目标节点实例 ID |
| `reason` | 可选原因 |

### 校验规则

| 情况 | 第一版处理 |
|---|---|
| `target_mode=anchor` 且 `target_anchor` 为空 | 验证错误 |
| `target_mode=node` 且 `target_node_id` 为空 | 验证错误 |
| 目标是否真实存在 | 第一版可只记录，不做全图解析 |

### 输出示例

```text
signal_type=jump
signal_status=planned
target_anchor=<target_anchor>
target_node_id=<target_node_id>
action=jump_to_anchor / jump_to_node
actual_control=false
```

## 节点三：ConditionalJumpNode

### 定位

读取条件结果表，输出条件跳转计划。

### 第一版行为

```text
输入：一个 ConditionFlagNode 输出的状态 TableRef
输出：控制状态表
不执行真实跳转
不修改 ready 队列
```

### 配置草案

| 字段 | 含义 |
|---|---|
| `condition_field` | 条件结果字段，默认 `result` |
| `true_target_mode` | `anchor` 或 `node` |
| `true_target_anchor` | true 分支目标锚点 |
| `true_target_node_id` | true 分支目标节点 |
| `false_target_mode` | `anchor` 或 `node` |
| `false_target_anchor` | false 分支目标锚点 |
| `false_target_node_id` | false 分支目标节点 |
| `default_branch` | 条件结果缺失时使用的分支，默认 `false` |

### 校验规则

| 情况 | 第一版处理 |
|---|---|
| 输入不是单表 | 验证错误 |
| 缺少 `condition_field` | 验证错误 |
| 条件值不是 true/false | 使用 `default_branch` 或输出 invalid |
| 被选分支目标为空 | 验证错误 |

### 输出示例

```text
signal_type=conditional_jump
signal_status=matched / not_matched
condition_result=true / false
selected_branch=true / false
target_anchor=<selected_target_anchor>
target_node_id=<selected_target_node_id>
actual_control=false
```

## 第一阶段后端实现顺序

| 顺序 | 交付内容 | 说明 |
|---:|---|---|
| 1 | 增加控制状态表 helper | 已完成：在 `builtin_table.py` 内复用 `_simple_schema` 和 `publish_rows` |
| 2 | 注册 `JumpAnchorNode` | 已完成：最小无输入状态表节点，输出 `anchor` 预览控制状态 |
| 3 | 注册 `UnconditionalJumpNode` | 已完成：输出跳转计划，不解析全图，不改变 DAG |
| 4 | 注册 `ConditionalJumpNode` | 已完成：读取 `ConditionFlagNode` 状态表并输出分支计划 |
| 5 | 补 API schema 测试 | 已完成：确认节点定义、端口、配置 schema 暴露 |
| 6 | 补执行测试 | 已完成：覆盖成功输出、默认分支和配置错误 |
| 7 | 更新节点状态文档 | 已完成：标记为预览控制节点，说明不改变 DAG |

## 测试计划

### JumpAnchorNode

- 能输出 `anchor` 控制状态表。
- `anchor_name` 为空返回验证错误。
- 输出字段符合统一控制状态表协议。

### UnconditionalJumpNode

- `target_mode=anchor` 能输出跳转计划。
- `target_mode=node` 能输出跳转计划。
- 目标字段缺失返回验证错误。
- `actual_control` 固定为 `false`。

### ConditionalJumpNode

- 读取 `ConditionFlagNode result=true` 时选择 true 分支。
- 读取 `ConditionFlagNode result=false` 时选择 false 分支。
- 缺少条件字段返回验证错误。
- 被选分支目标为空返回验证错误。
- `actual_control` 固定为 `false`。

## 耦合度评估

| 项目 | 影响 |
|---|---|
| 主程序调度 | 无影响 |
| DAG 构建 | 无影响 |
| ready queue | 无影响 |
| controller | 无影响 |
| NodeTaskModel | 无影响 |
| RuntimeStore | 无新增状态表结构 |
| 节点注册表 | 新增普通节点定义 |
| 测试 | 增加节点执行和 API schema 覆盖 |

第一阶段耦合度低，主要变更集中在：

```text
src/flowweaver/nodes/builtin_table.py
src/flowweaver/nodes/default_registry.py
tests/integration/test_builtin_table_nodes.py
tests/integration/test_api.py
docs/nodes/*
```

## 性能评估

预览型控制节点成本很低：

| 节点 | 主要成本 |
|---|---|
| `JumpAnchorNode` | 生成一行状态表 |
| `UnconditionalJumpNode` | 生成一行状态表 |
| `ConditionalJumpNode` | 读取一张很小的条件状态表并生成一行状态表 |

性能风险主要来自后续真实调度阶段，而不是第一阶段预览节点。

## 进入真实调度前的必要条件

在让控制节点真正影响执行路径前，需要单独完成这些能力：

1. 工作流定义支持条件边或控制边。
2. DAG 构建能识别控制边和普通数据边。
3. ready queue 能按分支选择下游。
4. controller 能把未选分支标记为跳过或未进入。
5. workflow 完成判断能接受分支跳过后的合法完成状态。
6. 运行事件能解释路径选择原因。
7. 测试覆盖并行分支、嵌套分支、失败分支和取消。

这些能力应作为调度协议建设，不放进单个节点 handler。

## 后续批次建议

### 第二阶段：条件边协议

在预览节点稳定后，再定义真实条件边或控制边的数据模型。

### 第三阶段：真实分支执行

让 `ConditionalJumpNode` 或条件边能影响 ready 选择，并记录未选分支状态。

### 第四阶段：循环节点

在分支执行稳定后，再处理 `LoopStartNode` 和 `LoopJudgeNode`，并加入最大迭代保护。

### 第五阶段：子工作流

最后再处理 `SubWorkflowNode`，重点是输入输出映射、父子运行记录、取消传播和结果汇总。

## 当前建议

下一步最小实现入口：

```text
先实现 JumpAnchorNode 的预览状态表版本。
随后实现 UnconditionalJumpNode 的预览状态表版本。
最后实现 ConditionalJumpNode 读取 ConditionFlagNode 状态表并输出分支计划。
```

这样可以先把控制节点的后端注册、状态协议和测试基础建立起来，同时不打断当前主程序 DAG 执行模型。
