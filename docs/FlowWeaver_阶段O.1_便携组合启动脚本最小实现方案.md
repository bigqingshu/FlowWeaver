# FlowWeaver 阶段O.1：便携组合启动脚本最小实现方案

> 文档状态：阶段O.1最小实现方案完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和 `FlowWeaver_阶段O.0_便携组合启动脚本边界分析.md`
> 适用范围：后续便携组合启动脚本的最小实现形态、参数、生成位置、生命周期和 smoke 方式
> 当前执行点：只做实现方案确认，不新增 launcher 脚本、不修改生成器、不修改 EngineHost 或 Avalonia 产品代码

## 1. 目标

O.1 的目标是把 O.0 中提出的组合启动脚本边界转成最小可实现方案，明确下一步代码实现时的文件形态、参数集合、生成位置和验收方式。

本阶段确认：

- launcher 采用什么语言和包装形式
- launcher 放在仓库哪里、生成到便携目录哪里
- 第一版支持哪些参数
- 第一版如何启动 EngineHost 和 Desktop
- 第一版如何处理 BaseUrl、token、日志和脱敏
- 第一版如何处理进程退出
- 第一版 smoke 测试怎么做

本阶段不做：

- 不新增 `portable_launcher.py`
- 不新增 `start_flowweaver.cmd`
- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/publish_desktop.py`
- 不修改 Avalonia UI 命令行参数
- 不实现 token 自动注入 UI
- 不实现安装器、系统托盘、后台服务或自动更新

## 2. 实现形态选择

第一版建议采用：

```text
Python launcher 核心 + Windows cmd 包装
```

建议文件形态：

| 文件 | 仓库位置 | 便携目录位置 | 作用 |
| --- | --- | --- | --- |
| `portable_launcher.py` | `tools/portable_launcher.py` | `FlowWeaverPortable/portable_launcher.py` | 跨平台核心启动逻辑 |
| `start_flowweaver.cmd` | 由生成器写入或模板复制 | `FlowWeaverPortable/start_flowweaver.cmd` | Windows 双击入口 |

选择理由：

- 当前便携目录已经包含 `EngineHost/python312/python.exe`
- Python 更适合实现 health 轮询、日志写入、进程清理和 smoke 测试
- `.cmd` 只负责调用 `EngineHost\python312\python.exe portable_launcher.py`
- 避免第一版在 PowerShell 执行策略、编码和窗口生命周期上承担过多风险

暂不采用：

- 纯 PowerShell 脚本作为唯一实现
- Avalonia UI 内部托管 EngineHost
- 后台 Windows Service
- 系统托盘常驻管理器

## 3. 生成位置与目录关系

后续实现时，`tools/create_portable_layout.py` 应负责把 launcher 文件复制或写入便携根目录。

建议生成后的结构：

```text
FlowWeaverPortable/
  portable_launcher.py
  start_flowweaver.cmd
  EngineHost/
    python312/python.exe
    src/
    runtime/
  Desktop/
    Avalonia_UI.exe
```

关键边界：

- launcher 的运行根目录是 `FlowWeaverPortable/`
- EngineHost 的工作目录仍是 `FlowWeaverPortable/EngineHost/`
- Desktop 的执行文件仍是 `FlowWeaverPortable/Desktop/Avalonia_UI.exe`
- launcher 不应依赖仓库源码路径
- launcher 不应从 repo 根目录读取配置或模块

## 4. 第一版参数集合

第一版建议支持：

| 参数 | 默认值 | 说明 |
| --- | --- | --- |
| `--host` | `127.0.0.1` | 只允许 loopback，第一版不支持外网监听 |
| `--port` | `8000` | 固定默认端口，占用即拒绝 |
| `--no-desktop` | `false` | 只启动 EngineHost，用于 smoke 和调试 |
| `--health-timeout-seconds` | `30` | 等待 health 的超时时间 |
| `--keep-enginehost-on-desktop-exit` | `false` | 默认 Desktop 退出后停止本次启动的 EngineHost |

第一版不支持：

- `--port 0` 随机端口
- 自动寻找空闲端口
- 自动接管已有 EngineHost
- 自动填入 UI token
- 后台 daemon 模式
- 多实例并存

显式非法值处理：

- `--host` 不是 `127.0.0.1` 或 `localhost` 时拒绝
- `--port` 不是 1 到 65535 的整数时拒绝
- `--health-timeout-seconds` 小于 1 时拒绝
- 找不到 EngineHost 或 Desktop 必需文件时拒绝

## 5. 启动流程

建议最小启动流程：

1. 解析参数
2. 定位 `FlowWeaverPortable/` 根目录
3. 验证 `EngineHost/python312/python.exe`
4. 验证 `EngineHost/src/flowweaver/api/app.py`
5. 在 `EngineHost/runtime/logs/` 创建日志目录
6. 检查目标端口是否可绑定
7. 启动 EngineHost 子进程
8. 轮询 `/api/v1/health`
9. 等待并读取 `EngineHost/runtime/config/local_api_token`
10. 写入 launcher 脱敏日志
11. 如果未指定 `--no-desktop`，启动 `Desktop/Avalonia_UI.exe`
12. 等待 Desktop 退出或等待用户中断
13. 按策略停止本次启动的 EngineHost

EngineHost 命令：

```powershell
EngineHost\python312\python.exe -m uvicorn --app-dir EngineHost\src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

实际实现中：

