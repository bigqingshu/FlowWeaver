using System.Linq;
using Avalonia_UI.Models;
using Microsoft.VisualStudio.TestTools.UnitTesting;

namespace Avalonia_UI.Tests;

[TestClass]
public sealed class WorkflowDefinitionLinearChainAnalyzerTests
{
    [TestMethod]
    public void AnalyzeReturnsOrderedNodeIdsForSimpleLinearChain()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "target_node_id": "filter"},
                {"connection_id": "filter_to_sink", "source_node_id": "filter", "target_node_id": "sink"}
              ]
            }
            """);

        Assert.IsTrue(result.IsLinear);
        CollectionAssert.AreEqual(
            new[] { "source", "filter", "sink" },
            result.NodeInstanceIds.ToArray());
        Assert.IsNull(result.Warning);
    }

    [TestMethod]
    public void AnalyzeAcceptsSingleNodeWithoutConnections()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"}
              ],
              "connections": []
            }
            """);

        Assert.IsTrue(result.IsLinear);
        CollectionAssert.AreEqual(
            new[] { "source" },
            result.NodeInstanceIds.ToArray());
    }

    [TestMethod]
    public void AnalyzeRejectsBranchingChain()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "left"},
                {"node_instance_id": "right"}
              ],
              "connections": [
                {"connection_id": "source_to_left", "source_node_id": "source", "target_node_id": "left"},
                {"connection_id": "source_to_right", "source_node_id": "source", "target_node_id": "right"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("LINEAR_CHAIN_BRANCHING", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsMergingChain()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "left"},
                {"node_instance_id": "right"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "left_to_sink", "source_node_id": "left", "target_node_id": "sink"},
                {"connection_id": "right_to_sink", "source_node_id": "right", "target_node_id": "sink"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("LINEAR_CHAIN_MERGING", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsDisconnectedNodes()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "filter"},
                {"node_instance_id": "orphan"}
              ],
              "connections": [
                {"connection_id": "source_to_filter", "source_node_id": "source", "target_node_id": "filter"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("LINEAR_CHAIN_DISCONNECTED", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsUnknownNodeReferences()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "source_to_missing", "source_node_id": "source", "target_node_id": "missing"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("TARGET_NODE_NOT_FOUND", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsDuplicateConnectionIds()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"},
                {"node_instance_id": "middle"},
                {"node_instance_id": "sink"}
              ],
              "connections": [
                {"connection_id": "duplicate", "source_node_id": "source", "target_node_id": "middle"},
                {"connection_id": "duplicate", "source_node_id": "middle", "target_node_id": "sink"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("CONNECTION_ALREADY_EXISTS", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsCycles()
    {
        var result = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """
            {
              "schema_version": "1.0",
              "nodes": [
                {"node_instance_id": "source"}
              ],
              "connections": [
                {"connection_id": "source_to_source", "source_node_id": "source", "target_node_id": "source"}
              ]
            }
            """);

        Assert.IsFalse(result.IsLinear);
        Assert.AreEqual("LINEAR_CHAIN_CYCLE", result.Warning);
    }

    [TestMethod]
    public void AnalyzeRejectsInvalidDraftShape()
    {
        var invalidJson = WorkflowDefinitionLinearChainAnalyzer.Analyze("{");
        var missingNodes = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """{"connections":[]}""");
        var missingConnections = WorkflowDefinitionLinearChainAnalyzer.Analyze(
            """{"nodes":[]}""");

        Assert.IsFalse(invalidJson.IsLinear);
        Assert.AreEqual("WORKFLOW_DRAFT_JSON_INVALID", invalidJson.Warning);
        Assert.IsFalse(missingNodes.IsLinear);
        Assert.AreEqual("WORKFLOW_DRAFT_NODES_MISSING", missingNodes.Warning);
        Assert.IsFalse(missingConnections.IsLinear);
        Assert.AreEqual("WORKFLOW_DRAFT_CONNECTIONS_MISSING", missingConnections.Warning);
    }
}
