# 阶段 Q：前端循环与表流转实施计划

> 文档状态：前端后续执行稿
> 当前用途：承接已完成的循环调度与阶段 Q 后端能力，规划循环节点 UI、表输入输出 UI、数据预览和后台运行界面的接入顺序
> 代码核对日期：2026-07-10
> 当前代码基线：本地 `main` 已与 `origin/main` 对齐；工作区除本文外无其他未提交改动
> 当前边界：本文只记录实施方案；每个实施批次开始前仍需重新检查分支、工作区和并行 UI 改动

## 1. 当前结论

当前前端后续工作应收束为两条主线：

```text
循环节点与循环运行 UI
+
阶段 Q 表流转与后台运行 UI
```

两条主线共享一个前置条件：节点配置保存必须从“整段替换 `config`”改成“按配置分区合并并保留未知字段”。

否则会出现以下问题：

- 循环节点中暂未结构化显示的数组、对象字段被保存操作删除。
- 阶段 Q 的 `input_sources`、`output_targets`、`output_save` 被业务配置表单覆盖。
- 插件或后续扩展写入节点 `config` 的附加字段无法稳定保留。

因此，不能直接从 XAML 控件开始实施，应先稳定前端配置读写和后端循环真实控制边界。

## 2. 当前代码状态

### 2.1 循环后端

当前后端已经具备：

- enabled 循环区域校验。
- `LoopRun` 和 `LoopIterationRun` 记录。
- 循环轮次内节点关联。
- `continue_loop`、`end_loop` 和最大轮数收口。
- 循环失败、取消和恢复幂等。
- 循环、轮次和轮次表引用查询 API。

当前仍需在 UI 实施前收口：

| 问题 | 当前情况 | 收口方向 |
| --- | --- | --- |
| 内置判断节点真实控制 | 内置控制状态仍固定输出 `actual_control=false` | 由调度层根据 enabled 循环上下文决定是否应用控制，不让用户手工配置该字段 |
| 最大轮数来源重复 | `LoopStartNode.max_loop_count` 用于预览计算，真实调度使用循环区域 `max_iterations` | UI 只把循环区域 `max_iterations` 作为真实执行上限 |
| 循环 ID 重复 | 起点节点、判断节点和循环区域均使用 `loop_id` | 循环区域编辑器统一校验并同步相关节点 |
| 分支字段边界 | 判断节点输出分支，循环区域也声明继续和结束分支 | 明确真实调度使用的唯一分支契约后再开放结构化编辑 |
| 轮次节点查询 | 后端保存了轮次和节点关联，但 API 尚无轮次节点列表 | 增加只读查询入口，UI 不按节点名称猜测轮次 |
| 轮次列表分页 | 当前循环和轮次列表没有分页参数 | 增加分页，避免大轮次运行一次返回全部记录 |

### 2.2 阶段 Q 后端

当前后端已经具备：

- 节点定义声明具名输入表槽位和输出表槽位。
- 稳定输入选择器解析。
- 当前表、内存表、运行内 SQL 表输出目标映射。
- 新建表和已有表目标区分。
- 运行内 SQL 事务化覆盖和内存表原子替换能力。
- TableRef 表类型、输出槽位、预览持久性和可读状态返回。
- 后台运行启动、查询、取消、重试和运行表清理接口。
- 数据 rows 分页读取。

当前 C# 前端尚未完整接入：

| 后端契约 | 前端当前缺口 |
| --- | --- |
| `input_table_slots` | `NodeDefinitionDto` 没有接收字段 |
| `output_table_slots` | `NodeDefinitionDto` 没有接收字段 |
| `output_slot` | `TableRefDto` 没有接收字段 |
| `table_type` | `TableRefDto` 没有接收字段 |
| `preview_persistence` | `TableRefDto` 没有接收字段 |
| `can_read_rows` / `supports_paged_rows` | `TableRefDto` 没有接收字段 |
| `trigger_source` | `WorkflowRunDto` 没有接收字段 |
| 后台启动、列表、重试、清理 | `IEngineHostApiClient` 尚未提供对应方法 |
| 循环和轮次查询 | C# 尚无 DTO、客户端方法和运行监视状态模型 |

### 2.3 当前前端已有基础

当前前端已经具备：

- 所有带后端 Schema 的节点默认进入通用配置编辑路径。
- 循环节点名称、基础字段和枚举值汉化。
- 工作流高级 JSON 编辑入口。
- 工作流草稿节点、连接、配置字和保存校验状态。
- 运行列表、节点运行列表和数据预览工作台。
- TableRef 查询和 rows 分页读取。

高级 JSON 可以作为前期调试入口，但不能替代正式循环结构编辑和表槽位选择 UI。

## 3. 公共前置：配置分区合并

### 3.1 当前问题

当前结构化节点配置保存会使用表单生成的新对象整段替换节点 `config`。

通用表单只编辑：

- 字符串。
- 整数。
- 小数。
- 布尔值。
- 静态枚举。

数组、对象、表输入选择器、输出目标以及插件附加配置不在表单结果中，因此整段替换会造成字段丢失。

### 3.2 目标

将节点配置拆成可独立修改的配置分区：

```text
业务配置字段
表输入绑定
表输出目标
节点扩展配置
```

每个编辑器只修改自己负责的键，保留其他键和值。

### 3.3 硬边界

- 业务 Schema 表单只更新本次实际提交的业务字段。
- 表输入编辑器只更新 `input_source`、`input_sources` 或统一后的正式键。
- 表输出编辑器只更新 `output_target`、`output_targets`、`output_save` 或统一后的正式键。
- 循环区域编辑器只更新工作流 `control_protocol` 及明确需要同步的循环节点字段。
- 未识别字段必须原样保留。
- 删除字段必须由明确的“清除”操作触发，不能因为控件未显示而自动删除。

### 3.4 验收

- 修改普通业务字段后，表输入输出配置保持不变。
- 修改表输入输出配置后，节点业务配置保持不变。
- 修改循环基础字段后，数组和对象字段保持不变。
- 高级 JSON 中的未知扩展字段不会被结构化编辑器清除。

## 4. 循环节点与循环运行 UI

### 4.1 节点配置层

循环起点和循环判断节点继续使用节点配置区域编辑自身计算参数。

需要补充的通用编辑能力：

- 字符串数组编辑，例如循环字段列表。
- 固定值编辑。
- 当前行字段值来源编辑。
- 条件值来源编辑。
- 根据条件模式显示或隐藏相关字段。

节点配置层不负责维护整个循环区域的成员关系。

### 4.2 工作流循环区域层

在工作流“连接”附近增加独立的“循环区域”配置区，因为循环区域同时引用多个节点，属于工作流结构，不属于单个节点业务配置。

第一版字段：

| 字段 | UI 形式 | 说明 |
| --- | --- | --- |
| 循环 ID | 文本输入 | 工作流内唯一 |
| 循环起点 | 节点下拉 | 选择循环入口节点 |
| 循环体节点 | 多选节点列表 | 第一版保持串行且不允许重叠 |
| 循环判断节点 | 节点下拉 | 选择输出循环判断信号的节点 |
| 循环出口 | 节点下拉，可为空 | 循环结束后放行的节点 |
| 最大轮数 | 整数输入 | 真实执行唯一上限 |
| 输入模式 | 固定枚举 | 第一版仅支持 `row` |
| 启用真实循环 | 开关 | 同步工作流 `control_protocol.mode` 和区域 `enabled` |

### 4.3 循环编辑校验

UI 提交前应检查：

- 循环 ID 非空且唯一。
- 起点和判断节点不能相同。
- 循环体不能为空。
- 循环体不包含起点、判断和出口节点。
- 同一个节点不能同时属于两个第一版循环区域。
- 循环区域节点必须存在于当前工作流草稿。
- 真实循环启用时，工作流控制协议必须为 enabled。
- 节点 `loop_id` 与循环区域 `loop_id` 保持一致。

后端仍是最终校验来源，UI 不独自定义执行规则。

### 4.4 循环运行监视

在运行详情中增加独立的循环只读区域：

```text
循环列表
-> 选中循环
-> 轮次列表
-> 选中轮次
-> 本轮节点和输入/输出表
```

建议显示：

| 层级 | 信息 |
| --- | --- |
| 循环 | 循环 ID、状态、当前轮数、最大轮数、结束原因、错误 |
| 轮次 | 轮次序号、状态、输入表、输出表、失败节点、开始和结束时间 |
| 轮次节点 | 节点实例、角色、状态、进度、错误 |
| 轮次表 | 输入、输出、中间表角色和 TableRef 状态 |

### 4.5 性能边界

