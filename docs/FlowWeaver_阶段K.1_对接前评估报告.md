# FlowWeaver 阶段 K.1 对接前评估报告

> 文档状态：K.1 实施前的只读评估（不改任何代码）
> 评估日期：2026-06-29
> 评估范围：Avalonia_UI 工程骨架现状、Python 主程序/engine/API 的收口与潜在漏洞、API/WebSocket 契约一致性、主程序解耦度
> 结论一句话：**后端对 K.1 不构成阻塞，可以进入 K.1；真正的契约风险集中在 K.2（C# Client）之前需要先拍板的几项，本报告逐条列出。**

---

## 0. 验证方法与可信度声明

本报告所有结论均基于对源码的逐文件精读 + 实际运行验证，并对一次自动化初审的结论做了人工复核与勘误。

实测环境与方法：

- 评估在 Linux 沙箱内进行；系统默认 Python 为 3.10，会导致 `datetime.UTC` 导入失败。已用 `uv` 拉起项目要求的 **Python 3.12.13** 重新建立 `.venv` 并在其下运行全部检查，与目标环境一致。
- `dotnet` SDK 在本 Linux 沙箱不可用，且 `Avalonia_UI` 为 `WinExe`（Windows 目标），因此 **`dotnet build` 无法在本环境实测**，相关结论基于对工程文件的静态核对，需在 Windows/.NET 10 环境最终确认。
- **重要提示（针对自动化结论的勘误）**：评估过程中一个自动化代码审查初稿把若干"严重问题"判断错了（详见 §5.0），并擅自在仓库根目录生成了两个未经核实的报告文件（`FlowWeaver_后端健康度评估.md`、`FlowWeaver_验收执行报告_20260629.md`）。这两个文件包含"预期结果/静态推测代替实际运行"的不可靠内容，已被删除。本报告中的每条后端问题均经我亲自读源码核对，错误判断已剔除。

---

## 1. 执行摘要

| 维度 | 结论 |
| --- | --- |
| 进入 K.1 是否就绪 | ✅ 就绪。K.1 只要求工程骨架 + 连接配置 + health，后端 `GET /api/v1/health` 已存在且免鉴权，连接契约清晰。 |
| Avalonia_UI 现状 | ⚠️ 标准 Avalonia MVVM 模板空壳。`net10.0`、MVVM、CommunityToolkit 已就位；连接配置、token、health 客户端、HTTP/WS 抽象**全部缺失**（这正是 K.1 的工作量）。 |
| 后端健康度 | ✅ 良好。ruff 全过；mypy 在 3.12 下仅 1 个 Windows 平台误报；单测 55 全过、集成测试除 1 个并发计时型脆弱用例外全过。 |
| 后端是否有阻塞性漏洞 | ❌ 无阻塞性漏洞。存在若干**中等收口缺口**（无日志基础设施、个别异常静默吞没、事件路由的连接期副作用），不影响 K.1，但建议在 K 阶段一并收口。 |
| API/WS 契约一致性 | ⚠️ 源码契约自洽且稳定，但**与 `00_规范` §5/§6 已有多处分歧**，且 `api_models.py` 里的一整套 DTO 是**死代码**（实际序列化走手写 `_to_jsonable`）。这是 K.2 之前最需要先定的事。 |
| 主程序解耦 | ✅ 目标基本达成。EngineHost 不执行节点；编排层 `controller.py` 为纯函数；执行器/执行池/清理回调均为可注入接缝。 |

Top 5 关注项（按对 UI 对接的影响排序）：

1. **契约真相在 `_to_jsonable`，不在 DTO 类**——C# DTO 必须照实际下发结构对齐，且 OpenAPI 因 `data: Any` 无法描述数据形状（§4.4）。
2. **实际端点与 `00_规范` 分歧**（`/runs` vs `/run`、`/shared-publications` vs `/publications`、`/audit-events` vs `/audit/events`、`/data/...` 未实现等）——以源码为准，规范文档需同步（§4.2、§4.3）。
3. **WebSocket 鉴权用查询参数 `?token=`，REST 用 `Authorization: Bearer`**——双鉴权方式，K.2 客户端要分别处理；且每次 WS 连接会广播并持久化一条 `ENGINE_READY`（§4.4、§5.1）。
4. **无任何 Python logging 基础设施**（全 `src` 0 处），`supervisor.maintenance_loop` 用 `except Exception: pass` 静默吞没——后端"卡住"类问题难以诊断（§5.1）。
5. **`pyproject.toml` 仍把 PySide6 列为主依赖**（叠加 `pytest-qt`），是已废弃 UI 路线的死重量，且在非 Windows/headless 下会让测试套件直接崩溃——K.1 应收口（§5.2）。

