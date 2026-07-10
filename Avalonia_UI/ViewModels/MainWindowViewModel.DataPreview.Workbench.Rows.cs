using System.Linq;
using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private TableDataPreviewRowViewModel CreateDataPreviewWorkbenchRow(int rowIndex)
    {
        return new TableDataPreviewRowViewModel(
            dataPreviewWorkbenchGridState.EditableCellRows[rowIndex]
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
}
