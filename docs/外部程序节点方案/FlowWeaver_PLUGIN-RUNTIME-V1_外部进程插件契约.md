# FlowWeaver PLUGIN-RUNTIME V1 外部进程插件契约

> 冻结日期：2026-07-12
>
> 契约状态：V1
>
> 适用范围：本地 `external_process` 插件
>
> 参考实现：`tests/fixtures/plugins/table_projection`

## 1. 契约目的

本契约固定 FlowWeaver 第一版外部进程插件的接入边界，使新增插件只需要增加插件包，不再修改 EngineHost、WorkflowRunProcess、Avalonia 页面或核心依赖。

V1 只解决以下闭环：

```text
可信发现
-> 统一节点目录
-> 通用 Schema 配置
-> 外部进程执行
-> TableRef 输入和 staging 输出
-> 标准结果发布
-> 日志、进度、心跳和动态配置字
-> 取消、超时和进程树清理
```

V1 不包含插件市场、在线安装、热加载、签名信任链、插件自定义 UI、远程执行和 `in_process`。

## 2. 插件包结构

插件根目录由 EngineHost 配置。发现器只扫描根目录下一级子目录，不递归扫描。

```text
plugins/
└─ <package_name>/
   ├─ plugin.json
   └─ runner.py 或 runner.exe
```

固定规则：

- 一个一级目录代表一个插件包。
- 清单文件名固定为 `plugin.json`。
- 入口必须是包内相对路径，解析后仍位于当前插件包内。
- Python 入口只接受 `.py`，原生入口只接受 `.exe`。
- 发现阶段只读取清单，不 import、不执行入口文件。
- 插件包不得依赖 FlowWeaver 的内部 Python 模块或 Avalonia 程序集。

## 3. Manifest V1

### 3.1 必要字段

```json
{
  "manifest_version": "1",
  "plugin_id": "vendor.plugin_name",
  "plugin_version": "1.0.0",
  "node_type": "plugin.vendor.node_name",
  "node_version": "1.0",
  "display_name": "Display Name",
  "category": "table",
  "config_schema": {
    "type": "object",
    "properties": {}
  },
  "input_ports": [],
  "output_ports": [],
  "input_table_slots": [],
  "output_table_slots": [],
  "execution_mode": "external_process",
  "protocol": "flowweaver.plugin-jsonl.v1",
  "entrypoint": "runner.py",
  "external_actions": false
}
```

### 3.2 固定约束

- `manifest_version` 固定为 `1`。
- `node_type` 必须以 `plugin.` 开头。
- `execution_mode` 固定为 `external_process`。
- `protocol` 固定为 `flowweaver.plugin-jsonl.v1`。
- 端口和表槽位使用具名绑定；表槽位必须存在同名端口。
- 必填输入表槽位与同名输入端口的必填状态必须一致。
- `enable_execute` 和 `allow_external_actions` 是宿主控制字段，插件清单不得重复声明。
- `external_actions=true` 时，节点还必须由用户显式允许外部动作才能启动。

### 3.3 配置 Schema

V1 通用配置字段类型为：

- `string`
- `integer`
- `number`
- `boolean`
- `enum`
- `array`
- `object`

Avalonia 使用统一 Schema 表单。复杂或当前不支持的 Schema 继续回退 JSON 编辑，不为插件创建专用页面。

## 4. 发现和目录状态

发现结果必须包含可用状态和安全禁用原因。单个插件损坏不得阻止核心节点目录或其他插件加载。

以下情况只禁用对应插件：

- 清单缺失、过大或 JSON 无效。
- Manifest 字段不合法或协议不支持。
- 入口缺失、类型不支持或路径越界。
- `plugin_id` 重复。
- 节点类型和版本重复。
- 与核心保留节点或保留插件 ID 冲突。

目录 API 只公开安全元数据，不公开入口、绝对路径、工作目录、环境变量和启动命令。