---

## 2. 实测验证结果

| 检查项 | 命令（Python 3.12 / `.venv`） | 结果 |
| --- | --- | --- |
| ruff | `ruff check src tests migrations` | ✅ **All checks passed**（0） |
| mypy | `python -m mypy`（配置 `packages=["flowweaver"]`, py312） | ⚠️ **Found 1 error**（67 文件）：`common/instance_lock.py:71 Module has no attribute "windll"` |
| pytest（单元） | `pytest tests/unit` | ✅ **55 passed** |
| pytest（集成） | `pytest tests/integration`（分批） | ✅ 除 1 个脆弱用例外全过（批次：30 + 88 + supervisor/wf-main） |
| pytest（合计） | 收集 **215** 用例 | ✅ **214 通过 / 1 失败（环境计时型脆弱，非逻辑缺陷，见下）** |
| Avalonia 构建 | `dotnet build Avalonia_UI.sln` | ⛔ 本 Linux 环境无 dotnet，未能实测；需 Windows/.NET10 确认 |

关于 mypy 的 1 个错误：`instance_lock.py:71` 引用 `ctypes.windll`，这是 **Windows 专用 API**，在 Linux 上必然报"无此属性"。项目目标平台是 Windows（CI 也在 Windows），在目标平台此处可通过；可视为**平台误报**，实质 mypy 在目标平台是干净的。

关于唯一失败用例 `test_workflow_process_main.py::test_workflow_process_with_threaded_pool_applies_parallel_ready_out_of_order`：

- 该用例用一个假的 `sleep_func` 驱动主循环节拍，并通过后台工作线程的 `started_event().wait()` / `release()` 协调"乱序完成"。
- 失败点在多次运行间**漂移**（先后落在第 2026 行、第 2055 行），这是**计时型脆弱用例**的典型特征：第 2026 行的断言 `executor.executed_nodes == ["source_a"]` **没有 wait/poll**，在本慢速沙箱里后台线程尚未跑完即被断言，于是出现 `assert [] == ['source_a']`。
- 该用例属于**可选的 `threaded` 并发执行池**路径，而**默认执行模式是 `immediate`（顺序，`max_concurrent_node_tasks=1`）**（见 `common/config.py:12-15`），即 UI 默认路径不会触发它。
- 判定：**非产品逻辑缺陷，属测试健壮性问题**。建议在该断言前加入轮询等待使其确定化；并按项目 K.0a 基线在 Windows 目标上复跑确认全绿。

---

## 3. Avalonia_UI 现状与 K.1 就绪度

### 3.1 工程清单（现状＝标准 Avalonia MVVM 模板空壳）

`Avalonia_UI/` 当前文件：`App.axaml(.cs)`、`Program.cs`、`ViewLocator.cs`、`Views/MainWindow.axaml(.cs)`、`ViewModels/MainWindowViewModel.cs`、`ViewModels/ViewModelBase.cs`、`app.manifest`、`Assets/avalonia-logo.ico`、空的 `Models/` 目录。`MainWindowViewModel` 仅有一个 `Greeting = "Welcome to Avalonia!"`，`MainWindow` 仅居中显示该文本——即官方模板未改动。

`Avalonia_UI.csproj` 关键项：

- `TargetFramework = net10.0` ✅（符合 K.1）
- `OutputType = WinExe`、`Nullable = enable`、`AvaloniaUseCompiledBindingsByDefault = true`
- 依赖：`Avalonia 11.3.12`（含 Desktop/Themes.Fluent/Fonts.Inter/Diagnostics）、`CommunityToolkit.Mvvm 8.2.1` ✅（MVVM 就位）

### 3.2 K.1 要点对照表

