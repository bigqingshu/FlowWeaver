namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanLoadSelectedDataPreviewTable()
    {
        return CanUseEngineActions
            && SelectedDataPreviewTableOption is not null
            && SelectedDataPreviewTableOption.CanReadRows
            && !IsLoadingDataPreviewWorkbench;
    }
}
