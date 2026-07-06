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
    public void FromTableRefsGroupsByWorkflowRunAndNodeRunInStableOrder()
    {
        var table1 = TableRef("table-1", "run-1", "node-run-1");
        var table2 = TableRef("table-2", "run-1", "node-run-1", storageKind: "MEMORY");
        var table3 = TableRef("table-3", "run-1", "node-run-2");
        var table4 = TableRef("table-4", "run-2", "node-run-1");

        var states = DataPreviewStateListItemViewModel.FromTableRefs(
            [table1, table2, table3, table4]);

        Assert.HasCount(3, states);
        Assert.AreEqual("run-1:node-run-1", states[0].StateKey);
        Assert.AreEqual("run-1:node-run-2", states[1].StateKey);
        Assert.AreEqual("run-2:node-run-1", states[2].StateKey);
        CollectionAssert.AreEqual(
            new[] { "table-1", "table-2" },
            states[0].TableRefs.Select(tableRef => tableRef.TableRefId).ToArray());
        CollectionAssert.AreEqual(
            new[] { "table-3" },
            states[1].TableRefs.Select(tableRef => tableRef.TableRefId).ToArray());
    }

    [TestMethod]
    public void StateExposesSummaryAndReadableTableBoundary()
    {
        var state = new DataPreviewStateListItemViewModel(
            "run-1",
            "node-run-1",
            [
                TableRef("table-1", "run-1", "node-run-1", storageKind: "RUNTIME_SQL"),
                TableRef("table-2", "run-1", "node-run-1", storageKind: "MEMORY", capabilities: ["WRITE"]),
                TableRef("table-3", "run-1", "node-run-1", storageKind: "RUNTIME_SQL", capabilities: ["READ"]),
            ]);

        Assert.AreEqual("node-run-1", state.DisplayText);
        Assert.AreEqual(3, state.TableCount);
        Assert.AreEqual("3 table(s)", state.TableCountText);
        Assert.AreEqual(2, state.ReadableTableCount);
        Assert.IsTrue(state.HasReadableTables);
        Assert.AreEqual("MEMORY, RUNTIME_SQL", state.StorageKindsText);
        Assert.AreEqual("3 table(s) · MEMORY, RUNTIME_SQL", state.SummaryText);
    }

    [TestMethod]
    public void ConstructorRejectsMixedNodeRunTableRefs()
    {
        var exception = Assert.ThrowsExactly<ArgumentException>(() =>
            new DataPreviewStateListItemViewModel(
                "run-1",
                "node-run-1",
                [
                    TableRef("table-1", "run-1", "node-run-1"),
                    TableRef("table-2", "run-1", "node-run-2"),
                ]));

        StringAssert.Contains(exception.Message, "same workflow run and node run");
    }

    private static TableRefListItemViewModel TableRef(
        string tableRefId,
        string workflowRunId,
        string nodeRunId,
        string storageKind = "RUNTIME_SQL",
        string[]? capabilities = null)
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
                Version = 1,
                Capabilities = capabilities ?? ["READ"],
                LifecycleStatus = "PUBLISHED",
                CreatedAt = DateTimeOffset.Parse("2026-06-29T01:02:03Z"),
            });
    }
}
