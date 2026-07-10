using System;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.ViewModels;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class DataPreviewStateListItemViewModelTests
{
    [TestMethod]
    public void FromTableRefsGroupsByBackendTableTypeInStableOrder()
    {
        var table1 = TableRef("table-1", "run-1", "node-run-1");
        var table2 = TableRef(
            "table-2",
            "run-1",
            "node-run-1",
            storageKind: "MEMORY",
            tableType: "memory_table");
        var table3 = TableRef("table-3", "run-1", "node-run-2");
        var table4 = TableRef("table-4", "run-2", "node-run-1");

        var states = DataPreviewStateListItemViewModel.FromTableRefs(
            [table1, table2, table3, table4]);

        Assert.HasCount(4, states);
        Assert.AreEqual("run-1:node-run-1:memory_table", states[0].StateKey);
        Assert.AreEqual("run-1:node-run-1:runtime_sql_table", states[1].StateKey);
        Assert.AreEqual("run-1:node-run-2:runtime_sql_table", states[2].StateKey);
        Assert.AreEqual("run-2:node-run-1:runtime_sql_table", states[3].StateKey);
        CollectionAssert.AreEqual(
            new[] { "table-2" },
            states[0].TableRefs.Select(tableRef => tableRef.TableRefId).ToArray());
        CollectionAssert.AreEqual(
            new[] { "table-1" },
            states[1].TableRefs.Select(tableRef => tableRef.TableRefId).ToArray());
    }

    [TestMethod]
    public void StateExposesSummaryAndReadableTableBoundary()
    {
        var state = new DataPreviewStateListItemViewModel(
            "run-1",
            "node-run-1",
            "runtime_sql_table",
            [
                TableRef("table-1", "run-1", "node-run-1", storageKind: "RUNTIME_SQL"),
                TableRef("table-3", "run-1", "node-run-1", storageKind: "RUNTIME_SQL", capabilities: ["READ"]),
            ]);

        Assert.AreEqual("node-run-1 | Runtime SQL table", state.DisplayText);
        Assert.AreEqual(2, state.TableCount);
        Assert.AreEqual("2 table(s)", state.TableCountText);
        Assert.AreEqual(2, state.ReadableTableCount);
        Assert.IsTrue(state.HasReadableTables);
        Assert.AreEqual("RUNTIME_SQL", state.StorageKindsText);
        Assert.AreEqual("2 table(s) · 2 readable · RUNTIME_SQL", state.SummaryText);
    }

    [TestMethod]
    public void ConstructorRejectsMixedNodeRunTableRefs()
    {
        var exception = Assert.ThrowsExactly<ArgumentException>(() =>
            new DataPreviewStateListItemViewModel(
                "run-1",
                "node-run-1",
                "runtime_sql_table",
                [
                    TableRef("table-1", "run-1", "node-run-1"),
                    TableRef("table-2", "run-1", "node-run-2"),
                ]));

        StringAssert.Contains(
            exception.Message,
            "same workflow run, node run, and table type");
    }

    private static TableRefListItemViewModel TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId,
        string storageKind = "RUNTIME_SQL",
        string[]? capabilities = null,
        string tableType = "runtime_sql_table")
    {
        return new TableRefListItemViewModel(
            new TableRefDto
            {
                TableRefId = tableRefId,
                WorkflowRunId = workflowRunId,
                NodeRunId = nodeRunId,
                Role = "OUTPUT",
                StorageKind = storageKind,
                Scope = "WORKFLOW_SCOPE",
                Mutability = "IMMUTABLE",
                ProviderId = "runtime",
                LogicalTableId = tableRefId,
                TableType = tableType,
                PreviewPersistence = storageKind == "MEMORY"
                    ? "memory_only"
                    : "workflow_run_sql",
                CanReadRows = capabilities?.Contains("READ") ?? true,
                SupportsPagedRows = capabilities?.Contains("READ") ?? true,
                Version = 1,
                Capabilities = capabilities ?? ["READ"],
                LifecycleStatus = "PUBLISHED",
                CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            });
    }
}
