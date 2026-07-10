using System.Text.Json;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowLoopRegionDraftPatcherTests
{
    [TestMethod]
    public void UpsertAddsLoopAndPreservesUnrelatedDocumentFields()
    {
        var result = WorkflowLoopRegionDraftPatcher.Upsert(
            """
            {
              "schema_version": "1.0",
              "metadata": {"owner":"tester"},
              "runtime_options": {"version":"1.0","custom":true},
              "nodes": [
                {"node_instance_id":"start","config":{"preview_count":3}},
                {"node_instance_id":"body","config":{"table_inputs":{"source":{"source":"current"}}}},
                {"node_instance_id":"judge","config":{"condition_field":"done"}},
                {"node_instance_id":"exit","config":{}}
              ],
              "connections": [{"connection_id":"c1","source_node_id":"start","target_node_id":"body"}],
              "extension": {"keep":"yes"}
            }
            """,
            Draft(enabled: true));

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual("tester", root.GetProperty("metadata").GetProperty("owner").GetString());
        Assert.IsTrue(root.GetProperty("runtime_options").GetProperty("custom").GetBoolean());
        Assert.AreEqual("yes", root.GetProperty("extension").GetProperty("keep").GetString());
        Assert.AreEqual("c1", root.GetProperty("connections")[0].GetProperty("connection_id").GetString());

        var protocol = root.GetProperty("control_protocol");
        Assert.AreEqual("1.0", protocol.GetProperty("version").GetString());
        Assert.AreEqual("enabled", protocol.GetProperty("mode").GetString());
        var region = protocol.GetProperty("loop_regions")[0];
        Assert.AreEqual("row", region.GetProperty("input_mode").GetString());
        Assert.AreEqual("continue_loop", region.GetProperty("continue_branch").GetString());
        Assert.AreEqual("end_loop", region.GetProperty("end_branch").GetString());

        var nodes = root.GetProperty("nodes");
        Assert.AreEqual(3, nodes[0].GetProperty("config").GetProperty("preview_count").GetInt32());
        Assert.AreEqual("orders_loop", nodes[0].GetProperty("config").GetProperty("loop_id").GetString());
        Assert.AreEqual("done", nodes[2].GetProperty("config").GetProperty("condition_field").GetString());
        Assert.AreEqual("orders_loop", nodes[2].GetProperty("config").GetProperty("loop_id").GetString());
        Assert.IsTrue(nodes[1].GetProperty("config").TryGetProperty("table_inputs", out _));
    }

    [TestMethod]
    public void UpsertUpdatesAndRenamesLoopWithoutDroppingUnknownRegionFields()
    {
        var result = WorkflowLoopRegionDraftPatcher.Upsert(
            """
            {
              "nodes": [
                {"node_instance_id":"start_old","config":{"loop_id":"old_loop","keep":1}},
                {"node_instance_id":"judge_old","config":{"loop_id":"old_loop","keep":2}},
                {"node_instance_id":"start_new","config":{"keep":3}},
                {"node_instance_id":"judge_new","config":{"keep":4}},
                {"node_instance_id":"body","config":{"keep":5}}
              ],
              "connections": [],
              "control_protocol": {
                "version":"1.0",
                "mode":"enabled",
                "custom_protocol":"keep",
                "loop_regions":[{
                  "loop_id":"old_loop",
                  "start_node_id":"start_old",
                  "judge_node_id":"judge_old",
                  "body_node_ids":["body"],
                  "enabled":true,
                  "custom_region":"keep"
                }]
              }
            }
            """,
            new WorkflowLoopRegionDraft
            {
                LoopId = "new_loop",
                StartNodeId = "start_new",
                JudgeNodeId = "judge_new",
                BodyNodeIds = ["body"],
                MaxIterations = 4,
                Enabled = false,
            },
            existingLoopId: "old_loop");

        Assert.IsTrue(result.Succeeded);
        using var updated = JsonDocument.Parse(result.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        var protocol = root.GetProperty("control_protocol");
        Assert.AreEqual("preview", protocol.GetProperty("mode").GetString());
        Assert.AreEqual("keep", protocol.GetProperty("custom_protocol").GetString());
        var region = protocol.GetProperty("loop_regions")[0];
        Assert.AreEqual("new_loop", region.GetProperty("loop_id").GetString());
        Assert.AreEqual("keep", region.GetProperty("custom_region").GetString());
        Assert.AreEqual(4, region.GetProperty("max_iterations").GetInt32());

        var nodes = root.GetProperty("nodes");
        Assert.IsFalse(nodes[0].GetProperty("config").TryGetProperty("loop_id", out _));
        Assert.IsFalse(nodes[1].GetProperty("config").TryGetProperty("loop_id", out _));
        Assert.AreEqual("new_loop", nodes[2].GetProperty("config").GetProperty("loop_id").GetString());
        Assert.AreEqual("new_loop", nodes[3].GetProperty("config").GetProperty("loop_id").GetString());
        Assert.AreEqual(5, nodes[4].GetProperty("config").GetProperty("keep").GetInt32());
    }

    [TestMethod]
    public void DeleteRemovesRegionAndLoopIdsButKeepsNodes()
    {
        var added = WorkflowLoopRegionDraftPatcher.Upsert(
            BaseDocumentJson,
            Draft(enabled: true));
        Assert.IsTrue(added.Succeeded);

        var deleted = WorkflowLoopRegionDraftPatcher.Delete(
            added.UpdatedWorkflowDefinitionDraftJson,
            "orders_loop");

        Assert.IsTrue(deleted.Succeeded);
        using var updated = JsonDocument.Parse(deleted.UpdatedWorkflowDefinitionDraftJson);
        var root = updated.RootElement;
        Assert.AreEqual(4, root.GetProperty("nodes").GetArrayLength());
        Assert.AreEqual(
            0,
            root.GetProperty("control_protocol").GetProperty("loop_regions").GetArrayLength());
        Assert.AreEqual(
            "preview",
            root.GetProperty("control_protocol").GetProperty("mode").GetString());
        Assert.IsFalse(root.GetProperty("nodes")[0].GetProperty("config").TryGetProperty("loop_id", out _));
        Assert.IsFalse(root.GetProperty("nodes")[2].GetProperty("config").TryGetProperty("loop_id", out _));
    }

    [TestMethod]
    public void UpsertRejectsUnknownNodeAndNonObjectTargetConfig()
    {
        var unknown = WorkflowLoopRegionDraftPatcher.Upsert(
            BaseDocumentJson,
            Draft(enabled: false) with { BodyNodeIds = ["missing"] });
        var badConfig = WorkflowLoopRegionDraftPatcher.Upsert(
            """
            {
              "nodes": [
                {"node_instance_id":"start","config":[]},
                {"node_instance_id":"body","config":{}},
                {"node_instance_id":"judge","config":{}},
                {"node_instance_id":"exit","config":{}}
              ],
              "connections": []
            }
            """,
            Draft(enabled: false));
        var bodyContainsExit = WorkflowLoopRegionDraftPatcher.Upsert(
            BaseDocumentJson,
            Draft(enabled: false) with { BodyNodeIds = ["body", "exit"] });

        Assert.AreEqual(WorkflowLoopRegionDraftPatchStatus.ValidationFailed, unknown.Status);
        Assert.AreEqual(
            WorkflowLoopRegionDraftValidationStatus.UnknownNode,
            unknown.Validation?.Status);
        Assert.AreEqual(WorkflowLoopRegionDraftPatchStatus.NodeConfigNotObject, badConfig.Status);
        Assert.AreEqual(
            WorkflowLoopRegionDraftValidationStatus.BodyContainsBoundary,
            bodyContainsExit.Validation?.Status);
    }

    private const string BaseDocumentJson =
        """
        {
          "nodes": [
            {"node_instance_id":"start","config":{"keep":1}},
            {"node_instance_id":"body","config":{"keep":2}},
            {"node_instance_id":"judge","config":{"keep":3}},
            {"node_instance_id":"exit","config":{"keep":4}}
          ],
          "connections": []
        }
        """;

    private static WorkflowLoopRegionDraft Draft(bool enabled)
    {
        return new WorkflowLoopRegionDraft
        {
            LoopId = "orders_loop",
            StartNodeId = "start",
            JudgeNodeId = "judge",
            BodyNodeIds = ["body"],
            EndNodeId = "exit",
            MaxIterations = 6,
            Enabled = enabled,
        };
    }
}
