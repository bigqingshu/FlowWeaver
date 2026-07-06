# FlowWeaver 当前总结与后续大阶段方向分析

> 审核状态（2026-07-05）：部分已实现 / 后续大阶段未全部进入
> 审核范围：本复制件用于 MD 状态审核，原始 docs/ 文件未修改；顺序按原文件创建时间从旧到新。
> 已实现：P+ 发布物完善、NODE-SCHEMA/UI-SCHEMA、NODE-CONFIG、WORKFLOW-EDIT、WORKFLOW-UX、PREVIEW、DATA-PREVIEW 和部分 RUN-SAVE-UX 已落地。
> 未实现：BUSINESS-NODES、REAL-WORKFLOW、完整 RELIABILITY、DISTRIBUTION 安装器/签名/自动更新/后台服务和 PRODUCTIZATION 未实现。
> 原因：该文件是路线图，当前已推进近期高优先级小步，产品化和真实业务生态仍需后续独立阶段。

> 文档用途：用于统一记录 FlowWeaver 当前完成状态、程序定位、后续大阶段划分、各阶段对应的实现范围，以及推荐推进顺序。  
> 当前基线：`main` 最新阶段已经完成 UI-ACTION 总体验收，当前程序已具备本地桌面工作流系统的最小完整闭环。  
> 当前定位：技术 MVP 完成，可控内部试用阶段，处于 Internal Alpha 后期 / Beta 候选前阶段。

---

# 一、当前项目总结

FlowWeaver 已经不再是单纯的后端原型，也不只是一个界面演示项目。

当前已经具备：

- Python FastAPI EngineHost。
- Avalonia + .NET 10 桌面端。
- HTTP + WebSocket 通信。
- Workflow 创建、读取、校验和保存。
- Revision 与冲突保护。
- WorkflowRun 启动和取消。
- NodeRun 状态、进度、阶段和心跳。
- RuntimeEvent。
- AuditEvent。
- TableRef。
- SharedPublication。
- Token 鉴权。
- 本地运行数据目录。
- 便携运行目录。
- ZIP 发布归档。
- Manifest、SHA-256 和许可证。
- Backend clean-room smoke。
- UI 页面拆分和 Shell。
- ActionState、按钮状态、鉴权门控和旧请求覆盖保护。

当前主要用户路径已经形成：

```text
启动 EngineHost / Desktop
→ 建立连接
→ 创建或选择 Workflow
→ 加载 Definition
→ 编辑 JSON 草稿
→ Validate
→ 保存 Revision
→ 启动 WorkflowRun
→ 查看 NodeRun
→ 取消或等待完成
→ 查看 RuntimeEvent / AuditEvent
→ 查看 TableRef / SharedPublication
```

## 当前程序定位

当前可以定义为：

```text
技术 MVP 已完成
可控内部试用
Internal Alpha 后期
Beta 候选前阶段
```

当前已经适合：

- 开发者内部使用。
- 受控环境下验证工作流。
- 验证后端执行内核。
- 验证 Desktop 与 EngineHost 联调。
- 验证发布包流程。
- 开始接入真实业务节点。

当前尚不适合：

- 大范围普通用户分发。
- 无技术背景用户独立配置工作流。
- 长时间无人值守运行。
- 自动安装和升级。
- 正式商业签名发布。
- 多实例管理和自动接管。
- 复杂节点画布编辑。
- 完全依赖 GUI 创建所有工作流。

---

# 二、后续大阶段总览

后续建议拆分为以下大阶段。

