# 2026-07-12 当前阶段：FlowWeaver PLUGIN-RUNTIME-1 插件发现与外部进程最小执行闭环执行计划

> 文档状态：待执行
>
> 当前边界：阶段 Q 第一版已经冻结；本计划不继续扩充内置业务节点，而是补齐插件发现、可信清单、外部进程执行、引用流转、运行反馈、生命周期和 UI 状态闭环
>
> 执行原则：每完成一批先跑定向测试，再使用中文提交并推送；前一批未达到停止条件，不进入下一批

## 0. 当前结论

当前不建议继续批量增加内置节点。

阶段 Q 文档和当前默认注册表已经形成 41 个内置节点的第一版基线，表流转、结果绑定、后台运行、配置字动态反馈、共享表和生命周期基础也已经冻结。后续若继续把单个算法、单个外部工具或单个业务系统适配做成内置节点，主程序会逐步承担插件依赖、业务分支、特殊 UI 和特殊生命周期，确实会越来越臃肿。

当前最需要补的不是更多内置业务功能，而是一条通用插件执行主线：

```text
固定插件目录
-> 只读取可信 manifest
-> 注册轻量节点定义
-> 工作流按通用入口选择插件执行器
-> 外部进程执行插件
-> 只传引用和小控制消息
-> 结果重新登记为 FlowWeaver 标准引用
-> 复用现有日志、进度、心跳、取消、超时和配置字动态切换
```

第一版只完成 `external_process`。不实现 `in_process`，不让主程序导入插件业务代码，也不为某个 `plugin_id` 增加专用分支。

## 1. 当前源码审计

### 1.1 已经具备的插件占位能力

| 当前文件 | 已实现内容 | 当前边界 |
| --- | --- | --- |
| `src/flowweaver/nodes/plugin_table_node.py` | 读取插件配置、调用清单校验、发布状态表 | 不发现插件、不加载插件、不执行插件 |
| `src/flowweaver/nodes/plugin_manifest_state.py` | 校验插件 ID、版本、必填参数、输入输出绑定、执行模式和外部动作声明 | 校验对象来自节点配置中的 `plugin_manifest` 草稿，不是已安装插件目录的可信清单 |
| `src/flowweaver/nodes/plugin_manifest_validation.py` | 生成 `execution_ready`、`validation_status` 和跳过原因 | 即使 `execution_ready=true`，仍固定 `actual_execute=false` |
| `src/flowweaver/nodes/default_plugin_resource_node_schemas.py` | 暴露插件 ID、版本、参数、绑定、执行模式、外部动作和执行开关 | 仍暴露 `in_process`，且 `plugin_manifest` 还是普通节点配置字段 |
| `src/flowweaver/nodes/default_resource_definitions.py` | 注册 `PluginNode`，输入端口为可选 `in`，输出端口只有 `status` | 还不能表达真实插件输出和禁用原因 |
| `tests/integration/test_builtin_table_nodes.py` | 覆盖占位状态表、外部动作阻断和未启用执行 | 当前测试明确断言插件不会真实执行 |

当前真实状态是：

```text
PluginNode = 可配置 + 可校验 + 可输出占位状态
PluginNode != 插件发现器
PluginNode != 插件加载器
PluginNode != 插件执行器
```

### 1.2 当前执行路由存在的耦合点

`PluginNode` 当前被加入 `src/flowweaver/nodes/builtin_table_registry.py`，因此 `is_table_node_type()` 会把它识别为普通内置表节点。

`src/flowweaver/workflow_process/executor_owner.py` 当前先判断表节点，再返回 `BuiltinTableNodeExecutor`。这意味着插件占位逻辑目前运行在 `WorkflowRunProcess` 内的内置表执行路径，而不是独立插件进程路径。

占位校验阶段这样做没有问题，但真实插件执行不能继续沿用该边界，原因是：

- 内置表执行器没有插件发现和可信入口解析职责。
- 插件依赖不能进入 WorkflowRunProcess。
- 插件取消、超时、标准输出、标准错误和子进程清理需要独立故障域。
- 插件进程不能通过 `BuiltinTableNodeContext` 直接获得主程序内部对象。
- 后续若在表 handler 中按插件 ID 分流，会把主程序重新耦合到插件业务。

因此真实执行前必须把插件节点从“普通内置表 handler 执行”迁移为“注册表驱动的通用插件外部进程执行”。

### 1.3 可以直接复用的运行能力

当前不需要为插件重新设计第二套工作流协议。

