namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void RestoreDataPreviewWorkbenchEditableRows()
    {
        dataPreviewWorkbenchGridState =
            dataPreviewWorkbenchGridState.RestoreEditableRows();
    }
}
