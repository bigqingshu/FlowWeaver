# FlowWeaver 阶段P+5d：正式 Desktop Publish 来源边界收口

> 文档状态：阶段P+5d完成
> 当前执行点：只收口 release strict 的 Desktop payload 输入验收，不改变默认开发 layout，不调用安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 背景

P+5c 复核时发现：

```text
create_portable_layout.py
```

会优先复制：

```text
Avalonia_UI/bin/Release/net10.0/win-x64/publish/
```

如果该目录不存在，会回退复制：

```text
Avalonia_UI/bin/Debug/net10.0/
```

这对开发 smoke 很方便，但不应被误认为正式发布 Desktop 输入。

阶段 N.6 已明确正式 Desktop 发布入口是：

```powershell
.\python312\python.exe tools\publish_desktop.py --output <portable-layout>\Desktop
```

该工具默认：

- `configuration = Release`
- `runtime = win-x64`
- `self_contained = false`
- 输出 framework-dependent Desktop payload

## 2. P+5d 决策

P+5d 不让 `create_portable_archive.py` 调用 `dotnet publish`。

原因：

- P.1/P.3 已明确归档脚本只接收已有便携目录
- Desktop publish 是独立工具职责
- 归档阶段不应隐式重新构建 UI
- 不应在 P 阶段切换 self-contained

P+5d 的最小收口点是：

```text
--release-strict 只检查输入是否像正式 Desktop payload
```

而不是负责生成该 payload。

## 3. release strict 新增 Desktop 验收

`tools/create_portable_archive.py --release-strict` 新增两类检查。

必须存在：

```text
Desktop/Avalonia_UI.exe
Desktop/Avalonia_UI.dll
Desktop/Avalonia_UI.deps.json
Desktop/Avalonia_UI.runtimeconfig.json
```

若缺失任意项，strict 增加：

```text
desktop_payload_incomplete
```

若缺失 exe，仍保留既有：

```text
desktop_executable_missing
```

明确拒绝 Debug 产物信号：

```text
Desktop/Avalonia.Diagnostics.dll
```

若存在，strict 增加：

```text
desktop_debug_payload_present
```

## 4. 默认开发路径不变

P+5d 不改变 `create_portable_layout.py` 的默认行为。

也就是说，开发或调试时仍可：

- 直接复制已有 Release publish
- 或在 Release publish 不存在时回退 Debug build
- 或显式传 `--no-desktop-build`
- 或后续再运行 `tools/publish_desktop.py --output <layout>\Desktop`

只有正式 `--release-strict` 归档会执行新增 Desktop payload 检查。

## 5. 正式发布前推荐顺序

推荐正式路径：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --locked --output .tmp\FlowWeaverReleasePython312
.\python312\python.exe tools\create_portable_layout.py --output .tmp\FlowWeaverPortable --python-runtime-dir .tmp\FlowWeaverReleasePython312 --no-desktop-build
.\python312\python.exe tools\publish_desktop.py --output .tmp\FlowWeaverPortable\Desktop
.\python312\python.exe tools\create_portable_archive.py --input .tmp\FlowWeaverPortable --output .tmp\dist --release-strict
```

该顺序避免 layout 复制 Debug fallback，并让 Desktop 发布职责仍停留在 `publish_desktop.py`。

## 6. 真实复测结果

执行：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --locked --output .tmp\P5dReleasePythonPreflight
.\python312\python.exe tools\create_portable_layout.py --output .tmp\P5dPortablePreflight --python-runtime-dir .tmp\P5dReleasePythonPreflight --no-desktop-build
.\python312\python.exe tools\publish_desktop.py --output .tmp\P5dPortablePreflight\Desktop
.\python312\python.exe tools\create_portable_archive.py --input .tmp\P5dPortablePreflight --output .tmp\P5dDist --release-strict
```

结果：

```text
error: release strict rejected portable input: git_worktree_dirty
```

说明在正式 Desktop publish 输入下：

- Python runtime audit 已通过
- NuGet file license warning 已消除
- Desktop payload strict 检查已通过
- 当前仅剩工作区 dirty 阻断

当前 dirty 来源仍包括未跟踪文档：

```text
docs/UI组件MainWindow的后续计划.MD
```

P+5d 复核产生的 `.tmp\P5dReleasePythonPreflight`、`.tmp\P5dPortablePreflight` 和 `.tmp\P5dDist` 已清理。

## 7. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_archive.py` | release strict 新增 Desktop payload 完整性和 Debug diagnostics 拒绝检查 |
| `tests/unit/test_create_portable_archive.py` | 覆盖 strict clean payload、缺失 payload 和 Debug diagnostics 拒绝 |
| `docs/FlowWeaver_阶段P+5d_正式DesktopPublish来源边界收口.md` | 固化 P+5d 决策、正式顺序和真实复测结果 |
| `README.md` | 更新 P+5d 阶段记录和下一步方向 |

## 8. 验收结果

单元和静态检查：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tests\unit\test_create_portable_archive.py
```

结果：

```text
pytest: 20 passed
ruff: All checks passed!
```

## 9. 下一步建议

下一小步建议进入 P+5e：dirty git 与正式 strict 最终复核边界。

建议先只处理决策，不自动处置用户文件：

1. 明确未跟踪的 `docs/UI组件MainWindow的后续计划.MD` 是否应提交、移动到外部、加入后续 UI 文档阶段，或保持未跟踪
2. 在工作区干净后，按 P+5d 推荐正式顺序再跑一次 `--release-strict`
3. 若 strict 通过，再做 P 阶段正式发布前置完成清单