| 大阶段 | 主要目标 | 对应实现大部分 |
| --- | --- | --- |
| P+ 发布物完善 | 让便携 ZIP 更接近可交付物 | 用户手册、docs入口、Desktop clean-room、严格发布检查 |
| UI-USABILITY | 提升界面可用性和视觉体验 | 页面布局、组件样式、状态提示、空状态、错误反馈、动画 |
| UI-VIEWMODEL | 收口 UI 内部结构 | MainWindowViewModel 拆分、页面 ViewModel、状态归属、生命周期 |
| NODE-SCHEMA / NODE-CATALOG | 建立节点定义和配置基础 | 节点元数据、配置 Schema、节点分类、节点目录 |
| WORKFLOW-EDITOR | 从 JSON 走向结构化编辑 | 表单编辑、连接编辑、Revision 操作、冲突体验 |
| BUSINESS-NODES | 建立真实业务节点生态 | 文件、Excel、SQLite、筛选、替换、去重、计算、共享表 |
| REAL-WORKFLOW | 用真实任务验证系统 | 真实流程、真实数据、异常场景、性能、恢复 |
| RELIABILITY | 提升长期运行可靠性 | 崩溃恢复、重启恢复、数据库迁移、备份、日志诊断 |
| DISTRIBUTION | 正式分发能力 | self-contained、安装器、签名、自动更新、后台服务 |
| PRODUCTIZATION | 产品级收口 | 权限体验、文档、反馈、版本策略、发布流程 |

这些阶段不需要完全串行。

推荐采用双线推进：

```text
Codex：
后端、接口、测试、发布、可靠性、最终复核

Gemini：
Avalonia 页面、XAML、组件、样式、动画、前端交互

所有阶段完成后：
由 Codex 做最终工程复核
```

---

# 三、推荐推进顺序

建议总体顺序：

```text
P+1 发布包文档补齐
+
UI-USABILITY 页面体验优化
↓
NODE-SCHEMA-0/1 最小配置 Schema
↓
真实业务节点首批落地
↓
真实工作流试运行
↓
WORKFLOW-EDITOR 结构化编辑
↓
可靠性增强
↓
正式分发
```

其中：

- P+1 可以快速完成。
- UI-USABILITY 可以和 P+ 并行。
- 真实业务节点应尽早开始，但应先固定最小配置 Schema，避免先落节点再反补协议。
- 安装器、自动更新、签名应延后。
- 自由节点画布不应过早开始。

---

# 四、P+ 发布物完善阶段

## 阶段目标

把当前“可以生成 ZIP”提升为“ZIP 本身更像一个完整交付物”。

## P+1：发布包内完整用户手册与 docs 入口

### 主要实现

- 将完整便携版用户手册复制进入 ZIP。
- 保留现有短 README 入口。
- README 中加入完整手册入口，且不引用仓库外路径。
- 复用或生成发布包内 `docs/` 目录。
- Manifest 包含文档文件。
- 测试文档路径、大小和 SHA-256。

### 建议发布包结构

```text
FlowWeaverPortable/
  docs/
    README.txt
    FlowWeaver_便携版用户手册.md
  EngineHost/
  Desktop/
  licenses/
  release-manifest.json
```

后续可选增强：

- 根目录 `README.md`。
- `docs/故障排查.md`。
- `docs/版本说明.md`。

### 验收重点

- ZIP 解压后可以直接找到手册。
- README 不引用仓库外路径。
- Manifest 包含 docs。
- 文档不包含真实 Token。
- 文档中的命令与发布包结构一致。

## P+2：真实 Desktop clean-room smoke

### 主要实现

- 在仓库外路径解压 ZIP。
- 路径包含空格和中文。
- 启动 Desktop 组合入口。
- 验证 EngineHost 拉起。
- 验证 UI 连接。
- 验证工作流列表。
- 验证 WebSocket。
- 验证关闭 Desktop 后 EngineHost 生命周期。
- 验证 `--keep-enginehost-on-desktop-exit`。

### 价值

当前 clean-room 主要覆盖 backend-only。

P+2 解决：

```text
发布包里的 Desktop 是否真的能在干净目录运行
```

## P+3：第三方许可证增强方案

### 主要实现

- 生成依赖清单。
- 补充 Python 包许可证。
- 补充 .NET NuGet 许可证。
- 将许可证清单写入归档。
- 校验许可证文件存在。
- 明确许可证正文来源、缺失策略和发布阻断策略。

## P+4：release strict 模式分析

### 主要实现

