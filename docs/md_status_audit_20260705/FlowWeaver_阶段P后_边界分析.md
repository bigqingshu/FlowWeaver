# FlowWeaver 阶段P后：边界分析

> 审核状态（2026-07-05）：已完成分析 / 候选方向未实现
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P 后边界分析已沉淀，P+1 到 P+5e 的发布包文档、Desktop clean-room、许可证、release strict 和 release runtime 主线随后已落地。
> 未实现：self-contained Desktop、代码签名、安装器、自动更新、后台服务/系统托盘未实现。
> 原因：这些被明确拆成独立 Distribution 或产品化方向，未并入 P/P+ 小步。

> 文档状态：阶段P后边界分析完成
> 优先级：低于 `00_第一阶段技术接口与验收规范.md`、`01_第一阶段执行方案.md`、阶段N/O完成记录和阶段P.0-P.7文档
> 适用范围：阶段P完成后的发布物、文档、clean-room、签名、安装器、自动更新和后台服务方向分流
> 当前执行点：只做边界分析和后续顺序建议，不修改发布脚本、不修改运行代码、不创建新发布能力

## 1. 背景

阶段P已经完成便携发布归档与用户手册收口的最小闭环：

- 发布归档脚本方案
- `python312` runtime audit
- zip、`release-manifest.json`、`licenses/` 和外部 `.sha256`
- 仓库外空格/中文路径 backend-only clean-room smoke
- 便携版用户手册正文
- 阶段P总体验收复核

P.7 明确后续不应直接混入安装器、自动更新、后台服务、代码签名或 self-contained Desktop。P 后边界分析的目标，是把这些候选方向拆清楚，避免把大范围分发能力塞进一个小的便携归档收口里。

## 2. 分流原则

P 后方向按四个维度判断：

| 维度 | 判断问题 | 结论倾向 |
| --- | --- | --- |
| 用户可见价值 | 是否能直接降低便携 zip 用户的启动、排查和反馈成本 | 优先 |
| 范围隔离 | 是否只影响 `.tmp/FlowWeaverPortable/`、zip 或文档 | 可作为 P 后小步 |
| 验收成本 | 是否可用现有 unit/integration smoke 验证 | 可优先 |
| 分发策略依赖 | 是否依赖证书、安装路径、更新策略、系统服务或权限模型 | 独立阶段 |

因此，P 后不应立刻进入“产品安装形态”。更稳的顺序是先把便携 zip 自身补齐，再决定是否进入更重的分发阶段。

## 3. 候选方向分级

| 候选方向 | 当前状态 | 范围判断 | 建议 |
| --- | --- | --- | --- |
| 发布包内携带完整用户手册 | P.7 明确未做，当前 zip 内只有短 `docs/README.txt` | 小范围，主要影响 `tools/create_portable_layout.py`、归档内容和测试 | 优先作为 P+1 |
| 发布包 docs 入口整理 | 当前 `README.txt` 可启动，但不能直接指向完整手册文件 | 小范围，可与完整手册同步处理 | 可并入 P+1 |
| 真实 Desktop clean-room smoke | O.10 已有真实 Desktop smoke，P.4 只有 backend-only clean-room | 中等范围，需要显式环境变量，可能打开窗口 | P+2 或独立 P 后小步 |
| 第三方许可证正文增强 | P.3 目前是 `third-party-licenses.json` summary-only | 中等范围，涉及包 metadata、许可证正文和法律表述 | P+3 先做方案，再实现 |
| manifest/release 严格模式 | 当前 manifest 记录 `git_dirty`，归档脚本没有强制 clean git | 中等范围，可能影响开发调试 | 后置，先分析是否需要 release-only 开关 |
| self-contained Desktop | P 阶段明确拒绝，当前 Desktop 为 `framework-dependent` | 大范围，涉及 .NET runtime、体积、clean-room 和用户手册 | 独立阶段，不并入 P 后小步 |
| 代码签名 | P 阶段明确不做 | 大范围，依赖证书、时间戳、CI/本机密钥管理 | 独立阶段 |
| 安装器 | P 阶段明确不做 | 大范围，涉及安装/卸载、快捷方式、权限、迁移、回滚 | 独立阶段 |
| 自动更新 | P 阶段明确不做 | 大范围，依赖版本协议、签名、兼容矩阵和回滚 | 独立阶段 |
| 后台服务/系统托盘 | P 阶段明确不做 | 大范围，改变 EngineHost 生命周期和所有权 | 独立阶段 |

