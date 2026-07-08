using CommunityToolkit.Mvvm.ComponentModel;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [ObservableProperty]
    private bool isWorkflowDefinitionDraftDirty;

    partial void OnIsWorkflowDefinitionDraftDirtyChanged(bool value)
    {
        RestoreWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }
}
