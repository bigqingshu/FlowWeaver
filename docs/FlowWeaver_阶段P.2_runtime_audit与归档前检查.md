# FlowWeaver 阶段P.2：runtime audit 与归档前检查

> 文档状态：阶段P.2完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录、阶段P.0、阶段P.0a和阶段P.1文档
> 适用范围：便携发布目录中的 `EngineHost/python312/` 运行时审计和归档前拒绝项识别
> 当前执行点：只实现 audit helper 和单元测试，不生成 zip、不清理 runtime、不改变 Desktop 发布模式

## 1. 目标

P.2 的目标是把 P.1 定义的 runtime audit 合约落成可复用、可单测的 helper，让 P.3 最小归档脚本能够在写 zip 前获得明确的审计结果。

本阶段完成：

- 新增 `tools/portable_runtime_audit.py`
- 新增 `tests/unit/test_portable_runtime_audit.py`
- 明确阻断项、warning 项和可排除项
- 提供 JSON 友好的 `RuntimeAuditResult.to_dict()`
- 提供只读 CLI：`tools/portable_runtime_audit.py --input <portable_root>`
- 更新 README 阶段记录和下一步建议

本阶段不做：

- 不新增 `tools/create_portable_archive.py`
- 不生成 zip
- 不生成 `release-manifest.json`
- 不生成 `.sha256`
- 不清理仓内或便携目录中的 `python312/`
- 不删除 dev/test/build 包
- 不执行 clean-room smoke
- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/publish_desktop.py`

## 2. 新增 helper

新增文件：

```text
tools/portable_runtime_audit.py
```

核心入口：

```python
audit_portable_runtime(
    portable_root: Path,
    *,
    command_runner: CommandRunner | None = None,
    runtime_audit_mode: Literal["strict"] = "strict",
) -> RuntimeAuditResult
```

默认输入是：

```text
.tmp/FlowWeaverPortable/
```

审计对象是便携目录中的：

```text
FlowWeaverPortable/EngineHost/python312/
```

P.2 只读取目录和运行 `python.exe --version`、`python.exe -m pip --version`，不修改任何文件。

## 3. 审计结果模型

`RuntimeAuditResult` 字段：

| 字段 | 含义 |
| --- | --- |
| `status` | `checked` / `warning` / `rejected` |
| `python_version` | 解析到的 Python 版本 |
| `pip_version` | 解析到的 pip 版本，无法读取时为 `None` |
| `errors` | 阻断项 |
| `warnings` | 风险项 |
| `rejected_paths` | 不允许进入归档的路径 |
| `excluded_paths` | 后续归档时应排除的 cache 路径 |
| `packages` | 从 `*.dist-info` 识别到的包名、版本和路径 |

状态计算：

| 状态 | 条件 |
| --- | --- |
| `rejected` | 存在任何 `errors` |
| `warning` | 无 `errors`，但存在 `warnings` |
| `checked` | 无 `errors` 且无 `warnings` |
| `unchecked` | P.2 helper 不直接生成；留给 P.3 表达未执行 audit 的情况 |

## 4. 阻断项

P.2 将以下情况视为阻断：

| code | 条件 |
| --- | --- |
| `portable_root_missing` | 输入便携目录不存在 |
| `python_exe_missing` | 缺少 `EngineHost/python312/python.exe` |
| `python_version_unavailable` | 无法读取 Python 版本 |
| `python_version_unparseable` | Python 版本输出无法解析 |
| `python_version_unsupported` | Python 版本不是 `3.12.x` |
| `python_pth_missing` | 缺少 `python312._pth` |
| `python_site_disabled` | `python312._pth` 未启用 `import site` |
| `python_license_missing` | 缺少 `python312/LICENSE.txt` |
| `rejected_path_present` | 出现 runtime、token、db、log 或禁止目录 |

阻断路径包括：

- `EngineHost/runtime/`
- `Desktop/runtime/`
- `.git/`
- `.tmp/`
- `.venv/`
- `.pytest_cache/`
- `flowweaver.db`
- `local_api_token`
- `portable-launcher.log`
- `*.stdout.log`
- `*.stderr.log`

这些路径一旦出现在便携输入目录，P.3 默认不得继续生成 zip。

## 5. Warning 项

P.2 将以下情况视为 warning：

| code | 条件 |
| --- | --- |
| `pip_version_unavailable` | 无法读取 pip 版本 |
| `pip_version_unparseable` | pip 版本输出无法解析 |
| `excluded_cache_paths_present` | 出现 `__pycache__/` 或 `*.pyc` |
| `dev_or_legacy_package_present` | 发现 dev/test/build 或旧 GUI 包 |

P.2 明确将 dev/test/build 和旧 GUI 包作为 warning，而不是阻断项。原因：

- P.2 不清理 runtime
- 当前仓内 `python312/` 已知可能包含 dev/test/build 包
- P.3 可以把 warning 写入 manifest，让归档产物明确不是“干净最小 runtime”
- 后续若要做正式 clean release，应新增单独小步清理或构建干净 runtime

当前识别的 warning 包集合包括：

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

## 6. Cache 排除项

P.2 不删除 cache，只记录：

- `__pycache__/`
- `*.pyc`

这些路径进入 `excluded_paths`，P.3 归档时应默认排除，并写入 manifest 的 `excluded_paths` 摘要。

## 7. CLI 使用

生成便携目录后，可运行：

```powershell
.\python312\python.exe tools\portable_runtime_audit.py --input .tmp\FlowWeaverPortable
```

CLI 输出 JSON：

```json
{
  "status": "warning",
  "python_version": "3.12.10",
  "pip_version": "26.1.2",
  "errors": [],
  "warnings": [],
  "rejected_paths": [],
  "excluded_paths": [],
  "packages": []
}
```

返回码：

| audit status | CLI 返回码 |
| --- | --- |
| `checked` | `0` |
| `warning` | `0` |
| `rejected` | `1` |

## 8. 单元测试

新增：

```text
tests/unit/test_portable_runtime_audit.py
```

覆盖：

- 最小 embedded runtime 通过
- 缺失 `python.exe` 拒绝
- `python312._pth` 未启用 `import site` 拒绝
- Python 非 3.12 拒绝
- `EngineHost/runtime/`、token、db、log 拒绝
- `__pycache__/` 和 `*.pyc` 进入 `excluded_paths`
- dev/legacy 包进入 warning
- pip 版本不可读进入 warning

## 9. 验证

本阶段已运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_runtime_audit.py
.\python312\python.exe -m ruff check tools\portable_runtime_audit.py tests\unit\test_portable_runtime_audit.py
```

## 10. 下一步建议

进入 P.3：最小归档脚本。

P.3 建议：

- 新增 `tools/create_portable_archive.py`
- 调用 `audit_portable_runtime()`
- `rejected` 时拒绝生成 zip
- `warning` 时允许生成最小归档，但必须写入 manifest
- 生成 `release-manifest.json`
- 生成 `licenses/`
- 生成 zip 和外部 `.sha256`
- 测试 zip 中不包含 runtime、token、db、logs、pyc/cache
