# FlowWeaver 外部程序数据协议方案

更新时间：2026-07-09

## 文档定位

本文记录外部程序节点与 OCR、YOLO、CLIP、SAM、截图服务等外部程序通信时的数据协议边界。

当前前提：

```text
生命周期使用 Private Runtime。
Job Object 边界固定为单个 WorkflowRun。
外部程序只在当前工作流内复用。
```

本文只讨论外部程序的数据输入、输出、启动参数和控制协议，不讨论跨工作流共享进程。

## 核心原则

协议分为两层：

```text
控制面：启动、ready、health、invoke、cancel、progress、result summary
数据面：图片、表格、JSON、大数组、tensor、mask、显存对象等真实大数据
```

核心原则：

```text
控制面传小消息。
数据面传引用。
大数据不经过主程序反复复制、解析、转换。
```

也就是说，不应把图片、mask、大 JSON、大表格 rows、大 tensor 直接塞进 HTTP body、stdio 或 named pipe。

外部程序和节点之间应传：

```text
数据在哪里
如何打开
如何解释
生命周期归谁
输出写到哪里
```

而不是直接传完整数据内容。

## 节点与外部程序职责边界

当前阶段建议把节点和外部程序的边界定义清楚：

```text
节点是 FlowWeaver 与外部程序之间的适配器和边界守门人。
外部程序是 OCR / YOLO / CLIP / SAM 等真实计算执行者。
共享内容由拥有数据或创建数据的一侧发布为 DataRef。
另一侧只按 DataRef 打开、读取、写入和关闭，不接收裸指针。
```

这里的“发布 DataRef”不是把大数据发出去，而是在当前 WorkflowRun 内创建或登记一个可解析的引用描述。

### 节点管理完成的内容

节点 RuntimeManager 或节点适配层负责完成：

```text
读取节点 manifest / runtime spec
选择 Python 环境、启动命令、cwd、env、模型路径、device
计算 runtime key，并决定当前工作流内是否复用已有 runtime
拉起外部程序，等待 ready，执行 health check
生成 request_id、lease、timeout、log_path、temp_dir
把 FlowWeaver 的输入引用转换成外部程序可理解的 DataRef
必要时创建 workflow-local shared memory / mmap / temp file
预分配或登记输出目标
发送 invoke / cancel / shutdown 等控制消息
校验外部程序返回的 output refs
把最终 output_refs 写入 NodeTaskResult
清理本节点创建的临时引用和句柄
```

节点不负责：

```text
理解 OCR / YOLO / SAM 模型内部逻辑
替外部程序执行推理
把大图、大 mask、大 JSON、大 tensor 反复解析成普通 JSON
把外部程序内部状态暴露给主程序
跨工作流复用外部程序
```

也就是说，节点的核心作用是：

```text
启动外部程序
翻译数据引用
控制请求生命周期
登记输出结果
保证当前 WorkflowRun 内的资源边界
```

### 外部程序完成的内容

节点拉起的外部程序负责完成：

```text
接收启动参数和环境变量
加载模型、语言包、checkpoint 或设备资源
暴露 ready / health 接口
接收 invoke 请求
解析 DataRef
打开输入数据
执行真实 OCR / 检测 / 分割 / embedding / 截图逻辑
把大输出写入约定的输出目标
返回小结果摘要、指标、错误码和 output refs
按 idle / lease / parent pid 规则自行软退出
```

外部程序不应：

```text
假设收到的是当前进程可用的裸内存地址
绕过节点随意访问工作流之外的路径或资源
把大结果直接塞进 result JSON
长期持有超过当前 WorkflowRun 生命周期的临时引用
要求主程序理解模型内部状态
```

### 共享内容由谁发布

共享内容的发布者应按“谁拥有、谁创建、谁登记”的原则决定。

