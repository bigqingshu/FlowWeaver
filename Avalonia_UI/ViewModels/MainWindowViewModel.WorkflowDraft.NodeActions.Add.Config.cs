using System.Text.Json;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool TryReadNewDraftNodeConfigJson(out JsonElement config)
    {
        try
        {
            using var parsed = JsonDocument.Parse(NewDraftNodeConfigJson);
            config = parsed.RootElement.Clone();
            return true;
        }
        catch (JsonException)
        {
            config = default;
            WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                T("definition.node_add_config_json_invalid");
            ShowWorkflowDefinitionNotification(
                "workflow.definition.add_node",
                UiNotificationKind.Error);
            return false;
        }
    }
}
