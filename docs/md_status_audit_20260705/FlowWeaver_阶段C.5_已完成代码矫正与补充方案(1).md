# FlowWeaver：阶段C.5已完成代码矫正与补充方案

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：对应阶段的代码矫正、运行主循环、节点执行、TableRef/运行数据、故障隔离和验收复核已经落地。
> 未实现：无本文件目标内的未实现项；早期文档中额外扩展仍按各自阶段后置。
> 原因：当前实现已被后续 I-P 与 UI 阶段持续复用。

> 文档状态：当前代码矫正实施稿
> 创建日期：2026-06-27
> 适用仓库：`bigqingshu/FlowWeaver`
> 当前基线：阶段A、阶段B、阶段C已完成控制面骨架
> 目标：在进入WorkflowRunProcess、NodeExecutor和运行数据面之前，矫正现有模型、数据库、API和启动方式，避免后续阶段发生大范围返工。

---

# 一、当前仓库状态判断

当前仓库没有明显偏离总体计划，已完成的内容主要包括：

```text
阶段A：
- pyproject.toml
- Pydantic公共协议模型
- 字符串枚举
- MessagePack序列化
- 统一错误模型
- 协议单元测试

阶段B：
- SQLAlchemy元数据模型
- Alembic初始化
- SQLite元数据库
- 工作流定义CRUD
- 工作流运行记录CRUD
- 数据库迁移测试

阶段C：
- FastAPI应用入口
- 统一API响应
- 工作流HTTP CRUD
- 工作流运行记录查询
- WebSocket连接骨架
- API集成测试
```

当前尚未进入：

```text
WorkflowRunProcess
NodeExecutor
RuntimeDataRegistry实际服务
SQLite运行表数据面
SharedPublication执行逻辑
PermissionManager服务
AuditService
Management UI
```

因此现在仍处于最适合调整基础模型的阶段。

---

# 二、本次矫正的核心目标

阶段C.5只做基础收口，不实现后续业务功能。

必须解决：

```text
1. 项目包名与产品名一致性
2. 工作流不可变版本
3. 严格工作流定义模型
4. DAG校验接口
5. SQLite运行参数
6. TableRef与数据库字段对齐
7. EngineHost启动与迁移解耦
8. 运行事件持久化
9. 状态迁移所有权
10. 静态检查和CI
```

阶段C.5完成后再进入：

```text
阶段D：WorkflowRunProcess
阶段E：NodeExecutor
阶段F：运行数据库与TableRef数据面
```

---

# 三、保留不改的部分

以下内容方向正确，应继续保留。

## 3.1 技术栈

```text
Python 3.12
FastAPI
Pydantic v2
MessagePack
SQLAlchemy 2
Alembic
SQLite
PySide6
pytest
```

## 3.2 IPC基础模型

继续保留：

```text
protocol_version
message_id
message_type
timestamp
workflow_run_id
node_run_id
correlation_id
payload
```

## 3.3 TableRef基础方向

继续保留：

```text
role
storage_kind
scope
mutability
provider_id
resource_profile_id
mount_id
logical_table_id
opaque_handle
schema
schema_fingerprint
version
capabilities
lifecycle_status
created_by
```

## 3.4 元数据表总体规划

继续保留：

```text
workflow_definitions
workflow_runs
node_runs
data_refs
shared_publications
shared_publication_members
input_snapshots
read_leases
audit_events
```

## 3.5 API分层

继续保持：

```text
UI / Web
→ HTTP / WebSocket
→ EngineHost
```

不得让UI直接读取SQLite或调用EngineHost内部对象。

---

# 四、矫正项一：Python包名统一

## 4.1 当前问题

仓库名和产品名是：

```text
FlowWeaver
```

Python包名目前是：

```text
workflow_platform
```

该名称过于通用，后续可能产生：

- import名称与项目名不一致；
- 与其他包名称冲突；
- 子进程入口和打包路径不直观；
- 日志、错误栈和插件模块定位不统一。

## 4.2 建议调整

将：

```text
src/workflow_platform/
```

改为：

```text
src/flowweaver/
```

同步修改：

```text
pyproject.toml
Alembic env导入
所有Python import
Uvicorn启动命令
测试导入
README
```

启动命令调整为：

```powershell
uvicorn --app-dir src flowweaver.api.app:create_app --factory --host 127.0.0.1 --port 8000
```

## 4.3 验收标准

```text
uv sync成功
全部测试通过
无workflow_platform残留导入
FastAPI可正常启动
Alembic迁移正常
```

> 此项应在进入多进程和节点注册之前完成。若决定不修改，则必须在项目规则中正式确认长期使用`workflow_platform`。

---

# 五、矫正项二：工作流不可变版本

## 5.1 当前问题

当前更新工作流时直接：

```text
覆盖definition_json
version + 1
```

这会造成：

```text
WorkflowRun记录引用version=1
但数据库中只剩version=3的定义
```

旧运行无法准确重放。

## 5.2 建议数据模型

拆成：

```text
workflows
└─ workflow_revisions
```

### workflows

保存逻辑工作流身份：

```text
workflow_id
name
current_revision_id
status
created_at
updated_at
```

### workflow_revisions

保存不可变版本：

```text
revision_id
workflow_id
version
definition_json
definition_hash
created_at
created_by
```

### workflow_runs

改为固定引用：

```text
workflow_run_id
workflow_id
revision_id
workflow_version
definition_hash
status
...
```

## 5.3 更新规则

修改工作流时：

```text
不覆盖旧revision
创建新revision
更新workflows.current_revision_id
```

删除工作流时：

```text
第一阶段优先软删除或归档
不得破坏历史WorkflowRun引用
```

## 5.4 API调整

建议：

