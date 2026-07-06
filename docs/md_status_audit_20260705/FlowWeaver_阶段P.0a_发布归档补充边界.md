# FlowWeaver 阶段P.0a：发布归档补充边界

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P.0a边界补充完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录和阶段P.0文档
> 适用范围：Desktop self-contained 决策、Python runtime 清洁度、版本统一、manifest、SHA-256、许可证、clean-room smoke 和用户手册警示
> 当前执行点：只补文档边界，不实现归档脚本、不调整发布模式、不清理运行时目录

## 1. 目标

P.0a 的目标是把 P.0 后补充提出的发布风险前置固化，避免 P.1 在设计归档脚本时遗漏关键发布语义。

本阶段补充确认：

- Desktop 当前不是 self-contained 发布
- `python312/` 当前可运行，但不是干净、可直接宣称可分发的发布 runtime
- Python、Avalonia、manifest 和 zip 必须使用统一发布版本
- manifest、SHA-256 和许可证应作为发布归档的一等边界
- clean-room smoke 必须覆盖仓库外、空格路径和中文路径
- 用户手册必须明确关闭 Desktop 对运行中 workflow 的影响

本阶段不做：

- 不修改 `tools/publish_desktop.py`
- 不修改 `tools/create_portable_layout.py`
- 不修改 `python312/`
- 不执行 `dotnet publish`
- 不生成 zip
- 不生成 release manifest
- 不新增 clean-room smoke 测试代码
- 不编写完整用户手册正文

## 2. Desktop self-contained 边界

当前事实：

- `tools/publish_desktop.py` 默认 `self_contained=False`
- `tests/integration/test_n6_desktop_publish_smoke.py` 也按 `self_contained=False` 验收
- `Avalonia_UI/Avalonia_UI.csproj` 当前没有显式发布版本，也没有强制 self-contained 配置

因此当前 Desktop 发布产物是 framework-dependent，不应在用户手册或归档说明中宣称“无需安装 .NET runtime”。

P.1 必须先做发布模式决策：

| 模式 | 含义 | P阶段建议 |
| --- | --- | --- |
| framework-dependent | zip 内不携带 .NET runtime，目标机器需要 .NET 10.0 Desktop Runtime | 维持当前默认，用户手册必须写明依赖 |
| self-contained | zip 内携带 .NET runtime，包体更大，目标机器不要求预装 .NET runtime | 需独立小步验证，不能在归档脚本中顺手切换 |

manifest 建议新增字段：

- `desktop_publish_mode`
- `desktop_self_contained`
- `dotnet_runtime_required`
- `dotnet_target_framework`
- `desktop_runtime_identifier`

P.1 不应默认改变 Desktop 发布模式。若未来切换 self-contained，应先做单独的 P.x 小步和 smoke。

## 3. Python runtime 清洁度边界

当前事实复核：

- `python312/python.exe --version` 返回 `Python 3.12.10`
- `python312/python312._pth` 已启用 `import site`
- `pip` 可用
- 当前 `python312/Lib/site-packages` 包含运行依赖，也包含 dev/test/build 相关包
- 当前 `python312/Lib/site-packages` 存在 `__pycache__` 和 `*.pyc`

当前 `pip list` 中可见的发布风险项包括：

- `pytest`
- `pytest-asyncio`
- `pytest-cov`
- `pytest-qt`
- `pytest-timeout`
- `ruff`
- `mypy`
- `coverage`
- `hatchling`
- `PySide6`
- `PySide6_Addons`
- `PySide6_Essentials`
- `shiboken6`

结论：

`python312/` 当前是仓内可运行 embedded Python runtime，但不能直接认定为“干净、最小、可分发发布 runtime”。

P.1 必须增加 Python runtime audit 方案：

| 检查项 | 要求 |
| --- | --- |
| Python 版本 | 记录 `python_version` |
| pip 版本 | 记录 `pip_version`，决定是否允许随包携带 |
| 运行依赖 | 与 `pyproject.toml` runtime dependencies 对齐 |
| dev 依赖 | 默认不得进入干净发布包，若保留必须明确理由 |
| GUI 旧依赖 | PySide6 / pytest-qt 等非当前 Avalonia 路线依赖默认应排查 |
| 缓存文件 | `__pycache__`、`*.pyc` 默认不进入归档 |
| 许可证 | Python `LICENSE.txt` 和第三方包 license 必须可追溯 |

P.3 如实现 zip 生成，不能简单把仓内 `python312/` 原样归档为正式发布 runtime，除非 manifest 明确标记为 `runtime_audit_status=unchecked` 并拒绝正式发布模式。

## 4. 版本统一边界

当前事实：

- Python 项目版本来自 `pyproject.toml`，当前为 `0.1.0`
- Avalonia `.csproj` 当前没有显式 `Version`
- P.0 仅建议 zip 名称为 `FlowWeaverPortable-<version>-win-x64.zip`
- release manifest 尚未实现

P阶段必须建立单一发布版本来源：

1. P.1 方案阶段先规定 `release_version` 的来源和优先级
2. P.3 归档脚本使用同一个 `release_version` 写入 zip 名称和 manifest
3. 后续如需要 Desktop 程序版本，再把同一个版本写入 `.csproj` 发布属性

推荐优先级：

| 优先级 | 来源 |
| --- | --- |
| 1 | 归档脚本显式 `--version` |
| 2 | `pyproject.toml` 的 `project.version` |
| 3 | git tag 或 CI build number，后续再接 |

manifest 建议新增：

- `release_version`
- `python_project_version`
- `desktop_project_version`
- `git_commit`
- `git_dirty`
- `archive_name`
- `archive_target_runtime`

