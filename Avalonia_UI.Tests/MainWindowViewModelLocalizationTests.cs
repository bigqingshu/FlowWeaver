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
        Assert.AreEqual("未连接。", viewModel.StatusMessage);
        Assert.AreEqual("尚未加载工作流。", viewModel.WorkflowMessage);
        Assert.AreEqual("选择一个工作流以加载定义。", viewModel.WorkflowDefinitionMessage);
        Assert.AreEqual("加载定义后编辑草稿 JSON。", viewModel.WorkflowDefinitionValidationMessage);
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
        Assert.AreEqual("服务地址", viewModel.ConnectionBaseUrlText);
        Assert.AreEqual("数据", viewModel.DataTabText);
        Assert.AreEqual("审计事件", viewModel.AuditEventsSectionText);
        Assert.AreEqual("版本", viewModel.VersionsText);
        Assert.AreEqual(1, uiSettingsStore.SaveCount);
        Assert.AreEqual("zh-Hans", uiSettingsStore.SavedSettings?.LanguageCode);
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
            SharedPublicationsResponse =
                ApiResponseEnvelope<List<SharedPublicationDto>>.Success(
                    new List<SharedPublicationDto> { SharedPublication("pub-1", "daily_report") }),
        };
        var viewModel = CreateViewModel(uiSettingsStore, apiClient);

        await viewModel.ChangeLanguageCommand.ExecuteAsync("zh-Hans");
        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshSharedPublicationsCommand.ExecuteAsync(null);

        Assert.AreEqual("2 个节点", viewModel.WorkflowDefinitionDetail?.NodeCountText);
        Assert.AreEqual("1 条连接", viewModel.WorkflowDefinitionDetail?.ConnectionCountText);
        Assert.AreEqual("已禁用", viewModel.WorkflowDefinitionDetail?.Nodes[1].EnabledText);
        Assert.AreEqual("第 1 次尝试", viewModel.NodeRuns[0].AttemptText);
        Assert.AreEqual("1 个成员", viewModel.SharedPublications[0].MemberCountText);
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

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationsResponse { get; init; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

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
            return Task.FromResult(WorkflowsResponse);
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
