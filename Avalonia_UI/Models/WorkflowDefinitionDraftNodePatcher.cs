using System;
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
                    nodeObject["node_instance_id"]?.GetValue<string>(),
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
}
