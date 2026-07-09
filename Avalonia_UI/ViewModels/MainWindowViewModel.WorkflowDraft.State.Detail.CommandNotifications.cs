namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowDefinitionDetailChangedCommands()
    {
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
}
