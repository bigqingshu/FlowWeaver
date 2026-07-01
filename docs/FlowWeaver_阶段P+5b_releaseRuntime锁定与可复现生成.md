# FlowWeaver 阶段P+5b：release runtime 锁定与可复现生成

> 文档状态：阶段P+5b完成
> 当前执行点：只做发布 Python runtime 的锁定依赖生成，不替换默认开发路径，不进入安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 1. 背景

P+5a 已经提供独立发布 Python runtime 生成入口：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py
```

但 P+5a 仍使用 `pyproject.toml` 的版本范围安装运行依赖，例如：

```text
fastapi>=0.124.0
uvicorn>=0.38.0
```

这能得到干净 runtime，但正式发布时仍会受当天依赖解析结果影响，不足以作为可复现发布输入。

P+5b 的目标是把 release runtime 依赖安装收口到仓内 `uv.lock`：

- 只取根包 `flowweaver` 的运行依赖闭包
- 不引入 `dev` extra
- 不安装 editable 根包本身
- 通过固定版本和 wheel hash 安装第三方运行依赖
- 默认开发路径继续保持不变

## 2. 实现边界

新增显式锁定模式：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --locked
```

默认不传 `--locked` 时仍保持 P+5a 行为：

```text
pyproject.toml project.dependencies -> pip install <version ranges>
```

显式传入 `--locked` 后：

```text
uv.lock
-> flowweaver.dependencies
-> transitive runtime dependency closure
-> pinned requirements with wheel hashes
-> pip install --require-hashes --only-binary=:all:
```

生成的 requirements 文件是临时文件，位于 `.tmp` 输出目录旁边，安装完成后删除，不复制进最终 runtime。

## 3. 锁定依赖闭包

当前 `uv.lock` 中，运行依赖闭包为 24 个包：

```text
alembic
annotated-doc
annotated-types
anyio
certifi
click
colorama
fastapi
greenlet
h11
httpcore
httpx
idna
mako
markupsafe
msgpack
pydantic
pydantic-core
sqlalchemy
starlette
typing-extensions
typing-inspection
uvicorn
websockets
```

明确未进入闭包的 dev/test/build 包包括：

```text
pytest
pytest-asyncio
pytest-cov
pytest-timeout
ruff
mypy
coverage
```

## 4. 安装门禁

锁定模式下会拒绝：

- `uv.lock` 缺失
- `uv.lock` 缺少根项目包
- 运行闭包中存在缺失的依赖包
- 运行闭包中存在无 wheel hash 的包
- `dependency_source` 传入非法值

锁定模式下使用：

```text
--require-hashes
--only-binary=:all:
```

这意味着发布 runtime 不再依赖实时版本解析，也不会在发布路径中触发 sdist build。

## 5. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_release_python_runtime.py` | 新增 `--locked` / `--lock-file`，从 `uv.lock` 生成运行依赖闭包的 hash requirements |
| `tests/unit/test_create_release_python_runtime.py` | 覆盖锁定安装命令、dev extra 排除、缺失 lock、缺失 wheel hash 和 CLI 参数 |
| `docs/FlowWeaver_阶段P+5b_releaseRuntime锁定与可复现生成.md` | 固化 P+5b 边界和验收结果 |
| `README.md` | 更新 P+5b 阶段记录与下一步方向 |

## 6. 验收结果

单元和静态检查：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_release_python_runtime.py tests\unit\test_create_portable_layout.py tests\unit\test_portable_runtime_audit.py
.\python312\python.exe -m ruff check tools\create_release_python_runtime.py tools\create_portable_layout.py tools\portable_runtime_audit.py tests\unit\test_create_release_python_runtime.py tests\unit\test_create_portable_layout.py tests\unit\test_portable_runtime_audit.py
```

结果：

```text
pytest: 21 passed
ruff: All checks passed!
```

真实 locked runtime smoke：

```powershell
.\python312\python.exe tools\create_release_python_runtime.py --locked --output .tmp\P5bReleasePythonSmoke
.\python312\python.exe tools\create_portable_layout.py --output .tmp\P5bPortableRuntimeSmoke --python-runtime-dir .tmp\P5bReleasePythonSmoke --no-desktop-build
.\python312\python.exe tools\portable_runtime_audit.py --input .tmp\P5bPortableRuntimeSmoke
```

结果：

```text
runtime audit status: checked
errors: []
warnings: []
rejected_paths: []
excluded_paths: []
```

smoke 结束后已清理 `.tmp\P5bReleasePythonSmoke` 和 `.tmp\P5bPortableRuntimeSmoke`。

## 7. 当前仍不宣称

P+5b 仍不宣称：

- 不替换 `create_portable_layout.py` 的默认 repo-local `python312/` 行为
- 不让完整 `create_portable_archive --release-strict` 全链路通过
- 不解决 dirty git、Desktop executable、NuGet metadata 或第三方许可证 warning 等其他 strict 门禁
- 不移除 pip
- 不做安装器、代码签名、自动更新、后台服务、系统托盘或 self-contained Desktop

## 8. 下一步建议

下一小步建议进入 P+5c：release strict 前置复核。

建议先只分析和执行组合门禁，不直接扩大实现范围：

1. 使用 `--locked` runtime 生成完整 portable layout
2. 复核 Desktop build 输出是否满足 `Desktop/Avalonia_UI.exe`
3. 复核 NuGet metadata / third-party license warning 是否阻断 strict
4. 复核当前 dirty git 对 strict 的影响
5. 再尝试 `tools/create_portable_archive.py --release-strict`
