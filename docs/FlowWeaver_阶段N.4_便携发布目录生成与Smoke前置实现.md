# FlowWeaver 阶段N.4：便携发布目录生成与 Smoke 前置实现

> 文档状态：阶段N.4完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0/N.1/N.2/N.3完成记录
> 适用范围：`.tmp/FlowWeaverPortable/` 便携目录生成、后端工作目录、Alembic、runtime、token 和 health 最小 smoke
> 当前执行点：生成测试目录和最小 smoke，不创建安装器、不提交生成物、不改变正式入口

## 1. 目标

N.4 的目标是把 N.3 的便携版双进程布局从“文档设计”推进到“可重复生成的测试目录”，并验证后端能在生成出的 `EngineHost/` 工作目录下完成最小启动链路。

本阶段只验证：

- 便携目录可以生成到 `.tmp/FlowWeaverPortable/`
- 生成目录包含后端运行所需的 `src/`、`migrations/`、`alembic.ini`
- 默认命令可复制仓内 `python312/`
- 后端从生成目录的 `EngineHost/` 作为工作目录启动
- Alembic 可在该工作目录解析迁移脚本
- `runtime/`、SQLite 元数据库、token 和运行子目录可自动生成
- `health` 和带 token 的最小只读 API 可用

## 2. 本阶段修改清单

- 新增 `tools/create_portable_layout.py`
- 新增 `tests/integration/test_n4_portable_layout_smoke.py`
- 更新 `.gitignore`，忽略 `.tmp/`
- 更新 README 当前阶段和下一步建议

本阶段生成物：

- `.tmp/FlowWeaverPortable/`

该生成物不提交。

## 3. 便携目录生成器

新增命令：

```powershell
.\python312\python.exe tools\create_portable_layout.py --no-desktop-build
```

默认输出：

```text
.tmp/FlowWeaverPortable/
```

默认生成结构：

```text
.tmp/FlowWeaverPortable/
  EngineHost/
    python312/
    src/
    migrations/
    alembic.ini
    pyproject.toml
    uv.lock
  Desktop/
  docs/
    README.txt
```

生成器默认：

- 清理并重建目标输出目录
- 复制 `alembic.ini`
- 复制 `pyproject.toml`
- 复制 `uv.lock`
- 复制 `migrations/`
- 复制 `src/`
- 复制 `python312/`
- 如果存在 Avalonia build 输出，可复制到 `Desktop/`
- 写入最小发布说明 `docs/README.txt`

安全边界：

- 输出目录必须是仓库 `.tmp/` 的子目录
- 不允许把 `.tmp/` 本身作为输出目录
- 不删除仓库源码、`runtime/`、`python312/` 或用户目录
- 不打印 token
- 不启动 EngineHost
- 不创建安装器

## 4. 测试策略

新增测试：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n4_portable_layout_smoke.py -q
```

测试执行：

1. 在 `.tmp/FlowWeaverPortableTest-*` 下生成便携目录
2. 为了保持测试速度，不复制 900MB 级别的 `python312/`
3. 从生成目录的 `EngineHost/` 作为工作目录启动 EngineHost
4. 使用动态空闲端口，避免占用 `8000`
5. 验证 `/api/v1/health`
6. 验证 `runtime/metadata/flowweaver.db`
7. 验证 `runtime/config/local_api_token`
8. 验证 `runtime/workflow_runs/`、`runtime/logs/`、`runtime/temp/`
9. 使用 token 查询 `/api/v1/workflows`
10. 停止 EngineHost 并清理测试目录

测试刻意不覆盖：

- Avalonia UI 发布产物启动
- `dotnet publish`
- 完整 workflow run
- WebSocket 事件
- 复制完整 `python312/` 的耗时路径
- 安装器或组合启动脚本

## 5. 验收结果

已执行：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n4_portable_layout_smoke.py -q
```

结果：

```text
1 passed
```

已执行默认生成命令：

```powershell
.\python312\python.exe tools\create_portable_layout.py --no-desktop-build
```

结果：

```text
D:\bigqingshu_project\FlowWeaver\.tmp\FlowWeaverPortable
```

已确认生成目录包含：

- `.tmp/FlowWeaverPortable/EngineHost/python312/python.exe`
- `.tmp/FlowWeaverPortable/EngineHost/src/flowweaver/api/app.py`
- `.tmp/FlowWeaverPortable/EngineHost/migrations/env.py`
- `.tmp/FlowWeaverPortable/EngineHost/alembic.ini`

## 6. 明确不在 N.4 实现

N.4 不做：

- 不提交 `.tmp/FlowWeaverPortable/`
- 不执行 `dotnet publish`
- 不生成真实发布压缩包
- 不创建安装器
- 不创建后台服务
- 不创建系统托盘
- 不创建自动更新
- 不新增 `start-enginehost.ps1`
- 不新增 `start-desktop.ps1`
- 不改变 Avalonia UI 对 EngineHost 的连接职责
- 不改变 EngineHost 默认入口

## 7. 当前缺口

N.4 后仍未完成：

- Avalonia UI 正式 `dotnet publish` 配置和产物复制验收
- 完整 `python312/` 复制后的端到端后端启动 smoke
- 发布目录中的 EngineHost stdout/stderr 日志归档
- 发布目录运行完整 workflow / table / shared / audit 链路
- 发布目录 WebSocket 重连 smoke
- token 缺失、轮换或失效后的 UI 恢复 smoke
- 组合启动脚本和进程所有权实现

## 8. 下一步建议

N.4 后建议进入 N.5：便携目录后端完整 runtime smoke。

N.5 建议保持小步：

- 使用 `.tmp/FlowWeaverPortable/EngineHost/python312/python.exe`
- 从 `.tmp/FlowWeaverPortable/EngineHost/` 启动 EngineHost
- 验证 health、token、workflow 创建、run、NodeRun、RuntimeEvent REST、TableRef、SharedPublication 和 AuditEvent
- 不启动 Avalonia UI
- 不创建安装器

完成 N.5 后，再进入 Avalonia `dotnet publish` 与 `Desktop/` 产物 smoke。