- 循环和轮次列表使用分页。
- 只在选中循环后加载轮次。
- 只在选中轮次后加载节点和表关联。
- 不在运行列表中携带节点详情和表 rows。
- 轮次表详情复用当前 run 已加载的 TableRef，通过 ID 关联，避免逐表重复请求。
- 表数据继续按用户选择后分页读取。

## 5. 阶段 Q 节点表输入输出 UI

### 5.1 前端契约接入

先扩展 C# DTO 和目录模型，使前端可以读取：

- 输入槽位名称、显示名、说明、是否必填、允许的存储类型和默认来源。
- 输出槽位名称、显示名、说明、默认角色和允许的输出目标类型。
- TableRef 的来源节点、输出槽位、表类型、预览持久性和可读状态。
- WorkflowRun 的运行模式和触发来源。

### 5.2 节点配置区位置

在当前选中节点的业务配置下方增加两个独立区域：

```text
输入表
输出目标
```

只有节点定义声明了对应槽位时才显示。

UI 不按 `FilterRowsNode`、`PluginNode` 等节点类型写分支，只按节点目录的槽位声明生成控件。

### 5.3 输入表选择

每个输入槽位显示：

- 中文显示名和英文槽位名。
- 槽位说明。
- 是否必填。
- 允许的表类型。
- 当前选择的稳定来源。

第一版选择项：

| 类型 | 保存内容 |
| --- | --- |
| 当前表 | 保存 `current`，不保存运行期 ID |
| 上游当前表 | 来源节点 + 输出槽位或 CURRENT 角色 |
| 上游内存表 | 来源节点 + 输出槽位/逻辑表名 + MEMORY |
| 上游运行内 SQL 表 | 来源节点 + 输出槽位/逻辑表名 + RUNTIME_SQL |
| 上游外部 SQL 引用表 | 来源节点 + 输出槽位/逻辑表名 + EXTERNAL_SQL |

工作流定义只保存稳定选择器，不保存 `table_ref_id`。

表选择候选优先根据当前工作流图和上游节点输出槽位构建。已选择运行的 TableRef 可作为辅助提示，但不能成为工作流定义的唯一依据。

### 5.4 输出目标选择

每个输出槽位根据后端声明显示允许的目标：

| 目标 | 表名行为 |
| --- | --- |
| 当前表 | 不可命名 |
| 新建内存表 | 用户填写逻辑表名 |
| 新建运行内 SQL 表 | 用户填写逻辑表名 |
| 已有内存表 | 从可用稳定表目标中选择，表名锁定 |
| 已有运行内 SQL 表 | 从可用稳定表目标中选择，表名锁定 |

UI 只解决“写到哪里”，不提供统一的覆盖、追加、更新或合并策略。具体写入方式继续由节点业务配置和节点实现决定。

### 5.5 输入输出同步

当用户为节点选择输入表后，可以将输出目标默认同步到同一张内部表。

边界如下：

- 只作为首次选择时的默认值。
- 用户手动修改输出后，不再自动覆盖。
- 是否允许选择已有表由输出槽位声明决定。
- 当前表仍保持不可命名。

## 6. 数据预览 UI

### 6.1 表目录展示

数据预览表选择器按类型分组：

- 当前表。
- 内存表。
- 运行内 SQL 表。
- 外部 SQL 引用表。

每张表显示：

- 逻辑表名。
- 表类型。
- 来源节点。
- 输出槽位。
- 版本。
- 生命周期状态。
- 预览持久性。
- 是否可分页读取。

### 6.2 内存表提示

内存表显示“临时内存表”状态。

- 当前 EngineHost 生命周期内可读时允许预览。
- 不把内存表描述为后台长期可回看的持久表。
- 没有稳定快照时明确显示 `memory_only`。
- 运行内 SQL 表显示为工作流运行内持久表。

### 6.3 多表与覆盖状态

- 一个节点可显示多个输出槽位。
- 节点运行详情显示每个输入槽位绑定的 TableRef。
- 同名表被覆盖后，预览显示当前最新状态。
- 已释放、已退休或孤立表不进入可读下拉，或显示为不可读状态。
- rows 继续按 offset / limit 分页读取。

## 7. 后台运行 UI

### 7.1 运行触发

工作流界面增加后台运行命令，调用后端后台运行入口。

后台运行和手动运行继续共用：

- WorkflowRun。
- Supervisor。
- workflow process。
- TableRef。
- 数据预览 API。
- 配置字执行链路。

### 7.2 运行列表

运行列表显示并支持筛选：

- 工作流。
- 状态。
- `run_mode`。
- `trigger_source`。
- 开始和结束时间。

后台运行使用 `background_manual` 作为触发来源，UI 显示中文“后台手动运行”。

### 7.3 后台操作

第一版接入：

- 启动后台运行。
- 取消运行。
- 基于原 revision 重试。
- 查看运行表目录和数据预览。
- 对终态运行执行用户手动表清理。

清理操作必须明确确认，且不能用于仍在运行的 workflow run。

## 8. 推荐实施顺序

本节只描述宏观依赖顺序。具体文件范围、测试、提交边界以第 13 节为准；性能与耦合要求以第 17 节为准。若三处表述不一致，以第 13 节和第 17 节的约束为最终执行依据。

### 阶段 UI-0：同步前端重构基线

- 等当前前端重构提交完成。
- 同步最新 `origin/main`。
- 确认工作树干净或只包含本阶段文件。
- 重新运行当前 Avalonia 定向测试，建立基线。

### 阶段 UI-1：配置合并语义收口

- 节点业务配置改为字段级合并。
- 保留数组、对象和未知扩展字段。
- 为表输入、表输出和循环区域预留独立 patcher。
- 补配置保留和删除边界测试。

### 阶段 UI-2：循环真实控制后端前置收口

- `LoopJudgeNode` 继续只输出控制意图，不允许用户配置 `actual_control`。
- `control_signal_interpreter` 只有在当前 `NodeRun` 关联到 enabled 循环当前轮且角色为 `JUDGE` 时，才把控制意图授权为真实循环决策。
- 未关联循环、关联角色不是 `JUDGE`、目标循环不匹配时均不得产生调度副作用。
- `advance_serial_loop_from_decision` 继续只接受已经由调度层授权的有效控制信号。
- 真实最大轮数只使用循环区域 `max_iterations`；`LoopStartNode.max_loop_count` 明确为预览字段。
- 第一版继续和结束分支固定为 `continue_loop`、`end_loop`，UI 不开放自定义；后端校验拒绝其他值，避免保存后被静默忽略。
- 增加轮次节点只读 API。
- 为循环和轮次查询增加分页。
- 为运行 NodeRun、TableRef 目录增加后端分页和筛选，禁止前端先全量拉取再切片。
- 固定运行内已有输出目标的逻辑表身份，并增加注册表索引查询，避免节点或循环每轮遍历整个 run 的 TableRef。
- 补内置循环节点端到端测试。

### 阶段 UI-3：前端 DTO 和 API 客户端接入

- 接入节点输入输出表槽位 DTO。
- 接入增强 TableRef 字段。
- 接入 `trigger_source`。
- 接入后台运行、重试、清理接口。
- 接入循环、轮次、轮次节点和轮次表接口。

### 阶段 UI-4：循环结构化编辑

- 增加循环区域 reader、draft、validator 和 patcher。
- 增加工作流级循环区域组件。
- 补循环节点数组和值来源编辑。
- 保留高级 JSON 作为调试入口。

### 阶段 UI-5：循环运行监视

- 增加循环列表。
- 增加轮次分页列表。
- 增加轮次节点和表查看。
- 与现有数据预览入口联动。

### 阶段 UI-6：阶段 Q 表绑定编辑

- 增加通用输入槽位选择器。
- 增加通用输出目标选择器。
- 保存稳定选择器和目标映射。
- 补节点切换、草稿恢复和配置保留测试。

### 阶段 UI-7：数据预览和后台运行增强

- 按表类型分组。
- 显示来源节点、输出槽位和预览持久性。
- 增加后台启动、筛选、重试和清理入口。
- 保持所有 rows 分页读取。

## 9. 耦合硬边界

