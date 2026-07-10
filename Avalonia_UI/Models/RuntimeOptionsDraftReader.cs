using System.Collections.Generic;
using System.Text.Json;

namespace Avalonia_UI.Models;

public static class RuntimeOptionsDraftReader
{
    public static RuntimeOptionsDraftReadResult Read(string workflowDefinitionDraftJson)
    {
        return Read(
            WorkflowDefinitionDraftSnapshot.Parse(workflowDefinitionDraftJson));
    }

    public static RuntimeOptionsDraftReadResult Read(
        WorkflowDefinitionDraftSnapshot snapshot)
    {
        if (!snapshot.Succeeded)
        {
            return Failed(
                RuntimeOptionsDraftReadStatus.JsonInvalid,
                snapshot.Warning ?? "WORKFLOW_DRAFT_JSON_INVALID");
        }

        var root = snapshot.Root;
        if (root.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                RuntimeOptionsDraftReadStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        if (!root.TryGetProperty("runtime_options", out var runtimeOptions))
        {
            return Succeeded(new RuntimeOptionsDraft());
        }

        if (runtimeOptions.ValueKind != JsonValueKind.Object)
        {
            return Failed(
                RuntimeOptionsDraftReadStatus.RuntimeOptionsNotObject,
                "RUNTIME_OPTIONS_NOT_OBJECT");
        }

        return Succeeded(ReadRuntimeOptions(runtimeOptions));
    }

    public static RuntimeOptionsDraftReadResult ReadRuntimeOptionsJson(
        string runtimeOptionsJson)
    {
        JsonDocument document;
        try
        {
            document = JsonDocument.Parse(runtimeOptionsJson);
        }
        catch (JsonException)
        {
            return Failed(
                RuntimeOptionsDraftReadStatus.JsonInvalid,
                "RUNTIME_OPTIONS_JSON_INVALID");
        }

        using (document)
        {
            var runtimeOptions = document.RootElement;
            if (runtimeOptions.ValueKind != JsonValueKind.Object)
            {
                return Failed(
                    RuntimeOptionsDraftReadStatus.RuntimeOptionsNotObject,
                    "RUNTIME_OPTIONS_NOT_OBJECT");
            }

            if (runtimeOptions.TryGetProperty("runtime_options", out var nested))
            {
                if (nested.ValueKind != JsonValueKind.Object)
                {
                    return Failed(
                        RuntimeOptionsDraftReadStatus.RuntimeOptionsNotObject,
                        "RUNTIME_OPTIONS_NOT_OBJECT");
                }

                runtimeOptions = nested;
            }

            return Succeeded(ReadRuntimeOptions(runtimeOptions));
        }
    }

    private static RuntimeOptionsDraft ReadRuntimeOptions(JsonElement runtimeOptions)
    {
        var workflow = runtimeOptions.TryGetProperty("workflow", out var workflowElement) &&
            workflowElement.ValueKind == JsonValueKind.Object
                ? ReadWorkflow(workflowElement)
                : new RuntimeOptionsWorkflowDraft();

        return new RuntimeOptionsDraft
        {
            Version = GetString(
                runtimeOptions,
                "version",
                RuntimeOptionsDefaults.Version),
            Workflow = workflow,
            NodeOverrides = ReadNodeOverrides(runtimeOptions),
        };
    }

    private static RuntimeOptionsWorkflowDraft ReadWorkflow(JsonElement workflow)
    {
        return new RuntimeOptionsWorkflowDraft
        {
            Profile = GetString(workflow, "profile", RuntimeOptionsDefaults.Profile),
            StrictValidation = GetBool(workflow, "strict_validation", true),
            Telemetry = workflow.TryGetProperty("telemetry", out var telemetry) &&
                telemetry.ValueKind == JsonValueKind.Object
                    ? ReadTelemetry(telemetry)
                    : new RuntimeOptionsTelemetryDraft(),
            Diagnostics = workflow.TryGetProperty("diagnostics", out var diagnostics) &&
                diagnostics.ValueKind == JsonValueKind.Object
                    ? ReadDiagnostics(diagnostics)
                    : new RuntimeOptionsDiagnosticsDraft(),
        };
    }

    private static RuntimeOptionsTelemetryDraft ReadTelemetry(JsonElement telemetry)
    {
        return new RuntimeOptionsTelemetryDraft
        {
            LogLevel = GetString(
                telemetry,
                "log_level",
                RuntimeOptionsDefaults.LogLevel),
            EventLevel = GetString(
                telemetry,
                "event_level",
                RuntimeOptionsDefaults.EventLevel),
            EventRateLimitPerSecond = GetInt(
                telemetry,
                "event_rate_limit_per_second",
                0),
            ProgressEnabled = GetBool(telemetry, "progress_enabled", true),
            ProgressIntervalSeconds = GetDouble(
                telemetry,
                "progress_interval_seconds",
                0),
        };
    }

    private static RuntimeOptionsDiagnosticsDraft ReadDiagnostics(JsonElement diagnostics)
    {
        return new RuntimeOptionsDiagnosticsDraft
        {
            CaptureErrorContext = GetBool(
                diagnostics,
                "capture_error_context",
                true),
            IncludeMetrics = GetBool(diagnostics, "include_metrics", true),
            PayloadByteLimit = GetInt(diagnostics, "payload_byte_limit", 0),
            TtlSeconds = GetInt(diagnostics, "ttl_seconds", 0),
            RedactColumns = ReadStringArray(diagnostics, "redact_columns"),
            MaskPolicy = GetString(
                diagnostics,
                "mask_policy",
                RuntimeOptionsDefaults.MaskPolicy),
        };
    }

    private static IReadOnlyDictionary<string, RuntimeOptionsNodeOverrideDraft>
        ReadNodeOverrides(JsonElement runtimeOptions)
    {
        if (!runtimeOptions.TryGetProperty("node_overrides", out var nodeOverrides) ||
            nodeOverrides.ValueKind != JsonValueKind.Object)
        {
            return new Dictionary<string, RuntimeOptionsNodeOverrideDraft>();
        }

        var result = new Dictionary<string, RuntimeOptionsNodeOverrideDraft>();
        foreach (var nodeOverride in nodeOverrides.EnumerateObject())
        {
            if (string.IsNullOrWhiteSpace(nodeOverride.Name) ||
                nodeOverride.Value.ValueKind != JsonValueKind.Object)
            {
                continue;
            }

            result[nodeOverride.Name] = ReadNodeOverride(nodeOverride.Value);
        }

        return result;
    }

    private static RuntimeOptionsNodeOverrideDraft ReadNodeOverride(JsonElement nodeOverride)
    {
        return new RuntimeOptionsNodeOverrideDraft
        {
            Profile = GetNullableString(nodeOverride, "profile"),
            StrictValidation = GetNullableBool(nodeOverride, "strict_validation"),
            Telemetry = nodeOverride.TryGetProperty("telemetry", out var telemetry) &&
                telemetry.ValueKind == JsonValueKind.Object
                    ? ReadTelemetryOverride(telemetry)
                    : null,
            Diagnostics = nodeOverride.TryGetProperty("diagnostics", out var diagnostics) &&
                diagnostics.ValueKind == JsonValueKind.Object
                    ? ReadDiagnosticsOverride(diagnostics)
                    : null,
        };
    }

    private static RuntimeOptionsTelemetryOverrideDraft ReadTelemetryOverride(
        JsonElement telemetry)
    {
        return new RuntimeOptionsTelemetryOverrideDraft
        {
            LogLevel = GetNullableString(telemetry, "log_level"),
            EventLevel = GetNullableString(telemetry, "event_level"),
            EventRateLimitPerSecond = GetNullableInt(
                telemetry,
                "event_rate_limit_per_second"),
            ProgressEnabled = GetNullableBool(telemetry, "progress_enabled"),
            ProgressIntervalSeconds = GetNullableDouble(
                telemetry,
                "progress_interval_seconds"),
        };
    }

    private static RuntimeOptionsDiagnosticsOverrideDraft ReadDiagnosticsOverride(
        JsonElement diagnostics)
    {
        return new RuntimeOptionsDiagnosticsOverrideDraft
        {
            CaptureErrorContext = GetNullableBool(
                diagnostics,
                "capture_error_context"),
            IncludeMetrics = GetNullableBool(diagnostics, "include_metrics"),
            PayloadByteLimit = GetNullableInt(diagnostics, "payload_byte_limit"),
            TtlSeconds = GetNullableInt(diagnostics, "ttl_seconds"),
            RedactColumns = diagnostics.TryGetProperty("redact_columns", out var value) &&
                value.ValueKind == JsonValueKind.Array
                    ? ReadStringArray(value)
                    : null,
            MaskPolicy = GetNullableString(diagnostics, "mask_policy"),
        };
    }

    private static string GetString(
        JsonElement element,
        string propertyName,
        string defaultValue)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String
                ? property.GetString() ?? defaultValue
                : defaultValue;
    }

