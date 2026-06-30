using System;
using System.Collections.Generic;
using System.IO;
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
        Assert.AreEqual("工作流定义", viewModel.WorkflowDefinitionSectionText);
        Assert.AreEqual("工作流运行", viewModel.WorkflowRunFilterText);
        Assert.AreEqual("共享名称", viewModel.ShareNameWatermarkText);
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
        Assert.AreEqual("服务地址", viewModel.ConnectionBaseUrlText);
        Assert.AreEqual("数据", viewModel.DataTabText);
        Assert.AreEqual("审计事件", viewModel.AuditEventsSectionText);
        Assert.AreEqual("版本", viewModel.VersionsText);
        Assert.AreEqual(1, uiSettingsStore.SaveCount);
        Assert.AreEqual("zh-Hans", uiSettingsStore.SavedSettings?.LanguageCode);
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
        return new MainWindowViewModel(
            new EngineHostHealthClient(new FakeApiClient()),
            new FakeApiClient(),
            new EngineHostRuntimeEventStreamClient(),
            runtimeEventReconnectDelay: _ => Task.CompletedTask,
            connectionSettingsStore: new FakeConnectionSettingsStore(),
            uiSettingsStore: uiSettingsStore,
            localizationService: new JsonLocalizationService(CreateLocalizationDirectory()));
    }

    private static string CreateLocalizationDirectory()
    {
        var directory = Path.Combine(
            Path.GetTempPath(),
            "FlowWeaverTests",
            Guid.NewGuid().ToString("N"),
            "Localization");
        Directory.CreateDirectory(directory);
        File.WriteAllText(
            Path.Combine(directory, "en-US.json"),
            JsonSerializer.Serialize(
                new Dictionary<string, string>
                {
                    ["app.title"] = "FlowWeaver",
                    ["app.subtitle"] = "EngineHost connection",
                    ["settings.menu"] = "Settings",
                    ["settings.language"] = "Language",
                    ["language.en-US"] = "English",
                    ["language.zh-Hans"] = "Simplified Chinese",
                    ["common.refresh"] = "Refresh",
                    ["common.limit"] = "Limit",
                    ["connection.base_url"] = "Base URL",
                    ["connection.token"] = "Token",
                    ["connection.status"] = "Status",
                    ["connection.events"] = "Events",
                    ["connection.check"] = "Check",
                    ["connection.stream"] = "Stream",
                    ["connection.stop"] = "Stop",
                    ["tab.execution"] = "Execution",
                    ["tab.definition"] = "Definition",
                    ["tab.logs"] = "Logs",
                    ["tab.data"] = "Data",
                    ["workflow.section"] = "Workflows",
                    ["workflow.run"] = "Run",
                    ["workflow.create"] = "Create",
                    ["workflow.name_watermark"] = "Workflow name",
                    ["runs.section"] = "Runs",
                    ["runs.cancel"] = "Cancel",
                    ["node_runs.section"] = "Node runs",
                    ["definition.section"] = "Workflow definition",
                    ["definition.details"] = "Details",
                    ["definition.name"] = "Name",
                    ["definition.version"] = "Version",
                    ["definition.revision"] = "Revision",
                    ["definition.status"] = "Status",
                    ["definition.hash"] = "Hash",
                    ["definition.updated"] = "Updated",
                    ["definition.nodes"] = "Nodes",
                    ["definition.connections"] = "Connections",
                    ["definition.draft_json"] = "Draft JSON",
                    ["definition.validate"] = "Validate",
                    ["definition.save"] = "Save",
                    ["logs.workflow_run"] = "Workflow run",
                    ["logs.run_id_watermark"] = "run id",
                    ["logs.node_run"] = "Node run",
                    ["logs.node_run_id_watermark"] = "node run id",
                    ["logs.event_type"] = "Event type",
                    ["logs.after"] = "After",
                    ["logs.sequence_watermark"] = "sequence",
                    ["logs.runtime"] = "Runtime",
                    ["logs.audit"] = "Audit",
                    ["logs.runtime_events"] = "Runtime events",
                    ["logs.audit_events"] = "Audit events",
                    ["data.table_refs"] = "Table refs",
                    ["data.share"] = "Share",
                    ["data.share_name_watermark"] = "share name",
                    ["data.versions"] = "Versions",
                }));
        File.WriteAllText(
            Path.Combine(directory, "zh-Hans.json"),
            JsonSerializer.Serialize(
                new Dictionary<string, string>
                {
                    ["app.title"] = "FlowWeaver",
                    ["app.subtitle"] = "EngineHost 连接",
                    ["settings.menu"] = "设置",
                    ["settings.language"] = "语言",
                    ["language.en-US"] = "English",
                    ["language.zh-Hans"] = "简体中文",
                    ["common.refresh"] = "刷新",
                    ["common.limit"] = "限制",
                    ["connection.base_url"] = "服务地址",
                    ["connection.token"] = "令牌",
                    ["connection.status"] = "状态",
                    ["connection.events"] = "事件",
                    ["connection.check"] = "检查",
                    ["connection.stream"] = "监听",
                    ["connection.stop"] = "停止",
                    ["tab.execution"] = "执行",
                    ["tab.definition"] = "定义",
                    ["tab.logs"] = "日志",
                    ["tab.data"] = "数据",
                    ["workflow.section"] = "工作流",
                    ["workflow.run"] = "运行",
                    ["workflow.create"] = "创建",
                    ["workflow.name_watermark"] = "工作流名称",
                    ["runs.section"] = "运行记录",
                    ["runs.cancel"] = "取消",
                    ["node_runs.section"] = "节点运行",
                    ["definition.section"] = "工作流定义",
                    ["definition.details"] = "详情",
                    ["definition.name"] = "名称",
                    ["definition.version"] = "版本",
                    ["definition.revision"] = "修订",
                    ["definition.status"] = "状态",
                    ["definition.hash"] = "哈希",
                    ["definition.updated"] = "更新时间",
                    ["definition.nodes"] = "节点",
                    ["definition.connections"] = "连接",
                    ["definition.draft_json"] = "草稿 JSON",
                    ["definition.validate"] = "校验",
                    ["definition.save"] = "保存",
                    ["logs.workflow_run"] = "工作流运行",
                    ["logs.run_id_watermark"] = "运行 ID",
                    ["logs.node_run"] = "节点运行",
                    ["logs.node_run_id_watermark"] = "节点运行 ID",
                    ["logs.event_type"] = "事件类型",
                    ["logs.after"] = "起始序号",
                    ["logs.sequence_watermark"] = "序号",
                    ["logs.runtime"] = "运行时",
                    ["logs.audit"] = "审计",
                    ["logs.runtime_events"] = "运行时事件",
                    ["logs.audit_events"] = "审计事件",
                    ["data.table_refs"] = "表引用",
                    ["data.share"] = "共享名",
                    ["data.share_name_watermark"] = "共享名称",
                    ["data.versions"] = "版本",
                }));
        return directory;
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
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<WorkflowDefinitionDto>> CreateWorkflowAsync(
            EngineHostConnectionSettings settings,
            string name,
            JsonElement definition,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
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
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
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
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
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

        public Task<ApiResponseEnvelope<List<AuditEventDto>>> ListAuditEventsAsync(
            EngineHostConnectionSettings settings,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
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
            throw new NotSupportedException();
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