```text
GET  /api/v1/workflows/{workflow_id}
GET  /api/v1/workflows/{workflow_id}/revisions
GET  /api/v1/workflows/{workflow_id}/revisions/{revision_id}
PUT  /api/v1/workflows/{workflow_id}
```

`PUT`创建新revision，不原地修改旧revision。

## 5.5 验收标准

```text
创建工作流后产生revision 1
更新后产生revision 2
revision 1仍可读取
旧WorkflowRun仍固定引用revision 1
删除逻辑工作流不破坏历史运行记录
```

---

# 六、矫正项三：严格WorkflowDefinition模型

## 6.1 当前问题

当前接口接受：

```python
definition: dict[str, Any]
```

任意字典都能入库，DAG执行阶段会承担大量错误处理。

## 6.2 建议模型

```python
class WorkflowDefinitionModel(BaseModel):
    schema_version: str
    nodes: list[NodeInstanceModel]
    connections: list[ConnectionModel]
    inputs: list[WorkflowInputModel] = []
    outputs: list[WorkflowOutputModel] = []
    failure_policy: FailurePolicyModel
```

### NodeInstanceModel

```text
node_instance_id
node_type
node_version
display_name
config
position
enabled
```

### ConnectionModel

```text
connection_id
source_node_id
source_port
target_node_id
target_port
```

### FailurePolicyModel

第一阶段支持：

```text
FAIL_FAST
CONTINUE_INDEPENDENT
SKIP_DEPENDENTS
```

## 6.3 第一阶段DAG规则

正式确定：

```text
只允许DAG
禁止循环
一个输入端口最多一个上游连接
一个输出端口可以连接多个下游
多输入通过命名端口表达
条件跳转暂不实现
循环节点暂不实现
Group节点暂不实现，只预留schema_version
```

## 6.4 验收标准

以下定义必须被拒绝：

```text
重复node_instance_id
连接不存在节点
连接不存在端口
输入端口多重连接
存在环
缺少必填输入
未知node_type
未知node_version
```

---

# 七、矫正项四：工作流验证接口

新增：

```text
POST /api/v1/workflows/{workflow_id}/validate
```

也支持在保存前验证草稿：

```text
POST /api/v1/workflows/validate
```

返回：

```json
{
  "valid": false,
  "errors": [
    {
      "code": "DAG_CYCLE_DETECTED",
      "path": "connections",
      "message": "Workflow contains a cycle"
    }
  ],
  "warnings": []
}
```

## 7.1 校验层次

```text
Schema校验
节点类型校验
节点版本校验
端口校验
DAG校验
必填输入校验
配置校验
```

## 7.2 验收标准

```text
合法工作流返回valid=true
非法工作流返回结构化错误
错误包含code、path和message
保存API不得保存未通过校验的正式revision
```

---

# 八、矫正项五：SQLite连接参数

## 8.1 当前问题

SQLite外键默认可能未启用，后续多个执行器并发访问运行数据库时也需要锁等待策略。

## 8.2 元数据库配置

每个连接启用：

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 5000;
```

## 8.3 运行数据库配置

后续运行数据库建议：

```sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA busy_timeout = 10000;
```

## 8.4 SQLAlchemy实现

通过：

```text
Engine connect event
```

统一设置PRAGMA，不在业务代码中重复。

## 8.5 验收标准

```text
外键违规写入被拒绝
WAL模式可查询
busy_timeout生效
两个连接并发读正常
短时间写锁等待后可成功
```

---

# 九、矫正项六：TableRef与data_refs字段对齐

## 9.1 当前问题

`TableRefModel`已有：

```text
resource_profile_id
mount_id
created_by_workflow_run_id
created_by_node_run_id
```

但数据库记录未完全对齐。

## 9.2 data_refs建议字段

```text
table_ref_id
workflow_run_id
node_run_id
role
storage_kind
scope
mutability
provider_id
resource_profile_id
mount_id
logical_table_id
opaque_handle_json
schema_json
schema_fingerprint
version
capabilities_json
lifecycle_status
created_at
published_at
released_at
```

## 9.3 索引建议

```text
workflow_run_id
node_run_id
logical_table_id
lifecycle_status
scope
```

## 9.4 唯一性建议

逻辑表版本唯一：

```text
(logical_table_id, version, workflow_run_id)
```

若后续逻辑表需要跨运行共享，再调整作用域。

## 9.5 验收标准

```text
TableRef可完整写入数据库
数据库读回后模型完全一致
resource_profile_id和mount_id不丢失
Schema序列化可稳定还原
```

---

# 十、矫正项七：EngineHostBootstrap

## 10.1 当前问题

当前FastAPI工厂直接执行Alembic迁移，后续可能造成：

```text
多进程重复迁移
打包后相对路径失效
启动职责混乱
迁移失败时服务状态不明确
```

## 10.2 新增启动层

```text
EngineHostBootstrap
├─ 获取单实例锁
├─ 加载配置
├─ 初始化数据目录
├─ 执行数据库备份检查
├─ 执行Alembic迁移
├─ 创建RuntimeStore
├─ 创建EventRouter
├─ 创建Supervisor
├─ 创建RuntimeDataRegistry
└─ 启动FastAPI
```

`create_app()`只接收已经初始化的服务：

```python
def create_app(container: ServiceContainer) -> FastAPI:
    ...
