namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasDataPreviewWorkbenchError =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchErrorMessage);

    public bool HasDataPreviewWorkbenchColumns => DataPreviewWorkbenchColumns.Count > 0;

    public bool HasDataPreviewWorkbenchRows => DataPreviewWorkbenchRows.Count > 0;

    public bool HasDataPreviewWorkbenchClipboardText =>
        !string.IsNullOrEmpty(DataPreviewWorkbenchClipboardText);

    public bool HasDataPreviewWorkbenchPasteText =>
        !string.IsNullOrWhiteSpace(DataPreviewWorkbenchPasteText);

    public bool IsDataPreviewWorkbenchDirty => dataPreviewWorkbenchGridState.IsDirty;

    public bool CanSaveDataPreviewWorkbenchAsDraft =>
        LoadedDataPreviewTableRef?.HasCapability("SAVE_AS") == true;

    public bool IsDataPreviewWorkbenchBusy => IsLoadingDataPreviewWorkbench;
}
