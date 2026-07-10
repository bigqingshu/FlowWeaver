using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ApplyDataPreviewWorkbenchSearch()
    {
        var visibleRowIndexes = DataPreviewTableGridBuilder.GetVisibleRowIndexes(
            dataPreviewWorkbenchGridState.EditableCellRows,
            DataPreviewWorkbenchSearchText);

        RefreshDataPreviewWorkbenchColumns();
        RefreshDataPreviewWorkbenchRows(visibleRowIndexes);
        NotifyDataPreviewWorkbenchRowsChanged();
    }

    private void RefreshDataPreviewWorkbenchColumns()
    {
        DataPreviewWorkbenchColumns.Clear();
        foreach (var column in dataPreviewWorkbenchGridState.Columns)
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
