namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsLoadingDataPreviewWorkbenchChanged(bool value)
    {
        OnPropertyChanged(nameof(IsDataPreviewWorkbenchBusy));
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
        RestoreDataPreviewWorkbenchDraftCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
    }
}
