# FlowWeaver 阶段O.6：Desktop启动前置复核与策略确认

> 审核状态（2026-07-05）：已实现 / 桌面产品化后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：portable launcher、backend-only 入口、Desktop 入口、日志脱敏、失败清理、真实 Desktop smoke 和阶段 O 验收已经落地。
> 未实现：安装器、托盘、后台服务、自动更新和业务 UI 扩展未在 O 阶段实现。
> 原因：O 阶段只负责便携组合启动和生命周期，不扩大到产品化壳层。

> 文档状态：阶段O.6完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0-O.5文档
> 适用范围：便携 launcher 接入真实 Desktop 前的默认行为、生命周期策略、失败处理和自动化 smoke 边界
> 当前执行点：只做策略确认和边界复核，不修改 launcher 运行代码，不自动打开真实 `Avalonia_UI.exe`

## 1. 目标

O.6 的目标是进入 Desktop 自动启动前，先把启动策略和验收边界固定下来，避免在 O.7 直接实现时把窗口行为、EngineHost 生命周期和测试边界揉在一起。

本阶段完成：

- 复核 O.5 后的便携启动入口状态
- 确认 `start_flowweaver.cmd` 当前仍默认 backend-only
- 确认真实 Desktop 自动启动不在 O.6 实现
- 明确 Desktop 启动失败、正常退出、异常退出和用户中断时的 EngineHost 生命周期策略
- 明确 `--keep-enginehost-on-desktop-exit` 的后续语义
- 明确下一小步 O.7 的最小实现范围

本阶段不做：

- 不修改 `tools/portable_launcher.py`
- 不修改 `tools/create_portable_layout.py`
- 不修改 `start_flowweaver.cmd` 生成内容
- 不启动真实 `Avalonia_UI.exe`
- 不引入 UI 自动化或窗口截图
- 不实现安装器、托盘、后台服务或自动更新

## 2. 当前状态

O.5 后，便携目录生成器已经输出：

```text
FlowWeaverPortable/
  portable_launcher.py
  start_flowweaver.cmd
  EngineHost/
  Desktop/
  docs/README.txt
```

`start_flowweaver.cmd` 当前语义仍是：

```bat
"EngineHost\python312\python.exe" "portable_launcher.py" --no-desktop %*
```

因此当前默认入口行为是：

1. 启动 EngineHost
2. 等待 `/api/v1/health`
3. 等待本地 token
4. 输出 BaseUrl 和 token 文件路径
5. 等待用户中断
6. 退出时清理本次 EngineHost 子进程

当前不会自动启动 Desktop。

## 3. O.6策略结论

O.6 确认：短期默认入口继续保持 backend-only。

原因：

- O.4/O.5 已经验证 backend-only 路径稳定，应先保留一个可自动化、可诊断的入口
- 真实 Desktop 自动启动会打开窗口，自动化环境和本地交互体验需要单独处理
- Desktop 退出后是否关闭 EngineHost 是用户体验决策，不应在生成器接入时顺手决定
- 当前 `portable_launcher.py` 已有 Desktop plan 构造能力，但 `run_launch_plan()` 对 Desktop 仍明确拒绝，适合在后续小步单独打开

推荐后续策略：

| 入口 | 默认行为 | 说明 |
| --- | --- | --- |
| `start_flowweaver.cmd` | 暂时继续 `--no-desktop` | 保留稳定后端-only 入口 |
| `portable_launcher.py --no-desktop` | 后端-only | 自动化 smoke 主路径 |
| `portable_launcher.py` | 后续 O.7 才允许启动 Desktop | 当前仍拒绝 |
| 未来 Desktop 默认入口 | 待 O.7/O.8 决定 | 可以是修改 `.cmd`，也可以新增单独 cmd |

## 4. Desktop生命周期策略矩阵

后续真正接入 Desktop 时，建议使用以下策略：