```

## 10.3 配置对象

新增：

```text
EngineConfig
data_dir
metadata_db_path
runtime_dir
log_dir
host
port
audit_level
```

## 10.4 验收标准

```text
迁移失败时API不启动
同一数据目录不能启动两个EngineHost
create_app测试无需执行真实迁移
工作目录变化不影响迁移路径
```

---

# 十一、矫正项八：EventRouter与运行事件持久化

## 11.1 当前问题

当前WebSocket只发送一次`ENGINE_READY`，没有真正的事件路由和重连基础。

## 11.2 区分两类记录

### runtime_events

用于UI实时状态和短期回放：

```text
event_id
sequence_number
event_type
timestamp
workflow_run_id
node_run_id
payload_json
```

### audit_events

用于长期审计事实：

```text
谁
对什么资源
执行了什么操作
结果如何
```

两者不能完全合并。

## 11.3 EventRouter职责

```text
发布事件
分配sequence_number
写入runtime_events
推送WebSocket订阅者
处理订阅过滤
```

## 11.4 WebSocket事件模型

必须完整包含：

```text
event_id
sequence_number
event_version
event_type
timestamp
workflow_run_id
node_run_id
payload
```

## 11.5 重连策略

第一阶段：

```text
UI重连
→ REST读取当前运行快照
→ WebSocket继续接收新事件
```

后续可支持：

```text
从sequence_number重放
```

## 11.6 验收标准

```text
事件可写入runtime_events
WebSocket订阅者能收到事件
多个订阅者互不影响
UI断开不影响EngineHost
重连后可通过REST恢复当前状态
```

---

# 十二、矫正项九：状态迁移所有权

## 12.1 核心原则

禁止API、Supervisor、WorkflowRunProcess和NodeExecutor同时任意修改同一业务状态。

## 12.2 建议所有权

### WorkflowRunProcess

拥有：

```text
NodeRun业务状态
DAG依赖状态
节点失败传播
WorkflowRun业务完成状态建议
```

### Supervisor

拥有：

```text
进程健康状态
执行器启动和退出
进程失联
强制终止
```

### EngineHost

负责：

```text
持久化协调
最终状态确认
API查询
异常恢复标记
```

### NodeExecutor

只能上报：

```text
任务已接受
任务心跳
进度
完成
失败
```

不能直接写元数据库状态。

## 12.3 状态版本

为`workflow_runs`和`node_runs`增加：

```text
state_version
```

状态更新采用条件更新：

```sql
UPDATE node_runs
SET status=?, state_version=state_version+1
WHERE node_run_id=? AND state_version=?;
```

避免旧消息覆盖新状态。

## 12.4 验收标准

```text
非法状态跳转被拒绝
旧state_version更新失败
Executor不能直接更新数据库
重复完成消息不会覆盖TIMED_OUT
```

---

# 十三、矫正项十：节点注册与版本

虽然NodeExecutor尚未实现，但节点注册必须提前定义。

## 13.1 NodeRegistry

```text
node_type
node_version
display_name
config_schema
input_ports
output_ports
execution_mode
default_timeout
retry_safe
implementation_path
```

## 13.2 节点标识规则

示例：

```text
core.generate_test_table@1.0
core.filter_rows@1.0
core.replace_field@1.0
core.publish_shared_tables@1.0
```

工作流保存：

```text
node_type
node_version
```

不得保存Python类名作为唯一标识。

## 13.3 验收标准

```text
重复注册被拒绝
未知节点类型校验失败
未知节点版本校验失败
Registry可列出节点摘要
```

---

# 十四、矫正项十一：IPC幂等与消息限制

## 14.1 消息去重

每个接收方维护短期：

```text
processed_message_ids
```

重复消息：

```text
不得重复执行节点
返回原结果或ACK
```

## 14.2 correlation_id

规则：

```text
请求消息生成message_id
响应消息correlation_id = 请求message_id
```

## 14.3 消息大小

第一阶段限制：

```text
单条IPC消息最大1 MiB
```

超出则拒绝并返回：

```text
IPC_MESSAGE_TOO_LARGE
```

表数据不得放入IPC消息。

## 14.4 验收标准

```text
重复NODE_TASK_SUBMIT不重复执行
重复NODE_TASK_COMPLETED不重复发布
超大消息被拒绝
请求与响应可通过correlation_id关联
```

---

# 十五、矫正项十二：运行数据库前置规则

虽然运行数据库在后续阶段实现，但以下规则现在必须写入方案。

## 15.1 每个WorkflowRun独立数据库

```text
runtime/workflow_runs/<workflow_run_id>.db
```

## 15.2 节点不得原地修改输入表

第一阶段采用：

```text
输入表只读
每个节点创建新输出表
```

这样能：

- 减少并发写冲突；
- 保证版本清晰；
- 简化回滚；
- 支持不可变血缘。

## 15.3 STAGING与PUBLISHED

同一个结果：

```text
table_ref_id保持不变
lifecycle_status从STAGING切换为PUBLISHED
```

新的内容版本：

```text
创建新的table_ref_id
logical_table_id相同
version递增
```

## 15.4 验收标准

```text
节点不能更新输入物理表
两个并行节点可写各自输出表
STAGING不可被下游读取
PUBLISHED后不可原地修改
```

---

# 十六、矫正项十三：行ID与字段ID

## 16.1 字段ID

继续保留稳定：

```text
field_id
```

字段重命名时：

```text
field_id不变
name变化
```

## 16.2 行ID

运行表自动增加隐藏字段：

```text
_fw_row_id
```

规则：

```text
首次进入工作流时生成
筛选、复制时保留
简单字段修改时保留
聚合时重新生成
多表合并按规则生成新ID
UI默认隐藏
```

## 16.3 验收标准

```text
筛选后row_id保持
字段替换后row_id保持
聚合结果row_id重新生成
row_id全表唯一
```

---

# 十七、矫正项十四：数据类型系统

第一阶段统一字段类型：

```text
NULL
BOOLEAN
INTEGER
FLOAT
DECIMAL
STRING
BYTES
DATE
DATETIME
JSON
```

每个Provider负责映射底层类型。

SQLite映射示例：

```text
INTEGER → INTEGER
FLOAT → REAL
DECIMAL → TEXT或规范化字符串
STRING → TEXT
BYTES → BLOB
DATE → TEXT ISO-8601
DATETIME → TEXT UTC ISO-8601
JSON → TEXT JSON
BOOLEAN → INTEGER 0/1
```

必须明确：

```text
空值规则
数字精度
日期时区
JSON序列化
```

---

# 十八、矫正项十五：共享表生命周期前置规则

## 18.1 WorkflowRun结束不等于数据库可删除

只要运行数据库中仍存在：

```text
SHARED_SCOPE数据
活跃ReadLease
保留策略
调试固定
```

运行数据库文件就不能删除。

## 18.2 多表发布采用原子可见性

流程：

```text
1. 所有成员TableRef已PUBLISHED
2. 创建SharedPublication(STAGING)
3. 写入全部成员关系
4. 完整性校验
5. SharedPublication切换为PUBLISHED
6. 发送事件
```

读取方只查询：

```text
status = PUBLISHED
```

## 18.3 崩溃恢复

长时间停留：

```text
SharedPublication(STAGING)
```

应由清理任务标记：

```text
ORPHANED
```

并根据成员引用情况清理。

---

# 十八-A、数据共享节点与表租约管理接口

> 本节记录已经确认的数据共享边界。
> 若本节与前文关于共享发布、租约或生命周期的职责描述发生冲突，以本节为准。

## 18A.1 核心结论

数据共享采用：

```text
共享业务逻辑全部位于节点内
+
主程序只提供一个通用表租约管理接口
```

主程序唯一新增的共享相关模块为：

```text
TableLeaseManager
表租约管理接口
```

该接口只负责不同进程之间的表占用判断和竞态保护。

主程序负责：

```text
读取租约申请
写入租约申请
租约心跳
租约释放
租约超时回收
活跃读取数量查询
表是否允许覆盖或删除
跨进程原子占用判断
```

主程序不负责：

```text
共享模式判断
需求消费者数量
完成消费者数量
完成标志计算
共享通道业务状态
V1/V2版本创建规则
实时覆盖或阻塞决策
累计差异SQL
消费者确认时机
旧共享数据删除
节点内部循环
```

以上全部由数据共享节点负责。

---

## 18A.2 数据共享节点组成

数据共享功能由三个节点组成：

```text
数据共享发布节点
数据共享接收节点
数据共享完成确认节点
```

### 数据共享发布节点

负责：

```text
接收源TableRef
设置共享名称
设置需求消费者数量
写入共享数据
维护共享协议字段
选择阻塞或实时模式
管理共享数据版本
检查完成数量
在满足条件后亲自删除共享数据
```

### 数据共享接收节点

负责：

```text
查找目标共享数据
申请读取租约
固定本次读取的表版本
输出TableRef给下游
保存消费者身份
按照确认策略提交完成或输出确认凭证
释放读取租约
```

### 数据共享完成确认节点

负责：

```text
接收确认凭证
确认指定消费者已处理完成
保证重复执行不重复计数
更新完成引用数量
重新计算完成标志
释放对应读取租约
```

---

## 18A.3 跨进程通信方式

不同进程中的共享节点不直接传递Python对象，也不直接调用对方函数。

通信链路：

```text
源共享节点进程
    │
    ├─ 数据：TableRef指向数据库表或内存表
    └─ 占用：TableLeaseManager
             │
