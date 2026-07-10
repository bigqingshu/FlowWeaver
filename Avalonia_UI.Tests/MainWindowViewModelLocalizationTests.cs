using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class MainWindowViewModelLocalizationTests
{
    [TestMethod]
    public async Task LoopStartMaxLoopCountTitleClarifiesPreviewOnly()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        Assert.AreEqual(
            "最大循环次数（仅预览）",
            localizationService.GetString("node_config.LoopStartNode.max_loop_count.title"));

        await localizationService.SetLanguageAsync("en-US");
        Assert.AreEqual(
            "Max Loop Count (Preview Only)",
            localizationService.GetString("node_config.LoopStartNode.max_loop_count.title"));
    }

    [TestMethod]
    public async Task TableBindingLabelsKeepLocalizedTextAndStableEnglishValues()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        Assert.AreEqual(
            "新建运行内 SQL 表",
            localizationService.GetString(
                "workflow.table_bindings.target.new_runtime_sql"));

        await localizationService.SetLanguageAsync("en-US");
        Assert.AreEqual(
            "New runtime SQL table",
            localizationService.GetString(
                "workflow.table_bindings.target.new_runtime_sql"));

        var option = new NodeTableOutputTargetKindOptionViewModel(
            NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind,
            "localized");
        Assert.AreEqual("new_runtime_sql", option.Value);
    }

    [TestMethod]
    public async Task DataPreviewDirectoryTypesAndPersistenceAreLocalized()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        Assert.AreEqual(
            "运行内 SQL 表",
            localizationService.GetString(
                "data_preview.table_type.runtime_sql_table"));
        Assert.AreEqual(
            "临时内存表",
            localizationService.GetString(
                "data_preview.persistence.memory_only"));

        await localizationService.SetLanguageAsync("en-US");
        Assert.AreEqual(
            "External SQL reference",
            localizationService.GetString(
                "data_preview.table_type.external_sql_table"));
        Assert.AreEqual(
            "Run-persistent table",
            localizationService.GetString(
                "data_preview.persistence.workflow_run_sql"));
    }

    [TestMethod]
    public async Task LoadUiSettingsAppliesPersistedLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore
        {
            SettingsToLoad = PersistedUiSettings.FromLanguageCode("zh-Hans"),
        };
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.LoadUiSettingsAsync();

        Assert.AreEqual("zh-Hans", viewModel.CurrentLanguageCode);
        Assert.AreEqual("EngineHost 连接", viewModel.AppSubtitleText);
        Assert.AreEqual("服务地址", viewModel.ConnectionBaseUrlText);
        Assert.AreEqual("语言: 简体中文", viewModel.LanguageMenuHeaderText);
        Assert.AreEqual("执行", viewModel.ExecutionTabText);
        Assert.AreEqual("刷新", viewModel.RefreshText);
        Assert.AreEqual("关闭", viewModel.CloseText);
        Assert.AreEqual(
            "运行和预览会使用当前已保存的工作流版本。",
            viewModel.WorkflowRunGuardText);
        Assert.AreEqual("工作流定义", viewModel.WorkflowDefinitionSectionText);
        Assert.AreEqual("循环区域", viewModel.WorkflowLoopRegions.SectionText);
        Assert.AreEqual("输入表", viewModel.WorkflowNodeTableBindings.InputSectionText);
        Assert.AreEqual("输出目标", viewModel.WorkflowNodeTableBindings.OutputSectionText);
        Assert.AreEqual("应用表绑定", viewModel.WorkflowNodeTableBindings.ApplyText);
        Assert.AreEqual("真实最大轮数", viewModel.WorkflowLoopRegions.MaxIterationsText);
        Assert.AreEqual("启用真实循环", viewModel.WorkflowLoopRegions.EnabledText);
        Assert.AreEqual("循环监视", viewModel.RunLoopMonitor.SectionText);
        Assert.AreEqual("运行概览", viewModel.RunLoopMonitor.OverviewText);
        Assert.AreEqual("刷新详情", viewModel.DetailsText);
        Assert.AreEqual("工作流节点", viewModel.WorkflowNodesSectionText);
        Assert.AreEqual("应用名称", viewModel.ApplyNodeDisplayNameText);
        Assert.AreEqual("结构化编辑", viewModel.StructuredEditSectionText);
        Assert.AreEqual("新增节点", viewModel.AddNodeText);
        Assert.AreEqual("复制节点", viewModel.CopyNodeText);
        Assert.AreEqual("删除节点", viewModel.DeleteNodeText);
        Assert.AreEqual("删除已选", viewModel.DeleteSelectedNodesText);
        Assert.AreEqual("列表上移", viewModel.MoveNodeUpText);
        Assert.AreEqual("列表下移", viewModel.MoveNodeDownText);
        Assert.AreEqual("已选择 0 个节点", viewModel.WorkflowDefinitionBatchSelectedNodeCountText);
        Assert.AreEqual("节点操作", viewModel.NodeActionsSectionText);
        Assert.AreEqual(
            "上移/下移仅在线性链路的中间相邻节点交换时重排连接；其他情况只调整草稿节点列表顺序。",
            viewModel.NodeMoveSemanticsText);
        Assert.AreEqual(
            "加载工作流定义后可检查线性连接支持状态。",
            viewModel.WorkflowLinearChainStatusText);
        Assert.AreEqual("数据预览", viewModel.DataPreviewSectionText);
        Assert.AreEqual("选择一个工作流节点以查看预览。", viewModel.DataPreviewEmptyText);
        Assert.AreEqual(
            "选择工作流节点后，可预览该节点及其上游节点的输出表前 50 行。",
            viewModel.DataPreviewPendingText);
        Assert.AreEqual("刷新预览", viewModel.DataPreviewRefreshText);
        Assert.AreEqual("处理状态", viewModel.DataPreviewStateSelectorText);
        Assert.AreEqual("数据表", viewModel.DataPreviewTableSelectorText);
        Assert.AreEqual("载入选中表", viewModel.DataPreviewLoadSelectedTableText);
        Assert.AreEqual("预览选中节点", viewModel.PreviewSelectedNodeText);
        Assert.AreEqual("尚未加载数据预览。", viewModel.DataPreviewSourceText);
        Assert.AreEqual("节点实例 ID", viewModel.NodeInstanceIdText);
        Assert.AreEqual("配置 JSON", viewModel.ConfigJsonText);
        Assert.AreEqual("显示连接", viewModel.ShowConnectionsText);
        Assert.AreEqual("新增连接", viewModel.AddConnectionText);
        Assert.AreEqual("删除连接", viewModel.DeleteConnectionText);
        Assert.AreEqual("源节点", viewModel.SourceNodeText);
        Assert.AreEqual("目标端口", viewModel.TargetPortText);
        Assert.AreEqual("显示草稿 JSON", viewModel.ShowAdvancedDraftJsonText);
        Assert.AreEqual("工作流运行", viewModel.WorkflowRunFilterText);
        Assert.AreEqual("共享名称", viewModel.ShareNameWatermarkText);
        Assert.AreEqual("未连接。", viewModel.StatusMessage);
        Assert.AreEqual("尚未加载工作流。", viewModel.WorkflowMessage);
        Assert.AreEqual("选择一个工作流以加载定义。", viewModel.WorkflowDefinitionMessage);
        Assert.AreEqual("加载定义后编辑草稿 JSON。", viewModel.WorkflowDefinitionValidationMessage);
        Assert.AreEqual("选择运行和工作流节点后刷新数据预览。", viewModel.DataPreviewMessage);
        Assert.AreEqual("尚未加载运行记录。", viewModel.RunMessage);
        Assert.AreEqual(1, uiSettingsStore.LoadCount);
        Assert.AreEqual(0, uiSettingsStore.SaveCount);
    }

    [TestMethod]
    public async Task ChangeLanguageCommandSavesUiSettings()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        Assert.AreEqual("zh-Hans", viewModel.CurrentLanguageCode);
        Assert.AreEqual("设置", viewModel.SettingsMenuText);
        Assert.AreEqual("数据预览", viewModel.DataPreviewTabText);
        Assert.AreEqual("服务地址", viewModel.ConnectionBaseUrlText);
        Assert.AreEqual("数据", viewModel.DataTabText);
        Assert.AreEqual("关闭", viewModel.CloseText);
        Assert.AreEqual(
            "运行和预览会使用当前已保存的工作流版本。",
            viewModel.WorkflowRunGuardText);
        Assert.AreEqual("节点类型", viewModel.NodeTypeText);
        Assert.AreEqual("循环区域", viewModel.WorkflowLoopRegions.SectionText);
        Assert.AreEqual("循环监视", viewModel.RunLoopMonitor.SectionText);
        Assert.AreEqual("刷新详情", viewModel.DetailsText);
        Assert.AreEqual("工作流节点", viewModel.WorkflowNodesSectionText);
        Assert.AreEqual("应用名称", viewModel.ApplyNodeDisplayNameText);
        Assert.AreEqual("复制节点", viewModel.CopyNodeText);
        Assert.AreEqual("删除已选", viewModel.DeleteSelectedNodesText);
        Assert.AreEqual("列表上移", viewModel.MoveNodeUpText);
        Assert.AreEqual("列表下移", viewModel.MoveNodeDownText);
        Assert.AreEqual("已选择 0 个节点", viewModel.WorkflowDefinitionBatchSelectedNodeCountText);
        Assert.AreEqual("节点版本", viewModel.NodeVersionText);
        Assert.AreEqual("节点操作", viewModel.NodeActionsSectionText);
        Assert.AreEqual(
            "上移/下移仅在线性链路的中间相邻节点交换时重排连接；其他情况只调整草稿节点列表顺序。",
            viewModel.NodeMoveSemanticsText);
        Assert.AreEqual(
            "加载工作流定义后可检查线性连接支持状态。",
            viewModel.WorkflowLinearChainStatusText);
        Assert.AreEqual("数据预览", viewModel.DataPreviewSectionText);
        Assert.AreEqual("选择一个工作流节点以查看预览。", viewModel.DataPreviewEmptyText);
        Assert.AreEqual("刷新预览", viewModel.DataPreviewRefreshText);
        Assert.AreEqual("处理状态", viewModel.DataPreviewStateSelectorText);
        Assert.AreEqual("数据表", viewModel.DataPreviewTableSelectorText);
        Assert.AreEqual("载入选中表", viewModel.DataPreviewLoadSelectedTableText);
        Assert.AreEqual("预览选中节点", viewModel.PreviewSelectedNodeText);
        Assert.AreEqual("尚未加载数据预览。", viewModel.DataPreviewSourceText);
        Assert.AreEqual("还原", viewModel.RestoreText);
        Assert.AreEqual("显示名称", viewModel.DisplayNameText);
        Assert.AreEqual("连接 ID", viewModel.ConnectionIdText);
        Assert.AreEqual("源端口", viewModel.SourcePortText);
        Assert.AreEqual("目标节点", viewModel.TargetNodeText);
        Assert.AreEqual("显示连接", viewModel.ShowConnectionsText);
        viewModel.IsWorkflowConnectionsAdvancedVisible = true;
        Assert.AreEqual("收起连接", viewModel.ShowConnectionsText);
        Assert.AreEqual("显示草稿 JSON", viewModel.ShowAdvancedDraftJsonText);
        viewModel.IsWorkflowDraftJsonAdvancedVisible = true;
        Assert.AreEqual("收起草稿 JSON", viewModel.ShowAdvancedDraftJsonText);
        Assert.AreEqual("版本", viewModel.VersionsText);
        Assert.AreEqual(1, uiSettingsStore.SaveCount);
        Assert.AreEqual("zh-Hans", uiSettingsStore.SavedSettings?.LanguageCode);
    }

    [TestMethod]
    public async Task RuntimeOptionsOptionDisplayUsesChineseTextAndEnglishValues()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        CollectionAssert.AreEqual(
            new[] { "normal", "background_fast", "diagnostic", "custom" },
            viewModel.RuntimeOptionsProfileOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "常规", "后台快速", "诊断", "自定义" },
            viewModel.RuntimeOptionsProfileOptions
                .Select(option => option.DisplayText)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { "DEBUG", "INFO", "WARN", "ERROR" },
            viewModel.RuntimeOptionsLogLevelOptions.Select(option => option.Value).ToArray());
        CollectionAssert.AreEqual(
            new[] { "调试", "信息", "警告", "错误" },
            viewModel.RuntimeOptionsLogLevelOptions
                .Select(option => option.DisplayText)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { "none", "basic", "progress", "verbose" },
            viewModel.RuntimeOptionsEventLevelOptions
                .Select(option => option.Value)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { "无事件", "基础事件", "进度事件", "详细事件" },
            viewModel.RuntimeOptionsEventLevelOptions
                .Select(option => option.DisplayText)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { "none", "partial", "full" },
            viewModel.RuntimeOptionsMaskPolicyOptions
                .Select(option => option.Value)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { "不脱敏", "部分脱敏", "完全脱敏" },
            viewModel.RuntimeOptionsMaskPolicyOptions
                .Select(option => option.DisplayText)
                .ToArray());

        viewModel.RuntimeOptionsProfileDraft = "custom";
        viewModel.RuntimeOptionsEventLevelDraft = "basic";
        viewModel.RuntimeOptionsProgressEnabledDraft = false;
        viewModel.RuntimeOptionsNodeOverrideCount = 2;

        Assert.AreEqual(
            "预设 自定义，事件 基础事件，进度 关闭，节点覆盖 2 个",
            viewModel.RuntimeOptionsSummaryText);
    }

    [TestMethod]
    public void ShellNavigationItemsMirrorBuiltinShellPages()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        CollectionAssert.AreEqual(
            BuiltinShellPages.All.Select(page => page.Key).ToArray(),
            viewModel.ShellNavigationItems.Select(item => item.Key).ToArray());
        CollectionAssert.AreEqual(
            BuiltinShellPages.All.Select(page => page.ContentKey).ToArray(),
            viewModel.ShellNavigationItems.Select(item => item.ContentKey).ToArray());
        CollectionAssert.AreEqual(
            BuiltinShellPages.All.Select(page => page.SortOrder).ToArray(),
            viewModel.ShellNavigationItems.Select(item => item.SortOrder).ToArray());
        CollectionAssert.AreEqual(
            BuiltinShellPages.All.Select(page => page.HeaderPropertyName).ToArray(),
            viewModel.ShellNavigationItems.Select(item => item.HeaderPropertyName).ToArray());
        CollectionAssert.AreEqual(
            BuiltinShellPages.All.Select(page => page.ViewTypeName).ToArray(),
            viewModel.ShellNavigationItems.Select(item => item.ViewTypeName).ToArray());
        CollectionAssert.AreEqual(
            new[] { "Workflows", "Data preview", "Runs", "Data", "Logs", "Settings" },
            viewModel.ShellNavigationItems.Select(item => item.HeaderText).ToArray());
        CollectionAssert.AreEqual(
            new[]
            {
                viewModel.WorkflowsNavigationItem.HeaderText,
                viewModel.DataPreviewNavigationItem.HeaderText,
                viewModel.RunsNavigationItem.HeaderText,
                viewModel.DataNavigationItem.HeaderText,
                viewModel.LogsNavigationItem.HeaderText,
                viewModel.SettingsNavigationItem.HeaderText,
            },
            viewModel.ShellNavigationItems.Select(item => item.HeaderText).ToArray());

        foreach (var item in viewModel.ShellNavigationItems)
        {
            Assert.IsTrue(item.IsVisible, $"{item.Key} should be visible by default.");
            Assert.IsTrue(item.IsEnabled, $"{item.Key} should be enabled by default.");
        }
    }

    [TestMethod]
    public void ShellSelectionDefaultsToWorkflowsPage()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        Assert.AreEqual(ShellPageKey.Workflows, viewModel.SelectedShellPageKey);
        Assert.AreEqual(
            ShellPageKey.Workflows,
            viewModel.SelectedShellNavigationItem.Key);
        Assert.AreEqual(
            ShellPageContentKey.Workflows,
            viewModel.SelectedShellPageContentKey);
        Assert.AreEqual(0, viewModel.SelectedShellPageIndex);
    }

    [TestMethod]
    public async Task ShellSelectionUsesStableKeyWhenNavigationItemsRefresh()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());
        viewModel.SelectedShellPageKey = ShellPageKey.Logs;

        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellNavigationItem.Key);
        Assert.AreEqual(ShellPageContentKey.Logs, viewModel.SelectedShellPageContentKey);
        Assert.AreEqual(GetShellPageIndex(viewModel, ShellPageKey.Logs), viewModel.SelectedShellPageIndex);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellPageKey);
        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellNavigationItem.Key);
        Assert.AreEqual(ShellPageContentKey.Logs, viewModel.SelectedShellPageContentKey);
        Assert.AreEqual(GetShellPageIndex(viewModel, ShellPageKey.Logs), viewModel.SelectedShellPageIndex);
        Assert.AreEqual("日志", viewModel.SelectedShellNavigationItem.HeaderText);
    }

    [TestMethod]
    public void ShellSelectionIndexUpdatesSelectedPageKey()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());
        var logsIndex = GetShellPageIndex(viewModel, ShellPageKey.Logs);

        viewModel.SelectedShellPageIndex = logsIndex;

        Assert.AreEqual(logsIndex, viewModel.SelectedShellPageIndex);
        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellPageKey);
        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellNavigationItem.Key);
        Assert.AreEqual(ShellPageContentKey.Logs, viewModel.SelectedShellPageContentKey);
    }

    [TestMethod]
    public void ShellSelectionKeyUpdatesSelectedPageIndex()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());
        var settingsIndex = GetShellPageIndex(viewModel, ShellPageKey.Settings);

        viewModel.SelectedShellPageKey = ShellPageKey.Settings;

        Assert.AreEqual(settingsIndex, viewModel.SelectedShellPageIndex);
        Assert.AreEqual(ShellPageKey.Settings, viewModel.SelectedShellNavigationItem.Key);
        Assert.AreEqual(ShellPageContentKey.Settings, viewModel.SelectedShellPageContentKey);
    }

    [TestMethod]
    public void ShellSelectionKeyChangeRaisesIndexAndDerivedNotifications()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());
        var changedProperties = new List<string?>();
        viewModel.PropertyChanged += (_, args) => changedProperties.Add(args.PropertyName);

        viewModel.SelectedShellPageKey = ShellPageKey.Data;

        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageKey));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageIndex));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellNavigationItem));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageContentKey));
    }

    [TestMethod]
    public void ShellSelectionIndexChangeRaisesKeyAndDerivedNotifications()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());
        var changedProperties = new List<string?>();
        viewModel.PropertyChanged += (_, args) => changedProperties.Add(args.PropertyName);

        viewModel.SelectedShellPageIndex = GetShellPageIndex(viewModel, ShellPageKey.Runs);

        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageIndex));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageKey));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellNavigationItem));
        CollectionAssert.Contains(changedProperties, nameof(viewModel.SelectedShellPageContentKey));
    }

    [TestMethod]
    public void ShellSelectionRejectsUnknownPageKey()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        try
        {
            viewModel.SelectedShellPageKey = (ShellPageKey)999;
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException)
        {
        }

        Assert.AreEqual(ShellPageKey.Workflows, viewModel.SelectedShellPageKey);
    }

    [TestMethod]
    public void ShellSelectionRejectsUnknownPageIndex()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        try
        {
            viewModel.SelectedShellPageIndex = viewModel.ShellNavigationItems.Count;
            Assert.Fail("Expected an InvalidOperationException.");
        }
        catch (InvalidOperationException)
        {
        }

        Assert.AreEqual(0, viewModel.SelectedShellPageIndex);
        Assert.AreEqual(ShellPageKey.Workflows, viewModel.SelectedShellPageKey);
        Assert.AreEqual(ShellPageContentKey.Workflows, viewModel.SelectedShellPageContentKey);
    }

    [TestMethod]
    public async Task ChangeLanguageRefreshesShellNavigationItemHeaders()
    {
        var viewModel = CreateViewModel(new FakeUiSettingsStore());

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        CollectionAssert.AreEqual(
            new[] { "工作流", "数据预览", "运行", "数据", "日志", "设置" },
            viewModel.ShellNavigationItems.Select(item => item.HeaderText).ToArray());
        Assert.AreEqual("工作流", viewModel.WorkflowsNavigationItem.HeaderText);
        Assert.AreEqual("数据预览", viewModel.DataPreviewNavigationItem.HeaderText);
        Assert.AreEqual("运行", viewModel.RunsNavigationItem.HeaderText);
        Assert.AreEqual("数据", viewModel.DataNavigationItem.HeaderText);
        Assert.AreEqual("日志", viewModel.LogsNavigationItem.HeaderText);
        Assert.AreEqual("设置", viewModel.SettingsNavigationItem.HeaderText);
    }

    [TestMethod]
    public async Task LoadUiSettingsAppliesPersistedTheme()
    {
        var uiSettingsStore = new FakeUiSettingsStore
        {
            SettingsToLoad = PersistedUiSettings.FromSettings("zh-Hans", "Dark"),
        };
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.LoadUiSettingsAsync();

        Assert.AreEqual("Dark", viewModel.CurrentThemeVariant);
        Assert.AreEqual("主题: 暗色", viewModel.ThemeMenuHeaderText);
        Assert.AreEqual(1, uiSettingsStore.LoadCount);
        Assert.AreEqual(0, uiSettingsStore.SaveCount);
    }

    [TestMethod]
    public async Task ChangeThemeCommandSavesUiSettings()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.ChangeThemeCommand.ExecuteAsync("Dark");

        Assert.AreEqual("Dark", viewModel.CurrentThemeVariant);
        Assert.AreEqual("Theme: Dark", viewModel.ThemeMenuHeaderText);
        Assert.AreEqual(1, uiSettingsStore.SaveCount);
        Assert.AreEqual("en-US", uiSettingsStore.SavedSettings?.LanguageCode);
        Assert.AreEqual("Dark", uiSettingsStore.SavedSettings?.ThemeVariant);
    }

    [TestMethod]
    public async Task ChangeThemeCommandFallsBackForUnsupportedTheme()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.ChangeThemeCommand.ExecuteAsync("midnight");

        Assert.AreEqual("System", viewModel.CurrentThemeVariant);
        Assert.AreEqual("Theme: System", viewModel.ThemeMenuHeaderText);
        Assert.AreEqual("System", uiSettingsStore.SavedSettings?.ThemeVariant);
    }

    [TestMethod]
    public async Task DynamicMessagesUseCurrentLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    new()
                    {
                        WorkflowId = "wf-1",
                        Name = "Daily Load",
                        RevisionId = "rev-wf-1",
                        Version = 2,
                        DefinitionHash = "hash-wf-1",
                        Definition = JsonDocument.Parse("""{"nodes":[]}""").RootElement.Clone(),
                        Status = "ACTIVE",
                        CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
                        UpdatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
                    },
                }),
        };
        var viewModel = CreateViewModel(uiSettingsStore, apiClient);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");
        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual("已加载 1 个工作流。", viewModel.WorkflowMessage);
        Assert.AreEqual("已选择 Daily Load。刷新运行记录以加载匹配项。", viewModel.RunMessage);
        Assert.AreEqual("已选择 Daily Load。加载定义以查看详情。", viewModel.WorkflowDefinitionMessage);
        Assert.AreEqual("编辑草稿 JSON 前请先加载定义。", viewModel.WorkflowDefinitionValidationMessage);
        Assert.IsFalse(viewModel.HasWorkflowError);

        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("已为 Daily Load 加载 0 条运行记录。", viewModel.RunMessage);
    }

    [TestMethod]
    public async Task ListItemDisplayTextUsesCurrentLanguage()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0"
                },
                {
                  "node_instance_id": "disabled-node",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "enabled": false
                }
              ],
              "connections": [
                {
                  "connection_id": "c1",
                  "source_node_id": "source",
                  "source_port": "out",
                  "target_node_id": "disabled-node",
                  "target_port": "in"
                }
              ]
            }
            """;
        var uiSettingsStore = new FakeUiSettingsStore();
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 2, definitionJson) }),
            WorkflowDetailResponse =
                ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                    Workflow("wf-1", "Daily Load", 2, definitionJson)),
            WorkflowRevisionsResponse =
                ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                    new List<WorkflowRevisionDto>()),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto> { NodeRun("node-run-1", "run-1", "source") }),
            NodeDefinitionsResponse = ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    new()
                    {
                        NodeType = "GenerateTestTableNode",
                        NodeVersion = "1.0",
                        DisplayName = "Generate Test Table",
                        InputPorts = [],
                        OutputPorts = [new NodePortDefinitionDto { Name = "out" }],
                        ExecutionMode = "PROCESS_POOL",
                        DefaultTimeoutSeconds = 60,
                        RetrySafe = false,
                        UiVisibility = "visible",
                        ConfigSchemaVersion = "1.0",
                        ConfigSchema = JsonDocument.Parse(
                            """{"type":"object","properties":{"rows":{"type":"integer"}}}""")
                            .RootElement
                            .Clone(),
                    },
                }),
            SharedPublicationsResponse =
                ApiResponseEnvelope<List<SharedPublicationDto>>.Success(
                    new List<SharedPublicationDto> { SharedPublication("pub-1", "daily_report") }),
        };
        var viewModel = CreateViewModel(uiSettingsStore, apiClient);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");
        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);
        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshSharedPublicationsCommand.ExecuteAsync(null);

        Assert.AreEqual("2 个节点", viewModel.WorkflowDefinitionDetail?.NodeCountText);
        Assert.AreEqual("1 条连接", viewModel.WorkflowDefinitionDetail?.ConnectionCountText);
        Assert.AreEqual(
            "JSON 回退编辑器",
            viewModel.WorkflowDefinitionDetail?.Nodes[0].NodeEditorStatusText);
        Assert.AreEqual(
            "source / 生成测试表",
            viewModel.WorkflowDefinitionDetail?.Nodes[0].NodeSummaryText);
        Assert.AreEqual("已禁用", viewModel.WorkflowDefinitionDetail?.Nodes[1].EnabledText);
        Assert.AreEqual("第 1 次尝试", viewModel.NodeRuns[0].AttemptText);
        Assert.AreEqual("1 个成员", viewModel.SharedPublications[0].MemberCountText);
    }

    [TestMethod]
    public async Task NodeCatalogChromeUsesCurrentLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        Assert.AreEqual("节点目录", viewModel.NodeCatalogSectionText);
        Assert.AreEqual("节点", viewModel.NodeText);
        Assert.AreEqual("输入", viewModel.InputsText);
        Assert.AreEqual("输出", viewModel.OutputsText);
        Assert.AreEqual("模式", viewModel.ModeText);
        Assert.AreEqual("超时", viewModel.TimeoutText);
        Assert.AreEqual(
            "尚未加载节点定义。请连接 EngineHost 后刷新节点目录。",
            viewModel.NodeCatalogEmptyStateText);
        Assert.AreEqual("尚未加载节点定义。", viewModel.NodeDefinitionCatalogMessage);
    }

    [TestMethod]
    public async Task ConnectionAndDiagnosticsMessagesUseCurrentLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Failure(
                "UNAUTHORIZED",
                "Invalid local API token"),
        };
        var viewModel = CreateViewModel(uiSettingsStore, apiClient);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");
        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual("EngineHost 健康检查通过。", viewModel.StatusMessage);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual("工作流刷新失败。", viewModel.WorkflowMessage);
        Assert.AreEqual(
            "EngineHost 令牌错误、已轮换或已失效。请重新输入当前本地 API 令牌。",
            viewModel.WorkflowErrorMessage);
    }

    [TestMethod]
    public async Task TemplateWorkflowDisplayTextUsesCurrentLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow(
                        "wf-new",
                        "生成表格工作流",
                        1,
                        """{"nodes":[]}"""),
                }),
            CreateWorkflowResponse =
                ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                    Workflow(
                        "wf-new",
                        "生成表格工作流",
                        1,
                        """{"nodes":[]}""")),
        };
        var viewModel = CreateViewModel(uiSettingsStore, apiClient);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        Assert.AreEqual("生成表格工作流", viewModel.NewWorkflowName);

        await viewModel.CreateTemplateWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("生成表格工作流", apiClient.CreatedWorkflowName);
        Assert.IsNotNull(apiClient.CreatedWorkflowDefinition);
        var nodes = apiClient.CreatedWorkflowDefinition.Value.GetProperty("nodes");
        Assert.AreEqual("生成数据行", nodes[0].GetProperty("display_name").GetString());
        Assert.AreEqual("保留金额大于 1 的行", nodes[1].GetProperty("display_name").GetString());
    }

    [TestMethod]
    public async Task DefaultWorkflowNameDoesNotOverwriteUserEditedName()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);
        viewModel.NewWorkflowName = "Custom workflow";

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");

        Assert.AreEqual("Custom workflow", viewModel.NewWorkflowName);
    }

    [TestMethod]
    public async Task ChangeLanguageCommandFallsBackForUnsupportedLanguage()
    {
        var uiSettingsStore = new FakeUiSettingsStore();
        var viewModel = CreateViewModel(uiSettingsStore);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("fr-FR");

        Assert.AreEqual("en-US", viewModel.CurrentLanguageCode);
        Assert.AreEqual("Settings", viewModel.SettingsMenuText);
        Assert.AreEqual("Base URL", viewModel.ConnectionBaseUrlText);
        Assert.AreEqual("en-US", uiSettingsStore.SavedSettings?.LanguageCode);
    }

    private static MainWindowViewModel CreateViewModel(FakeUiSettingsStore uiSettingsStore)
    {
        return CreateViewModel(uiSettingsStore, new FakeApiClient());
    }

    private static MainWindowViewModel CreateViewModel(
        FakeUiSettingsStore uiSettingsStore,
        FakeApiClient apiClient)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient,
            new EngineHostRuntimeEventStreamClient(),
            runtimeEventReconnectDelay: _ => Task.CompletedTask,
            connectionSettingsStore: new FakeConnectionSettingsStore(),
            uiSettingsStore: uiSettingsStore,
            localizationService: new JsonLocalizationService(CreateLocalizationDirectory()))
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
            ConnectionStatus = ConnectionStatus.Connected,
        };
    }

    private static int GetShellPageIndex(MainWindowViewModel viewModel, ShellPageKey key)
    {
        for (var index = 0; index < viewModel.ShellNavigationItems.Count; index++)
        {
            if (viewModel.ShellNavigationItems[index].Key == key)
            {
                return index;
            }
        }

        throw new InvalidOperationException($"Shell page key '{key}' was not found.");
    }

    private static string CreateLocalizationDirectory()
    {
        var directory = Path.Combine(
            Path.GetTempPath(),
            "FlowWeaverTests",
            Guid.NewGuid().ToString("N"),
            "Localization");
        Directory.CreateDirectory(directory);
        foreach (var file in Directory.GetFiles(GetSourceLocalizationDirectory(), "*.json"))
        {
            File.Copy(file, Path.Combine(directory, Path.GetFileName(file)));
        }

        return directory;
    }

    private static string GetSourceLocalizationDirectory()
    {
        var directory = new DirectoryInfo(AppContext.BaseDirectory);
        while (directory is not null)
        {
            var localizationDirectory = Path.Combine(
                directory.FullName,
                "Avalonia_UI",
                "Localization");
            if (Directory.Exists(localizationDirectory))
            {
                return localizationDirectory;
            }

            directory = directory.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate source localization directory.");
    }

    private static WorkflowDefinitionDto Workflow(
        string workflowId,
        string name,
        int version,
        string definitionJson)
    {
        return new WorkflowDefinitionDto
        {
            WorkflowId = workflowId,
            Name = name,
            RevisionId = $"rev-{workflowId}",
            Version = version,
            DefinitionHash = $"hash-{workflowId}",
            Definition = JsonDocument.Parse(definitionJson).RootElement.Clone(),
            Status = "ACTIVE",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            UpdatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static WorkflowRunDto Run(string workflowRunId, string workflowId)
    {
        return new WorkflowRunDto
        {
            WorkflowRunId = workflowRunId,
            WorkflowId = workflowId,
            WorkflowVersion = 1,
            Status = "RUNNING",
            StateVersion = 1,
            StartedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static NodeRunDto NodeRun(
        string nodeRunId,
        string workflowRunId,
        string nodeInstanceId)
    {
        return new NodeRunDto
        {
            NodeRunId = nodeRunId,
            WorkflowRunId = workflowRunId,
            NodeInstanceId = nodeInstanceId,
            NodeType = "builtin.table",
            Status = "RUNNING",
            StateVersion = 1,
            Attempt = 1,
        };
    }

    private static SharedPublicationDto SharedPublication(
        string publicationId,
        string shareName)
    {
        return new SharedPublicationDto
        {
            PublicationId = publicationId,
            ShareName = shareName,
            PublicationVersion = 1,
            ProducerWorkflowId = "wf-1",
            ProducerRunId = "run-1",
            Status = "PUBLISHED",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            Members =
            [
                new SharedPublicationMemberDto
                {
                    PublicationId = publicationId,
                    ExportName = "orders",
                    TableRefId = "table-1",
                    ExactTableVersion = 1,
                },
            ],
        };
    }

    private sealed class FakeUiSettingsStore : IUiSettingsStore
    {
        public PersistedUiSettings SettingsToLoad { get; set; } =
            PersistedUiSettings.Default();

        public int LoadCount { get; private set; }

        public int SaveCount { get; private set; }

        public PersistedUiSettings? SavedSettings { get; private set; }

        public Task<PersistedUiSettings> LoadAsync(
            CancellationToken cancellationToken = default)
        {
            LoadCount++;
            return Task.FromResult(SettingsToLoad);
        }

        public Task SaveAsync(
            PersistedUiSettings settings,
            CancellationToken cancellationToken = default)
        {
            SaveCount++;
            SavedSettings = settings.Normalized();
            return Task.CompletedTask;
        }
    }

    private sealed class FakeConnectionSettingsStore : IConnectionSettingsStore
    {
        public Task<PersistedConnectionSettings> LoadAsync(
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(PersistedConnectionSettings.Default());
        }

        public Task SaveAsync(
            PersistedConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.CompletedTask;
        }
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<WorkflowDefinitionDto>> WorkflowsResponse { get; init; } =
            ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(new List<WorkflowDefinitionDto>());

        public ApiResponseEnvelope<WorkflowDefinitionDto> CreateWorkflowResponse { get; init; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No create response configured.");

        public ApiResponseEnvelope<WorkflowDefinitionDto> WorkflowDetailResponse { get; init; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No workflow detail response configured.");

        public ApiResponseEnvelope<List<WorkflowRevisionDto>> WorkflowRevisionsResponse { get; init; } =
            ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(new List<WorkflowRevisionDto>());

        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; init; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>());

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; init; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<List<NodeDefinitionDto>> NodeDefinitionsResponse { get; init; } =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(new List<NodeDefinitionDto>());

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationsResponse { get; init; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

        public string? CreatedWorkflowName { get; private set; }

        public JsonElement? CreatedWorkflowDefinition { get; private set; }

        public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<HealthStatusDto>.Success(
                    new HealthStatusDto { Status = "ok" }));
        }

        public Task<ApiResponseEnvelope<List<NodeDefinitionDto>>> ListNodeDefinitionsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(NodeDefinitionsResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(WorkflowsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> CreateWorkflowAsync(
            EngineHostConnectionSettings settings,
            string name,
            JsonElement definition,
            CancellationToken cancellationToken = default)
        {
            CreatedWorkflowName = name;
            CreatedWorkflowDefinition = definition.Clone();
            return Task.FromResult(CreateWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowValidationResultDto>> ValidateWorkflowDraftAsync(
            EngineHostConnectionSettings settings,
            JsonElement definition,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> UpdateWorkflowAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string? name,
            JsonElement definition,
            string baseRevisionId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> GetWorkflowAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(WorkflowDetailResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(WorkflowRevisionsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowRevisionDto>> GetWorkflowRevisionAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string revisionId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(RunsResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(NodeRunsResponse);
        }

        public Task<ApiResponseEnvelope<NodeRunPageDto>> ListNodeRunsPageAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 100,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<NodeRunPageDto>.Failure(
                    "NOT_CONFIGURED",
                    "No paged node run response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<TableRefDto>>> ListTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListRunTableDirectoryAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 100,
            string? nodeRunId = null,
            string? tableType = null,
            IReadOnlyCollection<string>? lifecycleStatuses = null,
            string? logicalTableId = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<RunTableDirectoryPageDto>.Failure(
                    "NOT_CONFIGURED",
                    "No run table directory response configured."));
        }

        public Task<ApiResponseEnvelope<List<LoopRunDto>>> ListLoopRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<LoopRunDto>>.Failure(
                    "NOT_CONFIGURED",
                    "No loop run response configured."));
        }

        public Task<ApiResponseEnvelope<List<LoopIterationRunDto>>> ListLoopIterationsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<LoopIterationRunDto>>.Failure(
                    "NOT_CONFIGURED",
                    "No loop iteration response configured."));
        }

        public Task<ApiResponseEnvelope<List<LoopIterationNodeRunDto>>> ListLoopIterationNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            string loopIterationId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<LoopIterationNodeRunDto>>.Failure(
                    "NOT_CONFIGURED",
                    "No loop iteration node response configured."));
        }

        public Task<ApiResponseEnvelope<List<LoopIterationTableRefDto>>> ListLoopIterationTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string loopRunId,
            string loopIterationId,
            string? role = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<LoopIterationTableRefDto>>.Failure(
                    "NOT_CONFIGURED",
                    "No loop iteration table response configured."));
        }
        public Task<ApiResponseEnvelope<NodeDefinitionCatalogStateDto>> GetNodeDefinitionCatalogStateAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<NodeDefinitionCatalogStateDto>.Failure(
                    "NOT_CONFIGURED",
                    "No catalog state response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowDeleteResultDto>> DeleteWorkflowAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowDeleteResultDto>.Failure(
                    "NOT_CONFIGURED",
                    "No workflow delete response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string runMode,
            string? targetNodeInstanceId = null,
            CancellationToken cancellationToken = default)
        {
            return StartWorkflowRunAsync(settings, workflowId, cancellationToken);
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> StartBackgroundWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            string runMode = "full",
            string? targetNodeInstanceId = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunDto>.Failure(
                    "NOT_CONFIGURED",
                    "No background run response configured."));
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsPageAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            string? runMode = null,
            string? triggerSource = null,
            int offset = 0,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<WorkflowRunDto>>.Failure(
                    "NOT_CONFIGURED",
                    "No paged run response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowRunDto>> RetryWorkflowRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            string? triggerSource = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunDto>.Failure(
                    "NOT_CONFIGURED",
                    "No retry response configured."));
        }

        public Task<ApiResponseEnvelope<RunTableCleanupResultDto>> CleanupRunTableRefsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<RunTableCleanupResultDto>.Failure(
                    "NOT_CONFIGURED",
                    "No table cleanup response configured."));
        }

        public Task<ApiResponseEnvelope<TableDataSchemaDto>> GetTableDataSchemaAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<TableDataSchemaDto>.Failure(
                    "NOT_CONFIGURED",
                    "No table schema response configured."));
        }

        public Task<ApiResponseEnvelope<TableDataSummaryDto>> GetTableDataSummaryAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<TableDataSummaryDto>.Failure(
                    "NOT_CONFIGURED",
                    "No table summary response configured."));
        }

        public Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? columns = null,
            IReadOnlyCollection<string>? orderBy = null,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<TableDataRowsDto>.Failure(
                    "NOT_CONFIGURED",
                    "No table rows response configured."));
        }

        public Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
            EngineHostConnectionSettings settings,
            long? afterSequenceNumber = null,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationsAsync(
            EngineHostConnectionSettings settings,
            string? shareName = null,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(SharedPublicationsResponse);
        }

        public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationVersionsAsync(
            EngineHostConnectionSettings settings,
            string shareName,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }
    }
}
