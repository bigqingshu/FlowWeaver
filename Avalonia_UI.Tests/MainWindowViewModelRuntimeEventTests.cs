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
public sealed class MainWindowViewModelRuntimeEventTests
{
    [TestMethod]
    public async Task StartRuntimeEventStreamRejectsMissingToken()
    {
        var apiClient = new FakeApiClient();
        var streamClient = new FakeRuntimeEventStreamClient();
        var viewModel = CreateViewModel(apiClient, streamClient);
        viewModel.Token = string.Empty;

        await viewModel.StartRuntimeEventStreamCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.IsRuntimeEventStreamRunning);
        Assert.IsTrue(viewModel.HasRuntimeEventStreamError);
        Assert.AreEqual("Event stream configuration invalid.", viewModel.RuntimeEventStreamMessage);
        Assert.AreEqual(0, streamClient.ConnectCount);
    }

    [TestMethod]
    public async Task RuntimeEventStreamReceivesEventAndRefreshesRuntimeState()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "extract", "RUNNING", 0.25, "reading"),
                }),
        };
        var streamClient = new FakeRuntimeEventStreamClient(
            new FakeRuntimeEventStream(
                RuntimeEvent("evt-1", 7, "NODE_STARTED", "run-1", "node-run-1")));
        var viewModel = CreateViewModel(apiClient, streamClient);

        await viewModel.StartRuntimeEventStreamCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => viewModel.RuntimeEvents.Count == 1);
        await viewModel.StopRuntimeEventStreamCommand.ExecuteAsync(null);

        Assert.AreEqual(1, streamClient.ConnectCount);
        Assert.AreEqual(7, viewModel.LastRuntimeEventSequenceNumber);
        Assert.AreEqual("NODE_STARTED", viewModel.RuntimeEvents[0].EventType);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.HasCount(1, viewModel.NodeRuns);
        Assert.AreEqual("25%", viewModel.NodeRuns[0].ProgressText);
        Assert.IsGreaterThanOrEqualTo(2, apiClient.ListRunsCallCount);
        Assert.IsGreaterThanOrEqualTo(2, apiClient.ListNodeRunsCallCount);
        Assert.AreEqual("Event stream stopped.", viewModel.RuntimeEventStreamMessage);
    }

    [TestMethod]
    public async Task RuntimeEventStreamReconnectsAfterDisconnectAndRecoversState()
    {
        var apiClient = new FakeApiClient
        {
            RunsResponse = ApiResponseEnvelope<List<WorkflowRunDto>>.Success(
                new List<WorkflowRunDto> { Run("run-1", "wf-1", "RUNNING") }),
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "extract", "RUNNING", 0.5, "processing"),
                }),
        };
        var streamClient = new FakeRuntimeEventStreamClient(
            new FakeRuntimeEventStream((RuntimeEventDto?)null),
            new FakeRuntimeEventStream(
                RuntimeEvent("evt-2", 8, "NODE_FINISHED", "run-1", "node-run-1")));
        var viewModel = CreateViewModel(apiClient, streamClient);

        await viewModel.StartRuntimeEventStreamCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => streamClient.ConnectCount >= 2 && viewModel.RuntimeEvents.Count == 1);
        await viewModel.StopRuntimeEventStreamCommand.ExecuteAsync(null);

        Assert.AreEqual(2, streamClient.ConnectCount);
        Assert.AreEqual("NODE_FINISHED", viewModel.RuntimeEvents[0].EventType);
        Assert.AreEqual("run-1", viewModel.SelectedRun?.WorkflowRunId);
        Assert.IsGreaterThanOrEqualTo(3, apiClient.ListRunsCallCount);
        Assert.AreEqual("Event stream stopped.", viewModel.RuntimeEventStreamMessage);
    }

    private static MainWindowViewModel CreateViewModel(
        FakeApiClient apiClient,
        FakeRuntimeEventStreamClient streamClient)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient,
            streamClient,
            _ => Task.CompletedTask)
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
        };
    }

    private static async Task WaitUntilAsync(Func<bool> condition)
    {
        for (var attempt = 0; attempt < 100; attempt++)
        {
            if (condition())
            {
                return;
            }

            await Task.Delay(10);
        }

        Assert.Fail("Condition was not reached before timeout.");
    }

    private static RuntimeEventDto RuntimeEvent(
        string eventId,
        long sequenceNumber,
        string eventType,
        string workflowRunId,
        string nodeRunId)
    {
        return new RuntimeEventDto
        {
            EventId = eventId,
            SequenceNumber = sequenceNumber,
            EventVersion = "1.0",
            EventType = eventType,
            Timestamp = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            WorkflowRunId = workflowRunId,
            NodeRunId = nodeRunId,
            Payload = JsonDocument.Parse("""{"status":"ok"}""").RootElement.Clone(),
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

    private sealed class FakeRuntimeEventStreamClient : IEngineHostRuntimeEventStreamClient
    {
        private readonly Queue<IEngineHostRuntimeEventStream> _streams;

        public FakeRuntimeEventStreamClient(params IEngineHostRuntimeEventStream[] streams)
        {
            _streams = new Queue<IEngineHostRuntimeEventStream>(streams);
        }

        public int ConnectCount { get; private set; }

        public Uri BuildEventsUri(EngineHostConnectionSettings settings)
        {
            return settings.BuildRuntimeEventsWebSocketUri();
        }

        public async Task<IEngineHostRuntimeEventStream> ConnectAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            await Task.Yield();
            _ = BuildEventsUri(settings);
            ConnectCount++;
            if (_streams.Count == 0)
            {
                throw new InvalidOperationException("No fake event stream is configured.");
            }

            return _streams.Dequeue();
        }
    }

    private sealed class FakeRuntimeEventStream : IEngineHostRuntimeEventStream
    {
        private readonly Queue<RuntimeEventDto?> _events;

        public FakeRuntimeEventStream(params RuntimeEventDto?[] events)
        {
            _events = new Queue<RuntimeEventDto?>(events);
        }

        public async Task<RuntimeEventDto?> ReadNextAsync(
            CancellationToken cancellationToken = default)
        {
            await Task.Yield();
            if (_events.Count > 0)
            {
                return _events.Dequeue();
            }

            await Task.Delay(Timeout.InfiniteTimeSpan, cancellationToken);
            return null;
        }

        public ValueTask DisposeAsync()
        {
            return ValueTask.CompletedTask;
        }
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<WorkflowRunDto>> RunsResponse { get; set; } =
            ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>());

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public int ListRunsCallCount { get; private set; }

        public int ListNodeRunsCallCount { get; private set; }

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
            return Task.FromResult(
                ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                    new List<WorkflowDefinitionDto>()));
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
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowRunDto>.Failure(
                    "NOT_CONFIGURED",
                    "No run response configured."));
        }

        public Task<ApiResponseEnvelope<List<WorkflowRunDto>>> ListRunsAsync(
            EngineHostConnectionSettings settings,
            string? workflowId = null,
            IReadOnlyCollection<string>? statuses = null,
            CancellationToken cancellationToken = default)
        {
            ListRunsCallCount++;
            return Task.FromResult(RunsResponse);
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            ListNodeRunsCallCount++;
            return Task.FromResult(NodeRunsResponse);
        }

        public Task<ApiResponseEnvelope<WorkflowProcessDto>> CancelRunAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<WorkflowProcessDto>.Failure(
                    "NOT_CONFIGURED",
                    "No cancel response configured."));
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
