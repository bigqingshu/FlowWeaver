# FlowWeaver 阶段O.9：独立Desktop启动入口生成

> 文档状态：阶段O.9完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.8文档
> 适用范围：便携目录独立 Desktop 启动入口、便携 README 和文件级 smoke
> 当前执行点：只生成入口文件并做文件级验收，不启动真实 `Avalonia_UI.exe`

## 1. 目标

O.9 的目标是在 O.8 已确认“双入口”策略后，让便携发布目录同时具备后端诊断入口和完整桌面组合入口。

本阶段完成：

- 保留 `start_flowweaver.cmd` 为 backend-only 入口
- 新增 `start_flowweaver_desktop.cmd` 作为 EngineHost + Desktop 组合入口
- 更新便携目录 `docs/README.txt`，同时说明两个入口和等价命令
- 更新 N.4 文件级 smoke，验证两个入口文件的生成和参数边界

本阶段不做：

- 不启动真实 `Desktop/Avalonia_UI.exe`
- 不做窗口交互、截图或 UI 自动化
- 不通过命令行向 Desktop 注入 token
- 不修改 Avalonia UI 项目
- 不改变 `portable_launcher.py` 的 Desktop 生命周期逻辑

## 2. 入口语义

便携目录现在包含两个 Windows 入口：

| 文件 | 行为 | 底层命令 |
| --- | --- | --- |
| `start_flowweaver.cmd` | 只启动 EngineHost | `EngineHost/python312/python.exe portable_launcher.py --no-desktop %*` |
| `start_flowweaver_desktop.cmd` | 启动 EngineHost + Desktop | `EngineHost/python312/python.exe portable_launcher.py %*` |

两个入口都支持透传 launcher 参数，例如：

```powershell
start_flowweaver.cmd --port 8000 --health-timeout-seconds 30
start_flowweaver_desktop.cmd --port 8000 --health-timeout-seconds 30
```

`start_flowweaver_desktop.cmd` 不包含 `--no-desktop`，因此会走 O.7 已具备的 Desktop plan。

## 3. 文件级验收

N.4 便携布局 smoke 已补充以下检查：

- `start_flowweaver.cmd` 存在，且包含 `--no-desktop`
- `start_flowweaver_desktop.cmd` 存在，且不包含 `--no-desktop`
- 便携 README 同时包含两个入口名称
- 便携 README 同时说明 backend-only 和 Desktop combo 等价命令

这仍然是文件级 smoke，不负责真实 Desktop 启动。

## 4. 当前边界

O.9 后，用户已经可以在便携目录中明确选择：

- 只启动后端：`start_flowweaver.cmd`
- 启动桌面组合：`start_flowweaver_desktop.cmd`

仍未完成：

- 自动化启动真实 `Desktop/Avalonia_UI.exe`
- 验证 Desktop 进程真实启动后 launcher 能清理 EngineHost
- 覆盖 Desktop 正常退出、异常退出和用户中断真实路径
- 汇总阶段 O 的最终验收矩阵

## 5. 测试命令

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_n4_portable_layout_smoke.py
.\python312\python.exe -m pytest -q tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_layout.py tests\integration\test_n4_portable_layout_smoke.py
git diff --check
```

结果：

```text
pytest N.4: passed
pytest O.4: passed
ruff: passed
git diff --check: passed
```

## 6. 下一步建议

O.9 后建议进入 O.10：真实 Desktop 最小 smoke。

O.10 应保持进程级验收，只验证真实 `Avalonia_UI.exe` 可以由 launcher 启动、EngineHost health 正常、日志生成、退出清理和 token 脱敏，不做窗口点击、截图、workflow 或 UI 内部自动化。
