using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class WorkflowDefinitionLinearChainAnalyzer
{
    public static WorkflowDefinitionLinearChainAnalysis Analyze(
        string workflowDefinitionDraftJson)
    {
        return Analyze(
            WorkflowDefinitionDraftSnapshot.Parse(workflowDefinitionDraftJson));
    }

    public static WorkflowDefinitionLinearChainAnalysis Analyze(
        WorkflowDefinitionDraftSnapshot snapshot)
    {
        if (!snapshot.Succeeded)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected(
                snapshot.Warning ?? "WORKFLOW_DRAFT_JSON_INVALID");
        }

        var root = snapshot.Root;
        if (root.ValueKind != JsonValueKind.Object)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (!TryGetArray(root, "nodes", out var nodes))
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("WORKFLOW_DRAFT_NODES_MISSING");
        }

        if (!TryGetArray(root, "connections", out var connections))
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("WORKFLOW_DRAFT_CONNECTIONS_MISSING");
        }

        var nodeIds = ReadNodeIds(nodes);
        if (nodeIds is null)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("NODE_INSTANCE_ID_REQUIRED");
        }

        if (nodeIds.Count <= 1 && connections.GetArrayLength() == 0)
        {
            return WorkflowDefinitionLinearChainAnalysis.Linear(nodeIds);
        }

        var connectionRead = ReadConnections(connections, nodeIds);
        if (!connectionRead.Succeeded)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected(connectionRead.Warning);
        }

        if (connectionRead.Connections.Count != nodeIds.Count - 1)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_DISCONNECTED");
        }

        var incoming = new Dictionary<string, string>(StringComparer.Ordinal);
        var outgoing = new Dictionary<string, string>(StringComparer.Ordinal);
        foreach (var connection in connectionRead.Connections)
        {
            if (outgoing.ContainsKey(connection.SourceNodeId))
            {
                return WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_BRANCHING");
            }

            if (incoming.ContainsKey(connection.TargetNodeId))
            {
                return WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_MERGING");
            }

            outgoing[connection.SourceNodeId] = connection.TargetNodeId;
            incoming[connection.TargetNodeId] = connection.SourceNodeId;
        }

        var sources = nodeIds.Where(nodeId => !incoming.ContainsKey(nodeId)).ToArray();
        var sinks = nodeIds.Where(nodeId => !outgoing.ContainsKey(nodeId)).ToArray();
        if (sources.Length != 1 || sinks.Length != 1)
        {
            return WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_NOT_SINGLE_CHAIN");
        }

        var orderedNodeIds = new List<string>();
        var visited = new HashSet<string>(StringComparer.Ordinal);
        var current = sources[0];
        while (true)
        {
            if (!visited.Add(current))
            {
                return WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_CYCLE");
            }

            orderedNodeIds.Add(current);
            if (!outgoing.TryGetValue(current, out var next))
            {
                break;
            }

            current = next;
        }

        return orderedNodeIds.Count == nodeIds.Count
            ? WorkflowDefinitionLinearChainAnalysis.Linear(orderedNodeIds)
            : WorkflowDefinitionLinearChainAnalysis.Rejected("LINEAR_CHAIN_DISCONNECTED");
    }

    private static bool TryGetArray(
        JsonElement root,
        string propertyName,
        out JsonElement array)
    {
        if (root.TryGetProperty(propertyName, out array) &&
            array.ValueKind == JsonValueKind.Array)
        {
            return true;
        }

        array = default;
        return false;
    }

    private static IReadOnlyList<string>? ReadNodeIds(JsonElement nodes)
    {
        var nodeIds = new List<string>();
        var seen = new HashSet<string>(StringComparer.Ordinal);
        foreach (var node in nodes.EnumerateArray())
        {
            if (node.ValueKind != JsonValueKind.Object ||
                !node.TryGetProperty("node_instance_id", out var nodeIdElement) ||
                nodeIdElement.ValueKind != JsonValueKind.String)
            {
                return null;
            }

            var nodeId = nodeIdElement.GetString();
            if (string.IsNullOrWhiteSpace(nodeId) ||
                !seen.Add(nodeId))
            {
                return null;
            }

            nodeIds.Add(nodeId);
        }

        return nodeIds;
    }

    private static ConnectionReadResult ReadConnections(
        JsonElement connections,
        IReadOnlyCollection<string> nodeIds)
    {
        var knownNodeIds = nodeIds.ToHashSet(StringComparer.Ordinal);
        var connectionIds = new HashSet<string>(StringComparer.Ordinal);
        var result = new List<LinearConnection>();
        foreach (var connection in connections.EnumerateArray())
        {
            if (connection.ValueKind != JsonValueKind.Object)
            {
                return ConnectionReadResult.Rejected("CONNECTION_UNSUPPORTED");
            }

            var connectionId = ReadRequiredString(connection, "connection_id");
            if (connectionId is null)
            {
                return ConnectionReadResult.Rejected("CONNECTION_ID_REQUIRED");
            }

            if (!connectionIds.Add(connectionId))
            {
                return ConnectionReadResult.Rejected("CONNECTION_ALREADY_EXISTS");
            }

            var sourceNodeId = ReadRequiredString(connection, "source_node_id");
            if (sourceNodeId is null)
            {
                return ConnectionReadResult.Rejected("SOURCE_NODE_ID_REQUIRED");
            }

            var targetNodeId = ReadRequiredString(connection, "target_node_id");
            if (targetNodeId is null)
            {
                return ConnectionReadResult.Rejected("TARGET_NODE_ID_REQUIRED");
            }

            if (!knownNodeIds.Contains(sourceNodeId))
            {
                return ConnectionReadResult.Rejected("SOURCE_NODE_NOT_FOUND");
            }

            if (!knownNodeIds.Contains(targetNodeId))
            {
                return ConnectionReadResult.Rejected("TARGET_NODE_NOT_FOUND");
            }

            if (string.Equals(sourceNodeId, targetNodeId, StringComparison.Ordinal))
            {
                return ConnectionReadResult.Rejected("LINEAR_CHAIN_CYCLE");
            }

            result.Add(
                new LinearConnection(
                    connectionId,
                    sourceNodeId,
                    targetNodeId));
        }

        return ConnectionReadResult.Success(result);
    }

    private static string? ReadRequiredString(JsonElement element, string propertyName)
    {
        if (!element.TryGetProperty(propertyName, out var value) ||
            value.ValueKind != JsonValueKind.String)
        {
            return null;
        }

        var text = value.GetString();
        return string.IsNullOrWhiteSpace(text) ? null : text;
    }

    private sealed record LinearConnection(
        string ConnectionId,
        string SourceNodeId,
        string TargetNodeId);

    private sealed record ConnectionReadResult
    {
        public bool Succeeded { get; private init; }

        public string Warning { get; private init; } = string.Empty;

        public IReadOnlyList<LinearConnection> Connections { get; private init; } = [];

        public static ConnectionReadResult Success(
            IReadOnlyList<LinearConnection> connections)
        {
            return new ConnectionReadResult
            {
                Succeeded = true,
                Connections = connections,
            };
        }

        public static ConnectionReadResult Rejected(string warning)
        {
            return new ConnectionReadResult
            {
                Warning = warning,
            };
        }
    }
}
