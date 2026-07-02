using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class NodeConfigSchemaParser
{
    public const string SupportedSchemaVersion = "1.0";

    public static NodeConfigSchemaParseResult Parse(
        string? schemaVersion,
        JsonElement? schema)
    {
        var warnings = new List<string>();
        var version = schemaVersion ?? string.Empty;

        if (!schema.HasValue || schema.Value.ValueKind == JsonValueKind.Null)
        {
            warnings.Add("CONFIG_SCHEMA_MISSING");
            return Unsupported(version, warnings);
        }

        if (string.IsNullOrWhiteSpace(schemaVersion))
        {
            warnings.Add("CONFIG_SCHEMA_VERSION_MISSING");
            return Unsupported(version, warnings);
        }

        if (!string.Equals(
            schemaVersion,
            SupportedSchemaVersion,
            StringComparison.Ordinal))
        {
            warnings.Add("CONFIG_SCHEMA_VERSION_UNSUPPORTED");
            return Unsupported(version, warnings);
        }

        var schemaElement = schema.Value;
        if (!schemaElement.TryGetProperty("type", out var typeElement) ||
            typeElement.ValueKind != JsonValueKind.String ||
            !string.Equals(
                typeElement.GetString(),
                "object",
                StringComparison.Ordinal))
        {
            warnings.Add("CONFIG_SCHEMA_ROOT_TYPE_UNSUPPORTED");
            return Unsupported(version, warnings);
        }

        var fields = new List<NodeConfigFieldDescriptor>();
        if (!schemaElement.TryGetProperty("properties", out var properties) ||
            properties.ValueKind != JsonValueKind.Object)
        {
            warnings.Add("CONFIG_SCHEMA_PROPERTIES_MISSING");
        }
        else
        {
            fields.AddRange(ParseFields(properties));
        }

        return new NodeConfigSchemaParseResult
        {
            Schema = new NodeConfigSchemaDescriptor
            {
                Version = version,
                Type = "object",
                Fields = fields,
                Warnings = warnings,
                IsSupported = true,
            },
            Warnings = warnings,
        };
    }

    private static NodeConfigSchemaParseResult Unsupported(
        string version,
        IReadOnlyList<string> warnings)
    {
        return new NodeConfigSchemaParseResult
        {
            Schema = new NodeConfigSchemaDescriptor
            {
                Version = version,
                IsSupported = false,
                Warnings = warnings,
            },
            Warnings = warnings,
        };
    }

    private static IEnumerable<NodeConfigFieldDescriptor> ParseFields(
        JsonElement properties)
    {
        return properties
            .EnumerateObject()
            .Select(property => ParseField(property.Name, property.Value));
    }

    private static NodeConfigFieldDescriptor ParseField(
        string name,
        JsonElement field)
    {
        var warnings = new List<string>();
        var typeName = ReadString(field, "type") ?? string.Empty;
        var type = ParseFieldType(typeName);
        if (type == NodeConfigFieldType.Unsupported)
        {
            warnings.Add("CONFIG_FIELD_TYPE_UNSUPPORTED");
        }

        var enumValues = ReadStringArray(field, "enum", warnings);
        var itemType = ReadItemType(field, warnings);

        return new NodeConfigFieldDescriptor
        {
            Name = name,
            Type = type,
            TypeName = typeName,
            Title = ReadString(field, "title"),
            Required = ReadBool(field, "required"),
            DefaultValue = ReadDefault(field),
            Minimum = ReadNumber(field, "minimum"),
            EnumValues = enumValues,
            ItemType = itemType,
            Description = ReadString(field, "description"),
            Warnings = warnings,
        };
    }

    private static NodeConfigFieldType ParseFieldType(string typeName)
    {
        return typeName switch
        {
            "string" => NodeConfigFieldType.String,
            "integer" => NodeConfigFieldType.Integer,
            "number" => NodeConfigFieldType.Number,
            "boolean" => NodeConfigFieldType.Boolean,
            "enum" => NodeConfigFieldType.Enum,
            "array" => NodeConfigFieldType.Array,
            "object" => NodeConfigFieldType.Object,
            _ => NodeConfigFieldType.Unsupported,
        };
    }

    private static string? ReadString(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String
                ? property.GetString()
                : null;
    }

    private static bool ReadBool(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.True;
    }

    private static double? ReadNumber(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetDouble(out var value)
                ? value
                : null;
    }

    private static JsonElement? ReadDefault(JsonElement element)
    {
        return element.TryGetProperty("default", out var property)
            ? property.Clone()
            : null;
    }

    private static IReadOnlyList<string> ReadStringArray(
        JsonElement element,
        string propertyName,
        ICollection<string> warnings)
    {
        if (!element.TryGetProperty(propertyName, out var property))
        {
            return [];
        }

        if (property.ValueKind != JsonValueKind.Array)
        {
            warnings.Add("CONFIG_FIELD_ENUM_INVALID");
            return [];
        }

        var values = new List<string>();
        foreach (var item in property.EnumerateArray())
        {
            if (item.ValueKind != JsonValueKind.String)
            {
                warnings.Add("CONFIG_FIELD_ENUM_INVALID");
                return [];
            }

            values.Add(item.GetString() ?? string.Empty);
        }

        return values;
    }

    private static string? ReadItemType(
        JsonElement element,
        ICollection<string> warnings)
    {
        if (!element.TryGetProperty("items", out var items))
        {
            return null;
        }

        if (items.ValueKind != JsonValueKind.Object ||
            !items.TryGetProperty("type", out var type) ||
            type.ValueKind != JsonValueKind.String)
        {
            warnings.Add("CONFIG_FIELD_ITEMS_TYPE_MISSING");
            return null;
        }

        return type.GetString();
    }
}
