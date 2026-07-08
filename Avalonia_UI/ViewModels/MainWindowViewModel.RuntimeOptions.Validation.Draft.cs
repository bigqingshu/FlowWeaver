using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryValidateRuntimeOptionsDraft(
        RuntimeOptionsDraft draft,
        out string errorMessage)
    {
        if (!TryValidateRuntimeOptionsWorkflowDraft(draft.Workflow, out errorMessage))
        {
            return false;
        }

        foreach (var nodeOverride in draft.NodeOverrides.Values)
        {
            if (!TryValidateRuntimeOptionsNodeOverrideDraft(
                nodeOverride,
                out errorMessage))
            {
                return false;
            }
        }

        errorMessage = string.Empty;
        return true;
    }
}