| 边界 | 要求 |
| --- | --- |
| UI 不理解节点业务 | 表选择区只读取槽位声明，不按节点类型写业务分支 |
| 循环区域属于工作流结构 | 不把循环体和出口成员关系塞进单个节点业务表单 |
| 后端是最终校验来源 | UI 提前提示，但不复制一套独立执行规则 |
| 工作流不保存运行期 TableRef ID | 保存稳定来源节点、输出槽位、表角色、存储类型和逻辑表名 |
| 配置分区独立修改 | 业务配置、表绑定、循环结构和配置字互不覆盖 |
| 主窗口只做协调 | `MainWindowViewModel` 只桥接当前工作流、运行、节点选择、连接设置和顶层通知，功能状态归属子 ViewModel |
| 功能依赖小接口 | 循环查询、运行表目录和后台运行分别通过小型 gateway/service 暴露，不让子 ViewModel 依赖完整 API 客户端 |
| 不传整表 | UI 只读取元数据和分页 rows |
| 循环运行按需加载 | 不一次加载全部循环、轮次、节点和表 |
| 运行内逻辑表身份唯一 | `(workflow_run_id, storage_kind, role, logical_table_id)` 表示一条逻辑表版本链，来源节点和输出槽位只作为显示元数据 |
| 输入和输出身份分离 | 输入选择器可用来源节点和输出槽位区分候选；已有输出目标不能把来源节点误当作目标身份的一部分 |
| 后台运行不新增执行器 | 复用普通 WorkflowRun 和 workflow process |
| 配置字不控制表产物 | 配置字继续只限制日志、事件、进度和诊断反馈 |
| 外部副作用节点化 | 真实 SQL 和本地文件修改继续由指定节点负责 |

## 10. 性能硬边界

- 节点目录只加载槽位元数据，不加载表 rows。
- 输入表候选只按当前节点的直接上游依赖缩小范围。
- NodeRun、TableRef 表目录和运行列表必须在 SQL 层分页、筛选，不能读取全量后再切片。
- 循环轮次按选中循环分页加载。
- 轮次节点和表只在选中轮次后加载。
- 数据预览继续使用后端分页 rows API。
- 不在事件、日志、运行列表和节点目录中携带大表数据。
- UI 刷新只更新受影响的运行、循环、轮次和表状态。
- 同一草稿 JSON revision 只解析一次，所有 reader 共享同一份不可变解析快照。
- run、loop、iteration 和数据预览切换同时使用请求版本号与 `CancellationTokenSource`，旧请求既取消也不得覆盖新状态。
- 运行事件触发的刷新需要合并，循环监视、表目录和数据预览共享 run 级元数据缓存，避免各组件重复加载相同 NodeRun/TableRef。
- 已有输出目标通过注册表索引查找最新版本，禁止每次节点执行或循环迭代扫描整个 run 的 TableRef。

## 11. 完成标准

完成本文后，应达到：

- 用户可以不编辑原始 JSON 创建和修改第一版串行循环区域。
- 循环起点、循环体、判断节点和出口关系清楚可见。
- 运行详情可以按循环和轮次查看节点及表状态。
- 节点配置可以按声明选择输入表和输出目标。
- 修改业务配置不会删除表绑定和扩展配置。
- 数据预览可以区分当前表、内存表、运行内 SQL 表和外部 SQL 引用表。
- UI 可以区分手动运行和后台运行，并支持后台重试和手动清理。
- 所有列表和表数据保持按需加载，不因循环轮次或多表数量增加而全量读取。

## 12. 当前代码核对清单

本节用于固定本计划所依据的真实代码入口。执行时如果文件已经再次拆分，应沿用新结构，不把逻辑重新合并回旧文件。

### 12.1 循环控制链

| 职责 | 当前文件 | 当前事实 |
| --- | --- | --- |
| 循环节点控制表 | `src/flowweaver/nodes/table_control_status.py` | `publish_control_status(...)` 固定写出 `actual_control=false` |
| 循环判断节点 | `src/flowweaver/nodes/table_loop_judge_node.py` | 输出 `loop_decision`、目标循环和所选分支，但节点自身不调度 |
| 控制信号解释 | `src/flowweaver/workflow_process/control_signal_interpreter.py` | 当前在读取轮次关联前先拒绝 `actual_control=false`，因此内置判断节点不能直接推进真实循环 |
| 循环状态推进 | `src/flowweaver/workflow_process/loop_control_advance.py` | 已支持继续、结束、最大轮数、幂等和状态竞争保护 |
| 循环初始化 | `src/flowweaver/workflow_process/loop_runtime_initialization.py` | 真实最大轮数来自循环区域 `max_iterations` |
| 轮次节点关联 | `src/flowweaver/engine/runtime_loop_iteration_node_run_store.py` | 已保存 `ENTRY`、`BODY`、`JUDGE` 等轮次角色 |
| 循环查询 API | `src/flowweaver/api/routes_run_loops.py` | 已有循环、轮次、轮次表引用查询；缺轮次节点明细和分页 |
| 循环 API 输出 | `src/flowweaver/api/runtime_loop_responses.py` | 已有 LoopRun、LoopIterationRun、LoopIterationTableRef JSON 输出 |

当前真实循环测试 `tests/integration/test_loop_runtime_initialization.py` 使用测试 helper 手工创建 `actual_control=true` 的控制表，尚未证明内置 `LoopJudgeNode` 输出可以直接推进下一轮。

### 12.2 节点配置保存链

| 职责 | 当前文件 | 当前事实 |
| --- | --- | --- |
| Schema 解析 | `Avalonia_UI/Models/NodeConfigSchemaParser.cs` | 已识别数组和对象类型 |
| 可编辑字段筛选 | `Avalonia_UI/Models/NodeConfigDraftBuilder.cs` | 只把字符串、数字、布尔和枚举标记为可编辑 |
| 表单转 config | `Avalonia_UI/Models/NodeConfigEditableDraftConfigBuilder.cs` | 只生成结构化表单中的基础字段 |
| 节点 config 写回 | `Avalonia_UI/Models/NodeConfigDraftJsonPatcher.cs` | 当前整段替换节点 `config` |
| 应用命令 | `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.NodeConfig.Commands.cs` | 当前把表单生成结果直接交给整段替换 patcher |
| 现有测试 | `Avalonia_UI.Tests/NodeConfigDraftJsonPatcherTests.cs` | 当前测试名称和断言明确按“替换 config”验证 |

配置字 patcher `Avalonia_UI/Models/WorkflowDefinitionDraftRuntimeOptionsPatcher.cs` 已经证明“只修改负责的工作流分区并保留其他结构”是现有可复用模式。

### 12.3 阶段 Q 契约

| 后端能力 | 当前后端文件 | 当前前端状态 |
| --- | --- | --- |
| 节点输入/输出表槽位 | `src/flowweaver/api/routes_node_definitions.py` | `NodeDefinitionDto` 未接收 |
| 表类型和预览能力 | `src/flowweaver/api/table_ref_responses.py` | `TableRefDto` 未接收增强字段 |
| 后台运行来源 | `src/flowweaver/api/runtime_workflow_responses.py` | `WorkflowRunDto` 未接收 `trigger_source` |
| 后台启动 | `src/flowweaver/api/routes_workflow_runs.py` | `IEngineHostApiClient` 无对应方法 |
| 后台筛选 | `src/flowweaver/api/routes_run_queries.py`、`routes_runs.py` | 客户端未传 `run_mode`、`trigger_source`、`offset`、`limit` |
| 后台重试 | `src/flowweaver/api/routes_run_actions.py` | 客户端无对应方法 |
| 运行表清理 | `src/flowweaver/api/routes_run_tables.py` | 客户端无对应方法 |

当前默认节点定义共 41 个，其中 24 个节点已经声明输入或输出表槽位。UI 必须按声明显示，不能假设所有节点都有表绑定区域。

### 12.4 当前前端拆分结构

实施时继续采用：

```text
DTO
-> 功能 gateway / service
-> 纯 Models / Reader / Patcher / state
-> 子功能 ViewModel
-> 独立 UserControl
-> MainWindowViewModel 薄选择与协调桥接
-> 汇总页薄挂载
```

第一版至少拆出：

- `WorkflowLoopRegionsViewModel`
- `WorkflowNodeTableBindingsViewModel`
- `RunLoopMonitorViewModel`
- `BackgroundRunManagementViewModel`

`MainWindowViewModel` 的 partial 文件只允许桥接当前工作流、当前 run、当前节点选择、连接设置和顶层通知。功能列表、分页、缓存、取消令牌、编辑草稿和命令状态必须归属对应子 ViewModel，不能用 partial 文件形成新的语义大类。

禁止把新功能重新堆入：

