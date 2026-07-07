# FlowWeaver UI-CACHE-0：节点目录版本标识与最小缓存讨论方案

> 文档状态：讨论方案
> 当前阶段：先收敛最小可行方案，不进入代码实现
> 不适用范围：本阶段不做数据预览 rows 缓存、不做 workflow detail 缓存、不做 token 持久化、不重构后端 API 主流程

## 1. 背景

当前桌面 UI 在连接 EngineHost 后，会调用：

```text
GET /api/v1/node-definitions
```

并把后端返回的节点定义转换为 UI 节点目录：

```text
NodeDefinitionDto
→ NodeDefinitionListItemViewModel
→ NodeConfigSchemaParser.Parse(config_schema_version, config_schema)
```

节点目录本身一般不频繁变化，但当前客户端缺少明确的“目录是否变化”依据。手动刷新、连接切换、未来插件加载或开发模式热更新时，客户端只能重新接收并重新解析节点目录。

后端节点计划完成后，默认注册表中的节点数量已经明显增加。节点目录越大，完整拉取、DTO 反序列化、`NodeDefinitionListItemViewModel` 重建和 `config_schema` 解析的成本越值得单独控制。

本方案先讨论最小改动：让后端提前提供节点目录版本特征，客户端据此判断是否需要重建目录和重新解析 schema。

## 2. 设计判断

### 2.1 `node_version` 适合做契约版本

`node_type + node_version` 适合表示 workflow 引用的是哪个节点契约，例如：

```text
BuiltinTableFilter@1.0
CustomNode@0.1
```

它适合作为：

```text
Node definition lookup key
Workflow node definition reference
```

但它不适合单独作为缓存失效依据。

原因是 `node_version` 依赖人工维护。如果端口、schema、display name 或执行参数改了，但版本没有同步提升，客户端会错误复用旧缓存。

### 2.2 hash / fingerprint 适合做缓存失效依据

建议把职责拆开：

```text
node_type + node_version：表示节点契约身份
definition_hash：表示单个节点定义内容是否变化
schema_fingerprint：表示节点 config_schema 是否变化
catalog_hash：表示整个可见节点目录是否变化
program_hash / build_hash：表示后端程序构建身份
```

其中：

* `definition_hash` 由单个节点定义稳定内容计算。
* `schema_fingerprint` 只由 config schema 相关内容计算。
* `catalog_hash` 由当前可见节点定义集合计算。
* `program_hash` 只能作为辅助命名空间，不能替代 `catalog_hash`。

### 2.3 `program_hash` 有价值，但不能单独使用

后端程序 hash 可以帮助客户端区分不同 EngineHost 构建：

```text
engine_build_hash
engine_started_at
engine_instance_id
```

但它不一定能代表节点目录内容。未来可能出现：

* 同一程序版本加载不同插件；
* 配置决定启用不同节点；
* 开发模式中节点目录热更新；
* 节点定义来自外部包或运行时注册。

因此更稳妥的判断是：

```text
connection_key + program_hash + catalog_hash
```

其中 `catalog_hash` 是目录是否变化的核心依据。

## 3. 最小方案

### 3.1 第一阶段只新增全局 state

第一版建议保留当前完整目录接口不变：

```text
GET /api/v1/node-definitions
```

同时新增一个只用于缓存校验的轻量接口：

```text
GET /api/v1/node-definitions/state
```

该接口继续走现有 API envelope 风格，避免单独改一套客户端响应处理：

```text
APIResponseModel.data = {
  catalog_hash,
  program_hash 可选,
  node_count 可选
}
```

其中第一阶段只要求 `catalog_hash` 必须存在。其余字段用于诊断和后续命名空间增强。

该接口只返回极少量元信息：

```text
catalog_hash
program_hash 可选
node_count 可选
```

这样前端可以先用很小的数据判断本地节点目录是否仍然可用。只有 `catalog_hash` 不一致时，才回退到完整目录拉取。

后续如果需要一次响应中同时包含数据和 meta，可以再考虑把 `GET /api/v1/node-definitions` 从“直接返回 list”升级为“带 meta 的对象”，或新增 v2。第一阶段不建议直接破坏当前前端 DTO。

单个节点定义级字段后置到 manifest 阶段：

```text
definition_hash
schema_fingerprint
```

原因：

