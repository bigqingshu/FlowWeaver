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

        Assert.HasCount(2, viewModel.DataPreviewStates);
        Assert.AreEqual("run-1:node-run-1", viewModel.DataPreviewStates[0].StateKey);
        Assert.AreEqual("run-1:node-run-2", viewModel.DataPreviewStates[1].StateKey);
        Assert.AreEqual("run-1:node-run-1", viewModel.SelectedDataPreviewState?.StateKey);
        Assert.HasCount(2, viewModel.DataPreviewTableOptions);
        CollectionAssert.AreEqual(
            new[] { "table-1", "table-2" },
            viewModel.DataPreviewTableOptions.Select(tableRef => tableRef.TableRefId).ToArray());
        Assert.AreEqual("table-1", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);

        viewModel.SelectedDataPreviewState = viewModel.DataPreviewStates[1];

        Assert.HasCount(1, viewModel.DataPreviewTableOptions);
        Assert.AreEqual("table-3", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.IsNull(viewModel.LoadedDataPreviewTableRef);
        Assert.IsNull(apiClient.LastTableRowsTableRefId);
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
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual("table-1", apiClient.LastTableRowsTableRefId);
        Assert.AreEqual(0, apiClient.LastTableRowsOffset);
        Assert.AreEqual(50, apiClient.LastTableRowsLimit);
        Assert.AreEqual("table-1", viewModel.SelectedDataPreviewTableOption?.TableRefId);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
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
        await viewModel.LoadSelectedDataPreviewTableCommand.ExecuteAsync(null);

        Assert.AreEqual(1, apiClient.GetTableRowsCallCount);
        Assert.AreEqual("table-1", viewModel.LoadedDataPreviewTableRef?.TableRefId);
        CollectionAssert.AreEqual(
            new[] { "1", "12.5" },
            viewModel.DataPreviewWorkbenchRows[0].Cells.Select(cell => cell.Text).ToArray());

        viewModel.SelectedDataPreviewTableOption = viewModel.DataPreviewTableOptions[1];

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
        Assert.AreEqual("run-1:node-run-1", viewModel.SelectedDataPreviewState?.StateKey);
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
                    TableRef("table-other", "run-1", "node-run-other"),
                    TableRef("table-target", "run-1", "node-run-target"),
                    TableRef("table-side", "run-1", "node-run-target", storageKind: "MEMORY"),
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
        Assert.AreEqual("run-1:node-run-other", viewModel.SelectedDataPreviewState?.StateKey);

        await viewModel.RefreshSelectedWorkflowNodeDataPreviewCommand.ExecuteAsync(null);
        await viewModel.ShowDataPreviewDetailsCommand.ExecuteAsync(null);

        Assert.AreEqual(ShellPageKey.DataPreview, viewModel.SelectedShellPageKey);
        Assert.AreEqual("run-1:node-run-target", viewModel.SelectedDataPreviewState?.StateKey);
        Assert.HasCount(2, viewModel.DataPreviewTableOptions);
        CollectionAssert.AreEqual(
            new[] { "table-target", "table-side" },
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

    private static TableRefDto TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId,
        string storageKind = "RUNTIME_SQL",
        string[]? capabilities = null)
    {
        return new TableRefDto
        {
            TableRefId = tableRefId,
            WorkflowRunId = workflowRunId,
            NodeRunId = nodeRunId,
            Role = "OUTPUT",
            StorageKind = storageKind,
            Scope = "WORKFLOW_SCOPE",
            Mutability = "IMMUTABLE",
            ProviderId = "runtime",
            LogicalTableId = "orders",
            Schema = JsonDocument.Parse("""{"fields":[]}""").RootElement.Clone(),
            SchemaFingerprint = "schema-1",
            Version = 2,
            Capabilities = capabilities ?? ["WRITE", "READ"],
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

        public int GetTableRowsCallCount { get; private set; }

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
        public Task<ApiResponseEnvelope<TableDataRowsDto>> GetTableDataRowsAsync(
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
