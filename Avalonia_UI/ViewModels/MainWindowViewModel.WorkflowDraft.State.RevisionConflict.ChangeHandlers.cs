namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnHasWorkflowDefinitionRevisionConflictChanged(bool value)
    {
        NotifyWorkflowDefinitionRevisionConflictChangedCommands();
        OnPropertyChanged(nameof(WorkflowRunGuardText));
    }
}
