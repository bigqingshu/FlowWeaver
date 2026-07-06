# FlowWeaver 节点核心模板：当前主程序框架支持分析

> 分析对象：`docs/nodes/FlowWeaver_节点规划核心模板.md`
> 分析范围：后端节点定义、工作流定义、节点执行、运行记录、RuntimeEvent、Avalonia 节点目录和节点配置 UI。
> 2026-07-05 更新：默认主程序权限/审计模块已移除并后置。本文后续分析不再把权限句柄、AuditEvent 或权限审批视为当前框架能力。
> 结论用途：判断后续按节点模板逐个规划节点时，哪些内容当前框架已经能承接，哪些需要先补框架。

## 一、总体结论

当前主程序框架已经支持“最小可运行节点”的主链路：

```text
节点定义
-> 工作流节点实例
-> DAG 调度
-> NodeTask
-> NodeExecutor
-> NodeRun 状态
-> TableRef 输出
-> RuntimeEvent 查询
-> Avalonia 节点目录和配置表单
```

也就是说，后续如果新增的是普通数据处理节点，当前框架已经具备基础承载能力。

但当前框架还没有把“节点规划模板里的所有字段”都做成一等能力。很多字段目前适合先写在文档里，用来指导设计；真正实现时需要再补协议、存储、API 或 UI。

## 二、支持等级说明

| 状态 | 含义 |
| --- | --- |
| 已支持 | 当前代码已经有明确模型、运行链路或 UI 承接 |
| 部分支持 | 有基础能力，但不完整，或只覆盖内置节点 |
| 文档支持 | 适合先写在节点规划文档里，当前程序不需要直接存储 |
| 暂不支持 | 当前框架没有对应字段、接口或运行机制 |

## 三、节点模板字段支持矩阵

| 模板字段 | 当前支持 | 当前承接位置 | 说明 |
| --- | --- | --- | --- |
| 节点名称 | 已支持 | `NodeDefinitionSpec.node_type`、`display_name`、`NodeInstanceModel.display_name` | 后端有节点类型和显示名，工作流实例也可覆盖显示名 |
| 节点方向 | 文档支持 | 暂无程序字段 | 当前没有 `category`、`direction` 或分组字段，节点目录也未按方向分类 |
| 优先级 | 文档支持 | 暂无程序字段 | 适合规划阶段使用，不一定需要进入运行时 |
| 当前状态 | 文档支持 | 暂无程序字段 | 可在节点规划文档维护；程序只知道节点是否注册、是否可运行 |
| 要解决的问题 | 文档支持 | 暂无程序字段 | 属于产品说明，不需要进入执行链路 |
| 用户看到的能力 | 部分支持 | `display_name`、配置 schema、UI 节点目录 | UI 可展示节点名称、端口和配置摘要，但没有专门的能力描述字段 |
| 不解决的内容 | 文档支持 | 暂无程序字段 | 适合留在规划文档，防止节点范围扩大 |
| 输入 | 已支持 | `input_ports`、`connections`、`NodeTaskModel.input_refs` | 支持端口、连接和运行时输入引用 |
| 输出 | 已支持 | `output_ports`、`NodeTaskResultModel.output_refs`、`TableRef` | 支持输出端口和运行时结果引用 |
| 配置项 | 已支持 | `config_schema`、`NodeInstanceModel.config`、Avalonia 配置表单 | 后端节点定义可返回 schema，UI 已能生成基础配置输入 |
| 数据契约 | 部分支持 | `TableRef`、`RuntimeDataRegistry`、`NodeTaskModel.input_refs` | TableRef 主链路已支持；DataRef、字段级契约、完整 NodeResultModel 尚未完整落地 |
| 执行模式 | 部分支持 | `NodeDefinitionSpec.execution_mode`、WorkflowProcess execution mode | 节点定义有 execution_mode，但当前执行分流主要按内置节点类型处理 |
| 是否支持取消 | 部分支持 | `CancelToken`、`CancellableNodeExecutor`、WorkflowRun cancel | 运行框架支持取消；普通节点是否响应取消取决于节点实现 |
| 是否支持进度上报 | 部分支持 | `NODE_TASK_PROGRESS`、`NodeRun.progress`、`current_stage` | 框架支持进度事件；当前主要测试节点使用，普通内置表节点尚未统一上报 |
| 是否有副作用 | 文档支持 | 节点方案说明 | 主程序不再内置权限/审计模块；副作用和外部资源访问先在节点方案中声明 |
| 外部资源与副作用声明 | 文档支持 | 节点方案说明 | 当前没有统一授权字段，后续如需外部资源控制应作为节点能力或独立机制讨论 |
| 后台极简模式是否保留 | 暂不支持 | 暂无运行策略字段 | 目前没有 `BACKGROUND_MINIMAL` 之类的记录策略 |
| 后台极简模式保留内容 | 文档支持 | 暂无程序字段 | 适合先写在节点规划中，后续进入运行策略模型 |
| 后台极简模式关闭内容 | 文档支持 | 暂无程序字段 | 当前没有按模式关闭预览、追踪、详细日志的机制 |
| 性能影响等级 | 文档支持 | 暂无程序字段 | 当前节点定义没有 `performance_level` |
| 性能消耗点 | 文档支持 | 暂无程序字段 | 适合先文档化，用于后续 UI 提示或调度预算 |
| 性能控制方式 | 部分支持 | timeout、预览 run、limit 查询 | 有超时和部分查询限制，但没有节点级统一性能预算 |
| 失败场景 | 文档支持 | 运行时只记录实际错误 | 规划里的失败场景不进入程序；运行失败后会写入 NodeRun.error |
| 失败提示 | 部分支持 | `NodeTaskResultModel.error`、`NodeRun.error`、UI NodeRun 列表 | 当前多为底层错误摘要，缺少节点级用户友好提示模板 |
| 验收方式 | 文档支持 | 测试体系可承接 | 当前有 unit/integration/UI tests，但模板字段本身不自动生成测试 |
| 后续扩展 | 文档支持 | 暂无程序字段 | 保留在节点规划文档即可 |

