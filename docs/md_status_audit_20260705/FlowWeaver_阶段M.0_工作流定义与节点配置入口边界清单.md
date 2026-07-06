# FlowWeaver 阶段M.0：工作流定义与节点配置入口边界清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：节点定义只读 API、workflow detail/revision 客户端、definition 只读视图、创建入口、JSON 草稿校验、保存 revision 与冲突保护和运行闭环验收已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：后续结构化编辑已在 WORKFLOW-EDIT / UX 系列继续推进。

> 文档状态：阶段M.0边界确认
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K最小桌面UI基线和阶段L总体验收复核
> 适用范围：Avalonia UI 进入 workflow 定义查看、创建、最小编辑和启动闭环前
> 当前执行点：只写边界清单和检查现有 API，不修改后端、UI 或测试代码

## 1. M.0目标

阶段L已经完成运行入口、连接配置持久化和三类正式路径 smoke。阶段M建议把 Avalonia UI 从“观察并启动已有 workflow”推进到“能查看、创建和保存最小 workflow 定义”，但不直接进入完整画布。

M.0只确认边界：

- UI 查询可用节点类型的职责归属
- workflow definition 当前后端 API 能力
- 最小 workflow 定义查看、创建、保存和启动闭环
- 编辑、草稿、校验、正式保存和 revision 并发保护边界
- 节点配置第一版的表达方式
- 节点定义 API 的稳定 DTO、配置 schema 缺口和测试节点可见性
- M.1 到 M.7 的建议顺序

M.0不做：

- 不新增后端 API
- 不新增 Avalonia 页面、ViewModel 或 DTO
- 不新增工作流画布、拖拽、连线或布局算法
- 不新增复杂动态表单生成器
- 不修改 WorkflowRunProcess、NodeExecutor 或 RuntimeStore
- 不修改数据库迁移
- 不进入打包发布

## 2. 当前代码事实

### 2.1 后端 workflow API

当前已有 workflow 相关正式 API：

| 能力 | 路径 | 当前结论 |
| --- | --- | --- |
| 列出 workflow | `GET /api/v1/workflows` | 已有，UI 已接入 |
| 创建 workflow | `POST /api/v1/workflows` | 已有，会调用 `validate_workflow_definition()` |
| 校验 draft | `POST /api/v1/workflows/validate` | 已有，可校验未保存定义 |
| 获取 workflow detail | `GET /api/v1/workflows/{workflow_id}` | 已有，返回 definition |
| 更新 workflow | `PUT /api/v1/workflows/{workflow_id}` | 已有，会创建新 revision；当前请求体尚无 `base_revision_id` / `expected_version` 防覆盖字段 |
| 校验已保存 workflow | `POST /api/v1/workflows/{workflow_id}/validate` | 已有 |
| 列出 revisions | `GET /api/v1/workflows/{workflow_id}/revisions` | 已有 |
| 获取 revision | `GET /api/v1/workflows/{workflow_id}/revisions/{revision_id}` | 已有 |
| 删除 workflow | `DELETE /api/v1/workflows/{workflow_id}` | 已有 |
| 启动 run | `POST /api/v1/workflows/{workflow_id}/runs` | 已有，UI 已接入 |

结论：

- 后端已有 workflow 定义 CRUD、revision 和校验基础
- Avalonia UI 当前只接入了列表和启动 run
- M 阶段不需要先重写 workflow Store 或校验逻辑
- 当前 `WorkflowUpdateRequest` 只有 `name` 和 `definition`，正式编辑保存前必须补 revision 冲突保护，避免旧 revision 静默覆盖新 revision
- 当前 validate 已能服务 draft 校验，但 UI 还需要明确区分本地草稿、后端校验和正式保存

### 2.2 后端节点注册表

当前后端已有节点注册结构：

```text
NodeRegistry
├─ register(NodeDefinitionSpec)
├─ get(node_type, node_version)
└─ list_definitions()
```

当前 `NodeDefinitionSpec` 包含：

- `node_type`
- `node_version`
- `display_name`
- `input_ports`
- `output_ports`
- `execution_mode`
- `default_timeout_seconds`
- `retry_safe`
- `implementation_path`

当前 `NodeDefinitionSpec` 不包含：

- `config_schema`
- `ui_schema`
- `category`
- `visibility`
- `is_test_only`

