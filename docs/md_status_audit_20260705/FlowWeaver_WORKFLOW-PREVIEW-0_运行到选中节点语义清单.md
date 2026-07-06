# FlowWeaver WORKFLOW-PREVIEW-0：运行到选中节点语义清单

> 审核状态（2026-07-05）：已实现 / 副作用策略后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端 run_mode=preview_to_node、target_node_instance_id、上游闭包调度、RuntimeEvent/WorkflowRun 记录、Avalonia 预览按钮和数据预览刷新已经落地。
> 未实现：副作用节点阻断策略未实现。
> 原因：第一版只定义并实现运行到选中节点的调试闭包，副作用能力需要节点能力模型更稳定后单独处理。

## 背景

当前数据预览只能读取已存在 WorkflowRun 中某个 NodeRun 发布的 TableRef。若用户只想排查工作流中间节点，就必须先运行完整工作流；当下游节点尚未配置完成、耗时较长或存在副作用风险时，这会降低调试效率。

本阶段定义“预览选中节点”的正式语义，后续小步再落后端 Store/API/调度与 Avalonia UI 接入。

## 目标语义

`预览选中节点` 表示创建一次调试用途的 preview run，只执行选中节点所需的上游依赖链，以及选中节点本身。

执行边界：

- 选中节点没有上游时，只运行选中节点。
- 选中节点有上游时，运行所有直接或间接上游节点，再运行选中节点。
- 选中节点的下游节点不运行。
- 第一版不为下游节点创建 NodeRun，避免用户误解为完整工作流执行结果。
- 预览完成后，数据预览区读取目标节点最新可读输出 TableRef。

## API 草案

保持现有启动 run 入口，扩展可选请求体；无 body 或未指定 run_mode 时保持完整运行兼容。

完整运行：

```json
{
  "run_mode": "full"
}
```

运行到选中节点：

```json
{
  "run_mode": "preview_to_node",
  "target_node_instance_id": "filter"
}
```

拒绝边界：

- `run_mode` 不是 `full` 或 `preview_to_node` 时拒绝。
- `preview_to_node` 缺少 `target_node_instance_id` 时拒绝。
- `target_node_instance_id` 不存在于工作流定义时拒绝。
- 目标节点所在上游闭包无法形成有效 DAG 时拒绝或沿用现有工作流校验失败。

## 调度边界

preview run 的可执行节点集合为：

```text
upstream_closure(target_node_instance_id) + target_node_instance_id
```

连接处理：

- 保留目标闭包内部连接。
- 指向闭包外下游节点的连接不参与调度。
- 上游闭包外节点不创建 NodeRun。

终态建议：

- preview run 内所有目标闭包节点成功时，WorkflowRun = `SUCCEEDED`。
- 目标闭包内任一节点失败时，沿用现有失败策略。
- RuntimeEvent 需要能区分 `run_mode=preview_to_node` 和 `target_node_instance_id`。

## UI 行为

数据预览区放置两个动作：

- `预览选中节点`：启动 `preview_to_node`，运行完成后刷新目标节点输出表。
- `运行工作流`：启动完整运行，运行完成后尝试显示最终或当前选中节点的可读输出表。

按钮启用条件：

- `预览选中节点` 需要已连接、已选中工作流、已加载工作流定义、已选中工作流节点。
- `运行工作流` 需要已连接、已选中可运行工作流。

提示原则：

- 若目标节点没有输出表，显示“该节点没有可读输出表”。
- 若 preview run 失败，显示失败节点和错误摘要。
- 若目标节点有副作用能力，后续可在按钮旁追加风险提示；第一版暂不实现副作用拦截。

## 最小验收

- 后端接受 `run_mode=full`，行为与旧无 body 请求一致。
- 后端接受 `run_mode=preview_to_node`，只创建并执行目标上游闭包内 NodeRun。
- 后端拒绝非法 run_mode、缺失目标节点、未知目标节点。
- RuntimeEvent 或 WorkflowRun 记录可追踪 run_mode 与 target_node_instance_id。
- Avalonia 点击 `预览选中节点` 后，会自动选择新 run，并在完成后刷新数据预览表格。

## 明确不在 PREVIEW-0 实现

- 不改后端 API。
- 不改调度器。
- 不改 Avalonia 按钮。
- 不处理副作用节点阻断策略。
- 不实现运行完成轮询策略。
