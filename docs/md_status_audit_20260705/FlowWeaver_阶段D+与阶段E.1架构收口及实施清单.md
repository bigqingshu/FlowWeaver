# FlowWeaver 阶段D+与阶段E.1架构收口及实施清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：对应阶段的代码矫正、运行主循环、节点执行、TableRef/运行数据、故障隔离和验收复核已经落地。
> 未实现：无本文件目标内的未实现项；早期文档中额外扩展仍按各自阶段后置。
> 原因：当前实现已被后续 I-P 与 UI 阶段持续复用。

## 一、文档目的

本文件用于重新划分 FlowWeaver 阶段D进入阶段E前的修改范围。

此前整理的《阶段D进入阶段E前收口修改清单》所列问题总体成立，但其中同时包含了：

```text
当前阶段D已有代码必须修复的问题
+
正式NodeExecutor阶段才需要建立的协议
```

如果把全部内容一次性作为阶段D硬验收，会导致阶段D范围过度扩大，并提前实现阶段E内容。

因此，本文件将后续工作重新划分为：

```text
D+1：状态一致性收口
D+2：进程所有权与生命周期收口
D+3：事件与实时通信边界收口
E.1：任务协议与最小NodeExecutor骨架
```

这样既保留原风险清单的价值，又避免一次性扩大阶段范围。

---

# 二、总体结论

当前阶段D主方向仍然正确：

```text
EngineHost / Supervisor
→ WorkflowRunProcess
→ DAG Controller
→ NodeRun状态推进
```

当前已经实现或正在形成：

```text
WorkflowRunProcess独立子进程
固定Revision加载
DAG构建
NodeRun初始化
上游成功后推进下游READY
WorkflowRun终态识别
进程心跳、取消和失联检测
```

当前不存在需要推翻的架构。

需要调整的是实施顺序：

```text
先修复当前控制面的状态一致性
再明确进程所有权
再收口事件发布链路
最后进入正式NodeExecutor
```

---

# 三、为什么增加D+阶段

原始阶段D硬验收重点是：

```text
空工作流可以启动并完成
WorkflowRunProcess崩溃不影响EngineHost
EngineHost可以识别失联进程
DAG基础控制状态可以建立
```

阶段E才正式开始：

```text
NodeExecutor进程
IPC任务提交
节点任务执行
NodeResult返回
进度、超时和取消
```

因此以下内容不应全部放入阶段D：

```text
完整NodeTask
完整NodeTaskResult
Executor任务IPC
假执行器
Executor心跳
Executor任务取消
```

这些应归入阶段E.1。

但阶段E接入前，当前控制面已有的状态竞争、终态复活、进程双写和事件链路问题必须先修复，因此增加一个小步、可控的：

```text
阶段D+
```

阶段D+不增加真实节点业务，只收口控制面基础。

---

# 四、D+1：状态一致性收口

## 4.1 目标

修复当前已有 WorkflowRun、WorkflowRevision 和 NodeRun 状态模型中的一致性风险。

D+1不实现：

```text
NodeExecutor
NodeTask
NodeTaskResult
完整IPC
假执行器
```

---

## 4.2 WorkflowRun与Revision强一致性

创建WorkflowRun时必须验证：

```text
revision存在
revision.workflow_id == workflow_id
```

`workflow_version`只能从Revision派生：

```text
workflow_version = revision.version
```

不允许调用者单独传入一个可能不一致的版本。

数据库关系应明确：

```text
workflow_runs.workflow_id
→ workflows.workflow_id

workflow_runs.revision_id
→ workflow_revisions.revision_id
```

### 验收

```text
Workflow A不能使用Workflow B的Revision创建运行
调用者不能伪造workflow_version
```

---

## 4.3 WorkflowRun与NodeRun改为SQL级CAS

当前不能继续采用：

```text
SELECT记录
→ Python比较state_version
→ 修改ORM对象
→ COMMIT
```

必须改为单条条件更新：

```sql
UPDATE workflow_runs
SET
    status = :new_status,
    state_version = state_version + 1
WHERE workflow_run_id = :workflow_run_id
  AND state_version = :expected_state_version
  AND status IN (:allowed_source_statuses);
```

NodeRun使用相同机制：

