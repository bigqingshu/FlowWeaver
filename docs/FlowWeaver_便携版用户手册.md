# FlowWeaver 便携版用户手册

> 文档状态：P.5 骨架完成，P.6 补充正文细节
> 适用版本：FlowWeaver Portable `win-x64`
> 当前发布形态：便携 zip，Desktop 为 framework-dependent

## 1. 快速开始

本节用于放置用户首次解压后的最短启动路径。

P.6 待补：

- 推荐解压位置
- 首次启动顺序
- 如何确认 EngineHost 已启动
- 如何打开桌面端并连接 EngineHost
- 首次失败时先看哪些日志

## 2. 运行要求

本节用于说明便携版运行所需的系统和运行时。

已确认边界：

- 后端使用发布包内的 `EngineHost/python312/python.exe`
- Desktop 当前为 framework-dependent，不是 self-contained
- 使用 Desktop 时，目标机器需要可运行 .NET 10.0 Desktop Runtime
- 当前发布包面向 Windows `win-x64`

P.6 待补：

- Windows 版本建议
- .NET 10.0 Desktop Runtime 获取和检查方式
- 磁盘空间建议
- 防病毒软件或目录权限导致启动失败时的处理方式

## 3. 发布包结构

本节用于解释解压后的目录。

核心结构：

```text
FlowWeaverPortable/
  EngineHost/
  Desktop/
  docs/
  licenses/
  release-manifest.json
  portable_launcher.py
  start_flowweaver.cmd
  start_flowweaver_desktop.cmd
```

P.6 待补：

- 每个目录的用户可见含义
- 哪些文件可以查看
- 哪些目录不要手工删除
- `release-manifest.json` 和 `.sha256` 的用途

## 4. 启动方式

本节用于说明 backend-only 和 Desktop 组合启动的区别。

入口：

| 启动方式 | 用途 |
| --- | --- |
| `start_flowweaver.cmd` | 只启动 EngineHost，适合诊断、自动化 smoke 或只使用 HTTP API |
| `start_flowweaver_desktop.cmd` | 启动 EngineHost + Desktop，适合普通桌面使用 |
| `EngineHost/python312/python.exe portable_launcher.py --no-desktop` | backend-only 等价命令 |
| `EngineHost/python312/python.exe portable_launcher.py` | Desktop 组合等价命令 |

P.6 待补：

- 双击启动流程
- 命令行启动流程
- 自定义端口示例
- `--health-timeout-seconds` 使用场景
- `--keep-enginehost-on-desktop-exit` 使用场景

## 5. 重要警示：关闭 Desktop 与运行中 workflow

`start_flowweaver_desktop.cmd` 会由 launcher 同时管理 Desktop 和本次 EngineHost。

重要边界：

| 场景 | 影响 |
| --- | --- |
| 直接关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop | launcher 默认停止本次 EngineHost，运行中 workflow 可能中断 |
| 使用 `start_flowweaver_desktop.cmd --keep-enginehost-on-desktop-exit` | Desktop 退出后保留本次 EngineHost，运行中 workflow 可继续由后端执行 |
| 先用 `start_flowweaver.cmd` 启动后端，再单独启动 Desktop | 关闭 Desktop 只关闭客户端，不直接停止 backend-only EngineHost |

使用建议：

- 如果正在运行 workflow，不要直接关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop
- 关闭前先在 UI 中确认 workflow run 已结束、已取消或可以接受中断
- 想关闭界面但保留后端时，使用 `--keep-enginehost-on-desktop-exit`

P.6 待补：

- UI 中确认 workflow 状态的位置
- 安全退出步骤
- 误关闭后的恢复检查

## 6. Token 与连接

本节用于说明本地 API token 和桌面端连接。

已确认边界：

- token 文件位于 `EngineHost/runtime/config/local_api_token`
- REST API 使用 Bearer token
- RuntimeEvent WebSocket 使用 token 查询参数
- 不要分享 token
- 不要把带真实 token 的 WebSocket URL 发给他人或写入日志

P.6 待补：

- 如何找到 token 文件
- Desktop 首次连接如何填写 BaseUrl 和 token
- 默认 BaseUrl
- token 错误、轮换或失效时如何处理
- WebSocket URL 脱敏示例

## 7. 运行数据与备份

本节用于说明 `EngineHost/runtime/`。

关键目录：

```text
EngineHost/runtime/
  config/
  metadata/
  workflow_runs/
  logs/
  temp/
```

P.6 待补：

- 哪些文件属于用户运行数据
- 如何备份 `EngineHost/runtime/`
- 升级前备份步骤
- 哪些临时文件可以清理
- 不要把 runtime 放进发布归档

## 8. 日志与故障排查

本节用于说明启动失败、连接失败和工作流异常时先看哪里。

常见日志位置：

```text
EngineHost/runtime/logs/
```

P.6 待补：

- launcher 日志
- EngineHost stdout/stderr 日志
- Desktop 连接失败时的检查顺序
- 端口占用
- token 鉴权失败
- .NET Runtime 缺失
- 数据库无法创建或迁移失败

## 9. 升级与迁移

本节用于说明从一个便携版本升级到另一个便携版本。

P.6 待补：

- 先备份 `EngineHost/runtime/`
- 替换程序文件
- 保留 runtime 的建议方式
- release manifest 和版本检查
- 回退旧版本时的注意事项

## 10. 当前明确不支持

阶段 P 便携版当前明确不支持：

- 安装器
- 自动更新
- 后台服务
- 系统托盘常驻
- 多实例自动接管
- 代码签名
- self-contained Desktop 发布包
- 跨平台发布包

P.6 待补：

- 每个不支持项的用户侧影响
- 后续可能扩展的方向

## 11. 支持与诊断信息

本节用于说明用户反馈问题时应提供哪些信息。

P.6 待补：

- FlowWeaver 版本
- zip 文件名
- `.sha256` 校验结果
- `release-manifest.json` 摘要
- 启动方式
- BaseUrl
- 相关日志片段
- 不要提供真实 token
