# FlowWeaver 阶段P+3b：.NET NuGet 依赖许可证 metadata 采集

> 文档状态：阶段P+3b完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3 和 P+3a
> 适用范围：Avalonia Desktop 发布物存在时的 .NET / NuGet 依赖 metadata 采集、`third-party-licenses.json` dotnet entries、包级 warning
> 当前执行点：只做只读 metadata 采集，不复制 NuGet 许可证正文、不联网、不改变默认发布阻断策略

## 1. 目标

P+3b 的目标是在 P+3a 已经支持 Python 包许可证 metadata 的基础上，把 Desktop 侧 .NET / NuGet 依赖纳入 `third-party-licenses.json`。

本阶段完成：

- 当便携发布输入中存在 Desktop payload 时，采集 .NET / NuGet 依赖
- 优先读取仓库 `Avalonia_UI/obj/project.assets.json`
- 若 `project.assets.json` 不存在，则读取发布输入 `Desktop/Avalonia_UI.deps.json`
- 只记录 NuGet 包名、版本、依赖来源和许可证 metadata 状态
- 可选读取本机 NuGet cache 中 `.nuspec` 的 `<license type="expression">...`
- 无 NuGet 许可证 metadata 时写入包级 `nuget_license_metadata_unavailable`
- 不复制 NuGet 许可证正文
- 不联网下载许可证信息
- 不把 NuGet license metadata 缺失升级为归档阻断

本阶段不做：

- 不复制 NuGet 包许可证正文
- 不读取或复制 NuGet cache 文件到发布包
- 不解析 legacy `licenseUrl` 并联网下载
- 不判断许可证兼容性
- 不改变 Desktop framework-dependent 发布模式
- 不进入 release strict、安装器、签名、自动更新或后台服务

## 2. 采集条件

P+3b 只在发布输入目录中存在 Desktop payload 时采集 .NET 依赖。

这样可以避免 backend-only 归档仅因为仓库中存在 `Avalonia_UI/obj/project.assets.json`，就误把桌面依赖写入发布包许可证清单。

判断边界：

```text
FlowWeaverPortable/Desktop/ 下存在至少一个文件
```

## 3. 采集来源优先级

| 优先级 | 来源 | 说明 |
| --- | --- | --- |
| 1 | `Avalonia_UI/obj/project.assets.json` | 构建期 NuGet 依赖清单，优先使用 |
| 2 | `FlowWeaverPortable/Desktop/Avalonia_UI.deps.json` | 发布产物运行依赖清单，作为 fallback |
| 3 | 本机 NuGet cache `.nuspec` | 只用于尝试读取 license expression，不复制文件 |

NuGet cache 路径：

- 优先使用 `NUGET_PACKAGES`
- 未设置时使用用户目录下 `.nuget/packages`

## 4. 输出 schema

.NET 包写入同一个 `licenses/third-party-licenses.json`：

```json
{
  "ecosystem": "dotnet",
  "name": "Example.Package",
  "version": "1.2.3",
  "path": "Avalonia_UI/obj/project.assets.json#Example.Package/1.2.3",
  "metadata_source": "project.assets.json+nuspec",
  "license_expression": "MIT",
  "license_text": null,
  "license_classifiers": [],
  "license_files": [],
  "license_status": "metadata_found",
  "warnings": []
}
```

当只能从 `project.assets.json` 或 `.deps.json` 得到依赖名和版本，无法读取 NuGet license expression 时：

```json
{
  "ecosystem": "dotnet",
  "metadata_source": "deps.json",
  "license_expression": null,
  "license_status": "missing_license_metadata",
  "warnings": [
    "nuget_license_metadata_unavailable"
  ]
}
```

## 5. 缺失策略

| 情况 | P+3b 默认处理 |
| --- | --- |
| Desktop payload 不存在 | 不采集 .NET 包，不写 warning |
| Desktop payload 存在但找不到依赖来源 | 顶层 warning：`dotnet_dependency_source_missing` |
| 只能得到 NuGet 包名和版本 | 包级 warning：`nuget_license_metadata_unavailable` |
| 本机 `.nuspec` 有 license expression | 记录 `license_expression`，不写 warning |
| 本机 `.nuspec` 不存在 | 不阻断，记录包级 warning |

这些 warning 不改变 `runtime_audit_status`，也不阻断归档生成。

## 6. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_archive.py` | 增加 Desktop payload 判断、NuGet 依赖来源解析、`.nuspec` license expression 读取和 dotnet package entries |
| `tests/unit/test_create_portable_archive.py` | 覆盖 `project.assets.json + nuspec` 与 `.deps.json fallback` 两类场景 |
| `docs/FlowWeaver_阶段P+3b_DotNetNuGet许可证Metadata采集.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+3b 阶段记录和下一步建议 |

## 7. 验收结果

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

## 8. 阶段结论

P+3b 可以视为 .NET / NuGet 依赖许可证 metadata 采集的最小闭环。

下一步建议进入 P+3c：许可证正文复制评估。P+3c 应先评估哪些第三方许可证正文可以稳定定位和复制，不直接扩大 release strict 阻断策略。
