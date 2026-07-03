using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftNodePatcherTests
{
    [TestMethod]
    public void AddNodeAppendsNodeAndPreservesWorkflowShape()
    {
        using var config = JsonDocument.Parse("""{"rows":3}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {"rows": 1}
                }
              ],
              "connections": [
                {"connection_id": "existing"}
              ],
              "metadata": {"owner": "tester"}
            }
            """,
            "filter",
            "FilterRowsNode",
            "1.0",
            "Filter",
            config.RootElement);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual(
            "existing",
            root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
        Assert.AreEqual(2, root.GetProperty("nodes").GetArrayLength());

        var added = root.GetProperty("nodes")[1];
        Assert.AreEqual("filter", added.GetProperty("node_instance_id").GetString());
        Assert.AreEqual("FilterRowsNode", added.GetProperty("node_type").GetString());
        Assert.AreEqual("1.0", added.GetProperty("node_version").GetString());
        Assert.AreEqual("Filter", added.GetProperty("display_name").GetString());
        Assert.AreEqual(3, added.GetProperty("config").GetProperty("rows").GetInt32());
    }

    [TestMethod]
    public void AddNodeInsertsAfterAnchorNodeWhenRequested()
    {
        using var config = JsonDocument.Parse("""{"value":1}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "keep", "source_node_id": "source", "target_node_id": "sink"}
              ]
            }
            """,
            "filter",
            "FilterRowsNode",
            "1.0",
            null,
            config.RootElement,
            "source");

        Assert.IsTrue(result.Succeeded);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var nodes = updated.RootElement.GetProperty("nodes");
        Assert.AreEqual("source", nodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("filter", nodes[1].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", nodes[2].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(
            "keep",
            updated.RootElement
                .GetProperty("connections")[0]
                .GetProperty("connection_id")
                .GetString());
    }

    [TestMethod]
    public void AddNodeAutoWiresSingleDownstreamConnectionWhenPortsAreProvided()
    {
        using var config = JsonDocument.Parse("""{"field":"amount"}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "source_to_sink", "source_node_id": "source", "source_port": "out", "target_node_id": "sink", "target_port": "in"}
              ]
            }
            """,
            "filter",
            "FilterRowsNode",
            "1.0",
            null,
            config.RootElement,
            "source",
            "in",
            "out");

        Assert.IsTrue(result.Succeeded);
        Assert.HasCount(1, result.RemovedConnections);
        Assert.AreEqual("source_to_sink", result.RemovedConnections[0].ConnectionId);
        Assert.HasCount(2, result.AddedConnections);
        Assert.AreEqual("source_to_filter", result.AddedConnections[0].ConnectionId);
        Assert.AreEqual("source", result.AddedConnections[0].SourceNodeId);
        Assert.AreEqual("out", result.AddedConnections[0].SourcePort);
        Assert.AreEqual("filter", result.AddedConnections[0].TargetNodeId);
        Assert.AreEqual("in", result.AddedConnections[0].TargetPort);
        Assert.AreEqual("filter_to_sink", result.AddedConnections[1].ConnectionId);
        Assert.AreEqual("filter", result.AddedConnections[1].SourceNodeId);
        Assert.AreEqual("out", result.AddedConnections[1].SourcePort);
        Assert.AreEqual("sink", result.AddedConnections[1].TargetNodeId);
        Assert.AreEqual("in", result.AddedConnections[1].TargetPort);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var connections = updated.RootElement.GetProperty("connections");
        Assert.AreEqual(2, connections.GetArrayLength());
        Assert.AreEqual("source_to_filter", connections[0].GetProperty("connection_id").GetString());
        Assert.AreEqual("filter", connections[0].GetProperty("target_node_id").GetString());
        Assert.AreEqual("filter_to_sink", connections[1].GetProperty("connection_id").GetString());
        Assert.AreEqual("filter", connections[1].GetProperty("source_node_id").GetString());
    }

    [TestMethod]
    public void AddNodeDoesNotAutoWireWhenAnchorHasMultipleDownstreamConnections()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "left"},
                {"node_instance_id": "right"}
              ],
              "connections": [
                {"connection_id": "source_to_left", "source_node_id": "source", "source_port": "out", "target_node_id": "left", "target_port": "in"},
                {"connection_id": "source_to_right", "source_node_id": "source", "source_port": "out", "target_node_id": "right", "target_port": "in"}
              ]
            }
            """,
            "filter",
            "FilterRowsNode",
            "1.0",
            null,
            config.RootElement,
            "source",
            "in",
            "out");

        Assert.IsTrue(result.Succeeded);
        Assert.IsEmpty(result.RemovedConnections);
        Assert.IsEmpty(result.AddedConnections);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        Assert.AreEqual(4, updated.RootElement.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(2, updated.RootElement.GetProperty("connections").GetArrayLength());
    }

    [TestMethod]
    public void AddNodeRejectsMissingInsertionAnchor()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[{"node_instance_id":"source"}],"connections":[]}""",
            "filter",
            "FilterRowsNode",
            "1.0",
            null,
            config.RootElement,
            "missing");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftNodePatchStatus.InsertAfterNodeNotFound,
            result.Status);
        Assert.AreEqual("INSERT_AFTER_NODE_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void AddNodeOmitsBlankDisplayName()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[],"connections":[]}""",
            "source",
            "GenerateTestTableNode",
            "1.0",
            "   ",
            config.RootElement);

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        Assert.IsFalse(
            updated.RootElement
                .GetProperty("nodes")[0]
                .TryGetProperty("display_name", out _));
    }

    [TestMethod]
    public void AddNodeRejectsInvalidWorkflowJson()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            "{",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.JsonInvalid, result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_JSON_INVALID", result.Warning);
    }

    [TestMethod]
    public void AddNodeRejectsRootThatIsNotObject()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            "[]",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.RootNotObject, result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_ROOT_NOT_OBJECT", result.Warning);
    }

    [TestMethod]
    public void AddNodeRejectsMissingNodesArray()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"connections":[]}""",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodesMissing, result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_NODES_MISSING", result.Warning);
    }

    [TestMethod]
    public void AddNodeRejectsMissingConnectionsArray()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[]}""",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.ConnectionsMissing, result.Status);
        Assert.AreEqual("WORKFLOW_DRAFT_CONNECTIONS_MISSING", result.Warning);
    }

    [TestMethod]
    public void AddNodeRejectsDuplicateNodeInstanceId()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[{"node_instance_id":"source"}],"connections":[]}""",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodeAlreadyExists, result.Status);
        Assert.AreEqual("NODE_ALREADY_EXISTS", result.Warning);
    }

    [TestMethod]
    public void AddNodeRejectsBlankIdentityFields()
    {
        using var config = JsonDocument.Parse("""{}""");

        var missingId = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[],"connections":[]}""",
            " ",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);
        var missingType = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[],"connections":[]}""",
            "source",
            " ",
            "1.0",
            null,
            config.RootElement);
        var missingVersion = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[],"connections":[]}""",
            "source",
            "GenerateTestTableNode",
            " ",
            null,
            config.RootElement);

        Assert.AreEqual(
            WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
            missingId.Status);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodeTypeRequired, missingType.Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftNodePatchStatus.NodeVersionRequired,
            missingVersion.Status);
    }

    [TestMethod]
    public void AddNodeRejectsNonObjectConfig()
    {
        using var config = JsonDocument.Parse("""[]""");

        var result = WorkflowDefinitionDraftNodePatcher.AddNode(
            """{"nodes":[],"connections":[]}""",
            "source",
            "GenerateTestTableNode",
            "1.0",
            null,
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.ConfigUnsupported, result.Status);
        Assert.AreEqual("CONFIG_UNSUPPORTED", result.Warning);
    }

    [TestMethod]
    public void DeleteNodeRemovesUnconnectedNodeAndPreservesWorkflowShape()
    {
        var result = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source", "node_type": "GenerateTestTableNode"},
                {"node_instance_id": "orphan", "node_type": "FilterRowsNode"}
              ],
              "connections": [
                {"connection_id": "keep", "source_node_id": "source", "target_node_id": "source"}
              ],
              "metadata": {"owner": "tester"}
            }
            """,
            "orphan");

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual(1, root.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(
            "source",
            root.GetProperty("nodes")[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(1, root.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
    }

    [TestMethod]
    public void MoveNodeReordersNodesAndPreservesConnections()
    {
        var moveUp = WorkflowDefinitionDraftNodePatcher.MoveNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "target_node_id": "filter"}
              ]
            }
            """,
            "filter",
            -1);

        Assert.IsTrue(moveUp.Succeeded);
        using var movedUp = JsonDocument.Parse(moveUp.UpdatedWorkflowDefinitionDraftJson);
        var movedUpNodes = movedUp.RootElement.GetProperty("nodes");
        Assert.AreEqual("filter", movedUpNodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("source", movedUpNodes[1].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", movedUpNodes[2].GetProperty("node_instance_id").GetString());
        Assert.AreEqual(
            "source_to_filter",
            movedUp.RootElement
                .GetProperty("connections")[0]
                .GetProperty("connection_id")
                .GetString());

        var moveDown = WorkflowDefinitionDraftNodePatcher.MoveNode(
            moveUp.UpdatedWorkflowDefinitionDraftJson,
            "filter",
            1);

        Assert.IsTrue(moveDown.Succeeded);
        using var movedDown = JsonDocument.Parse(moveDown.UpdatedWorkflowDefinitionDraftJson);
        var movedDownNodes = movedDown.RootElement.GetProperty("nodes");
        Assert.AreEqual("source", movedDownNodes[0].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("filter", movedDownNodes[1].GetProperty("node_instance_id").GetString());
        Assert.AreEqual("sink", movedDownNodes[2].GetProperty("node_instance_id").GetString());
    }

    [TestMethod]
    public void MoveNodeRejectsOutOfRangeMove()
    {
        var result = WorkflowDefinitionDraftNodePatcher.MoveNode(
            """{"nodes":[{"node_instance_id":"source"}],"connections":[]}""",
            "source",
            -1);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodeMoveOutOfRange, result.Status);
        Assert.AreEqual("NODE_MOVE_OUT_OF_RANGE", result.Warning);
    }

    [TestMethod]
    public void DeleteNodeRemovesConnectedNodeAndRelatedConnections()
    {
        var result = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "c1", "source_node_id": "source", "source_port": "rows", "target_node_id": "filter", "target_port": "rows"},
                {"connection_id": "c2", "source_node_id": "filter", "source_port": "rows", "target_node_id": "sink", "target_port": "rows"},
                {"connection_id": "keep", "source_node_id": "source", "source_port": "rows", "target_node_id": "sink", "target_port": "rows"}
              ]
            }
            """,
            "filter");

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);
        Assert.HasCount(2, result.RemovedConnections);
        Assert.AreEqual("c1", result.RemovedConnections[0].ConnectionId);
        Assert.AreEqual("source", result.RemovedConnections[0].SourceNodeId);
        Assert.AreEqual("rows", result.RemovedConnections[0].SourcePort);
        Assert.AreEqual("filter", result.RemovedConnections[0].TargetNodeId);
        Assert.AreEqual("rows", result.RemovedConnections[0].TargetPort);
        Assert.AreEqual("c2", result.RemovedConnections[1].ConnectionId);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual(2, root.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(1, root.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
    }

    [TestMethod]
    public void DeleteNodeRejectsMissingNode()
    {
        var result = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """{"nodes":[{"node_instance_id":"source"}],"connections":[]}""",
            "missing");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodeNotFound, result.Status);
        Assert.AreEqual("NODE_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void DeleteNodeRejectsBlankNodeInstanceId()
    {
        var result = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """{"nodes":[],"connections":[]}""",
            " ");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
            result.Status);
        Assert.AreEqual("NODE_INSTANCE_ID_REQUIRED", result.Warning);
    }

    [TestMethod]
    public void DeleteNodeRejectsInvalidWorkflowDraftShape()
    {
        var invalidJson = WorkflowDefinitionDraftNodePatcher.DeleteNode("{", "source");
        var missingNodes = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """{"connections":[]}""",
            "source");
        var missingConnections = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """{"nodes":[]}""",
            "source");

        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.JsonInvalid, invalidJson.Status);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodesMissing, missingNodes.Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftNodePatchStatus.ConnectionsMissing,
            missingConnections.Status);
    }
}
