# FlowWeaver WORKFLOW-EDIT-2.0：结构化编辑可用性缺口边界分析

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.0 边界分析完成
> 当前阶段：结构化编辑第二阶段前置分析
> 不适用范围：代码实现、XAML 调整、后端 API 改动、桌面真实 smoke

## 1. 背景

WORKFLOW-EDIT-1 已经完成结构化编辑的最小闭环：

```text
WorkflowDefinitionDraftJson
-> draft structure readonly parser
-> node / connection patcher
-> ViewModel command
-> WorkflowSummaryView form
-> draft JSON dirty / validation invalidation / save revision guard
```

但当前体验仍偏“工程输入框”，用户需要手动填写 node type、node instance id、connection id、source / target node id 和 port。

WORKFLOW-EDIT-2 不应扩大成图形化编辑器或完整 schema 编辑器，而应先补齐最影响可用性的最小交互边界。

## 2. 缺口分类

### 2.1 UI 可先做的缺口

这些能力可以主要依赖现有 ViewModel / 本地状态完成：

| 缺口 | 当前表现 | 建议处理 |
| --- | --- | --- |
| patcher warning / error 不够用户友好 | UI 可能直接展示内部错误码 | 增加错误码到本地化文案的映射 |
| DeleteNode 遇 `NODE_HAS_CONNECTIONS` | 用户只知道删除失败 | 提示需要先删除相关 connection |
| node instance id 手填 | 容易重复或为空 | 增加最小自动建议值，用户仍可覆盖 |
| connection id 手填 | 容易重复或为空 | 增加最小自动建议值，用户仍可覆盖 |
| source / target node 手填 | 容易拼写错误 | 基于 draft nodes 提供可选项 |

### 2.2 依赖现有只读 API / 已有数据的缺口

这些能力不需要新增后端写接口，但需要稳定消费已有只读数据：

| 缺口 | 数据来源 | 建议处理 |
| --- | --- | --- |
| node type 选择 | 已有节点定义只读 API / catalog | 下拉选择可见节点类型 |
| node type 用户可读名 | node definition display 信息 | 下拉中显示 label，保存仍写 type |
| source / target 候选 | draft structure nodes | 下拉显示 node instance id 和 type |

### 2.3 需要后端 schema 或更深契约的缺口

这些能力暂不应在 WORKFLOW-EDIT-2 初期硬做：

| 缺口 | 原因 | 建议阶段 |
| --- | --- | --- |
| port 下拉选择 | 需要节点 input/output port schema 契约 | NODE-CONFIG-SCHEMA 或后续 workflow schema 阶段 |
| 端口类型兼容校验 | 需要端口类型、方向和数据契约 | 后端 schema 明确后再做 |
| 根据 node type 自动生成 config 表单 | 已属于 node config schema UI 深化 | 独立 schema 表单阶段 |
| 连接自动推荐 | 需要语义级端口信息 | 后续图编辑或智能辅助阶段 |

### 2.4 明确后置的能力

以下能力继续保留，不进入 WORKFLOW-EDIT-2 最小线：

* 图形化画布。
* 拖拽连线。
* 自动布局。
* 撤销 / 重做。
* 多选批量编辑。
* 节点模板市场。
* 外部插件节点编辑器。

## 3. 建议执行顺序

建议拆成以下小步：

```text
WORKFLOW-EDIT-2.1：
用户友好 warning / error 映射。

WORKFLOW-EDIT-2.2：
node type 与 node instance id 输入体验收口。

WORKFLOW-EDIT-2.3：
connection source / target / id 输入体验收口。

WORKFLOW-EDIT-2.4：
桌面真实 smoke 与后置复核。
```

暂不把 port 下拉和端口深校验放入 2.1 到 2.4，因为这两项更依赖后端 schema 契约。

## 4. WORKFLOW-EDIT-2.1 边界

建议 2.1 只做错误展示体验，不改变 patcher 行为：

* 保留现有 patcher 错误码。
* 在 ViewModel 或本地化层增加用户可读文案映射。
* 覆盖 AddNode、DeleteNode、AddConnection、DeleteConnection 四类命令。
* Revision conflict、保存失败、后端校验失败继续沿用既有保存流程，不混入 patcher 映射。

建议测试：

* 重复 node id 展示用户可读文案。
* 删除仍被 connection 引用的 node 展示“先删除连接”类文案。
* 重复 connection id 展示用户可读文案。
* source / target 不存在展示用户可读文案。

## 5. WORKFLOW-EDIT-2.2 边界

建议 2.2 做节点新增体验增强：

* node type 从可用节点定义中选择。
* node instance id 提供自动建议值。
* 用户仍可手动覆盖 node instance id。
* 不新增后端写接口。
* 不自动生成复杂 config。

如果节点定义列表为空或加载失败，应降级回手动输入，不阻断当前 JSON 编辑能力。

## 6. WORKFLOW-EDIT-2.3 边界

建议 2.3 做 connection 输入体验增强：

* source / target 从当前 draft nodes 中选择。
* connection id 提供自动建议值。
* source / target 选择变化后不自动推断 port。
* source port / target port 仍保留手动输入。
* 如果 draft structure 无法解析，应降级回手动输入。

## 7. WORKFLOW-EDIT-2.4 边界

建议 2.4 做真实桌面 smoke 与阶段复核：

* 启动后端。
* 启动 Desktop。
* 选择已有 workflow。
* 使用结构化表单新增 node。
* 新增 connection。
* 删除 connection。
* 删除 node。
* Validate。
* Save。
* 重载 workflow 后确认 JSON 保持一致。

如果 smoke 发现后端组合根或 API 客户端问题，应先修真实路径，不在 UI 内绕过。

## 8. 当前结论

WORKFLOW-EDIT-2 的最稳方向是先补“输入和错误可读性”，而不是进入图编辑器。

下一小步建议：

```text
WORKFLOW-EDIT-2.1：
用户友好 warning / error 映射。
```

这一步可以进入代码，但仍应保持小步：先做映射模型 / 文案 / ViewModel 测试，再决定是否需要微调 View。