目录缓存同时比较节点目录 hash 和插件目录 hash。任一 hash 改变都必须重新读取目录；两个 hash 均未变化时可复用前端缓存。

## 5. 进程启动契约

### 5.1 入口参数

宿主启动入口时传入：

```text
--executor-id <host-assigned-id>
```

插件必须使用该 ID 返回 `EXECUTOR_READY`，不得自行替换宿主分配的执行器身份。

### 5.2 标准流

- `stdin`：宿主发送 UTF-8 JSONL。
- `stdout`：插件发送 UTF-8 JSONL，不得混入普通文本。
- `stderr`：仅用于诊断，宿主只保留有界尾部。
- 每行是一条完整 JSON 消息。
- 单条消息只传控制信息、配置和引用，不传完整表数据。

### 5.3 进程环境

宿主只传递固定白名单环境变量。插件不得依赖宿主进程的任意环境、当前 Python 包路径或 FlowWeaver 源码路径。

V1 为一任务一进程。任务终态后进程关闭，不做跨任务或跨 WorkflowRun 常驻复用。

## 6. JSONL 消息契约

V1 消息类型固定为：

| 方向 | 消息类型 | 用途 |
| --- | --- | --- |
| 插件到宿主 | `EXECUTOR_READY` | 入口初始化完成 |
| 宿主到插件 | `NODE_TASK_SUBMIT` | 提交单个节点任务 |
| 插件到宿主 | `NODE_TASK_HEARTBEAT` | 低频活跃信号 |
| 插件到宿主 | `NODE_TASK_PROGRESS` | 业务进度，不替代心跳 |
| 插件到宿主 | `NODE_TASK_LOG` | 受配置字约束的节点日志 |
| 宿主到插件 | `NODE_TASK_RUNTIME_OPTIONS_UPDATE` | 更新当前任务配置字 |
| 插件到宿主 | `NODE_TASK_RUNTIME_OPTIONS_APPLIED` | 确认应用新版本 |
| 宿主到插件 | `NODE_TASK_CANCEL_REQUEST` | 请求协作取消 |
| 插件到宿主 | `NODE_TASK_COMPLETED` | 成功或取消终态 |
| 插件到宿主 | `NODE_TASK_FAILED` | 失败终态 |

消息必须携带并保持当前任务身份：

- `workflow_run_id`
- `node_run_id`
- `task_id`
- `attempt`
- `process_generation`
- 宿主分配的 `executor_id`

宿主会复核身份。错 WorkflowRun、错节点、错任务或错代际消息会被拒绝或转为明确失败。

## 7. 表数据契约

### 7.1 输入

插件从 `NODE_TASK_SUBMIT.payload.plugin_runtime.inputs` 获得具名输入描述。V1 输入引用固定为只读 SQLite 表描述：

- `slot_name`
- `table_ref_id`
- `ref_kind=sqlite_table`
- `access_mode=read_only`
- `database_uri`
- `table_name`
- `schema`
- `materialized`

可跨进程直读的运行表使用只读 URI。不可直读的表由宿主按固定批次物化到当前任务私有 staging，插件不感知 RuntimeStore 内部结构。

### 7.2 输出

插件从 `plugin_runtime.output_targets` 获得具名输出目标：

- `slot_name`
- `ref_kind=sqlite_table`
- `access_mode=write_staging`
- `database_path`
- `table_name`

插件只能写入宿主提供的当前任务 staging 目标。完成时返回输出槽位、staging 路径、表名和 Schema，不得返回或伪造 FlowWeaver `TableRef` ID。

宿主在成功后校验输出并按批复制、发布和登记标准 TableRef。失败、取消、超时或输出校验失败时不发布半成品，并清理私有 staging。

### 7.3 禁止的大载荷

JSONL 控制消息不得包含完整表数据或二进制编码。以下键不得用作表数据载荷：

```text
rows
records
record_batches
base64
bytes
binary
```

## 8. 运行反馈与配置字

