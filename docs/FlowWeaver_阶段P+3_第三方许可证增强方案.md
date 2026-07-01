# FlowWeaver 阶段P+3：第三方许可证增强方案

> 文档状态：阶段P+3方案完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2 和 `docs/FlowWeaver_阶段P后_边界分析.md`
> 适用范围：第三方依赖许可证清单、许可证 metadata、许可证正文来源、缺失策略、发布阻断策略和后续实现顺序
> 当前执行点：只做方案分析，不修改 `tools/create_portable_archive.py`、`tools/portable_runtime_audit.py`、归档输出结构或测试行为

## 1. 目标

P+3 的目标是把当前 `licenses/third-party-licenses.json` 的 `summary-only` 状态，拆解成可实施、可验收、可逐步增强的许可证清单方案。

本阶段完成：

- 复核当前 FlowWeaver、Python 和第三方依赖许可证输出事实
- 明确第三方许可证增强的数据来源
- 明确 Python 包和 .NET NuGet 包的许可证 metadata 采集边界
- 明确许可证正文是否复制、如何复制和何时阻断
- 明确默认开发归档与后续 release strict 的关系
- 明确后续 P+3a/P+3b/P+3c 的建议实现顺序

本阶段不做：

- 不修改归档脚本
- 不修改 runtime audit
- 不新增许可证正文复制
- 不改变 `third-party-licenses.json` 当前 schema
- 不把 warning 升级为发布阻断
- 不进入代码签名、安装器、自动更新、后台服务或 self-contained Desktop

## 2. 当前事实

当前 `tools/create_portable_archive.py` 已生成：

| 文件 | 当前来源 | 当前语义 |
| --- | --- | --- |
| `licenses/FlowWeaver-LICENSE.txt` | 仓库根目录 `LICENSE` | 项目许可证正文 |
| `licenses/Python-LICENSE.txt` | `EngineHost/python312/LICENSE.txt` | 便携 Python runtime 许可证正文 |
| `licenses/third-party-licenses.json` | `portable_runtime_audit.packages` | 第三方 Python 包 summary-only 清单 |

当前 `third-party-licenses.json` 示例语义：

```json
{
  "status": "summary-only",
  "packages": [
    {
      "name": "fastapi",
      "version": "0.124.0",
      "path": "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info"
    }
  ]
}
```

当前没有：

- Python 包 `License` / `License-Expression` / classifier metadata
- Python 包 `License-File` 或实际许可证正文路径
- .NET NuGet 依赖许可证 metadata
- 缺失许可证 metadata 的 warning 明细
- 许可证正文复制目录
- release strict 下的许可证阻断规则

## 3. 设计原则

P+3 后续实现应遵循：

- 离线优先：只读取发布输入目录、仓库文件和本地构建产物，不联网抓取许可证。
- 证据优先：记录发现了什么 metadata 和正文文件，不在工具里做法律解释。
- 默认不阻断：开发归档默认允许 metadata 缺失，但必须记录 warning。
- 正式发布可收紧：是否将缺失 metadata 或正文升级为阻断，留给后续 release strict。
- 不污染归档输入：生成的 `licenses/` 仍由归档脚本写入 zip，不要求 layout 预置许可证目录。
- 可重复生成：相同输入应生成稳定、可排序的许可证清单。
- 不泄露运行数据：不得扫描或复制 `runtime/`、token、数据库、日志和临时目录。

## 4. 建议输出结构

第一版建议继续保留：

```text
FlowWeaverPortable/
  licenses/
    FlowWeaver-LICENSE.txt
    Python-LICENSE.txt
    third-party-licenses.json
```

后续如果要复制许可证正文，再新增：

```text
FlowWeaverPortable/
  licenses/
    third-party/
      python/
        <package-name>/
          <license-file>
      dotnet/
        <package-name>/
          <license-file>
```

正文复制不建议在 P+3a 立刻做。更稳顺序是先增强 metadata，再决定哪些正文可以可靠定位和复制。

## 5. 建议 JSON schema

`third-party-licenses.json` 后续可从 `summary-only` 升级为 `metadata-only` 或 `metadata-and-files`。

建议字段：

```json
{
  "schema_version": 1,
  "status": "metadata-only",
  "generated_from": {
    "python_runtime": "EngineHost/python312",
    "desktop_project": "Avalonia_UI/Avalonia_UI.csproj"
  },
  "packages": [
    {
      "ecosystem": "python",
      "name": "fastapi",
      "version": "0.124.0",
      "path": "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info",
      "metadata_source": "METADATA",
      "license_expression": null,
      "license_text": null,
      "license_classifiers": [
        "License :: OSI Approved :: MIT License"
      ],
      "license_files": [],
      "license_status": "metadata_found",
      "warnings": []
    }
  ],
  "warnings": []
}
```

字段语义：

