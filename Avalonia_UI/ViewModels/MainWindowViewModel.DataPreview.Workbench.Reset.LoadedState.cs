using Avalonia_UI.Models;

namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void ResetDataPreviewWorkbenchLoadedState()
    {
        LoadedDataPreviewTableRef = null;
        dataPreviewWorkbenchGridState = new DataPreviewWorkbenchGridState();
        DataPreviewWorkbenchClipboardText = string.Empty;
        IsDataPreviewWorkbenchDraft = false;
        NotifyDataPreviewWorkbenchPagingChanged();
        NotifyDataPreviewWorkbenchDirtyStateChanged();
    }
}
