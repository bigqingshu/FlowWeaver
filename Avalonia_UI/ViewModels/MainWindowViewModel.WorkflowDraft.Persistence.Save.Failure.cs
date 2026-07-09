using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftRevisionConflictSaveFailure()
    {
        HasWorkflowDefinitionRevisionConflict = true;
        WorkflowDefinitionValidationMessage = T("definition.save_failed");
        WorkflowDefinitionValidationErrorMessage = T("definition.revision_conflict");
        ShowWorkflowDefinitionNotification(
            "workflow.definition.save",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftSaveFailure(
        ApiResponseEnvelope<WorkflowDefinitionDto> response)
    {
        WorkflowDefinitionValidationMessage = T("definition.save_failed");
        WorkflowDefinitionValidationErrorMessage = DescribeError(response);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.save",
            UiNotificationKind.Error);
    }
}
