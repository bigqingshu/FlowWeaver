namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnDataPreviewErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewError));
    }
}
