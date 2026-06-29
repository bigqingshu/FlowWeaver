# FlowWeaver 阶段 I.0 共享表边界确认清单

复核日期：2026-06-28

## 一、当前结论

阶段 I 可以进入，但 I.0 只做边界确认，不实现共享表运行时代码。

当前主程序已经具备进入共享表阶段的前置基础：

- EngineHost / Supervisor / WorkflowRunProcess / NodeExecutor 子进程入口已串通。
- `RuntimeDataRegistry` 已支持单表 STAGING 注册、发布为 PUBLISHED、查询和节点失败清理。
- `RuntimeStore` 已支持 `TableRef` 注册、查询和 STAGING 释放。
- `TableLeaseManager` 已支持表级 READ / WRITE 租约。
- 数据库迁移中已有 `shared_publications`、`shared_publication_members`、`input_snapshots`、`read_leases`。

但以下能力尚未实现，不能在 I.0 中提前声明完成：

- `SharedPublication` Store 服务接口。
- 多表共享发布原子写入。
- `InputSnapshot` 创建和 workflow run 关联。
- `ReadLease` 创建、查询和释放服务。
- 读取共享表的 `LATEST` / `EXACT_VERSION` 解析。
- 发布共享表节点和读取共享表节点。
- WorkflowRunProcess 中的共享表节点执行接入。

## 二、阶段 I 最小语义

阶段 I 的核心目标是让跨工作流共享表具备固定版本语义。

最小闭环：

```text
工作流 A 发布两张表为 A@V1
工作流 B 一次读取 A@V1 的完整成员集合
工作流 A 后续发布 A@V2
工作流 B 当前运行仍固定使用 A@V1
工作流 B 结束后释放读取租约
```

关键约束：

- 共享发布版本不可原地修改。
- 一次读取必须获得同一 publication version 的完整成员集合。
- 当前运行的 `InputSnapshot` 不随 latest 变化而漂移。
- 第一阶段不允许读取到半套版本。
- 已发布数据不通过 EngineHost 复制大表内容，只传递 `TableRef` / 元数据。

## 三、第一阶段支持范围

### 发布侧

支持：

- `share_name`
- 多个 member
- `export_name`
- `table_ref_id`
- `exact_table_version`
- `retention_policy_json`
- 最小状态 `PUBLISHED`

暂不支持：

- 下游工作流触发。
- 复杂 lineage。
- 跨数据库事务。
- 发布后原地修改。

### 读取侧

支持：

- `LATEST`
- `EXACT_VERSION`
- 一次性返回完整成员 `TableRef` 列表。
- 创建 `InputSnapshot` 固定本次读取版本。
- 创建 `ReadLease` 表达当前 workflow run 正在读取该版本。

暂不支持：

- `NEXT_VERSION`
- `NEWER_THAN_CURRENT`
- `SAME_AS_UPSTREAM`
- `FOLLOW_LINEAGE`
- 复杂等待策略。
- 完整 DependencyPin。

## 四、当前代码前置事实

当前已有数据库表：

```text
shared_publications
shared_publication_members
input_snapshots
read_leases
```

当前已有数据引用能力：

```text
RuntimeStore.register_table_ref()
RuntimeStore.get_table_ref()
RuntimeStore.list_table_refs_by_workflow_run()
RuntimeStore.list_table_refs_by_node_run()
RuntimeStore.mark_staging_table_ref_released()
RuntimeDataRegistry.register_staging()
RuntimeDataRegistry.publish()
RuntimeDataRegistry.cleanup_staging_for_node()
```

当前已有租约能力：

```text
TableLeaseManager.acquire_read_lease()
TableLeaseManager.acquire_write_lease()
TableLeaseManager.release()
```

注意：`TableLeaseManager` 管的是单个 `TableRef` 的读写租约；阶段 I 的 `ReadLease` 管的是 workflow run 对某个共享发布版本的读取快照，两者不能混用。

## 五、I.0 验收边界

I.0 只确认以下内容：

```text
共享表前置表结构存在
关键列存在
member 到 publication/table_ref 的外键存在
publication 的 share_name + publication_version 唯一约束存在
README 已列出 I.0-I.9 执行方向
```

I.0 不做：

- 不新增 `SharedPublication` dataclass / model。
- 不新增 RuntimeStore 共享表写入接口。
- 不新增读取服务。
- 不新增节点。
- 不接入 WorkflowRunProcess。
- 不变更主程序入口。
- 不改变 `CONTINUE_INDEPENDENT` / `SKIP_DEPENDENTS` 行为。

## 六、建议后续小步

下一步建议进入 I.1：

```text
SharedPublication Store 边界
```

I.1 的最小目标：

- 增加共享发布记录的数据模型或返回对象。
- 支持按 `share_name` 分配递增 `publication_version`。
- 支持原子写入 publication 与 members。
- 支持按 id、按 `share_name + version`、按 latest 查询。

仍不做：

- 不实现节点。
- 不接主循环。
- 不创建 read lease。
- 不实现 latest 读取策略服务。