消费者节点进程
```

消费者读取共享数据时，以下操作必须原子完成：

```text
确定当前共享表版本
+
建立读取租约
+
返回固定TableRef
```

禁止：

```text
先查询当前版本
→ 隔一段时间再申请租约
```

否则源节点可能在中间覆盖或删除该表。

---

## 18A.4 表租约类型

### READ_LEASE

表示消费者正在读取或处理指定表。

多个消费者可以同时持有READ_LEASE。

### WRITE_LEASE

表示节点准备：

```text
覆盖
清空
替换
删除
```

指定表。

同一张表同时只能存在一个WRITE_LEASE。

### 冲突规则

| 当前状态 | 新READ_LEASE | 新WRITE_LEASE |
|---|---:|---:|
| 无租约 | 允许 | 允许 |
| 存在READ_LEASE | 允许 | 拒绝 |
| 存在WRITE_LEASE | 拒绝 | 拒绝 |

---

## 18A.5 TableLeaseManager接口

建议接口：

```python
class TableLeaseManager:
    def acquire_read_lease(
        self,
        *,
        table_ref_id: str,
        workflow_run_id: str,
        node_run_id: str,
        consumer_key: str | None,
        ttl_seconds: int,
    ) -> "TableLease":
        ...

    def acquire_current_read_lease(
        self,
        *,
        current_table_resolver: "CurrentTableResolver",
        workflow_run_id: str,
        node_run_id: str,
        consumer_key: str,
        ttl_seconds: int,
    ) -> tuple["TableLease", "TableRefModel"]:
        ...

    def try_acquire_write_lease(
        self,
        *,
        table_ref_id: str,
        workflow_run_id: str,
        node_run_id: str,
        ttl_seconds: int,
    ) -> "TableLease | None":
        ...

    def heartbeat(
        self,
        lease_id: str,
        *,
        extend_seconds: int,
    ) -> None:
        ...

    def release(
        self,
        lease_id: str,
    ) -> None:
        ...

    def count_active_read_leases(
        self,
        table_ref_id: str,
    ) -> int:
        ...

    def has_active_write_lease(
        self,
        table_ref_id: str,
    ) -> bool:
        ...

    def expire_stale_leases(
        self,
        *,
        now: datetime,
    ) -> int:
        ...
```

其中：

```text
acquire_current_read_lease
```

必须在同一个事务或等价原子操作中完成：

```text
解析当前表
建立READ_LEASE
返回TableRef
```

---

## 18A.6 租约数据模型

建议字段：

```text
lease_id
table_ref_id
lease_type
workflow_run_id
node_run_id
consumer_key
status
acquired_at
heartbeat_at
expires_at
released_at
```

状态：

```text
ACTIVE
RELEASED
EXPIRED
REVOKED
```

必须区分：

```text
active_read_count
= 当前仍在读取或处理的租约数量

