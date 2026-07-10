namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void UpdateDataPreviewWorkbenchCell(
        int rowIndex,
        int columnIndex,
        string value)
    {
        if (!dataPreviewWorkbenchGridState.TryUpdateCell(
                rowIndex,
                columnIndex,
                value))
        {
            return;
        }

        DataPreviewWorkbenchClipboardText = string.Empty;
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }
}