## 四、当前已经比较稳的能力

### 1. 节点注册和节点目录

当前后端有 `NodeDefinitionSpec` 和 `NodeRegistry`，可注册：

```text
node_type
node_version
display_name
input_ports
output_ports
execution_mode
default_timeout_seconds
retry_safe
config_schema
```

对应文件：

```text
src/flowweaver/nodes/registry.py
src/flowweaver/nodes/default_registry.py
src/flowweaver/api/routes_node_definitions.py
```

Avalonia 端已能读取节点定义，并显示节点目录、端口、执行模式、超时、是否可重试、配置摘要。

对应文件：

```text
Avalonia_UI/Api/EngineHostDtos.cs
Avalonia_UI/ViewModels/NodeDefinitionListItemViewModel.cs
Avalonia_UI/Views/Components/Workflow/WorkflowNodeCatalogView.axaml
```

### 2. 工作流节点实例和配置

工作流定义已经支持节点实例：

```text
node_instance_id
node_type
node_version
display_name
config
position
enabled
```

对应文件：

```text
src/flowweaver/workflow/definition.py
```

这意味着后续每个节点的配置项可以先进入 `config`，再由后端 runner 读取。

### 3. DAG 调度、输入输出和运行记录

当前 WorkflowRunProcess 能把工作流定义转成 DAG，按依赖提交节点任务。

运行时任务里已经有：

```text
input_refs
config
timeout_seconds
```

节点结果里已经有：

```text
output_refs
status
error
started_at
finished_at
```

对应文件：

```text
src/flowweaver/workflow_process/dag.py
src/flowweaver/workflow_process/node_tasks.py
src/flowweaver/protocols/node_task.py
```

### 4. 状态、取消、超时和进度

NodeRun 已有最小运行字段：

```text
status
progress
current_stage
last_heartbeat
error
attempt
started_at
finished_at
```

执行器层支持：

```text
NODE_TASK_HEARTBEAT
NODE_TASK_PROGRESS
NODE_TASK_CANCEL_REQUEST
```

对应文件：

```text
src/flowweaver/node_executor/process.py
src/flowweaver/node_executor/cancel_token.py
src/flowweaver/workflow_process/node_tasks.py
src/flowweaver/engine/db_models.py
```

这说明“是否支持取消”和“是否支持进度上报”在框架层有基础，但未来普通节点需要有统一写法，否则每个节点都要自己接事件。

### 5. TableRef 数据交接

内置表节点已经能：

```text
读取 input_refs
创建 STAGING 表
写入数据
发布为 PUBLISHED TableRef
返回 output_refs
```

对应文件：

```text
src/flowweaver/nodes/builtin_table.py
src/flowweaver/engine/runtime_data_registry.py
src/flowweaver/engine/runtime_table_provider.py
```

共享表节点也已支持发布和读取共享版本。

对应文件：

```text
src/flowweaver/nodes/builtin_shared_table.py
src/flowweaver/engine/shared_table_reader.py
```

## 五、当前明显缺口

### 1. 缺少通用节点实现接口

当前 `NodeRegistry` 负责描述节点，真正执行则由内置 runner 或执行器分流完成。

现状：

```text
表节点：BuiltinTableNodeRunner
共享表节点：BuiltinSharedTableNodeRunner
测试节点：BuiltinFaultNodeExecutor
其他节点：FakeNodeExecutor
```

问题是：后续如果要大量新增业务节点，最好有一个统一的节点实现接口，例如：

```text
NodeDefinitionSpec
+ NodeRunner
+ NodeRuntimeContext
```

否则每新增一类节点，都要改执行器分流逻辑。

### 2. 缺少节点方向和分类字段

模板里的“节点方向”目前只能写在文档里。

如果后续节点很多，建议给 `NodeDefinitionSpec` 增加轻量字段：

```text
category
tags
description
```

