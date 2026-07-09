namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetDataPreviewWorkbenchLoadedState()
    {
        LoadedDataPreviewTableRef = null;
        dataPreviewWorkbenchLoadedColumns = [];
        dataPreviewWorkbenchLoadedRows = [];
        dataPreviewWorkbenchOriginalCellRows = [];
        dataPreviewWorkbenchEditableCellRows = [];
        dataPreviewWorkbenchOffset = 0;
        dataPreviewWorkbenchHasMore = false;
        dataPreviewWorkbenchRowCount = 0;
        DataPreviewWorkbenchClipboardText = string.Empty;
        IsDataPreviewWorkbenchDraft = false;
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }
}
