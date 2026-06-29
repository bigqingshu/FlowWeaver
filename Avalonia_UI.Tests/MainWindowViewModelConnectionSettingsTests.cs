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
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl("http://127.0.0.1:8010"),
        };
        var viewModel = CreateViewModel(new FakeApiClient(), store);
        viewModel.Token = "secret";

        await viewModel.LoadConnectionSettingsAsync();

        Assert.AreEqual("http://127.0.0.1:8010", viewModel.BaseUrl);
        Assert.AreEqual("secret", viewModel.Token);
        Assert.AreEqual(1, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
    }

    [TestMethod]
    public async Task LoadConnectionSettingsDoesNotRestoreToken()
    {
        var store = new FakeConnectionSettingsStore
        {
            SettingsToLoad = PersistedConnectionSettings.FromBaseUrl("http://127.0.0.1:8011"),
        };
        var viewModel = CreateViewModel(new FakeApiClient(), store);

        await viewModel.LoadConnectionSettingsAsync();

        Assert.AreEqual("http://127.0.0.1:8011", viewModel.BaseUrl);
        Assert.AreEqual(string.Empty, viewModel.Token);
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
        Assert.AreEqual("secret", viewModel.Token);
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

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual(0, store.LoadCount);
        Assert.AreEqual(0, store.SaveCount);
        Assert.AreEqual("secret", apiClient.LastSettings?.Token);
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

        public EngineHostConnectionSettings? LastSettings { get; private set; }

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
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
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
