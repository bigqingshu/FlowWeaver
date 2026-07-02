using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class WorkflowDefinitionDraftConnectionPatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static WorkflowDefinitionDraftConnectionPatchResult AddConnection(
        string workflowDefinitionDraftJson,
        string connectionId,
        string sourceNodeId,
        string sourcePort,
        string targetNodeId,
        string targetPort)
    {
        var requiredResult = ValidateRequiredFields(
            connectionId,
            sourceNodeId,
            sourcePort,
            targetNodeId,
            targetPort);
        if (requiredResult is not null)
        {
            return requiredResult;
        }

        var readResult = ReadMutableDraft(workflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            return Failed(readResult.Status, readResult.Warning);
        }

        if (ConnectionExists(readResult.Connections, connectionId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.ConnectionAlreadyExists,
                "CONNECTION_ALREADY_EXISTS");
        }

        if (!NodeExists(readResult.Nodes, sourceNodeId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.SourceNodeNotFound,
                "SOURCE_NODE_NOT_FOUND");
        }

        if (!NodeExists(readResult.Nodes, targetNodeId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.TargetNodeNotFound,
                "TARGET_NODE_NOT_FOUND");
        }

        readResult.Connections.Add(
            new JsonObject
            {
                ["connection_id"] = connectionId,
                ["source_node_id"] = sourceNodeId,
                ["source_port"] = sourcePort,
                ["target_node_id"] = targetNodeId,
                ["target_port"] = targetPort,
            });

        return Succeeded(readResult.Root);
    }

    public static WorkflowDefinitionDraftConnectionPatchResult DeleteConnection(
        string workflowDefinitionDraftJson,
        string connectionId)
    {
        if (string.IsNullOrWhiteSpace(connectionId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.ConnectionIdRequired,
                "CONNECTION_ID_REQUIRED");
        }

        var readResult = ReadMutableDraft(workflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            return Failed(readResult.Status, readResult.Warning);
        }

        var targetIndex = -1;
        for (var index = 0; index < readResult.Connections.Count; index++)
        {
            if (readResult.Connections[index] is JsonObject connectionObject &&
                string.Equals(
                    GetStringValue(connectionObject, "connection_id"),
                    connectionId,
                    StringComparison.Ordinal))
            {
                targetIndex = index;
                break;
            }
        }

        if (targetIndex < 0)
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.ConnectionNotFound,
                "CONNECTION_NOT_FOUND");
        }

        readResult.Connections.RemoveAt(targetIndex);
        return Succeeded(readResult.Root);
    }

    private static WorkflowDefinitionDraftConnectionPatchResult? ValidateRequiredFields(
        string connectionId,
        string sourceNodeId,
        string sourcePort,
        string targetNodeId,
        string targetPort)
    {
        if (string.IsNullOrWhiteSpace(connectionId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.ConnectionIdRequired,
                "CONNECTION_ID_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(sourceNodeId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.SourceNodeIdRequired,
                "SOURCE_NODE_ID_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(sourcePort))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.SourcePortRequired,
                "SOURCE_PORT_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(targetNodeId))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.TargetNodeIdRequired,
                "TARGET_NODE_ID_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(targetPort))
        {
            return Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.TargetPortRequired,
                "TARGET_PORT_REQUIRED");
        }

        return null;
    }

    private static bool NodeExists(JsonArray nodes, string nodeInstanceId)
    {
        foreach (var node in nodes)
        {
            if (node is JsonObject nodeObject &&
                string.Equals(
                    GetStringValue(nodeObject, "node_instance_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private static bool ConnectionExists(JsonArray connections, string connectionId)
    {
        foreach (var connection in connections)
        {
            if (connection is JsonObject connectionObject &&
                string.Equals(
                    GetStringValue(connectionObject, "connection_id"),
                    connectionId,
                    StringComparison.Ordinal))
            {
                return true;
            }
        }

        return false;
    }

    private static WorkflowDefinitionDraftConnectionPatchResult Succeeded(
        JsonObject root)
    {
        return new WorkflowDefinitionDraftConnectionPatchResult
        {
            Status = WorkflowDefinitionDraftConnectionPatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                root.ToJsonString(IndentedJsonOptions),
        };
    }

    private static WorkflowDefinitionDraftConnectionPatchResult Failed(
        WorkflowDefinitionDraftConnectionPatchStatus status,
        string warning)
    {
        return new WorkflowDefinitionDraftConnectionPatchResult
        {
            Status = status,
            Warning = warning,
        };
    }

    private static string? GetStringValue(JsonObject jsonObject, string propertyName)
    {
        return jsonObject[propertyName] is JsonValue jsonValue &&
            jsonValue.TryGetValue<string>(out var value)
                ? value
                : null;
    }

    private static MutableWorkflowDraftReadResult ReadMutableDraft(
        string workflowDefinitionDraftJson)
    {
        JsonNode? root;
        try
        {
            root = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        if (root is not JsonObject rootObject)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (rootObject["nodes"] is not JsonArray nodes)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        if (rootObject["connections"] is not JsonArray connections)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftConnectionPatchStatus.ConnectionsMissing,
                "WORKFLOW_DRAFT_CONNECTIONS_MISSING");
        }

        return MutableWorkflowDraftReadResult.Success(rootObject, nodes, connections);
    }

    private sealed record MutableWorkflowDraftReadResult
    {
        public WorkflowDefinitionDraftConnectionPatchStatus Status { get; private init; }

        public string Warning { get; private init; } = string.Empty;

        public JsonObject Root { get; private init; } = new();

        public JsonArray Nodes { get; private init; } = new();

        public JsonArray Connections { get; private init; } = new();

        public bool Succeeded =>
            Status == WorkflowDefinitionDraftConnectionPatchStatus.Succeeded;

        public static MutableWorkflowDraftReadResult Success(
            JsonObject root,
            JsonArray nodes,
            JsonArray connections)
        {
            return new MutableWorkflowDraftReadResult
            {
                Status = WorkflowDefinitionDraftConnectionPatchStatus.Succeeded,
                Root = root,
                Nodes = nodes,
                Connections = connections,
            };
        }

        public static MutableWorkflowDraftReadResult Failed(
            WorkflowDefinitionDraftConnectionPatchStatus status,
            string warning)
        {
            return new MutableWorkflowDraftReadResult
            {
                Status = status,
                Warning = warning,
            };
        }
    }
}
