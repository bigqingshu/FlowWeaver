# FlowWeaver 阶段P.1：发布归档脚本方案

> 文档状态：阶段P.1方案完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录、阶段P.0和阶段P.0a文档
> 适用范围：`tools/create_portable_archive.py` 的参数、版本来源、Desktop publish mode、runtime audit、manifest、SHA-256、许可证和安全检查方案
> 当前执行点：只做方案和接口边界，不新增归档脚本、不生成 zip、不清理 runtime

## 1. 目标

P.1 的目标是把发布归档脚本的最小契约固化，作为 P.2 runtime audit 和 P.3 最小 zip 归档实现的直接依据。

P.1 只确认：

- `tools/create_portable_archive.py` 的职责和 CLI 参数
- 归档输入、输出和路径约束
- 统一版本来源和拒绝条件
- Desktop 发布模式默认保持 framework-dependent
- Python runtime audit 如何表达通过、警告和拒绝
- `release-manifest.json` 第一版 schema
- zip 外部 `.sha256` 的生成位置和格式
- `licenses/` 目录的来源和最小内容
- 归档前安全扫描与拒绝边界
- P.4 clean-room smoke 对 P.3 归档产物的输入要求

P.1 不做：

- 不新增 `tools/create_portable_archive.py`
- 不修改 `tools/create_portable_layout.py`
- 不修改 `tools/publish_desktop.py`
- 不修改 `python312/`
- 不执行 `dotnet publish`
- 不生成 zip
- 不生成 manifest
- 不新增 clean-room smoke 测试
- 不编写用户手册正文

## 2. 当前事实

当前已有发布前置能力：

| 能力 | 文件 | 当前状态 |
| --- | --- | --- |
| 便携目录生成 | `tools/create_portable_layout.py` | 可生成 `.tmp/FlowWeaverPortable/` |
| 后端入口 | `start_flowweaver.cmd` | 固定 `portable_launcher.py --no-desktop` |
| 桌面组合入口 | `start_flowweaver_desktop.cmd` | 默认 `portable_launcher.py` |
| Desktop publish | `tools/publish_desktop.py` | 默认 `self_contained=False` |
| 项目版本 | `pyproject.toml` | `project.version = "0.1.0"` |
| Desktop 版本 | `Avalonia_UI/Avalonia_UI.csproj` | 当前无显式 `Version` |
| 仓库许可证 | `LICENSE` | MIT |

因此 P.3 的最小归档脚本应以现有便携目录为输入，而不是重新实现 layout 生成或 Desktop publish。

## 3. 脚本职责

拟新增脚本：

```text
tools/create_portable_archive.py
```

职责边界：

1. 读取一个已经生成好的便携目录，例如 `.tmp/FlowWeaverPortable/`
2. 执行发布归档前检查
3. 生成 `release-manifest.json`
4. 生成 `licenses/` 最小许可证目录
5. 打包 zip
6. 在 zip 旁边生成 `.sha256`
7. 输出归档摘要

明确不负责：

- 不调用 `dotnet publish`
- 不调用 `create_portable_layout.py`
- 不自动清理或改写 `python312/`
- 不写入真实 token
- 不执行 EngineHost smoke
- 不上传、不签名、不创建安装器

## 4. CLI 参数方案

P.3 最小实现建议支持：

```powershell
.\python312\python.exe tools\create_portable_archive.py `
  --input .tmp\FlowWeaverPortable `
  --output .tmp\dist `
  --version 0.1.0 `
  --target-runtime win-x64 `
  --desktop-publish-mode framework-dependent
```

参数建议：

| 参数 | 默认值 | 要求 |
| --- | --- | --- |
| `--input` | `.tmp/FlowWeaverPortable` | 必须是已存在目录，且目录名建议为 `FlowWeaverPortable` |
| `--output` | `.tmp/dist` | 必须位于仓库 `.tmp/` 内，P.3 阶段不允许写仓库外 |
| `--version` | 读取 `pyproject.toml` | 显式传入时必须等于 `pyproject.toml`，除非未来新增 `--allow-version-override` |
| `--target-runtime` | `win-x64` | P阶段只接受 `win-x64` |
| `--desktop-publish-mode` | `framework-dependent` | P阶段默认只接受 `framework-dependent` |
| `--runtime-audit-mode` | `strict` | `strict` 下有拒绝项必须失败 |
| `--force` | 不启用 | P阶段暂不建议实现，避免覆盖发布物 |

P.3 生成文件名：

```text
FlowWeaverPortable-<version>-win-x64.zip
FlowWeaverPortable-<version>-win-x64.zip.sha256
```

输出目录示例：

```text
.tmp/dist/
  FlowWeaverPortable-0.1.0-win-x64.zip
  FlowWeaverPortable-0.1.0-win-x64.zip.sha256
