using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftConnectionPatcherTests
{
    [TestMethod]
    public void AddConnectionAppendsConnectionAndPreservesWorkflowShape()
    {
        var result = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [],
              "metadata": {"owner": "tester"}
            }
            """,
            "source_to_filter",
            "source",
            "out",
            "filter",
            "in");

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(WorkflowDefinitionDraftConnectionPatchStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual(2, root.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(1, root.GetProperty("connections").GetArrayLength());

        var connection = root.GetProperty("connections")[0];
        Assert.AreEqual("source_to_filter", connection.GetProperty("connection_id").GetString());
        Assert.AreEqual("source", connection.GetProperty("source_node_id").GetString());
        Assert.AreEqual("out", connection.GetProperty("source_port").GetString());
        Assert.AreEqual("filter", connection.GetProperty("target_node_id").GetString());
        Assert.AreEqual("in", connection.GetProperty("target_port").GetString());
    }

    [TestMethod]
    public void AddConnectionRejectsDuplicateConnectionId()
    {
        var result = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "c1"}
              ]
            }
            """,
            "c1",
            "source",
            "out",
            "filter",
            "in");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.ConnectionAlreadyExists,
            result.Status);
        Assert.AreEqual("CONNECTION_ALREADY_EXISTS", result.Warning);
    }

    [TestMethod]
    public void AddConnectionRejectsMissingEndpointNodes()
    {
        var sourceMissing = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            """{"nodes":[{"node_instance_id":"target"}],"connections":[]}""",
            "c1",
            "source",
            "out",
            "target",
            "in");
        var targetMissing = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            """{"nodes":[{"node_instance_id":"source"}],"connections":[]}""",
            "c1",
            "source",
            "out",
            "target",
            "in");

        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.SourceNodeNotFound,
            sourceMissing.Status);
        Assert.AreEqual("SOURCE_NODE_NOT_FOUND", sourceMissing.Warning);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.TargetNodeNotFound,
            targetMissing.Status);
        Assert.AreEqual("TARGET_NODE_NOT_FOUND", targetMissing.Warning);
    }

    [TestMethod]
    public void AddConnectionRejectsBlankRequiredFields()
    {
        var draft = """{"nodes":[],"connections":[]}""";

        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.ConnectionIdRequired,
            WorkflowDefinitionDraftConnectionPatcher.AddConnection(
                draft,
                " ",
                "source",
                "out",
                "target",
                "in").Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.SourceNodeIdRequired,
            WorkflowDefinitionDraftConnectionPatcher.AddConnection(
                draft,
                "c1",
                " ",
                "out",
                "target",
                "in").Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.SourcePortRequired,
            WorkflowDefinitionDraftConnectionPatcher.AddConnection(
                draft,
                "c1",
                "source",
                " ",
                "target",
                "in").Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.TargetNodeIdRequired,
            WorkflowDefinitionDraftConnectionPatcher.AddConnection(
                draft,
                "c1",
                "source",
                "out",
                " ",
                "in").Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.TargetPortRequired,
            WorkflowDefinitionDraftConnectionPatcher.AddConnection(
                draft,
                "c1",
                "source",
                "out",
                "target",
                " ").Status);
    }

    [TestMethod]
    public void DeleteConnectionRemovesConnectionAndPreservesWorkflowShape()
    {
        var result = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            """
            {
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"}
              ],
              "connections": [
                {"connection_id": "remove"},
                {"connection_id": "keep"}
              ],
              "metadata": {"owner": "tester"}
            }
            """,
            "remove");

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual(2, root.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(1, root.GetProperty("connections").GetArrayLength());
        Assert.AreEqual(
            "keep",
            root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
    }

    [TestMethod]
    public void DeleteConnectionRejectsMissingConnection()
    {
        var result = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            """{"nodes":[],"connections":[{"connection_id":"c1"}]}""",
            "missing");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.ConnectionNotFound,
            result.Status);
        Assert.AreEqual("CONNECTION_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void DeleteConnectionRejectsBlankConnectionId()
    {
        var result = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            """{"nodes":[],"connections":[]}""",
            " ");

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.ConnectionIdRequired,
            result.Status);
        Assert.AreEqual("CONNECTION_ID_REQUIRED", result.Warning);
    }

    [TestMethod]
    public void ConnectionPatchersRejectInvalidWorkflowDraftShape()
    {
        var invalidJson = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection("{", "c1");
        var rootNotObject = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection("[]", "c1");
        var missingNodes = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            """{"connections":[]}""",
            "c1");
        var missingConnections = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            """{"nodes":[]}""",
            "c1");

        Assert.AreEqual(WorkflowDefinitionDraftConnectionPatchStatus.JsonInvalid, invalidJson.Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.RootNotObject,
            rootNotObject.Status);
        Assert.AreEqual(WorkflowDefinitionDraftConnectionPatchStatus.NodesMissing, missingNodes.Status);
        Assert.AreEqual(
            WorkflowDefinitionDraftConnectionPatchStatus.ConnectionsMissing,
            missingConnections.Status);
    }
}
