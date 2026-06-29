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
    public async Task LoadSelectedWorkflowDefinitionLoadsDetailNodesConnectionsAndRevisions()
    {
        var definitionJson =
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "display_name": "Source",
                  "config": {"rows": 3}
                },
                {
                  "node_instance_id": "filter",
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
                  "target_node_id": "filter",
                  "target_port": "in"
                }
              ]
            }
            """;
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 2) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Success(
                Workflow("wf-1", "Daily Load", 2, definitionJson)),
            WorkflowRevisionsResponse = ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(
                new List<WorkflowRevisionDto>
                {
                    Revision("rev-wf-1", "wf-1", 1, definitionJson),
                    Revision("rev-wf-1-2", "wf-1", 2, definitionJson),
                }),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.AreEqual("wf-1", apiClient.LastWorkflowDetailId);
        Assert.AreEqual("wf-1", apiClient.LastWorkflowRevisionsWorkflowId);
        Assert.IsTrue(viewModel.HasWorkflowDefinition);
        Assert.IsFalse(viewModel.HasWorkflowDefinitionError);
        var detail = viewModel.WorkflowDefinitionDetail;
        Assert.IsNotNull(detail);
        Assert.AreEqual("Daily Load", detail.Name);
        Assert.AreEqual("rev-wf-1", detail.RevisionId);
        Assert.AreEqual("hash-wf-1", detail.DefinitionHash);
        Assert.HasCount(2, detail.Nodes);
        Assert.HasCount(1, detail.Connections);
        Assert.HasCount(2, detail.Revisions);
        Assert.AreEqual("GenerateTestTableNode@1.0", detail.Nodes[0].TypeText);
        Assert.AreEqual("disabled", detail.Nodes[1].EnabledText);
        Assert.AreEqual(
            "source.out -> filter.in",
            detail.Connections[0].EdgeText);
        StringAssert.Contains(
            detail.RawDefinitionJson,
            "\"schema_version\": \"1.0\"");
        Assert.AreEqual("Loaded Daily Load v2.", viewModel.WorkflowDefinitionMessage);
    }

    [TestMethod]
    public async Task LoadSelectedWorkflowDefinitionShowsErrorEnvelope()
    {
        var apiClient = new FakeApiClient
        {
            WorkflowsResponse = ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                new List<WorkflowDefinitionDto> { Workflow("wf-1", "Daily Load", 1) }),
            WorkflowDetailResponse = ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "WORKFLOW_NOT_FOUND",
                "Workflow not found."),
        };
        var viewModel = CreateViewModel(apiClient);

        await viewModel.RefreshWorkflowsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedWorkflowDefinitionCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.HasWorkflowDefinition);
        Assert.IsTrue(viewModel.HasWorkflowDefinitionError);
        Assert.AreEqual("Workflow definition load failed.", viewModel.WorkflowDefinitionMessage);
        Assert.AreEqual("WORKFLOW_NOT_FOUND: Workflow not found.", viewModel.WorkflowDefinitionErrorMessage);
    }

    [TestMethod]
    public void LoadSelectedWorkflowDefinitionIsDisabledWithoutSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.LoadSelectedWorkflowDefinitionCommand.CanExecute(null));
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

    private static WorkflowDefinitionDto Workflow(
        string workflowId,
        string name,
        int version,
        string definitionJson = """{"nodes":[]}""")
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
            Definition = JsonDocument.Parse(definitionJson).RootElement.Clone(),
        };
    }

    private static WorkflowRevisionDto Revision(
        string revisionId,
        string workflowId,
        int version,
        string definitionJson)
    {
        return new WorkflowRevisionDto
        {
            RevisionId = revisionId,
            WorkflowId = workflowId,
            Version = version,
            DefinitionHash = $"hash-{workflowId}-{version}",
            Definition = JsonDocument.Parse(definitionJson).RootElement.Clone(),
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            CreatedBy = "tester",
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

        public ApiResponseEnvelope<WorkflowDefinitionDto> WorkflowDetailResponse { get; set; } =
            ApiResponseEnvelope<WorkflowDefinitionDto>.Failure(
                "NOT_CONFIGURED",
                "No workflow detail response configured.");

        public ApiResponseEnvelope<List<WorkflowRevisionDto>> WorkflowRevisionsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRevisionDto>>.Success(new List<WorkflowRevisionDto>());

        public ApiResponseEnvelope<WorkflowRunDto> StartWorkflowResponse { get; set; } =
            ApiResponseEnvelope<WorkflowRunDto>.Failure("NOT_CONFIGURED", "No run response configured.");

        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>());

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<WorkflowProcessDto> CancelRunResponse { get; set; } =
            ApiResponseEnvelope<WorkflowProcessDto>.Failure("NOT_CONFIGURED", "No cancel response configured.");

        public EngineHostConnectionSettings? LastSettings { get; private set; }

        public string? LastWorkflowDetailId { get; private set; }

        public string? LastWorkflowRevisionsWorkflowId { get; private set; }

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
