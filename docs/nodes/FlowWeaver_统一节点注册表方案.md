# FlowWeaver 统一节点注册表方案

更新时间：2026-07-06

## 文档定位

本文是节点体系规划草案，用来先记录“统一注册表 + 插件来源区分 + 执行懒加载”的方向。

后续可以继续补充细节，也可以做减法。当前不直接要求实现代码。

## 核心结论

节点可以统一注册。

统一注册不代表所有节点都混在一起，也不代表主程序要知道每个节点的业务逻辑。推荐做法是：

```text
NodeRegistry 统一保存所有节点定义
PluginCatalog 记录节点来自哪个插件或节点包
ExecutorFactory 在真正运行时加载对应实现
```

这样主程序只面对一套节点目录，仍然可以清楚地区分：

- 核心内置节点
- 官方自带插件节点
- 用户安装插件节点
- 开发测试节点
- 禁用节点
- 隐藏节点
- 版本冲突节点

## 统一注册表的含义

统一注册表只负责回答：

```text
当前系统有哪些节点可以被识别、展示、校验和运行
```

它不应该负责：

- 执行节点业务逻辑
- 导入所有插件代码
- 管理外部程序生命周期
- 处理节点内部资源
- 为某个节点写特殊判断

也就是说，`NodeRegistry` 是节点目录，不是节点执行中心。

## 第一版建议保留的 12 个参数

第一版节点定义建议先固定 12 个核心参数。

这 12 个参数用于完成：

- 统一注册
- 插件来源区分
- UI 分类展示
- Workflow 校验
- 节点配置生成
- 执行入口定位

暂时不要把字段扩得太细，避免还没接入节点就把协议做重。

| 字段 | 作用 |
| --- | --- |
| `node_type` | 全局唯一节点类型 |
| `node_version` | 节点版本 |
| `plugin_id` | 来自哪个插件、节点包或核心包 |
| `provider_type` | 节点来源类型，例如 `core`、`bundled_plugin`、`user_plugin`、`dev_test` |
| `category` | UI 分类 |
| `ui_visibility` | 是否展示给普通用户 |
| `enabled` | 当前是否启用 |
| `display_name` | UI 显示名 |
| `config_schema` | 通用配置表单依据 |
| `input_ports` | 工作流输入端口，用于连接和必填输入校验 |
| `output_ports` | 工作流输出端口，用于连接和下游输入校验 |
| `implementation_ref` | 内部执行入口引用，由执行器工厂用来定位节点实现 |

对应第一版结构可以先理解为：

```text
node_type
node_version
plugin_id
provider_type
category
ui_visibility
enabled
display_name
config_schema
input_ports
output_ports
implementation_ref
```

### 参数说明

| 参数 | 通俗说明 | 是否给普通 UI |
| --- | --- | --- |
| `node_type` | 节点的机器名，系统用它识别“这是哪个节点”。 | 是 |
| `node_version` | 节点版本，用来处理升级和兼容。 | 是 |
| `plugin_id` | 节点来自哪个核心包、插件或节点包。 | 是 |
| `provider_type` | 节点来源类型，例如核心、插件、用户安装、开发测试。 | 是 |
| `category` | 节点在 UI 里放到哪个分类。 | 是 |
| `ui_visibility` | 节点是否显示给普通用户，例如 `visible`、`hidden`、`dev_only`。 | 是 |
| `enabled` | 节点当前是否启用。 | 是 |
| `display_name` | 用户看到的节点名称。 | 是 |
| `config_schema` | 节点有哪些配置项，UI 可用它生成配置表单。 | 是 |
| `input_ports` | 节点需要哪些输入。 | 是 |
| `output_ports` | 节点会产生哪些输出。 | 是 |
| `implementation_ref` | 内部执行入口引用，用来找到真正处理节点的代码。 | 否 |

第一版可以不一次性补齐全部字段，但字段方向应保持一致。

### 暂时后置的字段

下面这些字段可以后续再讨论，不建议第一版强行纳入核心 12 参数：

| 字段 | 后置原因 |
| --- | --- |
| `config_schema_version` | 第一版可以先默认 `1.0`，等 schema 迁移需求明确后再细化。 |
| `default_timeout_seconds` | 可以先沿用全局默认超时。 |
| `retry_safe` | 等重试策略和副作用分类更清楚后再加入。 |
| `execution_mode` | 等 `ExecutorFactory` 和独立运行环境方案收口后再细化。 |
| `aliases` | 等真的需要重命名 `node_type` 时再做。 |
| `deprecated` | 等节点废弃和迁移策略明确后再做。 |

