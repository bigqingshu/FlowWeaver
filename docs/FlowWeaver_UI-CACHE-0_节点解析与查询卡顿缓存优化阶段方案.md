# FlowWeaver UI-CACHE-0：节点解析与查询卡顿缓存优化阶段方案

> 文档状态：前置方案
> 当前阶段：确认 UI 解析热点、缓存边界和分阶段落地顺序
> 不适用范围：本阶段不直接修改后端 API、不改 workflow 保存语义、不引入持久化 token

## 1. 背景

当前桌面 UI 已经具备：

* 连接 EngineHost 并按 token 鉴权访问 REST API。
* 拉取 `GET /api/v1/node-definitions` 并解析节点配置 schema。
* 拉取 workflow detail / revisions，并把 `definition` 展示为节点、连接和 JSON 草稿。
* 在 Workflow 页面中基于选中节点生成配置草稿表单。
* 在数据预览中按 run / node / table_ref 查询表格行。

用户点击节点、刷新详情或执行数据预览查询时，可能出现 UI 卡顿。初步分析显示，卡顿风险不只来自 HTTP 请求，也来自 UI 线程上对同一份 JSON 的重复解析和集合重建。

## 2. 当前热点判断

### 2.1 Workflow draft JSON 重复解析

`WorkflowDefinitionDraftJson` 变化后，当前会连续触发：

```text
WorkflowDefinitionDraftStructureBuilder.Build(...)
NodeConfigDraftBuilder.Build(...)
RuntimeOptionsDraftReader.Read(...)
```

其中 `NodeConfigDraftBuilder.Build(...)` 会再次 `JsonDocument.Parse(...)` 并线性扫描 `nodes` 查找当前节点。

此外，`WorkflowLinearChainStatusText` 当前在属性 getter 中调用：

```text
WorkflowDefinitionLinearChainAnalyzer.Analyze(...)
```

绑定刷新时可能重复 parse 整份 workflow JSON。

### 2.2 Node definitions 解析重复风险

节点目录刷新后，每个 `NodeDefinitionDto` 会构造 `NodeDefinitionListItemViewModel`，并调用：

```text
NodeConfigSchemaParser.Parse(config_schema_version, config_schema)
```

当前自动刷新已有保护：健康连接后只有 `NodeDefinitions` 为空才自动拉取。但手动刷新、连接切换和后续插件能力增强后，仍需要明确缓存和失效策略。

### 2.3 数据预览查询串行等待

按选中 workflow node 刷新数据预览时，当前链路是：

```text
ListNodeRunsAsync
→ ListTableRefsAsync
→ GetTableDataRowsAsync
→ UI 线程重建 Columns / Rows
```

如果后端响应慢、表列多、行对象复杂或 UI 集合频繁重建，都会形成点击后的等待感。

## 3. 缓存特征判断

### 3.1 `链接 + token` 可以做什么

`BaseUrl + token` 可以作为“连接身份命名空间”，用于区分不同 EngineHost 或不同鉴权上下文。

建议使用：

```text
connection_key = normalized_base_url + token_fingerprint
```

其中 `token_fingerprint` 必须是不可逆摘要或短 hash，不应保存 token 原文。

### 3.2 `链接 + token` 不能单独做什么

`链接 + token` 不能唯一代表内容版本。

同一个连接下：

* workflow definition 会随着 save 产生新 revision；
* node definitions 未来可能随插件加载、运行版本或开发模式变化；
* table rows 会随 `table_ref_id`、分页参数、排序参数变化；
* run / node_run 状态会持续变化。

因此缓存 key 必须叠加资源自身版本特征。

### 3.3 推荐缓存 key

| 数据 | 推荐 key | 说明 |
| --- | --- | --- |
| Workflow parsed state | `workflow_draft_json_hash` | 本地草稿变化即失效 |
| Saved workflow detail | `connection_key + workflow_id + revision_id + definition_hash` | 后端已有 `revision_id` / `definition_hash` |
| Node definitions | `connection_key + catalog_hash 或 TTL` | 当前后端缺少 catalog hash |
| Node definition lookup | `(node_type, node_version)` | ViewModel 内字典即可 |
| Selected node config draft | `workflow_draft_json_hash + node_instance_id + schema_key` | 避免切换节点时重复 parse 全 JSON |
| Runtime options draft | `workflow_draft_json_hash` | 与 workflow 草稿同步失效 |
| Linear chain analysis | `workflow_draft_json_hash` | 不应放在 getter 中实时解析 |
| Data preview rows | `connection_key + table_ref_id + offset + limit + columns + order_by` | `table_ref_id` 是更准确的数据版本身份 |
| Node runs / table refs | `workflow_run_id + 短 TTL 或事件刷新` | 状态动态变化，不适合长缓存 |

## 4. 分阶段方案

### UI-CACHE-1：建立性能基线与日志

