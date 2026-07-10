using System.Collections.Generic;
using System.Globalization;
using System.Linq;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class NodeConfigEditableDraftConfigBuilder
{
    public static NodeConfigEditableDraftConfigResult Build(
        NodeConfigEditableDraft draft)
    {
        if (!draft.HasFields)
        {
            return Failed(
                NodeConfigEditableDraftConfigBuildStatus.DraftUnsupported,
                draft.Warnings.Append("EDITABLE_CONFIG_NO_EDITABLE_FIELDS"));
        }

        var config = new JsonObject();
        var fieldErrors = new List<NodeConfigEditableDraftConfigFieldError>();

        foreach (var field in draft.Fields)
        {
            if (ShouldOmitMissingOptionalField(field))
            {
                continue;
            }

            if (TryBuildValue(field, fieldErrors, out var value))
            {
                config[field.Name] = value;
            }
        }

        if (fieldErrors.Count > 0)
        {
            return new NodeConfigEditableDraftConfigResult
            {
                Status = NodeConfigEditableDraftConfigBuildStatus.FieldInvalid,
                FieldErrors = fieldErrors,
                Warnings = draft.Warnings
                    .Concat(fieldErrors.Select(error => error.Warning))
                    .ToArray(),
            };
        }

        return new NodeConfigEditableDraftConfigResult
        {
            Status = NodeConfigEditableDraftConfigBuildStatus.Succeeded,
            ConfigJson = config.ToJsonString(),
            Warnings = draft.Warnings,
        };
    }

    private static bool ShouldOmitMissingOptionalField(
        NodeConfigEditableDraftField field)
    {
        return !field.Required && !field.HasInputValue;
    }

    private static bool TryBuildValue(
        NodeConfigEditableDraftField field,
        ICollection<NodeConfigEditableDraftConfigFieldError> errors,
        out JsonNode? value)
    {
        value = null;
        var input = field.InputValue;

        if (field.Required && string.IsNullOrWhiteSpace(input))
        {
            errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_REQUIRED_EMPTY"));
            return false;
        }

        switch (field.Type)
        {
            case NodeConfigFieldType.String:
                value = JsonValue.Create(input);
                return true;
            case NodeConfigFieldType.Integer:
                return TryBuildInteger(field, input, errors, out value);
            case NodeConfigFieldType.Number:
                return TryBuildNumber(field, input, errors, out value);
            case NodeConfigFieldType.Boolean:
                return TryBuildBoolean(field, input, errors, out value);
            case NodeConfigFieldType.Enum:
                return TryBuildEnum(field, input, errors, out value);
            default:
                errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_TYPE_UNSUPPORTED"));
                return false;
        }
    }

    private static bool TryBuildInteger(
        NodeConfigEditableDraftField field,
        string input,
        ICollection<NodeConfigEditableDraftConfigFieldError> errors,
        out JsonNode? value)
    {
        value = null;
        if (long.TryParse(
            input.Trim(),
            NumberStyles.Integer,
            CultureInfo.InvariantCulture,
            out var integer))
        {
            value = JsonValue.Create(integer);
            return true;
        }

        errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_INTEGER_INVALID"));
        return false;
    }

    private static bool TryBuildNumber(
        NodeConfigEditableDraftField field,
        string input,
        ICollection<NodeConfigEditableDraftConfigFieldError> errors,
        out JsonNode? value)
    {
        value = null;
        if (decimal.TryParse(
            input.Trim(),
            NumberStyles.Float,
            CultureInfo.InvariantCulture,
            out var number))
        {
            value = JsonValue.Create(number);
            return true;
        }

        errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_NUMBER_INVALID"));
        return false;
    }

    private static bool TryBuildBoolean(
        NodeConfigEditableDraftField field,
        string input,
        ICollection<NodeConfigEditableDraftConfigFieldError> errors,
        out JsonNode? value)
    {
        value = null;
        if (bool.TryParse(input.Trim(), out var boolean))
        {
            value = JsonValue.Create(boolean);
            return true;
        }

        errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_BOOLEAN_INVALID"));
        return false;
    }

    private static bool TryBuildEnum(
        NodeConfigEditableDraftField field,
        string input,
        ICollection<NodeConfigEditableDraftConfigFieldError> errors,
        out JsonNode? value)
    {
        value = null;
        if (field.EnumValues.Contains(input))
        {
            value = JsonValue.Create(input);
            return true;
        }

        errors.Add(Error(field.Name, "EDITABLE_CONFIG_FIELD_ENUM_INVALID"));
        return false;
    }

    private static NodeConfigEditableDraftConfigFieldError Error(
        string fieldName,
        string warning)
    {
        return new NodeConfigEditableDraftConfigFieldError
        {
            FieldName = fieldName,
            Warning = warning,
        };
    }

    private static NodeConfigEditableDraftConfigResult Failed(
        NodeConfigEditableDraftConfigBuildStatus status,
        IEnumerable<string> warnings)
    {
        return new NodeConfigEditableDraftConfigResult
        {
            Status = status,
            Warnings = warnings.ToArray(),
        };
    }
}
