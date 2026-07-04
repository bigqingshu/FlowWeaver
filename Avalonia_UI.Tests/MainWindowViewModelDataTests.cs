using System;
using System.Collections.Generic;
using System.Linq;
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

    [TestMethod]
    public async Task RefreshSelectedWorkflowNodeDataPreviewLoadsRowsForSelectedNode()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "generate"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.AreEqual("run-1", apiClient.LastNodeRunWorkflowRunId);
        Assert.AreEqual("run-1", apiClient.LastTableRefWorkflowRunId);
        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual(0, apiClient.LastTableRowsOffset);
        Assert.AreEqual(50, apiClient.LastTableRowsLimit);
        Assert.HasCount(2, viewModel.DataPreviewColumns);
        Assert.AreEqual("row_id", viewModel.DataPreviewColumns[0].Name);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.IsTrue(viewModel.HasDataPreviewColumns);
        Assert.IsTrue(viewModel.HasDataPreviewRows);
        Assert.IsFalse(viewModel.HasDataPreviewError);
        Assert.AreEqual("Loaded 1/1 preview row(s) for orders.", viewModel.DataPreviewMessage);
    }

    [TestMethod]
    public async Task RefreshSelectedWorkflowNodeDataPreviewShowsEmptyTableColumns()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "generate"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [],
                    rowCount: 0)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.HasCount(2, viewModel.DataPreviewColumns);
        Assert.AreEqual("row_id", viewModel.DataPreviewColumns[0].Name);
        Assert.IsEmpty(viewModel.DataPreviewRows);
        Assert.IsTrue(viewModel.HasDataPreviewColumns);
        Assert.IsFalse(viewModel.HasDataPreviewRows);
        Assert.AreEqual("Loaded 0/0 preview row(s) for orders.", viewModel.DataPreviewMessage);
    }

    [TestMethod]
    public async Task SameRunStatusRefreshKeepsRunRelatedData()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "generate"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");
        await viewModel.RefreshNodeRunsCommand.ExecuteAsync(null);
        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        Assert.HasCount(1, viewModel.NodeRuns);
        Assert.AreEqual("generate", viewModel.NodeRuns[0].NodeInstanceId);
        Assert.HasCount(1, viewModel.TableRefs);
        Assert.AreEqual("orders", viewModel.TableRefs[0].LogicalTableId);
        Assert.IsTrue(viewModel.HasDataPreviewColumns);
        Assert.IsTrue(viewModel.HasDataPreviewRows);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        Assert.AreEqual("Loaded 1/1 preview row(s) for orders.", viewModel.DataPreviewMessage);

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-2", "wf-1"));

        Assert.IsEmpty(viewModel.NodeRuns);
        Assert.IsEmpty(viewModel.TableRefs);
        Assert.IsFalse(viewModel.HasDataPreviewColumns);
        Assert.IsFalse(viewModel.HasDataPreviewRows);
        Assert.AreEqual("Select a run and workflow node, then refresh data preview.", viewModel.DataPreviewMessage);
    }

    [TestMethod]
    public async Task RefreshSelectedWorkflowNodeDataPreviewReportsMissingOutputTable()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "generate"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>()),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.IsFalse(viewModel.HasDataPreviewRows);
        Assert.AreEqual("Node generate has no readable output table.", viewModel.DataPreviewMessage);
        Assert.IsFalse(viewModel.HasDataPreviewError);
    }

    [TestMethod]
    public async Task RefreshSelectedWorkflowNodeDataPreviewKeepsPreviousRowsUntilNextSuccessfulLoad()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-1", "run-1", "generate"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "amount"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        apiClient.TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(new List<TableRefDto>());
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.HasCount(2, viewModel.DataPreviewColumns);
        Assert.AreEqual("row_id", viewModel.DataPreviewColumns[0].Name);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Node generate has no readable output table.", viewModel.DataPreviewMessage);
        Assert.IsFalse(viewModel.HasDataPreviewError);

        apiClient.TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            new List<TableRefDto>
            {
                TableRef("table-2", "run-1", "node-run-1"),
            });
        apiClient.TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
            TableRows(
                "table-2",
                ["code"],
                [
                    JsonDocument.Parse("""{"code":"A"}""")
                        .RootElement
                        .Clone(),
                ],
                rowCount: 1));
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.HasCount(1, viewModel.DataPreviewColumns);
        Assert.AreEqual("code", viewModel.DataPreviewColumns[0].Name);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "A" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Loaded 1/1 preview row(s) for orders.", viewModel.DataPreviewMessage);
        Assert.IsFalse(viewModel.HasDataPreviewError);
    }

    [TestMethod]
    public void DataRefreshCommandsRequireEngineActionsAndRequiredSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.RefreshTableRefsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSharedPublicationVersionsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshSharedPublicationsCommand.CanExecute(null));

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        Assert.IsTrue(viewModel.RefreshTableRefsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshSharedPublicationVersionsCommand.CanExecute(null));

        viewModel.Token = string.Empty;

        Assert.IsFalse(viewModel.RefreshTableRefsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSharedPublicationsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSharedPublicationVersionsCommand.CanExecute(null));
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

    private static TableDataRowsDto TableRows(
        string tableRefId,
        string[] columns,
        JsonElement[] rows,
        long rowCount)
    {
        return new TableDataRowsDto
        {
            TableRefId = tableRefId,
            Offset = 0,
            Limit = 50,
            RowCount = rowCount,
            Columns = columns,
            Rows = rows,
            HasMore = false,
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
            NodeType = "GenerateTestTableNode",
            Status = "SUCCEEDED",
            StateVersion = 1,
            Attempt = 1,
        };
    }

    private static WorkflowDefinitionNodeListItemViewModel WorkflowNode(
        string nodeInstanceId)
    {
        return new WorkflowDefinitionNodeListItemViewModel(
            nodeInstanceId,
            "GenerateTestTableNode",
            "1.0",
            "Generate",
            enabled: true,
            configJson: "{}");
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

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<TableDataRowsDto> TableRowsResponse { get; set; } =
            ApiResponseEnvelope<TableDataRowsDto>.Success(
                new TableDataRowsDto());

        public string? LastNodeRunWorkflowRunId { get; private set; }

        public string? LastTableRefWorkflowRunId { get; private set; }

        public string? LastTableRowsTableRefId { get; private set; }

        public int LastTableRowsOffset { get; private set; }

        public int LastTableRowsLimit { get; private set; }

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
            LastNodeRunWorkflowRunId = workflowRunId;
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
            LastTableRefWorkflowRunId = workflowRunId;
            return Task.FromResult(TableRefsResponse);
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
            LastTableRowsTableRefId = tableRefId;
            LastTableRowsOffset = offset;
            LastTableRowsLimit = limit;
            return Task.FromResult(TableRowsResponse);
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
