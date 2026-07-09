namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplyRuntimeOptionsDraft()
    {
        return HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }
}
