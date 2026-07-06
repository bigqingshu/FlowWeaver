# FlowWeaver 阶段P后续：总体验收复核

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P后续总体验收复核完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7 和 P+1-P+4a 各阶段文档
> 适用范围：P+1 到 P+4a 的便携发布归档、用户手册、Desktop smoke、第三方许可证增强和 release strict 门禁
> 当前执行点：只做阶段复核，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 完成矩阵

| 阶段 | 状态 | 主要产出 |
| --- | --- | --- |
| P+1 | 完成 | 发布包携带完整便携版用户手册，docs README 指向完整手册 |
| P+2 | 完成 | 真实 Desktop clean-room smoke，显式环境变量保护 |
| P+3 | 完成 | 第三方许可证增强方案，明确 metadata、正文复制和 strict 分流 |
| P+3a | 完成 | Python 包许可证 metadata 采集 |
| P+3b | 完成 | .NET NuGet 依赖许可证 metadata 采集 |
| P+3c | 完成 | 许可证正文复制评估 |
| P+3c-1 | 完成 | Python 许可证正文复制到 `licenses/third-party/python/` |
| P+3c-2 | 完成 | 正文缺失、越界和复制冲突 warning 边界复核 |
| P+4 | 完成 | release strict 模式分析 |
| P+4a | 完成 | `--release-strict` 最小实现与单元验收 |

## 2. 当前发布归档能力

当前便携 zip 归档已经覆盖：

- `release-manifest.json`
- zip 外部 `.sha256`
- FlowWeaver 项目许可证正文
- Python runtime 许可证正文
- `third-party-licenses.json`
- Python 包许可证 metadata
- Python 包许可证正文复制
- .NET NuGet metadata 记录
- 发布包内完整用户手册
- backend-only clean-room smoke
- 显式保护的真实 Desktop clean-room smoke

`third-party-licenses.json` 当前状态为 `metadata-and-files`：

- Python 包可记录 `License-Expression`、`License`、license classifier、`License-File`、`license_files` 和 `copied_license_files`
- Python 包正文复制目标为 `FlowWeaverPortable/licenses/third-party/python/<package>/...`
- NuGet 包目前只记录 metadata，不复制正文
- warning 会写入顶层 `warnings` 和包级 `warnings`

## 3. release strict 状态

当前 `tools/create_portable_archive.py` 支持：

```powershell
.\python312\python.exe tools\create_portable_archive.py --release-strict
```

默认开发归档仍保持宽松：

- runtime audit warning 可归档
- 第三方许可证 warning 可归档
- dirty git 只写入 manifest
- backend-only layout 可归档

显式 `--release-strict` 会拒绝：

| code | 含义 |
| --- | --- |
| `runtime_audit_warning` | runtime audit 仍有 warning |
| `third_party_license_warning` | 第三方许可证清单仍有 warning |
| `git_commit_unavailable` | 无法读取 Git commit |
| `git_worktree_dirty` | 工作区不干净 |
| `desktop_executable_missing` | 缺少 `Desktop/Avalonia_UI.exe` |

strict 失败时不会生成 zip、`.sha256` 或输出目录。

## 4. 验收结果

本轮 P+3c 到 P+4a 执行过的关键验收：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

最近一次完整结果：

```text
pytest create_portable_archive: 18 passed
pytest release archive checks: 31 passed
ruff: All checks passed!
git diff --check: passed
```

## 5. 明确未完成或不支持

当前仍不宣称支持：

- NuGet 许可证正文复制
- 联网下载许可证正文
- 许可证法律兼容性判断
- 代码签名
- 安装器
- 自动更新
- 后台服务
- 系统托盘
- Desktop self-contained 发布
- 把 clean-room smoke 结果写回 zip
- 当前仓内 `python312/` 一定可通过 `--release-strict`

其中最后一点很重要：P+4a 已经提供 strict 门禁，但当前本地 `python312/` 是否能通过 strict，取决于发布输入是否已经移除 dev/test/build/legacy 包、是否具备完整 Desktop build 和许可证 metadata。

## 6. 下一步建议

短期建议：

1. 先推送 P+3c 到 P+4a 的阶段提交。
2. 若要继续正式发布方向，先做“干净可分发 Python runtime”分析，目标是让 `--release-strict` 有机会通过。
3. 再做 release pipeline 串联分析：`layout -> archive --release-strict -> sha256 verify -> clean-room smoke`。

继续保持以下事项为独立后续阶段：

- 代码签名
- 安装器
- 自动更新
- 后台服务或系统托盘
- Desktop self-contained

## 7. 阶段结论

P 后续发布归档收口已经形成两个层级：

- 开发归档：便于本地测试和 clean-room smoke，允许 warning 但必须记录。
- 正式发布门禁：通过 `--release-strict` 显式启用，对发布输入洁净度做阻断。

当前可以进入提交推送；是否继续到“干净可分发 Python runtime”应作为下一阶段单独决策。
