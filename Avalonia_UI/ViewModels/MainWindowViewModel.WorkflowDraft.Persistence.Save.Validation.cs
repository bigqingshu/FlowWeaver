using System.Text.Json;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RejectWorkflowDefinitionSaveWithoutDetail()
    {
        WorkflowDefinitionValidationMessage = T("definition.save_rejected");
        WorkflowDefinitionValidationErrorMessage = T("definition.load_before_saving");
        ShowWorkflowDefinitionNotification(
            "workflow.definition.save",
            UiNotificationKind.Error);
    }

    private bool TryReadWorkflowDefinitionDraftJsonForSave(out JsonElement definition)
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
                "workflow.definition.save",
                UiNotificationKind.Error);
            return false;
        }
    }
}
