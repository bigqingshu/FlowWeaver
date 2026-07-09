namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsLoadingWorkflowDefinitionChanged(bool value)
    {
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
    }
}
