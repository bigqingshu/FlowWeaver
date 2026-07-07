using System.Collections.Generic;

namespace Avalonia_UI.Models;

public sealed record RuntimeOptionsDraft
{
    public string Version { get; init; } = RuntimeOptionsDefaults.Version;

    public RuntimeOptionsWorkflowDraft Workflow { get; init; } = new();

    public IReadOnlyDictionary<string, RuntimeOptionsNodeOverrideDraft> NodeOverrides
    {
        get;
        init;
    } = new Dictionary<string, RuntimeOptionsNodeOverrideDraft>();
}

public sealed record RuntimeOptionsWorkflowDraft
{
    public string Profile { get; init; } = RuntimeOptionsDefaults.Profile;

    public bool StrictValidation { get; init; } = true;

    public RuntimeOptionsTelemetryDraft Telemetry { get; init; } = new();

    public RuntimeOptionsDiagnosticsDraft Diagnostics { get; init; } = new();
}

public sealed record RuntimeOptionsTelemetryDraft
{
    public string LogLevel { get; init; } = RuntimeOptionsDefaults.LogLevel;

    public string EventLevel { get; init; } = RuntimeOptionsDefaults.EventLevel;

    public int EventRateLimitPerSecond { get; init; }

    public bool ProgressEnabled { get; init; } = true;

    public double ProgressIntervalSeconds { get; init; }
}

public sealed record RuntimeOptionsDiagnosticsDraft
{
    public bool CaptureErrorContext { get; init; } = true;

    public bool IncludeMetrics { get; init; } = true;

    public int PayloadByteLimit { get; init; }

    public int TtlSeconds { get; init; }

    public IReadOnlyList<string> RedactColumns { get; init; } = [];

    public string MaskPolicy { get; init; } = RuntimeOptionsDefaults.MaskPolicy;
}

public sealed record RuntimeOptionsNodeOverrideDraft
{
    public string? Profile { get; init; }

    public bool? StrictValidation { get; init; }

    public RuntimeOptionsTelemetryOverrideDraft? Telemetry { get; init; }

    public RuntimeOptionsDiagnosticsOverrideDraft? Diagnostics { get; init; }
}

public sealed record RuntimeOptionsTelemetryOverrideDraft
{
    public string? LogLevel { get; init; }

    public string? EventLevel { get; init; }

    public int? EventRateLimitPerSecond { get; init; }

    public bool? ProgressEnabled { get; init; }

    public double? ProgressIntervalSeconds { get; init; }
}

public sealed record RuntimeOptionsDiagnosticsOverrideDraft
{
    public bool? CaptureErrorContext { get; init; }

    public bool? IncludeMetrics { get; init; }

    public int? PayloadByteLimit { get; init; }

    public int? TtlSeconds { get; init; }

    public IReadOnlyList<string>? RedactColumns { get; init; }

    public string? MaskPolicy { get; init; }
}

public static class RuntimeOptionsDefaults
{
    public const string Version = "1.0";

    public const string Profile = "normal";

    public const string LogLevel = "INFO";

    public const string EventLevel = "progress";

    public const string MaskPolicy = "none";
}
