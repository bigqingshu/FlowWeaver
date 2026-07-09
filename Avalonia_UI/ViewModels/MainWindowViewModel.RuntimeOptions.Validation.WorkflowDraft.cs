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

}