- `Avalonia_UI/ViewModels/MainWindowViewModel.cs`
- `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
- `Avalonia_UI/Views/Pages/RunMonitorPage.axaml`

上述文件只允许增加构造依赖或一行组件挂载等薄改动。

## 13. 可执行实施批次

以下按宏观批次 A 至 L 的依赖顺序执行。D、E 内部另分明确子批次；每个宏观批次和子批次都必须单独测试、单独中文提交、单独推送，前一项未通过时不得继续下一项。

### 批次 A：节点配置改为合并写回

#### 目标

结构化业务表单只更新自己生成的字段，保留数组、对象、表绑定和未知扩展字段。

#### 修改文件

- `Avalonia_UI/Models/NodeConfigDraftJsonPatcher.cs`
- `Avalonia_UI/Models/NodeConfigDraftApplyResult.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.NodeConfig.Commands.cs`
- `Avalonia_UI.Tests/NodeConfigDraftJsonPatcherTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`

#### 实现要求

1. 新增字段级 patch 方法，例如 `ApplyPatch(...)`。
2. patch 输入包含：
   - 本次需要设置的字段对象。
   - 本次明确需要删除的字段名集合。
3. 设置集合和删除集合不得包含同一个字段。
4. 原节点 `config` 不存在时创建空对象。
5. 原节点 `config` 不是对象时继续拒绝。
6. 未出现在设置或删除集合中的字段原样保留。
7. 节点业务配置命令改用字段级 patch，不再调用整段替换路径。
8. 旧整段替换方法如果保留，必须改名体现 `Replace` 语义，且不能被结构化业务表单调用。

#### 必补测试

- 修改整数业务字段后保留 `fields` 数组。
- 修改枚举业务字段后保留 `condition_value` 对象。
- 修改业务字段后保留 `input_sources` 和 `output_targets`。
- 修改业务字段后保留未知 `plugin_extension`。
- 明确删除字段时只删除指定字段。
- 设置和删除同一字段时返回明确失败。
- 其他节点和工作流根结构不变。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigDraftJsonPatcherTests|MainWindowViewModelWorkflowTests"
```

#### 提交信息

`前端: 保留节点配置扩展字段`

### 批次 B：循环判断由调度层授权

#### 目标

内置 `LoopJudgeNode` 保持输出控制意图；只有真实循环当前轮的 `JUDGE` 节点成功后，调度层才允许该意图推进循环。

#### 修改文件

- `src/flowweaver/workflow_process/control_signal_interpreter.py`
- `src/flowweaver/workflow_process/loop_control_models.py`
- `tests/integration/test_control_signal_interpreter.py`
- `tests/integration/test_loop_runtime_initialization.py`

#### 唯一授权规则

按以下顺序解释控制信号：

1. 只接受 `signal_type=loop_decision`。
2. 查询当前 `completed_node.node_run_id` 的全部轮次关联。
3. 必须恰好存在一个属于当前运行、当前 enabled 循环轮次且角色为 `JUDGE` 的有效关联；零个或多个都拒绝控制。
4. 轮次和 LoopRun 必须存在，并属于当前 `workflow_run_id`。
5. LoopRun 必须仍处于可推进状态。
6. `target_anchor` 或 details 中的 `loop_id` 必须与 LoopRun 匹配。
7. 满足以上条件后，调度层创建一份内部有效信号，将 `actual_control` 规范化为 true，再交给 `advance_serial_loop_from_decision(...)`。
8. 节点输出表本身不回写、不篡改；真实授权只存在于调度解释结果中。

`advance_serial_loop_from_decision(...)` 保留 `actual_control=true` 的严格入口检查，避免其他调用者绕过授权。

解释器不得使用 `links[-1]` 或其他顺序规则静默选择关联。关联歧义必须返回明确拒绝结果，并保持循环状态不变。

#### 必补测试

- 无轮次关联的 `actual_control=false` 信号继续作为预览忽略。
- 关联角色为 `BODY` 的 loop decision 不推进循环。
- 存在轮次关联但没有 `JUDGE` 关联时不推进循环。
- 同一 NodeRun 存在两个 `JUDGE` 关联时拒绝控制，不选择最后一条。
- 关联角色为 `JUDGE` 的内置预览信号可以创建下一轮。
- 目标循环不匹配时无副作用。
- 重复解释同一判断结果不重复创建轮次。
- 内置 `LoopJudgeNode` 输出经过 NodeTaskManager 后完成两轮继续/结束链路。

#### 定向验证

```powershell
.\python312\python.exe -m pytest tests\integration\test_control_signal_interpreter.py tests\integration\test_loop_runtime_initialization.py tests\integration\test_loop_control.py -q
```

#### 提交信息

`后端: 接通循环判断真实调度`

### 批次 C：后端固定第一版循环分支协议

#### 目标

避免工作流保存自定义分支名后，运行时仍按默认分支处理。

#### 修改文件

- `src/flowweaver/workflow/control_protocol_validation.py`
- `tests/unit/test_workflow_validation.py`
- `src/flowweaver/nodes/default_control_loop_node_schemas.py`

#### 实现要求

- `continue_branch` 第一版只允许 `continue_loop`。
- `end_branch` 第一版只允许 `end_loop`。
- 非默认值返回明确工作流校验错误，不能静默接受。
- 本批次只修改后端校验和内置节点 schema，不混入 Avalonia 汉化或 UI 改动。

#### 必补测试

- 默认分支通过校验。
- 自定义继续分支被拒绝。
- 自定义结束分支被拒绝。
- 原 preview 循环定义仍通过校验。

#### 定向验证

```powershell
.\python312\python.exe -m pytest tests\unit\test_workflow_validation.py tests\integration\test_builtin_table_nodes.py -q
```

#### 提交信息

`后端: 固定首版循环分支协议`

### 批次 D：后端运行表身份与查询契约

本宏观批次按 D0、D1、D2 顺序执行。三个子批次必须分别测试、提交和推送，不能合并成一个大提交。

#### 子批次 D0：逻辑表身份与注册索引

**目标**

固定运行内已有输出目标的身份语义，并把最新版本查找从全 run 扫描改为注册表索引查询。

**修改文件**

- `src/flowweaver/workflow_process/table_output_target_models.py`
- `src/flowweaver/nodes/table_node_output_target_lookup.py`
- `src/flowweaver/engine/runtime_table_ref_store.py`
- `src/flowweaver/engine/runtime_table_ref_queries.py`
- `tests/unit/test_table_output_targets.py`
- `tests/integration/test_runtime_store.py`

**身份规则**

- `(workflow_run_id, storage_kind, role, logical_table_id)` 唯一表示一条运行内逻辑表版本链。
- 来源节点、来源 NodeRun 和输出槽位属于产出与显示元数据，不参与已有输出目标身份。
- 两张需要独立覆盖和演进的表必须使用不同 `logical_table_id`。
- 输入选择器仍可使用来源节点实例和输出槽位区分直接上游候选，这不改变输出目标身份。
- 已有输出目标 UI 只能选择逻辑表版本链，不能让用户误以为切换来源节点会改变写入目标。

**实现要求**

- 为 TableRef 注册表增加按上述身份返回最新版本的查询入口。
- 查询在 SQL/注册表层按身份过滤并取最高版本，节点不得调用 `list_by_workflow_run(...)` 后在内存扫描。
- 新建版本、覆盖已有表和清理 TableRef 后同步维护索引语义。
- 不把运行期 `table_ref_id` 写回工作流定义。

**必补测试**

- 同身份多版本只返回最高版本。
- 不同 role 或 storage kind 不会串表。
- 不同来源节点但同逻辑身份仍属于同一版本链。
- 不同 `logical_table_id` 保持独立。
- 清理后索引不返回已释放目标。

**定向验证**

```powershell
.\python312\python.exe -m pytest tests\unit\test_table_output_targets.py tests\integration\test_runtime_store.py -q
```

**提交信息**

`后端: 固定运行内逻辑表身份`

#### 子批次 D1：循环查询分页与轮次节点明细

**目标**

给循环运行监视提供无需猜测、无需 N+1 查询的只读契约。

**修改文件**

- `src/flowweaver/api/routes_run_loops.py`
- `src/flowweaver/api/runtime_loop_responses.py`
- `src/flowweaver/api/run_pagination.py`
- `src/flowweaver/engine/runtime_loop_run_queries.py`
- `src/flowweaver/engine/runtime_loop_iteration_run_queries.py`
- `src/flowweaver/engine/runtime_node_run_queries.py`
- `src/flowweaver/engine/runtime_node_run_store.py`
- `tests/integration/test_api.py`
- `tests/integration/test_runtime_store.py`

**API 契约**

```text
GET /api/v1/runs/{run_id}/loops?offset=0&limit=50
GET /api/v1/runs/{run_id}/loops/{loop_run_id}/iterations?offset=0&limit=50
GET /api/v1/runs/{run_id}/loops/{loop_run_id}/iterations/{iteration_id}/nodes
GET /api/v1/runs/{run_id}/loops/{loop_run_id}/iterations/{iteration_id}/table-refs
```

轮次节点明细至少返回：