completed_refs
= 已经成功完成确认的唯一消费者数量
```

租约只解决占用和竞态，不承担消费者完成计数。

---

## 18A.7 统一共享输出协议

源共享节点对外输出的逻辑表，前四列固定为：

| 顺序 | 字段 | 含义 |
|---:|---|---|
| 1 | `_fw_share_completed` | 是否达到需求完成数量 |
| 2 | `_fw_required_refs` | 源节点要求的消费者完成数量 |
| 3 | `_fw_completed_refs` | 已独立完成确认的唯一消费者数量 |
| 4 | `_fw_source_time` | 源工作流本轮输出时间 |

建议类型：

```text
_fw_share_completed：INTEGER，0或1
_fw_required_refs：INTEGER，最小为0
_fw_completed_refs：INTEGER，最小为0
_fw_source_time：TEXT，UTC ISO 8601
```

业务字段从第5列开始。

完成状态计算：

```text
required_refs == 0
→ completed = 1
```

或：

```text
completed_refs >= required_refs
→ completed = 1
```

其他情况：

```text
completed = 0
```

`_fw_share_completed`由共享节点计算，消费者不得直接修改。

---

## 18A.8 协议字段的物理实现

前四列是对外逻辑协议，不要求在每行业务数据中重复物理存储。

推荐物理结构：

```text
共享控制记录
+
业务数据表
+
逻辑输出视图
```

示例：

```text
_fw_share_meta
orders_data_v1
orders_shared_v1 VIEW
```

视图示例：

```sql
SELECT
    meta.completed AS _fw_share_completed,
    meta.required_refs AS _fw_required_refs,
    meta.completed_refs AS _fw_completed_refs,
    meta.source_time AS _fw_source_time,
    data.*
FROM orders_data_v1 AS data
CROSS JOIN _fw_share_meta AS meta;
```

优点：

```text
下游仍看到统一前四列
控制字段只更新一条记录
大表不需要整表更新完成数量
业务数据和共享控制状态物理解耦
```

共享控制表、业务表和视图都由共享节点创建和维护，不由主程序统一管理。

---

## 18A.9 消费者身份与幂等确认

消费者需要稳定身份：

```text
consumer_key
=
消费工作流ID
+
接收共享节点实例ID
```

示例：

```text
workflow_B.receive_orders
```

同一个消费者对同一个发布版本只能确认一次。

共享节点内部建议维护：

```text
publication_id
consumer_key
workflow_run_id
node_run_id
completed_at
status
```

唯一约束：

```text
UNIQUE(publication_id, consumer_key)
```

`completed_refs`应等于：

```text
COUNT(DISTINCT consumer_key)
WHERE status = SUCCESS
```

可以缓存计数，但独立确认记录才是业务事实来源。

这张确认表属于共享节点内部数据，不属于TableLeaseManager。

---

## 18A.10 发布节点基础配置

### 共享身份

```text
共享名称
共享逻辑表名
可选共享通道标识
```

### 消费需求

```text
需求消费者数量 required_refs
消费者计数模式
```

支持：

```text
COUNT_ONLY
任意N个唯一消费者完成即可

NAMED_CONSUMERS
指定消费者全部完成
```

第一阶段可以只实现：

```text
COUNT_ONLY
```

### 存储类型

```text
RUNTIME_SQL
MEMORY_TABLE
```

第一阶段优先：

```text
RUNTIME_SQL
```

### 循环和超时

```text
检查间隔
最长等待时间
读取租约TTL
写入租约TTL
租约心跳间隔
数据库锁重试间隔
删除失败重试次数
```

---

## 18A.11 模式一：BLOCKING_BATCH

用途：

```text
数据准确性优先
不允许跳过批次
上一批未完成，下一批不能继续
```

流程：

```text
源节点接收本批数据
→ 获取WRITE_LEASE
→ 写入STAGING
→ 设置required_refs
→ completed_refs初始化为0
→ 设置source_time
→ 原子发布
→ 释放WRITE_LEASE
→ 节点内部等待消费者
```

完成和删除条件：

```text
completed_refs >= required_refs
AND
active_read_count == 0
```

满足后：

```text
源节点申请WRITE_LEASE
→ 获得后再次检查完成数量和活跃租约
→ 标记DELETE_PENDING
→ 源节点亲自删除业务表和视图
→ 保留必要最小历史
→ 标记DELETED
→ 释放WRITE_LEASE
→ 进入下一轮
```

当前表仍被读取时：

```text
源节点继续等待
```

主程序不会替源节点决定继续、删除或失败。

---

## 18A.12 模式二：CONTINUOUS_LATEST

用途：

```text
源工作流不能停止
消费者只需要最新数据
允许跳过旧版本
```

### 当前表未被占用

```text
active_read_count == 0
→ 源节点获取WRITE_LEASE
→ 清空、替换或重建当前表
→ 写入最新数据
→ 更新source_time
→ 发布新代次
→ 释放WRITE_LEASE
```

物理表名可以复用，但每次成功替换必须产生新的：

```text
generation
或table_ref_id
```

用于审计和固定读取版本。

### 当前表正在被读取

```text
active_read_count > 0
→ 当前表不可覆盖
→ 源节点创建V2
→ 写入最新数据
→ 原子切换当前指针到V2
→ 新消费者读取V2
→ 原消费者继续读取V1
```

### 旧版本删除

```text
不是当前版本
AND
active_read_count == 0
AND
成功取得WRITE_LEASE
```

满足后由源节点删除。

实时最新模式不强制要求旧版本达到`completed_refs`。

---

## 18A.13 模式三：CONTINUOUS_ACCUMULATE

用途：

```text
源数据持续变化
需要保留新增或变化记录
消费者读取当前累计结果
```

用户配置：

```text
唯一键字段
比较字段
忽略字段
重复数据处理方式
追加时间字段
```

第一阶段基础规则：

```text
唯一键和比较字段完全相同
→ 不写入

