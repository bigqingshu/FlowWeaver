# FlowWeaver UI Backend Facts Contract

本文档固化 Avalonia UI 派生 ActionState 时可以依赖的后端事实。Gemini 只能依赖本文档已明确的事实，不得根据错误 Message 文本反推业务语义。

当前版本先完成 `UI-ACTION-0a` 的 RunMonitor 最小事实冻结。后续 Workflow Definition、Data、Logs、NodeDefinition 等事实按小步继续补充。

## 1. 连接与鉴权事实

当前 `GET /api/v1/health` 不需要 Bearer Token，只能证明 EngineHost HTTP 可访问。

UI 需要区分以下事实：

| 事实 | 来源 | UI 含义 |
| --- | --- | --- |
| HTTP未检查 | 尚未执行 health 或业务请求 | 不显示为已连接 |
| HTTP正在检查 | 正在执行 health | 禁用重复检查 |
| HTTP可访问 | health 返回 `ok=true` 且 `data.status=ok` | EngineHost 在线 |
| HTTP不可访问 | health 或请求连接失败 | 依赖 EngineHost 的动作不可用 |
| Token缺失 | 本地 Token 为空 | 需要 Bearer 的动作不可用 |
| Token待验证 | Token非空，但尚未有鉴权业务请求成功或失败 | 可发起业务请求，但不得显示为鉴权成功 |
| 鉴权成功 | Bearer 业务接口成功返回 | 可使用需要鉴权的业务动作 |
| 鉴权失败 | Bearer 业务接口返回 `UNAUTHORIZED` | 需要鉴权的业务动作不可用，直到 Token 变化或重新检查 |

最小 UI 可以在 Token 待验证时允许用户触发业务请求，由请求结果把状态推进为鉴权成功或鉴权失败。不得把 health 成功文案写成 Token 鉴权成功。

本地 API Client 稳定错误码：

| 错误码 | 含义 | UI 处理 |
| --- | --- | --- |
| `TOKEN_REQUIRED` | 需要 Token 但当前为空 | 禁用或提示填写 Token |
| `INVALID_BASE_URL` | BaseUrl无效 | 禁用 EngineHost 动作，提示修正 BaseUrl |
| `INVALID_RESPONSE` | 返回不是合法 API Envelope 或 JSON无效 | 作为技术错误显示 |
| `REQUEST_TIMEOUT` | 请求超时 | 可提示重试 |
| `REQUEST_FAILED` | HTTP请求失败 | 可提示 EngineHost 不可访问 |
| `UNAUTHORIZED` | 后端拒绝 Token | 标记鉴权失败 |

## 2. RunMonitor 最小事实

### 2.1 WorkflowRun status

当前 `WorkflowRun.status` 枚举值：

```text
PENDING
RUNNING
SUCCEEDED
FAILED
CANCELLED
ABORTED
```

当前终态集合：

```text
SUCCEEDED
FAILED
CANCELLED
ABORTED
```

非终态集合：

```text
PENDING
RUNNING
```

未知 status 必须保守处理为不可执行取消动作，并显示“未知状态”类禁用原因。

### 2.2 UI-ACTION-1 可取消集合

`UI-ACTION-1` 最小可取消集合只包括：

```text
RUNNING
```

`PENDING` 暂不启用取消按钮。原因是 cancel 后端虽然可以给已存在的 workflow process 标记取消请求，但 process 创建与 workflow run 从 `PENDING` 转为 `RUNNING` 之间存在窗口期；在补充正式验收前，UI 不应承诺 `PENDING` 可取消。

后续如需把 `PENDING` 纳入可取消集合，必须先补充：

- process 已创建但 run 仍为 `PENDING` 时 cancel 成功的后端验收。
- process 尚未创建时 cancel 返回 `WORKFLOW_PROCESS_NOT_FOUND` 的 UI 文案。
- WebSocket/REST 刷新后 run 状态从 `PENDING` 到 `RUNNING` 的按钮状态变化验收。

### 2.3 CancelRunAsync

客户端方法：

```text
CancelRunAsync(settings, workflowRunId, cancellationToken)
```

HTTP 接口：

```text
POST /api/v1/runs/{workflow_run_id}/cancel
```

成功响应：

- API Envelope `ok=true`。
- `data` 为 `WorkflowProcessDto`。
- `WorkflowProcessDto.status` 可能为 `STARTING`、`RUNNING`、`CANCEL_REQUESTED`、`EXITED`、`LOST` 或 `FAILED`，前端不得用该 process status 覆盖 `WorkflowRun.status`。
- 成功只表示取消请求已送达或 process 已被读取，不代表 workflow run 已立即进入 `CANCELLED`。

已知失败错误码：

| 错误码 | HTTP | UI 语义 |
| --- | --- | --- |
| `WORKFLOW_RUN_NOT_FOUND` | 404 | 选中的 run 已不存在，应刷新运行列表 |
| `WORKFLOW_PROCESS_NOT_FOUND` | 404 | 当前 run 没有关联 process 或 process 已不可取消，应刷新运行列表 |
| `UNAUTHORIZED` | 401 | Token 错误、轮换或失效，应标记鉴权失败 |

### 2.4 RunMonitor ActionState 规则

`CancelSelectedRun` 最小启用条件：

```text
BaseUrl有效
Token非空
未处于已知鉴权失败
SelectedRun != null
SelectedRun.Status == RUNNING
!IsRunBusy
```

禁用原因优先级：

```text
1. 正在刷新或取消运行
2. EngineHost不可访问、BaseUrl无效或Token缺失
3. 已知鉴权失败
4. 未选择Run
5. Run状态未知
6. Run不是RUNNING
```

点击可用的取消按钮后必须先确认。确认文案至少说明：

```text
确认取消当前运行？
已完成节点不会回滚。
```

取消成功后应刷新 run 列表，并以最终 `WorkflowRun.status` 显示状态。

## 3. 不在 UI-ACTION-1 范围内

- 不把 `PENDING` 作为可取消状态。
- 不实现关闭 Desktop 时的运行中 workflow 提醒。
- 不新增后端字段，例如 `show_cancel_button`、`enable_cancel_button`。
- 不新增复杂 Run 详情页。
- 不改变 cancel 后端协议。