```text
第一阶段只需要判断整个目录是否变化
完整目录接口仍返回旧 DTO，前端兼容成本最低
per-node hash 只有在做 manifest / 单节点懒刷新时才真正需要
```

### 3.2 后端预计算

后端在 NodeRegistry 注册完成后预计算：

```text
catalog_hash
```

请求到来时直接读取缓存结果，避免每次请求都重新计算 hash。

`catalog_hash` 必须基于“当前 API 实际返回给 UI 的可见节点目录”计算，而不是内部 registry 全量。也就是说，后端需要先应用 `BUILTIN_FAULT_NODE_TYPES` 等可见性过滤，再计算 hash。

稳定 hash 内容建议包含：

```text
node_type
node_version
display_name
input_ports
output_ports
execution_mode
default_timeout_seconds
retry_safe
ui_visibility
config_schema_version
config_schema
```

计算规则必须使用稳定 JSON：

```text
sort_keys = true
compact separators
utf-8
sha256
```

后续进入 manifest / 单节点懒刷新阶段时，再补充预计算：

```text
definition_hash by node_type + node_version
schema_fingerprint by node_type + node_version
manifest_hash 可选
```

### 3.3 客户端最小缓存

客户端维护连接命名空间：

```text
connection_key = normalized_base_url + token_fingerprint
```

其中 `token_fingerprint` 只能是不可逆短摘要，不保存 token 原文。

客户端缓存 key：

```text
catalog_cache_key = connection_key + program_hash + catalog_hash
definition_lookup_key = node_type + node_version
```

第一阶段不强依赖后端提供 `schema_fingerprint`。前端可以先做当前 catalog 内的 schema parse result 复用；等后端补齐 `schema_fingerprint` 后，再升级为跨 catalog 复用：

```text
schema_cache_key = node_type + node_version + config_schema_version + schema_fingerprint
```

命中策略：

* `catalog_hash` 未变化：复用已有节点目录描述和 schema parse result。
* `node_type + node_version`：用于字典查找，替代线性扫描。
* 自动刷新 / 连接恢复：优先请求 `/node-definitions/state`。
* 手动刷新：必须绕过本地命中，直接完整请求后端并覆盖缓存。
* 连接变化：切换 `connection_key`，没有命中则清空并等待重新加载。

后续命中策略：

* `schema_fingerprint` 未变化：复用已解析的 schema descriptor。
* `definition_hash` 未变化：复用对应节点 DTO / descriptor。
* manifest 显示节点被删除：从本地目录移除对应节点。

## 4. 能减少的计算

该最小方案主要减少：

```text
重复请求后端后重新解析相同 node config_schema
重复构造相同节点目录 descriptor
FindNodeDefinition 线性扫描
后端每次请求重复计算目录版本信息
```

如果后续支持 `ETag / If-None-Match`，还可以减少：

```text
节点目录未变化时的完整 JSON 传输
客户端反序列化整个节点目录 payload
```

## 5. 不能解决的问题

该方案不是完整 UI 卡顿优化，只覆盖节点目录和 schema 解析。

暂不解决：

```text
WorkflowDefinitionDraftJson 在 UI 内重复 JsonDocument.Parse
WorkflowLinearChainStatusText getter 中重复分析 workflow JSON
RuntimeOptionsDraftReader 多处重复读取同一 draft
数据预览 ListNodeRunsAsync → ListTableRefsAsync → GetTableDataRowsAsync 串行等待
数据预览 rows/columns UI 集合重建
```

这些问题后续仍需要独立方案，例如 UI parsed state、rows cache 或组合查询接口。

## 6. 耦合度分析

低耦合部分：

```text
catalog_hash 是 state 接口元信息，不改变完整目录 DTO
NodeRegistry 或目录 snapshot 负责预计算目录版本
客户端用 hash 判断是否复用 descriptor
```

中等耦合部分：

```text
如果未来让 node-definitions 响应结构从 list 改为对象，需要同步修改客户端 DTO
如果未来加入 definition_hash / schema_fingerprint，需要同步扩展后端 DTO 和 Avalonia DTO
如果加入 ETag，需要 API client 支持条件请求
```

不建议缓存：

```text
直接缓存 NodeDefinitionListItemViewModel
直接缓存带语言 formatter 的显示文本
直接缓存 token 原文
```

推荐缓存：

```text
NodeDefinitionDto
NodeConfigSchemaDescriptor
Node catalog metadata
definition lookup dictionary
```

## 7. 刷新规则