默认注册的第一阶段节点包括：

- `GenerateTestTableNode@1.0`
- `FilterRowsNode@1.0`
- `PublishSharedTablesNode@1.0`
- `ReadSharedTablesNode@1.0`
- `DelayTestNode@1.0`
- `FaultTestNode@1.0`

结论：

- 后端已经拥有“可用节点类型”的事实源
- 当前缺口是没有面向 UI 的只读节点定义 API
- UI 不应该硬编码这些节点类型和端口
- `DelayTestNode` 与 `FaultTestNode` 当前在默认 registry 中，但属于测试/验收节点，M.1 需要明确 UI 默认可见性
- 当前没有配置 schema，M 阶段第一版不能承诺动态表单生成

### 2.3 Avalonia UI API Client

当前 Avalonia UI 已有：

- `EngineHostApiClient.ListWorkflowsAsync()`
- `EngineHostApiClient.StartWorkflowRunAsync()`
- Run、NodeRun、RuntimeEvent、AuditEvent、TableRef、SharedPublication 只读查询
- `WorkflowDefinitionDto.Definition` 以 `JsonElement` 承载完整 definition

当前尚未接入：

- 获取单个 workflow detail
- 创建 workflow
- 更新 workflow
- 校验 workflow draft
- workflow revisions 查询
- 节点定义列表查询

结论：

- UI 已有 HTTP envelope、Bearer token、错误处理和 DTO 基础
- M 阶段应复用现有 `EngineHostApiClient`，不引入第二套通信层

## 3. 节点类型查询边界

用户关心的“UI 查询可用内置节点类型”，最稳边界是：

```text
Python FastAPI EngineHost
→ ServiceContainer.node_registry
→ NodeRegistry.list_definitions()
→ GET /api/v1/node-definitions
→ Avalonia UI
```

也就是说，可用节点类型应由后端提供一个只读接口，把当前 EngineHost 实际注册好的节点定义返回给 UI。

原因：

- 后端注册表是运行时事实源
- 后续新增内置节点或插件节点时，UI 不需要改硬编码清单
- workflow 校验已经依赖同一个 `NodeRegistry`
- UI 创建 workflow 时可用同一份节点类型、版本和端口定义
- 避免 UI 展示了后端并未注册的节点，导致保存时才失败

M.0建议的最小只读接口：

```text
GET /api/v1/node-definitions
```

M.1 不应直接把内部 `NodeDefinitionSpec` dataclass 序列化给 UI。建议新增显式 API DTO，例如：

```text
NodeDefinitionView
NodePortView
```

DTO 只暴露稳定字段，并由后端从 `NodeRegistry` 显式映射生成。建议返回 envelope 内的 `data` 为数组：

```json
[
  {
    "node_type": "GenerateTestTableNode",
    "node_version": "1.0",
    "display_name": "Generate Test Table",
    "input_ports": [],
    "output_ports": [
      { "name": "out", "required": false }
    ],
    "execution_mode": "PROCESS_POOL",
    "default_timeout_seconds": 60,
    "retry_safe": false,
    "ui_visibility": "visible"
  }
]
```

接口边界：

- 只读
- 需要本地 API token
- 不暴露 Python 实现细节路径给 UI，除非后续明确需要开发诊断
- 不直接暴露内部 dataclass，必须通过显式 API view / DTO
- 第一版不提供 config schema，因为当前 `NodeDefinitionSpec` 没有该字段
- 第一版不需要插件市场、分类、图标、分组或搜索
- 第一版不需要按权限过滤节点类型
- `DelayTestNode` / `FaultTestNode` 默认不应出现在普通 UI 节点选择器中

测试节点可见性建议：

| 节点 | 当前用途 | M.1 UI 默认可见性 |
| --- | --- | --- |
| `GenerateTestTableNode` | 第一阶段内置表生成节点 | 可见 |
| `FilterRowsNode` | 第一阶段内置表过滤节点 | 可见 |
| `PublishSharedTablesNode` | 第一阶段共享表发布节点 | 可见 |
| `ReadSharedTablesNode` | 第一阶段共享表读取节点 | 可见 |
| `DelayTestNode` | 长任务、heartbeat、cancel 验收节点 | 默认隐藏 |
| `FaultTestNode` | 失败策略、异常路径验收节点 | 默认隐藏 |

