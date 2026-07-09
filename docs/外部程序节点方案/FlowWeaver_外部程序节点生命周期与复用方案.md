# FlowWeaver 外部程序节点生命周期与复用方案

更新时间：2026-07-09

## 当前决策

当前讨论阶段只采用 Private Runtime。

```text
Private Runtime
Job Object 边界 = 单个 WorkflowRun
Job Object Owner = EngineHost / Supervisor
单个工作流只管理自己拉起的外部程序
工作流结束就整体清理
```

也就是说，OCR、YOLO、CLIP、SAM、系统截图、关键信息获取等外部程序节点，第一阶段只允许在单个 WorkflowRun 内复用。其他复用边界不在本文范围。

当前方案有一个主程序前置要求：

```text
EngineHost / Supervisor 启动 WorkflowRunProcess 时，
必须创建并持有当前工作流级 Windows Job Object，
并让该 WorkflowRunProcess 运行在这个 Job Object 内。
```

如果后台运行工作流链路尚未完全收口，这一项需要作为外部程序节点落地前的验收点。否则节点即使按 Private Runtime 设计，也无法保证工作流异常结束时外部程序一定被清理。

## 目标结构

推荐结构：

```text
EngineHost
-> WorkflowRun Job
   -> WorkflowRunProcess
   -> NodeExecutorProcess
      -> 节点 RuntimeManager
         -> OCR / YOLO / CLIP / SAM 子进程或本地服务
```

各层职责：

| 层级 | 职责 |
| --- | --- |
| EngineHost | 启动和监管 WorkflowRunProcess，不理解外部程序业务 |
| WorkflowRun Job | 当前工作流的硬兜底边界，由 EngineHost / Supervisor 创建并持有，工作流结束后清理整棵私有进程树 |
| WorkflowRunProcess | DAG 调度、NodeTask 状态、取消、超时、运行事件 |
| NodeExecutorProcess | 普通节点执行故障域，承载节点 RuntimeManager |
| 节点 RuntimeManager | 节点私有启动、连接、复用、健康检查、句柄丢弃 |
| 外部程序 | 执行 OCR/检测/分割/截图等真实业务，并可按 idle/lease 自退出 |

主程序不进入 OCR、YOLO、SAM 等业务细节，也不保存这些程序的内部状态。

## 生命周期边界

外部程序生命周期分为硬兜底和软退出。

### 硬兜底

硬兜底由工作流级 Windows Job Object 提供。

```text
WorkflowRunProcess 活着
-> 当前工作流拉起的 NodeExecutorProcess 和外部程序允许活着

WorkflowRunProcess 结束、被取消、超时、失败或被杀
-> WorkflowRun Job 清理当前工作流的私有进程树
```

这意味着单个工作流只清理自己拉起的程序，不影响其他工作流。

### 软退出

外部程序仍建议支持软退出。

```text
一段时间没有请求
-> 外部程序自行退出

lease 超时
-> 外部程序自行退出

父进程不存在
-> 外部程序自行退出

health check 失败
-> RuntimeManager 丢弃该 runtime，下次需要时重新拉起
```

软退出用于正常释放模型、显存、端口和临时文件；Job Object 用于异常兜底。

## 复用范围

当前只允许工作流内复用：

```text
同一个 WorkflowRun Job 内
同一个 NodeExecutorProcess 或同一组节点 RuntimeManager 内
相同 runtime key
复用同一个外部程序
```

工作流结束后，不论外部程序是否仍健康，都应被当前 WorkflowRun Job 清理。

暂不做：

```text
后台长期常驻模型服务
当前工作流私有进程树之外的复用
工作流结束后继续保留外部程序
```

## 节点 RuntimeManager 最小职责

即使生命周期由工作流级 Job Object 兜底，节点侧仍需要一个很薄的 RuntimeManager。

最小接口建议：

```text
get_or_start(spec) -> RuntimeHandle
health_check(handle) -> healthy / unhealthy
invoke(handle, request) -> response
mark_broken(handle, reason)
forget_handle(handle)
shutdown_all(reason)
```

