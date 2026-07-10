namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void BeginWorkflowDefinitionDraftSave()
    {
        IsSavingWorkflowDefinitionDraft = true;
        WorkflowDefinitionValidationMessage = T("definition.saving_draft");
        WorkflowDefinitionValidationErrorMessage = null;
    }

    private void CompleteWorkflowDefinitionDraftSave()
    {
        IsSavingWorkflowDefinitionDraft = false;
    }
}
