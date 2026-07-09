using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftAddNodeFailure(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_add_failed");
        WorkflowDefinitionValidationErrorMessage =
            LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.add_node",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftAddNodeSuccess(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(NewDraftNodeInstanceId);
        WorkflowDefinitionValidationMessage =
            patchResult.AddedConnections.Count > 0
                ? T("definition.node_added_with_connections")
                : T("definition.node_added");
        WorkflowDefinitionValidationErrorMessage =
            FormatAutoWiredConnectionsMessage(
                patchResult.RemovedConnections,
                patchResult.AddedConnections);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.add_node",
            UiNotificationKind.Success);
        ResetNewDraftNodeInput();
    }
}
