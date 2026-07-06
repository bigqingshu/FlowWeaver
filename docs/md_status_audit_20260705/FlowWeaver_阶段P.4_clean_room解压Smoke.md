# FlowWeaver 阶段P.4：clean-room 解压 smoke

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P.4完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录、阶段P.0、阶段P.0a、阶段P.1、阶段P.2和阶段P.3文档
> 适用范围：P.3 归档 zip 在仓库外、空格/中文路径下的 backend-only 正式启动验收
> 当前执行点：新增 clean-room backend-only smoke，不进入真实 Desktop、安装器、签名或上传

## 1. 目标

P.4 的目标是验证 P.3 生成的便携 zip 不依赖仓库工作目录，解压到仓库外、包含空格和中文的路径后，可以使用发布包内的 `python312` 和 `portable_launcher.py --no-desktop` 启动 EngineHost。

本阶段完成：

- 新增 `tests/integration/test_p4_portable_archive_clean_room_smoke.py`
- 从真实便携 layout 生成 zip 和 `.sha256`
- 校验外部 `.sha256`
- 解压到 `%TEMP%` 下仓库外 clean-room 目录
- clean-room 路径包含空格和中文
- 清理启动环境中的 `PYTHONPATH`
- 使用解压后的 `EngineHost/python312/python.exe`
- 启动 `portable_launcher.py --no-desktop`
- 验证 health、token 鉴权和 `GET /api/v1/workflows`
- 验证首次启动后生成 `runtime/`、token、数据库和 logs
- 验证 launcher 日志不泄漏 token

本阶段不做：

- 不打开真实 Desktop
- 不做 UI 自动化
- 不做安装器
- 不做代码签名
- 不上传发布物
- 不清理 `python312/`
- 不改变 Desktop framework-dependent 默认

## 2. 新增测试

新增：

```text
tests/integration/test_p4_portable_archive_clean_room_smoke.py
```

测试流程：

1. 调用 `tools/create_portable_layout.py` 生成临时便携 layout
2. 调用 `tools/create_portable_archive.py` 生成 zip 和 `.sha256`
3. 验证 `.sha256` 与 zip 实际 SHA-256 一致
4. 解压到仓库外 clean-room 路径：

```text
%TEMP%\FlowWeaver Clean Room 中文路径 <uuid>\FlowWeaverPortable\
```

5. 验证 clean-room 路径不在仓库目录内
6. 验证路径包含空格和 `中文路径`
7. 验证首次启动前 `EngineHost/runtime/` 不存在
8. 清理 `PYTHONPATH`
9. 从 clean-room 便携根目录启动：

```powershell
EngineHost\python312\python.exe portable_launcher.py --no-desktop --port <free_port> --health-timeout-seconds 30
```

10. 验证 `GET /api/v1/health`
11. 读取 `EngineHost/runtime/config/local_api_token`
12. 使用 token 验证 `GET /api/v1/workflows`
13. 验证 runtime 数据库、token 文件和 logs 已生成
14. 优雅停止 launcher 并确认 health 不再可达
15. 清理临时 layout、归档输出和 clean-room 目录

## 3. 覆盖范围

P.4 覆盖：

| 验收项 | 状态 |
| --- | --- |
| zip 外部 `.sha256` 可校验 | 已覆盖 |
| 仓库外解压 | 已覆盖 |
| 空格路径 | 已覆盖 |
| 中文路径 | 已覆盖 |
| 不依赖仓库 cwd | 已覆盖 |
| 使用包内 `python312` | 已覆盖 |
| `PYTHONPATH` 清理 | 已覆盖 |
| 首次启动前无 runtime | 已覆盖 |
| 首次启动后生成 runtime | 已覆盖 |
| health | 已覆盖 |
| token 鉴权 | 已覆盖 |
| workflow list | 已覆盖 |
| launcher token 脱敏 | 已覆盖 |

P.4 不覆盖：

| 项目 | 后续处理 |
| --- | --- |
| 真实 Desktop clean-room | 后续如需要单独增加显式环境变量触发 |
| 安装器 | 阶段P不进入 |
| 自动更新 | 阶段P不进入 |
| 代码签名 | 阶段P不进入 |
| 完整用户手册 | P.5/P.6 |

## 4. 发现与边界确认

P.4 复用 P.3 的归档产物和 P.2 的 audit 规则。P.3 中已修正 `pip --version` 可能生成 `__pycache__/*.pyc` 的问题，真实 P.4 解压 smoke 不再要求 zip 内带有 cache。

当前真实归档仍可能记录：

```text
runtime_audit_status = warning
```

这是预期行为，因为仓内 `python312/` 仍包含 dev/test/build 或旧 GUI 包。P.4 验证的是便携发布物可启动，不声称 runtime 已是干净最小正式发布运行时。

## 5. 验证

本阶段已运行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tests\integration\test_p4_portable_archive_clean_room_smoke.py
```

后续阶段复核建议同时运行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_archive.py tools\portable_runtime_audit.py tests\unit\test_create_portable_archive.py tests\unit\test_portable_runtime_audit.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
```

## 6. 下一步建议

进入 P.5：便携版用户手册骨架。

P.5 建议先建立用户手册文件和章节骨架，明确启动方式、token、日志、备份、关闭 Desktop 对运行中 workflow 的影响和当前不支持能力；P.6 再补正文细节。
