# FlowWeaver 阶段P.7：阶段P总体验收复核

> 文档状态：阶段P.7完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录和阶段P.0-P.6文档
> 适用范围：阶段P发布归档、runtime audit、manifest、SHA-256、许可证、clean-room smoke、便携版用户手册和不支持能力复核
> 当前执行点：只做阶段P总体验收复核，不进入安装器、自动更新、后台服务、代码签名或 self-contained Desktop

## 1. 目标

P.7 的目标是把阶段P的完成状态和验收证据集中固化，确认阶段P已经覆盖便携发布归档与用户手册收口所需的最小闭环。

本阶段完成：

- 复核 P.0/P.0a 到 P.6 的文档和代码产出
- 复核 runtime audit、zip、`release-manifest.json`、`licenses/` 和外部 `.sha256`
- 复核 clean-room smoke 覆盖仓库外、空格路径和中文路径
- 复核便携版用户手册已覆盖启动、token、runtime、日志、备份、升级和当前不支持能力
- 复核 Desktop 仍保持 `framework-dependent`
- 复核阶段P未进入安装器、自动更新、后台服务、代码签名或 self-contained Desktop
- 更新 README 阶段记录

本阶段不做：

- 不修改发布归档脚本行为
- 不修改 runtime audit 规则
- 不把完整用户手册复制进 zip
- 不新增真实 Desktop clean-room 自动化
- 不创建安装器
- 不创建自动更新
- 不创建后台服务
- 不切换 Desktop 为 self-contained

## 2. 完成矩阵

| 小步 | 状态 | 主要产出 | 验收结论 |
| --- | --- | --- | --- |
| P.0 | 完成 | `docs/FlowWeaver_阶段P.0_发布物归档与用户手册边界分析.md` | 发布物归档和用户手册边界已明确 |
| P.0a | 完成 | `docs/FlowWeaver_阶段P.0a_发布归档补充边界.md` | Desktop 模式、runtime audit、版本、manifest/hash/license 和 clean-room 要求已固化 |
| P.1 | 完成 | `docs/FlowWeaver_阶段P.1_发布归档脚本方案.md` | 归档脚本职责、CLI、拒绝项和 manifest schema 已明确 |
| P.2 | 完成 | `tools/portable_runtime_audit.py`、`tests/unit/test_portable_runtime_audit.py` | runtime audit 可识别阻断项、排除项和 warning |
| P.3 | 完成 | `tools/create_portable_archive.py`、`tests/unit/test_create_portable_archive.py` | zip、manifest、licenses 和 `.sha256` 生成闭环已覆盖 |
| P.4 | 完成 | `tests/integration/test_p4_portable_archive_clean_room_smoke.py`、`docs/FlowWeaver_阶段P.4_clean_room解压Smoke.md` | 仓库外空格/中文路径 backend-only smoke 已覆盖 |
| P.5 | 完成 | `docs/FlowWeaver_便携版用户手册.md` 骨架、`docs/FlowWeaver_阶段P.5_便携版用户手册骨架.md` | 手册章节和用户侧风险边界已建立 |
| P.6 | 完成 | `docs/FlowWeaver_便携版用户手册.md` 正文、`docs/FlowWeaver_阶段P.6_用户手册内容收口.md` | 手册正文已覆盖启动、token、runtime、日志、备份、升级和不支持能力 |
| P.7 | 完成 | `docs/FlowWeaver_阶段P.7_总体验收复核.md` | 阶段P完成状态、验收命令和剩余边界已固化 |

## 3. 发布归档复核

阶段P当前归档路径仍以 `.tmp/FlowWeaverPortable/` 为输入，并通过 `tools/create_portable_archive.py` 生成：

- `FlowWeaverPortable-<version>-win-x64.zip`
- `FlowWeaverPortable-<version>-win-x64.zip.sha256`
- zip 内 `FlowWeaverPortable/release-manifest.json`
- zip 内 `FlowWeaverPortable/licenses/FlowWeaver-LICENSE.txt`
- zip 内 `FlowWeaverPortable/licenses/Python-LICENSE.txt`
- zip 内 `FlowWeaverPortable/licenses/third-party-licenses.json`

已确认：

- `release-manifest.json` 不进入自身 `entries`
- manifest 完整性由 zip 外部 `.sha256` 覆盖
- `.sha256` 记录整个 zip 的 SHA-256
- `entries` 记录 zip 内 payload 文件的 path、size 和 sha256
- 归档脚本拒绝 `self-contained` Desktop 模式
- 归档脚本拒绝输出到 `.tmp/` 以外
- 归档脚本拒绝包含 runtime、token、db、log 等阻断路径的输入

