# FlowWeaver WORKFLOW-EDIT-2.6：目标完成审计与人工 Desktop smoke 决策

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.6 审计完成
> 当前阶段：节点配置与结构化编辑主线完成审计
> 不适用范围：新增代码实现、推送、真实人工 Desktop 点击执行、port schema 深校验、图形画布

## 1. 阶段目标

对当前 active goal 中列出的主线逐项做证据审计：

```text
UI-NODE-CATALOG-2
NODE-CONFIG-SCHEMA-0/1
UI-SCHEMA-0
UI-NODE-CONFIG-1/2
WORKFLOW-EDIT-1/2
```

同时明确人工 Desktop smoke 是否应作为当前目标阻塞项，还是转为发布前或用户试用前的手动验收项。

本阶段只做文档审计，不新增源码或 XAML 改动。

## 2. 主线完成审计矩阵

| 主线 | 当前证据 | 审计结论 |
| --- | --- | --- |
| UI-NODE-CATALOG-2 | `UI组件MainWindow的后续计划.MD` 2.84、`WorkflowNodeCatalogViewStructureTests`、`MainWindowViewModelWorkflowTests`、本地化测试 | 只读节点目录状态、空态、错误态、禁用提示和本地化已完成 |
| NODE-CONFIG-SCHEMA-0 | `FlowWeaver_NODE-CONFIG-SCHEMA-0_后端配置Schema边界清单.md` | 后端 config schema 契约边界已固化 |
| NODE-CONFIG-SCHEMA-1 | `src/flowweaver/nodes/registry.py`、`src/flowweaver/nodes/default_registry.py`、`src/flowweaver/api/api_models.py`、`src/flowweaver/api/routes_node_definitions.py`、`tests/integration/test_api.py`、`EngineHostApiClientTests` | 后端 node definitions API 已返回 `config_schema_version` / `config_schema`，Avalonia DTO 已承接 |
| UI-SCHEMA-0 | `FlowWeaver_UI-SCHEMA-0_Avalonia配置Schema解析模型边界清单.md` | Avalonia schema 解析边界已固化 |
| UI-SCHEMA-1 | `NodeConfigSchemaParser`、`NodeConfigSchemaParserTests` | Avalonia schema parser 已落地，支持第一版字段子集和 unsupported/warning 回退 |
| UI-NODE-CONFIG-1 | `NodeDefinitionListItemViewModelTests`、`WorkflowNodeCatalogViewStructureTests` | 节点目录只读配置摘要已完成，不进入编辑表单 |
| UI-NODE-CONFIG-2 | `FlowWeaver_UI-NODE-CONFIG-2q_阶段总体验收与WORKFLOW-EDIT前复核.md`、相关模型/ViewModel/View 测试 | 已有节点实例 config 的 schema → input → Apply → draft JSON 最小闭环已完成 |
| WORKFLOW-EDIT-1 | `FlowWeaver_WORKFLOW-EDIT-1.8_阶段总体验收复核.md`、patcher / ViewModel / View 结构测试 | 工作流结构化编辑第一阶段已完成 |
| WORKFLOW-EDIT-2 | `FlowWeaver_WORKFLOW-EDIT-2.5_结构化编辑阶段小结与后续边界分析.md`、`WorkflowSummaryViewHeadlessSmokeTests`、发布 Desktop event smoke | 输入体验和自动化 smoke 已完成；真实人工 Desktop 点击 smoke 仍未执行 |

## 3. 当前验证结果

本次审计补跑验证：

```text
.\python312\python.exe -m pytest -q tests\integration\test_api.py -k "node_definitions"
通过：2，失败：0，跳过：0
提示：FastAPI/TestClient 依赖层 StarletteDeprecationWarning，不影响本次断言。

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowNodeCatalogViewStructureTests|NodeConfigSchemaParserTests|NodeDefinitionListItemViewModelTests|NodeConfigDraftBuilderTests|NodeConfigEditableDraftBuilderTests|NodeConfigEditableFieldInputViewModelTests|NodeConfigEditableFieldInputConfigBuilderTests|MainWindowViewModelWorkflowTests|WorkflowSummaryViewStructureTests|WorkflowSummaryViewHeadlessSmokeTests"
通过：91，失败：0，跳过：0
```

最近完整 Avalonia 验证仍可引用：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
成功，0 警告，0 错误

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：265，失败：0，跳过：0
```

## 4. 人工 Desktop smoke 决策

当前有三层 smoke 证据：

| smoke | 状态 | 覆盖 |
| --- | --- | --- |
| 发布 Desktop API/WebSocket 自动 smoke | 已完成 | 发布 assembly、portable EngineHost、token、API client、RuntimeEvent WebSocket、workflow run lifecycle |
| `WorkflowSummaryView` Headless GUI smoke | 已完成 | View runtime 加载、结构化编辑关键 ComboBox 物化与绑定 |
| 人工 Desktop 点击 smoke | 未执行 | 真实窗口点击、真实用户输入、Validate / Save 视觉确认、重载后肉眼确认 |

结论：

* 如果当前目标只要求“节点配置主线和结构化编辑主线的自动化实现与验收”，则现有证据已经足够支撑进入推送前复核。
* 如果把 WORKFLOW-EDIT-2.4 最初的“桌面真实 smoke”解释为必须完成真实人工点击，则当前目标仍缺少该手动验收记录。
* 当前不建议通过伪造点击或在 UI 内绕过真实路径来填补该项。
* 更稳的处理是把人工 Desktop smoke 明确作为发布前或用户试用前手动验收项，或由用户确认后单独执行。

## 5. 当前不应继续偷做的能力

以下能力不应在本目标末尾顺手实现：

* port 下拉选择。
* 端口方向和类型兼容校验。
* workflow validation schema 深度接入。
* 图形化画布。
* 拖拽连线。
* 自动布局。
* 撤销 / 重做。
* 节点专用复杂编辑器。
* 外部模块加载或插件化。

这些都应另起阶段分析。

## 6. 下一步建议

建议下一步不要继续写功能，而是做推送前总复核或等待用户确认人工 smoke 策略：

```text
WORKFLOW-EDIT-2.7：
推送前总复核与人工 Desktop smoke 是否阻塞的最终确认。
```

如果用户确认“人工 Desktop smoke 转为发布前手动验收项”，则可进入推送前总复核。

如果用户要求“WORKFLOW-EDIT-2 必须包含真实 GUI 手点”，则下一步应单独执行人工 Desktop smoke，不应继续扩展 port/schema/画布能力。
