namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnRuntimeOptionsEditorErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasRuntimeOptionsEditorError));
    }
}
