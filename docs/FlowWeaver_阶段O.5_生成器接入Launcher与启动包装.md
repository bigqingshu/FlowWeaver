# FlowWeaver 阶段O.5：生成器接入Launcher与启动包装

> 文档状态：阶段O.5完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.4文档
> 适用范围：`tools/create_portable_layout.py` 生成便携根目录 launcher、Windows 启动包装和便携 README 启动说明
> 当前执行点：只接入生成器产物，不启动真实 Desktop，不改变 launcher 的 `--no-desktop` smoke 边界

## 1. 目标

O.5 的目标是把 O.4 已验证的 `portable_launcher.py --no-desktop` 正式接入便携目录生成器。

本阶段完成：

- `tools/create_portable_layout.py` 自动复制 `tools/portable_launcher.py` 到便携根目录
- 生成便携根目录 `start_flowweaver.cmd`
- 更新便携目录 `docs/README.txt` 启动说明
- N.4 便携目录 smoke 验证 launcher / cmd / README 文件边界
- O.4 端到端 smoke 改为直接使用生成器自带 launcher，不再手工复制

本阶段不做：

- 不启动真实 `Avalonia_UI.exe`
- 不让 `.cmd` 自动打开 Desktop
- 不改变 `portable_launcher.py` 的 Desktop 拒绝边界
- 不增加安装器、压缩包、托盘、后台服务或自动更新
- 不引入随机端口、多实例接管或 UI 参数注入

## 2. 生成目录变化

生成后的便携根目录新增：

```text
FlowWeaverPortable/
  portable_launcher.py
  start_flowweaver.cmd
  EngineHost/
  Desktop/
  docs/
    README.txt
```

`portable_launcher.py` 来源：

```text
tools/portable_launcher.py
```

`start_flowweaver.cmd` 当前内容语义：

```bat
cd /d "%~dp0"
"EngineHost\python312\python.exe" "portable_launcher.py" --no-desktop %*
```

因此双击或执行 `start_flowweaver.cmd` 的第一版行为仍是后端-only：

- 启动 EngineHost
- 等待 health
- 输出 BaseUrl 和 token 文件路径
- 不输出 token 原文
- 不启动 Desktop
- Ctrl+C / Break 时由 launcher 清理本次 EngineHost 子进程

## 3. README.txt 启动说明

便携目录 `docs/README.txt` 已更新为当前可用入口：

- Windows 后端-only 启动：`start_flowweaver.cmd`
- 等价命令：`EngineHost/python312/python.exe portable_launcher.py --no-desktop`
- 参数透传示例：`start_flowweaver.cmd --port 8000 --health-timeout-seconds 30`
- 明确当前便携 launcher 尚不自动启动 Desktop
- 说明 token 与日志路径

该说明仍避免写入或展示 token 原文。

## 4. 测试调整

N.4 便携目录 smoke 新增检查：

- 生成目录包含 `portable_launcher.py`
- 生成目录包含 `start_flowweaver.cmd`
- `docs/README.txt` 包含 `start_flowweaver.cmd`
- `docs/README.txt` 包含 `portable_launcher.py --no-desktop`
- `start_flowweaver.cmd` 包含 `portable_launcher.py`
- `start_flowweaver.cmd` 包含 `--no-desktop`

O.4 端到端 smoke 调整：

- 不再手工复制 `tools/portable_launcher.py`
- 直接使用 `tools/create_portable_layout.py` 生成出的 `portable_launcher.py`
- 继续验证 health、token、鉴权 API、日志脱敏和进程清理

## 5. 当前边界

O.5 后，便携生成器已经具备“可运行后端-only launcher”的目录产物。

仍未完成：

- Desktop 自动启动
- Desktop 退出后是否保留或关闭 EngineHost 的联动策略
- Desktop 启动失败时的用户可见错误体验
- `start_flowweaver.cmd` 的窗口标题、暂停策略或可视化提示优化
- 发布压缩包或安装包

这些应留到 O.6 或后续阶段单独收口。

## 6. 测试覆盖

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m ruff check tools\create_portable_layout.py tools\portable_launcher.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\unit\test_portable_launcher.py
git diff --check
```

结果：

```text
pytest N.4 + O.4: 2 passed
pytest launcher unit: 24 passed
ruff: All checks passed
git diff --check: passed
```

## 7. 下一步建议

O.5 后建议进入 O.6：Desktop 启动前置复核与策略确认。

O.6 建议先分析并确认：

- `start_flowweaver.cmd` 是否仍默认后端-only，还是改为默认启动 Desktop
- Desktop 启动失败时是否保留 EngineHost
- Desktop 退出时是否默认关闭 EngineHost
- `--keep-enginehost-on-desktop-exit` 在真实 Desktop 接入后的语义
- 自动化 smoke 是否只验证进程启动，不做窗口交互

建议 O.6 先做文档和最小前置测试，不直接打开真实 UI 窗口。
