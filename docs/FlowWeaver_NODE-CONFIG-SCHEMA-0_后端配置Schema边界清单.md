# FlowWeaver NODE-CONFIG-SCHEMA-0：后端配置 Schema 边界清单

> 文档状态：NODE-CONFIG-SCHEMA-0 边界分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段 M.0/M.1 已固化边界
> 适用范围：后端 `NodeDefinitionSpec`、`GET /api/v1/node-definitions`、后续 Avalonia 节点配置表单的前置契约
> 当前执行点：只做语义和接口范围确认，不实现 API 字段、不改 DTO、不生成 UI 表单

## 1. 当前事实

当前 `NodeDefinitionSpec` 已包含：

```text
node_type
node_version
display_name
input_ports
output_ports
execution_mode
default_timeout_seconds
retry_safe
implementation_path
```

当前 `NodeDefinitionSpec` 不包含：

```text
config_schema
config_schema_version
ui_schema
category
icon
capabilities
minimum_client_capabilities
```

当前 `GET /api/v1/node-definitions` 返回：

```text
node_type
node_version
display_name
input_ports
output_ports
execution_mode
default_timeout_seconds
retry_safe
ui_visibility
```

当前接口明确不返回：

```text
implementation_path
config_schema
Python executor 细节
```

当前 workflow 校验只覆盖：

```text
workflow definition 基础结构
node_type / node_version 是否注册
端口是否存在
必填输入是否连接
DAG 是否有环
failure_policy 是否可用
```

当前 workflow 校验尚未覆盖：

```text
节点 config 是否符合节点配置契约
节点 config 默认值补齐
节点 config 与输入表字段之间的动态关系
```

## 2. 目标

NODE-CONFIG-SCHEMA-0 的目标是固定后端配置 Schema 的最小契约边界，为后续阶段做准备：

```text
NODE-CONFIG-SCHEMA-1
→ 后端 NodeDefinitionSpec / NodeDefinitionView / API 测试落地

UI-SCHEMA-0
→ Avalonia 只读解析和展示 schema 摘要

UI-NODE-CONFIG-1/2
→ 节点配置只读预览和最小通用配置表单
```

本阶段只做文档和现状复核，不修改代码。

## 3. 第一版契约建议

建议后端新增稳定字段：

```text
config_schema_version: string
config_schema: object | null
```

其中：

```text
config_schema_version
```

用于标记 FlowWeaver 自己的配置 Schema 契约版本，不等同于 JSON Schema draft 版本。第一版建议固定为：

```text
"1.0"
```

```text
config_schema
```

用于描述普通节点配置字段，第一版建议采用 FlowWeaver 自己的最小 schema 子集，而不是直接承诺完整 JSON Schema。

最小结构：

```json
{
  "type": "object",
  "properties": {
    "rows": {
      "type": "integer",
      "title": "Rows",
      "required": true,
      "default": 3,
      "minimum": 0
    }
  }
}
```

## 4. 支持的字段类型

第一版建议只支持：

| type | 用途 | Avalonia 后续映射 |
| --- | --- | --- |
| `string` | 名称、字段名、共享名 | TextBox |
| `integer` | 行数、版本号、秒数 | 数字输入 |
| `number` | 过滤阈值等浮点值 | 数字输入 |
| `boolean` | 开关 | CheckBox / Toggle |
| `enum` | 固定枚举字符串 | ComboBox |
| `array` | 字符串列表、简单对象列表 | 后续小步 |
| `object` | 简单对象分组 | 后续小步 |

第一版暂不支持：

| 类型 | 原因 |
| --- | --- |
| `table-selector` | 依赖运行时数据和当前 workflow 上下文 |
| `field-selector` | 依赖输入表 schema，不能只靠静态 NodeDefinition 得出 |
| `file-path` / `directory-path` | 涉及本机外部资源访问、用户确认和跨平台 UI 体验 |
| `secret` | 涉及脱敏、持久化和节点侧安全策略 |
| `regex` 专用控件 | 可先作为普通 string |
| 条件显示 / 动态联动 | 需要单独 UI 状态协议 |

## 5. 内置节点第一版字段草案

### GenerateTestTableNode

当前运行时读取：

```text
rows: integer, required, non-negative
seed: integer, optional, default 0, non-negative
columns: array, optional, default ["row_id", "amount"]
```

第一版建议：

```text
rows
seed
columns
```

其中 `columns` 当前支持字符串列表和对象列表：

```text
["row_id", "amount"]
[
  {"name": "row_id", "data_type": "INTEGER", "nullable": false, "field_id": "row_id"}
]
```

建议 NODE-CONFIG-SCHEMA-1 先以只读 schema 暴露该事实，不急于要求 Avalonia 表单完整编辑对象列表。

### FilterRowsNode

当前运行时读取：

```text
field: string, required
operator: enum, required
value: any, optional
```

支持 operator：

```text
EQ
NE
GT
GE
LT
LE
CONTAINS
IS_NULL
```

注意：

```text
field
```

