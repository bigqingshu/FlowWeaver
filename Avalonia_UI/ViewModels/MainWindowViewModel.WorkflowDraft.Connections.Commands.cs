using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanAddWorkflowDefinitionDraftConnection))]
    private void AddWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.AddConnection(
            WorkflowDefinitionDraftJson,
            NewDraftConnectionId,
            NewDraftConnectionSourceNodeId,
            NewDraftConnectionSourcePort,
            NewDraftConnectionTargetNodeId,
            NewDraftConnectionTargetPort);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_add_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_added");
        WorkflowDefinitionValidationErrorMessage = null;
        ResetNewDraftConnectionInput();
    }

    [RelayCommand(CanExecute = nameof(CanDeleteWorkflowDefinitionDraftConnection))]
    private void DeleteWorkflowDefinitionDraftConnection()
    {
        var patchResult = WorkflowDefinitionDraftConnectionPatcher.DeleteConnection(
            WorkflowDefinitionDraftJson,
            SelectedWorkflowDefinitionDraftConnectionId);
        if (!patchResult.Succeeded)
        {
            WorkflowDefinitionValidationMessage = T("definition.connection_delete_failed");
            WorkflowDefinitionValidationErrorMessage =
                LocalizeWorkflowDefinitionDraftWarning(patchResult.Warning);
            return;
        }

        WorkflowDefinitionDraftJson = patchResult.UpdatedWorkflowDefinitionDraftJson;
        WorkflowDefinitionValidationMessage = T("definition.connection_deleted");
        WorkflowDefinitionValidationErrorMessage = null;
    }
}