```sql
UPDATE node_runs
SET
    status = :new_status,
    state_version = state_version + 1
WHERE node_run_id = :node_run_id
  AND state_version = :expected_state_version
  AND status IN (:allowed_source_statuses);
```

通过：

```text
rowcount == 1
```

判断成功。

### 验收

```text
两个连接同时更新同一个state_version
只有一个成功
另一个返回状态冲突
```

---

## 4.4 增加明确状态转换规则

### WorkflowRun基础状态转换

```text
PENDING → RUNNING
RUNNING → SUCCEEDED
RUNNING → FAILED
RUNNING → CANCELLED
RUNNING → ABORTED
```

禁止：

```text
CANCELLED → SUCCEEDED
FAILED → SUCCEEDED
ABORTED → SUCCEEDED
```

### NodeRun基础状态转换

当前D+阶段至少明确：

```text
WAITING_DEPENDENCY → READY
READY → QUEUED
QUEUED → RUNNING
RUNNING → SUCCEEDED
RUNNING → FAILED
RUNNING → CANCELLED
RUNNING → TIMED_OUT
```

其中正式：

```text
READY → QUEUED
QUEUED → RUNNING
```

可以在E.1接入Executor时落地，但状态机约束应在D+1先定义。

---

## 4.5 禁止工作流终态复活

工作流成功只能：

```text
RUNNING → SUCCEEDED
```

如果WorkflowRun已经是：

```text
CANCELLED
FAILED
ABORTED
```

迟到节点结果只能：

```text
记录为迟到结果
拒绝修改WorkflowRun终态
拒绝继续推进DAG
```

### 验收

```text
WorkflowRun已经CANCELLED
最后一个节点再返回成功
WorkflowRun仍然保持CANCELLED
```

---

## 4.6 限制节点成功路径来源状态

当前普通节点成功只能从：

```text
RUNNING
LONG_RUNNING
```

进入：

```text
SUCCEEDED
```

不允许：

```text
WAITING_DEPENDENCY → SUCCEEDED
READY → SUCCEEDED
QUEUED → SUCCEEDED
```

后续如果支持缓存命中，可以单独建立：

```text
READY → SUCCEEDED
reason = CACHE_HIT
```

不能复用普通执行成功路径。

---

## 4.7 D+1测试清单

必须增加：

```text
Revision不属于Workflow时拒绝创建运行
workflow_version只能从Revision派生
WorkflowRun并发CAS只有一个成功
NodeRun并发CAS只有一个成功
CANCELLED不能被迟到成功结果复活
FAILED不能被迟到成功结果复活
ABORTED不能被迟到成功结果复活
非法NodeRun状态转换被拒绝
```

---

# 五、D+2：进程所有权与生命周期收口

## 5.1 目标

明确 Supervisor 与 WorkflowRunProcess 的职责，防止同一状态由两个进程共同修改。

D+2仍然不实现真实NodeExecutor。

---

## 5.2 明确状态唯一修改者

建议固定：

| 状态对象 | 唯一主要修改者 |
|---|---|
| `WorkflowProcessRecord` | `Supervisor` |
| `WorkflowRunRecord` | `WorkflowRunProcess` |
| `NodeRunRecord` | `WorkflowRunProcess` |
| Executor进程状态 | `Supervisor` |
| 节点结果应用 | `WorkflowRunProcess` |
| RuntimeEvent持久化与广播 | `EventRouter` |

WorkflowRunProcess不再调用：

```text
mark_workflow_process_exited()
```

WorkflowRunProcess只通过：

```text
IPC完成报告
操作系统exit_code
```

表达退出结果。

Supervisor根据：

```text
IPC报告
子进程poll结果
心跳状态
```

统一修改WorkflowProcessRecord。

---

## 5.3 限制每个WorkflowRun只有一个活动进程

启动WorkflowRunProcess前需要原子认领WorkflowRun。

建议增加：

```text
owner_process_id
process_generation
```

启动流程：

```text
WorkflowRun为PENDING
且没有活动owner
→ 原子分配owner_process_id
→ 创建WorkflowProcess
→ 启动子进程
```

并发重复启动：

```text
返回RUN_ALREADY_OWNED
```

恢复运行：

```text
旧WorkflowProcess已经FAILED或LOST
→ process_generation加1
→ 创建新的WorkflowProcess
```

### 验收

```text
两个并发启动请求
只有一个WorkflowRunProcess启动成功
```

