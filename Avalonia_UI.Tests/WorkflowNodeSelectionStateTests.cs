using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowNodeSelectionStateTests
{
    [TestMethod]
    public void ResolveSelectedNodeId_PreservesExistingSelection()
    {
        var state = new WorkflowNodeSelectionState();
        state.Capture("filter", hasSelection: true);

        var selectedNodeId = state.ResolveSelectedNodeId(["source", "filter"]);

        Assert.AreEqual("filter", selectedNodeId);
    }

    [TestMethod]
    public void ResolveSelectedNodeId_ClearsMissingPreviousSelection()
    {
        var state = new WorkflowNodeSelectionState();
        state.Capture("filter", hasSelection: true);

        var selectedNodeId = state.ResolveSelectedNodeId(["source", "target"]);

        Assert.IsNull(selectedNodeId);
    }

    [TestMethod]
    public void ResolveSelectedNodeId_SelectsFirstNodeWithoutPreviousSelection()
    {
        var state = new WorkflowNodeSelectionState();
        state.Capture(nodeId: null, hasSelection: false);

        var selectedNodeId = state.ResolveSelectedNodeId(["source", "filter"]);

        Assert.AreEqual("source", selectedNodeId);
    }

    [TestMethod]
    public void ResolveSelectedNodeId_ReturnsNullWithoutAvailableNodes()
    {
        var state = new WorkflowNodeSelectionState();
        state.Capture(nodeId: null, hasSelection: false);

        var selectedNodeId = state.ResolveSelectedNodeId([]);

        Assert.IsNull(selectedNodeId);
    }

    [TestMethod]
    public void ResolveSelectedNodeId_UsesOrdinalNodeIdComparison()
    {
        var state = new WorkflowNodeSelectionState();
        state.Capture("Filter", hasSelection: true);

        var selectedNodeId = state.ResolveSelectedNodeId(["filter"]);

        Assert.IsNull(selectedNodeId);
    }
}
