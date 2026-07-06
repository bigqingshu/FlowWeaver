# FlowWeaver 阶段P+5：干净可分发 Python runtime 边界分析

> 审核状态（2026-07-05）：已实现 / 明确排除项仍后置
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P/P+ 便携发布、runtime audit、归档、SHA-256、manifest、第三方许可证 metadata/正文复制、release strict、release runtime、Desktop publish 来源和 clean-room strict 复核已经落地。
> 未实现：安装器、代码签名、自动更新、后台服务、系统托盘和默认 self-contained Desktop 未实现。
> 原因：这些能力在 P/P+ 文档中被明确排除或拆为后续 Distribution 方向。

> 文档状态：阶段P+5分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7 和 P+1-P+4a 各阶段文档
> 适用范围：repo-local `python312/`、便携发布 `EngineHost/python312/`、runtime audit warning、`--release-strict` 前置输入洁净度
> 当前执行点：只做边界分析和事实清单，不修改 `python312/`、不清理包、不改变 audit 规则、不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 阶段目标

P+4a 已经提供显式 `--release-strict` 门禁，但当前真实发布输入是否能通过 strict，取决于 Python runtime 是否足够干净。

P+5 的目标是回答：

- 当前 repo-local `python312/` 是否能直接作为正式发布 runtime
- 哪些包会触发 runtime audit warning
- 哪些包虽然当前 audit 未阻断，但仍不应进入干净发布 runtime
- 下一步应如何生成干净 runtime，而不是破坏开发环境

本阶段只做分析，不直接删除任何包。

## 2. 当前事实

本机 repo-local Python 状态：

```text
python312/python.exe: Python 3.12.10
pip: 26.1.2
python312._pth: import site 已启用
```

`pyproject.toml` 直接运行依赖：

```text
alembic, fastapi, httpx, msgpack, pydantic, SQLAlchemy, uvicorn, websockets
```

`pyproject.toml` 直接开发依赖：

```text
mypy, pytest, pytest-asyncio, pytest-cov, pytest-timeout, ruff
```

当前 `python312/Lib/site-packages` 实装包数量：

```text
50
```

按当前环境 marker 计算的应用运行依赖闭包数量：

```text
24
```

运行依赖闭包：

```text
alembic, annotated-doc, annotated-types, anyio, certifi, click, colorama,
fastapi, greenlet, h11, httpcore, httpx, idna, Mako, MarkupSafe, msgpack,
pydantic, pydantic-core, SQLAlchemy, starlette, typing-extensions,
typing-inspection, uvicorn, websockets
```

## 3. runtime audit 结果

使用当前 `python312/` 生成临时便携 layout 后执行 `portable_runtime_audit`：

```text
status: warning
python_version: 3.12.10
pip_version: 26.1.2
errors: 0
warnings: 14
rejected_paths: 0
excluded_paths: 162
packages: 50
```

warning code 统计：

| code | 数量 | 说明 |
| --- | ---: | --- |
| `excluded_cache_paths_present` | 1 | 存在 `__pycache__` / `*.pyc` 等可排除缓存路径 |
| `dev_or_legacy_package_present` | 13 | 存在 dev/test/build 或旧 GUI 包 |

当前会触发 `dev_or_legacy_package_present` 的包：

| 包 | 当前版本 | 判断 |
| --- | --- | --- |
| coverage | 7.14.3 | 测试覆盖率工具，不应进入发布 runtime |
| hatchling | 1.30.1 | 构建后端，不应进入发布 runtime |
| mypy | 2.1.0 | 静态检查工具，不应进入发布 runtime |
| PySide6 | 6.11.1 | 旧 Python GUI 栈，当前 UI 已迁移 Avalonia，不应进入发布 runtime |
| PySide6_Addons | 6.11.1 | 旧 Python GUI 栈，不应进入发布 runtime |
| PySide6_Essentials | 6.11.1 | 旧 Python GUI 栈，不应进入发布 runtime |
| pytest | 9.1.1 | 测试工具，不应进入发布 runtime |
| pytest-asyncio | 1.4.0 | 测试工具，不应进入发布 runtime |
| pytest-cov | 7.1.0 | 测试工具，不应进入发布 runtime |
| pytest-qt | 4.5.0 | 旧 Qt 测试工具，不应进入发布 runtime |
| pytest-timeout | 2.4.0 | 测试工具，不应进入发布 runtime |
| ruff | 0.15.20 | 静态检查工具，不应进入发布 runtime |
| shiboken6 | 6.11.1 | PySide6 相关运行时，不应进入发布 runtime |

