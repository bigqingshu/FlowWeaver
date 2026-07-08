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
}
