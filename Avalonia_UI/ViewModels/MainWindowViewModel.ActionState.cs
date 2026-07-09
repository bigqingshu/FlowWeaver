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

    private void NotifyRunMonitorActionStateChanged()
    {
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyRuntimeEventLogActionStateChanged()
    {
        RefreshRuntimeEventLogCommand.NotifyCanExecuteChanged();
    }

    private void NotifyDataPreviewActionStateChanged()
    {
        RefreshTableRefsCommand.NotifyCanExecuteChanged();
        RefreshSelectedWorkflowNodeDataPreviewCommand.NotifyCanExecuteChanged();
        ShowDataPreviewDetailsCommand.NotifyCanExecuteChanged();
        LoadSelectedDataPreviewTableCommand.NotifyCanExecuteChanged();
    }

    private void NotifySharedPublicationActionStateChanged()
    {
        RefreshSharedPublicationsCommand.NotifyCanExecuteChanged();
        RefreshSharedPublicationVersionsCommand.NotifyCanExecuteChanged();
    }
}
