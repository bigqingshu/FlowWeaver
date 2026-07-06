# FlowWeaver 阶段P+2：真实 Desktop clean-room smoke

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+2完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7、P+1 和 `docs/FlowWeaver_阶段P后_边界分析.md`
> 适用范围：便携 zip、仓库外空格/中文路径解压、真实 Desktop 最小进程级 smoke、launcher 日志脱敏与退出清理
> 当前执行点：只做 P+2 小步，不进入窗口点击、截图、UI 内 workflow 操作、安装器、签名、自动更新、后台服务或 self-contained Desktop

## 1. 目标

P+2 的目标是在 P.4 backend-only clean-room smoke 和 O.10 真实 Desktop smoke 的基础上，验证真实发布 zip 解压到仓库外路径后，Desktop 组合入口仍能最小启动并完成清理。

本阶段完成：

- 新增 `tests/integration/test_pplus2_portable_archive_desktop_clean_room_smoke.py`
- 使用 `tools/create_portable_layout.py` 生成便携 layout
- 使用 `tools/publish_desktop.py` 将 Avalonia Desktop 发布到便携 `Desktop/`
- 使用 `tools/create_portable_archive.py` 生成 zip 与 `.sha256`
- 解压 zip 到 `%TEMP%` 下包含空格和中文的仓库外路径
- 使用解压后的 `EngineHost/python312/python.exe portable_launcher.py` 启动真实 Desktop 组合路径
- 验证 EngineHost health、token 鉴权、workflow 列表、Desktop pid 日志、日志文件生成、退出清理和 token 脱敏

本阶段不做：

- 不做窗口点击
- 不做截图
- 不做 UI 内 workflow 操作
- 不改变 `start_flowweaver.cmd` backend-only 默认语义
- 不改变 EngineHost、Desktop、token、runtime 或 workflow 行为
- 不进入安装器、代码签名、自动更新、后台服务或 self-contained Desktop

## 2. 显式环境变量保护

真实 Desktop clean-room smoke 可能打开 Avalonia 窗口，因此默认跳过。

执行前需要显式设置：

```powershell
$env:FLOWWEAVER_RUN_DESKTOP_CLEAN_ROOM_SMOKE = "1"
```

默认未设置时，该测试只会被 pytest 标记为 skipped，不会启动真实 Desktop。

## 3. 验收边界

P+2 只验证进程级最小路径：

```text
create portable layout
→ publish Desktop
→ create portable archive
→ verify .sha256
→ clean-room extract
→ start portable_launcher.py
→ EngineHost health
→ token auth GET /api/v1/workflows
→ Desktop pid logged
→ CTRL_BREAK cleanup
→ EngineHost unreachable
→ Desktop process exits
→ token not leaked
```

## 4. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\integration\test_pplus2_portable_archive_desktop_clean_room_smoke.py
$env:FLOWWEAVER_RUN_DESKTOP_CLEAN_ROOM_SMOKE = "1"; .\python312\python.exe -m pytest -q tests\integration\test_pplus2_portable_archive_desktop_clean_room_smoke.py; Remove-Item Env:\FLOWWEAVER_RUN_DESKTOP_CLEAN_ROOM_SMOKE
.\python312\python.exe -m ruff check tests\integration\test_pplus2_portable_archive_desktop_clean_room_smoke.py
git diff --check
```

结果：

```text
默认 pytest：1 skipped
显式 Desktop clean-room smoke：1 passed
ruff：All checks passed!
git diff --check：passed
```

## 5. 阶段结论

P+2 可以视为真实 Desktop clean-room smoke 的最小验收闭环。

下一步建议进入 P+3：第三方许可证增强方案，先做方案分析，不直接扩大归档脚本或 runtime audit 行为。
