# FlowWeaver 阶段P：正式发布前置完成清单

> 文档状态：阶段P正式发布前置收口完成
> 覆盖范围：P+5b 到 P+5e，聚焦 release Python runtime 锁定、strict 前置复核、NuGet 文件许可证、Desktop publish 输入验收和 clean clone strict 证明

## 1. 完成矩阵

| 项目 | 状态 | 证据 |
| --- | --- | --- |
| release Python runtime 独立生成 | 完成 | `tools/create_release_python_runtime.py` |
| release runtime 使用锁定依赖 | 完成 | `--locked` / `uv.lock` 运行依赖闭包 |
| wheel hash 安装 | 完成 | `pip install --require-hashes --only-binary=:all:` |
| 默认开发路径不变 | 完成 | 不传 `--locked` 仍按 `pyproject.toml` dependency ranges |
| repo-local `python312/` 不原地清理 | 完成 | release runtime 输出到 `.tmp/` |
| portable layout 可接入独立 runtime | 完成 | `create_portable_layout.py --python-runtime-dir` |
| runtime audit 对 locked runtime 通过 | 完成 | P+5b/P+5e smoke 均为 `checked` |
| NuGet expression license metadata | 完成 | P+3b 已支持 |
| NuGet file license metadata 和复制 | 完成 | P+5c 支持 `<license type="file">LICENSE</license>` |
| release strict 阻断 license warning | 完成 | P+5e `third_party.warnings == []` |
| Desktop framework-dependent 模式保持 | 完成 | manifest `desktop_self_contained=false`、`dotnet_runtime_required=true` |
| Desktop 正式 publish 输入验收 | 完成 | strict 要求 exe/dll/deps/runtimeconfig，拒绝 `Avalonia.Diagnostics.dll` |
| clean clone strict 证明 | 完成 | P+5e `release_strict=true` 且生成 zip/sha256 |

## 2. 正式验证顺序

当前已验证的正式顺序：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py `
  --locked `
  --output .tmp\FlowWeaverReleasePython312

.\python312\python.exe tools\create_portable_layout.py `
  --output .tmp\FlowWeaverPortable `
  --python-runtime-dir .tmp\FlowWeaverReleasePython312 `
  --no-desktop-build

.\python312\python.exe tools\publish_desktop.py `
  --output .tmp\FlowWeaverPortable\Desktop

.\python312\python.exe tools\create_portable_archive.py `
  --input .tmp\FlowWeaverPortable `
  --output .tmp\dist `
  --release-strict
```

该顺序的职责分离：

| 步骤 | 责任 |
| --- | --- |
| `create_release_python_runtime.py --locked` | 生成干净、锁定、可复现 Python runtime |
| `create_portable_layout.py --python-runtime-dir ... --no-desktop-build` | 生成便携目录骨架并接入 release runtime |
| `publish_desktop.py --output ...\Desktop` | 生成正式 Release framework-dependent Desktop payload |
| `create_portable_archive.py --release-strict` | 归档并执行正式发布输入门禁 |

## 3. strict 当前门禁

`--release-strict` 当前会拒绝：

- runtime audit warning 或 rejected
- third-party license warning
- git commit 不可用
- git worktree dirty
- `Desktop/Avalonia_UI.exe` 缺失
- Desktop payload 不完整
- `Desktop/Avalonia.Diagnostics.dll` 存在
- `self-contained` Desktop 模式

## 4. clean clone 验证摘要

P+5e clean clone 验证结果：

```text
release_strict: true
git_dirty: false
runtime_audit_status: checked
desktop_self_contained: false
dotnet_runtime_required: true
third_party_warnings: []
package_count: 53
copied_dotnet_license_count: 1
archive: FlowWeaverPortable-0.1.0-win-x64.zip
sha256: 80006ea65f15baa8dbb179082f87d44af90b3f92de3c6efc3ee4415477cb9fc0
```

## 5. 当前明确不支持

以下能力仍不属于阶段P正式发布前置范围：

- 安装器
- 代码签名
- 自动更新
- 后台服务
- 系统托盘
- self-contained Desktop
- 跨平台发布包
- release notes 自动生成
- GitHub Release 上传
- CI/CD 自动发布流水线

## 6. 主工作区遗留边界

主工作区仍有未跟踪文件：

```text
docs/UI组件MainWindow的后续计划.MD
```

这会导致主工作区直接执行 strict 时触发：

```text
git_worktree_dirty
```

该文件需要用户后续决定是否提交、外置或纳入 UI 阶段文档整理。它不影响 P+5e 对已提交 HEAD 的 clean clone strict 证明。

## 7. 下一阶段建议

阶段P正式发布前置已具备：

- 可生成 strict zip
- 可生成 sha256
- manifest 和许可证 metadata 完整
- Desktop 仍保持 framework-dependent
- 发布输入门禁可拒绝常见脏输入

下一阶段建议不要继续扩大 P 阶段，而是进入独立 Distribution 方向分析，候选主题包括：

1. release checklist / release notes 手工模板
2. GitHub Release 或人工发布目录规范
3. 安装器评估
4. 代码签名评估
5. self-contained Desktop 独立评估
6. 自动更新/后台服务/系统托盘的后置产品决策
