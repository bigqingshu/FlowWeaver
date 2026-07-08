namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanLoadSelectedWorkflowDefinition()
    {
        return CanUseEngineActions
            && SelectedWorkflow is not null
            && !IsLoadingWorkflowDefinition;
    }
}
