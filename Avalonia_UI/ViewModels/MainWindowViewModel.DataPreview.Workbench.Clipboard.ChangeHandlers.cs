namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnDataPreviewWorkbenchClipboardTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchClipboardText));
    }
}
