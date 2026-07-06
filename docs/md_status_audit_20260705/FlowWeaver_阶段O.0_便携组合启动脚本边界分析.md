# FlowWeaver 阶段O.0：便携组合启动脚本边界分析

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.0边界分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录
> 适用范围：便携版 `EngineHost/` 与 `Desktop/` 的组合启动脚本语义、接口和验收边界
> 当前执行点：只做边界分析和计划固化，不新增脚本、不修改 EngineHost 或 Avalonia 产品代码、不进入安装器/托盘/自动更新

## 1. 背景

阶段N已经完成便携目录生成、后端 runtime smoke、Desktop publish 产物 smoke，以及发布目录 API/WebSocket Client 与便携 EngineHost 的最小联调。

当前便携目录结构基线为：

```text
FlowWeaverPortable/
  EngineHost/
    python312/python.exe
    src/
    migrations/
    alembic.ini
    runtime/
      config/local_api_token
      metadata/flowweaver.db
      workflow_runs/
      logs/
      temp/
  Desktop/
    Avalonia_UI.exe
    Avalonia_UI.dll
```

阶段O.0 的目标是明确后续“组合启动脚本”应该承担什么职责，以及哪些职责仍必须留给 EngineHost、Desktop UI 或未来安装器。

## 2. O.0目标

O.0 只确认语义和接口范围，目标是为后续 O.1/O.2 的最小实现降低歧义。

本阶段确认：

- 组合启动脚本的输入、输出和职责
- EngineHost 启动顺序、工作目录和健康检查边界
- 端口选择与 BaseUrl 传递策略
- token 文件读取、等待和脱敏日志策略
- EngineHost 日志路径与启动失败诊断策略
- Desktop UI 启动方式和配置交接边界
- 组合脚本退出时的进程生命周期策略
- 最小验收 smoke 应覆盖的路径

本阶段不做：

- 不新增 `start_portable.*` 脚本
- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/publish_desktop.py`
- 不修改 EngineHost API 或配置模型
- 不修改 Avalonia UI 启动入口
- 不实现 UI 托管后端
- 不实现系统托盘、后台服务、安装器或自动更新

## 3. 组合启动脚本定位

组合启动脚本应定位为“便携版开发/体验入口”，不是新的运行时事实源。

脚本可以负责：

- 从 `FlowWeaverPortable/` 根目录定位 `EngineHost/` 和 `Desktop/`
- 启动 EngineHost
- 等待 `/api/v1/health`
- 等待或读取 `EngineHost/runtime/config/local_api_token`
- 启动 `Desktop/Avalonia_UI.exe`
- 将 BaseUrl 以明确方式交给用户或 UI
- 将 EngineHost stdout/stderr 写入便携目录日志
- 在脚本控制台输出脱敏诊断信息

脚本不应负责：

- 直接读写 SQLite 元数据库
- 修改 workflow、run、node、event、table 或 audit 数据
- 持有运行状态事实源
- 替代 EngineHost 的 token 生成逻辑
- 让 UI 进程内嵌 Python EngineHost
- 实现系统级服务守护
- 实现多用户安装和权限提升

## 4. 启动顺序边界

建议的最小启动顺序：

1. 确认当前目录或脚本所在目录为 `FlowWeaverPortable/`
2. 验证 `EngineHost/python312/python.exe` 存在
3. 验证 `EngineHost/src/flowweaver/api/app.py` 存在
4. 验证 `Desktop/Avalonia_UI.exe` 存在
5. 选择 EngineHost 监听端口
6. 以 `EngineHost/` 为工作目录启动 uvicorn
7. 等待 `/api/v1/health` 返回 `ok`
8. 读取 `EngineHost/runtime/config/local_api_token`
9. 启动 `Desktop/Avalonia_UI.exe`
10. 在控制台输出 BaseUrl、日志路径和脱敏状态

EngineHost 启动命令基线：

```powershell
EngineHost\python312\python.exe -m uvicorn --app-dir EngineHost\src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port <port>
```

关键边界：

- `cwd` 必须是 `EngineHost/`
- `--app-dir` 指向 `EngineHost/src`
- `runtime/` 必须落在 `EngineHost/runtime/`
- 组合脚本不应把 repo 源码目录注入 `PYTHONPATH`
- 组合脚本不应覆盖现有 `runtime/config/local_api_token`

## 5. 端口与BaseUrl策略

第一版建议采用“固定默认端口 + 占用即拒绝”的保守策略：

| 项 | 建议 |
| --- | --- |
| 默认 host | `127.0.0.1` |
| 默认 port | `8000` |
| 自动寻找随机端口 | O.0 暂不作为默认方案 |
| 端口占用 | 明确失败并提示用户关闭占用进程或指定端口 |
| BaseUrl | `http://127.0.0.1:<port>` |
| 对外网卡监听 | 不支持 |

