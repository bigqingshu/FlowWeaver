# FlowWeaver 便携版用户手册

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：便携版用户手册已形成，并在发布 layout / archive 链路中作为 docs 入口被复制和 smoke 覆盖。
> 未实现：手册中列明的不支持项，如安装器、自动更新、后台服务、系统托盘、代码签名和 self-contained Desktop，仍未实现。
> 原因：这些是不支持能力说明，不是当前手册目标内的缺口。

> 文档状态：P.6 内容收口完成
> 适用版本：FlowWeaver Portable `win-x64`
> 当前发布形态：便携 zip，Desktop 为 framework-dependent

## 1. 快速开始

1. 将 `FlowWeaverPortable-<version>-win-x64.zip` 解压到一个普通用户可写目录。
2. 不要直接在压缩包预览窗口中运行程序，必须先完整解压。
3. 双击 `start_flowweaver_desktop.cmd` 启动 EngineHost 和 Desktop。
4. 等待控制台出现 `EngineHost ready.`。
5. 默认 BaseUrl 为 `http://127.0.0.1:8000`。
6. token 文件位于 `EngineHost/runtime/config/local_api_token`。
7. 在 Desktop 顶部连接区填写 BaseUrl 和 token，点击连接检查。

如果只需要启动后端或排查问题，双击 `start_flowweaver.cmd`。这个入口只启动 EngineHost，不启动 Desktop。

推荐解压位置示例：

```text
D:\Tools\FlowWeaverPortable\
```

避免解压到需要管理员权限的目录，例如 `C:\Program Files\`。路径可以包含空格或中文，但排查问题时，优先使用较短、用户可写的目录。

## 2. 运行要求

FlowWeaver 便携版当前面向 Windows `win-x64`。

后端运行要求：

- 后端使用发布包内的 `EngineHost/python312/python.exe`
- 不需要把 Python 加入系统 PATH
- 不需要安装系统级 Python

Desktop 运行要求：

- Desktop 当前为 framework-dependent
- Desktop 不是 self-contained
- 使用 Desktop 时，目标机器需要可运行 .NET 10.0 Desktop Runtime

如果只使用 `start_flowweaver.cmd` 的 backend-only 模式，Desktop Runtime 缺失不会影响 EngineHost 启动。使用 `start_flowweaver_desktop.cmd` 时，如果 Desktop 无法启动，先检查 .NET Desktop Runtime 是否可用。

可选检查：

```powershell
dotnet --list-runtimes
```

如果系统没有 `dotnet` 命令，但 Desktop 仍能正常启动，可以不处理；该命令只用于诊断。

## 3. 发布包结构

解压后的主要结构：

```text
FlowWeaverPortable/
  EngineHost/
    python312/
    src/
    migrations/
    runtime/
  Desktop/
  docs/
  licenses/
  release-manifest.json
  portable_launcher.py
  start_flowweaver.cmd
  start_flowweaver_desktop.cmd