RuntimeManager 第一阶段只负责：

- 不重复启动完全相同的 runtime。
- 不复用已经坏掉的 runtime。
- 请求前确认服务基本可用。
- 节点任务失败时丢弃或重启自己的 runtime。
- NodeExecutorProcess 退出时尽力释放本节点启动过的程序。

RuntimeManager 不负责：

```text
全局资源调度
主程序级服务面板
插件市场
复杂 GPU 调度
```

## Runtime Key

只有 runtime key 完全一致时才能复用外部程序。

建议 key 至少包含：

```text
node_runtime_id
program_path 或 command
python_env_path
model_path
device
communication_mode
runtime_params_hash
working_dir
```

说明：

| 字段 | 作用 |
| --- | --- |
| node_runtime_id | 节点或插件声明的运行时 ID |
| program_path / command | 实际启动的外部程序 |
| python_env_path | 节点自己的 Python 环境或解释器路径 |
| model_path | OCR/YOLO/SAM 等模型文件路径 |
| device | CPU、CUDA、DirectML 等设备选择 |
| communication_mode | HTTP、stdio、named pipe 等通信方式 |
| runtime_params_hash | batch size、precision、端口策略等影响服务行为的参数 |
| working_dir | 外部程序相对路径和缓存路径的基准 |

不要只按 node_type 复用。YOLO 模型路径、SAM checkpoint、OCR 语言包或 device 只要变化，就应视为不同 runtime。

## 外部程序启动协议

节点 RuntimeManager 懒启动外部程序。

启动时建议传入：

```text
runtime_id
workflow_run_id
workflow_process_id
node_task_id
parent_executor_pid
lease_token
idle_timeout_seconds
startup_timeout_seconds
communication endpoint
working_dir
model_path
device
log_path
```

外部程序启动后必须进入明确状态：

```text
starting
loading_model
ready
failed
shutting_down
```

RuntimeManager 不应只判断“进程存在”就认为可用。至少要等到 ready probe 成功。

## 健康检查

健康检查不应只检查端口连通。

建议 health 返回：

```text
runtime_id
ready
model_loaded
model_fingerprint
device
active_requests
last_error
```

RuntimeManager 在每次 invoke 前做轻量 health check：

```text
health healthy
-> 复用

health failed / timeout / runtime_id 不匹配
-> mark_broken
-> 尝试关闭旧进程
-> 下次重新启动
```

对于重模型服务，可以允许 health check 使用较轻接口，不要求每次跑真实推理。

## 通信模式

第一版可选通信模式：

| 模式 | 适用场景 | 说明 |
| --- | --- | --- |
| 本地 HTTP | 模型服务、截图服务、OCR 服务 | 调试简单，容易做 health / ready；只传轻量引用时性能足够 |
| stdio JSONL | 简单命令型程序 | 无端口，适合单请求串行；并发、日志分离、超时恢复更麻烦 |
| named pipe | Windows 本地服务 | 无端口冲突，适合本机 IPC；调试和跨语言封装比 HTTP 更复杂 |

第一版建议优先使用本地 HTTP 或 stdio JSONL。性能重点不是先换通信协议，而是避免通过 IPC 传大数据。

## 数据传递原则

工作流应只传轻量引用，大数据原地不动。

当前主线已经接近这个原则：

```text
NodeTask.input_refs 传 TableRef ID
NodeTaskResult.output_refs 传输出引用 ID
IPC 不传完整表数据
```

外部程序节点也应遵守同样原则。

请求中只传：

```text
table_ref_id
file_path / file_uri
blob_ref_id
shared_memory_name
offset
length
shape
dtype
device
schema_fingerprint
small config params
```

不要在 HTTP、stdio 或 named pipe 中传：

```text
大图 base64
完整视频帧列表
大表 rows
大 tensor bytes
```

后续如需更高性能，可以扩展 provider/ref 类型：

