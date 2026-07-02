using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigDraftJsonPatcherTests
{
    [TestMethod]
    public void ApplyConfigReplacesSelectedNodeConfigAndPreservesWorkflowShape()
    {
        using var config = JsonDocument.Parse("""{"field":"amount","operator":"GT"}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "config": {"rows": 3}
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "display_name": "Filter",
                  "config": {"field": "old"}
                }
              ],
              "connections": [
                {"connection_id": "c1"}
              ],
              "metadata": {"owner": "tester"}
            }
            """,
            "filter",
            config.RootElement);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.Succeeded, result.Status);
        Assert.IsNull(result.Warning);

        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("1.0", root.GetProperty("schema_version").GetString());
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual("c1", root.GetProperty("connections")[0].GetProperty("connection_id").GetString());
        Assert.AreEqual(
            3,
            root.GetProperty("nodes")[0].GetProperty("config").GetProperty("rows").GetInt32());

        var filter = root.GetProperty("nodes")[1];
        Assert.AreEqual("Filter", filter.GetProperty("display_name").GetString());
        Assert.AreEqual("amount", filter.GetProperty("config").GetProperty("field").GetString());
        Assert.AreEqual("GT", filter.GetProperty("config").GetProperty("operator").GetString());
    }

    [TestMethod]
    public void ApplyConfigAddsMissingConfigObject()
    {
        using var config = JsonDocument.Parse("""{"rows":5}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """{"nodes":[{"node_instance_id":"source","node_type":"GenerateTestTableNode"}]}""",
            "source",
            config.RootElement);

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        Assert.AreEqual(
            5,
            updated.RootElement
                .GetProperty("nodes")[0]
                .GetProperty("config")
                .GetProperty("rows")
                .GetInt32());
    }

    [TestMethod]
    public void ApplyConfigRejectsInvalidWorkflowJson()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            "{",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.JsonInvalid, result.Status);
        Assert.AreEqual("JSON_INVALID", result.Warning);
    }

    [TestMethod]
    public void ApplyConfigRejectsMissingNodesArray()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """{"schema_version":"1.0"}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodesMissing, result.Status);
        Assert.AreEqual("NODES_MISSING", result.Warning);
    }

    [TestMethod]
    public void ApplyConfigRejectsMissingNode()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """{"nodes":[{"node_instance_id":"source"}]}""",
            "filter",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodeNotFound, result.Status);
        Assert.AreEqual("NODE_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void ApplyConfigRejectsExistingNonObjectConfig()
    {
        using var config = JsonDocument.Parse("""{"rows":5}""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """{"nodes":[{"node_instance_id":"source","config":3}]}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodeConfigNotObject, result.Status);
        Assert.AreEqual("NODE_CONFIG_NOT_OBJECT", result.Warning);
    }

    [TestMethod]
    public void ApplyConfigRejectsNonObjectDraftConfig()
    {
        using var config = JsonDocument.Parse("""["rows"]""");

        var result = NodeConfigDraftJsonPatcher.ApplyConfig(
            """{"nodes":[{"node_instance_id":"source"}]}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.ConfigUnsupported, result.Status);
        Assert.AreEqual("CONFIG_UNSUPPORTED", result.Warning);
    }
}
