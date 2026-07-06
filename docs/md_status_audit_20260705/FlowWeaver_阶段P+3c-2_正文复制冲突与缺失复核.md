# FlowWeaver 阶段P+3c-2：正文复制冲突与缺失复核

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+3c-2完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3、P+3a、P+3b、P+3c 和 P+3c-1
> 适用范围：Python 第三方许可证正文复制的缺失、越界和重名冲突边界
> 当前执行点：只补防御性测试与验收记录，不改变默认归档阻断策略

## 1. 阶段目标

P+3c-2 的目标是复核 P+3c-1 新增的 Python 许可证正文复制逻辑在异常输入下的边界行为：

- 许可证正文源文件缺失
- `License-File` 指向发布输入目录外
- 同一包下多个许可证正文复制到相同 zip 路径且内容冲突

这些情况在开发归档模式下应只记录 warning，不应阻断 zip 生成。

## 2. 保持不变的边界

本阶段不进入：

- NuGet 许可证正文复制
- 联网下载许可证正文
- release strict 阻断策略
- 安装器、代码签名、自动更新、后台服务或系统托盘

## 3. 复核结果

| 场景 | 期望行为 | 当前结果 |
| --- | --- | --- |
| Python `license_files` 指向缺失文件 | 不生成 copied file，记录 `license_file_source_missing` | 通过 |
| Python `license_files` 指向输入目录外 | 不生成 copied file，记录 `license_file_source_outside_input` | 通过 |
| Python 多个正文目标路径冲突且内容不同 | 保留首个 copied file，记录 `license_file_copy_name_conflict` | 通过 |

上述 warning 同时写入顶层 `third-party-licenses.json.warnings` 和对应 package 的 `warnings`，便于后续 release strict 做统一判断。

## 4. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tests/unit/test_create_portable_archive.py` | 新增缺失源文件、输入目录外路径和复制目标冲突三个边界测试 |
| `docs/FlowWeaver_阶段P+3c-2_正文复制冲突与缺失复核.md` | 固化阶段完成状态 |
| `README.md` | 更新 P+3c-2 阶段记录和下一步建议 |

## 5. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py
.\python312\python.exe -m ruff check tests\unit\test_create_portable_archive.py tools\create_portable_archive.py
```

结果：

```text
pytest create_portable_archive: 12 passed
ruff: All checks passed!
```

完整发布归档相关复核见本阶段提交前的最终命令记录。

提交前完整复核：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

结果：

```text
pytest release archive checks: 25 passed
ruff: All checks passed!
git diff --check: passed
```

## 6. 阶段结论

P+3c-2 可以视为 Python 许可证正文复制异常边界的最小验收闭环。

下一步建议进入 P+4：release strict 模式分析。P+4 应先明确哪些 warning 在严格发布模式下升级为阻断，再决定是否新增 CLI 开关和对应验收。
