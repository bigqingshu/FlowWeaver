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
        return new NodeConfigEditableDraftField
        {
            Name = field.Name,
            Type = field.Type,
            Title = field.Title,
            Required = field.Required,
            InputValue = FormatInputValue(field),
            EnumValues = field.Type == NodeConfigFieldType.Enum
                ? field.EnumValues
                : [],
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

    private static string FormatInputValue(NodeConfigDraftField field)
    {
        var value = field.CurrentValue ?? field.DefaultValue;
        if (!value.HasValue)
        {
            return string.Empty;
        }

        return FormatJsonValue(value.Value);
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

}