| 引用类型 | 适用场景 |
| --- | --- |
| TableRef | 表格数据、运行 SQL 表、内存表 |
| FileRef / BlobRef | 图片、视频、二进制大文件 |
| SharedMemoryRef | CPU 大数组、图像 batch、低延迟本机处理 |
| TensorRef | 模型输入输出 tensor |
| GpuTensorRef | 后期显存对象或 CUDA IPC，第一阶段不承诺 |

当前阶段先坚持“传引用，不传大对象”。等引用协议稳定后，再考虑 shared memory、mmap 或 GPU handle。

## Lease 与 Idle 自退出

外部程序应支持 lease / idle 自退出。

推荐规则：

```text
每次请求刷新 last_activity_at
每次请求或固定周期刷新 lease
当前无 active_requests 且 idle_timeout 到期
-> 外部程序自行退出

lease 超过 ttl 未刷新
-> 外部程序自行退出

parent_executor_pid 不存在
-> 外部程序自行退出
```

这让外部程序可以在正常路径下优雅释放模型和显存，同时在异常路径下由 WorkflowRun Job 兜底。

## 关闭触发点

外部程序可由以下原因关闭：

| 触发点 | 关闭策略 |
| --- | --- |
| WorkflowRun 正常结束 | WorkflowRun Job 清理当前工作流私有进程树 |
| WorkflowRun 取消 | 先请求当前任务取消，超过 grace 后由 Job Object 兜底 |
| 节点超时 | 当前 runtime 标记 broken，关闭或等待 Job Object 清理 |
| health check 失败 | 丢弃 handle，不再复用 |
| idle timeout | 外部程序自行退出 |
| lease timeout | 外部程序自行退出 |
| NodeExecutorProcess 退出 | 外部程序可自退出；最终由 WorkflowRun Job 兜底 |

第一版可以不做精细关闭原因分类，但应保证错误写入 NodeTaskResult / NodeRun.error。

## 并发策略

第一版建议保守：

```text
每个 runtime key 默认单请求串行
```

原因：

- OCR/YOLO/SAM 对显存和模型对象有强依赖。
- 许多模型服务并不天然线程安全。
- 当前 WorkflowRunProcess 的并发上限也很保守。

后续可以在 runtime spec 中增加：

```text
max_concurrent_requests
queue_timeout_seconds
request_timeout_seconds
```

但这些应由节点或插件声明，不应由主程序猜测。

## 错误与降级

外部程序相关错误应区分：

| 错误 | 含义 |
| --- | --- |
| STARTUP_TIMEOUT | 外部程序启动或模型加载超时 |
| READY_CHECK_FAILED | ready probe 未通过 |
| HEALTH_CHECK_FAILED | 已启动服务健康检查失败 |
| REQUEST_TIMEOUT | 单次请求超时 |
| PROCESS_EXITED | 外部程序提前退出 |
| RUNTIME_KEY_MISMATCH | 连接到的服务不是期望 runtime |
| CANCELLED | 节点或工作流取消 |

失败处理建议：

```text
启动失败
-> 当前节点失败

请求失败
-> 当前节点失败，runtime 标记 broken

health 失败
-> runtime 标记 broken，下次重新启动

外部程序自行 idle 退出
-> 不视为错误，下次需要时重新启动
```

## 主程序需要提供的最小支持

主程序不需要管理 OCR/YOLO/SAM 生命周期，但需要提供当前阶段的硬边界。

### 1. 工作流级 Job Object 兜底

每个 WorkflowRun 必须对应一个工作流级 Windows Job Object。这是主程序需要提供的硬边界，不是节点自己的可选能力。

```text
WorkflowRun Job
Owner: EngineHost / Supervisor
-> WorkflowRunProcess
-> NodeExecutorProcess
-> 节点拉起的外部程序
```

工作流终态、取消、异常退出或进程被杀时，Job Object 清理当前工作流的私有进程树。