- 分析是否需要 `--release-strict`。
- 决定是否将部分 runtime audit warning 升级为阻断项。
- 检查开发包、测试包和旧 GUI 残留。
- 检查 runtime、token、db、log 泄露。
- 检查许可证完整性。
- 检查版本号和 manifest。
- 检查未提交构建产物。
- 区分开发归档和正式分发归档。

---

# 五、UI-USABILITY 阶段

## 阶段目标

在现有 Shell 和页面拆分基础上，提升用户体验。

当前 MainWindow 已经完成：

- Shell。
- 左侧导航。
- ConnectionStatusView。
- WorkflowPage。
- RunMonitorPage。
- DataPage。
- LogsAuditPage。
- SettingsPage。

因此本阶段不再重复拆 MainWindow。

## UI-USABILITY-0：页面体验审查

### 主要实现

对五个页面分别检查：

- 信息层级。
- 操作入口。
- 空状态。
- 加载状态。
- 错误状态。
- 禁用原因。
- 长文本。
- DPI。
- 窗口缩放。
- 列表密度。
- 技术详情展示。

### 输出

- 页面问题清单。
- 组件问题清单。
- 视觉规范。
- 页面改造优先级。
- 不改变业务逻辑的设计方案。

## UI-USABILITY-1：工作流页面

### 主要实现

- 工作流列表层级。
- 工作流选中状态。
- 创建入口。
- Definition 信息摘要。
- Revision 信息。
- 节点和连接列表。
- JSON 编辑器。
- Validate 状态。
- Save 状态。
- Run 操作区。
- Revision 冲突提示。
- Draft Dirty 状态。

### 目标

形成连续路径：

```text
选择
→ 编辑
→ 校验
→ 保存
→ 运行
```

## UI-USABILITY-2：运行监控页面

### 主要实现

- Run 列表。
- 当前 Run 摘要。
- NodeRun 列表。
- 状态色标。
- 进度。
- 当前阶段。
- 心跳。
- 取消确认。
- 错误详情。
- RuntimeEvent 入口。

### 目标

用户能够快速判断：

- 当前是否运行。
- 卡在哪个节点。
- 是否可以取消。
- 是否已经失败。
- 失败原因在哪里。

## UI-USABILITY-3：数据页面

### 主要实现

- TableRef 层级。
- 生命周期状态。
- capabilities。
- SharedPublication。
- Version。
- 来源 Run。
- 只读提示。
- 未实现能力说明。

## UI-USABILITY-4：日志与审计

### 主要实现

- 筛选区。
- RuntimeEvent 和 AuditEvent 区分。
- 事件级别。
- 技术详情。
- 复制信息。
- 空状态。
- 错误状态。
- 长列表性能。

## UI-USABILITY-5：设置页

### 主要实现

- BaseUrl。
- Token。
- Token 显示/隐藏。
- 检查连接。
- Event Stream。
- 语言。
- Runtime 路径。
- 日志路径。
- 启动模式说明。

## UI-USABILITY-6：统一样式与动画

### 主要实现

- Colors。
- Typography。
- Spacing。
- Button Styles。
- List Styles。
- Status Badge。
- Error Banner。
- Empty State。
- Loading State。
- Page Transition。

### 动画原则

推荐：

```text
120ms - 200ms
Opacity
轻微 Translate
颜色过渡
展开/折叠
```

避免：

- 大量缩放。
- 大面积阴影动画。
- 每条日志进入动画。
- 长列表复杂动画。

---

# 六、UI-VIEWMODEL 阶段

## 阶段目标

在页面和组件稳定后，整理 MainWindowViewModel。

当前不应在 Gemini 做视觉改版时同时进行。

## UI-VIEWMODEL-0：职责盘点

### 主要实现

分析当前 ViewModel 中：

- Connection。
- Workflow。
- Definition。
- Run。
- NodeRun。
- Data。
- Logs。
- Audit。
- Localization。
- ActionState。

## UI-VIEWMODEL-1：partial 文件拆分

### 建议结构