| 共享内容 | 发布者 | 消费者 | 说明 |
| --- | --- | --- | --- |
| 已存在的 TableRef / BlobRef / FileRef | 上游节点或 WorkflowRun 数据存储 | 当前节点、外部程序 | 当前节点只转发或转换成外部程序可访问的 DataRef，不复制大数据 |
| 当前请求输入 SharedMemoryRef | 当前节点 RuntimeManager / 节点适配层 | 外部程序 | 节点创建共享内存，写入或映射输入数据，并把 name、offset、length、shape、dtype 等传给外部程序 |
| 预分配输出 BlobRef / FileRef / SharedMemoryRef | 当前节点 RuntimeManager / 节点适配层 | 外部程序 | 节点先分配可写目标，外部程序只负责写入，完成后返回状态和引用 |
| 外部程序生成的临时输出文件 | 外部程序先写入允许目录，节点随后登记 | 当前节点、下游节点 | 外部程序只能写到节点提供的 temp_dir / output_dir，节点校验后登记为 BlobRef 或 FileRef |
| 输出 TableRef | 当前节点适配层 | 下游节点 | 外部程序可输出 JSONL / Parquet / SQLite 等结构化文件，节点再登记成 TableRef 或表摘要 |
| TensorRef / GpuTensorRef | 后续专门 provider | 外部程序或下游节点 | 当前阶段只保留协议方向，不作为第一版承诺 |

第一版更推荐：

```text
节点预分配输出目标。
外部程序写入输出目标。
节点校验并登记 output_refs。
```

这样所有可持久化结果仍由 FlowWeaver 当前 WorkflowRun 记录，外部程序只负责计算和写入，不需要理解主程序的结果存储细节。

### 程序如何接收和解析

外部程序收到的 invoke 请求应只包含小 JSON 控制消息和 DataRef。

示例：

```json
{
  "request_id": "req_001",
  "workflow_run_id": "run_001",
  "node_task_id": "task_001",
  "inputs": [
    {
      "name": "image",
      "kind": "shared_memory_ref",
      "shared_memory_name": "fw_run_001_img_001",
      "offset": 0,
      "length": 6220800,
      "shape": [1080, 1920, 3],
      "dtype": "uint8",
      "format": "rgb",
      "access": "read"
    }
  ],
  "outputs": [
    {
      "name": "mask",
      "kind": "blob_ref",
      "blob_ref_id": "blob_mask_001",
      "write_uri": "runtime://run_001/write/blob_mask_001",
      "mime": "image/png",
      "access": "write"
    }
  ],
  "params": {
    "confidence": 0.35
  }
}
```

外部程序解析步骤建议固定为：

```text
1. 校验 request_id、workflow_run_id、runtime_id 或 lease_token。
2. 遍历 inputs，根据 kind 选择对应 reader。
3. 对 file_ref / blob_ref，打开节点提供的 path、uri 或本地临时文件。
4. 对 table_ref，读取节点提供的表快照、导出文件或受控查询入口。
5. 对 shared_memory_ref，按 name 打开共享内存，再按 offset、length、shape、dtype、format 解释为数组。
6. 执行模型处理。
7. 按 outputs 中的目标写入结果。
8. 返回 succeeded / failed、summary、metrics、output_refs、warnings。
9. 关闭文件句柄、共享内存 view、临时 reader / writer。
```

外部程序返回示例：

```json
{
  "request_id": "req_001",
  "status": "succeeded",
  "output_refs": [
    {
      "name": "mask",
      "kind": "blob_ref",
      "blob_ref_id": "blob_mask_001"
    }
  ],
  "summary": {
    "mask_count": 1
  },
  "metrics": {
    "duration_ms": 96
  },
  "warnings": []
}
```

程序只需要理解 DataRef schema 和自己的模型参数，不需要理解 FlowWeaver 的 DAG 调度、NodeTask 状态机或 Job Object 细节。

## 启动信息边界

节点 RuntimeManager 拉起外部程序时，需要明确运行环境和启动参数。

建议启动信息来自节点包 manifest 或受控配置，不要全部暴露成普通节点业务配置。

建议字段：

```text
runtime_id
workflow_run_id
workflow_process_id
node_task_id
python_env_path
python_executable
entry_command
cwd
env
model_path
device
startup_timeout_seconds
request_timeout_seconds
idle_timeout_seconds
communication_mode
endpoint
log_path
temp_dir
```

字段说明：

