namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private bool CanLoadSelectedDataPreviewTable()
    {
        return CanUseEngineActions
            && SelectedDataPreviewTableOption is not null
            && !IsLoadingDataPreviewWorkbench;
    }

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

    private bool CanCopyDataPreviewWorkbenchTsv()
    {
        return HasDataPreviewWorkbenchColumns
            && HasDataPreviewWorkbenchRows;
    }

    private bool CanParseDataPreviewWorkbenchPaste()
    {
        return HasDataPreviewWorkbenchPasteText
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanRestoreDataPreviewWorkbenchDraft()
    {
        return IsDataPreviewWorkbenchDirty
            && !IsLoadingDataPreviewWorkbench;
    }

    private bool CanSaveDataPreviewWorkbenchAs()
    {
        return IsDataPreviewWorkbenchDirty
            && CanSaveDataPreviewWorkbenchAsDraft
            && !IsLoadingDataPreviewWorkbench;
    }
}