---

## 5.4 增加进程Generation与栅栏

仅把旧进程标记为LOST，不能阻止它恢复后继续写数据库。

需要增加：

```text
owner_process_id
process_generation
fencing_token
```

WorkflowRunProcess修改WorkflowRun或NodeRun时，必须携带：

```text
process_id
process_generation
```

数据库更新条件：

```sql
WHERE owner_process_id = :process_id
  AND process_generation = :generation
```

Supervisor启动新generation后，旧进程自动失去写入资格。

### 验收

```text
进程A失联
Supervisor启动进程B
进程A恢复并提交状态
数据库拒绝进程A继续写入
```

---

## 5.5 完成Supervisor自动维护循环

现有：

```text
sweep_exited_children()
mark_lost_workflow_processes()
```

需要形成长期运行服务：

```python
Supervisor.start()
Supervisor.maintenance_loop()
Supervisor.close()
```

维护循环负责：

```text
扫描子进程退出
识别STARTING超时
识别RUNNING心跳失联
处理取消宽限期
强制终止超时进程
回收退出进程
处理异常WorkflowRun
```

FastAPI lifespan：

```text
EngineHost启动
→ Supervisor.start()

EngineHost关闭
→ Supervisor.close()
→ RuntimeStore.dispose()
→ InstanceLock.release()
```

---

## 5.6 补齐进程崩溃后的状态闭环

第一阶段推荐：

```text
WorkflowRunProcess异常退出
+
WorkflowRun尚未进入终态
→ WorkflowRun = ABORTED
```

NodeRun处理：

```text
SUCCEEDED
→ 保留

WAITING_DEPENDENCY / READY
→ 保留用于诊断或恢复

QUEUED / RUNNING / LONG_RUNNING
→ 标记INTERRUPTED或CANCELLED
```

如果当前不增加`INTERRUPTED`，可以先使用：

```text
CANCELLED
reason = WORKFLOW_PROCESS_LOST
```

### 验收

```text
WorkflowRunProcess崩溃后
WorkflowRun不会长期停留RUNNING
NodeRun不会长期停留RUNNING
```

---

## 5.7 修正进程启动入口

开发期方式：

```text
python -c
sys.path.insert(...)
stdout=DEVNULL
stderr=DEVNULL
```

应改为：

```powershell
python -m flowweaver.workflow_process.main
```

每个WorkflowRun建立独立日志：

```text
runtime/logs/workflow_runs/<workflow_run_id>.stdout.log
runtime/logs/workflow_runs/<workflow_run_id>.stderr.log
```

这样方便：

```text
wheel安装
exe打包
错误诊断
进程崩溃定位
```

---

## 5.8 D+2测试清单

```text
同一WorkflowRun并发启动只成功一个
旧generation写入被拒绝
WorkflowProcess状态只由Supervisor修改
STARTING进程无心跳时可以识别超时
RUNNING进程心跳失联时标记LOST
异常退出后WorkflowRun进入ABORTED
EngineHost关闭时子进程得到清理
stdout和stderr日志能够保存
```

---

# 六、D+3：事件与实时通信边界收口

## 6.1 目标

修复子进程直接写运行事件、WebSocket无法实时收到以及事件序号并发分配问题。

D+3只建立最小的进程控制和事件通道，不实现NodeTask传输。

---

## 6.2 增加RuntimeEventSink

DAG Controller和WorkflowRunProcess不应直接依赖：

```python
store.append_runtime_event(...)
```

应改为：

```python
class RuntimeEventSink:
    def emit(self, event: EventModel) -> None:
        ...
```

建议实现：

```text
DatabaseEventSink
用于单元测试和独立集成测试

IPCEventSink
用于正式WorkflowRunProcess
```

---

## 6.3 正式事件链路

```text
WorkflowRunProcess
→ IPCEventSink
→ EngineHost
→ EventRouter
→ runtime_events
→ WebSocket实时广播
```

正式运行时：

```text
只有EngineHost负责事件落库和广播
子进程只负责产生事件
```

---

## 6.4 最小IPC范围

D+3只需要传递：

```text
WORKFLOW_PROCESS_READY
WORKFLOW_PROCESS_HEARTBEAT
WORKFLOW_CANCEL_REQUEST
RUNTIME_EVENT
WORKFLOW_PROCESS_COMPLETED
WORKFLOW_PROCESS_FAILED
```

