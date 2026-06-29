# FlowWeaver 阶段O.11：Desktop生命周期真实路径收口

> 文档状态：阶段O.11完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.10文档
> 适用范围：便携 launcher 的 Desktop 缺失、Desktop 启动失败、EngineHost 清理和日志脱敏边界
> 当前执行点：只补真实生命周期失败路径验收，不做业务 UI 功能扩展

## 1. 目标

O.11 的目标是在 O.10 已验证真实 Desktop 可启动并可由 launcher 中断清理后，补齐 Desktop 生命周期中的失败路径。

本阶段完成：

- 新增 `tests/integration/test_o11_portable_launcher_desktop_failure_smoke.py`
- 覆盖 Desktop 缺失时 launcher 在启动 EngineHost 前拒绝
- 覆盖 Desktop 文件存在但不可执行时，launcher 启动 EngineHost 后在 Desktop 启动阶段失败
- 验证 Desktop 启动失败后本次 EngineHost 被停止
- 验证 `portable-launcher.log` 记录失败和清理结果
- 验证 stdout、stderr、launcher 日志、EngineHost 日志和 Desktop 日志不包含 token 原文

本阶段不做：

- 不打开真实 Avalonia 窗口
- 不点击 UI 或做截图
- 不通过命令行向 Desktop 注入 token
- 不改变 `start_flowweaver.cmd` 的 backend-only 行为
- 不扩展业务 UI、托盘、安装器、后台服务或自动更新

## 2. 生命周期边界

O.11 后，阶段 O 已覆盖以下生命周期路径：

| 路径 | 覆盖方式 | 结果 |
| --- | --- | --- |
| backend-only 用户中断 | O.4 端到端 smoke | EngineHost 停止 |
| Desktop 真实启动后用户中断 | O.10 真实 Desktop smoke | Desktop 和 EngineHost 停止 |
| Desktop 缺失 | O.11 集成 smoke | 启动前配置拒绝，不创建 runtime |
| Desktop 启动失败 | O.11 集成 smoke | EngineHost 被清理，日志脱敏 |
| Desktop 正常退出和 keep 策略 | O.7 假进程单元测试 | 默认停止 EngineHost，显式 keep 时保留 |

真实 Desktop 正常退出和 `--keep-enginehost-on-desktop-exit` 的全真实窗口路径需要 UI 自动化或人工关闭窗口。阶段 O.11 不引入窗口交互，因此继续由 O.7 假进程单元测试覆盖其策略语义。

## 3. 测试命令

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_o11_portable_launcher_desktop_failure_smoke.py
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py tests\integration\test_o4_portable_launcher_no_desktop_smoke.py tests\integration\test_o10_portable_launcher_desktop_smoke.py tests\integration\test_o11_portable_launcher_desktop_failure_smoke.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tests\unit\test_portable_launcher.py tests\integration\test_o10_portable_launcher_desktop_smoke.py tests\integration\test_o11_portable_launcher_desktop_failure_smoke.py
git diff --check
```

结果：

```text
pytest O.11: passed
pytest launcher unit + O.4 + O.10 default + O.11: passed
ruff: passed
git diff --check: passed
```

## 4. 下一步建议

O.11 后建议进入 O.12：阶段 O 总体验收复核。

O.12 只汇总 O.0-O.11 完成矩阵、入口说明、日志/进程/安全边界和明确不支持清单，不继续增加安装器、自动更新或业务 UI 能力。
