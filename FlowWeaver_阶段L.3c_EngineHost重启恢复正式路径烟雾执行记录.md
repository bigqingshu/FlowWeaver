# FlowWeaver 阶段L.3c：EngineHost重启恢复正式路径烟雾执行记录

> 文档状态：阶段L.3c执行记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K验收基线、阶段L.0边界清单、阶段L.1运行入口收口、阶段L.2连接配置持久化闭环和阶段L.3正式路径烟雾清单
> 适用范围：EngineHost 使用同一 `runtime/` 重启后的恢复 smoke
> 当前执行点：只执行同一临时 `runtime/` 重启恢复，不扩展 UI 画布、打包或真实窗口自动化

## 1. 执行目标

L.3c验证默认 EngineHost 停止后，使用同一运行目录重新启动时，是否能通过正式 REST + WebSocket 路径恢复既有摘要状态。

本小步覆盖：

- 使用同一临时 `runtime/` 首次启动 EngineHost
- 创建 producer/consumer workflow
- 完成 producer/consumer run
- 停止 EngineHost
- 使用同一 `runtime/` 重新启动 EngineHost
- token 文件复用
- REST 恢复 workflows、runs、NodeRuns、RuntimeEvent、TableRef、SharedPublication、AuditEvent
- WebSocket 重连收到 `ENGINE_READY`

本小步不做：

- 不测试运行中的 workflow 跨 EngineHost 重启续跑
- 不测试 UI 真实窗口点击
- 不新增 UI 自动启动/停止 EngineHost
- 不保存 token
- 不新增打包或安装器
- 不执行工作流画布功能

## 2. 执行路径

本次 smoke 使用同一临时工作目录执行：

```text
临时工作目录
→ 复制 alembic.ini 与 migrations/
→ 第一次启动 create_default_app()
→ 创建 producer workflow 并运行至 SUCCEEDED
→ 创建 consumer workflow 并运行至 SUCCEEDED
→ 等待 RuntimeEvent 可通过 REST 查询
→ 停止 EngineHost
→ 第二次启动 create_default_app()
→ 读取同一 runtime/config/local_api_token
→ 通过 REST 恢复 workflow/run/node/event/table/shared/audit 摘要
→ WebSocket 重连收到 ENGINE_READY
```

说明：

- 后端走真实 uvicorn 子进程
- workflow run 走真实 WorkflowRunProcess 子进程
- 使用同一个临时 `runtime/`
- 未清理或修改仓库既有 `runtime/`
- 未打印真实 token

## 3. 实际执行结果

执行时间：2026-06-29

实际结果：

| 检查项 | 结果 |
| --- | --- |
| 第一次 EngineHost 正式入口启动 | PASS |
| 第一次 health 返回 ok | PASS |
| 第一次 token 文件生成 | PASS |
| producer workflow 创建 | PASS |
| producer run 进入 `SUCCEEDED` | PASS |
| consumer workflow 创建 | PASS |
| consumer run 进入 `SUCCEEDED` | PASS |
| producer/consumer RuntimeEvent 首次运行后可查 | PASS |
| 停止第一次 EngineHost | PASS |
| 第二次 EngineHost 使用同一 `runtime/` 启动 | PASS |
| 第二次 health 返回 ok | PASS |
| 第二次 token 与第一次一致 | PASS |
| workflows 可恢复 producer/consumer | PASS |
| runs 可恢复 producer/consumer `SUCCEEDED` 终态 | PASS |
| producer NodeRun 可恢复 | PASS |
| consumer NodeRun 可恢复 | PASS |
| producer TableRef 中存在 2 个 `PUBLISHED` 摘要 | PASS |
| SharedPublication `l3c.orders` 版本 1 可恢复 | PASS |
| SharedPublication versions 可恢复 | PASS |
| producer/consumer RuntimeEvent 可恢复 | PASS |
| producer/consumer AuditEvent 可恢复 | PASS |
| WebSocket 重连收到 `ENGINE_READY` | PASS |

## 4. 自动化补充

新增自动化：

```text
tests/integration/test_l3c_enginehost_restart_smoke.py
```

本次同时抽取正式路径 smoke helper：

```text
tests/integration/formal_smoke_helpers.py
```

用途：

- 复用真实 uvicorn 启动/停止逻辑
- 复用 HTTP API 调用逻辑
- 复用 WebSocket URL 构造
- 复用 producer/consumer workflow 定义
- 降低 L.3b 与 L.3c 的重复代码

## 5. 验收结论

L.3c通过。

第一阶段当前正式路径已经覆盖：

- L.3a 空数据库首次启动
- L.3b 已有工作流正式链路
- L.3c EngineHost 同一 `runtime/` 重启恢复

当前未覆盖并明确保留：

- 运行中 workflow 跨 EngineHost 重启续跑
- token 轮换后的 UI 自动恢复
- 真实桌面窗口端到端点击
- 打包入口和安装器

## 6. 下一步建议

建议进入 L 阶段总体验收复核。

复核重点：

- L.1 后端/桌面/组合脚本入口是否和 README 一致
- L.2 BaseUrl 持久化和 token 不持久化边界是否完整
- L.3a/L.3b/L.3c 正式路径 smoke 是否覆盖三类验收
- 是否需要把 L.3 smoke 命令整理成开发者命令清单
- 是否存在进入下一阶段前必须修的后端组合根缺口
