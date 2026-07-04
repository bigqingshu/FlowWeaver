# FlowWeaver

模块化数据工作流运行平台。

## 当前阶段

当前已完成第一阶段从阶段 A 到阶段 H 的主程序骨架、执行主循环、节点任务、进程监督、IPC、并发前置和失败策略收口。阶段 I 已完成 I.0 边界确认、I.1 `SharedPublication` Store 边界、I.2 发布输入校验与多表原子发布边界、I.3 `InputSnapshot` Store 边界、I.4 `ReadLease` Store 边界、I.5 读取共享表服务、I.6 共享表节点最小骨架、I.7 WorkflowRunProcess 接入、I.8 生命周期收口和 I.9 阶段总体验收。阶段 J 已完成 J.0 权限审计边界确认、J.1 权限审计协议模型、J.2 Store 边界、J.3 节点权限声明解析、J.4 主循环权限句柄绑定、J.5 内置节点发布前权限检查、J.6 STANDARD 权限审计事件和 J.7 阶段验收复核。阶段 K 已完成 K.0a 架构与验收基线固化、K.0b 默认正式路径烟雾测试及后端组合根缺口修正、K.0c UI API 契约复核与只读接口补齐、K.1 Avalonia_UI 最小桌面 UI 工程骨架与 EngineHost health 连接检查、K.2 UI API Client、K.3 工作流列表与运行入口、K.4 运行和节点状态 REST 恢复视图、K.5 RuntimeEvent WebSocket 事件流和断线重连、K.6 RuntimeEvent/AuditEvent 日志和审计最小只读视图、K.7 TableRef 和 SharedPublication 数据摘要视图、K.8 阶段总体验收。阶段 L 已完成 L.0 桌面端运行入口与配置边界清单、L.1a 后端运行入口收口、L.1b 桌面端运行入口收口、L.1c 组合开发脚本边界、L.2 UI连接配置持久化边界、L.2a 连接配置模型与 Store 边界、L.2b UI接入前复核、L.2c UI启动加载/health成功保存 BaseUrl、L.2d 连接配置失败场景验收复核、L.3 正式路径烟雾清单、L.3a 空数据库正式路径烟雾执行、L.3b 已有工作流正式链路烟雾执行、L.3c EngineHost 重启恢复正式路径烟雾执行和 L 阶段总体验收复核。阶段 M 已完成 M.0 工作流定义与节点配置入口边界清单、M.1 节点定义只读 API、M.2 Workflow detail / revision API 客户端接入、M.3 Workflow definition 只读视图、M.4 最小创建入口、M.5 最小 JSON 草稿校验、M.6 保存 revision 与冲突保护、M.7 工作流定义与运行闭环验收。阶段 N 已完成 N.0 真实 EngineHost + Avalonia API/WebSocket 客户端的正式路径运行闭环 smoke、N.1 连接体验稳定化复核、N.2 打包发布前置清单、N.3 便携版双进程发布布局设计、N.4 便携发布目录生成与 smoke 前置实现、N.5 便携目录后端完整 runtime smoke、N.6 Avalonia publish 与 Desktop 产物 smoke、N.7 Desktop 发布产物 API Client 联调前置 smoke、N.8 Desktop 发布产物 RuntimeEvent WebSocket Client 前置 smoke、N.9 Desktop 发布产物最小 WorkflowRun 事件联调 smoke和 N 阶段便携发布联调总体验收复核。阶段 O 已完成 O.0 到 O.12 便携组合启动入口与 launcher 生命周期收口，包括 backend-only 入口、Desktop 组合入口、真实 Desktop 最小 smoke、失败路径清理和阶段 O 总体验收复核。阶段 P 已完成 P.0 发布物归档与用户手册边界分析、P.0a 发布归档补充边界、P.1 发布归档脚本方案、P.2 runtime audit 与归档前检查、P.3 最小归档脚本、P.4 clean-room 解压 smoke、P.5 便携版用户手册骨架、P.6 用户手册内容收口和 P.7 阶段总体验收复核，后续暂不进入安装器、自动更新或后台服务。后续 UI 技术路线保持为 `Avalonia_UI/` 下的 Avalonia + .NET 10.0 + C# + MVVM，通信方式为 HTTP + WebSocket。

阶段 A 范围包括：

- `pyproject.toml` 项目配置
- Pydantic 公共协议模型
- 字符串枚举
- MessagePack 序列化与反序列化
- 统一错误模型
- 协议单元测试

阶段 B 范围包括：

- SQLAlchemy 元数据模型
- Alembic 初始化与首个迁移
- SQLite 元数据表
- 工作流定义基础 CRUD
- 工作流运行记录基础 CRUD
- 迁移与 RuntimeStore 集成测试

阶段 C 范围包括：

- FastAPI 应用入口
- 统一 API 响应结构
- 工作流定义 HTTP CRUD
- 工作流运行记录查询接口
- WebSocket 事件连接骨架
- API 集成测试

阶段 C.5 基础收口范围包括：

- 包名统一为 `flowweaver`
- 工作流不可变 revision 与 definition hash
- 严格 WorkflowDefinition 校验接口
- SQLite PRAGMA、`data_refs` 字段对齐与 `state_version`
- EngineHost Bootstrap、ServiceContainer、单实例锁与本地 token
- RuntimeEvent 持久化、EventRouter 与 WebSocket 广播
- API view 数据、统一 response_model 与本地 token 校验
- TableLeaseManager 最小 READ/WRITE 租约接口
- NodeRun/WorkflowRun `state_version` 竞争保护验收
- Ruff、mypy 与 Windows CI

阶段 D 当前范围包括：

- Supervisor 创建 WorkflowRunProcess 子进程
- WorkflowRunProcess 加载 workflow run 与 revision
- WorkflowRunProcess 构建 DAG 控制图
- 为 DAG 节点初始化 NodeRun 控制状态
- 节点成功结果推进下游 READY 状态
- 基于持久化 NodeRun 状态恢复 READY 节点
- WorkflowRunProcess 识别工作流终态并退出
- 运行进程心跳、取消请求和失联识别
- 空工作流可启动并完成

阶段 E 到阶段 H 已完成或收口的范围包括：

