using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplySelectedNodeConfigDraftMissingSelectionFailure()
    {
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        WorkflowDefinitionValidationErrorMessage =
            DisplayTextFormatter.FormatSelectedNodeConfigDraftMissingSelection();
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Error);
    }

    private void ApplySelectedNodeConfigDraftConfigBuildFailure(
        NodeConfigEditableDraftConfigResult configResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        WorkflowDefinitionValidationErrorMessage =
            FormatNodeConfigApplyErrors(configResult);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Error);
    }

    private void ApplySelectedNodeConfigDraftSpecializedValidationFailure(
        string errorMessage)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        WorkflowDefinitionValidationErrorMessage = errorMessage;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Error);
    }

    private void ApplySelectedNodeConfigDraftPatchFailure(
        NodeConfigDraftApplyResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_config_apply_failed");
        WorkflowDefinitionValidationErrorMessage = patchResult.Warning;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_config",
            UiNotificationKind.Error);
    }
}
