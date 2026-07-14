using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySelectedNodeConfigDraftSuccess(
        NodeConfigDraftApplyResult patchResult,
        bool automatic)
    {
        hasUnappliedNodeConfigChanges = false;
        hasUnappliedSpecializedNodeConfigChanges = false;
        if (automatic)
        {
            foreach (var field in SelectedNodeConfigEditableInputFields)
            {
                field.AcceptChanges();
            }

            SelectedNodeSpecializedEditor?.AcceptChanges();
        }

        preserveSelectedNodeConfigEditorForDraftChange = automatic;
        try
        {
            WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        }
        finally
        {
            preserveSelectedNodeConfigEditorForDraftChange = false;
        }

        WorkflowDefinitionValidationMessage = T("definition.node_config_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        if (!automatic)
        {
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Success);
        }
    }
}
