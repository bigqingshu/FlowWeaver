using System;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyWorkflowDefinitionDraftCopyNodeFailure(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionValidationMessage = T("definition.node_copy_failed");
        WorkflowDefinitionValidationErrorMessage =
            LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
        ShowWorkflowDefinitionNotification(
            "workflow.definition.copy_node",
            UiNotificationKind.Error);
    }

    private void ApplyWorkflowDefinitionDraftCopyNodeSuccess(
        WorkflowDefinitionDraftNodePatchResult patchResult)
    {
        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        if (!string.IsNullOrWhiteSpace(patchResult.AddedNodeInstanceId))
        {
            SelectWorkflowDefinitionDraftNode(patchResult.AddedNodeInstanceId);
        }

        WorkflowDefinitionValidationMessage = T("definition.node_copied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.copy_node",
            UiNotificationKind.Success);
    }
}