这样节点目录才能按输入、处理、输出、共享、调试等方向筛选。

### 3. 缺少外部资源与副作用声明

当前主程序已移除默认权限/审计模块，不再维护通用权限声明、授权句柄或审批链路。

后续如果节点会读写外部文件、数据库、程序或服务，建议先让节点方案写清楚副作用和外部资源访问范围，而不是把这些逻辑塞回主程序。

建议方向：

```text
side_effect_level
external_resource_summary
```

这些字段第一版可以先用于节点目录提示、用户确认和测试边界，不作为主程序统一授权机制。

### 4. 缺少后台极简运行策略

模板里有：

```text
后台极简模式是否保留
后台极简模式保留内容
后台极简模式关闭内容
```

当前程序没有运行记录档位，也没有工作流级或节点级记录策略。

目前能做到的是：

- 运行时自然记录最小 NodeRun。
- RuntimeEvent 已经可查。
- 预览 run 和正式 run 有 run_mode 区分。

还不能做到：

- 按 BACKGROUND_MINIMAL 关闭详细事件。
- 对单个节点覆盖记录策略。
- 对慢节点建议增强记录。

### 5. 缺少性能影响和性能预算模型

当前节点有：

```text
default_timeout_seconds
timeout_seconds
retry_safe
```

但没有：

```text
performance_level
resource_profile
max_preview_rows
max_metrics_events
max_output_rows
```

所以模板里的性能字段目前只能作为规划说明，不能被程序自动执行。

### 6. 缺少用户友好失败提示模型

当前节点失败会进入：

```text
NodeTaskResultModel.error
NodeRun.error
```

但错误多来自底层异常或 runner 内部拼接。未来如果希望每个节点都给用户稳定提示，可以给节点定义或错误模型增加：

```text
error_code
user_message
suggested_action
technical_detail
```

### 7. 缺少完整 DataRef 和完整 NodeResult 落地

协议里有更丰富的 `NodeResultModel`：

```text
affected_rows
skipped_rows
warnings
metrics
diagnostics
change_set_summary
side_effect_summary
```

但实际执行主链路使用的是更轻的 `NodeTaskResultModel`，只持久化：

```text
status
output_refs
error
started_at
finished_at
```

这对于第一版足够，但如果要做完整节点诊断、变更摘要或副作用摘要，需要再扩展结果持久化和 API。

## 六、按节点模板使用时的实际建议

### 可以直接开始用模板规划的字段

这些字段现在就可以用于后续节点分析：

```text
节点名称
节点方向
优先级
当前状态
要解决的问题
用户看到的能力
不解决的内容
输入
输出
配置项
数据契约
执行模式
是否支持取消
是否支持进度上报
是否有副作用
外部资源与副作用声明
性能影响等级
性能消耗点
失败场景
失败提示
验收方式
后续扩展
```

这些不要求当前程序立刻支持全部字段。它们可以先作为规划事实源。

### 实现节点时当前最容易落地的字段

如果现在就要新增一个普通节点，最容易落地的是：

```text
node_type
node_version
display_name
input_ports
output_ports
config_schema
timeout_seconds
input_refs
output_refs
NodeRun status/progress/error
```

### 实现节点前建议先补的框架字段

如果后续要连续增加很多节点，我建议先补最小框架，不然会越做越散：

```text
NodeDefinitionSpec.category
NodeDefinitionSpec.description
NodeDefinitionSpec.tags
NodeDefinitionSpec.supports_cancel
NodeDefinitionSpec.supports_progress
NodeDefinitionSpec.side_effect_level
NodeDefinitionSpec.performance_level
```

这些字段不一定都参与运行控制，但能让节点目录、规划文档和实现保持一致。

## 七、推荐下一步

### 第一步：先不要补复杂运行策略

暂时不要先做：

```text
BACKGROUND_MINIMAL
节点级记录覆盖
慢节点自动建议
字段级追踪
单元级追踪
完整 ChangeSet
```

这些都偏后续。

### 第二步：先补节点定义元数据

优先补：

```text
category
description
tags
supports_cancel
supports_progress
side_effect_level
performance_level
```

这样后续节点规划能映射到程序字段。

### 第三步：再补通用节点实现接口

建议形成：

```text
NodeRunner
NodeRuntimeContext
NodePermissionResolver
```

让每个新节点不用改主执行器分流代码。

### 第四步：按模板逐个节点分析

等上面最小元数据补齐后，就可以按：

```text
docs/nodes/FlowWeaver_节点规划核心模板.md
```

逐个节点写方案。

每个节点方案可以先落成独立 MD，再决定是否进入实现。

## 八、简短结论

当前主程序框架支持“能注册、能配置、能运行、能记录状态、能输出 TableRef、能取消、能看 NodeRun”的节点基础主线。

但它还不完全支持“节点规划模板”里的全部核心字段。模板现在可以作为规划工具使用；如果要让模板和程序真正对齐，下一步应先补节点定义元数据和通用节点实现接口，而不是直接进入大量节点开发。
