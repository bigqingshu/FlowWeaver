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
    public void DeleteNodeRejectsConnectedNode()
    {
        var result = WorkflowDefinitionDraftNodePatcher.DeleteNode(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "c1", "source_node_id": "source", "target_node_id": "filter"}
              ]
            }
            """,
            "filter");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftNodePatchStatus.NodeHasConnections, result.Status);
        Assert.AreEqual("NODE_HAS_CONNECTIONS", result.Warning);
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