| 字段 | 说明 |
| --- | --- |
| runtime_id | 节点运行时 ID，用于日志、health 和 runtime key |
| workflow_run_id | 当前工作流运行 ID |
| workflow_process_id | 当前 WorkflowRunProcess ID |
| node_task_id | 当前任务 ID |
| python_env_path | 节点自己的 Python 环境路径 |
| python_executable | 实际解释器路径 |
| entry_command | 外部程序启动命令 |
| cwd | 外部程序工作目录 |
| env | 附加环境变量 |
| model_path | 模型、checkpoint 或语言包路径 |
| device | cpu、cuda、directml 等设备 |
| startup_timeout_seconds | 启动与模型加载超时 |
| request_timeout_seconds | 单次请求超时 |
| idle_timeout_seconds | 空闲自退出超时 |
| communication_mode | http、stdio_jsonl、named_pipe 等 |
| endpoint | HTTP 地址、pipe 名、stdio 标识等 |
| log_path | 外部程序日志路径 |
| temp_dir | 当前工作流或节点临时目录 |

## 控制面协议

控制面建议至少包含以下消息。

```text
ready
health
invoke
cancel
progress
result
shutdown
```

### Ready

用于启动后确认外部程序可用。

建议返回：

```json
{
  "runtime_id": "ocr.default",
  "ready": true,
  "state": "ready",
  "model_loaded": true,
  "model_fingerprint": "sha256:...",
  "device": "cuda:0"
}
```

不要只通过“进程存在”或“端口可连”判断 ready。

### Health

用于每次 invoke 前或固定周期检查。

建议返回：

```json
{
  "runtime_id": "ocr.default",
  "healthy": true,
  "ready": true,
  "model_loaded": true,
  "active_requests": 0,
  "last_error": null
}
```

### Invoke

用于发起实际处理请求。

Invoke 请求只传轻量引用和小参数。

示例：

```json
{
  "request_id": "req_001",
  "workflow_run_id": "run_001",
  "node_task_id": "task_001",
  "inputs": [
    {
      "kind": "file_ref",
      "uri": "runtime://run_001/images/a.png",
      "mime": "image/png"
    },
    {
      "kind": "table_ref",
      "table_ref_id": "table_001"
    }
  ],
  "params": {
    "confidence": 0.35,
    "max_results": 1000
  },
  "outputs": {
    "preferred_storage": "blob_ref",
    "output_name": "detections"
  }
}
```

### Result

结果只返回状态、摘要、指标和输出引用。

示例：

```json
{
  "request_id": "req_001",
  "status": "succeeded",
  "output_refs": [
    {
      "kind": "blob_ref",
      "blob_ref_id": "blob_mask_001"
    },
    {
      "kind": "table_ref",
      "table_ref_id": "table_detection_001"
    }
  ],
  "summary": {
    "detected_count": 12
  },
  "metrics": {
    "duration_ms": 182
  },
  "warnings": []
}
```

Result 不应携带大 payload。

## 数据面引用类型

第一阶段建议把外部程序输入输出统一表达为 DataRef 风格引用。

可用引用类型：

| 类型 | 用途 |
| --- | --- |
| TableRef | 表格数据、运行 SQL 表、内存表 |
| FileRef | 图片、视频、普通文件 |
| BlobRef | 大 JSON、mask、二进制输出、可视化图 |
| SharedMemoryRef | CPU 大数组、图像 batch、低延迟本机处理 |
| TensorRef | embedding、模型输入输出 tensor |
| GpuTensorRef | 显存对象或 CUDA IPC，后期再讨论 |

当前阶段优先使用：

```text
TableRef
FileRef
BlobRef
```

SharedMemoryRef、TensorRef、GpuTensorRef 可以先作为协议方向记录，不急于第一版实现。

## 输入边界

输入请求中可以传：

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

输入请求中不应传：

```text
大图 base64
完整视频帧列表
大表 rows
大 JSON 字符串
大 tensor bytes
```

### 裸内存地址问题

不要设计成传裸内存地址。

原因：

```text
不同进程有不同虚拟地址空间。
一个进程中的地址，在另一个进程中通常没有意义。
```

可跨进程传递的应是：

```text
shared_memory_name + offset + length + dtype + shape
mmap_file_path + offset + length
OS handle / duplicated handle
GPU IPC handle + device + shape + dtype
```

也就是说，协议中传的是可跨进程打开的句柄或引用，不是裸指针。

