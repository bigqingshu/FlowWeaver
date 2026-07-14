using System;
using System.Collections.Generic;
using System.Globalization;
using System.Linq;

namespace Avalonia_UI.Models;

public sealed record RuntimeOptionsWorkflowDraftFieldState
{
    public string Profile { get; init; } = RuntimeOptionsDefaults.Profile;

    public bool StrictValidation { get; init; } = true;

    public string LogLevel { get; init; } = RuntimeOptionsDefaults.LogLevel;

    public string EventLevel { get; init; } = RuntimeOptionsDefaults.EventLevel;

    public string EventRateLimitPerSecond { get; init; } = "0";

    public bool ProgressEnabled { get; init; } = true;

    public string ProgressIntervalSeconds { get; init; } = "0";

    public bool CaptureErrorContext { get; init; } = true;

    public bool IncludeMetrics { get; init; } = true;

    public string PayloadByteLimit { get; init; } = "0";

    public string TtlSeconds { get; init; } = "0";

    public string RedactColumns { get; init; } = string.Empty;

    public string MaskPolicy { get; init; } = RuntimeOptionsDefaults.MaskPolicy;
}

public sealed record RuntimeOptionsNodeDraftFieldState
{
    public string? Profile { get; init; }

    public bool? StrictValidation { get; init; }

    public string? LogLevel { get; init; }

    public string? EventLevel { get; init; }

    public string? EventRateLimitPerSecond { get; init; }

    public bool? ProgressEnabled { get; init; }

    public string? ProgressIntervalSeconds { get; init; }

    public bool? CaptureErrorContext { get; init; }

    public bool? IncludeMetrics { get; init; }

    public string? PayloadByteLimit { get; init; }

    public string? TtlSeconds { get; init; }

    public string? RedactColumns { get; init; }

    public string? MaskPolicy { get; init; }
}

public static class RuntimeOptionsDraftStateMapper
{
    public static RuntimeOptionsWorkflowDraftFieldState ToWorkflowFieldState(
        RuntimeOptionsWorkflowDraft draft)
    {
        return new RuntimeOptionsWorkflowDraftFieldState
        {
            Profile = draft.Profile,
            StrictValidation = draft.StrictValidation,
            LogLevel = draft.Telemetry.LogLevel,
            EventLevel = draft.Telemetry.EventLevel,
            EventRateLimitPerSecond = FormatInvariant(
                draft.Telemetry.EventRateLimitPerSecond),
            ProgressEnabled = draft.Telemetry.ProgressEnabled,
            ProgressIntervalSeconds = FormatInvariant(
                draft.Telemetry.ProgressIntervalSeconds),
            CaptureErrorContext = draft.Diagnostics.CaptureErrorContext,
            IncludeMetrics = draft.Diagnostics.IncludeMetrics,
            PayloadByteLimit = FormatInvariant(draft.Diagnostics.PayloadByteLimit),
            TtlSeconds = FormatInvariant(draft.Diagnostics.TtlSeconds),
            RedactColumns = FormatRedactColumns(draft.Diagnostics.RedactColumns),
            MaskPolicy = draft.Diagnostics.MaskPolicy,
        };
    }

    public static RuntimeOptionsNodeDraftFieldState ToSelectedNodeFieldState(
        RuntimeOptionsDraft draft,
        string? selectedNodeInstanceId)
    {
        RuntimeOptionsNodeOverrideDraft? nodeOverride = null;
        if (!string.IsNullOrWhiteSpace(selectedNodeInstanceId))
        {
            draft.NodeOverrides.TryGetValue(selectedNodeInstanceId, out nodeOverride);
        }

        return new RuntimeOptionsNodeDraftFieldState
        {
            Profile = nodeOverride?.Profile ?? draft.Workflow.Profile,
            StrictValidation =
                nodeOverride?.StrictValidation ?? draft.Workflow.StrictValidation,
            LogLevel =
                nodeOverride?.Telemetry?.LogLevel ?? draft.Workflow.Telemetry.LogLevel,
            EventLevel =
                nodeOverride?.Telemetry?.EventLevel ?? draft.Workflow.Telemetry.EventLevel,
            EventRateLimitPerSecond = FormatInvariant(
                nodeOverride?.Telemetry?.EventRateLimitPerSecond
                    ?? draft.Workflow.Telemetry.EventRateLimitPerSecond),
            ProgressEnabled =
                nodeOverride?.Telemetry?.ProgressEnabled
                ?? draft.Workflow.Telemetry.ProgressEnabled,
            ProgressIntervalSeconds = FormatInvariant(
                nodeOverride?.Telemetry?.ProgressIntervalSeconds
                    ?? draft.Workflow.Telemetry.ProgressIntervalSeconds),
            CaptureErrorContext =
                nodeOverride?.Diagnostics?.CaptureErrorContext
                ?? draft.Workflow.Diagnostics.CaptureErrorContext,
            IncludeMetrics =
                nodeOverride?.Diagnostics?.IncludeMetrics
                ?? draft.Workflow.Diagnostics.IncludeMetrics,
            PayloadByteLimit = FormatInvariant(
                nodeOverride?.Diagnostics?.PayloadByteLimit
                    ?? draft.Workflow.Diagnostics.PayloadByteLimit),
            TtlSeconds = FormatInvariant(
                nodeOverride?.Diagnostics?.TtlSeconds
                    ?? draft.Workflow.Diagnostics.TtlSeconds),
            RedactColumns = FormatRedactColumns(
                nodeOverride?.Diagnostics?.RedactColumns
                    ?? draft.Workflow.Diagnostics.RedactColumns),
            MaskPolicy =
                nodeOverride?.Diagnostics?.MaskPolicy
                ?? draft.Workflow.Diagnostics.MaskPolicy,
        };
    }

    public static IReadOnlyList<string> ParseRedactColumns(string? input)
    {
        return (input ?? string.Empty)
            .Split([',', ';', '\r', '\n'], StringSplitOptions.TrimEntries)
            .Where(item => !string.IsNullOrWhiteSpace(item))
            .Distinct(StringComparer.Ordinal)
            .ToArray();
    }

    private static string FormatInvariant(int value)
    {
        return value.ToString(CultureInfo.InvariantCulture);
    }

    private static string FormatInvariant(double value)
    {
        return value.ToString(CultureInfo.InvariantCulture);
    }

    private static string FormatRedactColumns(IReadOnlyList<string> redactColumns)
    {
        return string.Join(", ", redactColumns);
    }
}