本地缓存刷新条件：

```text
手动点击刷新节点目录
BaseUrl 变化
token 变化
program_hash 变化
catalog_hash 变化
schema_fingerprint 变化
manifest 中节点新增 / 删除 / definition_hash 变化
后端返回鉴权失败或节点目录请求失败
```

其中：

* 自动刷新和连接恢复可以先走 `/node-definitions/state`。
* 手动刷新必须绕过本地命中，直接请求完整节点目录并覆盖缓存。
* token 不保存原文，只参与短 fingerprint。
* 语言切换不应重新请求节点目录，只刷新显示文本。
* catalog 未变化时，客户端可以避免重建 schema descriptor。

## 8. 建议实施顺序

推荐按“先全局校验，再完整刷新，最后分节点懒刷新”的顺序推进。

### UI-CACHE-MIN-1：保留完整目录接口

目标：

```text
保留 GET /api/v1/node-definitions 当前完整 list 行为
继续兼容现有前端 List<NodeDefinitionDto>
不在第一步改变已有响应结构
```

验收：

```text
旧客户端仍能完整刷新节点目录
当前节点目录页面行为不变
后端新增缓存能力不影响原接口语义
```

### UI-CACHE-MIN-2：新增全局 state 校验接口

目标：

```text
后端新增 GET /api/v1/node-definitions/state
通过 APIResponseModel.data 返回 catalog_hash / program_hash / node_count 等极小元信息
NodeRegistry 注册完成后预计算并缓存 catalog_hash
catalog_hash 基于实际 API 可见节点目录计算
```

验收：

```text
相同节点目录返回相同 catalog_hash
节点 schema、端口或定义内容变化后 catalog_hash 变化
state 接口不返回完整 config_schema
隐藏/测试节点变化不会误触发可见目录 catalog_hash 变化
```

### UI-CACHE-MIN-3：前端先校验 catalog_hash

目标：

```text
前端刷新节点目录前先请求 state
本地 catalog_hash 一致时直接复用已有节点目录
catalog_hash 不一致时回退到旧完整 GET /api/v1/node-definitions
手动刷新直接完整请求后端并覆盖缓存
```

验收：

```text
目录未变化时不重新拉完整节点目录
目录变化时仍能完整刷新并覆盖缓存
连接或 token 变化时切换 connection_key
```

### UI-CACHE-MIN-4：客户端目录字典与 schema 复用

目标：

```text
维护 NodeDefinitionByKey 字典
FindNodeDefinition 改为字典查找
同一 catalog 内复用 schema parse result
后端提供 schema_fingerprint 后升级为跨 catalog schema cache
```

验收：

```text
节点配置查找不再扫描 NodeDefinitions
相同节点目录重复加载时不重复解析 schema
语言切换后文本仍能刷新
catalog_hash 变化后能重建字典和 schema cache
```

### UI-CACHE-MIN-5：可选 manifest 与懒刷新

目标：

```text
全局 catalog_hash 不一致时，先请求节点 manifest
manifest 只包含 node_type / node_version / definition_hash / schema_fingerprint
前端逐节点比对本地缓存，确认哪些节点需要更新
只按需拉取变更节点定义
单节点定义开始返回 definition_hash / schema_fingerprint
```

可选接口：

```text
GET /api/v1/node-definitions/manifest
GET /api/v1/node-definitions/{node_type}/{node_version}
POST /api/v1/node-definitions/batch-get
```

验收：

```text
少量节点变化时不需要重新传输全部节点定义
未变化节点继续复用本地 descriptor 和 schema parse result
被删除节点能从本地目录移除
新增节点能被加入本地目录
```

### UI-CACHE-MIN-6：可选 ETag

目标：

```text
后端为 node-definitions/state 或完整 node-definitions 返回 ETag = catalog_hash
客户端带 If-None-Match
未变化时后端返回 304
```

验收：

```text
目录未变化时不传输完整节点目录 JSON
目录变化时客户端正常接收并更新缓存
ETag 只作为网络优化，不替代本地缓存失效规则
```

## 9. 备选办法与推荐组合

### 9.1 可选办法

#### ETag / If-None-Match

后端把 `catalog_hash` 作为 HTTP ETag，前端下次请求时带上：

```text
If-None-Match: catalog_hash
```

未变化时返回：

```text
304 Not Modified
```

优点：

```text
标准 HTTP 缓存语义
无需自定义 cache_status
适合后续网络层优化
```