M.1 最稳做法：

- API 默认只返回普通 UI 可见节点
- 测试节点先默认隐藏
- 如需开发诊断，后续单独增加显式查询参数或 EngineHost 开发模式配置
- 可见性判断由后端 API 层负责，UI 不硬编码隐藏列表

## 4. Workflow definition 最小编辑边界

当前 workflow definition 模型为：

```text
schema_version
nodes[]
connections[]
inputs[]
outputs[]
failure_policy
```

节点实例包含：

```text
node_instance_id
node_type
node_version
display_name
config
position
enabled
```

M 阶段第一版建议只支持：

- 查看完整 definition
- 以模板创建最小 workflow
- 选择已注册节点类型
- 编辑 `display_name`
- 编辑 `config` 的 JSON 文本
- 查看 input / output ports
- 以列表形式查看 connections
- 保存前调用后端 validate
- 保存成功后形成新 revision
- 保存后可启动 run

编辑与 revision 边界：

- workflow revision 不可变
- UI 编辑的是本地 draft，不直接修改已保存 revision
- draft 保存成功后由后端创建新 revision，并更新 workflow 当前 revision 指针
- workflow run 必须绑定明确的 `revision_id` 和 `definition_hash`
- UI 保存请求必须携带读取时的 `base_revision_id` 或 `expected_version`
- 后端发现当前 revision 已变化时应拒绝保存，而不是静默覆盖
- 冲突错误建议使用 `WORKFLOW_REVISION_CONFLICT`，UI 提示用户刷新、重新应用修改或放弃草稿

草稿、校验和正式保存必须区分：

| 层级 | 作用 | 是否创建 revision | 是否改变后端事实源 |
| --- | --- | --- | --- |
| Draft | UI 内存中的未保存定义 | 否 | 否 |
| Validate | 调用后端校验 draft，返回 errors / warnings | 否 | 否 |
| Save | 校验通过后提交正式保存 | 是 | 是 |

第一版不建议：

- 不做拖拽画布
- 不做复杂表单生成器
- 不做端口连线交互
- 不做节点自动布局
- 不做插件节点配置器
- 不做 workflow diff 视图
- 不做多人协同编辑

## 5. 配置编辑策略

M 阶段有两个可选策略：

| 策略 | 描述 | 建议 |
| --- | --- | --- |
| JSON 文本编辑 | 节点 `config` 以 JSON 文本显示和编辑，保存前解析并调用后端 validate | M 阶段最稳第一版 |
| 简单字段表单 | 对少量内置节点写最小表单 | 可作为 M.4 后的小步 |
| 动态 schema 表单 | 后端返回 config schema，UI 自动生成表单 | 暂缓 |
| 专属节点编辑器 | 每个节点一个 UI 编辑器 | 暂缓 |

M.0建议：

- 第一版先用 JSON 文本作为通用逃生口
- 对模板 workflow 的配置可以预填默认 JSON
- 后端 validate 是最终裁判
- UI 只做 JSON 语法、空值和明显必填提示
- 当前后端节点定义没有 `config_schema`，因此 M.1/M.2 不应设计动态表单契约
- 若后续增加 `config_schema`，必须作为单独小步从后端 DTO、校验和 UI 表单一起收口

## 6. M阶段建议执行顺序

| 小步 | 执行方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| M.0 | 边界清单 | 本文档，确认 API 缺口和执行顺序 | 代码实现 |
| M.1 | 节点定义只读 API | `GET /api/v1/node-definitions`、显式 API DTO、后端测试、Avalonia Client DTO、测试节点默认隐藏 | config schema |
| M.2 | Workflow detail / revision API 客户端接入 | UI 可读取 workflow detail、definition 和 revisions，并保留 `base_revision_id` | 编辑 |
| M.3 | Workflow definition 只读视图 | UI 展示节点、connections、revision、hash 和原始 JSON | 创建/保存 |
| M.4 | 最小创建入口 | 从内置模板创建 workflow，保存后刷新列表 | 自由画布 |
| M.5 | 最小 JSON 配置编辑 | 编辑节点 config JSON，调用 validate，展示错误，draft 不落库 | 动态表单 |
| M.6 | 保存 revision 与启动闭环 | 带 `base_revision_id` / `expected_version` 保存，防止旧 revision 静默覆盖，保存后启动 run | 批量编辑 |
| M.7 | 阶段验收 | 从 UI 创建、保存、启动并观察运行结果 | 打包发布 |

