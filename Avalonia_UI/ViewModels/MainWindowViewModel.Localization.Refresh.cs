namespace Avalonia_UI.ViewModels;

public partial class MainWindowViewModel
{
    private void NotifyLocalizedTextChanged()
    {
        NotifyAppShellLocalizedTextChanged();
        NotifyConnectionLocalizedTextChanged();
        NotifyDataPreviewWorkbenchLocalizedTextChanged();
        NotifyWorkflowListLocalizedTextChanged();
        NotifyRunsLocalizedTextChanged();
        NotifyWorkflowDefinitionBasicsLocalizedTextChanged();
        NotifyWorkflowDefinitionNodesLocalizedTextChanged();
        NotifyWorkflowNodeConfigLocalizedTextChanged();
        NotifyRuntimeOptionsLocalizedTextChanged();
        NotifyWorkflowStructuredEditSectionLocalizedTextChanged();
        NotifyWorkflowStructuredEditNodeActionsLocalizedTextChanged();
        NotifyWorkflowStructuredEditStatusLocalizedTextChanged();
        NotifyWorkflowDraftDataPreviewLocalizedTextChanged();
        NotifyWorkflowDraftActionsLocalizedTextChanged();
        NotifyWorkflowDraftNodeFieldsLocalizedTextChanged();
        NotifyWorkflowConnectionsLocalizedTextChanged();
        NotifyRecentEventsLocalizedTextChanged();
        NotifyNodeCatalogLocalizedTextChanged();
        NotifyAdvancedDraftJsonLocalizedTextChanged();
        NotifyRuntimeEventLogLocalizedTextChanged();
        NotifyTableRefsLocalizedTextChanged();
        NotifySharedPublicationsLocalizedTextChanged();
        RefreshLocalizedDerivedState();
    }
}