## 内置节点也按插件方式表达

内置节点不需要走另一套特殊机制。

可以把内置节点视为一个特殊来源：

```text
plugin_id = flowweaver.core
provider_type = core
```

测试节点也可以有明确来源：

```text
plugin_id = flowweaver.dev_test
provider_type = dev_test
ui_visibility = hidden 或 dev_only
```

这样后续迁移到插件体系时，不需要重新推翻节点注册模型。

## 物理目录和逻辑注册

推荐采用：

```text
物理目录可以分开
逻辑目录统一注册
```

也就是说，不同来源的节点可以放在不同目录里，但主程序识别节点时仍然全部进入统一 `NodeRegistry`。

示例目录可以是：

```text
nodes/core/
nodes/dev_test/
plugins/dataflowkit/
plugins/other_plugin/
```

这些目录只表示文件存放位置，不应该变成主程序判断节点类型的依据。

真正决定节点是什么、显示在哪里、能不能用、怎么加载的，应是节点定义元数据：

```text
node_type
node_version
plugin_id
provider_type
category
ui_visibility
enabled
display_name
config_schema
input_ports
output_ports
implementation_ref
```

例如：

```text
plugin_id = flowweaver.core
category = table
node_type = GenerateTestTableNode

plugin_id = dataflowkit.table
category = table
node_type = DeleteRowsNode

plugin_id = dataflowkit.file
category = file
node_type = ListFilesNode
```

UI 看到的是统一节点目录，再按 `category`、`plugin_id`、`provider_type`、`ui_visibility` 和 `enabled` 做分组、过滤和展示。

结论是：

```text
不要按目录决定节点是什么。
目录只负责存放。
节点是什么、显示在哪里、能不能用，应由节点定义元数据决定。
```

第一版可以先保留不同来源目录，例如 `core`、`dev_test`、`plugin`，但启动时全部读取轻量定义并注册进统一 `NodeRegistry`。

## 推荐运行链路

```text
启动主程序
→ 读取核心节点和插件 manifest
→ 注册轻量节点定义到 NodeRegistry
→ UI 从 NodeRegistry 读取节点目录
→ Workflow 校验使用 NodeRegistry
→ WorkflowRunProcess 创建 NodeTask
→ ExecutorFactory 根据 implementation_ref 找到实现
→ 真正执行时再加载节点代码
```

主程序在运行链路里只需要知道节点契约，不需要知道节点具体怎么处理数据。

## implementation_ref 的含义

`implementation_ref` 不是 UI 参数，也不是用户在节点配置里填写的业务字段。

它是内部执行入口引用，用来告诉 `ExecutorFactory`：

```text
这个 node_type 真正由哪个实现处理
```

第一版可以把它理解为“指向某个 Python 节点实现入口”的字符串，例如：

```text
flowweaver.nodes.builtin_table:GenerateTestTableRunner
dataflowkit.table.delete_rows:DeleteRowsNode
dataflowkit.file.list_files:ListFilesNode
```

但它不一定永远只是“调用一个函数”。更准确的定位是：

```text
ExecutorFactory 根据 implementation_ref 找到节点实现
再由节点实现处理 NodeTask
最后返回 NodeTaskResult
```

第一版最简单可以是：

```text
implementation_ref → Python module:callable
ExecutorFactory → import 对应模块
ExecutorFactory → 创建或调用节点实现
节点实现 → 接收 NodeTask / NodeExecutionContext / 数据访问服务
节点实现 → 返回 NodeTaskResult，并按需上报 progress / heartbeat
```

后续它也可以扩展为其他形式：

| 形式 | 说明 |
| --- | --- |
| Python 函数 | 最简单，适合轻量节点 |
| Python 类 | 适合有初始化、依赖注入或状态封装的节点 |
| 节点包入口 | 由插件或节点包统一暴露执行入口 |
| 外部程序包装器 | 节点实现内部拉起外部程序 |
| 独立进程执行器 | 后续如果需要更强隔离，可由执行器进程加载 |

无论哪种形式，`implementation_ref` 都应保持为内部字段：

