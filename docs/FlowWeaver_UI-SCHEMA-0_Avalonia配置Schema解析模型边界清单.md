# FlowWeaver UI-SCHEMA-0：Avalonia 配置 Schema 解析模型边界清单

> 文档状态：UI-SCHEMA-0 边界分析完成
> 当前阶段：只确认 Avalonia schema 解析模型、失败回退和后续渲染边界
> 不适用范围：动态配置表单、workflow definition 写回、节点新增删除、画布编辑、字段选择器、表选择器

## 1. 阶段目标

`NODE-CONFIG-SCHEMA-1` 已经让后端 `GET /api/v1/node-definitions` 返回：

```text
config_schema_version
config_schema
```

`UI-SCHEMA-0` 的目标不是立刻生成表单，而是先固定 Avalonia 端如何理解这份 schema：

* 解析 FlowWeaver 最小 schema 子集。
* 对未知字段、未知版本和缺失 schema 保持兼容。
* 为后续只读摘要、通用表单和专用节点编辑器提供共同模型。
* 明确哪些能力必须后置，避免 UI 提前承诺后端或运行时还没有稳定的语义。

## 2. 当前实现事实

后端已经具备：

* `NodeDefinitionSpec.config_schema_version`
* `NodeDefinitionSpec.config_schema`
* `NodeDefinitionView.config_schema_version`
* `NodeDefinitionView.config_schema`
* 四个普通内置节点的第一版 schema。

Avalonia 当前具备：

* `NodeDefinitionDto.ConfigSchemaVersion`
* `NodeDefinitionDto.ConfigSchema`
* `NodeDefinitionListItemViewModel`
* `NodeEditorRegistry`
* `NodeEditorResolver`
* `BuiltinNodeEditors`

Avalonia 当前尚未具备：

* schema 解析模型。
* schema 字段摘要 ViewModel。
* schema 到控件的映射。
* config 草稿对象模型。
* schema 与 `WorkflowDefinitionDraftJson` 的写回边界。

## 3. 建议模型位置

后续 `UI-SCHEMA-1` 可新增：

```text
Avalonia_UI/Models/NodeConfigSchemaDescriptor.cs
Avalonia_UI/Models/NodeConfigFieldDescriptor.cs
Avalonia_UI/Models/NodeConfigFieldType.cs
Avalonia_UI/Models/NodeConfigSchemaParseResult.cs
Avalonia_UI/Models/NodeConfigSchemaParser.cs
```

原因：

* schema 是 UI 领域模型，不属于 HTTP DTO。
* `Models` 目录已有 Shell、NodeEditor、Settings 等轻量协议模型。
* ViewModel 和后续控件可共同消费解析后的 descriptor。
* 测试可以先覆盖 parser，不依赖 Avalonia 视觉树。

暂不建议放在：

| 位置 | 原因 |
| --- | --- |
| `Api` | 会把后端传输对象和 UI 解释逻辑混在一起 |
| `ViewModels` | parser 不应依赖页面状态 |
| `Services` | 第一版不需要 IO、生命周期或注入边界 |
| `Views` | 还没有进入渲染阶段 |

## 4. 第一版解析字段

`NodeConfigSchemaDescriptor` 建议只承接：

```text
Version
Type
Fields
Warnings
IsSupported
```

`NodeConfigFieldDescriptor` 建议只承接：

```text
Name
Type
Title
Required
DefaultValue
Minimum
EnumValues
ItemType
Description
Warnings
```

`NodeConfigFieldType` 建议枚举：

```text
String
Integer
Number
Boolean
Enum
Array
Object
Unsupported
```

注意：

* `DefaultValue` 先保留为 `JsonElement?` 或只读字符串摘要，不提前转成强类型编辑值。
* `Object` 和 `Array` 第一版可解析但不直接承诺可编辑。
* `Unsupported` 必须保留，后端未来扩展字段时 UI 不应崩溃。

## 5. 解析规则

第一版建议规则：

