using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class NodeConfigDraftJsonPatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static NodeConfigDraftApplyResult ApplyPatch(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        JsonElement fieldsToSet,
        IEnumerable<string>? fieldsToDelete = null)
    {
        if (fieldsToSet.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                NodeConfigDraftApplyStatus.ConfigUnsupported,
                "CONFIG_UNSUPPORTED");
        }

        var setFieldNames = fieldsToSet
            .EnumerateObject()
            .Select(property => property.Name)
            .ToHashSet(StringComparer.Ordinal);
        var deleteFieldNames = (fieldsToDelete ?? [])
            .ToHashSet(StringComparer.Ordinal);
        var conflictingFields = setFieldNames
            .Intersect(deleteFieldNames, StringComparer.Ordinal)
            .Order(StringComparer.Ordinal)
            .ToArray();
        if (conflictingFields.Length > 0)
        {
            return new NodeConfigDraftApplyResult
            {
                Status = NodeConfigDraftApplyStatus.PatchConflict,
                Warning = "CONFIG_PATCH_FIELD_CONFLICT",
                ConflictingFields = conflictingFields,
            };
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

            JsonObject configObject;
            if (nodeObject.TryGetPropertyValue("config", out var existingConfig))
            {
                if (existingConfig is not JsonObject existingConfigObject)
                {
                    return Failed(
                        NodeConfigDraftApplyStatus.NodeConfigNotObject,
                        "NODE_CONFIG_NOT_OBJECT");
                }

                configObject = existingConfigObject;
            }
            else
            {
                configObject = new JsonObject();
                nodeObject["config"] = configObject;
            }

            foreach (var property in fieldsToSet.EnumerateObject())
            {
                configObject[property.Name] = JsonNode.Parse(property.Value.GetRawText());
            }

            foreach (var fieldName in deleteFieldNames)
            {
                configObject.Remove(fieldName);
            }

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
