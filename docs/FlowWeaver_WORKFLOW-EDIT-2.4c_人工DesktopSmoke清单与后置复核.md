# FlowWeaver WORKFLOW-EDIT-2.4c：人工 Desktop smoke 清单与后置复核

> 文档状态：WORKFLOW-EDIT-2.4c 清单与后置复核完成
> 当前阶段：结构化编辑真实路径验收
> 不适用范围：已执行人工 GUI 点击、port schema 深校验、图形画布

## 1. 背景

WORKFLOW-EDIT-2.4b 已通过发布 Desktop API/WebSocket 自动 smoke：

```text
dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore --filter "DesktopPublishWorkflowRunEventSmokeTests"
通过：1，失败：0，跳过：0
```

该 smoke 证明发布 Desktop assembly 中的 API client 与 RuntimeEvent WebSocket client 可以连接 portable EngineHost，并完成 workflow run lifecycle。

但它不等同于人工 GUI 点击 smoke。

## 2. 自动 smoke 已覆盖

已覆盖：

* Desktop 发布产物生成。
* portable EngineHost 独立启动。
* token 读取。
* `EngineHostApiClient` 正式连接。
* `EngineHostRuntimeEventStreamClient` 正式连接。
* 创建 workflow。
* 启动 workflow run。
* 接收 `WORKFLOW_STARTED` / `WORKFLOW_FINISHED`。

## 3. 自动 smoke 未覆盖

尚未覆盖：

* 打开真实 Desktop 窗口。
* 在 UI 中点击 health check。
* 在 UI 中刷新 node catalog。
* 在 UI 中加载 workflow definition。
* 在 UI 中选择 node type ComboBox。
* 在 UI 中确认 node instance id 自动建议。
* 在 UI 中点击 Add node。
* 在 UI 中选择 connection source / target ComboBox。
* 在 UI 中确认 connection id 自动建议。
* 在 UI 中填写 source / target port。
* 在 UI 中点击 Add connection。
* 在 UI 中 Validate / Save。
* 重新加载 workflow definition 并肉眼确认 JSON。

## 4. 人工 Desktop smoke 建议步骤

建议人工执行：

```text
1. 启动 EngineHost。
2. 启动 Avalonia Desktop。
3. 确认 health check 成功。
4. 打开 Workflow 页面。
5. 刷新 workflow list。
6. 创建或选择一个测试 workflow。
7. 加载 workflow definition。
8. 刷新 node catalog。
9. 在新增节点表单选择 GenerateTestTableNode。
10. 确认 node type / version / display name 已填充。
11. 确认 node instance id 自动建议。
12. 填写 config JSON。
13. 点击 Add node。
14. 再添加 FilterRowsNode。
15. 在新增 connection 表单选择 source / target。
16. 确认 connection id 自动建议。
17. 填写 source / target port。
18. 点击 Add connection。
19. 点击 Validate。
20. 点击 Save。
21. 重新加载 definition。
22. 确认 nodes / connections 已保留。
23. 删除 connection。
24. 删除 node。
25. 再次 Validate / Save。
```

## 5. 当前结论

当前可以确认：

* 自动发布路径 smoke 已通过。
* 结构化编辑 ViewModel / XAML 改动未破坏发布 Desktop API/WebSocket 基础链路。
* 人工 GUI 点击 smoke 尚未执行。

因此 WORKFLOW-EDIT-2 还不能宣称完整完成；仍需要人工 Desktop 点击 smoke 或等价的 GUI 自动化 harness。

## 6. 下一小步建议

建议进入：

```text
WORKFLOW-EDIT-2.4d：
Headless GUI 自动 smoke，先补齐 View 运行时加载与关键绑定验收。
```

人工 Desktop 点击 smoke 仍保留为后续人工验收项；如果暂时不执行人工点击，可先用 2.4d 的 Headless smoke 作为自动回归边界。
