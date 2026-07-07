using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace Avalonia_UI.Models;

public static class WorkflowDefinitionDraftRuntimeOptionsPatcher
{
    private static readonly JsonSerializerOptions IndentedJsonOptions = new()
    {
        WriteIndented = true,
    };

    public static WorkflowDefinitionDraftRuntimeOptionsPatchResult Apply(
        string workflowDefinitionDraftJson,
        RuntimeOptionsDraft draft)
    {
        JsonNode? root;
        try
        {
            root = JsonNode.Parse(workflowDefinitionDraftJson);
        }
        catch (JsonException)
        {
            return Failed(
                WorkflowDefinitionDraftRuntimeOptionsPatchStatus.JsonInvalid,
                "WORKFLOW_DRAFT_JSON_INVALID");
        }

        if (root is not JsonObject rootObject)
        {
            return Failed(
                WorkflowDefinitionDraftRuntimeOptionsPatchStatus.RootNotObject,
                "WORKFLOW_DRAFT_ROOT_NOT_OBJECT");
        }

        foreach (var nodeOverride in draft.NodeOverrides)
        {
            if (string.IsNullOrWhiteSpace(nodeOverride.Key))
            {
                return Failed(
                    WorkflowDefinitionDraftRuntimeOptionsPatchStatus.NodeInstanceIdRequired,
                    "NODE_INSTANCE_ID_REQUIRED");
            }
        }

        rootObject["runtime_options"] = CreateRuntimeOptionsObject(draft);
        return new WorkflowDefinitionDraftRuntimeOptionsPatchResult
        {
            Status = WorkflowDefinitionDraftRuntimeOptionsPatchStatus.Succeeded,
            UpdatedWorkflowDefinitionDraftJson =
                rootObject.ToJsonString(IndentedJsonOptions),
        };
    }

    private static JsonObject CreateRuntimeOptionsObject(RuntimeOptionsDraft draft)
    {
        return new JsonObject
        {
            ["version"] = string.IsNullOrWhiteSpace(draft.Version)
                ? RuntimeOptionsDefaults.Version
                : draft.Version,
            ["workflow"] = CreateWorkflowObject(draft.Workflow),
            ["node_overrides"] = CreateNodeOverridesObject(
                draft.Workflow,
                draft.NodeOverrides),
        };
    }

    private static JsonObject CreateWorkflowObject(RuntimeOptionsWorkflowDraft workflow)
    {
        return new JsonObject
        {
            ["profile"] = workflow.Profile,
            ["strict_validation"] = workflow.StrictValidation,
            ["telemetry"] = CreateTelemetryObject(workflow.Telemetry),
            ["diagnostics"] = CreateDiagnosticsObject(workflow.Diagnostics),
        };
    }

    private static JsonObject CreateTelemetryObject(RuntimeOptionsTelemetryDraft telemetry)
    {
        return new JsonObject
        {
            ["log_level"] = telemetry.LogLevel,
            ["event_level"] = telemetry.EventLevel,
            ["event_rate_limit_per_second"] = telemetry.EventRateLimitPerSecond,
            ["progress_enabled"] = telemetry.ProgressEnabled,
            ["progress_interval_seconds"] = telemetry.ProgressIntervalSeconds,
        };
    }

    private static JsonObject CreateDiagnosticsObject(
        RuntimeOptionsDiagnosticsDraft diagnostics)
    {
        return new JsonObject
        {
            ["capture_error_context"] = diagnostics.CaptureErrorContext,
            ["include_metrics"] = diagnostics.IncludeMetrics,
            ["payload_byte_limit"] = diagnostics.PayloadByteLimit,
            ["ttl_seconds"] = diagnostics.TtlSeconds,
            ["redact_columns"] = CreateStringArray(diagnostics.RedactColumns),
            ["mask_policy"] = diagnostics.MaskPolicy,
        };
    }

    private static JsonObject CreateNodeOverridesObject(
        RuntimeOptionsWorkflowDraft workflow,
        IReadOnlyDictionary<string, RuntimeOptionsNodeOverrideDraft> nodeOverrides)
    {
        var result = new JsonObject();
        foreach (var nodeOverride in nodeOverrides)
        {
            var overrideObject = CreateNodeOverrideObject(
                workflow,
                nodeOverride.Value);
            if (overrideObject.Count > 0)
            {
                result[nodeOverride.Key.Trim()] = overrideObject;
            }
        }

        return result;
    }

