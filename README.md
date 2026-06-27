# FlowWeaver

模块化数据工作流运行平台。

## 当前阶段

当前只实现第一阶段的阶段 A：工程骨架与协议。范围包括：

- `pyproject.toml` 项目配置
- Pydantic 公共协议模型
- 字符串枚举
- MessagePack 序列化与反序列化
- 统一错误模型
- 协议单元测试

尚未实现 EngineHost、RuntimeStore、WorkflowRunProcess、NodeExecutor、SQLite 运行表、共享表、审计和 UI。

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