| K.1 要点 | 现状 | 缺口 |
| --- | --- | --- |
| Avalonia 工程骨架 | ✅ 存在且为标准模板 | 仅需复核启动链路 |
| .NET 10.0 | ✅ `net10.0` | 需在 Windows 实测 `dotnet build` 通过 |
| C# + MVVM | ✅ CommunityToolkit.Mvvm + ViewLocator | — |
| 连接配置（EngineHost 地址 / token / 连接状态） | ❌ 完全没有 | 新建配置模型与状态（见 3.3） |
| health 检查入口 | ❌ 没有 | 新建一个最小 health 探测（命中 `GET /api/v1/health`） |
| 连接失败有明确错误 | ❌ 没有 | health/连接探测需返回可展示的错误 |
| 不直连 SQLite / 不进程内调用 Python | ✅ 天然满足（纯客户端壳） | 保持边界 |

### 3.3 K.1 缺口与待建清单（建议）

1. **连接配置模型**：`BaseUrl`（默认 `http://127.0.0.1:8000`）、`Token`、`ConnectionStatus`（Disconnected/Connecting/Connected/Error）。建议放在 `Models/`（目前为空）。
2. **Health 探测入口**：最小 `HttpClient` 调 `GET /api/v1/health`（免鉴权），把结果映射到连接状态与错误文案。注意这是 K.1 唯一需要的网络能力，完整 HTTP/WS Client 封装属于 K.2，不要在 K.1 提前展开。
3. **主窗口最小化改造**：把 `Greeting` 模板替换为"连接配置 + 连接按钮 + 状态/错误显示"的最小界面。
4. **`pyproject.toml` 的 PySide6 收口**：K 计划 §1 已点名"旧 PySide6 依赖是否移除留到 K.1 单独收口"。建议本步处理（详见 §5.2）。
5. **构建验收**：在 Windows/.NET 10 上跑通 `dotnet build Avalonia_UI/Avalonia_UI.sln`（K.1 验收硬指标，本环境无法替你完成）。

### 3.4 K.1 需要先拍板的设计决策点

- **Token 从哪来**：后端首启会把 token 写到 `runtime/config/local_api_token`（明文文件，非 SQLite）。UI 获取 token 有两条路：(a) 读取本机该 token 文件；(b) 用户手动粘贴。读 token 文件不违反"不直连 SQLite"的边界（它不是数据库），但要明确这是否在 K 阶段允许。建议 K.1 先支持手动填入 + 可选读取本地 token 文件。
- **谁来启动 EngineHost**：仓库没有内置"启动引擎"的入口，EngineHost 通过 `uvicorn ... flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000` 独立启动（README 已记录）。UI 是纯客户端、不拉起 Python 进程，因此 K.1 要假设 EngineHost 已在运行，并在连不上时给出明确提示。
- **Origin 策略**：后端 `allowed_origins` 默认 `{"http://127.0.0.1"}`，但 `check_origin` 对"无 Origin 头"直接放行。Avalonia 的 `HttpClient`/`ClientWebSocket` 作为原生客户端通常不发 Origin，因此默认可通过；K.2 不要主动设置不在白名单内的 Origin。

---

## 4. API / WebSocket 契约一致性（K.2–K.7 的对接真相）

### 4.1 已确认正确、稳定的契约基线

- **统一响应 envelope**（`responses.py`）：成功 `{ok:true, data, error:null, request_id}`；失败 `{ok:false, data:null, error:{error_code,message,details,retryable}, request_id}`。所有路由一致。
- **鉴权**：除 `GET /api/v1/health` 外，REST 全部需 `Authorization: Bearer <token>`（`dependencies.require_api_token`）+ origin 校验；失败统一返回 401 `UNAUTHORIZED` envelope。
- **health**：`GET /api/v1/health` 免鉴权，返回 `{ok:true, data:{status:"ok"}, ...}`——K.1 直接用它。
- **校验失败**：`RequestValidationError` 统一转 422 `VALIDATION_ERROR` envelope。
- **NodeRun/WorkflowRun/RuntimeEvent 字段齐全**：`NodeRun` 含 `progress`、`current_stage`、`status`、`executor_id`、`attempt`、`last_heartbeat`（K.4 需要的都在）；事件 REST 与 WS 都带 `sequence_number`（K.5 断线重连可据此排序/去重）。

### 4.2 实际端点全集（以源码为准）

