using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeTableBindingsDraftPatcherTests
{
    [TestMethod]
    public void ApplyWritesCanonicalBindingsAndPreservesUnrelatedConfiguration()
    {
        var result = NodeTableBindingsDraftPatcher.Apply(
            """
            {
              "metadata": {"owner":"tester"},
              "nodes": [{
                "node_instance_id": "target",
                "config": {
                  "business_field": 42,
                  "plugin_extension": {"keep":true},
                  "input_table_sources": {"old":{"table_ref_id":"old-input"}},
                  "output_save": {"enabled":true,"table_ref_id":"old-output"}
                }
              }],
              "connections": [],
              "control_protocol": {"mode":"preview"}
            }
            """,
            "target",
            [
                new NodeTableInputBindingDraft
                {
                    Slot = "in",
                    Type = NodeTableInputBindingDraft.UpstreamTableSourceType,
                    SourceNodeInstanceId = "source",
                    OutputSlot = "out",
                    StorageKind = "RUNTIME_SQL",
                    LogicalTableId = "orders",
                },
            ],
            [
                new NodeTableOutputTargetDraft
                {
                    Slot = "out",
                    TargetKind = NodeTableOutputTargetDraft.NewRuntimeSqlTargetKind,
                    LogicalTableId = "filtered_orders",
                },
            ]);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = document.RootElement;
        var config = root.GetProperty("nodes")[0].GetProperty("config");
        Assert.AreEqual(42, config.GetProperty("business_field").GetInt32());
        Assert.IsTrue(config.GetProperty("plugin_extension").GetProperty("keep").GetBoolean());
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.AreEqual("preview", root.GetProperty("control_protocol").GetProperty("mode").GetString());
        Assert.IsFalse(config.TryGetProperty("input_table_sources", out _));
        Assert.IsFalse(config.TryGetProperty("output_save", out _));

        var input = config.GetProperty("input_sources").GetProperty("in");
        Assert.AreEqual("upstream_table", input.GetProperty("type").GetString());
        Assert.AreEqual("source", input.GetProperty("source_node_instance_id").GetString());
        Assert.AreEqual("out", input.GetProperty("output_slot").GetString());
        var output = config.GetProperty("output_targets").GetProperty("out");
        Assert.AreEqual("new_runtime_sql", output.GetProperty("target_kind").GetString());
        Assert.AreEqual("filtered_orders", output.GetProperty("logical_table_id").GetString());
        Assert.DoesNotContain("table_ref_id", result.UpdatedWorkflowDefinitionDraftJson);
    }

    [TestMethod]
    public void ApplyWritesUnnamedCurrentBindings()
    {
        var result = NodeTableBindingsDraftPatcher.Apply(
            """{"nodes":[{"node_instance_id":"node","config":{"keep":"yes"}}],"connections":[]}""",
            "node",
            [new NodeTableInputBindingDraft { Slot = "in" }],
            [new NodeTableOutputTargetDraft { Slot = "out" }]);

        Assert.IsTrue(result.Succeeded);
        using var document = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var config = document.RootElement.GetProperty("nodes")[0].GetProperty("config");
        var input = config.GetProperty("input_sources").GetProperty("in");
        var output = config.GetProperty("output_targets").GetProperty("out");
        Assert.AreEqual("current", input.GetProperty("type").GetString());
        Assert.AreEqual("current", output.GetProperty("target_kind").GetString());
        Assert.IsFalse(input.TryGetProperty("logical_table_id", out _));
        Assert.IsFalse(output.TryGetProperty("logical_table_id", out _));
        Assert.AreEqual("yes", config.GetProperty("keep").GetString());
    }

    [TestMethod]
    public void ApplyRejectsInvalidTargetNamingWithoutChangingDocument()
    {
        const string json = """{"nodes":[{"node_instance_id":"node","config":{"keep":1}}],"connections":[]}""";
        var namedCurrent = NodeTableBindingsDraftPatcher.Apply(
            json,
            "node",
            [],
            [new NodeTableOutputTargetDraft { LogicalTableId = "bad" }]);
        var unnamedExisting = NodeTableBindingsDraftPatcher.Apply(
            json,
            "node",
            [],
            [new NodeTableOutputTargetDraft
            {
                TargetKind = NodeTableOutputTargetDraft.ExistingMemoryTargetKind,
            }]);

        Assert.AreEqual(NodeTableBindingsDraftPatchStatus.BindingInvalid, namedCurrent.Status);
        Assert.AreEqual("CURRENT_OUTPUT_TARGET_MUST_NOT_BE_NAMED", namedCurrent.Warning);
        Assert.AreEqual(NodeTableBindingsDraftPatchStatus.BindingInvalid, unnamedExisting.Status);
        Assert.AreEqual(
            "NAMED_OUTPUT_TARGET_REQUIRES_LOGICAL_TABLE_ID",
            unnamedExisting.Warning);
    }
}
