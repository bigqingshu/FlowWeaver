# FlowWeaver 阶段P+5c：release strict 前置复核与 NuGet 文件许可证收口

> 文档状态：阶段P+5c完成
> 当前执行点：复核 `--release-strict` 组合门禁，并只修正 P 阶段必要的许可证元数据误判；不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 复核目标

P+5b 已经让 release Python runtime 可以通过 `uv.lock` 固定版本和 wheel hash 生成。P+5c 的目标是把该 runtime 接入完整 portable layout，并尝试正式归档门禁：

```text
create_release_python_runtime --locked
-> create_portable_layout --python-runtime-dir <locked runtime>
-> create_portable_archive --release-strict
```

本阶段不以“强行通过 strict”为目标，而是先确认真实阻断项，并只修复属于当前 P 阶段边界内的后端归档元数据问题。

## 2. 初次 strict 复核结果

执行：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --locked --output .tmp\P5cReleasePythonPreflight
.\python312\python.exe tools\create_portable_layout.py --output .tmp\P5cPortablePreflight --python-runtime-dir .tmp\P5cReleasePythonPreflight
.\python312\python.exe tools\create_portable_archive.py --input .tmp\P5cPortablePreflight --output .tmp\P5cDist --release-strict
```

结果：

```text
error: release strict rejected portable input: git_worktree_dirty, third_party_license_warning
```

拆解结果：

| 阻断项 | 根因 |
| --- | --- |
| `git_worktree_dirty` | 当前工作区存在未跟踪的 `docs/UI组件MainWindow的后续计划.MD`，且阶段代码尚未提交时也会触发 dirty |
| `third_party_license_warning` | `Avalonia.Angle.Windows.Natives 2.1.25547.20250602` 的 NuGet 包使用 `<license type="file">LICENSE</license>`，但归档器此前只识别 `<license type="expression">...` |

非 strict 归档定位到具体 warning：

```text
warnings: ['nuget_license_metadata_unavailable']
dotnet Avalonia.Angle.Windows.Natives 2.1.25547.20250602 ['nuget_license_metadata_unavailable'] project.assets.json
```

本机 NuGet 缓存中实际存在：

```text
~/.nuget/packages/avalonia.angle.windows.natives/2.1.25547.20250602/avalonia.angle.windows.natives.nuspec
~/.nuget/packages/avalonia.angle.windows.natives/2.1.25547.20250602/LICENSE
```

因此该项属于“合法 NuGet file license 未被识别”的归档元数据缺口，而不是许可证文件实际缺失。

## 3. 最小修正

本阶段扩展 `tools/create_portable_archive.py` 的 NuGet 元数据处理：

- 保留既有 `<license type="expression">MIT</license>` 行为
- 新增 `<license type="file">LICENSE</license>` 识别
- 从本机 NuGet 包缓存读取声明的许可证文件
- 将文件复制到发布归档：

```text
FlowWeaverPortable/licenses/third-party/dotnet/<PackageName>/<Version>/<LicenseFile>
```

- 在 `third-party-licenses.json` 中写入：

```json
{
  "license_files": ["nuget-cache/<package>/<version>/LICENSE"],
  "copied_license_files": [
    "FlowWeaverPortable/licenses/third-party/dotnet/<PackageName>/<Version>/LICENSE"
  ],
  "license_status": "license_file_found",
  "warnings": []
}
```

仍然不做：

- NuGet 联网补元数据
- NuGet 许可证正文全文分析
- licenseUrl 兜底
- 安装器或签名链路

## 4. 修正后 strict 复测

修正后，使用相同 portable 输入重新执行：

```powershell
.\python312\python.exe tools\create_portable_archive.py --input .tmp\P5cPortablePreflight --output .tmp\P5cDistStrictAfterNuGetFix --release-strict
```

结果：

```text
error: release strict rejected portable input: git_worktree_dirty
```

这说明 `third_party_license_warning` 已消除，当前 strict 仅剩工作区 dirty 阻断。

## 5. Desktop publish 来源观察

当前机器上存在：

```text
Avalonia_UI/bin/Debug/net10.0/Avalonia_UI.exe
Avalonia_UI/bin/Release/net10.0/win-x64/Avalonia_UI.exe
```

但不存在：

```text
Avalonia_UI/bin/Release/net10.0/win-x64/publish/
```

`create_portable_layout.py` 当前优先复制 Release publish 目录；若不存在，则回退 Debug `net10.0` 目录。P+5c 没有改变该行为。

这意味着：

- 当前 strict 只要求 `Desktop/Avalonia_UI.exe` 存在
- 当前 strict 不区分该 exe 来自 Release publish 还是 Debug build
- 正式发布前仍建议单独收口 Desktop publish 来源边界

## 6. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_archive.py` | NuGet metadata 支持 `license type="file"`，并复制 NuGet 包许可证文件 |
| `tests/unit/test_create_portable_archive.py` | 新增 NuGet file license 归档和 metadata 断言 |
| `docs/FlowWeaver_阶段P+5c_releaseStrict前置复核与NuGet文件许可证收口.md` | 固化 P+5c 复核和修正结果 |
| `README.md` | 更新 P+5c 阶段记录和下一步方向 |

## 7. 验收结果

单元和静态检查：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tests\unit\test_create_portable_archive.py
```

结果：

```text
pytest: 19 passed
ruff: All checks passed!
```

P+5c 真实 strict 复测：

```text
third_party_license_warning 已消除
剩余阻断：git_worktree_dirty
```

复核产生的 `.tmp\P5cReleasePythonPreflight`、`.tmp\P5cPortablePreflight`、`.tmp\P5cDist`、`.tmp\P5cDistNonStrict` 和 `.tmp\P5cDistStrictAfterNuGetFix` 已清理。

## 8. 下一步建议

下一小步建议进入 P+5d：正式 Desktop publish 来源边界复核。

建议先只分析，不急着改默认开发行为：

1. 明确正式 release strict 是否必须要求 `Avalonia_UI/bin/Release/net10.0/win-x64/publish`
2. 若必须要求，决定是在 layout 阶段写入 build source marker，还是 archive strict 阶段检查 Desktop payload
3. 保留默认开发 layout 的 Debug fallback
4. 明确 untracked 用户文档导致 dirty git 时，正式 strict 需要先提交/移除/外置该文件
