using System.Collections.Generic;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class WorkflowDefinitionDraftStructureBuilder
{
    public static WorkflowDefinitionDraftStructure Build(string workflowDefinitionDraftJson)
    {
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Unsupported(
                WorkflowDefinitionDraftStructureStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        using (document)
        {
            var root = document.RootElement;
            if (root.ValueKind != JsonValueKind.Object)
            {
                return Unsupported(
                    WorkflowDefinitionDraftStructureStatus.RootNotObject,
                    "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
            }

            if (!TryGetArray(root, "nodes", out var nodes))
            {
                return Unsupported(
                    WorkflowDefinitionDraftStructureStatus.NodesMissing,
                    "WORKFLOW_DRAFT_NODES_MISSING");
            }

            if (!TryGetArray(root, "connections", out var connections))
            {
                return Unsupported(
                    WorkflowDefinitionDraftStructureStatus.ConnectionsMissing,
                    "WORKFLOW_DRAFT_CONNECTIONS_MISSING");
            }

            var warnings = new List<string>();
            return new WorkflowDefinitionDraftStructure
            {
                Status = WorkflowDefinitionDraftStructureStatus.Supported,
                Nodes = ReadNodes(nodes, warnings),
                Connections = ReadConnections(connections, warnings),
                Warnings = warnings,
            };
        }
    }

    private static WorkflowDefinitionDraftStructure Unsupported(
        WorkflowDefinitionDraftStructureStatus status,
        string warning)
    {
        return new WorkflowDefinitionDraftStructure
        {
            Status = status,
            Warnings = [warning],
        };
    }

    private static IReadOnlyList<WorkflowDefinitionDraftNode> ReadNodes(
        JsonElement nodes,
        List<string> warnings)
    {
        var result = new List<WorkflowDefinitionDraftNode>();
        foreach (var node in nodes.EnumerateArray())
        {
            if (node.ValueKind != JsonValueKind.Object)
            {
                warnings.Add("WORKFLOW_DRAFT_NODE_SKIPPED");
                continue;
            }

            if (!TryGetString(node, "node_instance_id", out var nodeInstanceId))
            {
                warnings.Add("WORKFLOW_DRAFT_NODE_INSTANCE_ID_MISSING");
                continue;
            }

            result.Add(new WorkflowDefinitionDraftNode
            {
                NodeInstanceId = nodeInstanceId,
                NodeType = GetStringOrEmpty(node, "node_type"),
                NodeVersion = GetStringOrEmpty(node, "node_version"),
                DisplayName = GetStringOrEmpty(node, "display_name"),
                Enabled = GetBoolOrDefault(node, "enabled", defaultValue: true),
                HasConfig = HasObject(node, "config"),
            });
        }

        return result;
    }

    private static IReadOnlyList<WorkflowDefinitionDraftConnection> ReadConnections(
        JsonElement connections,
        List<string> warnings)
    {
        var result = new List<WorkflowDefinitionDraftConnection>();
        foreach (var connection in connections.EnumerateArray())
        {
            if (connection.ValueKind != JsonValueKind.Object)
            {
                warnings.Add("WORKFLOW_DRAFT_CONNECTION_SKIPPED");
                continue;
            }

            if (!TryGetString(connection, "connection_id", out var connectionId))
            {
                warnings.Add("WORKFLOW_DRAFT_CONNECTION_ID_MISSING");
                continue;
            }

            result.Add(new WorkflowDefinitionDraftConnection
            {
                ConnectionId = connectionId,
                SourceNodeId = GetStringOrEmpty(connection, "source_node_id"),
                SourcePort = GetStringOrEmpty(connection, "source_port"),
                TargetNodeId = GetStringOrEmpty(connection, "target_node_id"),
                TargetPort = GetStringOrEmpty(connection, "target_port"),
            });
        }

        return result;
    }

    private static bool TryGetArray(
        JsonElement element,
        string propertyName,
        out JsonElement array)
    {
        if (element.TryGetProperty(propertyName, out array) &&
            array.ValueKind == JsonValueKind.Array)
        {
            return true;
        }

        array = default;
        return false;
    }

    private static bool TryGetString(
        JsonElement element,
        string propertyName,
        out string value)
    {
        if (element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String)
        {
            value = property.GetString() ?? string.Empty;
            return !string.IsNullOrWhiteSpace(value);
        }

        value = string.Empty;
        return false;
    }

    private static string GetStringOrEmpty(JsonElement element, string propertyName)
    {
        return TryGetString(element, propertyName, out var value) ? value : string.Empty;
    }

    private static bool GetBoolOrDefault(
        JsonElement element,
        string propertyName,
        bool defaultValue)
    {
        if (element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind is JsonValueKind.True or JsonValueKind.False)
        {
            return property.GetBoolean();
        }

        return defaultValue;
    }

    private static bool HasObject(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Object;
    }
}
