using System.Linq;
using Avalonia_UI.Api;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void LoadDataPreviewRows(TableDataRowsDto rows)
    {
        var grid = DataPreviewTableGridBuilder.BuildGrid(rows);

        DataPreviewColumns.Clear();
        foreach (var column in grid.Columns)
        {
            DataPreviewColumns.Add(new TableDataPreviewColumnViewModel(column));
        }

        DataPreviewRows.Clear();
        foreach (var row in grid.CellRows)
        {
            DataPreviewRows.Add(
                new TableDataPreviewRowViewModel(
                    row
                        .Select(value => new TableDataPreviewCellViewModel(value))
                        .ToArray()));
        }

        NotifyDataPreviewRowsChanged();
    }
}
