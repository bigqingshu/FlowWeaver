using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
