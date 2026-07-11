using System;
using System.Collections.Generic;
using System.Linq;
using Avalonia_UI.Api;

namespace Avalonia_UI.Models;

public sealed record RuntimeFeedbackPolicyOverrideDraft
{
    public string? LogLevel { get; init; }

    public string? EventLevel { get; init; }

    public int? EventRateLimitPerSecond { get; init; }

    public bool? ProgressEnabled { get; init; }

    public double? ProgressIntervalSeconds { get; init; }

    public bool? CaptureErrorContext { get; init; }

    public bool? IncludeMetrics { get; init; }

    public int? PayloadByteLimit { get; init; }

    public IReadOnlyList<string>? RedactColumns { get; init; }

    public string? MaskPolicy { get; init; }

    public bool IsEmpty =>
        LogLevel is null
        && EventLevel is null
        && EventRateLimitPerSecond is null
        && ProgressEnabled is null
        && ProgressIntervalSeconds is null
        && CaptureErrorContext is null
        && IncludeMetrics is null
        && PayloadByteLimit is null
        && RedactColumns is null
        && MaskPolicy is null;
}

public sealed record WorkflowRunRuntimeOptionsDraft
{
    public RuntimeFeedbackPolicyOverrideDraft Workflow { get; init; } = new();

    public IReadOnlyDictionary<string, RuntimeFeedbackPolicyOverrideDraft> NodeOverrides
    {
        get;
        init;
    } = new Dictionary<string, RuntimeFeedbackPolicyOverrideDraft>();
}

public static class WorkflowRunRuntimeOptionsDraftMapper
{
    public static WorkflowRunRuntimeOptionsDraft FromDto(
        WorkflowRunRuntimeOptionsOverlayDto overlay)
    {
        return new WorkflowRunRuntimeOptionsDraft
        {
            Workflow = FromDto(overlay.Workflow),
            NodeOverrides = overlay.NodeOverrides.ToDictionary(
                item => item.Key,
                item => FromDto(item.Value),
                StringComparer.Ordinal),
        };
    }

    public static WorkflowRunRuntimeOptionsOverlayDto ToDto(
        WorkflowRunRuntimeOptionsDraft draft)
    {
        return new WorkflowRunRuntimeOptionsOverlayDto
        {
            Workflow = draft.Workflow.IsEmpty ? null : ToDto(draft.Workflow),
            NodeOverrides = draft.NodeOverrides
                .Where(item => !item.Value.IsEmpty)
                .ToDictionary(
                    item => item.Key,
                    item => ToDto(item.Value),
                    StringComparer.Ordinal),
        };
    }

    private static RuntimeFeedbackPolicyOverrideDraft FromDto(
        RuntimeFeedbackPolicyOverrideDto? value)
    {
        return new RuntimeFeedbackPolicyOverrideDraft
        {
            LogLevel = value?.Telemetry?.LogLevel,
            EventLevel = value?.Telemetry?.EventLevel,
            EventRateLimitPerSecond = value?.Telemetry?.EventRateLimitPerSecond,
            ProgressEnabled = value?.Telemetry?.ProgressEnabled,
            ProgressIntervalSeconds = value?.Telemetry?.ProgressIntervalSeconds,
            CaptureErrorContext = value?.Diagnostics?.CaptureErrorContext,
            IncludeMetrics = value?.Diagnostics?.IncludeMetrics,
            PayloadByteLimit = value?.Diagnostics?.PayloadByteLimit,
            RedactColumns = value?.Diagnostics?.RedactColumns?.ToArray(),
            MaskPolicy = value?.Diagnostics?.MaskPolicy,
        };
    }

    private static RuntimeFeedbackPolicyOverrideDto ToDto(
        RuntimeFeedbackPolicyOverrideDraft value)
    {
        var hasTelemetry = value.LogLevel is not null
            || value.EventLevel is not null
            || value.EventRateLimitPerSecond is not null
            || value.ProgressEnabled is not null
            || value.ProgressIntervalSeconds is not null;
        var hasDiagnostics = value.CaptureErrorContext is not null
            || value.IncludeMetrics is not null
            || value.PayloadByteLimit is not null
            || value.RedactColumns is not null
            || value.MaskPolicy is not null;
        return new RuntimeFeedbackPolicyOverrideDto
        {
            Telemetry = hasTelemetry
                ? new RuntimeFeedbackTelemetryOverrideDto
                {
                    LogLevel = value.LogLevel,
                    EventLevel = value.EventLevel,
                    EventRateLimitPerSecond = value.EventRateLimitPerSecond,
                    ProgressEnabled = value.ProgressEnabled,
                    ProgressIntervalSeconds = value.ProgressIntervalSeconds,
                }
                : null,
            Diagnostics = hasDiagnostics
                ? new RuntimeFeedbackDiagnosticsOverrideDto
                {
                    CaptureErrorContext = value.CaptureErrorContext,
                    IncludeMetrics = value.IncludeMetrics,
                    PayloadByteLimit = value.PayloadByteLimit,
                    RedactColumns = value.RedactColumns?.ToList(),
                    MaskPolicy = value.MaskPolicy,
                }
                : null,
        };
    }
}