| 已有能力 | 当前落点 | 插件侧复用方式 |
| --- | --- | --- |
| 节点任务标识和超时 | `NodeTaskModel` | 沿用 task、run、process、node、attempt 和 timeout 信息 |
| 输入引用 | `input_refs`、`input_slot_bindings` | 只传引用和槽位，不传整表 rows |
| 输出引用 | `NodeTaskResultModel.output_refs` | 插件输出经宿主校验后登记为标准引用 |
| 输出槽位 | `output_slot_bindings` | 校验输出槽位来自 manifest，且引用必须存在于 `output_refs` |
| 结果摘要和错误 | `summary`、`error` | 只保存有界摘要、指标和可修正错误 |
| 节点提交和终态 | `NODE_TASK_SUBMIT`、`NODE_TASK_COMPLETED`、`NODE_TASK_FAILED` | 复用现有 JSONL IPC 消息语义 |
| 节点日志 | `NODE_TASK_LOG` | 插件日志进入现有配置字过滤和长度限制 |
| 节点进度 | `NODE_TASK_PROGRESS` | 只表达业务进度，不代替心跳 |
| 节点心跳 | `NODE_TASK_HEARTBEAT` | 长任务低频上报活跃状态 |
| 动态配置字 | `NODE_TASK_RUNTIME_OPTIONS_UPDATE/APPLIED` | 运行中的插件接收当前反馈策略，不新增插件专用配置字 |
| 取消 | `NODE_TASK_CANCEL_REQUEST` | 先请求插件退出，超过宽限期后终止进程 |
| 工作流监督 | `WorkflowRunProcess`、`Supervisor` | 继续负责任务超时、工作流取消和终态处理 |
| 通用配置 UI | Avalonia 的节点目录、`config_schema` 解析和 JSON 回退 | 首版不做插件自定义 UI |

### 1.4 当前仍缺少的真实闭环

| 序号 | 未落实项 | 影响 |
| --- | --- | --- |
| 1 | 固定插件目录和非递归发现器 | 主程序不知道当前安装了哪些插件 |
| 2 | 可信 manifest 模型和路径约束 | 工作流配置仍可能携带不可信清单草稿 |
| 3 | 插件来源、启用状态和禁用原因 | UI 和工作流校验无法区分可执行、损坏、冲突或被禁用插件 |
| 4 | 注册表驱动的插件执行入口 | 当前仍由 `PluginNode` 内置表 handler 占位处理 |
| 5 | 外部进程 runner | `enable_execute=true` 仍不会启动任何插件 |
| 6 | 跨进程数据引用适配 | 外部插件不能安全解析输入表和输出目标 |
| 7 | 结果引用校验和发布 | 外部插件还不能产生可供下游节点使用的标准结果 |
| 8 | 日志、进度、心跳和动态配置字转发 | 插件运行反馈尚未接入现有降噪链路 |
| 9 | 取消、超时和进程树清理 | 插件异常时可能残留子进程 |
| 10 | 可执行参考插件和端到端测试 | 当前没有真实插件验收样板 |

### 1.5 当前进程硬兜底缺口

`tools/portable_launcher.py` 已经有 Windows Job Object 的应用级 kill-on-close 处理，但当前 `src/flowweaver/engine/supervisor_process_launch.py` 仍直接使用 `subprocess.Popen` 启动 WorkflowRunProcess，没有为单个 WorkflowRun 创建并持有独立 Job Object。

因此当前只能确认：

```text
关闭或强杀整个便携启动器
-> 可以兜底清理整个应用进程树
```

还不能确认：

```text
EngineHost 继续运行
单个后台 WorkflowRun 被取消、失败或强杀
-> 该工作流私有插件进程一定全部消失
```

真实外部插件上线前，必须补齐或验证单 WorkflowRun 进程树硬兜底。只做 `process.terminate()` 不能替代该验收。

## 2. 第一版目标与非目标

### 2.1 第一版必须完成

1. 固定一个插件根目录：`plugins/`。
2. 只扫描 `plugins/<package>/plugin.json`，不递归遍历任意目录。
3. 启动时只读取 manifest，不导入插件业务模块。
4. 将有效插件注册为统一节点目录中的插件来源节点。
5. 将无效、冲突或不可运行插件记录为禁用状态，并提供明确原因。
6. 第一版只允许 `external_process`。
7. 插件启动入口只来自已发现 manifest，不接受工作流配置提供任意命令或绝对路径。
8. 外部进程只接收引用、槽位、参数和有界控制消息。
9. 插件输出必须经过宿主校验并转成标准 `output_refs` 和 `output_slot_bindings`。
10. 复用现有日志、进度、心跳、配置字动态切换、取消和超时链路。
11. 完成单 WorkflowRun 的插件进程清理验收。
12. 使用一个无外部副作用的纯表转换插件完成端到端验收。

### 2.2 第一版明确不做

- 不做 `in_process`。
- 不做插件市场、在线下载、安装器、卸载器和自动更新。
- 不做热加载；插件目录变化后重启 EngineHost 才生效。
- 不做远程插件执行。
- 不做插件签名、证书链或信任商店。
- 不做任意插件自定义 Avalonia 页面或控件。
- 不做插件依赖解析和 Python 环境自动创建。
- 不做跨 WorkflowRun 的常驻插件进程复用。
- 不做共享内存、mmap、GPU handle、CUDA IPC 或 TensorRef。
- 不做全局 GPU 调度、端口调度或模型服务管理面板。
- 不给配置字增加插件专用字段。
- 不为单个插件向 EngineHost、WorkflowRunProcess 或 MainWindowViewModel 增加业务判断。

## 3. 防止主程序继续臃肿的固定规则

### 3.1 内置节点冻结规则

当前 41 个内置节点作为第一版核心基线。插件运行时实施期间，默认节点数量不得因为参考插件而增加。

只有同时满足以下条件的能力，后续才考虑成为内置节点：

- 属于工作流控制、数据引用、生命周期或通用基础设施。
- 与具体第三方库、模型、业务系统和文件格式无关。
- 至少被多个节点或多个插件共同依赖。
- 进入核心后能减少总体复杂度，而不是只减少某一个插件的代码量。

