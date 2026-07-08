namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnDataPreviewWorkbenchErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchError));
    }
}
