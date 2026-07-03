using System.Linq;
using System.Threading.Tasks;
using Avalonia_UI.Localization;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionDraftStructureBuilderTests
{
    [TestMethod]
    public void BuildReadsNodesAndConnectionsFromWorkflowDraft()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {
                  "node_instance_id": "source",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0",
                  "display_name": "Source",
                  "config": {"rows": 3}
                },
                {
                  "node_instance_id": "filter",
                  "node_type": "FilterRowsNode",
                  "node_version": "1.0",
                  "enabled": false
                }
              ],
              "connections": [
                {
                  "connection_id": "c1",
                  "source_node_id": "source",
                  "source_port": "out",
                  "target_node_id": "filter",
                  "target_port": "in"
                }
              ]
            }
            """);

        Assert.IsTrue(structure.IsSupported);
        Assert.AreEqual(WorkflowDefinitionDraftStructureStatus.Supported, structure.Status);
        Assert.AreEqual(2, structure.NodeCount);
        Assert.AreEqual(1, structure.ConnectionCount);
        Assert.IsEmpty(structure.Warnings);

        var source = structure.Nodes.Single(item => item.NodeInstanceId == "source");
        Assert.AreEqual("GenerateTestTableNode", source.NodeType);
        Assert.AreEqual("GenerateTestTableNode", source.NodeTypeDisplayName);
        Assert.AreEqual("1.0", source.NodeVersion);
        Assert.AreEqual("Source", source.DisplayName);
        Assert.IsTrue(source.Enabled);
        Assert.IsTrue(source.HasConfig);

        var filter = structure.Nodes.Single(item => item.NodeInstanceId == "filter");
        Assert.IsFalse(filter.Enabled);
        Assert.IsFalse(filter.HasConfig);

        var connection = structure.Connections.Single();
        Assert.AreEqual("c1", connection.ConnectionId);
        Assert.AreEqual("source", connection.SourceNodeId);
        Assert.AreEqual("out", connection.SourcePort);
        Assert.AreEqual("filter", connection.TargetNodeId);
        Assert.AreEqual("in", connection.TargetPort);
    }

    [TestMethod]
    public void BuildReturnsJsonInvalidWhenDraftCannotParse()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build("{");

        Assert.IsFalse(structure.IsSupported);
        Assert.AreEqual(WorkflowDefinitionDraftStructureStatus.JsonInvalid, structure.Status);
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_JSON_INVALID");
    }

    [TestMethod]
    public void BuildReturnsRootNotObjectForArrayDraft()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build("[]");

        Assert.IsFalse(structure.IsSupported);
        Assert.AreEqual(WorkflowDefinitionDraftStructureStatus.RootNotObject, structure.Status);
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
    }

    [TestMethod]
    public void BuildReturnsNodesMissingWhenNodesArrayIsMissing()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build(
            """{"connections":[]}""");

        Assert.IsFalse(structure.IsSupported);
        Assert.AreEqual(WorkflowDefinitionDraftStructureStatus.NodesMissing, structure.Status);
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_NODES_MISSING");
    }

    [TestMethod]
    public void BuildReturnsConnectionsMissingWhenConnectionsArrayIsMissing()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build(
            """{"nodes":[]}""");

        Assert.IsFalse(structure.IsSupported);
        Assert.AreEqual(
            WorkflowDefinitionDraftStructureStatus.ConnectionsMissing,
            structure.Status);
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_CONNECTIONS_MISSING");
    }

    [TestMethod]
    public void BuildSkipsMalformedNodeAndConnectionItemsWithWarnings()
    {
        var structure = WorkflowDefinitionDraftStructureBuilder.Build(
            """
            {
              "nodes": [
                1,
                {"node_type": "MissingId"},
                {"node_instance_id": "valid"}
              ],
              "connections": [
                "bad",
                {"source_node_id": "source"},
                {"connection_id": "c1"}
              ]
            }
            """);

        Assert.IsTrue(structure.IsSupported);
        Assert.HasCount(1, structure.Nodes);
        Assert.HasCount(1, structure.Connections);
        Assert.AreEqual("valid", structure.Nodes.Single().NodeInstanceId);
        Assert.AreEqual("c1", structure.Connections.Single().ConnectionId);
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_NODE_SKIPPED");
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_NODE_INSTANCE_ID_MISSING");
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_CONNECTION_SKIPPED");
        CollectionAssert.Contains(
            structure.Warnings.ToArray(),
            "WORKFLOW_DRAFT_CONNECTION_ID_MISSING");
    }

    [TestMethod]
    public async Task BuildLocalizesDraftNodeTypeDisplayNameWithoutChangingNodeType()
    {
        var localizationService = new JsonLocalizationService();
        await localizationService.SetLanguageAsync("zh-Hans");
        var structure = WorkflowDefinitionDraftStructureBuilder.Build(
            """
            {
              "nodes": [
                {
                  "node_instance_id": "generate",
                  "node_type": "GenerateTestTableNode",
                  "node_version": "1.0"
                },
                {
                  "node_instance_id": "custom",
                  "node_type": "CustomPluginNode",
                  "node_version": "1.0"
                }
              ],
              "connections": []
            }
            """,
            new DisplayTextFormatter(localizationService));

        Assert.IsTrue(structure.IsSupported);
        var generate = structure.Nodes.Single(item => item.NodeInstanceId == "generate");
        Assert.AreEqual("GenerateTestTableNode", generate.NodeType);
        Assert.AreEqual("生成测试表", generate.NodeTypeDisplayName);

        var custom = structure.Nodes.Single(item => item.NodeInstanceId == "custom");
        Assert.AreEqual("CustomPluginNode", custom.NodeType);
        Assert.AreEqual("CustomPluginNode", custom.NodeTypeDisplayName);
    }
}
