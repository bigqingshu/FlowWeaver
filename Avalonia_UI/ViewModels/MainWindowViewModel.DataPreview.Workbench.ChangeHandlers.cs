using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnDataPreviewWorkbenchErrorMessageChanged(string? value)
    {
        OnPropertyChanged(nameof(HasDataPreviewWorkbenchError));
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
