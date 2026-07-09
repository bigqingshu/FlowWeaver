namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
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
