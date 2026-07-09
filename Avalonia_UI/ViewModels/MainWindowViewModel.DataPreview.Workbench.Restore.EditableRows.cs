using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RestoreDataPreviewWorkbenchEditableRows()
    {
        dataPreviewWorkbenchEditableCellRows =
            DataPreviewTableGridBuilder.CloneCellRows(dataPreviewWorkbenchOriginalCellRows);
    }
}