    private static JsonObject CreateNodeOverrideObject(
        RuntimeOptionsWorkflowDraft workflow,
        RuntimeOptionsNodeOverrideDraft nodeOverride)
    {
        var result = new JsonObject();
        AddIfDifferent(
            result,
            "profile",
            nodeOverride.Profile,
            workflow.Profile);
        AddIfDifferent(
            result,
            "strict_validation",
            nodeOverride.StrictValidation,
            workflow.StrictValidation);

        if (nodeOverride.Telemetry is not null)
        {
            var telemetry = CreateTelemetryOverrideObject(
                workflow.Telemetry,
                nodeOverride.Telemetry);
            if (telemetry.Count > 0)
            {
                result["telemetry"] = telemetry;
            }
        }

        if (nodeOverride.Diagnostics is not null)
        {
            var diagnostics = CreateDiagnosticsOverrideObject(
                workflow.Diagnostics,
                nodeOverride.Diagnostics);
            if (diagnostics.Count > 0)
            {
                result["diagnostics"] = diagnostics;
            }
        }

        return result;
    }

    private static JsonObject CreateTelemetryOverrideObject(
        RuntimeOptionsTelemetryDraft workflow,
        RuntimeOptionsTelemetryOverrideDraft nodeOverride)
    {
        var result = new JsonObject();
        AddIfDifferent(result, "log_level", nodeOverride.LogLevel, workflow.LogLevel);
        AddIfDifferent(
            result,
            "event_level",
            nodeOverride.EventLevel,
            workflow.EventLevel);
        AddIfDifferent(
            result,
            "event_rate_limit_per_second",
            nodeOverride.EventRateLimitPerSecond,
            workflow.EventRateLimitPerSecond);
        AddIfDifferent(
            result,
            "progress_enabled",
            nodeOverride.ProgressEnabled,
            workflow.ProgressEnabled);
        AddIfDifferent(
            result,
            "progress_interval_seconds",
            nodeOverride.ProgressIntervalSeconds,
            workflow.ProgressIntervalSeconds);
        return result;
    }

    private static JsonObject CreateDiagnosticsOverrideObject(
        RuntimeOptionsDiagnosticsDraft workflow,
        RuntimeOptionsDiagnosticsOverrideDraft nodeOverride)
    {
        var result = new JsonObject();
        AddIfDifferent(
            result,
            "capture_error_context",
            nodeOverride.CaptureErrorContext,
            workflow.CaptureErrorContext);
        AddIfDifferent(
            result,
            "include_metrics",
            nodeOverride.IncludeMetrics,
            workflow.IncludeMetrics);
        AddIfDifferent(
            result,
            "payload_byte_limit",
            nodeOverride.PayloadByteLimit,
            workflow.PayloadByteLimit);
        AddIfDifferent(
            result,
            "ttl_seconds",
            nodeOverride.TtlSeconds,
            workflow.TtlSeconds);
        if (nodeOverride.RedactColumns is not null &&
            !nodeOverride.RedactColumns.SequenceEqual(
                workflow.RedactColumns,
                StringComparer.Ordinal))
        {
            result["redact_columns"] = CreateStringArray(nodeOverride.RedactColumns);
        }

        AddIfDifferent(
            result,
            "mask_policy",
            nodeOverride.MaskPolicy,
            workflow.MaskPolicy);
        return result;
    }

    private static void AddIfDifferent(
        JsonObject target,
        string propertyName,
        string? value,
        string workflowValue)
    {
        if (value is not null && !string.Equals(value, workflowValue, StringComparison.Ordinal))
        {
            target[propertyName] = value;
        }
    }

    private static void AddIfDifferent(
        JsonObject target,
        string propertyName,
        bool? value,
        bool workflowValue)
    {
        if (value.HasValue && value.Value != workflowValue)
        {
            target[propertyName] = value.Value;
        }
    }

    private static void AddIfDifferent(
        JsonObject target,
        string propertyName,
        int? value,
        int workflowValue)
    {
        if (value.HasValue && value.Value != workflowValue)
        {
            target[propertyName] = value.Value;
        }
    }

    private static void AddIfDifferent(
        JsonObject target,
        string propertyName,
        double? value,
        double workflowValue)
    {
        if (value.HasValue && Math.Abs(value.Value - workflowValue) > double.Epsilon)
        {
            target[propertyName] = value.Value;
        }
    }

    private static JsonArray CreateStringArray(IEnumerable<string> values)
    {
        var result = new JsonArray();
        foreach (var value in values)
        {
            result.Add(value);
        }

        return result;
    }

    private static WorkflowDefinitionDraftRuntimeOptionsPatchResult Failed(
        WorkflowDefinitionDraftRuntimeOptionsPatchStatus status,
        string warning)
    {
        return new WorkflowDefinitionDraftRuntimeOptionsPatchResult
        {
            Status = status,
            Warning = warning,
        };
    }
}