- 普通节点目录 API 默认不返回它。
- UI 不依赖它。
- workflow 定义不直接填写它。
- 用户不能通过它注入任意代码路径。
- 它只由可信 manifest、内置注册表或已安装节点包提供。

节点业务参数仍然走 `config_schema` 和 `NodeTask.config`，不要混进 `implementation_ref`。

## 性能影响分析

统一注册本身性能影响很小。

真正影响性能的通常不是“是否统一注册”，而是“注册时做了多少事”。

| 情况 | 性能影响 | 建议 |
| --- | --- | --- |
| 只注册节点元数据 | 很小 | 推荐 |
| 启动时读取插件 manifest | 较小 | 推荐 |
| 启动时导入所有插件代码 | 可能明显变慢 | 避免 |
| 启动时生成大量复杂 schema | 可能变慢 | 缓存或懒生成 |
| 每次打开节点列表都重新扫描插件目录 | 会变慢 | 避免，改为启动扫描或缓存 |
| 节点执行前才加载对应实现 | 较理想 | 推荐 |
| API 一次返回大量完整 schema | UI 可能变慢 | 后续可分页、分类或按需加载 |

第一阶段建议：

```text
启动时只加载 manifest 和节点定义
执行时再加载节点实现
UI 先读取轻量节点列表
需要配置时再读取完整 config_schema
```

## 与主程序防耦合的关系

统一注册表可以减少主程序耦合。

关键点是：

- 主程序只知道节点定义，不知道节点业务
- UI 只读节点定义，不写死节点
- 执行器工厂只按实现引用加载，不在主程序里写大量 `if node_type`
- 插件来源、启用状态和隐藏状态都走元数据
- 测试节点和正式节点可以注册在同一套表里，但通过 `provider_type` 区分

这样新增节点时，理想流程是新增节点包或插件清单，而不是修改 EngineHost、WorkflowRunProcess 或 MainWindowViewModel。

## 初步模块分工

| 模块 | 职责 |
| --- | --- |
| `NodeRegistry` | 统一节点目录，按 `node_type + node_version` 查询节点定义 |
| `PluginCatalog` | 记录插件来源、启用状态、版本、路径和加载策略 |
| `NodeDefinition` | 描述节点输入、输出、配置、显示和来源信息 |
| `ExecutorFactory` | 根据节点定义里的实现引用，找到并创建执行器 |
| UI | 读取节点定义并生成节点目录、配置入口和显示文本 |
| Workflow 校验 | 根据节点定义校验节点存在、端口和连接关系 |

## 后续可减法点

后续讨论时可以继续删减：

- 是否第一版就需要 `PluginCatalog`
- `implementation_ref` 是否先只支持 Python 内部路径
- `provider_type` 是否只保留 `core`、`plugin`、`dev_test`
- `ui_visibility` 是否先只做 `visible` / `hidden`
- 是否先不做插件热加载
- 是否先不做插件卸载
- 是否先不做插件市场或安装器
- 是否先不做节点 schema 按需加载

## 当前暂定方向

当前建议方向是：

1. 统一 `NodeRegistry`，不要为内置节点和插件节点做两套注册。
2. 内置节点也按 `flowweaver.core` 这种来源注册。
3. 插件节点通过元数据区分来源、启用状态和显示状态。
4. 不同来源可以有不同物理目录，但逻辑上全部进入统一 `NodeRegistry`。
5. 启动时只加载轻量定义，不导入所有插件实现。
6. 真正执行节点时，由 `ExecutorFactory` 根据 `implementation_ref` 懒加载对应实现。
7. UI 和 Workflow 校验只依赖节点定义，不写死具体节点。

这样可以在不明显增加性能负担的前提下，为后续插件化和节点扩展留出空间。

## 当前代码现状与差距

当前主程序已经具备统一注册表的第一层基础，但还没有完成插件来源和执行懒加载的完整闭环。

### 已具备的基础

- `NodeRegistry` 已经按 `node_type + node_version` 保存和查询节点定义。
- `NodeDefinitionSpec` 已包含 `node_type`、`node_version`、`display_name`、端口、执行模式、默认超时、重试安全、`config_schema_version` 和 `config_schema`。
- `GET /api/v1/node-definitions` 已经通过显式 `NodeDefinitionView` 返回节点定义，而不是直接暴露内部 dataclass。
- Avalonia 端已有 `NodeDefinitionDto`，可以读取节点目录、端口、可见性和配置 schema。
- Workflow 校验已经依赖 `NodeRegistry` 判断节点是否存在、端口和连接关系是否合法。
- 默认注册表已经集中注册当前内置节点和测试节点。

