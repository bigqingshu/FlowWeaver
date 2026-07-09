namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetDataPreviewWorkbenchState()
    {
        dataPreviewWorkbenchLoadVersion++;
        IsLoadingDataPreviewWorkbench = false;
        SelectedDataPreviewState = null;
        DataPreviewStates.Clear();
        SelectedDataPreviewTableOption = null;
        DataPreviewTableOptions.Clear();
        SelectedDataPreviewTableRef = null;
        ResetDataPreviewWorkbenchLoadedState();
        DataPreviewWorkbenchColumns.Clear();
        DataPreviewWorkbenchRows.Clear();
        DataPreviewWorkbenchMessage = T("data_preview.workbench_select_table");
        DataPreviewWorkbenchErrorMessage = null;
        NotifyDataPreviewWorkbenchRowsChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

}