唯一键不存在
→ 追加

唯一键相同但比较字段不同
→ 追加一条变化记录
```

当前累计表未被占用：

```text
源节点取得WRITE_LEASE
→ SQL追加差异
→ 更新输出时间和代次
→ 释放WRITE_LEASE
```

当前累计表正在被占用：

```text
创建V2
→ 复制V1累计数据
→ 追加本轮差异
→ 切换当前指针到V2
→ V1无人读取后由源节点删除
```

完整INSERT、UPDATE、DELETE变化日志可以后续扩展，但仍属于节点逻辑。

---

## 18A.14 接收节点配置

```text
共享名称
consumer_key
读取策略
无数据策略
租约TTL
租约心跳间隔
完成确认策略
是否允许重复读取同一代次
输出逻辑表名
```

读取策略：

```text
LATEST
读取当前最新版本

NEXT
等待比last_consumed_generation更新的版本

EXACT
读取指定版本
```

第一阶段至少支持：

```text
LATEST
NEXT
```

无数据策略：

```text
WAIT
RETURN_EMPTY
FAIL
SKIP
```

---

## 18A.15 接收节点流程

```text
查询共享节点维护的当前发布信息
→ 调用acquire_current_read_lease
→ 原子获得固定TableRef和READ_LEASE
→ 读取并输出固定版本
→ 持续发送租约心跳
→ 根据确认策略进行确认
→ 释放租约
→ 保存last_consumed_generation
```

消费者取得V1的租约后，本次处理始终使用V1。

源节点发布V2后，当前消费者也不能中途切换。

---

## 18A.16 完成确认策略

### ACK_ON_READ

数据读取或映射成功后立即确认。

适合非关键实时数据。

### ACK_ON_RECEIVER_SUCCESS

接收节点自身全部逻辑完成后确认。

不代表整个消费工作流已经成功。

### EXPLICIT_ACK

接收节点输出：

```text
receipt_ref
```

由后续“数据共享完成确认节点”提交确认。

`receipt_ref`至少包含：

```text
publication_id
table_ref_id
consumer_key
lease_id
generation
```

严格阻塞模式推荐：

```text
EXPLICIT_ACK
```

---

## 18A.17 数据共享完成确认节点

输入：

```text
receipt_ref
处理结果
可选错误信息
```

成功确认流程：

```text
检查publication_id和consumer_key
→ 插入唯一完成记录
→ 已存在则返回ALREADY_CONFIRMED
→ 更新或重算completed_refs
→ 更新completed标志
→ 释放对应READ_LEASE
```

失败确认：

```text
记录FAILED
不增加completed_refs
由源共享节点按配置继续等待、失败或人工处理
```

确认必须幂等。

---

## 18A.18 节点内部循环

### 源共享节点循环

```text
生成本轮输入数据
→ 检查当前共享版本
→ 请求WRITE_LEASE

成功：
    按模式写入、覆盖或追加
    更新共享协议字段
    发布并释放租约

失败：
    BLOCKING_BATCH：
        节点内部等待并重试

    CONTINUOUS_LATEST：
        节点内部创建新版本

    CONTINUOUS_ACCUMULATE：
        节点内部复制累计版本并追加差异
```

### 接收共享节点循环

```text
申请READ_LEASE
→ 获得固定TableRef
→ 读取和处理
→ 按策略确认
→ 释放租约
```

这些循环全部属于节点实现。

主程序只响应租约操作。

---

## 18A.19 共享节点内部状态

共享节点可使用：

```text
STAGING
READY
COMPLETED
RETIRED
DELETE_PENDING
DELETED
ORPHANED
FAILED
```

阻塞模式：

```text
STAGING
→ READY
→ COMPLETED
→ DELETE_PENDING
→ DELETED
```

实时模式旧版本：

```text
READY
→ RETIRED
→ DELETE_PENDING
→ DELETED
```

这些是共享节点业务状态，不应扩展为EngineHost通用状态机。

---

## 18A.20 删除责任

共享数据由源共享节点亲自删除。

主程序不主动删除正常共享数据。

源节点删除流程：

```text
检查完成条件
→ 检查active_read_count为0
→ 申请WRITE_LEASE
→ 获得租约后再次检查
→ 标记DELETE_PENDING
→ 删除业务表和共享视图
→ 更新最小历史记录
→ 标记DELETED
→ 释放WRITE_LEASE
```

删除失败：

```text
保持DELETE_PENDING
记录错误
由源节点后续重试
```

主程序只保证删除时没有消费者进入，不决定删除时机。

---

## 18A.21 异常处理

### 消费者进程崩溃

```text
租约停止心跳
→ 超时后TableLeaseManager标记EXPIRED
→ completed_refs不增加
→ 源节点按自身策略处理
```

### 源节点写入时崩溃

```text
STAGING不对消费者可见
→ WRITE_LEASE超时
→ 共享节点恢复时标记ORPHANED或清理
```

### 消费者长期不确认

源节点可配置：

```text
继续等待
超时失败
跳过缺失消费者
人工确认
继续下一轮但保留旧数据
```

严格模式默认：

```text
超时失败
不自动跳过
```

### 重复确认

```text
不重复计数
返回ALREADY_CONFIRMED
```

### 数据库锁冲突

共享节点负责等待、退避和失败策略。

租约接口只返回明确的冲突结果。

---

## 18A.22 数据保留策略

共享节点可配置：

```text
完成且无人读取后立即删除
完成后保留N分钟
保留最近N个版本
失败时固定保存
始终保留
手动删除
```

默认建议：

```text
BLOCKING_BATCH：
完成并无租约后删除