### 主要差距

| 差距 | 当前状态 | 需要补齐 |
| --- | --- | --- |
| 来源信息 | `NodeDefinitionSpec` 暂无 `plugin_id`、`provider_type`、`category`、`enabled` | 增加来源和启用状态元数据 |
| UI 可见性 | API 当前固定返回 `ui_visibility = visible`，并用 `BUILTIN_FAULT_NODE_TYPES` 硬编码过滤测试节点 | 改为由节点定义元数据决定是否展示 |
| 执行实现引用 | 当前没有正式执行入口引用字段 | 新增内部 `implementation_ref`，不要再引入 `implementation_path` |
| API 安全边界 | API 当前不返回内部执行入口信息 | 后续也应默认不暴露 `implementation_ref` 或本地插件路径，只返回 UI 安全字段 |
| 执行器选择 | `WorkflowProcess` 当前仍按 `is_table_node_type()`、`is_shared_table_node_type()` 和故障节点常量分流 | 逐步迁移到 registry-backed `ExecutorFactory` |
| 插件 manifest | 尚无正式 manifest 格式 | 定义最小 manifest 字段和校验失败语义 |
| 禁用节点 | 尚无统一 `enabled=false` 语义 | 明确新增、校验、运行三处行为 |
| 兼容迁移 | 现有工作流仍使用 `GenerateTestTableNode` 等旧 node_type | 第一版不重命名；未来如改名需 alias / migration / deprecation 机制 |

### 需要特别保持的边界

- `implementation_ref` 属于内部执行信息，默认不应通过普通节点目录 API 返回给 UI。
- 测试节点应继续可注册、可用于验收，但默认不出现在普通 UI 节点选择器中。
- 统一注册表不应把权限审计、权限句柄或旧 audit 设计重新引回主程序。
- 第一版不应要求插件热加载、插件卸载、插件市场或外部沙箱能力。

## 第一版最小落地范围

第一版建议只做“统一元数据 + API 契约 + 执行迁移前置”，不要一次性实现完整插件系统。

### 1. 扩展内部 NodeDefinitionSpec

建议在 `NodeDefinitionSpec` 上按第一版 12 参数收口：

```text
node_type: str
node_version: str
plugin_id: str
provider_type: core | bundled_plugin | user_plugin | dev_test
category: str | None
ui_visibility: visible | hidden | dev_only
enabled: bool
display_name: str
config_schema: NodeConfigSchemaSpec | None
input_ports: tuple[NodePortSpec, ...]
output_ports: tuple[NodePortSpec, ...]
implementation_ref: str | None
```

其中：

- 内置正式节点默认 `plugin_id = flowweaver.core`，`provider_type = core`，`ui_visibility = visible`，`enabled = true`。
- 测试节点默认 `plugin_id = flowweaver.dev_test`，`provider_type = dev_test`，`ui_visibility = hidden` 或 `dev_only`。
- 第一版可以先不实现 `bundled_plugin` / `user_plugin` 的真实安装，只保留字段和校验。
- `implementation_ref` 只供内部执行器工厂使用，不进入普通 UI，也不由 workflow 直接填写。

### 2. 分离内部定义和公开 API DTO

普通节点目录 API 只返回 UI 安全字段：

```text
node_type
node_version
plugin_id
provider_type
category
ui_visibility
enabled
display_name
config_schema 或 schema 摘要
input_ports / output_ports
```

默认不返回：

```text
implementation_ref
插件本地绝对路径
加载入口内部对象名
```

如果未来需要调试接口，应单独做开发模式或管理员接口，不混入普通 UI API。

### 3. 拆分轻量列表和完整定义

建议保留现有：

```text
GET /api/v1/node-definitions
```

作为普通节点目录列表。后续可增加：

```text
GET /api/v1/node-definitions/{node_type}/{node_version}
```

用于读取单个节点完整配置 schema 和更多说明。

可选查询参数建议预留：

```text
provider_type
category
include_hidden
include_disabled
schema_mode = summary | full
```

第一版可以只实现默认列表，不急于增加全部查询参数，但文档和测试应固定默认行为。

### 4. 用元数据替代测试节点硬编码过滤

