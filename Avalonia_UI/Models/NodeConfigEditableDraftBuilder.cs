using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class NodeConfigEditableDraftBuilder
{
    public static NodeConfigEditableDraft Build(NodeConfigDraft draft)
    {
        if (!draft.IsSupported)
        {
            return new NodeConfigEditableDraft
            {
                NodeInstanceId = draft.NodeInstanceId,
                Warnings = draft.Warnings,
            };
        }

        var fields = draft.Fields
            .Where(field => field.IsEditable)
            .Select(BuildField)
            .ToArray();

        return new NodeConfigEditableDraft
        {
            NodeInstanceId = draft.NodeInstanceId,
            Fields = fields,
            Warnings = BuildWarnings(draft, fields).ToArray(),
        };
    }

    private static NodeConfigEditableDraftField BuildField(NodeConfigDraftField field)
    {
        var inputValue = ResolveInputValue(field);
        return new NodeConfigEditableDraftField
        {
            Name = field.Name,
            Type = field.Type,
            Title = field.Title,
            Required = field.Required,
            InputValue = inputValue.Value,
            HasInputValue = inputValue.HasValue,
            EnumValues = field.Type == NodeConfigFieldType.Enum
                ? field.EnumValues
                : [],
            ItemType = field.ItemType,
            StringArrayValues = FormatStringArrayValues(field),
            Warnings = field.Warnings,
        };
    }

    private static IEnumerable<string> BuildWarnings(
        NodeConfigDraft draft,
        IReadOnlyCollection<NodeConfigEditableDraftField> fields)
    {
        if (fields.Count == 0)
        {
            yield return "EDITABLE_DRAFT_NO_EDITABLE_FIELDS";
        }

        foreach (var warning in draft.Warnings)
        {
            yield return warning;
        }
    }

    private static (string Value, bool HasValue) ResolveInputValue(
        NodeConfigDraftField field)
    {
        var value = FirstNonNull(field.CurrentValue, field.DefaultValue);
        if (value.HasValue)
        {
            return (FormatJsonValue(value.Value), true);
        }

        if (!field.Required)
        {
            return (string.Empty, false);
        }

        if (field.Type == NodeConfigFieldType.Enum && field.EnumValues.Count > 0)
        {
            return (field.EnumValues[0], true);
        }

        return field.Type == NodeConfigFieldType.Boolean
            ? ("false", true)
            : (string.Empty, false);
    }

    private static IReadOnlyList<string> FormatStringArrayValues(
        NodeConfigDraftField field)
    {
        if (field.Type != NodeConfigFieldType.Array
            || !string.Equals(field.ItemType, "string", StringComparison.Ordinal))
        {
            return [];
        }

        var value = FirstNonNull(field.CurrentValue, field.DefaultValue);
        if (!value.HasValue || value.Value.ValueKind != JsonValueKind.Array)
        {
            return [];
        }

        return value.Value
            .EnumerateArray()
            .Select(item => item.GetString() ?? string.Empty)
            .ToArray();
    }

    private static string FormatJsonValue(JsonElement value)
    {
        return value.ValueKind switch
        {
            JsonValueKind.String => value.GetString() ?? string.Empty,
            JsonValueKind.Number => value.GetRawText(),
            JsonValueKind.True => "true",
            JsonValueKind.False => "false",
            _ => value.GetRawText(),
        };
    }

    private static JsonElement? FirstNonNull(
        JsonElement? preferred,
        JsonElement? fallback)
    {
        if (preferred.HasValue && preferred.Value.ValueKind != JsonValueKind.Null)
        {
            return preferred;
        }

        return fallback.HasValue && fallback.Value.ValueKind != JsonValueKind.Null
            ? fallback
            : null;
    }

}
