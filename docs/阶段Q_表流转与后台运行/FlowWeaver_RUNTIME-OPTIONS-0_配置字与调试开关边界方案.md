# FlowWeaver RUNTIME-OPTIONS-0：配置字与运行反馈开关边界方案

> 文档状态：前置方案
> 当前阶段：只定义运行时配置字边界、UI 入口和落地顺序，不修改代码
> 不适用范围：节点业务参数实现、权限审计模型、完整专用编辑器、全量性能优化

## 1. 背景

节点自身必须具备的计算参数，仍然归属于节点 `config_schema` 和节点实例 `config`。这部分决定节点如何完成业务处理，例如新增列的列名、默认值和数据类型。

配置字用于控制非业务能力，例如日志等级、运行反馈、进度上报、诊断上下文、反馈降噪等。它不应侵入节点业务配置，也不应要求每个普通节点都写一套 UI 专用逻辑。

目标是让任何工作流运行状态都可以通过一个独立入口切换运行反馈强度：前期测试保留普通可观测信息，后台稳定运行时降低反馈量，问题定位时提高日志和事件细节。

## 2. 当前主程序事实

当前已经具备的支点：

| 能力 | 当前事实 | 对配置字的意义 |
| --- | --- | --- |
| 节点业务配置 | `NodeInstanceModel.config` 会进入 `NodeTaskModel.config` | 节点业务参数已经有稳定通道 |
| 后端配置 schema | `NodeDefinitionSpec.config_schema` 可描述节点表单字段 | 业务参数继续由 schema 驱动 UI |
| 运行事件 | 已有 `WORKFLOW_STARTED`、`NODE_PROGRESS`、`NODE_FINISHED` 等 runtime events | 可按配置字控制事件详细程度 |
| 进度反馈 | 节点任务已有 progress 更新 | 可按配置字控制进度反馈频率 |

当前缺口：

| 缺口 | 说明 |
| --- | --- |
| 无工作流级运行时配置字段 | 工作流定义模型目前没有独立的 `runtime_options` 或配置字字段 |
| 无节点级运行时覆盖字段 | 现在只有节点业务 `config`，没有与业务参数分离的运行时覆盖 |
| 无合并层 | 主程序没有把“全局默认 + 节点覆盖”解析成最终运行选项 |
| 无版本化配置字模型 | 当前没有配置字 schema 版本、默认值和兼容策略 |
| 无反馈限流策略 | 当前没有统一限制事件、进度和诊断 payload 的配置层 |

## 3. 核心边界

配置字不等于节点业务参数。

配置字控制的是“运行时附加行为”：记录多少、反馈多少、是否保留错误上下文、是否限制诊断 payload。节点业务参数控制的是“业务怎么处理数据”。这两个通道需要隔离。

配置字只做减法，不做加法。它只能限制、降低、过滤当前已经存在的记录与反馈能力，不能凭空增加节点能力，不能改变节点核心计算结果，也不能替代副作用节点自己的业务配置。

主程序和节点都需要真实按照配置字运行：

* 主程序负责统一过滤 runtime events、progress、metrics、payload、脱敏和限流。
* 节点如果会上报 progress、metrics 或诊断信息，应通过统一通道上报，让配置字真实生效。
* 节点不得用配置字改变核心计算、当前表输出、外部写入、文件改名、插件调用等业务行为。

建议边界如下：

```text
节点业务 config
  - 由节点 config_schema 声明
  - 由节点实现读取
  - 决定数据处理逻辑

运行时配置字 runtime_options
  - 由主程序统一声明和合并
  - 由调度层、事件层、诊断模块和可选节点能力读取
  - 限制日志、反馈、进度、诊断记录强度
```

## 4. UI 入口方案

在工作流界面中保留现有节点配置区。节点配置区下方新增“配置字”入口按钮，点击后打开独立窗口。

配置字独立窗口建议分为上下两部分：

| 区域 | 用途 |
| --- | --- |
| 上方：工作流整体配置字 | 设置全体节点默认运行时选项 |
| 下方：节点独立配置字 | 通过下拉菜单选择节点，只保存与工作流默认值不同的覆盖项 |

节点独立配置字的字段和工作流整体配置字一致。区别是：工作流整体配置字提供默认值，节点独立配置字只表达覆盖。

建议 UI 只显示结构化字段。配置是否已应用由工作流草稿状态、保存结果和 revision 状态表达。

## 5. 配置字字段建议

配置字字段分为“第一版建议启用”和“后续可扩展”。第一版先覆盖运行过程中最容易产生性能和噪音的反馈能力。

