using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeConfigDraftJsonPatcherTests
{
    [TestMethod]
    public void ApplyPatchUpdatesSelectedFieldsAndPreservesWorkflowShape()
    {
        using var config = JsonDocument.Parse("""{"field":"amount","operator":"GT"}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
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
                  "config": {
                    "field": "old",
                    "fields": ["amount", "total"],
                    "condition_value": {"source": "fixed", "value": 3},
                    "input_sources": {"in": {"type": "current"}},
                    "output_targets": {"out": {"target_kind": "current"}},
                    "plugin_extension": {"enabled": true}
                  }
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
        Assert.AreEqual(
            "total",
            filter.GetProperty("config").GetProperty("fields")[1].GetString());
        Assert.AreEqual(
            3,
            filter.GetProperty("config").GetProperty("condition_value").GetProperty("value").GetInt32());
        Assert.AreEqual(
            "current",
            filter.GetProperty("config").GetProperty("input_sources").GetProperty("in").GetProperty("type").GetString());
        Assert.AreEqual(
            "current",
            filter.GetProperty("config").GetProperty("output_targets").GetProperty("out").GetProperty("target_kind").GetString());
        Assert.IsTrue(
            filter.GetProperty("config").GetProperty("plugin_extension").GetProperty("enabled").GetBoolean());
    }

    [TestMethod]
    public void ApplyPatchAddsMissingConfigObject()
    {
        using var config = JsonDocument.Parse("""{"rows":5}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
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
    public void ApplyPatchRejectsInvalidWorkflowJson()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            "{",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.JsonInvalid, result.Status);
        Assert.AreEqual("JSON_INVALID", result.Warning);
    }

    [TestMethod]
    public void ApplyPatchRejectsMissingNodesArray()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """{"schema_version":"1.0"}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodesMissing, result.Status);
        Assert.AreEqual("NODES_MISSING", result.Warning);
    }

    [TestMethod]
    public void ApplyPatchRejectsMissingNode()
    {
        using var config = JsonDocument.Parse("""{}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """{"nodes":[{"node_instance_id":"source"}]}""",
            "filter",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodeNotFound, result.Status);
        Assert.AreEqual("NODE_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void ApplyPatchRejectsExistingNonObjectConfig()
    {
        using var config = JsonDocument.Parse("""{"rows":5}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """{"nodes":[{"node_instance_id":"source","config":3}]}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.NodeConfigNotObject, result.Status);
        Assert.AreEqual("NODE_CONFIG_NOT_OBJECT", result.Warning);
    }

    [TestMethod]
    public void ApplyPatchRejectsNonObjectDraftConfig()
    {
        using var config = JsonDocument.Parse("""["rows"]""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """{"nodes":[{"node_instance_id":"source"}]}""",
            "source",
            config.RootElement);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.ConfigUnsupported, result.Status);
        Assert.AreEqual("CONFIG_UNSUPPORTED", result.Warning);
    }

    [TestMethod]
    public void ApplyPatchDeletesOnlyExplicitFields()
    {
        using var fieldsToSet = JsonDocument.Parse("""{"field":"total"}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """
            {
              "nodes": [
                {
                  "node_instance_id": "filter",
                  "config": {
                    "field": "amount",
                    "limit": 10,
                    "plugin_extension": {"enabled": true}
                  }
                }
              ]
            }
            """,
            "filter",
            fieldsToSet.RootElement,
            ["limit"]);

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var config = updated.RootElement.GetProperty("nodes")[0].GetProperty("config");
        Assert.AreEqual("total", config.GetProperty("field").GetString());
        Assert.IsFalse(config.TryGetProperty("limit", out _));
        Assert.IsTrue(config.GetProperty("plugin_extension").GetProperty("enabled").GetBoolean());
    }

    [TestMethod]
    public void ApplyPatchRejectsSetDeleteConflict()
    {
        using var fieldsToSet = JsonDocument.Parse("""{"field":"total"}""");

        var result = NodeConfigDraftJsonPatcher.ApplyPatch(
            """{"nodes":[{"node_instance_id":"filter","config":{"field":"amount"}}]}""",
            "filter",
            fieldsToSet.RootElement,
            ["field"]);

        Assert.IsFalse(result.Succeeded);
        Assert.AreEqual(NodeConfigDraftApplyStatus.PatchConflict, result.Status);
        Assert.AreEqual("CONFIG_PATCH_FIELD_CONFLICT", result.Warning);
        Assert.HasCount(1, result.ConflictingFields);
        Assert.AreEqual("field", result.ConflictingFields[0]);
    }
}
