# FlowWeaver 阶段P.5：便携版用户手册骨架

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：便携版用户手册已形成，并在发布 layout / archive 链路中作为 docs 入口被复制和 smoke 覆盖。
> 未实现：手册中列明的不支持项，如安装器、自动更新、后台服务、系统托盘、代码签名和 self-contained Desktop，仍未实现。
> 原因：这些是不支持能力说明，不是当前手册目标内的缺口。

> 文档状态：阶段P.5完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录和阶段P.0-P.4文档
> 适用范围：便携版用户手册文件、章节结构和关键警示
> 当前执行点：只建立手册骨架，不补完整操作正文、不增加截图、不改变发布脚本

## 1. 目标

P.5 的目标是把 P.0/P.0a 确认的用户手册入口落成文件，并先固定章节结构和用户可见的关键警示，供 P.6 继续补正文。

本阶段完成：

- 新增 `docs/FlowWeaver_便携版用户手册.md`
- 固定便携版手册的章节结构
- 写入 Desktop framework-dependent 边界
- 写入 backend-only 与 Desktop 组合入口
- 写入关闭 Desktop 对运行中 workflow 的影响
- 写入 token、runtime、日志、备份和不支持能力的章节骨架
- 更新 README 阶段记录和下一步建议

本阶段不做：

- 不写完整用户手册正文
- 不增加截图教程
- 不修改 `tools/create_portable_archive.py`
- 不修改 `tools/create_portable_layout.py`
- 不把完整手册复制进 zip
- 不创建安装器
- 不创建自动更新
- 不改变 Desktop framework-dependent 默认

## 2. 新增手册文件

新增：

```text
docs/FlowWeaver_便携版用户手册.md
```

P.5 中该文件是仓库内较完整用户手册的起点。后续如果需要把它复制到发布包内，应在独立小步修改归档脚本，不在 P.5 顺手实现。

## 3. 手册章节结构

P.5 固定以下章节：

| 章节 | 目的 |
| --- | --- |
| 快速开始 | 首次解压后的最短启动路径 |
| 运行要求 | Windows、内置 Python、.NET Desktop Runtime 等要求 |
| 发布包结构 | 解压后目录说明 |
| 启动方式 | backend-only 与 Desktop 组合入口 |
| 重要警示：关闭 Desktop 与运行中 workflow | 明确关闭 Desktop 的影响 |
| Token 与连接 | token 文件、REST 和 WebSocket 鉴权 |
| 运行数据与备份 | `EngineHost/runtime/` 和升级前备份 |
| 日志与故障排查 | 常见日志和启动失败排查入口 |
| 升级与迁移 | 替换程序文件和保留 runtime |
| 当前明确不支持 | 安装器、自动更新、后台服务等 |
| 支持与诊断信息 | 反馈问题时应提供的信息 |

每个章节均保留 `P.6 待补` 项，避免 P.5 提前扩展为完整手册。

## 4. 已固化关键警示

P.5 先写入以下用户可见警示：

| 警示 | 内容 |
| --- | --- |
| Desktop 发布模式 | 当前 Desktop 为 framework-dependent，不是 self-contained；使用 Desktop 时需要 .NET 10.0 Desktop Runtime |
| Desktop 关闭影响 | `start_flowweaver_desktop.cmd` 默认由 launcher 管理 EngineHost，关闭 Desktop 会停止本次 EngineHost，运行中 workflow 可能中断 |
| 保留后端 | 可使用 `start_flowweaver_desktop.cmd --keep-enginehost-on-desktop-exit`，或用 `start_flowweaver.cmd` 单独启动后端 |
| token | token 位于 `EngineHost/runtime/config/local_api_token`，不要分享真实 token 或带 token 的 WebSocket URL |
| runtime 数据 | `EngineHost/runtime/` 是用户运行数据和本机配置，不应进入发布归档 |
| 当前不支持 | 安装器、自动更新、后台服务、系统托盘、多实例接管、代码签名、self-contained Desktop、跨平台包 |

## 5. 验收

P.5 验收条件：

- `docs/FlowWeaver_便携版用户手册.md` 已存在
- 手册包含 P.0/P.0a 要求的主要章节
- 手册明确关闭 Desktop 可能影响运行中 workflow
- 手册明确 Desktop 当前不是 self-contained
- 手册明确 token 不应分享
- 手册明确当前不支持能力
- README 已指向 P.6 作为下一步
- `git diff --check` 通过

## 6. 下一步建议

进入 P.6：用户手册内容收口。

P.6 建议补齐：

- 首次启动正文
- Desktop 与 backend-only 操作步骤
- token 查找和连接配置
- 日志定位和故障排查
- runtime 备份与升级
- workflow 中断风险的安全退出步骤
- 当前不支持能力的用户侧影响说明
