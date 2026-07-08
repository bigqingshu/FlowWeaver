using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private string BuildDataPreviewWorkbenchTsv()
    {
        return DataPreviewTableGridBuilder.BuildTsv(
            DataPreviewWorkbenchColumns.Select(column => column.Name),
            DataPreviewWorkbenchRows.Select(
                row => row.Cells.Select(cell => cell.Text)));
    }
}
