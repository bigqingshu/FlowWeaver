namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyDataPreviewWorkbenchRowsChanged()
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchColumns));
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchRows));
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        CopyDataPreviewWorkbenchTsvCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchPagingChanged()
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchPageText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewWorkbenchDirtyStateChanged()
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchDirty));
        OnPropertyChanged(nameof(DataPreviewWorkbenchDirtyStateText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
    }
}