```text
MainWindowViewModel.cs
MainWindowViewModel.Connection.cs
MainWindowViewModel.Workflow.cs
MainWindowViewModel.Run.cs
MainWindowViewModel.Data.cs
MainWindowViewModel.Logs.cs
MainWindowViewModel.Localization.cs
MainWindowViewModel.ActionState.cs
```

### 优点

- 不改变 DataContext。
- 不改变页面绑定。
- 风险低。
- 容易逐步迁移。

## UI-VIEWMODEL-2：页面 ViewModel

页面结构完全稳定后，再考虑：

```text
ShellViewModel
ConnectionViewModel
WorkflowWorkspaceViewModel
RunMonitorViewModel
DataBrowserViewModel
LogsAuditViewModel
SettingsViewModel
```

## UI-VIEWMODEL-3：页面生命周期

### 需要解决

- 页面是否常驻。
- 页面切换是否重新加载。
- 选中项是否保留。
- 请求是否取消。
- WebSocket 状态如何共享。
- 全局错误如何传递。
- Connection 状态如何共享。

---

# 七、NODE-SCHEMA 与 NODE-CATALOG 阶段

## 阶段目标

为结构化节点配置和未来工作流编辑器建立基础。

## NODE-SCHEMA-0：节点定义事实冻结

### 主要实现

明确：

- node_type。
- display_name。
- description。
- category。
- input_ports。
- output_ports。
- retry_safe。
- ui_visibility。
- capabilities。
- permission declaration。
- configuration schema version。

## NODE-SCHEMA-1：配置 Schema

### 目标

每个节点提供可被 UI 读取的配置描述。

示例：

```json
{
  "type": "object",
  "properties": {
    "source_table": {
      "type": "string",
      "title": "来源表"
    },
    "target_field": {
      "type": "string",
      "title": "目标字段"
    }
  },
  "required": [
    "source_table",
    "target_field"
  ]
}
```

## NODE-CATALOG-0：只读节点目录

### 主要实现

- 节点分类。
- 节点搜索。
- 节点说明。
- 输入输出端口。
- 是否可重试。
- 权限摘要。
- 隐藏测试节点。

## NODE-CATALOG-1：节点选择入口

### 主要实现

- 新建工作流时选择节点。
- 添加节点。
- 只显示普通用户节点。
- 内部节点默认隐藏。
- 测试节点默认隐藏。

---

# 八、WORKFLOW-EDITOR 阶段

## 阶段目标

逐步减少用户直接编辑 JSON 的需要。

## WORKFLOW-EDITOR-0：结构化只读视图

### 主要实现

- 节点树。
- 连接关系。
- 节点配置摘要。
- Revision 对比。
- Definition Hash。
- 原始 JSON。

## WORKFLOW-EDITOR-1：节点属性表单

### 主要实现

- 基于 Schema 生成表单。
- 文本、数字、布尔、枚举。
- 字段选择。
- 表选择。
- 文件路径。
- 正则输入。
- 校验提示。

## WORKFLOW-EDITOR-2：连接关系编辑

### 主要实现

- 选择来源节点。
- 选择输出端口。
- 选择目标节点。
- 选择输入端口。
- 删除连接。
- 校验循环依赖。
- 校验端口类型。

## WORKFLOW-EDITOR-3：Revision 体验

### 主要实现

- Draft Dirty。
- Validate 结果。
- Save Revision。
- 冲突提示。
- Reload。
- Copy Draft。
- Diff。

## WORKFLOW-EDITOR-4：可视化画布评估

只有以下条件成熟后才考虑：

- 节点 Schema 稳定。
- 端口模型稳定。
- 连接编辑稳定。
- Revision 保存稳定。
- 列表式编辑器可用。

再评估：

- 拖拽节点。
- 连线。
- 缩放。
- MiniMap。
- 对齐。
- 分组。

---

# 九、BUSINESS-NODES 真实业务节点生态

## 阶段目标

让 FlowWeaver 能完成真实日常工作。

这是产品价值最高的阶段之一。

## 第一批建议节点

### 数据输入

