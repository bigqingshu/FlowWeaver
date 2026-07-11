using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class NodeConfigDraftBuilder
{
    public static NodeConfigDraft Build(
        string workflowDefinitionDraftJson,
        string nodeInstanceId,
        NodeConfigSchemaDescriptor? schema)
    {
        if (schema?.IsSupported != true)
        {
            return Draft(
                nodeInstanceId,
                NodeConfigDraftStatus.SchemaUnsupported,
                "CONFIG_DRAFT_SCHEMA_UNSUPPORTED");
        }

        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Draft(
                nodeInstanceId,
                NodeConfigDraftStatus.JsonInvalid,
                "CONFIG_DRAFT_JSON_INVALID");
        }

        using (document)
        {
            if (!TryFindNode(document.RootElement, nodeInstanceId, out var node))
            {
                return Draft(
                    nodeInstanceId,
                    NodeConfigDraftStatus.NodeNotFound,
                    "CONFIG_DRAFT_NODE_NOT_FOUND");
            }

            var config = TryGetObject(node, "config", out var configObject)
                ? configObject
                : default;

            return new NodeConfigDraft
            {
                NodeInstanceId = nodeInstanceId,
                Status = NodeConfigDraftStatus.Supported,
                Fields = schema.Fields.Select(field => BuildField(field, config)).ToArray(),
            };
        }
    }

    private static NodeConfigDraft Draft(
        string nodeInstanceId,
        NodeConfigDraftStatus status,
        string warning)
    {
        return new NodeConfigDraft
        {
            NodeInstanceId = nodeInstanceId,
            Status = status,
            Warnings = [warning],
        };
    }

    private static NodeConfigDraftField BuildField(
        NodeConfigFieldDescriptor field,
        JsonElement config)
    {
        JsonElement? currentValue = null;
        if (config.ValueKind == JsonValueKind.Object &&
            config.TryGetProperty(field.Name, out var value))
        {
            currentValue = value.Clone();
        }

        return new NodeConfigDraftField
        {
            Name = field.Name,
            Type = field.Type,
            Title = field.Title,
            Required = field.Required,
            CurrentValue = currentValue,
            DefaultValue = field.DefaultValue?.Clone(),
            EnumValues = field.EnumValues,
            ItemType = field.ItemType,
            IsEditable = IsEditable(field, currentValue),
            Warnings = BuildFieldWarnings(field, currentValue).ToArray(),
        };
    }

    private static IEnumerable<string> BuildFieldWarnings(
        NodeConfigFieldDescriptor field,
        JsonElement? currentValue)
    {
        if (!IsEditable(field, currentValue))
        {
            yield return "CONFIG_DRAFT_FIELD_JSON_FALLBACK";
        }

        if (field.Required && !currentValue.HasValue)
        {
            yield return "CONFIG_DRAFT_FIELD_REQUIRED_MISSING";
        }
    }

    private static bool IsEditable(
        NodeConfigFieldDescriptor field,
        JsonElement? currentValue)
    {
        if (field.Type is NodeConfigFieldType.String
            or NodeConfigFieldType.Integer
            or NodeConfigFieldType.Number
            or NodeConfigFieldType.Boolean
            or NodeConfigFieldType.Enum)
        {
            return true;
        }

        return field.Type == NodeConfigFieldType.Array
            && string.Equals(field.ItemType, "string", StringComparison.Ordinal)
            && IsStringArrayValue(currentValue ?? field.DefaultValue);
    }

    private static bool IsStringArrayValue(JsonElement? value)
    {
        if (!value.HasValue)
        {
            return true;
        }

        return value.Value.ValueKind == JsonValueKind.Array
            && value.Value.EnumerateArray().All(
                item => item.ValueKind == JsonValueKind.String);
    }

    private static bool TryFindNode(
        JsonElement definition,
        string nodeInstanceId,
        out JsonElement node)
    {
        node = default;
        if (!TryGetArray(definition, "nodes", out var nodes))
        {
            return false;
        }

        foreach (var item in nodes.EnumerateArray())
        {
            if (TryGetString(item, "node_instance_id", out var candidate) &&
                string.Equals(candidate, nodeInstanceId, StringComparison.Ordinal))
            {
                node = item;
                return true;
            }
        }

        return false;
    }

    private static bool TryGetArray(
        JsonElement element,
        string propertyName,
        out JsonElement array)
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out array) &&
            array.ValueKind == JsonValueKind.Array)
        {
            return true;
        }

        array = default;
        return false;
    }

    private static bool TryGetObject(
        JsonElement element,
        string propertyName,
        out JsonElement value)
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out value) &&
            value.ValueKind == JsonValueKind.Object)
        {
            return true;
        }

        value = default;
        return false;
    }

    private static bool TryGetString(
        JsonElement element,
        string propertyName,
        out string value)
    {
        if (element.ValueKind == JsonValueKind.Object &&
            element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String)
        {
            value = property.GetString() ?? string.Empty;
            return true;
        }

        value = string.Empty;
        return false;
    }
}