- `loop_iteration_id`
- `node_run_id`
- `node_instance_id`
- `role`
- `node_type`
- `status`
- `progress`
- `current_stage`
- `attempt`
- `started_at`
- `finished_at`
- `error`

**实现要求**

- 循环和轮次查询复用现有分页校验。
- RuntimeStore 查询在 SQL 层使用 offset/limit。
- 新增批量 `node_run_id` 查询，不能为每个轮次节点调用一次 `get_node_run`。
- 轮次节点结果按角色和节点实例稳定排序。
- 轮次表引用接口返回轻量 TableRef 摘要，或一次批量解析所需 TableRef；不得为每张表单独请求详情。

**必补测试**

- 循环列表分页。
- 轮次列表分页。
- 非法分页参数返回统一错误。
- 轮次节点接口返回角色和 NodeRun 状态。
- 轮次不属于目标循环或运行时返回 404。
- 轮次表引用使用轻量摘要或批量查询，角色筛选保持兼容。

**定向验证**

```powershell
.\python312\python.exe -m pytest tests\integration\test_api.py tests\integration\test_runtime_store.py -q
```

**提交信息**

`后端: 补齐循环运行查询契约`

#### 子批次 D2：运行元数据分页与轻量表目录

**目标**

在循环监视和数据预览接入前，为 NodeRun 与 TableRef 建立可筛选、可分页、无需全量关联的运行元数据契约。

**修改文件**

- `src/flowweaver/api/routes_run_tables.py`
- `src/flowweaver/api/table_ref_responses.py`
- `src/flowweaver/api/run_pagination.py`
- `src/flowweaver/engine/runtime_node_run_queries.py`
- `src/flowweaver/engine/runtime_table_ref_queries.py`
- `src/flowweaver/engine/runtime_node_run_store.py`
- `src/flowweaver/engine/runtime_table_ref_store.py`
- `tests/integration/test_api.py`
- `tests/integration/test_runtime_store.py`

**API 契约**

```text
GET /api/v1/runs/{run_id}/nodes?offset=0&limit=100&status=...
GET /api/v1/runs/{run_id}/table-refs?offset=0&limit=100&node_run_id=...&table_type=...&lifecycle=...&logical_table_id=...
```

**实现要求**

- NodeRun 和 TableRef 都在 SQL 层应用 offset/limit 与筛选条件。
- 返回分页元数据和总数或明确的下一页判定信息，前端不依赖“少于 limit 即结束”之外的隐式猜测。
- 轻量表目录直接返回 `source_node_instance_id`、`source_node_run_id`、`output_slot`、`table_type`、lifecycle、逻辑表身份和预览能力。
- 后端通过查询联接或批量映射补充 `source_node_instance_id`，禁止前端为了显示来源而加载当前 run 的全部 NodeRun。
- 列表响应不携带 rows、schema 大对象或诊断正文。

**必补测试**

- NodeRun 分页、状态筛选和非法分页参数。
- TableRef 分页及 node run、类型、生命周期、逻辑表筛选。
- 表目录返回 `source_node_instance_id`，且不会产生逐表 NodeRun 查询。
- 空页、末页和清理后目录状态正确。
- 原 rows 分页接口行为不变。

**定向验证**

```powershell
.\python312\python.exe -m pytest tests\integration\test_api.py tests\integration\test_runtime_store.py -q
```

**提交信息**

`后端: 增加运行元数据分页目录`

### 批次 E：前端 DTO、客户端与功能网关

本宏观批次按 E1、E2、E3 顺序执行，只接入已经由后端稳定提供的契约，不增加界面状态。三个子批次必须分别测试、提交和推送。

所有生产路径会调用的方法都必须作为 `IEngineHostApiClient` 的明确接口成员，由生产客户端和相关测试替身在编译期完整实现。禁止用默认 `NotSupportedException` 把缺失实现推迟到用户点击时才暴露。

#### 子批次 E1：节点表槽位与运行表目录

**修改文件**

- `Avalonia_UI/Api/EngineHostDtos.cs`
- `Avalonia_UI/Api/IEngineHostApiClient.cs`
- `Avalonia_UI/Api/EngineHostApiClient.cs`
- `Avalonia_UI/Services/IRunTableDirectoryService.cs`
- `Avalonia_UI/Services/RunTableDirectoryService.cs`
- `Avalonia_UI/ViewModels/NodeDefinitionListItemViewModel.cs`
- `Avalonia_UI/ViewModels/TableRefListItemViewModel.cs`
- `Avalonia_UI.Tests/EngineHostApiClientTests.cs`
- `Avalonia_UI.Tests/NodeDefinitionListItemViewModelTests.cs`

**DTO 与客户端范围**

- 新增 `NodeTableInputSlotDto`、`NodeTableOutputSlotDto` 和分页运行表目录 DTO。
- `NodeDefinitionDto` 接入 `input_table_slots`、`output_table_slots`。
- `TableRefDto` 接入 `source_node_instance_id`、`source_node_run_id`、`output_slot`、`table_type`、lifecycle、`preview_persistence`、`can_read_rows`、`supports_paged_rows`。
- 接入分页 NodeRun、TableRef 目录查询和筛选参数。
- `IRunTableDirectoryService` 对子功能暴露 run 级轻量元数据读取，不暴露完整 API 客户端。

**必补测试**

- 节点定义反序列化表槽位。
- TableRef 反序列化增强字段和分页元数据。
- NodeRun、TableRef 客户端验证路径、offset、limit 和筛选参数。
- `IRunTableDirectoryService` 不触发全量 NodeRun/TableRef 读取。
- 相关 FakeApiClient 显式实现新增方法，旧客户端方法行为不变。

**定向验证**

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostApiClientTests|NodeDefinitionListItemViewModelTests"
```

**提交信息**

`前端: 接入节点表目录契约`

#### 子批次 E2：循环运行查询网关

**修改文件**

- `Avalonia_UI/Api/EngineHostDtos.cs`
- `Avalonia_UI/Api/IEngineHostApiClient.cs`
- `Avalonia_UI/Api/EngineHostApiClient.cs`
- `Avalonia_UI/Services/ILoopRunQueryService.cs`
- `Avalonia_UI/Services/LoopRunQueryService.cs`
- `Avalonia_UI.Tests/EngineHostApiClientTests.cs`

**DTO 与客户端范围**

- 新增 `LoopRunDto`、`LoopIterationRunDto`、`LoopIterationNodeRunDto`、`LoopIterationTableRefDto`。
- 接入循环、轮次、轮次节点和轻量轮次表摘要查询。
- `ILoopRunQueryService` 只暴露循环监视需要的分页查询，不承担 UI 状态。

**必补测试**

- 循环和轮次反序列化分页结果。
- 轮次节点、表摘要反序列化角色和来源字段。
- 每个客户端方法验证 HTTP method、路径和查询参数。
- 相关 FakeApiClient 显式实现新增方法。

**定向验证**

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostApiClientTests"
```

**提交信息**

`前端: 接入循环运行查询契约`

#### 子批次 E3：后台运行管理网关

**修改文件**

- `Avalonia_UI/Api/EngineHostDtos.cs`
- `Avalonia_UI/Api/IEngineHostApiClient.cs`
- `Avalonia_UI/Api/EngineHostApiClient.cs`
- `Avalonia_UI/Services/IBackgroundRunService.cs`
- `Avalonia_UI/Services/BackgroundRunService.cs`
- `Avalonia_UI/ViewModels/WorkflowRunListItemViewModel.cs`
- `Avalonia_UI.Tests/EngineHostApiClientTests.cs`

**DTO 与客户端范围**

- `WorkflowRunDto` 接入 `trigger_source`。
- 新增运行表清理结果 DTO。
- 接入后台启动、按 `run_mode` 和 `trigger_source` 分页筛选、重试、终态运行表清理。
- `IBackgroundRunService` 只封装后台运行管理命令与查询，不新增执行器。

**必补测试**

- WorkflowRun 反序列化触发来源。
- 后台启动、运行筛选、重试和清理验证 HTTP method、路径、参数和 body。
- 相关 FakeApiClient 显式实现新增方法。
- 普通运行客户端行为不变。