以下能力默认应做成插件：

- 单个 OCR、YOLO、CLIP、SAM 或大模型实现。
- 单个云服务、数据库产品、办公软件或业务系统适配。
- 单个复杂算法或特定行业处理流程。
- 需要额外大型依赖、独立 Python 环境或专有 SDK 的节点。
- 需要独立升级节奏的功能。

### 3.2 核心依赖门槛

- `pyproject.toml` 不得因为参考插件增加插件业务依赖。
- EngineHost 不得 import 插件实现模块。
- WorkflowRunProcess 不得 import 插件实现模块。
- Avalonia 不得引用插件程序集或业务模型。
- 插件运行失败不得阻止核心节点目录和核心 API 启动。
- 插件扫描不得执行插件顶层代码。

### 3.3 分支门槛

核心代码允许判断“这是插件来源节点”或“执行入口是通用外部插件 runner”，但不允许出现：

```text
if plugin_id == "某插件"
switch plugin_id
按某个插件名称选择依赖
按某个插件名称渲染 UI
```

插件差异只能由 manifest、节点配置和插件进程自身解释。

## 4. 第一版推荐结构

```text
EngineHost
├─ PluginDiscovery
│  └─ 只读取 plugins/*/plugin.json
├─ PluginCatalog
│  └─ 保存插件元数据、manifest 指纹、启用状态和禁用原因
└─ NodeRegistry
   ├─ 当前 41 个核心内置节点
   └─ manifest 转换出的插件节点定义

WorkflowRunProcess
└─ RegistryBackedExecutorOwner
   ├─ 现有内置表节点执行器
   ├─ 现有共享表节点执行器
   ├─ 现有默认节点执行器
   └─ PluginExternalProcessExecutor
      ├─ 解析可信插件描述
      ├─ 准备输入引用和输出暂存目标
      ├─ 启动插件外部进程
      ├─ 转发日志、进度、心跳、配置字和取消
      ├─ 校验终态和输出
      └─ 登记 NodeTaskResult
```

第一版建议采用“一次 NodeTask 对应一个插件进程”的保守生命周期：

```text
节点开始
-> 懒启动插件进程
-> 完成一次任务
-> 正常关闭插件进程
```

这样可以先把取消、超时、错误隔离和残留进程清理做实。重模型或高启动成本插件的 WorkflowRun 内复用，继续按现有《外部程序节点生命周期与复用方案》单独实施，不混入本轮最小闭环。

## 5. 职责边界

| 层级 | 负责 | 不负责 |
| --- | --- | --- |
| EngineHost | 固定目录、启动扫描、公开安全目录信息 | 导入插件、执行插件、解释插件业务 |
| PluginDiscovery | 找到 manifest、限制文件大小和路径、解析 JSON | 启动进程、访问 RuntimeStore、执行插件代码 |
| PluginCatalog | 冲突处理、启用状态、禁用原因、manifest 指纹 | 保存运行期状态、读取表数据 |
| NodeRegistry | 提供节点定义、端口、表槽位、配置 schema 和来源信息 | 保存插件绝对路径到公开 API、执行插件 |
| Workflow 校验 | 插件是否存在、启用、版本匹配、端口和配置是否合法 | 自动安装插件、猜测插件参数 |
| PluginExternalProcessExecutor | 运行前复核、准备引用、启动和监督进程、映射结果 | 插件业务计算、插件依赖管理 |
| 插件进程 | 解析公开协议、读取输入、执行业务、写输出、反馈状态 | import EngineHost、Avalonia、RuntimeStore 内部结构 |
| Avalonia | 显示来源、状态、禁用原因和通用配置表单 | 按插件 ID 写专用页面、加载插件程序集 |
| Supervisor | 单 WorkflowRun 进程树硬兜底 | 理解插件业务和插件内部资源 |

## 6. Manifest V1 固定边界

### 6.1 目录结构

第一版只接受：

```text
plugins/
└─ example_table_transform/
   ├─ plugin.json
   └─ runner.py 或 runner.exe
```

固定规则：

- 只扫描插件根目录的一级子目录。
- 每个一级子目录最多读取一个 `plugin.json`。
- 不跟随解析后越出插件根目录的符号链接、junction 或相对路径。
- `runner` 必须位于当前插件包目录内。
- 不允许 shell 命令字符串；启动参数必须按参数数组执行。
- Python 脚本使用受控解释器直接启动；可执行文件直接启动。
- 工作目录固定为插件包目录，不由工作流覆盖。
- 工作流配置不能覆盖 executable、cwd、env 或协议版本。

### 6.2 Manifest V1 最小字段

| 字段 | 第一版要求 |
| --- | --- |
| `manifest_version` | 固定为 `1` |
| `plugin_id` | 全局唯一稳定 ID |
| `plugin_version` | 插件包版本 |
| `node_type` | 插件公开节点类型，不与核心或其他插件冲突 |
| `node_version` | 节点契约版本 |
| `display_name` | 节点目录显示名 |
| `category` | UI 分类，第一版只作为文本元数据 |
| `config_schema` | 通用配置表单 schema |
| `input_ports` | 工作流输入端口声明 |
| `output_ports` | 工作流输出端口声明 |
| `input_table_slots` | 具名表输入槽位声明 |
| `output_table_slots` | 具名表输出槽位声明 |
| `execution_mode` | 只能是 `external_process` |
| `protocol` | 固定为首版插件 JSONL 协议标识 |
| `entrypoint` | 插件目录内相对脚本或可执行文件 |
| `external_actions` | 是否会修改工作流边界之外的文件、数据库、进程或外部系统 |

