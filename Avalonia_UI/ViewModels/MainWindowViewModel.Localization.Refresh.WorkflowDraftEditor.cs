namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyWorkflowDraftEditorLocalizedTextChanged()
    {
        OnPropertyChanged(nameof(DataPreviewSectionText));
        OnPropertyChanged(nameof(DataPreviewEmptyText));
        OnPropertyChanged(nameof(DataPreviewPendingText));
        OnPropertyChanged(nameof(DataPreviewRefreshText));
        OnPropertyChanged(nameof(PreviewSelectedNodeText));
        OnPropertyChanged(nameof(DataPreviewSourceText));
        OnPropertyChanged(nameof(RestoreText));
        OnPropertyChanged(nameof(ValidateText));
        OnPropertyChanged(nameof(SaveText));
        OnPropertyChanged(nameof(NodeInstanceIdText));
        OnPropertyChanged(nameof(NodeTypeText));
        OnPropertyChanged(nameof(NodeVersionText));
        OnPropertyChanged(nameof(DisplayNameText));
        OnPropertyChanged(nameof(ConfigJsonText));
    }
}
