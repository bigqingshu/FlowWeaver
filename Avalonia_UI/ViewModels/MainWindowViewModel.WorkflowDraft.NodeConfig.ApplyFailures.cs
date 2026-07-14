using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySelectedNodeConfigDraftMissingSelectionFailure(
        bool showNotification)
    {
        WorkflowDefinitionValidationErrorMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        ShowNodeConfigApplyFailureNotification(showNotification);
    }

    private void ApplySelectedNodeConfigDraftConfigBuildFailure(
        NodeConfigEditableDraftConfigResult configResult,
        bool showNotification)
    {
        WorkflowDefinitionValidationErrorMessage =
            FormatNodeConfigApplyErrors(configResult);
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        ShowNodeConfigApplyFailureNotification(showNotification);
    }

    private void ApplySelectedNodeConfigDraftSpecializedValidationFailure(
        string errorMessage,
        bool showNotification)
    {
        WorkflowDefinitionValidationErrorMessage = errorMessage;
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        ShowNodeConfigApplyFailureNotification(showNotification);
    }

    private void ApplySelectedNodeConfigDraftPatchFailure(
        NodeConfigDraftApplyResult patchResult,
        bool showNotification)
    {
        WorkflowDefinitionValidationErrorMessage = patchResult.Warning;
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        ShowNodeConfigApplyFailureNotification(showNotification);
    }

    private void ShowNodeConfigApplyFailureNotification(bool showNotification)
    {
        if (showNotification)
        {
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_config",
                UiNotificationKind.Error);
        }
    }
}
