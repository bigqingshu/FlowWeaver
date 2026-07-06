# FlowWeaver 阶段O.10：真实Desktop最小Smoke

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.10完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.9文档
> 适用范围：便携 launcher 启动真实 `Desktop/Avalonia_UI.exe` 的最小进程级 smoke
> 当前执行点：只验证真实 Desktop 进程启动、EngineHost health、日志和退出清理，不做 UI 交互

## 1. 目标

O.10 的目标是在 O.9 已生成独立 Desktop 入口后，使用正式便携布局和真实 Avalonia 发布产物验证 launcher 的 Desktop 分支能跑通。

本阶段完成：

- 新增真实 Desktop smoke：`tests/integration/test_o10_portable_launcher_desktop_smoke.py`
- 测试生成临时便携目录并发布 `Avalonia_UI.exe`
- 使用便携 `EngineHost/python312/python.exe portable_launcher.py` 启动默认 Desktop 分支
- 验证 EngineHost health、鉴权 API、`Desktop pid=` 日志和 Desktop stdout/stderr 日志文件
- 通过中断 launcher 验证 Desktop 与 EngineHost 被清理
- 验证 launcher、EngineHost 和 Desktop 日志不包含 token 原文

本阶段不做：

- 不点击 UI
- 不做窗口截图或像素检查
- 不自动输入 BaseUrl/token
- 不运行 workflow
- 不通过命令行向 Desktop 注入 token
- 不改变 `start_flowweaver.cmd` 的 backend-only 行为

## 2. 测试保护边界

真实 Desktop smoke 会打开 Avalonia 窗口，因此默认跳过：

```text
FLOWWEAVER_RUN_DESKTOP_SMOKE != 1
```

显式运行时使用：

```powershell
$env:FLOWWEAVER_RUN_DESKTOP_SMOKE = "1"
.\python312\python.exe -m pytest -q tests\integration\test_o10_portable_launcher_desktop_smoke.py
Remove-Item Env:\FLOWWEAVER_RUN_DESKTOP_SMOKE
```

这保证普通 `pytest` 不会误打开桌面窗口。

## 3. 验收路径

O.10 smoke 路径：

1. 生成 `.tmp/FlowWeaverPortableDesktopTest-*`
2. 复制便携 EngineHost、`python312`、launcher 和启动包装
3. 发布 Avalonia Desktop 到便携 `Desktop/`
4. 启动 `portable_launcher.py` 默认 Desktop 分支
5. 等待 EngineHost `/api/v1/health`
6. 读取 token 并调用鉴权 `GET /api/v1/workflows`
7. 等待 `portable-launcher.log` 出现 `Desktop pid=`
8. 向 launcher 发送中断
9. 验证 health 不再可达
10. 验证 Desktop 进程退出
11. 验证日志存在且 token 脱敏

## 4. 当前边界

O.10 证明真实 Desktop 可以由 launcher 启动并被 launcher 清理。

仍未完成：

- Desktop 正常退出真实路径
- `--keep-enginehost-on-desktop-exit` 在真实 Desktop 路径下的保留策略
- Desktop 启动失败的真实路径补充验收
- 阶段 O 总体验收矩阵

这些留到 O.11 和 O.12。

## 5. 测试命令

已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_o10_portable_launcher_desktop_smoke.py
$env:FLOWWEAVER_RUN_DESKTOP_SMOKE = "1"; .\python312\python.exe -m pytest -q tests\integration\test_o10_portable_launcher_desktop_smoke.py; Remove-Item Env:\FLOWWEAVER_RUN_DESKTOP_SMOKE
.\python312\python.exe -m ruff check tests\integration\test_o10_portable_launcher_desktop_smoke.py
git diff --check
```

结果：

```text
pytest O.10 default: skipped
pytest O.10 real Desktop: passed
ruff: passed
git diff --check: passed
```

## 6. 下一步建议

O.10 后建议进入 O.11：Desktop 生命周期真实路径收口。

O.11 建议继续保持小步，只补真实路径生命周期验收，例如 Desktop 启动失败、用户中断清理和 `--keep-enginehost-on-desktop-exit` 的边界，不扩展业务 UI 功能。