| 方法 | 路径 | 鉴权 | 备注 |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | 否 | K.1 健康探测 |
| GET | `/api/v1/workflows` | 是 | 列表 |
| POST | `/api/v1/workflows` | 是 | 201；先 `validate_workflow_definition` |
| POST | `/api/v1/workflows/validate` | 是 | 校验草稿 |
| GET | `/api/v1/workflows/{workflow_id}` | 是 | |
| PUT | `/api/v1/workflows/{workflow_id}` | 是 | |
| DELETE | `/api/v1/workflows/{workflow_id}` | 是 | |
| POST | `/api/v1/workflows/{workflow_id}/validate` | 是 | 校验已存草稿 |
| POST | **`/api/v1/workflows/{workflow_id}/runs`** | 是 | **201，启动运行**（规范写的是 `/run` 单数） |
| GET | `/api/v1/workflows/{workflow_id}/revisions` | 是 | |
| GET | `/api/v1/workflows/{workflow_id}/revisions/{revision_id}` | 是 | |
| GET | `/api/v1/runs` | 是 | 查询参数 `workflow_id`、`status`（可重复） |
| GET | `/api/v1/runs/{workflow_run_id}` | 是 | |
| POST | `/api/v1/runs/{workflow_run_id}/cancel` | 是 | 返回 **WorkflowProcess** 快照（非 run） |
| GET | `/api/v1/runs/{workflow_run_id}/nodes` | 是 | NodeRun 列表 |
| GET | `/api/v1/runs/{workflow_run_id}/table-refs` | 是 | 该 run 的 TableRef（**完整对象**，非"摘要"） |
| GET | `/api/v1/events` | 是 | `after_sequence_number`、`workflow_run_id`、`node_run_id`、`event_type`、`limit`(1–1000，默认100) |
| GET | `/api/v1/audit-events` | 是 | `workflow_run_id`、`node_run_id`、`event_type`（无 time/limit/offset，无 `/{id}`） |
| GET | `/api/v1/shared-publications` | 是 | `share_name`、`limit` |
| GET | `/api/v1/shared-publications/{share_name}/versions` | 是 | `limit`；实现与上一条共用，按 `share_name` 返回各版本行 |
| WS | `/ws/v1/events?token=<token>` | 查询参数 token | 连接即发 `ENGINE_READY`，随后流式推送事件；origin 校验；失败 close 1008 |

### 4.3 与 `00_第一阶段技术接口与验收规范` §5/§6 的分歧点

> 处理原则：以**源码为准**对接 UI，同时建议把规范文档/`api_models` 同步，避免后续 K.2 照规范写出对不上的客户端。K.0c 已对部分接口做过改名/补齐，分歧多为有意演进，但文档未完全回灌。

| 规范（§5/§6） | 实际实现 | 影响 |
| --- | --- | --- |
| `POST /workflows/{id}/run`（单数） | `/workflows/{id}/runs`（复数） | K.3 启动按钮路径需用复数 |
| `GET /runs/{id}/events` | 无此子资源；改用 `/events?workflow_run_id=` | K.4/K.6 取某 run 事件走 `/events` 过滤 |
| `/api/v1/data/{table_ref_id}`（schema/rows/summary） | **未实现** | 与 K 计划一致（K.7 不加载完整表数据）；UI 仅有 `/runs/{id}/table-refs` 元数据 |
| `/api/v1/publications`、`/{id}/versions`（按 publication_id） | `/api/v1/shared-publications`、`/{share_name}/versions`（按 share_name） | K.7 命名与键不同 |
| `/api/v1/audit/events`、`/{event_id}`，含 time/limit/offset | `/api/v1/audit-events`，仅三个过滤，无分页/时间窗 | K.6 审计视图过滤能力受限（见 §5.2） |
| 错误模型含 `origin`、`trace_id`（§3.4） | `APIErrorModel` 仅 `error_code/message/details/retryable` | K.2 错误模型按 4 字段建（与 §5 示例一致，§3.4 的 6 字段未落地） |
| WS 事件未列 `sequence_number`（§6） | 实际带 `sequence_number` | 对 UI 有利：重连去重/排序更可靠 |

### 4.4 契约风险（K.2 之前最该先定的事）