当前阶段建议只使用这一层工作流级 Job Object。WorkflowRunProcess 和节点 RuntimeManager 不再额外创建第二层嵌套 Job Object，避免 Windows Job 嵌套、breakaway 和 assign 失败等复杂性。

验收重点：

```text
EngineHost / Supervisor 启动 WorkflowRunProcess 后，WorkflowRunProcess 已加入当前工作流 Job。
WorkflowRunProcess 拉起的 NodeExecutorProcess 及其子进程受同一 Job 兜底。
强杀 WorkflowRunProcess 或触发后台工作流异常退出时，不残留当前工作流私有外部程序。
WorkflowRunProcess / NodeExecutorProcess / 节点 RuntimeManager 不依赖第二层 Job Object 才能完成兜底。
```

### 2. NodeExecutorProcess 关闭可靠

WorkflowRunProcess 终态、取消、异常退出时，应确保复用的 NodeExecutorProcess 被 close。即使 close 失败，也由 WorkflowRun Job 做最终兜底。

### 3. 取消和超时继续按 NodeTask 处理

当前 NodeTask 级取消和超时模型可以继续使用。外部程序节点只需要把取消请求转成自己的请求取消或连接关闭。

### 4. 不把外部程序直接挂在 WorkflowRunProcess 业务线程内

OCR/YOLO/SAM 等重模型节点不应在 WorkflowRunProcess 的调度主逻辑或内置表 handler 中直接启动长期进程。

推荐只在 NodeExecutorProcess 内拉起外部程序，再由 WorkflowRun Job 做整棵私有进程树兜底。

## 节点配置与运行时配置边界

节点业务配置仍放在节点 `config` 中，例如：

```text
image_path
input_table_slot
model_name
confidence_threshold
output_format
```

外部程序运行时配置建议由节点或插件 manifest 提供，例如：

```text
reuse_scope = workflow
python_env_path
entry_command
model_path
device
startup_timeout_seconds
idle_timeout_seconds
communication_mode
```

不要把本地可执行路径、Python 环境、内部 command 直接作为普通用户工作流配置的核心字段。它们应来自可信节点包、插件 manifest 或受控的本地配置。

## 第一版落地范围

第一版目标：

```text
只使用 Private Runtime
reuse_scope 固定为 workflow
Job Object 边界固定为单个 WorkflowRun
Job Object Owner 固定为 EngineHost / Supervisor
节点可自行拉起外部程序
同一工作流内相同 runtime key 可复用
外部程序可按 idle/lease 自退出
工作流结束后整体清理当前工作流私有进程树
```

不做：

```text
后台长期常驻服务面板
远程服务调度
GPU 全局资源调度
复杂权限审批
当前工作流私有进程树之外的复用
工作流结束后继续保留外部程序
```

## 后续演进

后续可分阶段推进：

| 阶段 | 内容 |
| --- | --- |
| 0 | 固定 Private Runtime 边界和 manifest 草案 |
| 1 | 确认工作流级 Job Object 能覆盖 WorkflowRunProcess、NodeExecutorProcess 和外部子进程 |
| 2 | 增加最小 RuntimeManager helper 和外部程序 ready/health 协议 |
| 3 | 做一个假 OCR 或 echo service 节点进行 smoke |
| 4 | 接入真实 OCR/YOLO/SAM 中的一个低风险样例 |

## 当前暂定结论

当前推荐方案是：

```text
Private Runtime 是唯一当前目标。
Job Object 边界固定在单个 WorkflowRun。
Job Object 由 EngineHost / Supervisor 创建并持有。
单个工作流只管理自己拉起的外部程序。
工作流结束就整体清理。
节点 RuntimeManager 只做轻量启动、连接、复用和健康检查。
外部程序通过 lease / idle / parent pid 自行退出。
数据面只传引用，不通过 IPC 传大对象。
```

这条路线能保持 FlowWeaver 主程序边界干净，也能在当前重构阶段先稳定接入 OCR、YOLO、CLIP、SAM 这类重依赖节点。
