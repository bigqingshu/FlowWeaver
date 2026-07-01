# FlowWeaver 阶段P+1：发布包内完整用户手册与 docs 入口

> 文档状态：阶段P+1完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段P.0-P.7 和 `docs/FlowWeaver_阶段P后_边界分析.md`
> 适用范围：便携 layout、发布包内 docs 入口、完整用户手册进入 zip、manifest entries 验收
> 当前执行点：只做 P+1 小步，不进入真实 Desktop clean-room、第三方许可证增强、release strict、安装器、签名、自动更新或后台服务

## 1. 目标

P+1 的目标是补齐阶段P明确留下的用户侧发布包缺口：便携 zip 解压后，用户可以在发布包内直接找到完整用户手册，而不是只能依赖仓库文档。

本阶段完成：

- `tools/create_portable_layout.py` 生成便携目录时复制 `docs/FlowWeaver_便携版用户手册.md`
- 便携包内 `docs/README.txt` 增加完整手册入口
- layout 文件级 smoke 验证手册存在且 README 指向手册
- 归档单元测试验证 zip 包含 `docs/README.txt` 和完整手册
- clean-room backend-only smoke 验证解压后的完整手册存在，并进入 `release-manifest.json` entries

本阶段不做：

- 不新增真实 Desktop clean-room 自动化
- 不新增根目录 `README.md`
- 不新增 `docs/故障排查.md`
- 不新增 `docs/版本说明.md`
- 不修改 EngineHost、Desktop、token、runtime 或 workflow 行为
- 不进入安装器、代码签名、自动更新、后台服务或 self-contained Desktop

## 2. 修改清单

| 文件 | 修改 |
| --- | --- |
| `tools/create_portable_layout.py` | 复制完整便携版用户手册到发布包 `docs/`，并在短 README 中加入手册入口 |
| `tests/integration/test_n4_portable_layout_smoke.py` | 验证便携 layout 包含完整手册，README 指向手册 |
| `tests/unit/test_create_portable_archive.py` | 验证归档 zip 包含 `docs/README.txt` 和完整手册 |
| `tests/integration/test_p4_portable_archive_clean_room_smoke.py` | 验证 clean-room 解压后完整手册存在，并写入 manifest entries |
| `docs/FlowWeaver_阶段P+1_发布包内完整用户手册与docs入口.md` | 固化 P+1 完成状态和验收边界 |
| `README.md` | 更新 P+1 完成记录和下一步建议 |

## 3. 发布包结构

P+1 后最小 docs 结构为：

```text
FlowWeaverPortable/
  docs/
    README.txt
    FlowWeaver_便携版用户手册.md
```

`docs/README.txt` 保持短说明，只增加完整手册入口：

```text
docs/FlowWeaver_便携版用户手册.md
```

## 4. 验收结果

本次执行：

```powershell
.\python312\python.exe -m pytest -q tests\unit\test_create_portable_archive.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
.\python312\python.exe -m ruff check tools\create_portable_layout.py tests\unit\test_create_portable_archive.py tests\integration\test_n4_portable_layout_smoke.py tests\integration\test_p4_portable_archive_clean_room_smoke.py
git diff --check
```

结果：

```text
pytest: 9 passed
ruff: All checks passed!
git diff --check: passed
```

## 5. 阶段结论

P+1 可以视为完成发布包内完整用户手册与 docs 入口的最小闭环。

下一步建议进入 P+2：真实 Desktop clean-room smoke。P+2 应继续保持显式环境变量保护，不默认打开真实 Avalonia 窗口。