## 4. audit 未直接 warning 但仍需关注的包

按运行依赖闭包对比，以下包不在应用运行闭包中：

```text
ast-serialize, coverage, editables, flowweaver==0.2.2, hatchling, iniconfig,
librt, mypy, mypy-extensions, packaging, pathspec, pip, pluggy, pygments,
PySide6, PySide6_Addons, PySide6_Essentials, pytest, pytest-asyncio,
pytest-cov, pytest-qt, pytest-timeout, ruff, shiboken6, trove-classifiers, uv
```

其中重点关注：

| 包 | 风险 |
| --- | --- |
| `flowweaver==0.2.2` | 与当前 `pyproject.toml` 版本 `0.1.0` 不一致；便携运行应走 `EngineHost/src`，不应携带一个可能陈旧的 site-packages 安装副本 |
| `uv` | 开发/同步工具，不是 EngineHost 运行必需 |
| `pip` | 不是应用运行闭包；但当前 audit 通过 `python -m pip --version` 读取版本，第一版可作为 release tooling 依赖暂留 |
| `packaging` / `pathspec` / `trove-classifiers` / `editables` | 多数来自构建、开发或工具链依赖，应由干净 runtime 生成过程自然排除 |
| `pytest-*` / `pluggy` / `iniconfig` / `coverage` | 测试依赖，应排除 |
| `PySide6*` / `shiboken6` | 旧 Python GUI 栈，应排除 |

## 5. 结论

当前 repo-local `python312/` 不应直接宣称为“干净、可分发的正式发布 runtime”。

原因：

- `portable_runtime_audit` 当前返回 `warning`
- `--release-strict` 会因 `runtime_audit_warning` 拒绝
- 当前实装 50 个包，应用运行闭包约 24 个包
- 含测试、静态检查、构建后端、旧 PySide6 GUI 栈和工具链包
- `site-packages` 中存在与当前项目版本不一致的 `flowweaver==0.2.2`

但当前 runtime 没有 audit error：

- Python exe 存在
- `python312._pth` 已启用 `import site`
- Python LICENSE 存在
- 未发现 runtime/token/db/log 等 rejected path

因此它适合作为开发和 smoke runtime，不适合作为正式 strict runtime。

## 6. P+5a 建议方向

最稳方向是：**不要在原地清理 repo-local `python312/`，而是生成独立发布 runtime**。

建议 P+5a 先做方案或最小实现之一：

### 推荐方案：生成发布 runtime

输入：

- 当前 repo-local `python312/` 作为 embedded Python 基础模板，或重新解压官方 embedded Python
- `pyproject.toml` / `uv.lock`
- 运行依赖组，不包含 `dev`

输出：

```text
.tmp/FlowWeaverReleasePython312/
```

要求：

- 只安装应用运行依赖
- 不安装 `.[dev]`
- 不安装 PySide6 / pytest / ruff / mypy / hatchling 等发布无关包
- 不安装陈旧 `flowweaver` wheel；运行代码继续来自 `EngineHost/src`
- 清理 `__pycache__` 和 `*.pyc`
- 保留 Python LICENSE
- 暂时保留 pip，直到 audit 不再依赖 pip 读取版本

### 不推荐方案：原地卸载

不建议直接对 `python312/` 执行卸载清理。原因：

- 它同时承担本地开发、测试和 smoke 运行
- 容易误删开发依赖，影响后续测试
- 卸载可能留下孤儿文件或 dist-info 残留
- 很难稳定复现 clean-room 发布输入

### 后置可选：audit 去 pip 依赖

如果未来希望发布 runtime 不携带 pip，应先调整 `portable_runtime_audit`：

- Python 版本继续通过 `python.exe --version`
- pip 版本改为可选信息，不再导致 strict warning
- 第三方包 metadata 直接扫描 `dist-info`，不依赖 pip

## 7. 下一步建议

下一小步建议进入 P+5a：干净 runtime 生成方案。

P+5a 先不要直接替换 `create_portable_layout.py` 默认行为。更稳的落点是：

- 新增或设计一个独立 release runtime 生成入口
- 让便携 layout 后续可以选择使用该 release runtime
- 增加最小 audit 验收，目标是 runtime audit 从 `warning` 变为 `checked`
- 然后再进入 `create archive --release-strict` 的真实输入验收
