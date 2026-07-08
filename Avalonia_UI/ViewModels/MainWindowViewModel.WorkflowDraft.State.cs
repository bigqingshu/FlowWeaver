using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnWorkflowDefinitionDetailChanged(WorkflowDefinitionDetailViewModel? value)
    {
        ClearWorkflowDefinitionDraftBatchSelection();
        ResetWorkflowDefinitionStructuredEditInput();
        OnPropertyChanged(nameof(HasWorkflowDefinition));
        OnPropertyChanged(nameof(SelectedRunRuntimeOptionsSummaryText));
        RefreshSelectedNodeDisplayNameDraftState();
        RefreshSelectedNodeConfigDraftState();
        RefreshRuntimeOptionsDraftState();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeDisplayNameDraftCommand.NotifyCanExecuteChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    partial void OnWorkflowDefinitionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionError));
    }

    partial void OnWorkflowDefinitionDraftStructureChanged(
        WorkflowDefinitionDraftStructure? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructure));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCount));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCount));
        OnPropertyChanged(nameof(WorkflowDefinitionBatchSelectedNodeCountText));
        OnPropertyChanged(nameof(WorkflowDefinitionDraftConnectionCountText));
        OnPropertyChanged(nameof(HasWorkflowDefinitionDraftStructureWarnings));
        if (SelectedRuntimeOptionsNode is not null &&
            !WorkflowDefinitionDraftNodes.Contains(SelectedRuntimeOptionsNode))
        {
            SelectedRuntimeOptionsNode = null;
        }

        NotifyWorkflowDefinitionNodeActionCommandsChanged();
    }

    partial void OnIsWorkflowDefinitionDraftDirtyChanged(bool value)
    {
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }

    partial void OnHasWorkflowDefinitionRevisionConflictChanged(bool value)
    {
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
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }

    partial void OnIsWorkflowDraftJsonAdvancedVisibleChanged(bool value)
    {
        OnPropertyChanged(nameof(ShowAdvancedDraftJsonText));
    }
}
