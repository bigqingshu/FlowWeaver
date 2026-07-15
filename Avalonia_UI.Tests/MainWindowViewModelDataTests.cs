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
    public async Task RunTableDrilldownReusesDataDirectoryWithoutLoadingRows()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            [
                TableRef("table-1", "run-1", "node-run-1"),
                TableRef("table-2", "run-1", "node-run-2"),
            ]),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        viewModel.RunOverview.ViewTablesCommand.Execute(null);
        await viewModel.WaitForPendingRunMonitorDrilldownAsync();

        Assert.AreEqual(ShellPageKey.Data, viewModel.SelectedShellPageKey);
        Assert.IsNull(viewModel.RunTableNodeRunIdFilter);
        Assert.AreEqual("run-1", apiClient.LastTableRefWorkflowRunId);
        Assert.HasCount(2, viewModel.TableRefs);
        Assert.IsNull(apiClient.LastTableRowsTableRefId);
    }

    [TestMethod]
    public async Task NodePreviewDrilldownFiltersExistingDirectoryAndDoesNotLoadRows()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            [
                TableRef("table-1", "run-1", "node-run-1"),
                TableRef("table-2", "run-1", "node-run-2"),
            ]),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.NodeRunMonitor.Nodes.Add(new NodeRunListItemViewModel(
            NodeRun("node-run-2", "run-1")));
        viewModel.NodeRunMonitor.SelectedNodeRun = viewModel.NodeRunMonitor.Nodes[0];

        viewModel.NodeRunMonitor.ViewPreviewCommand.Execute(null);
        await viewModel.WaitForPendingRunMonitorDrilldownAsync();

        Assert.AreEqual(ShellPageKey.DataPreview, viewModel.SelectedShellPageKey);
        Assert.AreEqual("node-run-2", viewModel.RunTableNodeRunIdFilter);
        Assert.AreEqual("node-run-2", apiClient.LastTableRefNodeRunId);
        Assert.HasCount(1, viewModel.TableRefs);
        Assert.AreEqual("table-2", viewModel.TableRefs[0].TableRefId);
        Assert.IsNull(apiClient.LastTableRowsTableRefId);
    }

    [TestMethod]
    public async Task NodeLogDrilldownWritesExistingFiltersAndRefreshesLogs()
    {
        var apiClient = new FakeApiClient();
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.NodeRunMonitor.Nodes.Add(new NodeRunListItemViewModel(
            NodeRun("node-run-1", "run-1")));
        viewModel.NodeRunMonitor.SelectedNodeRun = viewModel.NodeRunMonitor.Nodes[0];

        viewModel.NodeRunMonitor.ViewLogsCommand.Execute(null);
        await viewModel.WaitForPendingRunMonitorDrilldownAsync();

        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellPageKey);
        Assert.AreEqual("run-1", viewModel.LogWorkflowRunIdFilter);
        Assert.AreEqual("node-run-1", viewModel.LogNodeRunIdFilter);
        Assert.AreEqual("run-1", apiClient.LastEventWorkflowRunId);
        Assert.AreEqual("node-run-1", apiClient.LastEventNodeRunId);
    }

    [TestMethod]
    public async Task RunLogDrilldownClearsPreviousNodeFilter()
    {
        var apiClient = new FakeApiClient();
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.LogNodeRunIdFilter = "old-node-run";

        viewModel.RunOverview.ViewLogsCommand.Execute(null);
        await viewModel.WaitForPendingRunMonitorDrilldownAsync();

        Assert.AreEqual(ShellPageKey.Logs, viewModel.SelectedShellPageKey);
        Assert.AreEqual("run-1", viewModel.LogWorkflowRunIdFilter);
        Assert.AreEqual(string.Empty, viewModel.LogNodeRunIdFilter);
        Assert.AreEqual("run-1", apiClient.LastEventWorkflowRunId);
        Assert.IsNull(apiClient.LastEventNodeRunId);
    }

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
    public async Task RefreshTableRefsBuildsDataPreviewStatesAndTableOptions()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                    TableRef("table-2", "run-1", "node-run-1", storageKind: "MEMORY"),
                    TableRef("table-3", "run-1", "node-run-2"),
                }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);

        Assert.HasCount(3, viewModel.DataPreviewStates);
        Assert.AreEqual(
            "run-1:node-run-1:memory_table",
            viewModel.DataPreviewStates[0].StateKey);
        Assert.AreEqual(
            "run-1:node-run-1:runtime_sql_table",
            viewModel.DataPreviewStates[1].StateKey);
        Assert.AreEqual(
            "run-1:node-run-2:runtime_sql_table",
            viewModel.DataPreviewStates[2].StateKey);
        Assert.AreEqual(
            "run-1:node-run-1:memory_table",
            viewModel.SelectedDataPreviewState?.StateKey);
        Assert.HasCount(1, viewModel.DataPreviewTableOptions);
        CollectionAssert.AreEqual(
            new[] { "table-2" },
            viewModel.DataPreviewTableOptions.Select(tableRef => tableRef.TableRefId).ToArray());
        Assert.AreEqual("table-2", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);

        viewModel.SelectedDataPreviewState = viewModel.DataPreviewStates[2];

        Assert.HasCount(1, viewModel.DataPreviewTableOptions);
        Assert.AreEqual("table-3", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);
        Assert.IsNull(apiClient.LastTableRowsTableRefId);
    }

    [TestMethod]
    public async Task TableDirectoryGroupsFourTypesAndKeepsUnreadableMetadataOutOfOptions()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            [
                TableRef(
                    "current",
                    "run-1",
                    "node-run-1",
                    sourceNodeInstanceId: "source-current",
                    tableType: "current_table"),
                TableRef(
                    "memory",
                    "run-1",
                    "node-run-1",
                    storageKind: "MEMORY",
                    capabilities: ["WRITE"],
                    sourceNodeInstanceId: "source-memory",
                    canReadRows: false),
                TableRef(
                    "runtime-left",
                    "run-1",
                    "node-run-1",
                    sourceNodeInstanceId: "source-left",
                    outputSlot: "left"),
                TableRef(
                    "runtime-right",
                    "run-1",
                    "node-run-1",
                    sourceNodeInstanceId: "source-right",
                    outputSlot: "right"),
                TableRef(
                    "external",
                    "run-1",
                    "node-run-1",
                    storageKind: "EXTERNAL_SQL",
                    sourceNodeInstanceId: "source-external"),
            ]),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);

        CollectionAssert.AreEqual(
            new[]
            {
                "current_table",
                "memory_table",
                "runtime_sql_table",
                "external_sql_table",
            },
            viewModel.DataPreviewStates.Select(state => state.TableType).ToArray());
        var memoryState = viewModel.DataPreviewStates.Single(state =>
            state.TableType == "memory_table");
        Assert.AreEqual("Temporary memory table", memoryState.TableRefs[0].PreviewPersistenceText);
        Assert.IsFalse(memoryState.TableRefs[0].CanReadRows);
        StringAssert.Contains(memoryState.TableRefs[0].ReadabilityText, "Unreadable");
        viewModel.SelectedDataPreviewState = memoryState;
        Assert.IsEmpty(viewModel.DataPreviewTableOptions);
        Assert.IsFalse(viewModel.LoadSelectedDataPreviewTableCommand.CanExecute(null));

        var runtimeState = viewModel.DataPreviewStates.Single(state =>
            state.TableType == "runtime_sql_table");
        viewModel.SelectedDataPreviewState = runtimeState;
        Assert.HasCount(2, viewModel.DataPreviewTableOptions);
        CollectionAssert.AreEqual(
            new[] { "source-left", "source-right" },
            viewModel.DataPreviewTableOptions.Select(table => table.SourceNodeText).ToArray());
        CollectionAssert.AreEqual(
            new[] { "left", "right" },
            viewModel.DataPreviewTableOptions.Select(table => table.OutputSlotText).ToArray());
        Assert.AreEqual(0, apiClient.GetTableRowsCallCount);
    }

    [TestMethod]
    public async Task RapidRunSwitchCancelsOldDirectoryAndRejectsLateResponse()
    {
        var firstStarted = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseFirst = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var firstCancelled = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var apiClient = new FakeApiClient
        {
            RunTableDirectoryHandler = async (workflowRunId, offset, limit, cancellationToken) =>
            {
                if (workflowRunId == "run-1")
                {
                    using var registration = cancellationToken.Register(
                        () => firstCancelled.TrySetResult());
                    firstStarted.TrySetResult();
                    await releaseFirst.Task;
                    return DirectoryPage(
                        TableRef("old", "run-1", "node-old"),
                        offset,
                        limit);
                }

                return DirectoryPage(
                    TableRef("new", "run-2", "node-new"),
                    offset,
                    limit);
            },
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        var firstLoad = viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await firstStarted.Task;

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-2", "wf-1"));
        await firstCancelled.Task.WaitAsync(TimeSpan.FromSeconds(1));
        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        releaseFirst.TrySetResult();
        await firstLoad;

        Assert.HasCount(1, viewModel.TableRefs);
        Assert.AreEqual("new", viewModel.TableRefs[0].TableRefId);
        Assert.AreEqual("run-2", viewModel.TableRefs[0].WorkflowRunId);
    }

    [TestMethod]
    public async Task RapidTableSwitchCancelsOldRowsAndRejectsLateResponse()
    {
        var firstStarted = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var releaseFirst = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var firstCancelled = new TaskCompletionSource(
            TaskCreationOptions.RunContinuationsAsynchronously);
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            [
                TableRef("table-1", "run-1", "node-run-1"),
                TableRef("table-2", "run-1", "node-run-1"),
            ]),
            TableRowsHandler = async (tableRefId, cancellationToken) =>
            {
                if (tableRefId == "table-1")
                {
                    using var registration = cancellationToken.Register(
                        () => firstCancelled.TrySetResult());
                    firstStarted.TrySetResult();
                    await releaseFirst.Task;
                    return TableRowsResponse("table-1", "old");
                }

                return TableRowsResponse("table-2", "new");
            },
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        var firstLoad = viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);
        await firstStarted.Task;

        viewModel.SelectedDataPreviewTableOption = viewModel.DataPreviewTableOptions[1];
        await firstCancelled.Task.WaitAsync(TimeSpan.FromSeconds(1));
        releaseFirst.TrySetResult();
        await firstLoad;
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual("table-2", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        Assert.AreEqual("new", viewModel.DataPreviewWorkbenchRows[0].Cells[0].Text);
    }

    [TestMethod]
    public async Task RefreshSharedPublicationsPassesFilterLimitAndSelectsFirst()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationCatalogResponse =
                ApiResponseEnvelope<SharedPublicationCatalogPageDto>.Success(
                    new SharedPublicationCatalogPageDto
                    {
                        Items =
                        [
                            SharedPublicationCatalogEntry("daily_report", 2),
                        ],
                        Limit = 25,
                        Total = 1,
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationShareNameFilter = " daily_report ";
        viewModel.SharedPublicationLimitFilter = "25";

        await viewModel.RefreshSharedPublicationsCommand.ExecuteAsync(null);

        Assert.AreEqual("daily_report", apiClient.LastSharedPublicationCatalogQuery);
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

        Assert.AreEqual(0, apiClient.ListSharedPublicationCatalogCallCount);
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
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items =
                        [
                            SharedPublicationSummary("pub-2", "daily_report", 2),
                            SharedPublicationSummary("pub-1", "daily_report", 1),
                        ],
                        Limit = 10,
                        Total = 2,
                    }),
            SharedPublicationMembersResponse =
                ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                    new SharedPublicationMemberPageDto
                    {
                        Items =
                        [
                            new SharedPublicationMemberDto
                            {
                                PublicationId = "pub-2",
                                ExportName = "orders",
                                TableRefId = "table-pub-2",
                                ExactTableVersion = 2,
                                TableRefLifecycleStatus = "PUBLISHED",
                                TableRefStorageKind = "RUNTIME_SQL",
                                LogicalTableId = "orders",
                                CanReadRows = true,
                            },
                        ],
                        Limit = 100,
                        Total = 1,
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
        Assert.AreEqual("1 member(s)", viewModel.SharedPublicationVersions[0].MemberCountText);
        Assert.AreEqual("pub-2", apiClient.LastSharedPublicationMembersPublicationId);
        Assert.HasCount(1, viewModel.SelectedSharedPublicationVersionMembers);
        Assert.AreEqual("orders", viewModel.SelectedSharedPublicationVersionMembers[0].ExportName);
        Assert.AreEqual(
            "PUBLISHED",
            viewModel.SelectedSharedPublicationVersionMembers[0].LifecycleStatusText);
        Assert.IsTrue(
            viewModel.SelectedSharedPublicationVersionMembers[0]
                .PreviewCommand
                .CanExecute(null));
        Assert.AreEqual("Loaded 2 version(s) for daily_report.", viewModel.SharedPublicationVersionMessage);
        Assert.IsFalse(viewModel.HasSharedPublicationVersionError);
    }

    [TestMethod]
    public async Task SharedPublicationCleanupPreviewShowsLifecycleAndEligibility()
    {
        var expiresAt = DateTimeOffset.Parse("2026-07-12T00:00:00Z");
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items =
                        [
                            SharedPublicationSummary("pub-1", "daily_report", 1) with
                            {
                                ExpiresAt = expiresAt,
                                IsLatestPublished = false,
                            },
                        ],
                        Total = 1,
                    }),
            SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = "pub-1",
                        Eligible = true,
                        Status = "PUBLISHED",
                        ExpiresAt = expiresAt,
                        ReleasableMemberCount = 2,
                        ProtectedMemberCount = 1,
                        ActiveReadLeaseCount = 0,
                        ActiveTableLeaseCount = 0,
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => apiClient.SharedPublicationCleanupPreviewCallCount > 0);

        Assert.AreEqual("pub-1", apiClient.LastSharedPublicationCleanupPreviewPublicationId);
        Assert.AreEqual("PUBLISHED", viewModel.SharedPublicationCleanupStatusText);
        Assert.AreEqual(
            expiresAt.ToLocalTime().ToString("yyyy-MM-dd HH:mm:ss"),
            viewModel.SharedPublicationCleanupExpiresAtText);
        Assert.AreEqual(
            "Releasable 2 · protected 1 · read leases 0 · table leases 0",
            viewModel.SharedPublicationCleanupCountsText);
        Assert.AreEqual(
            "This version can be cleaned.",
            viewModel.SharedPublicationCleanupMessage);
        Assert.IsTrue(viewModel.CleanupSharedPublicationCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SharedPublicationCleanupPreviewDisplaysBlockers()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [SharedPublicationSummary("pub-2", "daily_report", 2)],
                        Total = 1,
                    }),
            SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = "pub-2",
                        Status = "PUBLISHED",
                        Blockers =
                        [
                            "LATEST_VERSION_PROTECTED",
                            "ACTIVE_READ_LEASE",
                        ],
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => apiClient.SharedPublicationCleanupPreviewCallCount > 0);

        CollectionAssert.AreEqual(
            new[]
            {
                "The latest active version is protected",
                "An active read lease exists",
            },
            viewModel.SharedPublicationCleanupBlockers.ToArray());
        Assert.IsTrue(viewModel.HasSharedPublicationCleanupBlockers);
        Assert.IsFalse(viewModel.CleanupSharedPublicationCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SharedPublicationCleanupBlockedResponseRefreshesPreview()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items =
                        [
                            SharedPublicationSummary("pub-1", "daily_report", 1) with
                            {
                                IsLatestPublished = false,
                            },
                        ],
                        Total = 1,
                    }),
            SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = "pub-1",
                        Eligible = true,
                        Status = "PUBLISHED",
                    }),
        };
        apiClient.SharedPublicationCleanupHandler = (publicationId, _) =>
        {
            apiClient.SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = publicationId,
                        Status = "PUBLISHED",
                        Blockers = ["ACTIVE_TABLE_LEASE"],
                    });
            return Task.FromResult(
                ApiResponseEnvelope<SharedPublicationCleanupResultDto>.Success(
                    new SharedPublicationCleanupResultDto
                    {
                        PublicationId = publicationId,
                        Outcome = "BLOCKED",
                        Status = "PUBLISHED",
                        Blockers = ["ACTIVE_TABLE_LEASE"],
                    }));
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";
        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => viewModel.CleanupSharedPublicationCommand.CanExecute(null));

        await viewModel.CleanupSharedPublicationCommand.ExecuteAsync(null);

        Assert.AreEqual(1, apiClient.SharedPublicationCleanupCallCount);
        Assert.AreEqual(
            "The server blocked cleanup after rechecking conditions.",
            viewModel.SharedPublicationCleanupMessage);
        CollectionAssert.AreEqual(
            new[] { "An active table lease exists" },
            viewModel.SharedPublicationCleanupBlockers.ToArray());
        Assert.IsFalse(viewModel.CleanupSharedPublicationCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SharedPublicationCleanupSuccessRefreshesSelectedVersion()
    {
        var releasedSummary = SharedPublicationSummary("pub-1", "daily_report", 1) with
        {
            Status = "RELEASED",
            IsLatestPublished = false,
            ReleasedAt = DateTimeOffset.Parse("2026-07-12T01:00:00Z"),
        };
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items =
                        [
                            SharedPublicationSummary("pub-1", "daily_report", 1) with
                            {
                                IsLatestPublished = false,
                            },
                        ],
                        Total = 1,
                    }),
            SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = "pub-1",
                        Eligible = true,
                        Status = "PUBLISHED",
                    }),
        };
        apiClient.SharedPublicationCleanupHandler = (publicationId, _) =>
        {
            apiClient.SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [releasedSummary],
                        Total = 1,
                    });
            apiClient.SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = publicationId,
                        Status = "RELEASED",
                        Blockers = ["PUBLICATION_NOT_PUBLISHED"],
                    });
            return Task.FromResult(
                ApiResponseEnvelope<SharedPublicationCleanupResultDto>.Success(
                    new SharedPublicationCleanupResultDto
                    {
                        PublicationId = publicationId,
                        Outcome = "CLEANED",
                        Status = "RELEASED",
                        ReleasedMemberCount = 1,
                    }));
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";
        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => viewModel.CleanupSharedPublicationCommand.CanExecute(null));

        await viewModel.CleanupSharedPublicationCommand.ExecuteAsync(null);

        Assert.AreEqual(1, apiClient.SharedPublicationCleanupCallCount);
        Assert.AreEqual("pub-1", apiClient.LastSharedPublicationCleanupPublicationId);
        Assert.AreEqual("RELEASED", viewModel.SelectedSharedPublicationVersion?.Status);
        Assert.AreEqual(
            "The shared version was cleaned and its metadata was retained.",
            viewModel.SharedPublicationCleanupMessage);
        Assert.IsFalse(viewModel.CleanupSharedPublicationCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SharedPublicationCleanupRetryPendingRemainsActionable()
    {
        var releasingSummary = SharedPublicationSummary("pub-1", "daily_report", 1) with
        {
            Status = "RELEASING",
            IsLatestPublished = false,
        };
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [releasingSummary],
                        Total = 1,
                    }),
            SharedPublicationCleanupPreviewResponse =
                ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                    new SharedPublicationCleanupPreviewDto
                    {
                        PublicationId = "pub-1",
                        Status = "RELEASING",
                        Blockers = ["PUBLICATION_NOT_PUBLISHED"],
                    }),
            SharedPublicationCleanupResponse =
                ApiResponseEnvelope<SharedPublicationCleanupResultDto>.Success(
                    new SharedPublicationCleanupResultDto
                    {
                        PublicationId = "pub-1",
                        Outcome = "RETRY_PENDING",
                        Status = "RELEASING",
                        RemainingMemberCount = 2,
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";
        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        await WaitUntilAsync(() => viewModel.CleanupSharedPublicationCommand.CanExecute(null));

        await viewModel.CleanupSharedPublicationCommand.ExecuteAsync(null);

        Assert.AreEqual(
            "This cleanup pass finished with at least 2 member(s) remaining.",
            viewModel.SharedPublicationCleanupMessage);
        Assert.IsTrue(viewModel.CleanupSharedPublicationCommand.CanExecute(null));
    }

    [TestMethod]
    public async Task SharedPublicationMemberPreviewLoadsExistingDataWorkbench()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [SharedPublicationSummary("pub-2", "daily_report", 2)],
                        Total = 1,
                    }),
            SharedPublicationMembersResponse =
                ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                    new SharedPublicationMemberPageDto
                    {
                        Items = [SharedMember("pub-2", "orders", "table-pub-2")],
                        Total = 1,
                    }),
            TableRefDetailResponse = ApiResponseEnvelope<TableRefDto>.Success(
                TableRef("table-pub-2", "run-1", "node-run-1")),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-pub-2",
                    ["row_id", "amount"],
                    [JsonDocument.Parse("""{"row_id":1,"amount":12.5}""")
                        .RootElement.Clone()],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        var member = viewModel.SelectedSharedPublicationVersionMembers.Single();
        await member.PreviewCommand.ExecuteAsync(null);

        Assert.AreEqual("table-pub-2", apiClient.LastTableRefDetailId);
        Assert.AreEqual("table-pub-2", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual(ShellPageKey.DataPreview, viewModel.SelectedShellPageKey);
        Assert.AreEqual("table-pub-2", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        Assert.AreEqual("12.5", viewModel.DataPreviewWorkbenchRows[0].Cells[1].Text);
    }

    [TestMethod]
    public async Task ReleasedSharedPublicationMemberKeepsMetadataWithoutPreviewRequest()
    {
        var releasedMember = SharedMember("pub-1", "orders", "table-released") with
        {
            TableRefLifecycleStatus = "RELEASED",
            CanReadRows = false,
        };
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [SharedPublicationSummary("pub-1", "daily_report", 1)],
                        Total = 1,
                    }),
            SharedPublicationMembersResponse =
                ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                    new SharedPublicationMemberPageDto
                    {
                        Items = [releasedMember],
                        Total = 1,
                    }),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        var member = viewModel.SelectedSharedPublicationVersionMembers.Single();

        Assert.AreEqual("RELEASED", member.LifecycleStatusText);
        Assert.AreEqual("Table data was released", member.AvailabilityText);
        Assert.IsFalse(member.PreviewCommand.CanExecute(null));
        await member.PreviewCommand.ExecuteAsync(null);
        Assert.IsNull(apiClient.LastTableRefDetailId);
        Assert.IsNull(apiClient.LastTableRowsTableRefId);
    }

    [TestMethod]
    public async Task SharedPublicationMembersLoadAdditionalPagesOnDemand()
    {
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [SharedPublicationSummary("pub-2", "daily_report", 2)],
                        Total = 1,
                    }),
            SharedPublicationMembersHandler = (publicationId, offset, limit, _) =>
                Task.FromResult(
                    ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                        new SharedPublicationMemberPageDto
                        {
                            Items = offset == 0
                                ? [SharedMember(publicationId, "customers", "table-customers")]
                                : [SharedMember(publicationId, "orders", "table-orders")],
                            Offset = offset,
                            Limit = limit,
                            Total = 2,
                            HasMore = offset == 0,
                        })),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);
        Assert.IsTrue(viewModel.HasMoreSharedPublicationVersionMembers);
        await viewModel.LoadMoreSharedPublicationVersionMembersCommand.ExecuteAsync(null);

        CollectionAssert.AreEqual(
            new[] { "customers", "orders" },
            viewModel.SelectedSharedPublicationVersionMembers
                .Select(member => member.ExportName)
                .ToArray());
        CollectionAssert.AreEqual(
            new[] { 0, 1 },
            apiClient.SharedPublicationMemberOffsets.ToArray());
        Assert.IsFalse(viewModel.HasMoreSharedPublicationVersionMembers);
    }

    [TestMethod]
    public async Task ChangingSharedPublicationVersionCancelsAndClearsMemberPreview()
    {
        var rowsCompletion = new TaskCompletionSource<ApiResponseEnvelope<TableDataRowsDto>>(
            TaskCreationOptions.RunContinuationsAsynchronously);
        CancellationToken rowsCancellationToken = default;
        var apiClient = new FakeApiClient
        {
            SharedPublicationVersionSummariesResponse =
                ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                    new SharedPublicationSummaryPageDto
                    {
                        Items = [SharedPublicationSummary("pub-2", "daily_report", 2)],
                        Total = 1,
                    }),
            SharedPublicationMembersResponse =
                ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                    new SharedPublicationMemberPageDto
                    {
                        Items = [SharedMember("pub-2", "orders", "table-pub-2")],
                        Total = 1,
                    }),
            TableRefDetailResponse = ApiResponseEnvelope<TableRefDto>.Success(
                TableRef("table-pub-2", "run-1", "node-run-1")),
            TableRowsHandler = (_, cancellationToken) =>
            {
                rowsCancellationToken = cancellationToken;
                return rowsCompletion.Task;
            },
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";
        await viewModel.RefreshSharedPublicationVersionsCommand.ExecuteAsync(null);

        var previewTask = viewModel.SelectedSharedPublicationVersionMembers
            .Single()
            .PreviewCommand
            .ExecuteAsync(null);
        await WaitUntilAsync(() => apiClient.LastTableRowsTableRefId == "table-pub-2");
        viewModel.SelectedSharedPublicationVersion = null;

        Assert.IsTrue(rowsCancellationToken.IsCancellationRequested);
        rowsCompletion.SetResult(
            ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-pub-2",
                    ["value"],
                    [JsonDocument.Parse("""{"value":"late"}""").RootElement.Clone()],
                    rowCount: 1)));
        await previewTask;

        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);
        Assert.IsEmpty(viewModel.DataPreviewWorkbenchRows);
        Assert.IsNull(viewModel.SelectedSharedPublicationVersionMember);
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

        Assert.IsNull(apiClient.LastNodeRunWorkflowRunId);
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
        Assert.AreEqual(
            "Source: full run run-1, node generate, table orders.",
            viewModel.DataPreviewSourceText);
        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual("data_preview.refresh", viewModel.NotificationKey);
        Assert.AreEqual(UiNotificationKind.Success, viewModel.NotificationKind);
        Assert.AreEqual("Loaded 1/1 preview row(s) for orders.", viewModel.NotificationTitle);
        Assert.AreEqual(string.Empty, viewModel.NotificationMessage);
    }

    [TestMethod]
    public async Task LoadSelectedDataPreviewTableLoadsRowsForSelectedTableOption()
    {
        var apiClient = new FakeApiClient
        {
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

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        viewModel.SelectedDataPreviewState = viewModel.DataPreviewStates.Single(state =>
            state.TableType == "runtime_sql_table");
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual(0, apiClient.LastTableRowsOffset);
        Assert.AreEqual(50, apiClient.LastTableRowsLimit);
        Assert.AreEqual("table-1", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        StringAssert.Contains(
            viewModel.DataPreviewSourceTableMetadataText,
            "Runtime SQL table");
        Assert.HasCount(2, viewModel.DataPreviewWorkbenchColumns);
        Assert.AreEqual("row_id", viewModel.DataPreviewWorkbenchColumns[0].Name);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.IsTrue(viewModel.HasDataPreviewWorkbenchColumns);
        Assert.IsTrue(viewModel.HasDataPreviewWorkbenchRows);
        Assert.IsFalse(viewModel.HasDataPreviewWorkbenchError);
        Assert.AreEqual("Loaded 1/1 row(s) for orders.", viewModel.DataPreviewWorkbenchMessage);
        Assert.AreEqual(
            "Source: run run-1, node run node-run-1, table orders, storage RUNTIME_SQL.",
            viewModel.DataPreviewWorkbenchSourceText);
    }

    [TestMethod]
    public async Task DataPreviewTableOptionSelectionDoesNotReplaceLoadedTableUntilLoaded()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                    TableRef("table-2", "run-1", "node-run-1", storageKind: "MEMORY"),
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

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        viewModel.SelectedDataPreviewState = viewModel.DataPreviewStates.Single(state =>
            state.TableType == "runtime_sql_table");
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual(1, apiClient.GetTableRowsCallCount);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());

        viewModel.SelectedDataPreviewState = viewModel.DataPreviewStates.Single(state =>
            state.TableType == "memory_table");

        Assert.AreEqual(1, apiClient.GetTableRowsCallCount);
        Assert.AreEqual("table-2", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());

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

        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual(2, apiClient.GetTableRowsCallCount);
        Assert.AreEqual("table-2", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual("table-2", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchColumns);
        Assert.AreEqual("code", viewModel.DataPreviewWorkbenchColumns[0].Name);
        CollectionAssert.AreEqual(
            new[] { "A" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public async Task DataPreviewWorkbenchSearchFiltersCurrentPageAndCopiesTsv()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id", "name"],
                    [
                        JsonDocument.Parse("""{"row_id":1,"name":"Alice"}""")
                            .RootElement
                            .Clone(),
                        JsonDocument.Parse("""{"row_id":2,"name":"Bob"}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 2)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        viewModel.DataPreviewWorkbenchSearchText = "bob";

        Assert.HasCount(2, viewModel.DataPreviewWorkbenchColumns);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        CollectionAssert.AreEqual(
            new[] { "2", "Bob" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Filtered 1/2 current-page row(s): bob", viewModel.DataPreviewWorkbenchMessage);
        Assert.IsTrue(viewModel.CopyDataPreviewWorkbenchTsvCommand.CanExecute(null));

        viewModel.CopyDataPreviewWorkbenchTsvCommand.Execute(null);

        Assert.AreEqual(
            "row_id\tname\n2\tBob",
            viewModel.DataPreviewWorkbenchClipboardText.Replace("\r\n", "\n", StringComparison.Ordinal));
        Assert.IsTrue(viewModel.HasDataPreviewWorkbenchClipboardText);
    }

    [TestMethod]
    public void DataPreviewWorkbenchParsesPastedTableIntoLocalDraft()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.DataPreviewWorkbenchPasteText = "name\tamount\nAlice\t12\nBob\t34";

        Assert.IsTrue(viewModel.ParseDataPreviewWorkbenchPasteCommand.CanExecute(null));

        viewModel.ParseDataPreviewWorkbenchPasteCommand.Execute(null);

        Assert.IsTrue(viewModel.IsDataPreviewWorkbenchDraft);
        Assert.AreEqual(
            "Source: local temporary draft, not saved yet.",
            viewModel.DataPreviewWorkbenchSourceText);
        Assert.HasCount(2, viewModel.DataPreviewWorkbenchColumns);
        Assert.AreEqual("name", viewModel.DataPreviewWorkbenchColumns[0].Name);
        Assert.HasCount(2, viewModel.DataPreviewWorkbenchRows);
        CollectionAssert.AreEqual(
            new[] { "Alice", "12" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());
        CollectionAssert.AreEqual(
            new[] { "Bob", "34" },
            viewModel.DataPreviewWorkbenchRows[1].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual(
            "Parsed a temporary draft table: 2 row(s), 2 column(s).",
            viewModel.DataPreviewWorkbenchMessage);
        Assert.IsFalse(viewModel.HasDataPreviewWorkbenchError);
    }

    [TestMethod]
    public void DataPreviewWorkbenchTracksCellEditsAndRestoresDraft()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.DataPreviewWorkbenchPasteText = "name\tamount\nAlice\t12";
        viewModel.ParseDataPreviewWorkbenchPasteCommand.Execute(null);

        viewModel.DataPreviewWorkbenchRows[0].Cells[1].Text = "99";

        Assert.IsTrue(viewModel.IsDataPreviewWorkbenchDirty);
        Assert.AreEqual("Unsaved", viewModel.DataPreviewWorkbenchDirtyStateText);
        Assert.IsTrue(viewModel.RestoreDataPreviewWorkbenchDraftCommand.CanExecute(null));
        Assert.IsFalse(viewModel.SaveDataPreviewWorkbenchAsCommand.CanExecute(null));
        Assert.AreEqual(
            "Local drafts need a backend save-as capable target table first; this stage does not write the original table.",
            viewModel.DataPreviewWorkbenchSavePolicyText);

        viewModel.RestoreDataPreviewWorkbenchDraftCommand.Execute(null);

        Assert.IsFalse(viewModel.IsDataPreviewWorkbenchDirty);
        Assert.AreEqual("Unmodified", viewModel.DataPreviewWorkbenchDirtyStateText);
        Assert.AreEqual("12", viewModel.DataPreviewWorkbenchRows[0].Cells[1].Text);
        Assert.AreEqual(
            "Restored to the last loaded or parsed table.",
            viewModel.DataPreviewWorkbenchMessage);
    }

    [TestMethod]
    public async Task DataPreviewWorkbenchSaveAsRequiresBackendCapability()
    {
        var readOnlyApiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef(
                        "table-1",
                        "run-1",
                        "node-run-1",
                        capabilities: ["READ"]),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["name", "amount"],
                    [
                        JsonDocument.Parse("""{"name":"Alice","amount":12}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(readOnlyApiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);
        viewModel.DataPreviewWorkbenchRows[0].Cells[1].Text = "99";

        Assert.IsFalse(viewModel.CanSaveDataPreviewWorkbenchAsDraft);
        Assert.IsFalse(viewModel.SaveDataPreviewWorkbenchAsCommand.CanExecute(null));
        Assert.AreEqual(
            "Current table is not saveable: storage RUNTIME_SQL, capabilities READ; backend must declare SAVE_AS.",
            viewModel.DataPreviewWorkbenchSavePolicyText);

        var saveableApiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef(
                        "table-2",
                        "run-1",
                        "node-run-1",
                        capabilities: ["READ", "SAVE_AS"]),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-2",
                    ["name", "amount"],
                    [
                        JsonDocument.Parse("""{"name":"Alice","amount":12}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        viewModel = CreateViewModel(saveableApiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);
        viewModel.DataPreviewWorkbenchRows[0].Cells[1].Text = "99";

        Assert.IsTrue(viewModel.CanSaveDataPreviewWorkbenchAsDraft);
        Assert.IsTrue(viewModel.SaveDataPreviewWorkbenchAsCommand.CanExecute(null));
        Assert.AreEqual(
            "Current table supports controlled save-as: storage RUNTIME_SQL, capabilities READ, SAVE_AS.",
            viewModel.DataPreviewWorkbenchSavePolicyText);

        viewModel.SaveDataPreviewWorkbenchAsCommand.Execute(null);

        Assert.AreEqual(
            "The controlled backend save API is not implemented yet; this stage only confirms capability declaration and button boundaries.",
            viewModel.DataPreviewWorkbenchMessage);
    }

    [TestMethod]
    public void DataPreviewWorkbenchParsesQuotedCsvCells()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.DataPreviewWorkbenchPasteText = "name,note\nAlice,\"a,b\"";

        viewModel.ParseDataPreviewWorkbenchPasteCommand.Execute(null);

        Assert.HasCount(2, viewModel.DataPreviewWorkbenchColumns);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        CollectionAssert.AreEqual(
            new[] { "Alice", "a,b" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());
    }

    [TestMethod]
    public void DataPreviewWorkbenchRejectsPastedHeaderOnlyTable()
    {
        var viewModel = CreateViewModel(new FakeApiClient());
        viewModel.DataPreviewWorkbenchPasteText = "name\tamount";

        viewModel.ParseDataPreviewWorkbenchPasteCommand.Execute(null);

        Assert.IsFalse(viewModel.IsDataPreviewWorkbenchDraft);
        Assert.IsTrue(viewModel.HasDataPreviewWorkbenchError);
        Assert.AreEqual("Pasted table parse failed.", viewModel.DataPreviewWorkbenchMessage);
        Assert.AreEqual(
            "Paste at least one header row and one data row.",
            viewModel.DataPreviewWorkbenchErrorMessage);
    }

    [TestMethod]
    public async Task DataPreviewWorkbenchPagingUsesOffsetsAndUpdatesPageState()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef("table-1", "run-1", "node-run-1"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id"],
                    [
                        JsonDocument.Parse("""{"row_id":1}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 120,
                    hasMore: true)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual("1-1 / 120", viewModel.DataPreviewWorkbenchPageText);
        Assert.IsFalse(viewModel.LoadPreviousDataPreviewWorkbenchPageCommand.CanExecute(null));
        Assert.IsTrue(viewModel.LoadNextDataPreviewWorkbenchPageCommand.CanExecute(null));

        apiClient.TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
            TableRows(
                "table-1",
                ["row_id"],
                [
                    JsonDocument.Parse("""{"row_id":51}""")
                        .RootElement
                        .Clone(),
                ],
                rowCount: 120,
                offset: 50,
                hasMore: true));

        await viewModel.LoadNextDataPreviewWorkbenchPageCommand.ExecuteAsync(null);

        Assert.AreEqual(50, apiClient.LastTableRowsOffset);
        Assert.AreEqual("51-51 / 120", viewModel.DataPreviewWorkbenchPageText);
        Assert.IsTrue(viewModel.LoadPreviousDataPreviewWorkbenchPageCommand.CanExecute(null));

        apiClient.TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
            TableRows(
                "table-1",
                ["row_id"],
                [
                    JsonDocument.Parse("""{"row_id":1}""")
                        .RootElement
                        .Clone(),
                ],
                rowCount: 120,
                hasMore: true));

        await viewModel.LoadPreviousDataPreviewWorkbenchPageCommand.ExecuteAsync(null);

        Assert.AreEqual(0, apiClient.LastTableRowsOffset);
        Assert.AreEqual("1-1 / 120", viewModel.DataPreviewWorkbenchPageText);
    }

    [TestMethod]
    public async Task ShowDataPreviewDetailsSelectsDataPreviewPageAndLoadsCurrentTable()
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
                    ["row_id"],
                    [
                        JsonDocument.Parse("""{"row_id":1}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");
        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.IsTrue(viewModel.ShowDataPreviewDetailsCommand.CanExecute(null));

        await viewModel.ShowDataPreviewDetailsCommand.ExecuteAsync(null);

        Assert.AreEqual(ShellPageKey.DataPreview, viewModel.SelectedShellPageKey);
        Assert.AreEqual(ShellPageContentKey.DataPreview, viewModel.SelectedShellPageContentKey);
        Assert.AreEqual("table-1", viewModel.SelectedDataPreviewTableRef?.TableRefId);
        Assert.AreEqual(
            "run-1:node-run-1:runtime_sql_table",
            viewModel.SelectedDataPreviewState?.StateKey);
        Assert.AreEqual("table-1", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchColumns);
        Assert.AreEqual("row_id", viewModel.DataPreviewWorkbenchColumns[0].Name);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        Assert.AreEqual("1", viewModel.DataPreviewWorkbenchRows[0].Cells[0].Text);
        Assert.AreEqual("Loaded 1/1 row(s) for orders.", viewModel.DataPreviewWorkbenchMessage);
    }

    [TestMethod]
    public async Task ShowDataPreviewDetailsSelectsMatchingStateAndTableFromExistingRefs()
    {
        var apiClient = new FakeApiClient
        {
            NodeRunsResponse = ApiResponseEnvelope<List<NodeRunDto>>.Success(
                new List<NodeRunDto>
                {
                    NodeRun("node-run-other", "run-1", "other"),
                    NodeRun("node-run-target", "run-1", "target"),
                }),
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
                new List<TableRefDto>
                {
                    TableRef(
                        "table-other",
                        "run-1",
                        "node-run-other",
                        sourceNodeInstanceId: "other"),
                    TableRef(
                        "table-target",
                        "run-1",
                        "node-run-target",
                        sourceNodeInstanceId: "target"),
                    TableRef(
                        "table-side",
                        "run-1",
                        "node-run-target",
                        storageKind: "MEMORY",
                        sourceNodeInstanceId: "target"),
                }),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-target",
                    ["row_id"],
                    [
                        JsonDocument.Parse("""{"row_id":7}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("target");

        await viewModel.RefreshTableRefsCommand.ExecuteAsync(null);
        Assert.AreEqual(
            "run-1:node-run-target:memory_table",
            viewModel.SelectedDataPreviewState?.StateKey);

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);
        await viewModel.ShowDataPreviewDetailsCommand.ExecuteAsync(null);

        Assert.AreEqual(ShellPageKey.DataPreview, viewModel.SelectedShellPageKey);
        Assert.AreEqual(
            "run-1:node-run-target:runtime_sql_table",
            viewModel.SelectedDataPreviewState?.StateKey);
        Assert.HasCount(1, viewModel.DataPreviewTableOptions);
        CollectionAssert.AreEqual(
            new[] { "table-target" },
            viewModel.DataPreviewTableOptions.Select(tableRef => tableRef.TableRefId).ToArray());
        Assert.AreEqual("table-target", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.AreEqual("table-target", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        Assert.AreEqual("table-target", apiClient.LastTableRowsTableRefId);
        Assert.HasCount(1, viewModel.DataPreviewWorkbenchRows);
        Assert.AreEqual("7", viewModel.DataPreviewWorkbenchRows[0].Cells[0].Text);
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
    public async Task HistoricalNodePreviewRefreshDoesNotInitializeIndependentWorkbench()
    {
        var apiClient = new FakeApiClient
        {
            TableRefsResponse = ApiResponseEnvelope<List<TableRefDto>>.Success(
            [
                TableRef("table-1", "run-1", "node-run-1"),
            ]),
            TableRowsResponse = ApiResponseEnvelope<TableDataRowsDto>.Success(
                TableRows(
                    "table-1",
                    ["row_id"],
                    [
                        JsonDocument.Parse("""{"row_id":1}""")
                            .RootElement
                            .Clone(),
                    ],
                    rowCount: 1)),
        };
        var viewModel = CreateViewModel(apiClient);
        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);

        Assert.HasCount(1, viewModel.DataPreviewRows);
        Assert.IsEmpty(viewModel.DataPreviewStates);
        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);
        Assert.IsEmpty(viewModel.DataPreviewWorkbenchRows);
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
        Assert.IsTrue(viewModel.ShowDataPreviewDetailsCommand.CanExecute(null));

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-2", "wf-1"));

        Assert.IsEmpty(viewModel.NodeRuns);
        Assert.IsEmpty(viewModel.TableRefs);
        Assert.IsTrue(viewModel.HasDataPreviewColumns);
        Assert.IsTrue(viewModel.HasDataPreviewRows);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Select a run and workflow node, then refresh data preview.", viewModel.DataPreviewMessage);
        Assert.AreEqual(
            "Source: full run run-1, node generate, table orders.",
            viewModel.DataPreviewSourceText);
        Assert.IsTrue(viewModel.ShowDataPreviewDetailsCommand.CanExecute(null));

        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("filter");

        Assert.IsTrue(viewModel.HasDataPreviewColumns);
        Assert.IsTrue(viewModel.HasDataPreviewRows);
        Assert.HasCount(1, viewModel.DataPreviewRows);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewRows[0].Cells.Select(cell => cell.Text).ToArray());
        Assert.AreEqual("Select a run and workflow node, then refresh data preview.", viewModel.DataPreviewMessage);
        Assert.AreEqual(
            "Source: full run run-1, node generate, table orders.",
            viewModel.DataPreviewSourceText);
        Assert.IsTrue(viewModel.ShowDataPreviewDetailsCommand.CanExecute(null));
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
        Assert.AreEqual(
            "No data preview loaded yet.",
            viewModel.DataPreviewSourceText);
        Assert.IsFalse(viewModel.HasDataPreviewError);
        Assert.IsTrue(viewModel.IsNotificationOpen);
        Assert.AreEqual("data_preview.refresh", viewModel.NotificationKey);
        Assert.AreEqual(UiNotificationKind.Warning, viewModel.NotificationKind);
        Assert.AreEqual("Node generate has no readable output table.", viewModel.NotificationTitle);
        Assert.AreEqual(string.Empty, viewModel.NotificationMessage);
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
        Assert.AreEqual(
            "Source: full run run-1, node generate, table orders.",
            viewModel.DataPreviewSourceText);
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
        Assert.AreEqual(
            "Source: full run run-1, node generate, table orders.",
            viewModel.DataPreviewSourceText);
        Assert.IsFalse(viewModel.HasDataPreviewError);
    }

    [TestMethod]
    public void DataRefreshCommandsRequireEngineActionsAndRequiredSelection()
    {
        var viewModel = CreateViewModel(new FakeApiClient());

        Assert.IsFalse(viewModel.RefreshTableRefsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.CanExecute(null));
        Assert.IsFalse(viewModel.LoadSelectedDataPreviewTableCommand.CanExecute(null));
        Assert.IsFalse(viewModel.ShowDataPreviewDetailsCommand.CanExecute(null));
        Assert.IsFalse(viewModel.RefreshSharedPublicationVersionsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshSharedPublicationsCommand.CanExecute(null));

        viewModel.SelectedRun = new WorkflowRunListItemViewModel(Run("run-1", "wf-1"));
        viewModel.SelectedWorkflowDefinitionNode = WorkflowNode("generate");
        viewModel.SelectedDataPreviewTableOption = new TableRefListItemViewModel(
            TableRef("table-1", "run-1", "node-run-1"));
        viewModel.SharedPublicationVersionShareNameFilter = "daily_report";

        Assert.IsTrue(viewModel.RefreshTableRefsCommand.CanExecute(null));
        Assert.IsTrue(viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.CanExecute(null));
        Assert.IsTrue(viewModel.LoadSelectedDataPreviewTableCommand.CanExecute(null));
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

    private static NodeRunDto NodeRun(string nodeRunId, string workflowRunId)
    {
        return new NodeRunDto
        {
            NodeRunId = nodeRunId,
            WorkflowRunId = workflowRunId,
            NodeInstanceId = "node",
            NodeType = "FilterRowsNode",
            Status = "SUCCEEDED",
        };
    }

    private static RunTableDirectoryItemDto TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId,
        string storageKind = "RUNTIME_SQL",
        string[]? capabilities = null,
        string sourceNodeInstanceId = "generate",
        string? tableType = null,
        bool? canReadRows = null,
        string outputSlot = "out")
    {
        var resolvedCapabilities = capabilities ?? ["WRITE", "READ"];
        var resolvedCanReadRows = canReadRows ?? resolvedCapabilities.Contains("READ");
        return new RunTableDirectoryItemDto
        {
            TableRefId = tableRefId,
            WorkflowRunId = workflowRunId,
            NodeRunId = nodeRunId,
            SourceNodeRunId = nodeRunId,
            SourceNodeInstanceId = sourceNodeInstanceId,
            Role = "OUTPUT",
            StorageKind = storageKind,
            Scope = "WORKFLOW_SCOPE",
            Mutability = "IMMUTABLE",
            ProviderId = "runtime",
            LogicalTableId = "orders",
            OutputSlot = outputSlot,
            ResultBindings =
            [
                new ResultBindingSummaryDto
                {
                    NodeRunId = nodeRunId,
                    NodeInstanceId = sourceNodeInstanceId,
                    OutputSlots = [outputSlot],
                },
            ],
            TableType = tableType ?? storageKind switch
            {
                "MEMORY" => "memory_table",
                "EXTERNAL_SQL" => "external_sql_table",
                _ => "runtime_sql_table",
            },
            PreviewPersistence = storageKind switch
            {
                "MEMORY" => "memory_only",
                "EXTERNAL_SQL" => "external_source",
                _ => "workflow_run_sql",
            },
            CanReadRows = resolvedCanReadRows,
            SupportsPagedRows = resolvedCanReadRows,
            Schema = JsonDocument.Parse("""{"fields":[]}""").RootElement.Clone(),
            SchemaFingerprint = "schema-1",
            Version = 2,
            Capabilities = resolvedCapabilities,
            LifecycleStatus = "PUBLISHED",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
        };
    }

    private static TableDataRowsDto TableRows(
        string tableRefId,
        string[] columns,
        JsonElement[] rows,
        long rowCount,
        int offset = 0,
        bool hasMore = false)
    {
        return new TableDataRowsDto
        {
            TableRefId = tableRefId,
            Offset = offset,
            Limit = 50,
            RowCount = rowCount,
            Columns = columns,
            Rows = rows,
            HasMore = hasMore,
        };
    }

    private static ApiResponseEnvelope<RunTableDirectoryPageDto> DirectoryPage(
        RunTableDirectoryItemDto tableRef,
        int offset,
        int limit)
    {
        return ApiResponseEnvelope<RunTableDirectoryPageDto>.Success(
            new RunTableDirectoryPageDto
            {
                Items = offset == 0 ? [tableRef] : [],
                Offset = offset,
                Limit = limit,
                Total = 1,
                HasMore = false,
            });
    }

    private static ApiResponseEnvelope<TableDataRowsDto> TableRowsResponse(
        string tableRefId,
        string value)
    {
        return ApiResponseEnvelope<TableDataRowsDto>.Success(
            TableRows(
                tableRefId,
                ["value"],
                [JsonDocument.Parse($$"""{"value":"{{value}}"}""").RootElement.Clone()],
                rowCount: 1));
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

    private static SharedPublicationSummaryDto SharedPublicationSummary(
        string publicationId,
        string shareName,
        int publicationVersion)
    {
        return new SharedPublicationSummaryDto
        {
            PublicationId = publicationId,
            ShareName = shareName,
            PublicationVersion = publicationVersion,
            ProducerWorkflowId = "wf-1",
            ProducerRunId = "run-1",
            Status = "PUBLISHED",
            CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            MemberCount = 1,
            IsLatestPublished = publicationVersion == 2,
        };
    }

    private static SharedPublicationMemberDto SharedMember(
        string publicationId,
        string exportName,
        string tableRefId)
    {
        return new SharedPublicationMemberDto
        {
            PublicationId = publicationId,
            ExportName = exportName,
            TableRefId = tableRefId,
            ExactTableVersion = 2,
            TableRefLifecycleStatus = "PUBLISHED",
            TableRefStorageKind = "RUNTIME_SQL",
            LogicalTableId = exportName,
            CanReadRows = true,
        };
    }

    private static SharedPublicationCatalogEntryDto SharedPublicationCatalogEntry(
        string shareName,
        int latestPublishedVersion)
    {
        return new SharedPublicationCatalogEntryDto
        {
            ShareName = shareName,
            LatestPublishedVersion = latestPublishedVersion,
            PublishedVersionCount = latestPublishedVersion,
            LatestMemberCount = 1,
            LatestCreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
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

        Assert.Fail("Timed out waiting for asynchronous data state.");
    }

    private sealed class FakeApiClient : IEngineHostApiClient
    {
        public ApiResponseEnvelope<List<TableRefDto>> TableRefsResponse { get; set; } =
            ApiResponseEnvelope<List<TableRefDto>>.Success(new List<TableRefDto>());

        public ApiResponseEnvelope<TableRefDto> TableRefDetailResponse { get; set; } =
            ApiResponseEnvelope<TableRefDto>.Failure(
                "NOT_CONFIGURED",
                "No table ref detail response configured.");

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationsResponse { get; set; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

        public ApiResponseEnvelope<SharedPublicationCatalogPageDto> SharedPublicationCatalogResponse { get; set; } =
            ApiResponseEnvelope<SharedPublicationCatalogPageDto>.Success(
                new SharedPublicationCatalogPageDto());

        public ApiResponseEnvelope<List<SharedPublicationDto>> SharedPublicationVersionsResponse { get; set; } =
            ApiResponseEnvelope<List<SharedPublicationDto>>.Success(new List<SharedPublicationDto>());

        public ApiResponseEnvelope<SharedPublicationSummaryPageDto> SharedPublicationVersionSummariesResponse { get; set; } =
            ApiResponseEnvelope<SharedPublicationSummaryPageDto>.Success(
                new SharedPublicationSummaryPageDto());

        public ApiResponseEnvelope<SharedPublicationMemberPageDto> SharedPublicationMembersResponse { get; set; } =
            ApiResponseEnvelope<SharedPublicationMemberPageDto>.Success(
                new SharedPublicationMemberPageDto());

        public ApiResponseEnvelope<SharedPublicationCleanupPreviewDto> SharedPublicationCleanupPreviewResponse { get; set; } =
            ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>.Success(
                new SharedPublicationCleanupPreviewDto
                {
                    Status = "PUBLISHED",
                });

        public ApiResponseEnvelope<SharedPublicationCleanupResultDto> SharedPublicationCleanupResponse { get; set; } =
            ApiResponseEnvelope<SharedPublicationCleanupResultDto>.Success(
                new SharedPublicationCleanupResultDto
                {
                    Outcome = "BLOCKED",
                    Status = "PUBLISHED",
                });

        public ApiResponseEnvelope<List<NodeRunDto>> NodeRunsResponse { get; set; } =
            ApiResponseEnvelope<List<NodeRunDto>>.Success(new List<NodeRunDto>());

        public ApiResponseEnvelope<TableDataRowsDto> TableRowsResponse { get; set; } =
            ApiResponseEnvelope<TableDataRowsDto>.Success(
                new TableDataRowsDto());

        public Func<
            string,
            int,
            int,
            CancellationToken,
            Task<ApiResponseEnvelope<RunTableDirectoryPageDto>>>?
            RunTableDirectoryHandler
        { get; set; }

        public Func<
            string,
            CancellationToken,
            Task<ApiResponseEnvelope<TableDataRowsDto>>>?
            TableRowsHandler
        { get; set; }

        public Func<
            string,
            CancellationToken,
            Task<ApiResponseEnvelope<TableRefDto>>>?
            TableRefDetailHandler
        { get; set; }

        public Func<
            string,
            int,
            int,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>>>?
            SharedPublicationMembersHandler
        { get; set; }

        public Func<
            string,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>>>?
            SharedPublicationCleanupPreviewHandler
        { get; set; }

        public Func<
            string,
            CancellationToken,
            Task<ApiResponseEnvelope<SharedPublicationCleanupResultDto>>>?
            SharedPublicationCleanupHandler
        { get; set; }

        public string? LastNodeRunWorkflowRunId { get; private set; }

        public string? LastTableRefWorkflowRunId { get; private set; }

        public string? LastTableRefNodeRunId { get; private set; }

        public string? LastEventWorkflowRunId { get; private set; }

        public string? LastEventNodeRunId { get; private set; }

        public string? LastTableRowsTableRefId { get; private set; }

        public string? LastTableRefDetailId { get; private set; }

        public int GetTableRowsCallCount { get; private set; }

        public int LastTableRowsOffset { get; private set; }

        public int LastTableRowsLimit { get; private set; }

        public int ListSharedPublicationsCallCount { get; private set; }

        public int ListSharedPublicationCatalogCallCount { get; private set; }

        public string? LastSharedPublicationShareName { get; private set; }

        public string? LastSharedPublicationCatalogQuery { get; private set; }

        public int LastSharedPublicationLimit { get; private set; }

        public string? LastSharedPublicationVersionsShareName { get; private set; }

        public int LastSharedPublicationVersionsLimit { get; private set; }

        public string? LastSharedPublicationMembersPublicationId { get; private set; }

        public string? LastSharedPublicationCleanupPreviewPublicationId { get; private set; }

        public string? LastSharedPublicationCleanupPublicationId { get; private set; }

        public int SharedPublicationCleanupPreviewCallCount { get; private set; }

        public int SharedPublicationCleanupCallCount { get; private set; }

        public List<int> SharedPublicationMemberOffsets { get; } = [];

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
            LastTableRefWorkflowRunId = workflowRunId;
            return Task.FromResult(TableRefsResponse);
        }

        public Task<ApiResponseEnvelope<TableRefDto>> GetTableRefAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            CancellationToken cancellationToken = default)
        {
            LastTableRefDetailId = tableRefId;
            return TableRefDetailHandler?.Invoke(tableRefId, cancellationToken)
                ?? Task.FromResult(TableRefDetailResponse);
        }

        public async Task<ApiResponseEnvelope<RunTableDirectoryPageDto>> ListRunTableDirectoryAsync(
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
            LastTableRefWorkflowRunId = workflowRunId;
            LastTableRefNodeRunId = nodeRunId;
            if (RunTableDirectoryHandler is not null)
            {
                return await RunTableDirectoryHandler(
                    workflowRunId,
                    offset,
                    limit,
                    cancellationToken);
            }

            if (!TableRefsResponse.Ok || TableRefsResponse.Data is null)
            {
                return new ApiResponseEnvelope<RunTableDirectoryPageDto>
                {
                    Ok = false,
                    Error = TableRefsResponse.Error,
                    RequestId = TableRefsResponse.RequestId,
                };
            }

            var filtered = TableRefsResponse.Data
                .Select(RunTableDirectoryItemDto.FromTableRef)
                .Where(item => nodeRunId is null || item.NodeRunId == nodeRunId)
                .Where(item => tableType is null || item.TableType == tableType)
                .Where(item => logicalTableId is null || item.LogicalTableId == logicalTableId)
                .ToArray();
            var items = filtered.Skip(offset).Take(limit).ToArray();
            return ApiResponseEnvelope<RunTableDirectoryPageDto>.Success(
                    new RunTableDirectoryPageDto
                    {
                        Items = items,
                        Offset = offset,
                        Limit = limit,
                        Total = filtered.Length,
                        HasMore = offset + items.Length < filtered.Length,
                    });
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
        public async Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
            EngineHostConnectionSettings settings,
            string tableRefId,
            int offset = 0,
            int limit = 50,
            IReadOnlyCollection<string>? columns = null,
            IReadOnlyCollection<string>? orderBy = null,
            CancellationToken cancellationToken = default)
        {
            GetTableRowsCallCount++;
            LastTableRowsTableRefId = tableRefId;
            LastTableRowsOffset = offset;
            LastTableRowsLimit = limit;
            if (TableRowsHandler is not null)
            {
                return await TableRowsHandler(tableRefId, cancellationToken);
            }

            return TableRowsResponse;
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

        public Task<ApiResponseEnvelope<List<RuntimeEventDto>>> ListEventsAsync(
            EngineHostConnectionSettings settings,
            long? afterSequenceNumber = null,
            string? workflowRunId = null,
            string? nodeRunId = null,
            string? eventType = null,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            LastEventWorkflowRunId = workflowRunId;
            LastEventNodeRunId = nodeRunId;
            return Task.FromResult(
                ApiResponseEnvelope<List<RuntimeEventDto>>.Success([]));
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

        public Task<ApiResponseEnvelope<SharedPublicationCatalogPageDto>> ListSharedPublicationCatalogAsync(
            EngineHostConnectionSettings settings,
            string? query = null,
            int offset = 0,
            int limit = 50,
            CancellationToken cancellationToken = default)
        {
            ListSharedPublicationCatalogCallCount++;
            LastSharedPublicationCatalogQuery = query;
            LastSharedPublicationLimit = limit;
            return Task.FromResult(SharedPublicationCatalogResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationSummaryPageDto>> ListSharedPublicationVersionSummariesAsync(
            EngineHostConnectionSettings settings,
            string shareName,
            int offset = 0,
            int limit = 50,
            CancellationToken cancellationToken = default)
        {
            LastSharedPublicationVersionsShareName = shareName;
            LastSharedPublicationVersionsLimit = limit;
            return Task.FromResult(SharedPublicationVersionSummariesResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationMemberPageDto>> ListSharedPublicationMembersAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            int offset = 0,
            int limit = 100,
            CancellationToken cancellationToken = default)
        {
            LastSharedPublicationMembersPublicationId = publicationId;
            SharedPublicationMemberOffsets.Add(offset);
            return SharedPublicationMembersHandler?.Invoke(
                publicationId,
                offset,
                limit,
                cancellationToken)
                ?? Task.FromResult(SharedPublicationMembersResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationCleanupPreviewDto>> GetSharedPublicationCleanupPreviewAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            CancellationToken cancellationToken = default)
        {
            SharedPublicationCleanupPreviewCallCount++;
            LastSharedPublicationCleanupPreviewPublicationId = publicationId;
            return SharedPublicationCleanupPreviewHandler?.Invoke(
                publicationId,
                cancellationToken)
                ?? Task.FromResult(SharedPublicationCleanupPreviewResponse);
        }

        public Task<ApiResponseEnvelope<SharedPublicationCleanupResultDto>> CleanupSharedPublicationAsync(
            EngineHostConnectionSettings settings,
            string publicationId,
            CancellationToken cancellationToken = default)
        {
            SharedPublicationCleanupCallCount++;
            LastSharedPublicationCleanupPublicationId = publicationId;
            return SharedPublicationCleanupHandler?.Invoke(
                publicationId,
                cancellationToken)
                ?? Task.FromResult(SharedPublicationCleanupResponse);
        }
    }
}
