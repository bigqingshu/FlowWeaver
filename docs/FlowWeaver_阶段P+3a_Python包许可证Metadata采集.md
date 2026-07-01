# FlowWeaver 阶段P+3a：Python 包许可证 metadata 采集

> 文档状态：阶段P+3a完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2 和 P+3 方案文档
> 适用范围：Python `dist-info/METADATA` / `PKG-INFO` 许可证 metadata 采集、`third-party-licenses.json` metadata-only schema、包级 warning
> 当前执行点：只做 Python 包 metadata 采集，不复制许可证正文、不采集 .NET NuGet metadata、不改变默认发布阻断策略

## 1. 目标

P+3a 的目标是把 `third-party-licenses.json` 从 `summary-only` 升级为 Python 包 `metadata-only` 清单，记录可离线读取的许可证 metadata 和缺失情况。

本阶段完成：

- 扩展 `RuntimePackage`，记录 Python 包许可证 metadata 字段
- 从 `dist-info/METADATA` 或 `dist-info/PKG-INFO` 读取：
  - `License-Expression`
  - `License`
  - `Classifier: License :: ...`
  - `License-File`
- 发现 `dist-info/` 下的 `LICENSE*`、`COPYING*`、`NOTICE*` 文件
- 发现 `dist-info/licenses/` 下的许可证正文文件路径
- 在包级 `warnings` 中记录缺失 metadata、缺失许可证 metadata、声明的 License-File 不存在等情况
- 将 `licenses/third-party-licenses.json` 输出升级为 `metadata-only`
- 将 manifest 中 Third-party packages 的 `kind` 从 `summary` 调整为 `metadata`

本阶段不做：

- 不复制第三方许可证正文到 `licenses/third-party/`
- 不读取 .NET NuGet metadata
- 不联网下载许可证
- 不判断许可证兼容性
- 不把许可证 metadata 缺失升级为 runtime audit warning
- 不把许可证 metadata 缺失升级为归档阻断
- 不进入 release strict、安装器、签名、自动更新或后台服务

## 2. 输出 schema

P+3a 后 `third-party-licenses.json` 最小结构为：

```json
{
  "schema_version": 1,
  "status": "metadata-only",
  "generated_from": {
    "python_runtime": "EngineHost/python312"
  },
  "packages": [
    {
      "ecosystem": "python",
      "name": "fastapi",
      "version": "0.124.0",
      "path": "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info",
      "metadata_source": "METADATA",
      "license_expression": "MIT",
      "license_text": null,
      "license_classifiers": [
        "License :: OSI Approved :: MIT License"
      ],
      "license_files": [
        "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info/LICENSE"
      ],
      "license_status": "license_file_found",
      "warnings": []
    }
  ],
  "warnings": []
}
```

## 3. 缺失策略

许可证 metadata 缺失只写入包级 warning，不改变归档放行结果。

| 情况 | P+3a 默认处理 |
| --- | --- |
| `METADATA` / `PKG-INFO` 缺失 | `package.warnings += metadata_file_missing` |
| 没有 `License-Expression` / `License` / license classifier | `package.warnings += license_metadata_missing` |
| `License-File` 指向不存在文件 | `package.warnings += declared_license_file_missing:<path>` |
| 有许可证 metadata 但未发现许可证正文文件 | `package.warnings += license_file_missing` |
| 包级许可证 warning 存在 | 写入 `third-party-licenses.json` 顶层 `warnings` 去重列表 |

这些 warning 不加入 `RuntimeAuditResult.warnings`，因此不会让 `runtime_audit_status` 从 `checked` 变成 `warning`。

## 4. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/portable_runtime_audit.py` | 扩展 `RuntimePackage` 并采集 Python 包许可证 metadata |
| `tools/create_portable_archive.py` | 生成 `metadata-only` 的 `third-party-licenses.json` |
| `tests/unit/test_portable_runtime_audit.py` | 覆盖 metadata 采集、缺失 metadata、声明许可证文件缺失 |
| `tests/unit/test_create_portable_archive.py` | 覆盖新 JSON schema、manifest kind 和 package warning 序列化 |
| `docs/FlowWeaver_阶段P+3a_Python包许可证Metadata采集.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+3a 阶段记录和下一步建议 |

## 5. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\portable_runtime_audit.py tools\create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

结果：

```text
pytest unit: 19 passed
pytest P.4 clean-room smoke: 1 passed
ruff: All checks passed!
git diff --check: passed
```

## 6. 阶段结论

P+3a 可以视为 Python 包许可证 metadata 采集的最小闭环。

下一步建议进入 P+3b：.NET NuGet 依赖许可证 metadata 方案落地。P+3b 应继续保持只读 metadata 采集，不复制 NuGet 许可证正文，不依赖联网。
