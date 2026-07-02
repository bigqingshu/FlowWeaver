# FlowWeaver WORKFLOW-EDIT-1.4：节点删除 Preflight 与 Patcher

> 文档状态：WORKFLOW-EDIT-1.4 已完成
> 当前阶段：工作流结构化编辑的节点删除纯模型能力
> 不适用范围：ViewModel 命令、XAML 按钮、级联删除、连线编辑、画布编辑

## 1. 本小步目标

本小步在 `WorkflowDefinitionDraftNodePatcher` 中新增：

```text
DeleteNode(workflowDefinitionDraftJson, nodeInstanceId)
```

并扩展节点 patch 状态：

```text
NodeNotFound
NodeHasConnections
```

## 2. 当前能力

当前 `DeleteNode` 会：

* 解析完整 workflow draft JSON。
* 校验根必须是 object。
* 校验 `nodes` 必须是 array。
* 校验 `connections` 必须是 array。
* 校验 `nodeInstanceId` 必填。
* 查找目标节点。
* 扫描 connections 的 `source_node_id` / `target_node_id`。
* 如果目标节点仍被任何 connection 引用，则返回 `NODE_HAS_CONNECTIONS`。
* 仅删除无连接依赖的节点。
* 保留 root 其他字段和现有 `connections`。

## 3. 当前策略

第一版节点删除策略是：

```text
默认不做级联删除
存在连接依赖即阻断
```

原因：

* 级联删除会改变多个结构区域，风险高于单节点删除。
* 用户是否希望删除相关 connections 需要 UI 明确确认。
* 后续 connection patcher 完成后，再考虑由 UI 提供“先删连接，再删节点”的显式流程。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftNodePatcherTests"
通过：14，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：237，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.5：
connection 新增 / 删除纯 patcher。
```

建议范围：

* 只新增纯模型和测试。
* 新增 connection 时校验 connection_id 不重复。
* 新增 connection 时校验 source / target node 存在。
* 删除 connection 时校验目标 connection 存在。
* 第一版不做端口 schema 深校验。
* 不接 ViewModel 命令，不修改 XAML。
