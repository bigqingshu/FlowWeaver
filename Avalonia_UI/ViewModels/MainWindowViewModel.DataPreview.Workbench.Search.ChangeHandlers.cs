namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnDataPreviewWorkbenchSearchTextChanged(string value)
    {
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        UpdateDataPreviewWorkbenchLoadedMessage();
    }
}