1. **`api_models.py` 的 9 个 View DTO 是死代码**：`WorkflowRunView/NodeRunView/TableRefSummaryView/PublicationSummaryView/RuntimeEventView/...` 在全 `src` 中**仅有定义、零处使用**。路由把 ORM 对象直接交给 `responses._to_jsonable` 手写序列化。后果：
   - **真实下发结构由 `_to_jsonable` 决定**，C# DTO 必须照它对齐，而不是照这些 View 类（两者已存在差异，例如 `table-refs` 实际下发完整 TableRef，而 `TableRefSummaryView` 只有 6 个字段）。
   - 路由 `response_model=APIResponseModel` 且 `data: Any`，**OpenAPI/Swagger 无法描述 data 形状**，K.2 不能靠自动生成客户端 DTO。
   - View 类与 `_to_jsonable` 易**长期漂移**。建议：要么让路由真正使用强类型 DTO，要么删掉死 DTO 并把 `_to_jsonable` 的输出固化为契约文档（推荐后者成本更低）。
2. **启动失败的语义**：`POST /workflows/{id}/runs` 若 `supervisor.start_workflow_process` 抛错，会把 run 置 `FAILED` 并仍以 **HTTP 201 + `ok:true` + data=FAILED 的 run** 返回（`routes_workflows.py:112-127`）。K.3 不能只看 HTTP 码，必须读 `run.status`。
3. **取消是协作式、最终一致**：`cancel` 返回的是 WorkflowProcess 快照（带 `cancel_requested_at`），run 真正进入 `CANCELLED` 是异步发生的。K.4 取消后应靠轮询 REST + WS 事件收敛状态，而非假定立即终态。
4. **WS 连接副作用**：每次有客户端连 `/ws/v1/events`，`event_router.publish(ENGINE_READY)` 会**广播给所有在线订阅者并持久化一条事件**（`websocket_events.py:23` + `event_router.py:67-78`）。频繁重连会产生事件噪声与运行事件表增长；K.5 重连策略宜加退避，UI 对 `ENGINE_READY` 做幂等处理。
5. **WS 无重放**：符合规范"不要求事件重放"。断线期间的事件需 K.5 用 `GET /events?after_sequence_number=` 回补。

---

## 5. 后端漏洞与未收口项（已逐条核对）

### 5.0 对自动化初审的勘误（这些"严重问题"经核实不成立）

| 初审结论 | 核实结果 |
| --- | --- |
| supervisor 启动子进程"文件重复 close / FD 泄漏"（severe） | ❌ 不成立。`supervisor.py:82-112` 在 `Popen` 后关闭**父进程侧**句柄是正确做法（子进程已继承自己的 fd），`finally` 还用 `if not closed` 守护，且 Python `file.close()` 幂等。无泄漏。 |
| `_connect()` "不支持上下文管理器 / 连接池耗尽"（severe） | ❌ 前提错误。`sqlite3.Connection` **支持** `with`。真实问题仅是连接靠 GC 回收、未显式 `close()`（轻微，见 5.2）。 |
| `publish_staging` "无 ROLLBACK / 数据丢失"（severe） | ❌ 不成立。`with self._connect() as connection:` 在异常时**自动 rollback**，DROP+CREATE+INSERT 在同一事务内，具备原子性（`runtime_table_provider.py:264-275`）。 |
| `CONTINUE_INDEPENDENT / SKIP_DEPENDENTS` "未实现"（解耦评分） | ❌ 与设计相悖。K 计划 §3.4 与 README 明确：`CONTINUE_INDEPENDENT` 已实现（终态 `FAILED` + `completion_reason=PARTIAL_FAILURE`），`SKIP_DEPENDENTS` 为**有意保留不可用、显式配置会被拒绝**。 |

### 5.1 中等（建议在 K 阶段一并收口，不阻塞 K.1）

1. **完全没有 logging 基础设施**：全 `src` 0 处 `logging`/`getLogger`。与规范 §1.6（Python logging + QueueHandler/QueueListener + JSON Lines + RotatingFileHandler）不符。当前可观测性只剩子进程 stdout/stderr 重定向文件 + `traceback.print_exc()`。影响：后端"卡住/无声失败"难诊断。
2. **`Supervisor.maintenance_loop` 静默吞异常**：`supervisor.py:170-171` `except Exception: pass`。维护循环里 drain/sweep/标记失联 的任何异常都被无声丢弃且无日志。这是上一条缺失日志后果最重的一处——维护线程出问题时，UI 看到的是"进程不动"而非具体原因。建议至少记录日志。
3. **`workflow_process/main.py` 多处 `except Exception: pass`**：`main.py:1049、1129、1199、1214、1216`（多为关闭/清理路径）。清理期吞异常常见，但叠加"无日志"会降低可诊断性，建议补日志。
4. **`EventRouter` 订阅队列无上界 + 连接期副作用**：`asyncio.Queue()` 无 `maxsize`，慢消费者会无界堆积（本地单用户风险低）；叠加 §4.4(4) 的每连接广播+持久化 `ENGINE_READY`。建议给队列设上界并把"连接确认"改为只发给本连接、不全局持久化。
5. **审计/共享发布只读接口的过滤能力偏弱**：`audit-events` 无 time/limit/offset、无 `/{event_id}`；`shared-publications/{share_name}/versions` 与列表接口共用实现。K.6/K.7 若需时间窗或分页，需后端补齐。

