using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    partial void OnIsDataPreviewWorkbenchDraftChanged(bool value)
    {
        OnPropertyChanged(nameof(DataPreviewWorkbenchSourceText));
        OnPropertyChanged(nameof(DataPreviewSourceTableMetadataText));
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
