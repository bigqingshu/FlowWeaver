# FlowWeaver

模块化数据工作流运行平台。

## 当前阶段

当前已实现第一阶段的阶段 A 和阶段 B。

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

尚未实现 EngineHost、WorkflowRunProcess、NodeExecutor、SQLite 运行表数据面、共享表执行逻辑、权限审计服务和 UI。

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
.\.venv\Scripts\python.exe -m pytest
```

对指定 SQLite 元数据库执行迁移：

```powershell
.\.venv\Scripts\alembic.exe -c alembic.ini -x database_url=sqlite:///runtime/metadata/flowweaver.db upgrade head
```
