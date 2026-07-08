using Avalonia_UI.Models;

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

    partial void OnDataPreviewWorkbenchSearchTextChanged(string value)
    {
        DataPreviewWorkbenchClipboardText = string.Empty;
        ApplyDataPreviewWorkbenchSearch();
        UpdateDataPreviewWorkbenchLoadedMessage();
    }

    partial void OnDataPreviewWorkbenchClipboardTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchClipboardText));
    }

    partial void OnDataPreviewWorkbenchPasteTextChanged(string value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchPasteText));
        ParseDataPreviewWorkbenchPasteCommand.NotifyCanExecuteChanged();
    }

    partial void OnIsDataPreviewWorkbenchDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
    }

    partial void OnLoadedDataPreviewTableRefChanged(TableRefListItemViewModel? value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(CanSaveDataPreviewWorkbenchAsDraft));
        OnPropertyChanged(nameof(DataPreviewWorkbenchSavePolicyText));
        LoadPreviousDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        LoadNextDataPreviewWorkbenchPageCommand.NotifyCanExecuteChanged();
        SaveDataPreviewWorkbenchAsCommand.NotifyCanExecuteChanged();
    }
}
