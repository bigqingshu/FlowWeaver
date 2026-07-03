using System;
using System.Collections.Generic;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class WorkflowDefinitionDraftNodePatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static WorkflowDefinitionDraftNodePatchResult AddNode(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        string nodeType,
        string nodeVersion,
        string? displayName,
        JsonElement config)
    {
        if (string.IsNullOrWhiteSpace(nodeInstanceId))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(nodeType))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeTypeRequired,
                "NODE_TYPE_REQUIRED");
        }

        if (string.IsNullOrWhiteSpace(nodeVersion))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeVersionRequired,
                "NODE_VERSION_REQUIRED");
        }

        if (config.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.ConfigUnsupported,
                "CONFIG_UNSUPPORTED");
        }

        JsonNode? root;
        try
        {
            root = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        if (root is not JsonObject rootObject)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (rootObject["nodes"] is not JsonArray nodes)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        if (rootObject["connections"] is not JsonArray)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.ConnectionsMissing,
                "WORKFLOW_DRAFT_CONNECTIONS_MISSING");
        }

        foreach (var node in nodes)
        {
            if (node is JsonObject nodeObject &&
                string.Equals(
                    GetStringValue(nodeObject, "node_instance_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal))
            {
                return Failed(
                    WorkflowDefinitionDraftNodePatchStatus.NodeAlreadyExists,
                    "NODE_ALREADY_EXISTS");
            }
        }

        var newNode = new JsonObject
        {
            ["node_instance_id"] = nodeInstanceId,
            ["node_type"] = nodeType,
            ["node_version"] = nodeVersion,
            ["config"] = JsonNode.Parse(config.GetRawText()),
        };

        if (!string.IsNullOrWhiteSpace(displayName))
        {
            newNode["display_name"] = displayName;
        }

        nodes.Add(newNode);
        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                rootObject.ToJsonString(IndentedJsonOptions),
        };
    }

    private static WorkflowDefinitionDraftNodePatchResult Failed(
        WorkflowDefinitionDraftNodePatchStatus status,
        string warning)
    {
        return new WorkflowDefinitionDraftNodePatchResult
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

    public static WorkflowDefinitionDraftNodePatchResult DeleteNode(
        string workflowDefinitionDraftJson,
        string nodeInstanceId)
    {
        if (string.IsNullOrWhiteSpace(nodeInstanceId))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        var readResult = ReadMutableDraft(workflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            return Failed(readResult.Status, readResult.Warning);
        }

        var nodes = readResult.Nodes;
        var targetIndex = -1;
        for (var index = 0; index < nodes.Count; index++)
        {
            if (nodes[index] is JsonObject nodeObject &&
                string.Equals(
                    GetStringValue(nodeObject, "node_instance_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal))
            {
                targetIndex = index;
                break;
            }
        }

        if (targetIndex < 0)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeNotFound,
                "NODE_NOT_FOUND");
        }

        var removedConnections = new List<WorkflowDefinitionDraftConnection>();
        for (var index = readResult.Connections.Count - 1; index >= 0; index--)
        {
            if (readResult.Connections[index] is JsonObject connectionObject &&
                (string.Equals(
                    GetStringValue(connectionObject, "source_node_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal)
                || string.Equals(
                    GetStringValue(connectionObject, "target_node_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal)))
            {
                removedConnections.Insert(0, ReadConnection(connectionObject));
                readResult.Connections.RemoveAt(index);
            }
        }

        nodes.RemoveAt(targetIndex);
        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            RemovedConnections = removedConnections,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
        };
    }

    private static WorkflowDefinitionDraftConnection ReadConnection(
        JsonObject connectionObject)
    {
        return new WorkflowDefinitionDraftConnection
        {
            ConnectionId = GetStringValue(connectionObject, "connection_id") ?? string.Empty,
            SourceNodeId = GetStringValue(connectionObject, "source_node_id") ?? string.Empty,
            SourcePort = GetStringValue(connectionObject, "source_port") ?? string.Empty,
            TargetNodeId = GetStringValue(connectionObject, "target_node_id") ?? string.Empty,
            TargetPort = GetStringValue(connectionObject, "target_port") ?? string.Empty,
        };
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
                WorkflowDefinitionDraftNodePatchStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        if (root is not JsonObject rootObject)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftNodePatchStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (rootObject["nodes"] is not JsonArray nodes)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodesMissing,
                "WORKFLOW_DRAFT_NODES_MISSING");
        }

        if (rootObject["connections"] is not JsonArray connections)
        {
            return MutableWorkflowDraftReadResult.Failed(
                WorkflowDefinitionDraftNodePatchStatus.ConnectionsMissing,
                "WORKFLOW_DRAFT_CONNECTIONS_MISSING");
        }

        return MutableWorkflowDraftReadResult.Success(rootObject, nodes, connections);
    }

    private sealed record MutableWorkflowDraftReadResult
    {
        public WorkflowDefinitionDraftNodePatchStatus Status { get; private init; }

        public string Warning { get; private init; } = string.Empty;

        public JsonObject Root { get; private init; } = new();

        public JsonArray Nodes { get; private init; } = new();

        public JsonArray Connections { get; private init; } = new();

        public bool Succeeded => Status == WorkflowDefinitionDraftNodePatchStatus.Succeeded;

        public static MutableWorkflowDraftReadResult Success(
            JsonObject root,
            JsonArray nodes,
            JsonArray connections)
        {
            return new MutableWorkflowDraftReadResult
            {
                Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
                Root = root,
                Nodes = nodes,
                Connections = connections,
            };
        }

        public static MutableWorkflowDraftReadResult Failed(
            WorkflowDefinitionDraftNodePatchStatus status,
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
