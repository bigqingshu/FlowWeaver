# FlowWeaver WORKFLOW-EDIT-2.7：推送前总复核与人工 Desktop smoke 确认

> 文档状态：WORKFLOW-EDIT-2.7 推送前总复核完成
> 当前阶段：节点配置与结构化编辑主线推送前复核
> 不适用范围：推送、真实人工 Desktop 点击执行、新增功能实现、port schema 深校验、图形画布

## 1. 阶段目标

在不新增功能、不推送的前提下，对当前本地待推送范围做总复核：

* 当前分支状态。
* 待推送提交范围。
* 当前验证结果。
* 人工 Desktop smoke 是否阻塞推送。
* 下一步应等待用户确认的事项。

## 2. 当前分支状态

当前状态：

```text
main...origin/main [ahead 23]
工作区干净
```

本地领先 `origin/main` 23 个提交，尚未推送。

## 3. 待推送提交范围

当前待推送提交为：

```text
59a5020 补充结构化编辑View文本属性
fcfc72b 明确结构化编辑View修改任务
f9a6c12 接入结构化编辑表单View
d85093e 复核结构化编辑View接入
e296e92 复核工作流结构化编辑第一阶段
65624a2 明确结构化编辑第二阶段边界
110f903 本地化结构化编辑错误提示
842d867 分析节点新增输入体验边界
f143dfb 接入节点新增定义选择状态
db9a7c5 说明新增节点View接入边界
75f8351 接入新增节点目录选择View
118cb32 复核节点新增输入体验
5dee1b3 分析连接输入体验边界
5f53590 接入连接端点选择状态
937d80e 说明连接View接入边界
aa90032 接入连接端点选择View
109a079 复核连接输入体验
823c944 明确结构化编辑桌面Smoke清单
fc9ad91 记录桌面发布事件Smoke
a163979 复核结构化编辑桌面Smoke边界
379f0ef 补充WorkflowSummaryView Headless自动Smoke
b5528fa 总结结构化编辑第二阶段边界
4ef42a1 审计结构化编辑目标完成状态
```

## 4. 本次验证结果

本次推送前总复核补跑：

```text
.\python312\python.exe -m pytest -q tests\integration\test_api.py -k "node_definitions"
通过：2，失败：0，跳过：0
提示：FastAPI/TestClient 依赖层 StarletteDeprecationWarning，不影响本次断言。

dotnet test Avalonia_UI\Avalonia_UI.sln --no-restore
通过：265，失败：0，跳过：0
```

当前验证覆盖：

* 后端 node definitions / config_schema API 关键事实。
* Avalonia API DTO、schema parser、节点目录、节点配置表单、workflow edit、Headless GUI smoke 等全量测试集合。

## 5. 人工 Desktop smoke 是否阻塞

当前事实：

* 发布 Desktop API/WebSocket 自动 smoke 已完成。
* `WorkflowSummaryView` Headless GUI smoke 已完成。
* 真实人工 Desktop 点击 smoke 尚未执行。

决策建议：

* 如果人工 Desktop smoke 被视为发布前手动验收项，则当前本地提交可进入推送确认。
* 如果人工 Desktop smoke 被视为 WORKFLOW-EDIT-2 必需验收项，则暂不应推送，下一步应执行真实 Desktop 手动 smoke。
* 不建议用伪造点击或在 UI 内绕过正式路径来替代该决策。

## 6. 下一步等待确认

需要用户确认二选一：

```text
方案 A：
人工 Desktop smoke 不阻塞当前推送。
下一步执行 git push，并保留人工 smoke 为发布前手动验收项。

方案 B：
人工 Desktop smoke 阻塞当前推送。
下一步先执行真实 Desktop 手动 smoke，不进入新功能。
```

未经明确确认，不应继续扩展 port/schema/画布能力，也不应直接推送。
