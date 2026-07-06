# FlowWeaver 阶段L.3b：已有工作流正式链路烟雾执行记录

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：后端运行入口、桌面运行入口、组合开发脚本、连接配置持久化、失败场景和正式路径 smoke 已经落地。
> 未实现：无本文件目标内的未实现项。
> 原因：当前连接与运行入口已被后续 M/N/O/P 阶段继续复用。

> 文档状态：阶段L.3b执行记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口、阶段L.2连接配置持久化闭环和阶段L.3正式路径烟雾清单
> 适用范围：已有工作流正式链路 smoke
> 当前执行点：只执行已有工作流正式链路，不执行 EngineHost 重启恢复

## 1. 执行目标

L.3b验证默认 EngineHost 在真实 HTTP + WebSocket 路径下，是否能完成已有工作流的核心运行链路。

本小步覆盖：

- token 鉴权成功
- 创建 workflow
- 启动 workflow run
- 查询 run 和 NodeRun
- 查询 RuntimeEvent
- 查询 TableRef
- 发布和读取 SharedPublication
- 查询 AuditEvent
- WebSocket 收到 `ENGINE_READY` 与运行事件
- 断开并重连 WebSocket 后收到 `ENGINE_READY`

本小步不做：

- 不执行 EngineHost 重启恢复
- 不执行桌面窗口点击验收
- 不新增工作流画布
- 不新增 UI 直接 SQLite 读取
- 不保存 token
- 不引入测试专用 Executor 注入

## 2. 执行路径

本次 smoke 使用临时空工作目录执行：

```text
临时空工作目录
→ 复制 alembic.ini 与 migrations/
→ python312 -m uvicorn --app-dir <repo>/src flowweaver.api.app:create_default_app --factory
→ create_default_app()
→ bootstrap_default()
→ 临时目录/runtime/metadata/flowweaver.db
→ HTTP API + RuntimeEvent WebSocket
→ 创建 producer workflow
→ 启动 producer run
→ GenerateTestTableNode -> FilterRowsNode -> PublishSharedTablesNode
→ 查询 NodeRun、RuntimeEvent、TableRef、SharedPublication、AuditEvent
→ 创建 consumer workflow
→ 启动 consumer run
→ ReadSharedTablesNode
→ 查询 NodeRun、RuntimeEvent、AuditEvent
→ WebSocket 重连
```

说明：

- 后端走真实 uvicorn 子进程
- workflow run 走真实 WorkflowRunProcess 子进程
- 节点执行走默认内置节点执行器
- WebSocket 使用真实 `/ws/v1/events?token=...`
- 未打印真实 token
- 未修改仓库既有 `runtime/`

## 3. 发现并修正的缺口

L.3b首次执行时发现一个后端组合根缺口：

```text
父进程 create_default_app() 在临时工作目录创建 runtime/metadata/flowweaver.db
→ Supervisor 启动 WorkflowRunProcess 时 cwd 固定为仓库根目录
→ 子进程收到相对 sqlite:///runtime/metadata/flowweaver.db
→ 子进程尝试打开仓库根目录下的 runtime 数据库
→ sqlite3.OperationalError: unable to open database file
→ workflow run 被标记为 ABORTED
```

修正方式：

- 在 `EngineHostBootstrap` 初始化时把 `data_dir`、`metadata_db_path`、`runtime_dir`、`log_dir` 和 `temp_dir` 固化为绝对路径
- 保证父进程、Supervisor 和 WorkflowRunProcess 使用同一个运行目录
- 新增 bootstrap 测试固化相对 `data_dir` 的绝对化边界

该修正属于 L.3b 正式路径前置缺口，不改变 API、不改变默认技术栈、不扩大到重启恢复。

## 4. 实际执行结果

执行时间：2026-06-29

实际结果：

| 检查项 | 结果 |
| --- | --- |
| EngineHost 正式入口启动 | PASS |
| token 鉴权成功 | PASS |
| 创建 producer workflow | PASS |
| workflow 列表可读取 | PASS |
| 启动 producer run | PASS |
| producer run 进入 `SUCCEEDED` | PASS |
| WebSocket 收到 producer `WORKFLOW_STARTED` | PASS |
| WebSocket 收到 producer `WORKFLOW_FINISHED` | PASS |
| producer NodeRun 全部 `SUCCEEDED` | PASS |
| producer TableRef 中存在 2 个 `PUBLISHED` 摘要 | PASS |
| SharedPublication `l3b.orders` 版本 1 可查询 | PASS |
| SharedPublication versions 可查询 | PASS |
| 创建 consumer workflow | PASS |
| 启动 consumer run | PASS |
| consumer run 进入 `SUCCEEDED` | PASS |
| consumer `input_snapshot_id` 非空 | PASS |
| consumer NodeRun `read` 为 `SUCCEEDED` | PASS |
| producer RuntimeEvent 可按 workflow_run_id 查询 | PASS |
| consumer RuntimeEvent 可按 workflow_run_id 查询 | PASS |
| producer AuditEvent 可查询 | PASS |
| consumer AuditEvent 可查询 | PASS |
| run 列表可恢复 producer/consumer 终态摘要 | PASS |
| WebSocket 断开并重连收到 `ENGINE_READY` | PASS |

## 5. 自动化补充

新增自动化：

```text
tests/integration/test_l3b_formal_workflow_smoke.py
```

覆盖内容：

- 真实 uvicorn 子进程
- `create_default_app()` 正式入口
- 真实 HTTP 创建 workflow、启动 run、查询只读 API
- 真实 WorkflowRunProcess 子进程
- 默认内置表节点和共享表节点
- RuntimeEvent WebSocket 连接、事件接收和重连
- 相对运行目录下的绝对路径组合根

配套修正：

```text
src/flowweaver/engine/bootstrap.py
tests/integration/test_bootstrap_and_events.py
```

## 6. 验收结论

L.3b通过。

已有工作流正式链路已能通过真实 HTTP + WebSocket + WorkflowRunProcess 子进程完成 producer/consumer 两段运行，并能查询 NodeRun、RuntimeEvent、TableRef、SharedPublication 和 AuditEvent。

仍未覆盖：

- EngineHost 停止后 UI 恢复
- EngineHost 使用同一 `runtime/` 重启后的 REST 状态恢复
- WebSocket 断线后跨 EngineHost 重启恢复
- token 错误、轮换或失效后的 UI 恢复

## 7. 下一步建议

建议进入 L.3c：EngineHost 重启恢复正式路径烟雾执行。

L.3c建议只覆盖：

- 使用同一临时 `runtime/` 启动 EngineHost
- 保留已完成 workflow/run/event/shared/audit 数据
- 停止 EngineHost
- 使用同一 `runtime/` 重启 EngineHost
- token 可复用或重新读取
- REST 恢复 workflows/runs/events/shared/audit 摘要
- WebSocket 重连收到 `ENGINE_READY`

仍不建议在 L.3c 扩展 UI 画布、打包或真实窗口自动化。
