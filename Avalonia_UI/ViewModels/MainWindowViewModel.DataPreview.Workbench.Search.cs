using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyDataPreviewWorkbenchSearch()
    {
        var visibleRowIndexes = DataPreviewTableGridBuilder.GetVisibleRowIndexes(
            dataPreviewWorkbenchEditableCellRows,
            DataPreviewWorkbenchSearchText);

        RefreshDataPreviewWorkbenchColumns();
        RefreshDataPreviewWorkbenchRows(visibleRowIndexes);
        NotifyDataPreviewWorkbenchRowsChanged();
    }

    private void RefreshDataPreviewWorkbenchColumns()
    {
        DataPreviewWorkbenchColumns.Clear();
        foreach (var column in dataPreviewWorkbenchLoadedColumns)
        {
            DataPreviewWorkbenchColumns.Add(new TableDataPreviewColumnViewModel(column));
        }
    }

    private void RefreshDataPreviewWorkbenchRows(int[] visibleRowIndexes)
    {
        DataPreviewWorkbenchRows.Clear();
        foreach (var rowIndex in visibleRowIndexes)
        {
            DataPreviewWorkbenchRows.Add(CreateDataPreviewWorkbenchRow(rowIndex));
        }
    }
}
