using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class NodeConfigDraftJsonPatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static NodeConfigDraftApplyResult ApplyConfig(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        JsonElement config)
    {
        if (config.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeConfigDraftApplyStatus.ConfigUnsupported,
                "CONFIG_UNSUPPORTED");
        }

        JsonNode? root;
        try
        {
            root = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Failed(NodeConfigDraftApplyStatus.JsonInvalid, "JSON_INVALID");
        }

        if (root is not JsonObject rootObject ||
            rootObject["nodes"] is not JsonArray nodes)
        {
            return Failed(NodeConfigDraftApplyStatus.NodesMissing, "NODES_MISSING");
        }

        foreach (var node in nodes)
        {
            if (node is not JsonObject nodeObject)
            {
                continue;
            }

            if (!string.Equals(
                nodeObject["node_instance_id"]?.GetValue<string>(),
                nodeInstanceId,
                StringComparison.Ordinal))
            {
                continue;
            }

            if (nodeObject.TryGetPropertyValue("config", out var existingConfig) &&
                existingConfig is not JsonObject)
            {
                return Failed(
                    NodeConfigDraftApplyStatus.NodeConfigNotObject,
                    "NODE_CONFIG_NOT_OBJECT");
            }

            nodeObject["config"] = JsonNode.Parse(config.GetRawText());
            return new NodeConfigDraftApplyResult
            {
                Status = NodeConfigDraftApplyStatus.Succeeded,
                UpdatedWorkflowDefinitionDraftJson =
                    rootObject.ToJsonString(IndentedJsonOptions),
            };
        }

        return Failed(NodeConfigDraftApplyStatus.NodeNotFound, "NODE_NOT_FOUND");
    }

    private static NodeConfigDraftApplyResult Failed(
        NodeConfigDraftApplyStatus status,
        string warning)
    {
        return new NodeConfigDraftApplyResult
        {
            Status = status,
            Warning = warning,
        };
    }
}
