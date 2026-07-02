# FlowWeaver WORKFLOW-EDIT-2.4b：发布 Desktop workflow run event 自动 smoke

> 文档状态：WORKFLOW-EDIT-2.4b 自动 smoke 完成
> 当前阶段：结构化编辑真实路径验收
> 不适用范围：人工桌面点击、port schema 深校验、图形画布

## 1. 阶段目标

执行发布 Desktop assembly/API client + portable EngineHost 的正式路径自动 smoke，确认当前 Desktop 发布客户端仍能：

* 连接独立 EngineHost。
* 读取 token。
* 建立 RuntimeEvent WebSocket。
* 创建 workflow。
* 启动 workflow run。
* 接收 workflow lifecycle events。

## 2. 执行命令

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "DesktopPublishWorkflowRunEventSmokeTests"
```

## 3. 执行结果

```text
已通过
失败：0
通过：1
跳过：0
总计：1
持续时间：14 s
```

## 4. 覆盖边界

本 smoke 覆盖：

* 临时 portable layout 生成。
* Desktop 发布产物生成。
* 发布产物中 `Avalonia_UI.exe` 和 `Avalonia_UI.dll` 存在。
* 独立 portable EngineHost 启动。
* EngineHost health 变为 ok。
* 从 portable runtime 读取 `local_api_token`。
* 使用发布 Desktop assembly 中的 `EngineHostApiClient`。
* 使用发布 Desktop assembly 中的 `EngineHostRuntimeEventStreamClient`。
* WebSocket 首包收到 `ENGINE_READY`。
* 创建空 workflow。
* 启动 workflow run。
* 收到 `WORKFLOW_STARTED` 和 `WORKFLOW_FINISHED`。

## 5. 未覆盖边界

本 smoke 仍不覆盖：

* 人工 GUI 点击。
* 在真实窗口中选择 node type / source / target。
* 通过 GUI 添加 node / connection。
* GUI Validate / Save 操作。
* 关闭 Desktop 后 EngineHost 生命周期观察。

这些仍应保留到人工 Desktop smoke。

## 6. 当前结论

发布 Desktop API/WebSocket 正式路径保持可用，WORKFLOW-EDIT-2.1 到 2.3 的 ViewModel/XAML 改动没有破坏发布 Desktop client 与 EngineHost 的基本 run lifecycle 链路。

建议下一步：

```text
WORKFLOW-EDIT-2.4c：
结构化编辑人工 Desktop smoke 清单与后置复核。
```

如果暂时不做人工点击，应在 2.4c 中明确记录自动 smoke 已覆盖和未覆盖的边界。