| 场景 | 推荐 EngineHost 行为 | 推荐 launcher 退出码 | 备注 |
| --- | --- | --- | --- |
| EngineHost 启动失败 | 不启动 Desktop | `1` | 已符合当前 runtime error 路径 |
| health 超时 | 不启动 Desktop，停止 EngineHost | `1` | 保持当前 O.4 行为 |
| token 等待超时 | 不启动 Desktop，停止 EngineHost | `1` | 避免无 token UI 启动 |
| Desktop 文件缺失 | 不启动 EngineHost，配置错误退出 | `2` | 当前 layout 校验已具备基础 |
| Desktop 启动失败 | 停止本次 EngineHost | `1` | 不留下用户不可见后端进程 |
| Desktop 正常退出 | 默认停止本次 EngineHost | Desktop 退出码或 `0` | 第一版以用户关闭 UI 等于结束组合进程 |
| Desktop 异常退出 | 默认停止本次 EngineHost | Desktop 退出码或 `1` | 记录日志，避免静默保留后端 |
| 用户中断 launcher | 停止本次 EngineHost 和 Desktop | `130` | 保持 O.4 中断语义 |
| 显式 `--keep-enginehost-on-desktop-exit` | Desktop 退出后保留 EngineHost | Desktop 退出码或 `0` | 只对 Desktop 退出场景生效 |

## 5. `--keep-enginehost-on-desktop-exit` 语义

O.6 确认该参数后续只影响 Desktop 退出后的 EngineHost 处理。

建议语义：

- `false`：Desktop 退出后，launcher 停止本次启动的 EngineHost
- `true`：Desktop 退出后，launcher 不停止本次启动的 EngineHost
- 用户中断 launcher 时，即使该参数为 `true`，仍应停止 Desktop；EngineHost 是否保留需在 O.7 实现时明确测试
- EngineHost 启动失败、health 超时、token 超时不受该参数影响，仍应失败退出
- `--no-desktop` 模式下该参数不应改变当前 O.4 行为

O.7 实现前建议再补一条单元测试，确保 `--no-desktop --keep-enginehost-on-desktop-exit` 不会导致中断后留下 EngineHost。

## 6. 日志与脱敏边界

后续接入 Desktop 后，日志建议保持：

| 日志 | 内容边界 |
| --- | --- |
| `portable-launcher.log` | EngineHost 启动、ready、Desktop 启动、Desktop 退出、清理结果 |
| `enginehost.stdout.log` | EngineHost stdout |
| `enginehost.stderr.log` | EngineHost stderr |
| `desktop.stdout.log` | Desktop stdout，如果可捕获 |
| `desktop.stderr.log` | Desktop stderr，如果可捕获 |

必须继续满足：

- 不记录 token 原文
- 不记录完整 WebSocket URL token query
- 只输出 token 文件路径
- Desktop 启动命令若包含敏感参数，必须经过脱敏后写日志

当前推荐不通过命令行把 token 传给 Desktop；Desktop 仍由用户或连接配置输入 BaseUrl/token。

## 7. 自动化Smoke边界

O.6 确认：下一阶段不要马上做 UI 窗口自动化。

推荐 O.7 自动化只覆盖：

- `build_launch_plan()` 在 Desktop 存在时构造 Desktop spec
- Desktop 文件缺失时配置错误仍稳定
- Desktop 启动 helper 能启动一个可控假进程
- Desktop 正常退出时，launcher 清理 EngineHost
- Desktop 启动失败时，launcher 清理 EngineHost 并返回非 0
- `--no-desktop` O.4 smoke 不回退

真实 `Avalonia_UI.exe` 自动打开建议放到 O.8 或手工验收阶段。

## 8. 下一步建议

O.6 后建议进入 O.7：Desktop 启动 helper 与假 Desktop 进程验收。

O.7 最小范围建议：

- 在 `tools/portable_launcher.py` 增加 Desktop 启动 helper
- 增加 Desktop stdout/stderr 日志路径
- `run_launch_plan()` 支持 Desktop plan，但测试中使用假 Desktop 可执行文件
- 保持 `--no-desktop` 正式 smoke 不变
- 不修改 `start_flowweaver.cmd` 默认参数
- 不启动真实 Avalonia 窗口

O.7 通过后，再决定 O.8 是否把 `.cmd` 默认入口从 backend-only 改为组合启动，或新增单独的 `start_flowweaver_desktop.cmd`。
