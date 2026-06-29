# FlowWeaver 阶段L.3a：空数据库正式路径烟雾执行记录

> 文档状态：阶段L.3a执行记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口、阶段L.2连接配置持久化闭环和阶段L.3正式路径烟雾清单
> 适用范围：空数据库首次启动 smoke
> 当前执行点：只执行空数据库首次启动场景，不进入已有工作流正式链路或 EngineHost 重启恢复

## 1. 执行目标

L.3a只验证一件事：默认 EngineHost 在空运行目录下是否能通过正式入口启动，并提供空状态 API。

本小步不做：

- 不清理仓库内既有 `runtime/`
- 不创建 workflow
- 不启动 workflow run
- 不运行节点
- 不执行 SharedPublication 读写链路
- 不执行 EngineHost 重启恢复
- 不让 UI 直接读取 SQLite
- 不保存 token

## 2. 执行路径

本次 smoke 使用临时空工作目录执行：

```text
临时空工作目录
→ 复制 alembic.ini 与 migrations/
→ python312 -m uvicorn --app-dir <repo>/src flowweaver.api.app:create_default_app --factory
→ create_default_app()
→ bootstrap_default()
→ 临时目录/runtime/metadata/flowweaver.db
→ 临时目录/runtime/config/local_api_token
→ HTTP API
```

说明：

- 未使用测试专用 Executor 注入
- 未绕过 `create_default_app()`
- 未复用仓库既有 `runtime/`
- 未打印真实 token
- 未修改仓库运行数据

## 3. 实际执行结果

执行时间：2026-06-29

临时运行目录：

```text
C:\Users\12650\AppData\Local\Temp\flowweaver-l3a-empty-0158dbaab3204832b8a69af1423db093
```

实际结果：

| 检查项 | 结果 |
| --- | --- |
| EngineHost 正式入口启动 | PASS |
| health 返回 ok | PASS |
| 自动创建 `runtime/metadata/flowweaver.db` | PASS |
| 自动创建 `runtime/config/local_api_token` | PASS |
| 自动创建 `runtime/workflow_runs/` | PASS |
| 自动创建 `runtime/logs/` | PASS |
| 自动创建 `runtime/temp/` | PASS |
| token 文件非空 | PASS |
| `/api/v1/workflows` 空列表 | PASS |
| `/api/v1/runs` 空列表 | PASS |
| `/api/v1/events` 空列表 | PASS |
| `/api/v1/audit-events` 空列表 | PASS |
| `/api/v1/shared-publications` 空列表 | PASS |
| 错误 token 返回 401 | PASS |

结果摘要：

```text
result = PASS
health_ok = True
token_file_exists = True
token_length = 36
workflows_count = 0
runs_count = 0
runtime_events_count = 0
audit_events_count = 0
shared_publications_count = 0
invalid_token_status = 401
```

## 4. 自动化补充

新增自动化：

```text
tests/integration/test_l3a_empty_runtime_smoke.py
```

覆盖内容：

- 使用真实 uvicorn 子进程
- 使用 `create_default_app()` 正式入口
- 使用空临时运行目录
- 验证 runtime 目录、元数据库和本地 token 自动创建
- 验证空 workflow、run、RuntimeEvent、AuditEvent、SharedPublication 列表
- 验证错误 token 返回 401

不覆盖内容：

- 不覆盖桌面窗口点击
- 不覆盖 workflow 创建和运行
- 不覆盖节点执行
- 不覆盖 WebSocket
- 不覆盖 EngineHost 重启恢复

## 5. 验收结论

L.3a通过。

空数据库首次启动场景未发现后端组合根缺口。当前默认正式入口能够创建运行目录、元数据库和本地 token，并能通过 HTTP API 返回空状态。

UI 侧空状态未做真实窗口点击验收；本小步仅保持现有 Avalonia build/test 作为连接配置、空列表和 token 不持久化边界的回归验证。

## 6. 下一步建议

建议进入 L.3b：已有工作流正式链路烟雾执行。

L.3b建议只覆盖：

- token 鉴权成功
- 创建或读取 workflow
- 启动 run
- 查询 run 和 NodeRun
- 查询 RuntimeEvent
- 查询 TableRef
- 发布和读取 SharedPublication
- 查询 AuditEvent
- 验证 UI 可通过 REST 恢复摘要状态

仍不建议在 L.3b 做 EngineHost 重启恢复；重启恢复应保留给 L.3c。
