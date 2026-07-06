# FlowWeaver WORKFLOW-EDIT-3.0：WorkflowSummaryView 中间列布局收口

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

## 阶段目标

本阶段只修正工作流页面中间列 `WorkflowSummaryView` 的显示边界，重点处理“节点”和“连接”两块在桌面端窄列宽场景下出现的空白列表过高、编辑表单挤压和内容重叠问题。

本阶段不改变后端 API、不改变 workflow definition 保存语义、不新增节点类型、不调整端口推导或图画布能力。

## 问题现象

当前中间列在加载 workflow detail 后会出现：

```text
节点列表区域占用过高
连接列表区域占用过高
结构化编辑表单与列表边界混乱
节点/连接区域在列宽不足时互相挤压
```

根因是 `WorkflowSummaryView.axaml` 使用 `Auto,*,*` 和内部 `*` 行分配高度，叠加列表 `MinHeight`，导致节点与连接卡片在有限高度下被强行拉伸。

## 实施范围

本阶段采用最小 View 层修正：

```text
WorkflowSummaryView 根布局改为可滚动内容流
工作流定义、节点、连接三个卡片按内容自然排列
节点和连接列表改为 MaxHeight 上限
结构化编辑标题区分为新增/删除节点、新增/删除连接
主要输入框保持顶部对齐，避免被 Grid 行高拉伸
```

## 验收标准

完成后应满足：

```text
中间列内容可纵向滚动
节点列表不会撑满整块卡片
连接列表不会撑满整块卡片
新增/删除节点标题清晰区分
新增/删除连接标题清晰区分
原有 Command、ItemsSource、TwoWay 输入绑定保持不变
不引入 Converter 或新的业务判断
```

## 不在本阶段处理

以下能力后置：

```text
真实图画布显示
节点端口下拉选择
节点配置 Schema 表单化编辑
后端新增节点类型
自动连线推荐
人工 Desktop GUI 点击验收
```

## 测试计划

本阶段至少运行：

```powershell
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|WorkflowSummaryViewHeadlessSmokeTests"
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

其中 `WorkflowSummaryViewStructureTests` 需要覆盖中间列布局约束，防止后续再次引入 `Auto,*,*` 或列表固定最小高度导致的重叠回归。

## 验证结果

本阶段已完成以下验证：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
通过，0 warning，0 error

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowSummaryViewStructureTests|WorkflowSummaryViewHeadlessSmokeTests"
通过，7 passed

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过，266 passed
```
