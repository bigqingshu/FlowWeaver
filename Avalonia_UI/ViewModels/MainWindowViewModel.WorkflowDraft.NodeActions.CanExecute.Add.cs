namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanAddWorkflowDefinitionDraftNode()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftNodeInstanceId)
            && !string.IsNullOrWhiteSpace(NewDraftNodeType)
            && !string.IsNullOrWhiteSpace(NewDraftNodeVersion)
            && !string.IsNullOrWhiteSpace(NewDraftNodeConfigJson);
    }
}