不需要在D+3实现：

```text
NODE_TASK_SUBMIT
NODE_TASK_RESULT
Executor进度
Executor取消
```

这些属于E.1。

---

## 6.5 修复事件序号

不能继续：

```text
SELECT MAX(sequence_number)
→ +1
→ INSERT
```

应使用SQLite原子自增：

```sql
sequence_number INTEGER PRIMARY KEY AUTOINCREMENT
```

`event_id`继续作为业务唯一标识。

### 验收

```text
并发事件无重复sequence_number
事件顺序可以用于REST断线补拉
WebSocket实时收到WorkflowRunProcess事件
子进程不直接写runtime_events
```

---

# 七、E.1：NodeTask与最小NodeExecutor骨架

## 7.1 目标

在D+1、D+2、D+3收口完成后，正式进入执行器阶段。

E.1才开始实现：

```text
NodeTask
NodeTaskResult
NodeExecutorProcess
任务IPC
结果幂等
迟到结果处理
```

---

## 7.2 NodeTask协议

至少包含：

```text
task_id
workflow_run_id
workflow_process_id
process_generation
node_run_id
node_instance_id
node_type
node_version
attempt
input_refs
config
timeout
```

提交任务时：

```text
READY → QUEUED
```

Executor确认开始时：

```text
QUEUED → RUNNING
```

---

## 7.3 NodeTaskResult协议

至少包含：

```text
result_id
task_id
node_run_id
attempt
executor_id
process_generation
status
output_refs
error
started_at
finished_at
```

推荐幂等键：

```text
task_id + result_id
```

重复结果：

```text
返回ALREADY_APPLIED
不修改state_version
不重复发NODE_FINISHED
不重复推进下游
```

拒绝：

```text
旧attempt
旧process_generation
非当前executor
节点已终态后的重复结果
```

---

## 7.4 假执行器属于E.1

假执行器用于验证任务协议，而不是阶段D硬验收。

它应模拟：

```text
立即成功
立即失败
延迟成功
延迟失败
重复返回
旧attempt返回
旧generation返回
超时后迟到返回
```

先验证完整DAG状态机，再实现正式多进程NodeExecutor。

---

## 7.5 E.1测试清单

```text
READY节点提交后进入QUEUED
Executor确认后进入RUNNING
成功结果只应用一次
失败结果正确终止或传播
重复结果不重复推进DAG
旧attempt结果被拒绝
旧generation结果被拒绝
迟到结果不能复活终态
分叉DAG可以并行提交
汇合节点等待全部上游成功
```

---

# 八、原风险清单重新分类

## 8.1 D+必须完成

```text
Revision一致性
WorkflowRun与NodeRun SQL级CAS
终态保护
状态唯一修改者
单活动WorkflowRunProcess
process_generation与栅栏
Supervisor维护循环
崩溃状态闭环
RuntimeEventSink
事件原子序号
正式进程入口
独立进程日志
READY与QUEUED语义定义
禁用节点DAG规则
NodeRun唯一约束
NodeRun批量幂等初始化
```

## 8.2 E.1完成

```text
NodeTask
NodeTaskResult
task_id
result_id
Executor IPC
最小NodeExecutor
结果幂等
迟到结果
假执行器
Executor心跳
节点取消
```

## 8.3 E后续完成

```text
Executor池
DedicatedWorker
Windows Job Object完整集成
资源限制
Office Worker
浏览器Worker
模型Worker
串口Worker
完整超时和重试策略
远程Executor
```

---

# 九、READY与QUEUED的阶段处理

D+阶段只修正语义：

```text
节点依赖满足
→ NodeRun = READY
```

此时不能发送：

```text
NODE_QUEUED
```

可以：

```text
发送NODE_READY
```

或者暂时不发送事件。

E.1真正提交NodeTask时才：

```text
READY → QUEUED
发送NODE_QUEUED
```

Executor确认开始后：

```text
QUEUED → RUNNING
发送NODE_STARTED
```

---

# 十、NodeRun初始化和禁用节点规则

## 10.1 NodeRun唯一约束

建议增加：

```sql
UNIQUE(
    workflow_run_id,
    node_instance_id,
    attempt
)
```

并保存：

```text
node_version
```

后续E.1可增加：

```text
task_id
executor_id
process_generation
```

