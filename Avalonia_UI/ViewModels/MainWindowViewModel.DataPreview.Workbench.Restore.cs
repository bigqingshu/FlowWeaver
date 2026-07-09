using CommunityToolkit.Mvvm.Input;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    [RelayCommand(CanExecute = nameof(CanRestoreDataPreviewWorkbenchDraft))]
    private void RestoreDataPreviewWorkbenchDraft()
    {
        RestoreDataPreviewWorkbenchEditableRows();
        ApplyDataPreviewWorkbenchSearch();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
        DataPreviewWorkbenchClipboardText = string.Empty;
        DataPreviewWorkbenchMessage = T("data_preview.draft_restored");
    }
}
