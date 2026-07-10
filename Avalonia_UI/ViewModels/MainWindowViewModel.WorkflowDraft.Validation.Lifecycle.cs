namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void BeginWorkflowDefinitionDraftValidation()
    {
        IsValidatingWorkflowDefinitionDraft = true;
        WorkflowDefinitionValidationMessage = T("definition.validating_draft");
        WorkflowDefinitionValidationErrorMessage = null;
    }
}
