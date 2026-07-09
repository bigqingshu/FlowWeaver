namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplySelectedNodeConfigDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && HasSelectedNodeConfigEditableInputFields;
    }
}