第一版不要继续往 manifest 增加市场信息、下载地址、签名、自动更新、依赖解析、GPU 需求和复杂 UI 描述。

资源占用与外部副作用继续分开：

- `external_actions` 说明插件是否改变工作流边界之外的对象。
- CPU、内存、磁盘、网络和 GPU 压力属于资源占用，不等同于外部副作用。
- 启动插件进程和创建工作流私有临时文件属于运行生命周期，不应误写成业务外部写入。

### 6.3 可信来源规则

节点配置中的 `plugin_manifest` 不能继续作为真实执行信任来源。

迁移规则：

1. 发现器只信任固定插件目录中的 manifest。
2. 工作流只保存插件 ID、期望版本、业务参数和输入输出绑定。
3. 运行时按插件 ID 从 PluginCatalog 取已校验描述。
4. 节点配置携带的旧 `plugin_manifest` 只保留兼容读取，不参与命令、路径和权限决定。
5. 完成兼容窗口后，从公开 `config_schema` 中移除 `plugin_manifest`。
6. `in_process` 配置在第一版返回明确不支持错误，不做隐式回退。

### 6.4 扫描性能固定值

第一版使用代码常量，不增加用户配置项：

- 最多扫描 256 个一级插件目录。
- 单个 `plugin.json` 最大 256 KiB。
- 不递归扫描。
- 不在每次打开节点目录或每次执行节点时全目录重扫。
- 启动扫描后按 manifest 路径、修改时间、大小和内容指纹缓存。
- 单个无效插件只禁用自身，不阻断核心节点启动。

## 7. 插件进程协议

### 7.1 控制面

优先复用现有 `IPCEnvelope` 和节点消息语义：

```text
EXECUTOR_READY
NODE_TASK_SUBMIT
NODE_TASK_HEARTBEAT
NODE_TASK_PROGRESS
NODE_TASK_LOG
NODE_TASK_RUNTIME_OPTIONS_UPDATE
NODE_TASK_RUNTIME_OPTIONS_APPLIED
NODE_TASK_CANCEL_REQUEST
NODE_TASK_COMPLETED
NODE_TASK_FAILED
```

插件协议只补公开的插件调用载荷和引用描述，不再建立另一套日志、进度、取消或终态名称。

### 7.2 数据面

控制通道禁止传完整表、图片、二进制和大 JSON。

第一版表插件按以下原则处理：

1. 宿主按 `input_refs` 和 `input_slot_bindings` 解析真实 TableRef。
2. 如果 provider 能提供安全的只读本地描述，插件只收到数据库文件、物理表名、schema 和访问模式。
3. 如果 provider 不能跨进程直接读取，宿主按批次物化到 WorkflowRun 私有 staging SQLite。
4. 输出先写入 task 私有 staging 目标，插件不能直接登记 RuntimeStore 元数据。
5. 插件成功后，宿主校验输出槽位、文件范围、表存在性和 schema，再发布标准 TableRef。
6. 插件失败、取消或超时后，宿主删除未发布 staging，不留下半成品引用。

IPC 允许传：

```text
slot_name
ref_kind
read_only database path 或受控 URI
physical table name
schema 摘要
staging output path
small params
runtime feedback policy
timeout and task identifiers
```

IPC 禁止传：

```text
完整 table rows
base64 大对象
RuntimeStore 对象
EngineHost API token
数据库连接对象
任意 Python 对象序列化
```

### 7.3 输出结果约束

- 插件只能返回 manifest 声明过的输出槽位。
- 每个 `output_slot_bindings` 值必须出现在最终 `output_refs`。
- 插件返回的本地路径必须位于当前 task staging 目录内。
- 插件不能伪造已有 TableRef ID。
- `summary`、`metrics`、`warnings` 和 `error` 必须有大小上限。
- 插件成功但输出缺失时，节点应失败，不得用空成功掩盖。
- 外部动作摘要与资源指标分开记录。

## 8. 配置字与运行反馈边界

本轮不新增插件专用配置字。

插件直接复用当前已经实现的：

- 日志等级。
- 事件等级。
- 事件速率限制。
- 进度开关和间隔。
- 指标开关。
- payload 大小限制。
- 错误上下文开关。
- 脱敏列和掩码策略。
- current run 动态更新版本和 ACK。

固定规则：

- 插件 SDK 或参考 runner 必须在发送前应用当前反馈策略。
- 宿主仍要做第二层长度、速率和 payload 边界校验。
- 心跳不受“进度关闭”影响；长任务必须保留低频心跳。
- 心跳只表示任务仍活跃，不能伪造成业务进度。
- 动态配置字更新只改变后续反馈，不改变插件核心计算和输出。
- 插件业务选项继续放 manifest 和节点 config，不放配置字。

## 9. 六批执行顺序

### 批次 1：可信 Manifest 与插件发现

#### 目标

