# FlowWeaver 阶段P+5e：dirty git 与正式 strict 最终复核

> 文档状态：阶段P+5e完成
> 当前执行点：验证已提交 HEAD 在干净工作区下的正式 `--release-strict` 链路；不处理用户未跟踪 UI 文档，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 背景

P+5d 后，主工作区仍有未跟踪文件：

```text
docs/UI组件MainWindow的后续计划.MD
```

该文件会让 `git status --short` 非空，并触发：

```text
git_worktree_dirty
```

但该文件不属于 P+5b-P+5d 的发布 runtime / archive strict 实现范围。P+5e 因此不擅自提交、移动或删除该文件，而是用临时 clean clone 验证当前已提交 HEAD 的正式 strict 链路。

## 2. 验证方式

在仓库 `.tmp/` 下创建临时 clone：

```powershell
git clone --local --no-hardlinks <repo> .tmp\P5eStrictHeadRepo
```

该 clone 只包含已提交内容，不包含主工作区未跟踪文件。

在 clone 中执行正式顺序：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py `
  --source <repo>\python312 `
  --locked `
  --output .tmp\P5eReleasePython

.\python312\python.exe tools\create_portable_layout.py `
  --output .tmp\P5ePortable `
  --python-runtime-dir .tmp\P5eReleasePython `
  --no-desktop-build

.\python312\python.exe tools\publish_desktop.py `
  --output .tmp\P5ePortable\Desktop

.\python312\python.exe tools\create_portable_archive.py `
  --input .tmp\P5ePortable `
  --output .tmp\P5eDist `
  --release-strict
```

说明：

- `python312/` 是 gitignore 的本地 embedded Python runtime，因此从主仓库显式作为 `--source` 传入
- clone 内 `.tmp/`、Avalonia `bin/obj` 均为 gitignore 项，不会污染 clean git 状态
- Desktop 通过 `publish_desktop.py` 正式发布到 portable layout，不依赖 layout 的 Debug fallback

## 3. strict 通过结果

`create_portable_archive.py --release-strict` 输出：

```json
{
  "archive_path": "...\\.tmp\\P5eDist\\FlowWeaverPortable-0.1.0-win-x64.zip",
  "release_strict": true,
  "runtime_audit_status": "checked",
  "sha256_path": "...\\.tmp\\P5eDist\\FlowWeaverPortable-0.1.0-win-x64.zip.sha256"
}
```

生成物：

```text
FlowWeaverPortable-0.1.0-win-x64.zip
FlowWeaverPortable-0.1.0-win-x64.zip.sha256
```

归档大小：

```text
70315434 bytes
```

SHA-256：

```text
80006ea65f15baa8dbb179082f87d44af90b3f92de3c6efc3ee4415477cb9fc0
```

## 4. manifest 复核

从 zip 内读取 `FlowWeaverPortable/release-manifest.json`，关键字段为：

```text
release_strict: true
git_dirty: false
runtime_audit_status: checked
desktop_self_contained: false
dotnet_runtime_required: true
```

说明：

- strict 模式确实启用
- clean clone 中工作区干净
- release Python runtime audit 通过
- Desktop 仍是 framework-dependent
- 未进入 self-contained Desktop

## 5. 第三方许可证复核

从 zip 内读取 `FlowWeaverPortable/licenses/third-party-licenses.json`，关键结果为：

```text
warnings: []
package_count: 53
copied_dotnet_license_count: 1
```

说明：

- Python 运行依赖和 NuGet 依赖均无顶层许可证 warning
- NuGet file license 已至少复制 1 个许可证文件
- `third_party_license_warning` 不再阻断 strict

## 6. 当前主工作区状态

主工作区仍存在：

```text
docs/UI组件MainWindow的后续计划.MD
```

该文件会让主工作区直接执行 strict 时继续触发 `git_worktree_dirty`。

处理建议保留给用户决策：

| 选择 | 影响 |
| --- | --- |
| 提交该文档 | 主工作区可变干净，文档纳入仓库历史 |
| 移到仓库外 | 不污染发布 strict，但不作为项目文档跟踪 |
| 保持未跟踪 | 不影响已提交 HEAD 的 clean clone strict 证明，但主工作区直接 strict 会继续失败 |
| 后续单独整理到 UI 阶段提交 | 更符合该文件主题，但 P 阶段 strict 前仍需临时外置或提交 |

## 7. 修改清单

| 文件 | 修改 |
| --- | --- |
| `docs/FlowWeaver_阶段P+5e_dirtyGit与正式Strict最终复核.md` | 记录 clean clone strict 验证、manifest 摘要和 dirty git 边界 |
| `docs/FlowWeaver_阶段P_正式发布前置完成清单.md` | 汇总 P+5b-P+5e 完成矩阵和剩余边界 |
| `README.md` | 更新 P+5e 和 P 阶段发布前置完成状态 |

## 8. 结论

P+5e 证明：当前已提交 HEAD 在干净工作区中，按正式顺序可以通过 `create_portable_archive.py --release-strict`。

主工作区的未跟踪 UI 文档是本地 dirty 状态问题，不是 P 阶段发布 runtime、Desktop payload 或 archive strict 代码缺口。
