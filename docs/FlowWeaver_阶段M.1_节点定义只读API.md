# FlowWeaver 阶段M.1：节点定义只读API

> 文档状态：阶段M.1完成记录
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段M.0边界清单
> 适用范围：Avalonia UI 进入 workflow 定义查看和最小编辑前的节点类型查询边界
> 当前执行点：只实现节点定义只读 API、Avalonia DTO / API Client 和对应测试

## 1. 目标

M.1 的目标是让 Avalonia UI 可以从 EngineHost 查询当前后端实际注册、且普通 UI 默认可见的节点类型。

本阶段只做：

- 后端 `GET /api/v1/node-definitions`
- 显式 API DTO，不直接暴露内部 `NodeDefinitionSpec`
- 默认隐藏 `DelayTestNode` 和 `FaultTestNode`
- Avalonia DTO 和 `EngineHostApiClient.ListNodeDefinitionsAsync()`
- 后端和桌面端客户端测试

本阶段不做：

- 不实现 workflow 创建 UI
- 不实现 workflow detail / revision UI 接入
- 不实现节点配置表单或 `config_schema`
- 不实现动态表单、画布、拖拽或连线
- 不新增插件市场、分类、图标或按权限过滤节点类型

## 2. 后端接口

新增接口：

```text
GET /api/v1/node-definitions
```

接口特征：

- 使用统一 API envelope
- 需要本地 API token
- 受既有 Origin 检查保护
- 数据来源为 `ServiceContainer.node_registry`
- 返回字段由显式 API view 映射生成

当前返回的普通 UI 可见节点：

| 节点 | 版本 | 结论 |
| --- | --- | --- |
| `GenerateTestTableNode` | `1.0` | 可见 |
| `FilterRowsNode` | `1.0` | 可见 |
| `PublishSharedTablesNode` | `1.0` | 可见 |
| `ReadSharedTablesNode` | `1.0` | 可见 |

当前默认隐藏节点：

| 节点 | 原因 |
| --- | --- |
| `DelayTestNode` | 长任务、heartbeat、cancel 验收节点 |
| `FaultTestNode` | 失败策略、异常路径验收节点 |

## 3. API DTO

新增后端 view：

```text
NodeDefinitionView
NodePortDefinitionView
```

返回字段：

```json
{
  "node_type": "GenerateTestTableNode",
  "node_version": "1.0",
  "display_name": "Generate Test Table",
  "input_ports": [],
  "output_ports": [
    { "name": "out", "required": false }
  ],
  "execution_mode": "PROCESS_POOL",
  "default_timeout_seconds": 60,
  "retry_safe": false,
  "ui_visibility": "visible"
}
```

明确不返回：

- `implementation_path`
- `config_schema`
- Python executor 或实现路径细节

## 4. Avalonia Client

新增桌面端 DTO：

```text
NodeDefinitionDto
NodePortDefinitionDto
```

新增 API Client 方法：

```text
ListNodeDefinitionsAsync(settings, cancellationToken)
```

该方法走既有 HTTP envelope、BaseUrl 构造和 Bearer token 逻辑。M.1 暂不把它接入节点选择器或 workflow 编辑页面。

## 5. 验收测试

执行时间：2026-06-29

已运行：

```powershell
.\python312\python.exe -m ruff check src tests
.\python312\python.exe -m pytest -q tests\integration\test_api.py -k "node_definitions"
.\python312\python.exe -m pytest -q tests\integration\test_api.py
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --filter EngineHostApiClientTests --logger "console;verbosity=minimal"
dotnet test Avalonia_UI.Tests\Avalonia_UI.Tests.csproj --logger "console;verbosity=minimal"
dotnet build Avalonia_UI\Avalonia_UI.sln
```

结果：

| 命令 | 结果 |
| --- | --- |
| ruff `src tests` | PASS |
| pytest node definitions 定向测试 | PASS，2 passed，1 个 Starlette / httpx 上游弃用 warning |
| pytest `tests/integration/test_api.py` | PASS，19 passed，1 个 Starlette / httpx 上游弃用 warning |
| Avalonia client 定向测试 | PASS，17 passed |
| Avalonia 全量测试 | PASS，59 passed |
| Avalonia solution build | PASS，0 warnings，0 errors |

## 6. 阶段结论

M.1 已完成。

当前 UI 已具备查询后端可用普通节点定义的客户端入口，但还没有展示或编辑入口。下一步建议进入：

```text
M.2：Workflow detail / revision API 客户端接入
```

M.2 建议只补 UI API Client 对 workflow detail、revisions、validate 等已有后端接口的调用能力，并保留 `base_revision_id` / revision 防覆盖前置字段，不进入正式编辑保存。