先让系统可靠回答“安装了哪些插件、哪些可用、哪些不可用以及为什么”，不启动任何插件进程。

#### 建议文件范围

- 新增 `src/flowweaver/plugin_runtime/manifest.py`。
- 新增 `src/flowweaver/plugin_runtime/discovery.py`。
- 新增 `src/flowweaver/plugin_runtime/catalog.py`。
- 新增 `src/flowweaver/plugin_runtime/errors.py`。
- 修改 `src/flowweaver/common/config.py`，只增加一个固定插件根目录落点或内部解析 helper。
- 修改 `src/flowweaver/nodes/registry_definition_specs.py`，补齐插件来源、分类、可见性、启用状态和内部执行入口字段。
- 修改 `src/flowweaver/nodes/default_registry.py`，合并核心定义和有效插件定义。
- 修改节点定义 API DTO，只公开安全字段，不公开绝对路径和 entrypoint。
- 新增 `tests/unit/test_plugin_discovery.py`。
- 新增 `tests/unit/test_plugin_catalog.py`。
- 补 `tests/integration/test_api.py` 的插件目录契约测试。

#### 必测场景

- 有效 manifest 被发现，但扫描过程不 import `runner.py`。
- manifest 缺字段、类型错误、超大、JSON 损坏时只禁用该插件。
- 重复 `plugin_id`、重复 `node_type + node_version` 时明确冲突，不使用静默 first-win。
- entrypoint 路径越界、绝对路径或不存在时禁用。
- `in_process` manifest 被禁用并返回明确原因。
- 核心 41 节点基线不变。
- API 不返回 entrypoint、cwd、插件绝对路径或内部 `implementation_ref`。
- catalog hash 在 manifest 内容变化时变化，在目录顺序变化时保持稳定。

#### 定向测试建议

```powershell
.\python312\python.exe -m pytest tests/unit/test_plugin_discovery.py tests/unit/test_plugin_catalog.py -q
.\python312\python.exe -m pytest tests/integration/test_api.py -k "node_definition or plugin" -q
```

#### 中文提交建议

```text
插件：补齐可信清单发现与目录状态
```

#### 停止条件

- 扫描仍会 import 插件代码。
- 无效插件会阻断 EngineHost 启动。
- 工作流配置仍能提供 executable 或任意命令。
- 插件绝对路径通过普通 API 暴露给 UI。
- 核心默认节点数量被无意改变。

### 批次 2：外部进程 Runner

#### 目标

让一个无数据输入的参考插件能够真实启动、握手、完成或失败，并且进程始终被关闭。

#### 建议文件范围

- 新增 `src/flowweaver/plugin_runtime/process_protocol.py`。
- 新增 `src/flowweaver/plugin_runtime/process_client.py`。
- 新增 `src/flowweaver/plugin_runtime/executor.py`。
- 修改 `src/flowweaver/workflow_process/executor_owner.py`，按注册表内部通用入口选择插件执行器。
- 修改 `src/flowweaver/workflow_process/process_execution_helpers.py` 和必要的初始化参数传递。
- 修改 `src/flowweaver/nodes/builtin_table_registry.py`，不再让真实插件定义依赖普通内置表 handler 路由。
- 保留 `PluginNodeHandler` 作为兼容或诊断占位，真实已发现插件不走该 handler。
- 新增 `tests/unit/test_plugin_process_client.py`。
- 新增 `tests/integration/test_plugin_external_process.py`。

#### 固定实现规则

- 使用参数数组启动，不使用 shell。
- 工作目录固定为插件包目录。
- 清理 `PYTHONPATH` 等会泄漏主程序内部模块的环境变量。
- 不向插件传 API token、完整数据库 URL 或主程序内部对象。
- stdout 只允许一行一个 JSONL 协议消息。
- stderr 只保留有界尾部用于错误诊断。
- 首版一 NodeTask 一插件进程，完成后关闭。
- runner 只按通用 manifest 入口执行，不按插件 ID 分支。

#### 必测场景

- 正常 READY、提交、完成。
- 启动失败、READY 超时、进程提前退出、非法 JSONL、未知消息类型。
- stdout 混入普通文本时明确失败，不无限等待。
- stderr 很大时只保留有界尾部。
- 插件返回 task ID、run ID 或 node ID 不匹配时拒绝。
- 插件进程完成后 PID 不再存活。
- 现有内置节点仍走原执行器，不受插件 runner 影响。

#### 定向测试建议

```powershell
.\python312\python.exe -m pytest tests/unit/test_plugin_process_client.py -q
.\python312\python.exe -m pytest tests/integration/test_plugin_external_process.py -k "startup or ready or terminal" -q
.\python312\python.exe -m pytest tests/unit/test_node_executor_ipc_client.py tests/unit/test_node_executor_process.py -q
```

#### 中文提交建议

```text
插件：实现外部进程最小执行闭环
```

#### 停止条件

- 需要在 EngineHost 或 WorkflowRunProcess 中 import 插件实现。
- runner 需要 `if plugin_id` 才能执行。
- 插件可以从节点配置注入 command、cwd 或 env。
- 插件完成、失败或启动超时后仍残留直接子进程。
- 普通内置节点执行路由发生非预期回归。

### 批次 3：输入输出引用与结果绑定

#### 目标

