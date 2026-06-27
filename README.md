# FlowWeaver

模块化数据工作流运行平台。

## 当前阶段

当前已实现第一阶段的阶段 A、阶段 B、阶段 C 和阶段 C.5 的控制面基础收口。

阶段 A 范围包括：

- `pyproject.toml` 项目配置
- Pydantic 公共协议模型
- 字符串枚举
- MessagePack 序列化与反序列化
- 统一错误模型
- 协议单元测试

阶段 B 范围包括：

- SQLAlchemy 元数据模型
- Alembic 初始化与首个迁移
- SQLite 元数据表
- 工作流定义基础 CRUD
- 工作流运行记录基础 CRUD
- 迁移与 RuntimeStore 集成测试

阶段 C 范围包括：

- FastAPI 应用入口
- 统一 API 响应结构
- 工作流定义 HTTP CRUD
- 工作流运行记录查询接口
- WebSocket 事件连接骨架
- API 集成测试

阶段 C.5 基础收口范围包括：

- 包名统一为 `flowweaver`
- 工作流不可变 revision 与 definition hash
- 严格 WorkflowDefinition 校验接口
- SQLite PRAGMA、`data_refs` 字段对齐与 `state_version`
- EngineHost Bootstrap、ServiceContainer、单实例锁与本地 token
- RuntimeEvent 持久化、EventRouter 与 WebSocket 广播
- API view 数据、统一 response_model 与本地 token 校验
- TableLeaseManager 最小 READ/WRITE 租约接口
- NodeRun/WorkflowRun `state_version` 竞争保护验收
- Ruff、mypy 与 Windows CI

尚未实现 WorkflowRunProcess、NodeExecutor、SQLite 运行表数据面、共享表执行逻辑、权限审计服务和 UI。

## 环境

目标环境：

- Windows 10/11
- Python 3.12
- uv

同步依赖：

```powershell
py -3.12 -m uv sync --extra dev
```

如果本机还没有 `uv`，可以先在当前 Python 3.12 环境中安装：

```powershell
py -3.12 -m pip install uv
```

运行测试：

```powershell
.\python312\python.exe -m pytest
```

静态检查：

```powershell
.\python312\python.exe -m ruff check src tests migrations
.\python312\python.exe -m mypy
```

对指定 SQLite 元数据库执行迁移：

```powershell
.\python312\Scripts\alembic.exe -c alembic.ini -x database_url=sqlite:///runtime/metadata/flowweaver.db upgrade head
```

启动本机 EngineHost API：

```powershell
.\python312\Scripts\uvicorn.exe --app-dir src flowweaver.api.app:create_default_app --factory --host 127.0.0.1 --port 8000
```

首次启动会在 `runtime/config/local_api_token` 生成本地 API token。
除 `/api/v1/health` 外，HTTP API 需要携带：

```powershell
Authorization: Bearer <local_api_token>
```
