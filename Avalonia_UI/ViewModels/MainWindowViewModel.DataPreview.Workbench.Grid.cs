using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void LoadDataPreviewWorkbenchRows(TableDataRowsDto rows, bool isDraft = false)
    {
        var gridState = DataPreviewTableGridBuilder.BuildWorkbenchState(rows);
        IsDataPreviewWorkbenchDraft = isDraft;
        dataPreviewWorkbenchLoadedColumns = gridState.Columns;
        dataPreviewWorkbenchLoadedRows = gridState.Rows;
        dataPreviewWorkbenchOriginalCellRows = gridState.OriginalCellRows;
        dataPreviewWorkbenchEditableCellRows = gridState.EditableCellRows;
        dataPreviewWorkbenchOffset = gridState.Offset;
        dataPreviewWorkbenchHasMore = gridState.HasMore;
        dataPreviewWorkbenchRowCount = gridState.RowCount;
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    private void ApplyDataPreviewWorkbenchSearch()
    {
        var visibleRowIndexes = DataPreviewTableGridBuilder.GetVisibleRowIndexes(
            dataPreviewWorkbenchEditableCellRows,
            DataPreviewWorkbenchSearchText);

        DataPreviewWorkbenchColumns.Clear();
        foreach (var column in dataPreviewWorkbenchLoadedColumns)
        {
            DataPreviewWorkbenchColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewWorkbenchRows.Clear();
        foreach (var rowIndex in visibleRowIndexes)
        {
            DataPreviewWorkbenchRows.Add(CreateDataPreviewWorkbenchRow(rowIndex));
        }

        NotifyDataPreviewWorkbenchRowsChanged();
    }

    private TableDataPreviewRowViewModel CreateDataPreviewWorkbenchRow(int rowIndex)
    {
        return new TableDataPreviewRowViewModel(
            dataPreviewWorkbenchEditableCellRows[rowIndex]
                .Select(
                    (value, columnIndex) =>
                        new TableDataPreviewCellViewModel(
                            value,
                            updatedValue => UpdateDataPreviewWorkbenchCell(
                                rowIndex,
                                columnIndex,
                                updatedValue)))
                .ToArray());
    }

    private string BuildDataPreviewWorkbenchTsv()
    {
        return DataPreviewTableGridBuilder.BuildTsv(
            DataPreviewWorkbenchColumns.Select(column => column.Name),
            DataPreviewWorkbenchRows.Select(
                row => row.Cells.Select(cell => cell.Text)));
    }
}
