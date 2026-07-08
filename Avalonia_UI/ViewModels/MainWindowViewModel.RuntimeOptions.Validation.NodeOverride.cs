using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryValidateRuntimeOptionsNodeOverrideDraft(
        RuntimeOptionsNodeOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage))
        {
            return false;
        }

        if (draft.Telemetry is not null &&
            !TryValidateRuntimeOptionsTelemetryOverrideDraft(
                draft.Telemetry,
                out errorMessage))
        {
            return false;
        }

        if (draft.Diagnostics is not null &&
            !TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryOverrideDraft(
        RuntimeOptionsTelemetryOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsLogLevelValues,
            draft.LogLevel,
            RuntimeOptionsLogLevelText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsEventLevelValues,
                draft.EventLevel,
                RuntimeOptionsEventLevelText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.EventRateLimitPerSecond,
                RuntimeOptionsEventRateLimitText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.ProgressIntervalSeconds,
                RuntimeOptionsProgressIntervalText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsDiagnosticsOverrideDraft(
        RuntimeOptionsDiagnosticsOverrideDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsNonNegative(
            draft.PayloadByteLimit,
            RuntimeOptionsPayloadByteLimitText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsNonNegative(
                draft.TtlSeconds,
                RuntimeOptionsTtlSecondsText,
                out errorMessage) ||
            !TryValidateRuntimeOptionsOption(
                RuntimeOptionsMaskPolicyValues,
                draft.MaskPolicy,
                RuntimeOptionsMaskPolicyText,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }
}
