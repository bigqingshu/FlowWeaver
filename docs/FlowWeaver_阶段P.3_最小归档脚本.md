# FlowWeaver 阶段P.3：最小归档脚本

> 文档状态：阶段P.3完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录、阶段P.0、阶段P.0a、阶段P.1和阶段P.2文档
> 适用范围：从已生成的便携目录创建 zip、`release-manifest.json`、`licenses/` 和外部 `.sha256`
> 当前执行点：实现最小归档脚本和单元测试，不进入安装器、签名、上传或 clean-room smoke

## 1. 目标

P.3 的目标是把 P.1 的归档脚本方案和 P.2 的 runtime audit 结果接起来，生成第一版可供 P.4 clean-room smoke 使用的便携 zip。

本阶段完成：

- 新增 `tools/create_portable_archive.py`
- 调用 `audit_portable_runtime()`
- `rejected` 时拒绝生成 zip
- `warning` 时允许生成 zip，并把 warning 写入 manifest
- 生成 zip 内 `release-manifest.json`
- 生成 zip 内 `licenses/`
- 生成 zip 外 `.sha256`
- 新增 `tests/unit/test_create_portable_archive.py`
- 更新 README 阶段记录和下一步建议

本阶段不做：

- 不调用 `dotnet publish`
- 不调用 `create_portable_layout.py`
- 不清理 `python312/`
- 不创建安装器
- 不做代码签名
- 不上传发布物
- 不执行 P.4 clean-room smoke
- 不默认打开真实 Desktop

## 2. 新增脚本

新增文件：

```text
tools/create_portable_archive.py
```

最小 CLI：

```powershell
.\python312\python.exe tools\create_portable_archive.py `
  --input .tmp\FlowWeaverPortable `
  --output .tmp\dist `
  --version 0.1.0 `
  --target-runtime win-x64 `
  --desktop-publish-mode framework-dependent
```

默认值：

| 参数 | 默认值 |
| --- | --- |
| `--input` | `.tmp/FlowWeaverPortable` |
| `--output` | `.tmp/dist` |
| `--version` | `pyproject.toml` 的 `project.version` |
| `--target-runtime` | `win-x64` |
| `--desktop-publish-mode` | `framework-dependent` |

## 3. 输入输出

输入：

```text
.tmp/FlowWeaverPortable/
```

输出：

```text
.tmp/dist/
  FlowWeaverPortable-0.1.0-win-x64.zip
  FlowWeaverPortable-0.1.0-win-x64.zip.sha256
```

脚本不会回写输入目录；`release-manifest.json` 和 `licenses/` 只注入 zip 内部。

## 4. Runtime audit 接入

P.3 调用：

```python
audit_portable_runtime(input_dir)
```

处理规则：

| audit status | P.3 行为 |
| --- | --- |
| `checked` | 允许归档 |
| `warning` | 允许归档，并写入 manifest |
| `rejected` | 拒绝归档，不生成 zip |

当前真实便携目录的 audit 通常会返回 `warning`，因为仓内 `python312/` 中存在 dev/test/build 或旧 GUI 包。P.3 不清理这些包，只把状态写入 manifest。

## 5. Manifest

zip 内部包含：

```text
FlowWeaverPortable/release-manifest.json
```

关键字段：

| 字段 | 内容 |
| --- | --- |
| `manifest_schema_version` | `1` |
| `package_kind` | `portable` |
| `release_version` | 统一发布版本 |
| `archive_name` | zip 文件名 |
| `target_runtime` | `win-x64` |
| `desktop_publish_mode` | `framework-dependent` |
| `desktop_self_contained` | `false` |
| `dotnet_runtime_required` | `true` |
| `python_version` | audit 识别结果 |
| `pip_version` | audit 识别结果 |
| `runtime_audit_status` | `checked` 或 `warning` |
| `runtime_audit` | P.2 完整 audit 结果 |
| `entries` | zip 内 payload 文件的 path、size、sha256 |
| `excluded_paths` | audit 记录的 cache 排除项 |
| `licenses` | zip 内许可证文件摘要 |

P.3 对 P.1 的一个实现修正：

- `release-manifest.json` 不进入自身 `entries`
- 原因是 manifest 文件无法同时记录自身最终 SHA-256 并保持自洽
- manifest 的完整性由 zip 外部 `.sha256` 覆盖
- manifest 中通过 `manifest_path` 和 `manifest_integrity=covered_by_external_zip_sha256` 明确说明

## 6. Licenses

zip 内部包含：

```text
FlowWeaverPortable/licenses/
  FlowWeaver-LICENSE.txt
  Python-LICENSE.txt
  third-party-licenses.json
```

来源：

| 文件 | 来源 |
| --- | --- |
| `FlowWeaver-LICENSE.txt` | 仓库根 `LICENSE` |
| `Python-LICENSE.txt` | 便携目录 `EngineHost/python312/LICENSE.txt` |
| `third-party-licenses.json` | 由 P.3 根据 audit package 摘要生成 |

`third-party-licenses.json` 第一版为 summary-only，只记录包名、版本和路径，不展开完整第三方许可证正文。

## 7. SHA-256

zip 外部生成：

```text
FlowWeaverPortable-0.1.0-win-x64.zip.sha256
```

格式：

```text
<sha256>  FlowWeaverPortable-0.1.0-win-x64.zip
```

单元测试会重新读取 zip 并验证 `.sha256` 与实际文件 hash 一致。

## 8. 安全边界

P.3 依赖 P.2 audit 拒绝：

- `EngineHost/runtime/`
- `Desktop/runtime/`
- `flowweaver.db`
- `local_api_token`
- `*.stdout.log`
- `*.stderr.log`
- `portable-launcher.log`

P.3 会排除：

- `__pycache__/`
- `*.pyc`

P.3 暂不做全量文本扫描。原因是源码和文档中存在合法的 `Authorization: Bearer`、`token=` 示例；全量文本扫描容易误伤。后续若要做文本扫描，应单独增加规则和白名单。

## 9. 单元测试

新增：

```text
tests/unit/test_create_portable_archive.py
```

覆盖：

- 生成 zip、manifest、licenses 和 `.sha256`
- `.sha256` 与实际 zip hash 一致
- manifest entries 的 path、size、sha256 与 zip 内容一致
- `release-manifest.json` 不进入自身 entries
- audit warning 时仍允许归档并记录 warning
- cache 和 `.pyc` 被排除
- 版本不一致拒绝
- output 在 `.tmp/` 外拒绝
- `self-contained` 显式模式拒绝
- runtime audit rejected 时拒绝
- 已存在 archive 时拒绝覆盖

## 10. 验证

本阶段建议运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py
.\python312\python.exe tools\create_portable_layout.py --no-desktop-build
.\python312\python.exe tools\create_portable_archive.py --input .tmp\FlowWeaverPortable --output .tmp\dist-p3-smoke
```

## 11. 下一步建议

进入 P.4：clean-room 解压 smoke。

P.4 应使用 P.3 生成的 zip 和 `.sha256`，解压到仓库外、包含空格和中文的路径，验证 backend-only 启动、health、token 鉴权和首次 runtime 生成。
