# FlowWeaver 阶段P+3c：许可证正文复制评估

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+3c评估完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3、P+3a 和 P+3b
> 适用范围：第三方许可证正文复制来源、目标目录、JSON 字段调整、缺失策略和后续最小实现边界
> 当前执行点：只做评估和方案固化，不直接复制许可证正文、不改变 release strict 阻断策略

## 1. 目标

P+3c 的目标是判断第三方许可证正文是否可以安全、稳定地进入发布 zip，并明确后续最小实现范围。

当前结论：

- Python 包许可证正文可以作为 P+3c 最小实现对象。
- .NET / NuGet 许可证正文暂不复制，只保留 metadata 和 warning。
- 许可证正文缺失仍只记录 warning，不阻断开发归档。
- 是否在 release strict 下阻断缺失正文，留到 P+4 决策。

## 2. 当前事实

P+3a 已完成：

- Python 包 `dist-info/METADATA` / `PKG-INFO` metadata 采集
- `License-Expression`
- `License`
- license classifier
- `License-File`
- `dist-info/LICENSE*`
- `dist-info/COPYING*`
- `dist-info/NOTICE*`
- `dist-info/licenses/` 下文件
- 包级 `license_files`

P+3b 已完成：

- Desktop payload 存在时采集 .NET / NuGet 包名和版本
- 优先 `Avalonia_UI/obj/project.assets.json`
- fallback `Desktop/Avalonia_UI.deps.json`
- 可从本机 NuGet cache `.nuspec` 读取 license expression
- 缺失 NuGet license metadata 时记录包级 warning

当前尚未完成：

- 第三方许可证正文复制到 `licenses/third-party/...`
- `third-party-licenses.json` 中记录复制后的发布包内正文路径
- manifest entries 覆盖第三方许可证正文副本

## 3. 可复制来源判断

### 3.1 Python 包

Python 包可复制来源：

```text
EngineHost/python312/Lib/site-packages/<package>.dist-info/LICENSE*
EngineHost/python312/Lib/site-packages/<package>.dist-info/COPYING*
EngineHost/python312/Lib/site-packages/<package>.dist-info/NOTICE*
EngineHost/python312/Lib/site-packages/<package>.dist-info/licenses/**
License-File 指向且解析到发布输入内的文件
```

这些来源已经位于便携发布输入目录内，具备以下优点：

- 不依赖联网
- 不依赖本机全局路径
- 不需要从 NuGet cache 或外部包缓存复制
- 可由归档脚本读取并写入 zip
- 可由 manifest entries 记录 size 和 sha256

因此，Python 包许可证正文适合作为 P+3c 最小实现对象。

### 3.2 .NET / NuGet 包

NuGet 许可证正文暂不建议复制。

原因：

- `project.assets.json` 和 `.deps.json` 通常只提供依赖名、版本和路径，不提供许可证正文
- `.nuspec` 可能只有 license expression 或 legacy licenseUrl
- NuGet cache 是本机缓存，不一定稳定存在
- 不应联网下载 licenseUrl
- 不应把 NuGet cache 文件隐式复制进发布包

因此，P+3c 不复制 NuGet 许可证正文。NuGet 继续保留：

- 包名
- 版本
- metadata 来源
- license expression
- warning

后续如需 NuGet 正文复制，应作为单独阶段先定义 NuGet cache 证据来源和可复制性规则。

## 4. 建议目标目录

建议将 Python 第三方许可证正文复制到：

```text
FlowWeaverPortable/
  licenses/
    third-party/
      python/
        <package-name>/
          <source-file-name>
```

示例：

```text
FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE
FlowWeaverPortable/licenses/third-party/python/some-package/NOTICE
```

如果同一个包存在重名文件，应保持相对层级或追加稳定前缀，避免覆盖。

建议使用源文件在 package 目录内的相对路径生成目标路径：

```text
dist-info/LICENSE
dist-info/licenses/LICENSE-MIT
```

映射为：

```text
licenses/third-party/python/<package>/LICENSE
licenses/third-party/python/<package>/licenses/LICENSE-MIT
```

## 5. JSON schema 建议

P+3c 可将 `third-party-licenses.json` 的 `status` 从：

```json
"metadata-only"
```

升级为：

```json
"metadata-and-files"
```

建议新增字段：

```json
{
  "license_files": [
    "EngineHost/python312/Lib/site-packages/fastapi-0.124.0.dist-info/LICENSE"
  ],
  "copied_license_files": [
    "FlowWeaverPortable/licenses/third-party/python/fastapi/LICENSE"
  ]
}
```

字段语义：

| 字段 | 语义 |
| --- | --- |
| `license_files` | 原始发布输入内发现的许可证正文路径 |
| `copied_license_files` | zip 内复制后的许可证正文路径 |

NuGet 包的 `copied_license_files` 第一版应为空数组。

## 6. 复制规则

建议规则：

- 只复制 `license_files` 中位于发布输入目录内的文件
- 只复制普通文件
- 不复制目录
- 不复制绝对路径
- 不复制包含 `..` 的路径
- 不复制 `runtime/`、token、数据库、日志或临时目录
- 不联网下载
- 不从 NuGet cache 复制
- 默认缺失只写 warning

## 7. warning 策略

建议新增包级 warning：

| warning | 触发条件 |
| --- | --- |
| `license_file_copy_skipped` | 该 ecosystem 当前不支持正文复制，例如 dotnet |
| `license_file_source_missing` | `license_files` 指向的源文件不存在 |
| `license_file_source_outside_input` | `license_files` 指向发布输入目录外 |
| `license_file_copy_name_conflict` | 目标路径冲突且内容不同 |

这些 warning 不加入 `RuntimeAuditResult.warnings`，也不改变 `runtime_audit_status`。

## 8. 后续最小实现建议

### P+3c-1：Python 许可证正文复制

范围：

- 仅复制 Python 包 `license_files`
- 目标目录为 `licenses/third-party/python/<package>/...`
- `third-party-licenses.json` 增加 `copied_license_files`
- `status` 升级为 `metadata-and-files`
- manifest entries 记录复制后的正文文件
- NuGet 包 `copied_license_files` 保持空数组
- 不改变默认阻断策略

验收：

- 单元测试验证 Python LICENSE 文件进入 zip
- 单元测试验证 `copied_license_files`
- 单元测试验证 NuGet 包不复制正文
- P.4 clean-room smoke 仍通过

### P+3c-2：正文复制冲突与缺失复核

范围：

- 处理同包多文件、重名、缺失源文件
- 只记录 warning，不阻断
- 不引入 release strict

## 9. 不建议现在做

- 不复制 NuGet cache 文件
- 不下载 licenseUrl
- 不判断许可证兼容性
- 不把缺失正文升级为阻断
- 不引入 release strict
- 不修改 Desktop 发布模式
- 不进入安装器、签名、自动更新或后台服务

## 10. 阶段结论

P+3c 评估结论：

- 可以进入 P+3c-1 最小实现。
- 最小实现只复制 Python 包中已经位于发布输入内的许可证正文。
- .NET / NuGet 正文复制继续后置。
- release strict 阻断策略继续留到 P+4。

下一步建议进入 P+3c-1：Python 许可证正文复制最小实现。
