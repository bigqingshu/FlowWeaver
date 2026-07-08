using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftNode))]
    private void DeleteWorkflowDefinitionDraftNode()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var patchResult = WorkflowDefinitionDraftNodePatcher.DeleteNodeWithLinearBridge(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionNode.NodeInstanceId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.delete_node",
                UiNotificationKind.Error);
            return;
        }

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