```

常用路径：

| 路径 | 用途 |
| --- | --- |
| `start_flowweaver.cmd` | 后端-only 启动入口 |
| `start_flowweaver_desktop.cmd` | EngineHost + Desktop 组合启动入口 |
| `EngineHost/python312/python.exe` | 便携 Python |
| `EngineHost/runtime/` | 本机运行数据、token、数据库、日志 |
| `EngineHost/runtime/config/local_api_token` | 本地 API token |
| `EngineHost/runtime/logs/` | launcher、EngineHost 和 Desktop 日志 |
| `Desktop/` | Avalonia Desktop 发布产物 |
| `release-manifest.json` | 发布包清单 |
| `licenses/` | FlowWeaver、Python 和第三方包许可证摘要 |

`release-manifest.json` 用于记录版本、目标 runtime、文件 SHA-256、runtime audit 状态和许可证摘要。zip 外部的 `.sha256` 文件用于校验整个 zip 是否完整。

## 4. 启动方式

### 4.1 后端-only

双击：

```text
start_flowweaver.cmd
```

等价命令：

```powershell
EngineHost\python312\python.exe portable_launcher.py --no-desktop
```

用途：

- 后端诊断
- 只使用 HTTP API
- 自动化 smoke
- 排查 Desktop 无法启动的问题

停止方式：

- 在控制台按 `Ctrl+C`
- 等待日志出现 `EngineHost stopped`

### 4.2 Desktop 组合启动

双击：

```text
start_flowweaver_desktop.cmd
```

等价命令：

```powershell
EngineHost\python312\python.exe portable_launcher.py
```

用途：

- 普通桌面使用
- 同时启动 EngineHost 和 Desktop

默认行为：

- launcher 先启动 EngineHost
- health 检查通过后等待 token 文件
- 再启动 Desktop
- Desktop 退出后，launcher 默认停止本次 EngineHost

### 4.3 常用参数

自定义端口：

```powershell
start_flowweaver.cmd --port 8010
start_flowweaver_desktop.cmd --port 8010
```

延长启动等待时间：

```powershell
start_flowweaver_desktop.cmd --health-timeout-seconds 60
```

关闭 Desktop 后保留 EngineHost：

```powershell
start_flowweaver_desktop.cmd --keep-enginehost-on-desktop-exit
```

launcher 只允许 loopback 主机，默认是 `127.0.0.1`。不要把 EngineHost 暴露到局域网或公网。

## 5. 重要警示：关闭 Desktop 与运行中 workflow

`start_flowweaver_desktop.cmd` 会由 launcher 同时管理 Desktop 和本次 EngineHost。

重要边界：

| 场景 | 影响 |
| --- | --- |
| 直接关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop | launcher 默认停止本次 EngineHost，运行中 workflow 可能中断 |
| 使用 `start_flowweaver_desktop.cmd --keep-enginehost-on-desktop-exit` | Desktop 退出后保留本次 EngineHost，运行中 workflow 可继续由后端执行 |
| 先用 `start_flowweaver.cmd` 启动后端，再单独启动 Desktop | 关闭 Desktop 只关闭客户端，不直接停止 backend-only EngineHost |

安全退出建议：

1. 先在 Desktop 中确认 workflow run 已结束、已取消或可以接受中断。
2. 如果有运行中的 workflow，不要直接关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop。
3. 想关闭界面但保留后端时，使用 `--keep-enginehost-on-desktop-exit`。
4. 如果不确定后端是否还在运行，访问 `http://127.0.0.1:8000/api/v1/health` 或查看控制台/日志。

误关闭后的检查：

- 重新启动 EngineHost
- 用相同 BaseUrl 和当前 token 连接 Desktop
- 查看运行列表、节点状态和 RuntimeEvent 日志
- 对于已中断的 workflow，按当前 UI 支持能力重新启动或重新执行

## 6. Token 与连接

EngineHost 首次启动后会生成本地 API token：

```text
EngineHost/runtime/config/local_api_token
```

Desktop 默认 BaseUrl：

```text
http://127.0.0.1:8000
```

连接步骤：

1. 启动 EngineHost。
2. 打开 `EngineHost/runtime/config/local_api_token`。
3. 复制文件中的 token。
4. 在 Desktop 顶部连接区填写 BaseUrl 和 token。
5. 点击连接检查。

注意：

- token 是本机访问凭据，不要分享给他人
- 不要把真实 token 写入截图、日志、issue 或聊天记录
- WebSocket URL 中可能包含 `token=...`，对外发送前必须脱敏为 `token=***`
- REST API 使用 `Authorization: Bearer <token>`
- RuntimeEvent WebSocket 使用 `/ws/v1/events?token=<token>`

Desktop 会保存最近成功的 BaseUrl 到：

```text
%LOCALAPPDATA%\FlowWeaver\Avalonia_UI\connection-settings.json
```

该连接配置只保存 BaseUrl，不保存 token。token 错误、轮换或失效时，重新打开当前 `local_api_token` 文件并在 Desktop 中重新填写。

## 7. 运行数据与备份

`EngineHost/runtime/` 是用户运行数据目录。

关键结构：

```text
EngineHost/runtime/
  config/
    local_api_token
  metadata/
    flowweaver.db
  workflow_runs/
  logs/
  temp/
```

备份建议：

1. 停止 EngineHost。
2. 复制整个 `EngineHost/runtime/` 目录到安全位置。
3. 确认备份中包含 `metadata/flowweaver.db` 和需要保留的 `workflow_runs/`。
4. 不要把备份目录放回发布 zip 输入目录。

PowerShell 示例：

```powershell
Copy-Item -Recurse -Force `
  .\EngineHost\runtime `
  .\backup\runtime-2026-06-30
```

