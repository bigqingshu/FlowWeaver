# FlowWeaver 阶段N.5：便携目录后端完整 Runtime Smoke

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：正式路径运行闭环、便携 layout、后端 runtime smoke、Avalonia publish、Desktop 产物 API/WebSocket/workflow run 联调 smoke 和阶段 N 验收已经落地。
> 未实现：无本文件目标内的未实现项；安装器和签名等不属于 N 阶段。
> 原因：当前 N 阶段定位是便携发布联调，不承担后续分发产品化。

> 文档状态：阶段N.5完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0-N.4完成记录
> 适用范围：`.tmp/FlowWeaverPortable/EngineHost/python312/python.exe` 后端完整 runtime smoke
> 当前执行点：只验证便携目录后端 runtime，不启动 Avalonia UI、不执行 `dotnet publish`、不创建安装器

## 1. 目标

N.5 的目标是验证 N.4 生成的便携目录不仅能 health 启动，还能用便携目录自带的 Python runtime 走通完整后端 runtime 链路。

本阶段验证：

- 使用 `.tmp/FlowWeaverPortableRuntimeTest-*/EngineHost/python312/python.exe`
- 后端工作目录固定为 `.tmp/FlowWeaverPortableRuntimeTest-*/EngineHost/`
- 启动前清除测试进程传入的 `PYTHONPATH`
- 通过 `--app-dir EngineHost/src` 加载便携目录源码
- Alembic 在便携目录中解析 `alembic.ini` 和 `migrations/`
- `runtime/`、token、workflow run 日志由便携目录生成
- producer workflow 可生成、过滤并发布共享表
- consumer workflow 可读取共享表
- NodeRun、RuntimeEvent REST、TableRef、SharedPublication、AuditEvent 都可查询

## 2. 本阶段修改清单

- 新增 `tests/integration/test_n5_portable_runtime_smoke.py`
- 新增 `docs/FlowWeaver_阶段N.5_便携目录后端完整RuntimeSmoke.md`
- 更新 README 当前阶段和下一步建议

本阶段不修改：

- Python 后端产品代码
- Avalonia UI 产品代码
- `tools/create_portable_layout.py`
- `.csproj` 发布配置
- 运行入口
- 安装器或启动脚本

## 3. 测试路径

新增测试命令：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n5_portable_runtime_smoke.py -q
```

测试步骤：

1. 调用 `tools/create_portable_layout.py` 的生成函数
2. 生成 `.tmp/FlowWeaverPortableRuntimeTest-*`
3. 复制完整 `python312/`
4. 从 `EngineHost/` 作为工作目录启动后端
5. 使用便携目录中的 `EngineHost/python312/python.exe`
6. 清除测试环境传入的 `PYTHONPATH`
7. health 成功后读取 `runtime/config/local_api_token`
8. 创建 producer workflow
9. 启动 producer run 并等待终态
10. 验证 producer NodeRun 全部 `SUCCEEDED`
11. 验证 producer `TableRef` 中有两个 `PUBLISHED`
12. 验证 `SharedPublication` 和版本列表
13. 创建 consumer workflow
14. 启动 consumer run 并等待终态
15. 验证 consumer NodeRun 为 `SUCCEEDED`
16. 验证 producer / consumer RuntimeEvent REST
17. 验证 producer / consumer AuditEvent
18. 验证 workflow run stdout/stderr 日志落在便携 `runtime/logs/workflow_runs/`
19. 停止后端并清理测试目录

## 4. 关键边界

N.5 证明的边界：

- EngineHost 可从便携目录自带 Python 启动
- 后端 runtime 不依赖仓库根目录作为工作目录
- 子进程路径跟随便携目录中的 `flowweaver` 源码位置
- WorkflowRunProcess 和 NodeExecutorProcess 能完成真实内置节点执行
- `runtime/` 数据和日志都留在便携 `EngineHost/` 下

N.5 不证明：

- Avalonia UI 发布产物可启动
- UI 连接发布目录中的 EngineHost
- WebSocket 发布目录端到端重连
- token 缺失、轮换或失效后的 UI 恢复
- 发布压缩包、安装器或自动更新可用

## 5. 验收结果

已执行：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n5_portable_runtime_smoke.py -q
```

结果：

```text
1 passed
```

已执行：

```powershell
.\python312\python.exe -m ruff check tests/integration/test_n5_portable_runtime_smoke.py
```

结果：

```text
All checks passed!
```

## 6. 明确不在 N.5 实现

N.5 不做：

- 不启动 Avalonia UI
- 不执行 `dotnet publish`
- 不生成发布压缩包
- 不创建 `start-enginehost.ps1`
- 不创建 `start-desktop.ps1`
- 不让 UI 托管 EngineHost
- 不创建安装器、后台服务、系统托盘或自动更新
- 不提交 `.tmp/` 生成物

## 7. 下一步建议

N.5 后建议进入 N.6：Avalonia `dotnet publish` 与 Desktop 产物 smoke。

N.6 建议保持小步：

- 先执行 Avalonia Release publish 到 `.tmp/FlowWeaverPortable/Desktop/`
- 验证 `Desktop/` 目录存在主程序和依赖文件
- 不要求自动启动 UI
- 不让 UI 启动后端
- 可先做文件级和命令级 smoke，再决定是否进入 UI API 客户端发布目录联调
