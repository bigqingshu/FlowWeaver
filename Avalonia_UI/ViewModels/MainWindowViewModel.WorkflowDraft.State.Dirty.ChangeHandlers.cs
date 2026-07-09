namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsWorkflowDefinitionDraftDirtyChanged(bool value)
    {
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }
}
