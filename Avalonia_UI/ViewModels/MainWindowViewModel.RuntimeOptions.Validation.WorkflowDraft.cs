using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryValidateRuntimeOptionsWorkflowDraft(
        RuntimeOptionsWorkflowDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsOption(
            RuntimeOptionsProfileValues,
            draft.Profile,
            RuntimeOptionsProfileText,
            out errorMessage) ||
            !TryValidateRuntimeOptionsTelemetryDraft(
                draft.Telemetry,
                out errorMessage) ||
            !TryValidateRuntimeOptionsDiagnosticsDraft(
                draft.Diagnostics,
                out errorMessage))
        {
            return false;
        }

        errorMessage = string.Empty;
        return true;
    }

    private bool TryValidateRuntimeOptionsTelemetryDraft(
        RuntimeOptionsTelemetryDraft draft,
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

    private bool TryValidateRuntimeOptionsDiagnosticsDraft(
        RuntimeOptionsDiagnosticsDraft draft,
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