- `cwd` 必须设置为 `EngineHost/`
- 命令参数中的 `--app-dir` 应使用相对 `cwd` 的 `src` 或绝对路径
- stdout/stderr 必须重定向到日志文件
- 不注入 repo `PYTHONPATH`

## 6. token与BaseUrl策略

第一版不自动把 token 注入 UI。

launcher 输出策略：

```text
EngineHost ready.
BaseUrl: http://127.0.0.1:8000
Token file: EngineHost/runtime/config/local_api_token
Desktop: started
```

日志策略：

- `portable-launcher.log` 可以记录 token 文件路径
- `portable-launcher.log` 不记录 token 原文
- 控制台不打印 token 原文
- 如果未来记录 WebSocket URL，必须脱敏 query

UI 交接策略：

- 第一版只启动 Desktop
- BaseUrl 可由用户在 UI 中确认或输入
- token 由用户从 token 文件复制到 UI
- 不改变现有“BaseUrl 可持久化、token 默认不落盘”的 UI 策略

## 7. 日志文件

建议日志路径：

| 文件 | 内容 |
| --- | --- |
| `EngineHost/runtime/logs/enginehost.stdout.log` | uvicorn stdout |
| `EngineHost/runtime/logs/enginehost.stderr.log` | uvicorn stderr 和 traceback |
| `EngineHost/runtime/logs/portable-launcher.log` | launcher 步骤、BaseUrl、pid、失败原因 |

日志写入要求：

- UTF-8
- 每次启动追加或轮转二选一，第一版建议追加
- 明确记录本次 EngineHost pid
- 启动失败时记录最后一次 health 错误摘要
- 不记录 token 原文

## 8. 生命周期策略

第一版生命周期建议：

| 场景 | 行为 |
| --- | --- |
| EngineHost 启动失败 | 不启动 Desktop，退出非 0 |
| health 超时 | 停止本次 EngineHost，退出非 0 |
| token 文件缺失或为空 | 停止本次 EngineHost，退出非 0 |
| `--no-desktop` | health 和 token 就绪后保持 EngineHost 运行，直到用户中断 |
| Desktop 正常退出 | 默认停止本次 EngineHost |
| 用户 Ctrl+C | 停止本次 EngineHost |
| `--keep-enginehost-on-desktop-exit` | Desktop 退出后保留本次 EngineHost |

关键约束：

- launcher 只停止自己启动的 EngineHost
- launcher 不杀死端口上已有但非本次启动的进程
- launcher 不接管旧 EngineHost
- launcher 不判断运行中 workflow 是否可以被安全中断；这类能力留给后续阶段

## 9. smoke测试方案

第一版 smoke 建议使用 Python 集成测试，而不是 PowerShell 手工验收。

建议新增：

```text
tests/integration/test_o3_portable_launcher_smoke.py
```

测试前提：

- 先由 `tools/create_portable_layout.py --no-desktop-build` 生成独立临时便携目录
- 再由 `tools/publish_desktop.py --output <portable>/Desktop` 发布 Desktop
- 后续生成器会把 launcher 写入便携根目录

最小 smoke 建议先使用 `--no-desktop`：

1. 从便携根目录启动 `EngineHost/python312/python.exe portable_launcher.py --port <free_port> --no-desktop`
2. 等待 launcher 输出 health ready
3. 验证 `/api/v1/health`
4. 验证 `EngineHost/runtime/config/local_api_token`
5. 验证三类日志文件存在
6. 验证日志不包含 token 原文
7. 停止 launcher 进程
8. 验证本次 EngineHost 子进程退出

Desktop 进程启动 smoke 建议后置到 O.4：

- 因为启动真实 `Avalonia_UI.exe` 可能打开窗口
- CI 或无桌面环境可能不稳定
- 第一版可用手工验收清单或仅验证 `--no-desktop` 自动化

## 10. 与生成器的关系

后续实现建议分两步：

1. 先新增 `tools/portable_launcher.py` 和单元级 helper 测试
2. 再修改 `tools/create_portable_layout.py`，把 launcher 和 `.cmd` 复制到输出目录

生成器新增验收：

- 生成目录包含 `portable_launcher.py`
- Windows 生成目录包含 `start_flowweaver.cmd`
- `docs/README.txt` 更新启动说明
- 现有 N.4/N.5/N.6 smoke 不回退

## 11. 第一版不做事项

O.1 明确第一版 launcher 不做：

- 不做安装器
- 不做压缩包生成
- 不做系统托盘
- 不做后台服务
- 不做自动更新
- 不做 UI 托管 EngineHost
- 不做 token 自动注入 UI
- 不做 UI 命令行参数接入
- 不做随机端口
- 不做多实例接管
- 不做运行中 workflow 安全退出判断
- 不做可视化窗口自动化

## 12. 下一步执行建议

O.1 后建议进入 O.2：生成器改造前的 launcher 文件边界。

更稳的后续顺序：

| 小步 | 执行方向 | 主要产出 |
| --- | --- | --- |
| O.2 | launcher 文件边界 | 新增 `tools/portable_launcher.py` 的接口草案和可单测 helper，不接入生成器 |
| O.3 | 生成器接入 | `create_portable_layout.py` 复制 launcher 和 `.cmd` 到便携根目录 |
| O.4 | `--no-desktop` 自动化 smoke | 验证 health、token、日志和进程清理 |
| O.5 | Desktop 启动手工/前置 smoke | 明确是否允许自动打开窗口，决定是否引入 UI 自动化 |

当前最推荐的下一步是 O.2：先实现 launcher 核心文件和可测试 helper，但不马上接入生成器。
