using System;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanApplySelectedNodeDisplayNameDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && SelectedWorkflowDefinitionNode is not null
            && HasWorkflowDefinitionDraft
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict
            && !string.Equals(
                SelectedNodeDisplayNameDraft.Trim(),
                SelectedWorkflowDefinitionNode.DisplayName,
                StringComparison.Ordinal);
    }

    [RelayCommand(CanExecute = nameof(CanApplySelectedNodeDisplayNameDraft))]
    private void ApplySelectedNodeDisplayNameDraft()
    {
        if (SelectedWorkflowDefinitionNode is null)
        {
            return;
        }

        var nodeInstanceId = SelectedWorkflowDefinitionNode.NodeInstanceId;
        var patchResult = WorkflowDefinitionDraftNodePatcher.UpdateDisplayName(
            WorkflowDefinitionDraftJson,
            nodeInstanceId,
            SelectedNodeDisplayNameDraft);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.node_display_name_apply_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            ShowWorkflowDefinitionNotification(
                "workflow.definition.node_display_name",
                UiNotificationKind.Error);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        SelectWorkflowDefinitionDraftNode(nodeInstanceId);
        WorkflowDefinitionValidationMessage = T("definition.node_display_name_applied");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.node_display_name",
            UiNotificationKind.Success);
    }
}
