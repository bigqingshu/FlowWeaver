# FlowWeaver WORKFLOW-EDIT-2.4a：桌面 smoke 前置清单

> 审核状态（2026-07-05）：已实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：结构化只读解析、节点新增/删除、connection 新增/删除、ViewModel 命令、View 接入、用户友好 warning/error、节点/connection 输入体验和 smoke 复核已经落地。
> 未实现：自由画布、拖拽连线、完整撤销/重做和复杂 DAG 自动重排未在本阶段实现。
> 原因：这些能力超出结构化编辑最小闭环，已作为后续体验方向保留。

> 文档状态：WORKFLOW-EDIT-2.4a 前置清单完成
> 当前阶段：结构化编辑真实路径验收前置
> 不适用范围：人工桌面点击执行、port schema 深校验、图形画布

## 1. 阶段目标

WORKFLOW-EDIT-2.1 到 2.3 已经完成结构化编辑的主要输入体验：

```text
错误提示可读化
+ node type 选择
+ node instance id 自动建议
+ connection source / target 选择
+ connection id 自动建议
```

2.4 需要进入真实路径 smoke，确认这些改动没有破坏 Desktop 与 EngineHost 的正式连接边界。

## 2. 当前可自动化 smoke

仓库已有以下自动化 smoke：

| 测试 | 覆盖范围 | 适合本阶段 |
| --- | --- | --- |
| `EngineHostFormalSmokeTests` | 源码 Desktop API client + EngineHost formal workflow edit/run loop | 是 |
| `DesktopPublishApiClientSmokeTests` | 发布 Desktop assembly API client 连接 portable EngineHost | 是 |
| `DesktopPublishRuntimeEventSmokeTests` | 发布 Desktop runtime event client 连接 portable EngineHost | 是 |
| `DesktopPublishWorkflowRunEventSmokeTests` | 发布 Desktop API + WebSocket，创建 workflow 并观察 run lifecycle event | 最贴近 2.4 自动 smoke |

这些测试会创建临时目录并启动独立 EngineHost，测试结束后清理自己启动的进程。

## 3. 当前不自动执行的 smoke

本阶段不直接自动启动完整 GUI 进行点击：

* `dotnet run` 会打开 Avalonia 桌面窗口并挂住当前执行流。
* 当前没有稳定的 Avalonia GUI 自动点击 harness。
* 直接启动真实 Desktop 可能影响用户当前桌面环境。

因此 2.4 先采用“发布 Desktop client + EngineHost 正式路径”的自动 smoke；人工 GUI 操作作为后续手动复核项记录。

## 4. 建议自动化顺序

建议先跑最贴近当前阶段的发布 Desktop workflow run 事件 smoke：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "DesktopPublishWorkflowRunEventSmokeTests"
```

若通过，再根据耗时选择是否补跑：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "EngineHostFormalSmokeTests|DesktopPublishApiClientSmokeTests|DesktopPublishRuntimeEventSmokeTests"
```

最后仍应保留：

```text
dotnet build Avalonia_UI\Avalonia_UI.sln --no-restore
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
```

## 5. 手动 Desktop smoke 清单

后续人工桌面 smoke 至少覆盖：

* 启动 EngineHost。
* 启动 Desktop。
* 连接 EngineHost health 成功。
* 刷新 node catalog。
* 加载 workflow definition。
* 在结构化表单中选择 node type。
* 自动生成 node instance id。
* 添加 node。
* 在 connection 表单中选择 source / target。
* 自动生成 connection id。
* 填写 port。
* 添加 connection。
* 删除 connection。
* 删除 node。
* Validate。
* Save。
* 重新加载 definition 后确认 JSON 保持一致。

## 6. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.4b：
发布 Desktop workflow run event 自动 smoke。
```

如果自动 smoke 失败，优先修正式路径问题，不在 UI 内绕过。
