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
public sealed class MainWindowViewModelDataTests
{
    [TestMethod]
    public async Task RefreshTableRefsUsesSelectedRunAndLoadsSummaries()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.LastTableRefWorkflowRunId);
        Assert.HasCount(1, viewModel.TableRefs);
        Assert.AreEqual("orders", viewModel.TableRefs[0].LogicalTableId);
        Assert.AreEqual("READ, WRITE", viewModel.TableRefs[0].CapabilitiesText);
        Assert.AreEqual("Loaded 1 table ref(s).", viewModel.TableRefMessage);
        Assert.IsFalse(viewModel.HasTableRefError);
    }

    [TestMethod]
    public async Task RefreshSharedPublicationsPassesFilterLimitAndSelectsFirst()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationsResponse =
                ApiResponseEnvelope<List<SharedPublicationDto>>.Success(
                    new List<SharedPublicationDto>
                    {
                        SharedPublication("pub-1", "daily_report", 2),
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationShareNameFilter = " daily_report ";
        viewModel.SharedPublicationLimitFilter = "25";

        await viewModel.RefreshSharedPublicationsCommand.ExecuteAsync(null);

        Assert.AreEqual("daily_report", apiClient.LastSharedPublicationShareName);
        Assert.AreEqual(25, apiClient.LastSharedPublicationLimit);
        Assert.HasCount(1, viewModel.SharedPublications);
        Assert.AreEqual("daily_report", viewModel.SelectedSharedPublication?.ShareName);
        Assert.AreEqual("daily_report", viewModel.SharedPublicationVersionShareNameFilter);
        Assert.AreEqual("Loaded 1 shared publication(s).", viewModel.SharedPublicationMessage);
        Assert.IsFalse(viewModel.HasSharedPublicationError);
    }

    [TestMethod]
    public async Task RefreshSharedPublicationsRejectsInvalidLimitBeforeRequest()
    {
        var apiClient = new FakeApiClient();
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationLimitFilter = "0";

        await viewModel.RefreshSharedPublicationsCommand.ExecuteAsync(null);

        Assert.AreEqual(0, apiClient.ListSharedPublicationsCallCount);
        Assert.AreEqual("Shared publication refresh rejected.", viewModel.SharedPublicationMessage);
        Assert.AreEqual(
            "Shared publication limit must be between 1 and 1000.",
            viewModel.SharedPublicationErrorMessage);
        Assert.IsTrue(viewModel.HasSharedPublicationError);
    }

    [TestMethod]
    public async Task RefreshSharedPublicationVersionsLoadsMemberSummaries()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionsResponse =
                ApiResponseEnvelope<List<SharedPublicationDto>>.Success(
                    new List<SharedPublicationDto>
                    {
                        SharedPublication("pub-2", "daily_report", 2),
                        SharedPublication("pub-1", "daily_report", 1),
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";
        viewModel.SharedPublicationVersionLimitFilter = "10";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);

        Assert.AreEqual("daily_report", apiClient.LastSharedPublicationVersionsShareName);
        Assert.AreEqual(10, apiClient.LastSharedPublicationVersionsLimit);
        Assert.HasCount(2, viewModel.SharedPublicationVersions);
        Assert.AreEqual("v2", viewModel.SharedPublicationVersions[0].VersionText);
        Assert.HasCount(1, viewModel.SharedPublicationVersions[0].Members);
        Assert.AreEqual("orders", viewModel.SharedPublicationVersions[0].Members[0].ExportName);
        Assert.AreEqual("Loaded 2 version(s) for daily_report.", viewModel.SharedPublicationVersionMessage);
        Assert.IsFalse(viewModel.HasSharedPublicationVersionError);
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

    private static TableRefDto TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId)
    {
        return new TableRefDto
        {
            TableRefId = tableRefId,
            WorkflowRunId = workflowRunId,
            NodeRunId = nodeRunId,
            Role = "OUTPUT",
            StorageKind = "RUNTIME_SQL",
            Scope = "WORKFLOW_SCOPE",
            Mutability = "IMMUTABLE",
            ProviderId = "runtime",
            LogicalTableId = "orders",
            Schema = JsonDocument.Parse("""{"fields":[]}""").RootElement.Clone(),
            SchemaFingerprint = "schema-1",
            Version = 2,
            Capabilities = ["WRITE", "READ"],
            LifecycleStatus = "PUBLISHED",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static SharedPublicationDto SharedPublication(
        string publicationId,
        string shareName,
        int publicationVersion)
    {
        return new SharedPublicationDto
        {
            PublicationId = publicationId,
            ShareName = shareName,
            PublicationVersion = publicationVersion,
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
                    ExactTableVersion = 2,
                },
            ],
        };
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<TableRefDto>> TableRefsResponse { get; set; } =
            ApiResponseEnvelope<List<TableRefDto>>.Success(new List<TableRefDto>());

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationsResponse { get; set; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationVersionsResponse { get; set; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

        public string? LastTableRefWorkflowRunId { get; private set; }

        public int ListSharedPublicationsCallCount { get; private set; }

        public string? LastSharedPublicationShareName { get; private set; }

        public int LastSharedPublicationLimit { get; private set; }

        public string? LastSharedPublicationVersionsShareName { get; private set; }

        public int LastSharedPublicationVersionsLimit { get; private set; }

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
            LastTableRefWorkflowRunId = workflowRunId;
            return Task.FromResult(TableRefsResponse);
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
            ListSharedPublicationsCallCount++;
            LastSharedPublicationShareName = shareName;
            LastSharedPublicationLimit = limit;
            return Task.FromResult(SharedPublicationsResponse);
        }

        public Task<ApiResponseEnvelope<List<SharedPublicationDto>>> ListSharedPublicationVersionsAsync(
            EngineHostConnectionSettings settings,
            string shareName,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            LastSharedPublicationVersionsShareName = shareName;
            LastSharedPublicationVersionsLimit = limit;
            return Task.FromResult(SharedPublicationVersionsResponse);
        }
    }
}
