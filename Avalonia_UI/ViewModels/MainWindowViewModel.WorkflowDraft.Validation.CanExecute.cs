namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanValidateWorkflowDefinitionDraft()
    {
        return CanUseEngineActions && HasWorkflowDefinitionDraft && !IsWorkflowDefinitionDraftBusy;
    }
}
