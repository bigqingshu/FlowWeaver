namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanPreviewSelectedWorkflowNode()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && !IsWorkflowBusy
            && !IsDataPreviewBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }
}
