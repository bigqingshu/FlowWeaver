# FlowWeaver WORKFLOW-EDIT-1.3：节点新增纯 Patcher

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-1.3 已完成
> 当前阶段：工作流结构化编辑的节点新增纯模型能力
> 不适用范围：ViewModel 命令、XAML 按钮、节点删除、连线编辑、画布编辑

## 1. 本小步目标

本小步只新增节点新增的纯 patcher：

```text
WorkflowDefinitionDraftNodePatcher.AddNode(...)
```

输入：

```text
workflowDefinitionDraftJson
nodeInstanceId
nodeType
nodeVersion
displayName
config(JsonElement)
```

输出：

```text
WorkflowDefinitionDraftNodePatchResult
```

## 2. 当前能力

当前 patcher 会：

* 解析完整 workflow draft JSON。
* 校验根必须是 object。
* 校验 `nodes` 必须是 array。
* 校验 `connections` 必须是 array。
* 校验 `node_instance_id` / `node_type` / `node_version` 必填。
* 校验 `node_instance_id` 不重复。
* 校验初始 `config` 必须是 object。
* 将新节点 append 到 `nodes`。
* 保留 root 上已有字段和 `connections`。
* 输出缩进后的完整 draft JSON。

## 3. 当前不做

本小步没有做：

* ViewModel 接入。
* UI 按钮。
* 自动生成 node_instance_id。
* 自动生成 display_name。
* 根据 node definition schema 自动生成默认 config。
* 端口校验。
* 连接自动补齐。
* 节点布局。

这些能力应在后续小步单独评估。

## 4. 验证结果

已执行：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowDefinitionDraftNodePatcherTests"
通过：9，失败：0，跳过：0

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：232，失败：0，跳过：0
```

## 5. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-1.4：
节点删除 preflight / patcher。
```

建议范围：

* 只新增纯模型和测试。
* 先识别目标节点是否存在。
* 识别受影响 connections。
* 第一版建议不做默认级联删除。
* 有连接依赖时返回明确阻断状态。
* 不接 ViewModel 命令，不修改 XAML。
