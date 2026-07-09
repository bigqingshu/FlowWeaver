using System.Text.Json;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RejectWorkflowDefinitionDraftValidationWithoutDraft()
    {
        WorkflowDefinitionValidationMessage = T("definition.validation_rejected");
        WorkflowDefinitionValidationErrorMessage = T("definition.draft_required");
        ShowWorkflowDefinitionNotification(
            "workflow.definition.validate",
            UiNotificationKind.Error);
    }

    private bool TryReadWorkflowDefinitionDraftJsonForValidation(out JsonElement definition)
    {
        try
        {
            using var parsed = JsonDocument.Parse(WorkflowDefinitionDraftJson);
            definition = parsed.RootElement.Clone();
            return true;
        }
        catch (JsonException ex)
        {
            definition = default;
            WorkflowDefinitionValidationMessage = T("definition.draft_json_invalid");
            WorkflowDefinitionValidationErrorMessage = ex.Message;
            ShowWorkflowDefinitionNotification(
                "workflow.definition.validate",
                UiNotificationKind.Error);
            return false;
        }
    }
}
