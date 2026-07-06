# FlowWeaver 阶段P.6：用户手册内容收口

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P.6完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录和阶段P.0-P.5文档
> 适用范围：便携版用户手册正文、用户可见操作说明、故障排查和风险提示
> 当前执行点：只收口用户手册内容，不修改发布脚本、不进入安装器、自动更新或后台服务

## 1. 目标

P.6 的目标是把 P.5 形成的便携版用户手册骨架补成可读正文，让便携 zip 用户能够完成解压、启动、连接、查看日志、备份 runtime、升级迁移和基础故障排查。

本阶段完成：

- 更新 `docs/FlowWeaver_便携版用户手册.md`
- 移除 P.5 骨架中的 `P.6 待补` 标记
- 补齐快速开始
- 补齐运行要求
- 补齐发布包结构
- 补齐 backend-only 与 Desktop 组合启动步骤
- 补齐 Desktop 关闭对运行中 workflow 的影响
- 补齐 token 与连接配置
- 补齐 runtime 数据和备份说明
- 补齐日志与故障排查说明
- 补齐升级与迁移说明
- 补齐当前不支持能力的用户侧影响
- 补齐反馈问题时的诊断信息清单
- 更新 README 阶段记录和下一步建议

本阶段不做：

- 不修改 `tools/create_portable_archive.py`
- 不修改 `tools/create_portable_layout.py`
- 不把完整手册复制进 zip
- 不新增截图教程
- 不创建安装器
- 不创建自动更新
- 不创建后台服务
- 不改变 Desktop framework-dependent 默认

## 2. 手册正文收口点

P.6 已将手册补为以下内容：

| 章节 | 收口内容 |
| --- | --- |
| 快速开始 | 解压、启动、BaseUrl、token 和 Desktop 连接 |
| 运行要求 | 包内 Python、Desktop framework-dependent、.NET Runtime 诊断 |
| 发布包结构 | `EngineHost/`、`Desktop/`、`runtime/`、manifest 和 licenses |
| 启动方式 | `start_flowweaver.cmd`、`start_flowweaver_desktop.cmd`、参数示例 |
| Desktop 关闭警示 | 运行中 workflow 风险、安全退出和误关闭后检查 |
| Token 与连接 | token 文件、REST/WebSocket 鉴权、BaseUrl 持久化和脱敏 |
| 运行数据与备份 | runtime 目录、备份步骤、可清理/不可随意删除内容 |
| 日志与故障排查 | launcher、EngineHost、Desktop 日志和常见问题表 |
| 升级与迁移 | zip 校验、runtime 备份、迁移和回退 |
| 当前不支持 | 安装器、自动更新、后台服务、系统托盘、多实例、签名等用户影响 |
| 支持与诊断 | 应提供和不应提供的信息 |

## 3. 明确保留的后续边界

P.6 不把手册复制进 zip。当前完整手册仍位于仓库：

```text
docs/FlowWeaver_便携版用户手册.md
```

发布包内的 `docs/README.txt` 仍保持短说明。后续如果希望发布包内也带完整手册，应作为独立小步修改归档脚本和归档测试。

P.6 不新增截图教程。截图、图形化步骤和面向终端用户的排版优化可在阶段 P 之后独立规划。

## 4. 验收

P.6 验收条件：

- 手册不再包含 `P.6 待补`
- 手册包含首次启动正文
- 手册包含 backend-only 与 Desktop 组合启动步骤
- 手册包含 token 查找、连接配置和脱敏说明
- 手册包含 runtime 备份和升级迁移说明
- 手册包含 workflow 中断风险和安全退出说明
- 手册包含当前不支持能力的用户侧影响
- README 已指向 P.7 作为下一步
- `git diff --check` 通过

## 5. 下一步建议

进入 P.7：阶段 P 总体验收复核。

P.7 应逐项复核：

- P.1 发布归档脚本方案
- P.2 runtime audit
- P.3 zip、manifest、licenses 和 `.sha256`
- P.4 clean-room smoke
- P.5/P.6 用户手册
- Desktop framework-dependent 默认
- 未进入安装器、自动更新、后台服务
- 阶段 P 所有测试和文档记录
