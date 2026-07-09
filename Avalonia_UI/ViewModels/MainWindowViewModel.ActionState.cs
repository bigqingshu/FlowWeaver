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

    private void NotifyWorkflowListActionStateChanged()
    {
        RefreshWorkflowsCommand.NotifyCanExecuteChanged();
        CreateTemplateWorkflowCommand.NotifyCanExecuteChanged();
        ImportWorkflowCommand.NotifyCanExecuteChanged();
        ExportSelectedWorkflowCommand.NotifyCanExecuteChanged();
        DeleteSelectedWorkflowCommand.NotifyCanExecuteChanged();
        OnPropertyChanged(nameof(CanUseImportWorkflowAction));
        OnPropertyChanged(nameof(ImportWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseExportSelectedWorkflowAction));
        OnPropertyChanged(nameof(ExportSelectedWorkflowDisabledReasonText));
        OnPropertyChanged(nameof(CanUseDeleteSelectedWorkflowAction));
        OnPropertyChanged(nameof(DeleteSelectedWorkflowDisabledReasonText));
    }

    private void NotifyWorkflowExecutionActionStateChanged()
    {
        StartSelectedWorkflowCommand.NotifyCanExecuteChanged();
        PreviewSelectedWorkflowNodeCommand.NotifyCanExecuteChanged();
    }

    private void NotifyRunMonitorActionStateChanged()
    {
        RefreshRunsCommand.NotifyCanExecuteChanged();
        CancelSelectedRunCommand.NotifyCanExecuteChanged();
        RefreshNodeRunsCommand.NotifyCanExecuteChanged();
    }

    private void NotifyWorkflowDraftActionStateChanged()
    {
        LoadSelectedWorkflowDefinitionCommand.NotifyCanExecuteChanged();
        RefreshNodeDefinitionsCommand.NotifyCanExecuteChanged();
        ValidateWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
        ApplySelectedNodeConfigDraftCommand.NotifyCanExecuteChanged();
        NotifyRuntimeOptionsActionStateChanged();
        AddWorkflowDefinitionDraftNodeCommand.NotifyCanExecuteChanged();
        NotifyWorkflowDefinitionNodeActionCommandsChanged();
        AddWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        DeleteWorkflowDefinitionDraftConnectionCommand.NotifyCanExecuteChanged();
        SaveWorkflowDefinitionDraftCommand.NotifyCanExecuteChanged();
    }

    private void NotifyRuntimeOptionsActionStateChanged()
    {
        ApplyRuntimeOptionsDraftCommand.NotifyCanExecuteChanged();
        RegenerateRuntimeOptionsJsonDraftCommand.NotifyCanExecuteChanged();
        ResetRuntimeOptionsSelectedNodeOverrideCommand.NotifyCanExecuteChanged();
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