- NodeTask / NodeExecutor 最小任务模型
- NodeTaskResult 应用、迟到结果拒绝、generation / attempt / executor 边界
- heartbeat / progress 在 executor 执行期间实时上报
- 异常退出、超时、取消和 STAGING 清理边界
- 真实子进程 IPC 往返和单子进程客户端接入主循环
- READY 队列、输入 `TableRef` / `input_refs` 传递和下游推进
- `ImmediateNodeTaskExecutionPool` 与显式 `threaded` 模式配置
- `max_concurrent_node_tasks` 保守配置，默认仍为 `1`
- 多 READY 并发完成顺序、并行失败隔离和执行池 close 边界
- `CONTINUE_INDEPENDENT` 失败分支隔离与 `PARTIAL_FAILURE` 汇总
- `SKIP_DEPENDENTS` 明确保留但不可用，显式配置时拒绝

已具备阶段 I 的前置基础：

- 数据库模型和迁移中已有 `shared_publications`、`shared_publication_members`、`input_snapshots`、`read_leases`
- `RuntimeStore` 已具备 `TableRef` 注册、查询和 STAGING 释放能力
- `RuntimeStore` 已具备 `SharedPublication` 创建、发布输入校验、版本分配和查询能力
- `RuntimeStore` 已具备 `InputSnapshot` 创建、查询和 workflow run 关联能力
- `RuntimeStore` 已具备 `ReadLease` 创建、查询、active/released 区分和释放能力
- WorkflowRunProcess 已在 workflow 进入终态时释放当前 run 未释放的 read lease
- `SharedTableReader` 已支持 `LATEST` / `EXACT_VERSION` 解析，并一次性返回固定版本 `TableRef`、`InputSnapshot` 和 `ReadLease`
- `BuiltinSharedTableNodeRunner` 已具备发布共享表节点和读取共享表节点的最小执行入口
- `WorkflowRunProcess` 默认执行器路径已能分流并执行内置表节点和共享表节点
- 默认 `EngineHost` 已注册第一阶段内置节点定义，API 创建内置节点 workflow 不再依赖测试专用注册表
- 正式子进程启动会显式加载当前 `src` 路径，避免嵌入式 Python 捡到旧安装包
- 读取共享表节点在执行前已校验 `READ_SHARED` 权限并记录 `STANDARD` 审计事件
- UI 前置只读 API 已补齐：审计事件、运行 TableRef、共享发布列表、共享发布版本和 RuntimeEvent 服务端过滤
- K 阶段 UI 后续路径固定为 `Avalonia_UI/`，使用 Avalonia、.NET 10.0、C#、MVVM，通过 HTTP + WebSocket 访问 Python FastAPI EngineHost
- 阶段 I 已具备 A 发布 V1/V2、B 固定读取 V1、B 结束释放 ReadLease 的主循环验收
- `RuntimeDataRegistry` 已具备单表 STAGING 注册、发布为 PUBLISHED、按 workflow/node 查询和节点失败清理
- `TableLeaseManager` 已具备表级 READ / WRITE 租约基础能力
- EngineHost、Supervisor、WorkflowRunProcess 和默认 NodeExecutor 子进程入口已能串通

阶段 L 收口结果与下一步建议：