CONTINUOUS_LATEST：
保留当前版本，删除无人读取的旧版本

CONTINUOUS_ACCUMULATE：
保留当前累计版本，删除失效旧版本
```

保留策略不进入TableLeaseManager。

---

## 18A.23 执行模式

共享发布节点可能持续循环或长时间等待，建议：

```text
DEDICATED_WORKER
```

接收节点：

```text
立即读取：
PROCESS_POOL

长期等待NEXT：
DEDICATED_WORKER
```

节点等待期间必须持续上报：

```text
heartbeat
current_stage
waiting_reason
last_generation
active_read_count
completed_refs
required_refs
```

避免被误判为卡死。

---

## 18A.24 审计边界

主程序通用租约审计只记录：

```text
租约申请
租约授予
租约冲突
租约心跳
租约释放
租约超时
租约撤销
```

共享节点自行记录：

```text
共享通道创建
版本发布
消费者确认
完成数量变化
当前版本切换
旧版本删除
差异追加
共享业务超时
孤儿版本处理
```

主程序不得解析共享节点业务字段。

---

## 18A.25 分阶段实施范围

阶段C.5只实施：

```text
TableLeaseManager接口
READ_LEASE和WRITE_LEASE协议
跨进程原子申请规则
租约记录和超时回收
租约冲突测试
接口审计
```

阶段C.5不得实施：

```text
共享节点内部循环
消费者完成业务计数
共享版本业务状态机
实时覆盖策略
累计差异逻辑
源节点删除策略
```

共享节点第一阶段后续实现：

```text
单表共享
SQLite存储
BLOCKING_BATCH
CONTINUOUS_LATEST
COUNT_ONLY消费者数量
ACK_ON_READ
EXPLICIT_ACK
版本创建和源节点删除
基础超时
```

后续扩展：

```text
NAMED_CONSUMERS
CONTINUOUS_ACCUMULATE
完整变化日志
多表原子发布
复杂历史固定
人工干预界面
```

---

## 18A.26 核心验收场景

### 读取与删除竞态

```text
消费者准备读取V1
源节点同时准备删除V1
```

要求：

```text
READ_LEASE与WRITE_LEASE只能一方成功
不会返回已删除的TableRef
```

### 多消费者读取

```text
A、B同时读取V1
```

要求：

```text
A、B均可获得READ_LEASE
源节点无法获得WRITE_LEASE
```

### 消费者崩溃

```text
获得READ_LEASE后进程退出
```

要求：

```text
租约超时后自动EXPIRED
表不会永久占用
completed_refs不增加
```

### 重复确认

```text
同一个consumer_key确认两次
```

要求：

```text
completed_refs只增加一次
```

### 阻塞一致性闭环

```text
required_refs = 2
A完成
B完成
全部READ_LEASE释放
```

要求：

```text
源节点获得WRITE_LEASE
源节点亲自删除数据
主程序不主动删除共享数据
```

### 实时版本切换

```text
消费者正在读取V1
源节点产生最新数据
```

要求：

```text
源节点不能覆盖V1
源节点创建V2
新消费者读取V2
V1无人读取后由源节点删除
```

---

## 18A.27 最终边界

数据一致性闭环：

```text
源共享节点发布
→ 设置required_refs
→ 消费者取得READ_LEASE
→ 消费者固定读取TableRef
→ 消费者独立完成确认
→ completed_refs达到required_refs
→ 所有READ_LEASE释放或过期
→ 源节点取得WRITE_LEASE
→ 源节点亲自删除共享数据
```

最终确认：

```text
主程序：
仅新增TableLeaseManager表租约管理接口

共享节点：
负责全部共享业务、消费者计数、版本、循环和删除
```

不得把以下逻辑放入EngineHost核心：

```text
共享完成判断
共享业务状态机
消费者需求数量管理
实时覆盖决策
累计差异处理
源数据删除决策
```

---

# 十九、矫正项十六：API View模型

当前路由不应长期直接返回RuntimeStore内部dataclass。

新增：

```text
WorkflowSummaryView
WorkflowDetailView
WorkflowRevisionView
WorkflowRunView
NodeRunView
TableRefSummaryView
PublicationSummaryView
RuntimeEventView
```

FastAPI路由必须设置：

```text
response_model
```

这样内部数据库字段变化不会直接破坏桌面UI和Web。

---

# 二十、矫正项十七：本机API基础安全

即使只监听：

```text
127.0.0.1
```

也建议加入：

```text
随机本地访问令牌
Authorization头
WebSocket token
Origin校验
CORS默认关闭
```

启动时生成或读取：

```text
local_api_token
```

UI从本机配置文件读取。

第一阶段不做：

```text
用户账号
角色系统
远程登录
```

---

# 二十一、矫正项十八：EngineHost单实例与数据目录

## 21.1 单实例

同一用户数据目录只允许一个EngineHost。

建议使用：

```text
文件锁
端口检查
PID记录
```

## 21.2 正式数据目录

不要长期依赖仓库当前目录。

建议：

```text
FlowWeaverData/
├─ config/
├─ metadata/
├─ runtime/
│  └─ workflow_runs/
├─ logs/
├─ backups/
└─ temp/
```

开发环境允许通过配置指定：

```text
./runtime
```

## 21.3 验收标准

```text
第二个EngineHost启动被拒绝
旧PID失效后可恢复
不同数据目录可分别启动
```

---

# 二十二、矫正项十九：日志、磁盘与资源监控

阶段C.5先建立配置和指标，不立即做完整强制资源限制。

需要预留：

```text
max_concurrent_workflows
max_executors_per_workflow
max_ipc_message_bytes
max_runtime_db_bytes
max_log_file_bytes
staging_ttl_seconds
orphan_cleanup_interval
```

日志要求：

```text
JSON Lines
轮转
跨进程QueueHandler
不得记录密码和完整表内容
```

---

# 二十三、矫正项二十：静态检查和CI

新增开发依赖：

```text
ruff
pyright 或 mypy
```

建议命令：

```powershell
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

