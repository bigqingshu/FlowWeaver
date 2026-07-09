namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanAddWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(NewDraftConnectionId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourceNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionSourcePort)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetNodeId)
            && !string.IsNullOrWhiteSpace(NewDraftConnectionTargetPort);
    }

    private bool CanDeleteWorkflowDefinitionDraftConnection()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.IsNullOrWhiteSpace(SelectedWorkflowDefinitionDraftConnectionId);
    }
}
