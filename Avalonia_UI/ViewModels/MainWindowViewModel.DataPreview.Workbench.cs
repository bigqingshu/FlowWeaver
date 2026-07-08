namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetDataPreviewWorkbenchState()
    {
        dataPreviewWorkbenchLoadVersion++;
        IsLoadingDataPreviewWorkbench = false;
        SelectedDataPreviewState = null;
        DataPreviewStates.Clear();
        SelectedDataPreviewTableOption = null;
        DataPreviewTableOptions.Clear();
        SelectedDataPreviewTableRef = null;
        ResetDataPreviewWorkbenchLoadedState();
        DataPreviewWorkbenchColumns.Clear();
        DataPreviewWorkbenchRows.Clear();
        DataPreviewWorkbenchMessage = T("data_preview.workbench_select_table");
        DataPreviewWorkbenchErrorMessage = null;
        NotifyDataPreviewWorkbenchRowsChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

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

    private void UpdateDataPreviewWorkbenchLoadedMessage()
    {
        if (LoadedDataPreviewTableRef is null)
        {
            return;
        }

        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        DataPreviewWorkbenchMessage = filter is null
            ? F(
                "format.loaded_data_preview_table_rows",
                dataPreviewWorkbenchLoadedRows.Length,
                dataPreviewWorkbenchRowCount,
                LoadedDataPreviewTableRef.LogicalTableId)
            : F(
                "format.data_preview_search_matches",
                DataPreviewWorkbenchRows.Count,
                dataPreviewWorkbenchLoadedRows.Length,
                filter);
    }

}