**定向验证**

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostApiClientTests"
```

**提交信息**

`前端: 接入后台运行管理契约`

### 批次 F：循环区域纯模型与 Patcher

#### 目标

先实现无 UI 依赖的循环区域读取、草稿、校验和写回。

#### 新增建议文件

- `Avalonia_UI/Models/WorkflowDefinitionDraftSnapshot.cs`
- `Avalonia_UI/Models/WorkflowLoopRegionDraft.cs`
- `Avalonia_UI/Models/WorkflowLoopRegionDraftReadResult.cs`
- `Avalonia_UI/Models/WorkflowLoopRegionDraftReader.cs`
- `Avalonia_UI/Models/WorkflowLoopRegionDraftPatcher.cs`
- `Avalonia_UI/Models/WorkflowLoopRegionDraftValidationResult.cs`
- `Avalonia_UI.Tests/WorkflowLoopRegionDraftReaderTests.cs`
- `Avalonia_UI.Tests/WorkflowLoopRegionDraftPatcherTests.cs`
- `Avalonia_UI.Tests/WorkflowDefinitionDraftParseCacheTests.cs`

#### 实现要求

- 读取和写回工作流根级 `control_protocol`。
- 保留工作流其他根字段、节点、连接、配置字和未知字段。
- 支持新增、修改、删除循环区域。
- 写回循环区域时同步起点和判断节点 config 中的 `loop_id`，但保留节点其他 config 字段。
- 删除循环区域时不自动删除节点。
- 第一版只生成固定分支和 `input_mode=row`。
- 真实循环开关统一写入协议 mode 和区域 enabled。
- 每个草稿 JSON revision 只创建一份不可变 `WorkflowDefinitionDraftSnapshot`，结构、线性链、配置字、循环和表绑定 reader 共享同一解析根。
- `WorkflowDefinitionDraftParseCache` 负责按 revision 缓存解析快照，功能 builder 不得各自再次解析原始字符串。

#### 必补测试

- 空协议读取为空列表。
- 读取一个 enabled 循环。
- 新增、修改、删除循环区域。
- 同步两个节点的 `loop_id`。
- 保留节点表绑定、业务配置和未知字段。
- 非对象协议、重复循环 ID、未知节点返回明确状态。
- 同一 revision 连续读取结构、配置字、循环和表绑定时只发生一次 JSON 解析；revision 改变后只解析一次新快照。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowLoopRegionDraftReaderTests|WorkflowLoopRegionDraftPatcherTests|WorkflowDefinitionDraftParseCacheTests"
```

#### 提交信息

`前端: 增加循环区域草稿模型`

### 批次 G：循环区域结构化编辑 UI

#### 目标

用户不编辑原始 JSON 即可维护第一版串行循环区域。

#### 新增建议文件

- `Avalonia_UI/ViewModels/WorkflowLoopRegionListItemViewModel.cs`
- `Avalonia_UI/ViewModels/WorkflowLoopRegionsViewModel.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.LoopRegions.Bridge.cs`
- `Avalonia_UI/Views/Components/Workflow/WorkflowLoopRegionsView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowLoopRegionsView.axaml.cs`
- `Avalonia_UI.Tests/WorkflowLoopRegionsViewStructureTests.cs`

#### 修改文件

- `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
- `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.State.DraftJson.ChangeHandlers.cs`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs`

#### UI 位置和交互

- 在连接区之后挂载 `<workflow:WorkflowLoopRegionsView />`。
- 列表和编辑草稿分开，避免选择变化立即修改 JSON。
- 起点、判断和出口使用节点下拉。
- 循环体使用显式多选列表。
- 使用开关控制真实循环启用。
- 保存前执行前端快速校验，再调用后端工作流校验作为最终结果。
- 第一版不显示自定义继续和结束分支输入，固定使用 `continue_loop`、`end_loop`。
- `LoopStartNode.max_loop_count` 的中英文标题明确包含“预览”，避免和真实 `max_iterations` 混淆。
- 原始 JSON 编辑入口继续保留。
- 原始高级 JSON 连续输入使用短 debounce，避免每次按键同步刷新所有草稿读取器。
- 结构化 patch 完成后只触发一次统一 revision 刷新，由共享解析快照更新结构、配置字、循环和表绑定状态。
- `WorkflowLoopRegionsViewModel` 持有列表、编辑草稿和命令状态；MainWindow bridge 只同步当前工作流选择、草稿 revision 和顶层通知。

#### 必补测试

- XAML 只通过独立组件挂载。
- 选择循环区域会加载草稿但不立即改 JSON。
- 应用命令成功后更新草稿 JSON 和 dirty 状态。
- 删除循环区域需要确认。
- 语言切换后标题和选项更新。
- 原始 JSON 快速输入只在 debounce 后刷新一次；结构化 patch 只产生一次统一 revision 刷新。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowLoopRegionsViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests|WorkflowSummaryViewStructureTests"
```

#### 提交信息

`前端: 增加循环区域结构化编辑`

### 批次 H：循环运行监视 UI

#### 目标

按需查看循环、轮次、本轮节点和本轮表，不从日志推断结构。

#### 新增建议文件

- `Avalonia_UI/ViewModels/LoopRunListItemViewModel.cs`
- `Avalonia_UI/ViewModels/LoopIterationListItemViewModel.cs`
- `Avalonia_UI/ViewModels/LoopIterationNodeListItemViewModel.cs`
- `Avalonia_UI/ViewModels/RunLoopMonitorViewModel.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.Runs.LoopMonitor.Bridge.cs`
- `Avalonia_UI/Services/RunMetadataCache.cs`
- `Avalonia_UI/Views/Components/RunMonitor/RunLoopMonitorView.axaml`
- `Avalonia_UI/Views/Components/RunMonitor/RunLoopMonitorView.axaml.cs`
- `Avalonia_UI.Tests/RunLoopMonitorViewStructureTests.cs`

#### 修改文件

- `Avalonia_UI/Views/Pages/RunMonitorPage.axaml`
- `Avalonia_UI/ViewModels/MainWindowViewModel.Runs.Selection.cs`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`

#### UI 布局

保持运行页三列主结构：

```text
运行列表 | 节点运行列表 | 运行详情
```

循环监视放入右侧运行详情区域，通过页签或分段视图显示，避免新增第四列压缩可读宽度。

#### 加载规则

- 选择 run 后只加载第一页循环。
- 选择 loop 后加载第一页轮次。
- 选择 iteration 后并行加载本轮节点和表关联。
- `RunLoopMonitorViewModel` 只依赖 `ILoopRunQueryService` 和共享的 run 级元数据缓存，不依赖完整 `IEngineHostApiClient`。
- 切换 run、loop、iteration 时同时递增请求版本号并替换对应 `CancellationTokenSource`；旧请求必须主动取消，返回后也不得覆盖新状态。
- 运行事件触发的刷新按 run 合并，短时间多个事件只排队一次受影响区域刷新。
- 轮次表引用直接使用后端轻量摘要，或通过共享缓存进行一次批量关联；禁止为了每个组件独立加载当前 run 的全部 TableRef。

#### 必补测试

- 选择运行触发循环第一页查询。
- 选择循环后才查询轮次。
- 选择轮次后才查询节点和表。
- 快速切换选择时旧响应不覆盖新状态。
- 快速切换选择时旧请求收到取消信号。
- 同一 run 的循环监视和数据预览不会重复全量加载 NodeRun/TableRef 元数据。
- 无循环运行显示空状态，不显示错误。
- 分页下一页不重复已有项。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "RunLoopMonitorViewStructureTests|MainWindowViewModelWorkflowTests|EngineHostApiClientTests"
```

#### 提交信息

`前端: 增加循环轮次运行监视`

### 批次 I：节点表绑定纯模型与 Patcher

#### 目标

建立和节点业务配置解耦的稳定表选择草稿。

#### 新增建议文件

- `Avalonia_UI/Models/NodeTableInputBindingDraft.cs`
- `Avalonia_UI/Models/NodeTableOutputTargetDraft.cs`
- `Avalonia_UI/Models/NodeTableBindingsDraftReader.cs`
- `Avalonia_UI/Models/NodeTableBindingsDraftPatcher.cs`
- `Avalonia_UI/Models/NodeTableBindingCandidateBuilder.cs`
- `Avalonia_UI.Tests/NodeTableBindingsDraftReaderTests.cs`
- `Avalonia_UI.Tests/NodeTableBindingsDraftPatcherTests.cs`
- `Avalonia_UI.Tests/NodeTableBindingCandidateBuilderTests.cs`

#### 规范化写出格式

输入统一写为：

```json
{
  "input_sources": {
    "in": {
      "type": "upstream_table",
      "source_node_instance_id": "source",
      "output_slot": "out",
      "storage_kind": "RUNTIME_SQL",
      "logical_table_id": "orders"
    }
  }
}
```

输出统一写为：

```json
{
  "output_targets": {
    "out": {
      "target_kind": "new_runtime_sql",
      "logical_table_id": "filtered_orders"
    }
  }
}
```

#### 兼容读取

读取时兼容：

- `input_source`
- `input_sources`
- `input_table_sources`
- `output_target`
- `output_targets`
- `output_table_targets`
- `output_save`

UI 写回后使用规范化键；不得保存 `table_ref_id`。

#### 候选构建规则

- 只从当前节点 `dag_node.upstream_node_ids` 表示的直接上游依赖构建输入候选，不递归展开全部祖先节点。
- 优先使用节点定义的 `output_table_slots`。
- 使用来源节点实例 ID和输出槽位形成稳定选择器。
- 配置中明确命名的新建表可作为后续节点候选。
- 运行时 TableRef 只用于显示最近状态和帮助定位，不作为工作流定义主键。
- 输入候选中的同名表必须同时显示来源节点和输出槽位，用于区分直接上游产出。
- 已有输出目标按 `(workflow_run_id, storage_kind, role, logical_table_id)` 选择逻辑表版本链；来源节点和输出槽位不能作为输出目标身份。
- 候选缓存键使用 `draft revision + selected node ID + catalog hash`，任一部分变化时重建，不能按每次控件刷新重复扫描整个草稿。

#### 必补测试

- 读取单输入旧格式并规范化写回。
- 读取多槽位输入输出。
- 当前表目标不允许逻辑表名。
- 新建目标必须有逻辑表名。
- 已有目标锁定逻辑表名。
- Patcher 只修改表绑定键并保留业务配置。
- 候选只包含 DAG 直接上游依赖，不包含未直连祖先节点。
- 同名输入候选可按来源节点和输出槽位区分，已有输出目标不按来源节点拆成多个身份。
- 相同缓存键复用候选结果，revision、节点或 catalog hash 改变后失效。
- 生成 JSON 中不存在 `table_ref_id`。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeTableBindingsDraftReaderTests|NodeTableBindingsDraftPatcherTests|NodeTableBindingCandidateBuilderTests"
```