### 5.2 轻微 / 技术债

1. **`pyproject.toml` 把 `PySide6>=6.7.0` 列为主依赖**，dev 还有 `pytest-qt`。这是已废弃 UI 路线（规范 §1.5 旧定 PySide6，K 计划改 Avalonia）的死重量：体积大，且在本 headless/Linux 环境下 `pytest-qt` 因加载不到 `libQt6Core.so.6` 直接让整个测试套件 INTERNALERROR（我是卸载 `pytest-qt` 后才跑通的）。建议 K.1 移除或挪到可选 `[gui]` 分组。
2. **`instance_lock.py:71` 的 `ctypes.windll`**：mypy 在非 Windows 报 `attr-defined`。Windows 目标上正常。可加平台守卫或 `# type: ignore[attr-defined]` 注释消除噪声。
3. **`protocols/table_ref.py:50` 的 `# type: ignore`**：在 3.10 下被 `warn_unused_ignores` 判为冗余；3.12 下未复现。建议在目标 3.12 复核后决定是否保留。
4. **`runtime_table_provider._connect` 每次操作新建连接且依赖 GC 关闭**：CPython 下函数返回即回收，实际不漏；但建议用 `contextlib.closing` 显式关闭，避免依赖引用计数。
5. **并发执行池的脆弱测试**：见 §2，建议确定化。

### 5.3 明确"未发现问题"（健康项）

- 无 `TODO/FIXME/NotImplementedError/HACK` 占位（`...` 全部是 Protocol 桩，非未完成实现）。
- 关键数据路径的异常处理是**正确模式**：`runtime_store.py:864`、`table_lease_manager.py:301` 为 `except: rollback; raise`；`executor_pool.py:135`、`node_executor/process.py:172`、`routes_workflows.py:114` 为"异常转失败结果/错误 envelope"。
- 状态机收口良好：`controller.py` 用 `expected_state_version` + `allowed_source_statuses` 做乐观并发与状态守卫；迟到/旧 attempt/旧 generation/executor 不匹配的结果会被拒绝。
- 子进程显式注入 `src` 路径（`supervisor._child_environment` + `subprocess_command`），避免嵌入式 Python 误用旧安装包（K.0b 已修）。

---

## 6. 主程序解耦评估（"主程序只做管理、功能由节点实现"）

| 维度 | 评价 | 证据 |
| --- | --- | --- |
| EngineHost 不执行节点 | ✅ 达成 | EngineHost 只持有控制面（API + ServiceContainer + Supervisor）；节点执行在 WorkflowRunProcess / NodeExecutorProcess（`bootstrap.py`、进程所有权图）。 |
| 编排层是否纯管理 | ✅ 良好 | `controller.py` 全为纯函数，仅围绕 `store`/`dag`/`event_sink` 做状态推进，无业务逻辑内嵌。 |
| 依赖注入接缝 | ✅ 存在 | `run_workflow_process` 接受 `executor_factory`、`execution_pool`、`cleanup_staging_for_node` 等可注入参数（`main.py:222-228`）；`_DefaultWorkflowProcessExecutorOwner` 只是默认组合根。 |
| 执行器选择 | ⚠️ 默认组合根硬编码具体类 | `executor_for_task` 按节点类型分流到 `BuiltinTableNodeExecutor`/`BuiltinSharedTableNodeExecutor`/`SubprocessNodeExecutorIpcClient`（`main.py:141-167`）。属"组合根写死默认实现"，可被注入覆盖，可接受。 |
| 故障隔离边界 | ✅ 关键边界成立 | 子进程崩溃由 Supervisor `sweep_exited_children` → `abort_workflow_run_for_process` 落库 ABORTED；EngineHost 不受单 run 崩溃影响。 |
| 一个设计取舍需知晓 | ℹ️ | 内置**表节点/共享表节点在 WorkflowRunProcess 进程内执行**（非独立 executor 子进程），是 K 计划 §3.6 的有意第一阶段决策：这类节点崩溃会拖垮该 run 的 WorkflowRunProcess，但**不影响 EngineHost 与其它 run**——真正的隔离边界是 EngineHost ↔ WorkflowRunProcess，该边界成立。 |

