namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyEngineActionStateChanged()
    {
        OnPropertyChanged(nameof(CanUseEngineActions));
        NotifyRunSelectionActionStateChanged();
        NotifyNodeCatalogSummaryActionStateChanged();
        NotifyWorkflowListActionStateChanged();
        NotifyWorkflowExecutionActionStateChanged();
        NotifyRunMonitorActionStateChanged();
        NotifyWorkflowDraftActionStateChanged();
        NotifyRuntimeEventLogActionStateChanged();
        NotifyDataPreviewActionStateChanged();
        NotifySharedPublicationActionStateChanged();
    }

}
