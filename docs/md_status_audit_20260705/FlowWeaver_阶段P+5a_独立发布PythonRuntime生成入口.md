# FlowWeaver 阶段P+5a：独立发布 Python runtime 生成入口

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+5a完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1-P+4a 和 P+5 边界分析
> 适用范围：独立 release Python runtime 生成入口、portable layout 可选 runtime 接入、runtime audit 副作用修正
> 当前执行点：只生成 `.tmp/` 下独立发布 runtime，不原地清理开发用 `python312/`，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 阶段目标

P+5a 的目标是把 P+5 的建议落成最小入口：

- 新增独立发布 runtime 生成工具
- 不修改、不卸载、不清理 repo-local `python312/`
- 让 `create_portable_layout.py` 可以选择复制该发布 runtime
- 修正 runtime audit 自身写入 pip bytecode cache 的副作用

## 2. 新增入口

新增：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py
```

默认输出：

```text
.tmp/FlowWeaverReleasePython312/
```

默认行为：

1. 从 repo-local `python312/` 复制 embedded Python 基础文件
2. 清空输出 runtime 的 `Lib/site-packages`
3. 只从源 runtime 保留 `pip`
4. 根据 `pyproject.toml` 的 `project.dependencies` 安装运行依赖
5. 清理 `__pycache__` 和 `*.pyc`

可选参数：

| 参数 | 说明 |
| --- | --- |
| `--source <path>` | 指定源 embedded Python 目录，默认 `python312/` |
| `--output <path>` | 指定输出目录，必须位于 repo `.tmp/` 下 |
| `--no-clean` | 不删除已有输出目录；若目录已存在会拒绝 |
| `--no-install` | 只复制 Python 基础和 pip，不安装运行依赖 |

## 3. portable layout 接入

`tools/create_portable_layout.py` 新增可选参数：

```powershell
.\python312\python.exe tools\create_portable_layout.py `
  --python-runtime-dir .tmp\FlowWeaverReleasePython312
```

默认行为保持不变：

- 未指定 `--python-runtime-dir` 时继续复制 repo-local `python312/`
- `--no-python` 仍可跳过 Python runtime
- 现有 N/O/P smoke 默认路径不变

这让后续发布流水线可以变成：

```text
create_release_python_runtime
-> create_portable_layout --python-runtime-dir <release-runtime>
-> create_portable_archive --release-strict
```

## 4. runtime audit 副作用修正

P+5a 真实 smoke 中发现：

```text
portable_runtime_audit -> python -m pip --version
```

会导入 pip 并生成 `__pycache__`，从而让本来干净的 release runtime 被 audit 自己制造出 `excluded_cache_paths_present` warning。

本阶段已将 `tools/portable_runtime_audit.py` 的默认 subprocess 环境加入：

```text
PYTHONDONTWRITEBYTECODE=1
```

这样 audit 读取 pip 版本时不再写入 bytecode cache。

## 5. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_release_python_runtime.py` | 新增独立发布 runtime 生成入口 |
| `tools/create_portable_layout.py` | 新增 `python_runtime_dir` / `--python-runtime-dir` 可选接入点 |
| `tools/portable_runtime_audit.py` | 子进程禁写 bytecode，避免 audit 自身制造 cache warning |
| `tests/unit/test_create_release_python_runtime.py` | 覆盖独立输出、保留 pip、移除非运行包、跳过安装和输出路径保护 |
| `tests/unit/test_create_portable_layout.py` | 覆盖 portable layout 复制自定义 Python runtime |
| `docs/FlowWeaver_阶段P+5a_独立发布PythonRuntime生成入口.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+5a 阶段记录和下一步建议 |

## 6. 验收结果

单元和静态检查：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_release_python_runtime.py tests\unit\test_create_portable_layout.py tests\unit\test_portable_runtime_audit.py
.\python312\python.exe -m ruff check tools\create_release_python_runtime.py tools\create_portable_layout.py tools\portable_runtime_audit.py tests\unit\test_create_release_python_runtime.py tests\unit\test_create_portable_layout.py tests\unit\test_portable_runtime_audit.py
```

结果：

```text
pytest: 17 passed
ruff: All checks passed!
```

真实生成 smoke：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --output .tmp\P5aReleasePythonSmoke
.\python312\python.exe tools\create_portable_layout.py --output .tmp\P5aPortableRuntimeSmoke --python-runtime-dir .tmp\P5aReleasePythonSmoke --no-desktop-build
.\python312\python.exe tools\portable_runtime_audit.py --input .tmp\P5aPortableRuntimeSmoke
```

结果：

```text
runtime audit status: checked
errors: []
warnings: []
rejected_paths: []
excluded_paths: []
```

smoke 结束后已清理 `.tmp\P5aReleasePythonSmoke` 和 `.tmp\P5aPortableRuntimeSmoke`。

## 7. 当前边界

P+5a 仍不宣称：

- 不替换默认 layout 的 repo-local `python312/`
- 不让 `create_portable_archive --release-strict` 全链路通过
- 不做 Desktop build / NuGet metadata / dirty git 等 release strict 其他门禁收口
- 不移除 pip
- 不解析或强制使用 `uv.lock`

当前安装运行依赖使用 `pyproject.toml` 的版本范围，因此可得到干净 runtime，但不是完全确定性的锁定发布 runtime。

## 8. 下一步建议

下一小步建议进入 P+5b：release runtime 锁定与 strict 前置复核。

建议范围：

- 分析是否用 `uv.lock` 生成固定版本要求
- 确认 release runtime 依赖版本与项目锁文件一致
- 用 release runtime 生成完整 portable layout
- 补 Desktop build 和 NuGet metadata 后，再尝试 `create_portable_archive --release-strict`
