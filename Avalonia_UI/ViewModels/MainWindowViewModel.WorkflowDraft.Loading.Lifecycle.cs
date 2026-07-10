namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private int BeginWorkflowDefinitionLoad(string workflowName)
    {
        var requestVersion = ++workflowDefinitionLoadVersion;
        IsLoadingWorkflowDefinition = true;
        WorkflowDefinitionMessage = F(
            "format.loading_definition_for",
            workflowName);
        WorkflowDefinitionErrorMessage = null;
        return requestVersion;
    }

    private void CompleteWorkflowDefinitionLoad(int requestVersion)
    {
        if (requestVersion == workflowDefinitionLoadVersion)
        {
            IsLoadingWorkflowDefinition = false;
        }
    }
}