让一个单输入、单输出的纯表转换插件读取真实上游表，并产生可供下游节点继续使用的标准输出引用。

#### 建议文件范围

- 新增 `src/flowweaver/protocols/plugin_runtime.py`。
- 新增 `src/flowweaver/plugin_runtime/data_refs.py`。
- 新增 `src/flowweaver/plugin_runtime/staging.py`。
- 新增 `src/flowweaver/plugin_runtime/result_mapper.py`。
- 复用 `TableProviderRegistry`、`RuntimeDataRegistry`、现有 TableRef 和输出目标 helper；只在缺少通用能力时增加窄 helper。
- 修改插件执行器，准备输入描述、输出 staging 和最终 `NodeTaskResultModel`。
- 修改 manifest 校验，确保输入输出槽位和节点目录定义一致。
- 新增 `tests/integration/test_plugin_table_transform.py`。

#### 固定实现规则

- IPC 不出现完整 rows。
- 可直接安全读取的本地表只传只读描述。
- 不能直接跨进程读取的 provider 按固定 batch 大小物化到 task 私有 SQLite。
- 插件输出先进入 task 私有 staging，成功后再发布。
- 插件不能直接写 RuntimeStore 元数据。
- 插件不能返回工作流之外路径。
- 输出槽位必须由 manifest 声明。
- 失败、取消和超时必须清理未发布 staging。

#### 必测场景

- `input_slot_bindings` 能正确映射到 manifest 输入名。
- 上游 TableRef 不存在、不可读或槽位缺失时不启动插件。
- 参考插件读入表、转换字段、写出表，输出内容正确。
- `output_slot_bindings` 与 `output_refs` 一致。
- 未声明输出、重复输出、缺失必填输出和路径越界被拒绝。
- 插件失败时不发布半张表或空成功表。
- 大表测试确认 JSONL 中没有 rows、base64 或大 payload。
- staging 读取和发布按批次进行，不一次加载全表。

#### 定向测试建议

```powershell
.\python312\python.exe -m pytest tests/integration/test_plugin_table_transform.py -q
.\python312\python.exe -m pytest tests/integration/test_builtin_table_nodes.py -k "plugin or output_slot or table_ref" -q
.\python312\python.exe -m pytest tests/unit/test_node_executor_process.py -k "ref or payload" -q
```

#### 中文提交建议

```text
插件：贯通表引用与结果绑定
```

#### 停止条件

- 为了执行插件把整表 rows 放入 IPC。
- 插件需要 import RuntimeStore 或 EngineHost 才能读取输入。
- 插件能伪造或覆盖任意 TableRef。
- 输出失败后留下已发布半成品。
- 为某一个参考插件修改通用表流转语义。

### 批次 4：日志、进度、心跳、动态配置字、取消与超时

#### 目标

把插件运行完全接入现有节点监督和配置字反馈控制，并完成进程清理硬验收。

#### 建议文件范围

- 扩展插件 process client 和 executor 的事件转发。
- 复用 `src/flowweaver/protocols/runtime_feedback.py`。
- 复用 `src/flowweaver/protocols/runtime_logs.py` 的长度和上下文过滤规则。
- 复用 `src/flowweaver/workflow_process/ipc_events.py` 的节点状态写入。
- 复用 `CancellableNodeExecutor` 和 `RuntimeOptionsUpdatableNodeExecutor` 协议。
- 为 `src/flowweaver/engine/supervisor.py` 和 workflow child 启动链补单 WorkflowRun Job Object 所有权。
- 将 `tools/portable_launcher.py` 已验证的 Job Object 逻辑抽成可复用实现，或增加等价且独立测试的 EngineHost helper；不要让 `src` 反向依赖测试工具脚本。
- 新增插件反馈、取消、超时和 Windows 进程树集成测试。

#### 固定实现规则

- 插件启动后按现有节点心跳节奏发送低频心跳。
- 进度关闭不关闭心跳。
- 动态配置字更新必须转发给当前插件任务并返回应用 ACK。
- 插件 SDK 发送前过滤，宿主再次校验。
- 日志消息长度继续受当前 1024 字符边界约束。
- 取消先发协议消息，等待短宽限期，再 terminate，最后 kill。
- 超时和工作流取消都必须进入标准 NodeTask 终态。
- EngineHost/Supervisor 持有每个 WorkflowRun 的 Job Object，工作流终态后关闭该 Job。
- 插件进程不得依赖正常 finally 才能被清理。

#### 必测场景

- DEBUG/INFO/WARN/ERROR 按当前配置字过滤。
- 运行中切换配置字后，后续插件日志和进度立即按新策略处理。
- 动态配置字版本正确 ACK，旧版本或错任务更新被拒绝。
- 心跳更新 `NodeRun.last_heartbeat`，进度更新不代替心跳。
- 插件无进度但持续心跳时不被误判失联。
- 用户取消后插件收到取消，NodeRun 进入取消终态，PID 消失。
- 插件忽略取消时，宽限期后被强制终止。
- 节点超时后 PID 消失，错误明确为超时而不是普通失败。
- 强杀 WorkflowRunProcess 后，该 run 的插件子进程消失，其他 run 不受影响。
- 强杀便携启动器后，应用级 Job Object 仍能清理全部进程。

#### 定向测试建议