原因：

- 固定端口更容易和当前 Avalonia BaseUrl 持久化模型对齐
- 随机端口需要额外传递机制，否则 UI 可能仍连接旧 BaseUrl
- 第一版组合脚本更适合先保证可诊断和可复现

未来如果需要支持 `--port 0` 或自动寻找端口，必须同时补齐：

- UI 启动时接收 BaseUrl 的明确入口
- 日志中记录实际端口
- WebSocket URL 脱敏
- 端口复用和旧 EngineHost 残留进程识别

## 6. token交接边界

token 仍由 EngineHost 负责生成或复用，组合脚本只等待并读取。

建议策略：

- 等待 health 成功后读取 `EngineHost/runtime/config/local_api_token`
- token 只用于提示用户或传给 UI 的临时启动上下文
- 控制台日志不打印 token 原文
- WebSocket URL 永远不打印完整 query
- 如 token 文件不存在或为空，组合脚本应失败并指向 EngineHost stderr 日志

当前最保守方案：

- 组合脚本只打印：

```text
BaseUrl: http://127.0.0.1:8000
Token: see EngineHost/runtime/config/local_api_token
```

可选后续方案：

- UI 支持命令行参数 `--base-url`
- UI 支持从临时一次性文件读取 BaseUrl
- UI 支持“启动时只预填 BaseUrl，不持久化 token”

O.0 不决定 token 是否自动注入 UI；该问题应在实现前单独确认。

## 7. 日志与诊断边界

组合脚本至少应保留以下日志：

| 日志 | 建议路径 | 内容 |
| --- | --- | --- |
| EngineHost stdout | `EngineHost/runtime/logs/enginehost.stdout.log` | uvicorn 标准输出 |
| EngineHost stderr | `EngineHost/runtime/logs/enginehost.stderr.log` | 启动异常、traceback、端口占用 |
| launcher 日志 | `EngineHost/runtime/logs/portable-launcher.log` | 脚本启动步骤、脱敏状态、进程 id |

日志要求：

- 不记录 token 原文
- 不记录完整 WebSocket URL query
- 记录 Python exe 路径、EngineHost cwd、BaseUrl、health 等待结果
- 启动失败时输出 stderr 日志路径
- 健康检查超时时输出最后一次错误摘要

## 8. 进程生命周期边界

第一版需要先明确组合脚本和两个子进程的所有权。

建议最小策略：

| 场景 | 建议 |
| --- | --- |
| 脚本启动 EngineHost 失败 | 不启动 Desktop，退出非 0 |
| health 超时 | 停止本次启动的 EngineHost，退出非 0 |
| token 文件缺失 | 停止本次启动的 EngineHost，退出非 0 |
| Desktop 启动失败 | 停止本次启动的 EngineHost，退出非 0 |
| 用户关闭 Desktop | 第一版可停止本次启动的 EngineHost |
| 用户关闭脚本控制台 | 停止本次启动的 EngineHost |
| 已有 EngineHost 正在运行 | 第一版不接管，提示端口占用 |

