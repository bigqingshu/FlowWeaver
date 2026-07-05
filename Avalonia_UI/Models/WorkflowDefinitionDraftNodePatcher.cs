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
        JsonElement config,
        string? insertAfterNodeInstanceId = null,
        string? autoWireInputPort = null,
        string? autoWireOutputPort = null)
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

        if (rootObject["connections"] is not JsonArray connections)
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

        var insertIndex = nodes.Count;
        JsonObject? downstreamConnection = null;
        var downstreamConnectionIndex = -1;
        if (!string.IsNullOrWhiteSpace(insertAfterNodeInstanceId))
        {
            var anchorIndex = FindNodeIndex(nodes, insertAfterNodeInstanceId);
            if (anchorIndex < 0)
            {
                return Failed(
                    WorkflowDefinitionDraftNodePatchStatus.InsertAfterNodeNotFound,
                    "INSERT_AFTER_NODE_NOT_FOUND");
            }

            insertIndex = anchorIndex + 1;
            if (!string.IsNullOrWhiteSpace(autoWireInputPort) &&
                !string.IsNullOrWhiteSpace(autoWireOutputPort))
            {
                var downstreamConnections = FindOutgoingConnectionIndexes(
                    connections,
                    insertAfterNodeInstanceId);
                if (downstreamConnections.Count == 1 &&
                    connections[downstreamConnections[0]] is JsonObject foundConnection)
                {
                    downstreamConnection = foundConnection;
                    downstreamConnectionIndex = downstreamConnections[0];
                }
            }
        }

        nodes.Insert(insertIndex, newNode);
        var addedConnections = new List<WorkflowDefinitionDraftConnection>();
        var removedConnections = new List<WorkflowDefinitionDraftConnection>();
        if (downstreamConnection is not null &&
            !string.IsNullOrWhiteSpace(autoWireInputPort) &&
            !string.IsNullOrWhiteSpace(autoWireOutputPort))
        {
            var removedConnection = ReadConnection(downstreamConnection);
            removedConnections.Add(removedConnection);
            connections.RemoveAt(downstreamConnectionIndex);

            var anchorToNew = new WorkflowDefinitionDraftConnection
            {
                ConnectionId = BuildUniqueConnectionId(
                    connections,
                    removedConnection.SourceNodeId,
                    nodeInstanceId),
                SourceNodeId = removedConnection.SourceNodeId,
                SourcePort = removedConnection.SourcePort,
                TargetNodeId = nodeInstanceId,
                TargetPort = autoWireInputPort,
            };
            var newToDownstream = new WorkflowDefinitionDraftConnection
            {
                ConnectionId = BuildUniqueConnectionId(
                    connections,
                    nodeInstanceId,
                    removedConnection.TargetNodeId,
                    [anchorToNew.ConnectionId]),
                SourceNodeId = nodeInstanceId,
                SourcePort = autoWireOutputPort,
                TargetNodeId = removedConnection.TargetNodeId,
                TargetPort = removedConnection.TargetPort,
            };

            connections.Add(CreateConnectionObject(anchorToNew));
            connections.Add(CreateConnectionObject(newToDownstream));
            addedConnections.Add(anchorToNew);
            addedConnections.Add(newToDownstream);
        }

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            RemovedConnections = removedConnections,
            AddedConnections = addedConnections,
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

    private static int FindNodeIndex(JsonArray nodes, string nodeInstanceId)
    {
        for (var index = 0; index < nodes.Count; index++)
        {
            if (nodes[index] is JsonObject nodeObject &&
                string.Equals(
                    GetStringValue(nodeObject, "node_instance_id"),
                    nodeInstanceId,
                    StringComparison.Ordinal))
            {
                return index;
            }
        }

        return -1;
    }

    private static List<int> FindOutgoingConnectionIndexes(
        JsonArray connections,
        string sourceNodeId)
    {
        var result = new List<int>();
        for (var index = 0; index < connections.Count; index++)
        {
            if (connections[index] is JsonObject connectionObject &&
                string.Equals(
                    GetStringValue(connectionObject, "source_node_id"),
                    sourceNodeId,
                    StringComparison.Ordinal))
            {
                result.Add(index);
            }
        }

        return result;
    }

    private static List<int> FindIncomingConnectionIndexes(
        JsonArray connections,
        string targetNodeId)
    {
        var result = new List<int>();
        for (var index = 0; index < connections.Count; index++)
        {
            if (connections[index] is JsonObject connectionObject &&
                string.Equals(
                    GetStringValue(connectionObject, "target_node_id"),
                    targetNodeId,
                    StringComparison.Ordinal))
            {
                result.Add(index);
            }
        }

        return result;
    }

    private static WorkflowDefinitionDraftConnection? TryCreateLinearBridgeConnection(
        JsonArray connections,
        string nodeInstanceId)
    {
        var incomingConnectionIndexes = FindIncomingConnectionIndexes(
            connections,
            nodeInstanceId);
        var outgoingConnectionIndexes = FindOutgoingConnectionIndexes(
            connections,
            nodeInstanceId);
        if (incomingConnectionIndexes.Count != 1 ||
            outgoingConnectionIndexes.Count != 1 ||
            connections[incomingConnectionIndexes[0]] is not JsonObject incomingConnectionObject ||
            connections[outgoingConnectionIndexes[0]] is not JsonObject outgoingConnectionObject)
        {
            return null;
        }

        var incomingConnection = ReadConnection(incomingConnectionObject);
        var outgoingConnection = ReadConnection(outgoingConnectionObject);
        if (string.IsNullOrWhiteSpace(incomingConnection.SourcePort) ||
            string.IsNullOrWhiteSpace(outgoingConnection.TargetPort))
        {
            return null;
        }

        return new WorkflowDefinitionDraftConnection
        {
            ConnectionId = BuildUniqueConnectionId(
                connections,
                incomingConnection.SourceNodeId,
                outgoingConnection.TargetNodeId),
            SourceNodeId = incomingConnection.SourceNodeId,
            SourcePort = incomingConnection.SourcePort,
            TargetNodeId = outgoingConnection.TargetNodeId,
            TargetPort = outgoingConnection.TargetPort,
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

    private static JsonObject CreateConnectionObject(
        WorkflowDefinitionDraftConnection connection)
    {
        return new JsonObject
        {
            ["connection_id"] = connection.ConnectionId,
            ["source_node_id"] = connection.SourceNodeId,
            ["source_port"] = connection.SourcePort,
            ["target_node_id"] = connection.TargetNodeId,
            ["target_port"] = connection.TargetPort,
        };
    }

    private static string BuildUniqueConnectionId(
        JsonArray connections,
        string sourceNodeId,
        string targetNodeId,
        IReadOnlyCollection<string>? reservedIds = null)
    {
        var existingIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var connection in connections)
        {
            if (connection is JsonObject connectionObject)
            {
                var connectionId = GetStringValue(connectionObject, "connection_id");
                if (!string.IsNullOrWhiteSpace(connectionId))
                {
                    existingIds.Add(connectionId);
                }
            }
        }

        if (reservedIds is not null)
        {
            foreach (var reservedId in reservedIds)
            {
                existingIds.Add(reservedId);
            }
        }

        var baseId =
            $"{BuildSnakeCaseIdentifier(sourceNodeId, "source")}_to_{BuildSnakeCaseIdentifier(targetNodeId, "target")}";
        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    private static string BuildSnakeCaseIdentifier(string source, string fallback)
    {
        var builder = new System.Text.StringBuilder();
        for (var index = 0; index < source.Length; index++)
        {
            var current = source[index];
            if (char.IsLetterOrDigit(current))
            {
                var previous = index > 0 ? source[index - 1] : '\0';
                var next = index + 1 < source.Length ? source[index + 1] : '\0';
                var shouldSeparate =
                    char.IsUpper(current)
                    && builder.Length > 0
                    && builder[^1] != '_'
                    && (char.IsLower(previous)
                        || char.IsDigit(previous)
                        || char.IsLower(next));

                if (shouldSeparate)
                {
                    builder.Append('_');
                }

                builder.Append(char.ToLowerInvariant(current));
            }
            else if (builder.Length > 0 && builder[^1] != '_')
            {
                builder.Append('_');
            }
        }

        var value = builder.ToString().Trim('_');
        return string.IsNullOrWhiteSpace(value) ? fallback : value;
    }

    private static string BuildUniqueNodeInstanceId(
        JsonArray nodes,
        string sourceNodeInstanceId)
    {
        var existingIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var node in nodes)
        {
            if (node is JsonObject nodeObject)
            {
                var nodeInstanceId = GetStringValue(nodeObject, "node_instance_id");
                if (!string.IsNullOrWhiteSpace(nodeInstanceId))
                {
                    existingIds.Add(nodeInstanceId);
                }
            }
        }

        var baseId = $"{sourceNodeInstanceId}_copy";
        var candidate = baseId;
        var suffix = 2;
        while (existingIds.Contains(candidate))
        {
            candidate = $"{baseId}_{suffix}";
            suffix++;
        }

        return candidate;
    }

    public static WorkflowDefinitionDraftNodePatchResult DeleteNode(
        string workflowDefinitionDraftJson,
        string nodeInstanceId)
    {
        return DeleteNodeCore(
            workflowDefinitionDraftJson,
            nodeInstanceId,
            bridgeLinearConnections: false);
    }

    public static WorkflowDefinitionDraftNodePatchResult DeleteNodeWithLinearBridge(
        string workflowDefinitionDraftJson,
        string nodeInstanceId)
    {
        return DeleteNodeCore(
            workflowDefinitionDraftJson,
            nodeInstanceId,
            bridgeLinearConnections: true);
    }

    private static WorkflowDefinitionDraftNodePatchResult DeleteNodeCore(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        bool bridgeLinearConnections)
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

        WorkflowDefinitionDraftConnection? bridgeConnection = null;
        if (bridgeLinearConnections &&
            WorkflowDefinitionLinearChainAnalyzer
                .Analyze(workflowDefinitionDraftJson)
                .IsLinear)
        {
            bridgeConnection = TryCreateLinearBridgeConnection(
                readResult.Connections,
                nodeInstanceId);
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
        var addedConnections = new List<WorkflowDefinitionDraftConnection>();
        if (bridgeConnection is not null)
        {
            readResult.Connections.Add(CreateConnectionObject(bridgeConnection));
            addedConnections.Add(bridgeConnection);
        }

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            RemovedConnections = removedConnections,
            AddedConnections = addedConnections,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
        };
    }

    public static WorkflowDefinitionDraftNodePatchResult DeleteNodes(
        string workflowDefinitionDraftJson,
        IReadOnlyCollection<string> nodeInstanceIds)
    {
        if (nodeInstanceIds.Count == 0)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        var targetNodeIds = new HashSet<string>(StringComparer.Ordinal);
        foreach (var nodeInstanceId in nodeInstanceIds)
        {
            if (string.IsNullOrWhiteSpace(nodeInstanceId))
            {
                return Failed(
                    WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                    "NODE_INSTANCE_ID_REQUIRED");
            }

            targetNodeIds.Add(nodeInstanceId.Trim());
        }

        var readResult = ReadMutableDraft(workflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            return Failed(readResult.Status, readResult.Warning);
        }

        foreach (var nodeInstanceId in targetNodeIds)
        {
            if (FindNodeIndex(readResult.Nodes, nodeInstanceId) < 0)
            {
                return Failed(
                    WorkflowDefinitionDraftNodePatchStatus.NodeNotFound,
                    "NODE_NOT_FOUND");
            }
        }

        var removedConnections = new List<WorkflowDefinitionDraftConnection>();
        for (var index = readResult.Connections.Count - 1; index >= 0; index--)
        {
            if (readResult.Connections[index] is JsonObject connectionObject &&
                (targetNodeIds.Contains(
                    GetStringValue(connectionObject, "source_node_id") ?? string.Empty)
                || targetNodeIds.Contains(
                    GetStringValue(connectionObject, "target_node_id") ?? string.Empty)))
            {
                removedConnections.Insert(0, ReadConnection(connectionObject));
                readResult.Connections.RemoveAt(index);
            }
        }

        for (var index = readResult.Nodes.Count - 1; index >= 0; index--)
        {
            if (readResult.Nodes[index] is JsonObject nodeObject &&
                targetNodeIds.Contains(
                    GetStringValue(nodeObject, "node_instance_id") ?? string.Empty))
            {
                readResult.Nodes.RemoveAt(index);
            }
        }

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            RemovedConnections = removedConnections,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
        };
    }

    public static WorkflowDefinitionDraftNodePatchResult CopyNode(
        string workflowDefinitionDraftJson,
        string sourceNodeInstanceId,
        string? newNodeInstanceId = null)
    {
        if (string.IsNullOrWhiteSpace(sourceNodeInstanceId))
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

        var sourceIndex = FindNodeIndex(readResult.Nodes, sourceNodeInstanceId);
        if (sourceIndex < 0 ||
            readResult.Nodes[sourceIndex] is not JsonObject sourceNode)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeNotFound,
                "NODE_NOT_FOUND");
        }

        var addedNodeInstanceId = string.IsNullOrWhiteSpace(newNodeInstanceId)
            ? BuildUniqueNodeInstanceId(readResult.Nodes, sourceNodeInstanceId)
            : newNodeInstanceId.Trim();
        if (string.IsNullOrWhiteSpace(addedNodeInstanceId))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        if (FindNodeIndex(readResult.Nodes, addedNodeInstanceId) >= 0)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeAlreadyExists,
                "NODE_ALREADY_EXISTS");
        }

        var copiedNode = sourceNode.DeepClone().AsObject();
        copiedNode["node_instance_id"] = addedNodeInstanceId;
        readResult.Nodes.Insert(sourceIndex + 1, copiedNode);

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            AddedNodeInstanceId = addedNodeInstanceId,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
        };
    }

    public static WorkflowDefinitionDraftNodePatchResult MoveNode(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        int offset)
    {
        if (string.IsNullOrWhiteSpace(nodeInstanceId))
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeInstanceIdRequired,
                "NODE_INSTANCE_ID_REQUIRED");
        }

        if (offset == 0)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeMoveOutOfRange,
                "NODE_MOVE_OUT_OF_RANGE");
        }

        var readResult = ReadMutableDraft(workflowDefinitionDraftJson);
        if (!readResult.Succeeded)
        {
            return Failed(readResult.Status, readResult.Warning);
        }

        var sourceIndex = FindNodeIndex(readResult.Nodes, nodeInstanceId);
        if (sourceIndex < 0)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeNotFound,
                "NODE_NOT_FOUND");
        }

        var targetIndex = sourceIndex + offset;
        if (targetIndex < 0 || targetIndex >= readResult.Nodes.Count)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeMoveOutOfRange,
                "NODE_MOVE_OUT_OF_RANGE");
        }

        var node = readResult.Nodes[sourceIndex];
        readResult.Nodes.RemoveAt(sourceIndex);
        readResult.Nodes.Insert(targetIndex, node);

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
        };
    }

    public static WorkflowDefinitionDraftNodePatchResult UpdateDisplayName(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        string? displayName)
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

        var nodeIndex = FindNodeIndex(readResult.Nodes, nodeInstanceId);
        if (nodeIndex < 0 ||
            readResult.Nodes[nodeIndex] is not JsonObject nodeObject)
        {
            return Failed(
                WorkflowDefinitionDraftNodePatchStatus.NodeNotFound,
                "NODE_NOT_FOUND");
        }

        if (string.IsNullOrWhiteSpace(displayName))
        {
            nodeObject.Remove("display_name");
        }
        else
        {
            nodeObject["display_name"] = displayName.Trim();
        }

        return new WorkflowDefinitionDraftNodePatchResult
        {
            Status = WorkflowDefinitionDraftNodePatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                readResult.Root.ToJsonString(IndentedJsonOptions),
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
