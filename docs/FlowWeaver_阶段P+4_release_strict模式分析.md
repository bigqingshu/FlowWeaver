# FlowWeaver 阶段P+4：release strict 模式分析

> 文档状态：阶段P+4分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1、P+2、P+3、P+3a、P+3b、P+3c、P+3c-1 和 P+3c-2
> 适用范围：便携 zip 正式发布门禁、开发归档与正式分发归档的语义拆分
> 当前执行点：先固化 release strict 语义和实施顺序，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 背景

当前 `tools/create_portable_archive.py` 已经可以生成便携 zip、`release-manifest.json`、外部 `.sha256` 和许可证文件。默认行为面向开发归档：

- runtime audit 为 `rejected` 时拒绝归档
- runtime audit 为 `warning` 时允许归档，并写入 manifest
- 第三方许可证 metadata 或正文复制 warning 只写入 `third-party-licenses.json`
- `git_dirty` 只写入 manifest，不阻断归档
- backend-only layout 可以归档，用于 P.4 clean-room smoke

P+4 要解决的问题不是替换这些默认行为，而是增加一个显式正式发布门禁，让开发归档和正式分发归档分开。

## 2. 概念拆分

| 概念 | 当前状态 | P+4建议 |
| --- | --- | --- |
| `runtime_audit_mode=strict` | 已存在，只支持运行时目录安全审计 | 保持不变，不复用为发布门禁 |
| 开发归档 | 默认路径，允许 warning | 保持默认，不增加使用门槛 |
| release strict | 尚未实现 | 新增显式开关，例如 `--release-strict` |

`runtime_audit_mode=strict` 的含义是“运行时审计规则严格”，不是“正式发布门禁严格”。P+4 应新增单独语义，避免名称和职责混在一起。

## 3. release strict 第一版阻断矩阵

建议第一版只覆盖归档脚本自身可以稳定判断的事项：

| 检查项 | 默认开发归档 | release strict | 原因 |
| --- | --- | --- | --- |
| runtime audit `rejected` | 阻断 | 阻断 | 已有安全拒绝项 |
| runtime audit `warning` | 允许并写入 manifest | 阻断 | 正式发布不应携带 dev/test/build/legacy 包或 cache warning |
| 第三方许可证 warning | 允许并写入 `third-party-licenses.json` | 阻断 | 正式发布应先处理 metadata、正文缺失或复制冲突 |
| Git worktree dirty | 写入 manifest | 阻断 | 正式发布需要可追溯源码状态 |
| Git commit 不可读取 | 写入 `null` | 阻断 | 正式发布需要可追溯 commit |
| `Desktop/Avalonia_UI.exe` 缺失 | 允许 backend-only 归档 | 阻断 | 面向用户的正式发布应包含桌面入口 |
| `.sha256` | 总是生成 | 总是生成 | 已有行为 |
| clean-room smoke 已运行 | 脚本不判断 | 暂不自动阻断 | smoke 发生在归档之后，不应让归档脚本依赖未来证据 |

## 4. 暂不纳入第一版的事项

以下事项不进入 P+4 第一版：

- 不要求代码签名
- 不要求安装器
- 不要求自动更新
- 不要求后台服务或系统托盘
- 不切换 Desktop self-contained
- 不联网下载许可证正文
- 不在工具中判断许可证兼容性或给出法律结论
- 不把 clean-room smoke 结果写回 zip

clean-room smoke 更适合由发布流程或 CI 外层脚本串联：

```text
layout -> archive --release-strict -> sha256 verify -> clean-room smoke
```

归档脚本只负责“当前输入是否足够干净”，不负责证明后续 smoke 已完成。

## 5. 最小实现建议

P+4 后续代码小步建议：

1. 新增 `release_strict: bool = False` 参数和 CLI `--release-strict`
2. 默认值保持 `False`，现有测试和开发归档行为不变
3. 归档前收集第三方许可证 metadata 后执行 strict 检查
4. strict 失败时不生成 zip、不生成 `.sha256`
5. 错误信息中列出稳定的拒绝原因 code，便于测试和发布排查

建议错误 code：

| code | 触发条件 |
| --- | --- |
| `runtime_audit_warning` | `runtime_audit.status == "warning"` |
| `third_party_license_warning` | `third-party-licenses.json.warnings` 非空 |
| `git_commit_unavailable` | 无法读取 `git rev-parse HEAD` |
| `git_worktree_dirty` | `git status --short` 非空 |
| `desktop_executable_missing` | `Desktop/Avalonia_UI.exe` 不存在 |

## 6. 验收建议

单元测试：

- 默认开发归档仍允许 runtime audit warning
- `release_strict=True` 时拒绝 runtime audit warning
- `release_strict=True` 时拒绝第三方许可证 warning
- `release_strict=True` 时拒绝 dirty git
- `release_strict=True` 时拒绝缺失 Desktop executable
- `release_strict=True` 且输入干净时可以生成 zip

命令行验收：

```powershell
.\python312\python.exe tools\create_portable_archive.py --release-strict
```

如果当前 `python312/` 仍包含 dev/test/build 包，该命令应拒绝并说明 `runtime_audit_warning`，而不是生成看似正式的发布包。

## 7. 阶段结论

P+4 应进入最小代码实现，但必须保持：

- 默认开发归档行为不变
- release strict 必须显式启用
- strict 只做归档输入门禁，不替代 clean-room smoke
- 不进入安装器、签名、自动更新、后台服务、系统托盘或 self-contained Desktop

下一步建议进入 P+4a：`--release-strict` 最小实现与单元测试。
