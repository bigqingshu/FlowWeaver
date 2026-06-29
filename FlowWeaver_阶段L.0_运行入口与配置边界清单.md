# FlowWeaver 阶段L.0：运行入口与配置边界清单

> 文档状态：阶段L前置边界确认
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md` 和阶段K已固化验收基线
> 适用范围：K.8完成后、进入后续桌面端集成稳定化前
> 当前执行点：L.0，只做运行入口与配置边界清单，不修改运行时代码

## 1. L.0目标

阶段K已经完成最小 Avalonia 桌面客户端，UI 可以通过 HTTP 和 WebSocket 访问 Python FastAPI EngineHost。阶段L不应立刻进入工作流画布、完整表格编辑、打包发布或多用户能力。L.0先固化运行入口和配置边界，避免后续把启动、鉴权、配置持久化和进程所有权混在一起实现。

L.0目标：

- 明确 EngineHost 和 Avalonia UI 的当前启动入口
- 明确 BaseUrl、token、WebSocket 地址和本地运行数据的配置来源
- 明确哪些配置可以进入 UI 持久化，哪些仍应由 EngineHost 负责
- 明确断线、鉴权失败、端口变化和 EngineHost 重启时的处理边界
- 给出阶段L后续小步顺序

L.0不做：

- 不新增启动器代码
- 不新增配置持久化代码
- 不修改 EngineHost、Supervisor、WorkflowRunProcess 或 RuntimeStore
- 不让 UI 直接读取 SQLite 或 Python 内部文件作为运行事实源
- 不实现安装包、自动更新、系统托盘或后台服务

## 2. 继承自K阶段的基线

K.8完成后，当前基线为：

- UI路径固定为 `Avalonia_UI/`
- UI技术栈为 Avalonia、.NET 10.0、C#、MVVM
- 后端为 Python FastAPI EngineHost
- 通信方式为 HTTP + WebSocket
- UI只作为客户端，不拥有运行状态
- UI不直接访问 SQLite，不绕过 FastAPI、Supervisor、WorkflowRunProcess 或 RuntimeStore
- UI已具备 health、workflow 列表、启动 run、Run/NodeRun 状态、cancel、RuntimeEvent WebSocket、断线重连 REST 恢复、日志审计只读查询和数据摘要视图
- 当前仍不包含工作流画布、完整表格内容加载、表格编辑、权限审批页面、长期离线缓存、安装包发布和跨 workflow 触发能力

## 3. 当前运行入口

| 入口 | 当前命令或路径 | 所有权 | L.0结论 |
| --- | --- | --- | --- |
| EngineHost API | `.\python312\Scripts\uvicorn.exe --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000` | 用户或开发者手动启动 | 当前正式后端入口，UI不自动拥有该进程 |
| 本地 API token | `runtime/config/local_api_token` | EngineHost Bootstrap 创建和维护 | token 来源属于后端运行目录，不提交到仓库 |
| Avalonia UI | `dotnet run --project Avalonia_UI/Avalonia_UI.csproj` 或构建后的 UI 程序 | UI进程拥有展示和用户操作 | 当前只连接 EngineHost，不启动或嵌入 EngineHost |
| HTTP API | `BaseUrl + /api/v1/...` | EngineHost | 除 `/api/v1/health` 外需要 `Authorization: Bearer <token>` |
| RuntimeEvent WebSocket | `ws://host/ws/v1/events?token=<token>` | EngineHost | token通过查询参数传入，UI负责断线提示和重连 |
| 元数据和运行事实源 | `runtime/` 下 SQLite 与运行数据 | EngineHost / RuntimeStore | UI不得直接读取或修改 |

## 4. 配置边界

### 4.1 BaseUrl

当前默认值：

```text
http://127.0.0.1:8000
```

边界：

- BaseUrl 是 UI 连接 EngineHost 的客户端配置
- 当前由用户在 UI 中显式输入或使用默认值
- BaseUrl 必须是绝对 HTTP 或 HTTPS URL
- 端口冲突、EngineHost换端口或远程地址变化时，由用户更新 BaseUrl
- UI不得从 SQLite、RuntimeStore 或 workflow 数据中推导 BaseUrl

后续可实现的最小顺序：

1. 先持久化最近一次成功连接的 BaseUrl
2. 再补最近连接列表或环境标签
3. HTTPS、远程部署和证书配置留到更后续阶段

### 4.2 Token

当前来源：

```text
runtime/config/local_api_token
```

边界：

- token 由 EngineHost Bootstrap 生成和维护
- token 不进入仓库、不进入 README 示例明文、不进入日志
- UI当前由用户手动输入 token
- REST鉴权使用 `Authorization: Bearer <token>`
- WebSocket鉴权使用 `/ws/v1/events?token=<token>`
- WebSocket URL 在日志、错误提示和异常展示中必须脱敏，不得输出完整 query token
- `/api/v1/health` 不需要 token，只能证明 EngineHost 可达，不能证明业务API可用

后续可实现的最小顺序：

1. 先保持 token 手动输入，避免误读后端运行目录
2. 如果要持久化，必须明确使用用户级本地配置或系统凭据存储，不写入仓库目录
3. 如果要提供“从本机 EngineHost 读取 token”的开发便利入口，应作为显式用户动作，并只服务本机开发场景

### 4.3 UI本地配置

当前状态：

- `EngineHostConnectionSettings` 在 UI 进程内保存 BaseUrl 和 token
- 关闭 UI 后不保证保留输入
- 没有 appsettings、用户配置文件或凭据存储方案

L阶段建议配置优先级：

```text
用户当前显式输入
→ 用户级本地配置中的上次成功连接
→ 默认 BaseUrl http://127.0.0.1:8000
```

边界：