约束：

```text
当前 API client 主要按 APIResponseEnvelope<T> 解析
支持 304 需要调整请求层
第一阶段比新增 state 接口稍重
```

#### HEAD / node-definitions

增加：

```text
HEAD /api/v1/node-definitions
```

响应头只返回：

```text
ETag: catalog_hash
X-Node-Count: 26
```

优点：

```text
传输数据极少
语义接近“只校验，不取数据”
```

约束：

```text
FastAPI 路由和客户端都需要补 HEAD 支持
调试体验不如 JSON state 接口直观
```

#### summary/detail 拆分

把节点目录拆成轻量 summary 和详情：

```text
GET /api/v1/node-definitions/summary
GET /api/v1/node-definitions/{node_type}/{node_version}
```

summary 只返回：

```text
node_type
node_version
display_name
definition_hash
schema_fingerprint
```

详细 `config_schema` 只有选中节点或需要编辑时再拉。

优点：

```text
大 schema 场景收益明显
节点目录首屏数据更小
```

约束：

```text
前端需要处理 schema 未加载状态
如果页面需要立即展示 schema 摘要，仍要增加懒加载或后台预热
```

#### 前端懒解析 schema

不改后端完整目录接口，只调整前端：

```text
节点目录拉完整 DTO
构造 NodeDefinitionListItemViewModel 时不立即 Parse config_schema
第一次打开配置表单或展示 schema 摘要时再解析
解析结果按 schema_cache_key 缓存
```

优点：

```text
后端改动少
能减少节点目录首轮 UI 构建压力
```

约束：

```text
第一次点击某个节点时仍有解析成本
需要处理解析中的 UI 状态或后台预热
```

#### 后台预热

前端先显示已缓存目录或轻量目录，然后后台构建：

```text
NodeDefinitionByKey
NodeConfigSchemaDescriptor cache
schema summary
```

优点：

```text
用户体感更流畅
不阻塞主 UI 操作
```

约束：

```text
需要处理解析任务取消、连接切换和过期结果
```

#### 服务端事件通知

未来如果事件流稳定，可以新增：

```text
node_catalog_changed
catalog_hash: ...
```

前端收到事件后再刷新节点目录。

优点：

```text
变化驱动，减少轮询和主动校验
```

约束：

```text
依赖事件流稳定性
对当前低频变化的节点目录不是第一优先级
```

### 9.2 推荐组合

当前阶段推荐组合：

```text
第一步：保留 GET /api/v1/node-definitions 完整目录接口
第二步：新增 GET /api/v1/node-definitions/state
第三步：前端先校验 catalog_hash
第四步：catalog_hash 一致则复用本地缓存
第五步：catalog_hash 不一致则回退到完整目录拉取
第六步：前端维护 NodeDefinitionByKey 和同一 catalog 内 schema parse result cache
第七步：需要细粒度更新时，再加 definition_hash / schema_fingerprint / manifest / 单节点懒刷新
第八步：最后考虑 ETag / 304 标准化
```

推荐理由：

```text
不破坏当前完整目录接口
后端新增 state 接口很小
前端可以先只做全局缓存命中判断
catalog 不一致时仍然沿用旧完整刷新路径
per-node hash、manifest、单节点懒刷新和 ETag 都可以后置
```

因此 `/node-definitions/state` 是当前最稳的入口。它和未来的 ETag 方案不冲突，后续可以把 `catalog_hash` 同时放进 JSON state 和 HTTP ETag。

## 10. 当前阶段结论

最小方案建议先聚焦节点目录：

```text
node_type + node_version：节点契约身份
catalog_hash：第一阶段唯一必需的目录内容版本
definition_hash：后续 manifest 阶段的单节点定义内容版本
schema_fingerprint：后续 manifest 阶段的单节点 schema 内容版本
program_hash：后端程序构建辅助命名空间
connection_key：BaseUrl + token_fingerprint 的连接命名空间
```

这个方案能减少节点目录和 schema 的重复解析，改动边界清晰，耦合度可控。当前最小闭环是：

```text
后端：/node-definitions/state + catalog_hash
前端：catalog_hash 命中复用 + NodeDefinitionByKey + 同一 catalog 内 schema parse result cache
```

它不会直接解决 workflow draft JSON 重复 parse 和数据预览查询卡顿，但可以作为缓存体系的最小、稳定入口。