```powershell
.\python312\python.exe -m pytest tests/unit/test_plugin_process_client.py -k "log or progress or heartbeat or runtime_options or cancel" -q
.\python312\python.exe -m pytest tests/integration/test_plugin_external_process.py -k "cancel or timeout or runtime_options" -q
.\python312\python.exe -m pytest tests/integration/test_supervisor.py -k "workflow and process" -q
```

Windows 正式验收应另跑不依赖 mock 的 PID 残留测试。

#### 中文提交建议

```text
插件：接入运行反馈与进程生命周期
```

#### 停止条件

- 配置字切换只在主程序生效，插件仍持续发送全部日志。
- 心跳和进度仍被当作同一个信号。
- 取消或超时后仍能观察到插件 PID。
- 单个 WorkflowRun 结束只能依赖关闭整个 EngineHost 才能清理。
- Job Object 误杀其他仍在运行的 WorkflowRun。

### 批次 5：插件目录 API 与 Avalonia 状态收口

#### 目标

让用户能看出插件来源、版本、可用状态和禁用原因，并能使用通用 schema 编辑配置；不做插件自定义 UI。

#### 建议文件范围

- 新增或扩展插件目录只读 API。
- 修改 `Avalonia_UI/Api/EngineHostDtos.cs`，读取安全插件元数据。
- 修改 `Avalonia_UI/ViewModels/NodeDefinitionListItemViewModel.cs`，增加来源、启用状态和禁用原因展示状态。
- 修改 `Avalonia_UI/Views/Components/Workflow/WorkflowNodeCatalogView.axaml`。
- 修改 `Avalonia_UI/Views/Components/Workflow/WorkflowAddNodeView.axaml`，禁用不可新增的插件节点。
- 继续复用 `NodeConfigSchemaParser`、通用配置字段和 JSON 回退。
- 补 `Avalonia_UI.Tests` 的 API DTO、目录刷新、禁用节点和本地化测试。

#### UI 固定边界

- 普通新增节点列表只允许选择 `visible && enabled` 的定义。
- 已保存工作流引用禁用插件时仍显示节点，但明确提示不可运行。
- 禁用原因来自后端安全 DTO，不由 UI 猜测。
- UI 不显示 entrypoint、绝对路径、工作目录和内部执行入口。
- UI 不按 `plugin_id` 创建专用表单。
- 插件参数继续使用通用 `config_schema`。
- 复杂或暂不支持的 schema 继续回退 JSON 编辑，不新增插件页面框架。

#### 必测场景

- 有效插件显示来源和版本并可新增。
- 无效、冲突、路径越界、协议不支持的插件显示禁用原因且不可新增。
- 已存在工作流中的禁用插件节点不会静默消失。
- 刷新目录时 catalog hash 未变化则复用缓存。
- manifest 变化并重启后目录状态正确刷新。
- 普通核心节点目录和配置编辑无回归。

#### 定向测试建议

```powershell
dotnet test .\Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-restore --filter "NodeDefinition|NodeCatalog|WorkflowAddNode|Plugin"
```

#### 中文提交建议

```text
前端：接入插件目录与禁用状态
```

#### 停止条件

- UI 需要引用插件程序集或 Python 模块。
- UI 出现按插件 ID 的业务分支。
- 禁用插件在已保存工作流中完全不可见。
- 普通 API 暴露插件绝对路径或启动命令。
- 为插件新增第二套配置表单协议。

### 批次 6：参考插件与最终验收

#### 目标

使用一个纯表转换插件证明整条主线可用，并冻结第一版插件契约。

#### 参考插件要求

- 放在测试 fixture 或示例插件目录，不注册为第 42 个内置节点。
- 只使用 Python 标准库或极小的测试依赖。
- 一个必填输入表槽位。
- 一个必填输出表槽位。
- 一个简单业务参数，例如选择字段、重命名字段或投影字段。
- 不访问网络。
- 不写工作流目录之外文件。
- `external_actions=false`。
- 支持 READY、任务提交、日志、进度、低频心跳、动态配置字、取消和终态。
- 只通过 staging 表读取和写入数据。

#### 最终测试顺序

1. 运行插件发现、manifest 和目录单元测试。
2. 运行插件 process client 和协议单元测试。
3. 运行插件表转换集成测试。
4. 运行配置字、取消、超时和 PID 清理集成测试。
5. 运行节点目录和 Workflow 校验 API 测试。
6. 运行 Avalonia 插件目录和禁用状态测试。
7. 运行全部 Python 测试。
8. 运行全部 Avalonia 测试。
9. 运行 Ruff 和 Mypy。
10. 在 Windows 上执行真实 WorkflowRun 强杀和进程残留验收。

#### 全量命令建议

```powershell
.\python312\python.exe -m pytest
.\python312\python.exe -m ruff check src tests
.\python312\python.exe -m mypy
dotnet test .\Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --no-restore
```

#### 中文提交建议

```text
测试：完成外部插件最小闭环验收
```

#### 最终停止条件

- 参考插件需要修改核心节点业务代码才能运行。
- 参考插件依赖被加入核心 `pyproject.toml`。
- 输入或输出通过 IPC 传完整 rows。
- 动态配置字、取消、超时或心跳任一项未贯通。
- WorkflowRun 结束后仍残留插件进程。
- 核心 41 节点、阶段 Q 表流转或 Avalonia 通用节点编辑出现回归。