```

## 5. 版本来源与一致性

版本来源优先级：

| 优先级 | 来源 | P阶段处理 |
| --- | --- | --- |
| 1 | `--version` | 如传入，必须与 `pyproject.toml` 一致 |
| 2 | `pyproject.toml` 的 `project.version` | 默认来源 |
| 3 | git tag / CI build number | P阶段暂不接入 |

P.3 不应自动修改 `.csproj`，也不应把 Desktop 无显式版本视为失败。manifest 中先记录：

```json
{
  "release_version": "0.1.0",
  "python_project_version": "0.1.0",
  "desktop_project_version": null
}
```

拒绝条件：

- `--version` 与 `pyproject.toml` 不一致
- `--target-runtime` 不是 `win-x64`
- 归档文件名中缺失 `release_version`
- manifest 中版本字段无法写入

## 6. Desktop publish mode

P阶段默认：

```text
desktop_publish_mode = framework-dependent
desktop_self_contained = false
dotnet_target_framework = net10.0
desktop_runtime_identifier = win-x64
dotnet_runtime_required = true
```

P.3 归档脚本只记录事实，不调用 `dotnet publish`，也不切换 self-contained。

如果用户显式传入：

```powershell
--desktop-publish-mode self-contained
```

P.3 最小实现应直接拒绝，提示 self-contained 需要单独阶段验证后再开放。

## 7. Runtime audit 合约

P.2 应先实现可复用 audit；P.3 只调用 audit 结果。

建议 audit 输出：

```json
{
  "status": "checked",
  "python_version": "3.12.10",
  "pip_version": "26.1.2",
  "errors": [],
  "warnings": [],
  "rejected_paths": [],
  "excluded_paths": []
}
```

状态定义：

| 状态 | 含义 | P.3 行为 |
| --- | --- | --- |
| `checked` | 未发现阻断项 | 允许归档 |
| `warning` | 有风险但可归档 | 写入 manifest 并继续 |
| `rejected` | 有阻断项 | 拒绝生成 zip |
| `unchecked` | 未执行 audit | strict 模式拒绝 |

P.2 最小检查项：

| 检查项 | 默认结果 |
| --- | --- |
| `python312/python.exe` 存在 | 缺失则拒绝 |
| Python 版本为 3.12.x | 不匹配则拒绝 |
| `python312/python312._pth` 启用 `import site` | 缺失则拒绝 |
| dev/test 包存在 | `strict` 下警告或拒绝由 P.2 明确 |
| `__pycache__` / `*.pyc` | 归档时默认排除并记录 |
| `EngineHost/runtime/` | 必须拒绝 |
| 真实 token 文件 | 必须拒绝 |

P.1 决策：P.2 先实现 audit，不在 P.1/P.2 清理 runtime；P.3 只允许在 audit 通过后归档。

## 8. Manifest schema 第一版

zip 内部必须包含：

```text
FlowWeaverPortable/release-manifest.json
```

建议 schema：

```json
{
  "manifest_schema_version": 1,
  "package_kind": "portable",
  "release_version": "0.1.0",
  "archive_name": "FlowWeaverPortable-0.1.0-win-x64.zip",
  "target_runtime": "win-x64",
  "created_at_utc": "2026-06-30T00:00:00Z",
  "git_commit": null,
  "git_dirty": false,
  "python_project_version": "0.1.0",
  "desktop_project_version": null,
  "desktop_publish_mode": "framework-dependent",
  "desktop_self_contained": false,
  "dotnet_runtime_required": true,
  "dotnet_target_framework": "net10.0",
  "desktop_runtime_identifier": "win-x64",
  "python_version": "3.12.10",
  "pip_version": "26.1.2",
  "runtime_audit_status": "checked",
  "entries": [
    {
      "path": "FlowWeaverPortable/start_flowweaver.cmd",
      "size": 123,
      "sha256": "..."
    }
  ],
  "excluded_paths": [
    "FlowWeaverPortable/EngineHost/runtime/"
  ],
  "licenses": [
    {
      "name": "FlowWeaver",
      "path": "FlowWeaverPortable/licenses/FlowWeaver-LICENSE.txt",
      "kind": "project"
    }
  ]
}
```

约束：

- manifest 中 `entries` 只记录 zip 内文件，不记录目录
- `entries` 路径统一使用 `/`
- `release-manifest.json` 自身也应进入 `entries`
- zip 外部 `.sha256` 不进入 manifest
- 不记录 token 内容、Authorization header、完整 WebSocket URL

## 9. SHA-256 文件

外部 hash 文件格式建议：

```text
<sha256>  FlowWeaverPortable-0.1.0-win-x64.zip
```

要求：

- `.sha256` 与 zip 位于同一目录
- hash 只针对最终 zip 文件
- 文件使用 UTF-8，无 BOM 要求
- P.3 测试应重新读取 zip 并验证 `.sha256` 匹配

## 10. Licenses 目录

zip 内部建议包含：

```text
FlowWeaverPortable/licenses/
  FlowWeaver-LICENSE.txt
  Python-LICENSE.txt
  third-party-licenses.json
