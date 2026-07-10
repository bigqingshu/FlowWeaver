namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void UpdateDataPreviewWorkbenchLoadedMessage()
    {
        if (LoadedDataPreviewTableRef is null)
        {
            return;
        }

        var filter = NormalizeFilter(DataPreviewWorkbenchSearchText);
        DataPreviewWorkbenchMessage = filter is null
            ? FormatDataPreviewWorkbenchLoadedRowsMessage()
            : FormatDataPreviewWorkbenchSearchMatchesMessage(filter);
    }

    private string FormatDataPreviewWorkbenchLoadedRowsMessage()
    {
        return F(
            "format.loaded_data_preview_table_rows",
            dataPreviewWorkbenchGridState.Rows.Length,
            dataPreviewWorkbenchGridState.RowCount,
            LoadedDataPreviewTableRef!.LogicalTableId);
    }

    private string FormatDataPreviewWorkbenchSearchMatchesMessage(string filter)
    {
        return F(
            "format.data_preview_search_matches",
            DataPreviewWorkbenchRows.Count,
            dataPreviewWorkbenchGridState.Rows.Length,
            filter);
    }
}