暂不支持：

- 接管非本脚本启动的 EngineHost
- 后台守护 EngineHost
- UI 关闭后继续保留 EngineHost
- 系统托盘管理生命周期
- 崩溃后自动拉起 EngineHost

## 9. Desktop UI交接边界

当前 Avalonia UI 已支持用户输入 BaseUrl 和 token，并持久化 BaseUrl，不持久化 token。

组合脚本的第一版不应要求 UI 立即新增复杂托管能力。更稳的分阶段路线：

| 小步 | 建议 |
| --- | --- |
| O.1 | 文档和 smoke：启动脚本只启动 EngineHost 和 Desktop，控制台提示 BaseUrl/token 文件位置 |
| O.2 | UI 启动参数分析：是否只支持 `--base-url` 预填 |
| O.3 | 最小脚本实现：固定端口、固定日志、health 等待、启动 Desktop |
| O.4 | 脚本 smoke：验证 EngineHost health、token 文件和 Desktop 进程启动 |
| O.5 | 体验复核：失败提示、日志脱敏、关闭行为 |

在 UI 支持命令行参数前，组合脚本可以只输出 BaseUrl 和 token 文件路径，由用户在 UI 中输入 token。

## 10. 最小验收标准

组合启动脚本正式实现时，最小 smoke 应覆盖：

1. 从 `.tmp/FlowWeaverPortable/` 启动脚本
2. EngineHost 使用 `EngineHost/` 作为工作目录
3. `/api/v1/health` 返回 `ok`
4. `EngineHost/runtime/config/local_api_token` 存在且非空
5. `EngineHost/runtime/metadata/flowweaver.db` 存在
6. `Desktop/Avalonia_UI.exe` 被启动
7. EngineHost stdout/stderr 日志落在 `EngineHost/runtime/logs/`
8. 控制台和日志不包含 token 原文
9. 脚本退出后本次启动的 EngineHost 被停止

暂不要求：

- 自动填写 UI token
- UI 连接成功截图
- workflow 创建或运行
- 安装器生成
- 托盘控制
- 自动更新

## 11. 风险清单

| 风险 | 影响 | O.0建议 |
| --- | --- | --- |
| 端口被占用 | UI 连接到错误或旧 EngineHost | 第一版占用即拒绝，不自动接管 |
| token 自动注入 UI | 可能引入敏感信息落盘或日志泄露 | O.0 不实现，后续单独设计 |
| UI 关闭是否停止后端 | 影响用户预期和运行中 workflow | 第一版只管理本脚本启动的 EngineHost |
| 控制台窗口关闭 | 可能留下孤儿进程 | 实现时需对子进程做 finally 清理 |
| health 成功但 token 文件未就绪 | UI 无法访问业务 API | health 后仍显式等待 token 文件 |
| 随机端口 | 需要 UI BaseUrl 传递机制 | 第一版固定端口 |
| 日志泄露 token | 安全风险 | 所有 URL 和状态日志必须脱敏 |

## 12. 下一步建议

O.0 完成后，建议下一小步进入 O.1：便携组合启动脚本最小实现方案。

O.1 建议仍先不写脚本，先把实现形态定清楚：

- 采用 PowerShell 脚本、Python 脚本，还是两者都提供
- 脚本文件放在 `tools/` 还是生成到 `FlowWeaverPortable/`
- 是否支持 `--port`
- 是否支持 `--no-desktop`
- 是否在 Desktop 退出后停止 EngineHost
- smoke 测试采用 Python 集成测试还是 PowerShell 级手工验收

较稳的实现顺序：

1. O.1 文档：最小实现方案和验收命令
2. O.2 生成器改造：在便携目录写入 launcher 草稿或说明文件
3. O.3 最小 launcher 脚本实现
4. O.4 launcher smoke：只验 health、token、日志和 Desktop 进程启动
5. O.5 关闭行为和失败日志复核
