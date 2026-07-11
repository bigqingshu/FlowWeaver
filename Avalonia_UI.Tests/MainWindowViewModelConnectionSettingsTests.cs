using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Threading;
using System.Threading.Tasks;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Avalonia_UI.Services;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class MainWindowViewModelConnectionSettingsTests
{
    [TestMethod]
    public async Task LoadConnectionSettingsUsesPersistedBaseUrl()
    {
        var store = new FakeConnectionSettingsStore
        {
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl(
                "http://127.0.0.1:8010",
                "restored-token"),
        };
        var viewModel = CreateViewModel(new FakeApiClient(), store);

        await viewModel.LoadConnectionSettingsAsync();

        Assert.AreEqual("http://127.0.0.1:8010", viewModel.BaseUrl);
        Assert.AreEqual("restored-token", viewModel.Token);
        Assert.AreEqual(1, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsRestoresToken()
    {
        var store = new FakeConnectionSettingsStore
        {
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl(
                "http://127.0.0.1:8011",
                "persisted-token"),
        };
        var viewModel = CreateViewModel(new FakeApiClient(), store);

        await viewModel.LoadConnectionSettingsAsync();

        Assert.AreEqual("http://127.0.0.1:8011", viewModel.BaseUrl);
        Assert.AreEqual("persisted-token", viewModel.Token);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsFailureKeepsDefaultBaseUrl()
    {
        var store = new FakeConnectionSettingsStore
        {
            LoadException = new InvalidOperationException("settings unavailable"),
        };
        var viewModel = CreateViewModel(new FakeApiClient(), store);

        await viewModel.LoadConnectionSettingsAsync();

        Assert.AreEqual(EngineHostConnectionSettings.DefaultBaseUrl, viewModel.BaseUrl);
        Assert.AreEqual(
            "Connection settings were not loaded: settings unavailable",
            viewModel.ErrorMessage);
        Assert.IsTrue(viewModel.HasError);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsAndCheckConnectionUsesPersistedBaseUrlWhenHealthy()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
        };
        var store = new FakeConnectionSettingsStore
        {
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl(
                "http://127.0.0.1:8013",
                "restored-token"),
        };
        var viewModel = CreateViewModel(apiClient, store);

        await viewModel.LoadConnectionSettingsAndCheckConnectionAsync();

        Assert.AreEqual("http://127.0.0.1:8013", viewModel.BaseUrl);
        Assert.AreEqual(ConnectionStatus.Connected, viewModel.ConnectionStatus);
        Assert.AreEqual("EngineHost health check passed.", viewModel.StatusMessage);
        Assert.AreEqual(1, store.LoadCount);
        Assert.AreEqual(1, store.SaveCount);
        Assert.AreEqual("http://127.0.0.1:8013", store.SavedSettings?.LastSuccessfulBaseUrl);
        Assert.AreEqual("restored-token", store.SavedSettings?.Token);
        Assert.AreEqual("http://127.0.0.1:8013", apiClient.LastSettings?.BaseUrl);
        Assert.AreEqual("restored-token", apiClient.LastSettings?.Token);
        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual("connection.check", viewModel.NotificationKey);
        Assert.AreEqual(UiNotificationKind.Success, viewModel.NotificationKind);
        Assert.AreEqual("EngineHost health check passed.", viewModel.NotificationTitle);
        Assert.AreEqual(string.Empty, viewModel.NotificationMessage);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsAndCheckConnectionShowsFailureWhenUnavailable()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse = ApiResponseEnvelope<HealthStatusDto>.Failure(
                "UNAVAILABLE",
                "EngineHost unavailable."),
        };
        var store = new FakeConnectionSettingsStore
        {
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl("http://127.0.0.1:8014"),
        };
        var viewModel = CreateViewModel(apiClient, store);

        await viewModel.LoadConnectionSettingsAndCheckConnectionAsync();

        Assert.AreEqual("http://127.0.0.1:8014", viewModel.BaseUrl);
        Assert.AreEqual(ConnectionStatus.Error, viewModel.ConnectionStatus);
        Assert.AreEqual("Connection failed.", viewModel.StatusMessage);
        Assert.AreEqual("EngineHost unavailable.", viewModel.ErrorMessage);
        Assert.AreEqual(1, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
        Assert.AreEqual("http://127.0.0.1:8014", apiClient.LastSettings?.BaseUrl);
        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual("connection.check", viewModel.NotificationKey);
        Assert.AreEqual(UiNotificationKind.Error, viewModel.NotificationKind);
        Assert.AreEqual("Connection failed.", viewModel.NotificationTitle);
        Assert.AreEqual("EngineHost unavailable.", viewModel.NotificationMessage);
        Assert.IsTrue(viewModel.IsNotificationSticky);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsAndCheckConnectionDoesNotCheckWhenLoadFails()
    {
        var apiClient = new FakeApiClient();
        var store = new FakeConnectionSettingsStore
        {
            LoadException = new InvalidOperationException("settings unavailable"),
        };
        var viewModel = CreateViewModel(apiClient, store);

        await viewModel.LoadConnectionSettingsAndCheckConnectionAsync();

        Assert.AreEqual(EngineHostConnectionSettings.DefaultBaseUrl, viewModel.BaseUrl);
        Assert.AreEqual(ConnectionStatus.Disconnected, viewModel.ConnectionStatus);
        Assert.AreEqual(1, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
        Assert.IsNull(apiClient.LastSettings);
    }

    [TestMethod]
    public async Task CheckConnectionSavesBaseUrlWhenHealthy()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
        };
        var store = new FakeConnectionSettingsStore();
        var viewModel = CreateViewModel(apiClient, store);
        viewModel.BaseUrl = "http://127.0.0.1:8012/";
        viewModel.Token = "secret";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(ConnectionStatus.Connected, viewModel.ConnectionStatus);
        Assert.AreEqual(1, store.SaveCount);
        Assert.AreEqual("http://127.0.0.1:8012", store.SavedSettings?.LastSuccessfulBaseUrl);
        Assert.AreEqual("secret", store.SavedSettings?.Token);
        Assert.AreEqual("secret", viewModel.Token);
    }

    [TestMethod]
    public async Task CheckConnectionLoadsNodeDefinitionsWhenHealthyAndCatalogIsEmpty()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
            NodeDefinitionsResponse =
                ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                    new List<NodeDefinitionDto>
                    {
                        new()
                        {
                            NodeType = "GenerateTestTableNode",
                            NodeVersion = "1.0",
                            DisplayName = "Generate Test Table",
                            OutputPorts =
                            [
                                new NodePortDefinitionDto
                                {
                                    Name = "out",
                                    Required = true,
                                },
                            ],
                        },
                    }),
        };
        var viewModel = CreateViewModel(apiClient, new FakeConnectionSettingsStore());
        viewModel.BaseUrl = "http://127.0.0.1:8012/";
        viewModel.Token = "secret";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(ConnectionStatus.Connected, viewModel.ConnectionStatus);
        Assert.AreEqual(1, apiClient.ListNodeDefinitionsCallCount);
        Assert.HasCount(1, viewModel.NodeDefinitions);
        Assert.AreEqual("GenerateTestTableNode", viewModel.NodeDefinitions[0].NodeType);
        Assert.AreEqual("Loaded 1 node definition(s).", viewModel.NodeDefinitionCatalogMessage);
    }

    [TestMethod]
    public async Task CheckConnectionReusesNodeDefinitionsWhenCatalogStateMatches()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
            NodeDefinitionCatalogStateResponse =
                ApiResponseEnvelope<NodeDefinitionCatalogStateDto>.Success(
                    new NodeDefinitionCatalogStateDto
                    {
                        CatalogHash = "catalog-1",
                        NodeCount = 1,
                    }),
            NodeDefinitionsResponse =
                ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                    new List<NodeDefinitionDto>
                    {
                        NodeDefinition("GenerateTestTableNode", "Generate Test Table"),
                    }),
        };
        var viewModel = CreateViewModel(apiClient, new FakeConnectionSettingsStore());
        viewModel.BaseUrl = "http://127.0.0.1:8012/";
        viewModel.Token = "secret";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        apiClient.NodeDefinitionsResponse =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("ChangedNode", "Changed"),
                });

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(2, apiClient.GetNodeDefinitionCatalogStateCallCount);
        Assert.AreEqual(1, apiClient.ListNodeDefinitionsCallCount);
        Assert.HasCount(1, viewModel.NodeDefinitions);
        Assert.AreEqual("GenerateTestTableNode", viewModel.NodeDefinitions[0].NodeType);
        Assert.AreEqual("Loaded 1 node definition(s).", viewModel.NodeDefinitionCatalogMessage);
    }

    [TestMethod]
    public async Task CheckConnectionRefreshesNodeDefinitionsWhenTokenChanges()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
            NodeDefinitionCatalogStateResponse =
                ApiResponseEnvelope<NodeDefinitionCatalogStateDto>.Success(
                    new NodeDefinitionCatalogStateDto
                    {
                        CatalogHash = "catalog-1",
                        NodeCount = 1,
                    }),
            NodeDefinitionsResponse =
                ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                    new List<NodeDefinitionDto>
                    {
                        NodeDefinition("GenerateTestTableNode", "Generate Test Table"),
                    }),
        };
        var viewModel = CreateViewModel(apiClient, new FakeConnectionSettingsStore());
        viewModel.BaseUrl = "http://127.0.0.1:8012/";
        viewModel.Token = "secret";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        apiClient.NodeDefinitionsResponse =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("FilterRowsNode", "Filter Rows"),
                });
        viewModel.Token = "rotated";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(2, apiClient.GetNodeDefinitionCatalogStateCallCount);
        Assert.AreEqual(2, apiClient.ListNodeDefinitionsCallCount);
        Assert.HasCount(1, viewModel.NodeDefinitions);
        Assert.AreEqual("FilterRowsNode", viewModel.NodeDefinitions[0].NodeType);
        Assert.AreEqual("rotated", apiClient.LastSettings?.Token);
    }

    [TestMethod]
    public async Task RefreshNodeDefinitionsReusesSchemaParseResultForSameCatalog()
    {
        const string schemaJson =
            """
            {
              "type": "object",
              "properties": {
                "rows": {
                  "type": "integer",
                  "title": "Rows",
                  "required": true,
                  "default": 3
                }
              }
            }
            """;
        var apiClient = new FakeApiClient
        {
            NodeDefinitionCatalogStateResponse =
                ApiResponseEnvelope<NodeDefinitionCatalogStateDto>.Success(
                    new NodeDefinitionCatalogStateDto
                    {
                        CatalogHash = "catalog-1",
                        NodeCount = 1,
                    }),
            NodeDefinitionsResponse =
                ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                    new List<NodeDefinitionDto>
                    {
                        NodeDefinition("GenerateTestTableNode", "Generate Test Table", schemaJson),
                    }),
        };
        var viewModel = CreateViewModel(apiClient, new FakeConnectionSettingsStore());
        viewModel.Token = "secret";
        viewModel.ConnectionStatus = ConnectionStatus.Connected;

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        var firstSchema = viewModel.NodeDefinitions[0].ConfigSchema;
        apiClient.NodeDefinitionsResponse =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(
                new List<NodeDefinitionDto>
                {
                    NodeDefinition("GenerateTestTableNode", "Generate Test Table", schemaJson),
                });

        await viewModel.RefreshNodeDefinitionsCommand.ExecuteAsync(null);

        Assert.AreEqual(2, apiClient.GetNodeDefinitionCatalogStateCallCount);
        Assert.AreEqual(2, apiClient.ListNodeDefinitionsCallCount);
        Assert.AreSame(firstSchema, viewModel.NodeDefinitions[0].ConfigSchema);
    }

    [TestMethod]
    public async Task CheckConnectionLoadsWorkflowsWhenHealthyAndListIsEmpty()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
            WorkflowsResponse =
                ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                    new List<WorkflowDefinitionDto>
                    {
                        Workflow("workflow-1", "Daily report"),
                    }),
            WorkflowDetailResponse =
                ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                    Workflow("workflow-1", "Daily report")),
            WorkflowRevisionsResponse =
                ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                    new List<WorkflowRevisionDto>()),
        };
        var viewModel = CreateViewModel(apiClient, new FakeConnectionSettingsStore());
        viewModel.BaseUrl = "http://127.0.0.1:8012/";
        viewModel.Token = "secret";

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(ConnectionStatus.Connected, viewModel.ConnectionStatus);
        Assert.AreEqual(1, apiClient.ListWorkflowsCallCount);
        Assert.HasCount(1, viewModel.Workflows);
        Assert.AreEqual("workflow-1", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual("Loaded 1 workflow(s).", viewModel.WorkflowMessage);
        Assert.IsTrue(viewModel.HasWorkflowDefinition);
        Assert.AreEqual("workflow-1", apiClient.LastWorkflowDetailId);
    }

    [TestMethod]
    public async Task CheckConnectionDoesNotSaveWhenHealthFails()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse = ApiResponseEnvelope<HealthStatusDto>.Failure(
                "UNAVAILABLE",
                "EngineHost unavailable."),
        };
        var store = new FakeConnectionSettingsStore();
        var viewModel = CreateViewModel(apiClient, store);

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(ConnectionStatus.Error, viewModel.ConnectionStatus);
        Assert.AreEqual(0, store.SaveCount);
    }

    [TestMethod]
    public async Task SaveFailureDoesNotTurnHealthyConnectionIntoError()
    {
        var apiClient = new FakeApiClient
        {
            HealthResponse =
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }),
        };
        var store = new FakeConnectionSettingsStore
        {
            SaveException = new InvalidOperationException("disk unavailable"),
        };
        var viewModel = CreateViewModel(apiClient, store);

        await viewModel.CheckConnectionCommand.ExecuteAsync(null);

        Assert.AreEqual(ConnectionStatus.Connected, viewModel.ConnectionStatus);
        Assert.AreEqual("EngineHost health check passed.", viewModel.StatusMessage);
        Assert.AreEqual(
            "Connection settings were not saved: disk unavailable",
            viewModel.ErrorMessage);
        Assert.IsTrue(viewModel.HasError);
    }

    [TestMethod]
    public void CheckConnectionIsDisabledWhenBaseUrlIsBlank()
    {
        var viewModel = CreateViewModel(new FakeApiClient(), new FakeConnectionSettingsStore());

        viewModel.BaseUrl = "   ";

        Assert.IsFalse(viewModel.CheckConnectionCommand.CanExecute(null));

        viewModel.BaseUrl = "http://127.0.0.1:8000";

        Assert.IsTrue(viewModel.CheckConnectionCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task BusinessApiDoesNotReadOrSaveConnectionSettings()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse =
                ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(new List<WorkflowDefinitionDto>()),
        };
        var store = new FakeConnectionSettingsStore();
        var viewModel = CreateViewModel(apiClient, store);
        viewModel.Token = "secret";
        viewModel.ConnectionStatus = ConnectionStatus.Connected;

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual(0, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
        Assert.AreEqual("secret", apiClient.LastSettings?.Token);
    }

    [TestMethod]
    public async Task BusinessApiInvalidTokenShowsStableTokenRecoveryMessage()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Failure(
                "UNAUTHORIZED",
                "Invalid local API token"),
        };
        var store = new FakeConnectionSettingsStore();
        var viewModel = CreateViewModel(apiClient, store);
        viewModel.Token = "stale-token";
        viewModel.ConnectionStatus = ConnectionStatus.Connected;

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual("Workflow refresh failed.", viewModel.WorkflowMessage);
        Assert.AreEqual(
            "EngineHost token is wrong, rotated, or no longer valid. Re-enter the current local API token.",
            viewModel.WorkflowErrorMessage);
    }

    private static MainWindowViewModel CreateViewModel(
        FakeApiClient apiClient,
        FakeConnectionSettingsStore store)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient,
            new EngineHostRuntimeEventStreamClient(),
            runtimeEventReconnectDelay: _ => Task.CompletedTask,
            connectionSettingsStore: store);
    }

    private sealed class FakeConnectionSettingsStore : IConnectionSettingsStore
    {
        public PersistedConnectionSettings SettingsToLoad { get; set; } =
            PersistedConnectionSettings.Default();

        public Exception? LoadException { get; set; }

        public Exception? SaveException { get; set; }

        public int LoadCount { get; private set; }

        public int SaveCount { get; private set; }

        public PersistedConnectionSettings? SavedSettings { get; private set; }

        public Task<PersistedConnectionSettings> LoadAsync(
            CancellationToken cancellationToken = default)
        {
            LoadCount++;
            if (LoadException is not null)
            {
                throw LoadException;
            }

            return Task.FromResult(SettingsToLoad);
        }

        public Task SaveAsync(
            PersistedConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            SaveCount++;
            if (SaveException is not null)
            {
                throw SaveException;
            }

            SavedSettings = settings.Normalized();
            return Task.CompletedTask;
        }
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<HealthStatusDto> HealthResponse { get; set; } =
            ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" });

        public ApiResponseEnvelope<List<WorkflowDefinitionDto>> WorkflowsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(new List<WorkflowDefinitionDto>());

        public ApiResponseEnvelope<List<NodeDefinitionDto>> NodeDefinitionsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeDefinitionDto>>.Success(new List<NodeDefinitionDto>());

        public ApiResponseEnvelope<NodeDefinitionCatalogStateDto> NodeDefinitionCatalogStateResponse { get; set; } =
            ApiResponseEnvelope<NodeDefinitionCatalogStateDto>.Failure(
                "NOT_CONFIGURED",
                "No node definition catalog state response configured.");

        public Queue<ApiResponseEnvelope<NodeDefinitionCatalogStateDto>> NodeDefinitionCatalogStateResponses { get; } =
            new();

        public ApiResponseEnvelope<WorkflowDefinitionDto> WorkflowDetailResponse { get; set; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No workflow detail response configured.");

        public ApiResponseEnvelope<List<WorkflowRevisionDto>> WorkflowRevisionsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(new List<WorkflowRevisionDto>());

        public EngineHostConnectionSettings? LastSettings { get; private set; }

        public int ListNodeDefinitionsCallCount { get; private set; }

        public int GetNodeDefinitionCatalogStateCallCount { get; private set; }

        public int ListWorkflowsCallCount { get; private set; }

        public string? LastWorkflowDetailId { get; private set; }

        public string? LastWorkflowRevisionsWorkflowId { get; private set; }

        public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            return Task.FromResult(HealthResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeDefinitionDto>>> ListNodeDefinitionsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            ListNodeDefinitionsCallCount++;
            LastSettings = settings;
            return Task.FromResult(NodeDefinitionsResponse);
        }

        public Task<ApiResponseEnvelope<NodeDefinitionCatalogStateDto>> GetNodeDefinitionCatalogStateAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            GetNodeDefinitionCatalogStateCallCount++;
            LastSettings = settings;
            return Task.FromResult(
                NodeDefinitionCatalogStateResponses.Count > 0
                    ? NodeDefinitionCatalogStateResponses.Dequeue()
                    : NodeDefinitionCatalogStateResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            ListWorkflowsCallCount++;
            LastSettings = settings;
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
            LastSettings = settings;
            LastWorkflowDetailId = workflowId;
            return Task.FromResult(WorkflowDetailResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRevisionDto>>> ListWorkflowRevisionsAsync(
            EngineHostConnectionSettings settings,
            string workflowId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastWorkflowRevisionsWorkflowId = workflowId;
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
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
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

        public Task<ApiResponseEnvelope<TableRefDto>> GetTableRefAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
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
                ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                    new List<WorkflowRunDto>()));
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

        public Task<ApiResponseEnvelope<WorkflowRunDto>> GetRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunDto>.Failure(
                    "NOT_CONFIGURED",
                    "No run response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> GetRunRuntimeOptionsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>.Failure(
                    "NOT_CONFIGURED",
                    "No run runtime options response configured."));
        }

        public Task<ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>> ReplaceRunRuntimeOptionsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            int expectedVersion,
            WorkflowRunRuntimeOptionsOverlayDto overlay,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunRuntimeOptionsDto>.Failure(
                    "NOT_CONFIGURED",
                    "No run runtime options response configured."));
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

        public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> ListSharedPublicationCatalogAsync(
            EngineHostConnectionSettings settings,
            string? query = null,
            int offset = 0,
            int limit = 50,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListSharedPublicationVersionSummariesAsync(
            EngineHostConnectionSettings settings,
            string shareName,
            int offset = 0,
            int limit = 50,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListSharedPublicationMembersAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            int offset = 0,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }
    }

    private static WorkflowDefinitionDto Workflow(string workflowId, string name)
    {
        return new WorkflowDefinitionDto
        {
            WorkflowId = workflowId,
            RevisionId = $"revision-{workflowId}",
            Name = name,
            Version = 1,
            Status = "ACTIVE",
            Definition = JsonDocument.Parse("""{"schema_version":"1.0","nodes":[],"connections":[]}""")
                .RootElement
                .Clone(),
            DefinitionHash = $"hash-{workflowId}",
            CreatedAt = DateTimeOffset.Parse("2026-01-01T00:00:00Z"),
            UpdatedAt = DateTimeOffset.Parse("2026-01-01T00:00:00Z"),
        };
    }

    private static NodeDefinitionDto NodeDefinition(
        string nodeType,
        string displayName,
        string? schemaJson = null)
    {
        JsonElement? configSchema = null;
        if (schemaJson is not null)
        {
            using var schemaDocument = JsonDocument.Parse(schemaJson);
            configSchema = schemaDocument.RootElement.Clone();
        }

        return new NodeDefinitionDto
        {
            NodeType = nodeType,
            NodeVersion = "1.0",
            DisplayName = displayName,
            ExecutionMode = "PROCESS_POOL",
            DefaultTimeoutSeconds = 60,
            RetrySafe = false,
            UiVisibility = "visible",
            ConfigSchemaVersion = schemaJson is null ? string.Empty : "1.0",
            ConfigSchema = configSchema,
        };
    }
}
