using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftDeleteNodeFailure(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
        WorkflowDefinitionValidationErrorMessage =
            LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_node",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftDeleteNodeSuccess(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_deleted_with_rewired_connections")
                : patchResult.RemovedConnections.Count > 0
                ? T("definition.node_deleted_with_connections")
                : T("definition.node_deleted");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatDeletedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_node",
            UiNotificationKind.Success);
    }
}