    private static string? GetNullableString(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.String
                ? property.GetString()
                : null;
    }

    private static bool GetBool(
        JsonElement element,
        string propertyName,
        bool defaultValue)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind is JsonValueKind.True or JsonValueKind.False
                ? property.GetBoolean()
                : defaultValue;
    }

    private static bool? GetNullableBool(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind is JsonValueKind.True or JsonValueKind.False
                ? property.GetBoolean()
                : null;
    }

    private static int GetInt(
        JsonElement element,
        string propertyName,
        int defaultValue)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetInt32(out var value)
                ? value
                : defaultValue;
    }

    private static int? GetNullableInt(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetInt32(out var value)
                ? value
                : null;
    }

    private static double GetDouble(
        JsonElement element,
        string propertyName,
        double defaultValue)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetDouble(out var value)
                ? value
                : defaultValue;
    }

    private static double? GetNullableDouble(JsonElement element, string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Number &&
            property.TryGetDouble(out var value)
                ? value
                : null;
    }

    private static IReadOnlyList<string> ReadStringArray(
        JsonElement element,
        string propertyName)
    {
        return element.TryGetProperty(propertyName, out var property) &&
            property.ValueKind == JsonValueKind.Array
                ? ReadStringArray(property)
                : [];
    }

    private static IReadOnlyList<string> ReadStringArray(JsonElement array)
    {
        var result = new List<string>();
        foreach (var item in array.EnumerateArray())
        {
            if (item.ValueKind == JsonValueKind.String)
            {
                result.Add(item.GetString() ?? string.Empty);
            }
        }

        return result;
    }

    private static RuntimeOptionsDraftReadResult Succeeded(RuntimeOptionsDraft draft)
    {
        return new RuntimeOptionsDraftReadResult
        {
            Status = RuntimeOptionsDraftReadStatus.Succeeded,
            Draft = draft,
        };
    }

    private static RuntimeOptionsDraftReadResult Failed(
        RuntimeOptionsDraftReadStatus status,
        string warning)
    {
        return new RuntimeOptionsDraftReadResult
        {
            Status = status,
            Warning = warning,
        };
    }
}
