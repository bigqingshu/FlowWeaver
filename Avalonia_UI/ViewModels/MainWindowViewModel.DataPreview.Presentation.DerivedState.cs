namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    public bool HasTableRefError => !string.IsNullOrWhiteSpace(TableRefErrorMessage);

    public bool HasDataPreviewError =>
        !string.IsNullOrWhiteSpace(DataPreviewErrorMessage);

    public bool HasDataPreviewColumns => DataPreviewColumns.Count > 0;

    public bool HasDataPreviewRows => DataPreviewRows.Count > 0;

    public bool IsDataPreviewBusy => IsLoadingDataPreview;
}
