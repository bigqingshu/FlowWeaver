# FlowWeaver 阶段P+4a：release strict 最小实现

> 文档状态：阶段P+4a完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3、P+3a、P+3b、P+3c、P+3c-1、P+3c-2 和 P+4 分析文档
> 适用范围：便携 zip 正式发布门禁的显式开关、拒绝条件和单元验收
> 当前执行点：只做 `--release-strict` 最小归档输入门禁，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 阶段目标

P+4a 根据 P+4 分析新增显式正式发布门禁：

```powershell
.\python312\python.exe tools\create_portable_archive.py --release-strict
```

默认开发归档行为保持不变。只有显式传入 `--release-strict` 或代码调用 `release_strict=True` 时，才启用正式发布门禁。

## 2. 已实现内容

| 项目 | 结果 |
| --- | --- |
| `create_portable_archive(..., release_strict=False)` | 新增参数，默认关闭 |
| CLI `--release-strict` | 已新增 |
| manifest `release_strict` | 已记录当前归档是否启用 strict |
| strict 失败时输出 | 不创建 zip，不创建 `.sha256`，不创建输出目录 |
| 默认 warning audit | 仍允许开发归档 |

## 3. strict 阻断条件

第一版 strict 覆盖以下 code：

| code | 触发条件 |
| --- | --- |
| `runtime_audit_warning` | runtime audit 为 `warning` |
| `third_party_license_warning` | `third-party-licenses.json.warnings` 非空 |
| `git_commit_unavailable` | 无法读取 `git rev-parse HEAD` |
| `git_worktree_dirty` | `git status --short` 非空 |
| `desktop_executable_missing` | `Desktop/Avalonia_UI.exe` 不存在 |

已有 `runtime_audit.status == "rejected"` 仍沿用原有归档拒绝路径。

## 4. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_archive.py` | 新增 `release_strict` 参数、CLI 开关、manifest 字段和 `_validate_release_strict` |
| `tests/unit/test_create_portable_archive.py` | 覆盖 strict 拒绝 runtime warning、许可证 warning、dirty git、缺失 Desktop，以及干净输入通过 |
| `docs/FlowWeaver_阶段P+4a_release_strict最小实现.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+4a 阶段记录和下一步建议 |

## 5. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tests\unit\test_create_portable_archive.py
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

结果：

```text
pytest create_portable_archive: 18 passed
pytest release archive checks: 31 passed
ruff: All checks passed!
git diff --check: passed
```

## 6. 阶段结论

P+4a 已形成 release strict 的最小闭环：

- 开发归档仍默认宽松
- 正式发布门禁必须显式启用
- strict 只判断当前归档输入是否干净
- clean-room smoke 仍由发布流程在归档后执行

下一步建议做 P 阶段后续总体验收复核，汇总 P+3c 到 P+4a 的许可证和 strict 发布门禁状态，再决定是否推送或进入更重的分发阶段。
