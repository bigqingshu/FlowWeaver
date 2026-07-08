using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryBuildRuntimeOptionsWorkflowDraft(
        out RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsWorkflowDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsPayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsWorkflowDraft
        {
            Profile = RuntimeOptionsProfileDraft,
            StrictValidation = RuntimeOptionsStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryDraft
            {
                LogLevel = RuntimeOptionsLogLevelDraft,
                EventLevel = RuntimeOptionsEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsDraft
            {
                CaptureErrorContext = RuntimeOptionsCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsMaskPolicyDraft,
            },
        };
        return true;
    }
}
