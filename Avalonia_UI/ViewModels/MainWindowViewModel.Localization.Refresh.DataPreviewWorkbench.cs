namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyDataPreviewWorkbenchLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchPendingText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(DataPreviewTableSelectorText));
        OnPropertyChanged(nameof(DataPreviewStateSelectorText));
        OnPropertyChanged(nameof(DataPreviewLoadSelectedTableText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchRefreshText));
        OnPropertyChanged(nameof(DataPreviewDetailsText));
        OnPropertyChanged(nameof(DataPreviewSearchText));
        OnPropertyChanged(nameof(DataPreviewSearchWatermarkText));
        OnPropertyChanged(nameof(DataPreviewCopyTsvText));
        OnPropertyChanged(nameof(DataPreviewPasteText));
        OnPropertyChanged(nameof(DataPreviewPasteWatermarkText));
        OnPropertyChanged(nameof(DataPreviewParsePasteText));
        OnPropertyChanged(nameof(DataPreviewRestoreDraftText));
        OnPropertyChanged(nameof(DataPreviewSaveAsText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchDirtyStateText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        OnPropertyChanged(nameof(DataPreviewPreviousPageText));
        OnPropertyChanged(nameof(DataPreviewNextPageText));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
    }
}