| 字段 | 语义 |
| --- | --- |
| `ecosystem` | `python` 或 `dotnet` |
| `name` / `version` | 依赖名和版本 |
| `path` | 证据路径，保持发布包相对路径或仓库相对路径 |
| `metadata_source` | `METADATA`、`PKG-INFO`、`project.assets.json`、`deps.json` 等 |
| `license_expression` | PEP 639 或 NuGet license expression，缺失为 `null` |
| `license_text` | 包 metadata 中的短 license 字段，缺失为 `null` |
| `license_classifiers` | Python classifier 中的 license 信息 |
| `license_files` | 已发现许可证正文文件路径 |
| `license_status` | `metadata_found`、`missing_metadata`、`license_file_found`、`license_file_missing` |
| `warnings` | 包级缺失、歧义或未支持来源 |

## 6. Python 包 metadata 来源

建议读取：

- `<package>.dist-info/METADATA`
- `<package>.dist-info/PKG-INFO`
- `<package>.dist-info/LICENSE*`
- `<package>.dist-info/COPYING*`
- `<package>.dist-info/NOTICE*`
- `METADATA` 内的 `License-Expression`
- `METADATA` 内的 `License`
- `METADATA` 内的 `Classifier: License :: ...`
- `METADATA` 内的 `License-File`

缺失策略：

| 情况 | 默认处理 | release strict 可选处理 |
| --- | --- | --- |
| 没有 `METADATA` / `PKG-INFO` | warning | 可阻断 |
| 没有任何 license metadata | warning | 可阻断 |
| 有 license metadata，但没有正文文件 | warning | 可允许或阻断 |
| `License-File` 指向不存在文件 | warning | 可阻断 |
| 发现多个许可证正文 | 全部记录 | 不阻断 |

## 7. .NET NuGet metadata 来源

Desktop 当前为 `framework-dependent`，仍需要记录 Avalonia / NuGet 依赖的许可证信息。

建议来源优先级：

1. `Avalonia_UI/obj/project.assets.json`
2. 发布目录中的 `Avalonia_UI.deps.json`
3. 本机 NuGet cache 中对应 package 的 `.nuspec`

P+3 后续第一版可以先只做 `project.assets.json` / `deps.json` 的只读解析方案，不复制 NuGet cache 文件。原因：

- NuGet cache 不一定在 clean-room 发布机上保留完整许可证正文
- `.deps.json` 能给出运行依赖清单，但通常不含许可证表达式
- `.nuspec` 可能包含 `license` / `licenseUrl`，但路径来源和可复制性需要单独确认

缺失策略：

| 情况 | 默认处理 | release strict 可选处理 |
| --- | --- | --- |
| 找不到 Desktop dependency source | warning | 可阻断 |
| 只能从 `.deps.json` 得到包名版本 | warning | 可允许 |
| `.nuspec` 有 license expression | 记录 | 不阻断 |
| `.nuspec` 只有 legacy licenseUrl | 记录 URL，不联网下载 | 可允许或阻断 |
| 找不到许可证正文 | warning | 可后置 |

## 8. 后续小步建议

### P+3a：Python 包许可证 metadata 采集

范围：

- 新增 Python 包 metadata 解析 helper
- 从 `dist-info/METADATA` 读取 license 字段、classifier 和 License-File
- 保持 `third-party-licenses.json` 仍只写一个文件
- 不复制许可证正文
- 不改变默认阻断策略

验收：

- 单元测试覆盖有 `License-Expression`、有 classifier、缺失 metadata、缺失 License-File 的场景
- `test_create_portable_archive.py` 验证 JSON schema 和 warning

### P+3b：.NET NuGet 依赖许可证 metadata 方案落地

范围：

- 从 `project.assets.json` 或 `.deps.json` 读取 Desktop 依赖清单
- 尝试读取本机 NuGet cache 的 `.nuspec`
- 只记录 metadata，不复制正文
- 无可用 NuGet metadata 时记录 warning

验收：

- 单元测试用最小 `project.assets.json` / `.deps.json` fixture
- 不要求本机真实 NuGet cache 稳定存在

### P+3c：许可证正文复制评估

范围：

- 只复制发布输入内已经存在的许可证正文
- 明确第三方正文复制目标目录
- 缺失正文默认 warning
- 是否阻断留给 release strict

验收：

- zip 内 `licenses/third-party/...` entries
- manifest entries 记录正文文件
- clean-room smoke 不受影响

## 9. 不建议现在做的事项

以下事项不并入 P+3：

- 不联网下载许可证正文
- 不在工具中判断许可证兼容性
- 不给出法律结论
- 不强制移除 dev/test/build 包
- 不把所有 warning 升级为阻断
- 不修改 Desktop 发布模式
- 不引入安装器、签名、自动更新或后台服务

## 10. 阶段结论

P+3 当前建议结论：

- `third-party-licenses.json` 应从 `summary-only` 逐步升级到 `metadata-only`
- 第一实现小步应先做 Python 包 metadata 采集
- .NET NuGet metadata 应作为独立小步，避免把 NuGet cache、`.deps.json` 和 `.nuspec` 解析混在一起
- 许可证正文复制应后置，先解决哪些正文可以稳定定位
- release strict 是否阻断缺失许可证，应留到 P+4 或后续严格发布模式中决策

下一步最稳是 P+3a：Python 包许可证 metadata 采集。
