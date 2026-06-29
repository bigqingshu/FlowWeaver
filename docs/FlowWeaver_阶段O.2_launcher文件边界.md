# FlowWeaver 阶段O.2：launcher 文件边界

> 文档状态：阶段O.2完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N完成记录和阶段O.0/O.1文档
> 适用范围：`tools/portable_launcher.py` 的接口草案、纯 helper 边界和单元测试
> 当前执行点：只新增 launcher 文件骨架和可单测 helper，不接入生成器、不生成 `.cmd`、不启动真实 EngineHost 或 Desktop

## 1. 目标

O.2 的目标是把 O.1 中确认的 launcher 方案落成一个最小可测试文件边界，但不进入真实进程启动和便携目录生成器接入。

本阶段完成：

- 新增 `tools/portable_launcher.py`
- 新增 `tests/unit/test_portable_launcher.py`
- 固化 launcher 参数解析和校验边界
- 固化便携目录路径解析边界
- 固化 EngineHost / Desktop 启动命令构造边界
- 固化 token 读取和日志脱敏 helper
- README 更新到 O.2

本阶段不做：

- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/publish_desktop.py`
- 不把 launcher 复制到 `.tmp/FlowWeaverPortable/`
- 不新增 `start_flowweaver.cmd`
- 不启动真实 EngineHost
- 不启动真实 Desktop
- 不实现 health 轮询
- 不实现端口绑定检查
- 不实现进程生命周期清理

## 2. 新增文件边界

新增：

```text
tools/portable_launcher.py
tests/unit/test_portable_launcher.py
```

`tools/portable_launcher.py` 当前只提供计划层能力：

- `LauncherSettings`
- `PortableLayout`
- `EngineHostLaunchSpec`
- `DesktopLaunchSpec`
- `PortableLaunchPlan`
- `parse_launcher_args()`
- `resolve_portable_layout()`
- `validate_portable_layout()`
- `build_launch_plan()`
- `read_local_api_token()`
- `redact_sensitive_text()`

当前 `main()` 只验证计划并打印：

```text
FlowWeaver portable launcher plan is valid.
BaseUrl: ...
Process startup is implemented in a later stage.
```

这表示 O.2 还不是可用 launcher。

## 3. 参数边界

已支持的参数解析和校验：

| 参数 | 默认值 | 当前行为 |
| --- | --- | --- |
| `--host` | `127.0.0.1` | 只接受 `127.0.0.1` 或 `localhost` |
| `--port` | `8000` | 只接受 1 到 65535 |
| `--no-desktop` | `false` | 构造计划时允许缺少 Desktop |
| `--health-timeout-seconds` | `30` | 只接受大于等于 1 |
| `--keep-enginehost-on-desktop-exit` | `false` | 只进入 settings，不执行生命周期逻辑 |

暂未实现：

- 端口占用检查
- health 轮询
- `--port 0`
- 自动寻找空闲端口
- 接管已有 EngineHost

## 4. 便携目录边界

当前路径解析固定为：

```text
FlowWeaverPortable/
  EngineHost/python312/python.exe
  EngineHost/src/flowweaver/api/app.py
  EngineHost/runtime/logs/
  EngineHost/runtime/config/local_api_token
  Desktop/Avalonia_UI.exe
```

`validate_portable_layout()` 当前只做文件存在性检查：

- `EngineHost/python312/python.exe`
- `EngineHost/src/flowweaver/api/app.py`
- `Desktop/Avalonia_UI.exe`，除非 `--no-desktop`

暂未检查：

- `uvicorn` 是否可导入
- `alembic.ini` 是否存在
- migrations 是否完整
- Desktop 依赖 DLL 是否完整
- runtime 是否可写

这些留给 O.3/O.4 smoke。

## 5. 启动命令构造

当前 EngineHost 命令构造为：

```text
EngineHost/python312/python.exe
-m uvicorn
--app-dir src
flowweaver.api.app:create_default_app
--factory
--host <host>
--port <port>
```

并固定：

- `cwd = EngineHost/`
- stdout 日志路径：`EngineHost/runtime/logs/enginehost.stdout.log`
- stderr 日志路径：`EngineHost/runtime/logs/enginehost.stderr.log`

Desktop 命令构造为：

```text
Desktop/Avalonia_UI.exe
```

并固定：

- `cwd = Desktop/`

O.2 不执行这些命令。

## 6. token和脱敏边界

已新增：

- `read_local_api_token(token_path)`
- `redact_sensitive_text(text, token=None)`

当前语义：

- token 文件不存在时拒绝
- token 文件为空时拒绝
- token 返回前会 `strip()`
- `?token=...` / `&token=...` 会脱敏为 `token=***`
- 显式传入的 token 字符串会被替换为 `***`

O.2 不打印 token，不把 token 交给 UI。

## 7. 测试覆盖

新增测试覆盖：

- 默认参数
- 显式支持参数
- 非 loopback host 拒绝
- 非法 port 拒绝
- 非法 health timeout 拒绝
- 便携目录路径解析
- Desktop 默认必需
- `--no-desktop` 允许缺少 Desktop
- EngineHost / Desktop 启动命令构造
- token 文件读取和空文件拒绝
- token query 和 token 原文脱敏

测试命令：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_launcher.py
.\python312\python.exe -m ruff check tools\portable_launcher.py tests\unit\test_portable_launcher.py
```

## 8. 下一步建议

O.2 后建议进入 O.3：生成器接入前的真实启动最小层。

较稳的后续顺序：

| 小步 | 执行方向 | 主要产出 |
| --- | --- | --- |
| O.3 | launcher 真实启动层 | 在 `portable_launcher.py` 内补端口检查、EngineHost 启动、health 轮询、token 等待、日志写入；仍不接入生成器 |
| O.4 | `--no-desktop` launcher smoke | 使用临时便携目录复制 launcher，验证 health、token、日志和进程清理 |
| O.5 | 生成器接入 | `create_portable_layout.py` 复制 launcher，并生成 `start_flowweaver.cmd` |
| O.6 | Desktop 启动前置复核 | 决定是否允许自动打开窗口，或先保留手工验收 |

当前最推荐下一步是 O.3：补 launcher 真实启动层，但仍只走 `--no-desktop` 自动化路径。
