using System;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class NodeConfigDefaultBuilder
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static string BuildJson(NodeConfigSchemaDescriptor? schema)
    {
        if (schema?.IsSupported != true)
        {
            return "{}";
        }

        var config = new JsonObject();
        foreach (var field in schema.Fields)
        {
            var value = field.DefaultValue.HasValue
                ? CloneDefaultValue(field.DefaultValue.Value)
                : BuildRequiredFallbackValue(field);

            if (value is not null || ShouldIncludeNullDefault(field))
            {
                config[field.Name] = value;
            }
        }

        return config.ToJsonString(IndentedJsonOptions);
    }

    private static bool ShouldIncludeNullDefault(NodeConfigFieldDescriptor field)
    {
        return field.DefaultValue.HasValue &&
            field.DefaultValue.Value.ValueKind == JsonValueKind.Null;
    }

    private static JsonNode? CloneDefaultValue(JsonElement value)
    {
        return JsonNode.Parse(value.GetRawText());
    }

    private static JsonNode? BuildRequiredFallbackValue(NodeConfigFieldDescriptor field)
    {
        if (!field.Required)
        {
            return null;
        }

        return field.Type switch
        {
            NodeConfigFieldType.String => JsonValue.Create(string.Empty),
            NodeConfigFieldType.Integer => JsonValue.Create(
                (long)Math.Ceiling(field.Minimum ?? 0)),
            NodeConfigFieldType.Number => JsonValue.Create(field.Minimum ?? 0),
            NodeConfigFieldType.Boolean => JsonValue.Create(false),
            NodeConfigFieldType.Enum when field.EnumValues.Count > 0 =>
                JsonValue.Create(field.EnumValues[0]),
            NodeConfigFieldType.Array => new JsonArray(),
            NodeConfigFieldType.Object => new JsonObject(),
            _ => null,
        };
    }
}