可以优先清理或忽略：

- `EngineHost/runtime/temp/`
- 过旧且已确认不需要的日志备份

不要随意删除：

- `EngineHost/runtime/config/local_api_token`
- `EngineHost/runtime/metadata/flowweaver.db`
- 仍需要排查的 `workflow_runs/`

默认发布归档不会包含 `EngineHost/runtime/`。升级、迁移或反馈问题前，先自己备份 runtime。

## 8. 日志与故障排查

常见日志目录：

```text
EngineHost/runtime/logs/
```

常见日志文件：

| 日志 | 用途 |
| --- | --- |
| `portable-launcher.log` | launcher 启动、health、token 等流程 |
| `enginehost.stdout.log` | EngineHost 标准输出 |
| `enginehost.stderr.log` | EngineHost 错误输出 |
| `desktop.stdout.log` | Desktop 标准输出 |
| `desktop.stderr.log` | Desktop 错误输出 |

常见问题：

| 现象 | 建议检查 |
| --- | --- |
| 控制台没有出现 `EngineHost ready.` | 看 `portable-launcher.log` 和 `enginehost.stderr.log` |
| BaseUrl 连接失败 | 确认端口、BaseUrl、EngineHost 是否仍在运行 |
| token 鉴权失败 | 重新读取当前 `local_api_token`，确认没有复制空格或旧 token |
| Desktop 启动失败 | 检查 .NET 10.0 Desktop Runtime 和 `desktop.stderr.log` |
| 端口占用 | 换一个端口，例如 `--port 8010` |
| 数据库无法创建或迁移失败 | 检查 `EngineHost/runtime/metadata/` 权限和 `enginehost.stderr.log` |
| WebSocket 事件流失败 | 确认 BaseUrl、token 和 EngineHost 仍可访问 |

不要把包含真实 token 的日志片段直接发给他人。若日志中出现 `token=...`，先改为 `token=***`。

## 9. 升级与迁移

升级前：

1. 停止 EngineHost 和 Desktop。
2. 备份旧目录中的 `EngineHost/runtime/`。
3. 校验新 zip 的 `.sha256`。
4. 解压新版本到新目录，或替换旧目录中的程序文件。

推荐方式：

- 保留一份旧版本目录
- 新版本解压到新目录
- 将旧版本的 `EngineHost/runtime/` 复制到新版本的 `EngineHost/runtime/`
- 启动新版本并确认 health、workflow 列表和日志正常

回退建议：

- 先停止新版本 EngineHost
- 保留当前 runtime 备份
- 使用升级前备份的 runtime 恢复到旧版本目录

跨版本数据库迁移可能不可逆。正式升级前，始终保留升级前 runtime 备份。

## 10. 当前明确不支持

阶段 P 便携版当前明确不支持：

| 不支持能力 | 用户侧影响 |
| --- | --- |
| 安装器 | 需要手动解压和启动 |
| 自动更新 | 需要手动下载、校验、替换或迁移 |
| 后台服务 | 关闭控制台或 launcher 可能停止本次 EngineHost |
| 系统托盘常驻 | 暂无托盘图标或后台隐藏运行管理 |
| 多实例自动接管 | 不要同时启动多个使用同一 runtime 的实例 |
| 代码签名 | 系统或安全软件可能显示未知发布者提示 |
| self-contained Desktop 发布包 | 使用 Desktop 时需要 .NET 10.0 Desktop Runtime |
| 跨平台发布包 | 当前发布目标是 Windows `win-x64` |

这些能力未来可以单独规划，但不属于阶段 P 当前范围。

## 11. 支持与诊断信息

反馈问题时建议提供：

- FlowWeaver zip 文件名
- `.sha256` 校验结果
- `release-manifest.json` 中的 `release_version`、`target_runtime`、`runtime_audit_status`
- 使用的启动方式
- BaseUrl
- 操作系统版本
- 是否安装 .NET 10.0 Desktop Runtime
- 相关日志片段

不要提供：

- `local_api_token` 的真实内容
- 带真实 token 的 WebSocket URL
- 完整 `EngineHost/runtime/` 目录
- 含敏感业务数据的数据库或 workflow 输出

如果必须提供日志，请先搜索并脱敏：

```text
token=
Authorization:
Bearer
local_api_token
```
