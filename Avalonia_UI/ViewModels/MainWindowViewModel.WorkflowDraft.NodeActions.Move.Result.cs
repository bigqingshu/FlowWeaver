using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftMoveNodeFailure(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_move_failed");
        WorkflowDefinitionValidationErrorMessage =
            LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.move_node",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftMoveNodeSuccess(
        WorkflowDefinitionDraftNodePatchResult patchResult,
        string nodeInstanceId)
    {
        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_moved_with_rewired_connections")
                : T("definition.node_moved");
        WorkflowDefinitionValidationErrorMessage =
            patchResult.AddedConnections.Count > 0
                ? FormatMovedRewiredConnectionsMessage(
                    patchResult.RemovedConnections,
                    patchResult.AddedConnections)
                : null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.move_node",
            UiNotificationKind.Success);
    }
}
