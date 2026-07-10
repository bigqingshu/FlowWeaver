using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeTableBindingsDraftReaderTests
{
    [TestMethod]
    public void ReadsLegacySingleBindingsAndNormalizesAliases()
    {
        var result = NodeTableBindingsDraftReader.Read(
            """
            {
              "nodes": [{
                "node_instance_id": "target",
                "config": {
                  "input_source": {
                    "type": "upstream",
                    "source_node_instance_id": "source",
                    "output_alias": "orders",
                    "storage_kind": "RUNTIME_SQL",
                    "logical_table_id": "orders",
                    "table_ref_id": "runtime-only"
                  },
                  "output_target": {
                    "target_type": "memory_table",
                    "table_name": "filtered_orders",
                    "table_ref_id": "runtime-only"
                  }
                }
              }],
              "connections": []
            }
            """,
            "target");

        Assert.IsTrue(result.Succeeded);
        Assert.HasCount(1, result.InputBindings);
        Assert.HasCount(1, result.OutputTargets);
        var input = result.InputBindings[0];
        Assert.AreEqual("in", input.Slot);
        Assert.AreEqual(NodeTableInputBindingDraft.UpstreamTableSourceType, input.Type);
        Assert.AreEqual("source", input.SourceNodeInstanceId);
        Assert.AreEqual("orders", input.OutputSlot);
        var output = result.OutputTargets[0];
        Assert.AreEqual("out", output.Slot);
        Assert.AreEqual(NodeTableOutputTargetDraft.NewMemoryTargetKind, output.TargetKind);
        Assert.AreEqual("filtered_orders", output.LogicalTableId);
        Assert.IsTrue(output.IsLogicalTableIdEditable);
    }

    [TestMethod]
    public void ReadsMultipleInputAndOutputSlotsFromLegacyCollections()
    {
        var result = NodeTableBindingsDraftReader.Read(
            """
            {
              "nodes": [{
                "node_instance_id": "merge",
                "config": {
                  "input_table_sources": [
                    {"input_slot":"left","type":"current_table"},
                    {"slot":"right","source_node_instance_id":"rules","output_slot":"out"}
                  ],
                  "output_table_targets": {
                    "out": {"target_type":"current_table"},
                    "audit": {"target_kind":"existing_runtime_sql","target_table":"audit_rows"}
                  }
                }
              }],
              "connections": []
            }
            """,
            "merge");

        Assert.IsTrue(result.Succeeded);
        Assert.HasCount(2, result.InputBindings);
        Assert.HasCount(2, result.OutputTargets);
        Assert.IsTrue(result.InputBindings[0].IsCurrent);
        Assert.AreEqual("rules", result.InputBindings[1].SourceNodeInstanceId);
        Assert.IsTrue(result.OutputTargets[0].IsCurrent);
        Assert.IsTrue(result.OutputTargets[1].IsExistingTarget);
        Assert.IsFalse(result.OutputTargets[1].IsLogicalTableIdEditable);
    }

    [TestMethod]
    public void RejectsInvalidCurrentAndNamedOutputTargets()
    {
        var namedCurrent = NodeTableBindingsDraftReader.Read(
            DocumentWithConfig(
                """{"output_target":{"target_kind":"current","table_name":"bad"}}"""),
            "node");
        var unnamedNew = NodeTableBindingsDraftReader.Read(
            DocumentWithConfig(
                """{"output_target":{"target_kind":"new_runtime_sql"}}"""),
            "node");

        Assert.AreEqual(NodeTableBindingsDraftReadStatus.BindingInvalid, namedCurrent.Status);
        Assert.AreEqual("CURRENT_OUTPUT_TARGET_MUST_NOT_BE_NAMED", namedCurrent.Warning);
        Assert.AreEqual(NodeTableBindingsDraftReadStatus.BindingInvalid, unnamedNew.Status);
        Assert.AreEqual(
            "NAMED_OUTPUT_TARGET_REQUIRES_LOGICAL_TABLE_ID",
            unnamedNew.Warning);
    }

    [TestMethod]
    public void SharedParseCacheReusesNodeBindingResultPerDraftAndNode()
    {
        var cache = new WorkflowDefinitionDraftParseCache();
        const string json = """{"nodes":[{"node_instance_id":"node","config":{}}],"connections":[]}""";

        var first = cache.GetNodeTableBindings(json, "node");
        var second = cache.GetNodeTableBindings(json, "node");

        Assert.AreSame(first, second);
        Assert.AreSame(cache.GetSnapshot(json), cache.GetSnapshot(json));
    }

    private static string DocumentWithConfig(string config)
    {
        return $$"""
            {
              "nodes": [{"node_instance_id":"node","config":{{config}}}],
              "connections": []
            }
            """;
    }
}
