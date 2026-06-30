# FlowWeaver 阶段P.0：发布物归档与用户手册边界分析

> 文档状态：阶段P.0边界分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录
> 适用范围：便携发布物归档、发布包命名、生成物校验、用户手册和故障排查文档边界
> 当前执行点：只做边界分析，不实现压缩归档工具、不生成正式发布包、不编写完整用户手册正文

## 1. 背景

阶段 N 已完成便携发布目录、后端 runtime smoke、Avalonia publish 和发布产物 API/WebSocket 联调。阶段 O 已完成便携组合启动入口、launcher 生命周期、真实 Desktop 最小 smoke 和失败路径清理。

当前已经具备：

- `.tmp/FlowWeaverPortable/` 便携目录生成器
- `EngineHost/` 后端工作目录
- `Desktop/` Avalonia 发布产物目录
- `portable_launcher.py`
- `start_flowweaver.cmd`
- `start_flowweaver_desktop.cmd`
- 便携目录 `docs/README.txt`
- backend-only、真实 Desktop 和 Desktop 失败路径 smoke

下一步如果直接做安装器或自动更新，范围会明显扩大。因此 P.0 先只固化“发布物归档”和“用户手册”的边界。

P.0a 已补充发布归档关键边界：Desktop 当前为 framework-dependent 发布，`python312/` 需要 runtime audit 后才能作为干净发布运行时，Python/Avalonia/manifest/zip 需要统一发布版本，manifest、SHA-256 和许可证必须纳入发布物边界，clean-room smoke 必须覆盖仓库外空格/中文路径，用户手册必须明确关闭 Desktop 可能影响运行中 workflow。

## 2. 目标

P.0 的目标是回答：

- 发布归档物应该从哪个目录生成
- 归档物应包含哪些文件
- 归档物不应包含哪些运行时或本地敏感文件
- 发布包命名和版本信息最低需要哪些字段
- 归档前 smoke 应如何复用 N/O 阶段成果
- 便携版用户手册应放在哪里、包含哪些内容
- 哪些能力继续明确留到后续阶段

P.0 只形成清单和执行顺序，不改代码。

## 3. 当前发布输入

当前最稳定的发布输入仍是便携目录生成链：

```text
tools/create_portable_layout.py
tools/publish_desktop.py
```

推荐发布输入目录：

```text
.tmp/FlowWeaverPortable/
```

该目录仍是生成物，不进入版本控制。

当前便携目录关键结构：

```text
FlowWeaverPortable/
  EngineHost/
    python312/
    src/
    migrations/
    alembic.ini
    pyproject.toml
    uv.lock
  Desktop/
    Avalonia_UI.exe
    Avalonia_UI.dll
    *.deps.json
    *.runtimeconfig.json
  docs/
    README.txt
  portable_launcher.py
  start_flowweaver.cmd
  start_flowweaver_desktop.cmd
```

## 4. 归档物边界

第一版发布归档建议为 zip 文件：

```text
FlowWeaverPortable-<version>-win-x64.zip
```

归档根目录建议保留一层顶层目录：

```text
FlowWeaverPortable/
```

这样用户解压后不会把文件散落到当前目录。

### 必须包含

| 路径 | 原因 |
| --- | --- |
| `EngineHost/python312/` | 便携 Python runtime |
| `EngineHost/src/` | 后端源码运行入口 |
| `EngineHost/migrations/` | Alembic 迁移 |
| `EngineHost/alembic.ini` | 数据库迁移配置 |
| `EngineHost/pyproject.toml` | 依赖和项目元信息参考 |
| `EngineHost/uv.lock` | 依赖锁定参考 |
| `Desktop/` | Avalonia 发布产物 |
| `portable_launcher.py` | 组合启动核心 |
| `start_flowweaver.cmd` | 后端诊断入口 |
| `start_flowweaver_desktop.cmd` | 桌面组合入口 |
| `docs/README.txt` | 便携包内快速说明 |

### 默认不包含

| 路径 | 原因 |
| --- | --- |
| `EngineHost/runtime/` | 本机数据、token、日志和运行文件，不应进入干净发布包 |
| `.tmp/` 中其他目录 | 临时生成物 |
| `.pytest_cache/`、`__pycache__/`、`*.pyc` | 开发缓存 |
| `Avalonia_UI/bin/`、`Avalonia_UI/obj/` 原始构建目录 | 只归档 `Desktop/` 发布产物 |
| `.git/`、`.gitignore` | 不属于用户运行包 |
| 测试数据、测试临时 runtime | 避免污染首次启动体验 |

如果未来需要“带示例数据”的发布包，应作为单独归档类型，不与默认干净发布包混用。

## 5. 版本与清单边界

发布物至少需要一个归档清单文件，建议后续命名为：

```text
FlowWeaverPortable/release-manifest.json
```

第一版字段建议：

