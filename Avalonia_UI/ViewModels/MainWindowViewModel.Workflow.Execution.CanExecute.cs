namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanStartSelectedWorkflow()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && IsActiveWorkflowStatus(SelectedWorkflow.Status)
            && !IsWorkflowBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }
}
