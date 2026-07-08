using System.Threading.Tasks;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.ComponentModel;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isSavingWorkflowDefinitionDraft;

    private bool CanRestoreWorkflowDefinitionDraft()
    {
        return HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy;
    }

    private bool CanSaveWorkflowDefinitionDraft()
    {
        return CanUseEngineActions
            && WorkflowDefinitionDetail is not null
            && HasWorkflowDefinitionDraft
            && IsWorkflowDefinitionDraftDirty
            && !IsWorkflowDefinitionDraftBusy
            && !HasWorkflowDefinitionRevisionConflict;
    }

    [RelayCommand(CanExecute = nameof(CanRestoreWorkflowDefinitionDraft))]
    private void RestoreWorkflowDefinitionDraft()
    {
        if (!CanRestoreWorkflowDefinitionDraft())
        {
            return;
        }

        var selectedNodeId = SelectedWorkflowDefinitionNode?.NodeInstanceId;
        WorkflowDefinitionDraftJson = originalWorkflowDefinitionJson;
        if (!string.IsNullOrWhiteSpace(selectedNodeId))
        {
            SelectWorkflowDefinitionDraftNode(selectedNodeId);
        }

        WorkflowDefinitionValidationMessage = T("definition.draft_restored");
        WorkflowDefinitionValidationErrorMessage = null;
        ShowWorkflowDefinitionNotification(
            "workflow.definition.restore",
            UiNotificationKind.Success);
    }

    [RelayCommand(CanExecute = nameof(CanSaveWorkflowDefinitionDraft))]
    private async Task SaveWorkflowDefinitionDraftAsync()
    {
        await TrySaveWorkflowDefinitionDraftAsync();
    }

    partial void OnIsSavingWorkflowDefinitionDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(IsWorkflowDefinitionDraftBusy));
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }
}