| 字段 | 类型 | 默认值 | 说明 |
| --- | --- | --- | --- |
| `version` | string | `1.0` | 配置字结构版本，用于后续兼容 |
| `profile` | enum | `normal` | 快速切换预设，可选 `background_fast`、`normal`、`diagnostic`、`custom` |
| `strict_validation` | boolean | `true` | 配置字非法时是否阻止保存/运行；关闭时可回退默认值 |
| `telemetry.log_level` | enum | `INFO` | 控制节点和主程序附加日志等级 |
| `telemetry.event_level` | enum | `progress` | 控制 runtime event 详细程度，可选 `none`、`basic`、`progress`、`verbose` |
| `telemetry.event_rate_limit_per_second` | integer | `0` | 限制高频事件写入和推送，`0` 表示不限制 |
| `telemetry.progress_enabled` | boolean | `true` | 是否接收节点进度反馈 |
| `telemetry.progress_interval_seconds` | number | `0` | 进度最小上报间隔，`0` 表示不限制 |
| `diagnostics.capture_error_context` | boolean | `true` | 失败时保留错误上下文 |
| `diagnostics.include_metrics` | boolean | `true` | 是否保留节点上报的 metrics |
| `diagnostics.payload_byte_limit` | integer | `0` | 限制单次诊断 payload 大小，`0` 表示不限制 |
| `diagnostics.ttl_seconds` | integer | `0` | 诊断事件保留建议时间；当前不负责清理业务输出数据 |
| `diagnostics.redact_columns` | array | `[]` | 需要脱敏的字段名列表 |
| `diagnostics.mask_policy` | enum | `none` | 可选 `none`、`partial`、`full` |

后续可扩展但不建议第一版强做的字段：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| `apply_scope` | enum | 区分 `workflow`、`node`、`this_run`。其中 `this_run` 属于运行请求层，不应默认写入工作流定义 |
| `run_override` | object | 仅本次运行临时覆盖，用于临时 diagnostic，不污染工作流草稿 |
| `performance.max_event_queue_size` | integer | 限制事件缓冲队列大小 |
| `performance.defer_ui_updates` | boolean | 后台高速运行时降低 UI 刷新频率 |

不建议第一版加入：权限、审计、细粒度安全策略、外部存储清理策略、业务输出表自动清理策略。这些会把当前配置字方案拖回高耦合设计。

## 6. 建议数据结构

工作流定义中建议新增一个独立结构，不放进节点业务 `config`：

```json
{
  "schema_version": "1.0",
  "nodes": [],
  "connections": [],
  "runtime_options": {
    "version": "1.0",
    "workflow": {
      "profile": "normal",
      "strict_validation": true,
      "telemetry": {
        "log_level": "INFO",
        "event_level": "progress",
        "event_rate_limit_per_second": 0,
        "progress_enabled": true,
        "progress_interval_seconds": 0
      },
      "diagnostics": {
        "capture_error_context": true,
        "include_metrics": true,
        "payload_byte_limit": 0,
        "ttl_seconds": 0,
        "redact_columns": [],
        "mask_policy": "none"
      }
    },
    "node_overrides": {
      "node_001": {
        "telemetry": {
          "log_level": "DEBUG",
          "event_level": "verbose"
        },
        "diagnostics": {
          "include_metrics": true
        }
      }
    }
  }
}
```

调度时生成最终结果：

```text
resolved_runtime_options(node_001)
  = system defaults
  + runtime_options.workflow
  + runtime_options.node_overrides.node_001
```

最终下发给执行层时，建议进入独立字段，例如：

```text
workflow process 内部 resolved runtime options
```

不建议把运行时配置直接塞进：

```text
NodeTaskModel.config.__runtime
```

原因是这样会污染节点业务配置，并让 schema 表单、节点实现、诊断功能互相耦合。第一版也不要求扩大 `NodeTaskModel` 协议；如果后续确实需要让外部执行器直接读取配置字，再单独评估 `NodeTaskModel.runtime_options`。

## 7. 同步与保存规则

配置字以真实结构化配置为准，直接保存、合并和下发。

建议规则：

1. 工作流草稿保存真实 `runtime_options`。
2. 节点覆盖只保存与工作流默认值不同的差异。
3. 运行前合并出节点最终配置字 `resolved_runtime_options`。
4. 下发真实配置字。
5. UI 通过草稿 dirty 状态、保存结果和 workflow revision 判断配置是否已应用。

各场景规则如下：

| 场景 | 规则 |
| --- | --- |
| UI 同步提示 | 使用草稿 dirty 状态和保存成功状态 |
| 运行日志关联 | 使用 `workflow_run_id`、`node_run_id`、`node_instance_id` |
| 配置回放 | 如确实需要，保存当次 `resolved_runtime_options` 快照 |
| 判断配置变化 | 使用 workflow revision 或直接比较 JSON 内容 |
| 调度缓存 | 第一版不缓存，配置字很小，合并成本可忽略 |
| 业务输出清理 | 当前先由用户手动清理，不由配置字自动删除 TableRef 或 runtime sqlite 表 |

## 8. 反馈边界

建议第一版语义：

| 配置 | 行为 |
| --- | --- |
| `progress_enabled=false` | 不记录或不推送节点进度细节 |
| `event_level=basic` | 只保留开始、结束、失败等关键事件 |
| `event_level=verbose` | 保存进度、阶段、metrics 等详细事件 |
| `event_rate_limit_per_second` | 对高频事件做限流，避免后台运行时事件写入放大 |