## 7. M.1前置清单

进入 M.1 前建议确认：

- 新增节点定义接口的路径是否使用 `/api/v1/node-definitions`
- 返回字段是否使用显式 API DTO，而不是直接序列化 `NodeDefinitionSpec`
- `implementation_path` 是否不暴露给 UI
- 当前没有 `config_schema`，M.1 是否明确不返回配置 schema
- `DelayTestNode` / `FaultTestNode` 是否默认隐藏
- 测试节点可见性是否由后端 API 层控制，而不是 UI 硬编码
- API 是否继续使用统一 envelope
- API 是否继续受本地 token 保护
- Avalonia DTO 是否放入 `EngineHostDtos.cs`
- API Client 方法是否命名为 `ListNodeDefinitionsAsync`
- 测试是否覆盖默认可见节点、隐藏测试节点、端口、排序和鉴权

## 8. M.5 / M.6编辑保存前置清单

进入真正编辑和保存前建议确认：

- UI 是否把编辑内容保存在本地 draft 状态
- validate 是否只调用 `POST /api/v1/workflows/validate` 或保存 workflow 的 validate 端点
- validate 是否不创建 revision
- save 是否必须携带 `base_revision_id` 或 `expected_version`
- 后端是否能检测当前 workflow revision 已变化
- 冲突时是否返回 `WORKFLOW_REVISION_CONFLICT`
- UI 是否在冲突时停止保存并提示刷新
- 保存成功后是否刷新 workflow detail、current revision、definition hash 和列表
- 启动 run 是否使用保存后的 workflow 当前 revision
- 未保存 draft 是否不会影响现有 run

## 9. 与L.4连接体验稳定化的关系

L.4 可以作为 M 阶段前或 M 阶段中的小修分支，但不建议阻塞 M.1。

L.4候选范围：

- 连接错误文案微调
- WebSocket 断线和重连状态更清晰
- token 为空、错误、轮换或失效时的提示统一
- WebSocket URL 日志和错误展示脱敏复核
- 手动刷新入口和当前连接状态提示

L.4不应进入：

- token 持久化
- UI 自动读取后端 token 文件
- UI 托管 EngineHost
- 长期离线缓存

## 10. 打包发布前置清单

打包发布建议继续后置。进入打包前至少需要单独确认：

- EngineHost 是独立启动、组合脚本启动，还是由 UI 托管
- Python runtime、依赖、Alembic migrations 和 `runtime/` 数据目录如何分布
- token 文件生成、读取、轮换和清理策略
- 用户级 UI 配置位置和迁移策略
- 日志目录、崩溃诊断和脱敏规则
- 空数据库首次启动、已有 workflow 和 EngineHost 重启恢复 smoke 是否能在打包形态复现
- 是否需要安装器、便携版、后台服务、系统托盘或自动更新

当前不建议直接打包，因为 UI 还缺少 workflow 定义和节点配置入口。先完成 M 阶段最小闭环后，打包验收价值更高。

## 11. M.0结论

M.0结论：

- 下一阶段主线建议定为阶段M：工作流定义与节点配置入口
- 可用节点类型查询应由后端基于 `NodeRegistry` 提供只读 API，但必须通过显式 API DTO 暴露
- UI 不应硬编码内置节点清单
- 当前后端已有 workflow CRUD、revision 和 validate 基础
- 当前缺口优先级是节点定义只读 API，其次是 Avalonia Client 接入 workflow detail / create / update / validate
- 当前节点定义没有配置 schema，第一版配置编辑建议先用 JSON 文本，不直接做动态表单或完整画布
- `DelayTestNode` / `FaultTestNode` 应由后端 API 默认隐藏，不交给 UI 硬编码过滤
- workflow 编辑必须区分 draft、validate 和 save
- 正式保存必须带 revision 并发保护，避免旧 revision 静默覆盖

建议下一小步：

```text
M.1：节点定义只读 API
```

M.1只补后端只读接口、显式 API DTO、Avalonia DTO / API Client 和对应测试，不进入 workflow 创建 UI。
