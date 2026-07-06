# FlowWeaver 阶段P+3c-1：Python 许可证正文复制最小实现

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+3c-1完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3、P+3a、P+3b 和 P+3c 评估文档
> 适用范围：Python 包许可证正文复制、`copied_license_files`、`metadata-and-files` schema、manifest entries
> 当前执行点：只复制 Python 包中已位于发布输入内的许可证正文，不复制 NuGet 正文、不改变默认归档阻断策略

## 1. 目标

P+3c-1 的目标是把 P+3a 已经发现的 Python 包许可证正文文件复制进发布 zip 的 `licenses/third-party/python/` 目录，并在 `third-party-licenses.json` 中记录复制后的路径。

本阶段完成：

- 将 `third-party-licenses.json` 的 `status` 从 `metadata-only` 升级为 `metadata-and-files`
- 为 Python 包新增 `copied_license_files`
- 将 Python 包 `license_files` 中位于发布输入内的文件复制到 zip：

```text
FlowWeaverPortable/licenses/third-party/python/<package-name>/<license-file>
```

- 复制后的许可证正文作为归档生成文件进入 manifest entries
- NuGet 包 `copied_license_files` 保持空数组
- 复制失败只写包级 warning，不阻断归档

本阶段不做：

- 不复制 NuGet cache 文件
- 不联网下载许可证正文
- 不处理 release strict 阻断
- 不判断许可证兼容性
- 不修改 Desktop 发布模式
- 不进入安装器、签名、自动更新或后台服务

## 2. 复制规则

只复制满足以下条件的文件：

- 来源在发布输入目录内
- 来源是普通文件
- 路径不是绝对路径
- 路径不包含 `..`
- 来源由 P+3a 的 Python 包 `license_files` 发现

目标路径：

```text
FlowWeaverPortable/licenses/third-party/python/<package-name>/<relative-license-path>
```

示例：

```text
EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info/LICENSE
```

复制为：

```text
FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE
```

## 3. JSON schema 变化

P+3c-1 后 Python 包示例：

```json
{
  "ecosystem": "python",
  "name": "fastapi",
  "version": "0.124.0",
  "license_files": [
    "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info/LICENSE"
  ],
  "copied_license_files": [
    "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE"
  ],
  "license_status": "license_file_found",
  "warnings": []
}
```

NuGet 包示例：

```json
{
  "ecosystem": "dotnet",
  "copied_license_files": []
}
```

## 4. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_archive.py` | 复制 Python 包许可证正文，生成 `copied_license_files`，输出 `metadata-and-files` |
| `tests/unit/test_create_portable_archive.py` | 验证 Python LICENSE 进入 zip，JSON 记录 copied path，NuGet copied list 为空 |
| `docs/FlowWeaver_阶段P+3c-1_Python许可证正文复制最小实现.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+3c-1 阶段记录和下一步建议 |

## 5. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

结果：

```text
pytest unit: 21 passed
pytest P.4 clean-room smoke: 1 passed
ruff: All checks passed!
git diff --check: passed
```

## 6. 阶段结论

P+3c-1 可以视为 Python 许可证正文复制的最小闭环。

下一步建议进入 P+3c-2：正文复制冲突与缺失复核，重点确认同包多文件、重名、缺失源文件等场景是否只记录 warning 且不阻断开发归档。