| 输入情况 | 解析结果 |
| --- | --- |
| `config_schema` 为 null | `IsSupported=false`，提示无配置 schema |
| `config_schema_version` 为空 | `IsSupported=false`，提示缺少版本 |
| `config_schema_version != "1.0"` | `IsSupported=false`，提示版本暂不支持 |
| `type != "object"` | `IsSupported=false`，提示根类型不支持 |
| `properties` 缺失或不是对象 | `IsSupported=true`，字段列表为空并记录 warning |
| 字段 `type` 缺失 | 字段类型为 `Unsupported` |
| 字段 `enum` 不是字符串数组 | 字段保留，记录 warning |
| 字段 `items.type` 缺失 | `ItemType` 为空，记录 warning |

解析失败原则：

```text
失败不抛到 UI 顶层。
失败不清空节点目录。
失败不阻止 Workflow 页面加载。
失败只影响该节点的 schema 摘要或后续配置表单可用性。
```

## 6. 后续只读摘要边界

`UI-SCHEMA-1` 或 `UI-NODE-CONFIG-1` 可在节点目录中展示只读摘要，例如：

```text
3 config fields
rows, seed, columns
```

但摘要展示必须满足：

* 不修改 `WorkflowDefinitionDraftJson`。
* 不启用保存按钮。
* 不暗示用户已经可以编辑节点配置。
* 对不支持 schema 显示可读回退，而不是隐藏节点。

## 7. 后续表单渲染边界

真正进入 `UI-NODE-CONFIG-2` 之前，不应实现：

* TextBox、ComboBox、CheckBox 等动态控件生成。
* config 草稿与 JSON 的双向绑定。
* 必填、枚举和范围的 UI 校验。
* workflow save 前的 config 静态校验。
* 复杂数组或对象编辑器。

后续控件映射建议：

| field type | 第一版控件方向 |
| --- | --- |
| `string` | TextBox |
| `integer` | Numeric input 或 TextBox 加解析 |
| `number` | Numeric input 或 TextBox 加解析 |
| `boolean` | CheckBox |
| `enum` | ComboBox |
| `array` | 暂只读摘要或 JSON fallback |
| `object` | JSON fallback |
| `unsupported` | JSON fallback |

## 8. 专用编辑器关系

Schema 通用表单和专用节点编辑器不是同一个层次。

建议顺序：

```text
NodeEditorResolver
1. 有专用 editor 时，使用专用 editor。
2. 没有专用 editor 但 schema 可支持时，使用通用 schema editor。
3. schema 不支持或解析失败时，回退 JSON editor。
```

当前 `NodeEditorRegistry` 已有专用编辑器注册雏形，`UI-SCHEMA-0` 不改变它，只为后续 resolution 增加通用 schema editor 的位置。

## 9. Gemini 视图协作边界

如需让 Gemini 后续改 View 层，应先提供这些输入：

* schema 字段只读摘要 ViewModel 名称。
* 是否只展示字段数量和字段名。
* 不要求实现动态表单。
* 不要求编辑 workflow JSON。
* 不要求改变 Workflow 页面布局主结构。

第一份给 Gemini 的任务建议是：

```text
只在节点目录或节点详情区域增加只读 schema 摘要展示，
不要新增动态编辑控件，
不要改 Command / Save / Validate 行为。
```

## 10. UI-SCHEMA-0 验收标准

本阶段完成标准：

* 明确 Avalonia schema 解析模型位置。
* 明确第一版 descriptor 字段。
* 明确缺失、未知版本、未知字段类型的回退策略。
* 明确专用编辑器、通用 schema editor、JSON fallback 的关系。
* 明确后续 UI 视图协作边界。
* 不改 Avalonia 代码。
* 不实现动态表单。
* 不改变 workflow 保存和校验。

## 11. 建议下一步

```text
UI-SCHEMA-1：
新增 Avalonia schema 解析模型和 parser 测试，
只解析 NodeDefinitionDto.ConfigSchema，
不生成 UI 表单。
```

之后再进入：

```text
UI-NODE-CONFIG-1：
基于解析结果展示只读节点配置摘要。

UI-NODE-CONFIG-2：
评估最小通用配置表单草稿。
```