#### 提交信息

`前端: 增加节点表绑定草稿模型`

### 批次 J：节点表输入输出选择 UI

#### 目标

按后端槽位声明生成通用输入表和输出目标控件。

#### 新增建议文件

- `Avalonia_UI/ViewModels/NodeTableInputBindingViewModel.cs`
- `Avalonia_UI/ViewModels/NodeTableOutputTargetViewModel.cs`
- `Avalonia_UI/ViewModels/WorkflowNodeTableBindingsViewModel.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.TableBindings.Bridge.cs`
- `Avalonia_UI/Views/Components/Workflow/WorkflowNodeTableBindingsView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowNodeTableBindingsView.axaml.cs`
- `Avalonia_UI.Tests/WorkflowNodeTableBindingsViewStructureTests.cs`

#### 修改文件

- `Avalonia_UI/Views/Components/Workflow/WorkflowSummaryView.axaml`
- `Avalonia_UI/ViewModels/MainWindowViewModel.WorkflowDraft.Selection.ChangeHandlers.cs`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs`

#### UI 位置

在 `<workflow:WorkflowSelectedNodeConfigView />` 后挂载：

```xml
<workflow:WorkflowNodeTableBindingsView />
```

组件内部包含“输入表”和“输出目标”两个未嵌套卡片的分区。节点未声明槽位时整个组件隐藏。

#### 交互要求

- 左侧显示中文说明，保留英文槽位名。
- 输入来源使用下拉菜单。
- 输出目标类型使用下拉菜单。
- 只有新建目标显示表名输入框。
- 选择已有目标后表名只读。
- 已有目标按 storage kind、role 和逻辑表名显示；来源节点和输出槽位仅用于输入候选标签，不作为输出目标选择维度。
- 首次选择输入表时可以建议同步输出目标；用户修改输出后停止自动同步。
- 应用表绑定只调用表绑定 patcher，不触发业务配置保存。
- `WorkflowNodeTableBindingsViewModel` 持有候选、草稿和命令状态；MainWindow bridge 只传入当前节点、草稿 revision 和节点目录 catalog。

#### 必补测试

- 单槽位和多槽位节点正确生成行。
- 无槽位节点隐藏组件。
- 允许的 storage kind 和 target kind 来自节点声明。
- 用户修改输出后不再被输入变化覆盖。
- 应用后业务字段和循环字段保持不变。
- 汉化文本和英文枚举值正确。
- 切换输入候选来源不会伪造新的已有输出目标身份。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "WorkflowNodeTableBindingsViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelLocalizationTests|WorkflowSummaryViewStructureTests"
```

#### 提交信息

`前端: 增加节点表输入输出选择`

### 批次 K：数据预览表目录增强

#### 目标

让数据预览消费后端已经返回的表类型、输出槽位和持久性字段。

#### 修改文件

- `Avalonia_UI/ViewModels/TableRefListItemViewModel.cs`
- `Avalonia_UI/Models/DataPreviewSelectionState.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.DataPreview.Selection.Rebuild.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.DataPreview.Presentation.SourceText.cs`
- `Avalonia_UI/Views/Pages/DataPreviewPage.axaml`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI.Tests/DataPreviewSelectionStateTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelDataTests.cs`
- `Avalonia_UI.Tests/DataPreviewPageStructureTests.cs`

#### 实现要求

- 按 `table_type` 分组，而不是前端重复推断。
- 显示 logical table、输出槽位、storage kind、版本和持久性。
- `memory_only` 显示“临时内存表”。
- `workflow_run_sql` 显示“运行内持久表”。
- `external_source` 显示“外部 SQL 引用”。
- `can_read_rows=false` 的表不进入可加载选项，仍可在状态目录显示不可读原因。
- 来源节点直接使用分页轻量表目录返回的 `source_node_instance_id`；不得为了把 `source_node_run_id` 转成实例名称而加载当前 run 的全部 NodeRun。
- 数据预览按 run 复用共享元数据缓存，只对选中表调用分页 rows API。
- 切换 run 或表时同时使用请求版本号与 `CancellationTokenSource`，主动取消旧目录和 rows 请求。
- 继续使用当前二级状态模型，不退回直接绑定原始 `TableRefs`。

#### 必补测试

- 四类表正确分组和显示。
- 不可读表不会触发 rows 请求。
- 同名表显示来源节点和输出槽位后可区分。
- memory only 状态不会显示为长期持久。
- 当前分页、搜索和编辑草稿行为不回归。
- 快速切换 run 或表时旧请求被取消，旧响应不能覆盖新预览。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "DataPreviewSelectionStateTests|MainWindowViewModelDataTests|DataPreviewPageStructureTests"
```

#### 提交信息

`前端: 增强运行表目录预览`

### 批次 L：后台运行管理 UI

#### 目标

接入后台启动、筛选、重试和用户手动清理，不新增执行链路。

#### 新增建议文件

- `Avalonia_UI/ViewModels/BackgroundRunManagementViewModel.cs`
- `Avalonia_UI/ViewModels/MainWindowViewModel.Runs.BackgroundManagement.Bridge.cs`

#### 修改文件

- `Avalonia_UI/ViewModels/WorkflowRunListItemViewModel.cs`
- `Avalonia_UI/Views/Components/RunMonitor/RunListView.axaml`
- `Avalonia_UI/Views/Components/Workflow/WorkflowListView.axaml`
- `Avalonia_UI/Localization/zh-Hans.json`
- `Avalonia_UI/Localization/en-US.json`
- `Avalonia_UI.Tests/EngineHostApiClientTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelWorkflowTests.cs`
- `Avalonia_UI.Tests/MainWindowViewModelLocalizationTests.cs`

#### 交互要求

- 工作流列表提供后台运行命令。
- 运行列表显示并筛选 `trigger_source`。
- 列表使用 offset/limit 分页。
- 重试明确显示将基于原 revision 创建新 run。
- 只有终态运行允许清理表。
- 清理需要确认，并在成功后刷新该 run 的 TableRef 和数据预览状态。
- 取消继续复用当前取消命令。
- `BackgroundRunManagementViewModel` 只依赖 `IBackgroundRunService`，持有筛选、分页、重试和清理状态；MainWindow bridge 只同步当前工作流、当前 run 和顶层通知。
- 快速切换筛选或页码时主动取消上一请求并保留请求版本保护；运行事件刷新按 run 合并。

#### 必补测试

- 后台启动发送 `background_manual`。
- 运行筛选传递 trigger source、run mode、offset、limit。
- 重试成功后选择新 run。
- 非终态运行禁止清理。
- 清理成功后相关 TableRef 变为不可读或从可读选项移除。
- 手动运行和后台运行继续使用同一运行详情和数据预览。
- 快速切换筛选时旧请求被取消，旧结果不覆盖当前页。

