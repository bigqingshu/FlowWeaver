using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftValidationSuccess(
        WorkflowValidationResultDto result)
    {
        WorkflowDefinitionValidationMessage = result.Valid
            ? T("definition.draft_valid")
            : T("definition.draft_has_issues");
        WorkflowDefinitionValidationErrorMessage = FormatValidationIssues(result);
        IsValidatingWorkflowDefinitionDraft = false;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.validate",
            result.Valid ? UiNotificationKind.Success : UiNotificationKind.Warning);
    }

    private void ApplyWorkflowDefinitionDraftValidationFailure(
        ApiResponseEnvelope<WorkflowValidationResultDto> response)
    {
        WorkflowDefinitionValidationMessage = T("definition.validation_failed");
        WorkflowDefinitionValidationErrorMessage = DescribeError(response);
        IsValidatingWorkflowDefinitionDraft = false;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.validate",
            UiNotificationKind.Error);
    }
}