## 10. 性能门槛

| 方向 | 第一版硬门槛 |
| --- | --- |
| 启动扫描 | 只读一级 manifest，不 import 插件，不递归扫描 |
| 执行加载 | 只有插件节点真实运行时才启动插件进程 |
| 核心启动 | 单个无效插件不能拖垮 EngineHost |
| IPC | 只传小 JSON 控制消息和引用描述 |
| 表数据 | 能直读则只读引用；不能直读则按批物化到 staging |
| 输出 | 先写 task 私有 staging，成功后按批发布 |
| 日志 | 使用现有等级、速率、长度、上下文和 payload 限制 |
| 心跳 | 低频固定节奏，不随业务循环高频发送 |
| stderr | 只保存有界尾部，不无限累积 |
| 进程 | 一任务一进程，终态立即关闭，不常驻后台 |
| UI | catalog hash 未变化时不重复解析全部 schema |
| 依赖 | 核心不安装插件业务依赖 |

建议增加协议级断言，扫描提交中的 JSONL 载荷键，确保不存在 `rows`、`records`、`base64`、`bytes` 等大数据字段。

## 11. 耦合门槛

完成后应满足：

```text
新增一个符合 V1 manifest 的插件
-> 不修改 EngineHost 业务代码
-> 不修改 WorkflowRunProcess 业务代码
-> 不修改 Avalonia 业务页面
-> 不修改核心依赖
-> 重启后出现在统一节点目录
-> 配置后可通过通用外部进程 runner 执行
```

允许修改的只有插件包自身：

```text
plugin.json
runner.py / runner.exe
插件自己的依赖和测试
```

如果新增第二个参考插件时仍需要修改核心代码，说明通用边界尚未收口，不能宣布 PLUGIN-RUNTIME-1 完成。

## 12. 验收矩阵

| 验收项 | 预期结果 |
| --- | --- |
| 核心基线 | 当前 41 个内置节点不因参考插件增加 |
| 发现 | 有效插件被发现，无效插件只禁用自身 |
| 安全 | 工作流不能注入命令、绝对路径或环境变量 |
| 懒加载 | 打开 UI 和扫描目录时不执行插件代码 |
| 注册 | 有效插件进入统一节点目录，来源和版本可见 |
| 禁用 | 冲突、损坏、不支持协议插件有明确禁用原因 |
| 配置 | 使用通用 schema；复杂字段可回退 JSON |
| 输入 | 插件按具名槽位获得引用，不接收完整 rows |
| 输出 | 输出被宿主校验并登记为标准引用 |
| 下游 | 下游节点可以使用插件输出 TableRef |
| 日志 | 配置字能限制插件日志等级和数量 |
| 动态切换 | current run 更新后插件返回 ACK 并使用新策略 |
| 进度 | 业务进度可查，关闭进度不影响心跳 |
| 心跳 | 长任务 `last_heartbeat` 持续刷新 |
| 取消 | 插件收到取消，超时后可被强制终止 |
| 超时 | 节点进入明确超时终态，插件 PID 消失 |
| 硬兜底 | 单 WorkflowRun 被强杀后只清理自己的插件进程 |
| 故障隔离 | 插件崩溃不导致 EngineHost 或其他 WorkflowRun 崩溃 |
| 性能 | 扫描、日志、IPC、staging 和 UI 都有明确上限 |
| 解耦 | 第二个 V1 插件接入时不改核心业务代码 |

## 13. 推荐实际执行顺序

```text
批次 1：可信 manifest + discovery + catalog
-> 测试
-> 中文提交并推送

批次 2：外部进程 runner
-> 测试
-> 中文提交并推送

批次 3：TableRef 输入输出 + result binding
-> 测试
-> 中文提交并推送

批次 4：日志/进度/心跳/动态配置字/取消/超时/Job Object
-> 测试
-> 中文提交并推送

批次 5：目录 API + Avalonia 启用/禁用状态
-> 测试
-> 中文提交并推送

批次 6：参考插件 + 全量回归 + Windows 真实进程验收
-> 测试
-> 中文提交并推送
-> 冻结 V1 契约
```

批次 2 至批次 4 不建议并行。它们依次依赖 manifest 信任边界、进程协议、数据引用和监督链路，提前并行容易出现两套临时协议。

Avalonia 批次可以在批次 4 后单独进行，但不得先用 UI 假状态掩盖后端插件尚不可执行。

## 14. 完成后的整体状态

本计划完成后，FlowWeaver 的边界应变为：

```text
核心内置节点
-> 保持稳定、依赖轻、数量受控

插件节点
-> manifest 描述
-> 统一目录展示和校验
-> 外部进程隔离执行
-> TableRef 和标准结果回到工作流
-> 复用当前配置字和运行监督

具体插件业务
-> 留在插件包内
-> 独立依赖
-> 独立升级
-> 不进入主程序分支
```

这项补齐的本质不是“再增加一个插件节点功能”，而是建立一条以后新增插件不再膨胀主程序的稳定通道。第一版一旦通过参考插件、动态配置字、取消、超时和进程残留验收，就应冻结协议，后续插件优先在插件包内扩展，不再回到核心继续堆节点。