## 4. 推荐后续顺序

### P+1：发布包内完整用户手册与 docs 入口

目标：

- 把 `docs/FlowWeaver_便携版用户手册.md` 复制进便携目录
- 更新便携包内 `docs/README.txt`，明确完整手册路径
- 归档后确保完整手册进入 zip entries
- 保持 Desktop 仍为 `framework-dependent`
- 不新增安装器、签名、自动更新或后台服务

建议验收：

- 文件级 smoke 验证 `.tmp/FlowWeaverPortable/docs/FlowWeaver_便携版用户手册.md`
- 归档单元测试验证 zip 内包含完整手册
- P.4 clean-room smoke 仍通过

### P+2：真实 Desktop clean-room smoke

目标：

- 在 P.4 的仓库外空格/中文路径基础上，增加真实 Desktop 最小进程级 smoke
- 继续使用显式环境变量保护，默认 CI 不打开窗口
- 验证 Desktop 可由 clean-room 便携目录启动
- 验证 EngineHost health、token 脱敏、日志生成和退出清理

建议边界：

- 不做窗口点击
- 不做截图
- 不做 UI 内 workflow 操作
- 不改变 `start_flowweaver.cmd` backend-only 默认语义

### P+3：第三方许可证增强方案

目标：

- 分析 `third-party-licenses.json` 是否需要从 summary-only 升级到带 license metadata
- 明确许可证正文来源、缺失策略和发布阻断策略
- 明确是否需要把 dev/test/build 包从发布 runtime 移除，而不是只 warning

建议先只做方案，不直接改 audit 或归档脚本。

### P+4：release 严格模式分析

目标：

- 分析是否需要 `--release-strict`
- 决定是否在正式归档时拒绝 dirty git、warning audit、缺失 Desktop build 或未运行 clean-room smoke
- 区分开发归档和正式分发归档

该方向会影响日常开发便利性，建议在 P+1/P+2 后再讨论。

## 5. 独立阶段候选

以下方向不建议作为 P 后小步直接实现。

| 独立阶段候选 | 需要先回答的问题 |
| --- | --- |
| self-contained Desktop | 是否接受包体增大、是否仍保留 framework-dependent、clean-room 如何双模式验收 |
| 代码签名 | 证书来源、私钥存放、时间戳服务、签名失败是否阻断发布 |
| 安装器 | 安装路径、用户数据路径、升级迁移、卸载保留数据、快捷方式、权限 |
| 自动更新 | 更新源、版本协议、签名校验、后端/桌面兼容矩阵、失败回滚 |
| 后台服务/系统托盘 | EngineHost 所有权、关机恢复、崩溃恢复、托盘关闭语义、权限和日志 |

这些方向都可能改变用户安装、启动、运行和升级模型，应先做独立 `Q.0` 或后续阶段边界清单。

## 6. 建议结论

最稳的下一步是 P+1：发布包内完整用户手册与 docs 入口。

理由：

- 它直接补齐 P.7 明确留下的用户侧缺口
- 范围只触及便携 layout、归档内容和测试
- 不改变 EngineHost、Desktop、token、runtime 或 workflow 行为
- 不提前进入安装器、签名、自动更新或后台服务

P+1 完成后，再进入 P+2 真实 Desktop clean-room smoke 会比较顺：先让用户拿到完整离线手册，再验证完整便携包在仓库外也能打开真实 Desktop。
