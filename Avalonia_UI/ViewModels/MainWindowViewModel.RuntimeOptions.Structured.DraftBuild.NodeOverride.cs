using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryBuildSelectedRuntimeOptionsNodeOverrideDraft(
        out RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        draft = new RuntimeOptionsNodeOverrideDraft();
        errorMessage = string.Empty;
        if (!TryParseNonNegativeInt(
            RuntimeOptionsSelectedNodeEventRateLimitPerSecondDraft,
            RuntimeOptionsEventRateLimitText,
            out var eventRateLimit,
            out errorMessage) ||
            !TryParseNonNegativeDouble(
                RuntimeOptionsSelectedNodeProgressIntervalSecondsDraft,
                RuntimeOptionsProgressIntervalText,
                out var progressInterval,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodePayloadByteLimitDraft,
                RuntimeOptionsPayloadByteLimitText,
                out var payloadByteLimit,
                out errorMessage) ||
            !TryParseNonNegativeInt(
                RuntimeOptionsSelectedNodeTtlSecondsDraft,
                RuntimeOptionsTtlSecondsText,
                out var ttlSeconds,
                out errorMessage))
        {
            return false;
        }

        draft = new RuntimeOptionsNodeOverrideDraft
        {
            Profile = RuntimeOptionsSelectedNodeProfileDraft,
            StrictValidation = RuntimeOptionsSelectedNodeStrictValidationDraft,
            Telemetry = new RuntimeOptionsTelemetryOverrideDraft
            {
                LogLevel = RuntimeOptionsSelectedNodeLogLevelDraft,
                EventLevel = RuntimeOptionsSelectedNodeEventLevelDraft,
                EventRateLimitPerSecond = eventRateLimit,
                ProgressEnabled = RuntimeOptionsSelectedNodeProgressEnabledDraft,
                ProgressIntervalSeconds = progressInterval,
            },
            Diagnostics = new RuntimeOptionsDiagnosticsOverrideDraft
            {
                CaptureErrorContext =
                    RuntimeOptionsSelectedNodeCaptureErrorContextDraft,
                IncludeMetrics = RuntimeOptionsSelectedNodeIncludeMetricsDraft,
                PayloadByteLimit = payloadByteLimit,
                TtlSeconds = ttlSeconds,
                RedactColumns = RuntimeOptionsDraftStateMapper.ParseRedactColumns(
                    RuntimeOptionsSelectedNodeRedactColumnsDraft),
                MaskPolicy = RuntimeOptionsSelectedNodeMaskPolicyDraft,
            },
        };
        return true;
    }
}
