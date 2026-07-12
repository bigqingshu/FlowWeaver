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
public sealed class MainWindowViewModelLogTests
{
    [TestMethod]
    public async Task RefreshRuntimeEventLogPassesFiltersAndLoadsEvents()
    {
        var apiClient = new FakeApiClient
        {
            EventsResponse = ApiResponseEnvelope<List<RuntimeEventDto>>.Success(
                new List<RuntimeEventDto>
                {
                    RuntimeEvent("evt-1", 11, "NODE_STARTED", "run-1", "node-run-1"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.LogWorkflowRunIdFilter = " run-1 ";
        viewModel.LogNodeRunIdFilter = "node-run-1";
        viewModel.LogEventTypeFilter = "NODE_STARTED";
        viewModel.RuntimeEventAfterSequenceNumberFilter = "10";
        viewModel.RuntimeEventLimitFilter = "25";

        await viewModel.RefreshRuntimeEventLogCommand.ExecuteAsync(null);

        Assert.AreEqual(10, apiClient.LastAfterSequenceNumber);
        Assert.AreEqual("run-1", apiClient.LastEventWorkflowRunId);
        Assert.AreEqual("node-run-1", apiClient.LastEventNodeRunId);
        Assert.AreEqual("NODE_STARTED", apiClient.LastEventType);
        Assert.AreEqual(25, apiClient.LastEventLimit);
        Assert.HasCount(1, viewModel.RuntimeEventLogEntries);
        Assert.AreEqual("NODE_STARTED", viewModel.RuntimeEventLogEntries[0].EventType);
        Assert.AreEqual("Loaded 1 runtime event(s).", viewModel.RuntimeEventLogMessage);
        Assert.IsFalse(viewModel.HasRuntimeEventLogError);
    }

    [TestMethod]
    public async Task RefreshRuntimeEventLogRejectsInvalidLimitBeforeRequest()
    {
        var apiClient = new FakeApiClient();
        var viewModel = CreateViewModel(apiClient);
        viewModel.RuntimeEventLimitFilter = "1001";

        await viewModel.RefreshRuntimeEventLogCommand.ExecuteAsync(null);

        Assert.AreEqual(0, apiClient.ListEventsCallCount);
        Assert.AreEqual("Runtime event refresh rejected.", viewModel.RuntimeEventLogMessage);
        Assert.AreEqual(
            "Runtime event limit must be between 1 and 1000.",
            viewModel.RuntimeEventLogErrorMessage);
        Assert.IsTrue(viewModel.HasRuntimeEventLogError);
    }

    [TestMethod]
    public async Task RuntimeEventFilterChangeReleasesBusyAndIgnoresStaleResponse()
    {
        var pendingResponse =
            new TaskCompletionSource<ApiResponseEnvelope<List<RuntimeEventDto>>>(
                TaskCreationOptions.RunContinuationsAsynchronously);
        var apiClient = new FakeApiClient
        {
            EventsResponseTask = pendingResponse.Task,
        };
        var viewModel = CreateViewModel(apiClient);

        var refreshTask = viewModel.RefreshRuntimeEventLogCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.IsLoadingRuntimeEventLog);
        Assert.IsFalse(viewModel.RefreshRuntimeEventLogCommand.CanExecute(null));

        viewModel.LogWorkflowRunIdFilter = "run-new";

        Assert.IsFalse(viewModel.IsLoadingRuntimeEventLog);
        Assert.IsTrue(viewModel.RefreshRuntimeEventLogCommand.CanExecute(null));

        pendingResponse.SetResult(
            ApiResponseEnvelope<List<RuntimeEventDto>>.Success(
                new List<RuntimeEventDto>
                {
                    RuntimeEvent("evt-old", 1, "NODE_STARTED", "run-old", "node-old"),
                }));
        await refreshTask;

        Assert.IsFalse(viewModel.IsLoadingRuntimeEventLog);
        Assert.IsEmpty(viewModel.RuntimeEventLogEntries);
    }

    private static MainWindowViewModel CreateViewModel(FakeApiClient apiClient)
    {
        return new MainWindowViewModel(
            new EngineHostHealthClient(apiClient),
            apiClient)
        {
            BaseUrl = "http://127.0.0.1:8000",
            Token = "secret",
            ConnectionStatus = ConnectionStatus.Connected,
        };
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

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<RuntimeEventDto>> EventsResponse { get; set; } =
            ApiResponseEnvelope<List<RuntimeEventDto>>.Success(new List<RuntimeEventDto>());

        public Task<ApiResponseEnvelope<List<RuntimeEventDto>>>? EventsResponseTask { get; set; }

        public int ListEventsCallCount { get; private set; }

        public long? LastAfterSequenceNumber { get; private set; }

        public string? LastEventWorkflowRunId { get; private set; }

        public string? LastEventNodeRunId { get; private set; }

        public string? LastEventType { get; private set; }

        public int LastEventLimit { get; private set; }

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
            return Task.FromResult(
                ApiResponseEnvelope<List<WorkflowRunDto>>.Success(new List<WorkflowRunDto>()));
        }

        public Task<ApiResponseEnvelope<List<NodeRunDto>>> ListNodeRunsAsync(
            EngineHostConnectionSettings settings,
            string workflowRunId,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>()));
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
            ListEventsCallCount++;
            LastAfterSequenceNumber = afterSequenceNumber;
            LastEventWorkflowRunId = workflowRunId;
            LastEventNodeRunId = nodeRunId;
            LastEventType = eventType;
            LastEventLimit = limit;
            if (EventsResponseTask is not null)
            {
                return EventsResponseTask;
            }

            return Task.FromResult(EventsResponse);
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

        public Task<ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>> GetSharedPublicationCleanupPreviewAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }

        public Task<ApiResponseEnvelope<SharedPublicationCleanupResultDto>> CleanupSharedPublicationAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            CancellationToken cancellationToken = default)
        {
            throw new NotSupportedException();
        }
    }
}