#### 定向验证

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostApiClientTests|MainWindowViewModelWorkflowTests|MainWindowViewModelDataTests|MainWindowViewModelLocalizationTests"
```

#### 提交信息

`前端: 增加后台运行管理入口`

## 14. 全量验证矩阵

### 14.1 后端定向测试

```powershell
.\python312\python.exe -m pytest tests\integration\test_control_signal_interpreter.py tests\integration\test_loop_runtime_initialization.py tests\integration\test_loop_control.py tests\integration\test_api.py tests\integration\test_runtime_store.py tests\unit\test_workflow_validation.py tests\unit\test_table_input_resolver.py tests\unit\test_table_output_targets.py -q
```

### 14.2 后端静态检查

```powershell
.\python312\python.exe -m ruff check src tests migrations
.\python312\python.exe -m mypy src\flowweaver
```

### 14.3 前端定向测试

```powershell
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "NodeConfigDraftJsonPatcherTests|EngineHostApiClientTests|WorkflowSummaryViewStructureTests|MainWindowViewModelWorkflowTests|MainWindowViewModelDataTests|MainWindowViewModelLocalizationTests|DataPreviewPageStructureTests"
```

### 14.4 前端全量测试

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj
```

如果正在运行的 Avalonia_UI 锁住 Debug 输出，使用隔离输出目录验证，不删除或覆盖被占用文件：

```powershell
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj /p:UseSharedCompilation=false /p:UseAppHost=false /p:OutputPath=".tmp\dotnet-verify-out\Avalonia_UI.Tests\"
```

### 14.5 人工 UI 验收

1. 创建起点、循环体、判断和出口节点。
2. 在循环区域 UI 中建立 enabled 串行循环。
3. 保存并重新加载，确认区域和节点 `loop_id` 不丢失。
4. 运行两轮循环，确认运行监视显示两轮和每轮节点。
5. 给纯表节点选择上游运行内 SQL 表作为输入。
6. 输出另存为命名内存表和运行内 SQL 表。
7. 修改节点业务字段，确认表绑定未被清除。
8. 在数据预览中确认表类型、来源节点、输出槽位和持久性。
9. 启动后台运行，关闭工作流详情后仍可从运行列表查看结果。
10. 重试后台运行并确认生成新 run。
11. 对终态运行执行手动清理，确认不可再读取已释放表。

## 15. 提交、推送与竞态规则

### 15.1 每批次开始前

```powershell
git status --short --branch
git log --oneline HEAD..origin/main --max-count=10
```

- 如果落后远端，先同步并重新读取本批次目标文件。
- 如果存在其他任务的未提交改动，不覆盖、不回退、不混入本批次提交。
- 如果同一目标文件正在被其他任务修改，先停下确认合并基线。

### 15.2 每批次结束后

- 先运行该批次定向测试。
- 再检查 `git diff --check`。
- 只暂存本批次文件。
- 使用本文给出的中文提交信息。
- 推送当前 `main`。
- 推送失败时先拉取并处理真实冲突，不使用强制推送。

### 15.3 停止条件

出现以下任一情况时，当前批次不得提交：

- 定向测试失败且原因与本批次有关。
- 节点业务配置会删除未知字段。
- 工作流定义写入了运行期 `table_ref_id`。
- 未关联 JUDGE 的控制信号产生循环副作用。
- 控制解释器在零个或多个 JUDGE 关联中静默选择一条。
- UI 为具体节点类型写了表绑定业务分支。
- 数据预览或运行列表一次加载整表 rows。
- NodeRun 或 TableRef 目录在后端全量读取后才做前端或内存分页。
- 已有输出目标仍通过遍历整个 run 的 TableRef 查找最新版本。
- 同一草稿 revision 被不同 reader 重复解析。
- 快速切换只忽略旧响应，却没有取消仍在执行的旧请求。
- 新功能状态、分页或取消令牌继续堆入 `MainWindowViewModel` partial。
- 生产调用接口通过默认 `NotSupportedException` 延迟暴露缺失实现。
- 后台运行绕过普通 WorkflowRun 和 workflow process。
- 工作区混入无法确认来源的同文件改动。

## 16. Codex 目标执行说明

以后以本文触发 Codex 目标时，目标应明确为：

```text
以 docs/阶段Q_表流转与后台运行/阶段Q_前端循环与表流转实施计划.md 为执行依据，
严格按 A -> B -> C -> D0 -> D1 -> D2 -> E1 -> E2 -> E3 -> F -> G -> H -> I -> J -> K -> L 顺序实施。
宏观批次仍为 A 至 L；D0-D2 和 E1-E3 也必须作为独立执行、测试、中文提交和推送单位。
不得合并多个宏观批次或子批次提交，不得修改批次范围外的业务代码，不得覆盖并行任务改动。
遇到接口或代码现状与文档不一致时，先以当前代码为准完成只读核对，再更新计划或说明差异。
```

目标完成需要同时满足：

- A 至 C、D0 至 D2、E1 至 E3、F 至 L 全部完成，或明确记录被当前代码替代的执行单位。
- 后端定向测试、静态检查通过。
- 前端定向测试、全量测试通过。
- 人工 UI 验收完成。
- 工作区干净，所有批次提交均已推送。

## 17. 性能与耦合复核补充约束

本节是第 13 节所有执行批次的共同硬边界。第 8 节仅用于查看依赖总览；如概述文字与本节或第 13 节不同，以本节和第 13 节为准。

| 约束项 | 硬边界 | 验收信号 |
| --- | --- | --- |
| 状态归属 | 循环编辑、表绑定、循环监视、后台运行分别由四个子功能 ViewModel 持有；`MainWindowViewModel` 只做选择和通知桥接 | 主窗口 partial 中没有功能列表、分页器、编辑草稿、缓存或取消令牌 |
| 功能接口 | 子 ViewModel 依赖 `ILoopRunQueryService`、`IRunTableDirectoryService`、`IBackgroundRunService` 等小接口，不依赖完整 API 客户端 | 测试可用小型 fake 独立构造功能 ViewModel |
| 接口完整性 | 生产使用的 API 方法必须由接口、生产客户端和相关 fake 在编译期实现 | 不存在默认 `NotSupportedException` 占位实现 |
| 草稿解析 | 每个 JSON revision 只生成一个不可变解析快照，所有 reader 共用解析根 | 缓存测试证明同 revision 多功能读取只解析一次 |
| 草稿刷新 | 原始 JSON 输入短 debounce；结构化 patch 只触发一次统一 revision 刷新 | 连续输入和一次 patch 不会重复重建全部功能状态 |
| 候选缓存 | 表候选缓存键固定为 `draft revision + selected node ID + catalog hash` | 相同键不重扫草稿，任一键变化后正确失效 |
| 直接上游 | 输入候选只读取 `dag_node.upstream_node_ids` 的直接依赖，不递归展开祖先节点 | 未直连节点不会进入候选列表 |
| 表身份 | `(workflow_run_id, storage_kind, role, logical_table_id)` 是运行内逻辑表版本链身份 | 不同来源节点不会被误建为不同输出目标；独立表使用不同 logical ID |
| 表索引 | 最新已有输出目标由注册表/SQL 索引查询，不允许节点扫描整个 run 的 TableRef | 节点执行和循环迭代次数增加时，目标查找不随 run 全部表数量线性扫描 |
| 元数据分页 | NodeRun、TableRef、循环和轮次在 SQL 层 offset/limit 和筛选 | 接口不会先构造全量集合再分页 |
| 轻量目录 | 表目录直接携带 `source_node_instance_id` 和预览所需元数据，不携带 rows | UI 显示来源节点不需要全量加载 NodeRun |
| 请求取消 | run、loop、iteration、表和筛选变化同时使用请求版本与独立 `CancellationTokenSource` | 旧请求收到取消，且迟到响应不能覆盖当前状态 |
| 刷新合并 | 同一 run 的短时间运行事件合并刷新，循环监视和数据预览共享 run 级元数据缓存 | 一个事件窗口内不重复请求同一批 NodeRun/TableRef |
| 禁止 N+1 | 轮次节点、轮次表和来源节点信息使用批量查询、联接或轻量摘要 | 不出现按节点或按表逐条调用详情接口 |
| 数据平面 | 列表、事件和目录只传元数据；表 rows 只由选中表的分页预览接口读取 | 循环轮次和多表数量增长不会放大单次响应为整表数据 |
| 批次边界 | 宏观批次 A-L 保留，D0-D2、E1-E3 也独立测试、提交和推送 | 任一提交只对应一个文档执行单位，可单独回退和验证 |

执行中如果为了赶进度需要突破任一硬边界，应停止当前批次并先更新本文，不允许把临时例外直接固化到代码中。
