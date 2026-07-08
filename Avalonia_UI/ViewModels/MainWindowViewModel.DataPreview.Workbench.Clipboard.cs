using System.Linq;
using Avalonia_UI.Models;
using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanCopyDataPreviewWorkbenchTsv))]
    private void CopyDataPreviewWorkbenchTsv()
    {
        DataPreviewWorkbenchClipboardText = BuildDataPreviewWorkbenchTsv();
    }

    private string BuildDataPreviewWorkbenchTsv()
    {
        return DataPreviewTableGridBuilder.BuildTsv(
            DataPreviewWorkbenchColumns.Select(column => column.Name),
            DataPreviewWorkbenchRows.Select(
                row => row.Cells.Select(cell => cell.Text)));
    }
}