- L.0 到 L.3c 已完成运行入口、连接配置持久化和三类正式路径 smoke 收口
- L 阶段总体验收复核已新增 `docs/FlowWeaver_阶段L_总体验收复核.md`
- 当前 EngineHost 入口仍为 `.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000`
- 当前 Avalonia UI 入口仍为 `dotnet run --project Avalonia_UI/Avalonia_UI.csproj`
- UI 会持久化上次成功连接的 BaseUrl 和本机 token，启动后自动复用；完整 WebSocket URL 必须脱敏
- L.3a / L.3b / L.3c 已覆盖空数据库、已有工作流和同一 `runtime/` EngineHost 重启恢复
- M.0 工作流定义与节点配置入口边界清单已新增 `docs/FlowWeaver_阶段M.0_工作流定义与节点配置入口边界清单.md`
- M.1 节点定义只读 API 已新增 `GET /api/v1/node-definitions`、后端显式 DTO、Avalonia DTO / API Client 和完成记录 `docs/FlowWeaver_阶段M.1_节点定义只读API.md`
- M.2 Workflow detail / revision API 客户端接入已新增 Avalonia `GetWorkflowAsync()`、`ListWorkflowRevisionsAsync()`、`GetWorkflowRevisionAsync()` 和完成记录 `docs/FlowWeaver_阶段M.2_Workflow详情与Revision客户端接入.md`
- M.3 Workflow definition 只读视图已新增 Definition tab、nodes / connections / revisions / raw JSON 只读展示和完成记录 `docs/FlowWeaver_阶段M.3_Workflow定义只读视图.md`
- M.4 最小创建入口已新增 Avalonia `CreateWorkflowAsync()`、固定 Generate + Filter 模板创建入口、创建后刷新并选中新建 workflow，完成记录 `docs/FlowWeaver_阶段M.4_最小创建入口.md`
- M.5 最小 JSON 草稿校验已新增 Avalonia `ValidateWorkflowDraftAsync()`、Definition 页 draft JSON 编辑和后端 validate 结果展示，完成记录 `docs/FlowWeaver_阶段M.5_最小JSON草稿校验.md`
- M.6 保存 revision 与冲突保护已新增后端 `base_revision_id` 检查、`WORKFLOW_REVISION_CONFLICT`、Avalonia `UpdateWorkflowAsync()` 和 Definition 页 Save，完成记录 `docs/FlowWeaver_阶段M.6_保存Revision与冲突保护.md`
- M.7 工作流定义与运行闭环验收已新增 ViewModel 级创建、加载、编辑 draft、validate、save、启动 run 和 node status 观察闭环测试，完成记录 `docs/FlowWeaver_阶段M.7_工作流定义与运行闭环验收.md`
- N.0 正式路径运行闭环 smoke 已新增真实 EngineHost + Avalonia API/WebSocket 客户端的创建、校验、保存 revision、启动、事件/REST恢复和数据/审计摘要闭环测试，完成记录 `docs/FlowWeaver_阶段N.0_正式路径运行闭环Smoke.md`
- N.1 连接体验稳定化复核已新增连接错误描述和 WebSocket token 脱敏边界，完成记录 `docs/FlowWeaver_阶段N.1_连接体验稳定化复核.md`
- N.2 打包发布前置清单已固化运行时、数据目录、token、日志、配置迁移和发布 smoke 边界，完成记录 `docs/FlowWeaver_阶段N.2_打包发布前置清单.md`
- N.3 便携版双进程发布布局设计已固化便携目录结构、后端工作目录、Python runtime、Avalonia UI、runtime、日志和发布目录 smoke 边界，完成记录 `docs/FlowWeaver_阶段N.3_便携版双进程发布布局设计.md`
- N.4 便携发布目录生成与 smoke 前置实现已新增 `.tmp/FlowWeaverPortable/` 生成器、`.tmp/` 忽略规则和后端工作目录最小 smoke，完成记录 `docs/FlowWeaver_阶段N.4_便携发布目录生成与Smoke前置实现.md`
- N.5 便携目录后端完整 runtime smoke 已验证便携目录自带 `python312/python.exe` 可完成 workflow、run、NodeRun、RuntimeEvent REST、TableRef、SharedPublication、AuditEvent 和 workflow run 日志链路，完成记录 `docs/FlowWeaver_阶段N.5_便携目录后端完整RuntimeSmoke.md`
- N.6 Avalonia publish 与 Desktop 产物 smoke 已新增 `.tmp/FlowWeaverPortable/Desktop/` 发布工具和文件级产物验收，完成记录 `docs/FlowWeaver_阶段N.6_AvaloniaPublish与Desktop产物Smoke.md`
- N.7 Desktop 发布产物 API Client 联调前置 smoke 已验证发布目录 `Avalonia_UI.dll` 中的 API Client 可连接便携 EngineHost 并完成 health、node definitions 和 workflows 基础 API，完成记录 `docs/FlowWeaver_阶段N.7_Desktop发布产物APIClient联调前置Smoke.md`
- N.8 Desktop 发布产物 RuntimeEvent WebSocket Client 前置 smoke 已验证发布目录 `Avalonia_UI.dll` 中的 RuntimeEvent WebSocket Client 可连接便携 EngineHost 并收到 `ENGINE_READY`，完成记录 `docs/FlowWeaver_阶段N.8_Desktop发布产物RuntimeEventWebSocketClient前置Smoke.md`
- N.9 Desktop 发布产物最小 WorkflowRun 事件联调 smoke 已验证发布目录 `Avalonia_UI.dll` 中的 API Client 与 RuntimeEvent WebSocket Client 可组合创建空 workflow、启动 run 并收到 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`，完成记录 `docs/FlowWeaver_阶段N.9_Desktop发布产物WorkflowRun事件联调Smoke.md`
- N 阶段便携发布联调总体验收复核已汇总 N.0 到 N.9 完成矩阵、便携发布边界、自动化验收覆盖和明确不支持能力，完成记录 `docs/FlowWeaver_阶段N_便携发布联调总体验收复核.md`
- O.0 便携组合启动脚本边界分析已明确组合脚本定位、启动顺序、固定端口优先策略、token 交接、日志脱敏、进程生命周期和最小验收标准，完成记录 `docs/FlowWeaver_阶段O.0_便携组合启动脚本边界分析.md`
- O.1 便携组合启动脚本最小实现方案已确认采用 Python launcher 核心加 Windows cmd 包装、生成到便携根目录、第一版支持 `--host` / `--port` / `--no-desktop` / `--health-timeout-seconds` / `--keep-enginehost-on-desktop-exit`，并明确 smoke 优先覆盖 `--no-desktop` 路径，完成记录 `docs/FlowWeaver_阶段O.1_便携组合启动脚本最小实现方案.md`
- O.2 launcher 文件边界已新增 `tools/portable_launcher.py` 的参数、路径、启动命令、token 读取和脱敏 helper，以及对应单元测试；当前不接入生成器、不启动真实 EngineHost 或 Desktop，完成记录 `docs/FlowWeaver_阶段O.2_launcher文件边界.md`
- O.3 launcher 真实启动层已补端口检查、EngineHost 启动、health 轮询、token 等待、日志写入和进程清理；当前仍不接入生成器、不生成 `.cmd`、不启动真实 Desktop，完成记录 `docs/FlowWeaver_阶段O.3_launcher真实启动层.md`
- O.4 `--no-desktop` launcher 端到端 smoke 已使用临时便携目录手工复制 launcher，验证 health、token、鉴权 API、日志脱敏和进程清理；同时修正 Windows 中断信号与 EngineHost 子进程组边界，完成记录 `docs/FlowWeaver_阶段O.4_no_desktop_launcher端到端Smoke.md`
- O.5 生成器接入已让便携目录自动包含 `portable_launcher.py` 和 Windows `start_flowweaver.cmd`，并更新便携 README；O.4 端到端 smoke 已改为直接使用生成器自带 launcher，完成记录 `docs/FlowWeaver_阶段O.5_生成器接入Launcher与启动包装.md`
- O.6 Desktop 启动前置复核已确认短期默认入口继续 backend-only，Desktop 自动启动后置；已固化 Desktop 启动失败、退出、中断和 `--keep-enginehost-on-desktop-exit` 的生命周期策略，完成记录 `docs/FlowWeaver_阶段O.6_Desktop启动前置复核与策略确认.md`
- O.7 Desktop 启动 helper 与假进程验收已补 Desktop stdout/stderr 日志路径、Desktop 启动 helper、退出等待和假进程生命周期测试；`start_flowweaver.cmd` 默认仍为 `--no-desktop`，不打开真实 Avalonia 窗口，完成记录 `docs/FlowWeaver_阶段O.7_Desktop启动Helper与假进程验收.md`
- O.8 Desktop 入口策略与真实 smoke 前置决策已确认采用双入口策略：保留 `start_flowweaver.cmd` 为 backend-only，后续新增 `start_flowweaver_desktop.cmd`；真实 Desktop smoke 后置到独立小步，完成记录 `docs/FlowWeaver_阶段O.8_Desktop入口策略与真实Smoke前置决策.md`
- O.9 独立 Desktop 启动入口生成已让便携目录同时生成 `start_flowweaver.cmd` 和 `start_flowweaver_desktop.cmd`，并更新便携 README 与 N.4 文件级 smoke；`start_flowweaver.cmd` 继续保持 backend-only，完成记录 `docs/FlowWeaver_阶段O.9_独立Desktop启动入口生成.md`
- O.10 真实 Desktop 最小 smoke 已新增显式环境变量保护的真实 `Avalonia_UI.exe` 启动验收，覆盖便携 launcher 默认 Desktop 分支、EngineHost health、鉴权 API、Desktop pid 日志、退出清理和 token 脱敏，完成记录 `docs/FlowWeaver_阶段O.10_真实Desktop最小Smoke.md`
- O.11 Desktop 生命周期真实路径收口已补 Desktop 缺失启动前拒绝和 Desktop 可执行文件无效时 EngineHost 清理验收；真实 Desktop 用户中断由 O.10 覆盖，正常退出与 keep 策略由 O.7 假进程单元测试覆盖，完成记录 `docs/FlowWeaver_阶段O.11_Desktop生命周期真实路径收口.md`
- O.12 阶段 O 总体验收复核已汇总 O.0-O.11 完成矩阵、便携入口说明、进程所有权、日志脱敏、自动化验收覆盖和明确不支持清单，完成记录 `docs/FlowWeaver_阶段O_总体验收复核.md`
- P.0 发布物归档与用户手册边界分析已固化默认 zip 归档输入、必须包含/默认排除路径、release manifest 字段建议、归档前验收顺序、用户手册章节边界和不做事项，完成记录 `docs/FlowWeaver_阶段P.0_发布物归档与用户手册边界分析.md`
- P.0a 发布归档补充边界已固化 Desktop 当前 framework-dependent、`python312/` 需要 runtime audit、统一发布版本、manifest/SHA-256/许可证、仓库外空格/中文路径 clean-room smoke 和关闭 Desktop 对 workflow 的影响，完成记录 `docs/FlowWeaver_阶段P.0a_发布归档补充边界.md`
- P.1 发布归档脚本方案已固化 `tools/create_portable_archive.py` 的职责、CLI 参数、版本来源、Desktop framework-dependent 默认、runtime audit 合约、manifest schema、SHA-256、licenses、安全拒绝项和 P.4 clean-room 输入要求，完成记录 `docs/FlowWeaver_阶段P.1_发布归档脚本方案.md`
- P.2 runtime audit 与归档前检查已新增 `tools/portable_runtime_audit.py` 和单元测试，能识别 Python 3.12、pip、`import site`、Python LICENSE、runtime/token/db/log 阻断项、cache 排除项和 dev/legacy 包 warning，完成记录 `docs/FlowWeaver_阶段P.2_runtime_audit与归档前检查.md`
- P.3 最小归档脚本已新增 `tools/create_portable_archive.py` 和单元测试，能在 runtime audit 通过或 warning 时生成 zip、`release-manifest.json`、`licenses/` 和外部 `.sha256`，并拒绝 runtime/token/db/log、版本不一致、输出越界和 self-contained 模式，完成记录 `docs/FlowWeaver_阶段P.3_最小归档脚本.md`
- P.4 clean-room 解压 smoke 已新增 `tests/integration/test_p4_portable_archive_clean_room_smoke.py`，使用 P.3 zip 和 `.sha256` 解压到仓库外空格/中文路径，验证 backend-only 启动、health、token 鉴权、首次 runtime 生成和 token 脱敏，完成记录 `docs/FlowWeaver_阶段P.4_clean_room解压Smoke.md`
- P.5 便携版用户手册骨架已新增 `docs/FlowWeaver_便携版用户手册.md`，固定快速开始、运行要求、发布包结构、启动方式、Desktop 关闭警示、token、runtime、日志、备份、升级、不支持能力和诊断信息章节，完成记录 `docs/FlowWeaver_阶段P.5_便携版用户手册骨架.md`
- P.6 用户手册内容收口已补齐 `docs/FlowWeaver_便携版用户手册.md` 的首次启动、运行要求、发布包结构、启动方式、workflow 中断风险、token 连接、runtime 备份、日志排查、升级迁移、不支持能力和诊断信息正文，完成记录 `docs/FlowWeaver_阶段P.6_用户手册内容收口.md`
- P.7 阶段 P 总体验收复核已汇总 P.0/P.0a 到 P.6 的完成矩阵、发布归档、runtime audit、manifest/hash/license、clean-room smoke、用户手册、验收命令和明确不支持能力，完成记录 `docs/FlowWeaver_阶段P.7_总体验收复核.md`
- P 后边界分析已明确优先收口发布包内完整用户手册与 docs 入口，再考虑真实 Desktop clean-room smoke；第三方许可证增强和 release 严格模式先分析，self-contained Desktop、代码签名、安装器、自动更新、后台服务和系统托盘保留为独立阶段候选，完成记录 `docs/FlowWeaver_阶段P后_边界分析.md`
- P+1 发布包内完整用户手册与 docs 入口已完成，便携 layout 生成时会复制 `docs/FlowWeaver_便携版用户手册.md`，短 README 会指向完整手册，归档 manifest 和 clean-room smoke 已覆盖该手册文件，完成记录 `docs/FlowWeaver_阶段P+1_发布包内完整用户手册与docs入口.md`
- P+2 真实 Desktop clean-room smoke 已完成，新增显式环境变量保护的发布 zip 解压后真实 Desktop 最小进程级 smoke，覆盖 EngineHost health、token 鉴权、Desktop pid 日志、日志生成、退出清理和 token 脱敏，完成记录 `docs/FlowWeaver_阶段P+2_真实DesktopCleanRoomSmoke.md`
- P+3 第三方许可证增强方案已完成，明确 `third-party-licenses.json` 从 `summary-only` 渐进升级到 `metadata-only` 的数据来源、缺失策略、默认不阻断边界和 P+3a/P+3b/P+3c 后续顺序，完成记录 `docs/FlowWeaver_阶段P+3_第三方许可证增强方案.md`
- P+3a Python 包许可证 metadata 采集已完成，`third-party-licenses.json` 已升级为 `metadata-only` schema，能记录 `License-Expression`、`License`、license classifier、`License-File`、许可证正文路径和包级 warning，且不改变默认归档阻断策略，完成记录 `docs/FlowWeaver_阶段P+3a_Python包许可证Metadata采集.md`
- P+3b .NET NuGet 依赖许可证 metadata 采集已完成，Desktop payload 存在时会从 `project.assets.json` 或发布目录 `.deps.json` 记录 NuGet 包 metadata，并可从本机 `.nuspec` 读取 license expression；缺失 metadata 只写入包级 warning，不复制正文、不联网、不改变阻断策略，完成记录 `docs/FlowWeaver_阶段P+3b_DotNetNuGet许可证Metadata采集.md`
- P+3c 许可证正文复制评估已完成，结论是最小实现只复制 Python 包中已位于发布输入内的许可证正文，NuGet 正文复制继续后置，release strict 阻断策略留到 P+4，完成记录 `docs/FlowWeaver_阶段P+3c_许可证正文复制评估.md`
- P+3c-1 Python 许可证正文复制最小实现已完成，Python 包 `license_files` 会复制到 `licenses/third-party/python/<package>/...` 并写入 `copied_license_files`，NuGet 包保持空数组，默认阻断策略不变，完成记录 `docs/FlowWeaver_阶段P+3c-1_Python许可证正文复制最小实现.md`
- P+3c-2 正文复制冲突与缺失复核已完成，缺失源文件、输入目录外路径和复制目标冲突都会写入 warning，不阻断开发归档，完成记录 `docs/FlowWeaver_阶段P+3c-2_正文复制冲突与缺失复核.md`
- P+4 release strict 模式分析已完成，明确默认开发归档保持 warning 可归档，正式发布门禁通过显式 `--release-strict` 启用，并优先阻断 runtime audit warning、第三方许可证 warning、dirty git、缺失 commit 和缺失 Desktop executable，完成记录 `docs/FlowWeaver_阶段P+4_release_strict模式分析.md`
- P+4a release strict 最小实现已完成，`tools/create_portable_archive.py` 支持显式 `--release-strict`，默认开发归档行为不变，strict 会拒绝 runtime audit warning、第三方许可证 warning、dirty git、缺失 commit 和缺失 Desktop executable，完成记录 `docs/FlowWeaver_阶段P+4a_release_strict最小实现.md`
- P 后续总体验收复核已完成，汇总 P+1 到 P+4a 的便携发布、用户手册、Desktop smoke、第三方许可证增强和 release strict 门禁状态，完成记录 `docs/FlowWeaver_阶段P后续_总体验收复核.md`
- P+5 干净可分发 Python runtime 边界分析已完成，确认当前 repo-local `python312/` 可用于开发和 smoke，但因 dev/test/build、旧 PySide6 GUI 栈、缓存路径和陈旧 `flowweaver==0.2.2` 等杂质，不应直接作为正式 strict runtime，完成记录 `docs/FlowWeaver_阶段P+5_干净可分发PythonRuntime边界分析.md`
- P+5a 独立发布 Python runtime 生成入口已完成，新增 `tools/create_release_python_runtime.py`，`create_portable_layout.py` 可通过 `--python-runtime-dir` 接入独立 runtime，并修正 audit 读取 pip 版本时写入 bytecode cache 的副作用；真实生成 smoke 的 runtime audit 已达到 `checked`，完成记录 `docs/FlowWeaver_阶段P+5a_独立发布PythonRuntime生成入口.md`
- P+5b release runtime 锁定与可复现生成已完成，`tools/create_release_python_runtime.py --locked` 会从 `uv.lock` 的运行依赖闭包生成固定版本和 wheel hash requirements，并用 `--require-hashes --only-binary=:all:` 安装；真实 locked runtime smoke 的 runtime audit 已达到 `checked`，完成记录 `docs/FlowWeaver_阶段P+5b_releaseRuntime锁定与可复现生成.md`
- P+5c release strict 前置复核与 NuGet 文件许可证收口已完成，初次 strict 发现 `git_worktree_dirty` 和 `third_party_license_warning`，已补齐 NuGet `<license type="file">LICENSE</license>` 识别与许可证文件复制，复测后 strict 仅剩 dirty git 阻断，完成记录 `docs/FlowWeaver_阶段P+5c_releaseStrict前置复核与NuGet文件许可证收口.md`
- P+5d 正式 Desktop publish 来源边界收口已完成，`--release-strict` 新增 Desktop payload 完整性检查并拒绝 `Avalonia.Diagnostics.dll` Debug 产物信号；正式顺序改为 layout `--no-desktop-build` 后显式 `tools/publish_desktop.py --output <layout>/Desktop`，复测后 strict 仍仅剩 dirty git 阻断，完成记录 `docs/FlowWeaver_阶段P+5d_正式DesktopPublish来源边界收口.md`
- P+5e dirty git 与正式 strict 最终复核已完成，在临时 clean clone 中按正式顺序生成 locked runtime、portable layout、Release framework-dependent Desktop publish 和 strict archive，manifest 显示 `release_strict=true`、`git_dirty=false`、`runtime_audit_status=checked`，第三方许可证 warning 为空，完成记录 `docs/FlowWeaver_阶段P+5e_dirtyGit与正式Strict最终复核.md`
- P 阶段正式发布前置完成清单已固化，汇总 P+5b-P+5e 完成矩阵、正式验证顺序、strict 门禁、clean clone 验证摘要、明确不支持能力和主工作区未跟踪 UI 文档边界，完成记录 `docs/FlowWeaver_阶段P_正式发布前置完成清单.md`
- 下一步建议不要继续扩大 P 阶段，转入独立 Distribution 方向分析；若要在主工作区直接运行 strict，需要先决策未跟踪 `docs/UI组件MainWindow的后续计划.MD` 如何处理

## 阶段 I 计划

阶段 I 对应第一阶段规范中的“共享表”部分，目标是验证：

```text
工作流A发布两张表
工作流B一次读取完整版本
A发布V2后B当前运行仍固定V1
租约释放后状态正确
```

结合当前代码，建议按以下小步执行。

执行方向总览：

| 小步 | 执行方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| I.0 | 语义和测试边界 | 阶段 I 最小语义、测试夹具和不做事项固定 | 运行时代码实现 |
| I.1 | Store 读写模型 | `SharedPublication` 与成员表的创建、版本分配、查询接口 | 节点执行和主循环接入 |
| I.2 | 原子发布边界 | 多成员发布的校验和同事务落库 | 读取节点、租约清理 |
| I.3 | 固定读取版本 | `InputSnapshot` 记录和 workflow run 关联 | 完整血缘、跨工作流触发 |
| I.4 | 读取租约边界 | `ReadLease` 创建、查询、释放 | 复杂 DependencyPin |
| I.5 | 读取共享表服务 | `LATEST` / `EXACT_VERSION` 解析和一次性完整返回 | 更多版本等待策略 |
| I.6 | 节点骨架 | 发布共享表节点、读取共享表节点的最小执行入口 | UI 配置器 |
| I.7 | 主循环接入 | 共享表节点可在 WorkflowRunProcess 中执行 | EngineHost 复制大表数据 |
| I.8 | 生命周期收口 | workflow 结束时释放读取租约 | 删除已发布真实数据 |
| I.9 | 阶段验收 | A 发布 V1/V2、B 固定 V1、租约释放的端到端测试 | 阶段 J 权限审计 |

建议执行方向：

1. 先做 I.0，写清阶段 I 的最小测试夹具和模型边界，避免把讨论文档中的扩展策略提前实现。
2. 然后做 I.1 到 I.2，先把 `SharedPublication` 的 Store 层和多表原子发布打稳。
3. 再做 I.3 到 I.5，补齐读取固定版本需要的 `InputSnapshot`、`ReadLease` 和读取服务。
4. 最后做 I.6 到 I.9，把能力接到节点和 WorkflowRunProcess，再做生命周期与总体验收。

当前最推荐的第一步是 I.0。如果已经确认不需要再补文档边界，也可以直接进入 I.1，但仍应保持 Store 层小步，不先做节点或主循环接入。

### I.0：边界确认

范围：

- 继续使用现有 `shared_publications`、`shared_publication_members`、`input_snapshots`、`read_leases` 表结构
- 第一阶段只支持 `LATEST` 和 `EXACT_VERSION`
- 不实现 `NEXT_VERSION`、`NEWER_THAN_CURRENT`、`SAME_AS_UPSTREAM`、`FOLLOW_LINEAGE`
- 不实现触发下游工作流
- 不引入跨数据库事务或完整 DependencyPin

验收：

- 文档和测试用例明确阶段 I 的最小语义
- 不改变阶段 H 既有调度、取消和失败策略行为

### I.1：SharedPublication Store 边界

范围：

- 增加共享发布记录的数据模型或返回对象
- 支持按 `share_name` 分配递增 `publication_version`
- 支持原子写入 publication 与 members
- 支持按 id、按 `share_name + version`、按 latest 查询

验收：

- 创建包含两张表的 publication 后，members 要么全部存在，要么全部不存在
- 同一 `share_name` 的版本单调递增

### I.2：发布输入校验与多表原子发布

范围：

- 校验所有成员 `TableRef` 存在
- 固定每个 member 的 `exact_table_version`
- 将发布状态最小落为 `PUBLISHED`
- 写入 `retention_policy_json`

验收：

- 任一成员不存在时不产生半套 publication
- 发布成功后可完整读回两张成员表

### I.3：InputSnapshot Store 边界

范围：

- 记录一次 workflow run 实际读取的 publication 版本和成员选择
- 支持把 `workflow_runs.input_snapshot_id` 关联到当前 run
- snapshot 内容用 JSON 保留可扩展结构

验收：

- workflow B 读取 A@V1 后，snapshot 固定为 A@V1
- 后续 A 发布 V2 不改变 B 已保存的 snapshot

### I.4：ReadLease Store 边界

范围：

- 为读取 workflow run 创建 read lease
- 记录 `publication_id`、`publication_version`、`selected_members`
- 支持释放 lease
- 支持查询 active / released 状态

验收：

- 读取共享表时产生 read lease
- workflow 释放后 lease 状态正确

### I.5：读取共享表服务

范围：

- 支持 `LATEST` 解析为当前 latest publication
- 支持 `EXACT_VERSION` 读取指定版本
- 返回完整 `TableRef` 列表、`InputSnapshot` 和 `ReadLease`

验收：

- B 一次读取完整两张表
- A 发布 V2 后，B 当前运行仍固定 V1
- 不会出现读取一张 V1、一张 V2 的半套版本

### I.6：共享表节点最小骨架

范围：

- 增加发布共享表节点的最小配置和执行入口
- 增加读取共享表节点的最小配置和执行入口
- 节点输出继续通过 `NodeTaskResult.output_refs` 传递引用

验收：

- 发布节点可把输入 TableRef 发布为 SharedPublication
- 读取节点可输出固定版本 TableRef 列表

### I.7：WorkflowRunProcess 接入

范围：

- 将共享表服务接入节点执行上下文
- 保持 WorkflowRunProcess 只管 DAG、状态和任务分发
- 不让 EngineHost 复制大表数据

验收：

- 现有普通节点和表节点测试不回退
- 共享表节点可以在主循环中完成发布和读取

### I.8：生命周期清理

范围：

- workflow 成功、失败、取消、ABORTED 时释放当前 run 的 read lease
- 保留已发布版本，不在第一小步删除真实数据
- 为后续 orphan / retention 清理预留接口

验收：

- workflow 结束后 read lease 可释放
- 异常退出或失联后不会留下 active lease 误判

### I.9：阶段 I 总体验收

范围：

- 工作流 A 生成并发布两张表为 V1
- 工作流 B 读取 V1 并形成 InputSnapshot
- 工作流 A 发布 V2
- 工作流 B 当前运行仍读取 V1
- B 结束后释放 ReadLease

验收命令：

```powershell
.\python312\python.exe -m ruff check src tests migrations
.\python312\python.exe -m mypy
.\python312\python.exe -m pytest -q
```

## 阶段 J 计划

阶段 J 对应第一阶段规范中的“权限与审计”部分，目标是验证：

```text
无权限节点无法写入目标表
审计记录包含节点、表、字段和影响行数
权限检查始终开启
审计等级默认 STANDARD
```

J.0 只确认语义和接口范围，不落 Store/API/节点执行检查。

### J.0：权限审计边界清单

范围：

- 第一阶段只管理工作流内部数据权限
- 权限检查始终开启，不允许为了性能完全关闭
- 审计等级可以切换，默认 `STANDARD`
- “关闭审计”后续只允许降为最低运行记录，不等于关闭权限检查
- 权限层判断节点是否允许读取、写入、追加、覆盖、清空、结构修改、输出发布和共享表读取
- 审计层记录允许/拒绝、节点、表、字段、写入模式、影响行数和 ChangeSet 摘要
- 节点或插件负责具体资源操作，平台负责权限声明、授权结果、标准数据引用和审计记录

已有基础：

- `EngineConfig.audit_level` 已有默认 `STANDARD`
- `audit_events` 表已存在
- `NodeTask.permission_handle_id` 字段已存在
- `PermissionRequestModel`、`PermissionGrantModel` 和 `AuditEventModel` 已具备最小协议边界
- `RuntimeStore` 已具备权限句柄创建、查询、撤销和审计事件追加、查询能力
- 内置表节点和共享表节点已具备配置到 `PermissionRequestModel` 的解析入口
- WorkflowRunProcess 已在创建支持权限声明的内置 `NodeTask` 前签发并绑定 `permission_handle_id`
- 内置表节点和共享表发布节点已在发布前校验 `permission_handle_id`
- 内置表节点和共享表发布节点已记录 `STANDARD` 权限检查审计事件
- `TableLeaseManager` 已有表级 READ / WRITE 租约与轻量审计记录
- `RuntimeEvent` 与 `NodeTaskResult` 已能承载运行状态和节点失败结果

J.0 暂不进入：

- 不新增 `permissions/` 模块
- 不新增或修改数据库迁移
- 不改 Store 写入权限强制逻辑
- 不改 API 权限端点
- 不改 NodeTask 分发时的权限句柄签发
- 不改内置节点执行器的权限校验
- 不实现 UI 权限审批或审计页面
- 不为文件、Web、Office、串口、屏幕等外部系统建立统一强制规则
- 不实现 `FULL` / `DEBUG` 级字段差分或行级差分

建议后续小步：

| 小步 | 执行方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| J.1 | 协议模型 | PermissionRequest / PermissionGrant / AuditEvent 最小模型 | Store 强制拦截 |
| J.2 | Store 边界 | 权限句柄与审计事件 CRUD | API 和节点执行接入 |
| J.3 | 节点权限声明 | 节点配置解析出本次运行需要的内部数据权限 | 外部系统统一权限 |
| J.4 | 主循环接入 | 创建 NodeTask 前校验并绑定 permission_handle_id | UI 审批 |
| J.5 | 节点执行检查 | 内置表节点写入前校验权限句柄 | 所有插件沙盒 |
| J.6 | STANDARD 审计 | 写入节点审计节点、表、字段、影响行数和摘要 | FULL 行级差分 |
| J.7 | 阶段验收 | 无权限写入拒绝和审计记录完整性测试 | 权限页面 |

J.7 验收结果：

- 支持权限声明的内置 `NodeTask` 已在主循环创建前绑定 `permission_handle_id`
- 内置表节点和共享表发布节点在发布前校验权限句柄
- 缺少权限句柄时会拒绝发布并记录 `denied` 审计事件
- 授权通过时会记录 `granted` 的 `PERMISSION_CHECK` 审计事件
- 主循环端到端测试已覆盖权限句柄、授权记录和 `STANDARD` 审计事件
- 第一阶段仍不包含 UI 审批、权限页面、FULL 行级差分和所有插件沙盒

K.1 验收结果：

- `Avalonia_UI/` 已纳入仓库，保持 Avalonia、.NET 10.0、C# 和 MVVM 骨架
- 主窗口已从模板问候语收口为 EngineHost 地址、token、连接状态和错误提示面板
- 已补最小 health 检查服务，仅调用 `GET /api/v1/health`
- 已补 C# 单元测试覆盖 health URI 拼接、健康响应和 HTTP 失败
- 已移除 Python 依赖中的旧 PySide6 和 pytest-qt 路线
- UI 不直接读取 SQLite，不嵌入或启动 Python EngineHost

K.2 验收结果：

- 已补 `EngineHostApiClient`，封装 REST 统一响应 envelope、错误模型、Bearer token 注入和超时入口
- 已补 Workflow、Run、NodeRun、RuntimeEvent、TableRef、SharedPublication、AuditEvent 的最小 DTO
- 已补 RuntimeEvent WebSocket 客户端边界，固定 `/ws/v1/events?token=...`
- health 检查已改为复用 API Client，不在 ViewModel 或控件里写 HTTP 细节
- 已补 C# 单元测试覆盖鉴权失败、连接失败、事件过滤查询、错误 envelope 和 RuntimeEvent 解析
- 暂未实现工作流列表 UI、运行按钮和事件视图

K.3 验收结果：

- 主窗口已接入工作流列表、刷新按钮和运行按钮
- UI通过 `EngineHostApiClient` 访问 EngineHost，不直接创建本地运行状态
- 启动运行后仅展示本次返回的 `workflow_run_id` 和状态
- 已补 ViewModel 测试覆盖刷新列表、保留选择、刷新失败、启动运行和无选择时禁用运行
- 暂未实现 Run列表、停止按钮、NodeRun状态、事件流和重连

K.4 验收结果：

- 主窗口已接入 Run 列表、Cancel 按钮和 NodeRun 列表
- Run 列表通过 `GET /api/v1/runs` 按已选 workflow 过滤刷新
- Cancel 通过 `POST /api/v1/runs/{run_id}/cancel` 发起取消请求，随后刷新 Run 列表并保留选中项
- NodeRun 通过 `GET /api/v1/runs/{run_id}/nodes` 展示 `status`、`progress` 和 `current_stage`
- 已补 ViewModel 测试覆盖 Run 刷新、取消、无选择禁用取消、NodeRun 状态刷新
- 已补 API Client 测试覆盖 Run 查询、NodeRun 查询和 cancel 路径
- 暂未实现 WebSocket 事件合并、断线提示和重连恢复

K.5 验收结果：

- RuntimeEvent WebSocket 客户端已抽象为可测试接口，正式实现仍使用 C# `ClientWebSocket`
- 主窗口已增加事件流 Start/Stop 控制和连接/断线/最近事件提示
- `MainWindowViewModel` 已接入 RuntimeEvent 读取循环，收到事件后记录最近事件并通过 REST 恢复 Run/NodeRun 当前状态
- WebSocket 正常关闭或异常后会提示断线，执行 REST 补状态，然后按最小重连延迟重新连接
- 缺少 token 时启动事件流会在 UI 层明确拒绝，不进入重连循环
- 已补 C# 测试覆盖缺 token 拒绝、收到 RuntimeEvent 后刷新状态、断线后重连并恢复状态
- 暂未实现 RuntimeEvent/AuditEvent 可过滤只读日志视图、长期离线缓存和事件详情展开

K.6 验收结果：

- 主窗口已拆为 `Execution` 和 `Logs` 页签，运行操作与日志查询互不挤占
- `Logs` 页签已接入 RuntimeEvent REST 只读视图，支持 workflow_run_id、node_run_id、event_type、after_sequence_number 和 limit 过滤
- `Logs` 页签已接入 AuditEvent REST 只读视图，支持 workflow_run_id、node_run_id 和 event_type 过滤
- RuntimeEvent limit 限制为 1 到 1000，非法显式输入会在 UI 层拒绝，不发送无效请求
- 已补 C# 测试覆盖 RuntimeEvent 过滤查询、非法 limit 拒绝、AuditEvent 过滤查询和 audit API 路径
- 暂未实现权限审批页面、事件详情展开、长期离线缓存和完整大表查看

K.7 验收结果：

- 主窗口已增加 `Data` 页签，和 `Execution`、`Logs` 分离
- `Data` 页签可按当前 selected run 查询 TableRef 摘要，展示 logical_table_id、table_ref_id、node_run_id、version、lifecycle_status 和 capabilities
- `Data` 页签可查询 SharedPublication 列表，支持 share_name 和 limit
- `Data` 页签可按指定 share_name 查询 SharedPublication 版本列表，并展示 members 的 export_name 与 exact_table_version 摘要
- SharedPublication limit 和版本 limit 均在 UI 层按 1 到 1000 校验，非法显式输入直接拒绝
- 已补 C# 测试覆盖 TableRef 摘要查询、SharedPublication 过滤查询、非法 limit 拒绝、版本 members 摘要和三条 API 路径
- 暂未实现完整大表内容加载、表格编辑、ReadLease 明细页和跨 workflow 触发能力

K.8 验收结果：

- K.0a 到 K.7 已完成并形成阶段 K 最小桌面 UI 基线
- Avalonia UI 仅通过 HTTP + WebSocket 访问 Python FastAPI EngineHost，不直接访问 SQLite，不绕过后端正式边界
- UI 已具备 health、workflow 列表、启动 run、Run/NodeRun 状态、取消、RuntimeEvent WebSocket、断线重连 REST 恢复、日志审计只读查询和数据摘要视图
- K.0b 默认正式路径烟雾测试通过
- `dotnet build Avalonia_UI/Avalonia_UI.sln` 通过
- `dotnet test Avalonia_UI.Tests/Avalonia_UI.Tests.csproj --no-build` 通过，42 个 C# 测试通过
- `ruff`、`mypy` 和全量 `pytest -q` 通过
- 阶段 K 仍不包含工作流画布编辑、完整大表内容加载、表格编辑、权限审批页面、长期离线缓存、安装包发布和跨 workflow 触发能力

阶段 K 后已进入并完成阶段 L 运行入口、连接配置和正式路径 smoke 收口。当前建议下一步是先做下一阶段边界分析，再决定是否进入连接体验稳定化、工作流定义与节点配置入口或打包发布前置清单。

## 环境

目标环境：

- Windows 10/11
- Python 3.12
- uv
- .NET 10.0 SDK
- Avalonia UI项目位于 `Avalonia_UI/`

同步依赖：

```powershell
.\python312\python.exe -m uv sync --extra dev
```

如果本机还没有 `uv`，可以先在当前 Python 3.12 环境中安装：

```powershell
.\python312\python.exe -m pip install uv
```

运行测试：

```powershell
.\python312\python.exe -m pytest
```

静态检查：

```powershell
.\python312\python.exe -m ruff check src tests migrations
.\python312\python.exe -m mypy
```

对指定 SQLite 元数据库执行迁移：

```powershell
.\python312\python.exe -m alembic -c alembic.ini -x database_url=sqlite:///runtime/metadata/flowweaver.db upgrade head
```

启动本机 EngineHost API：

```powershell
.\python312\python.exe -m uvicorn --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

默认启动会创建 `runtime/` 目录、执行 Alembic 迁移，并在 `runtime/config/local_api_token` 生成或复用本地 API token。
`/api/v1/health` 不需要 token：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/v1/health
```

除 `/api/v1/health` 外，HTTP API 需要携带：

```powershell
Authorization: Bearer <local_api_token>
```

PowerShell 中可这样读取本机 token 并做最小鉴权检查：

```powershell
$token = (Get-Content -Raw runtime\config\local_api_token).Trim()
$headers = @{ Authorization = "Bearer $token" }
Invoke-RestMethod -Headers $headers http://127.0.0.1:8000/api/v1/workflows
```

构建桌面端：

```powershell
dotnet build Avalonia_UI/Avalonia_UI.sln
```

启动桌面端：

```powershell
dotnet run --project Avalonia_UI/Avalonia_UI.csproj
```

桌面端启动后会自动读取上次成功连接的 EngineHost `Base URL` 和本机 token，并尝试连接；无法连接时会在右上角状态区显示失败。首次使用或 token 轮换后，在主窗口输入当前 Base URL 和本机 token，点击 `Check` 保存并更新连接配置；业务 API 和 RuntimeEvent WebSocket 仍需要 token。