GitHub Actions至少包含：

```text
Windows
Python 3.12
uv sync
Alembic迁移
静态检查
单元测试
集成测试
```

进程测试后续进入阶段D/E时增加。

---

# 二十四、建议修改文件清单

阶段C.5预计涉及：

```text
pyproject.toml
README.md
alembic.ini
migrations/env.py
migrations/versions/<new_revision>.py

src/<package>/api/app.py
src/<package>/api/api_models.py
src/<package>/api/routes_workflows.py
src/<package>/api/websocket_events.py

src/<package>/engine/runtime_store.py
src/<package>/engine/db_models.py
src/<package>/engine/bootstrap.py
src/<package>/engine/event_router.py
src/<package>/engine/service_container.py

src/<package>/workflow/definition.py
src/<package>/workflow/validation.py
src/<package>/nodes/registry.py

src/<package>/protocols/enums.py
src/<package>/protocols/events.py
src/<package>/protocols/table_ref.py
src/<package>/protocols/workflow_definition.py

src/<package>/common/database.py
src/<package>/common/config.py
src/<package>/common/instance_lock.py

tests/unit/
tests/integration/
.github/workflows/ci.yml
```

---

# 二十五、阶段C.5实施顺序

## C.5-1 名称与工程规则

```text
确定包名
增加Ruff和类型检查
更新README
```

## C.5-2 工作流版本模型

```text
新增workflows
新增workflow_revisions
迁移现有workflow_definitions数据
WorkflowRun引用revision
```

## C.5-3 严格定义与验证

```text
WorkflowDefinitionModel
NodeRegistry
DAG校验
validate API
```

## C.5-4 数据库连接标准化

```text
SQLite PRAGMA
data_refs字段对齐
runtime_events表
state_version字段
```

## C.5-5 Bootstrap和服务容器

```text
迁移移出create_app
单实例锁
数据目录
ServiceContainer
```

## C.5-6 EventRouter

```text
事件落盘
sequence_number
WebSocket广播
REST状态恢复
```

## C.5-7 API View与本地令牌

```text
response_model
View模型
本地Token
Origin控制
```

## C.5-8 CI与总体验收

```text
Windows CI
迁移测试
API测试
事件测试
版本历史测试
DAG验证测试
```

---

# 二十六、阶段C.5最终验收场景

## 场景1：工作流版本历史

```text
创建Workflow V1
更新为V2
查询V1和V2
创建Run固定V1
```

通过条件：

```text
V1内容不变
Run始终引用V1
```

## 场景2：非法DAG

```text
A → B → A
```

通过条件：

```text
validate返回DAG_CYCLE_DETECTED
不得保存正式revision
```

## 场景3：SQLite外键

插入不存在Workflow的Run。

通过条件：

```text
数据库拒绝写入
```

## 场景4：事件发布

EngineHost发布测试事件。

通过条件：

```text
runtime_events有记录
WebSocket客户端收到相同event_id和sequence_number
```

## 场景5：状态竞争

先将NodeRun更新为TIMED_OUT，再模拟旧SUCCEEDED消息。

通过条件：

```text
旧消息因state_version不匹配被拒绝
```

## 场景6：EngineHost单实例

同一数据目录启动两个实例。

通过条件：

```text
第二个实例明确失败
不会同时迁移或写数据库
```

## 场景7：API视图稳定

内部数据库增加字段。

通过条件：

```text
API返回结构不发生未声明变化
```

---

# 二十七、阶段C.5完成标准

全部满足以下条件后，才进入阶段D：

```text
包名正式确定
工作流Revision不可变
WorkflowRun固定revision_id
工作流定义有严格Schema
DAG验证接口完成
NodeRegistry基础完成
SQLite外键/WAL/busy_timeout启用
TableRef和data_refs字段一致
TableLeaseManager边界与原子租约接口完成
迁移与FastAPI工厂解耦
EngineHostBootstrap完成
runtime_events和EventRouter完成
状态所有权和state_version完成
API View模型完成
本地访问令牌完成
EngineHost单实例完成
Ruff、类型检查和Windows CI通过
```

---

# 二十八、对Codex的执行要求

将本文档交给Codex时，应明确：

```text
当前仓库已经完成阶段A、B、C。
本次只执行阶段C.5。
不得开始WorkflowRunProcess、NodeExecutor或运行数据库业务实现。
```

Codex每一小阶段必须：

```text
1. 先检查现有代码
2. 列出更改清单
3. 编写迁移
4. 编写测试
5. 运行全量测试
6. 汇总兼容性影响
7. 提交变更
```

不得：

```text
直接删除现有数据表而不迁移
覆盖历史工作流定义
提前实现节点业务
把共享节点的完成判断、版本循环或删除决策写入EngineHost
除TableLeaseManager外继续增加共享业务核心服务
一次性重写整个仓库
更换已确认技术栈
```

---

# 二十九、最终收口

当前仓库整体方向正确，不需要推翻。

本次矫正的核心是：

```text
让控制面骨架从“可以演示”
提升为“可以承载后续运行面”
```

阶段C.5完成后，系统将具备：

```text
稳定的工作流版本基础
严格的DAG定义
可扩展节点注册
可靠的元数据库约束
明确的状态所有权
可供UI/Web使用的事件系统
稳定的EngineHost启动边界
明确且最小化的TableLeaseManager跨进程一致性边界
```

随后再进入WorkflowRunProcess和NodeExecutor，返工风险会明显降低。