如果版本不一致，归档脚本应默认拒绝正式发布归档，而不是静默继续。

## 5. Manifest、SHA-256 与许可证边界

P.0 中已有 `release-manifest.json` 建议，P.0a 补充将它提升为 P阶段必做边界。

建议发布物包含：

```text
FlowWeaverPortable/
  release-manifest.json
  licenses/
    FlowWeaver-LICENSE.txt
    Python-LICENSE.txt
    third-party-licenses.json
```

建议发布物旁边包含：

```text
FlowWeaverPortable-<version>-win-x64.zip.sha256
```

原因：

- zip 的 SHA-256 不适合写入 zip 内部 manifest，否则会产生循环
- zip 外部 `.sha256` 文件更适合分发校验
- zip 内部 manifest 记录包内文件清单和关键文件 SHA-256

manifest 第一版建议扩展字段：

| 字段 | 说明 |
| --- | --- |
| `manifest_schema_version` | manifest schema 版本 |
| `release_version` | 统一发布版本 |
| `package_kind` | `portable` |
| `target_runtime` | `win-x64` |
| `desktop_publish_mode` | `framework-dependent` 或 `self-contained` |
| `python_version` | 便携 Python 版本 |
| `pip_version` | 便携 pip 版本 |
| `runtime_audit_status` | `unchecked` / `checked` / `rejected` |
| `licenses` | 许可证文件摘要 |
| `files` | 包内文件路径、大小和 SHA-256 |
| `excluded_paths` | runtime、cache、token 等排除项摘要 |

P.1 需要定义 manifest schema；P.3 才实现写入。

## 6. Clean-room smoke 边界

P.0 中已有“从 zip 解压到新的 `.tmp/` 目录做最小 smoke”。P.0a 补充要求该 smoke 必须离开仓库目录。

P.4 的 clean-room smoke 推荐路径：

```text
%TEMP%\FlowWeaver Clean Room 中文路径 <uuid>\FlowWeaverPortable\
```

clean-room smoke 必须满足：

- 不在仓库 `D:\bigqingshu_project\FlowWeaver` 内运行
- 路径包含空格
- 路径包含中文
- 清理 `PYTHONPATH`
- 后端工作目录固定为解压后的 `EngineHost/`
- 不读取仓库源码、测试文件或 `.tmp/FlowWeaverPortable/`
- 首次启动前 `EngineHost/runtime/` 不存在
- 启动后能生成 runtime、token、metadata 和 logs
- backend-only health 和鉴权 `GET /api/v1/workflows` 通过

真实 Desktop clean-room smoke 仍建议显式环境变量触发，避免普通测试自动打开窗口。

## 7. 用户手册 workflow 中断警示

用户手册必须明确区分两类启动方式：

| 启动方式 | 关闭 Desktop 的影响 |
| --- | --- |
| `start_flowweaver_desktop.cmd` | Desktop 由 launcher 启动；关闭 Desktop 后 launcher 默认停止本次 EngineHost，运行中 workflow 可能中断 |
| `start_flowweaver_desktop.cmd --keep-enginehost-on-desktop-exit` | Desktop 退出后保留本次 EngineHost，运行中 workflow 可继续由后端执行 |
| `start_flowweaver.cmd` + 单独启动 Desktop | 关闭 Desktop 只关闭客户端，不直接停止已启动的 backend-only EngineHost |

手册必须给出建议：

- 如果正在运行 workflow，不要直接关闭由 `start_flowweaver_desktop.cmd` 启动的 Desktop
- 想关闭界面但保留后端时，使用 `--keep-enginehost-on-desktop-exit`
- 或者先用 `start_flowweaver.cmd` 启动后端，再单独启动 Desktop
- 关闭前应在 UI 中确认 workflow run 已结束、取消或处于可接受的中断状态

这属于用户可见行为说明，不改变当前 launcher 语义。

## 8. 对 P 阶段计划的调整

P.0a 后，P 阶段建议调整为：

| 小步 | 方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| P.1 | 发布归档脚本方案 | 参数、版本来源、Desktop publish 模式、runtime audit、manifest/hash/license schema | 不写 zip 代码 |
| P.2 | runtime audit 与归档前检查 | 检查 python312 清洁度、dev 包、cache、许可证、版本一致性 | 不清理 runtime |
| P.3 | 最小归档脚本 | 生成 zip、release-manifest、外部 `.sha256` | 安装器、签名、上传 |
| P.4 | clean-room 解压 smoke | 仓库外、空格/中文路径 backend-only smoke | 默认不打开真实 Desktop |
| P.5 | 用户手册骨架 | 便携版用户手册章节和关键警示 | 完整截图教程 |
| P.6 | 用户手册内容收口 | 启动、token、日志、备份、workflow 中断和故障排查 | 安装器文档 |
| P.7 | 阶段 P 验收复核 | 归档、manifest、hash、license、clean-room 和手册复核 | 自动更新 |

最稳下一步仍是 P.1，但 P.1 必须吸收 P.0a 的补充项。

## 9. 验证

P.0a 为文档补充小步，不运行发布或功能测试。

建议验证：

```powershell
git diff --check
```

## 10. 下一步建议

进入 P.1：发布归档脚本方案。

P.1 应先写清：

- `tools/create_portable_archive.py` 的参数
- `--version` 与 `pyproject.toml` 版本的关系
- Desktop publish mode 是否保持 framework-dependent
- Python runtime audit 如何表达失败、警告和拒绝
- release manifest schema
- zip 外部 `.sha256` 生成位置
- licenses 目录生成策略
- P.4 clean-room smoke 的输入要求