插件必须在发送前执行第一层过滤，宿主继续执行第二层校验和限流。

### 8.1 日志

- 支持 `DEBUG`、`INFO`、`WARN`、`ERROR`。
- 单条消息最长 1024 字符。
- 遵守日志等级和每秒事件数量限制。
- 上下文不得携带整行、批次或二进制数据。
- 遵守指标开关、错误上下文开关、payload 上限、列脱敏和掩码策略。

### 8.2 进度和心跳

- 进度遵守开关、事件等级和最小发送间隔。
- 关闭进度不得关闭心跳。
- 心跳使用独立低频节奏，不随每行或每个业务循环高频发送。

### 8.3 动态更新

- 更新只对匹配的当前任务生效。
- 版本必须严格大于插件当前已应用版本。
- 应用后返回同一任务和版本的 `NODE_TASK_RUNTIME_OPTIONS_APPLIED`。
- 错任务、旧版本和重复版本不得改变当前策略。

## 9. 取消、超时和进程树

- 收到取消请求后，插件应尽快停止业务循环并返回 `CANCELLED`。
- 宿主先发送协作取消，超过宽限期后 terminate，最后 kill。
- 节点超时进入明确超时终态，不能伪装成普通插件失败。
- 每个 WorkflowRun 由 Supervisor 持有独立 Windows Job Object。
- WorkflowRun 正常结束、取消、失败或被强杀后，其插件进程树必须全部消失。
- 一个 WorkflowRun 的清理不得终止其他仍在运行的 WorkflowRun。
- 便携启动器继续保留应用级 Job Object 作为整棵应用进程树的最终兜底。

## 10. Avalonia 契约

Avalonia 只读取安全目录 DTO：

- 插件来源和版本。
- 节点类型和版本。
- 启用状态。
- 后端提供的禁用原因。
- 通用配置 Schema。

新增下拉只包含 `visible && enabled` 的真实节点定义。禁用或损坏插件仍显示在统一目录中，但不可新增。

已保存工作流引用禁用插件时，节点不得静默消失；它继续使用 JSON 回退查看配置，并明确显示不可运行及后端原因。

Avalonia 不加载插件程序集，不显示入口和路径，不按 `plugin_id` 写业务分支。

## 11. 参考插件

V1 参考插件位于：

```text
tests/fixtures/plugins/table_projection/
├─ plugin.json
└─ runner.py
```

它证明以下能力：

- 不增加第 42 个内置节点。
- 发现后以用户插件定义进入统一目录。
- 使用一个必填输入表槽位和一个必填输出表槽位。
- 按批读取输入 staging/运行表并写入输出 staging。
- 支持字段投影、首字段重命名和批大小配置。
- 支持日志、进度、低频心跳、动态配置字和协作取消。
- 不访问网络，不写宿主提供目标之外的文件。
- 只使用 Python 标准库，不增加核心依赖。

定向验收：

```powershell
.\python312\python.exe -m pytest tests\integration\test_reference_plugin.py -q
```

## 12. V1 变更规则

以下修改属于兼容修复，可以保留 V1：

- 修复实现错误但不改变已有字段语义。
- 收紧宿主对已有安全边界的校验。
- 增加不影响协议载荷的诊断和测试。
- 修复 UI 展示，但不改变插件业务协议。

以下修改必须设计新版本，不得静默改变 V1：

- 修改必填 Manifest 字段或既有字段语义。
- 修改 JSONL 消息类型、身份字段或终态语义。
- 修改输入输出引用结构或允许通过 IPC 传完整表。
- 引入 `in_process`、远程执行、常驻复用或共享内存数据面。
- 允许插件加载 Avalonia 自定义程序集或页面。
- 给核心增加某个插件专用分支或业务依赖。

新增符合 V1 的第二个及后续插件时，只允许修改插件包自身及其测试。若仍需修改 EngineHost、WorkflowRunProcess、Avalonia 业务页面或核心依赖，说明 V1 通用边界被破坏。