- SQLite 读取。
- Excel 导入。
- CSV 导入。
- 剪贴板表格导入。
- 文件列表。
- 文件内容读取。

### 数据处理

- 字段筛选。
- 条件筛选。
- 字段映射。
- 批量替换。
- 正则提取。
- 分割。
- 合并列。
- 去重。
- 数值计算。
- 序列填充。
- 区域填充。
- 排序。
- 分组统计。

### 数据存储

- SQLite 写入。
- SQLite 追加。
- 中转表保存。
- SharedPublication 发布。
- SharedPublication 读取。

### 输出

- Excel 导出。
- CSV 导出。
- JSON 导出。
- 文件重命名。
- Word / Excel 插件输出接口。

## 节点实现要求

每个节点必须具备：

- 明确输入。
- 明确输出。
- 配置 Schema。
- 权限声明。
- 审计。
- 可重试语义。
- 失败策略。
- 测试。
- 示例 Workflow。

## 建议优先闭环

第一条真实闭环建议：

```text
Excel 导入
→ 字段筛选
→ 批量替换
→ 去重
→ 数值计算
→ Excel 导出
```

这条路径可以快速验证：

- 节点配置。
- 表传递。
- 错误提示。
- 运行监控。
- 性能。
- 输出结果。
- 用户操作流程。

---

# 十、REAL-WORKFLOW 真实任务试运行阶段

## 阶段目标

不再只看单元测试和 smoke，而是用真实任务验证完整系统。

## REAL-WORKFLOW-0：选择真实任务

建议选：

- Excel 清洗。
- BOM 处理。
- 文件批量改名。
- 数据库字段整理。
- Word / Excel 替换前的数据准备。
- 共享中转表处理。

## REAL-WORKFLOW-1：真实数据

### 测试维度

- 小数据。
- 中等数据。
- 大数据。
- 空数据。
- 错误数据。
- 中文字段。
- 长字段。
- 重复数据。
- 缺失字段。

## REAL-WORKFLOW-2：异常场景

### 测试

- 用户取消。
- 节点失败。
- EngineHost 重启。
- Desktop 关闭。
- WebSocket 断开。
- 数据库锁。
- 文件占用。
- 输出路径无权限。
- Revision 冲突。

## REAL-WORKFLOW-3：结果验证

### 需要确认

- 数据结果正确。
- 日志可定位。
- Audit可追踪。
- TableRef正确。
- SharedPublication正确。
- 失败不污染后续数据。
- 取消不会破坏已完成结果。
- 重跑行为明确。

---

# 十一、RELIABILITY 运行可靠性阶段

## 阶段目标

让系统能够长时间稳定运行，并支持故障后恢复。

## RELIABILITY-0：长时间运行

### 测试

- 8小时运行。
- 24小时运行。
- 多个Workflow连续执行。
- 大量RuntimeEvent。
- 大量NodeRun。
- WebSocket重连。
- 日志增长。

## RELIABILITY-1：崩溃与重启恢复

### 需要实现

- EngineHost异常退出检测。
- 未完成Run标记。
- ABORTED状态。
- 重启后的Run状态恢复。
- 临时TableRef清理。
- 未完成Publication处理。

## RELIABILITY-2：数据库迁移

### 需要实现

- Migration版本管理。
- 升级前备份。
- Migration失败回滚。
- 旧数据库兼容。
- Schema校验。

## RELIABILITY-3：备份恢复

### 主要实现

- runtime备份。
- metadata DB备份。
- 配置备份。
- 日志可选备份。
- 还原验证。
- 版本兼容说明。

## RELIABILITY-4：多实例策略

### 可选方向

- 直接拒绝第二实例。
- 连接现有实例。
- 明确接管。
- 只读查看。
- 独立runtime目录。

---

# 十二、DISTRIBUTION 正式分发阶段

## 阶段目标

从便携开发分发走向正式用户分发。

## DISTRIBUTION-0：self-contained Desktop评估

### 评估

- 包体积。
- .NET Runtime。
- 启动速度。
- 更新成本。
- 架构支持。
- 许可证。