最终应来自输入表 schema，但第一版 `config_schema` 只能静态描述为 string，不能承诺字段下拉选择。

### PublishSharedTablesNode

当前运行时读取：

```text
share_name: string, required
export_names: string[], required
retention_seconds: integer, optional, positive
```

注意：

```text
export_names
```

需要与 `input_refs` 数量一致。该约束依赖 workflow 连接关系，不能只靠静态 schema 完整表达。NODE-CONFIG-SCHEMA-1 可以先暴露字段类型和基础必填，复杂一致性仍由运行时/后续 workflow validation 处理。

### ReadSharedTablesNode

当前运行时读取：

```text
share_name: string, required
version_policy: enum, required
exact_version: integer, optional
selected_members: string[], optional
```

`version_policy` 建议枚举值以后端 `SharedTableVersionPolicy` 为准。

## 6. 校验边界

第一版应明确区分三层校验：

| 层级 | 职责 |
| --- | --- |
| Schema 结构校验 | `NodeDefinitionSpec.config_schema` 本身是否合法 |
| Workflow draft 校验 | 节点 config 是否满足静态字段类型、必填、枚举、基础范围 |
| 节点运行时校验 | 依赖输入表、共享表版本、权限、运行时数据的动态校验 |

NODE-CONFIG-SCHEMA-1 可以先只落：

```text
Schema 结构校验
API 返回字段
API 测试
Avalonia DTO 测试
```

是否把 `config_schema` 接入 `validate_workflow_definition()`，建议作为 NODE-CONFIG-SCHEMA-2 或 WORKFLOW-VALIDATION-SCHEMA-1 单独小步，不在 NODE-CONFIG-SCHEMA-1 偷做。

原因：

* 当前 workflow validation 还没有 config 校验结构。
* 直接加入 config 校验会影响现有工作流保存和运行入口。
* 部分约束依赖输入表或连接关系，不能和静态 schema 混在一起。

## 7. API 边界

`GET /api/v1/node-definitions` 后续建议新增字段：

```json
{
  "node_type": "GenerateTestTableNode",
  "node_version": "1.0",
  "display_name": "Generate Test Table",
  "input_ports": [],
  "output_ports": [
    {"name": "out", "required": false}
  ],
  "execution_mode": "PROCESS_POOL",
  "default_timeout_seconds": 60,
  "retry_safe": false,
  "ui_visibility": "visible",
  "config_schema_version": "1.0",
  "config_schema": {
    "type": "object",
    "properties": {}
  }
}
```

仍然不返回：

```text
implementation_path
Python callable
executor class
内部 dataclass 原始序列化
```

## 8. Avalonia 边界

NODE-CONFIG-SCHEMA-1 之后，Avalonia 可先增加 DTO 字段：

```text
ConfigSchemaVersion
ConfigSchema
```

但 `UI-SCHEMA-0` 之前，Avalonia 不应：

* 生成配置表单。
* 自动修改 `WorkflowDefinitionDraftJson`。
* 保存节点配置。
* 根据 schema 添加节点。
* 做字段选择器或表选择器。

第一步 UI 只能做：

```text
接收 schema
解析 schema 是否存在
展示只读摘要
对未知 schema 保持兼容
```

## 9. 不做事项

NODE-CONFIG-SCHEMA-0 / 1 明确不做：

* 不实现 Avalonia 动态表单。
* 不实现节点添加/删除。
* 不实现拖拽画布。
* 不实现字段选择器。
* 不实现表选择器。
* 不实现插件 schema 扫描。
* 不改变现有 Workflow Save / Validate / revision conflict 流程。
* 不改变节点运行时 config 校验行为。
* 不把测试节点 Fault / Delay 暴露给普通 UI。

## 10. 建议执行顺序

```text
NODE-CONFIG-SCHEMA-1
1. 增加后端 ConfigSchema 最小类型模型。
2. 给 NodeDefinitionSpec 增加 config_schema_version / config_schema。
3. 给四个普通可见内置节点补最小 schema。
4. NodeDefinitionView 显式映射新增字段。
5. 后端 API 测试确认返回字段。
6. 后端 API 测试确认不返回 implementation_path。
7. Avalonia NodeDefinitionDto 增加只读字段。
8. Avalonia API Client 测试确认反序列化。
```

后续：

```text
UI-SCHEMA-0
只读解析 schema 摘要。

UI-NODE-CONFIG-1
展示节点配置只读预览。

UI-NODE-CONFIG-2
最小通用配置表单草稿。

WORKFLOW-EDIT-1
配置草稿同步到 WorkflowDefinitionDraftJson，并继续走 Validate / Save。
```

## 11. 验收标准

NODE-CONFIG-SCHEMA-0 完成标准：

* 当前后端和 Avalonia 实现事实已复核。
* 明确第一版 schema 字段、类型和不做事项。
* 明确四个普通内置节点的 config 字段草案。
* 明确不在本阶段实现 API 字段。
* 明确下一步 NODE-CONFIG-SCHEMA-1 的实施顺序。
