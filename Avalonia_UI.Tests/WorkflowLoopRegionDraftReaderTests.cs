using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowLoopRegionDraftReaderTests
{
    [TestMethod]
    public void MissingControlProtocolReadsAsEmptyPreviewList()
    {
        var result = WorkflowLoopRegionDraftReader.Read(
            """{"schema_version":"1.0","nodes":[],"connections":[]}""");

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual("preview", result.ProtocolMode);
        Assert.IsEmpty(result.Regions);
    }

    [TestMethod]
    public void ReadsEnabledLoopRegionWithFixedProtocolFields()
    {
        var result = WorkflowLoopRegionDraftReader.Read(
            """
            {
              "nodes": [
                {"node_instance_id":"start"},
                {"node_instance_id":"body"},
                {"node_instance_id":"judge"},
                {"node_instance_id":"exit"}
              ],
              "connections": [],
              "control_protocol": {
                "version": "1.0",
                "mode": "enabled",
                "loop_regions": [{
                  "loop_id": "orders_loop",
                  "start_node_id": "start",
                  "judge_node_id": "judge",
                  "body_node_ids": ["body"],
                  "end_node_id": "exit",
                  "max_iterations": 8,
                  "input_mode": "row",
                  "continue_branch": "continue_loop",
                  "end_branch": "end_loop",
                  "enabled": true
                }]
              }
            }
            """);

        Assert.IsTrue(result.Succeeded);
        Assert.AreEqual("enabled", result.ProtocolMode);
        Assert.HasCount(1, result.Regions);
        var region = result.Regions[0];
        Assert.AreEqual("orders_loop", region.LoopId);
        Assert.AreEqual("start", region.StartNodeId);
        Assert.AreEqual("judge", region.JudgeNodeId);
        CollectionAssert.AreEqual(new[] { "body" }, (System.Collections.ICollection)region.BodyNodeIds);
        Assert.AreEqual("exit", region.EndNodeId);
        Assert.AreEqual(8, region.MaxIterations);
        Assert.IsTrue(region.Enabled);
    }

    [TestMethod]
    public void RejectsNonObjectProtocolAndDuplicateLoopIdExplicitly()
    {
        var nonObject = WorkflowLoopRegionDraftReader.Read(
            """{"nodes":[],"connections":[],"control_protocol":[]}""");
        var duplicate = WorkflowLoopRegionDraftReader.Read(
            """
            {
              "nodes": [
                {"node_instance_id":"start"},
                {"node_instance_id":"body"},
                {"node_instance_id":"judge"}
              ],
              "connections": [],
              "control_protocol": {
                "mode": "preview",
                "loop_regions": [
                  {"loop_id":"same","start_node_id":"start","judge_node_id":"judge","body_node_ids":["body"]},
                  {"loop_id":"same","start_node_id":"start","judge_node_id":"judge","body_node_ids":["body"]}
                ]
              }
            }
            """);

        Assert.AreEqual(
            WorkflowLoopRegionDraftReadStatus.ControlProtocolNotObject,
            nonObject.Status);
        Assert.AreEqual("CONTROL_PROTOCOL_NOT_OBJECT", nonObject.Warning);
        Assert.AreEqual(
            WorkflowLoopRegionDraftReadStatus.DuplicateLoopId,
            duplicate.Status);
        Assert.AreEqual("same", duplicate.ProblemLoopId);
    }

    [TestMethod]
    public void RejectsUnknownNodeWithNodeDetails()
    {
        var result = WorkflowLoopRegionDraftReader.Read(
            """
            {
              "nodes": [
                {"node_instance_id":"start"},
                {"node_instance_id":"judge"}
              ],
              "connections": [],
              "control_protocol": {
                "mode": "preview",
                "loop_regions": [{
                  "loop_id":"orders_loop",
                  "start_node_id":"start",
                  "judge_node_id":"judge",
                  "body_node_ids":["missing_body"]
                }]
              }
            }
            """);

        Assert.AreEqual(WorkflowLoopRegionDraftReadStatus.UnknownNode, result.Status);
        Assert.IsNotNull(result.Validation);
        CollectionAssert.AreEqual(
            new[] { "missing_body" },
            (System.Collections.ICollection)result.Validation!.UnknownNodeIds);
    }

    [TestMethod]
    public void RejectsNodeSharedByTwoLoopRegions()
    {
        var result = WorkflowLoopRegionDraftReader.Read(
            """
            {
              "nodes": [
                {"node_instance_id":"start_1"},
                {"node_instance_id":"judge_1"},
                {"node_instance_id":"start_2"},
                {"node_instance_id":"judge_2"},
                {"node_instance_id":"shared_body"}
              ],
              "connections": [],
              "control_protocol": {
                "mode": "preview",
                "loop_regions": [
                  {"loop_id":"loop_1","start_node_id":"start_1","judge_node_id":"judge_1","body_node_ids":["shared_body"]},
                  {"loop_id":"loop_2","start_node_id":"start_2","judge_node_id":"judge_2","body_node_ids":["shared_body"]}
                ]
              }
            }
            """);

        Assert.AreEqual(
            WorkflowLoopRegionDraftReadStatus.OverlappingLoopNode,
            result.Status);
        Assert.AreEqual("loop_2", result.ProblemLoopId);
        Assert.AreEqual("NESTED_LOOP_REGION_UNAVAILABLE", result.Warning);
    }
}