```

P.3 最小策略：

| 文件 | 来源 | P.3 要求 |
| --- | --- | --- |
| `FlowWeaver-LICENSE.txt` | 仓库根 `LICENSE` | 必须存在 |
| `Python-LICENSE.txt` | `python312/LICENSE.txt` | 缺失时 strict 模式拒绝 |
| `third-party-licenses.json` | P.3 生成占位摘要 | 允许先记录包名和版本，许可证正文后续扩展 |

`third-party-licenses.json` 第一版可先包含：

```json
{
  "status": "summary-only",
  "packages": []
}
```

但如果 runtime audit 已发现无法追溯的运行依赖，P.3 应拒绝正式归档或标记 `runtime_audit_status=rejected`。

## 11. 安全扫描与拒绝项

归档脚本必须拒绝包含：

- `EngineHost/runtime/`
- `Desktop/runtime/`
- `.git/`
- `.venv/`
- `.tmp/` 嵌套目录
- `.pytest_cache/`
- `__pycache__/`
- `*.pyc`
- `flowweaver.db`
- `local_api_token`
- `*.stdout.log`
- `*.stderr.log`
- `portable-launcher.log`

文本扫描建议覆盖：

| 文本 | 处理 |
| --- | --- |
| `Authorization:` | 拒绝 |
| `Bearer ` | 拒绝 |
| `token=` | 拒绝 |
| `api_token` | 视文件位置决定，代码中的字段名允许 |
| `ws://127.0.0.1` | 允许文档示例，但不得带 token |

P.3 最小实现应先用路径拒绝保证安全，文本扫描作为第二层。

## 12. P.4 clean-room 输入要求

P.3 归档产物必须能被 P.4 使用：

```text
%TEMP%\FlowWeaver Clean Room 中文路径 <uuid>\FlowWeaverPortable\
```

P.4 只接受：

- `.tmp/dist/FlowWeaverPortable-<version>-win-x64.zip`
- 对应 `.zip.sha256`
- zip 内有 `FlowWeaverPortable/release-manifest.json`
- zip 内有 `start_flowweaver.cmd`
- zip 内有 `EngineHost/python312/python.exe`
- 首次解压后没有 `EngineHost/runtime/`

P.4 backend-only smoke 不依赖仓库工作目录，不读取仓库源码。

## 13. 建议测试边界

P.2 建议新增：

```text
tests/unit/test_portable_runtime_audit.py
```

覆盖：

- 缺失 `python312/python.exe` 拒绝
- runtime 中有 `EngineHost/runtime/` 拒绝
- `__pycache__` / `*.pyc` 进入排除列表
- dev/test 包识别结果可进入 warnings 或 rejected

P.3 建议新增：

```text
tests/unit/test_create_portable_archive.py
```

覆盖：

- 版本读取和显式版本一致性
- output 必须在 `.tmp/`
- self-contained 显式模式拒绝
- 生成 zip、manifest 和 `.sha256`
- zip 内不包含 runtime、token、logs、pyc
- `.sha256` 与 zip 实际 hash 一致
- manifest entries 的路径、大小和 hash 与 zip 内容一致

P.4 建议新增：

```text
tests/integration/test_p4_portable_archive_clean_room_smoke.py
```

覆盖：

- 解压到仓库外空格/中文路径
- 清理 `PYTHONPATH`
- 使用 `start_flowweaver.cmd` 或等价 backend-only 命令启动
- health 和 `GET /api/v1/workflows` 鉴权通过

## 14. P.1 修改清单

本阶段只修改：

- 新增 `docs/FlowWeaver_阶段P.1_发布归档脚本方案.md`
- 更新 `README.md` 阶段记录和下一步建议

本阶段不修改源码、测试或发布脚本。

## 15. 验收

P.1 验收条件：

- P.1 文档明确 `tools/create_portable_archive.py` 的方案边界
- 明确 Desktop 默认保持 framework-dependent
- 明确 runtime audit 先于 zip 实现
- 明确 manifest、SHA-256、licenses 和安全拒绝项
- README 已指向 P.2 作为下一步
- `git diff --check` 通过

## 16. 下一步建议

进入 P.2：runtime audit 与归档前检查。

P.2 建议先实现可单测的 audit helper，不生成 zip，不清理 runtime。完成后，P.3 再接入最小 archive 脚本。
