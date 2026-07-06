# FlowWeaver 阶段O.8：Desktop入口策略与真实Smoke前置决策

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.8完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.7文档
> 适用范围：便携 Desktop 入口策略、真实 Desktop smoke 前置决策和阶段O后续执行顺序
> 当前执行点：只做入口策略与真实 smoke 前置决策，不修改生成器或 launcher，不启动真实 `Avalonia_UI.exe`

## 1. 目标

O.8 的目标是在 O.7 已具备 Desktop helper 和假进程验收后，先确认真实 Desktop 接入的入口策略与 smoke 边界。

本阶段完成：

- 确认不直接修改 `start_flowweaver.cmd` 的 backend-only 默认行为
- 确认后续新增独立 `start_flowweaver_desktop.cmd`
- 确认真实 Desktop smoke 后置到独立小步
- 确认真实 Desktop smoke 第一版只验证进程启动、EngineHost health、日志和退出清理
- 确认不做窗口交互、截图、UI 自动化和 token 命令行注入
- 固化 O.9 到 O.12 的已知后续顺序

本阶段不做：

- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/portable_launcher.py`
- 不生成 `start_flowweaver_desktop.cmd`
- 不启动真实 `Desktop/Avalonia_UI.exe`
- 不修改 Avalonia UI 项目
- 不改连接配置、BaseUrl 或 token 交接方式

## 2. 当前前置状态

O.7 后，当前能力为：

| 能力 | 当前状态 |
| --- | --- |
| backend-only 入口 | `start_flowweaver.cmd` 固定调用 `portable_launcher.py --no-desktop %*` |
| launcher Desktop 分支 | 已支持 Desktop plan、Desktop helper 和假进程生命周期测试 |
| Desktop 发布产物 | N.6/N.7/N.8/N.9 已具备发布产物和客户端联调前置 smoke |
| 真实 Desktop 自动启动 | 尚未接入默认入口，也尚未自动化运行 |
| token 交接 | 仍只输出 token 文件路径，不通过命令行传给 Desktop |

## 3. O.8决策

O.8 确认采用“双入口”策略：

| 入口 | 保留/新增 | 默认行为 | 原因 |
| --- | --- | --- | --- |
| `start_flowweaver.cmd` | 保留 | backend-only | 保留 O.4/O.5 已验证的稳定诊断入口 |
| `start_flowweaver_desktop.cmd` | 后续 O.9 新增 | EngineHost + Desktop | 将真实 UI 启动风险隔离到独立入口 |
| `portable_launcher.py --no-desktop` | 保留 | backend-only | 自动化 smoke 主路径 |
| `portable_launcher.py` | 已具备 Desktop plan | EngineHost + Desktop | 作为 Desktop 入口的底层命令 |

不建议直接把 `start_flowweaver.cmd` 改为 Desktop 默认入口。

原因：

- backend-only smoke 是当前最稳定的便携诊断入口
- 真实 Desktop 会打开窗口，可能影响自动化和本地调试
- 双入口可以让用户显式选择“只启动后端”或“启动完整桌面组合”
- 后续如果 Desktop 入口稳定，再决定是否调整默认入口

## 4. `start_flowweaver_desktop.cmd`建议语义

后续 O.9 建议生成：

```bat
@echo off
setlocal
cd /d "%~dp0"
"EngineHost\python312\python.exe" "portable_launcher.py" %*
exit /b %ERRORLEVEL%
```

注意：

- 不带 `--no-desktop`
- 支持透传 `--port`、`--health-timeout-seconds`、`--keep-enginehost-on-desktop-exit`
- 不透传 token
- 不自动修改 UI 连接配置
- 不改变 `start_flowweaver.cmd`

## 5. 真实Desktop Smoke边界

真实 Desktop smoke 后置到 O.10，第一版建议只验证：

1. 生成便携目录
2. 确认 `Desktop/Avalonia_UI.exe` 存在
3. 使用便携 Python 启动 `portable_launcher.py`
4. 等待 EngineHost health
5. 等待 launcher 记录 Desktop started 或可观测到 Desktop 进程启动
6. 结束 launcher
7. 验证 EngineHost health 不再可达
8. 验证 `portable-launcher.log`、`enginehost.*.log`、`desktop.*.log` 存在
9. 验证日志不包含 token 原文

真实 Desktop smoke 第一版不做：

- 不点击 UI
- 不做窗口截图
- 不检查窗口像素
- 不自动输入 BaseUrl/token
- 不运行 workflow
- 不将 token 注入 Desktop 命令行

## 6. 风险与缓解

| 风险 | 缓解 |
| --- | --- |
| 真实 Desktop 打开窗口影响开发者 | O.10 单独执行，并保持 O.4 backend-only smoke 可用 |
| CI 或无桌面环境不稳定 | 真实 Desktop smoke 可先保持本地/手工或带环境条件跳过 |
| Desktop 启动后无法自动退出 | O.10 只验证进程启动和 launcher 清理，不做 UI 内部关闭 |
| Desktop 未自动获得 token | 第一阶段不通过命令行注入 token，保持用户输入/配置路径 |
| 默认入口行为突变 | 保留 `start_flowweaver.cmd` backend-only |

## 7. 后续已知阶段

| 阶段 | 目标 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| O.9 | 独立 Desktop 启动入口生成 | 生成 `start_flowweaver_desktop.cmd`，更新 README.txt 和 N.4 文件级测试 | 不启动真实 Desktop |
| O.10 | 真实 Desktop 最小 smoke | 运行真实 `Avalonia_UI.exe` 的最小进程级 smoke | 不做窗口交互、截图、workflow |
| O.11 | Desktop 生命周期真实路径收口 | 覆盖正常退出、异常退出、用户中断和 keep EngineHost 策略 | 不改业务 UI 功能 |
| O.12 | 阶段O总体验收复核 | 汇总 O.0-O.11 完成矩阵、入口说明、日志/进程/安全边界和不支持清单 | 不扩展安装器或自动更新 |

## 8. O.9建议范围

O.9 建议作为最小代码小步：

- 修改 `tools/create_portable_layout.py`
- 新增 `_write_start_desktop_cmd()`
- 生成 `start_flowweaver_desktop.cmd`
- 更新便携 `docs/README.txt`
- 更新 `tests/integration/test_n4_portable_layout_smoke.py`
- 不启动真实 Desktop
- 不修改 `start_flowweaver.cmd`

推荐验证：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_n4_portable_layout_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_layout.py tests\integration\test_n4_portable_layout_smoke.py
git diff --check
```

## 9. 本阶段验证

O.8 为文档/策略小步，验证不打开真实 Desktop。

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m pytest -q tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tools\create_portable_layout.py tests\unit\test_portable_launcher.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
git diff --check
```

结果：

```text
pytest launcher unit: passed
pytest N.4 + O.4: passed
ruff: passed
git diff --check: passed
```

## 10. 下一步建议

O.8 后建议进入 O.9：独立 Desktop 启动入口生成。

最稳路径是先只生成和测试 `start_flowweaver_desktop.cmd` 文件边界，继续保留真实 Desktop smoke 到 O.10。
