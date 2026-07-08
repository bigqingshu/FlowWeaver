using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanCopyDataPreviewWorkbenchTsv))]
    private void CopyDataPreviewWorkbenchTsv()
    {
        DataPreviewWorkbenchClipboardText = BuildDataPreviewWorkbenchTsv();
    }

    [RelayCommand(CanExecute = nameof(CanSaveDataPreviewWorkbenchAs))]
    private void SaveDataPreviewWorkbenchAs()
    {
        DataPreviewWorkbenchMessage = T("data_preview.save_as_api_pending");
        DataPreviewWorkbenchErrorMessage = null;
    }
}
