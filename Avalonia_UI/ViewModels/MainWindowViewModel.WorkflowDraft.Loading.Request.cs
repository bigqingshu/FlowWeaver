namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool IsStaleWorkflowDefinitionLoadRequest(
        int requestVersion,
        string workflowId)
    {
        return SelectedWorkflow?.WorkflowId != workflowId
            || requestVersion != workflowDefinitionLoadVersion;
    }
}