这样可以在手动运行、预览运行和后台运行中统一控制反馈量，同时保留必要的运行状态可观察性。

## 9. 诊断能力边界

配置字只控制日志、事件、进度、错误上下文、metrics 和 payload 限制。

第一版诊断能力建议：

| 能力 | 说明 |
| --- | --- |
| 错误上下文 | 节点失败时记录错误类型、错误消息、阶段、关键配置摘要 |
| metrics | 节点主动上报时，可按 `include_metrics` 控制是否保留 |
| payload 限制 | 通过 `payload_byte_limit` 限制诊断信息大小 |
| 保留建议 | 通过 `ttl_seconds` 表达诊断记录保留建议；业务输出表当前先按用户手动清理 |
| 脱敏 | 通过 `redact_columns` 和 `mask_policy` 避免日志/事件携带敏感字段 |

## 10. 推荐实现顺序

### RUNTIME-OPTIONS-1：模型与文档落地

目标：让工作流 JSON 正式承载 `runtime_options`。

范围：

* 新增 `RuntimeOptionsModel`。
* `WorkflowDefinitionModel` 增加 `runtime_options`。
* 增加默认值、校验、序列化测试。
* 不改变运行行为。

验收：旧工作流不带 `runtime_options` 仍可加载，新工作流可保存并回读配置字。

### RUNTIME-OPTIONS-2：UI 独立窗口

目标：让用户可编辑工作流整体配置字和节点覆盖。

范围：

* 工作流界面节点配置区下方新增入口。
* 独立窗口上方编辑 workflow 配置字。
* 独立窗口下方选择节点并编辑覆盖项。
* 写回 workflow draft。

验收：不运行工作流也能编辑、保存、重新加载配置字。

### RUNTIME-OPTIONS-3：合并与下发

目标：运行时为每个节点生成最终配置字。

范围：

* 增加 resolver：`system defaults + workflow + node override`。
* 运行开始时生成工作流进程内部的 resolved runtime options。
* 第一版不写入 `NodeTaskModel.config`，也不强制扩大 `NodeTaskModel` 协议。
* 不缓存跨运行结果。

验收：无覆盖节点继承工作流默认值；有覆盖节点得到正确的最终配置字；节点业务 config 不被污染。

### RUNTIME-OPTIONS-4：事件、日志、进度控制

目标：配置字开始影响反馈量。

范围：

* `event_level` 控制 runtime events 粒度。
* `progress_enabled` 控制进度记录和推送。
* `event_rate_limit_per_second` 控制事件写入和推送频率。
* `log_level` 控制附加日志等级。
* `payload_byte_limit` 控制诊断 payload 大小。

验收：后台快速配置下事件量明显减少；diagnostic 配置下事件信息更完整。

### RUNTIME-OPTIONS-5：诊断上下文与脱敏

目标：支持按配置控制失败上下文、metrics 和脱敏。

范围：

* 支持 `capture_error_context`。
* 支持 `include_metrics`。
* 支持 `payload_byte_limit`。
* 支持 `redact_columns` 和 `mask_policy`。
* 支持 `ttl_seconds` 作为保留建议。

验收：后台快速配置下诊断 payload 精简；diagnostic 配置下错误上下文更完整。

## 11. 风险与约束

| 风险 | 说明 | 建议 |
| --- | --- | --- |
| 业务配置与运行配置混杂 | 会导致节点 schema、UI 和主程序互相耦合 | 使用独立 `runtime_options` |
| 诊断 payload 放大 | verbose 事件和 metrics 可能让 runtime events 变多 | 增加事件限流和 payload 大小限制 |
| 临时运行覆盖污染工作流 | this-run 配置如果写回草稿，会造成用户误判 | `run_override` 保持在运行请求层，不默认持久化 |
| 脱敏策略不完整 | 错误上下文可能包含敏感字段 | 支持 `redact_columns` 和 `mask_policy`，默认保守 |
| 配置字窗口过早复杂化 | UI 可能先于后端语义发散 | 先支持固定字段，后续再 schema 化 |

## 12. 当前结论

配置字方案可以作为主程序运行时能力推进，但第一版应保持低耦合：

* 节点业务参数继续走节点 `config_schema`。
* 配置字进入工作流级 `runtime_options`。
* 节点覆盖只保存差异。
* 真实配置直接保存、合并、下发。
* 主程序负责事件、进度、日志、metrics、payload、脱敏和诊断上下文控制。
* 节点已有的 progress、metrics、诊断输出需要走统一通道，让配置字真实生效。
* 节点不使用配置字改变业务计算、当前表输出或副作用行为。
* 运行数据当前保持持久化记录，UI 通过查询记录读取；清理先由用户手动执行。

这个方向适合所有运行状态：普通运行默认可观测，后台运行可降噪，问题排查可提高局部诊断等级，而不是把所有节点长期变成高反馈、高 IO 模式。