- UI本地配置只保存客户端连接偏好
- UI本地配置不是运行状态事实源
- workflow、run、node、event、table、audit 数据仍必须从 EngineHost API 获取
- token若持久化，需要单独决策存储位置和脱敏策略

### 4.4 启动脚本和进程所有权

当前状态：

- EngineHost 由用户或开发者手动启动
- Avalonia UI 单独启动并连接已有 EngineHost
- UI关闭不应终止 EngineHost、WorkflowRunProcess 或 NodeExecutorProcess

后续可选方案：

| 方案 | 描述 | 建议 |
| --- | --- | --- |
| 手动启动 EngineHost，UI只连接 | 保持当前进程所有权最清晰 | L阶段默认方案 |
| 仓内开发脚本启动后端和UI | 用 PowerShell 脚本串起开发体验 | 可在L.1c作为小步 |
| UI提供“启动本机EngineHost”按钮 | UI创建后端进程并负责清理 | 暂缓，需要先定义子进程所有权 |
| 安装包内置后台服务 | 桌面程序管理后台生命周期 | 不属于L.0，留到打包阶段 |

L.0结论：

- 下一小步优先补 L.1a 后端运行入口说明
- 暂不让 UI 自动启动 EngineHost
- 若未来进入 UI 启动后端，必须先定义 PID 记录、退出清理、端口冲突和重复实例拒绝

## 5. 连接失败与恢复边界

| 场景 | 当前或建议处理 | 不做事项 |
| --- | --- | --- |
| EngineHost未启动 | health失败，UI展示连接错误 | 不自动创建数据库或启动后台 |
| BaseUrl非法 | UI客户端边界拒绝请求 | 不发送无效请求到后端 |
| token为空 | 业务API和WebSocket在UI层拒绝 | 不进入无限重连 |
| token错误、轮换或失效 | 后端返回鉴权错误，UI展示错误 | 不自动改写 token 文件 |
| WebSocket断开 | UI提示断线，REST补状态后重连 | 不做长期离线事件缓存 |
| EngineHost重启 | UI重新 health / REST 刷新 / WS重连 | 不假设旧内存状态仍有效 |
| 端口变化 | 用户修改 BaseUrl 后重新连接 | 不扫描端口或猜测服务 |

WebSocket日志脱敏规则：

- 禁止记录包含真实 token 的完整 WebSocket URL
- 可以记录 `ws://host/ws/v1/events?token=***`
- 可以记录不含 query 的 `ws://host/ws/v1/events`
- UI错误提示和异常消息中也应遵守同一规则

## 6. 明确不支持能力

L.0不进入以下能力：

- 工作流画布和复杂节点编辑器
- 节点配置表单生成器
- 完整表格内容查看或编辑
- 权限审批 UI 和交互式授权
- UI直接读取 `runtime/metadata/flowweaver.db`
- 自动发现、启动或杀死 EngineHost
- 后台服务、系统托盘、安装包和自动更新
- 多用户登录、远程权限、HTTPS证书和生产部署
- 长期离线缓存、增量事件回放和复杂冲突合并

## 7. L.0验收清单

L.0完成条件：

- 已列出 EngineHost、token、Avalonia UI、HTTP API、WebSocket 和 RuntimeStore 的当前入口
- 已明确 UI 配置只保存连接偏好，不保存运行事实源
- 已明确 BaseUrl 和 token 的来源、输入和后续持久化边界
- 已明确 WebSocket URL 在日志、错误提示和异常展示中必须脱敏
- 已明确 UI当前不启动、不嵌入、不拥有 EngineHost
- 已列出连接失败、鉴权失败、断线、重启和端口变化的处理边界
- 已将 L.1 拆分为后端运行入口、桌面端运行入口和组合开发脚本边界
- 已将 L.3 验收扩展为空数据库、已有工作流和 EngineHost 重启三类场景

## 8. 阶段L后续建议顺序

| 小步 | 执行方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| L.0 | 运行入口与配置边界 | 本清单 | 代码实现 |
| L.1a | 后端运行入口收口 | EngineHost启动、迁移、token读取和health检查说明 | UI自动托管后端 |
| L.1b | 桌面端运行入口收口 | Avalonia build/run、BaseUrl/token输入和连接检查说明 | 桌面端内嵌后端逻辑 |
| L.1c | 组合开发脚本边界 | 可选PowerShell开发脚本候选清单 | 安装包、服务化和后台托管 |
| L.2 | UI连接配置持久化 | BaseUrl等客户端偏好保存和加载 | token默认明文落盘 |
| L.3 | 桌面端正式路径烟雾清单 | 空数据库、已有工作流、EngineHost重启三类验收 | 新业务功能 |
| L.4 | 连接体验稳定化 | 错误文案、重连状态和刷新入口小修 | 长期离线缓存 |

L.3验收场景需要至少覆盖：

- 空数据库：首次启动、迁移、health、workflow/run空列表和UI空状态不报错
- 已有工作流：workflow列表、启动run、NodeRun、RuntimeEvent WebSocket、日志审计和数据摘要可走通
- EngineHost重启：UI提示断线，重新health，REST恢复Run/NodeRun状态，WebSocket重连，不依赖旧内存状态

L阶段完成后，再评估是否进入下一条主线：

- 工作流定义和节点配置入口
- 工作流画布
- 表格内容查看和编辑
- 权限审批 UI
- 打包发布

## 9. 当前建议

最稳的下一小步是 L.1a：先补后端运行入口收口。建议优先产出：

- README 中的 EngineHost 启动、迁移、token读取和 health 检查顺序
- 桌面端启动入口和组合开发脚本只列入 L.1b / L.1c，不在 L.1a 提前实现
- 不让 UI 自动启动 EngineHost
- 不修改协议和后端组合根