## 4. Runtime Audit 复核

`tools/portable_runtime_audit.py` 当前覆盖：

- `EngineHost/python312/python.exe` 存在性
- Python 版本为 3.12
- `python312._pth` 启用 `import site`
- pip 可读取版本
- Python `LICENSE.txt` 存在
- `EngineHost/runtime`、`Desktop/runtime`、`local_api_token`、数据库和日志等路径不得进入归档输入
- `__pycache__` 和 `*.pyc` 作为归档排除项
- dev/test/build/legacy GUI 包作为 warning

当前阶段允许 audit 结果为 `checked` 或 `warning`。如果仓内 `python312/` 带有开发、测试、构建或旧 GUI 包，runtime audit 会给出 warning；该 warning 不等同于发布阻断，但必须写入 manifest 并由发布者在正式分发前确认。

## 5. Clean-Room Smoke 复核

P.4 已新增正式 clean-room smoke，覆盖：

- 从真实便携 layout 生成 zip 和 `.sha256`
- 校验外部 `.sha256`
- 解压到 `%TEMP%` 下仓库外目录
- 解压路径包含空格和中文
- 解压后首次启动前不存在 `EngineHost/runtime/`
- 清除 `PYTHONPATH`
- 使用便携目录内 `EngineHost/python312/python.exe` 启动 `portable_launcher.py --no-desktop`
- 验证 health
- 读取 `EngineHost/runtime/config/local_api_token`
- 使用 token 查询 `GET /api/v1/workflows`
- 验证首次启动生成 metadata db、token 和日志目录
- 验证 launcher 日志、stdout、stderr 不泄露真实 token

P.4 当前默认只覆盖 backend-only 路径。真实 Desktop clean-room 自动化仍保留为后续显式小步。

## 6. 用户手册复核

`docs/FlowWeaver_便携版用户手册.md` 当前已覆盖：

- 快速开始
- 运行要求
- 发布包结构
- backend-only 启动
- Desktop 组合启动
- Desktop 关闭对运行中 workflow 的影响
- token 与连接配置
- runtime 数据和备份
- 日志与故障排查
- 升级与迁移
- 当前不支持能力
- 反馈问题时应提供和不应提供的信息

手册明确：

- Desktop 当前为 `framework-dependent`
- 使用 Desktop 需要 .NET 10.0 Desktop Runtime
- 关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop 可能停止本次 EngineHost，并影响运行中 workflow
- 需要保留后端时应使用 `--keep-enginehost-on-desktop-exit` 或单独 backend-only 入口
- token 不应分享，带 token 的 WebSocket URL 必须脱敏
- `runtime/` 是用户运行数据，升级前应备份

当前完整手册仍只位于仓库文档中，发布包内仍是短 README。把完整手册复制进 zip 需要后续单独小步修改归档脚本和测试。

## 7. 验收命令

本次 P.7 运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
```

结果：

```text
17 passed
```

本次 P.7 运行：

```powershell
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
```

结果：

```text
All checks passed!
```

本次 P.7 运行：

```powershell
git diff --check
```

结果：通过。

本次 P.7 还复核了 P 阶段关键词：

- `P.6 待补`
- `安装器`
- `自动更新`
- `后台服务`
- `self-contained`
- `framework-dependent`
- `release-manifest`
- `sha256`
- `licenses`
- `clean-room`
- `local_api_token`
- `keep-enginehost-on-desktop-exit`

复核结论：相关关键词均处于阶段记录、明确不支持、显式拒绝或未来扩展语境中；未发现阶段P将安装器、自动更新、后台服务或 self-contained Desktop 误标为已支持。

## 8. 当前明确不支持

阶段P完成后仍明确不支持：

- 安装器
- 自动更新
- 后台服务
- 系统托盘
- 代码签名
- self-contained Desktop 发布包
- 真实 Desktop clean-room 自动化默认执行
- 发布包内携带完整用户手册
- 上传发布物或远端分发
- 多实例接管

这些能力需要后续独立阶段或明确小步，不应在 UI 或发布归档脚本中顺手绕过。

## 9. 阶段P验收结论

阶段P已经完成便携发布归档与用户手册收口的最小闭环：

- 有发布归档方案
- 有 runtime audit
- 有 zip、manifest、licenses 和外部 `.sha256`
- 有 clean-room backend-only smoke
- 有便携版用户手册
- 有阶段P验收记录

阶段P可以收口。下一步建议先做 P 后边界分析，决定是否进入发布包内文档、真实 Desktop clean-room、签名、安装器、自动更新或后台服务等后续方向；在用户明确要求前不默认进入这些扩展。