目标：

* 先确认卡顿主因是网络、JSON parse、集合重建还是绑定刷新。
* 为后续优化提供可比较数据。

建议工作：

```text
在关键路径增加 Debug/Trace 级耗时记录
统计 workflow JSON 大小、node 数、connection 数
统计 NodeConfigDraftBuilder / RuntimeOptionsDraftReader / LinearChainAnalyzer 耗时
统计数据预览 rows/columns 数和 UI 重建耗时
```

验收标准：

```text
能在日志中看到点击节点、加载 workflow、刷新数据预览的分段耗时
不输出 token 原文
不改变用户可见行为
```

### UI-CACHE-2：Workflow draft parsed state 缓存

目标：

* 消除同一份 `WorkflowDefinitionDraftJson` 在 UI 状态刷新中的重复 parse。
* 让选中节点、runtime options、线性链分析共享同一个解析结果。

建议新增模型：

```text
WorkflowDefinitionDraftParsedState
WorkflowDefinitionDraftParsedStateBuilder
WorkflowDefinitionDraftParsedStateCache
```

建议内容：

```text
DraftJsonHash
Structure
NodesById
NodeConfigJsonById
RuntimeOptionsReadResult
LinearChainAnalysis
Warnings
```

ViewModel 调整方向：

```text
OnWorkflowDefinitionDraftJsonChanged
→ 只构建一次 ParsedState
→ 从 ParsedState 更新 WorkflowDefinitionDraftStructure
→ 从 ParsedState 更新 RuntimeOptionsDraftState
→ 从 ParsedState 更新 WorkflowLinearChainStatusText 的 backing field
```

关键要求：

* `WorkflowLinearChainStatusText` 不再在 getter 中 parse JSON。
* `RefreshSelectedNodeConfigDraftState` 优先从 `ParsedState.NodesById` 读取 config。
* JSON 无效时也缓存失败状态，避免同一无效文本被重复解析。

验收标准：

```text
同一 draft JSON 下，切换节点不再 parse 整份 workflow JSON
线性链状态绑定刷新不触发 JsonDocument.Parse
现有 workflow draft、节点配置、runtime options 测试保持通过
```

### UI-CACHE-3：Node definitions 本地目录优化

目标：

* 减少节点目录刷新后的重复解析和线性查找。
* 为后续连接级缓存做准备。

建议工作：

```text
维护 NodeDefinitionByKey 字典
key = node_type + node_version
FindNodeDefinition(...) 改为字典查找
schema parse result 与 DTO 分离，避免重复解析同一 schema
```

注意：

* 不建议直接长期缓存 `NodeDefinitionListItemViewModel`，因为它依赖当前语言 formatter。
* 可以缓存 DTO 或不可变 schema descriptor，UI item 在当前语言环境下重新包装。

验收标准：

```text
FindNodeDefinition 不再 FirstOrDefault 扫描整个 NodeDefinitions
切换语言后节点显示文本仍能刷新
刷新节点目录仍可覆盖旧 catalog
```

### UI-CACHE-4：连接级 Node catalog 缓存

目标：

* 避免同一 EngineHost 连接下反复拉取和解析节点目录。
* 解决连接切换时旧目录短暂残留的问题。

建议客户端 key：

```text
connection_key = normalized_base_url + token_fingerprint
```

第一版失效策略：

```text
手动点击刷新：强制请求后端并覆盖缓存
BaseUrl/token 变化：切换到对应 connection_key 的缓存；没有缓存则清空并等待刷新
TTL：可选，开发阶段建议较短，例如 5 到 30 分钟
```

后端增强后失效策略：

```text
GET /api/v1/node-definitions 返回 catalog_hash 或 catalog_version
客户端发现 hash 变化后重新解析
```

验收标准：

```text
同一连接二次进入页面可复用 node catalog
连接切换不会显示错误连接的节点目录
手动刷新一定能绕过缓存拿最新结果
不持久化 token 原文
```

### UI-CACHE-5：Workflow detail/revision 缓存

目标：

* 避免重复加载同一个 workflow revision 时重新格式化 JSON、重建节点列表和 revision 列表。

推荐 key：

```text
connection_key + workflow_id + revision_id + definition_hash
```

建议策略：

* 当前 workflow 列表返回的 revision/version 可作为预检查。
* 点击加载详情时，如果缓存 key 命中，先立即显示缓存内容。
* 后台仍可轻量确认当前 revision 是否变化。
* 保存成功后用新 revision 更新缓存，并清理旧 revision 的当前选中状态。

验收标准：

```text
重复点击同一 workflow 详情时可快速回显
保存产生新 revision 后不会使用旧 parsed state
revision conflict 处理保持不变
```

### UI-CACHE-6：数据预览查询缓存与异步构建

目标：

* 降低“查询/刷新预览”点击后的等待感。
* 区分可缓存的静态行数据和动态 run 状态。

