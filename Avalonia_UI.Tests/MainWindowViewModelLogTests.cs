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
    public async Task RefreshAuditEventsPassesFiltersAndLoadsEvents()
    {
        var apiClient = new FakeApiClient
        {
            AuditEventsResponse = ApiResponseEnvelope<List<AuditEventDto>>.Success(
                new List<AuditEventDto>
                {
                    new()
                    {
                        AuditEventId = "audit-1",
                        EventType = "PERMISSION_CHECK",
                        Decision = "granted",
                        WorkflowRunId = "run-1",
                        NodeRunId = "node-run-1",
                    },
                }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.LogWorkflowRunIdFilter = "run-1";
        viewModel.LogNodeRunIdFilter = "node-run-1";
        viewModel.LogEventTypeFilter = "PERMISSION_CHECK";

        await viewModel.RefreshAuditEventsCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.LastAuditWorkflowRunId);
        Assert.AreEqual("node-run-1", apiClient.LastAuditNodeRunId);
        Assert.AreEqual("PERMISSION_CHECK", apiClient.LastAuditEventType);
        Assert.HasCount(1, viewModel.AuditEvents);
        Assert.AreEqual("granted", viewModel.AuditEvents[0].Decision);
        Assert.AreEqual("Loaded 1 audit event(s).", viewModel.AuditEventLogMessage);
        Assert.IsFalse(viewModel.HasAuditEventLogError);
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

        public ApiResponseEnvelope<List<AuditEventDto>> AuditEventsResponse { get; set; } =
            ApiResponseEnvelope<List<AuditEventDto>>.Success(new List<AuditEventDto>());

        public int ListEventsCallCount { get; private set; }

        public long? LastAfterSequenceNumber { get; private set; }

        public string? LastEventWorkflowRunId { get; private set; }

        public string? LastEventNodeRunId { get; private set; }

        public string? LastEventType { get; private set; }

        public int LastEventLimit { get; private set; }

        public string? LastAuditWorkflowRunId { get; private set; }

        public string? LastAuditNodeRunId { get; private set; }

        public string? LastAuditEventType { get; private set; }

        public Task<ApiResponseEnvelope<HealthStatusDto>> GetHealthAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<HealthStatusDto>.Success(new HealthStatusDto { Status = "ok" }));
        }

        public Task<ApiResponseEnvelope<List<WorkflowDefinitionDto>>> ListWorkflowsAsync(
            EngineHostConnectionSettings settings,
            CancellationToken cancellationToken = default)
        {
            return Task.FromResult(
                ApiResponseEnvelope<List<WorkflowDefinitionDto>>.Success(
                    new List<WorkflowDefinitionDto>()));
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
            ListEventsCallCount++;
            LastAfterSequenceNumber = afterSequenceNumber;
            LastEventWorkflowRunId = workflowRunId;
            LastEventNodeRunId = nodeRunId;
            LastEventType = eventType;
            LastEventLimit = limit;
            return Task.FromResult(EventsResponse);
        }

        public Task<ApiResponseEnvelope<List<AuditEventDto>>> ListAuditEventsAsync(
            EngineHostConnectionSettings settings,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
            CancellationToken cancellationToken = default)
        {
            LastAuditWorkflowRunId = workflowRunId;
            LastAuditNodeRunId = nodeRunId;
            LastAuditEventType = eventType;
            return Task.FromResult(AuditEventsResponse);
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