| 字段 | 说明 |
| --- | --- |
| `product_name` | 固定为 `FlowWeaver` |
| `package_kind` | 固定为 `portable` |
| `target_runtime` | 例如 `win-x64` |
| `version` | 后续阶段决定来源，P.0 不实现 |
| `commit` | 生成发布物时的 git commit |
| `created_at_utc` | 归档生成时间 |
| `python_version` | 便携 Python 版本 |
| `dotnet_target_framework` | 当前为 `net10.0` |
| `desktop_entry` | `Desktop/Avalonia_UI.exe` |
| `backend_entry` | `portable_launcher.py --no-desktop` |
| `combo_entry` | `portable_launcher.py` |

P.0 暂不决定版本号来源。后续可选：

- `pyproject.toml` 的 `project.version`
- git tag
- 手工参数
- CI 构建号

最稳方向是 P.1 先支持显式命令行参数，缺省使用 `pyproject.toml` 版本。

## 6. 归档前验收顺序

生成发布归档前应先通过以下最小验收：

1. 生成干净 `.tmp/FlowWeaverPortable/`
2. 发布 Avalonia Desktop 到 `.tmp/FlowWeaverPortable/Desktop/`
3. 确认 `EngineHost/runtime/` 不存在或已被清理
4. 运行 N.4 文件级便携目录 smoke
5. 运行 O.4 backend-only 端到端 smoke
6. 运行 O.11 Desktop 缺失/失败路径 smoke
7. 可选显式运行 O.10 真实 Desktop smoke
8. 检查归档输入目录不包含 token、SQLite runtime、日志或临时缓存
9. 生成 zip
10. 从 zip 解压到新的 `.tmp/` 目录做最小 smoke

P.0 只固化顺序，不实现 zip 或解压 smoke。

## 7. 用户手册边界

第一版用户文档建议分两层：

| 文件 | 位置 | 用途 |
| --- | --- | --- |
| `docs/README.txt` | 便携包内 | 解压后第一眼启动说明 |
| `docs/FlowWeaver_便携版用户手册.md` | 仓库文档，后续可复制到发布包 | 较完整的用户手册 |

便携包内 `README.txt` 应保持短小，只包含：

- 先启动哪个入口
- backend-only 与 Desktop combo 的区别
- 默认 BaseUrl
- token 文件位置
- 日志目录位置
- 不要分享 token
- 常见启动失败时看哪个日志

完整用户手册建议包含：

- 解压位置建议
- 首次启动流程
- 后端诊断入口
- 桌面组合入口
- token 获取和输入
- health 检查
- 如何查看日志
- 如何重启 EngineHost
- 如何保留或备份 `EngineHost/runtime/`
- 常见问题和故障排查
- 如何升级：先备份 runtime，再替换程序文件
- 明确不支持：安装器、后台服务、自动更新、多实例接管

P.0 不编写完整用户手册正文，只确认目录和章节。

## 8. 安全与隐私边界

发布归档必须避免包含：

- `EngineHost/runtime/config/local_api_token`
- `EngineHost/runtime/metadata/flowweaver.db`
- `EngineHost/runtime/logs/`
- 用户连接配置
- 任何真实 token、Authorization header 或完整 WebSocket URL

归档生成前建议做文本扫描：

```text
token=
Authorization:
local_api_token
flowweaver.db
```

其中 `local_api_token` 作为文档中的路径名可以出现，但真实 token 文件不能出现。

## 9. 不做事项

P.0 明确不做：

- 不实现 zip 生成脚本
- 不实现 release manifest 写入
- 不生成正式发布包
- 不执行真实发布流程
- 不改 `create_portable_layout.py`
- 不改 `publish_desktop.py`
- 不改 `portable_launcher.py`
- 不改 Avalonia UI
- 不写完整用户手册正文
- 不创建安装器
- 不创建自动更新
- 不创建后台服务
- 不创建系统托盘
- 不做代码签名
- 不做 CI/CD 发布流水线

## 10. 后续建议顺序

P.0 后建议按以下顺序继续：

| 小步 | 方向 | 主要产出 | 暂不进入 |
| --- | --- | --- | --- |
| P.0a | 发布归档补充边界 | self-contained、runtime audit、版本统一、manifest/hash/license、clean-room 和手册警示 | 代码实现 |
| P.1 | 发布归档脚本方案 | 确认 `tools/create_portable_archive.py` 参数、版本来源、输入输出和安全检查 | 不写 zip 代码 |
| P.2 | runtime audit 与归档前检查 | 检查 `python312/` 清洁度、dev 包、cache、许可证和版本一致性 | 清理 runtime |
| P.3 | 最小归档脚本 | 从 `.tmp/FlowWeaverPortable/` 生成 zip、manifest 和外部 `.sha256` | 安装器、签名、上传 |
| P.4 | clean-room 解压 smoke | 仓库外、空格/中文路径 backend-only smoke | 默认真实 UI 自动化 |
| P.5 | 用户手册骨架 | 新增便携版用户手册章节骨架和 workflow 中断警示 | 完整截图教程 |
| P.6 | 用户手册内容收口 | 补启动、token、日志、备份、workflow 中断和故障排查 | 安装器文档 |
| P.7 | 阶段 P 验收复核 | 归档、manifest、hash、license、clean-room 和手册复核 | 自动更新 |

最稳下一步是 P.1：先做发布归档脚本方案，确认参数、版本、runtime audit、manifest、SHA-256、许可证和安全检查后，再决定是否实现最小 zip 生成。