## 输出边界

小结果可以直接返回：

```text
状态
耗时
命中数量
少量 bbox
少量标签
错误码
输出引用 ID
```

大结果应写入引用：

```text
BlobRef：图片、mask、JSON 文件、视频片段
TableRef：结构化结果表
SharedMemoryRef：大数组、图像 batch
TensorRef：embedding、模型输出 tensor
```

### OCR 输出

推荐：

```text
少量文本块 -> Result summary 或 TableRef
大量 OCR 文本和版面结构 -> BlobRef(JSON/JSONL) + 可选 TableRef 摘要
可视化结果图 -> BlobRef
```

避免：

```text
把完整 OCR 大 JSON 塞进 NodeTaskResult.summary
把图片 base64 放进结果 JSON
```

### YOLO 输出

推荐：

```text
少量 bbox -> TableRef 或小 JSON summary
大量检测结果 -> TableRef 或 BlobRef(JSONL)
可视化图片 -> BlobRef
```

避免：

```text
反复把检测结果转成表再转成大 JSON
```

### SAM 输出

推荐：

```text
mask -> BlobRef(PNG/RLE/NPY) 或 SharedMemoryRef
mask summary -> TableRef 或小 JSON
可视化 overlay -> BlobRef
```

避免：

```text
把大型 mask 二维数组转成 JSON 数组
```

### CLIP 输出

推荐：

```text
embedding -> TensorRef 或 SharedMemoryRef
少量 top-k 相似度 -> TableRef 或小 JSON summary
```

避免：

```text
把大量 embedding 向量直接塞进普通 JSON
```

## 通信方式与数据面关系

HTTP、stdio、named pipe 都应只作为控制通道。

| 通信方式 | 适合内容 | 不适合内容 |
| --- | --- | --- |
| HTTP | ready、health、invoke、result summary、引用 ID | 大图片、大 tensor、大 mask |
| stdio JSONL | 单请求串行控制消息、小结果 | 并发请求、大数据、日志混杂 |
| named pipe | 本机 IPC 控制消息、后期二进制帧 | 第一版复杂数据面 |

性能优化优先级：

```text
第一优先：不传大对象，只传引用
第二优先：减少重复解析和格式转换
第三优先：必要时再换 named pipe / shared memory
```

不要在第一阶段因为担心 HTTP 开销，就提前引入复杂二进制协议。只要 HTTP 里传的是轻量引用，它的开销通常不是主要瓶颈。

## 生命周期与数据引用

由于当前使用 Private Runtime，所有外部程序和临时数据都归属当前 WorkflowRun。

因此 DataRef 需要明确生命周期：

```text
workflow_run_id
node_run_id
owner_process_id
storage_kind
provider_id
lifecycle_status
cleanup_policy
```

工作流结束后：

```text
运行结果 TableRef / BlobRef 可按主程序规则保留
临时 shared memory / mmap / temp file 应清理
外部程序进程树由 WorkflowRun Job 兜底清理
```

如果输出需要长期查看，应落到可持久化引用，例如：

```text
runtime_sql TableRef
file-backed BlobRef
run artifact file
```

不要把只能在外部程序进程存活时读取的内存对象，作为长期输出结果。

## 第一版建议

第一版数据协议目标：

```text
控制面使用 HTTP 或 stdio JSONL。
InvokeRequest 只传轻量引用和小参数。
InvokeResult 只传状态、摘要、指标和 output refs。
大图片、大 JSON、大 mask、大 tensor 均通过引用传递。
优先支持 TableRef / FileRef / BlobRef。
SharedMemoryRef / TensorRef / GpuTensorRef 先作为后续方向。
```

第一版不做：

```text
裸内存地址传递
显存对象跨进程复用
大对象塞进 HTTP body
大对象塞进 NodeTaskResult.summary
复杂二进制 IPC 协议
远程服务数据协议
```

## 当前暂定结论

外部程序数据协议的核心是：

```text
控制面小消息。
数据面引用化。
大数据原地不动。
主程序只看 refs，不反复解析和转换大对象。
```

这样既能保持主程序和外部节点低耦合，也能为后续 shared memory、mmap、tensor 和 GPU 句柄留下扩展空间。