结论：解耦目标基本达成，主程序耦合度低，对 UI 对接友好。无需为 K.1 做解耦改造。

---

## 7. 结论与 K.1 行动建议

### 7.1 Go / No-Go

**结论：Go（可以进入 K.1）。** 后端对 K.1 的唯一硬依赖是 `GET /api/v1/health`（已存在、免鉴权）与清晰的连接契约（已确认）。本报告未发现任何阻塞 K.1 的后端缺陷。

### 7.2 K.1 落地清单（建议范围，勿越界到 K.2）

1. 复核 `Program.cs/App.axaml(.cs)/MainWindow` 启动链路保持可运行。
2. 在 `Models/` 建连接配置模型：`BaseUrl`（默认 `http://127.0.0.1:8000`）、`Token`、`ConnectionStatus`。
3. 加最小 health 探测（仅 `GET /api/v1/health`）并把成功/失败映射到状态与错误文案；连接失败要有明确提示。
4. 主窗口替换模板问候语为"连接配置 + 连接/测试按钮 + 状态显示"。
5. 收口 `pyproject.toml` 的 PySide6/pytest-qt（移除或移入可选分组）。
6. 在 Windows/.NET 10 跑通 `dotnet build Avalonia_UI/Avalonia_UI.sln`（K.1 验收硬指标）。
7. 先拍板 §3.4 的两个决策点（token 来源、谁启动 EngineHost）。

### 7.3 K.2（C# Client）开工前必须先定的契约项

1. 以 `_to_jsonable` 的实际输出为准制定 C# DTO（不要依赖 `api_models.py` 的死 View 类，也别指望 OpenAPI 描述 data）。建议同时决定后端是否清理死 DTO / 固化契约文档。
2. 错误模型按 `{error_code,message,details,retryable}` 4 字段建。
3. REST 用 `Authorization: Bearer`，WS 用 `?token=`；二者分开实现。
4. 把 §4.3 的端点分歧回灌到 `00_规范`/`api_models`，避免规范与实现继续漂移。

### 7.4 跨阶段技术债（不阻塞，建议排期）

- 引入 logging（优先 `supervisor.maintenance_loop` 与 `main.py` 的静默吞没点）。
- `EventRouter` 队列设上界；连接确认改为点对点、不全局持久化。
- 视 K.6/K.7 需要补齐 audit/publication 的时间窗与分页过滤。
- 确定化并发执行池脆弱测试；在 Windows 目标复跑确认 `pytest -q` 全绿（项目 K.0a 基线要求）。
- `_connect` 显式关闭连接；`instance_lock` 平台守卫消除 mypy 噪声。

---

## 附录 A：C# 客户端端点速查（K.2 用）

- Base URL（默认）：`http://127.0.0.1:8000`
- 鉴权：REST `Authorization: Bearer <token>`；WS `?token=<token>`；token 文件 `runtime/config/local_api_token`
- 免鉴权：`GET /api/v1/health`
- 启动运行：`POST /api/v1/workflows/{workflow_id}/runs`（看返回 run.status，不只看 201）
- 取消：`POST /api/v1/runs/{workflow_run_id}/cancel`（返回 process 快照，状态异步收敛）
- 运行/节点：`GET /api/v1/runs`、`/runs/{id}`、`/runs/{id}/nodes`、`/runs/{id}/table-refs`
- 事件：REST `GET /api/v1/events?after_sequence_number=&workflow_run_id=&node_run_id=&event_type=&limit=`；WS `/ws/v1/events?token=`（带 `sequence_number`，用于重连去重）
- 审计：`GET /api/v1/audit-events?workflow_run_id=&node_run_id=&event_type=`
- 共享发布：`GET /api/v1/shared-publications?share_name=&limit=`、`GET /api/v1/shared-publications/{share_name}/versions?limit=`
- 统一响应：`{ ok, data, error:{error_code,message,details,retryable}|null, request_id }`
