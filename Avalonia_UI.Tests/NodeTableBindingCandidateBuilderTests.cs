using System;
using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class NodeTableBindingCandidateBuilderTests
{
    [TestMethod]
    public void InputCandidatesContainOnlyDirectUpstreamDeclaredOutputs()
    {
        var snapshot = WorkflowDefinitionDraftSnapshot.Parse(
            """
            {
              "nodes": [
                {"node_instance_id":"ancestor","node_type":"source","node_version":"1","config":{}},
                {"node_instance_id":"direct","node_type":"source","node_version":"1","config":{}},
                {"node_instance_id":"target","node_type":"target","node_version":"1","config":{}}
              ],
              "connections": [
                {"connection_id":"a","source_node_id":"ancestor","target_node_id":"direct"},
                {"connection_id":"b","source_node_id":"direct","target_node_id":"target"}
              ]
            }
            """);
        var builder = new NodeTableBindingCandidateBuilder();

        var result = builder.Build(
            snapshot,
            "revision-1",
            "target",
            "catalog-1",
            [SourceDefinition()],
            []);

        Assert.HasCount(1, result.InputCandidates);
        Assert.AreEqual("direct", result.InputCandidates[0].SourceNodeInstanceId);
        Assert.AreEqual("out", result.InputCandidates[0].OutputSlot);
    }

    [TestMethod]
    public void SameNamedInputsRemainDistinctWhileExistingTargetsUseLogicalIdentity()
    {
        var snapshot = WorkflowDefinitionDraftSnapshot.Parse(
            """
            {
              "nodes": [
                {"node_instance_id":"left","node_type":"source","node_version":"1","config":{"output_targets":{"out":{"target_kind":"new_memory","logical_table_id":"orders"}}}},
                {"node_instance_id":"right","node_type":"source","node_version":"1","config":{"output_targets":{"out":{"target_kind":"new_memory","logical_table_id":"orders"}}}},
                {"node_instance_id":"target","node_type":"target","node_version":"1","config":{}}
              ],
              "connections": [
                {"connection_id":"a","source_node_id":"left","target_node_id":"target"},
                {"connection_id":"b","source_node_id":"right","target_node_id":"target"}
              ]
            }
            """);
        var oldTable = Table("ref-left", "left", 1);
        var latestTable = Table("ref-right", "right", 2);
        var builder = new NodeTableBindingCandidateBuilder();

        var result = builder.Build(
            snapshot,
            "revision-1",
            "target",
            "catalog-1",
            [SourceDefinition()],
            [oldTable, latestTable]);

        Assert.HasCount(2, result.InputCandidates);
        Assert.AreNotEqual(
            result.InputCandidates[0].SourceNodeInstanceId,
            result.InputCandidates[1].SourceNodeInstanceId);
        Assert.IsTrue(result.InputCandidates.All(candidate =>
            candidate.LogicalTableId == "orders" && candidate.OutputSlot == "out"));
        Assert.HasCount(1, result.ExistingOutputTargets);
        Assert.AreEqual("ref-right", result.ExistingOutputTargets[0].LatestTableRefId);
        Assert.AreEqual(2, result.ExistingOutputTargets[0].Version);
    }

    [TestMethod]
    public void CandidateCacheUsesRevisionNodeAndCatalogHash()
    {
        var snapshot = WorkflowDefinitionDraftSnapshot.Parse(
            """{"nodes":[{"node_instance_id":"target","node_type":"target","node_version":"1","config":{}}],"connections":[]}""");
        var builder = new NodeTableBindingCandidateBuilder();

        var first = builder.Build(snapshot, "r1", "target", "c1", [], []);
        var same = builder.Build(snapshot, "r1", "target", "c1", [], []);
        var changedRevision = builder.Build(snapshot, "r2", "target", "c1", [], []);
        var changedNode = builder.Build(snapshot, "r2", "other", "c1", [], []);
        var changedCatalog = builder.Build(snapshot, "r2", "other", "c2", [], []);

        Assert.AreSame(first, same);
        Assert.AreNotSame(same, changedRevision);
        Assert.AreNotSame(changedRevision, changedNode);
        Assert.AreNotSame(changedNode, changedCatalog);
    }

    private static NodeDefinitionDto SourceDefinition()
    {
        return new NodeDefinitionDto
        {
            NodeType = "source",
            NodeVersion = "1",
            OutputTableSlots =
            [
                new NodeTableOutputSlotDto
                {
                    Name = "out",
                    DisplayName = "Result",
                    DefaultRole = "CURRENT",
                    AllowCurrent = true,
                    AllowNewMemory = true,
                },
            ],
        };
    }

    private static TableRefDto Table(string id, string sourceNodeId, int version)
    {
        return new TableRefDto
        {
            TableRefId = id,
            WorkflowRunId = "run-1",
            SourceNodeInstanceId = sourceNodeId,
            OutputSlot = "out",
            Role = "AUXILIARY",
            StorageKind = "MEMORY",
            LogicalTableId = "orders",
            Version = version,
            LifecycleStatus = "ACTIVE",
            CreatedAt = DateTimeOffset.UnixEpoch.AddMinutes(version),
        };
    }
}
