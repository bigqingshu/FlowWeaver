namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
}
