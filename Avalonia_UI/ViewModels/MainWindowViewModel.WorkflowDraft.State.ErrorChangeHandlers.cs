namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnWorkflowDefinitionErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasWorkflowDefinitionError));
    }
}