## DISTRIBUTION-1：安装器

### 主要实现

- 安装目录。
- 用户数据目录。
- 快捷方式。
- 卸载。
- 升级保留runtime。
- 管理员权限。
- 文件关联。

## DISTRIBUTION-2：代码签名

### 主要实现

- EXE签名。
- Installer签名。
- 时间戳。
- 证书管理。
- CI签名。

## DISTRIBUTION-3：自动更新

### 主要实现

- 更新源。
- 版本检查。
- Manifest签名。
- 增量/全量更新。
- 回滚。
- runtime保护。
-更新失败恢复。

## DISTRIBUTION-4：后台服务与系统托盘

### 需要单独评估

- EngineHost后台运行。
- Windows服务。
- Tray。
- Desktop退出行为。
- 工作流继续运行。
- 服务权限。
- 日志和恢复。

这些能力会改变当前生命周期模型，不应顺手加入。

---

# 十三、PRODUCTIZATION 产品化收口阶段

## 阶段目标

形成可持续维护和正式交付的产品流程。

## 主要部分

- 正式版本号策略。
- Release Notes。
- 用户手册。
- 开发者文档。
- API文档。
- 节点开发文档。
- 插件开发文档。
- 错误码文档。
- 反馈问题模板。
- 崩溃报告。
- 遥测边界。
- 隐私说明。
- 发布审批。
- 兼容性矩阵。
- 支持周期。

---

# 十四、Codex 与 Gemini 分工

## Codex负责

- Python后端。
- API和DTO。
- 状态语义。
- 错误码。
- 数据库。
- Migration。
- 发布脚本。
- 自动化测试。
- 本地化资源。
- ViewModel核心逻辑。
- ActionState 语义、API 事实和旧请求丢弃边界。
- 最终代码复核。
- CI。
- 验收文档。
- 提交。

## Gemini负责

- Avalonia页面。
- XAML。
- 组件拆分。
- 布局。
- 样式。
- 动画。
- ActionState 的 XAML 展示和绑定落位。
- 页面状态显示。
- 空状态。
- 错误状态。
- 响应式和DPI。
- 前端实现说明。

## 统一复核

所有Gemini完成的前端阶段，均由Codex复核：

- Binding。
- Command。
- ItemsSource。
- SelectedItem。
- ActionState。
- API契约。
- 中文化。
- Token安全。
- 生命周期。
- Build。
- Test。
- 功能回归。

---

# 十五、当前推荐的近期路线

## 路线A：Codex

```text
P+1 发布包内完整用户手册与docs入口
→ P+2 Desktop clean-room smoke
→ NODE-SCHEMA-0/1 最小配置 Schema
→ 首批真实业务节点后端接口
→ 真实工作流测试
```

## 路线B：Gemini

```text
UI-USABILITY-0 页面体验审查
→ UI-USABILITY-1 工作流页
→ UI-USABILITY-2 运行监控页
→ UI-USABILITY-3 数据页
→ UI-USABILITY-4 日志审计页
→ UI-USABILITY-5 设置页
```

## 双方汇合

```text
首批真实业务节点
→ 真实任务Workflow
→ UI与后端联合验收
→ Reliability
```

---

# 十六、最终建议

当前不建议马上进入：

- 安装器。
- 自动更新。
- 后台服务。
- 自由节点画布。
- 大规模ViewModel重构。
- 全量插件生态。

当前最值得推进的三件事：

```text
1. P+1：把完整手册放入发布包
2. UI-USABILITY：继续优化现有五个页面
3. NODE-SCHEMA-0/1：先固定最小配置 Schema，再开始第一批 BUSINESS-NODES
```

下一项真正决定 FlowWeaver 是否有实际价值的，不再是继续补架构文档，而是：

```text
能否稳定完成一个真实工作任务
```

因此后续应逐步从：

```text
架构和验收是否完整
```

转向：

```text
真实任务是否可用
结果是否正确
失败是否可诊断
运行是否可靠
普通用户是否能操作
```
