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

    private void NotifyRunSelectionActionStateChanged()
    {
        OnPropertyChanged(nameof(CanUseCancelSelectedRunAction));
        OnPropertyChanged(nameof(CancelSelectedRunDisabledReasonText));
    }

    private void NotifyNodeCatalogSummaryActionStateChanged()
    {
        OnPropertyChanged(nameof(RefreshNodeDefinitionsDisabledReasonText));
    }

}