当前测试节点过滤不应长期依赖 node_type 常量。迁移方向：

```text
NodeDefinitionSpec.ui_visibility = hidden/dev_only
NodeDefinitionSpec.provider_type = dev_test
GET /api/v1/node-definitions 默认只返回 visible 且 enabled 的节点
开发/验收接口可显式 include_hidden=true
```

这样新增测试节点时，不需要再改 API 路由里的特殊判断。

### 5. 执行器迁移分阶段进行

执行器迁移建议分三步，不要一次性替换：

1. 保留当前 `is_table_node_type()` / `is_shared_table_node_type()` / fault 常量分流。
2. 在默认注册表中为这些节点补齐 `implementation_ref`。
3. 新增 `ExecutorFactory`，先用 registry 查定义，再 fallback 到旧分流。
4. 所有正式路径测试通过后，再逐步删除旧分流硬编码。

第一版验收重点是“不破坏现有运行”，不是立刻消灭所有旧判断。

### 6. 明确禁用节点语义

建议统一规则：

- `enabled = false` 的节点不出现在普通新增节点列表。
- 已存在工作流如果引用禁用节点，详情页可以显示，但应提示不可运行。
- Workflow 校验应返回明确错误，例如 `NODE_DISABLED`。
- 运行前如果仍发现禁用节点，应拒绝启动，而不是执行到一半失败。

### 7. 保持 node_type 兼容

第一版不建议重命名现有 node_type。

现有工作流继续使用：

```text
GenerateTestTableNode
FilterRowsNode
PublishSharedTablesNode
ReadSharedTablesNode
DelayTestNode
FaultTestNode
```

如果未来改为更稳定的命名，例如 `flowweaver.core.generate_table`，需要先设计：

- `aliases`
- 旧 workflow revision 的迁移规则
- API 显示名和内部 machine id 的对应关系
- deprecation 提示
- 回滚策略

## 验收清单

第一版最小验收建议如下。

### 后端注册表

- `NodeRegistry` 仍按 `node_type + node_version` 唯一注册。
- 重复注册同一 `node_type + node_version` 会拒绝。
- 默认内置正式节点带有 `plugin_id = flowweaver.core`。
- `DelayTestNode` / `FaultTestNode` 带有 `provider_type = dev_test`，默认不可见。
- `enabled=false` 的定义可被注册，但 Workflow 校验能识别并拒绝运行。

### API 契约

- `GET /api/v1/node-definitions` 默认只返回普通 UI 可见节点。
- API 不返回 `implementation_ref` 或本地插件路径。
- API 返回 `plugin_id`、`provider_type`、`category`、`ui_visibility`、`enabled` 等安全元数据。
- 缺少 token 时仍按现有鉴权规则拒绝。
- 现有 Avalonia `ListNodeDefinitionsAsync` 能继续解析响应。

### UI 行为

- 节点目录默认不显示测试节点。
- 新增节点下拉只显示 `visible && enabled` 的节点。
- 已存在工作流如果引用隐藏节点，可以显示节点本身，但不要把它当作普通新增候选。
- 禁用节点应有可读提示，不应静默消失。
- 没有完整 schema 时，UI 仍可回退到 JSON 配置入口。

### Workflow 校验

- 未注册节点返回明确未知节点错误。
- 禁用节点返回明确禁用节点错误。
- 端口校验继续使用注册表中的 `input_ports` / `output_ports`。
- 现有正式工作流仍可校验通过。
- preview-to-node 不因新增来源字段而改变语义。

### 执行链路

- 现有 `GenerateTestTableNode`、`FilterRowsNode`、`PublishSharedTablesNode`、`ReadSharedTablesNode` 正式运行不回退。
- `DelayTestNode` / `FaultTestNode` 仍可用于后端验收路径，但不进入普通 UI。
- 第一版引入 `ExecutorFactory` 时，应有 fallback，避免一次性破坏现有执行分流。
- 执行实现懒加载失败时，应返回明确错误，不能让 WorkflowRun 长时间卡住。

### 兼容与迁移

- 已保存 workflow revision 不需要立即迁移 node_type。
- 新字段应有默认值，旧测试和旧数据库数据不应因为缺少字段崩溃。
- 后续如引入 manifest，应先支持核心内置 manifest，再支持外部插件 manifest。
- 插件 manifest 校验失败时，应记录错误并跳过对应插件，不影响核心节点启动。