建议拆分：

```text
NodeRuns / TableRefs：短 TTL 或事件驱动刷新
Rows：按 table_ref_id + paging 参数缓存
UI Rows：后台构建轻量中间结构，UI 线程只替换集合
```

Rows 推荐 key：

```text
connection_key
+ table_ref_id
+ offset
+ limit
+ columns
+ order_by
```

可选后端增强：

```text
GET /api/v1/runs/{run_id}/nodes/{node_instance_id}/latest-table-rows
```

该组合接口可以把当前三次 REST 往返减少为一次：

```text
node run 查找 + table ref 查找 + rows 读取
```

验收标准：

```text
重复打开同一 table_ref 同一页能快速回显
刷新按钮可强制绕过 rows cache
run/node_run 动态状态不会被长期缓存误导
数据预览加载期间 UI 可继续响应
```

### UI-CACHE-7：后端版本特征补齐

目标：

* 给客户端缓存提供稳定失效依据。

建议后端新增：

```text
GET /api/v1/health 增加 engine_instance_id 或 started_at
GET /api/v1/node-definitions 增加 catalog_hash/catalog_version
数据 rows 响应可回传 schema_fingerprint / table version
可选支持 ETag / If-None-Match
```

注意：

* `engine_instance_id` 只表示进程身份，不代表 node catalog 一定变化。
* `catalog_hash` 应由 node type、version、ports、schema 等内容计算。
* ETag 是优化网络传输，不替代 UI parsed state 缓存。

验收标准：

```text
客户端可以基于 hash 判断 node catalog 是否需要重新解析
EngineHost 重启后客户端能识别连接身份变化
旧客户端仍能兼容没有 hash 的响应
```

## 5. 推荐落地顺序

建议按下面顺序推进：

```text
1. UI-CACHE-1：先加耗时观测
2. UI-CACHE-2：先修最明显的 UI 重复 parse
3. UI-CACHE-3：节点目录字典与 schema 解析复用
4. UI-CACHE-6：数据预览 rows 缓存与异步构建
5. UI-CACHE-5：workflow detail/revision 缓存
6. UI-CACHE-4：连接级 node catalog 缓存
7. UI-CACHE-7：后端 catalog hash / ETag 增强
```

理由：

* `UI-CACHE-2` 最直接对应点击节点和绑定刷新卡顿。
* `UI-CACHE-3` 低风险，能改善目录和 schema 查找。
* `UI-CACHE-6` 对“点击查询”体感收益更明显。
* 后端版本特征可以后置，避免先改接口契约扩大影响面。

## 6. 风险与约束

### 6.1 token 安全

缓存 key 不得包含 token 原文。

推荐：

```text
token_fingerprint = SHA256(token).前 8 到 16 位
```

仅用于本地分区显示和内存缓存，不用于日志输出。

### 6.2 stale cache

所有缓存都必须有明确失效条件。

最低要求：

```text
手动刷新必须绕过缓存
保存成功必须更新 workflow parsed cache
连接变化必须切换缓存命名空间
鉴权失败不能继续展示为“已刷新成功”
```

### 6.3 ViewModel 缓存边界

不建议跨语言、跨连接长期复用 ViewModel 对象。

推荐缓存：

```text
DTO
不可变 descriptor
parsed state
轻量 row/cell 数据
```

不推荐缓存：

```text
持有当前 localization formatter 的 ListItemViewModel
持有 UI 事件订阅的节点 item
可编辑输入框 ViewModel
```

## 7. 测试计划

建议分层补测试：

```text
WorkflowDefinitionDraftParsedStateBuilderTests
MainWindowViewModelWorkflowTests
NodeDefinitionListItemViewModelTests
DataPreview cache / stale request tests
```

重点场景：

```text
无效 JSON 只进入失败 parsed state，不抛异常
切换节点不重建整份 workflow parsed state
修改 draft JSON 后 selected node config 及时更新
切换语言后 node catalog 文本仍刷新
切换 BaseUrl/token 后不会继续显示错误连接的 node catalog
手动刷新绕过 node catalog cache
同 table_ref 同分页命中 rows cache
run/node_run 动态状态不会被长缓存污染
```

## 8. 当前阶段结论

可以做缓存，但缓存粒度不应停留在“链接 + token”。

推荐结论：

```text
链接 + token：只作为连接身份命名空间
workflow：使用 revision_id + definition_hash
draft JSON：使用 draft json hash
node config：使用 draft json hash + node_instance_id + schema key
table rows：使用 table_ref_id + paging/filter 参数
node catalog：短期用 connection key + TTL/手动刷新，长期补 catalog_hash
```

第一优先级应放在 UI 端 parsed state 缓存，因为它不改变后端契约，且最直接减少点击节点、刷新绑定和编辑草稿时的重复解析。
