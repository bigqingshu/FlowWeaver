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
public sealed class MainWindowViewModelWorkflowTests
{
    [TestMethod]
    public async Task RefreshWorkflowsLoadsAndSelectsFirstWorkflow()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.HasCount(2, viewModel.Workflows);
        Assert.AreEqual("wf-1", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual("Loaded 2 workflow(s).", viewModel.WorkflowMessage);
        Assert.IsFalse(viewModel.HasWorkflowError);
        Assert.AreEqual("secret", apiClient.LastSettings?.Token);
    }

    [TestMethod]
    public async Task RefreshWorkflowsKeepsSelectionWhenStillPresent()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        viewModel.SelectedWorkflow = viewModel.Workflows[1];
        apiClient.WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
            new List<WorkflowDefinitionDto>
            {
                Workflow("wf-2", "Report", 3),
                Workflow("wf-3", "Archive", 1),
            });

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-2", viewModel.SelectedWorkflow?.WorkflowId);
        Assert.AreEqual(3, viewModel.SelectedWorkflow?.Version);
    }

    [TestMethod]
    public async Task RefreshWorkflowsShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Failure(
                "TOKEN_REQUIRED",
                "EngineHost token is required."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);

        Assert.IsEmpty(viewModel.Workflows);
        Assert.AreEqual("Workflow refresh failed.", viewModel.WorkflowMessage);
        Assert.AreEqual("TOKEN_REQUIRED: EngineHost token is required.", viewModel.WorkflowErrorMessage);
        Assert.IsTrue(viewModel.HasWorkflowError);
    }

    [TestMethod]
    public async Task StartSelectedWorkflowStoresRunFeedback()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            StartWorkflowResponse = ApiResponseEnvelope<WorkflowRunDto>.Success(
                new WorkflowRunDto
                {
                    WorkflowRunId = "run-1",
                    WorkflowId = "wf-1",
                    Status = "PENDING",
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "PENDING") }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.StartSelectedWorkflowCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.StartedWorkflowId);
        Assert.AreEqual("run-1", viewModel.LastStartedRunId);
        Assert.AreEqual("PENDING", viewModel.LastStartedRunStatus);
        Assert.AreEqual("Started run run-1 (PENDING).", viewModel.WorkflowMessage);
        Assert.IsTrue(viewModel.HasLastStartedRun);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("wf-1", apiClient.LastRunWorkflowId);
    }

    [TestMethod]
    public void StartSelectedWorkflowIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.StartSelectedWorkflowCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task RefreshRunsLoadsRunsForSelectedWorkflow()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto>
                {
                    Workflow("wf-1", "Daily Load", 1),
                    Workflow("wf-2", "Report", 2),
                }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto>
                {
                    Run("run-1", "wf-1", "RUNNING"),
                    Run("run-2", "wf-1", "SUCCEEDED"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.LastRunWorkflowId);
        Assert.HasCount(2, viewModel.Runs);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("Loaded 2 run(s) for Daily Load.", viewModel.RunMessage);
        Assert.IsFalse(viewModel.HasRunError);
    }

    [TestMethod]
    public async Task CancelSelectedRunSendsRunIdAndRefreshesRuns()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            CancelRunResponse = ApiResponseEnvelope<WorkflowProcessDto>.Success(
                new WorkflowProcessDto
                {
                    ProcessId = "proc-1",
                    WorkflowRunId = "run-1",
                    Status = "CANCEL_REQUESTED",
                    StartedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        apiClient.RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
            new List<WorkflowRunDto> { Run("run-1", "wf-1", "CANCEL_REQUESTED") });

        await viewModel.CancelSelectedRunCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.CancelledWorkflowRunId);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.AreEqual("CANCEL_REQUESTED", viewModel.SelectedRun?.Status);
        Assert.IsFalse(viewModel.HasRunError);
    }

    [TestMethod]
    public void CancelSelectedRunIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.CancelSelectedRunCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task RefreshNodeRunsLoadsProgressAndStageForSelectedRun()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "extract", "RUNNING", 0.5, "reading"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.RefreshRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.LastNodeRunWorkflowRunId);
        Assert.HasCount(1, viewModel.NodeRuns);
        Assert.AreEqual("extract", viewModel.NodeRuns[0].NodeInstanceId);
        Assert.AreEqual("50%", viewModel.NodeRuns[0].ProgressText);
        Assert.AreEqual("reading", viewModel.NodeRuns[0].CurrentStageText);
        Assert.AreEqual("Loaded 1 node run(s).", viewModel.NodeRunMessage);
        Assert.IsFalse(viewModel.HasNodeRunError);
    }

    private static MainWindowViewModel CreateViewModel(FakeApiClient apiClient)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient)
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
        };
    }

    private static WorkflowDefinitionDto Workflow(string workflowId, string name, int version)
    {
        return new WorkflowDefinitionDto
        {
            WorkflowId = workflowId,
            Name = name,
            RevisionId = $"rev-{workflowId}",
            Version = version,
            DefinitionHash = $"hash-{workflowId}",
            Status = "ACTIVE",
            UpdatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            Definition = JsonDocument.Parse("""{"nodes":[]}""").RootElement.Clone(),
        };
    }

    private static WorkflowRunDto Run(string workflowRunId, string workflowId, string status)
    {
        return new WorkflowRunDto
        {
            WorkflowRunId = workflowRunId,
            WorkflowId = workflowId,
            WorkflowVersion = 1,
            Status = status,
            StateVersion = 1,
            StartedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static NodeRunDto NodeRun(
        string nodeRunId,
        string workflowRunId,
        string nodeInstanceId,
        string status,
        double? progress,
        string? currentStage)
    {
        return new NodeRunDto
        {
            NodeRunId = nodeRunId,
            WorkflowRunId = workflowRunId,
            NodeInstanceId = nodeInstanceId,
            NodeType = "builtin.table",
            Status = status,
            StateVersion = 1,
            Progress = progress,
            CurrentStage = currentStage,
            Attempt = 1,
            LastHeartbeat = DateTimeOffset.Parse("2026-06-29T01:03:03Z"),
        };
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<WorkflowDefinitionDto>> WorkflowsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(new List<WorkflowDefinitionDto>());

        public ApiResponseEnvelope<WorkflowRunDto> StartWorkflowResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No run response configured.");

        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>());

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<WorkflowProcessDto> CancelRunResponse { get; set; } =
            ApiResponseEnvelope<WorkflowProcessDto>.Failure("NOT_CONFIGURED", "No cancel response configured.");

        public EngineHostConnectionSettings? LastSettings { get; private set; }

        public string? StartedWorkflowId { get; private set; }

        public string? LastRunWorkflowId { get; private set; }

        public string? LastNodeRunWorkflowRunId { get; private set; }

        public string? CancelledWorkflowRunId { get; private set; }

        public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }));
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
            LastSettings = settings;
            StartedWorkflowId = workflowId;
            return Task.FromResult(StartWorkflowResponse);
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastRunWorkflowId = workflowId;
            return Task.FromResult(RunsResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            LastNodeRunWorkflowRunId = workflowRunId;
            return Task.FromResult(NodeRunsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            LastSettings = settings;
            CancelledWorkflowRunId = workflowRunId;
            return Task.FromResult(CancelRunResponse);
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
