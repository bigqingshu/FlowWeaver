using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftDeleteNodesFailure(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
        WorkflowDefinitionValidationErrorMessage =
            LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_nodes",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftDeleteNodesSuccess(
        WorkflowDefinitionDraftNodePatchResult patchResult,
        int deletedNodeCount)
    {
        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage =
            patchResult.RemovedConnections.Count > 0
                ? F(
                    "format.workflow_definition_nodes_deleted_with_connections",
                    deletedNodeCount)
                : F("format.workflow_definition_nodes_deleted", deletedNodeCount);
        WorkflowDefinitionValidationErrorMessage =
            FormatRemovedConnectionsMessage(patchResult.RemovedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.delete_nodes",
            UiNotificationKind.Success);
    }
}
