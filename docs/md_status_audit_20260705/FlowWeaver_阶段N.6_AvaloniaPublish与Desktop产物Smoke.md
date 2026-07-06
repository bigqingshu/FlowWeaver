# FlowWeaver 阶段N.6：Avalonia Publish 与 Desktop 产物 Smoke

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：正式路径运行闭环、便携 layout、后端 runtime smoke、Avalonia publish、Desktop 产物 API/WebSocket/workflow run 联调 smoke 和阶段 N 验收已经落地。
> 未实现：无本文件目标内的未实现项；安装器和签名等不属于 N 阶段。
> 原因：当前 N 阶段定位是便携发布联调，不承担后续分发产品化。

> 文档状态：阶段N.6完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段K/L/M/N.0-N.5完成记录
> 适用范围：Avalonia `dotnet publish`、`.tmp/FlowWeaverPortable/Desktop/` 文件级产物 smoke
> 当前执行点：只验证 Desktop 发布产物，不启动 UI、不让 UI 托管 EngineHost、不创建安装器

## 1. 目标

N.6 的目标是把 N.3/N.4 设计中的 `Desktop/` 目录从占位目录推进到可生成的 Avalonia 发布产物目录，并做最小文件级 smoke。

本阶段验证：

- 可以执行 Avalonia Release publish
- 发布输出目录固定在 `.tmp/FlowWeaverPortable/Desktop/`
- 产物包含桌面端主程序、主 dll、deps 和 runtimeconfig
- Release 发布产物不包含 `Avalonia.Diagnostics.dll`
- 产物包含 Avalonia 和 CommunityToolkit.Mvvm 依赖

## 2. 本阶段修改清单

- 新增 `tools/publish_desktop.py`
- 新增 `tests/integration/test_n6_desktop_publish_smoke.py`
- 新增 `docs/FlowWeaver_阶段N.6_AvaloniaPublish与Desktop产物Smoke.md`
- 更新 README 当前阶段和下一步建议

本阶段不修改：

- Python 后端产品代码
- Avalonia UI 产品代码
- `Avalonia_UI.csproj`
- `tools/create_portable_layout.py`
- 安装器、启动脚本、后台服务或自动更新

## 3. Desktop Publish 工具

新增命令：

```powershell
.\python312\python.exe tools\publish_desktop.py
```

默认行为：

- 调用 `dotnet publish`
- 项目为 `Avalonia_UI/Avalonia_UI.csproj`
- configuration 为 `Release`
- runtime 为 `win-x64`
- self-contained 为 `false`
- 输出到 `.tmp/FlowWeaverPortable/Desktop/`

安全边界：

- 输出目录必须是仓库 `.tmp/` 的子目录
- 不允许输出到仓库根目录、源码目录或用户目录
- 不启动发布后的 UI
- 不读取或写入 EngineHost token
- 不修改 UI 连接配置

## 4. 测试路径

新增测试命令：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n6_desktop_publish_smoke.py -q
```

测试执行：

1. 清理 `.tmp/FlowWeaverPortable/Desktop/`
2. 调用 `tools/publish_desktop.py` 的 `publish_desktop()`
3. 执行 `dotnet publish Avalonia_UI/Avalonia_UI.csproj`
4. 验证 `Avalonia_UI.exe`
5. 验证 `Avalonia_UI.dll`
6. 验证 `Avalonia_UI.deps.json`
7. 验证 `Avalonia_UI.runtimeconfig.json`
8. 验证 Release 产物不包含 `Avalonia.Diagnostics.dll`
9. 验证存在 Avalonia 相关 dll
10. 验证存在 CommunityToolkit.Mvvm 相关 dll

## 5. 验收结果

已执行：

```powershell
.\python312\python.exe -m pytest tests/integration/test_n6_desktop_publish_smoke.py -q
```

结果：

```text
1 passed
```

已执行：

```powershell
.\python312\python.exe -m ruff check tools/publish_desktop.py tests/integration/test_n6_desktop_publish_smoke.py
```

结果：

```text
All checks passed!
```

## 6. 明确不在 N.6 实现

N.6 不做：

- 不启动 Avalonia UI
- 不用 UI 连接 EngineHost
- 不让 UI 启动或停止 EngineHost
- 不生成发布压缩包
- 不创建 `start-enginehost.ps1`
- 不创建 `start-desktop.ps1`
- 不创建安装器、后台服务、系统托盘或自动更新
- 不提交 `.tmp/` 生成物

## 7. 下一步建议

N.6 后建议进入 N.7：Desktop 发布产物 API 客户端联调前置 smoke。

N.7 建议保持小步：

- 继续使用 `.tmp/FlowWeaverPortable/EngineHost/` 启动后端
- 使用已发布的 Desktop 产物目录作为 UI 文件来源
- 先不启动可视化窗口
- 优先复用 Avalonia API Client 层做已发布产物路径下的连接配置、health 和基础 API 联调
- 不进入安装器、系统托盘或 UI 托管后端
