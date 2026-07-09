namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanLoadPreviousDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchOffset > 0;
    }

    private bool CanLoadNextDataPreviewWorkbenchPage()
    {
        return CanUseEngineActions
            && LoadedDataPreviewTableRef is not null
            && !IsLoadingDataPreviewWorkbench
            && dataPreviewWorkbenchHasMore;
    }
}