---

## 10.2 批量幂等初始化

NodeRun初始化改为：

```text
开始事务
→ 查询已有NodeRun
→ 计算缺失节点
→ 批量插入
→ 提交
→ 提交成功后产生READY事件
```

重复执行不会产生：

```text
重复NodeRun
重复READY事件
```

---

## 10.3 禁用节点规则

第一阶段：

```text
禁用节点视为不存在
启用节点不得依赖禁用节点
```

发现：

```text
disabled A → enabled B
```

验证时直接报错：

```text
ENABLED_NODE_DEPENDS_ON_DISABLED_NODE
```

不能静默删除连接后把B当成根节点。

---

# 十一、推荐实施顺序

## 第一步：D+1 状态一致性

```text
Revision归属校验
workflow_version派生
WorkflowRun SQL级CAS
NodeRun SQL级CAS
终态保护
并发测试
```

## 第二步：D+2 进程所有权

```text
WorkflowProcess状态归Supervisor
单活动WorkflowRunProcess
process_generation
fencing_token
Supervisor维护循环
崩溃收尾
正式模块入口
独立日志
```

## 第三步：D+3 事件边界

```text
RuntimeEventSink
最小IPC控制通道
EngineHost统一事件落库
WebSocket实时广播
事件原子序号
```

## 第四步：E.1 任务与执行器

```text
NodeTask
NodeTaskResult
NodeExecutorProcess
结果幂等
迟到结果
假执行器验收
```

---

# 十二、后期开发收益

这样拆分的目的，是让后续功能可以在稳定边界上扩展。

## 12.1 方便替换不同执行器

只要遵守：

```text
NodeTask
NodeTaskResult
```

就可以接入：

```text
普通Python执行器
Office Worker
浏览器Worker
模型Worker
串口Worker
远程执行器
```

不需要修改DAG Controller。

## 12.2 方便故障恢复

通过：

```text
SQL级CAS
process_generation
fencing_token
结果幂等
持久NodeRun
```

可以处理：

```text
进程崩溃
EngineHost重启
Executor重试
迟到结果
重复消息
IPC中断
```

## 12.3 方便增加桌面UI和Web UI

事件统一经过EngineHost：

```text
桌面UI
Web UI
监控工具
日志工具
远程API客户端
```

都可以使用同一事件流，不需要直接读取子进程内部状态。

## 12.4 方便增加专用Worker

Office、浏览器、模型和串口等节点可以运行在独立Worker中。

某个Worker崩溃时，不直接破坏：

```text
EngineHost
其他WorkflowRun
其他Executor
```

## 12.5 方便审计和定位问题

每次节点执行都可以追踪：

```text
Workflow Revision
node_type
node_version
task_id
attempt
executor_id
process_generation
input_refs
output_refs
错误和退出原因
```

## 12.6 避免后期大规模返工

如果NodeExecutor实现后再修改：

```text
状态所有权
任务身份
事件链路
进程栅栏
结果幂等
```

会同时影响：

```text
Executor
Worker
UI
数据库
插件协议
共享节点
```

在D+阶段先固定这些边界，可以显著减少跨模块重构。

---

# 十三、当前下一步建议

当前不需要一次性执行整个清单。

下一步只执行：

```text
D+1：状态一致性收口
```

具体包括：

```text
修复WorkflowRun与Revision强一致性
workflow_version只从Revision派生
实现WorkflowRun SQL级CAS
实现NodeRun SQL级CAS
增加允许来源状态
禁止工作流终态复活
补齐并发和一致性测试
```

完成D+1并通过测试后，再进入D+2。

---

# 十四、最终结论

原始风险清单中的问题大部分成立，但不应全部作为阶段D一次性硬验收。

最终阶段划分为：

```text
D+1：状态一致性
D+2：进程所有权
D+3：事件边界
E.1：NodeTask与NodeExecutor
```

这样可以同时保证：

```text
不提前扩大阶段E
不忽略当前真实风险
不让SQLite演变为高频消息总线
不让多个进程共同修改同一状态
不让迟到和重复结果污染DAG
```

后续整体架构保持：

```text
EngineHost负责控制与进程管理
WorkflowRunProcess负责DAG和状态机
EventRouter负责事件落库和广播
NodeExecutor只负责执行NodeTask
节点只负责自身业务
```
